"""
Flow engine for the UI fixture: variables, control flow (IF / ELSE / FOR EACH / BREAK),
error-handling modes (retry / continue / stop on failure) and reusable components.

Every FitNesse step method is wrapped with @step. The wrapper is the single place that:
  * substitutes ${variables} in the arguments,
  * records steps while a FOR EACH body is being collected (replayed at END LOOP),
  * skips steps inside an inactive IF branch, after BREAK or after STOP ON FAILURE,
  * retries the next step when RETRY ACTION was requested.
"""
import functools
import html
import os
import re
import time

from core.logger import logger

_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][\w.\-]*)\}")
_ANCHOR_PATTERN = re.compile(r"<a[^>]*>([\s\S]*?)</a>")
_COMPARISON_PATTERN = re.compile(r"^(.*?)\s*(==|!=|>=|<=|~=|>|<|\bnot contains\b|\bcontains\b)\s*(.*)$", re.IGNORECASE)
_FALSY = {"", "false", "0", "no", "none", "null", "off"}
_MAX_COMPONENT_DEPTH = 5
_WORKSPACE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
COMPONENTS_DIR = os.path.join(_WORKSPACE_DIR, "data", "components")


def substitute_variables(value, variables: dict):
    """Replaces ${name} with the stored variable value; unknown names are left untouched."""
    if not isinstance(value, str) or "${" not in value:
        return value
    return _VAR_PATTERN.sub(lambda m: str(variables[m.group(1)]) if m.group(1) in variables else m.group(0), value)


def clean_cell(value):
    """Removes FitNesse's HTML escaping and auto-generated anchors from a table cell value."""
    if not isinstance(value, str):
        return value
    return html.unescape(_ANCHOR_PATTERN.sub(lambda m: m.group(1), value)).strip()


class StepError(str):
    """An error message returned to FitNesse; counted as a failed step."""


def is_failure(result) -> bool:
    """A step failed when it returns False, an inline failure-screenshot link or a StepError."""
    return result is False or isinstance(result, StepError) or (isinstance(result, str) and result.startswith("<a "))


def step(func=None, *, flow=False, raw=False, getter=False, always=False):
    """
    Decorator for FitNesse-callable step methods.

    flow   - control-flow keyword (IF/ELSE/END IF/FOR EACH/END LOOP/BREAK): never skipped.
    raw    - legacy step: only ${variable} substitution, arguments are otherwise untouched.
    getter - returns data (not pass/fail): never retried and never counted as a failure.
    always - executes even when skipped or halted (e.g. close browser), but is still recorded in loops.
    """
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(self, *args):
            return self._dispatch(fn, args, flow=flow, raw=raw, getter=getter, always=always)
        return wrapper
    return decorate(func) if func is not None else decorate


class FlowMixin:
    """Variables, control flow, error handling and reusable components."""

    def _init_flow(self) -> None:
        self._vars: dict = {}
        self._flow_stack: list = []
        self._halted: bool = False
        self._stop_on_failure: bool = False
        self._retry_next: int = 0
        self._suppress_failure_capture: int = 0
        self._component_depth: int = 0
        self._step_failures: list = []

    # ── Dispatcher ────────────────────────────────────────────────────────────
    def _dispatch(self, fn, args, *, flow, raw, getter, always):
        name = fn.__name__
        recording = self._recording_frame()
        if recording is not None:
            return self._record_step(recording, name, args, flow)

        args = self._prepare_args(args, raw)

        if flow:
            return fn(self, *args)
        if not always:
            if not self._is_active():
                return "skipped"
            if self._halted:
                return "skipped (stop on failure)"

        retries = 0 if (getter or always) else self._retry_next
        if retries:
            self._retry_next = 0
        result = self._run_with_retries(fn, args, retries)
        if not getter and not always and is_failure(result):
            self._step_failures.append(name)
            if self._stop_on_failure:
                self._halted = True
        return result

    def _prepare_args(self, args, raw):
        prepared = []
        for arg in args:
            arg = substitute_variables(arg, self._vars)
            prepared.append(arg if raw else clean_cell(arg))
        return tuple(prepared)

    def _run_with_retries(self, fn, args, retries):
        result = None
        for attempt in range(retries + 1):
            last_attempt = attempt == retries
            if not last_attempt:
                self._suppress_failure_capture += 1
            try:
                result = fn(self, *args)
            finally:
                if not last_attempt:
                    self._suppress_failure_capture -= 1
            if not is_failure(result):
                return result
            if not last_attempt:
                logger.info(f"[UiFixture] Retry {attempt + 1}/{retries} for step '{fn.__name__}'")
                time.sleep(1)
        return result

    # ── Flow state helpers ────────────────────────────────────────────────────
    def _is_active(self) -> bool:
        for frame in self._flow_stack:
            if frame["kind"] == "if" and not frame["active"]:
                return False
            if frame["kind"] == "loop" and (frame.get("broken") or frame.get("skip")):
                return False
        return True

    def _recording_frame(self):
        for frame in self._flow_stack:
            if frame["kind"] == "loop" and frame["recording"]:
                return frame
        return None

    def _record_step(self, frame, name, args, flow):
        if name == "for_each_in":
            frame["depth"] += 1
        elif name == "end_loop":
            if frame["depth"] == 0:
                return self._replay_loop(frame)
            frame["depth"] -= 1
        frame["steps"].append((name, args))
        return True

    # ── Variables ─────────────────────────────────────────────────────────────
    @step
    def set_variable_to(self, name: str, value: str) -> bool:
        """| set variable | name | to | value |"""
        self._vars[str(name).strip()] = value
        logger.info(f"[UiFixture] Variable set: {name} = {value}")
        return self._ok(f"Set variable '{name}' = '{value}'")

    @step(getter=True)
    def get_variable(self, name: str) -> str:
        """| check | get variable | name | expected |"""
        return str(self._vars.get(str(name).strip(), "variable not found"))

    # ── Control flow ──────────────────────────────────────────────────────────
    @step(flow=True)
    def if_condition(self, condition: str) -> bool:
        """| if condition | ${role} == admin |  or  | if condition | element visible: #banner |"""
        parent_active = self._is_active()
        result = parent_active and self._evaluate_condition(condition)
        self._flow_stack.append({"kind": "if", "active": result, "taken": result})
        if parent_active:
            self._ok(f"IF {condition} -> {result}")
        return True

    @step(flow=True)
    def else_branch(self) -> bool:
        """| else branch |"""
        frame = self._top_frame("if")
        if frame is None:
            return StepError("ELSE without IF")
        frame["active"] = (not frame["taken"]) and self._parent_active_of(frame)
        frame["taken"] = True
        return True

    @step(flow=True)
    def end_if(self) -> bool:
        """| end if |"""
        if self._top_frame("if") is None:
            return StepError("END IF without IF")
        self._flow_stack.pop()
        return True

    @step(flow=True)
    def for_each_in(self, variable: str, items: str) -> bool:
        """| for each | item | in | a,b,c |  (or a numeric range such as 1..5)"""
        values = self._expand_items(items)
        self._flow_stack.append({
            "kind": "loop", "variable": str(variable).strip(), "items": values,
            "recording": True, "depth": 0, "steps": [], "skip": not self._is_active(),
        })
        return True

    @step(flow=True)
    def end_loop(self) -> bool:
        """| end loop |"""
        return StepError("END LOOP without FOR EACH")

    @step(flow=True)
    def break_loop(self) -> bool:
        """| break loop |"""
        frame = self._top_frame("loop", search=True)
        if frame is None:
            return StepError("BREAK outside a loop")
        if self._is_active():
            frame["broken"] = True
            self._ok("BREAK loop")
        return True

    def _top_frame(self, kind, search=False):
        frames = reversed(self._flow_stack) if search else [self._flow_stack[-1]] if self._flow_stack else []
        for frame in frames:
            if frame["kind"] == kind:
                return frame
        return None

    def _parent_active_of(self, frame) -> bool:
        index = self._flow_stack.index(frame)
        return all(f["kind"] != "if" or f["active"] for f in self._flow_stack[:index]) and not any(
            f["kind"] == "loop" and (f.get("broken") or f.get("skip")) for f in self._flow_stack[:index])

    def _replay_loop(self, frame):
        frame["recording"] = False
        failures_before = len(self._step_failures)
        iterations = 0
        if not frame["skip"]:
            for item in frame["items"]:
                if frame.get("broken") or self._halted:
                    break
                frame["broken"] = False
                self._vars[frame["variable"]] = item
                iterations += 1
                for name, args in frame["steps"]:
                    getattr(self, name)(*args)
        self._flow_stack.remove(frame)
        failed = len(self._step_failures) - failures_before
        if frame["skip"]:
            return "skipped"
        self._ok(f"FOR EACH {frame['variable']} ({iterations} iteration(s))")
        return True if not failed else StepError(f"{failed} step(s) failed inside the loop")

    @staticmethod
    def _expand_items(items: str) -> list:
        text = clean_cell(str(items)).strip()
        match = re.fullmatch(r"(-?\d+)\s*\.\.\s*(-?\d+)", text)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            step_size = 1 if end >= start else -1
            return [str(n) for n in range(start, end + step_size, step_size)]
        return [part.strip() for part in text.split(",") if part.strip()]

    def _evaluate_condition(self, condition: str) -> bool:
        text = clean_cell(substitute_variables(str(condition), self._vars)).strip()
        prefix_match = re.match(r"^(element visible|element present|element enabled|text present)\s*:\s*(.+)$", text, re.IGNORECASE)
        if prefix_match:
            return self._peek(prefix_match.group(1).lower(), prefix_match.group(2).strip())
        match = _COMPARISON_PATTERN.match(text)
        if match:
            left, operator, right = match.group(1).strip(), match.group(2).lower(), match.group(3).strip()
            return self._compare(left, operator, right)
        return text.lower() not in _FALSY

    @staticmethod
    def _compare(left: str, operator: str, right: str) -> bool:
        if operator == "contains":
            return right in left
        if operator == "not contains":
            return right not in left
        if operator == "~=":
            return left.lower() == right.lower()
        try:
            left_value, right_value = float(left), float(right)
        except ValueError:
            left_value, right_value = left, right
        if operator == "==":
            return left_value == right_value
        if operator == "!=":
            return left_value != right_value
        if isinstance(left_value, str):
            return False  # ordering comparisons only make sense for numbers
        return {">": left_value > right_value, "<": left_value < right_value,
                ">=": left_value >= right_value, "<=": left_value <= right_value}[operator]

    # ── Error handling ────────────────────────────────────────────────────────
    @step
    def retry_action(self, times: str) -> bool:
        """| retry action | 3 |  - the NEXT step is retried up to 3 more times if it fails."""
        try:
            self._retry_next = max(0, int(str(times).strip()))
        except ValueError:
            return StepError(f"Invalid retry count '{times}'")
        return self._ok(f"Retry next action up to {self._retry_next} time(s)")

    @step(always=True)
    def continue_on_failure(self) -> bool:
        """| continue on failure |  - default: later steps still run after a failure."""
        self._stop_on_failure = False
        self._halted = False
        return self._ok("Continue on failure")

    @step(always=True)
    def stop_on_failure(self) -> bool:
        """| stop on failure |  - after the first failed step the remaining steps are skipped."""
        self._stop_on_failure = True
        return self._ok("Stop on failure")

    # ── Reusable components ───────────────────────────────────────────────────
    @step
    def execute_reusable_component(self, name: str) -> bool:
        """| execute reusable component | Login |"""
        return self._run_component(name, "")

    @step
    def execute_reusable_component_with(self, name: str, parameters: str) -> bool:
        """| execute reusable component | Login | with | user=qa,pass=secret |"""
        return self._run_component(name, parameters)

    def _run_component(self, name: str, parameters: str):
        safe_name = re.sub(r"[^\w\- ]", "", str(name)).strip()
        path = os.path.join(COMPONENTS_DIR, f"{safe_name}.flow")
        if not safe_name or not os.path.isfile(path):
            logger.error(f"[UiFixture] Reusable component not found: {path}")
            return StepError(f"Component '{name}' not found in data/components")
        if self._component_depth >= _MAX_COMPONENT_DEPTH:
            return StepError(f"Component nesting deeper than {_MAX_COMPONENT_DEPTH}")

        missing = object()
        saved_params = {}
        for pair in str(parameters).split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                saved_params.setdefault(key.strip(), self._vars.get(key.strip(), missing))
                self._vars[key.strip()] = value.strip()

        failures_before = len(self._step_failures)
        self._component_depth += 1
        try:
            with open(path, "r", encoding="utf-8") as component_file:
                for line in component_file:
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if not line.strip() or line.lstrip().startswith("#") or not cells[0]:
                        continue
                    keyword = cells[0].lower()
                    if keyword == "note":
                        continue
                    if keyword in ("ensure", "reject", "show"):
                        cells = cells[1:]
                    elif keyword == "check":
                        cells = cells[1:-1]  # trailing cell is the expected value; the step itself decides pass/fail
                    if not cells:
                        continue
                    method = "_".join(" ".join(cells[0::2]).lower().split())
                    target = getattr(self, method, None)
                    if target is None:
                        self._step_failures.append(method)
                        logger.error(f"[UiFixture] Unknown step '{method}' in component '{name}'")
                        continue
                    target(*cells[1::2])
        finally:
            self._component_depth -= 1
            for key, old in saved_params.items():  # parameters are local; variables set by the component persist
                if old is missing:
                    self._vars.pop(key, None)
                else:
                    self._vars[key] = old

        failed = len(self._step_failures) - failures_before
        self._ok(f"Execute reusable component '{name}'")
        return True if not failed else StepError(f"Component '{name}': {failed} step(s) failed")
