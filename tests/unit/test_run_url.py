"""A run address (...?test, ...?suite) must not run again on refresh, and must not run behind the login form."""
import os

import pytest

HEADER = os.path.join(os.path.dirname(__file__), "..", "..", "FitNesseRoot", "PageHeader", "content.txt")
TEXT = open(HEADER, encoding="utf-8").read()


def early_script() -> str:
    start = TEXT.index("window.__iciRealPath = window.__iciRealPath || location.pathname;")
    end = TEXT.index("window.iciPrettyUrl = function")
    return TEXT[start:end]


PAGE = "<html><body><p id='marker'>page</p><script>(function(){%s})();</script></body></html>" % early_script()


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


def open_page(browser, url, signed_in):
    context = browser.new_context()
    if signed_in:
        context.add_init_script("sessionStorage.setItem('ici_session', JSON.stringify({user:'qa', role:'editor', display:'QA'}))")
    page = context.new_page()
    requested = []
    page.route("http://wiki.test/**", lambda route: (requested.append(route.request.url),
                                                     route.fulfill(status=200, content_type="text/html", body=PAGE)))
    page.goto(url)
    page.wait_for_timeout(300)
    return context, page, requested


@pytest.mark.parametrize("query, kind", [("?test", "test"), ("?suite", "suite"), ("?suite&format=text", "suite")])
def test_signed_in_the_run_query_leaves_the_address_bar(browser, query, kind):
    context, page, requested = open_page(browser, f"http://wiki.test/FrontPage.Suite.Page{query}", True)
    try:
        assert page.evaluate("location.search") == ""                      # a refresh will not run it again
        assert page.evaluate("window.iciIsRunPage()") is True               # this load still knows it is a run page
        assert page.evaluate("window.__iciRunKind") == kind
        assert page.evaluate("location.pathname") == "/FrontPage.Suite.Page"
        assert len(requested) == 1
    finally:
        context.close()


def test_not_signed_in_a_run_address_opens_the_plain_page(browser):
    context, page, requested = open_page(browser, "http://wiki.test/FrontPage.Suite.Page?suite", False)
    try:
        assert page.evaluate("location.search") == ""
        assert page.evaluate("location.pathname") == "/FrontPage.Suite.Page"
        assert page.evaluate("window.iciIsRunPage()") is False              # the second load is the plain page
        assert page.inner_text("#marker") == "page"
    finally:
        context.close()


def test_an_ordinary_address_is_left_alone(browser):
    context, page, requested = open_page(browser, "http://wiki.test/FrontPage.Suite.Page?edit", True)
    try:
        assert page.evaluate("location.search") == "?edit"
        assert page.evaluate("window.iciIsRunPage()") is False
        assert len(requested) == 1
    finally:
        context.close()


def test_a_query_that_only_contains_the_word_does_not_count(browser):
    context, page, requested = open_page(browser, "http://wiki.test/FrontPage.Suite.Page?responder=testHistory", True)
    try:
        assert page.evaluate("location.search") == "?responder=testHistory"
        assert page.evaluate("window.iciIsRunPage()") is False
    finally:
        context.close()
