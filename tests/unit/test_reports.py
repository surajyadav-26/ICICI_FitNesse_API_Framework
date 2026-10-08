"""Unit tests for report data: FitNesse result scanning, step mapping, Allure results and ENV variables."""
import json
import os

import pytest

from core import allure_helper, report_generator
from fixtures import ui_flow


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Redirects every report path into a temporary workspace."""
    files = tmp_path / "FitNesseRoot" / "files"
    (files / "testResults").mkdir(parents=True)
    monkeypatch.setattr(report_generator, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(report_generator, "HISTORY_FILE", str(files / "report_history.json"))
    monkeypatch.setattr(report_generator, "REPORT_FILE", str(files / "report.html"))
    monkeypatch.setattr(report_generator, "report_history", [])
    monkeypatch.setattr(report_generator, "trigger_delayed_report", lambda: None)
    monkeypatch.setattr(allure_helper, "ALLURE_RESULTS_DIR", str(files / "testResults" / "allure-results"))
    monkeypatch.setattr(allure_helper, "_ACTIVE_RESULTS", {})
    for name in ("FITNESSE_PAGE_NAME", "FITNESSE_PAGE_PATH"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def write_result(workspace, page, name):
    folder = workspace / "FitNesseRoot" / "files" / "testResults" / page
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("<testResults/>", encoding="utf-8")


# ── Simple report ─────────────────────────────────────────────────────────────
def test_fitnesse_result_file_names_are_read(workspace):
    write_result(workspace, "FrontPage.LoginTest", "20261008101509_3_1_0_2.xml")
    [result] = report_generator.scan_test_results()
    assert result["name"] == "LoginTest"
    assert (result["right"], result["wrong"], result["ignored"], result["exceptions"]) == (3, 1, 0, 2)
    assert result["timestamp"] == "2026-10-08 10:15:09"


def test_page_history_zips_are_not_test_results(workspace):
    import zipfile
    page = workspace / "FitNesseRoot" / "FrontPage" / "LoginTest"
    page.mkdir(parents=True)
    with zipfile.ZipFile(page / "20261008101509.zip", "w") as archive:
        archive.writestr("content.txt", "| script |")
        archive.writestr("properties.xml", "<properties/>")
    assert report_generator.scan_test_results() == []


def test_unrelated_xml_files_are_ignored(workspace):
    write_result(workspace, "FrontPage.LoginTest", "notes.xml")
    write_result(workspace, "FrontPage.LoginTest", "20261008101509.xml")
    assert report_generator.scan_test_results() == []


def test_test_page_directly_under_front_page_is_listed_with_its_steps(workspace):
    write_result(workspace, "FrontPage.LoginTest", "20261008101500_0_1_0_0.xml")   # FitNesse stamps the START of the run
    report_generator.report_history.extend([
        {"timestamp": "2026-10-08 10:15:01", "method": "STEP", "url": "Navigate to 'http://x'", "status_code": 200,
         "response_time_ms": 0, "request_body": "", "response_body": "", "curl": "", "page": "LoginTest"},
        {"timestamp": "2026-10-08 10:15:05", "method": "STEP", "url": "FAILED: Click element 'Login'", "status_code": 500,
         "response_time_ms": 0, "request_body": "", "response_body": "Click failed - timeout", "curl": "", "page": "LoginTest"},
    ])
    report_generator.generate_html_report()
    page = open(report_generator.REPORT_FILE, encoding="utf-8").read()
    assert "NO TEST RESULTS CAPTURED" not in page
    assert "LoginTest" in page
    assert "Navigate to" in page and "FAILED: Click element" in page and "Click failed - timeout" in page
    assert "STEP 1" in page and "STEP 2" in page


def test_suite_summary_is_not_listed_as_a_test_case(workspace):
    write_result(workspace, "FrontPage.Regression", "20261008101600_2_0_0_0.xml")
    write_result(workspace, "FrontPage.Regression.LoginTest", "20261008101510_1_0_0_0.xml")
    write_result(workspace, "FrontPage.Regression.HomeTest", "20261008101550_1_0_0_0.xml")
    report_generator.generate_html_report()
    page = open(report_generator.REPORT_FILE, encoding="utf-8").read()
    assert 'data-name="Regression.LoginTest"' in page and 'data-name="Regression.HomeTest"' in page
    assert 'data-name="Regression"' not in page


def test_steps_of_each_run_follow_their_own_result(workspace):
    write_result(workspace, "FrontPage.LoginTest", "20261008101000_1_0_0_0.xml")
    write_result(workspace, "FrontPage.LoginTest", "20261008103000_1_0_0_0.xml")
    report_generator.report_history.extend([
        {"timestamp": "2026-10-08 10:10:03", "method": "STEP", "url": "first run step", "status_code": 200,
         "response_time_ms": 0, "request_body": "", "response_body": "", "curl": "", "page": "LoginTest"},
        {"timestamp": "2026-10-08 10:30:03", "method": "STEP", "url": "second run step", "status_code": 200,
         "response_time_ms": 0, "request_body": "", "response_body": "", "curl": "", "page": "LoginTest"},
    ])
    results = {r["timestamp_raw"]: r for r in report_generator.scan_test_results()}
    report_generator.generate_html_report()
    page = open(report_generator.REPORT_FILE, encoding="utf-8").read()
    assert page.count(">first run step<") == 1 and page.count(">second run step<") == 1
    assert len(results) == 2


def test_records_are_tagged_with_the_running_page(workspace, monkeypatch):
    monkeypatch.setenv("FITNESSE_PAGE_NAME", "LoginTest")
    monkeypatch.setenv("FITNESSE_PAGE_PATH", "FrontPage")
    assert report_generator.current_page_full_name() == "LoginTest"
    monkeypatch.setenv("FITNESSE_PAGE_PATH", "FrontPage.Regression")
    assert report_generator.current_page_full_name() == "Regression.LoginTest"
    report_generator.add_record({"timestamp": "2026-10-08 10:00:00", "method": "STEP", "url": "x", "status_code": 200,
                                 "response_time_ms": 0, "request_body": "", "response_body": "", "curl": ""})
    assert json.load(open(report_generator.HISTORY_FILE, encoding="utf-8"))[0]["page"] == "Regression.LoginTest"


# ── Allure ────────────────────────────────────────────────────────────────────
def read_results(workspace):
    folder = workspace / "FitNesseRoot" / "files" / "testResults" / "allure-results"
    return [json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*-result.json")]


def test_allure_result_exists_after_every_step_without_closing(workspace):
    helper = allure_helper.AllureHelper.for_test("LoginTest", "UI Tests")
    helper.add_step("Navigate to http://x", "passed", 30)
    [result] = read_results(workspace)
    assert result["status"] == "passed" and [s["name"] for s in result["steps"]] == ["Navigate to http://x"]
    helper.add_step("Click login", "passed", 20)
    [result] = read_results(workspace)
    assert [s["name"] for s in result["steps"]] == ["Navigate to http://x", "Click login"]


def test_failed_step_keeps_recording_later_steps(workspace):
    helper = allure_helper.AllureHelper.for_test("LoginTest", "UI Tests")
    helper.set_failed("Click failed - timeout")
    helper.add_step("FAILED: Click login", "failed", 1, message="Click failed - timeout")
    helper.add_step("Take screenshot", "passed")
    [result] = read_results(workspace)
    assert result["status"] == "failed" and len(result["steps"]) == 2
    assert result["statusDetails"]["message"] == "Click failed - timeout"
    assert result["steps"][0]["statusDetails"]["message"] == "Click failed - timeout"


def test_first_failure_message_is_kept(workspace):
    helper = allure_helper.AllureHelper.for_test("LoginTest", "UI Tests")
    helper.set_failed("first")
    helper.set_failed("second")
    assert helper.error_message == "first"


def test_http_steps_share_one_result_with_attachments_inside_the_step(workspace, monkeypatch):
    monkeypatch.setenv("FITNESSE_PAGE_NAME", "GetUsers")
    monkeypatch.setenv("FITNESSE_PAGE_PATH", "FrontPage")
    allure_helper.record_http_step("GET x", "GET http://api/users -> 200 (120 ms)", True, 120,
                                   [("Request Headers", "{}", "application/json", "json"),
                                    ("Response Body", '{"total": 1}', "application/json", "json")])
    allure_helper.record_http_step("GET x", "GET http://api/users/9 -> 404 (80 ms)", False, 80,
                                   [("Response Body", "{}", "application/json", "json")], "Expected status [200] but got 404")
    [result] = read_results(workspace)
    assert result["name"] == "GetUsers" and result["status"] == "failed"
    assert [s["status"] for s in result["steps"]] == ["passed", "failed"]
    assert [a["name"] for a in result["steps"][0]["attachments"]] == ["Request Headers", "Response Body"]
    assert result["steps"][1]["statusDetails"]["message"].startswith("Expected status")
    assert result["attachments"] == []
    for step in result["steps"]:
        for attachment in step["attachments"]:
            assert os.path.isfile(os.path.join(allure_helper.ALLURE_RESULTS_DIR, attachment["source"]))


def test_parent_suite_page_creates_no_http_result(workspace, monkeypatch):
    monkeypatch.setenv("FITNESSE_PAGE_NAME", "Regression")
    monkeypatch.setenv("FITNESSE_PAGE_PATH", "FrontPage.Regression")
    allure_helper.record_http_step("GET x", "GET /", True, 1, [])
    assert read_results(workspace) == []


# ── ENV variables in steps ────────────────────────────────────────────────────
def test_environment_variables_resolve_from_the_variable_page(tmp_path, monkeypatch):
    folder = tmp_path / "FitNesseRoot" / "VariablePage"
    folder.mkdir(parents=True)
    (folder / "content.txt").write_text(
        "!define API_BASE_URL {https://api.test}\n!define UI_BASE_URL {http://localhost:8080/}\n", encoding="utf-8")
    monkeypatch.setattr(ui_flow, "_WORKSPACE_DIR", str(tmp_path))
    assert ui_flow.substitute_variables("${UI_BASE_URL}", {}) == "http://localhost:8080/"
    assert ui_flow.substitute_variables("${UI_Base_URL}home", {}) == "http://localhost:8080/home"   # any capitalisation
    assert ui_flow.substitute_variables("${api_base_url}/users", {}) == "https://api.test/users"
    assert ui_flow.substitute_variables("${other}", {}) == "${other}"
    assert ui_flow.substitute_variables("${UI_BASE_URL}", {"UI_BASE_URL": "http://mine"}) == "http://mine"  # step variables win


def test_fitnesse_rewritten_undefined_variable_is_restored(tmp_path, monkeypatch):
    folder = tmp_path / "FitNesseRoot" / "VariablePage"
    folder.mkdir(parents=True)
    (folder / "content.txt").write_text("!define UI_BASE_URL {http://localhost:8080/}", encoding="utf-8")
    monkeypatch.setattr(ui_flow, "_WORKSPACE_DIR", str(tmp_path))
    # FitNesse turns ${UI_Base_URL} (not defined with that capitalisation) into this text before Slim sees it
    assert ui_flow.substitute_variables("undefined variable: UI_Base_URL", {}) == "http://localhost:8080/"
    assert ui_flow.substitute_variables('<span class="undefined">undefined variable: UI_Base_URL</span>/home', {}) == "http://localhost:8080/home"
    assert ui_flow.substitute_variables("${UI_BASE_URL}/home", {}) == "http://localhost:8080/home"


def test_undefined_environment_variable_stays_visible(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_flow, "_WORKSPACE_DIR", str(tmp_path))
    assert ui_flow.substitute_variables("${UI_BASE_URL}", {}) == "${UI_BASE_URL}"
