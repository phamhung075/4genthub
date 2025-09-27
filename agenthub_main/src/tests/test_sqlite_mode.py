#!/usr/bin/env python
"""Test SQLite mode for test execution"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment to use SQLite
os.environ['DATABASE_TYPE'] = 'sqlite'
os.environ['PYTEST_CURRENT_TEST'] = 'test_sqlite_mode'

def test_sqlite_configuration():
    """Test that SQLite can be used in test mode"""
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

    try:
        print("\n" + "="*60)
        print("Testing SQLite Configuration for Tests")
        print("="*60)

        # Initialize database with SQLite
        db = DatabaseConfig()

        assert db.database_type == "sqlite", f"Expected sqlite, got {db.database_type}"
        print(f"✅ Database type: {db.database_type}")

        # Get database URL
        db_url = db._get_database_url()
        assert db_url.startswith("sqlite:///"), f"Expected SQLite URL, got {db_url}"
        print(f"✅ Database URL: {db_url}")

        # Test session creation
        session = db.get_session()
        assert session is not None, "Failed to create session"
        print("✅ SQLite session created successfully")

        # Test simple query
        from sqlalchemy import text
        result = session.execute(text("SELECT sqlite_version()"))
        version = result.scalar()
        print(f"✅ SQLite version: {version}")

        session.close()

        print("\n✅ SQLite test mode configuration SUCCESSFUL!")
        return True

    except Exception as e:
        print(f"\n❌ SQLite test mode configuration FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sqlite_configuration()
    sys.exit(0 if success else 1)