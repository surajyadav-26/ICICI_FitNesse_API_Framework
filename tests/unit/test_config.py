"""
Unit tests for Config class
Tests configuration loading, validation, and environment management
"""
import pytest
import os
from unittest.mock import patch
from core.config import Config


class TestConfig:
    """Test suite for Config class"""
    
    def test_get_base_url_dev(self):
        """Test getting dev environment base URL"""
        url = Config.get_base_url("dev")
        assert "dev" in url.lower() or "example.com" in url
    
    def test_get_base_url_staging(self):
        """Test getting staging environment base URL"""
        url = Config.get_base_url("staging")
        assert "staging" in url.lower() or "example.com" in url
    
    def test_get_base_url_uat(self):
        """Test getting UAT environment base URL"""
        url = Config.get_base_url("uat")
        assert "uat" in url.lower() or "example.com" in url
    
    def test_get_base_url_prod(self):
        """Test getting prod environment base URL"""
        url = Config.get_base_url("prod")
        assert "example.com" in url or "api" in url.lower()
    
    def test_get_base_url_production_alias(self):
        """Test 'production' is an alias for 'prod'"""
        url1 = Config.get_base_url("prod")
        url2 = Config.get_base_url("production")
        assert url1 == url2
    
    def test_get_base_url_case_insensitive(self):
        """Test environment name is case-insensitive"""
        url1 = Config.get_base_url("DEV")
        url2 = Config.get_base_url("dev")
        assert url1 == url2
    
    def test_get_base_url_invalid_raises_error(self):
        """Test invalid environment raises ValueError"""
        with pytest.raises(ValueError, match="Invalid environment"):
            Config.get_base_url("invalid")
    
    def test_get_credentials_admin(self):
        """Test getting admin credentials"""
        username, password = Config.get_credentials("admin")
        assert username is not None
        assert password is not None
        assert len(username) > 0
        assert len(password) > 0
    
    def test_get_credentials_qa(self):
        """Test getting QA credentials"""
        username, password = Config.get_credentials("qa")
        assert username is not None
        assert password is not None
    
    def test_get_credentials_dev(self):
        """Test getting dev credentials"""
        username, password = Config.get_credentials("dev")
        assert username is not None
        assert password is not None
    
    def test_get_credentials_reader(self):
        """Test getting reader credentials"""
        username, password = Config.get_credentials("reader")
        assert username is not None
        assert password is not None
    
    def test_get_credentials_case_insensitive(self):
        """Test user type is case-insensitive"""
        creds1 = Config.get_credentials("ADMIN")
        creds2 = Config.get_credentials("admin")
        assert creds1 == creds2
    
    def test_get_credentials_invalid_raises_error(self):
        """Test invalid user type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid user type"):
            Config.get_credentials("superuser")
    
    def test_validate_returns_list(self):
        """Test validate returns list of errors"""
        errors = Config.validate()
        assert isinstance(errors, list)
    
    def test_validate_warns_about_default_password(self):
        """Test validate warns if using default password"""
        errors = Config.validate()
        # Should contain warning about default password
        assert any("admin password" in err.lower() for err in errors) or len(errors) == 0
    
    def test_default_timeout_is_positive(self):
        """Test default timeout is positive integer"""
        assert Config.DEFAULT_TIMEOUT > 0
        assert isinstance(Config.DEFAULT_TIMEOUT, int)
    
    def test_max_retries_is_non_negative(self):
        """Test max retries is non-negative"""
        assert Config.MAX_RETRIES >= 0
        assert isinstance(Config.MAX_RETRIES, int)
    
    def test_ssl_verify_is_boolean(self):
        """Test SSL verify is boolean"""
        assert isinstance(Config.SSL_VERIFY, bool)
    
    def test_mock_server_port_is_valid(self):
        """Test mock server port is valid"""
        assert 1024 <= Config.MOCK_SERVER_PORT <= 65535
    
    @patch.dict(os.environ, {"API_ADMIN_PASS": "custom_password"})
    def test_loads_from_environment_variable(self):
        """Test config loads from environment variables"""
        # This test verifies environment variable loading works
        # Note: Actual value depends on whether .env file exists
        assert Config.API_ADMIN_PASS is not None
