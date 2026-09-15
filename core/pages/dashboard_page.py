"""
Page Object Model (POM) for the ICICI Retail Banking Dashboard.
Encapsulates selectors and page properties to maintain clean test specifications.
"""


class DashboardPage:
    """
    Selectors and endpoints for the Dashboard portal.
    """

    # Static CSS/XPath selectors for Dashboard elements
    SELECTORS = {
        "account_balance": ".balance-amount, #acc-balance, .ici-balance",
        "profile_link": "#user-profile, .profile-nav, a[href*='profile']",
        "fund_transfer_tab": "#transfer-menu, a[href*='transfer'], .ici-transfer-nav",
        "logout_button": "#logout-btn, .logout-link, a[href*='logout']"
    }

    @classmethod
    def get_locator(cls, page, element_name: str):
        """
        Returns the native Playwright Locator for the dashboard element.
        """
        norm_name = str(element_name).lower().strip().replace(" ", "_").replace("-", "_")
        selector = cls.SELECTORS.get(norm_name, element_name)
        return page.locator(selector)
