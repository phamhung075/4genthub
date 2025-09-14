"""Test suite for Keycloak Authentication Dependencies

Comprehensive test coverage for Keycloak authentication including:
- JWT token validation (RS256 and HS256)
- Keycloak token validation
- Local token validation
- JWKS client functionality
- Error handling and edge cases
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from fastmcp.auth.keycloak_dependencies import (
    get_keycloak_jwks_client,
    get_current_user_universal,
    validate_keycloak_token,
    validate_local_token,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    KEYCLOAK_URL,
    KEYCLOAK_REALM
)
from fastmcp.auth.domain.entities.user import User


class TestKeycloakJWKSClient:
    """Test JWKS client functionality"""
    
    def test_get_keycloak_jwks_client_not_configured(self):
        """Test JWKS client when Keycloak is not configured"""
        with patch.dict(os.environ, {"KEYCLOAK_URL": ""}):
            client = get_keycloak_jwks_client()
            assert client is None
    
    @patch('fastmcp.auth.keycloak_dependencies._keycloak_jwks_client', None)
    @patch('fastmcp.auth.keycloak_dependencies.KEYCLOAK_URL', 'https://keycloak.example.com')
    def test_get_keycloak_jwks_client_creates_new(self):
        """Test JWKS client creation"""
        with patch('jwt.PyJWKClient') as mock_jwks_class:
            mock_client = Mock()
            mock_jwks_class.return_value = mock_client
            
            # First call creates client
            client1 = get_keycloak_jwks_client()
            assert client1 == mock_client
            mock_jwks_class.assert_called_once()
            
            # Second call returns cached client
            client2 = get_keycloak_jwks_client()
            assert client2 == mock_client
            assert mock_jwks_class.call_count == 1  # Not called again
    
    @patch('fastmcp.auth.keycloak_dependencies._keycloak_jwks_client', None)
    @patch.dict(os.environ, {
        "KEYCLOAK_URL": "https://keycloak.test.com",
        "KEYCLOAK_REALM": "test-realm"
    })
    def test_get_keycloak_jwks_client_correct_url(self):
        """Test JWKS client uses correct URL"""
        with patch('jwt.PyJWKClient') as mock_jwks_class:
            get_keycloak_jwks_client()
            
            expected_url = "https://keycloak.test.com/realms/test-realm/protocol/openid-connect/certs"
            mock_jwks_class.assert_called_with(expected_url, cache_keys=True, lifespan=3600)


class TestUniversalUserAuthentication:
    """Test universal user authentication"""
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP credentials"""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test.jwt.token"
        )
    
    @pytest.mark.asyncio
    async def test_get_current_user_keycloak_token(self, mock_credentials):
        """Test authentication with Keycloak token"""
        # Create Keycloak-like token
        keycloak_payload = {
            "sub": "keycloak-user-123",
            "email": "user@keycloak.com",
            "preferred_username": "kcuser",
            "iss": "https://keycloak.example.com/realms/mcp"
        }
        
        with patch.dict(os.environ, {"KEYCLOAK_URL": "https://keycloak.example.com"}):
            with patch('fastmcp.auth.keycloak_dependencies.KEYCLOAK_URL', "https://keycloak.example.com"):
                with patch('jwt.decode') as mock_decode:
                    # First call returns unverified payload
                    mock_decode.return_value = keycloak_payload

                    with patch('fastmcp.auth.keycloak_dependencies.validate_keycloak_token') as mock_validate:
                        mock_user = User(
                            id="keycloak-user-123",
                            email="user@keycloak.com",
                            username="kcuser",
                            password_hash="keycloak-authenticated"
                        )
                        mock_validate.return_value = mock_user

                        user = await get_current_user_universal(mock_credentials)

                        assert user.id == "keycloak-user-123"
                        assert user.email == "user@keycloak.com"
                        mock_validate.assert_called_once_with("test.jwt.token")
    
    @pytest.mark.asyncio
    async def test_get_current_user_local_token(self, mock_credentials):
        """Test authentication with local token"""
        # Create local token payload
        local_payload = {
            "sub": "local-user-456",
            "email": "user@local.com",
            "iss": "local-issuer"
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = local_payload
            
            with patch('fastmcp.auth.keycloak_dependencies.validate_local_token') as mock_validate:
                mock_user = User(
                    id="local-user-456",
                    email="user@local.com",
                    username="user@local.com",
                    password_hash="local-jwt-authenticated"
                )
                mock_validate.return_value = mock_user
                
                user = await get_current_user_universal(mock_credentials)
                
                assert user.id == "local-user-456"
                assert user.email == "user@local.com"
                mock_validate.assert_called_once_with("test.jwt.token")
    
    @pytest.mark.asyncio
    async def test_get_current_user_decode_error(self, mock_credentials):
        """Test authentication with decode error"""
        with patch('jwt.decode') as mock_decode:
            # Use the DecodeError from jwt module
            mock_decode.side_effect = DecodeError("Invalid token")
            
            with patch('fastmcp.auth.keycloak_dependencies.validate_local_token') as mock_validate:
                mock_user = User(
                    id="fallback-user",
                    email="fallback@local.com",
                    username="fallback",
                    password_hash="local-jwt-authenticated"
                )
                mock_validate.return_value = mock_user
                
                user = await get_current_user_universal(mock_credentials)
                
                # Should fall back to local validation
                assert user.id == "fallback-user"
                mock_validate.assert_called_once_with("test.jwt.token")


class TestKeycloakTokenValidation:
    """Test Keycloak token validation"""
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_success(self):
        """Test successful Keycloak token validation"""
        token = "valid.keycloak.token"
        
        with patch.dict(os.environ, {
            "AUTH_PROVIDER": "keycloak",
            "KEYCLOAK_URL": "https://keycloak.example.com"
        }):
            with patch('fastmcp.auth.keycloak_dependencies.get_keycloak_jwks_client') as mock_get_client:
                # Mock JWKS client
                mock_client = Mock()
                mock_signing_key = Mock()
                mock_signing_key.key = "test-key"
                mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
                mock_get_client.return_value = mock_client
                
                # Mock jwt.decode
                with patch('jwt.decode') as mock_decode:
                    mock_decode.return_value = {
                        "sub": "kc-user-789",
                        "email": "kcuser@example.com",
                        "preferred_username": "kcuser789",
                        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                    }
                    
                    user = await validate_keycloak_token(token)
                    
                    assert user.id == "kc-user-789"
                    assert user.email == "kcuser@example.com"
                    assert user.username == "kcuser789"
                    assert user.password_hash == "keycloak-authenticated"
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_not_configured(self):
        """Test Keycloak validation when not configured"""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local", "KEYCLOAK_URL": ""}):
            with pytest.raises(HTTPException) as exc_info:
                await validate_keycloak_token("some.token")
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Keycloak not configured"
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_no_jwks_client(self):
        """Test Keycloak validation when JWKS client unavailable"""
        with patch.dict(os.environ, {
            "AUTH_PROVIDER": "keycloak",
            "KEYCLOAK_URL": "https://keycloak.example.com"
        }):
            with patch('fastmcp.auth.keycloak_dependencies.get_keycloak_jwks_client') as mock_get_client:
                mock_get_client.return_value = None
                
                with pytest.raises(HTTPException) as exc_info:
                    await validate_keycloak_token("some.token")
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Keycloak JWKS client not available"
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_expired(self):
        """Test Keycloak token validation with expired token"""
        with patch.dict(os.environ, {
            "AUTH_PROVIDER": "keycloak",
            "KEYCLOAK_URL": "https://keycloak.example.com"
        }):
            with patch('fastmcp.auth.keycloak_dependencies.get_keycloak_jwks_client') as mock_get_client:
                mock_client = Mock()
                mock_get_client.return_value = mock_client
                
                with patch('jwt.decode') as mock_decode:
                    mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await validate_keycloak_token("expired.token")
                    
                    assert exc_info.value.status_code == 401
                    assert exc_info.value.detail == "Token expired"
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_missing_sub(self):
        """Test Keycloak token validation with missing sub claim"""
        with patch.dict(os.environ, {
            "AUTH_PROVIDER": "keycloak",
            "KEYCLOAK_URL": "https://keycloak.example.com"
        }):
            with patch('fastmcp.auth.keycloak_dependencies.get_keycloak_jwks_client') as mock_get_client:
                mock_client = Mock()
                mock_signing_key = Mock()
                mock_signing_key.key = "test-key"
                mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
                mock_get_client.return_value = mock_client
                
                with patch('jwt.decode') as mock_decode:
                    mock_decode.return_value = {
                        "email": "user@example.com",
                        # Missing 'sub' claim
                    }
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await validate_keycloak_token("invalid.token")
                    
                    assert exc_info.value.status_code == 401
                    assert exc_info.value.detail == "Invalid token: missing user ID"
    
    @pytest.mark.asyncio
    async def test_validate_keycloak_token_no_email(self):
        """Test Keycloak token validation without email"""
        with patch.dict(os.environ, {
            "AUTH_PROVIDER": "keycloak",
            "KEYCLOAK_URL": "https://keycloak.example.com"
        }):
            with patch('fastmcp.auth.keycloak_dependencies.get_keycloak_jwks_client') as mock_get_client:
                mock_client = Mock()
                mock_signing_key = Mock()
                mock_signing_key.key = "test-key"
                mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
                mock_get_client.return_value = mock_client
                
                with patch('jwt.decode') as mock_decode:
                    mock_decode.return_value = {
                        "sub": "user-no-email",
                        "preferred_username": "noemail",
                        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                    }
                    
                    user = await validate_keycloak_token("valid.token")
                    
                    assert user.id == "user-no-email"
                    assert user.email == "noemail@keycloak.local"
                    assert user.username == "noemail"


class TestLocalTokenValidation:
    """Test local token validation"""
    
    def test_validate_local_token_success(self):
        """Test successful local token validation"""
        # Create valid token
        payload = {
            "sub": "local-123",
            "email": "local@example.com",
            "username": "localuser",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = payload
            
            user = validate_local_token("valid.local.token")
            
            assert user.id == "local-123"
            assert user.email == "local@example.com"
            assert user.username == "localuser"
            assert user.password_hash == "local-jwt-authenticated"
    
    def test_validate_local_token_no_secret(self):
        """Test local token validation without JWT secret"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            with pytest.raises(HTTPException) as exc_info:
                validate_local_token("some.token")
            
            assert exc_info.value.status_code == 500
            assert "JWT secret not set" in exc_info.value.detail
    
    def test_validate_local_token_expired(self):
        """Test local token validation with expired token"""
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            
            with pytest.raises(HTTPException) as exc_info:
                validate_local_token("expired.token")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Token expired"
    
    def test_validate_local_token_invalid(self):
        """Test local token validation with invalid token"""
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                validate_local_token("invalid.token")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid token"
    
    def test_validate_local_token_missing_user_id(self):
        """Test local token validation with missing user ID"""
        payload = {
            "email": "user@example.com",
            # Missing both 'sub' and 'user_id'
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = payload
            
            with pytest.raises(HTTPException) as exc_info:
                validate_local_token("invalid.token")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid token: missing user ID"
    
    def test_validate_local_token_user_id_fallback(self):
        """Test local token validation with user_id instead of sub"""
        payload = {
            "user_id": "legacy-user-456",  # Using user_id instead of sub
            "email": "legacy@example.com",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = payload
            
            user = validate_local_token("legacy.token")
            
            assert user.id == "legacy-user-456"
            assert user.email == "legacy@example.com"
    
    def test_validate_local_token_minimal(self):
        """Test local token validation with minimal claims"""
        payload = {
            "sub": "minimal-user",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = payload
            
            user = validate_local_token("minimal.token")
            
            assert user.id == "minimal-user"
            assert user.email == "minimal-user@local.dev"
            assert user.username == "minimal-user"
    
    def test_validate_local_token_expired_by_timestamp(self):
        """Test local token validation with expired timestamp"""
        payload = {
            "sub": "expired-user",
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
        }
        
        with patch('jwt.decode') as mock_decode:
            # Return payload without raising ExpiredSignatureError
            mock_decode.return_value = payload
            
            with pytest.raises(HTTPException) as exc_info:
                validate_local_token("expired.token")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Token expired"


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_keycloak_to_local_fallback(self):
        """Test fallback from Keycloak to local validation"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="ambiguous.token"
        )
        
        # First decode returns non-Keycloak issuer
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "user-123",
                "iss": "local-issuer"
            }
            
            with patch('fastmcp.auth.keycloak_dependencies.validate_local_token') as mock_validate:
                mock_user = User(
                    id="user-123",
                    email="user@local.com",
                    username="localuser",
                    password_hash="local-jwt-authenticated"
                )
                mock_validate.return_value = mock_user
                
                user = await get_current_user_universal(credentials)
                
                assert user.id == "user-123"
                mock_validate.assert_called_once()
    
    def test_clock_skew_tolerance(self):
        """Test that clock skew tolerance is applied"""
        # Token that expired 20 seconds ago (within 30 second leeway)
        payload = {
            "sub": "skew-user",
            "exp": (datetime.now(timezone.utc) - timedelta(seconds=20)).timestamp()
        }
        token = jwt.encode(payload, JWT_SECRET_KEY or "test-secret", algorithm=JWT_ALGORITHM)
        
        with patch('jwt.decode') as mock_decode:
            # Mock successful decode with leeway
            mock_decode.return_value = {**payload, "exp": (datetime.now(timezone.utc) + timedelta(seconds=10)).timestamp()}
            
            user = validate_local_token(token)
            
            # Verify leeway was passed
            mock_decode.assert_called_with(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                leeway=30
            )
            assert user.id == "skew-user"