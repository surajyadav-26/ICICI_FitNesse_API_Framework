"""
Accessibility fixtures (axe-core in the browser; engine and report in core/accessibility.py).

    | import | fixtures.accessibility |
    | script | accessibility fixture |        (script table, one page)
    | accessibility test |                    (column table, one row per page / WCAG setting)
"""
from importlib import import_module

_FIXTURE_MODULES = {
    "AccessibilityFixture": "accessibility_fixture",
    "AccessibilityTest": "accessibility_test",
}

__all__ = list(_FIXTURE_MODULES)


def __getattr__(name: str):
    module_name = _FIXTURE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = value
    return value
