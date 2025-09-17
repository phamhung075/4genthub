#!/usr/bin/env python3
"""
Migration: Add user_id field to project_contexts table

This migration adds a user_id field to the project_contexts table
to support user isolation and multi-tenancy.
"""

from sqlalchemy import Column, String, text
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

def upgrade(session: Session):
    """Add user_id column to project_contexts table."""
    # Add the column as nullable first
    session.execute(text("""
        ALTER TABLE project_contexts 
        ADD COLUMN IF NOT EXISTS user_id VARCHAR
    """))
    session.commit()

def downgrade(session: Session):
    """Remove user_id column from project_contexts table."""
    session.execute(text("ALTER TABLE project_contexts DROP COLUMN IF EXISTS user_id"))
    session.commit()

if __name__ == "__main__":
    # This is just a migration file - run it through your migration system
    print("Migration file for adding user_id to project_contexts table")