"""Unit tests for column (decision-table) fixtures; the browser is replaced by a fake UiFixture."""
import pytest

from fixtures.ui.decision_fixture import DecisionFixture, Row, RowFailure
from fixtures.ui.scenario.login import LoginTest


class FakeUi:
    """Records what a fixture asks the UiFixture to do."""

    instances = []

    def __init__(self, name="x"):
        self.calls, self.notes, self.failures, self.closed = [], [], [], False
        self.browser = None
        self.fail_on = None
        FakeUi.instances.append(self)

    def set_browser(self, value):
        self.browser = value

    def start_browser(self, *args):
        return True

    def close_browser(self):
        self.closed = True

    def _ok(self, text):
        self.notes.append(text)
        return True

    def _capture_failure_state(self, key, detail="", description=""):
        self.failures.append((key, detail, description))

    def step(self, name):
        def run(*args):
            self.calls.append((name, args))
            return False if self.fail_on == name else True
        run.__name__ = name
        return run

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self.step(name)


@pytest.fixture(autouse=True)
def fresh_fakes():
    FakeUi.instances = []


class Echo(DecisionFixture):
    ui_class = FakeUi
    INPUTS = ("name", "pin")
    OUTPUTS = ("greeting",)

    def run_row(self, row):
        self.do(self.ui.navigate_to, "http://x")
        return {"greeting": f"Hello {row.name}"}


def run_table(fixture, header, rows, expected_header=None):
    """Plays the calls FitNesse makes for a decision table."""
    fixture.table([header] + [list(r) for r in rows])   # Slim sends the header row, then the data rows
    fixture.begin_table()
    outputs = []
    for row in rows:
        fixture.reset()
        for column, value in zip(header, row):
            if not column.endswith("?"):
                getattr(fixture, "set_" + column.replace(" ", "_"))(value)
        fixture.execute()
        # FitNesse turns the header "login result?" into the method loginResult, which waferslim maps to login_result
        outputs.append({c.rstrip("?"): getattr(fixture, c.rstrip("?").replace(" ", "_"))() for c in header if c.endswith("?")})
    fixture.end_table()
    return outputs


def test_each_row_runs_in_its_own_browser_session_and_returns_outputs():
    outputs = run_table(Echo(), ["name", "greeting?"], [["Asha", "Hello Asha"], ["Ravi", "Hello Ravi"]])
    assert outputs == [{"greeting": "Hello Asha"}, {"greeting": "Hello Ravi"}]
    assert len(FakeUi.instances) == 2 and all(ui.closed for ui in FakeUi.instances)


def test_browser_column_is_optional():
    run_table(Echo(), ["name", "browser", "greeting?"], [["Asha", "", ""], ["Ravi", "firefox", ""]])
    assert [ui.browser for ui in FakeUi.instances] == [None, "firefox"]


def test_missing_columns_read_as_empty():
    class NoPin(Echo):
        def run_row(self, row):
            return {"greeting": f"pin=[{row.pin}] has={row.has('pin')} default={row.get('pin', '0000')}"}
    outputs = run_table(NoPin(), ["name", "greeting?"], [["Asha", ""]])
    assert outputs[0]["greeting"] == "pin=[] has=False default=0000"


def test_secrets_are_masked_in_the_row_step():
    run_table(Echo(), ["name", "pin", "greeting?"], [["Asha", "1234", "Hello Asha"]])
    note = FakeUi.instances[0].notes[0]
    assert "name=Asha" in note and "pin=***" in note and "1234" not in note


def test_failed_step_gives_an_error_value_and_a_failure_record():
    class Breaks(Echo):
        def run_row(self, row):
            self.ui.fail_on = "navigate_to"
            return super().run_row(row)
    outputs = run_table(Breaks(), ["name", "greeting?"], [["Asha", "Hello Asha"]])
    assert outputs[0]["greeting"].startswith("ERROR: Step 'navigate_to' failed")
    key, detail, description = FakeUi.instances[0].failures[0]
    assert key == "row_1_failed" and "navigate_to" in detail and description.startswith("Row 1")


def test_unexpected_exception_is_reported_per_row_and_the_next_row_still_runs():
    class Flaky(Echo):
        def run_row(self, row):
            if row.name == "bad":
                raise ValueError("boom")
            return super().run_row(row)
    outputs = run_table(Flaky(), ["name", "greeting?"], [["bad", ""], ["Ravi", "Hello Ravi"]])
    assert outputs[0]["greeting"] == "ERROR: boom" and outputs[1]["greeting"] == "Hello Ravi"


def test_wrong_result_is_recorded_as_a_failed_step():
    run_table(Echo(), ["name", "greeting?"], [["Asha", "Goodbye Asha"]])
    key, detail, description = FakeUi.instances[0].failures[0]
    assert "expected 'Goodbye Asha' but was 'Hello Asha'" in detail


def test_matching_and_slim_comparator_results_are_not_flagged():
    run_table(Echo(), ["name", "greeting?"], [["Asha", "Hello Asha"], ["Ravi", "=~/Hello .*/"], ["Mia", ""]])
    assert all(not ui.failures for ui in FakeUi.instances)


def test_unknown_output_column_is_a_clear_error():
    fixture = Echo()
    fixture.begin_table()
    fixture.reset()
    fixture.set_name("Asha")
    fixture.execute()
    with pytest.raises(AttributeError, match="No output 'nothing'"):
        fixture.nothing
    fixture.end_table()


def test_environment_variables_in_cells_are_resolved(tmp_path, monkeypatch):
    from core import flow as ui_flow
    folder = tmp_path / "FitNesseRoot" / "VariablePage"
    folder.mkdir(parents=True)
    (folder / "content.txt").write_text("!define UI_BASE_URL {http://localhost:8080/}", encoding="utf-8")
    monkeypatch.setattr(ui_flow, "_WORKSPACE_DIR", str(tmp_path))

    class Url(Echo):
        def run_row(self, row):
            return {"greeting": row.name}
    outputs = run_table(Url(), ["name", "greeting?"], [["${UI_BASE_URL}home", ""]])
    assert outputs[0]["greeting"] == "http://localhost:8080/home"


def test_row_object():
    row = Row({"a": "1", "password": "secret", "empty": ""})
    assert row.a == "1" and row.nothing == "" and row.get("empty", "d") == "d" and row.has("a")
    assert row.masked() == {"a": "1", "password": "***", "empty": ""}


def test_subclass_must_implement_run_row():
    class Empty(DecisionFixture):
        ui_class = FakeUi
    outputs = run_table(Empty(), ["x", "y?"], [["1", ""]])
    assert "must implement run_row" in outputs[0]["y"]


# ── The Login example fixture ─────────────────────────────────────────────────
class FakeLocator:
    def __init__(self, text="", hidden=False):
        self.text, self.hidden = text, hidden

    def count(self):
        return 1 if self.text else 0

    @property
    def first(self):
        return self

    def inner_text(self):
        return self.text

    def is_hidden(self):
        return self.hidden


class FakePage:
    def __init__(self, hidden):
        self.hidden = hidden

    def locator(self, selector):
        return FakeLocator(hidden=self.hidden)

    def wait_for_timeout(self, ms):
        pass


class LoginUi(FakeUi):
    error_text = ""
    overlay_hidden = False

    def __init__(self, name="x"):
        super().__init__(name)
        self._page = FakePage(LoginUi.overlay_hidden)

    def _locator(self, name):
        if "overlay" in name:
            return FakeLocator(hidden=LoginUi.overlay_hidden)
        return FakeLocator(LoginUi.error_text)


def login(monkeypatch, error="", hidden=False):
    LoginUi.error_text, LoginUi.overlay_hidden = error, hidden
    monkeypatch.setattr(LoginTest, "ui_class", LoginUi)
    return run_table(LoginTest(), ["username", "password", "login result?"], [["admin", "pw", ""]])[0]["login result"]


def test_login_success_when_the_login_screen_closes(monkeypatch):
    assert login(monkeypatch, hidden=True) == "Success"
    calls = [c for c in LoginUi.instances[0].calls]
    assert ("navigate_to", ("${UI_BASE_URL}",)) in calls
    assert ("enter_text_with_value", ("LoginPage.username", "admin")) in calls
    assert ("click_element", ("LoginPage.login button",)) in calls


def test_login_reports_the_error_text_shown_by_the_form(monkeypatch):
    assert login(monkeypatch, error="Invalid username or password.") == "Invalid username or password."


def test_login_times_out_cleanly(monkeypatch):
    assert login(monkeypatch) == "No response from the login form"
