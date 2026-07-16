"""
Token Encryption Module
Securely encrypts and decrypts OAuth tokens and sensitive data.
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from core.logger import logger


class TokenEncryption:
    """
    Handles encryption and decryption of sensitive tokens.
    Uses Fernet (symmetric encryption) with AES-128-CBC.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryptor with key.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, generates new key.
        """
        if encryption_key:
            try:
                self._cipher = Fernet(encryption_key.encode())
            except Exception as e:
                logger.error(f"[Encryption] Invalid encryption key: {e}")
                logger.warning("[Encryption] Generating new key. Tokens encrypted with old key cannot be decrypted!")
                self._cipher = Fernet(Fernet.generate_key())
        else:
            # Generate new key if none provided
            self._cipher = Fernet(Fernet.generate_key())
            logger.warning("[Encryption] No encryption key provided. Using temporary key (tokens won't persist across restarts)")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self._cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"[Encryption] Failed to encrypt data: {e}")
            return ""
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""
        
        try:
            decrypted_bytes = self._cipher.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("[Encryption] Failed to decrypt: Invalid token or wrong key")
            return ""
        except Exception as e:
            logger.error(f"[Encryption] Decryption error: {e}")
            return ""
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate new Fernet encryption key.
        
        Returns:
            Base64-encoded key string
        """
        return Fernet.generate_key().decode()


class SecureTokenStorage:
    """
    Secure storage for OAuth tokens with encryption.
    """
    
    def __init__(self):
        # Initialize encryptor
        from core.config import Config
        encryption_key = Config.TOKEN_ENCRYPTION_KEY
        
        if encryption_key:
            self._encryptor = TokenEncryption(encryption_key)
            self._encryption_enabled = True
        else:
            self._encryptor = None
            self._encryption_enabled = False
            logger.warning("[TokenStorage] Encryption disabled. Set TOKEN_ENCRYPTION_KEY in .env to enable.")
        
        # Storage
        self._access_token_encrypted = ""
        self._refresh_token_encrypted = ""
        self._token_type = "Bearer"
        self._expires_at = 0
    
    def store_access_token(self, token: str) -> None:
        """
        Store access token (encrypted if encryption enabled).
        
        Args:
            token: Access token to store
        """
        if self._encryption_enabled and self._encryptor:
            self._access_token_encrypted = self._encryptor.encrypt(token)
            logger.debug("[TokenStorage] Access token stored (encrypted)")
        else:
            self._access_token_encrypted = token
            logger.debug("[TokenStorage] Access token stored (plaintext)")
    
    def get_access_token(self) -> str:
        """
        Retrieve access token (decrypted if encrypted).
        
        Returns:
            Access token string
        """
        if not self._access_token_encrypted:
            return ""
        
        if self._encryption_enabled and self._encryptor:
            return self._encryptor.decrypt(self._access_token_encrypted)
        else:
            return self._access_token_encrypted
    
    def store_refresh_token(self, token: str) -> None:
        """Store refresh token (encrypted)"""
        if self._encryption_enabled and self._encryptor:
            self._refresh_token_encrypted = self._encryptor.encrypt(token)
            logger.debug("[TokenStorage] Refresh token stored (encrypted)")
        else:
            self._refresh_token_encrypted = token
            logger.debug("[TokenStorage] Refresh token stored (plaintext)")
    
    def get_refresh_token(self) -> str:
        """Retrieve refresh token (decrypted)"""
        if not self._refresh_token_encrypted:
            return ""
        
        if self._encryption_enabled and self._encryptor:
            return self._encryptor.decrypt(self._refresh_token_encrypted)
        else:
            return self._refresh_token_encrypted
    
    def store_token_type(self, token_type: str) -> None:
        """Store token type (usually 'Bearer')"""
        self._token_type = token_type
    
    def get_token_type(self) -> str:
        """Get token type"""
        return self._token_type
    
    def store_expires_at(self, expires_at: int) -> None:
        """Store token expiration timestamp"""
        self._expires_at = expires_at
    
    def get_expires_at(self) -> int:
        """Get token expiration timestamp"""
        return self._expires_at
    
    def is_token_expired(self) -> bool:
        """Check if access token has expired"""
        import time
        if self._expires_at == 0:
            return False
        return time.time() >= self._expires_at
    
    def clear_tokens(self) -> None:
        """Clear all stored tokens"""
        self._access_token_encrypted = ""
        self._refresh_token_encrypted = ""
        self._token_type = "Bearer"
        self._expires_at = 0
        logger.debug("[TokenStorage] All tokens cleared")
    
    def is_encryption_enabled(self) -> bool:
        """Check if encryption is enabled"""
        return self._encryption_enabled


# Global secure token storage instance
_secure_storage = SecureTokenStorage()


def get_secure_storage() -> SecureTokenStorage:
    """Get global secure token storage instance"""
    return _secure_storage
