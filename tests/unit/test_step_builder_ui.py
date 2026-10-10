"""
Step Builder regression tests: the drawer (HTML, CSS and script) is cut out of FitNesseRoot/PageHeader/content.txt and run in a
plain browser page, with the user store server's /fixtures and /pages answers supplied from the real catalog and registry.
"""
import json
import os
import re

import pytest

from core import fixture_catalog
from pages import registry

HEADER = os.path.join(os.path.dirname(__file__), "..", "..", "FitNesseRoot", "PageHeader", "content.txt")
TEXT = open(HEADER, encoding="utf-8").read()


def between(start: str, end: str) -> str:
    a = TEXT.index(start)
    return TEXT[a:TEXT.index(end, a)]


def harness_html() -> str:
    drawer = between('<div id="ici-dict-drawer"', "<!-- ═══").replace('class="ici-drawer"', 'class="ici-drawer open"', 1)
    css = between("/* ── Step Builder Drawer", "/* ── Login Overlay")
    script = between("    /* ── Step Builder catalog", "    window.iciLiveDebug = function()")
    return (f"<html><head><style>.ici-env-input{{width:100%;box-sizing:border-box}}{css}</style></head><body>"
            f"<script>window.iciToggleDictDrawer=function(){{document.getElementById('ici-dict-drawer').classList.toggle('open')}};</script>"
            f"{drawer}<script>{script}</script></body></html>")


def test_page_contains_exactly_one_wiki_end_marker():
    """A second dash-bang sequence anywhere in PageHeader would end the literal block early and break the whole UI."""
    assert TEXT.count("-" + "!") == 1
    assert TEXT.rstrip().endswith("-" + "!")


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


@pytest.fixture
def builder(browser):
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    answers = {"fixtures": json.dumps(fixture_catalog.list_fixtures()), "pages": json.dumps({"pages": registry.list_pages()})}
    for name in answers:
        page.route(f"**/127.0.0.1:8090/{name}", lambda route, body=None, key=name: route.fulfill(
            status=200, body=answers[key], headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}))
    page.set_content(harness_html())
    page.evaluate("iciInitBuilder(); iciLoadPages();")
    page.wait_for_timeout(300)
    yield page
    assert errors == []
    page.close()


def open_column_mode(page, fixture):
    page.click("#ici-tt-column")
    page.wait_for_selector("#ici-col-fixture option", state="attached")
    page.select_option("#ici-col-fixture", label=fixture)


def row_inputs(page, row=1):
    return page.query_selector_all(f"#ici-col-grid tr:nth-child({row + 1}) .ici-env-input")


def fill_by_header(page, row, values):
    headers = page.eval_on_selector_all("#ici-col-grid tr:first-child th", "els => els.map(e => e.textContent.trim().toLowerCase())")
    for cell, header in zip(row_inputs(page, row), headers):
        if header in values:
            if cell.evaluate("e => e.tagName") == "SELECT":
                cell.select_option(values[header])
            else:
                cell.fill(values[header])


def tick(page, header):
    page.check(f"#ici-col-list .ici-col-item:has(.h:text-is('{header}')) input")


# ── script mode keeps working exactly as before ───────────────────────────────
def test_script_mode_output_is_unchanged(builder):
    assert builder.is_visible("#ici-builder-script-mode") and not builder.is_visible("#ici-builder-column-mode")
    builder.select_option("#ici-builder-category", "Browser")
    builder.select_option("#ici-builder-action", "Navigate to URL")
    assert builder.input_value("#ici-builder-param-url") == "${UI_BASE_URL}"          # defaults to the selected environment
    builder.click("#ici-builder-add")
    builder.select_option("#ici-builder-category", "Mouse")
    builder.select_option("#ici-builder-action", "Click Element")
    builder.select_option("#ici-builder-param-locator-sel", "login button")
    builder.click("#ici-builder-add")
    assert builder.input_value("#ici-builder-script") == "\n".join([
        "| script | fixtures.UiFixture |", "| navigate to | ${UI_BASE_URL} |", "| click element | login button |"])


# ── column mode ───────────────────────────────────────────────────────────────
def test_fixtures_are_grouped_and_ordered(builder):
    builder.click("#ici-tt-column")
    builder.wait_for_selector("#ici-col-fixture option", state="attached")
    groups = builder.eval_on_selector_all("#ici-col-fixture optgroup", "g => g.map(x => x.label)")
    assert groups == ["UI scenarios - Login", "Accessibility", "Visual", "API"]
    tables = builder.eval_on_selector_all("#ici-col-fixture option", "o => o.map(x => x.textContent)")
    assert tables[:2] == ["login test", "accessibility test"] and "get request fixture" in tables and "post request fixture" in tables


def test_columns_show_required_optional_and_result(builder):
    open_column_mode(builder, "login test")
    items = builder.eval_on_selector_all("#ici-col-list .ici-col-item", """els => els.map(i => ({
        header: i.querySelector('.h').textContent, tag: i.querySelector('.tag').textContent,
        checked: i.querySelector('input').checked, locked: i.querySelector('input').disabled}))""")
    assert items == [
        {"header": "username", "tag": "required", "checked": True, "locked": True},
        {"header": "password", "tag": "required", "checked": True, "locked": True},
        {"header": "browser", "tag": "optional", "checked": False, "locked": False},
        {"header": "login result?", "tag": "result", "checked": True, "locked": False},
    ]


def test_required_columns_must_be_filled_before_the_table_can_be_added(builder):
    open_column_mode(builder, "login test")
    assert builder.is_disabled("#ici-col-add") and "fill in username" in builder.inner_text("#ici-col-problem")
    fill_by_header(builder, 1, {"username": "admin"})
    assert builder.is_disabled("#ici-col-add") and "fill in password" in builder.inner_text("#ici-col-problem")
    fill_by_header(builder, 1, {"password": "admin123"})
    assert not builder.is_disabled("#ici-col-add") and builder.inner_text("#ici-col-problem") == ""
    builder.click("text=+ Add row")
    assert builder.is_disabled("#ici-col-add") and "Row 2" in builder.inner_text("#ici-col-problem")


def test_generated_login_table(builder):
    open_column_mode(builder, "login test")
    fill_by_header(builder, 1, {"username": "admin", "password": "admin123", "login result?": "Success"})
    builder.click("text=+ Add row")
    fill_by_header(builder, 2, {"username": "admin", "password": "wrong", "login result?": "Invalid username or password."})
    assert builder.inner_text("#ici-col-preview") == "\n".join([
        "|login test|", "|username|password|login result?|",
        "|admin|admin123|Success|", "|admin|wrong|Invalid username or password.|"])
    builder.click("#ici-col-add")
    assert builder.input_value("#ici-builder-script").startswith("|login test|")
    assert len(row_inputs(builder, 1)) == 3 and row_inputs(builder, 1)[0].input_value() == ""      # a fresh row for the next table


def test_optional_columns_can_be_added_and_offer_their_allowed_values(builder):
    open_column_mode(builder, "login test")
    tick(builder, "browser")
    headers = builder.eval_on_selector_all("#ici-col-grid tr:first-child th", "e => e.map(x => x.textContent.trim())")
    assert [h.lower() for h in headers[:4]] == ["username", "password", "browser", "login result?"]
    browser_cell = row_inputs(builder, 1)[2]
    assert browser_cell.evaluate("e => e.tagName") == "SELECT"
    assert browser_cell.evaluate("e => [...e.options].map(o => o.value)") == ["", "chromium", "firefox", "webkit"]
    fill_by_header(builder, 1, {"username": "admin", "password": "x", "browser": "firefox"})
    assert "|admin|x|firefox|" in builder.inner_text("#ici-col-preview")
    builder.uncheck("#ici-col-list .ici-col-item:has(.h:text-is('browser')) input")
    assert "firefox" not in builder.inner_text("#ici-col-preview")


def test_password_cells_are_hidden_while_typing(builder):
    open_column_mode(builder, "login test")
    types = [cell.get_attribute("type") for cell in row_inputs(builder, 1)]
    assert types[:2] == ["text", "password"]


def test_a_pipe_inside_a_value_is_wrapped_so_the_wiki_table_stays_intact(builder):
    open_column_mode(builder, "login test")
    fill_by_header(builder, 1, {"username": "a|b", "password": "p", "login result?": "Success"})
    line = [line for line in builder.inner_text("#ici-col-preview").splitlines() if "a|b" in line][0]
    assert line == "|" + "!" + "-a|b-" + "!" + "|p|Success|"
    assert "|!-" not in builder.inner_text("#ici-col-preview").splitlines()[0]          # the table name line is untouched


def test_the_wiki_end_marker_inside_a_value_is_refused(builder):
    open_column_mode(builder, "login test")
    fill_by_header(builder, 1, {"username": "x-" + "!", "password": "p"})
    assert builder.is_disabled("#ici-col-add") and "cannot contain" in builder.inner_text("#ici-col-problem")


def test_api_table_with_body_and_expected_values(builder):
    open_column_mode(builder, "post request fixture")
    tick(builder, "key")
    tick(builder, "body json")
    fill_by_header(builder, 1, {"url": "${API_BASE_URL}/users/add", "key": "firstName", "body json": '{"firstName":"Asha"}',
                                "status code?": "201", "json value?": "Asha"})
    assert builder.inner_text("#ici-col-preview") == "\n".join([
        "|post request fixture|", "|url|key|body json|status code?|json value?|",
        '|${API_BASE_URL}/users/add|firstName|{"firstName":"Asha"}|201|Asha|'])


def test_accessibility_table_uses_the_defaults_for_unticked_columns(builder):
    open_column_mode(builder, "accessibility test")
    fill_by_header(builder, 1, {"url": "${UI_BASE_URL}", "status?": "PASS"})
    assert builder.inner_text("#ici-col-preview").splitlines() == [
        "|accessibility test|", "|url|violations?|status?|", "|${UI_BASE_URL}||PASS|"]


# ── mixing both table types in one script ─────────────────────────────────────
def test_script_steps_and_column_tables_compile_in_order(builder):
    builder.select_option("#ici-builder-category", "Browser")
    builder.select_option("#ici-builder-action", "Refresh Page")
    builder.click("#ici-builder-add")
    open_column_mode(builder, "login test")
    fill_by_header(builder, 1, {"username": "admin", "password": "x"})
    builder.click("#ici-col-add")
    builder.click("#ici-tt-script")
    builder.select_option("#ici-builder-action", "Go Back")
    builder.click("#ici-builder-add")
    builder.select_option("#ici-builder-action", "Go Forward")
    builder.click("#ici-builder-add")
    text = builder.input_value("#ici-builder-script")
    assert text == "\n".join([
        "| script | fixtures.UiFixture |", "| refresh page |", "",
        "|login test|", "|username|password|login result?|", "|admin|x||", "",
        "| script | fixtures.UiFixture |", "| go back |", "| go forward |"])
    labels = builder.eval_on_selector_all("#ici-builder-steps .txt", "e => e.map(x => x.textContent)")
    assert labels[1] == "login test - 1 row(s): username, password, login result?" and builder.inner_text("#ici-builder-count") == "4"


def test_table_items_can_be_moved_and_removed_like_steps(builder):
    open_column_mode(builder, "login test")
    fill_by_header(builder, 1, {"username": "a", "password": "b"})
    builder.click("#ici-col-add")
    builder.click("#ici-tt-script")
    builder.select_option("#ici-builder-category", "Browser")
    builder.select_option("#ici-builder-action", "Go Back")
    builder.click("#ici-builder-add")
    builder.click("#ici-builder-steps .ici-builder-step:nth-child(2) .ctl[title='Move up']")
    assert builder.input_value("#ici-builder-script").splitlines()[:2] == ["| script | fixtures.UiFixture |", "| go back |"]
    assert "|login test|" in builder.input_value("#ici-builder-script")
    builder.click("#ici-builder-steps .ici-builder-step:nth-child(2) .ctl[title='Remove']")
    assert builder.input_value("#ici-builder-script") == "| script | fixtures.UiFixture |\n| go back |"
    builder.click("text=Clear all")
    assert builder.input_value("#ici-builder-script") == ""


# ── failure modes ─────────────────────────────────────────────────────────────
def test_unreachable_server_is_explained(browser):
    page = browser.new_page()
    page.route("**/127.0.0.1:8090/**", lambda route: route.abort())
    page.set_content(harness_html())
    page.evaluate("iciInitBuilder();")
    page.click("#ici-tt-column")
    page.wait_for_selector("#ici-col-notes:not(:empty)", state="attached")
    assert "not reachable" in page.inner_text("#ici-col-notes")
    assert page.eval_on_selector_all("#ici-col-fixture option", "o => o.map(x => x.textContent)") == ["(no fixtures found)"]
    assert page.is_disabled("#ici-col-add")
    page.close()


def test_fixtures_that_could_not_load_are_reported(browser):
    page = browser.new_page()
    payload = json.dumps({"fixtures": [], "problems": ["fixtures.api.broken: boom"]})
    page.route("**/127.0.0.1:8090/fixtures", lambda route: route.fulfill(status=200, body=payload, headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}))
    page.set_content(harness_html())
    page.evaluate("iciInitBuilder();")
    page.click("#ici-tt-column")
    page.wait_for_selector("#ici-col-notes:not(:empty)", state="attached")
    assert "fixtures.api.broken: boom" in page.inner_text("#ici-col-notes")
    page.close()
