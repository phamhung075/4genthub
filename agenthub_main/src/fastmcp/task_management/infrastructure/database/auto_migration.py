"""
Automatic database migration runner for agenthub.
This module runs necessary migrations on startup to keep database schema in sync with ORM models.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

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
            AutoMigration._add_subtask_count_column()
            AutoMigration._add_usage_tracking_columns()

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
                            except SQLAlchemyError:
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
                            SET progress_state = (CASE
                                WHEN status = 'done' THEN 'COMPLETE'
                                WHEN status IN ('in_progress', 'active') THEN 'IN_PROGRESS'
                                ELSE 'INITIAL'
                            END)::progressstate
                            WHERE progress_state = 'INITIAL'
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

    @staticmethod
    def _add_subtask_count_column():
        """Add subtask_count column to tasks table."""
        try:
            with get_session() as session:
                inspector = inspect(session.bind)
                
                # Check if tasks table exists
                if 'tasks' not in inspector.get_table_names():
                    logger.info("Table tasks doesn't exist yet - will be created by ORM")
                    return
                
                # Check if column exists
                columns = [col['name'] for col in inspector.get_columns('tasks')]
                
                if 'subtask_count' not in columns:
                    logger.info("Adding subtask_count column to tasks table...")
                    
                    # Determine database type
                    dialect_name = session.bind.dialect.name
                    
                    if dialect_name == 'postgresql':
                        # PostgreSQL syntax
                        session.execute(text(
                            "ALTER TABLE tasks ADD COLUMN subtask_count INTEGER DEFAULT 0"
                        ))
                    else:
                        # SQLite syntax
                        session.execute(text(
                            "ALTER TABLE tasks ADD COLUMN subtask_count INTEGER DEFAULT 0"
                        ))
                    
                    session.commit()
                    logger.info("✅ Added subtask_count column to tasks table")
                else:
                    logger.info("✅ subtask_count column already exists in tasks table")
        
        except OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("subtask_count column already exists in tasks table")
            else:
                logger.error(f"Failed to add subtask_count column: {e}")
                raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to add subtask_count column: {e}")
            raise

    @staticmethod
    def _add_usage_tracking_columns():
        """Add usage_count and last_used_at columns to user_agent_instances table."""
        try:
            with get_session() as session:
                inspector = inspect(session.bind)

                # Check if user_agent_instances table exists
                if 'user_agent_instances' not in inspector.get_table_names():
                    logger.info("Table user_agent_instances doesn't exist yet - will be created by ORM")
                    return

                # Check existing columns
                columns = [col['name'] for col in inspector.get_columns('user_agent_instances')]

                # Determine database type
                dialect_name = session.bind.dialect.name

                # Add usage_count column if missing
                if 'usage_count' not in columns:
                    logger.info("Adding usage_count column to user_agent_instances table...")

                    if dialect_name == 'postgresql':
                        session.execute(text(
                            "ALTER TABLE user_agent_instances ADD COLUMN usage_count INTEGER DEFAULT 0 NOT NULL"
                        ))
                    else:
                        session.execute(text(
                            "ALTER TABLE user_agent_instances ADD COLUMN usage_count INTEGER DEFAULT 0 NOT NULL"
                        ))

                    session.commit()
                    logger.info("✅ Added usage_count column to user_agent_instances table")
                else:
                    logger.info("✅ usage_count column already exists in user_agent_instances table")

                # Refresh inspector after adding usage_count
                inspector = inspect(session.bind)
                columns = [col['name'] for col in inspector.get_columns('user_agent_instances')]

                # Add last_used_at column if missing
                if 'last_used_at' not in columns:
                    logger.info("Adding last_used_at column to user_agent_instances table...")

                    if dialect_name == 'postgresql':
                        session.execute(text(
                            "ALTER TABLE user_agent_instances ADD COLUMN last_used_at TIMESTAMP WITH TIME ZONE"
                        ))
                    else:
                        session.execute(text(
                            "ALTER TABLE user_agent_instances ADD COLUMN last_used_at DATETIME"
                        ))

                    session.commit()
                    logger.info("✅ Added last_used_at column to user_agent_instances table")
                else:
                    logger.info("✅ last_used_at column already exists in user_agent_instances table")

        except OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("Usage tracking columns already exist in user_agent_instances table")
            else:
                logger.error(f"Failed to add usage tracking columns: {e}")
                raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to add usage tracking columns: {e}")
            raise


def run_auto_migrations():
    """Entry point for running automatic migrations."""
    return AutoMigration.run_all_migrations()