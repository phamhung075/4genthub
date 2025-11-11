#!/usr/bin/env python3
"""
Database Reset Script - Clean Start
====================================

This script drops all tables and recreates them fresh from ORM models.
Perfect for development when you want a clean slate.

Usage:
    python scripts/reset_database.py

What it does:
    1. Drops all existing tables in the database
    2. Recreates tables from SQLAlchemy ORM models (source of truth)
    3. Ensures database schema matches ORM models exactly

Safety:
    - Use only in development
    - All data will be lost
    - Requires confirmation before proceeding
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from sqlalchemy import text

from fastmcp.task_management.infrastructure.database.database_config import (
    Base,
    get_db_config,
)


def reset_database():
    """Drop all tables and recreate from ORM models."""

    print("=" * 60)
    print("DATABASE RESET - Clean Start")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("📋 Actions:")
    print("   1. Drop all existing tables")
    print("   2. Recreate tables from ORM models")
    print()

    # Get user confirmation
    response = input("Type 'RESET' to confirm: ")
    if response != "RESET":
        print("❌ Cancelled - no changes made")
        return

    print()
    print("🔄 Starting database reset...")

    try:
        # Get database configuration
        db_config = get_db_config()
        engine = db_config.engine

        print(f"📊 Database: {db_config.config.database_name}")
        print(f"🔧 Type: {db_config.config.database_type}")
        print()

        # Drop all tables
        print("🗑️  Step 1: Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully")
        print()

        # Recreate all tables from ORM models
        print("🏗️  Step 2: Creating tables from ORM models...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        print()

        # Verify tables were created
        with engine.connect() as conn:
            if db_config.config.database_type == "postgresql":
                result = conn.execute(
                    text("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
                )
            else:  # SQLite
                result = conn.execute(
                    text("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name
                """)
                )

            tables = [row[0] for row in result]

        print("📋 Created tables:")
        for table in tables:
            print(f"   ✓ {table}")
        print()

        print("=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        print()
        print("📝 Summary:")
        print("   • Tables dropped: All existing tables")
        print(f"   • Tables created: {len(tables)} tables")
        print("   • Status: Fresh database ready to use")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR DURING RESET")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    reset_database()
