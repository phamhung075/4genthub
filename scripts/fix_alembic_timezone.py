#!/usr/bin/env python3
"""
Fix alembic_version.applied_at column timezone issue.

This script alters the applied_at column from 'timestamp without time zone'
to 'timestamp with time zone' to match timezone-aware datetime objects.
"""

from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

from fastmcp.config import get_settings

def fix_timezone_column():
    """Alter applied_at column to support timezone-aware datetimes."""
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)

        print("🔧 Fixing alembic_version.applied_at column type...")

        with engine.connect() as conn:
            # Alter column type
            conn.execute(text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN applied_at TYPE timestamp with time zone"
            ))
            conn.commit()

        print("✅ Column type updated successfully!")
        print("   alembic_version.applied_at is now 'timestamp with time zone'")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_timezone_column()
    sys.exit(0 if success else 1)
