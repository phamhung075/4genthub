"""
Test suite for Supabase Authentication Service

Tests the Supabase authentication integration including sign up, sign in,
password reset, token verification, and OAuth capabilities.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any, Optional

from fastmcp.auth.infrastructure.supabase_auth import (
    SupabaseAuthService,
    SupabaseAuthResult
)


# Mock classes for Supabase responses
@dataclass
class MockUser:
    """Mock Supabase user object"""
    id: str = "test-user-id"
    email: str = "test@example.com"
    confirmed_at: Optional[str] = "2024-01-01T00:00:00Z"
    email_confirmed_at: Optional[str] = "2024-01-01T00:00:00Z"
    created_at: str = "2024-01-01T00:00:00Z"
    updated_at: str = "2024-01-01T00:00:00Z"
    last_sign_in_at: str = "2024-01-01T00:00:00Z"


@dataclass
class MockSession:
    """Mock Supabase session object"""
    access_token: str = "mock-access-token"
    refresh_token: str = "mock-refresh-token"
    expires_at: int = 1234567890


@dataclass
class MockAuthResponse:
    """Mock Supabase auth response"""
    user: Optional[MockUser] = None
    session: Optional[MockSession] = None
    url: Optional[str] = None


class TestSupabaseAuthService:
    """Test suite for SupabaseAuthService"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "mock-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock-service-key")
        monkeypatch.setenv("FRONTEND_URL", "http://localhost:3800")

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client"""
        client = MagicMock()
        client.auth = MagicMock()
        return client

    @pytest.fixture
    @patch('fastmcp.auth.infrastructure.supabase_auth.create_client')
    def auth_service(self, mock_create_client, mock_env):
        """Create SupabaseAuthService with mocked dependencies"""
        mock_client = MagicMock()
        mock_admin_client = MagicMock()
        mock_create_client.side_effect = [mock_client, mock_admin_client]
        
        service = SupabaseAuthService()
        service.client = mock_client
        service.admin_client = mock_admin_client
        
        return service

    @pytest.mark.asyncio
    async def test_init_with_missing_credentials(self, monkeypatch):
        """Test initialization fails with missing credentials"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        
        with pytest.raises(ValueError, match="Missing Supabase credentials"):
            SupabaseAuthService()

    @pytest.mark.asyncio
    async def test_sign_up_success(self, auth_service):
        """Test successful user sign up"""
        # Mock successful response
        mock_user = MockUser(confirmed_at=None)  # Unconfirmed user
        mock_session = MockSession()
        auth_service.client.auth.sign_up.return_value = MockAuthResponse(
            user=mock_user,
            session=mock_session
        )
        
        result = await auth_service.sign_up(
            email="newuser@example.com",
            password="securepassword123",
            metadata={"username": "newuser"}
        )
        
        assert result.success is True
        assert result.user == mock_user
        assert result.session == mock_session
        assert result.requires_email_verification is True
        assert result.error_message == "Please check your email to verify your account"
        
        # Verify the sign_up call
        auth_service.client.auth.sign_up.assert_called_once()
        call_args = auth_service.client.auth.sign_up.call_args[0][0]
        assert call_args["email"] == "newuser@example.com"
        assert call_args["password"] == "securepassword123"
        assert call_args["options"]["data"] == {"username": "newuser"}

    @pytest.mark.asyncio
    async def test_sign_up_with_confirmed_email(self, auth_service):
        """Test sign up when email confirmation is disabled"""
        # Mock confirmed user
        mock_user = MockUser(confirmed_at="2024-01-01T00:00:00Z")
        mock_session = MockSession()
        auth_service.client.auth.sign_up.return_value = MockAuthResponse(
            user=mock_user,
            session=mock_session
        )
        
        result = await auth_service.sign_up(
            email="newuser@example.com",
            password="securepassword123"
        )
        
        assert result.success is True
        assert result.requires_email_verification is False
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_sign_up_user_already_exists(self, auth_service):
        """Test sign up with already registered email"""
        auth_service.client.auth.sign_up.side_effect = Exception("User already registered")
        
        result = await auth_service.sign_up(
            email="existing@example.com",
            password="password123"
        )
        
        assert result.success is False
        assert result.error_message == "Email already registered"

    @pytest.mark.asyncio
    async def test_sign_up_weak_password(self, auth_service):
        """Test sign up with weak password"""
        auth_service.client.auth.sign_up.side_effect = Exception("Password should be at least 6 characters")
        
        result = await auth_service.sign_up(
            email="newuser@example.com",
            password="123"
        )
        
        assert result.success is False
        assert result.error_message == "Password must be at least 6 characters"

    @pytest.mark.asyncio
    async def test_sign_in_success(self, auth_service):
        """Test successful user sign in"""
        mock_user = MockUser()
        mock_session = MockSession()
        auth_service.client.auth.sign_in_with_password.return_value = MockAuthResponse(
            user=mock_user,
            session=mock_session
        )
        
        result = await auth_service.sign_in(
            email="test@example.com",
            password="password123"
        )
        
        assert result.success is True
        assert result.user == mock_user
        assert result.session == mock_session
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_sign_in_unverified_email(self, auth_service):
        """Test sign in with unverified email"""
        mock_user = MockUser(confirmed_at=None)
        auth_service.client.auth.sign_in_with_password.return_value = MockAuthResponse(
            user=mock_user,
            session=None
        )
        
        result = await auth_service.sign_in(
            email="unverified@example.com",
            password="password123"
        )
        
        assert result.success is False
        assert result.requires_email_verification is True
        assert result.error_message == "Please verify your email before signing in"

    @pytest.mark.asyncio
    async def test_sign_in_invalid_credentials(self, auth_service):
        """Test sign in with invalid credentials"""
        auth_service.client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        
        result = await auth_service.sign_in(
            email="test@example.com",
            password="wrongpassword"
        )
        
        assert result.success is False
        assert result.error_message == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_sign_out_success(self, auth_service):
        """Test successful sign out"""
        auth_service.client.auth.sign_out.return_value = None
        
        result = await auth_service.sign_out("mock-access-token")
        
        assert result is True
        auth_service.client.auth.set_session.assert_called_once_with("mock-access-token", "")
        auth_service.client.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_out_failure(self, auth_service):
        """Test sign out failure"""
        auth_service.client.auth.sign_out.side_effect = Exception("Sign out error")
        
        result = await auth_service.sign_out("mock-access-token")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_password_request_success(self, auth_service):
        """Test successful password reset request"""
        auth_service.client.auth.reset_password_for_email.return_value = None
        
        result = await auth_service.reset_password_request("test@example.com")
        
        assert result.success is True
        assert result.error_message == "Password reset email sent. Please check your inbox."
        
        auth_service.client.auth.reset_password_for_email.assert_called_once_with(
            "test@example.com",
            {"redirect_to": "http://localhost:3800/auth/reset-password"}
        )

    @pytest.mark.asyncio
    async def test_reset_password_request_failure(self, auth_service):
        """Test password reset request failure"""
        auth_service.client.auth.reset_password_for_email.side_effect = Exception("Network error")
        
        result = await auth_service.reset_password_request("test@example.com")
        
        assert result.success is False
        assert result.error_message == "Failed to send password reset email"

    @pytest.mark.asyncio
    async def test_update_password_success(self, auth_service):
        """Test successful password update"""
        mock_user = MockUser()
        auth_service.client.auth.update_user.return_value = MockAuthResponse(user=mock_user)
        
        result = await auth_service.update_password("mock-access-token", "newpassword123")
        
        assert result.success is True
        assert result.user == mock_user
        
        auth_service.client.auth.set_session.assert_called_once_with("mock-access-token", "")
        auth_service.client.auth.update_user.assert_called_once_with({"password": "newpassword123"})

    @pytest.mark.asyncio
    async def test_update_password_failure(self, auth_service):
        """Test password update failure"""
        auth_service.client.auth.update_user.return_value = MockAuthResponse(user=None)
        
        result = await auth_service.update_password("mock-access-token", "newpassword123")
        
        assert result.success is False
        assert result.error_message == "Failed to update password"

    @pytest.mark.asyncio
    async def test_verify_token_success_with_admin_client(self, auth_service):
        """Test successful token verification with admin client"""
        mock_user = MockUser()
        auth_service.admin_client.auth.get_user.return_value = MockAuthResponse(user=mock_user)
        
        result = await auth_service.verify_token("valid-token")
        
        assert result.success is True
        assert result.user == mock_user
        auth_service.admin_client.auth.get_user.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_verify_token_success_without_admin_client(self, auth_service):
        """Test token verification without admin client"""
        # Remove admin client
        auth_service.admin_client = None
        
        mock_user = MockUser()
        auth_service.client.auth.get_user.return_value = MockAuthResponse(user=mock_user)
        
        result = await auth_service.verify_token("valid-token")
        
        assert result.success is True
        assert result.user == mock_user
        auth_service.client.auth.get_user.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service):
        """Test verification of invalid token"""
        auth_service.admin_client.auth.get_user.return_value = MockAuthResponse(user=None)
        
        result = await auth_service.verify_token("invalid-token")
        
        assert result.success is False
        assert result.error_message == "Invalid or expired token"

    @pytest.mark.asyncio
    async def test_verify_token_exception(self, auth_service):
        """Test token verification with exception"""
        auth_service.admin_client.auth.get_user.side_effect = Exception("JWT expired")
        
        result = await auth_service.verify_token("expired-token")
        
        assert result.success is False
        assert result.error_message == "Invalid or expired token"

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self, auth_service):
        """Test successful resend of verification email"""
        mock_user = MockUser(confirmed_at=None)  # Unconfirmed user
        auth_service.client.auth.sign_up.return_value = MockAuthResponse(user=mock_user)
        
        result = await auth_service.resend_verification_email("unverified@example.com")
        
        assert result.success is True
        assert result.error_message == "Verification email sent. Please check your inbox."

    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(self, auth_service):
        """Test resend for already verified email"""
        mock_user = MockUser(confirmed_at="2024-01-01T00:00:00Z")
        auth_service.client.auth.sign_up.return_value = MockAuthResponse(user=mock_user)
        
        result = await auth_service.resend_verification_email("verified@example.com")
        
        assert result.success is False
        assert result.error_message == "This email is already verified. Please try logging in."

    @pytest.mark.asyncio
    async def test_resend_verification_email_rate_limit(self, auth_service):
        """Test resend with rate limit error"""
        auth_service.client.auth.sign_up.side_effect = Exception("Rate limit exceeded")
        
        result = await auth_service.resend_verification_email("test@example.com")
        
        assert result.success is False
        assert result.error_message == "Too many requests. Please wait 60 seconds before trying again."

    @pytest.mark.asyncio
    async def test_resend_verification_already_registered(self, auth_service):
        """Test resend for already registered user"""
        auth_service.client.auth.sign_up.side_effect = Exception("User already registered")
        
        result = await auth_service.resend_verification_email("existing@example.com")
        
        assert result.success is True
        assert result.error_message == "Verification email sent. Please check your inbox."

    @pytest.mark.asyncio
    async def test_sign_in_with_provider_success(self, auth_service):
        """Test successful OAuth provider sign in"""
        auth_service.client.auth.sign_in_with_oauth.return_value = MockAuthResponse(
            url="https://provider.com/oauth/authorize?..."
        )
        
        result = await auth_service.sign_in_with_provider("google")
        
        assert result["url"] == "https://provider.com/oauth/authorize?..."
        assert result["provider"] == "google"
        assert "error" not in result
        
        auth_service.client.auth.sign_in_with_oauth.assert_called_once_with({
            "provider": "google",
            "options": {
                "redirect_to": "http://localhost:3800/auth/callback"
            }
        })

    @pytest.mark.asyncio
    async def test_sign_in_with_provider_failure(self, auth_service):
        """Test OAuth provider sign in failure"""
        auth_service.client.auth.sign_in_with_oauth.side_effect = Exception("Invalid provider")
        
        result = await auth_service.sign_in_with_provider("invalid_provider")
        
        assert "error" in result
        assert result["error"] == "Invalid provider"