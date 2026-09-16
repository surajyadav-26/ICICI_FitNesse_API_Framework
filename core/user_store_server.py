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
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8080")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        if self.path != "/users":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            self._send_json(200, read_users())
        except (OSError, json.JSONDecodeError) as error:
            self._send_json(500, {"error": str(error)})

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
