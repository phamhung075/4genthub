"""Unit tests for User Domain Entity following DDD patterns"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from fastmcp.auth.domain.entities.user import User, UserStatus, UserRole


class TestUserEntity:
    """Test suite for User domain entity following DDD patterns"""
    
    def test_user_creation_with_required_fields(self):
        """Test user creation with only required fields"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password_123"
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password_123"
        assert user.status == UserStatus.PENDING_VERIFICATION
        assert user.roles == [UserRole.USER]
        assert user.email_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_creation_with_all_fields(self):
        """Test user creation with all fields specified"""
        now = datetime.now(timezone.utc)
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password_123",
            full_name="Test User",
            status=UserStatus.ACTIVE,
            roles=[UserRole.ADMIN, UserRole.DEVELOPER],
            email_verified=True,
            email_verified_at=now,
            last_login_at=now,
            created_at=now,
            updated_at=now,
            project_ids=["proj1", "proj2"],
            default_project_id="proj1"
        )
        
        assert user.id == "user123"
        assert user.full_name == "Test User"
        assert user.status == UserStatus.ACTIVE
        assert UserRole.ADMIN in user.roles
        assert UserRole.DEVELOPER in user.roles
        assert user.email_verified is True
        assert user.project_ids == ["proj1", "proj2"]
        assert user.default_project_id == "proj1"
    
    def test_invalid_email_raises_error(self):
        """Test that invalid email format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid email format"):
            User(
                email="invalid-email",
                username="testuser",
                password_hash="hashed_password"
            )
    
    def test_empty_username_raises_error(self):
        """Test that empty username raises ValueError"""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            User(
                email="test@example.com",
                username="",
                password_hash="hashed_password"
            )
        
        with pytest.raises(ValueError, match="Username cannot be empty"):
            User(
                email="test@example.com",
                username="   ",
                password_hash="hashed_password"
            )
    
    def test_is_active_checks_all_conditions(self):
        """Test is_active method checks status, email verification, and lock status"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Initially not active (not verified, pending status)
        assert user.is_active() is False
        
        # Verify email and activate
        user.verify_email()
        assert user.is_active() is True
        
        # Suspend user
        user.suspend()
        assert user.is_active() is False
        
        # Reactivate but lock account
        user.activate()
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        assert user.is_active() is False
    
    def test_is_locked_checks_lock_expiry(self):
        """Test is_locked method checks lock expiry time"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Initially not locked
        assert user.is_locked() is False
        
        # Lock for 1 hour
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        assert user.is_locked() is True
        
        # Lock already expired
        user.locked_until = datetime.now(timezone.utc) - timedelta(hours=1)
        assert user.is_locked() is False
    
    def test_can_login_checks_lock_and_suspension(self):
        """Test can_login method checks lock and suspension status"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Initially can login (not locked, not suspended)
        assert user.can_login() is True
        
        # Lock account
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        assert user.can_login() is False
        
        # Unlock but suspend
        user.locked_until = None
        user.suspend()
        assert user.can_login() is False
    
    def test_record_failed_login_increments_attempts(self):
        """Test record_failed_login increments attempts and locks after threshold"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Record 4 failed attempts - should not lock
        for i in range(4):
            user.record_failed_login()
            assert user.failed_login_attempts == i + 1
            assert user.locked_until is None
        
        # 5th attempt should lock the account
        user.record_failed_login()
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.is_locked() is True
    
    def test_record_successful_login_resets_failures(self):
        """Test record_successful_login resets failure count and unlock"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Set up failed state
        user.failed_login_attempts = 3
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Record successful login
        user.record_successful_login()
        
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at is not None
    
    def test_verify_email_updates_status(self):
        """Test verify_email updates verification status and user status"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        assert user.email_verified is False
        assert user.status == UserStatus.PENDING_VERIFICATION
        
        user.verify_email()
        
        assert user.email_verified is True
        assert user.email_verified_at is not None
        assert user.status == UserStatus.ACTIVE
    
    def test_initiate_password_reset(self):
        """Test initiate_password_reset sets token and expiry"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        token = "reset_token_123"
        user.initiate_password_reset(token, expires_in_hours=2)
        
        assert user.password_reset_token == token
        assert user.password_reset_expires is not None
        assert user.password_reset_expires > datetime.now(timezone.utc)
    
    def test_complete_password_reset(self):
        """Test complete_password_reset updates password and clears reset fields"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="old_hash"
        )
        
        # Set up reset state
        user.password_reset_token = "token123"
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        old_version = user.refresh_token_version
        
        # Complete reset
        new_hash = "new_password_hash"
        user.complete_password_reset(new_hash)
        
        assert user.password_hash == new_hash
        assert user.password_reset_token is None
        assert user.password_reset_expires is None
        assert user.password_changed_at is not None
        assert user.refresh_token_version == old_version + 1
    
    def test_change_password(self):
        """Test change_password updates hash and token version"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="old_hash"
        )
        
        old_version = user.refresh_token_version
        new_hash = "new_password_hash"
        
        user.change_password(new_hash)
        
        assert user.password_hash == new_hash
        assert user.password_changed_at is not None
        assert user.refresh_token_version == old_version + 1
    
    def test_role_management(self):
        """Test role checking, adding, and removing"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Initial role
        assert user.has_role(UserRole.USER) is True
        assert user.has_role(UserRole.ADMIN) is False
        
        # Add role
        user.add_role(UserRole.ADMIN)
        assert user.has_role(UserRole.ADMIN) is True
        assert len(user.roles) == 2
        
        # Add duplicate role (should not add)
        user.add_role(UserRole.ADMIN)
        assert len(user.roles) == 2
        
        # Remove role
        user.remove_role(UserRole.ADMIN)
        assert user.has_role(UserRole.ADMIN) is False
        assert len(user.roles) == 1
    
    def test_status_transitions(self):
        """Test suspend, activate, and deactivate status transitions"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        
        # Suspend
        user.suspend()
        assert user.status == UserStatus.SUSPENDED
        
        # Activate
        user.activate()
        assert user.status == UserStatus.ACTIVE
        
        # Deactivate
        user.deactivate()
        assert user.status == UserStatus.INACTIVE
    
    def test_to_dict_excludes_sensitive_data(self):
        """Test to_dict excludes sensitive information"""
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="secret_hash",
            password_reset_token="secret_token",
            refresh_token_family="secret_family"
        )
        
        user_dict = user.to_dict()
        
        # Should include safe fields
        assert user_dict["id"] == "user123"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["username"] == "testuser"
        
        # Should exclude sensitive fields
        assert "password_hash" not in user_dict
        assert "password_reset_token" not in user_dict
        assert "refresh_token_family" not in user_dict
    
    def test_from_dict_creates_user(self):
        """Test from_dict creates User instance from dictionary"""
        now = datetime.now(timezone.utc)
        data = {
            "id": "user123",
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hashed_password",
            "status": "active",
            "roles": ["admin", "developer"],
            "email_verified": True,
            "email_verified_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        user = User.from_dict(data)
        
        assert user.id == "user123"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.status == UserStatus.ACTIVE
        assert UserRole.ADMIN in user.roles
        assert UserRole.DEVELOPER in user.roles
        assert user.email_verified is True
        assert isinstance(user.email_verified_at, datetime)
        assert isinstance(user.created_at, datetime)
    
    def test_from_dict_handles_none_dates(self):
        """Test from_dict handles None date values correctly"""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hashed_password",
            "email_verified_at": None,
            "last_login_at": None
        }
        
        user = User.from_dict(data)
        
        assert user.email_verified_at is None
        assert user.last_login_at is None
    
    def test_user_metadata_field(self):
        """Test user metadata field for storing additional data"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            metadata={"preferences": {"theme": "dark"}}
        )
        
        assert user.metadata == {"preferences": {"theme": "dark"}}
        
        # Metadata should be included in to_dict
        user_dict = user.to_dict()
        assert user_dict["metadata"] == {"preferences": {"theme": "dark"}}
    
    def test_project_associations(self):
        """Test project ID associations"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            project_ids=["proj1", "proj2"],
            default_project_id="proj1"
        )
        
        assert user.project_ids == ["proj1", "proj2"]
        assert user.default_project_id == "proj1"
        
        # Should be included in to_dict
        user_dict = user.to_dict()
        assert user_dict["project_ids"] == ["proj1", "proj2"]
        assert user_dict["default_project_id"] == "proj1"