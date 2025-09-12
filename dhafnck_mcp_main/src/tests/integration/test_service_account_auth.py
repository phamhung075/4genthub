"""
Integration tests for Keycloak Service Account Authentication

These tests validate the service account authentication flow with a real Keycloak instance.
Run with: pytest -xvs tests/integration/test_service_account_auth.py

Note: Requires proper Keycloak configuration and environment variables.
"""

import os
import pytest
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from fastmcp.auth.service_account import (
    ServiceAccountAuth,
    ServiceAccountConfig,
    ServiceToken,
    get_service_account_auth,
    authenticate_service_request
)

# Test configuration
TEST_CONFIG = ServiceAccountConfig(
    keycloak_url="https://test-keycloak.example.com",
    realm="test-realm",
    client_id="test-service-account",
    client_secret="test-secret",
    scopes=["openid", "profile", "mcp:read", "mcp:write"]
)

class TestServiceAccountAuth:
    """Test service account authentication functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.auth = ServiceAccountAuth(TEST_CONFIG)

    async def teardown_method(self):
        """Cleanup after each test method"""
        await self.auth.close()

    @pytest.mark.asyncio
    async def test_service_account_config_from_env(self):
        """Test loading configuration from environment variables"""
        env_vars = {
            "KEYCLOAK_URL": "https://env-keycloak.com",
            "KEYCLOAK_REALM": "env-realm",
            "KEYCLOAK_SERVICE_CLIENT_ID": "env-client",
            "KEYCLOAK_SERVICE_CLIENT_SECRET": "env-secret"
        }
        
        with patch.dict(os.environ, env_vars):
            auth = ServiceAccountAuth()
            
            assert auth.config.keycloak_url == "https://env-keycloak.com"
            assert auth.config.realm == "env-realm"
            assert auth.config.client_id == "env-client"
            assert auth.config.client_secret == "env-secret"
            
            await auth.close()

    def test_service_token_expiry_logic(self):
        """Test service token expiry calculation"""
        # Create token that expires in 300 seconds
        token = ServiceToken(
            access_token="test-token",
            expires_in=300,
            created_at=datetime.now(timezone.utc)
        )
        
        # Token should not be expired
        assert not token.is_expired
        assert token.seconds_until_expiry > 250  # Account for test execution time
        
        # Create expired token
        expired_token = ServiceToken(
            access_token="expired-token",
            expires_in=60,
            created_at=datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        
        # Token should be expired
        assert expired_token.is_expired
        assert expired_token.seconds_until_expiry == 0

    @pytest.mark.asyncio
    async def test_config_validation(self):
        """Test configuration validation"""
        # Missing keycloak_url
        with pytest.raises(ValueError, match="Missing required service account configuration"):
            invalid_config = ServiceAccountConfig(
                keycloak_url="",
                realm="test",
                client_id="test",
                client_secret="test"
            )
            ServiceAccountAuth(invalid_config)

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful service account authentication"""
        # Mock successful token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 300,
            "scope": "openid profile mcp:read mcp:write"
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response):
            token = await self.auth.authenticate()
            
            assert token is not None
            assert token.access_token == "test-access-token"
            assert token.token_type == "Bearer"
            assert token.expires_in == 300
            assert not token.is_expired

    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test authentication failure handling"""
        # Mock failed authentication response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials"
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response):
            token = await self.auth.authenticate()
            
            assert token is None

    @pytest.mark.asyncio
    async def test_token_caching(self):
        """Test that tokens are properly cached"""
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "cached-token",
            "expires_in": 300
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response) as mock_post:
            # First authentication
            token1 = await self.auth.authenticate()
            assert token1.access_token == "cached-token"
            
            # Second authentication should use cached token
            token2 = await self.auth.authenticate()
            assert token2 is token1  # Same object
            
            # Should only have called the endpoint once
            assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_force_refresh(self):
        """Test forcing token refresh"""
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed-token",
            "expires_in": 300
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response) as mock_post:
            # First authentication
            await self.auth.authenticate()
            
            # Force refresh should make new request
            token = await self.auth.authenticate(force_refresh=True)
            assert token.access_token == "refreshed-token"
            
            # Should have called endpoint twice
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_valid_token(self):
        """Test getting valid token convenience method"""
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "valid-token-string",
            "expires_in": 300
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response):
            token_string = await self.auth.get_valid_token()
            assert token_string == "valid-token-string"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test service account health check"""
        # Mock Keycloak well-known endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(self.auth.client, 'get', return_value=mock_response):
            health = await self.auth.health_check()
            
            assert isinstance(health, dict)
            assert "service_account_configured" in health
            assert "keycloak_reachable" in health
            assert "configuration" in health
            
            # Should be configured with test config
            assert health["service_account_configured"] is True
            assert health["keycloak_reachable"] is True

    @pytest.mark.asyncio
    async def test_get_service_info(self):
        """Test getting service account info"""
        # Mock authentication
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {
            "access_token": "info-token",
            "expires_in": 300
        }
        
        # Mock userinfo response
        mock_info_response = MagicMock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "sub": "service-account-client-id",
            "preferred_username": "service-account-test-service-account",
            "email_verified": False,
            "client_id": "test-service-account"
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_auth_response):
            with patch.object(self.auth.client, 'get', return_value=mock_info_response):
                info = await self.auth.get_service_info()
                
                assert info is not None
                assert info["client_id"] == "test-service-account"
                assert "service-account" in info["preferred_username"]

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        import time
        
        start_time = time.time()
        
        # Make multiple rate-limited calls
        await self.auth._rate_limit()
        await self.auth._rate_limit()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should have added some delay
        assert elapsed >= 1.0  # At least 1 second delay

    def test_get_auth_headers(self):
        """Test getting authorization headers"""
        # Test without token
        headers = self.auth.get_auth_headers()
        assert headers == {}
        
        # Set a valid token
        self.auth._current_token = ServiceToken(
            access_token="header-test-token",
            expires_in=300
        )
        
        headers = self.auth.get_auth_headers()
        assert headers == {"Authorization": "Bearer header-test-token"}
        
        # Test with expired token
        expired_token = ServiceToken(
            access_token="expired-header-token",
            expires_in=60,
            created_at=datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        self.auth._current_token = expired_token
        
        headers = self.auth.get_auth_headers()
        assert headers == {}

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using service account as async context manager"""
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "context-token",
            "expires_in": 300
        }
        
        with patch.object(self.auth.client, 'post', return_value=mock_response):
            async with ServiceAccountAuth(TEST_CONFIG) as auth:
                assert auth._current_token is not None
                assert auth._current_token.access_token == "context-token"

    @pytest.mark.asyncio
    async def test_singleton_instance(self):
        """Test singleton pattern for service account auth"""
        # Mock environment variables
        env_vars = {
            "KEYCLOAK_URL": "https://singleton-test.com",
            "KEYCLOAK_SERVICE_CLIENT_SECRET": "singleton-secret"
        }
        
        with patch.dict(os.environ, env_vars):
            auth1 = get_service_account_auth()
            auth2 = get_service_account_auth()
            
            # Should be the same instance
            assert auth1 is auth2
            
            await auth1.close()


class TestAuthenticationHelper:
    """Test authentication helper functions"""

    @pytest.mark.asyncio
    async def test_authenticate_service_request_valid(self):
        """Test service request authentication with valid token"""
        # Mock JWT validation
        mock_payload = {
            "azp": "test-client",
            "sub": "service-account-test",
            "scope": "openid mcp:read mcp:write",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        
        with patch('fastmcp.auth.service_account.get_service_account_auth') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.validate_token.return_value = mock_payload
            mock_get_auth.return_value = mock_auth
            
            result = await authenticate_service_request("Bearer test-token")
            
            assert result is not None
            assert result["service_account"] is True
            assert result["client_id"] == "test-client"
            assert result["authenticated"] is True
            assert result["auth_provider"] == "keycloak_service_account"
            assert "mcp:*" in result["permissions"]

    @pytest.mark.asyncio
    async def test_authenticate_service_request_invalid_header(self):
        """Test service request authentication with invalid header"""
        # No header
        result = await authenticate_service_request(None)
        assert result is None
        
        # Invalid format
        result = await authenticate_service_request("Invalid-Header")
        assert result is None
        
        # Wrong scheme
        result = await authenticate_service_request("Basic dGVzdA==")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_service_request_invalid_token(self):
        """Test service request authentication with invalid token"""
        with patch('fastmcp.auth.service_account.get_service_account_auth') as mock_get_auth:
            mock_auth = AsyncMock()
            mock_auth.validate_token.return_value = None
            mock_get_auth.return_value = mock_auth
            
            result = await authenticate_service_request("Bearer invalid-token")
            assert result is None


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors"""
        auth = ServiceAccountAuth(TEST_CONFIG)
        
        with patch.object(auth.client, 'post', side_effect=Exception("Network error")):
            token = await auth.authenticate()
            assert token is None
        
        await auth.close()

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed responses"""
        auth = ServiceAccountAuth(TEST_CONFIG)
        
        # Mock response with missing required fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "response"}
        
        with patch.object(auth.client, 'post', return_value=mock_response):
            token = await auth.authenticate()
            # Should handle gracefully and return None or default values
            assert token is None or token.access_token is None
        
        await auth.close()


@pytest.mark.integration
class TestRealKeycloakIntegration:
    """
    Integration tests with real Keycloak instance.
    
    These tests are marked as integration and require:
    - Running Keycloak instance
    - Proper environment configuration
    - Valid service account setup
    
    Run with: pytest -m integration
    """

    def setup_method(self):
        """Setup for integration tests"""
        # Check if integration test environment is configured
        if not all([
            os.getenv("KEYCLOAK_URL"),
            os.getenv("KEYCLOAK_SERVICE_CLIENT_ID"), 
            os.getenv("KEYCLOAK_SERVICE_CLIENT_SECRET")
        ]):
            pytest.skip("Integration test environment not configured")
        
        self.auth = ServiceAccountAuth()

    async def teardown_method(self):
        """Cleanup after integration tests"""
        if hasattr(self, 'auth'):
            await self.auth.close()

    @pytest.mark.asyncio
    async def test_real_authentication(self):
        """Test authentication against real Keycloak instance"""
        token = await self.auth.authenticate()
        
        assert token is not None, "Authentication should succeed with proper configuration"
        assert token.access_token, "Should receive access token"
        assert not token.is_expired, "Token should not be expired"

    @pytest.mark.asyncio
    async def test_real_token_validation(self):
        """Test token validation against real Keycloak instance"""
        # First authenticate to get a token
        token = await self.auth.authenticate()
        assert token is not None
        
        # Validate the token
        payload = await self.auth.validate_token(token.access_token)
        assert payload is not None, "Token should be valid"
        assert "sub" in payload, "Token should contain subject"
        assert "azp" in payload, "Token should contain authorized party"

    @pytest.mark.asyncio
    async def test_real_health_check(self):
        """Test health check against real Keycloak instance"""
        health = await self.auth.health_check()
        
        assert health["service_account_configured"] is True
        assert health["keycloak_reachable"] is True
        
        # Try to authenticate to get more complete health info
        await self.auth.authenticate()
        health = await self.auth.health_check()
        
        assert health["token_available"] is True
        assert health["token_valid"] is True


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])