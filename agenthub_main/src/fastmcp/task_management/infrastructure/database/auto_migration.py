"""
Automatic database migration runner for agenthub.
This module runs necessary migrations on startup to keep database schema in sync with ORM models.
"""

import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from .database_config import get_session

logger = logging.getLogger(__name__)


class AutoMigration:
    """Handles automatic database migrations on startup."""

    @staticmethod
    def run_all_migrations():
        """Run all necessary migrations."""
        try:
            logger.info("Starting automatic database migrations...")

            # Run individual migrations
            AutoMigration._rename_subtasks_table()
            AutoMigration._add_progress_state_columns()

            logger.info("✅ All database migrations completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    @staticmethod
    def _rename_subtasks_table():
        """Rename task_subtasks table to subtasks if needed."""
        try:
            with get_session() as session:
                # Check if old table exists
                inspector = inspect(session.bind)
                existing_tables = inspector.get_table_names()

                if 'task_subtasks' in existing_tables and 'subtasks' not in existing_tables:
                    logger.info("Renaming task_subtasks table to subtasks...")
                    session.execute(text("ALTER TABLE task_subtasks RENAME TO subtasks"))
                    session.commit()
                    logger.info("✅ Table renamed from task_subtasks to subtasks")
                elif 'subtasks' in existing_tables:
                    logger.info("✅ subtasks table already exists")
                else:
                    logger.warning("Neither task_subtasks nor subtasks table exists - will be created by ORM")

        except OperationalError as e:
            # Table might not exist yet, that's okay
            logger.info(f"Subtasks table migration skipped: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to rename subtasks table: {e}")
            raise

    @staticmethod
    def _add_progress_state_columns():
        """Add progress_state column to tasks and subtasks tables."""
        try:
            with get_session() as session:
                inspector = inspect(session.bind)

                # Check and add progress_state to tasks table
                tables_to_check = ['tasks', 'subtasks']

                for table_name in tables_to_check:
                    try:
                        # Check if table exists
                        if table_name not in inspector.get_table_names():
                            logger.info(f"Table {table_name} doesn't exist yet - will be created by ORM")
                            continue

                        # Check if column exists
                        columns = [col['name'] for col in inspector.get_columns(table_name)]

                        if 'progress_state' not in columns:
                            logger.info(f"Adding progress_state column to {table_name} table...")

                            # PostgreSQL syntax
                            try:
                                session.execute(text(
                                    f"ALTER TABLE {table_name} "
                                    f"ADD COLUMN progress_state VARCHAR(20) DEFAULT 'INITIAL' NOT NULL"
                                ))
                                session.commit()
                                logger.info(f"✅ Added progress_state column to {table_name} table")
                            except SQLAlchemyError as pg_err:
                                # Try SQLite syntax if PostgreSQL fails
                                session.rollback()
                                try:
                                    session.execute(text(
                                        f"ALTER TABLE {table_name} "
                                        f"ADD COLUMN progress_state TEXT DEFAULT 'INITIAL' NOT NULL"
                                    ))
                                    session.commit()
                                    logger.info(f"✅ Added progress_state column to {table_name} table (SQLite)")
                                except SQLAlchemyError:
                                    # Column might already exist
                                    session.rollback()
                                    logger.info(f"progress_state column might already exist in {table_name}")
                        else:
                            logger.info(f"✅ progress_state column already exists in {table_name} table")

                        # Update existing records to set proper progress_state based on status
                        session.execute(text(f"""
                            UPDATE {table_name}
                            SET progress_state = CASE
                                WHEN status = 'done' THEN 'COMPLETE'
                                WHEN status IN ('in_progress', 'active') THEN 'IN_PROGRESS'
                                ELSE 'INITIAL'
                            END
                            WHERE progress_state = 'INITIAL' OR progress_state = 'initial'
                        """))
                        session.commit()

                    except OperationalError as e:
                        logger.info(f"Table {table_name} operation skipped: {e}")
                        session.rollback()
                    except SQLAlchemyError as e:
                        logger.warning(f"Issue with {table_name} table: {e}")
                        session.rollback()

        except SQLAlchemyError as e:
            logger.error(f"Failed to add progress_state columns: {e}")
            raise


def run_auto_migrations():
    """Entry point for running automatic migrations."""
    return AutoMigration.run_all_migrations()