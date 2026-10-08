"""
Page object registry: named pages (LoginPage, DashboardPage, ...) with their own locators.

Each page lives in data/pages/<PageName>.json:
    {"page": "LoginPage", "locators": {"username": "role=textbox:User ID", "login button": "css=button.login-btn"}}

Selectors use the same syntax as UI steps: plain CSS, //xpath or a prefix such as css= id= text= role=.
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES_DIR = os.path.join(BASE_DIR, "data", "pages")
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][\w \-]{0,60}$")


def _clean_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not _NAME_PATTERN.match(cleaned):
        raise ValueError(f"Invalid name '{name}': use letters, numbers, spaces, '-' or '_'")
    return cleaned


def _path_for(page: str) -> str:
    return os.path.join(PAGES_DIR, f"{_clean_name(page).replace(' ', '')}.json")


def _read(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as page_file:
        data = json.load(page_file)
    locators = data.get("locators", {}) if isinstance(data, dict) else {}
    return {str(k): str(v) for k, v in locators.items()}


def list_pages() -> dict:
    """Returns {page name: {locator name: selector}} for every page file."""
    pages = {}
    if not os.path.isdir(PAGES_DIR):
        return pages
    for file_name in sorted(os.listdir(PAGES_DIR)):
        if not file_name.endswith(".json"):
            continue
        path = os.path.join(PAGES_DIR, file_name)
        try:
            with open(path, "r", encoding="utf-8") as page_file:
                data = json.load(page_file)
            if not isinstance(data, dict):
                continue      # not a page file
            pages[str(data.get("page") or file_name[:-5])] = _read(path)
        except (OSError, ValueError, AttributeError):
            continue
    return pages


def get_locators(page: str) -> dict:
    """Locators of one page (empty dict when the page does not exist)."""
    return list_pages().get(str(page or "").strip(), {})


def page_exists(page: str) -> bool:
    return str(page or "").strip() in list_pages()


def save_locator(page: str, locator: str, selector: str) -> dict:
    """Adds or updates a locator, creating the page file when needed. Returns the page's locators."""
    page_name, locator_name = _clean_name(page), _clean_name(locator)
    selector = str(selector or "").strip()
    if not selector:
        raise ValueError("Selector is required")
    locators = get_locators(page_name)
    locators[locator_name] = selector
    _write(page_name, locators)
    return locators


def remove_locator(page: str, locator: str) -> dict:
    locators = get_locators(page)
    locators.pop(str(locator).strip(), None)
    _write(_clean_name(page), locators)
    return locators


def _write(page_name: str, locators: dict) -> None:
    os.makedirs(PAGES_DIR, exist_ok=True)
    path = _path_for(page_name)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as page_file:
        json.dump({"page": page_name, "locators": locators}, page_file, indent=2)
    os.replace(temporary, path)
