"""Small local file-backed user store for the FitNesse UI demo."""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
FITNESSE_USERS_FILE = os.path.join(BASE_DIR, "runtime", "fitnesse-passwords.txt")
HOST = "0.0.0.0"
PORT = 8090

# Memory-only Queue to dynamically source FitNesse page names with ZERO table modifications!
ACTIVE_RUNS_QUEUE = []


def read_users():
    with open(USERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def write_users(users):
    temporary_file = USERS_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=2)
        file.write("\n")
    os.replace(temporary_file, USERS_FILE)


def sync_fitnesse_password_file(users=None):
    """Generate FitNesse's temporary username:password adapter from JSON."""
    users = users or read_users()
    os.makedirs(os.path.dirname(FITNESSE_USERS_FILE), exist_ok=True)
    temporary_file = FITNESSE_USERS_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        for username, user in sorted(users.items()):
            file.write(f"{username}:{user['password']}\n")
    os.replace(temporary_file, FITNESSE_USERS_FILE)


def update_env_file(payload):
    """
    Dynamically parses the local .env file.
    Preserves all framework-level configurations intact.
    Completely synchronizes and mirrors environment-wise URLs on disk
    to match exactly what the user added, edited, or deleted in the UI.
    """
    env_file = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_file):
        env_file = os.path.join(BASE_DIR, ".env.example")
        if not os.path.exists(env_file):
            return
            
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    environments = payload.get("environments", {})
    runtime_config = payload.get("config", {})
    
    preserved_lines = []
    
    # 1. Process and filter existing .env lines
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            # Strip out older dynamic sync comments or section headers to avoid duplicates
            if "DYNAMICALLY SYNCHRONIZED" not in line_stripped and "from UI" not in line_stripped:
                preserved_lines.append(line)
            continue
            
        if "=" in line_stripped:
            key, val = line_stripped.split("=", 1)
            key = key.strip()
            
            # Check if this key is an environment-wise URL
            is_env_url = False
            if key.endswith("_API_URL") or key.endswith("_BASE_URL") or key.endswith("_UI_URL") or (key.endswith("_URL") and "UI" not in key and "TOKEN" not in key):
                is_env_url = True
                
            if is_env_url:
                continue  # Discard old environment-specific URL lines completely!
                
            # Update runtime configs on the fly if present in payload
            if key == "UI_BROWSER" and "browser" in runtime_config:
                preserved_lines.append(f"UI_BROWSER={runtime_config['browser']}\n")
            elif key == "UI_HEADLESS" and "headless" in runtime_config:
                preserved_lines.append(f"UI_HEADLESS={runtime_config['headless']}\n")
            elif key == "MAX_RETRIES" and "retries" in runtime_config:
                preserved_lines.append(f"MAX_RETRIES={runtime_config['retries']}\n")
            elif key == "RETRY_DELAY" and "delay" in runtime_config:
                preserved_lines.append(f"RETRY_DELAY={runtime_config['delay']}\n")
            elif key == "UI_WORKERS" and "workers" in runtime_config:
                preserved_lines.append(f"UI_WORKERS={runtime_config['workers']}\n")
            else:
                preserved_lines.append(line)
        else:
            preserved_lines.append(line)
            
    # 2. Compile exactly the active environments list from the UI
    new_env_lines = []
    new_env_lines.append("\n# ═════════════════════════════════════════════════════════════════════\n")
    new_env_lines.append("# DYNAMICALLY SYNCHRONIZED ENVIRONMENTS FROM THE UI\n")
    new_env_lines.append("# ═════════════════════════════════════════════════════════════════════\n")
    
    for env_name, urls in sorted(environments.items()):
        env_upper = env_name.upper().replace(" ", "_")
        api_url = urls.get("api", "").strip()
        ui_url = urls.get("ui", "").strip()
        
        new_env_lines.append(f"{env_upper}_API_URL={api_url}\n")
        new_env_lines.append(f"{env_upper}_UI_URL={ui_url}\n")
        
    final_lines = preserved_lines + new_env_lines
    
    # 3. Write mirrored results straight to disk
    temporary_file = env_file + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    os.replace(temporary_file, env_file)


class UserStoreHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        if self.path == "/users":
            try:
                self._send_json(200, read_users())
            except (OSError, json.JSONDecodeError) as error:
                self._send_json(500, {"error": str(error)})
            return
            
        elif self.path == "/serve-allure":
            try:
                import subprocess
                import shutil
                results_path = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")
                report_path = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-report")
                os.makedirs(results_path, exist_ok=True)
                
                # Write Environment Metadata to populate the Allure Environment widget!
                env_path = os.path.join(results_path, "environment.properties")
                with open(env_path, "w", encoding="utf-8") as ef:
                    ef.write("Browser=Chromium (Playwright)\n")
                    ef.write("Headless=Headed (Live Debug Supported)\n")
                    ef.write("Platform=Windows 10/11\n")
                    ef.write("Framework=Python-native Playwright Symmetrical Automation\n")
                    ef.write("Active_URL=https://dummyjson.com / https://www.saucedemo.com\n")
                    
                # Write Executor Metadata to populate the Allure Executors widget beautifully (removing 'Unknown')!
                exec_path = os.path.join(results_path, "executor.json")
                with open(exec_path, "w", encoding="utf-8") as exf:
                    json.dump({
                        "name": "Nirikshan Test Automation Runner",
                        "type": "fitnesse",
                        "url": "http://localhost:8080",
                        "buildOrder": 1,
                        "buildName": "Local Run",
                        "buildUrl": "http://localhost:8080/FrontPage"
                    }, exf, indent=2)
                
                # Symmetrical Allure History Copier (Natively preserves Trend and History graphs!)
                prev_history_path = os.path.join(report_path, "history")
                dest_history_path = os.path.join(results_path, "history")
                if os.path.exists(prev_history_path):
                    try:
                        # Copy previous history directory to allure-results before generating
                        shutil.copytree(prev_history_path, dest_history_path, dirs_exist_ok=True)
                    except Exception as hist_err:
                        pass
                
                # Compile the results permanently as a static folder inside your project!
                try:
                    # Generate the permanent report
                    gen_proc = subprocess.run(f"allure generate \"{results_path}\" -o \"{report_path}\" --clean", shell=True, capture_output=True, text=True)
                    
                    # Inject a native script inside the compiled HTML to force Allure to load in its premium Dark Mode theme!
                    index_html_path = os.path.join(report_path, "index.html")
                    if os.path.exists(index_html_path):
                        with open(index_html_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                        if "allure-theme" not in html_content:
                            dark_script = '<script>localStorage.setItem("allure-theme", "dark"); localStorage.setItem("allure-playbook-theme", "dark"); if(!document.body.classList.contains("theme_dark")){document.body.classList.add("theme_dark");}</script>'
                            html_content = html_content.replace("</head>", f"{dark_script}</head>")
                            with open(index_html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                                
                    self._send_json(200, {"served": True, "url": "http://localhost:8090/allure/index.html"})
                except FileNotFoundError:
                    self._send_json(400, {"error": "Allure CLI command was not found in your system PATH! Make sure Allure is installed."})
            except Exception as error:
                self._send_json(500, {"error": str(error)})
            return

        elif self.path.startswith("/allure"):
            try:
                # Strip query parameters (e.g. "?t=1273918237") to bypass FitNesse blocks and load files cleanly!
                clean_path = self.path.split("?")[0]
                
                # Resolve the physical file path on disk
                relative_file_path = clean_path.replace("/allure", "").lstrip("/")
                if not relative_file_path or relative_file_path == "":
                    relative_file_path = "index.html"
                
                file_path = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-report", relative_file_path)
                
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    # Determine MIME type
                    content_type = "text/plain"
                    if file_path.endswith(".html"):
                        content_type = "text/html"
                    elif file_path.endswith(".js"):
                        content_type = "application/javascript"
                    elif file_path.endswith(".css"):
                        content_type = "text/css"
                    elif file_path.endswith(".json"):
                        content_type = "application/json"
                    elif file_path.endswith(".png"):
                        content_type = "image/png"
                    elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                        content_type = "image/jpeg"
                    elif file_path.endswith(".svg"):
                        content_type = "image/svg+xml"
                    
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    # Force Cache-Busting to prevent browser from caching old Allure report results!
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.end_headers()
                    
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self._send_json(404, {"error": f"File not found: {relative_file_path}"})
            except Exception as error:
                self._send_json(500, {"error": str(error)})
            return

        elif self.path == "/pop-run":
            try:
                page_name = "UI Test Run"
                if ACTIVE_RUNS_QUEUE:
                    page_name = ACTIVE_RUNS_QUEUE.pop()  # Get and erase so it is one-time use!
                self._send_json(200, {"page_name": page_name})
            except Exception as error:
                self._send_json(400, {"error": str(error)})
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/users":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                users = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(users, dict) or not users:
                    raise ValueError("At least one user is required")
                if not any(user.get("role") == "admin" for user in users.values()):
                    raise ValueError("At least one Admin user must remain")
                write_users(users)
                sync_fitnesse_password_file(users)
                self._send_json(200, {"saved": True})
            except (ValueError, json.JSONDecodeError, OSError) as error:
                self._send_json(400, {"error": str(error)})
            return
            
        elif self.path == "/environments":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict) or not payload:
                    raise ValueError("At least one configuration payload is required")
                update_env_file(payload)
                self._send_json(200, {"saved": True})
            except Exception as error:
                self._send_json(400, {"error": str(error)})
            return
            
        elif self.path == "/live-debug":
            try:
                debug_file = os.path.join(BASE_DIR, "runtime", "live-debug.txt")
                os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write("true")
                self._send_json(200, {"debug": True})
            except Exception as error:
                self._send_json(400, {"error": str(error)})
            return
            
        elif self.path == "/clear-allure":
            try:
                import glob
                import shutil
                results_path = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")
                if os.path.exists(results_path):
                    # Delete all files inside allure-results cleanly to avoid duplicate history logs
                    files = glob.glob(os.path.join(results_path, "*"))
                    for file_path in files:
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except Exception:
                            pass
                            
                report_path = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-report")
                if os.path.exists(report_path):
                    # Delete compiled allure-report files but EXPLICITLY preserve the 'history' folder for Trend graphs!
                    files = glob.glob(os.path.join(report_path, "*"))
                    for file_path in files:
                        try:
                            # Skip deleting the history directory to preserve past execution runs' Trends!
                            if os.path.isdir(file_path) and os.path.basename(file_path).lower() == "history":
                                continue
                                
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception:
                            pass
                            
                self._send_json(200, {"cleared": True})
            except Exception as error:
                self._send_json(400, {"error": str(error)})
            return

        elif self.path == "/register-run":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                page_path = payload.get("page", "")
                if page_path:
                    page_name = page_path.split(".")[-1].split("/")[-1]
                    ACTIVE_RUNS_QUEUE.append(page_name)
                    # Limit queue size to avoid bloat
                    if len(ACTIVE_RUNS_QUEUE) > 10:
                        ACTIVE_RUNS_QUEUE.pop(0)
                self._send_json(200, {"registered": True})
            except Exception as error:
                self._send_json(400, {"error": str(error)})
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format_string, *args):
        return


if __name__ == "__main__":
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--sync":
        sync_fitnesse_password_file()
        raise SystemExit(0)
    sync_fitnesse_password_file()
    ThreadingHTTPServer((HOST, PORT), UserStoreHandler).serve_forever()
