#!/usr/bin/env python
"""Test that database initialization fix works"""

import sys
import os
from pathlib import Path

# Load environment from .env.dev
project_root = Path(__file__).parent.parent.parent.parent
env_dev_path = project_root / ".env.dev"

if env_dev_path.exists():
    from dotenv import load_dotenv
    print(f"📄 Loading environment from: {env_dev_path}")
    load_dotenv(env_dev_path, override=True)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_database_initialization():
    """Test that SessionLocal is properly initialized"""
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig, get_db_config

    try:
        print("\n" + "="*60)
        print("Testing Database Initialization Fix")
        print("="*60)

        # Reset singleton to force re-initialization
        DatabaseConfig.reset_instance()

        # Initialize database
        print("\n🔄 Initializing database configuration...")
        db_config = get_db_config()

        # Check that SessionLocal is initialized
        assert hasattr(db_config, 'SessionLocal'), "SessionLocal attribute missing"
        assert db_config.SessionLocal is not None, "SessionLocal is None"
        print("✅ SessionLocal is properly initialized")

        # Check that engine is initialized
        assert hasattr(db_config, 'engine'), "engine attribute missing"
        assert db_config.engine is not None, "engine is None"
        print("✅ Engine is properly initialized")

        # Try to get a session
        print("\n🔄 Testing session creation...")
        session = db_config.get_session()
        assert session is not None, "Failed to create session"
        print("✅ Session created successfully")

        # Test a query
        from sqlalchemy import text
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1, "Query failed"
        print("✅ Query executed successfully")

        session.close()

        print("\n✅ Database initialization VERIFIED!")
        return True

    except Exception as e:
        print(f"\n❌ Database initialization test FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_initialization()
    sys.exit(0 if success else 1)