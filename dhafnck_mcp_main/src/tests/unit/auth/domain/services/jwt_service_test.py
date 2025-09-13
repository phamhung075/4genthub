"""
Tests for JWT Service - Token generation and validation

This module tests JWT token creation, validation, and refresh token management.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from fastmcp.auth.domain.services.jwt_service import JWTService


class TestJWTService:
    """Test suite for JWTService"""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service instance for testing"""
        return JWTService(secret_key="test-secret-key-12345", issuer="test-issuer")
    
    def test_init_requires_secret_key(self):
        """Test that JWTService requires a secret key"""
        with pytest.raises(ValueError, match="Secret key is required"):
            JWTService(secret_key="", issuer="test")
    
    def test_create_access_token(self, jwt_service):
        """Test access token creation with standard claims"""
        user_id = "user123"
        email = "test@example.com"
        roles = ["user", "admin"]
        
        token = jwt_service.create_access_token(user_id, email, roles)
        
        # Decode token to verify contents (skip audience validation for testing)
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["roles"] == roles
        assert payload["type"] == "access"
        assert payload["aud"] == "mcp-server"  # Default audience
        assert payload["iss"] == jwt_service.issuer
        assert "jti" in payload  # JWT ID should be present
        assert "iat" in payload
        assert "exp" in payload
        
        # Verify expiration is correct
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        duration = (exp_time - iat_time).total_seconds()
        expected = 15 * 60  # 15 minutes
        assert abs(duration - expected) < 60, f"Expected ~{expected}s, got {duration}s"
    
    def test_create_access_token_with_additional_claims(self, jwt_service):
        """Test access token creation with additional claims"""
        additional_claims = {"department": "Engineering", "level": 5}
        
        token = jwt_service.create_access_token(
            "user123",
            "test@example.com",
            ["user"],
            additional_claims=additional_claims
        )
        
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        assert payload["department"] == "Engineering"
        assert payload["level"] == 5
    
    def test_create_refresh_token(self, jwt_service):
        """Test refresh token creation"""
        user_id = "user123"
        
        token, token_family = jwt_service.create_refresh_token(user_id)
        
        # Verify token family is returned
        assert token_family is not None
        assert len(token_family) == 32  # hex string of 16 bytes
        
        # Decode and verify token
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert payload["family"] == token_family
        assert payload["version"] == 0
        assert payload["iss"] == jwt_service.issuer
        
        # Verify expiration is 30 days
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        assert (exp_time - iat_time).days == 30
    
    def test_create_refresh_token_with_family(self, jwt_service):
        """Test refresh token creation with existing token family"""
        user_id = "user123"
        existing_family = "existing-family-id"
        token_version = 3
        
        token, returned_family = jwt_service.create_refresh_token(
            user_id,
            token_family=existing_family,
            token_version=token_version
        )
        
        assert returned_family == existing_family
        
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        assert payload["family"] == existing_family
        assert payload["version"] == token_version
    
    def test_create_reset_token(self, jwt_service):
        """Test password reset token creation"""
        user_id = "user123"
        email = "test@example.com"
        
        token = jwt_service.create_reset_token(user_id, email)
        
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "reset"
        assert payload["iss"] == jwt_service.issuer
        
        # Verify expiration is 24 hours
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        duration = (exp_time - iat_time).total_seconds()
        expected = 24 * 3600  # 24 hours
        assert abs(duration - expected) < 300, f"Expected ~{expected}s, got {duration}s"
    
    def test_verify_valid_access_token(self, jwt_service):
        """Test verification of valid access token"""
        user_id = "user123"
        email = "test@example.com"
        roles = ["user"]
        
        token = jwt_service.create_access_token(user_id, email, roles)
        payload = jwt_service.verify_access_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["roles"] == roles
        assert payload["type"] == "access"
    
    def test_verify_token_type_mismatch(self, jwt_service):
        """Test verification fails with wrong token type"""
        # Create refresh token but try to verify as access token
        token, _ = jwt_service.create_refresh_token("user123")
        
        payload = jwt_service.verify_access_token(token)
        assert payload is None
    
    def test_verify_token_api_token_compatibility(self, jwt_service):
        """Test api_token type is accepted for access token"""
        # Create token with api_token type
        token_payload = {
            "sub": "user123",
            "type": "api_token",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iss": jwt_service.issuer,
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        # Should accept api_token as access token
        payload = jwt_service.verify_access_token(token)
        assert payload is not None
        assert payload["type"] == "api_token"
    
    def test_verify_expired_token(self, jwt_service):
        """Test verification of expired token"""
        # Create token that's already expired
        now = datetime.now(timezone.utc)
        token_payload = {
            "sub": "user123",
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": jwt_service.issuer,
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        payload = jwt_service.verify_access_token(token)
        assert payload is None
    
    def test_verify_invalid_token(self, jwt_service):
        """Test verification of invalid token"""
        payload = jwt_service.verify_access_token("invalid.token.here")
        assert payload is None
    
    def test_verify_token_wrong_secret(self, jwt_service):
        """Test verification fails with wrong secret"""
        # Create token with different secret
        token_payload = {
            "sub": "user123",
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iss": jwt_service.issuer,
        }
        token = jwt.encode(token_payload, "wrong-secret", algorithm=jwt_service.ALGORITHM)
        
        payload = jwt_service.verify_access_token(token)
        assert payload is None
    
    def test_verify_token_without_issuer(self, jwt_service):
        """Test verification of token without issuer (compatibility mode)"""
        # Create token without issuer
        token_payload = {
            "sub": "user123",
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        # Should still verify successfully
        payload = jwt_service.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
    
    def test_refresh_access_token(self, jwt_service):
        """Test refreshing access token with refresh token"""
        user_id = "user123"
        
        # Create initial refresh token
        refresh_token, token_family = jwt_service.create_refresh_token(user_id)
        
        # Use refresh token to get new tokens
        result = jwt_service.refresh_access_token(refresh_token)
        assert result is not None
        
        new_access_token, new_refresh_token = result
        
        # Verify new access token
        access_payload = jwt.decode(
            new_access_token,
            jwt_service.secret_key,
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"
        
        # Verify new refresh token
        refresh_payload = jwt.decode(
            new_refresh_token,
            jwt_service.secret_key,
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"
        assert refresh_payload["family"] == token_family
        assert refresh_payload["version"] == 1  # Version should be incremented
    
    def test_refresh_access_token_invalid(self, jwt_service):
        """Test refreshing with invalid refresh token"""
        result = jwt_service.refresh_access_token("invalid.refresh.token")
        assert result is None
    
    def test_extract_token_from_header(self, jwt_service):
        """Test extracting token from Authorization header"""
        # Valid Bearer token
        token = jwt_service.extract_token_from_header("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        
        # Case insensitive
        token = jwt_service.extract_token_from_header("bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        
        # Invalid formats
        assert jwt_service.extract_token_from_header("") is None
        assert jwt_service.extract_token_from_header("Token abc123") is None
        assert jwt_service.extract_token_from_header("Bearer") is None
        assert jwt_service.extract_token_from_header("Bearer token extra") is None
    
    def test_get_token_expiry(self, jwt_service):
        """Test getting token expiration time"""
        # Create token with known expiration
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(hours=1)
        
        token_payload = {
            "sub": "user123",
            "exp": int(exp_time.timestamp()),
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        expiry = jwt_service.get_token_expiry(token)
        assert expiry is not None
        assert abs((expiry - exp_time).total_seconds()) < 1
        
        # Test token without expiry
        token_payload = {"sub": "user123"}
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        expiry = jwt_service.get_token_expiry(token)
        assert expiry is None
        
        # Test invalid token
        expiry = jwt_service.get_token_expiry("invalid.token")
        assert expiry is None
    
    def test_is_token_expired(self, jwt_service):
        """Test checking if token is expired"""
        # Create expired token
        now = datetime.now(timezone.utc)
        token_payload = {
            "sub": "user123",
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        assert jwt_service.is_token_expired(token) is True
        
        # Create valid token
        token_payload = {
            "sub": "user123",
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(token_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        assert jwt_service.is_token_expired(token) is False
        
        # Invalid token
        assert jwt_service.is_token_expired("invalid.token") is True
    
    def test_verify_refresh_token(self, jwt_service):
        """Test verification of refresh token"""
        user_id = "user123"
        token, _ = jwt_service.create_refresh_token(user_id)
        
        payload = jwt_service.verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
    
    def test_verify_reset_token(self, jwt_service):
        """Test verification of reset token"""
        user_id = "user123"
        email = "test@example.com"
        token = jwt_service.create_reset_token(user_id, email)
        
        payload = jwt_service.verify_reset_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "reset"
    
    def test_create_access_token_custom_audience(self, jwt_service):
        """Test access token creation with custom audience"""
        user_id = "user123"
        email = "test@example.com"
        roles = ["user"]
        custom_audience = "custom-api"
        
        token = jwt_service.create_access_token(
            user_id, email, roles, audience=custom_audience
        )
        
        payload = jwt.decode(
            token, 
            jwt_service.secret_key, 
            algorithms=[jwt_service.ALGORITHM],
            options={"verify_aud": False}
        )
        
        assert payload["aud"] == custom_audience
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
    
    def test_verify_token_with_audience_validation(self, jwt_service):
        """Test token verification with audience validation"""
        user_id = "user123"
        email = "test@example.com"
        roles = ["user"]
        audience = "test-audience"
        
        # Create token with specific audience
        token = jwt_service.create_access_token(
            user_id, email, roles, audience=audience
        )
        
        # Verify with correct audience - should succeed
        payload = jwt_service.verify_token(token, "access", audience)
        assert payload is not None
        assert payload["aud"] == audience
        
        # Verify with wrong audience - should fail
        payload = jwt_service.verify_token(token, "access", "wrong-audience")
        assert payload is None
        
        # Verify without audience check - should succeed
        payload = jwt_service.verify_token(token, "access")
        assert payload is not None
    
    def test_verify_supabase_token_simulation(self, jwt_service):
        """Test verification of Supabase-style token (no 'type' field, 'authenticated' audience)"""
        # Create token similar to Supabase structure (no 'type' field)
        now = datetime.now(timezone.utc)
        supabase_payload = {
            "sub": "user123",
            "email": "test@example.com", 
            "aud": "authenticated",  # Supabase uses this audience
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "supabase",
            # No 'type' field like Supabase tokens
        }
        
        token = jwt.encode(supabase_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        # Should accept token without 'type' field when checking for access token
        payload = jwt_service.verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["aud"] == "authenticated"
        assert "type" not in payload  # No type field in original Supabase token
    
    def test_verify_local_vs_supabase_audience_validation(self, jwt_service):
        """Test that audience validation correctly handles local vs Supabase tokens"""
        # Create local token (has 'type' field, should have 'mcp-server' audience)
        local_token = jwt_service.create_access_token(
            "user123", "test@example.com", ["user"], audience="mcp-server"
        )
        
        # Create Supabase-style token (no 'type' field, should have 'authenticated' audience)
        now = datetime.now(timezone.utc)
        supabase_payload = {
            "sub": "user456",
            "email": "supabase@example.com",
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": jwt_service.issuer,
        }
        supabase_token = jwt.encode(supabase_payload, jwt_service.secret_key, algorithm=jwt_service.ALGORITHM)
        
        # Local token should validate with 'mcp-server' audience
        payload = jwt_service.verify_token(local_token, "access", "mcp-server")
        assert payload is not None
        assert payload["type"] == "access"
        
        # Local token should fail with 'authenticated' audience
        payload = jwt_service.verify_token(local_token, "access", "authenticated")
        assert payload is None
        
        # Supabase token should validate with 'authenticated' audience
        payload = jwt_service.verify_token(supabase_token, "access", "authenticated")
        assert payload is not None
        assert "type" not in payload
        
        # Supabase token should fail with 'mcp-server' audience  
        payload = jwt_service.verify_token(supabase_token, "access", "mcp-server")
        assert payload is None