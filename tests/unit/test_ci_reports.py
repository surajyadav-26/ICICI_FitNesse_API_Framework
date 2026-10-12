"""The CI build step: static indexes for the visual and accessibility reports, and the quality gate."""
import json

import pytest

from core import accessibility_review, ci_reports, visual_compare, visual_report


@pytest.fixture
def stores(tmp_path, monkeypatch):
    monkeypatch.setattr(visual_compare, "RESULT_DIR", str(tmp_path / "visual"))
    monkeypatch.setattr(visual_compare, "RESULTS_FILE", str(tmp_path / "visual" / "results.json"))
    monkeypatch.setattr(ci_reports.accessibility_review.accessibility, "REPORT_DIR", str(tmp_path / "accessibility"))
    monkeypatch.setattr(ci_reports, "build_allure", lambda: "skipped in the test")
    return tmp_path


def add_visual(name, status, pct=0.0):
    visual_compare.record_result(visual_compare.VisualResult(status, name, "chromium-1600x1043", mismatch_pct=pct,
                                                             message=f"{pct}% of pixels differ"))


def add_accessibility(folder, stem, status, url="http://x/"):
    folder.mkdir(exist_ok=True)
    (folder / f"{stem}.json").write_text(json.dumps({"url": url, "status": status, "wcagVersion": "2.1", "wcagLevel": "AA",
                                                     "countedViolations": 3, "violationCount": 3, "maxViolations": 0,
                                                     "compliancePercentage": 80, "affectedElements": 3}), encoding="utf-8")
    (folder / f"{stem}.html").write_text("<html></html>", encoding="utf-8")


def test_visual_index_links_every_comparison_relatively(stores):
    add_visual("login page", "failed", 5.3)
    add_visual("home page", "passed")
    path = visual_report.write_index()
    page = open(path, encoding="utf-8").read()
    assert path.endswith("index.html")
    assert "chromium-1600x1043/login%20page/report.html" in page and "chromium-1600x1043/home%20page/report.html" in page
    assert "MISMATCH" in page and "5.3%" in page


def test_accessibility_index_uses_links_relative_to_its_folder(stores):
    add_accessibility(stores / "accessibility", "home-20261010-101500", "FAIL")
    path = accessibility_review.write_index()
    page = open(path, encoding="utf-8").read()
    assert "href='home-20261010-101500.html'" in page and "/accessibility-report/" not in page


def test_gate_passes_when_everything_matches(stores):
    add_visual("login page", "passed")
    add_accessibility(stores / "accessibility", "ok", "PASS")
    assert ci_reports.main(["--gate"]) == 0


def test_gate_fails_on_a_visual_mismatch_or_an_accessibility_failure(stores, capsys):
    add_visual("login page", "failed", 7.5)
    assert ci_reports.main(["--gate"]) == 1
    assert "MISMATCH login page" in capsys.readouterr().out
    add_visual("login page", "passed")
    add_accessibility(stores / "accessibility", "bad", "FAIL", "http://x/home")
    assert ci_reports.main(["--gate"]) == 1
    assert "FAIL http://x/home" in capsys.readouterr().out


def test_without_the_gate_flag_a_failure_only_reports(stores):
    add_visual("login page", "failed", 7.5)
    assert ci_reports.main([]) == 0
