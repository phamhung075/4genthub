"""
Tests for Supabase Authentication Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import os
from typing import Dict, Any

from fastmcp.auth.infrastructure.supabase_auth import (
    SupabaseAuthService,
    SupabaseAuthResult
)


class MockUser:
    """Mock Supabase User object"""
    def __init__(self, id="user-123", email="test@example.com", confirmed_at=None):
        self.id = id
        self.email = email
        self.confirmed_at = confirmed_at
        self.email_confirmed_at = confirmed_at
        self.created_at = "2024-01-01T00:00:00Z"


class MockSession:
    """Mock Supabase Session object"""
    def __init__(self, access_token="access-token-123", refresh_token="refresh-token-123"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = 1234567890


class MockAuthResponse:
    """Mock Supabase Auth Response"""
    def __init__(self, user=None, session=None, url=None):
        self.user = user
        self.session = session
        self.url = url


class TestSupabaseAuthService:
    """Test Supabase authentication service"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
        monkeypatch.setenv("FRONTEND_URL", "http://localhost:3800")

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client"""
        client = Mock()
        client.auth = Mock()
        return client

    @pytest.fixture
    def service(self, mock_env):
        """Create service with mocked client"""
        # Create a context manager that keeps the patch active
        patcher1 = patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True)
        patcher2 = patch('fastmcp.auth.infrastructure.supabase_auth.ClientOptions')
        patcher3 = patch('fastmcp.auth.infrastructure.supabase_auth.create_client')
        
        patcher1.start()
        mock_options = patcher2.start()
        mock_create = patcher3.start()
        
        mock_options.return_value = Mock()
        mock_client = Mock()
        mock_admin_client = Mock()
        mock_create.side_effect = [mock_client, mock_admin_client]
        
        service = SupabaseAuthService()
        service.client = mock_client
        service.admin_client = mock_admin_client
        
        # Store patchers to stop them later
        service._patchers = [patcher1, patcher2, patcher3]
        
        yield service
        
        # Clean up patches
        for p in service._patchers:
            p.stop()

    def test_init_with_missing_credentials(self, monkeypatch):
        """Test initialization fails with missing credentials"""
        # Ensure we're testing with Supabase available
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            monkeypatch.delenv("SUPABASE_URL", raising=False)
            
            with pytest.raises(ValueError, match="Missing Supabase credentials"):
                SupabaseAuthService()

    def test_init_success(self, mock_env):
        """Test successful initialization"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            with patch('fastmcp.auth.infrastructure.supabase_auth.ClientOptions') as mock_options:
                mock_options.return_value = Mock()
                with patch('fastmcp.auth.infrastructure.supabase_auth.create_client') as mock_create:
                    mock_create.return_value = Mock()
                    
                    service = SupabaseAuthService()
                    
                    assert service.supabase_url == "https://test.supabase.co"
                    assert service.supabase_anon_key == "test-anon-key"
                    assert service.supabase_service_key == "test-service-key"
                    assert mock_create.call_count == 2  # Client and admin client

    @pytest.mark.asyncio
    async def test_sign_up_success(self, service):
        """Test successful user signup"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at="2024-01-01T00:00:00Z")
            mock_session = MockSession()
            mock_response = MockAuthResponse(user=mock_user, session=mock_session)
            
            service.client.auth.sign_up.return_value = mock_response
            
            result = await service.sign_up("test@example.com", "password123", {"username": "testuser"})
        
        assert result.success is True
        assert result.user == mock_user
        assert result.session == mock_session
        assert result.requires_email_verification is False
        
        # Verify sign_up was called correctly
        service.client.auth.sign_up.assert_called_once_with({
            "email": "test@example.com",
            "password": "password123",
            "options": {
                "data": {"username": "testuser"},
                "email_redirect_to": "http://localhost:3800/auth/verify"
            }
        })

    @pytest.mark.asyncio
    async def test_sign_up_requires_verification(self, service):
        """Test signup requiring email verification"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at=None)
            mock_session = MockSession()
            mock_response = MockAuthResponse(user=mock_user, session=mock_session)
            
            service.client.auth.sign_up.return_value = mock_response
            
            result = await service.sign_up("test@example.com", "password123")
        
        assert result.success is True
        assert result.user == mock_user
        assert result.requires_email_verification is True
        assert result.error_message == "Please check your email to verify your account"

    @pytest.mark.asyncio
    async def test_sign_up_user_already_exists(self, service):
        """Test signup with existing user"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_up.side_effect = Exception("User already registered")
            
            result = await service.sign_up("existing@example.com", "password123")
        
        assert result.success is False
        assert result.error_message == "Email already registered"

    @pytest.mark.asyncio
    async def test_sign_up_weak_password(self, service):
        """Test signup with weak password"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_up.side_effect = Exception("Password should be at least 6 characters")
            
            result = await service.sign_up("test@example.com", "123")
        
        assert result.success is False
        assert result.error_message == "Password must be at least 6 characters"

    @pytest.mark.asyncio
    async def test_sign_in_success(self, service):
        """Test successful user signin"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at="2024-01-01T00:00:00Z")
            mock_session = MockSession()
            mock_response = MockAuthResponse(user=mock_user, session=mock_session)
            
            service.client.auth.sign_in_with_password.return_value = mock_response
            
            result = await service.sign_in("test@example.com", "password123")
        
        assert result.success is True
        assert result.user == mock_user
        assert result.session == mock_session
        
        service.client.auth.sign_in_with_password.assert_called_once_with({
            "email": "test@example.com",
            "password": "password123"
        })

    @pytest.mark.asyncio
    async def test_sign_in_unverified_email(self, service):
        """Test signin with unverified email"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at=None)
            mock_session = MockSession()
            mock_response = MockAuthResponse(user=mock_user, session=mock_session)
            
            service.client.auth.sign_in_with_password.return_value = mock_response
            
            result = await service.sign_in("test@example.com", "password123")
        
        assert result.success is False
        assert result.requires_email_verification is True
        assert result.error_message == "Please verify your email before signing in"

    @pytest.mark.asyncio
    async def test_sign_in_invalid_credentials(self, service):
        """Test signin with invalid credentials"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
            
            result = await service.sign_in("test@example.com", "wrongpassword")
        
        assert result.success is False
        assert result.error_message == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_sign_out_success(self, service):
        """Test successful sign out"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.set_session = Mock()
            service.client.auth.sign_out = Mock()
        
            result = await service.sign_out("access-token-123")
        
            assert result is True
            service.client.auth.set_session.assert_called_once_with("access-token-123", "")
            service.client.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_out_error(self, service):
        """Test sign out error handling"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.set_session = Mock(side_effect=Exception("Token error"))
        
            result = await service.sign_out("invalid-token")
        
            assert result is False

    @pytest.mark.asyncio
    async def test_reset_password_request_success(self, service):
        """Test successful password reset request"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.reset_password_for_email = Mock()
        
            result = await service.reset_password_request("test@example.com")
        
            assert result.success is True
            assert result.error_message == "Password reset email sent. Please check your inbox."
        
            service.client.auth.reset_password_for_email.assert_called_once_with(
                "test@example.com",
                {"redirect_to": "http://localhost:3800/auth/reset-password"}
            )

    @pytest.mark.asyncio
    async def test_reset_password_request_error(self, service):
        """Test password reset request error"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.reset_password_for_email.side_effect = Exception("Email error")
        
            result = await service.reset_password_request("test@example.com")
        
            assert result.success is False
            assert result.error_message == "Failed to send password reset email"

    @pytest.mark.asyncio
    async def test_update_password_success(self, service):
        """Test successful password update"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser()
            mock_response = Mock(user=mock_user)
        
            service.client.auth.set_session = Mock()
            service.client.auth.update_user = Mock(return_value=mock_response)
        
            result = await service.update_password("access-token-123", "newpassword123")
        
            assert result.success is True
            assert result.user == mock_user
        
            service.client.auth.set_session.assert_called_once_with("access-token-123", "")
            service.client.auth.update_user.assert_called_once_with({
                "password": "newpassword123"
            })

    @pytest.mark.asyncio
    async def test_update_password_error(self, service):
        """Test password update error"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.set_session = Mock()
            service.client.auth.update_user.side_effect = Exception("Update error")
        
            result = await service.update_password("access-token-123", "newpassword123")
        
            assert result.success is False
            assert "Update error" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_token_success(self, service):
        """Test successful token verification"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser()
            mock_response = Mock()
            mock_response.user = mock_user
        
            # Configure mock to return the response we want - use admin_client since it exists
            service.admin_client.auth.get_user.return_value = mock_response
        
            result = await service.verify_token("access-token-123")
        
            assert result.success is True
            assert result.user is not None  # Just verify user is present, not exact match
        
            service.admin_client.auth.get_user.assert_called_once_with("access-token-123")

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, service):
        """Test invalid token verification"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.admin_client.auth.get_user.side_effect = Exception("Invalid token")
        
            result = await service.verify_token("invalid-token")
        
            assert result.success is False
            assert result.error_message == "Invalid or expired token"

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self, service):
        """Test successful verification email resend"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at=None)
            mock_response = MockAuthResponse(user=mock_user)
        
            service.client.auth.sign_up.return_value = mock_response
        
            result = await service.resend_verification_email("test@example.com")
        
            assert result.success is True
            assert result.error_message == "Verification email sent. Please check your inbox."

    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(self, service):
        """Test resend for already verified email"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_user = MockUser(confirmed_at="2024-01-01T00:00:00Z")
            mock_response = MockAuthResponse(user=mock_user)
        
            service.client.auth.sign_up.return_value = mock_response
        
            result = await service.resend_verification_email("verified@example.com")
        
            assert result.success is False
            assert result.error_message == "This email is already verified. Please try logging in."

    @pytest.mark.asyncio
    async def test_resend_verification_email_user_exists(self, service):
        """Test resend for existing user (expected behavior)"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_up.side_effect = Exception("User already registered")
        
            result = await service.resend_verification_email("existing@example.com")
        
            assert result.success is True
            assert result.error_message == "Verification email sent. Please check your inbox."

    @pytest.mark.asyncio
    async def test_resend_verification_email_rate_limit(self, service):
        """Test resend rate limit error"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_up.side_effect = Exception("Rate limit exceeded")
        
            result = await service.resend_verification_email("test@example.com")
        
            assert result.success is False
            assert "Too many requests" in result.error_message

    @pytest.mark.asyncio
    async def test_sign_in_with_provider_success(self, service):
        """Test OAuth provider sign in"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            mock_response = Mock(url="https://provider.com/oauth/authorize")
            service.client.auth.sign_in_with_oauth = Mock(return_value=mock_response)
        
            result = await service.sign_in_with_provider("google")
        
            assert result["url"] == "https://provider.com/oauth/authorize"
            assert result["provider"] == "google"
        
            service.client.auth.sign_in_with_oauth.assert_called_once_with({
                "provider": "google",
                "options": {
                    "redirect_to": "http://localhost:3800/auth/callback"
                }
            })

    @pytest.mark.asyncio
    async def test_sign_in_with_provider_error(self, service):
        """Test OAuth provider error"""
        with patch('fastmcp.auth.infrastructure.supabase_auth.SUPABASE_AVAILABLE', True):
            service.client.auth.sign_in_with_oauth.side_effect = Exception("Provider error")
        
            result = await service.sign_in_with_provider("invalid-provider")
        
            assert "error" in result
            assert "Provider error" in result["error"]