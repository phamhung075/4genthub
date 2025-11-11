"""
Database model for API tokens.
"""

from datetime import UTC, datetime

from sqlalchemy import ARRAY, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import JSON

Base = declarative_base()


class ApiToken(Base):
    """
    Database model for API tokens.
    Stores tokens generated for users to access the MCP API.
    This is the SOURCE OF TRUTH for the database schema.
    """

    __tablename__ = "api_tokens"

    # Token identification
    id = Column(String(36), primary_key=True)  # tok_xxxxx format
    user_id = Column(String(36), nullable=False, index=True)  # Keycloak user ID
    name = Column(String(255), nullable=False)

    # Token data (we store the hash, not the actual token for security)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)

    # Permissions - using ARRAY as per ORM design
    scopes = Column(ARRAY(String), nullable=False, default=list)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    rate_limit = Column(Integer, default=1000, nullable=False)

    # Detailed usage statistics (operation-level tracking)
    # Stores counts like: {"task_create": 10, "task_update": 5, "subtask_create": 3, "agent_call": 20}
    usage_stats = Column(JSON, nullable=False, default=dict)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self, include_token=False, token_value=None):
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "name": self.name,
            "scopes": self.scopes or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat()
            if self.last_used_at
            else None,
            "usage_count": self.usage_count,
            "rate_limit": self.rate_limit,
            "usage_stats": self.usage_stats or {},
            "is_active": self.is_active,
            "user_id": self.user_id,
        }

        # Only include the actual token when generating (not on list/get)
        if include_token and token_value:
            result["token"] = token_value

        return result
