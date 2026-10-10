"""The `visual test` column table, driven with a fake browser session (no browser needed)."""
import pytest

from core import visual_compare
from core.visual_compare import VisualResult
from fixtures.visual.visual_test import VisualTest


class FakePage:
    def __init__(self):
        self.viewport = None

    def set_viewport_size(self, size):
        self.viewport = size


class FakeUi:
    instances = []
    next_result = None

    def __init__(self, name="x"):
        self._page = FakePage()
        self._last_visual = None
        self.notes, self.opened, self.ignored, self.threshold, self.checked, self.closed = [], [], [], None, [], False
        FakeUi.instances.append(self)

    def set_browser(self, value):
        self.browser = value

    def set_test_name(self, name):
        self.test_name = name

    def start_browser(self, *args):
        return True

    def close_browser(self):
        self.closed = True

    def navigate_to(self, url):
        self.opened.append(url)
        return True

    def ignore_visual_region(self, locator):
        self.ignored.append(locator)
        return True

    def set_visual_threshold(self, value):
        self.threshold = value
        return True

    def verify_visual_match(self, name):
        self.checked.append(name)
        self._last_visual = FakeUi.next_result
        return self._last_visual.status != "failed"

    def _ok(self, text):
        self.notes.append((text, "PASSED", ""))
        return True

    def _capture_failure_state(self, *args, **kwargs):
        self.notes.append(("failure", args, ""))


def result(status="passed", pct=0.0, message="Matches baseline"):
    return VisualResult(status, "login page", "chromium-1600x1043", mismatch_pct=pct, message=message)


def play(header, rows):
    fixture = VisualTest()
    fixture.table([header] + [list(r) for r in rows])
    fixture.begin_table()
    outputs = []
    for row in rows:
        fixture.reset()
        for column, value in zip(header, row):
            if not column.endswith("?"):
                getattr(fixture, "set_" + column.replace(" ", "_"))(value)
        fixture.execute()
        outputs.append({c.rstrip("?"): getattr(fixture, c.rstrip("?").replace(" ", "_"))() for c in header if c.endswith("?")})
    fixture.end_table()
    return outputs


@pytest.fixture(autouse=True)
def fake_ui(monkeypatch):
    FakeUi.instances, FakeUi.next_result = [], result()
    monkeypatch.setattr(VisualTest, "ui_class", FakeUi)


def test_a_matching_page_returns_status_and_difference():
    [out] = play(["url", "name", "status?", "difference?"], [["http://x/", "login page", "passed", ""]])
    assert out == {"status": "passed", "difference": "0.0"}
    ui = FakeUi.instances[0]
    assert ui.opened == ["http://x/"] and ui.checked == ["login page"] and ui.closed
    assert not [n for n in ui.notes if n[0] == "failure"]


def test_a_differing_page_is_a_failed_row_even_without_an_expected_cell():
    FakeUi.next_result = result("failed", 12.5, "12.5% of pixels differ (allowed 0.1%)")
    [out] = play(["url", "name", "difference?"], [["http://x/", "login page", ""]])
    assert out["difference"] == "12.5"
    failures = [n for n in FakeUi.instances[0].notes if n[0] == "failure"]
    assert failures and "12.5% of pixels differ" in failures[0][1][1]


def test_viewport_threshold_and_ignore_columns_are_applied():
    play(["url", "name", "viewport", "threshold", "ignore"], [["http://x/", "login page", "1600x1043", "0.5", "css=.clock, css=.ad"]])
    ui = FakeUi.instances[0]
    assert ui._page.viewport == {"width": 1600, "height": 1043}
    assert ui.threshold == "0.5" and ui.ignored == ["css=.clock", "css=.ad"]


def test_bad_input_is_reported_per_row():
    outputs = play(["url", "name", "viewport", "status?"],
                   [["http://x/", "login page", "wide", ""], ["http://x/", "", "", ""], ["http://x/", "login page", "", ""]])
    assert outputs[0]["status"].startswith("ERROR: Invalid viewport")
    assert outputs[1]["status"].startswith("ERROR: The name column is empty")
    assert outputs[2]["status"] == "passed"


def test_baseline_column_names_the_source(monkeypatch, tmp_path):
    monkeypatch.setattr(visual_compare, "REFERENCE_DIR", str(tmp_path))
    [out] = play(["url", "name", "baseline?"], [["http://x/", "login page", ""]])
    assert out["baseline"].startswith("stored baseline")
    (tmp_path / "login page.png").write_bytes(b"x")
    [out] = play(["url", "name", "baseline?"], [["http://x/", "login page", ""]])
    assert out["baseline"] == "reference image"
