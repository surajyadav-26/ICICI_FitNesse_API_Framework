"""The fixture catalog behind the Step Builder: complete, accurate and tolerant of a broken fixture file."""
import sys
import textwrap

import pytest

from core import fixture_catalog
from core.fixture_meta import Column, input_column, output_column, table_name
from fixtures.ui.decision_fixture import DecisionFixture

EXPECTED_TABLES = {
    "login test", "accessibility test", "visual test", "layout test", "auth fixture", "get request fixture", "post request fixture", "put request fixture",
    "patch request fixture", "delete request fixture", "head request fixture", "options request fixture",
}


@pytest.fixture(scope="module")
def catalog():
    return fixture_catalog.list_fixtures()


def test_every_column_fixture_is_listed(catalog):
    assert catalog["problems"] == []
    assert {f["table"] for f in catalog["fixtures"]} == EXPECTED_TABLES


def test_entries_have_what_the_builder_needs(catalog):
    for fixture in catalog["fixtures"]:
        assert fixture["description"], fixture["class"]
        assert fixture["import"].startswith("fixtures."), fixture["class"]
        assert any(c["kind"] == "input" for c in fixture["columns"]), fixture["class"]
        assert any(c["kind"] == "output" for c in fixture["columns"]), fixture["class"]
        assert any(c["required"] for c in fixture["columns"] if c["kind"] == "input"), f"{fixture['class']} has no required input"
        headers = [c["header"] for c in fixture["columns"]]
        assert len(headers) == len(set(headers)), f"duplicate columns in {fixture['class']}"
        for column in fixture["columns"]:
            assert column["header"].endswith("?") == (column["kind"] == "output")


def test_groups_and_import_lines(catalog):
    by_table = {f["table"]: f for f in catalog["fixtures"]}
    assert by_table["login test"]["import"] == "fixtures.ui.scenario.login" and by_table["login test"]["group"] == "Login"
    assert by_table["accessibility test"]["import"] == "fixtures.accessibility"
    assert by_table["get request fixture"]["import"] == "fixtures.api" and by_table["get request fixture"]["area"] == "API"
    areas = [f["area"] for f in catalog["fixtures"]]
    assert areas == sorted(areas, key=["UI scenarios", "Accessibility", "Visual", "API"].index)       # scenarios, accessibility, visual, then API


def test_login_columns(catalog):
    login = next(f for f in catalog["fixtures"] if f["table"] == "login test")
    columns = {c["name"]: c for c in login["columns"]}
    assert columns["username"]["required"] and columns["password"]["required"] and columns["password"]["secret"]
    assert not columns["browser"]["required"] and columns["browser"]["options"] == ["chromium", "chrome", "msedge", "firefox", "webkit"]
    assert columns["login_result"]["kind"] == "output" and columns["login_result"]["header"] == "login result?"


def test_every_listed_column_exists_on_its_fixture(catalog):
    """A column the builder offers must be something the fixture really understands (guards metadata drift)."""
    import importlib
    for entry in catalog["fixtures"]:
        cls = getattr(importlib.import_module(entry["import"]), entry["class"])
        instance = cls()
        for column in entry["columns"]:
            if column["kind"] == "input":
                assert hasattr(instance, "set_" + column["name"]), f"{entry['class']}: no setter for {column['header']}"
            elif issubclass(cls, DecisionFixture):
                assert column["name"] in cls.OUTPUTS, f"{entry['class']}: {column['header']} is not in OUTPUTS"
            else:
                assert hasattr(instance, column["name"]), f"{entry['class']}: no result method for {column['header']}"


def test_decision_fixture_derives_columns_when_not_declared():
    class Plain(DecisionFixture):
        INPUTS = ("a_field", "b_field")
        OUTPUTS = ("result",)
    assert [c.header for c in Plain.columns()] == ["a field", "b field", "result?"]
    assert not any(c.required for c in Plain.columns())


def test_column_helpers():
    assert input_column("wcag_version").header == "wcag version"
    assert output_column("login_result").header == "login result?"
    assert Column("x").to_dict()["kind"] == "input"
    assert table_name("GetRequestFixture") == "get request fixture" and table_name("LoginTest") == "login test"


def test_a_broken_fixture_file_does_not_hide_the_others(tmp_path, monkeypatch):
    package = tmp_path / "demo_fixtures"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "good_fixture.py").write_text(textwrap.dedent("""
        from core.fixture_meta import input_column, output_column

        class GoodTest:
            DESCRIPTION = "Works"
            COLUMNS = (input_column("name", required=True), output_column("greeting"))
    """), encoding="utf-8")
    (package / "broken_fixture.py").write_text("import module_that_does_not_exist\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(fixture_catalog, "SCAN_ROOTS", (("Demo", "demo_fixtures"), ("Missing", "no_such_package")))
    monkeypatch.setattr(fixture_catalog, "_modified", {})
    result = fixture_catalog.list_fixtures()
    assert [f["table"] for f in result["fixtures"]] == ["good test"]
    assert len(result["problems"]) == 2
    assert any("broken_fixture" in p for p in result["problems"]) and any("no_such_package" in p for p in result["problems"])
    for name in ("demo_fixtures", "demo_fixtures.good_fixture"):
        sys.modules.pop(name, None)
