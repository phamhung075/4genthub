#!/usr/bin/env python3
"""
Migration: Add progress_percentage field to Task model

This migration adds a progress_percentage field to the Task model
to support automatic progress aggregation from subtasks.
"""

from sqlalchemy import Column, Integer
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

def upgrade(session: Session):
    """Add progress_percentage column to tasks table."""
    # Add the column with a default value of 0
    session.execute("""
        ALTER TABLE tasks 
        ADD COLUMN IF NOT EXISTS progress_percentage INTEGER DEFAULT 0
        CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
    """)
    session.commit()

def downgrade(session: Session):
    """Remove progress_percentage column from tasks table."""
    session.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS progress_percentage")
    session.commit()

if __name__ == "__main__":
    # This is just a migration file - run it through your migration system
    print("Migration file for adding progress_percentage to tasks table")