"""Page Object Model for the SauceDemo (Swag Labs) inventory page."""
from typing import Final


class SwagLabsInventoryPage:
    """Selectors and inventory actions for https://www.saucedemo.com/inventory.html."""

    URL_PATTERN: Final[str] = "**/inventory.html"
    SELECTORS: Final[dict[str, str]] = {
        "inventory_title": ".title",
        "products_title": ".title",
        "backpack": "[data-test='add-to-cart-sauce-labs-backpack']",
        "bike_light": "[data-test='add-to-cart-sauce-labs-bike-light']",
        "cart_link": ".shopping_cart_link",
        "cart_badge": ".shopping_cart_badge",
        "menu_button": "#react-burger-menu-btn",
        "logout_link": "#logout_sidebar_link",
    }

    @classmethod
    def get_locator(cls, page, element_name: str):
        """Return a Playwright locator for an inventory element name."""
        normalized_name = (
            str(element_name).lower().strip().replace(" ", "_").replace("-", "_")
        )
        selector = cls.SELECTORS.get(normalized_name, element_name)
        return page.locator(selector)

    @classmethod
    def add_backpack_to_cart(cls, page) -> None:
        """Add the Sauce Labs Backpack to the shopping cart."""
        cls.get_locator(page, "backpack").click()

    @classmethod
    def cart_item_count(cls, page) -> str:
        """Return the visible shopping cart badge count."""
        return cls.get_locator(page, "cart_badge").inner_text()
