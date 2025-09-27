"""User Domain Entity for Authentication"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from fastmcp.task_management.domain.entities.base.base_timestamp_entity import BaseTimestampEntity

logger = logging.getLogger(__name__)


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserRole(str, Enum):
    """User role in the system"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    DEVELOPER = "developer"


@dataclass
class User(BaseTimestampEntity):
    """User domain entity with authentication business logic"""
    
    # Required fields with default values to fix dataclass ordering
    email: str = ""
    username: str = ""
    password_hash: str = ""  # Never store plain passwords

    # Optional fields
    id: Optional[str] = None
    full_name: Optional[str] = None
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    roles: List[UserRole] = field(default_factory=lambda: [UserRole.USER])
    
    # Authentication tracking
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    # Password management
    password_changed_at: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    
    # JWT refresh tokens (storing token family for security)
    refresh_token_family: Optional[str] = None
    refresh_token_version: int = 0
    
    # Metadata (timestamps inherited from BaseTimestampEntity)
    created_by: Optional[str] = None
    
    # Project associations
    project_ids: List[str] = field(default_factory=list)
    default_project_id: Optional[str] = None
    
    # Additional metadata
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamps and validate data"""
        # Initialize base timestamp entity first
        super().__post_init__()

    def _get_entity_id(self) -> str:
        """Get entity ID for BaseTimestampEntity"""
        return str(self.id) if self.id else f"user:{self.username}"
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        return "@" in email and "." in email.split("@")[1] if "@" in email else False

    def _validate_entity(self) -> None:
        """Ensure user invariants hold."""
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")
        if not self.username or not self.username.strip():
            raise ValueError("Username cannot be empty")
    
    def is_active(self) -> bool:
        """Check if user account is active and can login"""
        return (
            self.status == UserStatus.ACTIVE 
            and self.email_verified
            and not self.is_locked()
        )
    
    def is_locked(self) -> bool:
        """Check if account is temporarily locked"""
        if not self.locked_until:
            return False
        current_time = datetime.now(timezone.utc)
        return current_time < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can attempt login"""
        return not self.is_locked() and self.status != UserStatus.SUSPENDED
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        self.touch("failed_login_recorded")

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            current_time = datetime.now(timezone.utc)
            self.locked_until = current_time + timedelta(minutes=30)
            logger.warning(f"Account locked for user {self.username} due to failed login attempts")
    
    def record_successful_login(self):
        """Record a successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        current_time = datetime.now(timezone.utc)
        self.last_login_at = current_time
        self.touch("login_successful")
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        current_time = datetime.now(timezone.utc)
        self.email_verified_at = current_time
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE
        self.touch("email_verified")
    
    def initiate_password_reset(self, token: str, expires_in_hours: int = 24):
        """Initiate password reset process"""
        from datetime import timedelta
        self.password_reset_token = token
        current_time = datetime.now(timezone.utc)
        self.password_reset_expires = current_time + timedelta(hours=expires_in_hours)
        self.touch("password_reset_initiated")
    
    def complete_password_reset(self, new_password_hash: str):
        """Complete password reset"""
        self.password_hash = new_password_hash
        self.password_reset_token = None
        self.password_reset_expires = None
        current_time = datetime.now(timezone.utc)
        self.password_changed_at = current_time
        self.refresh_token_version += 1  # Invalidate all existing refresh tokens
        self.touch("password_reset_completed")
    
    def change_password(self, new_password_hash: str):
        """Change user password"""
        self.password_hash = new_password_hash
        current_time = datetime.now(timezone.utc)
        self.password_changed_at = current_time
        self.refresh_token_version += 1  # Invalidate all existing refresh tokens
        self.touch("password_changed")
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def add_role(self, role: UserRole):
        """Add a role to the user"""
        if role not in self.roles:
            self.roles.append(role)
            self.touch("role_added")
    
    def remove_role(self, role: UserRole):
        """Remove a role from the user"""
        if role in self.roles:
            self.roles.remove(role)
            self.touch("role_removed")
    
    def suspend(self):
        """Suspend user account"""
        self.status = UserStatus.SUSPENDED
        self.touch("account_suspended")
    
    def activate(self):
        """Activate user account"""
        self.status = UserStatus.ACTIVE
        self.touch("account_activated")
    
    def deactivate(self):
        """Deactivate user account"""
        self.status = UserStatus.INACTIVE
        self.touch("account_deactivated")
    
    def to_dict(self) -> dict:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "roles": [r.value if isinstance(r, UserRole) else r for r in self.roles],
            "email_verified": self.email_verified,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "project_ids": self.project_ids,
            "default_project_id": self.default_project_id,
            "metadata": self.metadata,
            # Never expose password_hash, tokens, or security-related fields
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary"""
        # Parse dates
        for date_field in ["created_at", "updated_at", "email_verified_at", "last_login_at", 
                          "password_changed_at", "password_reset_expires", "locked_until"]:
            if date_field in data and data[date_field]:
                if isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(data[date_field])
        
        # Parse enums
        if "status" in data and isinstance(data["status"], str):
            data["status"] = UserStatus(data["status"])
        
        if "roles" in data:
            data["roles"] = [UserRole(r) if isinstance(r, str) else r for r in data["roles"]]
        
        return cls(**data)
