"""
Unit tests for test_data_capture module
Tests sanitization and JSON file generation
"""
import pytest
import json
import os
import tempfile
import shutil
from core.test_data_capture import (
    sanitize_value,
    sanitize_dict,
    sanitize_headers,
    generate_test_id,
    save_test_data
)


class TestSanitization:
    """Test suite for data sanitization functions"""
    
    def test_sanitize_value_password_field(self):
        """Test password field is masked"""
        result = sanitize_value("password", "MySecret123")
        assert result != "MySecret123"
        assert "***" in result or "*" in result
    
    def test_sanitize_value_token_field(self):
        """Test token field is masked"""
        result = sanitize_value("api_token", "secret_token_value")
        assert result != "secret_token_value"
        assert "REDACTED" in result or "*" in result
    
    def test_sanitize_value_authorization_field(self):
        """Test authorization field is masked"""
        result = sanitize_value("Authorization", "Bearer abc123")
        assert result != "Bearer abc123"
        assert "REDACTED" in result or "*" in result
    
    def test_sanitize_value_normal_field_unchanged(self):
        """Test normal field is not masked"""
        result = sanitize_value("name", "John Doe")
        assert result == "John Doe"
    
    def test_sanitize_value_short_sensitive_field(self):
        """Test short sensitive value is fully masked"""
        result = sanitize_value("pwd", "abc")
        assert result == "***"
    
    def test_sanitize_dict_masks_sensitive_keys(self):
        """Test sanitize_dict masks sensitive keys"""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }
        result = sanitize_dict(data)
        assert result["username"] == "john"
        assert result["email"] == "john@example.com"
        assert result["password"] != "secret123"
    
    def test_sanitize_dict_nested_objects(self):
        """Test sanitize_dict handles nested objects"""
        data = {
            "user": {
                "name": "john",
                "password": "secret123"
            }
        }
        result = sanitize_dict(data)
        assert result["user"]["name"] == "john"
        assert result["user"]["password"] != "secret123"
    
    def test_sanitize_dict_arrays(self):
        """Test sanitize_dict handles arrays"""
        data = {
            "passwords": ["pass1", "pass2", "pass3"]
        }
        result = sanitize_dict(data)
        assert all("*" in p or "REDACTED" in p for p in result["passwords"])
    
    def test_sanitize_headers_masks_authorization(self):
        """Test sanitize_headers masks Authorization header"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123"
        }
        result = sanitize_headers(headers)
        assert result["Content-Type"] == "application/json"
        assert result["Authorization"] != "Bearer token123"
    
    def test_sanitize_headers_empty_dict(self):
        """Test sanitize_headers with empty dict"""
        result = sanitize_headers({})
        assert result == {}
    
    def test_sanitize_headers_none_returns_empty(self):
        """Test sanitize_headers with None returns empty dict"""
        result = sanitize_headers(None)
        assert result == {}


class TestGenerateTestId:
    """Test suite for generate_test_id function"""
    
    def test_generate_test_id_format(self):
        """Test test ID has expected format"""
        test_id = generate_test_id("POST", "https://api.example.com/users", "2026-07-16 10:30:00")
        assert test_id.startswith("POST_")
        assert "_" in test_id
    
    def test_generate_test_id_unique(self):
        """Test different inputs generate different IDs"""
        id1 = generate_test_id("GET", "https://api.example.com/users", "2026-07-16 10:30:00")
        id2 = generate_test_id("POST", "https://api.example.com/users", "2026-07-16 10:30:00")
        assert id1 != id2
    
    def test_generate_test_id_consistent(self):
        """Test same inputs generate same ID"""
        id1 = generate_test_id("GET", "https://api.example.com/users", "2026-07-16 10:30:00")
        id2 = generate_test_id("GET", "https://api.example.com/users", "2026-07-16 10:30:00")
        assert id1 == id2


class TestSaveTestData:
    """Test suite for save_test_data function"""
    
    def setup_method(self):
        """Create temp directory for test data"""
        self.temp_dir = tempfile.mkdtemp()
        # Patch TEST_DATA_DIR
        import core.test_data_capture as tdc
        self.original_dir = tdc.TEST_DATA_DIR
        tdc.TEST_DATA_DIR = self.temp_dir
    
    def teardown_method(self):
        """Remove temp directory"""
        import core.test_data_capture as tdc
        tdc.TEST_DATA_DIR = self.original_dir
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_test_data_creates_file(self):
        """Test save_test_data creates JSON file"""
        filepath = save_test_data(
            test_name="Test_API",
            method="GET",
            url="https://api.example.com/users",
            request_headers={"Content-Type": "application/json"},
            request_body='{"test": true}',
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"result": "success"}',
            response_time_ms=123,
            assertions={"right": 1, "wrong": 0, "ignored": 0, "exceptions": 0},
            timestamp="2026-07-16 10:30:00"
        )
        
        assert filepath != ""
        assert "test_data/" in filepath
        assert filepath.endswith(".json")
    
    def test_save_test_data_json_structure(self):
        """Test saved JSON has correct structure"""
        filepath = save_test_data(
            test_name="Test_API",
            method="POST",
            url="https://api.example.com/users",
            request_headers={},
            request_body='{"name": "John"}',
            response_status=201,
            response_headers={},
            response_body='{"id": 123}',
            response_time_ms=234,
            assertions={"right": 1, "wrong": 0, "ignored": 0, "exceptions": 0},
            timestamp="2026-07-16 10:30:00"
        )
        
        # Read the file
        filename = filepath.split("/")[1]
        full_path = os.path.join(self.temp_dir, filename)
        
        with open(full_path, 'r') as f:
            data = json.load(f)
        
        assert "test_name" in data
        assert "timestamp" in data
        assert "request" in data
        assert "response" in data
        assert "assertions" in data
        assert "metadata" in data
        
        assert data["request"]["method"] == "POST"
        assert data["response"]["status_code"] == 201
    
    def test_save_test_data_sanitizes_password(self):
        """Test save_test_data sanitizes sensitive data"""
        filepath = save_test_data(
            test_name="Login_Test",
            method="POST",
            url="https://api.example.com/login",
            request_headers={},
            request_body='{"username": "john", "password": "MySecret123"}',
            response_status=200,
            response_headers={},
            response_body='{"token": "abc123xyz"}',
            response_time_ms=150,
            assertions={"right": 1, "wrong": 0, "ignored": 0, "exceptions": 0},
            timestamp="2026-07-16 10:30:00"
        )
        
        filename = filepath.split("/")[1]
        full_path = os.path.join(self.temp_dir, filename)
        
        with open(full_path, 'r') as f:
            data = json.load(f)
        
        # Password should be sanitized
        assert data["request"]["body"]["password"] != "MySecret123"
        # Token should be sanitized
        assert data["response"]["body"]["token"] != "abc123xyz"
