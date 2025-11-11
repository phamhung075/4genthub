#!/usr/bin/env python3
"""
Create missing database tables using SQLAlchemy ORM models
"""

import os
import sys
from pathlib import Path

# Set up environment for PostgreSQL
os.environ["DATABASE_TYPE"] = "postgresql"
os.environ["DATABASE_URL"] = (
    "postgresql://agenthub_user:agenthub_password@localhost:5432/agenthub"
)

# Add the project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agenthub_main.src.fastmcp.task_management.infrastructure.database.database_config import (
    get_db_config,
)
from agenthub_main.src.fastmcp.task_management.infrastructure.database.models import *
from sqlalchemy import text


def create_missing_tables():
    """Create missing database tables"""
    print("🔧 Creating missing database tables...")

    try:
        # Get database configuration
        db = get_db_config()
        print("✅ Database connection established")

        # Get the metadata from Base
        from agenthub_main.src.fastmcp.task_management.infrastructure.database.database_config import (
            Base,
        )

        # Check which tables exist
        with db.get_session() as session:
            # List existing tables
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            existing_tables = {row[0] for row in result.fetchall()}
            print(f"📋 Existing tables: {sorted(existing_tables)}")

            # Tables that should exist based on our models
            expected_tables = {
                "projects",
                "project_git_branchs",
                "tasks",
                "task_subtasks",
                "task_assignees",
                "task_dependencies",
                "task_labels",
                "agents",
                "labels",
                "templates",
                "rules",
                "global_contexts",
                "project_contexts",
                "branch_contexts",
                "task_contexts",
                "context_inheritance_cache",
                "project_task_trees",
            }

            missing_tables = expected_tables - existing_tables
            print(f"❌ Missing tables: {sorted(missing_tables)}")

        # Create all tables using SQLAlchemy metadata
        print("🏗️  Creating all tables from ORM models...")
        Base.metadata.create_all(db.engine)
        print("✅ Tables created successfully!")

        # Verify tables were created
        with db.get_session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            final_tables = {row[0] for row in result.fetchall()}
            print(f"📋 Final table count: {len(final_tables)}")

            newly_created = final_tables - existing_tables
            if newly_created:
                print(f"✅ Newly created tables: {sorted(newly_created)}")
            else:
                print("ℹ️  No new tables were created (may already exist)")

        return True

    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Database Schema Creation Tool")
    print("=" * 50)

    success = create_missing_tables()

    if success:
        print("\n🎉 SUCCESS: All database tables are now available!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Could not create all required tables")
        sys.exit(1)
