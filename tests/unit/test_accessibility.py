"""Unit tests for the accessibility engine and fixtures; axe-core output is supplied by hand, no browser is started."""
import json
import os

import pytest

from core import accessibility as a
from core.flow import StepError
from fixtures.accessibility import checker
from fixtures.accessibility.accessibility_fixture import AccessibilityFixture
from fixtures.accessibility.accessibility_test import AccessibilityTest


def rule(rule_id, impact, nodes=1, help_text="Fix it"):
    return {"id": rule_id, "impact": impact, "description": f"{rule_id} description", "help": help_text,
            "helpUrl": f"https://dequeuniversity.com/rules/axe/4.10/{rule_id}", "tags": ["cat.forms", "wcag2a", "wcag412"],
            "nodes": [{"target": [f"#{rule_id}-{i}"], "html": f"<div id='{rule_id}-{i}'>", "failureSummary": "Fix any of:\n  needs a name"}
                      for i in range(nodes)]}


RAW = {"violations": [rule("label", "critical", 2), rule("color-contrast", "serious"), rule("region", "moderate"), rule("tabindex", "minor")],
       "passes": [{"id": f"p{i}"} for i in range(16)], "incomplete": [{"id": "i1"}, {"id": "i2"}]}


@pytest.fixture(autouse=True)
def report_folder(tmp_path, monkeypatch):
    # mirror the real layout so report links come out as /files/testResults/accessibility/...
    monkeypatch.setattr(a, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(a, "REPORT_DIR", str(tmp_path / "FitNesseRoot" / "files" / "testResults" / "accessibility"))
    return tmp_path


# ── engine ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("version,level,expected", [
    ("2.0", "AA", ["wcag2a", "wcag2aa"]),
    ("2.1", "A", ["wcag2a", "wcag21a"]),
    ("2.1", "aa", ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]),
    ("2.2", "AA", ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]),
])
def test_wcag_tags(version, level, expected):
    assert a.tags_for(version, level) == expected


@pytest.mark.parametrize("version,level", [("1.0", "AA"), ("2.1", "AAAA"), ("two", "AA")])
def test_unsupported_wcag_settings_are_rejected(version, level):
    with pytest.raises(ValueError):
        a.tags_for(version, level)


def test_summary_counts_and_compliance():
    summary = a.summarize(RAW, "http://x/", "2.1", "AA")
    assert summary["violationCount"] == 4 and summary["affectedElements"] == 5
    assert summary["passedChecks"] == 16 and summary["incompleteCount"] == 2
    assert summary["compliancePercentage"] == round(16 * 100 / 22, 2)          # 16 / (16 + 4 + 2)
    assert summary["byImpact"] == {"critical": 1, "serious": 1, "moderate": 1, "minor": 1}
    assert [v["id"] for v in summary["violations"]][0] == "label"                # worst first
    assert summary["violations"][0]["wcagTags"] == ["wcag2a", "wcag412"]
    assert summary["status"] == "FAIL"


def test_allowed_violations_and_minimum_impact_decide_the_verdict():
    assert a.summarize(RAW, "u", max_violations=4)["status"] == "PASS"
    assert a.summarize(RAW, "u", max_violations=3)["status"] == "FAIL"
    serious = a.summarize(RAW, "u", minimum_impact="serious", max_violations=2)
    assert serious["countedViolations"] == 2 and serious["violationCount"] == 4 and serious["status"] == "PASS"
    assert a.summarize(RAW, "u", minimum_impact="critical", max_violations=0)["status"] == "FAIL"
    assert a.summarize({"violations": [], "passes": [1], "incomplete": []}, "u")["status"] == "PASS"
    with pytest.raises(ValueError):
        a.summarize(RAW, "u", minimum_impact="catastrophic")


def test_empty_results_are_fully_compliant():
    summary = a.summarize({}, "u")
    assert summary["compliancePercentage"] == 100.0 and summary["status"] == "PASS"


def test_report_files_are_written_and_html_is_escaped(tmp_path):
    raw = {"violations": [rule("label", "critical")], "passes": [], "incomplete": []}
    raw["violations"][0]["nodes"][0]["html"] = "<script>alert('x')</script>"
    html_path, json_path = a.write_report(a.summarize(raw, "http://x/"), "home page")
    page = open(html_path, encoding="utf-8").read()
    assert "label" in page and "FAIL" in page and "<script>alert" not in page and "&lt;script&gt;" in page
    assert json.load(open(json_path, encoding="utf-8"))["violationCount"] == 1
    assert os.path.basename(html_path).startswith("home_page-")


def test_report_url_is_relative_to_the_fitnesse_root(monkeypatch):
    path = os.path.join(a.BASE_DIR, "FitNesseRoot", "files", "testResults", "accessibility", "x.html")
    assert a.report_url(path) == "/files/testResults/accessibility/x.html"


def test_run_axe_injects_the_script_and_asks_for_the_right_rules():
    calls = []

    class Page:
        def evaluate(self, script, options=None):
            calls.append((script, options))
            return {"violations": []}

    result = a.run_axe(Page(), "2.2", "AA")
    assert result == {"violations": []}
    assert "axe v4" in calls[0][0][:20] and calls[0][1] is None            # first call injects axe-core itself
    assert calls[1][1]["runOnly"]["values"] == a.tags_for("2.2", "AA")
    assert calls[1][1]["resultTypes"] == ["violations", "incomplete"]


# ── fakes for the fixtures ────────────────────────────────────────────────────
class FakePage:
    url = "http://localhost:8080/"

    def wait_for_load_state(self, *args, **kwargs):
        pass


class FakeUi:
    instances = []
    open_ok = True

    def __init__(self, name="x"):
        self._page = FakePage()
        self._allure = None
        self.notes, self.browser, self.closed, self.opened = [], None, False, []
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
        return FakeUi.open_ok

    def _log_simple_step(self, name, status="PASSED", body=""):
        self.notes.append((name, status, body))

    def _ok(self, text):
        self.notes.append((text, "PASSED", ""))
        return True

    def _capture_failure_state(self, *args, **kwargs):
        self.notes.append(("failure", args, ""))


@pytest.fixture
def fake_axe(monkeypatch):
    FakeUi.instances, FakeUi.open_ok = [], True
    state = {"raw": RAW}
    monkeypatch.setattr(a, "run_axe", lambda page, version, level: state["raw"])
    monkeypatch.setattr("fixtures.ui.ui_fixture.UiFixture", FakeUi)
    return state


# ── checker ───────────────────────────────────────────────────────────────────
def test_check_records_the_result_in_the_simple_report(fake_axe):
    ui = FakeUi()
    summary, html_path = checker.run_check(ui, "http://localhost:8080/", "2.1", "AA", "minor", 0, "home")
    assert summary["status"] == "FAIL" and os.path.isfile(html_path)
    name, status, body = ui.notes[-1]
    assert "FAIL" in name and "4 violation(s) counted of 4" in name and status == "FAILED"
    assert body.startswith("Report: http://localhost:8080/files/testResults/accessibility/")


def test_check_adds_a_step_per_violation_and_attachments_to_allure(fake_axe):
    from core import allure_helper
    ui = FakeUi()
    ui._allure = allure_helper.AllureHelper("Home", "Suite")
    checker.run_check(ui, "http://x/", "2.1", "AA", "serious", 0, "home")
    steps = ui._allure.steps
    assert steps[0]["status"] == "failed" and {a_["name"][:25] for a_ in steps[0]["attachments"]} == {"Accessibility report - ho", "Accessibility data - home"}
    names = [s["name"] for s in steps[1:]]
    assert names[0].startswith("[critical] label") and any("not counted" in n for n in names)
    assert [s["status"] for s in steps[1:]] == ["failed", "failed", "passed", "passed"]
    assert ui._allure.status == "failed"


def test_violations_inside_the_allowed_limit_are_not_failed_steps(fake_axe):
    from core import allure_helper
    ui = FakeUi()
    ui._allure = allure_helper.AllureHelper("Home", "Suite")
    checker.run_check(ui, "http://x/", "2.1", "AA", "minor", 4, "home")
    assert ui._allure.status == "passed"
    assert {s["status"] for s in ui._allure.steps} == {"passed"}
    assert all("within the allowed limit" in s["name"] for s in ui._allure.steps[1:])


def test_check_errors_are_clear(fake_axe):
    with pytest.raises(checker.AccessibilityError, match="No url"):
        checker.run_check(FakeUi(), "  ", "2.1", "AA", "minor", 0, "x")
    FakeUi.open_ok = False
    with pytest.raises(checker.AccessibilityError, match="Could not open"):
        checker.run_check(FakeUi(), "http://x/", "2.1", "AA", "minor", 0, "x")
    FakeUi.open_ok = True
    with pytest.raises(ValueError):
        checker.run_check(FakeUi(), "http://x/", "9.9", "AA", "minor", 0, "x")


# ── script table fixture ──────────────────────────────────────────────────────
def test_script_fixture_passes_within_the_allowed_violations(fake_axe):
    fixture = AccessibilityFixture()
    assert fixture.status() == "NOT RUN" and fixture.compliance() == "n/a" and fixture.report() == "No report"
    fixture.set_url('<a href="http://localhost:8080/">http://localhost:8080/</a>home')
    fixture.set_wcag_version("2.1")
    fixture.set_wcag_level("aa")
    fixture.set_max_violations("4")
    fixture.set_browser("firefox")
    assert fixture.run_accessibility_check() is True
    ui = FakeUi.instances[-1]
    assert ui.opened == ["http://localhost:8080/home"] and ui.browser == "firefox" and ui.closed
    assert (fixture.status(), fixture.violations(), fixture.all_violations(), fixture.passed_checks(), fixture.needs_review()) \
        == ("PASS", "4", "4", "16", "2")
    assert fixture.compliance() == "72.73%"
    assert 'href="/files/testResults/accessibility/' in fixture.report()
    assert "[critical] label" in fixture.details()


def test_script_fixture_fails_when_there_are_too_many_violations(fake_axe):
    fixture = AccessibilityFixture()
    fixture.set_url("http://x/")
    fixture.set_minimum_impact("serious")
    assert fixture.run_accessibility_check() is False
    assert fixture.status() == "FAIL" and fixture.violations() == "2" and fixture.all_violations() == "4"


def test_script_fixture_reports_a_check_that_could_not_run(fake_axe):
    fixture = AccessibilityFixture()
    result = fixture.run_accessibility_check()
    assert isinstance(result, StepError) and "No url" in result
    fixture.set_url("http://x/")
    fixture.set_wcag_version("9.9")
    assert isinstance(fixture.run_accessibility_check(), StepError)
    assert FakeUi.instances[-1].closed and fixture.status() == "NOT RUN"


# ── column table fixture ──────────────────────────────────────────────────────
def play(fixture, header, rows):
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
def column_fixture(fake_axe, monkeypatch):
    monkeypatch.setattr(AccessibilityTest, "ui_class", FakeUi)
    return AccessibilityTest()


def test_column_fixture_returns_the_results_per_row(column_fixture):
    outputs = play(column_fixture, ["url", "wcag version", "max violations", "violations?", "all violations?", "passed checks?", "compliance?", "status?"],
                   [["http://x/", "2.1", "0", "", "", "", "", "FAIL"], ["http://y/", "2.2", "4", "", "", "", "", "PASS"]])
    assert outputs[0]["violations"] == "4" and outputs[0]["status"] == "FAIL" and outputs[0]["passed checks"] == "16"
    assert outputs[0]["compliance"] == "72.73%"
    assert outputs[1]["status"] == "PASS"
    assert [ui.opened for ui in FakeUi.instances] == [["http://x/"], ["http://y/"]]


def test_column_fixture_marks_a_failing_page_even_without_an_expected_cell(column_fixture):
    play(column_fixture, ["url", "violations?"], [["http://x/", ""]])
    failures = [n for n in FakeUi.instances[0].notes if n[0] == "failure"]
    assert failures and "4 counted violation(s), 0 allowed" in failures[0][1][1]


def test_column_fixture_passing_page_has_no_failure(column_fixture):
    play(column_fixture, ["url", "max violations", "status?"], [["http://x/", "9", "PASS"]])
    assert not [n for n in FakeUi.instances[0].notes if n[0] == "failure"]


def test_column_fixture_reports_bad_input_per_row(column_fixture):
    outputs = play(column_fixture, ["url", "wcag version", "status?"], [["http://x/", "7.7", ""], ["", "2.1", ""], ["http://x/", "2.1", ""]])
    assert outputs[0]["status"].startswith("ERROR: Unsupported WCAG version")
    assert outputs[1]["status"] == "ERROR: No url was given"
    assert outputs[2]["status"] == "FAIL"


def test_the_report_has_a_defect_description_to_copy():
    from core import accessibility as a
    results = {"violations": [{"id": "image-alt", "impact": "critical", "help": "Images must have alternative text", "helpUrl": "http://fix",
                               "tags": ["wcag2a", "wcag111"], "nodes": [{"target": ["img"], "html": "<img src='x.png'>", "failureSummary": "a\nb"}]}],
               "passes": [1], "incomplete": []}
    summary = a.summarize(results, "http://app/login")
    text = a.defect_text(summary)
    assert text.startswith("[Accessibility] http://app/login has 1 WCAG 2.1 Level AA violation(s)")
    assert "[critical] Images must have alternative text (image-alt; wcag2a, wcag111)" in text and "element: img" in text and "http://fix" in text
    assert "id='defect'" in a.render_html(summary) and "Copy description" in a.render_html(summary)
    assert "id='defect'" not in a.render_html(a.summarize({"violations": [], "passes": [1], "incomplete": []}, "http://app"))
