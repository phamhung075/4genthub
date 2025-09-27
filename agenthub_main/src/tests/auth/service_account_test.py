"""Test suite for Keycloak Service Account Authentication

Comprehensive test coverage for service account authentication including:
- Client credentials flow
- Token caching and refresh
- Automatic token renewal
- Health checks
- Error handling and edge cases
"""

import pytest
import os
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
from jose import jwt

from fastmcp.auth.service_account import (
    ServiceAccountConfig,
    ServiceToken,
    ServiceAccountAuth,
    get_service_account_auth,
    authenticate_service_request
)


class TestServiceAccountConfig:
    """Test ServiceAccountConfig dataclass"""
    
    def test_config_initialization(self):
        """Test config initialization with all parameters"""
        config = ServiceAccountConfig(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            client_secret="test-secret",
            scopes=["openid", "profile"]
        )
        
        assert config.keycloak_url == "https://keycloak.example.com"
        assert config.realm == "test-realm"
        assert config.client_id == "test-client"
        assert config.client_secret == "test-secret"
        assert config.scopes == ["openid", "profile"]
    
    def test_config_default_scopes(self):
        """Test config with default scopes"""
        config = ServiceAccountConfig(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        assert config.scopes == ["openid", "profile", "email", "mcp:read", "mcp:write"]


class TestServiceToken:
    """Test ServiceToken dataclass"""
    
    def test_token_initialization(self):
        """Test token initialization"""
        token = ServiceToken(
            access_token="test.access.token",
            refresh_token="test.refresh.token",
            expires_in=300,
            scope="openid profile"
        )
        
        assert token.access_token == "test.access.token"
        assert token.refresh_token == "test.refresh.token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 300
        assert token.scope == "openid profile"
        assert token.created_at is not None
    
    def test_token_expiry_calculation(self):
        """Test token expiry calculations"""
        created = datetime.now(timezone.utc)
        token = ServiceToken(
            access_token="token",
            expires_in=3600,
            created_at=created
        )
        
        expected_expiry = created + timedelta(seconds=3600)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 1
    
    def test_token_is_expired(self):
        """Test token expiration check"""
        # Non-expired token
        token = ServiceToken(
            access_token="token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        assert not token.is_expired
        
        # Expired token
        expired_token = ServiceToken(
            access_token="token",
            expires_in=60,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
        assert expired_token.is_expired
        
        # Token within buffer period (30 seconds)
        buffer_token = ServiceToken(
            access_token="token",
            expires_in=25,  # Expires in 25 seconds (within 30 second buffer)
            created_at=datetime.now(timezone.utc)
        )
        assert buffer_token.is_expired
    
    def test_seconds_until_expiry(self):
        """Test seconds until expiry calculation"""
        token = ServiceToken(
            access_token="token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        
        # Should be close to 3600
        assert 3595 <= token.seconds_until_expiry <= 3600
        
        # Expired token
        expired_token = ServiceToken(
            access_token="token",
            expires_in=60,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
        assert expired_token.seconds_until_expiry == 0


class TestServiceAccountAuth:
    """Test ServiceAccountAuth class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        return ServiceAccountConfig(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="service-client",
            client_secret="service-secret"
        )
    
    @pytest.fixture
    def auth_instance(self, mock_config):
        """Create ServiceAccountAuth instance"""
        with patch('httpx.AsyncClient'):
            auth = ServiceAccountAuth(mock_config)
            auth.client = AsyncMock()
            return auth
    
    def test_initialization_with_config(self, mock_config):
        """Test initialization with provided config"""
        with patch('httpx.AsyncClient'):
            auth = ServiceAccountAuth(mock_config)
            
            assert auth.config == mock_config
            assert auth.realm_url == "https://keycloak.example.com/realms/test-realm"
            assert auth.token_endpoint.endswith("/protocol/openid-connect/token")
            assert auth._current_token is None
    
    def test_initialization_from_env(self):
        """Test initialization from environment variables"""
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "https://env.keycloak.com",
            "KEYCLOAK_REALM": "env-realm",
            "KEYCLOAK_SERVICE_CLIENT_ID": "env-client",
            "KEYCLOAK_SERVICE_CLIENT_SECRET": "env-secret",
            "KEYCLOAK_SERVICE_SCOPES": "openid profile mcp:admin"
        }):
            with patch('httpx.AsyncClient'):
                auth = ServiceAccountAuth()
                
                assert auth.config.keycloak_url == "https://env.keycloak.com"
                assert auth.config.realm == "env-realm"
                assert auth.config.client_id == "env-client"
                assert auth.config.client_secret == "env-secret"
                assert auth.config.scopes == ["openid", "profile", "mcp:admin"]
    
    def test_validate_config_missing_fields(self):
        """Test config validation with missing fields"""
        with patch('httpx.AsyncClient'):
            # Missing Keycloak URL
            with pytest.raises(ValueError) as exc_info:
                ServiceAccountAuth(ServiceAccountConfig(
                    keycloak_url="",
                    realm="realm",
                    client_id="client",
                    client_secret="secret"
                ))
            assert "KEYCLOAK_URL" in str(exc_info.value)
            
            # Missing client secret
            with pytest.raises(ValueError) as exc_info:
                ServiceAccountAuth(ServiceAccountConfig(
                    keycloak_url="https://kc.com",
                    realm="realm",
                    client_id="client",
                    client_secret=""
                ))
            assert "KEYCLOAK_CLIENT_SECRET" in str(exc_info.value)
    
    def test_config_url_trailing_slash(self):
        """Test config removes trailing slash from URL"""
        with patch('httpx.AsyncClient'):
            auth = ServiceAccountAuth(ServiceAccountConfig(
                keycloak_url="https://keycloak.com/",  # Trailing slash
                realm="realm",
                client_id="client",
                client_secret="secret"
            ))
            
            assert auth.config.keycloak_url == "https://keycloak.com"  # No trailing slash
    
    def test_jwks_client_creation(self, auth_instance):
        """Test JWKS client lazy initialization"""
        with patch('fastmcp.auth.service_account.PyJWKClient') as mock_jwks_class:
            mock_client = Mock()
            mock_jwks_class.return_value = mock_client

            # Reset the instance's client to None to test lazy initialization
            auth_instance._jwks_client = None

            # First access creates client
            client1 = auth_instance.jwks_client
            assert client1 == mock_client
            mock_jwks_class.assert_called_once_with(
                auth_instance.jwks_endpoint,
                cache_keys=True,
                lifespan=3600
            )

            # Second access returns same client (no additional calls)
            client2 = auth_instance.jwks_client
            assert client2 == mock_client
            assert mock_jwks_class.call_count == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_instance):
        """Test successful authentication"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new.access.token",
            "refresh_token": "new.refresh.token",
            "token_type": "Bearer",
            "expires_in": 300,
            "scope": "openid profile"
        }
        
        auth_instance.client.post.return_value = mock_response
        
        token = await auth_instance.authenticate()
        
        assert token is not None
        assert token.access_token == "new.access.token"
        assert token.refresh_token == "new.refresh.token"
        assert token.expires_in == 300
        
        # Check request was made correctly
        auth_instance.client.post.assert_called_once()
        call_args = auth_instance.client.post.call_args
        assert call_args[0][0] == auth_instance.token_endpoint
        assert call_args[1]["data"]["grant_type"] == "client_credentials"
        assert call_args[1]["data"]["client_id"] == "service-client"
        assert call_args[1]["data"]["client_secret"] == "service-secret"
    
    @pytest.mark.asyncio
    async def test_authenticate_cached_token(self, auth_instance):
        """Test authentication uses cached token when valid"""
        # Set a valid cached token
        auth_instance._current_token = ServiceToken(
            access_token="cached.token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        
        token = await auth_instance.authenticate()
        
        # Should return cached token without making request
        assert token.access_token == "cached.token"
        auth_instance.client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_force_refresh(self, auth_instance):
        """Test forced token refresh"""
        # Set a valid cached token
        auth_instance._current_token = ServiceToken(
            access_token="old.token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed.token",
            "expires_in": 300
        }
        
        auth_instance.client.post.return_value = mock_response
        
        token = await auth_instance.authenticate(force_refresh=True)
        
        # Should get new token despite cached one being valid
        assert token.access_token == "refreshed.token"
        auth_instance.client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, auth_instance):
        """Test authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": "invalid_client"}'
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Client authentication failed"
        }
        
        auth_instance.client.post.return_value = mock_response
        
        token = await auth_instance.authenticate()
        
        assert token is None
    
    @pytest.mark.asyncio
    async def test_authenticate_exception(self, auth_instance):
        """Test authentication with exception"""
        auth_instance.client.post.side_effect = httpx.RequestError("Network error")
        
        token = await auth_instance.authenticate()
        
        assert token is None
    
    @pytest.mark.asyncio
    async def test_get_valid_token(self, auth_instance):
        """Test get_valid_token method"""
        with patch.object(auth_instance, 'authenticate') as mock_auth:
            mock_auth.return_value = ServiceToken(
                access_token="valid.token",
                expires_in=300
            )
            
            token = await auth_instance.get_valid_token()
            
            assert token == "valid.token"
            mock_auth.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_valid_token_none(self, auth_instance):
        """Test get_valid_token when authentication fails"""
        with patch.object(auth_instance, 'authenticate') as mock_auth:
            mock_auth.return_value = None
            
            token = await auth_instance.get_valid_token()
            
            assert token is None
    
    @pytest.mark.asyncio
    async def test_validate_token_valid(self, auth_instance):
        """Test successful token validation"""
        token = "valid.jwt.token"

        # Mock the JWKS client directly
        mock_jwks = Mock()
        mock_signing_key = Mock(key="test-key")
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
        auth_instance._jwks_client = mock_jwks

        with patch('fastmcp.auth.service_account.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "service-account",
                "azp": "service-client",
                "typ": "Bearer",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            }

            result = await auth_instance.validate_token(token)

            assert result is not None
            assert result["azp"] == "service-client"

            mock_decode.assert_called_once_with(
                token,
                "test-key",
                algorithms=["RS256"],
                audience="service-client",
                issuer="https://keycloak.example.com/realms/test-realm"
            )
    
    @pytest.mark.asyncio
    async def test_validate_token_wrong_type(self, auth_instance):
        """Test token validation with wrong token type"""
        # Mock the JWKS client directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="key")
        auth_instance._jwks_client = mock_jwks

        with patch('fastmcp.auth.service_account.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "typ": "ID",  # Not a Bearer token
                "azp": "service-client"
            }

            result = await auth_instance.validate_token("token")

            assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_token_wrong_client(self, auth_instance):
        """Test token validation with wrong client"""
        # Mock the JWKS client directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="key")
        auth_instance._jwks_client = mock_jwks

        with patch('fastmcp.auth.service_account.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "typ": "Bearer",
                "azp": "different-client"  # Wrong client
            }

            result = await auth_instance.validate_token("token")

            assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_token_expired(self, auth_instance):
        """Test token validation with expired token"""
        # Mock the JWKS client directly
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="key")
        auth_instance._jwks_client = mock_jwks

        with patch('fastmcp.auth.service_account.jwt.decode') as mock_decode:
            from jwt import ExpiredSignatureError
            mock_decode.side_effect = ExpiredSignatureError("Token expired")

            result = await auth_instance.validate_token("expired.token")

            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_service_info_success(self, auth_instance):
        """Test successful service info retrieval"""
        with patch.object(auth_instance, 'get_valid_token') as mock_get_token:
            mock_get_token.return_value = "valid.token"
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "sub": "service-account-id",
                "azp": "service-client",
                "email": "service@example.com"
            }
            
            auth_instance.client.get.return_value = mock_response
            
            info = await auth_instance.get_service_info()
            
            assert info is not None
            assert info["azp"] == "service-client"
            
            auth_instance.client.get.assert_called_once_with(
                auth_instance.userinfo_endpoint,
                headers={"Authorization": "Bearer valid.token"}
            )
    
    @pytest.mark.asyncio
    async def test_get_service_info_no_token(self, auth_instance):
        """Test service info retrieval without token"""
        with patch.object(auth_instance, 'get_valid_token') as mock_get_token:
            mock_get_token.return_value = None
            
            info = await auth_instance.get_service_info()
            
            assert info is None
            auth_instance.client.get.assert_not_called()
    
    def test_get_auth_headers_with_token(self, auth_instance):
        """Test getting auth headers with valid token"""
        auth_instance._current_token = ServiceToken(
            access_token="current.token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        
        headers = auth_instance.get_auth_headers()
        
        assert headers == {"Authorization": "Bearer current.token"}
    
    def test_get_auth_headers_no_token(self, auth_instance):
        """Test getting auth headers without token"""
        headers = auth_instance.get_auth_headers()
        assert headers == {}
    
    def test_get_auth_headers_expired_token(self, auth_instance):
        """Test getting auth headers with expired token"""
        auth_instance._current_token = ServiceToken(
            access_token="expired.token",
            expires_in=60,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
        
        headers = auth_instance.get_auth_headers()
        assert headers == {}
    
    @pytest.mark.asyncio
    async def test_health_check(self, auth_instance):
        """Test health check"""
        # Set current token
        auth_instance._current_token = ServiceToken(
            access_token="health.token",
            expires_in=3600,
            created_at=datetime.now(timezone.utc)
        )
        
        # Mock well-known endpoint
        mock_response = Mock()
        mock_response.status_code = 200
        auth_instance.client.get.return_value = mock_response
        
        health = await auth_instance.health_check()
        
        assert health["service_account_configured"] is True
        assert health["token_available"] is True
        assert health["token_valid"] is True
        assert health["token_expires_in"] > 0
        assert health["keycloak_reachable"] is True
        assert health["configuration"]["client_id"] == "service-client"
    
    @pytest.mark.asyncio
    async def test_health_check_no_token(self, auth_instance):
        """Test health check without token"""
        auth_instance.client.get.side_effect = Exception("Network error")
        
        health = await auth_instance.health_check()
        
        assert health["token_available"] is False
        assert health["token_valid"] is False
        assert health["keycloak_reachable"] is False
        assert "keycloak_error" in health
    
    @pytest.mark.asyncio
    async def test_token_refresh_loop(self, auth_instance):
        """Test automatic token refresh loop"""
        # Set token that expires soon
        auth_instance._current_token = ServiceToken(
            access_token="expiring.token",
            expires_in=35,  # Expires in 35 seconds
            created_at=datetime.now(timezone.utc)
        )
        
        # Mock authenticate for refresh
        with patch.object(auth_instance, 'authenticate') as mock_auth:
            mock_auth.return_value = ServiceToken(
                access_token="refreshed.token",
                expires_in=300
            )
            
            # Start refresh task
            auth_instance._start_token_refresh_task()
            
            # Wait a bit to ensure task starts
            await asyncio.sleep(0.1)
            
            # Cancel task to stop loop
            if auth_instance._refresh_task:
                auth_instance._refresh_task.cancel()
                try:
                    await auth_instance._refresh_task
                except asyncio.CancelledError:
                    pass
    
    @pytest.mark.asyncio
    async def test_context_manager(self, auth_instance):
        """Test async context manager"""
        with patch.object(auth_instance, 'authenticate') as mock_auth:
            with patch.object(auth_instance, 'close') as mock_close:
                mock_auth.return_value = ServiceToken(access_token="ctx.token")
                
                async with auth_instance as auth:
                    assert auth == auth_instance
                    mock_auth.assert_called_once()
                
                mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, auth_instance):
        """Test closing auth instance"""
        # Create a mock refresh task
        auth_instance._refresh_task = asyncio.create_task(asyncio.sleep(10))
        
        await auth_instance.close()
        
        assert auth_instance._refresh_task.cancelled()
        auth_instance.client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_instance):
        """Test rate limiting between requests"""
        import time
        # Simulate a recent request to trigger rate limiting
        auth_instance._last_request_time = time.time()
        start_time = time.time()

        await auth_instance._rate_limit()

        # Should have waited
        elapsed = time.time() - start_time
        assert elapsed >= auth_instance._min_request_interval - 0.1  # Allow small variance


class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_service_account_auth_singleton(self):
        """Test service account auth singleton"""
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "https://test.com",
            "KEYCLOAK_SERVICE_CLIENT_SECRET": "secret"
        }):
            with patch('httpx.AsyncClient'):
                # Reset global
                import fastmcp.auth.service_account as module
                module._service_auth_instance = None
                
                auth1 = get_service_account_auth()
                auth2 = get_service_account_auth()
                
                assert auth1 is auth2
    
    @pytest.mark.asyncio
    async def test_authenticate_service_request_valid(self):
        """Test service request authentication with valid token"""
        auth_header = "Bearer valid.service.token"
        
        with patch('fastmcp.auth.service_account.get_service_account_auth') as mock_get_auth:
            mock_auth = Mock()
            mock_get_auth.return_value = mock_auth
            
            mock_auth.validate_token = AsyncMock(return_value={
                "sub": "service-123",
                "azp": "service-client",
                "scope": "openid profile mcp:read",
                "exp": 1234567890
            })
            
            result = await authenticate_service_request(auth_header)
            
            assert result is not None
            assert result["service_account"] is True
            assert result["client_id"] == "service-client"
            assert result["subject"] == "service-123"
            assert result["authenticated"] is True
            assert result["auth_provider"] == "keycloak_service_account"
            assert result["permissions"] == ["mcp:*"]
            assert "mcp:read" in result["scopes"]
    
    @pytest.mark.asyncio
    async def test_authenticate_service_request_no_header(self):
        """Test service request authentication without header"""
        result = await authenticate_service_request(None)
        assert result is None
        
        result = await authenticate_service_request("")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_service_request_invalid_format(self):
        """Test service request authentication with invalid header"""
        result = await authenticate_service_request("InvalidFormat")
        assert result is None
        
        result = await authenticate_service_request("Basic dXNlcjpwYXNz")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_service_request_invalid_token(self):
        """Test service request authentication with invalid token"""
        with patch('fastmcp.auth.service_account.get_service_account_auth') as mock_get_auth:
            mock_auth = Mock()
            mock_get_auth.return_value = mock_auth
            mock_auth.validate_token = AsyncMock(return_value=None)
            
            result = await authenticate_service_request("Bearer invalid.token")
            assert result is None