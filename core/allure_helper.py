"""
Custom Allure JSON Results Compiler.
Symmetrically writes standard Allure-compatible JSON test results, steps,
and attachments directly to disk for both API and UI test runs.
"""
import json
import os
import time
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLURE_RESULTS_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")


class AllureHelper:
    """
    Lightweight, robust, lifecycle-free Allure JSON result builder.
    Bypasses Pytest dependencies to allow clean, concurrent SLiM runs.
    """

    def __init__(self, test_name: str, suite_name: str = "FitNesse Suite") -> None:
        self.test_name = str(test_name).strip()
        self.suite_name = str(suite_name).strip()
        self.start_time = int(time.time() * 1000)
        self.steps = []
        self.attachments = []
        self.status = "passed"  # Default: passed
        self.error_message = ""
        self.error_trace = ""
        self.test_uuid = str(uuid.uuid4())

    def add_step(self, name: str, status: str = "passed", duration_ms: int = 10) -> None:
        """Appends a completed sub-step to the test run results."""
        s_time = int(time.time() * 1000) - duration_ms
        self.steps.append({
            "name": str(name).strip(),
            "status": str(status).strip(),
            "stage": "finished",
            "start": s_time,
            "stop": s_time + duration_ms
        })

    def add_attachment(self, name: str, content: any, mime_type: str = "application/json", file_ext: str = "json") -> None:
        """Saves an attachment file on disk (like JSON payload or PNG bytes) and links it to the run."""
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
        attach_uuid = str(uuid.uuid4())
        attach_filename = f"{attach_uuid}-attachment.{file_ext}"
        attach_path = os.path.join(ALLURE_RESULTS_DIR, attach_filename)

        try:
            if isinstance(content, bytes):
                with open(attach_path, "wb") as f:
                    f.write(content)
            else:
                with open(attach_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

            self.attachments.append({
                "name": str(name).strip(),
                "source": attach_filename,
                "type": mime_type
            })
        except Exception as e:
            print(f"[ALLURE WARNING] Attaching {name} failed: {e}")

    def set_failed(self, message: str, traceback: str = "") -> None:
        """Flags the test run state as failed with details."""
        self.status = "failed"
        self.error_message = str(message).strip()
        self.error_trace = str(traceback).strip()

    def write_result(self) -> None:
        """Compiles and writes the final standard Allure JSON result to disk."""
        os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
        stop_time = int(time.time() * 1000)

        result = {
            "uuid": self.test_uuid,
            "historyId": str(uuid.uuid5(uuid.NAMESPACE_DNS, self.test_name)),
            "fullName": f"FitNesseRoot.FrontPage.{self.suite_name}.{self.test_name}",
            "labels": [
                {"name": "parentSuite", "value": "FitNesseRoot"},
                {"name": "suite", "value": self.suite_name},
                {"name": "subSuite", "value": self.test_name},
                {"name": "framework", "value": "Nirikshan Framework"},
                {"name": "language", "value": "python"}
            ],
            "name": self.test_name,
            "status": self.status,
            "stage": "finished",
            "steps": self.steps,
            "attachments": self.attachments,
            "start": self.start_time,
            "stop": stop_time
        }

        if self.status == "failed":
            result["statusDetails"] = {
                "message": self.error_message,
                "trace": self.error_trace
            }

        result_path = os.path.join(ALLURE_RESULTS_DIR, f"{self.test_uuid}-result.json")
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"[ALLURE WARNING] Writing result JSON failed: {e}")
