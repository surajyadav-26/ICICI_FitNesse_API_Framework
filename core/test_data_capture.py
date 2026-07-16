"""
Test Data Capture Module
Saves request/response data as downloadable JSON files for debugging and audit purposes.
"""
import os
import json
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "test_data")

# Sensitive field patterns to sanitize (case-insensitive)
SENSITIVE_PATTERNS = [
    r"password",
    r"passwd",
    r"pwd",
    r"secret",
    r"token",
    r"api[_-]?key",
    r"apikey",
    r"auth",
    r"authorization",
    r"bearer",
    r"private[_-]?key",
    r"access[_-]?token",
    r"refresh[_-]?token",
    r"session[_-]?id",
    r"cookie",
    r"ssn",
    r"credit[_-]?card",
    r"card[_-]?number",
    r"cvv",
    r"pin",
]

def sanitize_value(key: str, value: Any) -> Any:
    """
    Sanitize sensitive data by masking values for fields matching sensitive patterns.
    
    Args:
        key: The field name
        value: The field value
        
    Returns:
        Sanitized value (masked if sensitive, original otherwise)
    """
    if not isinstance(key, str):
        return value
    
    # Check if key matches any sensitive pattern
    key_lower = key.lower()
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, key_lower):
            # Mask the value but show length
            if isinstance(value, str):
                if len(value) <= 4:
                    return "***"
                return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            else:
                return "***REDACTED***"
    
    return value

def sanitize_dict(data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary by masking sensitive fields.
    
    Args:
        data: Dictionary to sanitize
        parent_key: Parent key for nested dictionaries
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        
        if isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, full_key)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, full_key) if isinstance(item, dict) else sanitize_value(key, item)
                for item in value
            ]
        else:
            sanitized[key] = sanitize_value(key, value)
    
    return sanitized

def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Sanitize HTTP headers by masking sensitive values.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Sanitized headers dictionary
    """
    if not headers:
        return {}
    
    sanitized = {}
    for key, value in headers.items():
        sanitized[key] = sanitize_value(key, value)
    
    return sanitized

def generate_test_id(method: str, url: str, timestamp: str) -> str:
    """
    Generate a unique test ID based on method, URL, and timestamp.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        timestamp: Timestamp string
        
    Returns:
        Unique test ID (hash-based)
    """
    # Create hash from method + url + timestamp
    hash_input = f"{method}_{url}_{timestamp}".encode('utf-8')
    hash_hex = hashlib.md5(hash_input).hexdigest()[:12]
    
    # Create readable ID: method_hash_timestamp
    timestamp_clean = timestamp.replace("-", "").replace(":", "").replace(" ", "_")
    return f"{method}_{hash_hex}_{timestamp_clean}"

def save_test_data(
    test_name: str,
    method: str,
    url: str,
    request_headers: Optional[Dict[str, str]],
    request_body: str,
    response_status: int,
    response_headers: Optional[Dict[str, str]],
    response_body: str,
    response_time_ms: int,
    assertions: Dict[str, Any],
    timestamp: str
) -> str:
    """
    Save test execution data as JSON file with sanitization.
    
    Args:
        test_name: Name of the test page
        method: HTTP method
        url: Request URL
        request_headers: Request headers dictionary
        request_body: Request body (JSON string or plain text)
        response_status: HTTP response status code
        response_headers: Response headers dictionary
        response_body: Response body (JSON string or plain text)
        response_time_ms: Response time in milliseconds
        assertions: Dictionary of assertions (right, wrong, exceptions)
        timestamp: Execution timestamp
        
    Returns:
        Path to the saved JSON file (relative to FitNesseRoot/files/)
    """
    try:
        # Ensure test data directory exists
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        
        # Parse JSON bodies if possible
        try:
            request_body_json = json.loads(request_body) if request_body and request_body.strip() else None
        except (json.JSONDecodeError, ValueError):
            request_body_json = None
        
        try:
            response_body_json = json.loads(response_body) if response_body and response_body.strip() else None
        except (json.JSONDecodeError, ValueError):
            response_body_json = None
        
        # Sanitize data
        sanitized_req_headers = sanitize_headers(request_headers or {})
        sanitized_resp_headers = sanitize_headers(response_headers or {})
        sanitized_req_body = sanitize_dict(request_body_json) if request_body_json else request_body
        sanitized_resp_body = sanitize_dict(response_body_json) if response_body_json else response_body
        
        # Build test data structure
        test_data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "request": {
                "method": method,
                "url": url,
                "headers": sanitized_req_headers,
                "body": sanitized_req_body
            },
            "response": {
                "status_code": response_status,
                "headers": sanitized_resp_headers,
                "body": sanitized_resp_body,
                "duration_ms": response_time_ms
            },
            "assertions": assertions,
            "metadata": {
                "sanitized": True,
                "captured_at": datetime.now().isoformat()
            }
        }
        
        # Generate unique filename
        test_id = generate_test_id(method, url, timestamp)
        filename = f"{test_id}.json"
        filepath = os.path.join(TEST_DATA_DIR, filename)
        
        # Save JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        # Return relative path for download link
        return f"test_data/{filename}"
        
    except Exception as e:
        # Log error but don't fail the test
        print(f"[ERROR] Failed to save test data: {e}")
        import traceback
        traceback.print_exc()
        return ""

def cleanup_old_files(days: int = 7) -> int:
    """
    Clean up test data files older than specified days.
    
    Args:
        days: Number of days to keep files (default: 7)
        
    Returns:
        Number of files deleted
    """
    if not os.path.exists(TEST_DATA_DIR):
        return 0
    
    deleted_count = 0
    current_time = datetime.now()
    
    try:
        for filename in os.listdir(TEST_DATA_DIR):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(TEST_DATA_DIR, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            age_days = (current_time - file_time).days
            
            if age_days > days:
                os.remove(filepath)
                deleted_count += 1
    except Exception as e:
        print(f"[WARNING] Cleanup error: {e}")
    
    return deleted_count
