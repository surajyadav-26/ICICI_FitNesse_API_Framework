"""The framework's own login screen (Nirikshan)."""
from core.flow import is_failure
from pages.base_page import BasePage

_RESULT_WAIT_MS = 6000


class LoginPage(BasePage):
    # Locators (wiki tables use them as `LoginPage.username`; short names such as `username` resolve here too)
    USERNAME = "role=textbox:Username"
    PASSWORD = "role=textbox:Password"
    LOGIN_BUTTON = "role=button:Log In"
    FRAMEWORK_USERNAME = USERNAME
    FRAMEWORK_PASSWORD = PASSWORD
    FRAMEWORK_LOGIN_BUTTON = LOGIN_BUTTON
    LOGIN_ERROR_MESSAGE = "id=icici-login-error"
    PROFILE_MENU = "id=icici-user-chip"
    SIGN_OUT_BUTTON = "role=button:🚪 Sign Out"
    LOGIN_OVERLAY = "css=#icici-login-overlay"

    # Actions
    def open(self, url: str = "${UI_BASE_URL}"):
        return self.do(self.ui.navigate_to, url)

    def login(self, username: str, password: str):
        """Types the credentials and presses Log In."""
        self.fill("username", username)
        self.fill("password", password)
        self.click("login button")

    def error_text(self) -> str:
        """The error the form shows, or an empty string."""
        return self.text_of("login error message")

    def outcome(self, wait_ms: int = _RESULT_WAIT_MS) -> str:
        """The error text shown by the form, or "Success" once the login screen has gone."""
        page = self.ui._page
        waited = 0
        while waited < wait_ms:
            message = self.error_text()
            if message:
                return message
            if self.locator("login overlay").is_hidden():
                return "Success"
            page.wait_for_timeout(200)
            waited += 200
        return "No response from the login form"

    def sign_out(self):
        self.click("profile menu")
        self.click("sign out button")
