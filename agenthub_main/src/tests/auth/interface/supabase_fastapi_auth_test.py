"""Test suite for Supabase FastAPI authentication integration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from fastmcp.auth.interface.supabase_fastapi_auth import (
    SupabaseFastAPIAuth,
    JWTBearer,
    get_supabase_auth,
    decode_token,
    extract_user_from_token
)

class TestJWTBearer:
    """Test cases for JWTBearer class."""
    
    @pytest.fixture
    def jwt_bearer(self):
        """Create JWTBearer instance."""
        return JWTBearer()
    
    @pytest.mark.asyncio
    async def test_call_with_valid_bearer_token(self, jwt_bearer):
        """Test JWT bearer with valid token."""
        # Mock request with authorization header
        request = Mock(spec=Request)
        request.headers = {"authorization": "Bearer valid_token_123"}
        
        # Call should return credentials
        credentials = await jwt_bearer(request)
        
        assert credentials is not None
        assert credentials.credentials == "valid_token_123"
        assert credentials.scheme == "Bearer"
    
    @pytest.mark.asyncio
    async def test_call_with_invalid_scheme(self, jwt_bearer):
        """Test JWT bearer with invalid scheme."""
        request = Mock(spec=Request)
        request.headers = {"authorization": "Basic invalid_token"}
        
        with pytest.raises(HTTPException) as exc_info:
            await jwt_bearer(request)
        
        assert exc_info.value.status_code == 403
        assert "Invalid authentication scheme" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_call_without_authorization_header(self, jwt_bearer):
        """Test JWT bearer without authorization header."""
        request = Mock(spec=Request)
        request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await jwt_bearer(request)
        
        assert exc_info.value.status_code == 403
        assert "Invalid authorization code" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_verify_jwt_with_valid_token(self, jwt_bearer):
        """Test JWT verification with valid token."""
        # Mock successful verification
        with patch('fastmcp.auth.interface.supabase_fastapi_auth.decode_token') as mock_decode:
            mock_decode.return_value = {"sub": "user123", "exp": 9999999999}
            
            result = jwt_bearer.verify_jwt("valid_token")
            
            assert result is True
            mock_decode.assert_called_once_with("valid_token")
    
    @pytest.mark.asyncio
    async def test_verify_jwt_with_invalid_token(self, jwt_bearer):
        """Test JWT verification with invalid token."""
        with patch('fastmcp.auth.interface.supabase_fastapi_auth.decode_token') as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")
            
            result = jwt_bearer.verify_jwt("invalid_token")
            
            assert result is False


class TestSupabaseFastAPIAuth:
    """Test cases for SupabaseFastAPIAuth class."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        client.auth = Mock()
        client.auth.get_user = AsyncMock()
        return client
    
    @pytest.fixture
    def auth_instance(self, mock_supabase_client):
        """Create SupabaseFastAPIAuth instance."""
        with patch('fastmcp.auth.interface.supabase_fastapi_auth.create_client') as mock_create:
            mock_create.return_value = mock_supabase_client
            instance = SupabaseFastAPIAuth()
            instance._client = mock_supabase_client
            return instance
    
    @pytest.mark.asyncio
    async def test_get_user_from_token_success(self, auth_instance):
        """Test successful user retrieval from token."""
        # Mock successful user response
        mock_user_response = Mock()
        mock_user_response.user = Mock(
            id="user123",
            email="test@example.com",
            user_metadata={"name": "Test User"}
        )
        
        auth_instance._client.auth.get_user.return_value = mock_user_response
        
        user = await auth_instance.get_user_from_token("valid_token")
        
        assert user is not None
        assert user.id == "user123"
        assert user.email == "test@example.com"
        assert user.user_metadata == {"name": "Test User"}
    
    @pytest.mark.asyncio
    async def test_get_user_from_token_no_user(self, auth_instance):
        """Test user retrieval when no user found."""
        mock_response = Mock()
        mock_response.user = None
        
        auth_instance._client.auth.get_user.return_value = mock_response
        
        user = await auth_instance.get_user_from_token("invalid_token")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_user_from_token_exception(self, auth_instance):
        """Test user retrieval with exception."""
        auth_instance._client.auth.get_user.side_effect = Exception("Auth error")
        
        user = await auth_instance.get_user_from_token("bad_token")
        
        assert user is None


class TestModuleFunctions:
    """Test module-level functions."""
    
    def test_decode_token_success(self):
        """Test successful token decoding."""
        # Create a valid token
        payload = {"sub": "user123", "exp": 9999999999}
        secret = "test_secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        with patch.dict('os.environ', {'JWT_SECRET': secret}):
            decoded = decode_token(token)
            
            assert decoded["sub"] == "user123"
            assert "exp" in decoded
    
    def test_decode_token_invalid(self):
        """Test decoding invalid token."""
        with patch.dict('os.environ', {'JWT_SECRET': 'test_secret'}):
            with pytest.raises(Exception):
                decode_token("invalid_token")
    
    def test_extract_user_from_token_with_user_object(self):
        """Test extracting user ID from token with user object."""
        decoded_token = {
            "user": {"id": "user123"},
            "sub": "other_id"
        }
        
        user_id = extract_user_from_token(decoded_token)
        assert user_id == "user123"
    
    def test_extract_user_from_token_with_sub_only(self):
        """Test extracting user ID from token with sub only."""
        decoded_token = {"sub": "user456"}
        
        user_id = extract_user_from_token(decoded_token)
        assert user_id == "user456"
    
    def test_extract_user_from_token_no_user_id(self):
        """Test extracting user ID when not present."""
        decoded_token = {"other": "data"}
        
        user_id = extract_user_from_token(decoded_token)
        assert user_id is None
    
    @pytest.mark.asyncio
    async def test_get_supabase_auth_singleton(self):
        """Test that get_supabase_auth returns singleton."""
        with patch('fastmcp.auth.interface.supabase_fastapi_auth._supabase_auth_instance', None):
            with patch('fastmcp.auth.interface.supabase_fastapi_auth.SupabaseFastAPIAuth') as mock_class:
                mock_instance = Mock()
                mock_class.return_value = mock_instance
                
                # First call creates instance
                auth1 = get_supabase_auth()
                assert auth1 == mock_instance
                
                # Second call returns same instance
                auth2 = get_supabase_auth()
                assert auth2 == auth1
                
                # Constructor called only once
                mock_class.assert_called_once()