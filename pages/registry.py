"""
Page registry (pages/registry.py): finds the page objects in pages/*.py and exposes their locators.

    pages/login_page.py   class LoginPage(BasePage): USERNAME = "role=textbox:Username"  ->  {"LoginPage": {"username": ...}}

Selectors use the same syntax as UI steps: plain CSS, //xpath or a prefix such as css= id= text= role=.
The registry is read by the UI fixtures (to resolve `LoginPage.username`) and by the Step Builder (locator drop-down).
"""
import importlib.util
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_DIR = os.path.dirname(os.path.abspath(__file__))     # this folder: pages/

_SKIPPED_MODULES = {"__init__", "base_page", "registry"}
_cache: dict = {}    # file path -> (modified time, {page name: {locator name: selector}})


def _normalise(name: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(name).strip().lower())


def _pages_in(path: str) -> dict:
    """Loads one module file and returns the locators of every BasePage subclass defined in it."""
    from pages.base_page import BasePage     # the same class object the page modules import

    stem = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(f"_page_registry_{stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found = {}
    for value in vars(module).values():
        if isinstance(value, type) and issubclass(value, BasePage) and value is not BasePage \
                and value.__module__ == module.__name__:
            found[value.page_name()] = value.locators()
    return found


def list_pages() -> dict:
    """{page name: {locator name: selector}} for every page object in the pages folder."""
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    pages: dict = {}
    if not os.path.isdir(PAGES_DIR):
        return pages
    for file_name in sorted(os.listdir(PAGES_DIR)):
        stem, extension = os.path.splitext(file_name)
        if extension != ".py" or stem in _SKIPPED_MODULES or stem.startswith("_"):
            continue
        path = os.path.join(PAGES_DIR, file_name)
        try:
            modified = os.path.getmtime(path)
            cached = _cache.get(path)
            if cached is None or cached[0] != modified:
                cached = (modified, _pages_in(path))
                _cache[path] = cached
            pages.update(cached[1])
        except Exception:
            continue     # a broken page file must not take the other pages down
    return pages


def get_locators(page: str) -> dict:
    """Locators of one page (empty dict when the page does not exist)."""
    wanted = str(page or "").strip().lower()
    for name, locators in list_pages().items():
        if name.lower() == wanted:
            return locators
    return {}


def page_exists(page: str) -> bool:
    wanted = str(page or "").strip().lower()
    return any(name.lower() == wanted for name in list_pages())


def find_selector(page: str, locator: str):
    """The selector of a locator on a page (names ignore case, spaces, '_' and '-'), or None."""
    wanted = _normalise(locator)
    for name, selector in get_locators(page).items():
        if _normalise(name) == wanted:
            return selector
    return None
