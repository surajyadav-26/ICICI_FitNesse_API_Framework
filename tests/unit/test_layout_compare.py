"""The layout check: position, size and colours of chosen elements (no browser needed)."""
import json
import os

import pytest

from core import layout_compare as lc
from fixtures.visual.layout_test import LayoutTest
from fixtures.ui.decision_fixture import RowFailure


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    monkeypatch.setattr(lc, "BASELINE_DIR", str(tmp_path / "baselines"))
    monkeypatch.setattr(lc, "REFERENCE_DIR", str(tmp_path / "reference"))
    monkeypatch.setattr(lc, "RESULT_DIR", str(tmp_path / "results"))
    return tmp_path


def element(x=100, y=200, width=400, height=40, **styles):
    values = {"x": x, "y": y, "width": width, "height": height, "color": "rgb(0, 0, 0)",
              "backgroundColor": "rgb(255, 255, 255)", "borderColor": "rgb(203, 213, 225)", "borderWidth": "1px",
              "fontSize": "16px", "fontWeight": "400", "fontFamily": "Mulish", "textAlign": "left"}
    values.update(styles)
    return lc.normalize(values)


def test_colours_are_normalised():
    assert lc.normalize_color("rgb(255, 0, 128)") == "#ff0080"
    assert lc.normalize_color("rgba(0, 0, 0, 0)") == "transparent"
    assert lc.normalize_color("rgba(0, 0, 0, 0.5)") == "#000000"
    assert lc.normalize_color("red") == "red"


def test_identical_layouts_have_no_differences():
    assert lc.compare({"username": element()}, {"username": element()}) == []


def test_position_and_size_use_the_tolerance():
    base = {"username": element()}
    assert lc.compare(base, {"username": element(x=102, width=398)}, tolerance=2) == []
    differences = lc.compare(base, {"username": element(x=110, width=380)}, tolerance=2)
    assert [d["property"] for d in differences] == ["x", "width"]
    assert "width 400.0 -> 380.0" in differences[1]["message"] and "left position" in differences[0]["message"]


def test_colours_must_match_exactly():
    differences = lc.compare({"login": element()}, {"login": element(backgroundColor="rgb(245, 245, 245)")}, tolerance=50)
    assert [d["property"] for d in differences] == ["backgroundColor"]
    assert differences[0]["expected"] == "#ffffff" and differences[0]["actual"] == "#f5f5f5"


def test_a_missing_or_added_element_is_reported():
    differences = lc.compare({"a": element()}, {"b": element()})
    assert {d["property"] for d in differences} == {"presence"} and len(differences) == 2
    assert lc.compare({"a": element()}, {"a": {"missing": True, "reason": "x"}})[0]["actual"] == "not found"


def test_first_run_stores_a_baseline_then_compares(stores):
    first = lc.check({"username": element()}, "chromium-1600x1043", "home page")
    assert first["status"] == "new" and os.path.isfile(lc.baseline_path("chromium-1600x1043", "home page"))
    same = lc.check({"username": element()}, "chromium-1600x1043", "home page")
    assert same["status"] == "passed"
    moved = lc.check({"username": element(y=260)}, "chromium-1600x1043", "home page")
    assert moved["status"] == "failed" and moved["differences"][0]["property"] == "y"
    updated = lc.check({"username": element(y=260)}, "chromium-1600x1043", "home page", update=True)
    assert updated["status"] == "updated"
    assert lc.check({"username": element(y=260)}, "chromium-1600x1043", "home page")["status"] == "passed"


def test_a_reference_file_wins_over_the_stored_snapshot(stores):
    folder = stores / "reference"
    folder.mkdir()
    (folder / "home page.json").write_text(json.dumps({"username": element(width=500)}), encoding="utf-8")
    result = lc.check({"username": element(width=400)}, "firefox-1280x720", "home page")
    assert result["status"] == "failed" and "reference file" in result["baseline_source"]
    assert not os.path.exists(lc.baseline_path("firefox-1280x720", "home page"))


def test_report_lists_the_differences_and_escapes(stores):
    result = lc.check({"<b>x": element()}, "p", "home page")
    result = lc.check({"<b>x": element(height=90)}, "p", "home page", context={"url": "http://x/?a=<i>"})
    page = open(os.path.join(lc.result_dir("p", "home page"), "report.html"), encoding="utf-8").read()
    assert "MISMATCH" in page and "height" in page and "&lt;b&gt;x" in page and "<b>x" not in page
    assert "[Layout] &#x27;home page&#x27; differs from its baseline" in page
    assert lc.report_url("p", "home page") == "/files/testResults/layout/p/home%20page/report.html"


@pytest.mark.parametrize("bad", ["", "../x", "a/b"])
def test_unsafe_names_are_rejected(bad):
    with pytest.raises(ValueError):
        lc.clean_name(bad)


# ── the column table ─────────────────────────────────────────────────────────
class FakeLocator:
    def __init__(self, box):
        self.first, self._box = self, box

    def wait_for(self, **kwargs):
        if self._box is None:
            raise RuntimeError("not visible")

    def evaluate(self, script):
        return self._box


class FakePage:
    url = "http://x/home"

    def __init__(self):
        self.viewport = None

    def set_viewport_size(self, size):
        self.viewport = size


class FakeUi:
    instances = []
    layout = {}

    def __init__(self, name="x"):
        self._page, self._allure, self.notes, self.opened, self.failures = FakePage(), None, [], [], []
        self._test_name = name
        FakeUi.instances.append(self)

    def set_browser(self, value): pass
    def set_test_name(self, value): pass
    def start_browser(self, *args): return True
    def close_browser(self): pass
    def navigate_to(self, url):
        self.opened.append(url)
        return True
    def _visual_profile(self): return "chromium-1600x1043"
    def _locator(self, name): return FakeLocator(FakeUi.layout.get(name))
    def _log_simple_step(self, name, status="PASSED", body=""): self.notes.append((name, status))
    def _ok(self, text): return True
    def _capture_failure_state(self, *args, **kwargs): self.failures.append(args)


def play(header, rows):
    fixture = LayoutTest()
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


@pytest.fixture
def fake_ui(monkeypatch):
    FakeUi.instances = []
    FakeUi.layout = {"LoginPage.username": {"x": 10, "y": 20, "width": 300, "height": 40, "color": "rgb(0, 0, 0)",
                                            "backgroundColor": "rgb(255, 255, 255)", "borderColor": "rgb(0, 0, 0)",
                                            "borderWidth": "1px", "fontSize": "16px", "fontWeight": "400",
                                            "fontFamily": "Mulish", "textAlign": "left"}}
    monkeypatch.setattr(LayoutTest, "ui_class", FakeUi)


def test_column_table_creates_then_matches_then_flags_a_change(fake_ui):
    header = ["url", "name", "elements", "status?", "differences?", "checked?"]
    row = ["http://x/home", "home page", "LoginPage.username", "", "", ""]
    assert play(header, [row])[0]["status"] == "new"
    assert play(header, [row])[0] == {"status": "passed", "differences": "", "checked": "1"}
    FakeUi.layout["LoginPage.username"]["width"] = 250
    out = play(header, [row])[0]
    assert out["status"] == "failed" and "width 300.0 -> 250.0" in out["differences"]
    assert [n for n in FakeUi.instances[-1].failures]             # the row is a failed test case without an expected cell


def test_bad_input_is_reported_per_row(fake_ui):
    header = ["url", "name", "elements", "tolerance", "status?"]
    outputs = play(header, [["http://x/", "", "a", "", ""], ["http://x/", "n", "", "", ""], ["http://x/", "n", "a", "wide", ""]])
    assert outputs[0]["status"].startswith("ERROR: The name column is empty")
    assert outputs[1]["status"].startswith("ERROR: The elements column is empty")
    assert outputs[2]["status"].startswith("ERROR: Invalid tolerance")
