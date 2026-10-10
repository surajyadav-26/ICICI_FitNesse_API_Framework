import http.server
import socketserver
import threading
import json
from typing import Optional

class MockServerRequestHandler(http.server.BaseHTTPRequestHandler):
    """Background HTTP Request Handler matching reference endpoints."""
    
    def log_message(self, format, *args):
        # Suppress request logs to keep FitNesse terminal cleanly formatted
        pass

    def do_HEAD(self):
        if self.path in ["/api/users", "/api/aml/users", "/api/aml/health"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Response-Type", "MOCK_HEAD")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Allow", "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/login":
            self.send_json_response(200, {"token": "mock-token-abc123"})
        elif self.path in ["/api/users", "/api/aml/auth/token"]:
            self.send_json_response(201, {"id": 3, "name": "New User", "createdAt": "2026-06-16", "access_token": "mock-token-abc123"})
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_GET(self):
        if self.path in ["/api/users", "/api/aml/users"]:
            self.send_json_response(200, {"data": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]})
        elif self.path in ["/api/users/1", "/api/aml/users/1"]:
            self.send_json_response(200, {"data": {"id": 1, "name": "John", "email": "john@reqres.in"}})
        elif self.path in ["/api/users/99", "/api/aml/users/99"]:
            self.send_json_response(404, {"error": "User not found"})
        elif self.path == "/api/aml/transactions":
            self.send_json_response(200, {"transactions": [{"id": 101, "amount": 50000.0, "status": "APPROVED"}]})
        elif self.path == "/api/aml/alerts":
            self.send_json_response(200, {"alerts": [{"id": 501, "severity": "HIGH", "type": "SUSPICIOUS_TRANSACTION"}]})
        elif self.path == "/api/aml/health":
            self.send_json_response(200, {"status": "UP"})
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_PUT(self):
        if self.path in ["/api/users", "/api/aml/users"]:
            self.send_json_response(200, {"id": 1, "name": "Updated User", "updatedAt": "2026-06-16"})
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_PATCH(self):
        if self.path in ["/api/users", "/api/aml/users"]:
            self.send_json_response(200, {"id": 1, "job": "Updated Job", "updatedAt": "2026-06-16"})
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_DELETE(self):
        if self.path in ["/api/users", "/api/aml/users"]:
            self.send_response(204)
            self.end_headers()
        else:
            self.send_json_response(404, {"error": "Not found"})

    def send_json_response(self, status_code: int, data: dict) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class MockServerFixture:
    """
    Python SLIM Decision Table fixture to start/stop the embedded HTTP mock server.
    Allows running complete, offline/offline-CI test suites on port 8089.
    """
    _server: Optional[socketserver.TCPServer] = None
    _thread: Optional[threading.Thread] = None

    def start_server(self) -> bool:
        try:
            if MockServerFixture._server is not None:
                self.stop_server()

            # Enable socket address reuse to prevent address-already-in-use errors on restarts
            socketserver.TCPServer.allow_reuse_address = True
            MockServerFixture._server = socketserver.TCPServer(("127.0.0.1", 8089), MockServerRequestHandler)
            
            MockServerFixture._thread = threading.Thread(target=MockServerFixture._server.serve_forever, daemon=True)
            MockServerFixture._thread.start()
            print("[MockServer] Started at http://127.0.0.1:8089")
            return True
        except Exception as e:
            print(f"[MockServer] Start failed: {str(e)}")
            return False

    def stop_server(self) -> bool:
        try:
            if MockServerFixture._server is not None:
                MockServerFixture._server.shutdown()
                MockServerFixture._server.server_close()
                MockServerFixture._server = None
                MockServerFixture._thread = None
                print("[MockServer] Stopped.")
            return True
        except Exception as e:
            print(f"[MockServer] Stop failed: {str(e)}")
            return False
