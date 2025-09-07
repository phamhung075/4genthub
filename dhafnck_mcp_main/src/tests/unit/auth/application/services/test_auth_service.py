"""
Unit tests for AuthService - Application Layer

Tests the authentication service that orchestrates authentication operations
including registration, login, password management, and token handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from fastmcp.auth.application.services.auth_service import (
    AuthService,
    LoginResult,
    RegistrationResult
)
from fastmcp.auth.domain.entities.user import User, UserStatus, UserRole
from fastmcp.auth.domain.services.password_service import PasswordService
from fastmcp.auth.domain.services.jwt_service import JWTService
from fastmcp.auth.domain.value_objects.email import Email
from fastmcp.auth.domain.value_objects.user_id import UserId


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository"""
    repository = Mock()
    repository.get_by_email = AsyncMock(return_value=None)
    repository.get_by_username = AsyncMock(return_value=None)
    repository.get_by_id = AsyncMock(return_value=None)
    repository.save = AsyncMock()
    return repository


@pytest.fixture
def mock_jwt_service():
    """Create a mock JWT service"""
    service = Mock(spec=JWTService)
    service.create_access_token = Mock(return_value="test_access_token")
    service.create_refresh_token = Mock(return_value=("test_refresh_token", "test_family"))
    service.create_reset_token = Mock(return_value="test_reset_token")
    service.verify_access_token = Mock(return_value={"sub": "test_user_id", "email": "test@example.com"})
    service.verify_refresh_token = Mock(return_value={"sub": "test_user_id", "family": "test_family", "version": 0})
    service.verify_reset_token = Mock(return_value={"sub": "test_user_id", "email": "test@example.com"})
    return service


@pytest.fixture
def mock_password_service():
    """Create a mock password service"""
    service = Mock(spec=PasswordService)
    service.hash_password = Mock(return_value="hashed_password")
    service.verify_password = Mock(return_value=True)
    service.check_password_strength = Mock(return_value={"strength": "strong", "suggestions": []})
    service.needs_rehash = Mock(return_value=False)
    service.generate_reset_token = Mock(return_value="reset_token")
    return service


@pytest.fixture
def auth_service(mock_user_repository, mock_jwt_service, mock_password_service):
    """Create an AuthService instance with mocked dependencies"""
    return AuthService(
        user_repository=mock_user_repository,
        jwt_service=mock_jwt_service,
        password_service=mock_password_service
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing"""
    return User(
        id="test_user_id",
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        full_name="Test User",
        status=UserStatus.ACTIVE,
        email_verified=True,
        roles=[UserRole.USER],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        refresh_token_family="test_family",
        refresh_token_version=0
    )


class TestAuthServiceRegistration:
    """Test user registration functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_registration(self, auth_service, mock_user_repository, mock_password_service):
        """Test successful user registration"""
        # Arrange
        email = "newuser@example.com"
        username = "newuser"
        password = "SecureP@ssw0rd"
        full_name = "New User"
        
        mock_user_repository.save.return_value = User(
            id="new_user_id",
            email=email,
            username=username,
            password_hash="hashed_password",
            full_name=full_name,
            status=UserStatus.PENDING_VERIFICATION,
            email_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Act
        result = await auth_service.register_user(email, username, password, full_name)
        
        # Assert
        assert result.success is True
        assert result.user is not None
        assert result.user.email == email
        assert result.user.username == username
        assert result.verification_token is not None
        assert result.error_message is None
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_registration_with_existing_email(self, auth_service, mock_user_repository, sample_user):
        """Test registration fails with existing email"""
        # Arrange
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        result = await auth_service.register_user(
            "test@example.com", "newusername", "SecureP@ssw0rd"
        )
        
        # Assert
        assert result.success is False
        assert result.error_message == "Email already registered"
        assert result.user is None
        mock_user_repository.save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_registration_with_existing_username(self, auth_service, mock_user_repository, sample_user):
        """Test registration fails with existing username"""
        # Arrange
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.get_by_username.return_value = sample_user
        
        # Act
        result = await auth_service.register_user(
            "new@example.com", "testuser", "SecureP@ssw0rd"
        )
        
        # Assert
        assert result.success is False
        assert result.error_message == "Username already taken"
        assert result.user is None
        mock_user_repository.save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_registration_with_weak_password(self, auth_service, mock_password_service):
        """Test registration fails with weak password"""
        # Arrange
        mock_password_service.check_password_strength.return_value = {
            "strength": "weak",
            "suggestions": ["Use uppercase letters", "Add special characters"]
        }
        
        # Act
        result = await auth_service.register_user(
            "new@example.com", "newuser", "weakpass"
        )
        
        # Assert
        assert result.success is False
        assert "Password too weak" in result.error_message
        assert "Use uppercase letters" in result.error_message
        assert result.user is None
    
    @pytest.mark.asyncio
    async def test_registration_with_invalid_email(self, auth_service):
        """Test registration fails with invalid email format"""
        # Act
        result = await auth_service.register_user(
            "invalid-email", "newuser", "SecureP@ssw0rd"
        )
        
        # Assert
        assert result.success is False
        assert "Registration failed" in result.error_message
        assert result.user is None


class TestAuthServiceLogin:
    """Test user login functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_login_with_email(self, auth_service, mock_user_repository, sample_user):
        """Test successful login with email"""
        # Arrange
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is True
        assert result.user == sample_user
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.error_message is None
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_login_with_username(self, auth_service, mock_user_repository, sample_user):
        """Test successful login with username"""
        # Arrange
        mock_user_repository.get_by_username.return_value = sample_user
        
        # Act
        result = await auth_service.login("testuser", "password")
        
        # Assert
        assert result.success is True
        assert result.user == sample_user
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
    
    @pytest.mark.asyncio
    async def test_login_with_non_existent_user(self, auth_service, mock_user_repository):
        """Test login fails with non-existent user"""
        # Arrange
        mock_user_repository.get_by_email.return_value = None
        
        # Act
        result = await auth_service.login("nonexistent@example.com", "password")
        
        # Assert
        assert result.success is False
        assert result.error_message == "Invalid credentials"
        assert result.user is None
        assert result.access_token is None
    
    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self, auth_service, mock_user_repository, mock_password_service, sample_user):
        """Test login fails with wrong password"""
        # Arrange
        mock_user_repository.get_by_email.return_value = sample_user
        mock_password_service.verify_password.return_value = False
        
        # Act
        result = await auth_service.login("test@example.com", "wrong_password")
        
        # Assert
        assert result.success is False
        assert result.error_message == "Invalid credentials"
        assert sample_user.failed_login_attempts == 1
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_with_locked_account(self, auth_service, mock_user_repository, sample_user):
        """Test login fails with locked account"""
        # Arrange
        sample_user.failed_login_attempts = 10
        sample_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is False
        assert "temporarily locked" in result.error_message
    
    @pytest.mark.asyncio
    async def test_login_with_suspended_account(self, auth_service, mock_user_repository, sample_user):
        """Test login fails with suspended account"""
        # Arrange
        sample_user.status = UserStatus.SUSPENDED
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is False
        assert result.error_message == "Account suspended"
    
    @pytest.mark.asyncio
    async def test_login_with_unverified_email(self, auth_service, mock_user_repository, sample_user):
        """Test login requires email verification"""
        # Arrange
        sample_user.email_verified = False
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is False
        assert result.requires_email_verification is True
        assert result.error_message == "Email verification required"
    
    @pytest.mark.asyncio
    async def test_login_with_password_rehash(self, auth_service, mock_user_repository, mock_password_service, sample_user):
        """Test login rehashes password when needed"""
        # Arrange
        mock_user_repository.get_by_email.return_value = sample_user
        mock_password_service.needs_rehash.return_value = True
        mock_password_service.hash_password.return_value = "new_hashed_password"
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is True
        assert sample_user.password_hash == "new_hashed_password"
        mock_password_service.hash_password.assert_called_with("password")


class TestAuthServiceEmailVerification:
    """Test email verification functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_email_verification(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test successful email verification"""
        # Arrange
        sample_user.email_verified = False
        sample_user.status = UserStatus.PENDING_VERIFICATION
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Act
        success, error = await auth_service.verify_email("valid_token")
        
        # Assert
        assert success is True
        assert error is None
        assert sample_user.email_verified is True
        assert sample_user.status == UserStatus.ACTIVE
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_verification_with_invalid_token(self, auth_service, mock_jwt_service):
        """Test email verification fails with invalid token"""
        # Arrange
        mock_jwt_service.verify_reset_token.return_value = None
        
        # Act
        success, error = await auth_service.verify_email("invalid_token")
        
        # Assert
        assert success is False
        assert error == "Invalid or expired verification token"
    
    @pytest.mark.asyncio
    async def test_email_verification_with_non_existent_user(self, auth_service, mock_user_repository, mock_jwt_service):
        """Test email verification fails with non-existent user"""
        # Arrange
        mock_user_repository.get_by_id.return_value = None
        
        # Act
        success, error = await auth_service.verify_email("valid_token")
        
        # Assert
        assert success is False
        assert error == "User not found"


class TestAuthServicePasswordReset:
    """Test password reset functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_password_reset_request(self, auth_service, mock_user_repository, sample_user):
        """Test successful password reset request"""
        # Arrange
        mock_user_repository.get_by_email.return_value = sample_user
        
        # Act
        success, token, error = await auth_service.request_password_reset("test@example.com")
        
        # Assert
        assert success is True
        assert token is not None
        assert error is None
        assert sample_user.password_reset_token is not None
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_password_reset_request_non_existent_email(self, auth_service, mock_user_repository):
        """Test password reset request with non-existent email (should not reveal)"""
        # Arrange
        mock_user_repository.get_by_email.return_value = None
        
        # Act
        success, token, error = await auth_service.request_password_reset("nonexistent@example.com")
        
        # Assert
        assert success is True  # Don't reveal if email exists
        assert token is None
        assert error is None
        mock_user_repository.save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_successful_password_reset(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test successful password reset"""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        new_password = "NewSecureP@ssw0rd"
        
        # Act
        success, error = await auth_service.reset_password("valid_token", new_password)
        
        # Assert
        assert success is True
        assert error is None
        assert sample_user.password_reset_token is None
        assert sample_user.password_reset_expires is None
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_password_reset_with_invalid_token(self, auth_service, mock_jwt_service):
        """Test password reset fails with invalid token"""
        # Arrange
        mock_jwt_service.verify_reset_token.return_value = None
        
        # Act
        success, error = await auth_service.reset_password("invalid_token", "NewPassword123!")
        
        # Assert
        assert success is False
        assert error == "Invalid or expired reset token"
    
    @pytest.mark.asyncio
    async def test_password_reset_with_weak_password(self, auth_service, mock_user_repository, mock_password_service, sample_user):
        """Test password reset fails with weak password"""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_password_service.check_password_strength.return_value = {
            "strength": "weak",
            "suggestions": ["Add numbers", "Use special characters"]
        }
        
        # Act
        success, error = await auth_service.reset_password("valid_token", "weak")
        
        # Assert
        assert success is False
        assert "Password too weak" in error
        assert "Add numbers" in error


class TestAuthServiceTokenOperations:
    """Test token refresh and validation operations"""
    
    @pytest.mark.asyncio
    async def test_successful_token_refresh(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test successful token refresh"""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_jwt_service.create_access_token.return_value = "new_access_token"
        mock_jwt_service.create_refresh_token.return_value = ("new_refresh_token", "test_family")
        
        # Act
        tokens = await auth_service.refresh_tokens("valid_refresh_token")
        
        # Assert
        assert tokens is not None
        access_token, refresh_token = tokens
        assert access_token == "new_access_token"
        assert refresh_token == "new_refresh_token"
        assert sample_user.refresh_token_version == 1
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_invalid_token(self, auth_service, mock_jwt_service):
        """Test token refresh fails with invalid token"""
        # Arrange
        mock_jwt_service.verify_refresh_token.return_value = None
        
        # Act
        tokens = await auth_service.refresh_tokens("invalid_token")
        
        # Assert
        assert tokens is None
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_wrong_family(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test token refresh fails with wrong token family"""
        # Arrange
        sample_user.refresh_token_family = "different_family"
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Act
        tokens = await auth_service.refresh_tokens("valid_refresh_token")
        
        # Assert
        assert tokens is None
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_old_version(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test token refresh fails with old token version"""
        # Arrange
        sample_user.refresh_token_version = 5
        mock_user_repository.get_by_id.return_value = sample_user
        mock_jwt_service.verify_refresh_token.return_value = {
            "sub": "test_user_id",
            "family": "test_family",
            "version": 3
        }
        
        # Act
        tokens = await auth_service.refresh_tokens("old_refresh_token")
        
        # Assert
        assert tokens is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, auth_service, mock_user_repository, mock_jwt_service, sample_user):
        """Test getting current user with valid access token"""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Act
        user = await auth_service.get_current_user("valid_access_token")
        
        # Assert
        assert user == sample_user
        mock_jwt_service.verify_access_token.assert_called_with("valid_access_token")
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, auth_service, mock_jwt_service):
        """Test getting current user fails with invalid token"""
        # Arrange
        mock_jwt_service.verify_access_token.return_value = None
        
        # Act
        user = await auth_service.get_current_user("invalid_token")
        
        # Assert
        assert user is None


class TestAuthServiceLogout:
    """Test logout functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_logout(self, auth_service, mock_user_repository, sample_user):
        """Test successful logout"""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Act
        success = await auth_service.logout("test_user_id")
        
        # Assert
        assert success is True
        mock_user_repository.save.assert_not_called()  # No save needed for simple logout
    
    @pytest.mark.asyncio
    async def test_logout_with_token_revocation(self, auth_service, mock_user_repository, sample_user):
        """Test logout with all tokens revoked"""
        # Arrange
        initial_version = sample_user.refresh_token_version
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Act
        success = await auth_service.logout("test_user_id", revoke_all_tokens=True)
        
        # Assert
        assert success is True
        assert sample_user.refresh_token_version == initial_version + 1
        mock_user_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logout_with_non_existent_user(self, auth_service, mock_user_repository):
        """Test logout fails with non-existent user"""
        # Arrange
        mock_user_repository.get_by_id.return_value = None
        
        # Act
        success = await auth_service.logout("non_existent_id")
        
        # Assert
        assert success is False


class TestAuthServiceExceptionHandling:
    """Test exception handling in auth service"""
    
    @pytest.mark.asyncio
    async def test_registration_handles_repository_exception(self, auth_service, mock_user_repository):
        """Test registration handles repository exceptions gracefully"""
        # Arrange
        mock_user_repository.save.side_effect = Exception("Database error")
        
        # Act
        result = await auth_service.register_user(
            "new@example.com", "newuser", "SecureP@ssw0rd"
        )
        
        # Assert
        assert result.success is False
        assert "Registration failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_login_handles_exception(self, auth_service, mock_user_repository):
        """Test login handles exceptions gracefully"""
        # Arrange
        mock_user_repository.get_by_email.side_effect = Exception("Database error")
        
        # Act
        result = await auth_service.login("test@example.com", "password")
        
        # Assert
        assert result.success is False
        assert result.error_message == "Login failed"
    
    @pytest.mark.asyncio
    async def test_email_verification_handles_exception(self, auth_service, mock_jwt_service):
        """Test email verification handles exceptions gracefully"""
        # Arrange
        mock_jwt_service.verify_reset_token.side_effect = Exception("Token error")
        
        # Act
        success, error = await auth_service.verify_email("token")
        
        # Assert
        assert success is False
        assert error == "Email verification failed"
    
    @pytest.mark.asyncio
    async def test_password_reset_handles_exception(self, auth_service, mock_user_repository):
        """Test password reset request handles exceptions gracefully"""
        # Arrange
        mock_user_repository.get_by_email.side_effect = Exception("Database error")
        
        # Act
        success, token, error = await auth_service.request_password_reset("test@example.com")
        
        # Assert
        assert success is False
        assert token is None
        assert error == "Password reset request failed"