"""User Domain Entity for Authentication"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

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
class User:
    """User domain entity with authentication business logic"""
    
    # Required fields
    email: str
    username: str
    password_hash: str  # Never store plain passwords
    
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
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    # Project associations
    project_ids: List[str] = field(default_factory=list)
    default_project_id: Optional[str] = None
    
    # Additional metadata
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamps and validate data"""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc)
        
        # Validate email format (basic validation)
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")
        
        # Ensure username is not empty
        if not self.username or not self.username.strip():
            raise ValueError("Username cannot be empty")
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        return "@" in email and "." in email.split("@")[1] if "@" in email else False
    
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
        return datetime.now(timezone.utc) < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can attempt login"""
        return not self.is_locked() and self.status != UserStatus.SUSPENDED
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        self.updated_at = datetime.now(timezone.utc)
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            logger.warning(f"Account locked for user {self.username} due to failed login attempts")
    
    def record_successful_login(self):
        """Record a successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verified_at = datetime.now(timezone.utc)
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def initiate_password_reset(self, token: str, expires_in_hours: int = 24):
        """Initiate password reset process"""
        from datetime import timedelta
        self.password_reset_token = token
        self.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_password_reset(self, new_password_hash: str):
        """Complete password reset"""
        self.password_hash = new_password_hash
        self.password_reset_token = None
        self.password_reset_expires = None
        self.password_changed_at = datetime.now(timezone.utc)
        self.refresh_token_version += 1  # Invalidate all existing refresh tokens
        self.updated_at = datetime.now(timezone.utc)
    
    def change_password(self, new_password_hash: str):
        """Change user password"""
        self.password_hash = new_password_hash
        self.password_changed_at = datetime.now(timezone.utc)
        self.refresh_token_version += 1  # Invalidate all existing refresh tokens
        self.updated_at = datetime.now(timezone.utc)
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def add_role(self, role: UserRole):
        """Add a role to the user"""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_role(self, role: UserRole):
        """Remove a role from the user"""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.now(timezone.utc)
    
    def suspend(self):
        """Suspend user account"""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self):
        """Activate user account"""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self):
        """Deactivate user account"""
        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
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