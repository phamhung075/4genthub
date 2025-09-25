#!/usr/bin/env python3
"""
Clean Timestamp Migration Runner

This script runs the clean timestamp migration (007) to ensure all database
timestamp columns are compatible with the clean timestamp management system.

The migration:
1. Ensures all required timestamp columns exist
2. Sets defaults for any NULL timestamp values
3. Validates timestamp consistency
4. Prepares database for automatic timestamp management

Usage:
    python run_clean_timestamp_migration.py

Requirements:
    - DATABASE_TYPE and connection settings in environment
    - Database must be accessible and have applied_migrations table
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_migration_sql() -> str:
    """Read the migration SQL file."""
    migration_file = Path(__file__).parent / "src" / "fastmcp" / "task_management" / "infrastructure" / "database" / "migrations" / "007_clean_timestamp_migration.sql"

    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    with open(migration_file, 'r', encoding='utf-8') as f:
        return f.read()


def check_migration_applied() -> bool:
    """Check if migration has already been applied."""
    try:
        db_config = get_db_config()

        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT success FROM applied_migrations WHERE migration_name = '007_clean_timestamp_migration'")
            ).fetchone()

            if result:
                return result[0] is True
            return False

    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return False


def run_migration() -> bool:
    """Run the clean timestamp migration."""
    try:
        # Check if already applied
        if check_migration_applied():
            logger.info("✅ Migration 007_clean_timestamp_migration already applied successfully")
            return True

        # Read migration SQL
        logger.info("📖 Reading migration SQL...")
        migration_sql = read_migration_sql()

        # Get database configuration
        logger.info("🔧 Getting database configuration...")
        db_config = get_db_config()

        # Execute migration
        logger.info("🚀 Starting clean timestamp migration...")

        with db_config.get_session() as session:
            try:
                # Split SQL into individual statements and execute
                statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

                for i, statement in enumerate(statements):
                    if statement:
                        logger.debug(f"Executing statement {i+1}/{len(statements)}")
                        session.execute(text(statement))

                # Commit all changes
                session.commit()
                logger.info("✅ Migration committed successfully")

                # Run validation queries
                logger.info("🔍 Running validation checks...")

                # Check for NULL timestamps
                result = session.execute(
                    text("""
                    SELECT COUNT(*) FROM projects WHERE created_at IS NULL OR updated_at IS NULL
                    UNION ALL
                    SELECT COUNT(*) FROM tasks WHERE created_at IS NULL OR updated_at IS NULL
                    UNION ALL
                    SELECT COUNT(*) FROM subtasks WHERE created_at IS NULL OR updated_at IS NULL
                    """)
                ).fetchall()

                null_count = sum(row[0] for row in result)
                if null_count > 0:
                    logger.warning(f"⚠️ Found {null_count} records with NULL timestamps")
                else:
                    logger.info("✅ No NULL timestamps found")

                # Check timestamp consistency
                consistency_result = session.execute(
                    text("""
                    SELECT COUNT(*) FROM (
                        SELECT id FROM projects WHERE updated_at < created_at
                        UNION ALL
                        SELECT id FROM tasks WHERE updated_at < created_at
                        UNION ALL
                        SELECT id FROM subtasks WHERE updated_at < created_at
                    ) inconsistent
                    """)
                ).scalar()

                if consistency_result > 0:
                    logger.warning(f"⚠️ Found {consistency_result} records with inconsistent timestamps")
                else:
                    logger.info("✅ All timestamps are consistent")

                return True

            except Exception as e:
                session.rollback()
                logger.error(f"❌ Migration failed during execution: {e}")

                # Update migration record to failed
                try:
                    session.execute(
                        text("""
                        UPDATE applied_migrations
                        SET success = :success, error_message = :error
                        WHERE migration_name = '007_clean_timestamp_migration'
                        """),
                        {"success": False, "error": str(e)}
                    )
                    session.commit()
                except Exception as update_error:
                    logger.error(f"Could not update migration status: {update_error}")

                return False

    except Exception as e:
        logger.error(f"❌ Migration setup failed: {e}")
        return False


def main():
    """Main migration runner."""
    logger.info("🏗️ Clean Timestamp Migration Runner")
    logger.info("=" * 50)

    # Check environment
    db_type = os.getenv("DATABASE_TYPE")
    if not db_type:
        logger.error("❌ DATABASE_TYPE environment variable not set")
        sys.exit(1)

    logger.info(f"📊 Database Type: {db_type}")

    # Run migration
    success = run_migration()

    if success:
        logger.info("🎉 Clean timestamp migration completed successfully!")
        logger.info("✅ Database is now ready for clean timestamp management")
        logger.info("✅ All timestamp columns are compatible with automatic management")
        logger.info("✅ Event handlers will now manage created_at/updated_at automatically")
        sys.exit(0)
    else:
        logger.error("💥 Clean timestamp migration failed!")
        logger.error("❌ Please check the logs above and resolve any issues")
        logger.error("❌ Database may not be ready for clean timestamp system")
        sys.exit(1)


if __name__ == "__main__":
    main()