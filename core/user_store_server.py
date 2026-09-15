"""Small local file-backed user store for the FitNesse UI demo."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
FITNESSE_USERS_FILE = os.path.join(BASE_DIR, "runtime", "fitnesse-passwords.txt")
HOST = "127.0.0.1"
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
        if self.path != "/users":
            self._send_json(404, {"error": "Not found"})
            return
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

    def log_message(self, format_string, *args):
        return


if __name__ == "__main__":
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--sync":
        sync_fitnesse_password_file()
        raise SystemExit(0)
    sync_fitnesse_password_file()
    ThreadingHTTPServer((HOST, PORT), UserStoreHandler).serve_forever()
