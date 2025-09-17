"""Test suite for MCP Authentication Dependencies

Comprehensive test coverage for MCP authentication dependencies including:
- Frontend JWT token validation
- User extraction from tokens
- Optional authentication support
- Error handling and edge cases
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from fastmcp.auth.mcp_dependencies import (
    get_current_mcp_user,
    get_optional_mcp_user,
    FRONTEND_JWT_SECRET,
    FRONTEND_JWT_ALGORITHM
)
from fastmcp.auth.domain.entities.user import User


class TestGetCurrentMCPUser:
    """Test get_current_mcp_user dependency"""

    @pytest.fixture(autouse=True)
    def setup_jwt_secret(self):
        """Set up JWT secret for tests"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
            # Force reload of the constant
            import fastmcp.auth.mcp_dependencies as module
            module.FRONTEND_JWT_SECRET = "test-secret"
            yield

    @pytest.fixture
    def valid_token_payload(self):
        """Create valid token payload"""
        return {
            "sub": "user-123",
            "email": "test@example.com",
            "username": "testuser",
            "auth_provider": "keycloak",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp()
        }
    
    @pytest.fixture
    def valid_token(self, valid_token_payload):
        """Create valid JWT token"""
        return jwt.encode(
            valid_token_payload,
            "test-secret",  # Use same secret as setup_jwt_secret fixture
            algorithm=FRONTEND_JWT_ALGORITHM
        )
    
    @pytest.fixture
    def credentials(self, valid_token):
        """Create HTTP credentials with valid token"""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_success(self, credentials, valid_token_payload):
        """Test successful user authentication"""
        user = await get_current_mcp_user(credentials)
        
        assert isinstance(user, User)
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash == "keycloak-authenticated"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_no_jwt_secret(self, credentials):
        """Test authentication when JWT secret is not configured"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            # Force reload of the constant
            import fastmcp.auth.mcp_dependencies as module
            module.FRONTEND_JWT_SECRET = ""
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_mcp_user(credentials)
            
            assert exc_info.value.status_code == 500
            assert "JWT secret not set" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_invalid_token(self):
        """Test authentication with invalid token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.jwt.token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_mcp_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_expired_token(self):
        """Test authentication with expired token"""
        expired_payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
        }
        
        expired_token = jwt.encode(
            expired_payload,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=expired_token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_mcp_user(credentials)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_missing_user_id(self):
        """Test authentication with token missing user ID"""
        payload_no_id = {
            "email": "test@example.com",
            "username": "testuser",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            # Missing both 'sub' and 'user_id'
        }
        
        token = jwt.encode(
            payload_no_id,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_mcp_user(credentials)
        
        assert exc_info.value.status_code == 401
        assert "missing user ID" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_user_id_fallback(self):
        """Test authentication with user_id instead of sub"""
        payload_with_user_id = {
            "user_id": "legacy-user-456",  # Using user_id instead of sub
            "email": "legacy@example.com",
            "auth_provider": "local",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        token = jwt.encode(
            payload_with_user_id,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        user = await get_current_mcp_user(credentials)
        
        assert user.id == "legacy-user-456"
        assert user.email == "legacy@example.com"
        assert user.password_hash == "local-authenticated"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_minimal_payload(self):
        """Test authentication with minimal token payload"""
        minimal_payload = {
            "sub": "minimal-user",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        token = jwt.encode(
            minimal_payload,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        user = await get_current_mcp_user(credentials)
        
        assert user.id == "minimal-user"
        assert user.email == "minimal-user@unknown.local"
        assert user.username == "minimal-user"
        assert user.password_hash == "unknown-authenticated"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_with_auth_provider(self):
        """Test authentication with different auth providers"""
        providers = ["keycloak", "supabase", "google", "github"]
        
        for provider in providers:
            payload = {
                "sub": f"{provider}-user",
                "auth_provider": provider,
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            }
            
            token = jwt.encode(
                payload,
                "test-secret",
                algorithm=FRONTEND_JWT_ALGORITHM
            )
            
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token
            )
            
            user = await get_current_mcp_user(credentials)
            
            assert user.id == f"{provider}-user"
            assert user.email == f"{provider}-user@{provider}.local"
            assert user.password_hash == f"{provider}-authenticated"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_expired_by_timestamp(self):
        """Test token expiration check by timestamp"""
        with patch('jwt.decode') as mock_decode:
            # Return expired payload without raising ExpiredSignatureError
            mock_decode.return_value = {
                "sub": "user-123",
                "exp": (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
            }
            
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="some.token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_mcp_user(credentials)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Token expired"
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_exception_handling(self):
        """Test general exception handling"""
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Unexpected error")
            
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="some.token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_mcp_user(credentials)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Could not validate credentials"
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    @pytest.mark.asyncio
    async def test_get_current_mcp_user_http_exception_passthrough(self):
        """Test that HTTPException is passed through"""
        with patch('jwt.decode') as mock_decode:
            # Simulate an HTTPException being raised during processing
            custom_exc = HTTPException(
                status_code=403,
                detail="Custom forbidden error"
            )
            mock_decode.side_effect = custom_exc
            
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="some.token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_mcp_user(credentials)
            
            # Should pass through the custom exception
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Custom forbidden error"


class TestGetOptionalMCPUser:
    """Test get_optional_mcp_user dependency"""

    @pytest.fixture(autouse=True)
    def setup_jwt_secret(self):
        """Set up JWT secret for tests"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
            # Force reload of the constant
            import fastmcp.auth.mcp_dependencies as module
            module.FRONTEND_JWT_SECRET = "test-secret"
            yield

    @pytest.fixture
    def valid_credentials(self):
        """Create valid credentials"""
        payload = {
            "sub": "optional-user",
            "email": "optional@example.com",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        token = jwt.encode(
            payload,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
    
    @pytest.mark.asyncio
    async def test_get_optional_mcp_user_with_valid_credentials(self, valid_credentials):
        """Test optional auth with valid credentials"""
        user = await get_optional_mcp_user(valid_credentials)
        
        assert user is not None
        assert isinstance(user, User)
        assert user.id == "optional-user"
        assert user.email == "optional@example.com"
    
    @pytest.mark.asyncio
    async def test_get_optional_mcp_user_no_credentials(self):
        """Test optional auth without credentials"""
        user = await get_optional_mcp_user(None)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_optional_mcp_user_invalid_credentials(self):
        """Test optional auth with invalid credentials"""
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )
        
        user = await get_optional_mcp_user(invalid_credentials)
        
        # Should return None instead of raising exception
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_optional_mcp_user_expired_token(self):
        """Test optional auth with expired token"""
        expired_payload = {
            "sub": "expired-user",
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
        }
        
        expired_token = jwt.encode(
            expired_payload,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        expired_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=expired_token
        )
        
        user = await get_optional_mcp_user(expired_credentials)
        
        # Should return None instead of raising exception
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_optional_mcp_user_exception_handling(self):
        """Test optional auth exception handling"""
        with patch('fastmcp.auth.mcp_dependencies.get_current_mcp_user') as mock_get_user:
            # Simulate various exceptions
            exceptions = [
                HTTPException(status_code=401, detail="Unauthorized"),
                HTTPException(status_code=500, detail="Server error"),
                Exception("Unexpected error")
            ]
            
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="some.token"
            )
            
            for exc in exceptions:
                mock_get_user.side_effect = exc
                user = await get_optional_mcp_user(credentials)
                
                # Should always return None on any exception
                assert user is None


class TestIntegration:
    """Integration tests"""

    @pytest.fixture(autouse=True)
    def setup_jwt_secret(self):
        """Set up JWT secret for tests"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
            # Force reload of the constant
            import fastmcp.auth.mcp_dependencies as module
            module.FRONTEND_JWT_SECRET = "test-secret"
            yield

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow"""
        # Create token with all fields
        payload = {
            "sub": "integration-user",
            "email": "integration@example.com",
            "username": "integrationtest",
            "auth_provider": "keycloak",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        token = jwt.encode(
            payload,
            "test-secret",
            algorithm=FRONTEND_JWT_ALGORITHM
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Test required auth
        user = await get_current_mcp_user(credentials)
        assert user.id == "integration-user"
        assert user.email == "integration@example.com"
        assert user.username == "integrationtest"
        
        # Test optional auth with same credentials
        optional_user = await get_optional_mcp_user(credentials)
        assert optional_user is not None
        assert optional_user.id == user.id
    
    @pytest.mark.asyncio
    async def test_authentication_with_different_algorithms(self):
        """Test that only HS256 algorithm is accepted"""
        payload = {
            "sub": "algo-user",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        # Try to create token with different algorithm
        with patch('fastmcp.auth.mcp_dependencies.FRONTEND_JWT_ALGORITHM', 'RS256'):
            # This should fail because the secret is for HS256, not RS256
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="fake.rs256.token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_mcp_user(credentials)
            
            assert exc_info.value.status_code == 401


class TestConstants:
    """Test module constants"""
    
    def test_frontend_jwt_algorithm(self):
        """Test JWT algorithm constant"""
        assert FRONTEND_JWT_ALGORITHM == "HS256"
    
    def test_frontend_jwt_secret_from_env(self):
        """Test JWT secret from environment"""
        test_secret = "test-secret-key-123"
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret}):
            # Force reload of the module
            import importlib
            import fastmcp.auth.mcp_dependencies
            importlib.reload(fastmcp.auth.mcp_dependencies)
            
            from fastmcp.auth.mcp_dependencies import FRONTEND_JWT_SECRET
            assert FRONTEND_JWT_SECRET == test_secret