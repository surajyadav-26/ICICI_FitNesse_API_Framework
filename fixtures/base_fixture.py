import html
import json
import time
import base64
from typing import List, Optional
import requests
from .auth_fixture import AuthFixture
from .json_utils import extract_json_field
from core.logger import logger, log_request, log_response

class BaseRequestFixture:
    """
    Shared engine inherited by Get/Post/Put/Patch/Delete fixtures.
    Handles: auth injection, timing, status checks, JSONPath lookups, logging.
    """
    def __init__(self) -> None:
        self._url: str = ""
        self._body_json: str = ""
        self._key: str = ""
        self._expected_codes: List[int] = []
        self._basic_auth_header: str = ""
        self._custom_headers: dict = {}
        self._ssl_verify: bool = True
        self._response_headers: dict = {}
        self._header_lookup_key: str = ""
        self._file_path: str = ""

        self._executed: bool = False
        self._actual_status_code: int = 0
        self._response_body: str = ""
        self._response_time_ms: int = 0
        self._response_body_json: dict = {}

    # Setters (Supporting both camelCase and snake_case natively for compatibility!)
    def set_url(self, url: str) -> None:
        self._url = url
    def setUrl(self, url: str) -> None:
        self.set_url(url)

    def set_body_json(self, body_json: str) -> None:
        self._body_json = body_json
    def setBodyJson(self, body_json: str) -> None:
        self.set_body_json(body_json)

    def set_key(self, key: str) -> None:
        self._key = key
    def setKey(self, key: str) -> None:
        self.set_key(key)

    def set_basic_auth(self, credentials: str) -> None:
        """
        Sets Basic Authentication header.
        Format inside FitNesse cell: username:password (e.g. suraj:Sur$0402)
        """
        unescaped_cred = html.unescape(credentials)
        if ":" in unescaped_cred:
            user, pwd = unescaped_cred.split(":", 1)
            encoded = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("utf-8")
            self._basic_auth_header = f"Basic {encoded}"
        else:
            logger.warning(f"Invalid basic auth format: '{credentials}'")
    def setBasicAuth(self, credentials: str) -> None:
        self.set_basic_auth(credentials)

    def set_status_codes(self, codes: str) -> None:
        self._expected_codes = []
        for code in codes.split(","):
            try:
                self._expected_codes.append(int(code.strip()))
            except ValueError:
                logger.warning(f"Invalid status code: {code}")
    def setStatusCodes(self, codes: str) -> None:
        self.set_status_codes(codes)

    def _make_request(self, method: str) -> bool:
        try:
            headers: dict = {}
            
            # Use Basic Auth if specified, otherwise fall back to cached Bearer Token
            if self._basic_auth_header:
                headers["Authorization"] = self._basic_auth_header
            else:
                token = AuthFixture.get_stored_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"

            # Inject custom headers if set
            headers.update(self._custom_headers)

            unescaped_body = html.unescape(self._body_json)
            
            # Log Request
            log_request(method, self._url, headers=headers, payload=unescaped_body or None)

            start = time.perf_counter()
            
            # Perform POST / PUT / PATCH natively with dictionary payloads if available!
            if self._file_path:
                try:
                    # Open file and request
                    with open(self._file_path, 'rb') as f:
                        files = {'file': f}
                        response = requests.request(method, self._url, files=files, headers=headers, timeout=15, verify=self._ssl_verify)
                except Exception as e:
                    logger.error(f"[Upload] Failed to open/send file {self._file_path}: {e}")
                    raise e
            elif method in ("POST", "PUT", "PATCH") and unescaped_body:
                try:
                    json_payload = json.loads(unescaped_body)
                    response = requests.request(method, self._url, json=json_payload, headers=headers, timeout=15, verify=self._ssl_verify)
                except Exception:
                    response = requests.request(method, self._url, data=unescaped_body.encode('utf-8'), headers=headers, timeout=15, verify=self._ssl_verify)
            else:
                response = requests.request(method, self._url, headers=headers, timeout=15, verify=self._ssl_verify)

            # Log equivalent cURL command for developers
            try:
                curl_cmd = self._generate_curl_command(method, headers)
                logger.info(f"[cURL Replicator] {curl_cmd}")
            except Exception as e:
                logger.debug(f"Failed to generate cURL command: {e}")

            self._response_headers = dict(response.headers)
            self._response_time_ms = int((time.perf_counter() - start) * 1000)
            self._actual_status_code = response.status_code
            self._response_body = response.text

            try:
                self._response_body_json = response.json()
            except Exception:
                self._response_body_json = {}

            # Log Response
            log_response(self._actual_status_code, self._response_body, dict(response.headers))
            logger.info(f"[{method}] {self._url} -> {self._actual_status_code} ({self._response_time_ms}ms)")
            
            # Calculate assertion counts
            right_count = 0
            wrong_count = 0
            if self._expected_codes:
                if self._actual_status_code in self._expected_codes:
                    right_count = 1
                else:
                    wrong_count = 1
            else:
                if 200 <= self._actual_status_code < 400 or self._actual_status_code == 204:
                    right_count = 1
                else:
                    wrong_count = 1

            # Auto-generate our 3rd-party corporate HTML report dynamically on the fly!
            try:
                from core.report_generator import add_record
                add_record({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "method": method,
                    "url": self._url,
                    "status_code": self._actual_status_code,
                    "response_time_ms": self._response_time_ms,
                    "curl": self._generate_curl_command(method, headers),
                    "request_body": unescaped_body or "",
                    "response_body": self._response_body or "",
                    "right": right_count,
                    "wrong": wrong_count,
                    "ignored": 0,
                    "exceptions": 0
                })
            except Exception as e:
                logger.error(f"[Report] Failed to trigger report generator: {e}")
            
            self._executed = True
            return True

        except Exception as e:
            logger.error(f"[{method}] Unexpected exception [{self._url}]: {str(e)}")
            # Log as exception to the report generator!
            try:
                from core.report_generator import add_record
                add_record({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "method": method,
                    "url": self._url,
                    "status_code": 0,
                    "response_time_ms": 0,
                    "curl": self._generate_curl_command(method, self._custom_headers) if hasattr(self, '_custom_headers') else f"curl -X {method} \"{self._url}\"",
                    "request_body": self._body_json or "",
                    "response_body": f"exception: {str(e)}",
                    "right": 0,
                    "wrong": 0,
                    "ignored": 0,
                    "exceptions": 1
                })
            except Exception:
                pass
            return False

    def executed(self) -> bool:
        return self._executed

    def actual_status_code(self) -> int:
        return self._actual_status_code

    def status_code(self) -> str:
        """Returns the actual status code as a string (supports statusCode?)."""
        return str(self._actual_status_code)

    def response_body(self) -> str:
        try:
            json_data = json.loads(self._response_body)
            pretty_json = json.dumps(json_data, indent=2)
            return f"\n{{{{\n{pretty_json}\n}}}}\n"
        except Exception:
            return f"\n{{{{\n{self._response_body}\n}}}}\n"

    def response_time(self) -> int:
        return self._response_time_ms

    def status_codes(self) -> str:
        if not self._expected_codes:
            return str(self._actual_status_code)
        if self._actual_status_code in self._expected_codes:
            return str(self._actual_status_code)
        return f"{self._actual_status_code} (expected: {self._expected_codes})"

    def response_field(self) -> str:
        body_stripped = self._response_body.strip()
        if body_stripped.startswith("<") and body_stripped.endswith(">"):
            from .json_utils import extract_xml_field
            return extract_xml_field(self._response_body, self._key)
        return extract_json_field(self._response_body_json, self._key)

    def json_value(self) -> str:
        return self.response_field()

    def set_header(self, name: str, value: str) -> None:
        """Sets a custom HTTP header for the request."""
        self._custom_headers[name] = html.unescape(value)

    def setHeader(self, name: str, value: str) -> None:
        self.set_header(name, value)

    def set_ssl_verify(self, verify: str) -> None:
        """Enables/Disables SSL Certificate verification. Set to 'false' to bypass self-signed SSL warnings in UAT."""
        self._ssl_verify = verify.strip().lower() != "false"

    def setSslVerify(self, verify: str) -> None:
        self.set_ssl_verify(verify)

    def set_header_lookup(self, key: str) -> None:
        """Sets the header key to look up in the response headers (e.g. 'Content-Type')."""
        self._header_lookup_key = key

    def setHeaderLookup(self, key: str) -> None:
        self.set_header_lookup(key)

    def response_header(self) -> str:
        """Returns the value of the looked-up response header, or 'header not found'."""
        if not self._header_lookup_key:
            return "no header key set"
        return self._response_headers.get(self._header_lookup_key, "header not found")

    def responseHeader(self) -> str:
        return self.response_header()

    def set_file_path(self, path: str) -> None:
        """Sets the file path to upload for multipart/form-data."""
        self._file_path = html.unescape(path)

    def setFilePath(self, path: str) -> None:
        self.set_file_path(path)

    def _generate_curl_command(self, method: str, headers: dict) -> str:
        """Generates equivalent cURL command for debugging."""
        curl = f"curl -s -X {method} \"{self._url}\""
        for k, v in headers.items():
            curl += f" -H \"{k}: {v}\""
        if self._file_path:
            curl += f" -F \"file=@{self._file_path}\""
        elif method in ("POST", "PUT", "PATCH") and self._body_json:
            body = html.unescape(self._body_json).replace('"', '\\"')
            curl += f" -d \"{body}\""
        return curl
