"""
Centralized Page Object Registry with QA-Brain Natural Language Translation.
Delegates locator resolution dynamically to feature-specific Page Objects, supporting
natural English with spaces, dynamic text-row scoping ("for <text>"), and index-based selections ("<name> <number>").
"""
import re
from .dashboard_page import DashboardPage
from .swag_labs_login_page import SwagLabsLoginPage
from .swag_labs_inventory_page import SwagLabsInventoryPage


class PageRegistry:
    """
    Central repository of all element locators. Normalizes plain English
    to support highly intuitive, non-technical test specifications for BAs.
    """

    @classmethod
    def get_locator(cls, page, element_name: str):
        """
        Dynamically delegates and compiles a native Playwright Locator object at runtime.
        Natively supports plain English, row-text scoping, and numeric indices.
        """
        raw_name = str(element_name).strip()
        
        # 1. Handle Row-Text Scoping: "pay button for electricity"
        # Syntax: "<element_name> for <row_text>"
        if " for " in raw_name.lower():
            parts = re.split(r'\s+for\s+', raw_name, maxsplit=1, flags=re.IGNORECASE)
            base_element = parts[0].strip()
            row_text = parts[1].strip()
            
            # Resolve the base element selector
            base_selector = cls._resolve_selector_string(base_element)
            
            # Playwright: Find table row or container containing the text, then locate base element inside it
            logger_info = f"[PageRegistry] Scoping element '{base_element}' inside row containing '{row_text}'"
            return page.locator("tr, div, li, .row, .card").filter(has_text=row_text).locator(base_selector)

        # 2. Handle Numeric Indexing: "pay button 2"
        # Syntax: "<element_name> <index_number>"
        match_index = re.search(r'\s+(\d+)$', raw_name)
        if match_index:
            index_num = int(match_index.group(1))
            base_element = raw_name[:match_index.start()].strip()
            
            base_selector = cls._resolve_selector_string(base_element)
            
            # Playwright indices are 0-based, so "button 2" becomes .nth(1)
            return page.locator(base_selector).nth(index_num - 1)

        # 3. Handle Standard Plain English
        # "Login Button" -> "login_button"
        base_selector = cls._resolve_selector_string(raw_name)
        
        norm_name = raw_name.lower().replace(" ", "_").replace("-", "_")
        if norm_name in ["swag_username", "swag_password", "swag_login_button", "error_message"]:
            return SwagLabsLoginPage.get_locator(page, raw_name)

        if norm_name in ["username", "password", "login_button"]:
            return page.locator(base_selector)
            
        return page.locator(base_selector)

    @classmethod
    def _resolve_selector_string(cls, element_name: str) -> str:
        """
        Helper to normalize English strings and return raw selector string from POM.
        """
        norm_name = str(element_name).lower().strip().replace(" ", "_").replace("-", "_")
        
        # Merge static selectors for check
        all_selectors = {
            **DashboardPage.SELECTORS,
            **SwagLabsLoginPage.SELECTORS,
            **SwagLabsInventoryPage.SELECTORS,
            "username": "#user-name, input[type='text'], input[name='username'], input#username",
            "password": "#password, input[type='password'], input[name='password'], input#password",
            "login_button": "#login-button, #loginButton, button.login-btn, button[type='submit'], input[type='submit']",
            "submit_button": "button[type='submit'], input[type='submit']",
            "search_box": "input[type='text'], input[type='search'], input[name='q']",
            "date_input": "input[type='date'], input[name*='date']",
            "dropdown": "select, [role='combobox']",
            "logout_button": "button:has-text('Logout'), a:has-text('Logout')",
            "profile_link": "a:has-text('Profile'), [data-testid='profile']"
        }
        
        return all_selectors.get(norm_name, element_name)
