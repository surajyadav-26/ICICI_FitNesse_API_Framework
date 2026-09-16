"""
Unit tests for RequestValidator class
Tests URL, JSON, header, and other input validation functions
"""
import pytest
from core.validators import (
    RequestValidator, 
    DataValidator, 
    ValidationError,
    validate_url,
    validate_json
)


class TestRequestValidator:
    """Test suite for RequestValidator class"""
    
    # URL Validation Tests
    def test_validate_url_valid_http(self):
        """Test valid HTTP URL"""
        url = "http://api.example.com/users"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_valid_https(self):
        """Test valid HTTPS URL"""
        url = "https://api.example.com/users"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_valid_websocket(self):
        """Test valid WebSocket URL"""
        url = "ws://api.example.com/socket"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_valid_websocket_secure(self):
        """Test valid WSS URL"""
        url = "wss://api.example.com/socket"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_empty_raises_error(self):
        """Test empty URL raises ValidationError"""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            RequestValidator.validate_url("")
    
    def test_validate_url_invalid_scheme_raises_error(self):
        """Test invalid scheme raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            RequestValidator.validate_url("ftp://example.com")
    
    def test_validate_url_no_hostname_raises_error(self):
        """Test URL without hostname raises ValidationError"""
        with pytest.raises(ValidationError, match="must have a valid hostname"):
            RequestValidator.validate_url("http://")
    
    def test_validate_url_too_long_raises_error(self):
        """Test URL exceeding max length raises ValidationError"""
        long_url = "https://example.com/" + "a" * 3000
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            RequestValidator.validate_url(long_url)
    
    def test_validate_url_crlf_injection_raises_error(self):
        """Test URL with CRLF characters raises ValidationError"""
        with pytest.raises(ValidationError, match="invalid characters"):
            RequestValidator.validate_url("https://example.com\r\nHost: evil.com")
    
    def test_validate_url_localhost_allowed_by_default(self):
        """Test localhost is allowed by default"""
        url = "http://localhost:8080/api"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_localhost_blocked_in_production(self):
        """Test localhost can be blocked"""
        with pytest.raises(ValidationError, match="Localhost URLs not allowed"):
            RequestValidator.validate_url("http://localhost:8080", allow_localhost=False)
    
    def test_validate_url_strips_whitespace(self):
        """Test URL whitespace is stripped"""
        url = "  https://api.example.com/users  "
        result = RequestValidator.validate_url(url)
        assert result == "https://api.example.com/users"
    
    # JSON Validation Tests
    def test_validate_json_valid(self):
        """Test valid JSON"""
        json_str = '{"name": "John", "age": 30}'
        result = RequestValidator.validate_json(json_str)
        assert result == {"name": "John", "age": 30}
    
    def test_validate_json_valid_array(self):
        """Test valid JSON array"""
        json_str = '[{"id": 1}, {"id": 2}]'
        result = RequestValidator.validate_json(json_str)
        assert result == [{"id": 1}, {"id": 2}]
    
    def test_validate_json_empty_raises_error(self):
        """Test empty JSON raises ValidationError"""
        with pytest.raises(ValidationError, match="JSON cannot be empty"):
            RequestValidator.validate_json("")
    
    def test_validate_json_invalid_raises_error(self):
        """Test invalid JSON raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid JSON"):
            RequestValidator.validate_json('{"name": invalid}')
    
    def test_validate_json_too_large_raises_error(self):
        """Test JSON exceeding size limit raises ValidationError"""
        large_json = '{"data": "' + "x" * (11 * 1024 * 1024) + '"}'
        with pytest.raises(ValidationError, match="exceeds maximum size"):
            RequestValidator.validate_json(large_json)
    
    # Header Validation Tests
    def test_validate_header_valid(self):
        """Test valid header"""
        name, value = RequestValidator.validate_header("Content-Type", "application/json")
        assert name == "Content-Type"
        assert value == "application/json"
    
    def test_validate_header_strips_value_whitespace(self):
        """Test header value whitespace is stripped"""
        name, value = RequestValidator.validate_header("Authorization", "  Bearer token123  ")
        assert value == "Bearer token123"
    
    def test_validate_header_empty_name_raises_error(self):
        """Test empty header name raises ValidationError"""
        with pytest.raises(ValidationError, match="Header name cannot be empty"):
            RequestValidator.validate_header("", "value")
    
    def test_validate_header_invalid_name_raises_error(self):
        """Test invalid header name raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid header name"):
            RequestValidator.validate_header("Invalid Header!", "value")
    
    def test_validate_header_crlf_in_value_raises_error(self):
        """Test CRLF in header value raises ValidationError"""
        with pytest.raises(ValidationError, match="illegal character"):
            RequestValidator.validate_header("Header", "value\r\nEvil: header")
    
    def test_validate_header_value_too_long_raises_error(self):
        """Test header value exceeding max length raises ValidationError"""
        long_value = "x" * 10000
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            RequestValidator.validate_header("Header", long_value)
    
    # Status Code Validation Tests
    def test_validate_status_code_valid(self):
        """Test valid status codes"""
        assert RequestValidator.validate_status_code(200) == 200
        assert RequestValidator.validate_status_code(404) == 404
        assert RequestValidator.validate_status_code(500) == 500
    
    def test_validate_status_code_invalid_type_raises_error(self):
        """Test non-integer status code raises ValidationError"""
        with pytest.raises(ValidationError, match="must be an integer"):
            RequestValidator.validate_status_code("200")
    
    def test_validate_status_code_out_of_range_raises_error(self):
        """Test status code out of range raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid HTTP status code"):
            RequestValidator.validate_status_code(99)
        with pytest.raises(ValidationError, match="Invalid HTTP status code"):
            RequestValidator.validate_status_code(600)
    
    # Timeout Validation Tests
    def test_validate_timeout_valid(self):
        """Test valid timeout"""
        assert RequestValidator.validate_timeout(15) == 15
        assert RequestValidator.validate_timeout(60) == 60
    
    def test_validate_timeout_invalid_type_raises_error(self):
        """Test non-integer timeout raises ValidationError"""
        with pytest.raises(ValidationError, match="must be an integer"):
            RequestValidator.validate_timeout("15")
    
    def test_validate_timeout_too_low_raises_error(self):
        """Test timeout below minimum raises ValidationError"""
        with pytest.raises(ValidationError, match="must be at least 1 second"):
            RequestValidator.validate_timeout(0)
    
    def test_validate_timeout_too_high_raises_error(self):
        """Test timeout above maximum raises ValidationError"""
        with pytest.raises(ValidationError, match="cannot exceed 300 seconds"):
            RequestValidator.validate_timeout(400)
    
    # Retry Count Validation Tests
    def test_validate_retry_count_valid(self):
        """Test valid retry count"""
        assert RequestValidator.validate_retry_count(3) == 3
        assert RequestValidator.validate_retry_count(0) == 0
    
    def test_validate_retry_count_invalid_type_raises_error(self):
        """Test non-integer retry count raises ValidationError"""
        with pytest.raises(ValidationError, match="must be an integer"):
            RequestValidator.validate_retry_count("3")
    
    def test_validate_retry_count_negative_raises_error(self):
        """Test negative retry count raises ValidationError"""
        with pytest.raises(ValidationError, match="cannot be negative"):
            RequestValidator.validate_retry_count(-1)
    
    def test_validate_retry_count_too_high_raises_error(self):
        """Test retry count above maximum raises ValidationError"""
        with pytest.raises(ValidationError, match="cannot exceed 10"):
            RequestValidator.validate_retry_count(15)
    
    # Sanitize for Log Tests
    def test_sanitize_for_log_removes_control_chars(self):
        """Test control characters are removed"""
        result = RequestValidator.sanitize_for_log("test\x00\x01string")
        assert result == "teststring"
    
    def test_sanitize_for_log_truncates_long_values(self):
        """Test long values are truncated"""
        long_value = "x" * 300
        result = RequestValidator.sanitize_for_log(long_value, max_length=100)
        assert len(result) <= 115  # 100 + "[truncated]"
        assert "[truncated]" in result
    
    def test_sanitize_for_log_empty_returns_empty(self):
        """Test empty value returns empty"""
        assert RequestValidator.sanitize_for_log("") == ""
        assert RequestValidator.sanitize_for_log(None) == ""


class TestDataValidator:
    """Test suite for DataValidator class"""
    
    # Email Validation Tests
    def test_validate_email_valid(self):
        """Test valid email addresses"""
        assert DataValidator.validate_email("user@example.com") == "user@example.com"
        assert DataValidator.validate_email("test.user@example.co.uk") == "test.user@example.co.uk"
    
    def test_validate_email_empty_raises_error(self):
        """Test empty email raises ValidationError"""
        with pytest.raises(ValidationError, match="Email cannot be empty"):
            DataValidator.validate_email("")
    
    def test_validate_email_invalid_raises_error(self):
        """Test invalid email raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid email format"):
            DataValidator.validate_email("invalid.email")
        with pytest.raises(ValidationError, match="Invalid email format"):
            DataValidator.validate_email("@example.com")
    
    def test_validate_email_converts_to_lowercase(self):
        """Test email is converted to lowercase"""
        result = DataValidator.validate_email("USER@EXAMPLE.COM")
        assert result == "user@example.com"
    
    # Phone Validation Tests
    def test_validate_phone_empty_raises_error(self):
        """Test empty phone raises ValidationError"""
        with pytest.raises(ValidationError, match="Phone number cannot be empty"):
            DataValidator.validate_phone("")
    
    # Date Validation Tests
    def test_validate_date_valid(self):
        """Test valid date"""
        result = DataValidator.validate_date("2026-07-16")
        assert result == "2026-07-16"
    
    def test_validate_date_empty_raises_error(self):
        """Test empty date raises ValidationError"""
        with pytest.raises(ValidationError, match="Date cannot be empty"):
            DataValidator.validate_date("")
    
    def test_validate_date_invalid_format_raises_error(self):
        """Test invalid date format raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid date format"):
            DataValidator.validate_date("16-07-2026")


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_validate_url_function(self):
        """Test validate_url convenience function"""
        url = "https://api.example.com"
        result = validate_url(url)
        assert result == url
    
    def test_validate_json_function(self):
        """Test validate_json convenience function"""
        json_str = '{"test": true}'
        result = validate_json(json_str)
        assert result == {"test": True}
