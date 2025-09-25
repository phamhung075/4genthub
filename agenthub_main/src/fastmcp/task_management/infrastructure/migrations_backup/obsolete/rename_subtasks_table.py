"""
Migration to rename task_subtasks table to subtasks.

This migration handles the table rename for existing databases to maintain
data consistency while updating to the new simplified table naming convention.
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging
from typing import Any

logger = logging.getLogger(__name__)


def upgrade(engine: Any) -> None:
    """Rename task_subtasks table to subtasks."""

    with engine.begin() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Check if old table exists and new table doesn't
        has_old_table = 'task_subtasks' in existing_tables
        has_new_table = 'subtasks' in existing_tables

        if has_old_table and not has_new_table:
            try:
                logger.info("Renaming task_subtasks table to subtasks")

                # Check dialect to use appropriate SQL
                dialect_name = engine.dialect.name

                if dialect_name == 'postgresql':
                    # PostgreSQL syntax
                    conn.execute(text("ALTER TABLE task_subtasks RENAME TO subtasks"))

                    # Update index names if they exist
                    try:
                        conn.execute(text("ALTER INDEX IF EXISTS idx_task_subtasks_task_id RENAME TO idx_subtasks_task_id"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_task_subtasks_status RENAME TO idx_subtasks_status"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_task_subtasks_priority RENAME TO idx_subtasks_priority"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_task_subtasks_progress RENAME TO idx_subtasks_progress"))
                    except Exception as e:
                        logger.warning(f"Could not rename some indexes: {e}")

                elif dialect_name == 'sqlite':
                    # SQLite doesn't support RENAME TABLE directly with all constraints
                    # We need to create new table and copy data
                    logger.info("SQLite detected - using CREATE/INSERT/DROP approach")

                    # Get the current table structure
                    columns_info = inspector.get_columns('task_subtasks')
                    indexes_info = inspector.get_indexes('task_subtasks')

                    # Create new table with same structure
                    conn.execute(text("""
                        CREATE TABLE subtasks AS SELECT * FROM task_subtasks WHERE 1=0
                    """))

                    # Copy all data
                    conn.execute(text("""
                        INSERT INTO subtasks SELECT * FROM task_subtasks
                    """))

                    # Recreate indexes with new names
                    try:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_status ON subtasks(status)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_priority ON subtasks(priority)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_progress ON subtasks(progress_percentage)"))
                    except Exception as e:
                        logger.warning(f"Could not create all indexes: {e}")

                    # Drop old table
                    conn.execute(text("DROP TABLE task_subtasks"))

                else:
                    # MySQL and other databases
                    conn.execute(text("ALTER TABLE task_subtasks RENAME TO subtasks"))

                logger.info("Successfully renamed task_subtasks table to subtasks")

            except (OperationalError, ProgrammingError) as e:
                logger.error(f"Failed to rename table: {e}")
                raise

        elif has_new_table and not has_old_table:
            logger.info("Table already renamed to subtasks - no action needed")

        elif has_old_table and has_new_table:
            logger.warning("Both task_subtasks and subtasks tables exist - manual intervention required")

        else:
            logger.info("Neither table exists - will be created by ORM")


def downgrade(engine: Any) -> None:
    """Rename subtasks table back to task_subtasks."""

    with engine.begin() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Check if new table exists and old table doesn't
        has_new_table = 'subtasks' in existing_tables
        has_old_table = 'task_subtasks' in existing_tables

        if has_new_table and not has_old_table:
            try:
                logger.info("Renaming subtasks table back to task_subtasks")

                # Check dialect to use appropriate SQL
                dialect_name = engine.dialect.name

                if dialect_name == 'postgresql':
                    # PostgreSQL syntax
                    conn.execute(text("ALTER TABLE subtasks RENAME TO task_subtasks"))

                    # Update index names back
                    try:
                        conn.execute(text("ALTER INDEX IF EXISTS idx_subtasks_task_id RENAME TO idx_task_subtasks_task_id"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_subtasks_status RENAME TO idx_task_subtasks_status"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_subtasks_priority RENAME TO idx_task_subtasks_priority"))
                        conn.execute(text("ALTER INDEX IF EXISTS idx_subtasks_progress RENAME TO idx_task_subtasks_progress"))
                    except Exception as e:
                        logger.warning(f"Could not rename some indexes: {e}")

                elif dialect_name == 'sqlite':
                    # SQLite approach
                    logger.info("SQLite detected - using CREATE/INSERT/DROP approach")

                    # Create old table structure
                    conn.execute(text("""
                        CREATE TABLE task_subtasks AS SELECT * FROM subtasks WHERE 1=0
                    """))

                    # Copy all data back
                    conn.execute(text("""
                        INSERT INTO task_subtasks SELECT * FROM subtasks
                    """))

                    # Recreate old indexes
                    try:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_subtasks_task_id ON task_subtasks(task_id)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_subtasks_status ON task_subtasks(status)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_subtasks_priority ON task_subtasks(priority)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_subtasks_progress ON task_subtasks(progress_percentage)"))
                    except Exception as e:
                        logger.warning(f"Could not create all indexes: {e}")

                    # Drop new table
                    conn.execute(text("DROP TABLE subtasks"))

                else:
                    # MySQL and other databases
                    conn.execute(text("ALTER TABLE subtasks RENAME TO task_subtasks"))

                logger.info("Successfully renamed subtasks table back to task_subtasks")

            except (OperationalError, ProgrammingError) as e:
                logger.error(f"Failed to rename table back: {e}")
                raise

        else:
            logger.info("Table rename rollback not needed or not possible")


if __name__ == "__main__":
    # This can be run directly for testing
    import sys
    sys.path.append("../../../../../../")

    from fastmcp.task_management.infrastructure.database.database_config import get_engine

    engine = get_engine()
    upgrade(engine)
    print("Table rename migration completed successfully")