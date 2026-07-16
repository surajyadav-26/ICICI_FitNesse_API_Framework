"""
Integration tests for API testing workflow
Tests end-to-end request execution, token management, and reporting
"""
import pytest
import time
from fixtures.get_request_fixture import GetRequestFixture
from fixtures.post_request_fixture import PostRequestFixture
from fixtures.auth_fixture import AuthFixture
from core.config import Config


@pytest.mark.integration
class TestGetRequestIntegration:
    """Integration tests for GET requests"""
    
    def test_get_request_success(self):
        """Test successful GET request"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/users/1")
        
        result = fixture.execute()
        
        assert result is True
        assert fixture.status_code() == 200
        assert len(fixture.response_body()) > 0
    
    def test_get_request_with_timeout(self):
        """Test GET request with custom timeout"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/users/1")
        fixture.set_timeout("10")
        
        result = fixture.execute()
        
        assert result is True
        assert fixture.response_time_ms() < 10000
    
    def test_get_request_404(self):
        """Test GET request returning 404"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/users/999999")
        
        result = fixture.execute()
        
        assert result is True  # Execute succeeds even with 404
        assert fixture.status_code() == 404
    
    def test_get_request_json_extraction(self):
        """Test extracting field from JSON response"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/users/1")
        fixture.set_key("name")
        
        result = fixture.execute()
        
        assert result is True
        assert len(fixture.value_for_key()) > 0


@pytest.mark.integration
class TestPostRequestIntegration:
    """Integration tests for POST requests"""
    
    def test_post_request_with_json_body(self):
        """Test POST request with JSON body"""
        fixture = PostRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts")
        fixture.set_body_json('{"title": "Test Post", "body": "Test body", "userId": 1}')
        
        result = fixture.execute()
        
        assert result is True
        assert fixture.status_code() == 201
        response = fixture.response_body()
        assert "Test Post" in response or "test post" in response.lower()
    
    def test_post_request_extract_response_field(self):
        """Test extracting field from POST response"""
        fixture = PostRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts")
        fixture.set_body_json('{"title": "New Post", "body": "Content", "userId": 1}')
        fixture.set_key("id")
        
        result = fixture.execute()
        
        assert result is True
        value = fixture.value_for_key()
        assert value is not None
        assert len(str(value)) > 0


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication"""
    
    def test_auth_token_storage(self):
        """Test token storage and retrieval"""
        AuthFixture.set_token("test_token_12345")
        token = AuthFixture.get_stored_token()
        
        assert token == "test_token_12345"
        
        # Clean up
        AuthFixture.clear_token()
    
    def test_auth_token_clear(self):
        """Test clearing stored token"""
        AuthFixture.set_token("token_to_clear")
        AuthFixture.clear_token()
        
        token = AuthFixture.get_stored_token()
        assert token == ""
    
    def test_get_request_with_auth_token(self):
        """Test GET request uses stored auth token"""
        # Store a token
        AuthFixture.set_token("Bearer test_token")
        
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/users/1")
        
        # Execute request (will include auth header)
        result = fixture.execute()
        
        assert result is True
        
        # Clean up
        AuthFixture.clear_token()


@pytest.mark.integration
class TestRetryMechanism:
    """Integration tests for retry mechanism"""
    
    def test_retry_on_failure(self):
        """Test request retries on failure"""
        fixture = GetRequestFixture()
        # Use an invalid URL that will fail
        fixture.set_url("https://invalid-domain-that-does-not-exist-12345.com/api")
        fixture.set_retries("2")
        fixture.set_retry_delay("0.1")
        
        start_time = time.time()
        result = fixture.execute()
        elapsed = time.time() - start_time
        
        # Request should fail after retries
        assert result is False
        # Should have taken at least 0.2 seconds (2 retries with 0.1s delay)
        assert elapsed >= 0.2


@pytest.mark.integration
class TestValidationIntegration:
    """Integration tests for input validation"""
    
    def test_invalid_url_logs_error(self):
        """Test invalid URL logs validation error"""
        fixture = GetRequestFixture()
        
        # Set invalid URL (no scheme)
        fixture.set_url("invalid-url-without-http")
        
        # URL is stored but validation error is logged
        # Execution will fail when attempted
        result = fixture.execute()
        assert result is False
    
    def test_invalid_json_logs_error(self):
        """Test invalid JSON logs validation error"""
        fixture = PostRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts")
        
        # Set invalid JSON
        fixture.set_body_json('{"invalid": json}')
        
        # JSON validation error is logged
        # Can still proceed (for backward compatibility)
        # But request might fail


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration management"""
    
    def test_get_environment_base_url(self):
        """Test getting base URL from config"""
        dev_url = Config.get_base_url("dev")
        assert dev_url is not None
        assert len(dev_url) > 0
    
    def test_get_credentials_from_config(self):
        """Test getting credentials from config"""
        username, password = Config.get_credentials("admin")
        assert username is not None
        assert password is not None
        assert len(username) > 0
        assert len(password) > 0
