"""The Visual Review page with many screens: nothing heavy is loaded up front, and the list can be searched and paged."""
import base64

import pytest

from core import visual_compare, visual_review

PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def items(failed=0, passed=0, new=0):
    found = []
    for number in range(failed):
        found.append({"name": f"broken {number}", "profile": "chromium-1600x1043", "status": "failed", "mismatch_pct": 3.2,
                      "timestamp": "2026-10-12 10:00:00", "message": "3.2% of pixels differ"})
    for number in range(new):
        found.append({"name": f"fresh {number}", "profile": "chromium-1600x1043", "status": "new", "mismatch_pct": 0,
                      "timestamp": "2026-10-12 10:00:00", "message": "Baseline created from this run"})
    for number in range(passed):
        found.append({"name": f"screen {number}", "profile": "firefox-1366x768", "status": "passed", "mismatch_pct": 0,
                      "timestamp": "2026-10-12 10:00:00", "message": "Matches baseline"})
    return found


def test_no_image_is_requested_by_the_html_itself(monkeypatch):
    monkeypatch.setattr(visual_compare, "list_results", lambda: items(failed=8, passed=300))
    page = visual_review.render_page()
    assert "<img src=" not in page.split("<main>")[1]                    # every screenshot waits for data-src
    assert page.count("data-src=") >= 308 * 3
    assert 'class="card failed"' in page and "<details" in page
    assert "id=\"q\"" in page and "id=\"size\"" in page and "id=\"next\"" in page


def test_few_mismatches_are_opened_many_are_not(monkeypatch):
    monkeypatch.setattr(visual_compare, "list_results", lambda: items(failed=3, passed=10))
    few = visual_review.render_page().split("<main>")[1]
    assert few.count("data-status=\"failed\" data-name") == 3 and few.count("\" open>") == 3
    monkeypatch.setattr(visual_compare, "list_results", lambda: items(failed=visual_review.OPEN_WHEN_AT_MOST + 1))
    many = visual_review.render_page().split("<main>")[1]
    assert "\" open>" not in many


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as error:
            pytest.skip(f"Chromium is not available: {error}")
        yield instance
        instance.close()


def open_review(browser, monkeypatch, found):
    monkeypatch.setattr(visual_compare, "list_results", lambda: found)
    html = visual_review.render_page()
    page = browser.new_page(viewport={"width": 1300, "height": 900})
    images = []

    def route(route):
        url = route.request.url
        if "/visual-image/" in url:
            images.append(url)
            route.fulfill(status=200, content_type="image/png", body=PIXEL)
        elif url.endswith("/visual"):
            route.fulfill(status=200, content_type="text/html", body=html)
        else:
            route.fulfill(status=204, body="")
    page.route("http://review.test/**", route)
    page.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(status=204, body=""))
    page.goto("http://review.test/visual")
    page.wait_for_timeout(400)
    return page, images


def test_images_are_loaded_only_when_a_row_is_opened(browser, monkeypatch):
    page, images = open_review(browser, monkeypatch, items(failed=8, passed=120))
    try:
        assert images == []                                                # 128 screens, nothing opened, nothing requested
        page.locator(".card >> nth=0").locator("summary").click()
        page.wait_for_timeout(300)
        assert len(images) == 3 and all("broken%200" in url for url in images)   # baseline, actual, diff of that one screen
    finally:
        page.close()


def test_paging_and_search(browser, monkeypatch):
    page, _ = open_review(browser, monkeypatch, items(failed=2, passed=70))
    try:
        visible = lambda: page.evaluate("[...document.querySelectorAll('.card')].filter(c => c.style.display !== 'none').length")
        assert visible() == 25
        assert "page 1 of 3" in page.inner_text("#info")
        page.click("#next"); assert "page 2 of 3" in page.inner_text("#info") and visible() == 25
        page.click("#next"); assert visible() == 22                         # 72 screens: 25 + 25 + 22
        page.fill("#q", "broken 1"); page.wait_for_timeout(100)
        assert visible() == 1 and "1 screen(s)" in page.inner_text("#info")
        page.fill("#q", ""); page.click("[data-filter=failed]"); page.wait_for_timeout(100)
        assert visible() == 2
    finally:
        page.close()
