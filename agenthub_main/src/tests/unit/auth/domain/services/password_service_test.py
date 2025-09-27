"""Unit tests for PasswordService following DDD patterns"""

import pytest
import string
from unittest.mock import patch, MagicMock

from fastmcp.auth.domain.services.password_service import PasswordService


class TestPasswordService:
    """Test suite for PasswordService domain service following DDD patterns"""
    
    def test_hash_password_creates_valid_hash(self):
        """Test hash_password creates a valid bcrypt hash"""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)
        
        # Bcrypt hashes start with $2b$ (or $2a$ for older versions)
        assert hashed.startswith('$2b$') or hashed.startswith('$2a$')
        # Hash should be different from original password
        assert hashed != password
        # Hash should have proper length (60 chars for bcrypt)
        assert len(hashed) >= 60
    
    def test_hash_password_creates_unique_hashes(self):
        """Test that same password generates different hashes (due to salt)"""
        password = "SecurePassword123!"
        hash1 = PasswordService.hash_password(password)
        hash2 = PasswordService.hash_password(password)
        
        # Same password should produce different hashes due to random salt
        assert hash1 != hash2
    
    def test_verify_password_correct_password(self):
        """Test verify_password returns True for correct password"""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect_password(self):
        """Test verify_password returns False for incorrect password"""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password("WrongPassword", hashed) is False
        assert PasswordService.verify_password("securepassword123!", hashed) is False  # Case sensitive
        assert PasswordService.verify_password("SecurePassword123", hashed) is False  # Missing char
    
    def test_verify_password_handles_invalid_hash(self):
        """Test verify_password handles invalid hash gracefully"""
        password = "SecurePassword123!"
        
        # Invalid hash format
        assert PasswordService.verify_password(password, "invalid_hash") is False
        assert PasswordService.verify_password(password, "") is False
        assert PasswordService.verify_password(password, "123") is False
    
    def test_hash_password_validates_empty_password(self):
        """Test hash_password rejects empty password"""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password("")
        
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password(None)
    
    def test_hash_password_validates_min_length(self):
        """Test hash_password enforces minimum length"""
        with pytest.raises(ValueError, match=f"Password must be at least {PasswordService.MIN_PASSWORD_LENGTH} characters"):
            PasswordService.hash_password("short")
    
    def test_hash_password_validates_max_length(self):
        """Test hash_password enforces maximum length"""
        long_password = "a" * (PasswordService.MAX_PASSWORD_LENGTH + 1)
        with pytest.raises(ValueError, match=f"Password cannot exceed {PasswordService.MAX_PASSWORD_LENGTH} characters"):
            PasswordService.hash_password(long_password)
    
    def test_check_password_strength_weak_password(self):
        """Test check_password_strength identifies weak password"""
        analysis = PasswordService.check_password_strength("password")
        
        assert analysis["strength"] == "weak"
        assert analysis["score"] <= 2
        assert not analysis["has_uppercase"]
        assert not analysis["has_digit"]
        assert not analysis["has_special"]
        assert "Add uppercase letters" in analysis["suggestions"]
        assert "Add numbers" in analysis["suggestions"]
        assert "Add special characters" in analysis["suggestions"]
    
    def test_check_password_strength_medium_password(self):
        """Test check_password_strength identifies medium strength password"""
        analysis = PasswordService.check_password_strength("Password123")
        
        assert analysis["strength"] == "medium"
        assert 2 < analysis["score"] <= 4
        assert analysis["has_uppercase"]
        assert analysis["has_lowercase"]
        assert analysis["has_digit"]
        assert not analysis["has_special"]
        assert "Add special characters" in analysis["suggestions"]
    
    def test_check_password_strength_strong_password(self):
        """Test check_password_strength identifies strong password"""
        analysis = PasswordService.check_password_strength("SecureP@ssw0rd123!")
        
        assert analysis["strength"] == "strong"
        assert analysis["score"] > 4
        assert analysis["has_uppercase"]
        assert analysis["has_lowercase"]
        assert analysis["has_digit"]
        assert analysis["has_special"]
        assert len(analysis["suggestions"]) == 0 or analysis["suggestions"] == []
    
    def test_check_password_strength_length_scoring(self):
        """Test check_password_strength scores length appropriately"""
        # Short password (8 chars)
        short_analysis = PasswordService.check_password_strength("Pass123!")
        
        # Long password (12+ chars)
        long_analysis = PasswordService.check_password_strength("Password123!")
        
        # Longer password should have higher score
        assert long_analysis["score"] >= short_analysis["score"]
        assert long_analysis["length"] == 12
    
    def test_generate_secure_password_default_parameters(self):
        """Test generate_secure_password with default parameters"""
        password = PasswordService.generate_secure_password()
        
        assert len(password) == 16  # Default length
        analysis = PasswordService.check_password_strength(password)
        assert analysis["has_uppercase"]
        assert analysis["has_lowercase"]
        assert analysis["has_digit"]
        assert analysis["has_special"]
        assert analysis["strength"] == "strong"
    
    def test_generate_secure_password_custom_length(self):
        """Test generate_secure_password with custom length"""
        password_short = PasswordService.generate_secure_password(length=8)
        password_long = PasswordService.generate_secure_password(length=32)
        
        assert len(password_short) == 8
        assert len(password_long) == 32
    
    def test_generate_secure_password_enforces_min_max_length(self):
        """Test generate_secure_password enforces length constraints"""
        # Below minimum
        password_min = PasswordService.generate_secure_password(length=4)
        assert len(password_min) == PasswordService.MIN_PASSWORD_LENGTH
        
        # Above maximum
        password_max = PasswordService.generate_secure_password(length=200)
        assert len(password_max) == PasswordService.MAX_PASSWORD_LENGTH
    
    def test_generate_secure_password_custom_character_sets(self):
        """Test generate_secure_password with custom character sets"""
        # Only lowercase
        password = PasswordService.generate_secure_password(
            include_uppercase=False,
            include_digits=False,
            include_special=False
        )
        assert all(c in string.ascii_lowercase for c in password)
        
        # Only digits
        password = PasswordService.generate_secure_password(
            include_uppercase=False,
            include_lowercase=False,
            include_special=False
        )
        assert all(c in string.digits for c in password)
        
        # No character set specified (should use fallback)
        password = PasswordService.generate_secure_password(
            include_uppercase=False,
            include_lowercase=False,
            include_digits=False,
            include_special=False
        )
        assert len(password) > 0
    
    def test_generate_secure_password_uniqueness(self):
        """Test generate_secure_password generates unique passwords"""
        passwords = [PasswordService.generate_secure_password() for _ in range(10)]
        
        # All passwords should be unique
        assert len(set(passwords)) == 10
    
    def test_generate_reset_token_default_length(self):
        """Test generate_reset_token with default length"""
        token = PasswordService.generate_reset_token()
        
        # URL-safe base64 encoding increases length
        assert len(token) > 32
        # Should only contain URL-safe characters
        assert all(c in string.ascii_letters + string.digits + '-_' for c in token)
    
    def test_generate_reset_token_custom_length(self):
        """Test generate_reset_token with custom length"""
        token_short = PasswordService.generate_reset_token(length=16)
        token_long = PasswordService.generate_reset_token(length=64)
        
        assert len(token_short) > 16  # Base64 encoding increases length
        assert len(token_long) > 64
        assert len(token_long) > len(token_short)
    
    def test_generate_reset_token_uniqueness(self):
        """Test generate_reset_token generates unique tokens"""
        tokens = [PasswordService.generate_reset_token() for _ in range(10)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 10
    
    def test_needs_rehash_old_rounds(self):
        """Test needs_rehash detects old bcrypt rounds"""
        # Mock hash with old rounds (10)
        old_hash = "$2b$10$abcdefghijklmnopqrstuabcdefghijklmnopqrstuvwxyz123456"
        
        assert PasswordService.needs_rehash(old_hash) is True
    
    def test_needs_rehash_current_rounds(self):
        """Test needs_rehash returns False for current rounds"""
        # Create a hash with current rounds
        password = "TestPassword123!"
        current_hash = PasswordService.hash_password(password)
        
        assert PasswordService.needs_rehash(current_hash) is False
    
    def test_needs_rehash_invalid_format(self):
        """Test needs_rehash handles invalid hash format"""
        assert PasswordService.needs_rehash("invalid_hash") is False
        assert PasswordService.needs_rehash("") is False
        assert PasswordService.needs_rehash("$1$invalid") is False
    
    @patch('fastmcp.auth.domain.services.password_service.bcrypt.gensalt')
    @patch('fastmcp.auth.domain.services.password_service.bcrypt.hashpw')
    def test_hash_password_uses_correct_rounds(self, mock_hashpw, mock_gensalt):
        """Test hash_password uses correct bcrypt rounds"""
        mock_gensalt.return_value = b'$2b$12$salt'
        mock_hashpw.return_value = b'$2b$12$hashed'
        
        PasswordService.hash_password("TestPassword123!")
        
        mock_gensalt.assert_called_once_with(rounds=PasswordService.DEFAULT_ROUNDS)
    
    def test_verify_password_handles_bytes_and_string(self):
        """Test verify_password handles both bytes and string hashes"""
        password = "TestPassword123!"
        hashed_str = PasswordService.hash_password(password)
        hashed_bytes = hashed_str.encode('utf-8')
        
        # Should work with string hash
        assert PasswordService.verify_password(password, hashed_str) is True
        
        # Should work with bytes hash
        assert PasswordService.verify_password(password, hashed_bytes) is True
    
    @patch('fastmcp.auth.domain.services.password_service.logger')
    def test_verify_password_logs_exceptions(self, mock_logger):
        """Test verify_password logs exceptions for debugging"""
        # Force an exception by passing invalid types
        result = PasswordService.verify_password(123, "hash")
        
        assert result is False
        mock_logger.warning.assert_called()
        
    def test_password_service_constants(self):
        """Test PasswordService constants are reasonable"""
        assert PasswordService.DEFAULT_ROUNDS >= 10  # Minimum secure rounds
        assert PasswordService.DEFAULT_ROUNDS <= 15  # Maximum practical rounds
        assert PasswordService.MIN_PASSWORD_LENGTH >= 8  # Industry standard minimum
        assert PasswordService.MAX_PASSWORD_LENGTH <= 256  # Reasonable maximum
        assert PasswordService.MAX_PASSWORD_LENGTH > PasswordService.MIN_PASSWORD_LENGTH