"""
Base class for column ("decision table") UI fixtures: one class per feature, one column per input, one row per data set.

    !|login test|
    |username|password|browser |login result?                |
    |admin   |admin123|        |Success                      |
    |admin   |wrong   |firefox |Invalid username or password.|

  * input columns   -> available as row.username, row.password, row.browser (an empty cell means "not given")
  * output columns  -> end with "?"; whatever run_row() returns under that name is compared by FitNesse
  * browser column  -> optional; when it is missing or empty the browser chosen in the environment settings is used
  * every row runs in its own fresh browser session, with a "Row n" step in Allure and the simple report
  * a row that breaks gets a failure screenshot, and a wrong result is recorded as a failed step as well

Writing a fixture:

    class LoginTest(DecisionFixture):
        INPUTS = ("username", "password", "browser")
        OUTPUTS = ("login_result",)

        def run_row(self, row):
            self.do(self.ui.navigate_to, "${UI_BASE_URL}")
            self.do(self.ui.enter_text_with_value, "LoginPage.username", row.username)
            ...
            return {"login_result": "Success"}
"""
import os
import re

from core.fixture_meta import input_column, output_column
from core.logger import logger
from core.flow import clean_cell, is_failure, substitute_variables

_SECRET_MARKERS = ("pass", "pwd", "secret", "token", "otp", "cvv", "pin")


class RowFailure(Exception):
    """Raised by do() when a UI step of the row fails; the row then reports ERROR instead of a result."""


class Row:
    """The input cells of one table row. Unknown or empty columns read as an empty string."""

    def __init__(self, values: dict) -> None:
        self._values = dict(values)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._values.get(name, "")

    def get(self, name: str, default=None):
        """The cell value, or the default when the column is missing or the cell is empty."""
        value = self._values.get(name)
        return default if value in (None, "") else value

    def has(self, name: str) -> bool:
        return self._values.get(name) not in (None, "")

    def as_dict(self) -> dict:
        return dict(self._values)

    def masked(self) -> dict:
        """Row values with anything that looks like a secret hidden (used for reports and logs)."""
        return {key: ("***" if value and any(marker in key for marker in _SECRET_MARKERS) else value)
                for key, value in self._values.items()}


class DecisionFixture:
    """Slim decision-table fixture that drives the browser through a UiFixture, one fresh session per row."""

    INPUTS: tuple = ()      # documented input columns (snake_case)
    OUTPUTS: tuple = ()     # documented output columns (snake_case, without the "?")
    DESCRIPTION: str = ""   # one line for the Step Builder
    COLUMNS: tuple = ()     # core.fixture_meta columns; derived from INPUTS / OUTPUTS when empty

    ui_class = None         # defaults to UiFixture; tests replace it with a fake

    @classmethod
    def columns(cls) -> tuple:
        """The declared columns, or one optional column per INPUTS / OUTPUTS entry."""
        if cls.COLUMNS:
            return tuple(cls.COLUMNS)
        return tuple(input_column(name) for name in cls.INPUTS) + tuple(output_column(name) for name in cls.OUTPUTS)

    def __init__(self) -> None:
        self._inputs: dict = {}
        self._outputs: dict = {}
        self._row_error = ""
        self._row_number = 0
        self._expected_rows: list = []
        self._header: list = []
        self._ui = None

    # ── Slim decision-table protocol ──────────────────────────────────────────
    def table(self, table) -> None:
        """Slim hands over the whole table; the expected values let the reports flag a wrong result."""
        try:
            rows = [[clean_cell(str(cell)) for cell in row] for row in table]
            # Slim passes the column-name row first, then one row per data set.
            self._header = [self._snake(cell) for cell in rows[0]]
            self._expected_rows = rows[1:]
        except Exception:
            self._header, self._expected_rows = [], []

    def begin_table(self) -> None:
        self._row_number = 0
        self.on_table_start()

    def reset(self) -> None:
        self._inputs = {}
        self._outputs = {}
        self._row_error = ""

    def execute(self) -> None:
        self._row_number += 1
        row = Row(self._inputs)
        masked = ", ".join(f"{key}={value}" for key, value in row.masked().items() if value != "")
        try:
            self._start_row(row, masked)
            self._outputs = {self._snake(key): value for key, value in (self.run_row(row) or {}).items()}
            self._judge_row(masked)
        except Exception as error:
            self._row_error = str(error) or error.__class__.__name__
            logger.error(f"[DecisionFixture] Row {self._row_number} failed: {self._row_error}")
            self._record_row_failure(masked)
        finally:
            self._close_row()

    def end_table(self) -> None:
        self._close_row()
        self.on_table_end()

    def __getattr__(self, name: str):
        """set_<column> stores an input cell; any other name is an output column (read after execute)."""
        if name.startswith("_"):
            raise AttributeError(name)
        if name.startswith("set_"):
            column = name[4:]

            def setter(value):
                self._inputs[column] = substitute_variables(clean_cell(value), {})
            return setter
        if self._row_error:
            return lambda: f"ERROR: {self._row_error}"
        if name in self._outputs:
            return lambda: "" if self._outputs[name] is None else str(self._outputs[name])
        raise AttributeError(f"No output '{name}' was produced by {self.__class__.__name__}.run_row")

    # ── What a fixture author uses ────────────────────────────────────────────
    @property
    def ui(self):
        """The UiFixture of the current row (fresh browser session)."""
        return self._ui

    def run_row(self, row: Row) -> dict:
        """Drive the application for one row and return {output_column: value}. Override in the fixture."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement run_row(row)")

    def row_verdict(self, outputs: dict) -> str:
        """Optional: return a message to mark the row failed in the reports even when no expected cell says so."""
        return ""

    def on_table_start(self) -> None:
        """Optional hook before the first row."""

    def on_table_end(self) -> None:
        """Optional hook after the last row."""

    def do(self, step, *args):
        """Runs one UiFixture step; a failed step stops the row with a clear message."""
        result = step(*args)
        if is_failure(result):
            raise RowFailure(f"Step '{getattr(step, '__name__', step)}' failed ({', '.join(str(a) for a in args)})")
        return result

    # ── Row lifecycle ─────────────────────────────────────────────────────────
    def _new_ui(self):
        if self.ui_class is not None:
            return self.ui_class(self.__class__.__name__)
        from .ui_fixture import UiFixture
        return UiFixture(self.__class__.__name__)

    def _start_row(self, row: Row, masked: str) -> None:
        self._close_row()
        self._ui = self._new_ui()
        # Every row is its own test case in Allure, named after the page and its (masked) data.
        page = os.environ.get("FITNESSE_PAGE_NAME") or self.__class__.__name__
        self._ui.set_test_name(f"{page} - row {self._row_number}: {masked or 'no input'}"[:140])
        if row.has("browser"):
            self._ui.set_browser(row.browser)     # otherwise the browser selected in the environment settings
        if self._ui.start_browser() is False:
            raise RowFailure("The browser could not be started")
        self._ui._ok(f"ROW {self._row_number}: {masked or 'no input'}")

    def _judge_row(self, masked: str) -> None:
        """Compares each output with the expected cell so Allure and the simple report show a wrong result."""
        mismatches = []
        expected_row = self._expected_rows[self._row_number - 1] if self._row_number - 1 < len(self._expected_rows) else []
        for index, column in enumerate(self._header):
            if index >= len(expected_row):
                continue
            name = column.rstrip("?")
            expected = expected_row[index]
            if not column.endswith("?") or expected == "" or name not in self._outputs:
                continue
            if re.match(r"^(=~|~=|<|>|!|_$)", expected):
                continue                              # Slim comparators: FitNesse alone judges these
            actual = "" if self._outputs[name] is None else str(self._outputs[name])
            if actual != expected:
                mismatches.append(f"{name}: expected '{expected}' but was '{actual}'")
        verdict = self.row_verdict(self._outputs)
        if verdict:
            mismatches.append(verdict)
        if mismatches:
            self._record_row_failure(masked, "; ".join(mismatches))
        else:
            results = ", ".join(f"{k}={v}" for k, v in self._outputs.items())
            self._ui._ok(f"ROW {self._row_number} result: {results}")

    def _record_row_failure(self, masked: str, detail: str = "") -> None:
        if self._ui is None:
            return
        reason = detail or self._row_error
        try:
            self._ui._capture_failure_state(f"row_{self._row_number}_failed", reason, f"Row {self._row_number} ({masked})")
        except Exception as error:
            logger.debug(f"[DecisionFixture] Could not record the failed row: {error}")

    def _close_row(self) -> None:
        if self._ui is not None:
            try:
                self._ui.close_browser()
            except Exception as error:
                logger.debug(f"[DecisionFixture] Browser cleanup ignored: {error}")
            self._ui = None

    @staticmethod
    def _snake(text: str) -> str:
        keep_question = text.strip().endswith("?")
        value = re.sub(r"[^0-9a-zA-Z]+", "_", text.strip().rstrip("?")).strip("_").lower()
        return value + ("?" if keep_question else "")
