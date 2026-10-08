"""Unit tests for the page/locator registry and the use_page step."""
import json

import pytest

from core.pages import page_registry


@pytest.fixture
def pages_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(page_registry, "PAGES_DIR", str(tmp_path))
    return tmp_path


def test_save_and_list_locators(pages_dir):
    page_registry.save_locator("LoginPage", "username", "#user")
    page_registry.save_locator("LoginPage", "login button", "css=button.login")
    page_registry.save_locator("DashboardPage", "banner", "text=Welcome")
    pages = page_registry.list_pages()
    assert pages == {
        "LoginPage": {"username": "#user", "login button": "css=button.login"},
        "DashboardPage": {"banner": "text=Welcome"},
    }
    assert json.loads((pages_dir / "LoginPage.json").read_text(encoding="utf-8"))["page"] == "LoginPage"


def test_update_and_remove_locator(pages_dir):
    page_registry.save_locator("LoginPage", "username", "#a")
    page_registry.save_locator("LoginPage", "username", "#b")
    assert page_registry.get_locators("LoginPage") == {"username": "#b"}
    page_registry.remove_locator("LoginPage", "username")
    assert page_registry.get_locators("LoginPage") == {}
    assert page_registry.page_exists("LoginPage")


@pytest.mark.parametrize("page,locator,selector", [
    ("../evil", "x", "#a"), ("", "x", "#a"), ("Page", "", "#a"), ("Page", "x", "  "), ("a/b", "x", "#a"),
])
def test_invalid_input_is_rejected(pages_dir, page, locator, selector):
    with pytest.raises(ValueError):
        page_registry.save_locator(page, locator, selector)
    assert list(pages_dir.iterdir()) == []


def test_corrupt_page_file_is_ignored(pages_dir):
    (pages_dir / "Broken.json").write_text("{not json", encoding="utf-8")
    page_registry.save_locator("Good", "x", "#x")
    assert list(page_registry.list_pages()) == ["Good"]


def test_ui_fixture_resolves_locators_from_active_page(pages_dir):
    from fixtures.ui_fixture import UiFixture

    page_registry.save_locator("DashboardPage", "username", "css=#dash-user")
    fixture = UiFixture("pages-test")
    assert fixture._page_selector("username") == "username"            # no page selected: untouched
    page_registry.save_locator("LoginPage", "username", "css=#login-user")
    page_registry.save_locator("LoginPage", "password", "css=#login-password")
    page_registry.save_locator("LoginPage", "login button", "css=#login-submit")
    assert fixture._page_selector("username") == "css=#login-user"     # LoginPage is the default
    assert fixture._page_selector("password") == "css=#login-password"
    assert fixture._page_selector("login button") == "css=#login-submit"
    assert fixture.use_page("LoginPage") is True
    assert fixture._page_selector("username") == "css=#login-user"
    assert fixture._page_selector("DashboardPage.username") == "css=#dash-user"  # explicit Page.name
    assert fixture._page_selector("#raw-css") == "#raw-css"             # unknown names pass through
    assert fixture.use_page("DashboardPage") is True
    assert fixture._page_selector("username") == "css=#dash-user"
    assert "not found" in fixture.use_page("NopePage")
