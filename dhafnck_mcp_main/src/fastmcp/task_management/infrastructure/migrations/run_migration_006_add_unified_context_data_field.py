#!/usr/bin/env python3
"""
Migration 006: Add unified_context_data field to global_contexts table

This migration fixes the context data persistence issue by adding the missing
'unified_context_data' field to the GlobalContext database model.

ISSUE: Context data was not being properly stored/returned because the GlobalContext
model lacked the unified context data field that enables compatibility with the
unified context API.

SOLUTION: Add 'unified_context_data' field to global_contexts table and populate it from existing nested_structure data.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(src_path))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_engine():
    """Get database engine from environment configuration."""
    try:
        db_config = get_db_config()
        database_url = db_config._get_database_url()
        logger.info(f"Connecting to database: {database_url.split('@')[0] if '@' in database_url else database_url}...")
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Could not inspect table {table_name}: {e}")
        return False


def apply_migration_006(engine):
    """Apply migration 006 to add unified_context_data field to global_contexts table."""

    logger.info("🔧 Starting Migration 006: Add unified_context_data field to global_contexts")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if unified_context_data column already exists
        if check_column_exists(engine, 'global_contexts', 'unified_context_data'):
            logger.info("✅ Column 'unified_context_data' already exists in global_contexts table")
            return True

        # Step 1: Add the unified_context_data column
        logger.info("📝 Adding 'unified_context_data' column to global_contexts table...")
        session.execute(text("""
            ALTER TABLE global_contexts
            ADD COLUMN unified_context_data JSON DEFAULT '{}'
        """))
        session.commit()
        logger.info("✅ Successfully added 'unified_context_data' column")

        # Step 2: Populate unified_context_data field from existing nested_structure
        logger.info("📄 Populating unified_context_data field from existing nested_structure...")
        result = session.execute(text("""
            UPDATE global_contexts
            SET unified_context_data = CASE
                WHEN nested_structure IS NOT NULL AND nested_structure != '{}' THEN nested_structure
                ELSE '{}'
            END
            WHERE unified_context_data IS NULL OR unified_context_data = '{}'
        """))

        rows_updated = result.rowcount
        session.commit()
        logger.info(f"✅ Updated {rows_updated} rows with existing nested_structure data")

        # Step 3: Verify the migration
        logger.info("🔍 Verifying migration results...")
        verification_result = session.execute(text("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN unified_context_data IS NOT NULL AND unified_context_data != '{}' THEN 1 END) as rows_with_data,
                COUNT(CASE WHEN nested_structure IS NOT NULL AND nested_structure != '{}' THEN 1 END) as rows_with_nested
            FROM global_contexts
        """)).fetchone()

        if verification_result:
            total, with_data, with_nested = verification_result
            logger.info(f"📊 Migration verification:")
            logger.info(f"   Total rows: {total}")
            logger.info(f"   Rows with data field: {with_data}")
            logger.info(f"   Rows with nested_structure: {with_nested}")

        logger.info("🎉 Migration 006 completed successfully!")
        return True

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during migration: {e}")
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def rollback_migration_006(engine):
    """Rollback migration 006 by removing the unified_context_data field."""

    logger.info("🔄 Rolling back Migration 006: Remove unified_context_data field from global_contexts")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if unified_context_data column exists before trying to remove it
        if not check_column_exists(engine, 'global_contexts', 'unified_context_data'):
            logger.info("✅ Column 'unified_context_data' does not exist in global_contexts table")
            return True

        # Remove the unified_context_data column
        logger.info("🗑️ Removing 'unified_context_data' column from global_contexts table...")
        session.execute(text("ALTER TABLE global_contexts DROP COLUMN unified_context_data"))
        session.commit()

        logger.info("✅ Migration 006 rolled back successfully!")
        return True

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during rollback: {e}")
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during rollback: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    """Main function to run the migration."""

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("🔄 Running Migration 006 Rollback...")
        engine = get_database_engine()
        rollback_migration_006(engine)
    else:
        print("🚀 Running Migration 006...")
        engine = get_database_engine()
        apply_migration_006(engine)

    print("Migration 006 completed!")


if __name__ == "__main__":
    main()