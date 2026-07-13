import html
import json
import time
from typing import Optional
import requests
from .auth_fixture import AuthFixture
from .oauth2_fixture import OAuth2Fixture
from .json_utils import extract_json_field
from core.logger import logger, log_request, log_response

class GraphQLFixture:
    """
    Python SLIM Decision Table fixture for GraphQL API testing.
    Supports queries, mutations, and variables.
    """
    def __init__(self) -> None:
        self._endpoint: str = ""
        self._query: str = ""
        self._variables: str = "{}"
        self._operation_name: str = ""
        self._key: str = ""
        self._ssl_verify: bool = True
        self._timeout: int = 15
        self._use_oauth2: bool = False
        
        self._executed: bool = False
        self._actual_status_code: int = 0
        self._response_body: str = ""
        self._response_time_ms: int = 0
        self._response_body_json: dict = {}
        self._errors: list = []

    # Setters
    def set_endpoint(self, endpoint: str) -> None:
        self._endpoint = html.unescape(endpoint).strip() if endpoint else ""
        if not self._endpoint:
            logger.warning("[GraphQL] Endpoint is empty. Request will fail.")
        elif not (self._endpoint.startswith("http://") or self._endpoint.startswith("https://")):
            logger.warning(f"[GraphQL] Endpoint should start with http:// or https://: {self._endpoint}")
    def setEndpoint(self, endpoint: str) -> None:
        self.set_endpoint(endpoint)

    def set_query(self, query: str) -> None:
        """Sets the GraphQL query or mutation"""
        self._query = html.unescape(query).strip()
    def setQuery(self, query: str) -> None:
        self.set_query(query)

    def set_variables(self, variables: str) -> None:
        """Sets GraphQL variables as JSON string"""
        self._variables = html.unescape(variables).strip()
    def setVariables(self, variables: str) -> None:
        self.set_variables(variables)

    def set_operation_name(self, name: str) -> None:
        """Sets the operation name (optional)"""
        self._operation_name = html.unescape(name).strip()
    def setOperationName(self, name: str) -> None:
        self.set_operation_name(name)

    def set_key(self, key: str) -> None:
        """Sets JSONPath key for extracting specific field from response"""
        self._key = html.unescape(key).strip()
    def setKey(self, key: str) -> None:
        self.set_key(key)

    def set_ssl_verify(self, verify: str) -> None:
        """Enables/Disables SSL Certificate verification. Set to 'false' to bypass self-signed SSL warnings."""
        self._ssl_verify = verify.strip().lower() != "false"
    def setSslVerify(self, verify: str) -> None:
        self.set_ssl_verify(verify)

    def set_timeout(self, seconds: str) -> None:
        """Sets request timeout in seconds. Default is 15 seconds."""
        try:
            self._timeout = int(seconds)
        except ValueError:
            logger.warning(f"[GraphQL] Invalid timeout value: '{seconds}', using default 15s")
            self._timeout = 15
    def setTimeout(self, seconds: str) -> None:
        self.set_timeout(seconds)

    def set_use_oauth2(self, use: str) -> None:
        """Set to 'true' to use OAuth2 token instead of bearer token from AuthFixture"""
        self._use_oauth2 = use.strip().lower() == "true"
    def setUseOAuth2(self, use: str) -> None:
        self.set_use_oauth2(use)

    # Execution
    def execute(self) -> bool:
        """Executes the GraphQL query/mutation"""
        # Validate endpoint
        if not self._endpoint:
            logger.error("[GraphQL] Cannot execute: Endpoint is empty")
            return False
        if not (self._endpoint.startswith("http://") or self._endpoint.startswith("https://")):
            logger.error(f"[GraphQL] Cannot execute: Invalid endpoint format: {self._endpoint}")
            return False

        try:
            # Build GraphQL request payload
            payload = {
                "query": self._query
            }

            # Add variables if provided
            if self._variables and self._variables != "{}":
                try:
                    variables_dict = json.loads(self._variables)
                    payload["variables"] = variables_dict
                except json.JSONDecodeError as e:
                    logger.error(f"[GraphQL] Invalid variables JSON: {e}")
                    return False

            # Add operation name if provided
            if self._operation_name:
                payload["operationName"] = self._operation_name

            # Build headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Add authentication token
            if self._use_oauth2:
                token = OAuth2Fixture.get_stored_access_token()
                token_type = OAuth2Fixture.get_token_type()
                if token:
                    headers["Authorization"] = f"{token_type} {token}"
                    logger.debug("[GraphQL] Using OAuth2 token for authentication")
            else:
                token = AuthFixture.get_stored_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    logger.debug("[GraphQL] Using Bearer token for authentication")

            # Log Request
            log_request("POST", self._endpoint, headers=headers, payload=payload)

            start = time.perf_counter()
            response = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout,
                verify=self._ssl_verify
            )
            self._response_time_ms = int((time.perf_counter() - start) * 1000)
            self._actual_status_code = response.status_code
            self._response_body = response.text

            try:
                self._response_body_json = response.json()
                # Extract GraphQL errors if present
                self._errors = self._response_body_json.get("errors", [])
            except Exception:
                self._response_body_json = {}
                self._errors = []

            # Log Response
            log_response(self._actual_status_code, self._response_body, dict(response.headers))
            logger.info(f"[GraphQL] {self._endpoint} -> {self._actual_status_code} ({self._response_time_ms}ms)")

            if self._errors:
                logger.warning(f"[GraphQL] Response contains errors: {self._errors}")

            self._executed = True
            return True

        except requests.exceptions.Timeout:
            logger.error(f"[GraphQL] Timeout [{self._endpoint}]")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[GraphQL] Connection error [{self._endpoint}]: {e}")
            return False
        except Exception as e:
            logger.error(f"[GraphQL] Exception: {e}")
            return False

    # Getters
    def executed(self) -> bool:
        return self._executed

    def actual_status_code(self) -> int:
        return self._actual_status_code

    def status_code(self) -> str:
        return str(self._actual_status_code)

    def response_time(self) -> int:
        return self._response_time_ms

    def response_body(self) -> str:
        try:
            pretty = json.dumps(self._response_body_json, indent=2)
            return f"\n{{\n{pretty}\n}}\n"
        except Exception:
            return f"\n{{\n{self._response_body}\n}}\n"

    def has_errors(self) -> bool:
        """Returns true if the GraphQL response contains errors"""
        return len(self._errors) > 0

    def errors(self) -> str:
        """Returns GraphQL errors as JSON string"""
        if not self._errors:
            return "[]"
        try:
            return json.dumps(self._errors, indent=2)
        except Exception:
            return str(self._errors)

    def data(self) -> str:
        """Returns the data field from GraphQL response"""
        if "data" not in self._response_body_json:
            return "{}"
        try:
            return json.dumps(self._response_body_json["data"], indent=2)
        except Exception:
            return str(self._response_body_json.get("data", {}))

    def json_value(self) -> str:
        """Extracts value from data using the configured key (JSONPath style)"""
        if not self._key:
            return "no key set"
        
        # GraphQL responses are in data field
        data = self._response_body_json.get("data", {})
        if not data:
            return "no data in response"
        
        return extract_json_field(data, self._key)

    def field_value(self) -> str:
        """Alias for json_value for consistency"""
        return self.json_value()
