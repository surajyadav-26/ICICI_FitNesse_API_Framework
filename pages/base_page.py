"""Base class of every page object."""
import re


class PageActionFailed(Exception):
    """A UI step of a page action failed; the message says which one."""


def locator_name(attribute: str) -> str:
    """LOGIN_BUTTON -> "login button" (the name used in wiki tables and the Step Builder)."""
    return attribute.lower().replace("_", " ")


def normalise(name: str) -> str:
    """Case, spacing, '_' and '-' do not matter when a locator is looked up by name."""
    return re.sub(r"[\s_\-]+", " ", str(name).strip().lower())


class BasePage:
    """
    Subclass it, declare locators as UPPER_CASE class attributes and write the page actions as methods:

        class LoginPage(BasePage):
            USERNAME = "role=textbox:Username"

            def login(self, user, password):
                self.fill("username", user)
    """

    NAME = ""            # defaults to the class name

    def __init__(self, ui) -> None:
        self.ui = ui

    @classmethod
    def page_name(cls) -> str:
        return cls.NAME or cls.__name__

    @classmethod
    def locators(cls) -> dict:
        """{locator name: selector} for every UPPER_CASE string attribute (inherited ones included)."""
        found = {}
        for klass in reversed(cls.__mro__):
            for attribute, value in vars(klass).items():
                if attribute.isupper() and attribute != "NAME" and isinstance(value, str):
                    found[locator_name(attribute)] = value
        return found

    # ── helpers for page actions ──────────────────────────────────────────────
    def selector(self, name: str) -> str:
        return f"{self.page_name()}.{name}"

    def locator(self, name: str):
        """The Playwright locator of one of this page's locators."""
        return self.ui._locator(self.selector(name))

    def do(self, step, *args):
        """Runs a UiFixture step; a failed step raises PageActionFailed."""
        from core.flow import is_failure
        result = step(*args)
        if is_failure(result):
            raise PageActionFailed(f"{self.page_name()}: step '{getattr(step, '__name__', step)}' failed ({', '.join(str(a) for a in args)})")
        return result

    def fill(self, name: str, value: str):
        return self.do(self.ui.enter_text_with_value, self.selector(name), value)

    def click(self, name: str):
        return self.do(self.ui.click_element, self.selector(name))

    def text_of(self, name: str) -> str:
        locator = self.locator(name)
        return locator.first.inner_text().strip() if locator.count() else ""

    def is_visible(self, name: str) -> bool:
        locator = self.locator(name)
        return bool(locator.count()) and locator.first.is_visible()
