"""The accessibility listing and the report files when there are many pages and many runs."""
import json
import os
import time

import pytest

from core import accessibility, accessibility_review as review


def violation(rule, impact="serious", nodes=2):
    return {"id": rule, "impact": impact, "help": f"{rule} help", "helpUrl": f"http://fix/{rule}",
            "wcagTags": ["wcag2a"], "nodes": [{"target": f"#n{i}", "html": "<x>", "summary": ""} for i in range(nodes)]}


def summary(url, status="FAIL", version="2.1", level="AA", violations=(), compliance=80.0):
    return {"url": url, "wcagVersion": version, "wcagLevel": level, "timestamp": "2026-10-12 10:00:00", "status": status,
            "minimumImpact": "minor", "maxViolations": 0, "passedChecks": 12, "violationCount": len(violations),
            "countedViolations": len(violations), "incompleteCount": 0, "affectedElements": sum(len(v["nodes"]) for v in violations),
            "compliancePercentage": compliance, "byImpact": {}, "violations": list(violations)}


def test_two_pages_with_the_same_start_do_not_share_a_report_file(tmp_path):
    long_prefix = "http://host/application/section/subsection/area/"
    first = accessibility.write_report(summary(long_prefix + "page-a"), long_prefix + "page-a", str(tmp_path))
    second = accessibility.write_report(summary(long_prefix + "page-b"), long_prefix + "page-b", str(tmp_path))
    assert first[1] != second[1] and len(os.listdir(tmp_path)) == 4          # two json + two html


def test_only_the_newest_runs_of_one_page_are_kept(tmp_path, monkeypatch):
    names = []
    for number in range(6):
        monkeypatch.setattr(accessibility.time, "strftime", lambda fmt, n=number: f"20261012-1000{n:02d}")
        names.append(accessibility.write_report(summary("http://x/home"), "http://x/home", str(tmp_path), keep=3)[1])
    kept = sorted(f for f in os.listdir(tmp_path) if f.endswith(".json"))
    assert len(kept) == 3 and kept == sorted(os.path.basename(n) for n in names[-3:])
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".html")]) == 3
    other = accessibility.write_report(summary("http://x/home"), "http://x/home", str(tmp_path), keep=3)   # same page, same second
    assert other[1].endswith(".json")


def test_another_standard_of_the_same_page_has_its_own_history(tmp_path, monkeypatch):
    monkeypatch.setattr(accessibility.time, "strftime", lambda fmt: "20261012-100000")
    accessibility.write_report(summary("http://x/home", version="2.1"), "http://x/home", str(tmp_path), keep=1)
    accessibility.write_report(summary("http://x/home", version="2.2"), "http://x/home", str(tmp_path), keep=1)
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".json")]) == 2


def write_runs(folder, specs):
    """specs: (file stem, summary, age in seconds); older runs get older modification times."""
    now = time.time()
    for stem, data, age in specs:
        base = os.path.join(folder, stem)
        json.dump(data, open(base + ".json", "w", encoding="utf-8"))
        open(base + ".html", "w", encoding="utf-8").write("<html></html>")
        os.utime(base + ".json", (now - age, now - age))


def test_the_list_shows_the_latest_result_per_page_and_hides_earlier_runs(tmp_path):
    write_runs(str(tmp_path), [
        ("home-old", summary("http://x/home", "FAIL", violations=[violation("label")]), 500),
        ("home-new", summary("http://x/home", "PASS", compliance=100.0), 10),
        ("cart", summary("http://x/cart", "FAIL", violations=[violation("label"), violation("color-contrast", "critical")]), 20),
    ])
    page = review.render_page(str(tmp_path))
    assert page.count("class='row'") == 2 and page.count("class='row old'") == 1       # two pages, one earlier run
    assert "2 run(s)" in page and "earlier run" in page
    assert "<span>Pages checked</span><b>2</b>" in page and "<span>Failing</span><b>1</b>" in page
    assert "<span>Runs kept</span><b>3</b>" in page


def test_most_frequent_issues_are_ranked_across_pages(tmp_path):
    write_runs(str(tmp_path), [
        ("a", summary("http://x/a", violations=[violation("label", "serious", 3), violation("color-contrast", "critical", 1)]), 1),
        ("b", summary("http://x/b", violations=[violation("label", "moderate", 2)]), 2),
        ("c", summary("http://x/c", "PASS"), 3),
    ])
    issues = review.top_issues(list(review.latest_per_page(review.list_runs(str(tmp_path)))[0].values()))
    assert [i["id"] for i in issues] == ["color-contrast", "label"]                  # critical first
    label = issues[1]
    assert len(label["pages"]) == 2 and label["elements"] == 5 and label["impact"] == "serious"   # worst impact seen


def test_a_long_list_is_paged_and_searchable_in_the_browser(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    specs = [(f"page{number:03d}", summary(f"http://x/page-{number}", "FAIL" if number % 4 == 0 else "PASS"), number)
             for number in range(90)]
    write_runs(str(tmp_path), specs)
    html = review.render_page(str(tmp_path), link_base="")
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:
            pytest.skip(f"Chromium is not available: {error}")
        page = browser.new_page(viewport={"width": 1300, "height": 900})
        page.set_content(html)
        shown = lambda: page.evaluate("[...document.querySelectorAll('#runs tr.row')].filter(r => r.style.display !== 'none').length")
        assert shown() == 25 and "page 1 of 4" in page.inner_text("#info")
        page.select_option("#status", "FAIL"); page.wait_for_timeout(100)
        assert shown() == 23                                              # 0, 4, ... 88
        page.fill("#q", "page-44"); page.wait_for_timeout(100)
        assert shown() == 1
        browser.close()
