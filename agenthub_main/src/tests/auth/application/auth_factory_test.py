"""
Unit tests for AuthFactory

Tests the factory pattern for creating authentication providers
based on environment configuration.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional

from fastmcp.auth.application.auth_factory import (
    AuthFactory,
    AuthProvider,
    AuthResult,
    AuthServiceInterface,
    SupabaseAuthAdapter,
    KeycloakAuthAdapter,
    LocalAuthAdapter
)


class MockSupabaseClient:
    """Mock Supabase client for testing"""
    def __init__(self):
        self.auth = Mock()
        self.auth.sign_up = AsyncMock()
        self.auth.sign_in_with_password = AsyncMock()
        self.auth.sign_out = AsyncMock()
        self.auth.refresh_session = AsyncMock()
        self.auth.get_user = AsyncMock()


class MockKeycloakOpenIDConnect:
    """Mock Keycloak client for testing"""
    def __init__(self, server_url, realm_name, client_id, client_secret_key=None):
        self.server_url = server_url
        self.realm_name = realm_name
        self.client_id = client_id
        self.client_secret_key = client_secret_key
        
        # Mock methods
        self.token = AsyncMock()
        self.userinfo = AsyncMock()
        self.logout = AsyncMock()
        self.refresh_token = AsyncMock()


class TestAuthFactory:
    """Test cases for AuthFactory"""
    
    def test_auth_provider_enum(self):
        """Test AuthProvider enum values"""
        assert AuthProvider.SUPABASE.value == "supabase"
        assert AuthProvider.KEYCLOAK.value == "keycloak"
        assert AuthProvider.LOCAL.value == "local"
    
    def test_auth_result_model(self):
        """Test AuthResult model initialization"""
        # Test successful result
        result = AuthResult(
            success=True,
            user={"id": "123", "email": "test@example.com"},
            access_token="token123",
            refresh_token="refresh123"
        )
        assert result.success is True
        assert result.error_message is None
        assert result.user["email"] == "test@example.com"
        assert result.expires_in == 900  # default
        
        # Test failed result
        failed_result = AuthResult(
            success=False,
            error_message="Invalid credentials"
        )
        assert failed_result.success is False
        assert failed_result.error_message == "Invalid credentials"
        assert failed_result.user is None
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "supabase"})
    def test_get_provider_supabase(self):
        """Test getting Supabase provider"""
        # Get provider
        provider = AuthFactory.create_auth_service()
        
        # Verify
        assert isinstance(provider, SupabaseAuthAdapter)
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_get_provider_keycloak(self):
        """Test getting Keycloak provider"""
        # Get provider
        provider = AuthFactory.create_auth_service()
        
        # Verify
        assert isinstance(provider, KeycloakAuthAdapter)
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "local"})
    def test_get_provider_local(self):
        """Test getting Local provider"""
        provider = AuthFactory.create_auth_service()
        assert isinstance(provider, LocalAuthAdapter)
    
    def test_get_provider_default(self):
        """Test default provider when AUTH_PROVIDER not set"""
        # Clear existing instances to ensure clean test
        AuthFactory._instances.clear()
        
        # Mock environment to ensure AUTH_PROVIDER is not set
        with patch.dict(os.environ, {'AUTH_PROVIDER': ''}, clear=True):
            provider = AuthFactory.create_auth_service()
            assert isinstance(provider, LocalAuthAdapter)
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "invalid"})
    def test_get_provider_invalid(self):
        """Test invalid provider falls back to local"""
        with patch("fastmcp.auth.application.auth_factory.logger") as mock_logger:
            provider = AuthFactory.create_auth_service()
            assert isinstance(provider, LocalAuthAdapter)
            mock_logger.warning.assert_called_once()


class TestSupabaseAuthAdapter:
    """Test cases for SupabaseAuthAdapter"""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client"""
        return MockSupabaseClient()
    
    @pytest.fixture
    def supabase_service(self):
        """Create SupabaseAuthAdapter instance with mocked internal service"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SupabaseAuthService'):
            service = SupabaseAuthAdapter()
            # Create an async mock service to replace the internal one
            mock_service = AsyncMock()
            service.service = mock_service
            return service

    @pytest.mark.asyncio
    async def test_sign_up_success(self, supabase_service):
        """Test successful user signup"""
        # Setup mock response for the internal service
        supabase_service.service.sign_up.return_value = Mock(
            success=True,
            error_message=None,
            user=Mock(
                id="user123",
                email="test@example.com",
                created_at="2025-01-01T00:00:00",
                user_metadata={"username": "testuser"},
                confirmed_at="2025-01-01T00:00:00"
            ),
            session=Mock(
                access_token="access123",
                refresh_token="refresh123",
                expires_in=3600
            ),
            requires_email_verification=False
        )

        # Test signup
        result = await supabase_service.sign_up(
            email="test@example.com",
            password="password123",
            username="testuser"
        )

        # Verify
        assert result.success is True
        assert result.error_message is None
        assert result.user["email"] == "test@example.com"
        assert result.access_token == "access123"
        # Note: expires_in uses default 900 (15min), not from session
        assert result.expires_in == 900

        # Verify mock was called correctly
        supabase_service.service.sign_up.assert_called_once_with(
            "test@example.com",
            "password123",
            {"username": "testuser"}
        )
    
    @pytest.mark.asyncio
    async def test_sign_up_failure(self, supabase_service):
        """Test failed user signup"""
        # Setup mock to raise exception
        supabase_service.service.sign_up.side_effect = Exception("Email already exists")

        # Test signup
        result = await supabase_service.sign_up(
            email="test@example.com",
            password="password123"
        )

        # Verify
        assert result.success is False
        assert result.user is None
    
    @pytest.mark.asyncio
    async def test_sign_in_success(self, supabase_service):
        """Test successful user signin"""
        # Setup mock response
        supabase_service.service.sign_in.return_value = Mock(
            success=True,
            error_message=None,
            user=Mock(
                id="user123",
                email="test@example.com",
                user_metadata={},
                confirmed_at="2025-01-01T00:00:00",
                created_at="2025-01-01T00:00:00"
            ),
            session=Mock(
                access_token="access123",
                refresh_token="refresh123",
                expires_in=3600
            ),
            requires_email_verification=False
        )

        # Test signin
        result = await supabase_service.sign_in(
            email="test@example.com",
            password="password123"
        )

        # Verify
        assert result.success is True
        assert result.user["email"] == "test@example.com"
        assert result.access_token == "access123"
    
    @pytest.mark.asyncio
    async def test_sign_out(self, supabase_service):
        """Test user sign out"""
        supabase_service.service.sign_out.return_value = True

        result = await supabase_service.sign_out("some_token")

        assert result is True
        supabase_service.service.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, supabase_service):
        """Test valid token verification"""
        # Setup mock
        supabase_service.service.verify_token.return_value = Mock(
            success=True,
            error_message=None,
            user=Mock(
                id="user123",
                email="test@example.com",
                user_metadata={},
                confirmed_at="2025-01-01T00:00:00",
                created_at="2025-01-01T00:00:00"
            )
        )

        # Test
        result = await supabase_service.verify_token("valid_token")

        # Verify
        assert result.success is True
        assert result.user["email"] == "test@example.com"
        supabase_service.service.verify_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, supabase_service):
        """Test token refresh"""
        # Setup mock
        supabase_service.service.refresh_session.return_value = Mock(
            success=True,
            error_message=None,
            user=Mock(id="user123"),
            session=Mock(
                access_token="new_access",
                refresh_token="new_refresh",
                expires_in=3600
            )
        )

        # Test
        result = await supabase_service.refresh_token("old_refresh")

        # Verify
        assert result.success is True
        assert result.access_token == "new_access"
        assert result.refresh_token == "new_refresh"


class TestKeycloakAuthAdapter:
    """Test cases for KeycloakAuthAdapter"""
    
    @pytest.fixture
    def mock_keycloak_client(self):
        """Create mock Keycloak client"""
        return MockKeycloakOpenIDConnect(
            server_url="http://localhost:8080",
            realm_name="test-realm",
            client_id="test-client",
            client_secret_key="test-secret"
        )
    
    @pytest.fixture
    def keycloak_service(self):
        """Create KeycloakAuthAdapter instance with mocked internal service"""
        with patch('fastmcp.auth.keycloak_auth.KeycloakAuth'):
            service = KeycloakAuthAdapter()
            # Create an async mock keycloak client to replace the internal one
            mock_keycloak = AsyncMock()
            service.keycloak = mock_keycloak
            return service

    @pytest.mark.asyncio
    async def test_sign_in_success(self, keycloak_service):
        """Test successful Keycloak signin"""
        # Setup mock
        keycloak_service.keycloak.login.return_value = Mock(
            success=True,
            error=None,
            user={
                "sub": "user-id-123",
                "email": "test@example.com",
                "preferred_username": "testuser"
            },
            access_token="keycloak_access",
            refresh_token="keycloak_refresh"
        )

        # Test
        result = await keycloak_service.sign_in(
            email="test@example.com",
            password="password123"
        )

        # Verify
        assert result.success is True
        assert result.access_token == "keycloak_access"
        assert result.user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_sign_in_failure(self, keycloak_service):
        """Test failed Keycloak signin"""
        # Setup mock to fail
        keycloak_service.keycloak.login.side_effect = Exception("Invalid credentials")

        # Test
        result = await keycloak_service.sign_in(
            email="test@example.com",
            password="wrong_password"
        )

        # Verify
        assert result.success is False
        assert "Authentication failed" in result.error_message

    @pytest.mark.asyncio
    async def test_sign_up_not_implemented(self, keycloak_service):
        """Test Keycloak signup returns not implemented"""
        result = await keycloak_service.sign_up(
            email="test@example.com",
            password="password123"
        )

        assert result.success is False
        assert "not implemented" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_verify_token(self, keycloak_service):
        """Test token verification"""
        # Keycloak adapter returns not implemented for verify_token
        result = await keycloak_service.verify_token("valid_token")

        # Verify
        assert result.success is False
        assert "not implemented" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_refresh_token(self, keycloak_service):
        """Test token refresh"""
        # Keycloak adapter returns not implemented for refresh_token
        result = await keycloak_service.refresh_token("old_refresh")

        # Verify
        assert result.success is False
        assert "not implemented" in result.error_message.lower()


class TestLocalAuthAdapter:
    """Test cases for LocalAuthAdapter"""
    
    @pytest.fixture
    def local_service(self):
        """Create LocalAuthAdapter instance with mocked internal service"""
        from unittest.mock import Mock, AsyncMock

        service = LocalAuthAdapter()

        # Create mock auth service and db session
        mock_auth_service = AsyncMock()
        mock_db = Mock()

        # Configure mock responses for sign_up
        mock_auth_service.register_user.return_value = Mock(
            success=True,
            user=Mock(
                id="test-user-id",
                email="test@example.com",
                username="test",
                full_name=None,
                email_verified=False,
                status=Mock(value="PENDING_VERIFICATION"),
                roles=[Mock(value="user")]
            ),
            error_message=None
        )

        # Configure mock responses for sign_in
        mock_auth_service.login.return_value = Mock(
            success=True,
            access_token="local_mock_token",
            refresh_token="local_mock_refresh_token",
            user=Mock(
                id="test-user-id",
                email="test@example.com",
                username="test",
                full_name=None,
                email_verified=True,
                status=Mock(value="ACTIVE"),
                roles=[Mock(value="user")]
            ),
            error_message=None,
            requires_email_verification=False
        )

        # Configure mock responses for logout
        mock_auth_service.logout.return_value = True

        # Configure mock responses for refresh_tokens (returns tuple)
        mock_auth_service.refresh_tokens.return_value = (
            "local_mock_token",
            "local_mock_refresh_token"
        )

        # Mock JWT service for sign_out and verify_token
        service.jwt_service = Mock()
        service.jwt_service.verify_access_token.return_value = {
            "sub": "test-user-id",
            "email": "test@example.com",
            "username": "test",
            "roles": ["user"],
            "provider": "local"
        }

        # Patch _get_auth_service to return our mocks
        service._get_auth_service = Mock(return_value=(mock_auth_service, mock_db))

        return service
    
    @pytest.mark.asyncio
    async def test_local_auth_methods(self, local_service):
        """Test all LocalAuthAdapter methods return mock data"""
        # Test signup
        signup_result = await local_service.sign_up(
            email="test@example.com",
            password="password123"
        )
        assert signup_result.success is True
        assert signup_result.user["email"] == "test@example.com"
        assert signup_result.user["provider"] == "local"
        
        # Test signin
        signin_result = await local_service.sign_in(
            email="test@example.com",
            password="password123"
        )
        assert signin_result.success is True
        assert signin_result.access_token == "local_mock_token"
        
        # Test signout (returns bool, not AuthResult)
        signout_result = await local_service.sign_out("local_mock_token")
        assert signout_result is True
        
        # Test verify token
        verify_result = await local_service.verify_token("any_token")
        assert verify_result.success is True
        assert verify_result.user["id"] == "test-user-id"
        assert verify_result.user["email"] == "test@example.com"
        
        # Test refresh token
        refresh_result = await local_service.refresh_token("old_token")
        assert refresh_result.success is True
        assert refresh_result.access_token == "local_mock_token"
        assert refresh_result.refresh_token == "local_mock_refresh_token"


class TestAuthServiceInterface:
    """Test AuthServiceInterface abstract methods"""
    
    def test_interface_cannot_be_instantiated(self):
        """Test that AuthServiceInterface cannot be instantiated directly"""
        with pytest.raises(TypeError):
            AuthServiceInterface()
    
    def test_interface_methods_defined(self):
        """Test that all required methods are defined in interface"""
        required_methods = [
            "sign_up",
            "sign_in",
            "sign_out",
            "verify_token",
            "refresh_token"
        ]
        
        for method_name in required_methods:
            assert hasattr(AuthServiceInterface, method_name)
            method = getattr(AuthServiceInterface, method_name)
            assert hasattr(method, "__isabstractmethod__")
            assert method.__isabstractmethod__ is True


class TestAuthFactoryIntegration:
    """Integration tests for AuthFactory with environment configs"""
    
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "supabase",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-key"
    })
    def test_factory_creates_supabase_with_env(self):
        """Test factory creates Supabase service with environment config"""
        provider = AuthFactory.create_auth_service()
        assert isinstance(provider, SupabaseAuthAdapter)
    
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://keycloak:8080",
        "KEYCLOAK_REALM": "master",
        "KEYCLOAK_CLIENT_ID": "agenthub",
        "KEYCLOAK_CLIENT_SECRET": "secret123"
    })
    def test_factory_creates_keycloak_with_env(self):
        """Test factory creates Keycloak service with environment config"""
        provider = AuthFactory.create_auth_service()
        assert isinstance(provider, KeycloakAuthAdapter)
    
    def test_factory_singleton_behavior(self):
        """Test that factory returns same instance for same provider"""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}):
            provider1 = AuthFactory.create_auth_service()
            provider2 = AuthFactory.create_auth_service()
            
            # Should be same instance
            assert provider1 is provider2
    
    def test_factory_reset(self):
        """Test factory reset clears cached provider"""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}):
            provider1 = AuthFactory.create_auth_service()
            
            # Reset factory
            AuthFactory._instances.clear()
            
            provider2 = AuthFactory.create_auth_service()
            
            # Should be different instances after reset
            assert provider1 is not provider2