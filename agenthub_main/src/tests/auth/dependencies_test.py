"""
Tests for FastAPI authentication dependencies.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import os

from fastmcp.auth.dependencies import (
    get_current_user,
    get_optional_current_user,
    JWT_ALGORITHM
)
from fastmcp.auth.domain.entities.user import User


class TestGetCurrentUser:
    """Test the get_current_user dependency."""
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP credentials."""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "test_token"
        return credentials
    
    @pytest.fixture
    def valid_jwt_payload(self):
        """Create a valid JWT payload."""
        return {
            "sub": "user123",
            "email": "user@example.com",
            "username": "testuser",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, mock_credentials, valid_jwt_payload):
        """Test successful user extraction from valid JWT token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            # Reload the module to pick up the environment variable
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            with patch('jwt.decode', return_value=valid_jwt_payload):
                user = await get_current_user(mock_credentials)
                
                assert isinstance(user, User)
                assert user.id == "user123"
                assert user.email == "user@example.com"
                assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_user_id_instead_of_sub(self, mock_credentials):
        """Test extraction when token uses user_id instead of sub."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            payload = {
                "user_id": "user456",  # Using user_id instead of sub
                "email": "another@example.com",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            }
            
            with patch('jwt.decode', return_value=payload):
                user = await get_current_user(mock_credentials)
                
                assert user.id == "user456"
                assert user.email == "another@example.com"
    
    @pytest.mark.asyncio
    async def test_get_current_user_without_jwt_secret(self, mock_credentials):
        """Test that authentication fails when JWT_SECRET_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = None
            
            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials)
            
            assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "JWT secret not set" in exc.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_token(self, mock_credentials):
        """Test authentication fails with expired token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            with patch('jwt.decode', side_effect=jwt.ExpiredSignatureError):
                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_credentials)
                
                assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert exc.value.detail == "Token expired"
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, mock_credentials):
        """Test authentication fails with invalid token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            with patch('jwt.decode', side_effect=jwt.InvalidTokenError("Invalid")):
                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_credentials)
                
                assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert exc.value.detail == "Invalid token"
    
    @pytest.mark.asyncio
    async def test_get_current_user_missing_user_id(self, mock_credentials):
        """Test authentication fails when token missing user_id/sub."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            payload = {
                "email": "user@example.com",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                # Missing both sub and user_id
            }
            
            with patch('jwt.decode', return_value=payload):
                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_credentials)
                
                assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert exc.value.detail == "Invalid authentication credentials"
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_timestamp(self, mock_credentials):
        """Test authentication fails when token exp timestamp is expired."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            payload = {
                "sub": "user123",
                "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()  # Expired
            }
            
            with patch('jwt.decode', return_value=payload):
                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_credentials)
                
                assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert exc.value.detail == "Token expired"
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_minimal_payload(self, mock_credentials):
        """Test user creation with minimal JWT payload."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            payload = {
                "sub": "user789",
                # No email, username, or exp
            }
            
            with patch('jwt.decode', return_value=payload):
                user = await get_current_user(mock_credentials)
                
                assert user.id == "user789"
                assert user.email == "user789@example.com"  # Default email
                assert user.username == "user789"  # Defaults to user_id
    
    @pytest.mark.asyncio
    async def test_get_current_user_general_exception(self, mock_credentials):
        """Test authentication fails gracefully on unexpected errors."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            with patch('jwt.decode', side_effect=Exception("Unexpected error")):
                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_credentials)
                
                assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert exc.value.detail == "Could not validate credentials"


class TestGetOptionalCurrentUser:
    """Test the get_optional_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_optional_user_with_no_credentials(self):
        """Test returns None when no credentials provided."""
        user = await get_optional_current_user(None)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_with_valid_credentials(self):
        """Test returns user when valid credentials provided."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            payload = {
                "sub": "optional_user",
                "email": "optional@example.com"
            }
            
            with patch('jwt.decode', return_value=payload):
                user = await get_optional_current_user(mock_credentials)
                
                assert isinstance(user, User)
                assert user.id == "optional_user"
                assert user.email == "optional@example.com"
    
    @pytest.mark.asyncio
    async def test_get_optional_user_with_invalid_credentials(self):
        """Test returns None when invalid credentials provided."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid_token"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.auth.dependencies
            fastmcp.auth.dependencies.JWT_SECRET_KEY = "test_secret"
            
            with patch('jwt.decode', side_effect=jwt.InvalidTokenError):
                user = await get_optional_current_user(mock_credentials)
                assert user is None


class TestJWTConfiguration:
    """Test JWT configuration and environment variables."""
    
    def test_jwt_algorithm_default(self):
        """Test default JWT algorithm is HS256."""
        from fastmcp.auth.dependencies import JWT_ALGORITHM
        assert JWT_ALGORITHM == "HS256"
    
    def test_jwt_algorithm_from_env(self):
        """Test JWT algorithm can be set via environment variable."""
        with patch.dict(os.environ, {"JWT_ALGORITHM": "RS256"}):
            # Need to reload module to pick up new env var
            import importlib
            import fastmcp.auth.dependencies
            importlib.reload(fastmcp.auth.dependencies)
            
            assert fastmcp.auth.dependencies.JWT_ALGORITHM == "RS256"
    
    def test_jwt_secret_key_warning_when_not_set(self, caplog):
        """Test warning is logged when JWT_SECRET_KEY not set."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import fastmcp.auth.dependencies
            importlib.reload(fastmcp.auth.dependencies)
            
            assert fastmcp.auth.dependencies.JWT_SECRET_KEY is None
            assert "CRITICAL SECURITY WARNING" in caplog.text
            assert "JWT_SECRET_KEY not set" in caplog.text