"""
Input Validation Module
Validates URLs, JSON, headers, and other user inputs to prevent security issues.
"""
import re
import json
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class RequestValidator:
    """
    Validates HTTP request inputs to prevent security vulnerabilities.
    """
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = ["http", "https", "ws", "wss"]
    
    # Dangerous characters in headers (CRLF injection prevention)
    DANGEROUS_HEADER_CHARS = ["\r", "\n", "\0"]
    
    # Maximum lengths to prevent DoS
    MAX_URL_LENGTH = 2048
    MAX_HEADER_VALUE_LENGTH = 8192
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
    
    @staticmethod
    def validate_url(url: str, allow_localhost: bool = True) -> str:
        """
        Validate and sanitize URL.
        
        Args:
            url: URL to validate
            allow_localhost: Whether to allow localhost/127.0.0.1
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL cannot be empty")
        
        url = url.strip()
        
        # Check length
        if len(url) > RequestValidator.MAX_URL_LENGTH:
            raise ValidationError(f"URL exceeds maximum length of {RequestValidator.MAX_URL_LENGTH} characters")
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}")
        
        # Validate scheme
        if parsed.scheme not in RequestValidator.ALLOWED_SCHEMES:
            raise ValidationError(
                f"Invalid URL scheme '{parsed.scheme}'. "
                f"Allowed: {', '.join(RequestValidator.ALLOWED_SCHEMES)}"
            )
        
        # Validate hostname exists
        if not parsed.netloc:
            raise ValidationError("URL must have a valid hostname")
        
        # Check for localhost in production
        if not allow_localhost:
            hostname = parsed.hostname or ""
            if hostname in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
                raise ValidationError("Localhost URLs not allowed in production")
        
        # Check for suspicious characters
        if any(char in url for char in ["\r", "\n", "\0", " "]):
            raise ValidationError("URL contains invalid characters")
        
        return url
    
    @staticmethod
    def validate_json(json_str: str) -> dict:
        """
        Validate and parse JSON string.
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            Parsed JSON dict
            
        Raises:
            ValidationError: If JSON is invalid
        """
        if not json_str:
            raise ValidationError("JSON cannot be empty")
        
        json_str = json_str.strip()
        
        # Check size
        if len(json_str) > RequestValidator.MAX_BODY_SIZE:
            raise ValidationError(
                f"JSON body exceeds maximum size of "
                f"{RequestValidator.MAX_BODY_SIZE / (1024*1024)} MB"
            )
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
    
    @staticmethod
    def validate_header(name: str, value: str) -> tuple:
        """
        Validate HTTP header name and value.

        Args:
            name: Header name
            value: Header value

        Returns:
            Tuple of (validated_name, validated_value)

        Raises:
            ValidationError: If header is invalid
        """
        if not name:
            raise ValidationError("Header name cannot be empty")

        # Check for CRLF injection (run this first!)
        for char in RequestValidator.DANGEROUS_HEADER_CHARS:
            if char in name:
                raise ValidationError(f"Header name contains illegal character: {repr(char)}")
            if char in value:
                raise ValidationError(f"Header value contains illegal character: {repr(char)}")

        # Validate header name (RFC 7230)
        if not re.match(r'^[!#$%&\'*+\-.0-9A-Z^_`a-z|~]+$', name):
            raise ValidationError(f"Invalid header name: {name}")

        # Check value length
        if len(value) > RequestValidator.MAX_HEADER_VALUE_LENGTH:
            raise ValidationError(
                f"Header value exceeds maximum length of "
                f"{RequestValidator.MAX_HEADER_VALUE_LENGTH} characters"
            )

        return name, value.strip()
    
    @staticmethod
    def validate_status_code(code: int) -> int:
        """
        Validate HTTP status code.
        
        Args:
            code: Status code to validate
            
        Returns:
            Validated status code
            
        Raises:
            ValidationError: If status code is invalid
        """
        if not isinstance(code, int):
            raise ValidationError(f"Status code must be an integer, got {type(code).__name__}")
        
        if code < 100 or code > 599:
            raise ValidationError(f"Invalid HTTP status code: {code}. Must be 100-599")
        
        return code
    
    @staticmethod
    def validate_timeout(timeout: int) -> int:
        """
        Validate timeout value.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Validated timeout
            
        Raises:
            ValidationError: If timeout is invalid
        """
        if not isinstance(timeout, int):
            raise ValidationError(f"Timeout must be an integer, got {type(timeout).__name__}")
        
        if timeout < 1:
            raise ValidationError("Timeout must be at least 1 second")
        
        if timeout > 300:  # 5 minutes max
            raise ValidationError("Timeout cannot exceed 300 seconds (5 minutes)")
        
        return timeout
    
    @staticmethod
    def validate_retry_count(retries: int) -> int:
        """
        Validate retry count.
        
        Args:
            retries: Number of retries
            
        Returns:
            Validated retry count
            
        Raises:
            ValidationError: If retry count is invalid
        """
        if not isinstance(retries, int):
            raise ValidationError(f"Retry count must be an integer, got {type(retries).__name__}")
        
        if retries < 0:
            raise ValidationError("Retry count cannot be negative")
        
        if retries > 10:
            raise ValidationError("Retry count cannot exceed 10")
        
        return retries
    
    @staticmethod
    def sanitize_for_log(value: str, max_length: int = 200) -> str:
        """
        Sanitize value for safe logging (prevent log injection).
        
        Args:
            value: Value to sanitize
            max_length: Maximum length to log
            
        Returns:
            Sanitized value
        """
        if not value:
            return ""
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', value)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "...[truncated]"
        
        return sanitized
    
    @staticmethod
    def is_safe_redirect(original_url: str, redirect_url: str) -> bool:
        """
        Check if redirect URL is safe (same domain or whitelisted).
        
        Args:
            original_url: Original request URL
            redirect_url: Redirect target URL
            
        Returns:
            True if redirect is safe
        """
        try:
            original = urlparse(original_url)
            redirect = urlparse(redirect_url)
            
            # Same domain is safe
            if original.netloc == redirect.netloc:
                return True
            
            # Check against whitelist (could be configured)
            # For now, only allow same domain
            return False
            
        except Exception:
            return False


class DataValidator:
    """
    Validates data types and business rules.
    """
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email format.
        
        Args:
            email: Email address
            
        Returns:
            Validated email
            
        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError("Email cannot be empty")
        
        # Basic email regex (RFC 5322 compliant would be more complex)
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email format: {email}")
        
        return email.lower().strip()
    
    @staticmethod
    def validate_phone(phone: str, country_code: str = "IN") -> str:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number
            country_code: Country code (default: IN for India)
            
        Returns:
            Validated phone number
            
        Raises:
            ValidationError: If phone is invalid
        """
        if not phone:
            raise ValidationError("Phone number cannot be empty")
        
        # Remove common separators
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Basic validation (10 digits for India)
        if country_code == "IN":
            if not re.match(r'^\+?91?[6-9]\d{9}$', cleaned):
                raise ValidationError(f"Invalid Indian phone number: {phone}")
        
        return cleaned
    
    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> str:
        """
        Validate date format.
        
        Args:
            date_str: Date string
            format: Expected format (default: YYYY-MM-DD)
            
        Returns:
            Validated date string
            
        Raises:
            ValidationError: If date is invalid
        """
        if not date_str:
            raise ValidationError("Date cannot be empty")
        
        from datetime import datetime
        
        try:
            datetime.strptime(date_str, format)
            return date_str
        except ValueError:
            raise ValidationError(f"Invalid date format. Expected: {format}, got: {date_str}")


# Convenience function for backward compatibility
def validate_url(url: str) -> str:
    """Validate URL (convenience function)"""
    return RequestValidator.validate_url(url)


def validate_json(json_str: str) -> dict:
    """Validate JSON (convenience function)"""
    return RequestValidator.validate_json(json_str)
