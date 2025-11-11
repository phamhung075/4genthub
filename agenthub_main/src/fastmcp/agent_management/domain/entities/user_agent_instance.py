"""UserAgentInstance Domain Entity - User-specific customizable agent instance"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastmcp.task_management.domain.entities.base.base_timestamp_entity import (
    BaseTimestampEntity,
)

from ..value_objects.agent_configuration import AgentConfiguration
from ..value_objects.agent_template_id import AgentTemplateId
from ..value_objects.user_agent_instance_id import UserAgentInstanceId
from ..value_objects.user_id import UserId

logger = logging.getLogger(__name__)


@dataclass
class UserAgentInstance(BaseTimestampEntity):
    """User-specific agent instance with customization capabilities.

    This entity represents a user's personal instance of an agent template.
    Users can customize these instances, share them publicly, and import
    instances from other users.

    Business Rules:
        - UNIQUE(user_id, template_id): Each user can have only one instance per template
        - is_customized=True when configuration differs from template default
        - is_enabled=True by default; controls visibility in call_agent tools
        - share_token is 64-char random string when visibility='public'
        - original_creator_id is set when instance is imported from another user
        - usage_count increments on each call_agent invocation

    Attributes:
        id: Unique identifier for this instance (UUID)
        user_id: ID of the user who owns this instance
        template_id: ID of the template this instance is based on
        agent_name: Custom name for this instance (defaults to template name)
        is_customized: True if user has modified the configuration
        is_enabled: True if agent is enabled for use in call_agent tools
        configuration: Agent configuration (can be customized)
        visibility: 'private' or 'public' (public allows sharing)
        share_token: Secure token for sharing (None if private)
        original_creator_id: User ID of original creator (if imported)
        usage_count: Number of times this instance has been invoked
        last_used_at: Timestamp of last invocation
        metadata: Additional instance metadata

    DDD Patterns:
        - Aggregate root for user agent instance
        - Value objects for all IDs (type safety)
        - Domain methods for business logic (customize, track_usage)
        - Immutable configuration through AgentConfiguration value object
    """

    id: UserAgentInstanceId | None = None
    user_id: UserId | None = None
    template_id: AgentTemplateId | None = None
    agent_name: str = ""
    is_customized: bool = False
    is_enabled: bool = True  # Default to enabled
    configuration: AgentConfiguration | None = None
    visibility: str = "private"  # 'private' or 'public'
    share_token: str | None = None
    original_creator_id: UserId | None = None
    usage_count: int = 0
    last_used_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize timestamps and validate entity."""
        # Ensure configuration is an AgentConfiguration instance
        if self.configuration is not None and isinstance(self.configuration, dict):
            object.__setattr__(
                self, "configuration", AgentConfiguration.from_dict(self.configuration)
            )

        # Call parent initialization for timestamps
        super().__post_init__()

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity.

        Returns:
            str: String representation of the instance ID
        """
        return str(self.id) if self.id else "unknown"

    def _validate_entity(self) -> None:
        """Validate instance business rules (invariants).

        Raises:
            ValueError: If any business rules are violated
        """
        if not self.user_id:
            raise ValueError("UserAgentInstance must have a user_id")

        if not self.template_id:
            raise ValueError("UserAgentInstance must have a template_id")

        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("UserAgentInstance agent_name cannot be empty")

        if self.visibility not in ("private", "public"):
            raise ValueError(
                f"UserAgentInstance visibility must be 'private' or 'public', got '{self.visibility}'"
            )

        if self.visibility == "public" and not self.share_token:
            raise ValueError(
                "UserAgentInstance with visibility='public' must have a share_token"
            )

        if self.visibility == "private" and self.share_token:
            raise ValueError(
                "UserAgentInstance with visibility='private' should not have a share_token"
            )

        if self.configuration is None:
            raise ValueError("UserAgentInstance must have a configuration")

        if self.usage_count < 0:
            raise ValueError("UserAgentInstance usage_count cannot be negative")

    def customize_configuration(
        self,
        new_configuration: AgentConfiguration,
        customization_notes: str | None = None,
    ) -> None:
        """Customize the agent configuration.

        This method updates the instance's configuration and marks it as customized.
        The original template configuration remains unchanged.

        Args:
            new_configuration: The new customized configuration
            customization_notes: Optional notes about the customization

        Raises:
            ValueError: If new_configuration is invalid
        """
        if not isinstance(new_configuration, AgentConfiguration):
            raise ValueError("new_configuration must be an AgentConfiguration instance")

        # Update configuration
        object.__setattr__(self, "configuration", new_configuration)

        # Mark as customized
        object.__setattr__(self, "is_customized", True)

        # Update metadata with customization info
        if customization_notes:
            metadata_copy = self.metadata.copy()
            metadata_copy["last_customization"] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "notes": customization_notes,
            }
            object.__setattr__(self, "metadata", metadata_copy)

        logger.info(
            f"Customized agent instance {self.id} for user {self.user_id}. "
            f"Notes: {customization_notes or 'None'}"
        )

    def track_usage(self) -> None:
        """Track usage of this agent instance.

        Increments the usage count and updates the last_used_at timestamp.
        Called each time the agent is invoked via call_agent.
        """
        # Increment usage count
        object.__setattr__(self, "usage_count", self.usage_count + 1)

        # Update last used timestamp
        object.__setattr__(self, "last_used_at", datetime.now(UTC))

        logger.debug(
            f"Tracked usage for instance {self.id}: count={self.usage_count}, "
            f"last_used_at={self.last_used_at}"
        )

    def get_creator_display_name(self, creator_email: str | None = None) -> str:
        """Get the display name for the creator of this instance.

        Returns "System Default" for non-customized instances or instances
        without an original creator. Otherwise returns the creator's email.

        Args:
            creator_email: The email of the original creator (if imported)

        Returns:
            str: Display name for the creator

        Examples:
            # Non-customized instance
            instance.get_creator_display_name()  # Returns "System Default"

            # Customized but not imported
            instance.get_creator_display_name()  # Returns "System Default"

            # Imported from another user
            instance.get_creator_display_name("user@example.com")  # Returns "user@example.com"
        """
        # If instance was imported from another user, show their email
        if self.original_creator_id and creator_email:
            return creator_email

        # Default to "System Default" for non-imported instances
        return "System Default"

    def generate_share_token(self, token: str) -> None:
        """Generate a share token and make the instance public.

        Args:
            token: A 64-character secure random token

        Raises:
            ValueError: If token is invalid
        """
        if not token or len(token) != 64:
            raise ValueError("Share token must be exactly 64 characters")

        object.__setattr__(self, "share_token", token)
        object.__setattr__(self, "visibility", "public")

        logger.info(f"Generated share token for instance {self.id}")

    def revoke_share_token(self) -> None:
        """Revoke the share token and make the instance private."""
        object.__setattr__(self, "share_token", None)
        object.__setattr__(self, "visibility", "private")

        logger.info(f"Revoked share token for instance {self.id}")

    def is_public(self) -> bool:
        """Check if this instance is publicly shared.

        Returns:
            bool: True if instance is public and has a share token
        """
        return self.visibility == "public" and self.share_token is not None

    def is_imported(self) -> bool:
        """Check if this instance was imported from another user.

        Returns:
            bool: True if instance has an original_creator_id
        """
        return self.original_creator_id is not None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserAgentInstance:
        """Create UserAgentInstance from dictionary (e.g., from database).

        Args:
            data: Dictionary containing instance data

        Returns:
            UserAgentInstance instance
        """
        # Parse IDs
        instance_id = None
        if "id" in data and data["id"]:
            instance_id = (
                data["id"]
                if isinstance(data["id"], UserAgentInstanceId)
                else UserAgentInstanceId.from_string(str(data["id"]))
            )

        user_id = None
        if "user_id" in data and data["user_id"]:
            user_id = (
                data["user_id"]
                if isinstance(data["user_id"], UserId)
                else UserId.from_string(str(data["user_id"]))
            )

        template_id = None
        if "template_id" in data and data["template_id"]:
            template_id = (
                data["template_id"]
                if isinstance(data["template_id"], AgentTemplateId)
                else AgentTemplateId.from_string(str(data["template_id"]))
            )

        original_creator_id = None
        if "original_creator_id" in data and data["original_creator_id"]:
            original_creator_id = (
                data["original_creator_id"]
                if isinstance(data["original_creator_id"], UserId)
                else UserId.from_string(str(data["original_creator_id"]))
            )

        # Handle configuration
        config = data.get("configuration")
        if isinstance(config, dict):
            configuration = AgentConfiguration.from_dict(config)
        elif isinstance(config, AgentConfiguration):
            configuration = config
        else:
            raise ValueError("Invalid configuration format")

        # Parse timestamps
        last_used_at = None
        if "last_used_at" in data and data["last_used_at"]:
            if isinstance(data["last_used_at"], str):
                last_used_at = datetime.fromisoformat(data["last_used_at"])
            else:
                last_used_at = data["last_used_at"]

        created_at = None
        if "created_at" in data and data["created_at"]:
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            else:
                created_at = data["created_at"]

        updated_at = None
        if "updated_at" in data and data["updated_at"]:
            if isinstance(data["updated_at"], str):
                updated_at = datetime.fromisoformat(data["updated_at"])
            else:
                updated_at = data["updated_at"]

        return cls(
            id=instance_id,
            user_id=user_id,
            template_id=template_id,
            agent_name=data.get("agent_name", ""),
            is_customized=data.get("is_customized", False),
            is_enabled=data.get("is_enabled", True),
            configuration=configuration,
            visibility=data.get("visibility", "private"),
            share_token=data.get("share_token"),
            original_creator_id=original_creator_id,
            usage_count=data.get("usage_count", 0),
            last_used_at=last_used_at,
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert instance to dictionary for storage/serialization.

        Returns:
            Dictionary representation including all fields
        """
        return {
            "id": str(self.id) if self.id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "template_id": str(self.template_id) if self.template_id else None,
            "agent_name": self.agent_name,
            "is_customized": self.is_customized,
            "is_enabled": self.is_enabled,
            "configuration": self.configuration.to_dict() if self.configuration else {},
            "visibility": self.visibility,
            "share_token": self.share_token,
            "original_creator_id": str(self.original_creator_id)
            if self.original_creator_id
            else None,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat()
            if self.last_used_at
            else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation of the instance."""
        return (
            f"UserAgentInstance("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"agent_name='{self.agent_name}', "
            f"is_customized={self.is_customized}, "
            f"visibility='{self.visibility}')"
        )
