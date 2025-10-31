#!/usr/bin/env python3
"""
Runner script for subtask progress tracking migration

Executes the migration to add progress_history and progress_count columns to subtasks table.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastmcp.task_management.infrastructure.database.migrations import add_subtask_progress_tracking as migration


def get_database_url():
    """Get database URL from environment or use default."""
    import os
    from dotenv import load_dotenv

    # Load .env.dev file
    env_path = project_root / ".env.dev"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")

    # Get database connection details
    db_type = os.getenv("DATABASE_TYPE", "postgresql")
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "agenthub")
    db_user = os.getenv("DATABASE_USER", "agenthub_user")
    db_password = os.getenv("DATABASE_PASSWORD", "")

    if db_type == "postgresql":
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    return url


def run_migration():
    """Execute the migration."""
    try:
        print("🚀 Starting subtask progress tracking migration...")
        print("")

        # Get database URL
        database_url = get_database_url()
        print(f"📊 Connecting to database...")

        # Create engine and session
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Run upgrade
        print("⬆️  Running upgrade...")
        migration.upgrade(session)

        session.close()
        print("")
        print("✅ Migration completed successfully!")
        print("")
        print("Next steps:")
        print("  1. Restart backend to apply changes")
        print("  2. Test subtask progress tracking via API")

        return 0

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def run_rollback():
    """Rollback the migration."""
    try:
        print("🔄 Rolling back subtask progress tracking migration...")
        print("")

        # Get database URL
        database_url = get_database_url()
        print(f"📊 Connecting to database...")

        # Create engine and session
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Run downgrade
        print("⬇️  Running downgrade...")
        migration.downgrade(session)

        session.close()
        print("")
        print("✅ Rollback completed successfully!")

        return 0

    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run subtask progress tracking migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration instead of applying it"
    )

    args = parser.parse_args()

    if args.rollback:
        exit_code = run_rollback()
    else:
        exit_code = run_migration()

    sys.exit(exit_code)
