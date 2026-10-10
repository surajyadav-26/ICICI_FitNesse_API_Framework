"""Build the static Allure report used by the FitNesse server and UI tables."""
import json
import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")
REPORT_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-report")


# Failure groups shown on Allure's Categories tab. The first matching category wins, so the specific ones come first.
CATEGORIES = [
    {"name": "Visual differences", "matchedStatuses": ["failed"], "messageRegex": ".*Visual (mismatch|error).*"},
    {"name": "Accessibility violations", "matchedStatuses": ["failed"], "messageRegex": ".*Accessibility WCAG.*"},
    {"name": "API failures", "matchedStatuses": ["failed", "broken"],
     "messageRegex": ".*(Expected status|-> not sent|-> no response|-> crashed|Authenticat).*"},
    {"name": "UI element problems", "matchedStatuses": ["failed", "broken"],
     "messageRegex": ".*(Timeout|not found|locator|not visible|Element).*"},
    {"name": "Other failures", "matchedStatuses": ["failed"]},
    {"name": "Test errors", "matchedStatuses": ["broken"]},
]


def generate_allure_report(active_url: str = "") -> str:
    """Generate the static report, retaining history and surfacing CLI errors."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "environment.properties"), "w", encoding="utf-8") as file:
        file.write("Browser=Chromium (Playwright)\n")
        file.write("Headless=Headed (Live Debug Supported)\n")
        file.write("Platform=Windows 10/11\n")
        file.write("Framework=Python-native Playwright Symmetrical Automation\n")
        file.write(f"Active_URL={active_url}\n")

    with open(os.path.join(RESULTS_DIR, "executor.json"), "w", encoding="utf-8") as file:
        json.dump({
            "name": "Nirikshan Test Automation Runner",
            "type": "fitnesse",
            "url": "http://localhost:8080",
            "buildOrder": 1,
            "buildName": "Local Run",
            "buildUrl": "http://localhost:8080/FrontPage",
        }, file, indent=2)

    with open(os.path.join(RESULTS_DIR, "categories.json"), "w", encoding="utf-8") as file:
        json.dump(CATEGORIES, file, indent=2)

    history_dir = os.path.join(REPORT_DIR, "history")
    if os.path.isdir(history_dir):
        shutil.copytree(history_dir, os.path.join(RESULTS_DIR, "history"), dirs_exist_ok=True)

    command = ["allure", "generate", RESULTS_DIR, "-o", REPORT_DIR, "--clean"]
    if os.name == "nt":
        command = ["cmd.exe", "/c", "allure.cmd", *command[1:]]
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )

    index_path = os.path.join(REPORT_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        if "allure-theme" not in html_content:
            dark_script = (
                '<script>localStorage.setItem("allure-theme", "dark"); '
                'localStorage.setItem("allure-playbook-theme", "dark"); '
                'if(!document.body.classList.contains("theme_dark"))'
                '{document.body.classList.add("theme_dark");}</script>'
            )
            with open(index_path, "w", encoding="utf-8") as file:
                file.write(html_content.replace("</head>", f"{dark_script}</head>"))
    return REPORT_DIR
