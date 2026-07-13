import html
import json
import base64
import requests
import time
from typing import Optional
from .json_utils import extract_json_field
from core.logger import logger, log_request, log_response

class OAuth2Fixture:
    """
    Python SLIM Decision Table fixture for OAuth2 authentication flows.
    Supports Client Credentials, Password Grant, and Authorization Code flows.
    Stores tokens statically for use by other fixtures.
    """
    _access_token = ""
    _refresh_token = ""
    _token_type = "Bearer"
    _expires_at = 0

    def __init__(self) -> None:
        self._token_url: str = ""
        self._client_id: str = ""
        self._client_secret: str = ""
        self._grant_type: str = "client_credentials"
        self._username: str = ""
        self._password: str = ""
        self._scope: str = ""
        self._authorization_code: str = ""
        self._redirect_uri: str = ""
        self._ssl_verify: bool = True
        self._timeout: int = 15
        
        self._actual_status_code: int = 0
        self._response_body: str = ""
        self._response_body_json: dict = {}
        self._response_time_ms: int = 0

    @classmethod
    def get_stored_access_token(cls) -> str:
        """Returns the currently stored access token."""
        return cls._access_token

    @classmethod
    def get_stored_refresh_token(cls) -> str:
        """Returns the currently stored refresh token."""
        return cls._refresh_token

    @classmethod
    def get_token_type(cls) -> str:
        """Returns the token type (usually 'Bearer')."""
        return cls._token_type

    @classmethod
    def is_token_expired(cls) -> bool:
        """Checks if the access token has expired."""
        if cls._expires_at == 0:
            return False
        return time.time() >= cls._expires_at

    @classmethod
    def clear_tokens(cls) -> None:
        """Clears all stored tokens."""
        cls._access_token = ""
        cls._refresh_token = ""
        cls._token_type = "Bearer"
        cls._expires_at = 0

    # Setters
    def set_token_url(self, token_url: str) -> None:
        self._token_url = html.unescape(token_url).strip() if token_url else ""
        if not self._token_url:
            logger.warning("[OAuth2] Token URL is empty. Authentication will fail.")
        elif not (self._token_url.startswith("http://") or self._token_url.startswith("https://")):
            logger.warning(f"[OAuth2] Token URL should start with http:// or https://: {self._token_url}")
    def setTokenUrl(self, token_url: str) -> None:
        self.set_token_url(token_url)

    def set_client_id(self, client_id: str) -> None:
        self._client_id = html.unescape(client_id).strip()
    def setClientId(self, client_id: str) -> None:
        self.set_client_id(client_id)

    def set_client_secret(self, client_secret: str) -> None:
        self._client_secret = html.unescape(client_secret).strip()
    def setClientSecret(self, client_secret: str) -> None:
        self.set_client_secret(client_secret)

    def set_grant_type(self, grant_type: str) -> None:
        """Grant type: client_credentials, password, authorization_code, refresh_token"""
        self._grant_type = html.unescape(grant_type).strip().lower()
    def setGrantType(self, grant_type: str) -> None:
        self.set_grant_type(grant_type)

    def set_username(self, username: str) -> None:
        """Username for password grant flow"""
        self._username = html.unescape(username).strip()
    def setUsername(self, username: str) -> None:
        self.set_username(username)

    def set_password(self, password: str) -> None:
        """Password for password grant flow"""
        self._password = html.unescape(password).strip()
    def setPassword(self, password: str) -> None:
        self.set_password(password)

    def set_scope(self, scope: str) -> None:
        """OAuth2 scope (space-separated)"""
        self._scope = html.unescape(scope).strip()
    def setScope(self, scope: str) -> None:
        self.set_scope(scope)

    def set_authorization_code(self, code: str) -> None:
        """Authorization code for authorization_code grant flow"""
        self._authorization_code = html.unescape(code).strip()
    def setAuthorizationCode(self, code: str) -> None:
        self.set_authorization_code(code)

    def set_redirect_uri(self, uri: str) -> None:
        """Redirect URI for authorization_code grant flow"""
        self._redirect_uri = html.unescape(uri).strip()
    def setRedirectUri(self, uri: str) -> None:
        self.set_redirect_uri(uri)

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
            logger.warning(f"[OAuth2] Invalid timeout value: '{seconds}', using default 15s")
            self._timeout = 15
    def setTimeout(self, seconds: str) -> None:
        self.set_timeout(seconds)

    # Execution
    def execute(self) -> bool:
        """Standard Decision Table execution alias."""
        return self.get_token()

    def get_token(self) -> bool:
        """Fetches OAuth2 token based on the configured grant type."""
        # Validate URL
        if not self._token_url:
            logger.error("[OAuth2] Cannot execute: Token URL is empty")
            return False
        if not (self._token_url.startswith("http://") or self._token_url.startswith("https://")):
            logger.error(f"[OAuth2] Cannot execute: Invalid URL format: {self._token_url}")
            return False

        try:
            # Build request payload based on grant type
            payload = {
                "grant_type": self._grant_type
            }

            if self._grant_type == "client_credentials":
                # Client Credentials Flow
                pass  # Only grant_type needed
            elif self._grant_type == "password":
                # Resource Owner Password Credentials Flow
                if not self._username or not self._password:
                    logger.error("[OAuth2] Username and password are required for password grant")
                    return False
                payload["username"] = self._username
                payload["password"] = self._password
            elif self._grant_type == "authorization_code":
                # Authorization Code Flow
                if not self._authorization_code:
                    logger.error("[OAuth2] Authorization code is required for authorization_code grant")
                    return False
                payload["code"] = self._authorization_code
                if self._redirect_uri:
                    payload["redirect_uri"] = self._redirect_uri
            elif self._grant_type == "refresh_token":
                # Refresh Token Flow
                if not OAuth2Fixture._refresh_token:
                    logger.error("[OAuth2] No refresh token available")
                    return False
                payload["refresh_token"] = OAuth2Fixture._refresh_token
            else:
                logger.error(f"[OAuth2] Unsupported grant type: {self._grant_type}")
                return False

            # Add optional scope
            if self._scope:
                payload["scope"] = self._scope

            # Build Basic Auth header with client credentials
            auth_header = None
            if self._client_id and self._client_secret:
                credentials = f"{self._client_id}:{self._client_secret}"
                encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
                auth_header = f"Basic {encoded}"

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            if auth_header:
                headers["Authorization"] = auth_header

            # Log Request
            log_request("POST", self._token_url, headers=headers, payload=payload)

            start = time.perf_counter()
            response = requests.post(
                self._token_url,
                data=payload,
                headers=headers,
                timeout=self._timeout,
                verify=self._ssl_verify
            )
            self._response_time_ms = int((time.perf_counter() - start) * 1000)
            self._actual_status_code = response.status_code
            self._response_body = response.text

            try:
                self._response_body_json = response.json()
            except Exception:
                self._response_body_json = {}

            # Log Response
            log_response(self._actual_status_code, self._response_body, dict(response.headers))

            if response.status_code not in [200, 201]:
                logger.error(f"[OAuth2] Failed with status {response.status_code}: {response.text}")
                return False

            # Extract tokens
            access_token = self._response_body_json.get("access_token", "")
            if not access_token:
                logger.error("[OAuth2] No access_token in response")
                return False

            # Store tokens
            OAuth2Fixture._access_token = access_token
            OAuth2Fixture._refresh_token = self._response_body_json.get("refresh_token", "")
            OAuth2Fixture._token_type = self._response_body_json.get("token_type", "Bearer")
            
            # Calculate expiration time
            expires_in = self._response_body_json.get("expires_in", 0)
            if expires_in:
                OAuth2Fixture._expires_at = time.time() + int(expires_in)
            
            logger.info(f"[OAuth2] Token acquired successfully (expires in {expires_in}s)")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"[OAuth2] Timeout [{self._token_url}]")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[OAuth2] Connection error [{self._token_url}]: {e}")
            return False
        except Exception as e:
            logger.error(f"[OAuth2] Exception: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """Refreshes the access token using the stored refresh token."""
        if not OAuth2Fixture._refresh_token:
            logger.error("[OAuth2] No refresh token available to refresh access token")
            return False
        
        self._grant_type = "refresh_token"
        return self.get_token()

    # Getters
    def actual_status_code(self) -> int:
        return self._actual_status_code

    def status_code(self) -> str:
        return str(self._actual_status_code)

    def response_time(self) -> int:
        return self._response_time_ms

    def access_token(self) -> str:
        return OAuth2Fixture._access_token

    def refresh_token(self) -> str:
        return OAuth2Fixture._refresh_token

    def token_type(self) -> str:
        return OAuth2Fixture._token_type

    def is_expired(self) -> bool:
        return OAuth2Fixture.is_token_expired()

    def response_body(self) -> str:
        try:
            pretty = json.dumps(self._response_body_json, indent=2)
            return f"\n{{\n{pretty}\n}}\n"
        except Exception:
            return f"\n{{\n{self._response_body}\n}}\n"
