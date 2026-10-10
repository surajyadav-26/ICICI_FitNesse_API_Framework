import json

from core import allure_report


def test_allure_report_generation_preserves_history_and_uses_checked_command(tmp_path, monkeypatch):
    results_dir = tmp_path / "allure-results"
    report_dir = tmp_path / "allure-report"
    (report_dir / "history").mkdir(parents=True)
    (report_dir / "history" / "history.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(allure_report, "RESULTS_DIR", str(results_dir))
    monkeypatch.setattr(allure_report, "REPORT_DIR", str(report_dir))
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        output = report_dir / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("<html><head></head><body></body></html>", encoding="utf-8")

    monkeypatch.setattr(allure_report.subprocess, "run", run)

    assert allure_report.generate_allure_report("http://localhost:8080/Home") == str(report_dir)
    expected_command = ["allure", "generate", str(results_dir), "-o", str(report_dir), "--clean"]
    if allure_report.os.name == "nt":
        expected_command = ["cmd.exe", "/c", "allure.cmd", *expected_command[1:]]
    assert commands == [expected_command]
    assert (results_dir / "history" / "history.json").is_file()
    assert "Active_URL=http://localhost:8080/Home" in (results_dir / "environment.properties").read_text(encoding="utf-8")
    assert json.loads((results_dir / "executor.json").read_text(encoding="utf-8"))["type"] == "fitnesse"
    assert "allure-theme" in (report_dir / "index.html").read_text(encoding="utf-8")


def test_failure_categories_are_written_for_every_test_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(allure_report, "RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(allure_report, "REPORT_DIR", str(tmp_path / "report"))

    def run(command, **kwargs):
        (tmp_path / "report").mkdir(exist_ok=True)
        (tmp_path / "report" / "index.html").write_text("<head></head>", encoding="utf-8")

    monkeypatch.setattr(allure_report.subprocess, "run", run)
    allure_report.generate_allure_report()
    names = [item["name"] for item in json.loads((tmp_path / "results" / "categories.json").read_text(encoding="utf-8"))]
    assert names[:3] == ["Visual differences", "Accessibility violations", "API failures"] and "UI element problems" in names
