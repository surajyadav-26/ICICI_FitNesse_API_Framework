"""
Catalog of the column-table fixtures, for the Step Builder.

Every class below the scanned packages that declares COLUMNS (see core/fixture_meta.py) is listed with its wiki table name,
the import line a page needs, a description and its columns (required / optional, allowed values, examples).

    fixtures/ui/scenario/*   UI scenarios (login, ...)        fixtures/accessibility   WCAG checks        fixtures/visual   screenshot comparison        fixtures/api   HTTP requests
"""
import importlib
import inspect
import os
import pkgutil

from core.fixture_meta import table_name
from core.logger import logger

SCAN_ROOTS = (
    ("UI scenarios", "fixtures.ui.scenario"),
    ("Accessibility", "fixtures.accessibility"),
    ("Visual", "fixtures.visual"),
    ("API", "fixtures.api"),
)

_modified: dict = {}      # module name -> file modified time when it was last (re)loaded


def _load(name: str):
    """Imports a module, reloading it when its file has changed (the server runs for a long time)."""
    module = importlib.import_module(name)
    path = getattr(module, "__file__", None)
    if path and os.path.exists(path):
        stamp = os.path.getmtime(path)
        if name in _modified and _modified[name] != stamp:
            module = importlib.reload(module)
        _modified[name] = stamp
    return module


def _columns_of(cls) -> tuple:
    getter = getattr(cls, "columns", None)
    columns = getter() if callable(getter) else getattr(cls, "COLUMNS", ())
    return tuple(columns or ())


def _import_path(module_name: str, class_name: str) -> str:
    """The shortest package that exposes the class, e.g. fixtures.ui.scenario.login for LoginTest."""
    parts = module_name.split(".")
    for end in range(len(parts) - 1, 1, -1):
        candidate = ".".join(parts[:end])
        try:
            if hasattr(importlib.import_module(candidate), class_name):
                return candidate
        except Exception:
            continue
    return ".".join(parts[:-1])


def _description(cls) -> str:
    declared = getattr(cls, "DESCRIPTION", "")
    if declared:
        return declared
    lines = (inspect.getdoc(cls) or "").strip().splitlines()
    return lines[0] if lines else ""


def list_fixtures() -> dict:
    """{"fixtures": [...], "problems": [...]}; one broken fixture file never hides the others."""
    fixtures, problems = [], []
    for area, package_name in SCAN_ROOTS:
        try:
            package = _load(package_name)
        except Exception as error:
            problems.append(f"{package_name}: {error}")
            continue
        names = [package_name] + [info.name for info in pkgutil.walk_packages(package.__path__, package_name + ".") if not info.ispkg]
        for module_name in names:
            try:
                module = _load(module_name)
            except Exception as error:
                problems.append(f"{module_name}: {error}")
                logger.warning(f"[FixtureCatalog] Could not load {module_name}: {error}")
                continue
            for cls in vars(module).values():
                if not (inspect.isclass(cls) and cls.__module__ == module.__name__):
                    continue
                columns = _columns_of(cls)
                if not columns:
                    continue
                group = area
                if package_name.endswith(".scenario") and module_name.count(".") > package_name.count("."):
                    group = module_name.split(".")[package_name.count(".") + 1].replace("_", " ").title()
                fixtures.append({
                    "class": cls.__name__, "table": table_name(cls.__name__), "area": area, "group": group,
                    "import": _import_path(module_name, cls.__name__), "description": _description(cls),
                    "columns": [column.to_dict() for column in columns],
                })
    fixtures.sort(key=lambda item: ([root[0] for root in SCAN_ROOTS].index(item["area"]), item["group"], item["class"]))
    return {"fixtures": fixtures, "problems": problems}
