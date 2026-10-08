"""Keeps unit tests from writing into the real report, history and Allure folders."""
import pytest

from core import allure_helper, report_generator


@pytest.fixture(autouse=True)
def isolated_report_output(tmp_path_factory, monkeypatch):
    tmp_path = tmp_path_factory.mktemp("report-output")
    monkeypatch.setattr(report_generator, "HISTORY_FILE", str(tmp_path / "report_history.json"))
    monkeypatch.setattr(report_generator, "REPORT_FILE", str(tmp_path / "report.html"))
    monkeypatch.setattr(report_generator, "report_history", [])
    monkeypatch.setattr(report_generator, "trigger_delayed_report", lambda: None)
    monkeypatch.setattr(allure_helper, "ALLURE_RESULTS_DIR", str(tmp_path / "allure-results"))
    monkeypatch.setattr(allure_helper, "_ACTIVE_RESULTS", {})
