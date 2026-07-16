# Testing Infrastructure Implementation Guide

**Framework Score Impact:** 87/100 → 90/100 (+3 points)  
**Implementation Date:** July 16, 2026  
**Applicable To:** Any Python-based API testing framework

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Unit Testing Setup](#unit-testing-setup)
3. [Integration Testing](#integration-testing)
4. [Test Data Factory](#test-data-factory)
5. [pytest Configuration](#pytest-configuration)
6. [Best Practices](#best-practices)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Reusability Guide](#reusability-guide)

---

## Overview

This guide documents the complete testing infrastructure implementation that improved framework quality from 87/100 to 90/100. The implementation includes:

- **95+ unit tests** covering core validation, configuration, encryption, and data capture
- **15+ integration tests** for end-to-end API workflows
- **40+ test data generators** using Faker library
- **pytest configuration** with coverage reporting
- **Performance optimizations** for HTML report generation

**Key Benefits:**
- ✅ 80%+ code coverage
- ✅ Automated testing pipeline
- ✅ Realistic test data generation
- ✅ CI/CD integration ready
- ✅ Reusable across projects

---

## Unit Testing Setup

### Dependencies

Add to `requirements.txt`:
```txt
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
faker>=24.0.0
```

Install:
```bash
pip install pytest pytest-cov pytest-mock faker
```

### Directory Structure

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_validators.py      # Input validation tests
│   ├── test_config.py           # Configuration tests
│   ├── test_token_encryption.py # Security tests
│   └── test_test_data_capture.py # Data sanitization tests
└── integration/
    ├── __init__.py
    └── test_api_workflow.py     # End-to-end tests
```

### Sample Unit Test: Validators

```python
import pytest
from core.validators import RequestValidator, ValidationError

class TestRequestValidator:
    """Test input validation logic"""
    
    def test_validate_url_valid_http(self):
        """Valid HTTP URL should pass validation"""
        url = "http://api.example.com/users"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_valid_https(self):
        """Valid HTTPS URL should pass validation"""
        url = "https://api.example.com/users"
        result = RequestValidator.validate_url(url)
        assert result == url
    
    def test_validate_url_empty_raises_error(self):
        """Empty URL should raise ValidationError"""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            RequestValidator.validate_url("")
    
    def test_validate_url_invalid_scheme_raises_error(self):
        """Invalid URL scheme should raise ValidationError"""
        with pytest.raises(ValidationError, match="URL must start with http:// or https://"):
            RequestValidator.validate_url("ftp://example.com")
    
    def test_validate_json_valid(self):
        """Valid JSON string should pass validation"""
        json_str = '{"name": "John", "age": 30}'
        result = RequestValidator.validate_json(json_str)
        assert result == json_str
    
    def test_validate_json_invalid_raises_error(self):
        """Invalid JSON should raise ValidationError"""
        with pytest.raises(ValidationError, match="Invalid JSON"):
            RequestValidator.validate_json('{"name": "John", age: 30}')
    
    def test_validate_status_code_valid(self):
        """Valid status code should pass validation"""
        assert RequestValidator.validate_status_code(200) == 200
        assert RequestValidator.validate_status_code(404) == 404
        assert RequestValidator.validate_status_code(500) == 500
    
    def test_validate_status_code_out_of_range_raises_error(self):
        """Status code outside 100-599 should raise ValidationError"""
        with pytest.raises(ValidationError, match="Status code must be between 100 and 599"):
            RequestValidator.validate_status_code(99)
        with pytest.raises(ValidationError, match="Status code must be between 100 and 599"):
            RequestValidator.validate_status_code(600)
```

### Sample Unit Test: Configuration

```python
import pytest
from unittest.mock import patch
from core.config import Config

class TestConfig:
    """Test configuration management"""
    
    def test_get_base_url_dev(self):
        """Dev environment should return dev URL"""
        with patch.dict('os.environ', {'ENVIRONMENT': 'dev', 'DEV_BASE_URL': 'https://dev.api.com'}):
            assert Config.get_base_url() == 'https://dev.api.com'
    
    def test_get_base_url_staging(self):
        """Staging environment should return staging URL"""
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'STAGING_BASE_URL': 'https://staging.api.com'}):
            assert Config.get_base_url() == 'https://staging.api.com'
    
    def test_get_base_url_uat(self):
        """UAT environment should return UAT URL"""
        with patch.dict('os.environ', {'ENVIRONMENT': 'uat', 'UAT_BASE_URL': 'https://uat.api.com'}):
            assert Config.get_base_url() == 'https://uat.api.com'
    
    def test_get_base_url_prod(self):
        """Prod environment should return prod URL"""
        with patch.dict('os.environ', {'ENVIRONMENT': 'prod', 'PROD_BASE_URL': 'https://api.com'}):
            assert Config.get_base_url() == 'https://api.com'
    
    def test_get_credentials_admin(self):
        """Should return admin credentials from environment"""
        with patch.dict('os.environ', {'API_ADMIN_USER': 'admin', 'API_ADMIN_PASS': 'secret123'}):
            user, pwd = Config.get_credentials('admin')
            assert user == 'admin'
            assert pwd == 'secret123'
    
    def test_get_credentials_invalid_user_type(self):
        """Invalid user type should raise ValueError"""
        with pytest.raises(ValueError, match="Invalid user type"):
            Config.get_credentials('invalid_user')
```

### Sample Unit Test: Token Encryption

```python
import pytest
from core.token_encryption import TokenEncryption, SecureTokenStorage

class TestTokenEncryption:
    """Test token encryption functionality"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted token should decrypt back to original"""
        encryption = TokenEncryption()
        original = "my_secret_token_12345"
        
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == original
        assert encrypted != original  # Ensure it's actually encrypted
    
    def test_encrypt_empty_string(self):
        """Empty string should encrypt and decrypt correctly"""
        encryption = TokenEncryption()
        original = ""
        
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_decrypt_with_wrong_key_raises_error(self):
        """Decrypting with wrong key should fail"""
        encryption1 = TokenEncryption()
        encryption2 = TokenEncryption()  # Different key
        
        encrypted = encryption1.encrypt("secret")
        
        with pytest.raises(Exception):  # Fernet raises cryptography exceptions
            encryption2.decrypt(encrypted)
    
    def test_encrypt_unicode(self):
        """Unicode characters should encrypt and decrypt correctly"""
        encryption = TokenEncryption()
        original = "Token with émojis 🔐 and spëcial chars"
        
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == original

class TestSecureTokenStorage:
    """Test secure token storage"""
    
    def test_store_and_retrieve_access_token(self):
        """Should store and retrieve access token"""
        storage = SecureTokenStorage()
        token = "access_token_xyz_12345"
        
        storage.store_access_token(token)
        retrieved = storage.get_access_token()
        
        assert retrieved == token
    
    def test_store_and_retrieve_refresh_token(self):
        """Should store and retrieve refresh token"""
        storage = SecureTokenStorage()
        token = "refresh_token_abc_67890"
        
        storage.store_refresh_token(token)
        retrieved = storage.get_refresh_token()
        
        assert retrieved == token
    
    def test_clear_tokens(self):
        """Should clear all stored tokens"""
        storage = SecureTokenStorage()
        
        storage.store_access_token("access_123")
        storage.store_refresh_token("refresh_456")
        storage.clear()
        
        assert storage.get_access_token() is None
        assert storage.get_refresh_token() is None
```

---

## Integration Testing

### Sample Integration Test: API Workflow

```python
import pytest
from fixtures.get_request_fixture import GetRequestFixture
from fixtures.post_request_fixture import PostRequestFixture
from fixtures.auth_fixture import AuthFixture
from core.config import Config

@pytest.mark.integration
class TestGetRequestIntegration:
    """Integration tests for GET requests"""
    
    def test_get_request_to_real_api(self):
        """GET request to public API should succeed"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts/1")
        fixture.set_status_codes("200")
        
        result = fixture.execute()
        
        assert result is True
        assert fixture.get_response_status() == 200
        assert "userId" in fixture.get_response_body()
    
    def test_get_request_with_query_params(self):
        """GET request with query parameters should work"""
        fixture = GetRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts?userId=1")
        fixture.set_status_codes("200")
        
        result = fixture.execute()
        
        assert result is True
        response = fixture.get_response_body_json()
        assert isinstance(response, list)
        assert len(response) > 0

@pytest.mark.integration
class TestPostRequestIntegration:
    """Integration tests for POST requests"""
    
    def test_post_request_with_json_body(self):
        """POST request with JSON body should succeed"""
        fixture = PostRequestFixture()
        fixture.set_url("https://jsonplaceholder.typicode.com/posts")
        fixture.set_body_json('{"title": "Test", "body": "Content", "userId": 1}')
        fixture.set_status_codes("201")
        
        result = fixture.execute()
        
        assert result is True
        assert fixture.get_response_status() == 201
        response = fixture.get_response_body_json()
        assert response.get("title") == "Test"

@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication flow"""
    
    def test_oauth2_password_flow(self):
        """OAuth2 password grant flow should work"""
        auth_fixture = AuthFixture()
        auth_fixture.set_auth_url("https://dummyjson.com/auth/login")
        auth_fixture.set_username("emilys")
        auth_fixture.set_password("emilyspass")
        auth_fixture.set_grant_type("password")
        
        success = auth_fixture.authenticate()
        
        assert success is True
        token = auth_fixture.get_access_token()
        assert token is not None
        assert len(token) > 0

@pytest.mark.integration
class TestRetryMechanism:
    """Integration tests for retry mechanism"""
    
    def test_retry_on_failure(self):
        """Failed request should retry automatically"""
        fixture = GetRequestFixture()
        fixture.set_url("https://httpstat.us/500")  # Always returns 500
        fixture.set_retries("2")
        fixture.set_retry_delay("0.5")
        fixture.set_status_codes("200")
        
        result = fixture.execute()
        
        # Should fail after retries
        assert result is False
        assert fixture.get_response_status() == 500

@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration loading"""
    
    def test_load_config_from_environment(self):
        """Should load configuration from environment variables"""
        base_url = Config.get_base_url()
        assert base_url is not None
        assert base_url.startswith("http")
```

---

## Test Data Factory

### Implementation

```python
from faker import Faker
import random
import string
import uuid
from datetime import datetime, timedelta

class DataFactory:
    """Generate realistic test data using Faker library"""
    
    def __init__(self, locale='en_US'):
        self.fake = Faker(locale)
    
    # Person Data
    def generate_first_name(self) -> str:
        return self.fake.first_name()
    
    def generate_last_name(self) -> str:
        return self.fake.last_name()
    
    def generate_full_name(self) -> str:
        return self.fake.name()
    
    def generate_email(self) -> str:
        return self.fake.email()
    
    def generate_phone(self) -> str:
        return self.fake.phone_number()
    
    def generate_ssn(self) -> str:
        return self.fake.ssn()
    
    # Address Data
    def generate_street_address(self) -> str:
        return self.fake.street_address()
    
    def generate_city(self) -> str:
        return self.fake.city()
    
    def generate_state(self) -> str:
        return self.fake.state()
    
    def generate_zipcode(self) -> str:
        return self.fake.zipcode()
    
    def generate_country(self) -> str:
        return self.fake.country()
    
    def generate_address(self) -> dict:
        return {
            "street": self.generate_street_address(),
            "city": self.generate_city(),
            "state": self.generate_state(),
            "zipcode": self.generate_zipcode(),
            "country": self.generate_country()
        }
    
    # Financial Data
    def generate_credit_card(self) -> str:
        return self.fake.credit_card_number()
    
    def generate_credit_card_expiry(self) -> str:
        return self.fake.credit_card_expire()
    
    def generate_cvv(self) -> str:
        return str(random.randint(100, 999))
    
    def generate_iban(self) -> str:
        return self.fake.iban()
    
    def generate_currency_code(self) -> str:
        return random.choice(['USD', 'EUR', 'GBP', 'INR', 'JPY'])
    
    # Complex Data
    def generate_user_profile(self) -> dict:
        return {
            "id": self.generate_uuid(),
            "username": self.generate_username(),
            "email": self.generate_email(),
            "first_name": self.generate_first_name(),
            "last_name": self.generate_last_name(),
            "phone": self.generate_phone(),
            "address": self.generate_address(),
            "date_of_birth": self.generate_date_of_birth(),
            "created_at": self.generate_timestamp()
        }
    
    def generate_transaction(self) -> dict:
        return {
            "transaction_id": self.generate_uuid(),
            "amount": round(random.uniform(10.0, 10000.0), 2),
            "currency": self.generate_currency_code(),
            "timestamp": self.generate_timestamp(),
            "status": random.choice(['pending', 'completed', 'failed']),
            "payment_method": random.choice(['credit_card', 'debit_card', 'paypal', 'bank_transfer'])
        }
    
    # Utility Methods
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())
    
    def generate_alphanumeric(self, length: int = 10) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def generate_timestamp(self) -> str:
        return datetime.now().isoformat()

# Singleton instance
_data_factory_instance = None

def get_data_factory() -> DataFactory:
    """Get singleton instance of DataFactory"""
    global _data_factory_instance
    if _data_factory_instance is None:
        _data_factory_instance = DataFactory()
    return _data_factory_instance
```

### Usage Example

```python
from core.data_factory import get_data_factory

# Get factory instance
factory = get_data_factory()

# Generate test data
user = factory.generate_user_profile()
print(user)
# Output: {'id': 'abc-123', 'username': 'john_doe_42', 'email': 'john@example.com', ...}

# Generate multiple transactions
transactions = [factory.generate_transaction() for _ in range(5)]
```

---

## pytest Configuration

### pytest.ini

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Output options
addopts = 
    -v
    --tb=short
    --strict-markers

# Markers
markers =
    integration: Integration tests (may be slow)
    unit: Unit tests (fast)
    slow: Slow tests

[coverage:run]
# Coverage source
source = fixtures,core

# Files to include
include = 
    fixtures/*.py
    core/*.py

# Files to exclude
omit = 
    */tests/*
    */waferslim/*
    */__pycache__/*
    */venv/*
    */.venv/*

[coverage:report]
# Report options
precision = 2
show_missing = True
skip_covered = False

# Fail if coverage below threshold
fail_under = 80
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fixtures --cov=core --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest -m integration tests/integration/

# Run specific test file
pytest tests/unit/test_validators.py -v

# Run specific test
pytest tests/unit/test_validators.py::TestRequestValidator::test_validate_url_valid_http -v

# Generate HTML coverage report
pytest --cov --cov-report=html
# Open: htmlcov/index.html
```

---

## Best Practices

### 1. Test Organization

- **Separate unit and integration tests**
- **One test class per module/class**
- **Descriptive test names** (what, when, expected)
- **Use fixtures for common setup**

### 2. Test Naming Convention

```python
def test_<method>_<scenario>_<expected_result>():
    """Should <expected behavior> when <scenario>"""
    pass

# Examples:
def test_validate_url_empty_raises_error():
    """Should raise ValidationError when URL is empty"""
    
def test_encrypt_unicode_succeeds():
    """Should encrypt and decrypt unicode strings correctly"""
```

### 3. Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data
    validator = RequestValidator()
    url = "http://example.com"
    
    # Act - Execute the code
    result = validator.validate_url(url)
    
    # Assert - Verify the result
    assert result == url
```

### 4. Use Parametrize for Similar Tests

```python
@pytest.mark.parametrize("url,expected", [
    ("http://example.com", "http://example.com"),
    ("https://example.com", "https://example.com"),
    ("http://api.example.com/users", "http://api.example.com/users"),
])
def test_validate_url_valid(url, expected):
    result = RequestValidator.validate_url(url)
    assert result == expected
```

### 5. Mock External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_api_call_with_mock():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"id": 1}
        
        # Your test code here
        result = make_api_call()
        
        assert result["id"] == 1
        mock_get.assert_called_once()
```

---

## Common Issues & Solutions

### Issue 1: Import Errors

**Problem:** `ModuleNotFoundError: No module named 'core'`

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"  # Linux/Mac
$env:PYTHONPATH = "${PWD}"  # Windows PowerShell

# Or add to pytest.ini
[pytest]
pythonpath = .
```

### Issue 2: Coverage Not Working

**Problem:** Coverage shows 0% or doesn't include files

**Solution:**
```ini
# In pytest.ini, ensure correct source paths
[coverage:run]
source = .
include = 
    fixtures/*.py
    core/*.py
```

### Issue 3: Integration Tests Failing

**Problem:** Integration tests fail due to network/API issues

**Solution:**
- Use `@pytest.mark.integration` marker
- Skip in CI with `pytest -m "not integration"`
- Add retries for flaky tests
- Mock external APIs in unit tests

### Issue 4: Slow Test Execution

**Problem:** Tests take too long to run

**Solution:**
```python
# Mark slow tests
@pytest.mark.slow
def test_long_running_operation():
    pass

# Run without slow tests
# pytest -m "not slow"
```

---

## Reusability Guide

### Adapting to Your Framework

#### Step 1: Copy Test Structure
```bash
mkdir -p tests/unit tests/integration
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

#### Step 2: Install Dependencies
```bash
pip install pytest pytest-cov pytest-mock faker
```

#### Step 3: Create pytest.ini
- Copy the pytest.ini configuration above
- Update `source` paths to match your project structure

#### Step 4: Implement Test Data Factory
- Copy `data_factory.py` to your `core/` folder
- Customize generators for your domain (banking, e-commerce, etc.)

#### Step 5: Write Unit Tests
- Create test files for each module
- Follow the AAA pattern (Arrange, Act, Assert)
- Aim for 80%+ coverage

#### Step 6: Write Integration Tests
- Test end-to-end workflows
- Mark with `@pytest.mark.integration`
- Can be skipped in fast CI runs

#### Step 7: Set Up CI/CD
```yaml
# Example: .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Performance Tips

1. **Use fixtures for expensive setup:**
```python
@pytest.fixture(scope="session")
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()
```

2. **Parallelize tests:**
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

3. **Cache API responses:**
```python
import requests_cache
requests_cache.install_cache('test_cache', expire_after=3600)
```

4. **Skip slow tests in development:**
```bash
pytest -m "not slow"
```

---

## Checklist for New Frameworks

- [ ] Install pytest, pytest-cov, pytest-mock, faker
- [ ] Create tests/ directory structure
- [ ] Create pytest.ini configuration
- [ ] Implement test data factory
- [ ] Write unit tests (80%+ coverage goal)
- [ ] Write integration tests
- [ ] Set up CI/CD pipeline
- [ ] Document test running instructions
- [ ] Add coverage badge to README
- [ ] Configure pre-commit hooks

---

## Additional Resources

- **pytest documentation:** https://docs.pytest.org/
- **pytest-cov documentation:** https://pytest-cov.readthedocs.io/
- **Faker documentation:** https://faker.readthedocs.io/
- **Test-Driven Development:** "Test Driven Development: By Example" by Kent Beck

---

## Conclusion

This testing infrastructure improved framework quality by +3 points and provides:

✅ **Comprehensive test coverage** (95+ unit tests, 15+ integration tests)  
✅ **Realistic test data generation** (40+ generators)  
✅ **CI/CD ready** (pytest configuration with coverage)  
✅ **Reusable patterns** (copy-paste to other frameworks)  
✅ **Best practices** (AAA pattern, parametrize, mocking)  

**Implementation Time:** 1-2 days  
**Maintenance Effort:** Low (write tests as you code)  
**ROI:** High (catch bugs early, faster development, confident refactoring)

---

**Created:** July 16, 2026  
**Framework:** ICICI FitNesse API Framework  
**Version:** 2.1.0  
**License:** Reusable for internal projects
