#!/usr/bin/env python3
"""
Add usage_stats column to api_tokens table
"""
import os
import sys
from sqlalchemy import create_engine, text, JSON

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config

def add_usage_stats_column():
    """Add usage_stats JSON column to api_tokens table if it doesn't exist."""

    db_config = get_db_config()
    engine = db_config.engine

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'api_tokens'
            AND column_name = 'usage_stats'
        """))

        if result.fetchone() is None:
            print("❌ Column 'usage_stats' not found. Adding it now...")

            # Add the column
            conn.execute(text("""
                ALTER TABLE api_tokens
                ADD COLUMN usage_stats JSONB DEFAULT '{}'::jsonb NOT NULL
            """))
            conn.commit()

            print("✅ Successfully added 'usage_stats' column to api_tokens table")
        else:
            print("✅ Column 'usage_stats' already exists")

        # Verify the column was added
        result = conn.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'api_tokens'
            AND column_name IN ('usage_count', 'usage_stats', 'rate_limit')
            ORDER BY column_name
        """))

        print("\n📊 Current usage-related columns in api_tokens table:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} (default: {row[2]})")

if __name__ == "__main__":
    try:
        add_usage_stats_column()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
