"""
Configuration Management Module
Loads environment variables and provides centralized config access.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback to system environment variables
    load_dotenv()


class Config:
    """
    Centralized configuration management using environment variables.
    Falls back to safe defaults if variables not set.
    """
    
    # API Authentication
    API_ADMIN_USER = os.getenv("API_ADMIN_USER", "admin")
    API_ADMIN_PASS = os.getenv("API_ADMIN_PASS", "admin123")
    API_QA_USER = os.getenv("API_QA_USER", "qa")
    API_QA_PASS = os.getenv("API_QA_PASS", "qa123")
    API_DEV_USER = os.getenv("API_DEV_USER", "dev")
    API_DEV_PASS = os.getenv("API_DEV_PASS", "dev123")
    API_READER_USER = os.getenv("API_READER_USER", "reader")
    API_READER_PASS = os.getenv("API_READER_PASS", "reader123")
    
    # OAuth2 Configuration
    OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", "")
    OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "")
    OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL", "")
    
    # API Base URLs (never hardcoded - synced from the FitNesse UI environment drawer into .env)
    DEV_API_URL = os.getenv("DEV_API_URL", "")
    STAGING_API_URL = os.getenv("STAGING_API_URL", "")
    QA_API_URL = os.getenv("QA_API_URL", "")
    UAT_API_URL = os.getenv("UAT_API_URL", "")
    PROD_API_URL = os.getenv("PROD_API_URL", "")
    
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "1433"))
    DB_NAME = os.getenv("DB_NAME", "testdb")
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # UI Automation Config
    UI_BROWSER = os.getenv("UI_BROWSER", "chromium")
    UI_HEADLESS = os.getenv("UI_HEADLESS", "true").lower() == "true"
    UI_BASE_URL = os.getenv("UI_BASE_URL", "")
    UI_WORKERS = int(os.getenv("UI_WORKERS", "1"))
    
    # Environment-Wise UI URLs
    DEV_UI_URL = os.getenv("DEV_UI_URL", "")
    STAGING_UI_URL = os.getenv("STAGING_UI_URL", "")
    QA_UI_URL = os.getenv("QA_UI_URL", "")
    UAT_UI_URL = os.getenv("UAT_UI_URL", "")
    PROD_UI_URL = os.getenv("PROD_UI_URL", "")
    
    # Framework Configuration
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "15"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"
    
    # Token Encryption
    TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))
    SCREENSHOT_RETENTION_DAYS = int(os.getenv("SCREENSHOT_RETENTION_DAYS", "7"))
    
    # Visual testing (screenshot comparison against baselines in data/visual/baselines)
    VISUAL_THRESHOLD = float(os.getenv("VISUAL_THRESHOLD", "0.1"))              # allowed % of differing pixels
    VISUAL_PIXEL_TOLERANCE = int(os.getenv("VISUAL_PIXEL_TOLERANCE", "10"))     # 0-255 per colour channel
    VISUAL_UPDATE_BASELINE = os.getenv("VISUAL_UPDATE_BASELINE", "false").lower() == "true"
    VISUAL_FAIL_ON_NEW = os.getenv("VISUAL_FAIL_ON_NEW", "false").lower() == "true"  # strict mode for CI
    VISUAL_FULL_PAGE = os.getenv("VISUAL_FULL_PAGE", "true").lower() == "true"

    # Mock Server
    MOCK_SERVER_PORT = int(os.getenv("MOCK_SERVER_PORT", "8089"))
    
    @classmethod
    def get_base_url(cls, environment: str) -> str:
        """
        Get base URL for specified environment.
        
        Args:
            environment: One of 'dev', 'staging', 'uat', 'prod'
            
        Returns:
            Base URL string
            
        Raises:
            ValueError: If environment is invalid
        """
        env_map = {
            "dev": cls.DEV_API_URL,
            "staging": cls.STAGING_API_URL,
            "qa": cls.QA_API_URL,
            "uat": cls.UAT_API_URL,
            "prod": cls.PROD_API_URL,
            "production": cls.PROD_API_URL
        }
        
        env_lower = environment.lower()
        if env_lower not in env_map:
            raise ValueError(f"Invalid environment: {environment}. Must be one of: {list(env_map.keys())}")
        
        return cls._require_url(env_map[env_lower], env_lower, "API")
    
    @staticmethod
    def _require_url(url: str, environment: str, kind: str) -> str:
        """Fail clearly when an environment URL has not been set from the UI."""
        if not url:
            raise ValueError(f"{kind} URL for environment '{environment}' is not configured. Add it from the UI environment settings.")
        return url
    
    @classmethod
    def get_ui_url(cls, environment: str) -> str:
        """
        Get UI URL for specified environment.
        
        Args:
            environment: One of 'dev', 'staging', 'uat', 'prod'
            
        Returns:
            UI URL string
            
        Raises:
            ValueError: If environment is invalid
        """
        env_map = {
            "dev": cls.DEV_UI_URL,
            "staging": cls.STAGING_UI_URL,
            "qa": cls.QA_UI_URL,
            "uat": cls.UAT_UI_URL,
            "prod": cls.PROD_UI_URL,
            "production": cls.PROD_UI_URL
        }
        
        env_lower = environment.lower()
        if env_lower not in env_map:
            raise ValueError(f"Invalid environment: {environment}. Must be one of: {list(env_map.keys())}")
        
        return cls._require_url(env_map[env_lower], env_lower, "UI")
    
    @classmethod
    def get_credentials(cls, user_type: str = "admin") -> tuple:
        """
        Get username and password for specified user type.
        
        Args:
            user_type: One of 'admin', 'qa', 'dev', 'reader'
            
        Returns:
            Tuple of (username, password)
            
        Raises:
            ValueError: If user_type is invalid
        """
        creds_map = {
            "admin": (cls.API_ADMIN_USER, cls.API_ADMIN_PASS),
            "qa": (cls.API_QA_USER, cls.API_QA_PASS),
            "dev": (cls.API_DEV_USER, cls.API_DEV_PASS),
            "reader": (cls.API_READER_USER, cls.API_READER_PASS)
        }
        
        user_lower = user_type.lower()
        if user_lower not in creds_map:
            raise ValueError(f"Invalid user type: {user_type}. Must be one of: {list(creds_map.keys())}")
        
        return creds_map[user_lower]
    
    @classmethod
    def validate(cls) -> list:
        """
        Validate critical configuration values are set.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check if using default passwords (security risk in production)
        if cls.API_ADMIN_PASS == "admin123":
            errors.append("WARNING: Using default admin password. Set API_ADMIN_PASS in .env")
        
        # Check OAuth2 config if needed
        if cls.OAUTH2_TOKEN_URL and not cls.OAUTH2_CLIENT_ID:
            errors.append("ERROR: OAUTH2_TOKEN_URL set but OAUTH2_CLIENT_ID missing")
        
        # Check token encryption key
        if not cls.TOKEN_ENCRYPTION_KEY:
            errors.append("WARNING: TOKEN_ENCRYPTION_KEY not set. Token encryption disabled.")
        
        return errors
    
    @classmethod
    def print_config_summary(cls) -> None:
        """Print configuration summary (for debugging)"""
        print("\n=== Configuration Summary ===")
        print(f"Environment: {os.getenv('ENV', 'dev')}")
        print(f"Default Timeout: {cls.DEFAULT_TIMEOUT}s")
        print(f"Max Retries: {cls.MAX_RETRIES}")
        print(f"SSL Verify: {cls.SSL_VERIFY}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Mock Server Port: {cls.MOCK_SERVER_PORT}")
        
        # Check for warnings
        errors = cls.validate()
        if errors:
            print("\n⚠️  Configuration Warnings:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n✅ All configuration validated")
        print("============================\n")


# Auto-validate on import
_validation_errors = Config.validate()
if _validation_errors:
    import warnings
    for error in _validation_errors:
        warnings.warn(error, UserWarning)
