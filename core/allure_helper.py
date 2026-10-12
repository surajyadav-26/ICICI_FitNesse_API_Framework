"""
Custom Allure JSON Results Compiler.
Symmetrically writes standard Allure-compatible JSON test results, steps,
and attachments directly to disk for both API and UI test runs.

One result is kept per test page and process (see AllureHelper.for_test): every fixture used by the page adds its
steps to the same result, and the result file is rewritten after each change so the report has data even when a
test never closes its browser or stops half way.
"""
import json
import os
import time
import uuid

from core.config import Config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLURE_RESULTS_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")

_ACTIVE_RESULTS: dict = {}

# Test kinds shown in Allure's Behaviors / Categories tabs and as tags, so UI, API, visual and accessibility runs
# can be told apart and filtered.
KINDS = {"ui": "UI", "api": "API", "visual": "Visual", "accessibility": "Accessibility"}


class AllureHelper:
    """
    Lightweight, robust, lifecycle-free Allure JSON result builder.
    Bypasses Pytest dependencies to allow clean, concurrent SLiM runs.
    """

    def __init__(self, test_name: str, suite_name: str = "FitNesse Suite") -> None:
        self.test_name = str(test_name).strip()
        self.suite_name = str(suite_name).strip()
        self.start_time = int(time.time() * 1000)
        self.steps = []
        self.attachments = []
        self.status = "passed"  # Default: passed
        self.error_message = ""
        self.error_trace = ""
        self.test_uuid = str(uuid.uuid4())
        self.kinds = []            # kinds of test that ran on this page, in the order they were first used
        self.parameters = {}       # name -> value shown on the test (browser, url, ...)
        self.flaky_note = ""       # set when the test failed first and passed on a retry

    def mark(self, kind: str, **parameters) -> None:
        """Records what kind of test this page ran (ui / api / visual / accessibility) and optional parameters."""
        if kind in KINDS and kind not in self.kinds:
            self.kinds.append(kind)
        for name, value in parameters.items():
            if value not in (None, ""):
                self.parameters.setdefault(str(name), str(value))

    def add_parameters(self, values: dict) -> None:
        """Adds name/value pairs shown on the test (long values are cut; an empty value is skipped)."""
        for name, value in (values or {}).items():
            text = str(value).strip()
            if text:
                self.parameters.setdefault(str(name), text[:200])

    def recover(self, note: str) -> None:
        """A retry passed: the result is passed again, but it is flagged flaky and keeps the failed attempt's steps."""
        self.status = "passed"
        self.error_message = ""
        self.error_trace = ""
        self.flaky_note = str(note).strip()
        self.add_step(f"Passed on a retry - {self.flaky_note}", "passed", 1)

    @classmethod
    def for_test(cls, test_name: str, suite_name: str = "FitNesse Suite") -> "AllureHelper":
        """Returns the shared result of this test page, creating it on first use."""
        key = (str(suite_name).strip(), str(test_name).strip())
        helper = _ACTIVE_RESULTS.get(key)
        if helper is None:
            helper = cls(test_name, suite_name)
            _ACTIVE_RESULTS[key] = helper
        return helper

    def add_step(self, name: str, status: str = "passed", duration_ms: int = 10, attachments: list = None,
                 message: str = "") -> None:
        """Appends a completed sub-step (optionally with its own attachments) and saves the result."""
        s_time = int(time.time() * 1000) - int(duration_ms)
        step = {
            "name": str(name).strip(),
            "status": str(status).strip(),
            "stage": "finished",
            "start": s_time,
            "stop": s_time + int(duration_ms),
        }
        if attachments:
            step["attachments"] = list(attachments)
        if message and status != "passed":
            step["statusDetails"] = {"message": str(message).strip()}
        self.steps.append(step)
        self.write_result()

    def add_attachment(self, name: str, content: any, mime_type: str = "application/json", file_ext: str = "json",
                       step: bool = False):
        """
        Saves an attachment file on disk (like JSON payload or PNG bytes).
        By default it is linked to the whole test; with step=True the link dict is returned instead so the caller can
        place it inside a step.
        """
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
        attach_uuid = str(uuid.uuid4())
        attach_filename = f"{attach_uuid}-attachment.{file_ext}"
        attach_path = os.path.join(ALLURE_RESULTS_DIR, attach_filename)

        try:
            if isinstance(content, bytes):
                with open(attach_path, "wb") as f:
                    f.write(content)
            else:
                with open(attach_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

            link = {"name": str(name).strip(), "source": attach_filename, "type": mime_type}
            if step:
                return link
            self.attachments.append(link)
        except Exception as e:
            print(f"[ALLURE WARNING] Attaching {name} failed: {e}")
        return None

    def set_failed(self, message: str, traceback: str = "") -> None:
        """Flags the test run state as failed with details (the first failure message is kept)."""
        if self.status != "failed":
            self.error_message = str(message).strip()
            self.error_trace = str(traceback).strip()
        self.status = "failed"

    def write_result(self) -> None:
        """Compiles and writes (or refreshes) the standard Allure JSON result on disk."""
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
        stop_time = int(time.time() * 1000)

        result = {
            "uuid": self.test_uuid,
            "historyId": str(uuid.uuid5(uuid.NAMESPACE_DNS, self.test_name)),
            "fullName": f"FitNesseRoot.FrontPage.{self.suite_name}.{self.test_name}",
            "labels": [
                {"name": "parentSuite", "value": "FitNesseRoot"},
                {"name": "suite", "value": self.suite_name},
                {"name": "subSuite", "value": self.test_name},
                {"name": "framework", "value": f"{Config.APP_NAME} Framework"},
                {"name": "language", "value": "python"},
                {"name": "epic", "value": Config.APP_NAME},
                {"name": "story", "value": self.test_name},
                {"name": "severity", "value": "normal"},
            ] + [{"name": "feature", "value": KINDS[kind]} for kind in self.kinds]
              + [{"name": "tag", "value": KINDS[kind]} for kind in self.kinds],
            "parameters": [{"name": name, "value": value} for name, value in self.parameters.items()],
            "links": self._links(),
            "description": self._description(),
            "name": self.test_name,
            "status": self.status,
            "stage": "finished",
            "steps": self.steps,
            "attachments": self.attachments,
            "start": self.start_time,
            "stop": stop_time
        }

        if self.status == "failed":
            result["statusDetails"] = {
                "message": self.error_message,
                "trace": self.error_trace
            }
        elif self.flaky_note:
            result["statusDetails"] = {"flaky": True, "message": self.flaky_note}

        result_path = os.path.join(ALLURE_RESULTS_DIR, f"{self.test_uuid}-result.json")
        temporary = result_path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            os.replace(temporary, result_path)
        except Exception as e:
            print(f"[ALLURE WARNING] Writing result JSON failed: {e}")

    def _links(self) -> list:
        """A link back to the FitNesse page that was running, so QA can open the table and re-run it."""
        page = os.environ.get("FITNESSE_PAGE_PATH", "").strip()
        if not page:
            return []
        return [{"name": f"Open the test page ({page})", "url": f"{Config.fitnesse_url()}/{page}", "type": "custom"}]

    def _description(self) -> str:
        kinds = ", ".join(KINDS[kind] for kind in self.kinds) or "not classified"
        lines = [f"Page: {self.test_name}", f"Suite: {self.suite_name}", f"Test kind: {kinds}"]
        lines += [f"{name}: {value}" for name, value in self.parameters.items()]
        return "\n\n".join(lines)

    def finish(self) -> None:
        """Persist the final result and remove it from the active per-test cache."""
        self.write_result()
        for key, active_result in list(_ACTIVE_RESULTS.items()):
            if active_result is self:
                del _ACTIVE_RESULTS[key]


def current_names(default_test: str) -> tuple:
    """Test and suite name of the running FitNesse page (falls back to the given default test name)."""
    test_name = os.environ.get("FITNESSE_PAGE_NAME") or default_test
    suite_name = "API Tests"
    parts = [p.strip() for p in os.environ.get("FITNESSE_PAGE_PATH", "").split(".") if p.strip()]
    if len(parts) >= 3:
        suite_name = parts[-2]      # "FrontPage.Suite.Test" -> "Suite"
    elif len(parts) == 2:
        suite_name = parts[-1]
    return str(test_name).strip(), suite_name


def record_http_step(default_test: str, step_name: str, ok: bool, duration_ms: int = 0,
                     attachments: list = None, message: str = "") -> None:
    """
    Adds one step for an HTTP call to the running page's Allure result.
    attachments: list of (name, content, mime_type, file_ext) shown inside the step.
    """
    test_name, suite_name = current_names(default_test)
    if test_name == suite_name:
        return  # parent suite pages must not create empty cards
    helper = AllureHelper.for_test(test_name, suite_name)
    helper.mark("api")
    links = []
    for name, content, mime_type, file_ext in (attachments or []):
        link = helper.add_attachment(name, content, mime_type, file_ext, step=True)
        if link:
            links.append(link)
    if not ok:
        helper.set_failed(message or step_name)
    helper.add_step(step_name, "passed" if ok else "failed", max(int(duration_ms), 1), links, message)
