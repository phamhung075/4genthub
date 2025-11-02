#!/usr/bin/env python3
"""
Migration: Add is_enabled field to user_agent_instances table

This migration adds an is_enabled boolean field to the user_agent_instances table
to support selective agent activation. Users can enable/disable specific agents
to control which ones appear in call_agent tools.

Date: 2025-11-02
Feature: Agent Enable/Disable Selection
"""

from sqlalchemy.orm import Session

def upgrade(session: Session):
    """Add is_enabled column to user_agent_instances table."""
    # Add the column with default value of TRUE (all existing agents remain enabled)
    session.execute("""
        ALTER TABLE user_agent_instances
        ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE
    """)

    # Add index for efficient querying of enabled agents
    session.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_agent_instances_user_enabled
        ON user_agent_instances(user_id, is_enabled)
    """)

    session.commit()
    print("✅ Added is_enabled column to user_agent_instances table with default TRUE")
    print("✅ Added index ix_user_agent_instances_user_enabled for efficient queries")

def downgrade(session: Session):
    """Remove is_enabled column from user_agent_instances table."""
    # Drop index first
    session.execute("DROP INDEX IF EXISTS ix_user_agent_instances_user_enabled")

    # Drop column
    session.execute("ALTER TABLE user_agent_instances DROP COLUMN IF EXISTS is_enabled")

    session.commit()
    print("✅ Removed is_enabled column and index from user_agent_instances table")

if __name__ == "__main__":
    # This is just a migration file - run it through your migration system
    print("Migration file for adding is_enabled to user_agent_instances table")
    print("Run via: python -m fastmcp.task_management.infrastructure.database.migration_runner")
