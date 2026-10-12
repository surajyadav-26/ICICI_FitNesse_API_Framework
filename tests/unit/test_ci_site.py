"""The static site of one run (what GitHub Pages serves)."""
import os

from core import ci_reports


def make_results(root):
    for folder in ("allure-report", "visual", "accessibility"):
        (root / folder).mkdir(parents=True)
        (root / folder / "index.html").write_text(f"<html>{folder}</html>", encoding="utf-8")
    (root / "visual" / "chromium-1600x1043" / "login page").mkdir(parents=True)
    (root / "visual" / "chromium-1600x1043" / "login page" / "report.html").write_text("<html>cmp</html>", encoding="utf-8")


def test_site_collects_every_report_and_links_them(tmp_path):
    results = tmp_path / "testResults"
    make_results(results)
    simple = tmp_path / "report.html"
    simple.write_text("<html>simple</html>", encoding="utf-8")
    site = tmp_path / "site"
    found = ci_reports.build_site(str(site), str(results), str(simple),
                                  {"GITHUB_REPOSITORY": "acme/bank", "GITHUB_REF_NAME": "main", "GITHUB_RUN_NUMBER": "42",
                                   "GITHUB_SHA": "0123456789abcdef"})
    assert found == ["Allure report", "Visual regression", "Accessibility", "Simple report"]
    page = (site / "index.html").read_text(encoding="utf-8")
    for link in ("allure/index.html", "visual/index.html", "accessibility/index.html", "simple-report.html"):
        assert f"href='{link}'" in page and (site / link).is_file()
    assert (site / "visual" / "chromium-1600x1043" / "login page" / "report.html").is_file()
    assert "acme/bank" in page and "run #42" in page and "commit 01234567" in page
    assert (site / ".nojekyll").exists()


def test_a_missing_report_is_left_out_not_faked(tmp_path):
    results = tmp_path / "testResults"
    (results / "visual").mkdir(parents=True)
    (results / "visual" / "index.html").write_text("<html>v</html>", encoding="utf-8")
    site = tmp_path / "site"
    found = ci_reports.build_site(str(site), str(results), str(tmp_path / "nothing.html"), {})
    assert found == ["Visual regression"]
    page = (site / "index.html").read_text(encoding="utf-8")
    assert "visual/index.html" in page and "allure/index.html" not in page and "simple-report.html" not in page


def test_an_empty_run_still_gets_an_index(tmp_path):
    site = tmp_path / "site"
    assert ci_reports.build_site(str(site), str(tmp_path / "none"), str(tmp_path / "none.html"), {}) == []
    assert "No reports were produced" in (site / "index.html").read_text(encoding="utf-8")


def test_the_site_option_needs_a_folder(monkeypatch):
    monkeypatch.setattr(ci_reports, "build_allure", lambda: "skipped")
    monkeypatch.setattr(ci_reports.visual_compare, "list_results", lambda: [])
    monkeypatch.setattr(ci_reports.visual_report, "write_index", lambda results=None: "")
    monkeypatch.setattr(ci_reports.accessibility_review, "list_runs", lambda: [])
    monkeypatch.setattr(ci_reports.accessibility_review, "write_index", lambda: "")
    assert ci_reports.main(["--site"]) == 2
