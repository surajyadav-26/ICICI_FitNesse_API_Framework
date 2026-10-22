"""
The framework's structural rules (see AGENTS.md), as tests, so an AI tool or a new developer cannot drift from the design by
accident. If one of these fails, fix the change, not the test. Changing a rule needs the owner's approval and an update of
AGENTS.md in the same change.
"""
import ast
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Folders that may exist at the top level. A new one means the change does not fit a layer (AGENTS.md section 4, rule 6).
ALLOWED_TOP_LEVEL = {".claude", ".cursor", ".git", ".github", ".pytest_cache", ".venv", ".vscode", "FitNesseRoot", "__pycache__",
                     "core", "data", "fixtures", "logs", "pages", "runtime", "test-artifacts", "tests", "waferslim"}


def python_files(*folders):
    for folder in folders:
        for base, dirs, files in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if name.endswith(".py"):
                    yield os.path.join(base, name)


def imports_of(path) -> set:
    tree = ast.parse(open(path, encoding="utf-8-sig").read())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def relative(path) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def offenders(folders, forbidden_prefixes, allowed_files=()):
    found = []
    for path in python_files(*folders):
        if relative(path) in allowed_files:
            continue
        for name in imports_of(path):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes):
                found.append(f"{relative(path)} imports {name}")
    return sorted(set(found))


def test_engines_do_not_import_fixtures():
    assert offenders(["core"], ["fixtures"]) == []


def test_only_the_server_reads_page_objects_from_core():
    assert offenders(["core"], ["pages"], allowed_files={"core/user_store_server.py"}) == []


def test_page_objects_do_not_import_fixtures():
    assert offenders(["pages"], ["fixtures"]) == []


def test_api_fixtures_stay_independent_of_the_browser_fixtures():
    assert offenders(["fixtures/api"], ["fixtures.ui", "fixtures.visual", "fixtures.accessibility", "pages"]) == []


def test_the_vendored_slim_server_reaches_into_the_project_in_two_places_only():
    # server.py reports the run to core.report_generator; execution.py searches the fixtures package for classes
    assert offenders(["waferslim"], ["pages"]) == []
    assert offenders(["waferslim"], ["fixtures"], allowed_files={"waferslim/execution.py"}) == []
    assert offenders(["waferslim"], ["core"], allowed_files={"waferslim/server.py"}) == []
    execution = open(os.path.join(ROOT, "waferslim", "execution.py"), encoding="utf-8").read()
    assert execution.count("from fixtures import") == 1


def test_no_new_top_level_folder():
    found = {entry for entry in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, entry))}
    assert found - ALLOWED_TOP_LEVEL == set(), "put new files in the layer they belong to (AGENTS.md)"


def test_framework_code_does_not_name_the_application():
    names = ("Nirikshan", "ICICI")
    found = []
    for path in python_files("core", "fixtures/api", "fixtures/accessibility", "fixtures/visual", "waferslim"):
        if relative(path) == "core/config.py":           # the default name lives here, once
            continue
        for number, line in enumerate(open(path, encoding="utf-8-sig").read().splitlines(), 1):
            if any(name in line for name in names):
                found.append(f"{relative(path)}:{number}")
    assert found == [], "use Config.APP_NAME / Config.APP_TITLE"


def test_launch_scripts_never_kill_processes_by_name():
    for name in ("start_server.bat", "setup_env.bat", ".github/workflows/automation-tests.yml"):
        text = open(os.path.join(ROOT, name), encoding="utf-8", errors="replace").read().lower()
        assert "/im java" not in text and "/im python" not in text and "stop-process -name" not in text, name


def test_every_column_fixture_declares_snake_case_columns():
    from core import fixture_catalog
    catalog = fixture_catalog.list_fixtures()
    assert catalog["problems"] == []
    for fixture in catalog["fixtures"]:
        for column in fixture["columns"]:
            assert column["name"] == column["name"].lower() and " " not in column["name"], f"{fixture['class']}.{column['name']}"
        assert any(column["required"] for column in fixture["columns"]), f"{fixture['class']} has no required column"


@pytest.mark.parametrize("pointer", ["CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", ".cursor/rules/framework.mdc"])
def test_every_tool_is_pointed_at_the_one_rule_file(pointer):
    text = open(os.path.join(ROOT, *pointer.split("/")), encoding="utf-8").read()
    assert "AGENTS.md" in text, f"{pointer} must send the tool to AGENTS.md"


def test_the_rule_file_names_the_test_command_that_works():
    text = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8").read()
    assert "python -m pytest -q -p no:allure_pytest_bdd tests/unit" in text


def test_the_import_scan_really_sees_violations(tmp_path):
    sample = tmp_path / "bad.py"
    sample.write_text("import fixtures.ui.ui_fixture\nfrom pages.login_page import LoginPage\n", encoding="utf-8")
    found = imports_of(str(sample))
    assert "fixtures.ui.ui_fixture" in found and "pages.login_page.LoginPage" in found


# pip name of every third-party module the framework (not the vendored Slim server's own specs) imports
_PIP_NAMES = {"PIL": "pillow", "dotenv": "python-dotenv", "websocket": "websocket-client", "grpc": "grpcio",
              "grpc_tools": "grpcio-tools", "google": "protobuf", "jwt": "pyjwt", "jsonpath_ng": "jsonpath-ng",
              "requests_oauthlib": "requests-oauthlib", "requests_toolbelt": "requests-toolbelt"}
_LOCAL_TOP_LEVEL = {"core", "fixtures", "pages", "waferslim", "tests", "data"}


def test_every_package_the_code_imports_is_in_requirements_txt():
    import sys
    text = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().lower()
    declared = {line.split(">=")[0].split("==")[0].strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}
    missing = {}
    for path in python_files("core", "fixtures", "pages"):
        for name in imports_of(path):
            top = name.split(".")[0]
            if top in sys.stdlib_module_names or top in _LOCAL_TOP_LEVEL:
                continue
            package = _PIP_NAMES.get(top, top).lower()
            if package not in declared:
                missing.setdefault(package, set()).add(relative(path))
    assert missing == {}, f"imported but not in requirements.txt: {missing}"


def test_every_setting_config_reads_is_listed_in_env_example():
    """A new QA copies .env.example to .env, so a setting missing from it can only be found by reading the code."""
    with open(os.path.join(ROOT, "core", "config.py"), encoding="utf-8") as handle:
        read = set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"', handle.read()))
    with open(os.path.join(ROOT, ".env.example"), encoding="utf-8") as handle:
        listed = set(re.findall(r"^([A-Z0-9_]+)=", handle.read(), re.M))
    internal = {"FITNESSE_PAGE_NAME", "FITNESSE_PAGE_PATH", "PLAYWRIGHT_BROWSERS_PATH", "LOCALAPPDATA"}      # set by FitNesse / the machine
    assert read - listed - internal == set(), "add these to .env.example"
