#!/usr/bin/env python3
"""
Migration: Add progress_history and progress_count to Subtask model

This migration adds detailed progress tracking fields to subtasks,
matching the functionality already present in the Task model.

Created: 2025-10-31
"""

from sqlalchemy.orm import Session
from sqlalchemy import text


def upgrade(session: Session):
    """Add progress_history and progress_count columns to subtasks table."""

    # Add progress_history column (JSON type for progress entries)
    session.execute(text("""
        ALTER TABLE subtasks
        ADD COLUMN IF NOT EXISTS progress_history JSON DEFAULT '{}'::json NOT NULL
    """))

    # Add progress_count column (integer for tracking number of progress entries)
    session.execute(text("""
        ALTER TABLE subtasks
        ADD COLUMN IF NOT EXISTS progress_count INTEGER DEFAULT 0 NOT NULL
    """))

    session.commit()
    print("✅ Added progress_history and progress_count columns to subtasks table")


def downgrade(session: Session):
    """Remove progress_history and progress_count columns from subtasks table."""

    # Drop columns in reverse order
    session.execute(text("ALTER TABLE subtasks DROP COLUMN IF EXISTS progress_count"))
    session.execute(text("ALTER TABLE subtasks DROP COLUMN IF EXISTS progress_history"))

    session.commit()
    print("✅ Removed progress_history and progress_count columns from subtasks table")


if __name__ == "__main__":
    # This is just a migration file - run it through your migration system
    print("Migration file for adding progress tracking to subtasks table")
