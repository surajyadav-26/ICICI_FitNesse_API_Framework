"""
Unit tests for TokenEncryption and SecureTokenStorage classes
Tests encryption, decryption, and secure token storage
"""
import pytest
from core.token_encryption import TokenEncryption, SecureTokenStorage, get_secure_storage


class TestTokenEncryption:
    """Test suite for TokenEncryption class"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip"""
        encryptor = TokenEncryption()
        plaintext = "my_secret_token_12345"
        
        encrypted = encryptor.encrypt(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0
        
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string returns empty"""
        encryptor = TokenEncryption()
        encrypted = encryptor.encrypt("")
        assert encrypted == ""
    
    def test_decrypt_empty_string(self):
        """Test decrypting empty string returns empty"""
        encryptor = TokenEncryption()
        decrypted = encryptor.decrypt("")
        assert decrypted == ""
    
    def test_decrypt_with_wrong_key_fails(self):
        """Test decryption with wrong key returns empty"""
        encryptor1 = TokenEncryption()
        encryptor2 = TokenEncryption()  # Different key
        
        plaintext = "secret_token"
        encrypted = encryptor1.encrypt(plaintext)
        
        # Decrypting with different key should fail
        decrypted = encryptor2.decrypt(encrypted)
        assert decrypted == ""  # Returns empty on failure
    
    def test_encrypt_decrypt_unicode(self):
        """Test encrypting Unicode characters"""
        encryptor = TokenEncryption()
        plaintext = "token_with_émojis_🔐"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_generate_key_returns_valid_key(self):
        """Test key generation returns valid base64 key"""
        key = TokenEncryption.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0
        
        # Should be able to create encryptor with generated key
        encryptor = TokenEncryption(key)
        assert encryptor is not None


class TestSecureTokenStorage:
    """Test suite for SecureTokenStorage class"""
    
    def test_store_and_retrieve_access_token(self):
        """Test storing and retrieving access token"""
        storage = SecureTokenStorage()
        token = "access_token_12345"
        
        storage.store_access_token(token)
        retrieved = storage.get_access_token()
        assert retrieved == token
    
    def test_store_and_retrieve_refresh_token(self):
        """Test storing and retrieving refresh token"""
        storage = SecureTokenStorage()
        token = "refresh_token_67890"
        
        storage.store_refresh_token(token)
        retrieved = storage.get_refresh_token()
        assert retrieved == token
    
    def test_store_and_retrieve_token_type(self):
        """Test storing and retrieving token type"""
        storage = SecureTokenStorage()
        
        storage.store_token_type("Bearer")
        assert storage.get_token_type() == "Bearer"
    
    def test_store_and_retrieve_expires_at(self):
        """Test storing and retrieving expiration timestamp"""
        storage = SecureTokenStorage()
        import time
        expires_at = int(time.time()) + 3600
        
        storage.store_expires_at(expires_at)
        assert storage.get_expires_at() == expires_at
    
    def test_is_token_expired_not_expired(self):
        """Test token not expired when expiry is in future"""
        storage = SecureTokenStorage()
        import time
        expires_at = int(time.time()) + 3600  # 1 hour from now
        
        storage.store_expires_at(expires_at)
        assert not storage.is_token_expired()
    
    def test_is_token_expired_expired(self):
        """Test token expired when expiry is in past"""
        storage = SecureTokenStorage()
        import time
        expires_at = int(time.time()) - 3600  # 1 hour ago
        
        storage.store_expires_at(expires_at)
        assert storage.is_token_expired()
    
    def test_is_token_expired_zero_timestamp(self):
        """Test token not expired when timestamp is zero"""
        storage = SecureTokenStorage()
        storage.store_expires_at(0)
        assert not storage.is_token_expired()
    
    def test_clear_tokens(self):
        """Test clearing all tokens"""
        storage = SecureTokenStorage()
        
        storage.store_access_token("access")
        storage.store_refresh_token("refresh")
        storage.store_token_type("Bearer")
        storage.store_expires_at(123456)
        
        storage.clear_tokens()
        
        assert storage.get_access_token() == ""
        assert storage.get_refresh_token() == ""
        assert storage.get_token_type() == "Bearer"  # Resets to default
        assert storage.get_expires_at() == 0
    
    def test_get_access_token_empty_when_not_set(self):
        """Test getting access token when not set returns empty"""
        storage = SecureTokenStorage()
        assert storage.get_access_token() == ""
    
    def test_get_refresh_token_empty_when_not_set(self):
        """Test getting refresh token when not set returns empty"""
        storage = SecureTokenStorage()
        assert storage.get_refresh_token() == ""
    
    def test_is_encryption_enabled_returns_boolean(self):
        """Test is_encryption_enabled returns boolean"""
        storage = SecureTokenStorage()
        result = storage.is_encryption_enabled()
        assert isinstance(result, bool)


class TestGlobalSecureStorage:
    """Test global secure storage instance"""
    
    def test_get_secure_storage_returns_instance(self):
        """Test get_secure_storage returns SecureTokenStorage instance"""
        storage = get_secure_storage()
        assert isinstance(storage, SecureTokenStorage)
    
    def test_get_secure_storage_returns_same_instance(self):
        """Test get_secure_storage returns singleton"""
        storage1 = get_secure_storage()
        storage2 = get_secure_storage()
        assert storage1 is storage2
