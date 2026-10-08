from pathlib import Path

from core.pages import page_registry
from fixtures.ui_fixture import UiFixture


class FakeLocator:
    def __init__(self, text=""):
        self.text = text
        self.filled = None
        self.clicked = False

    def wait_for(self, **kwargs):
        return None

    def fill(self, value):
        self.filled = value

    def click(self):
        self.clicked = True

    def inner_text(self, **kwargs):
        return self.text


class FakePage:
    def __init__(self):
        self.url = "http://localhost:8080/"
        self.locators = {
            ("role", "textbox", "Username"): FakeLocator(),
            ("role", "textbox", "Password"): FakeLocator(),
            ("role", "button", "Log In"): FakeLocator(),
            ("role", "button", "🚪 Sign Out"): FakeLocator(),
            ("css", "#icici-login-error"): FakeLocator("Invalid username or password."),
            ("css", "#icici-user-chip"): FakeLocator(),
        }

    def get_by_role(self, role, name):
        return self.locators[("role", role, name)]

    def locator(self, selector):
        return self.locators[("css", selector)]

    def wait_for_url(self, url, **kwargs):
        self.url = url


def test_ui_fixture_can_initialize():
    fixture = UiFixture()

    assert fixture._default_browser == "chromium"
    assert fixture._page is None
    assert fixture._browser is None


def test_requirements_include_playwright():
    requirements_text = Path("requirements.txt").read_text(encoding="utf-8")

    assert "playwright" in requirements_text.lower()


def test_login_page_has_framework_login_locators():
    locators = page_registry.get_locators("LoginPage")

    assert locators["framework username"] == "role=textbox:Username"
    assert locators["framework password"] == "role=textbox:Password"
    assert locators["framework login button"] == "role=button:Log In"
    assert locators["login error message"] == "id=icici-login-error"
    assert locators["profile menu"] == "id=icici-user-chip"
    assert locators["sign out button"] == "role=button:🚪 Sign Out"


def test_login_steps_fill_click_verify_and_logout():
    fixture = UiFixture()
    fixture._page = FakePage()
    fixture._log_simple_step = lambda *args, **kwargs: None

    assert fixture.attempt_login_with_password("admin", "admin123") is True
    assert fixture._page.locators[("role", "textbox", "Username")].filled == "admin"
    assert fixture._page.locators[("role", "textbox", "Password")].filled == "admin123"
    assert fixture._page.locators[("role", "button", "Log In")].clicked is True
    assert fixture.verify_login_error("Invalid username or password.") is True
    assert fixture.logout() is True
    assert fixture._page.locators[("css", "#icici-user-chip")].clicked is True
    assert fixture._page.locators[("role", "button", "🚪 Sign Out")].clicked is True

