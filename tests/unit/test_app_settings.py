"""One place for the application name and the ports: a copy of the framework must need only .env edits."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADDRESS = re.compile(r"(localhost|127\.0\.0\.1|0\.0\.0\.0):\d{2,5}")


def code_files():
    for folder in ("core", "fixtures", "pages"):
        for base, _, files in os.walk(os.path.join(ROOT, folder)):
            if "__pycache__" in base:
                continue
            for name in files:
                if name.endswith(".py"):
                    yield os.path.join(base, name)
    yield os.path.join(ROOT, "FitNesseRoot", "PageHeader", "content.txt")


def test_no_code_or_header_names_a_port():
    found = []
    for path in code_files():
        for number, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "*", "/*")) or "Config." in line:
                continue
            if ADDRESS.search(line):
                found.append(f"{os.path.relpath(path, ROOT)}:{number}: {stripped[:100]}")
    assert found == [], "hardcoded address(es):\n" + "\n".join(found)


def run_config(env: dict) -> dict:
    """Reads the settings in a fresh interpreter, so the test never disturbs the modules already imported."""
    code = ("import json,warnings; warnings.simplefilter('ignore'); from core.config import Config as C;"
            "print(json.dumps([C.APP_NAME, C.APP_TITLE, C.fitnesse_url(), C.store_url(), C.store_url('127.0.0.1'), C.MOCK_SERVER_PORT]))")
    base = {key: value for key, value in os.environ.items()
            if key not in ("APP_NAME", "APP_TITLE", "FITNESSE_PORT", "STORE_PORT", "MOCK_SERVER_PORT")}
    base.update(env)
    base["PYTHONPATH"] = ROOT
    output = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=base, capture_output=True, text=True, timeout=60)
    assert output.returncode == 0, output.stderr
    return json.loads(output.stdout.strip().splitlines()[-1])


def test_name_and_ports_come_from_the_environment():
    values = run_config({"APP_NAME": "Acme Bank", "APP_TITLE": "Acme Bank Portal", "FITNESSE_PORT": "9080",
                         "STORE_PORT": "9090", "MOCK_SERVER_PORT": "9089"})
    assert values == ["Acme Bank", "Acme Bank Portal", "http://localhost:9080", "http://localhost:9090", "http://127.0.0.1:9090", 9089]


def test_the_header_reads_name_and_ports_from_app_config(tmp_path, monkeypatch):
    from core import user_store_server
    monkeypatch.setattr(user_store_server.Config, "APP_NAME", "Acme Bank")
    monkeypatch.setattr(user_store_server.Config, "APP_TITLE", "Acme Bank Portal")
    monkeypatch.setattr(user_store_server.Config, "FITNESSE_PORT", 9080)
    monkeypatch.setattr(user_store_server.Config, "STORE_PORT", 9090)
    monkeypatch.setattr(user_store_server, "APP_CONFIG_FILE", str(tmp_path / "files" / "app-config.json"))
    user_store_server.write_app_config()
    written = json.loads((tmp_path / "files" / "app-config.json").read_text(encoding="utf-8"))
    assert written == {"appName": "Acme Bank", "appTitle": "Acme Bank Portal", "fitnessePort": 9080, "storePort": 9090}


def test_reports_carry_the_application_name(tmp_path, monkeypatch):
    from core import accessibility_review
    monkeypatch.setattr(accessibility_review.Config, "APP_NAME", "Acme Bank")
    assert "Acme Bank - Accessibility Report" in accessibility_review.render_page(str(tmp_path))
