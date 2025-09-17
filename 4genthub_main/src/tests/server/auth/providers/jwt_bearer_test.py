"""
Test suite for JWT Bearer Authentication Provider

This module tests the JWT Bearer authentication provider that validates
JWT tokens for MCP authentication, including both user tokens and API tokens.
"""

import os
import jwt
import time
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from mcp.server.auth.provider import AccessToken

from fastmcp.server.auth.providers.jwt_bearer import JWTBearerAuthProvider


class TestJWTBearerAuthProvider:
    """Test cases for JWT Bearer authentication provider"""
    
    @pytest.fixture
    def secret_key(self):
        """Test JWT secret key"""
        return "test-jwt-secret-key-for-testing"
    
    @pytest.fixture
    def mock_jwt_backend(self):
        """Mock JWT auth backend"""
        backend = AsyncMock()
        backend.verify_token = AsyncMock()
        return backend
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        session.query = Mock()
        session.commit = Mock()
        session.close = Mock()
        return session
    
    @pytest.fixture
    def mock_api_token(self):
        """Mock API token from database"""
        token = Mock()
        token.id = "test-token-id"
        token.user_id = "test-user-123"
        token.name = "Test API Token"
        token.is_active = True
        token.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        token.last_used_at = datetime.now(timezone.utc)
        token.usage_count = 10
        token.rate_limit = None
        token.scopes = ["read:tasks", "write:tasks"]
        return token
    
    @pytest.fixture
    def valid_user_token_payload(self):
        """Valid user JWT token payload"""
        return {
            "sub": "user-123",
            "email": "user@example.com",
            "token_type": "access",
            "roles": ["developer"],
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "iss": "4genthub",
            "aud": ["mcp-client"]
        }
    
    @pytest.fixture
    def valid_api_token_payload(self):
        """Valid API JWT token payload"""
        return {
            "sub": "api-token-123",
            "token_id": "test-token-id",
            "token_type": "api_token",
            "user_id": "user-123",
            "scopes": ["read:tasks", "write:tasks", "execute:mcp"],
            "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "iss": "4genthub",
            "aud": ["mcp-api"]
        }
    
    def test_init_with_secret_key(self, secret_key):
        """Test initialization with provided secret key"""
        provider = JWTBearerAuthProvider(
            secret_key=secret_key,
            issuer="test-issuer",
            audience=["test-audience"],
            required_scopes=["mcp:read"]
        )
        
        assert provider.secret_key == secret_key
        assert provider.issuer == "test-issuer"
        assert provider.audience == ["test-audience"]
        assert provider.required_scopes == ["mcp:read"]
        assert provider.check_database is True
    
    def test_init_with_env_secret(self, secret_key):
        """Test initialization with environment variable secret"""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": secret_key}):
            provider = JWTBearerAuthProvider()
            
            assert provider.secret_key == secret_key
            assert provider.issuer == "4genthub"
            assert provider.required_scopes == ["mcp:access"]
    
    def test_init_without_secret_raises_error(self):
        """Test initialization without secret key raises error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be provided"):
                JWTBearerAuthProvider()
    
    def test_init_with_custom_settings(self, secret_key):
        """Test initialization with custom settings"""
        provider = JWTBearerAuthProvider(
            secret_key=secret_key,
            issuer="custom-issuer",
            audience=["api1", "api2"],
            required_scopes=["mcp:admin", "mcp:write"],
            check_database=False
        )
        
        assert provider.issuer == "custom-issuer"
        assert provider.audience == ["api1", "api2"]
        assert provider.required_scopes == ["mcp:admin", "mcp:write"]
        assert provider.check_database is False
    
    @pytest.mark.asyncio
    async def test_verify_token_delegates_to_backend(self, secret_key, mock_jwt_backend):
        """Test verify_token delegates to JWT backend"""
        with patch('fastmcp.auth.mcp_integration.jwt_auth_backend.create_jwt_auth_backend', return_value=mock_jwt_backend):
            provider = JWTBearerAuthProvider(secret_key=secret_key)
            
            # Mock backend response
            expected_token = AccessToken(
                token="test-jwt-token",
                client_id="test-client",
                scopes=["mcp:read"],
                expires_at=int(time.time()) + 3600
            )
            mock_jwt_backend.verify_token.return_value = expected_token
            
            # Test verification
            result = await provider.verify_token("test-jwt-token")
            
            assert result == expected_token
            mock_jwt_backend.verify_token.assert_called_once_with("test-jwt-token")
    
    @pytest.mark.asyncio
    async def test_load_access_token_delegates_to_verify(self, secret_key, mock_jwt_backend):
        """Test load_access_token delegates to verify_token"""
        with patch('fastmcp.auth.mcp_integration.jwt_auth_backend.create_jwt_auth_backend', return_value=mock_jwt_backend):
            provider = JWTBearerAuthProvider(secret_key=secret_key)
            
            # Mock backend response
            expected_token = AccessToken(
                token="test-jwt-token",
                client_id="test-client",
                scopes=["mcp:write"],
                expires_at=int(time.time()) + 3600
            )
            mock_jwt_backend.verify_token.return_value = expected_token
            
            # Test loading
            result = await provider.load_access_token("test-jwt-token")
            
            assert result == expected_token
            mock_jwt_backend.verify_token.assert_called_once_with("test-jwt-token")
    
    @pytest.mark.asyncio
    async def test_validate_user_token_valid(self, valid_user_token_payload):
        """Test validation of valid user token"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is not None
        assert result.client_id == "user-123"
        assert "mcp:access" in result.scopes
        assert "mcp:write" in result.scopes
        assert "mcp:read" in result.scopes
    
    @pytest.mark.asyncio
    async def test_validate_user_token_admin_scopes(self, valid_user_token_payload):
        """Test admin user gets full scopes"""
        valid_user_token_payload["roles"] = ["admin"]
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is not None
        assert set(result.scopes) == {"mcp:access", "mcp:admin", "mcp:write", "mcp:read"}
    
    @pytest.mark.asyncio
    async def test_validate_user_token_user_scopes(self, valid_user_token_payload):
        """Test regular user gets limited scopes"""
        valid_user_token_payload["roles"] = ["user"]
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is not None
        assert set(result.scopes) == {"mcp:access", "mcp:read"}
    
    @pytest.mark.asyncio
    async def test_validate_user_token_no_roles(self, valid_user_token_payload):
        """Test user with no roles gets basic access"""
        valid_user_token_payload["roles"] = []
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is not None
        assert result.scopes == ["mcp:access"]
    
    @pytest.mark.asyncio
    async def test_validate_user_token_wrong_type(self, valid_user_token_payload):
        """Test rejection of non-access token"""
        valid_user_token_payload["token_type"] = "refresh"
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_user_token_no_subject(self, valid_user_token_payload):
        """Test rejection of token without subject"""
        del valid_user_token_payload["sub"]
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_user_token_with_user_id_fallback(self, valid_user_token_payload):
        """Test fallback to user_id field if sub missing"""
        del valid_user_token_payload["sub"]
        valid_user_token_payload["user_id"] = "user-456"
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        result = await provider._validate_user_token("token", valid_user_token_payload)
        
        assert result is not None
        assert result.client_id == "user-456"
    
    @pytest.mark.asyncio
    async def test_validate_user_token_exception_handling(self):
        """Test graceful handling of exceptions"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        # Invalid payload that causes exception
        result = await provider._validate_user_token("token", None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_valid(self, mock_db_session, mock_api_token):
        """Test validation of valid token in database"""
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([mock_db_session])
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_token
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("test-token-id")
            
            assert result is True
            assert mock_api_token.usage_count == 11
            assert mock_api_token.last_used_at is not None
            mock_db_session.commit.assert_called_once()
            mock_db_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_not_found(self, mock_db_session):
        """Test validation when token not found in database"""
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([mock_db_session])
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("non-existent-token")
            
            assert result is False
            mock_db_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_inactive(self, mock_db_session, mock_api_token):
        """Test validation of inactive token"""
        mock_api_token.is_active = False
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([mock_db_session])
            mock_db_session.query.return_value.filter.return_value.first.return_value = None  # Filtered out
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("test-token-id")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_expired(self, mock_db_session, mock_api_token):
        """Test validation of expired token"""
        mock_api_token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([mock_db_session])
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_token
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("test-token-id")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_exception(self, mock_db_session):
        """Test graceful handling of database exceptions"""
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database error")
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("test-token-id")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_in_database_with_rate_limit(self, mock_db_session, mock_api_token):
        """Test token validation with rate limit set"""
        mock_api_token.rate_limit = 100  # 100 requests per period
        with patch('fastmcp.auth.interface.fastapi_auth.get_db') as mock_get_db:
            mock_get_db.return_value = iter([mock_db_session])
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_token
            
            provider = JWTBearerAuthProvider(secret_key="test-key")
            result = await provider._validate_token_in_database("test-token-id")
            
            assert result is True
            # Rate limit check is placeholder for now
    
    def test_map_scopes_to_mcp_read_write(self):
        """Test mapping of read/write scopes"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        scopes = ["read:tasks", "write:context", "read:agents"]
        mcp_scopes = provider._map_scopes_to_mcp(scopes)
        
        assert set(mcp_scopes) == {"mcp:read", "mcp:write"}
    
    def test_map_scopes_to_mcp_execute(self):
        """Test mapping of execute scope"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        scopes = ["execute:mcp", "read:tasks"]
        mcp_scopes = provider._map_scopes_to_mcp(scopes)
        
        assert set(mcp_scopes) == {"mcp:execute", "mcp:read"}
    
    def test_map_scopes_to_mcp_no_duplicates(self):
        """Test no duplicate MCP scopes"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        scopes = ["read:tasks", "read:context", "read:agents", "write:tasks", "write:context"]
        mcp_scopes = provider._map_scopes_to_mcp(scopes)
        
        assert mcp_scopes == ["mcp:read", "mcp:write"]
        assert len(mcp_scopes) == 2
    
    def test_map_scopes_to_mcp_unknown_scopes(self):
        """Test unknown scopes are ignored"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        scopes = ["unknown:scope", "invalid", "read:tasks"]
        mcp_scopes = provider._map_scopes_to_mcp(scopes)
        
        assert mcp_scopes == ["mcp:read"]
    
    def test_map_scopes_to_mcp_empty_list(self):
        """Test empty scope list returns empty"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        mcp_scopes = provider._map_scopes_to_mcp([])
        
        assert mcp_scopes == []
    
    def test_map_scopes_no_admin_mapping(self):
        """Test admin scope is not mapped (must be set in database)"""
        provider = JWTBearerAuthProvider(secret_key="test-key")
        
        scopes = ["admin:all", "mcp:admin", "write:tasks"]
        mcp_scopes = provider._map_scopes_to_mcp(scopes)
        
        # Admin scopes are not mapped, only write
        assert mcp_scopes == ["mcp:write"]
    
    @pytest.mark.asyncio
    async def test_integration_with_jwt_backend_factory(self):
        """Test proper integration with JWT backend factory"""
        with patch('fastmcp.auth.mcp_integration.jwt_auth_backend.create_jwt_auth_backend') as mock_factory:
            mock_backend = AsyncMock()
            mock_factory.return_value = mock_backend
            
            provider = JWTBearerAuthProvider(
                secret_key="test-key",
                required_scopes=["mcp:admin", "mcp:write"]
            )
            
            # Verify factory called with correct scopes
            mock_factory.assert_called_once_with(
                required_scopes=["mcp:admin", "mcp:write"]
            )
            
            # Verify backend is stored
            assert provider.jwt_backend == mock_backend
    
    @pytest.mark.asyncio
    async def test_database_check_disabled(self, secret_key, mock_jwt_backend):
        """Test behavior when database check is disabled"""
        with patch('fastmcp.auth.mcp_integration.jwt_auth_backend.create_jwt_auth_backend', return_value=mock_jwt_backend):
            provider = JWTBearerAuthProvider(
                secret_key=secret_key,
                check_database=False
            )
            
            assert provider.check_database is False
            
            # Token should be validated without database check
            expected_token = AccessToken(
                token="test-token",
                client_id="test-client",
                scopes=["mcp:read"]
            )
            mock_jwt_backend.verify_token.return_value = expected_token
            
            result = await provider.verify_token("test-token")
            assert result == expected_token