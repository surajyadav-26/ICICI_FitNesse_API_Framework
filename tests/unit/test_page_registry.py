"""Unit tests for the page objects (pages/*.py), the registry that reads them, and locator lookup in UI steps."""
import textwrap

import pytest

from pages import registry as page_registry
from pages.base_page import BasePage, normalise
from pages.login_page import LoginPage


@pytest.fixture
def pages_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(page_registry, "PAGES_DIR", str(tmp_path))
    monkeypatch.setattr(page_registry, "_cache", {})
    return tmp_path


def write_page(folder, file_name, body):
    (folder / file_name).write_text(textwrap.dedent(body), encoding="utf-8")


DASHBOARD = """
    from pages.base_page import BasePage

    class DashboardPage(BasePage):
        WELCOME_BANNER = "css=#welcome"
        ACCOUNT_LIST = "role=list:Accounts"
        helper_note = "not a locator"
"""


# ── page objects ──────────────────────────────────────────────────────────────
def test_locator_names_come_from_upper_case_attributes():
    class Demo(BasePage):
        SIGN_IN_BUTTON = "css=#in"
        NAME = "ignored-as-locator"
        lower_case = "css=#no"

    assert Demo.locators() == {"sign in button": "css=#in"}
    assert Demo.page_name() == "ignored-as-locator"


def test_locators_are_inherited_and_can_be_overridden():
    class Parent(BasePage):
        A_FIELD = "css=#a"
        B_FIELD = "css=#b"

    class Child(Parent):
        B_FIELD = "css=#b2"
        C_FIELD = "css=#c"

    assert Child.locators() == {"a field": "css=#a", "b field": "css=#b2", "c field": "css=#c"}


def test_login_page_defines_every_locator_the_steps_and_tests_use():
    locators = LoginPage.locators()
    assert locators["username"] == "role=textbox:Username"
    assert locators["password"] == "role=textbox:Password"
    assert locators["login button"] == "role=button:Log In"
    assert locators["framework username"] == "role=textbox:Username"
    assert locators["framework password"] == "role=textbox:Password"
    assert locators["framework login button"] == "role=button:Log In"
    assert locators["login error message"] == "id=icici-login-error"
    assert locators["profile menu"] == "id=icici-user-chip"
    assert locators["sign out button"] == "role=button:🚪 Sign Out"


def test_login_page_actions_use_the_ui_steps():
    calls = []

    class Ui:
        def enter_text_with_value(self, locator, value):
            calls.append(("fill", locator, value))
            return True

        def click_element(self, locator):
            calls.append(("click", locator))
            return True

        def navigate_to(self, url):
            calls.append(("open", url))
            return True

    page = LoginPage(Ui())
    page.open()
    page.login("admin", "pw")
    assert calls == [("open", "${UI_BASE_URL}"), ("fill", "LoginPage.username", "admin"),
                     ("fill", "LoginPage.password", "pw"), ("click", "LoginPage.login button")]


def test_a_failed_step_stops_the_page_action():
    class Ui:
        def enter_text_with_value(self, locator, value):
            return False

    from pages.base_page import PageActionFailed
    with pytest.raises(PageActionFailed, match="LoginPage"):
        LoginPage(Ui()).login("a", "b")


def test_normalise_ignores_case_spacing_and_separators():
    assert normalise("Login_Button") == normalise("login button") == normalise(" LOGIN-button ")


# ── registry ──────────────────────────────────────────────────────────────────
def test_registry_lists_every_page_object_in_the_folder(pages_dir):
    write_page(pages_dir, "dashboard_page.py", DASHBOARD)
    write_page(pages_dir, "other_page.py", DASHBOARD.replace("DashboardPage", "OtherPage").replace("WELCOME_BANNER", "TITLE"))
    pages = page_registry.list_pages()
    assert pages["DashboardPage"] == {"welcome banner": "css=#welcome", "account list": "role=list:Accounts"}
    assert pages["OtherPage"]["title"] == "css=#welcome"


def test_registry_lookup_ignores_case_and_separators(pages_dir):
    write_page(pages_dir, "dashboard_page.py", DASHBOARD)
    assert page_registry.find_selector("dashboardpage", "Welcome_Banner") == "css=#welcome"
    assert page_registry.find_selector("DashboardPage", "welcome-banner") == "css=#welcome"
    assert page_registry.find_selector("DashboardPage", "missing") is None
    assert page_registry.find_selector("NopePage", "welcome banner") is None
    assert page_registry.page_exists("DASHBOARDPAGE") and not page_registry.page_exists("Nope")
    assert page_registry.get_locators("Nope") == {}


def test_registry_picks_up_edited_files(pages_dir):
    write_page(pages_dir, "dashboard_page.py", DASHBOARD)
    assert "welcome banner" in page_registry.list_pages()["DashboardPage"]
    path = pages_dir / "dashboard_page.py"
    write_page(pages_dir, "dashboard_page.py", DASHBOARD.replace("WELCOME_BANNER", "HEADLINE"))
    import os
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert "headline" in page_registry.list_pages()["DashboardPage"]


def test_a_broken_page_file_does_not_hide_the_others(pages_dir):
    write_page(pages_dir, "broken_page.py", "this is not python (")
    write_page(pages_dir, "dashboard_page.py", DASHBOARD)
    write_page(pages_dir, "_private.py", DASHBOARD.replace("DashboardPage", "PrivatePage"))
    assert list(page_registry.list_pages()) == ["DashboardPage"]


def test_real_pages_folder_is_discovered():
    pages = page_registry.list_pages()
    assert "LoginPage" in pages and pages["LoginPage"]["username"] == "role=textbox:Username"


# ── lookup inside UI steps ────────────────────────────────────────────────────
def test_ui_fixture_resolves_locators_from_pages(pages_dir):
    from fixtures.ui.ui_fixture import UiFixture

    write_page(pages_dir, "login_page.py", """
        from pages.base_page import BasePage

        class LoginPage(BasePage):
            USERNAME = "css=#login-user"
            LOGIN_BUTTON = "css=#login-submit"
    """)
    write_page(pages_dir, "dashboard_page.py", DASHBOARD.replace("WELCOME_BANNER", "USERNAME").replace("css=#welcome", "css=#dash-user"))
    fixture = UiFixture("pages-test")
    assert fixture._page_selector("username") == "css=#login-user"            # LoginPage is the default
    assert fixture._page_selector("Login_Button") == "css=#login-submit"
    assert fixture._page_selector("DashboardPage.username") == "css=#dash-user"  # explicit Page.name
    assert fixture._page_selector("#raw-css") == "#raw-css"                     # unknown names pass through
    assert fixture._page_selector("div.item") == "div.item"
    assert fixture.use_page("DashboardPage") is True
    assert fixture._page_selector("username") == "css=#dash-user"              # the active page wins
    assert "not found" in fixture.use_page("NopePage")
