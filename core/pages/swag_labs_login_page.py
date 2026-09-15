"""Page Object Model for the SauceDemo (Swag Labs) login page."""
from typing import Final


class SwagLabsLoginPage:
    """Selectors and login behavior for https://www.saucedemo.com/."""

    URL: Final[str] = "https://www.saucedemo.com/"
    SELECTORS: Final[dict[str, str]] = {
        "username": "#user-name",
        "user_name": "#user-name",
        "password": "#password",
        "login_button": "#login-button",
        "loginbutton": "#login-button",
        "error_message": "[data-test='error']",
    }

    @classmethod
    def get_locator(cls, page, element_name: str):
        """Return a Playwright locator for a SauceDemo element name."""
        normalized_name = (
            str(element_name).lower().strip().replace(" ", "_").replace("-", "_")
        )
        selector = cls.SELECTORS.get(normalized_name, element_name)
        return page.locator(selector)

    @classmethod
    def login(cls, page, username: str, password: str) -> None:
        """Complete the SauceDemo login form."""
        cls.get_locator(page, "username").fill(username)
        cls.get_locator(page, "password").fill(password)
        cls.get_locator(page, "login_button").click()
