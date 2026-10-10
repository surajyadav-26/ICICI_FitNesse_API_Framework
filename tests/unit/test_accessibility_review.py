import json

import pytest

from core import accessibility_review


def write_run(folder, stem, status="PASS", url="http://x/", counted=0, total=0, compliance=100.0, mtime=None):
    summary = {"url": url, "wcagVersion": "2.1", "wcagLevel": "AA", "timestamp": "2026-10-10 10:00:00", "status": status,
               "countedViolations": counted, "violationCount": total, "affectedElements": total, "compliancePercentage": compliance}
    (folder / f"{stem}.json").write_text(json.dumps(summary), encoding="utf-8")
    (folder / f"{stem}.html").write_text("<html>report</html>", encoding="utf-8")


def test_empty_folder_shows_a_helpful_message(tmp_path):
    page = accessibility_review.render_page(str(tmp_path))
    assert "No accessibility checks yet" in page and "Accessibility Report" in page


def test_lists_runs_newest_first_with_links_and_totals(tmp_path):
    import os
    write_run(tmp_path, "old-1", "FAIL", "http://old/", 3, 4, 70.0)
    write_run(tmp_path, "new-2", "PASS", "http://new/", 0, 1, 90.0)
    os.utime(tmp_path / "old-1.json", (1, 1))
    runs = accessibility_review.list_runs(str(tmp_path))
    assert [run["file"] for run in runs] == ["new-2.html", "old-1.html"]
    page = accessibility_review.render_page(str(tmp_path))
    assert "/accessibility-report/new-2.html" in page and "http://old/" in page
    assert "<b>2</b>" in page and "80.0%" in page         # two runs, average compliance


def test_report_path_rejects_anything_but_a_plain_report_name(tmp_path):
    assert accessibility_review.report_path("home-20261010-101500.html", str(tmp_path)).endswith("home-20261010-101500.html")
    for bad in ("../secrets.html", "a/b.html", "report.txt", "", "..\\x.html"):
        with pytest.raises(ValueError):
            accessibility_review.report_path(bad, str(tmp_path))


def test_unreadable_json_is_skipped(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "broken.html").write_text("x", encoding="utf-8")
    assert accessibility_review.list_runs(str(tmp_path)) == []
