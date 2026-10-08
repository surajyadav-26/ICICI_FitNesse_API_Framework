"""
Page Object Model (POM) for ICICI Net Banking Login Page.
Encapsulates selectors and page properties to maintain clean test specifications dynamically.
"""
from core.config import Config


class LoginPage:
    """
    Selectors and endpoints for the Net Banking login portal.
    """

    # Target login endpoint loaded from centralized Config!
    URL = Config.UI_BASE_URL

    @classmethod
    def get_locator(cls, page, element_name: str):
        """
        Returns the exact, precise native Playwright Locator for the element.
        """
        norm_name = str(element_name).lower().strip().replace(" ", "_").replace("-", "_")
        
        # ICICI Bank-Specific Locators
        if norm_name == "username":
            # page.getByRole('textbox', { name: 'User ID' })
            return page.get_by_role("textbox", name="User ID")
            
        if norm_name == "password":
            # page.getByLabel('Password')
            return page.get_by_label("Password")
            
        if norm_name in ["login_button", "loginbutton"]:
            # page.locator('button.login-btn')
            return page.locator("button.login-btn")

        if norm_name in ["framework_username", "nirikshan_username"]:
            return page.get_by_role("textbox", name="Username")

        if norm_name in ["framework_password", "nirikshan_password"]:
            return page.get_by_role("textbox", name="Password")

        if norm_name in ["framework_login_button", "nirikshan_login_button"]:
            return page.get_by_role("button", name="Log In")

        if norm_name in ["login_error_message", "login_error"]:
            return page.locator("#icici-login-error")

        if norm_name in ["profile_menu", "user_profile"]:
            return page.locator("#icici-user-chip")

        if norm_name in ["sign_out_button", "sign_out"]:
            return page.get_by_role("button", name="🚪 Sign Out")
            
        # Fallback to standard selector if not predefined
        return page.locator(element_name)
