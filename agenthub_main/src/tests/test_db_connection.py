#!/usr/bin/env python
"""Test PostgreSQL Database Connection"""

import sys
import os
from pathlib import Path

# Load environment variables from .env.dev
try:
    from dotenv import load_dotenv
    # Get project root (go up from tests directory)
    project_root = Path(__file__).parent.parent.parent.parent
    env_dev_path = project_root / ".env.dev"
    env_path = project_root / ".env"

    # Try loading .env.dev first, then .env
    if env_dev_path.exists():
        print(f"📄 Loading environment from: {env_dev_path}")
        load_dotenv(env_dev_path, override=True)
    elif env_path.exists():
        print(f"📄 Loading environment from: {env_path}")
        load_dotenv(env_path, override=True)
    else:
        print("⚠️ No .env or .env.dev file found, using system environment")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

def test_connection():
    """Test the database connection"""
    try:
        print("=" * 60)
        print("Testing PostgreSQL Database Connection")
        print("=" * 60)

        print("\n📋 Configuration loaded from environment:")
        print(f"  DATABASE_TYPE: {os.getenv('DATABASE_TYPE', 'NOT SET')}")
        print(f"  DATABASE_HOST: {os.getenv('DATABASE_HOST', 'NOT SET')}")
        print(f"  DATABASE_PORT: {os.getenv('DATABASE_PORT', 'NOT SET')}")
        print(f"  DATABASE_NAME: {os.getenv('DATABASE_NAME', 'NOT SET')}")
        print(f"  DATABASE_USER: {os.getenv('DATABASE_USER', 'NOT SET')}")
        print(f"  DATABASE_PASSWORD: {'SET' if os.getenv('DATABASE_PASSWORD') else 'NOT SET'}")
        print(f"  ENV: {os.getenv('ENV', 'NOT SET')}")

        # Check if we have minimal configuration
        if not os.getenv('DATABASE_HOST'):
            print("\n⚠️ DATABASE_HOST not set in environment!")
            print("Please ensure .env or .env.dev file exists and contains database configuration")
            return False

        print("\n🔄 Initializing database configuration...")
        db = DatabaseConfig()

        print(f"✅ Database type: {db.database_type}")
        print(f"✅ Database URL configured: Yes" if db.database_url else "❌ Database URL configured: No")

        print("\n🔄 Testing actual connection...")
        session = db.get_session()

        # Execute a simple query to verify connection
        from sqlalchemy import text
        result = session.execute(text("SELECT version()"))
        version = result.scalar()

        print(f"✅ Successfully connected to PostgreSQL!")
        print(f"📊 Database version: {version}")

        # Check if tables exist
        result = session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        print(f"\n📋 Existing tables in database:")
        if tables:
            for table in tables:
                print(f"  - {table}")
        else:
            print("  (No tables found - database is empty)")

        session.close()

        print("\n✅ Database connection test SUCCESSFUL!")
        return True

    except Exception as e:
        print(f"\n❌ Database connection test FAILED!")
        print(f"Error: {e}")

        import traceback
        print("\nDetailed error:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)