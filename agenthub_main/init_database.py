#!/usr/bin/env python3
"""
Database Initialization Script

This script replaces the complex migration system with a simple approach:
- Drops all existing tables
- Recreates the database schema using single comprehensive SQL files
- Supports both PostgreSQL and SQLite databases

Usage:
    python init_database.py [--database-type postgresql|sqlite] [--confirm]

Examples:
    python init_database.py --database-type sqlite --confirm
    python init_database.py --database-type postgresql --confirm
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from typing import Union

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from fastmcp.core.config import get_db_config
    from fastmcp.task_management.infrastructure.database.database import Database
except ImportError as e:
    print(f"Error importing database modules: {e}")
    print("Make sure you're running this from the agenthub_main directory")
    sys.exit(1)


def read_sql_file(file_path: Path) -> str:
    """Read SQL file content."""
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def init_sqlite_database(db_path: str, sql_file: Path) -> bool:
    """Initialize SQLite database with complete schema."""
    try:
        # Remove existing database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ Removed existing SQLite database: {db_path}")

        # Read SQL schema
        sql_content = read_sql_file(sql_file)

        # Create new database and execute schema
        conn = sqlite3.connect(db_path)
        conn.executescript(sql_content)
        conn.close()

        print(f"✅ SQLite database initialized: {db_path}")
        return True

    except Exception as e:
        print(f"❌ Error initializing SQLite database: {e}")
        return False


def init_postgresql_database(connection_params: dict, sql_file: Path) -> bool:
    """Initialize PostgreSQL database with complete schema."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Read SQL schema
        sql_content = read_sql_file(sql_file)

        # Connect and drop/recreate schema
        conn = psycopg2.connect(**connection_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Drop all tables (cascade will handle dependencies)
        cursor.execute("""
            DROP SCHEMA IF EXISTS public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
        """)

        # Execute schema creation
        cursor.execute(sql_content)

        cursor.close()
        conn.close()

        print("✅ PostgreSQL database schema initialized")
        return True

    except ImportError:
        print("❌ Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error initializing PostgreSQL database: {e}")
        return False


def get_database_config():
    """Get database configuration from environment."""
    try:
        config = get_db_config()
        return config
    except Exception as e:
        print(f"❌ Error getting database config: {e}")
        return None


def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(description="Initialize database with complete schema")
    parser.add_argument(
        "--database-type",
        choices=["postgresql", "sqlite"],
        help="Database type to initialize (auto-detected if not specified)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm database initialization (required to prevent accidental runs)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force initialization without confirmation prompts"
    )

    args = parser.parse_args()

    # Safety check - require confirmation
    if not args.confirm and not args.force:
        print("⚠️  WARNING: This will DROP ALL existing database tables!")
        print("⚠️  Add --confirm flag to proceed with initialization")
        sys.exit(1)

    # Get project root and SQL files
    project_root = Path(__file__).parent
    sql_dir = project_root / "src" / "fastmcp" / "task_management" / "infrastructure" / "database"

    postgresql_sql = sql_dir / "init_schema_postgresql.sql"
    sqlite_sql = sql_dir / "init_schema_sqlite.sql"

    # Verify SQL files exist
    if not postgresql_sql.exists():
        print(f"❌ PostgreSQL SQL file not found: {postgresql_sql}")
        sys.exit(1)

    if not sqlite_sql.exists():
        print(f"❌ SQLite SQL file not found: {sqlite_sql}")
        sys.exit(1)

    # Get database configuration
    config = get_database_config()
    if not config:
        print("❌ Failed to load database configuration")
        sys.exit(1)

    # Determine database type
    db_type = args.database_type
    if not db_type:
        # Auto-detect from config
        db_url = config.get('DATABASE_URL', '')
        if 'postgresql' in db_url or 'postgres' in db_url:
            db_type = "postgresql"
        elif 'sqlite' in db_url or db_url.endswith('.db'):
            db_type = "sqlite"
        else:
            print("❌ Could not auto-detect database type. Please specify --database-type")
            sys.exit(1)

    print(f"🗄️  Initializing {db_type.upper()} database...")

    # Initialize based on database type
    if db_type == "sqlite":
        db_path = config.get('DATABASE_URL', '').replace('sqlite:///', '')
        if not db_path:
            print("❌ SQLite database path not found in configuration")
            sys.exit(1)

        success = init_sqlite_database(db_path, sqlite_sql)

    elif db_type == "postgresql":
        # Parse PostgreSQL connection parameters
        db_url = config.get('DATABASE_URL', '')
        if not db_url.startswith('postgresql'):
            print("❌ PostgreSQL connection URL not found in configuration")
            sys.exit(1)

        # Extract connection parameters
        # Example: postgresql://user:password@localhost:5432/dbname
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)

        connection_params = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') or 'agenthub',
            'user': parsed.username,
            'password': parsed.password
        }

        success = init_postgresql_database(connection_params, postgresql_sql)

    if success:
        print(f"🎉 Database initialization completed successfully!")
        print(f"📝 Schema loaded from: {sqlite_sql if db_type == 'sqlite' else postgresql_sql}")
        print(f"✨ You can now start the application with a clean database")
    else:
        print(f"❌ Database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()