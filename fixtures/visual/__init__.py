"""
Visual-testing fixtures. The comparison engine is core/visual_compare.py (baselines, diff, approval); the review page is
core/visual_review.py.

visual_steps.py holds the `verify visual match` family of steps. UiFixture inherits them, so they work in any UI script table;
this module only imports from core, which keeps fixtures/ui -> fixtures/visual a one-way dependency.

    | visual test |                         (column table, one row per page and baseline name; see visual_test.py)
    | layout test |                         (column table: alignment, size and colours of chosen elements; see layout_test.py)
"""
from importlib import import_module

_FIXTURE_MODULES = {"VisualTestingMixin": "visual_steps", "VisualTest": "visual_test", "LayoutTest": "layout_test"}

__all__ = list(_FIXTURE_MODULES)


def __getattr__(name: str):
    module_name = _FIXTURE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = value
    return value
