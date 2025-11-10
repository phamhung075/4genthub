"""
SQLAlchemy ORM Models for Authentication System

This module defines the User model for authentication,
supporting both SQLite and PostgreSQL databases.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Import from task management for database base and potential relationships
from fastmcp.task_management.infrastructure.database.database_config import Base

# Import domain enums
from ...domain.entities.user import UserRole, UserStatus


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    
    # Authentication fields
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile fields
    full_name: Mapped[str | None] = mapped_column(String(255))
    
    # Status and roles
    status: Mapped[str] = mapped_column(
        SQLEnum(UserStatus, native_enum=False, length=50),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION
    )
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)  # Store as JSON array
    
    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Password management
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Refresh token management
    refresh_token_family: Mapped[str | None] = mapped_column(String(255))
    refresh_token_version: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))
    
    # Project associations (stored as JSON for flexibility)
    project_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    
    # Additional metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_username', 'username'),
        Index('ix_users_status', 'status'),
        Index('ix_users_password_reset_token', 'password_reset_token'),
        Index('ix_users_refresh_token_family', 'refresh_token_family'),
        CheckConstraint('length(email) > 0', name='check_email_not_empty'),
        CheckConstraint('length(username) > 0', name='check_username_not_empty'),
    )
    
    def to_domain(self) -> "User":
        """Convert SQLAlchemy model to domain entity"""
        from ...domain.entities.user import User as DomainUser
        from ...domain.entities.user import UserStatus
        
        return DomainUser(
            id=self.id,
            email=self.email,
            username=self.username,
            password_hash=self.password_hash,
            full_name=self.full_name,
            status=UserStatus(self.status) if isinstance(self.status, str) else self.status,
            roles=[UserRole(r) for r in self.roles] if self.roles else [UserRole.USER],
            email_verified=self.email_verified,
            email_verified_at=self.email_verified_at,
            last_login_at=self.last_login_at,
            failed_login_attempts=self.failed_login_attempts,
            locked_until=self.locked_until,
            password_changed_at=self.password_changed_at,
            password_reset_token=self.password_reset_token,
            password_reset_expires=self.password_reset_expires,
            refresh_token_family=self.refresh_token_family,
            refresh_token_version=self.refresh_token_version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by,
            project_ids=self.project_ids or [],
            default_project_id=self.default_project_id,
        )
    
    @classmethod
    def from_domain(cls, domain_user: "User") -> "User":
        """Create SQLAlchemy model from domain entity"""
        # Ensure status is converted to string value
        if hasattr(domain_user.status, 'value'):
            status_value = domain_user.status.value
        elif isinstance(domain_user.status, str):
            # If it's already a string, check if it needs conversion
            if domain_user.status in ['PENDING_VERIFICATION', 'ACTIVE', 'INACTIVE', 'SUSPENDED']:
                # Convert enum name to enum value
                status_mapping = {
                    'PENDING_VERIFICATION': 'pending_verification',
                    'ACTIVE': 'active',
                    'INACTIVE': 'inactive', 
                    'SUSPENDED': 'suspended'
                }
                status_value = status_mapping.get(domain_user.status, domain_user.status.lower())
            else:
                status_value = domain_user.status
        else:
            status_value = str(domain_user.status).lower()
        
        return cls(
            id=domain_user.id or str(uuid.uuid4()),
            email=domain_user.email,
            username=domain_user.username,
            password_hash=domain_user.password_hash,
            full_name=domain_user.full_name,
            status=status_value,
            roles=[r.value if hasattr(r, 'value') else r for r in domain_user.roles],
            email_verified=domain_user.email_verified,
            email_verified_at=domain_user.email_verified_at,
            last_login_at=domain_user.last_login_at,
            failed_login_attempts=domain_user.failed_login_attempts,
            locked_until=domain_user.locked_until,
            password_changed_at=domain_user.password_changed_at,
            password_reset_token=domain_user.password_reset_token,
            password_reset_expires=domain_user.password_reset_expires,
            refresh_token_family=domain_user.refresh_token_family,
            refresh_token_version=domain_user.refresh_token_version,
            created_at=domain_user.created_at or datetime.now(UTC),
            updated_at=domain_user.updated_at or datetime.now(UTC),
            created_by=domain_user.created_by,
            project_ids=domain_user.project_ids,
            default_project_id=domain_user.default_project_id,
        )


class UserSession(Base):
    """User session tracking for security and analytics"""
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Session details
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(255), unique=True)
    
    # Session metadata
    ip_address: Mapped[str | None] = mapped_column(String(45))  # Supports IPv6
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_user_sessions_user_id', 'user_id'),
        Index('ix_user_sessions_session_token', 'session_token'),
        Index('ix_user_sessions_refresh_token', 'refresh_token'),
        Index('ix_user_sessions_is_active', 'is_active'),
    )


class UserTokenBalance(Base):
    """Token balance tracking for user quotas and consumption"""
    __tablename__ = "user_token_balances"

    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Current balance
    available_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)

    # Reset tracking
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_reset_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Usage statistics
    tokens_consumed_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_consumed_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationship to user (optional, for easier queries)
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="select")

    # Indexes for performance
    __table_args__ = (
        Index('ix_user_token_balances_user_id', 'user_id'),
        CheckConstraint('available_tokens >= 0', name='check_available_tokens_non_negative'),
        CheckConstraint('monthly_quota >= 0', name='check_monthly_quota_non_negative'),
    )