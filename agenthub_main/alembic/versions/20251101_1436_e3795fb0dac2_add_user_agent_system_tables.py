"""add_user_agent_system_tables

Revision ID: e3795fb0dac2
Revises: 0392de6e70d2
Create Date: 2025-11-01 14:36:02.201948

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3795fb0dac2"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user agent system tables for dynamic per-user agent instances"""

    # ============================================================================
    # Table 1: agent_templates
    # ============================================================================
    # Base table for immutable agent templates from agent-library
    op.create_table(
        "agent_templates",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("default_configuration", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("agent_templates_pkey")),
        sa.UniqueConstraint("slug", name=op.f("agent_templates_slug_key")),
    )

    # Indexes for agent_templates
    op.create_index(op.f("idx_agent_templates_slug"), "agent_templates", ["slug"])
    op.create_index(
        op.f("idx_agent_templates_category"), "agent_templates", ["category"]
    )

    # ============================================================================
    # Table 2: user_agent_instances
    # ============================================================================
    # Per-user agent instances with customization and sharing capabilities
    op.create_table(
        "user_agent_instances",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("template_id", postgresql.UUID(), nullable=False),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column(
            "is_customized", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column(
            "customizations", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        # Sharing fields
        sa.Column(
            "visibility", sa.String(20), nullable=False, server_default="private"
        ),
        sa.Column("share_token", sa.String(64), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("original_creator_id", postgresql.UUID(), nullable=True),
        sa.Column("imported_from_instance_id", postgresql.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("user_agent_instances_pkey")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("user_agent_instances_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["agent_templates.id"],
            name=op.f("user_agent_instances_template_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["original_creator_id"],
            ["users.id"],
            name=op.f("user_agent_instances_original_creator_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["imported_from_instance_id"],
            ["user_agent_instances.id"],
            name=op.f("user_agent_instances_imported_from_instance_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "user_id",
            "template_id",
            name=op.f("user_agent_instances_user_template_key"),
        ),
        sa.UniqueConstraint(
            "share_token", name=op.f("user_agent_instances_share_token_key")
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'public')", name="check_visibility_values"
        ),
    )

    # Indexes for user_agent_instances
    op.create_index(
        op.f("idx_user_agent_instances_user_template"),
        "user_agent_instances",
        ["user_id", "template_id"],
    )
    op.create_index(
        op.f("idx_user_agent_instances_user_id"), "user_agent_instances", ["user_id"]
    )
    op.create_index(
        op.f("idx_user_agent_instances_template_id"),
        "user_agent_instances",
        ["template_id"],
    )
    op.create_index(
        op.f("idx_user_agent_instances_share_token"),
        "user_agent_instances",
        ["share_token"],
        postgresql_where=sa.text("share_token IS NOT NULL"),
    )
    op.create_index(
        op.f("idx_user_agent_instances_public"),
        "user_agent_instances",
        ["user_id", "visibility"],
        postgresql_where=sa.text("visibility = 'public'"),
    )
    op.create_index(
        op.f("idx_user_agent_instances_creator"),
        "user_agent_instances",
        ["original_creator_id"],
        postgresql_where=sa.text("original_creator_id IS NOT NULL"),
    )

    # ============================================================================
    # Table 3: user_agent_configurations_md
    # ============================================================================
    # Markdown storage for frontend editing of agent configurations
    op.create_table(
        "user_agent_configurations_md",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("instance_id", postgresql.UUID(), nullable=False),
        sa.Column("configuration_type", sa.String(50), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("user_agent_configurations_md_pkey")),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["user_agent_instances.id"],
            name=op.f("user_agent_configurations_md_instance_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "instance_id",
            "configuration_type",
            name=op.f("user_agent_configurations_md_instance_type_key"),
        ),
    )

    # Indexes for user_agent_configurations_md
    op.create_index(
        op.f("idx_configurations_md_instance"),
        "user_agent_configurations_md",
        ["instance_id", "configuration_type"],
    )

    # ============================================================================
    # Table 4: agent_import_history
    # ============================================================================
    # Track agent import operations for analytics and auditing
    op.create_table(
        "agent_import_history",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("importer_user_id", postgresql.UUID(), nullable=False),
        sa.Column("source_instance_id", postgresql.UUID(), nullable=False),
        sa.Column("imported_instance_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("share_token", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("agent_import_history_pkey")),
        sa.ForeignKeyConstraint(
            ["importer_user_id"],
            ["users.id"],
            name=op.f("agent_import_history_importer_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_instance_id"],
            ["user_agent_instances.id"],
            name=op.f("agent_import_history_source_instance_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_instance_id"],
            ["user_agent_instances.id"],
            name=op.f("agent_import_history_imported_instance_id_fkey"),
            ondelete="CASCADE",
        ),
    )

    # Indexes for agent_import_history
    op.create_index(
        op.f("idx_import_history_importer"),
        "agent_import_history",
        ["importer_user_id"],
    )
    op.create_index(
        op.f("idx_import_history_source"),
        "agent_import_history",
        ["source_instance_id"],
    )
    op.create_index(
        op.f("idx_import_history_date"), "agent_import_history", ["imported_at"]
    )


def downgrade() -> None:
    """Drop all user agent system tables in reverse order"""

    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table("agent_import_history")
    op.drop_table("user_agent_configurations_md")
    op.drop_table("user_agent_instances")
    op.drop_table("agent_templates")
