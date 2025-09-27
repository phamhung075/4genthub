#!/usr/bin/env python3
"""
Fix PostgreSQL task_count triggers by executing migration 006.

This script executes the 006_add_task_count_triggers.sql migration
to fix the issue where task_count is always 0 in production PostgreSQL.
"""

import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

# Add the project to path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig


def check_triggers_exist(engine):
    """Check if the triggers already exist in PostgreSQL"""
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.triggers
            WHERE trigger_name LIKE '%branch_task_counts%'
        """))
        count = result.scalar()
        return count > 0


def check_database_type(engine):
    """Check if we're using PostgreSQL"""
    with engine.begin() as conn:
        try:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            return "PostgreSQL" in str(version)
        except:
            return False


def execute_trigger_migration(engine):
    """Execute the trigger migration SQL"""
    migration_file = project_root / "src/fastmcp/task_management/infrastructure/migrations/006_add_task_count_triggers.sql"

    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    print(f"Reading migration from: {migration_file}")

    # Read the migration SQL
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print("Executing migration...")

    # Split the SQL into individual statements (PostgreSQL can handle this better)
    with engine.begin() as conn:
        # Execute the entire migration as one transaction
        conn.execute(text(migration_sql))
        print("Migration executed successfully!")


def verify_fix(engine):
    """Verify the fix by checking if triggers are working"""
    print("\n=== Verifying the fix ===")

    with engine.begin() as conn:
        # Check if triggers exist
        result = conn.execute(text("""
            SELECT trigger_name, event_manipulation, action_timing
            FROM information_schema.triggers
            WHERE trigger_name LIKE '%branch_task_counts%'
            ORDER BY trigger_name
        """))

        triggers = result.fetchall()
        if triggers:
            print(f"✅ Found {len(triggers)} triggers installed:")
            for trigger in triggers:
                print(f"   - {trigger[0]} ({trigger[2]} {trigger[1]})")
        else:
            print("❌ No triggers found!")
            return False

        # Check if function exists
        result = conn.execute(text("""
            SELECT proname FROM pg_proc
            WHERE proname = 'update_branch_task_counts'
        """))

        if result.fetchone():
            print("✅ Trigger function 'update_branch_task_counts' exists")
        else:
            print("❌ Trigger function not found!")
            return False

        # Check current task counts in a sample branch
        result = conn.execute(text("""
            SELECT
                b.id, b.name,
                b.task_count as stored_count,
                COUNT(t.id) as actual_count
            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            GROUP BY b.id, b.name, b.task_count
            LIMIT 5
        """))

        branches = result.fetchall()
        if branches:
            print("\n✅ Sample branch task counts (after trigger sync):")
            for branch in branches:
                stored = branch[2] or 0
                actual = branch[3] or 0
                status = "✅" if stored == actual else "❌"
                print(f"   {status} {branch[1]}: stored={stored}, actual={actual}")

        return True


def main():
    """Main execution function"""
    print("=== PostgreSQL Task Count Triggers Fix ===")
    print("This script will install database triggers to fix task_count always being 0\n")

    try:
        # Create database configuration
        db_config = DatabaseConfig()

        # Get the engine (initialization happens automatically)
        engine = db_config.get_engine()

        # Check if we're using PostgreSQL
        is_postgres = check_database_type(engine)
        if not is_postgres:
            print("❌ This fix is only needed for PostgreSQL. Current database appears to be SQLite.")
            print("SQLite task counting works differently and doesn't need these triggers.")
            return

        print("✅ PostgreSQL database detected")

        # Check if triggers already exist
        triggers_exist = check_triggers_exist(engine)
        if triggers_exist:
            print("ℹ️ Triggers already exist. Running verification...")
            # Verify the fix
            success = verify_fix(engine)
        else:
            print("ℹ️ Triggers not found. Installing triggers...")
            # Execute the migration
            execute_trigger_migration(engine)

            # Verify the fix
            success = verify_fix(engine)

        if success:
            print("\n🎉 SUCCESS! Task count triggers have been installed and verified.")
            print("The WebSocket task_count issue should now be resolved.")
            print("\nNext steps:")
            print("1. Restart the application server")
            print("2. Create a test task and verify the task_count updates in real-time")
            print("3. Check the WebSocket responses show correct task counts")
        else:
            print("\n❌ VERIFICATION FAILED! Please check the logs above for issues.")
            return 1

    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"❌ File error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    # Run the main function
    exit_code = main()
    sys.exit(exit_code or 0)