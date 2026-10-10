"""
Wiki lint: every example page must import fixtures that exist, call fixture classes that exist, and use only columns the fixture
offers. It reads the page files directly, so a rename or a typo is caught without starting FitNesse.
"""
import glob
import importlib
import os
import re

import pytest

import fixtures
from core import fixture_catalog

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "FitNesseRoot", "FrontPage")
PAGES = sorted(glob.glob(os.path.join(ROOT, "**", "*.wiki"), recursive=True) +
               glob.glob(os.path.join(ROOT, "**", "content.txt"), recursive=True))
CATALOG = {item["table"]: item for item in fixture_catalog.list_fixtures()["fixtures"]}


def tables(path):
    """Yields the wiki tables of a page as lists of rows (each row a list of stripped cells)."""
    block = []
    for line in open(path, encoding="utf-8").read().splitlines() + [""]:
        if line.startswith("|") or line.startswith("!|"):
            body = line.lstrip("!").strip()
            body = body[1:-1] if body.endswith("|") else body[1:]          # one pipe each side only: empty trailing cells are real cells
            block.append([cell.strip() for cell in body.split("|")])
        elif block:
            yield block
            block = []


def class_name(table_name):
    return "".join(word.capitalize() for word in table_name.split())


@pytest.mark.parametrize("path", PAGES, ids=[os.path.relpath(p, ROOT) for p in PAGES])
def test_page_uses_real_fixtures_and_columns(path):
    page_tables = list(tables(path))
    imports = fixtures.fixture_packages()                                   # searched automatically, no import table needed
    for table in page_tables:
        if table[0] == ["import"]:
            imports += [row[0] for row in table[1:]]
    for prefix in imports:
        importlib.import_module(prefix)                                     # every import line must be importable

    for table in page_tables:
        first = table[0]
        if len(first) != 1 or first[0] in ("import", "library", "comment") or len(table) < 2:
            continue                                                         # script tables, imports and plain tables are not column tables
        name = first[0]
        found = next((getattr(importlib.import_module(p), class_name(name), None) for p in imports
                      if getattr(importlib.import_module(p), class_name(name), None) is not None), None)
        assert found is not None, f"{os.path.basename(path)}: no fixture class {class_name(name)} in {imports}"
        entry = CATALOG.get(name)
        if entry:
            allowed = {column["header"] for column in entry["columns"]}
            unknown = [header for header in table[1] if header not in allowed]
            assert not unknown, f"{os.path.basename(path)}: '{name}' has no column(s) {unknown}; it offers {sorted(allowed)}"
            for row in table[2:]:
                assert len(row) == len(table[1]), f"{os.path.basename(path)}: row {row} does not match the {len(table[1])} headers"


def test_lint_catches_a_wrong_column(tmp_path):
    page = tmp_path / "Bad.wiki"
    page.write_text("|login test|\n|username|passwrd|\n|a|b|\n", encoding="utf-8")
    table = list(tables(str(page)))[0]
    allowed = {column["header"] for column in CATALOG["login test"]["columns"]}
    assert [h for h in table[1] if h not in allowed] == ["passwrd"]
