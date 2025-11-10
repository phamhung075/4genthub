"""
SQLAlchemy ORM models for agent_management module.

This module defines the database schema for:
- agent_templates: Global agent template definitions
- user_agent_instances: Per-user agent instances with customizations
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fastmcp.task_management.infrastructure.database.database_config import Base
from fastmcp.task_management.infrastructure.database.timestamp_events import (
    setup_timestamp_events,
)
from fastmcp.task_management.infrastructure.database.uuid_column_type import UnifiedUUID


class AgentTemplateORM(Base):
    """
    ORM model for agent_templates table.

    Represents global agent template definitions loaded from agent-library.
    These are shared across all users and provide the base configuration.

    Table: agent_templates
    Primary Key: id (UUID)
    Unique Constraints: slug (for lookups like "coding-agent")
    Indexes: category, version for filtering
    """

    __tablename__ = "agent_templates"

    # Primary key
    id: Mapped[str] = mapped_column(
        UnifiedUUID,
        primary_key=True,
        doc="UUID identifier for the template"
    )

    # Core identification fields
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-friendly identifier (e.g., 'coding-agent', 'debugger-agent')"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Human-readable name (e.g., 'Coding Agent')"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Description of agent's purpose and capabilities"
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Category (e.g., 'development', 'testing', 'security')"
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Version string (e.g., '1.0.0')"
    )

    # Configuration (JSON fields)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Complete system prompt/instructions for the agent"
    )

    tools: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="JSON array of tool names the agent can use"
    )

    capabilities: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="JSON object describing agent capabilities"
    )

    rules: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of rules and constraints"
    )

    output_format: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="JSON object for output formatting preferences"
    )

    metadata_json: Mapped[str | None] = mapped_column(
        "metadata",  # Column name in DB
        Text,
        nullable=True,
        doc="JSON object for additional metadata (includes source info)"
    )

    # Timestamps (managed automatically)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Last update timestamp"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_agent_templates_category_version", "category", "version"),
    )


class UserAgentInstanceORM(Base):
    """
    ORM model for user_agent_instances table.

    Represents per-user instances of agent templates with customizations.
    Each user gets their own instances that can be customized independently.

    Table: user_agent_instances
    Primary Key: id (UUID)
    Unique Constraints: (user_id, template_id) - one instance per template per user
    Indexes: user_id, template_id, share_token, visibility for queries
    """

    __tablename__ = "user_agent_instances"

    # Primary key
    id: Mapped[str] = mapped_column(
        UnifiedUUID,
        primary_key=True,
        doc="UUID identifier for the instance"
    )

    # Ownership
    user_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        index=True,
        doc="UUID of the user who owns this instance"
    )

    # Template relationship
    template_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        index=True,
        doc="UUID of the agent template this instance is based on"
    )

    # Instance naming
    agent_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="User-visible name for this instance"
    )

    # Customization tracking
    is_customized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether user has customized the configuration"
    )

    # Agent selection/activation
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether this agent instance is enabled for use in call_agent tools"
    )

    customization_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="User notes about customizations made"
    )

    # Configuration (JSON fields)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="System prompt (may be customized from template)"
    )

    tools: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="JSON array of tool names"
    )

    capabilities: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="JSON object of capabilities"
    )

    rules: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of rules"
    )

    output_format: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="JSON object for output format"
    )

    metadata_json: Mapped[str | None] = mapped_column(
        "metadata",  # Column name in DB
        Text,
        nullable=True,
        doc="JSON object for metadata"
    )

    # Sharing
    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="private",
        index=True,
        doc="Visibility: 'private' or 'public'"
    )

    share_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
        doc="Unique token for sharing (64 characters)"
    )

    share_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the share token was generated"
    )

    # Import tracking
    original_creator_id: Mapped[str | None] = mapped_column(
        UnifiedUUID,
        nullable=True,
        doc="User ID of the original creator if this was imported"
    )

    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this instance was imported"
    )

    # Timestamps (managed automatically)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Last update timestamp"
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time this agent instance was used"
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of times this agent has been used"
    )

    # Constraints and indexes
    __table_args__ = (
        # UNIQUE constraint: one instance per template per user
        UniqueConstraint(
            "user_id",
            "template_id",
            name="uq_user_agent_instances_user_template"
        ),
        # Composite index for user queries
        Index("ix_user_agent_instances_user_visibility", "user_id", "visibility"),
        # Index for public instance queries
        Index("ix_user_agent_instances_visibility_created", "visibility", "created_at"),
        # Index for enabled instance queries (call_agent filtering)
        Index("ix_user_agent_instances_user_enabled", "user_id", "is_enabled"),
    )


class AgentImportHistoryORM(Base):
    """
    ORM model for agent_import_history table.

    Tracks when users import public agents from marketplace.
    Records importer, source instance, and imported instance for analytics.

    Table: agent_import_history
    Primary Key: id (UUID)
    Foreign Keys: importer_user_id (for cascade delete when user removed)
    Indexes: importer_user_id, source_instance_id, imported_at for analytics queries
    """

    __tablename__ = "agent_import_history"

    # Primary key
    id: Mapped[str] = mapped_column(
        UnifiedUUID,
        primary_key=True,
        doc="UUID identifier for the import record"
    )

    # User who imported the agent
    importer_user_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        index=True,
        doc="User who performed the import"
    )

    # Source agent instance (the shared agent being imported)
    source_instance_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        index=True,
        doc="Original agent instance that was shared"
    )

    # Imported agent instance (the copy created for importer)
    imported_instance_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        doc="New agent instance created for the importer"
    )

    # Timestamp of import
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the agent was imported"
    )

    # Share token used for import
    share_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Share token that was used for the import"
    )

    # Constraints and indexes
    __table_args__ = (
        # Index for date-based analytics
        Index("idx_import_history_date", "imported_at"),
    )


class UserAgentConfigurationMdORM(Base):
    """
    ORM model for user_agent_configurations_md table.

    Stores markdown-formatted configuration documentation for agent instances.
    Allows users to document their agent customizations in different categories.

    Table: user_agent_configurations_md
    Primary Key: id (UUID)
    Unique Constraint: (instance_id, configuration_type) - one of each type per instance
    Indexes: (instance_id, configuration_type) for quick lookups
    """

    __tablename__ = "user_agent_configurations_md"

    # Primary key
    id: Mapped[str] = mapped_column(
        UnifiedUUID,
        primary_key=True,
        doc="UUID identifier for the configuration"
    )

    # Agent instance this configuration belongs to
    instance_id: Mapped[str] = mapped_column(
        UnifiedUUID,
        nullable=False,
        doc="Agent instance this configuration documents"
    )

    # Configuration type (e.g., 'usage', 'customization', 'examples')
    configuration_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of configuration documentation"
    )

    # Markdown content
    content_markdown: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Markdown-formatted documentation content"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Last update timestamp"
    )

    # Constraints and indexes
    __table_args__ = (
        # UNIQUE constraint: one of each configuration type per instance
        UniqueConstraint(
            "instance_id",
            "configuration_type",
            name="user_agent_configurations_md_instance_type_key"
        ),
        # Composite index for lookups
        Index("idx_configurations_md_instance", "instance_id", "configuration_type"),
    )


# Setup automatic timestamp management (global setup for all models)
setup_timestamp_events()
