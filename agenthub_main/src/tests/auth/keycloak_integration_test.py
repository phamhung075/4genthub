"""Test suite for Keycloak Integration

Comprehensive test coverage for Keycloak integration including:
- Token validation and exchange
- User info retrieval
- MCP authentication mapping
- Error handling and edge cases
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
from jose import jwt

from fastmcp.auth.keycloak_integration import (
    KeycloakAuthProvider,
    KeycloakMCPAuth,
    get_keycloak_provider,
    get_keycloak_mcp_auth
)


class TestKeycloakAuthProvider:
    """Test KeycloakAuthProvider class"""
    
    @pytest.fixture
    def provider(self):
        """Create KeycloakAuthProvider instance"""
        with patch('httpx.AsyncClient'):
            provider = KeycloakAuthProvider(
                keycloak_url="https://keycloak.example.com",
                realm="test-realm",
                client_id="test-client",
                client_secret="test-secret"
            )
            # Replace http_client with mock
            provider.http_client = AsyncMock()
            return provider
    
    def test_initialization_with_params(self):
        """Test provider initialization with parameters"""
        with patch('httpx.AsyncClient'):
            provider = KeycloakAuthProvider(
                keycloak_url="https://kc.test.com",
                realm="mcp",
                client_id="mcp-app",
                client_secret="secret123",
                verify_audience=False,
                ssl_verify=False,
                token_cache_ttl=600,
                public_key_cache_ttl=7200
            )
            
            assert provider.keycloak_url == "https://kc.test.com"
            assert provider.realm == "mcp"
            assert provider.client_id == "mcp-app"
            assert provider.client_secret == "secret123"
            assert provider.verify_audience is False
            assert provider.ssl_verify is False
            assert provider.token_cache_ttl == 600
            assert provider.public_key_cache_ttl == 7200
    
    def test_initialization_from_env(self):
        """Test provider initialization from environment variables"""
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "https://env.keycloak.com",
            "KEYCLOAK_REALM": "env-realm",
            "KEYCLOAK_CLIENT_ID": "env-client",
            "KEYCLOAK_CLIENT_SECRET": "env-secret"
        }):
            with patch('httpx.AsyncClient'):
                provider = KeycloakAuthProvider()
                
                assert provider.keycloak_url == "https://env.keycloak.com"
                assert provider.realm == "env-realm"
                assert provider.client_id == "env-client"
                assert provider.client_secret == "env-secret"
    
    def test_initialization_missing_url(self):
        """Test provider initialization fails without URL"""
        with patch.dict(os.environ, {"KEYCLOAK_URL": ""}):
            with pytest.raises(ValueError) as exc_info:
                KeycloakAuthProvider()
            
            assert "KEYCLOAK_URL is required" in str(exc_info.value)
    
    def test_url_construction(self, provider):
        """Test URL construction"""
        assert provider.realm_url == "https://keycloak.example.com/realms/test-realm"
        assert provider.well_known_url == "https://keycloak.example.com/realms/test-realm/.well-known/openid-configuration"
        assert provider.token_url == "https://keycloak.example.com/realms/test-realm/protocol/openid-connect/token"
        assert provider.userinfo_url == "https://keycloak.example.com/realms/test-realm/protocol/openid-connect/userinfo"
        assert provider.jwks_url == "https://keycloak.example.com/realms/test-realm/protocol/openid-connect/certs"
    
    def test_jwks_client_creation(self, provider):
        """Test JWKS client lazy initialization"""
        with patch('fastmcp.auth.keycloak_integration.PyJWKClient') as mock_jwks_class:
            mock_client = Mock()
            mock_jwks_class.return_value = mock_client
            
            # First access creates client
            client1 = provider.jwks_client
            assert client1 == mock_client
            mock_jwks_class.assert_called_once_with(
                provider.jwks_url,
                cache_keys=True,
                lifespan=3600
            )
            
            # Second access returns same client
            client2 = provider.jwks_client
            assert client2 == mock_client
            assert mock_jwks_class.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_oidc_configuration_success(self, provider):
        """Test successful OIDC configuration fetch"""
        mock_config = {
            "issuer": "https://keycloak.example.com/realms/test-realm",
            "authorization_endpoint": "https://keycloak.example.com/auth",
            "token_endpoint": "https://keycloak.example.com/token"
        }
        
        provider.http_client.get.return_value = Mock(
            status_code=200,
            json=lambda: mock_config,
            raise_for_status=lambda: None
        )
        
        config = await provider.get_oidc_configuration()
        
        assert config == mock_config
        provider.http_client.get.assert_called_once_with(provider.well_known_url)
    
    @pytest.mark.asyncio
    async def test_get_oidc_configuration_cached(self, provider):
        """Test OIDC configuration caching"""
        mock_config = {"issuer": "test-issuer"}
        
        # Set cache
        provider._oidc_config = mock_config
        provider._last_config_fetch = datetime.now(timezone.utc)
        
        config = await provider.get_oidc_configuration()
        
        assert config == mock_config
        # Should not make HTTP request
        provider.http_client.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_oidc_configuration_cache_expired(self, provider):
        """Test OIDC configuration cache expiration"""
        old_config = {"issuer": "old-issuer"}
        new_config = {"issuer": "new-issuer"}
        
        # Set expired cache
        provider._oidc_config = old_config
        provider._last_config_fetch = datetime.now(timezone.utc) - timedelta(hours=2)
        
        provider.http_client.get.return_value = Mock(
            json=lambda: new_config,
            raise_for_status=lambda: None
        )
        
        config = await provider.get_oidc_configuration()
        
        assert config == new_config
        provider.http_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, provider):
        """Test successful token validation"""
        token = "valid.jwt.token"
        mock_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        # Mock OIDC config
        with patch.object(provider, 'get_oidc_configuration') as mock_get_config:
            mock_get_config.return_value = {"issuer": "https://keycloak.example.com/realms/test-realm"}
            
            # Mock JWKS client
            mock_jwks = Mock()
            mock_signing_key = Mock(key="test-key")
            mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
            provider._jwks_client = mock_jwks
                
            # Mock jwt.decode
            with patch('jwt.decode') as mock_decode:
                mock_decode.return_value = mock_payload

                result = await provider.validate_token(token)

                assert result == mock_payload
                mock_decode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_token_expired(self, provider):
        """Test token validation with expired token"""
        token = "expired.jwt.token"
        
        with patch.object(provider, 'get_oidc_configuration') as mock_get_config:
            mock_get_config.return_value = {"issuer": "test-issuer"}

            mock_jwks = Mock()
            mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="test-key")
            provider._jwks_client = mock_jwks

            with patch('jwt.decode') as mock_decode:
                mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

                result = await provider.validate_token(token)

                assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, provider):
        """Test token validation with invalid token"""
        token = "invalid.jwt.token"
        
        with patch.object(provider, 'get_oidc_configuration') as mock_get_config:
            mock_get_config.return_value = {"issuer": "test-issuer"}

            mock_jwks = Mock()
            mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="test-key")
            provider._jwks_client = mock_jwks

            with patch('jwt.decode') as mock_decode:
                mock_decode.side_effect = jwt.JWTError("Invalid signature")

                result = await provider.validate_token(token)

                assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_token_missing_sub(self, provider):
        """Test token validation with missing subject claim"""
        token = "nosub.jwt.token"
        mock_payload = {
            "username": "testuser",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            # Missing 'sub' claim
        }
        
        with patch.object(provider, 'get_oidc_configuration') as mock_get_config:
            mock_get_config.return_value = {"issuer": "test-issuer"}

            mock_jwks = Mock()
            mock_jwks.get_signing_key_from_jwt.return_value = Mock(key="test-key")
            provider._jwks_client = mock_jwks

            with patch('jwt.decode') as mock_decode:
                mock_decode.return_value = mock_payload

                result = await provider.validate_token(token)

                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, provider):
        """Test successful user info retrieval"""
        access_token = "valid.access.token"
        mock_user_info = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "email_verified": True
        }
        
        provider.http_client.get.return_value = Mock(
            json=lambda: mock_user_info,
            raise_for_status=lambda: None
        )
        
        result = await provider.get_user_info(access_token)
        
        assert result == mock_user_info
        provider.http_client.get.assert_called_once_with(
            provider.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, provider):
        """Test user info retrieval failure"""
        access_token = "invalid.token"
        
        provider.http_client.get.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock(status_code=401)
        )
        
        result = await provider.get_user_info(access_token)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exchange_token_password_grant(self, provider):
        """Test token exchange with password grant"""
        mock_response = {
            "access_token": "new.access.token",
            "refresh_token": "new.refresh.token",
            "token_type": "Bearer",
            "expires_in": 300
        }
        
        provider.http_client.post.return_value = Mock(
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await provider.exchange_token(
            username="testuser",
            password="testpass"
        )
        
        assert result == mock_response
        
        # Verify request data
        call_args = provider.http_client.post.call_args
        assert call_args[0][0] == provider.token_url
        assert call_args[1]["data"]["grant_type"] == "password"
        assert call_args[1]["data"]["username"] == "testuser"
        assert call_args[1]["data"]["password"] == "testpass"
    
    @pytest.mark.asyncio
    async def test_exchange_token_refresh_grant(self, provider):
        """Test token exchange with refresh token grant"""
        mock_response = {
            "access_token": "refreshed.access.token",
            "refresh_token": "refreshed.refresh.token"
        }
        
        provider.http_client.post.return_value = Mock(
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await provider.exchange_token(refresh_token="old.refresh.token")
        
        assert result == mock_response
        
        # Verify request data
        call_args = provider.http_client.post.call_args
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
        assert call_args[1]["data"]["refresh_token"] == "old.refresh.token"
    
    @pytest.mark.asyncio
    async def test_exchange_token_auth_code_grant(self, provider):
        """Test token exchange with authorization code grant"""
        mock_response = {"access_token": "code.access.token"}
        
        provider.http_client.post.return_value = Mock(
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await provider.exchange_token(
            authorization_code="auth123",
            redirect_uri="https://app.example.com/callback"
        )
        
        assert result == mock_response
        
        # Verify request data
        call_args = provider.http_client.post.call_args
        assert call_args[1]["data"]["grant_type"] == "authorization_code"
        assert call_args[1]["data"]["code"] == "auth123"
        assert call_args[1]["data"]["redirect_uri"] == "https://app.example.com/callback"
    
    @pytest.mark.asyncio
    async def test_exchange_token_no_credentials(self, provider):
        """Test token exchange with no valid credentials"""
        result = await provider.exchange_token()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exchange_token_http_error(self, provider):
        """Test token exchange with HTTP error"""
        provider.http_client.post.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=Mock(status_code=400, text="Invalid credentials")
        )
        
        result = await provider.exchange_token(username="bad", password="creds")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_logout_success(self, provider):
        """Test successful logout"""
        provider.http_client.post.return_value = Mock(
            raise_for_status=lambda: None
        )
        
        result = await provider.logout("refresh.token.123")
        
        assert result is True
        
        # Verify request
        call_args = provider.http_client.post.call_args
        assert call_args[0][0].endswith("/protocol/openid-connect/logout")
        assert call_args[1]["data"]["refresh_token"] == "refresh.token.123"
    
    @pytest.mark.asyncio
    async def test_logout_failure(self, provider):
        """Test logout failure"""
        provider.http_client.post.side_effect = Exception("Network error")
        
        result = await provider.logout("refresh.token.123")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close(self, provider):
        """Test closing HTTP client"""
        await provider.close()
        provider.http_client.aclose.assert_called_once()


class TestKeycloakMCPAuth:
    """Test KeycloakMCPAuth class"""
    
    @pytest.fixture
    def mcp_auth(self):
        """Create KeycloakMCPAuth instance"""
        with patch('httpx.AsyncClient'):
            provider = KeycloakAuthProvider(
                keycloak_url="https://keycloak.example.com",
                realm="test-realm"
            )
            provider.http_client = AsyncMock()
            return KeycloakMCPAuth(provider)
    
    @pytest.mark.asyncio
    async def test_authenticate_mcp_request_success(self, mcp_auth):
        """Test successful MCP request authentication"""
        auth_header = "Bearer valid.jwt.token"
        mock_payload = {
            "sub": "user-123",
            "preferred_username": "mcpuser",
            "email": "mcp@example.com",
            "realm_access": {"roles": ["developer"]},
            "scope": "openid profile email",
            "exp": 1234567890,
            "sid": "session-123"
        }
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            result = await mcp_auth.authenticate_mcp_request(auth_header)
            
            assert result is not None
            assert result["user_id"] == "user-123"
            assert result["username"] == "mcpuser"
            assert result["email"] == "mcp@example.com"
            assert result["authenticated"] is True
            assert result["auth_provider"] == "keycloak"
            assert "developer" in result["roles"]
            assert result["mcp_permissions"] == ["mcp:read", "mcp:write", "mcp:execute"]
    
    @pytest.mark.asyncio
    async def test_authenticate_mcp_request_no_header(self, mcp_auth):
        """Test MCP authentication without header"""
        result = await mcp_auth.authenticate_mcp_request(None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_mcp_request_invalid_format(self, mcp_auth):
        """Test MCP authentication with invalid header format"""
        result = await mcp_auth.authenticate_mcp_request("InvalidFormat")
        assert result is None
        
        result = await mcp_auth.authenticate_mcp_request("Basic dXNlcjpwYXNz")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_mcp_request_invalid_token(self, mcp_auth):
        """Test MCP authentication with invalid token"""
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await mcp_auth.authenticate_mcp_request("Bearer invalid.token")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_mcp_permissions_mapping_admin(self, mcp_auth):
        """Test MCP permissions mapping for admin role"""
        mock_payload = {
            "sub": "admin-user",
            "realm_access": {"roles": ["admin"]},
            "scope": "",
            "exp": 1234567890
        }
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            result = await mcp_auth.authenticate_mcp_request("Bearer admin.token")
            
            assert result["mcp_permissions"] == ["mcp:*"]
    
    @pytest.mark.asyncio
    async def test_mcp_permissions_mapping_user(self, mcp_auth):
        """Test MCP permissions mapping for regular user role"""
        mock_payload = {
            "sub": "regular-user",
            "realm_access": {"roles": ["user"]},
            "scope": "",
            "exp": 1234567890
        }
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            result = await mcp_auth.authenticate_mcp_request("Bearer user.token")
            
            assert result["mcp_permissions"] == ["mcp:read", "mcp:execute"]
    
    @pytest.mark.asyncio
    async def test_mcp_permissions_mapping_default(self, mcp_auth):
        """Test MCP permissions mapping for unknown role"""
        mock_payload = {
            "sub": "guest-user",
            "realm_access": {"roles": ["guest"]},
            "scope": "",
            "exp": 1234567890
        }
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            result = await mcp_auth.authenticate_mcp_request("Bearer guest.token")
            
            assert result["mcp_permissions"] == ["mcp:read"]
    
    @pytest.mark.asyncio
    async def test_create_mcp_token_success(self, mcp_auth):
        """Test successful MCP token creation"""
        keycloak_token = "valid.keycloak.token"
        mock_payload = {
            "sub": "user-456",
            "preferred_username": "tokenuser",
            "sid": "kc-session-123"
        }
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            with patch('secrets.token_urlsafe') as mock_token:
                mock_token.return_value = "random_token_string"
                
                result = await mcp_auth.create_mcp_token(
                    keycloak_token,
                    name="Test Token",
                    scopes=["mcp:read", "mcp:write"]
                )
                
                assert result is not None
                assert result["token"].startswith("mcp_")
                assert result["name"] == "Test Token"
                assert result["user_id"] == "user-456"
                assert result["username"] == "tokenuser"
                assert result["scopes"] == ["mcp:read", "mcp:write"]
                assert result["active"] is True
                assert "created_at" in result
                assert "expires_at" in result
                assert "token_hash" in result
    
    @pytest.mark.asyncio
    async def test_create_mcp_token_invalid_keycloak(self, mcp_auth):
        """Test MCP token creation with invalid Keycloak token"""
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await mcp_auth.create_mcp_token("invalid.token")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_create_mcp_token_default_scopes(self, mcp_auth):
        """Test MCP token creation with default scopes"""
        mock_payload = {"sub": "user-789", "preferred_username": "defaultuser"}
        
        with patch.object(mcp_auth.keycloak, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_payload
            
            result = await mcp_auth.create_mcp_token("valid.token")
            
            assert result["scopes"] == ["mcp:read", "mcp:execute"]


class TestSingletonFunctions:
    """Test singleton functions"""
    
    def test_get_keycloak_provider_singleton(self):
        """Test Keycloak provider singleton"""
        with patch.dict(os.environ, {"KEYCLOAK_URL": "https://test.com"}):
            with patch('httpx.AsyncClient'):
                # Reset global
                import fastmcp.auth.keycloak_integration as module
                module._default_provider = None
                
                provider1 = get_keycloak_provider()
                provider2 = get_keycloak_provider()
                
                assert provider1 is provider2
    
    def test_get_keycloak_mcp_auth(self):
        """Test Keycloak MCP auth creation"""
        with patch.dict(os.environ, {"KEYCLOAK_URL": "https://test.com"}):
            with patch('httpx.AsyncClient'):
                auth = get_keycloak_mcp_auth()
                
                assert isinstance(auth, KeycloakMCPAuth)
                assert auth.keycloak is not None