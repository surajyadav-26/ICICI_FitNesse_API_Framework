"""Browser fixtures. In a wiki page: `| import |` / `| fixtures.ui |`, then `| script | ui fixture |`.
Scenario fixtures live in fixtures.ui.scenario.<name> (for example fixtures.ui.scenario.login)."""
from importlib import import_module

_FIXTURE_MODULES = {
    "UiFixture": "ui_fixture",
        "SuiteHelper": "suite_helper",
    "DecisionFixture": "decision_fixture",
}

__all__ = list(_FIXTURE_MODULES)


def __getattr__(name: str):
    module_name = _FIXTURE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    fixture_class = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = fixture_class
    return fixture_class
