#!/usr/bin/env python3
"""Database migration runner - automatically applies migrations on server startup"""

import logging
import psycopg2
from psycopg2 import sql
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles database migrations for the application"""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize the migrator with database connection"""
        if database_url:
            self.database_url = database_url
        else:
            # Build database URL from environment variables
            db_type = os.getenv('DATABASE_TYPE', 'postgresql')
            if db_type == 'postgresql':
                host = os.getenv('DATABASE_HOST', 'localhost')
                port = os.getenv('DATABASE_PORT', '5432')
                name = os.getenv('DATABASE_NAME', 'postgresdb')
                user = os.getenv('DATABASE_USER', 'agenthub_user')
                password = os.getenv('DATABASE_PASSWORD', 'agenthub_password')
                self.database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
            else:
                # SQLite or other database types
                self.database_url = os.getenv('DATABASE_URL', 'sqlite:///agenthub_dev.db')

    def run_migrations(self) -> bool:
        """Run all necessary database migrations"""
        try:
            logger.info("Starting database migrations...")

            # Only run migrations for PostgreSQL
            if 'postgresql' not in self.database_url:
                logger.info("Skipping migrations for non-PostgreSQL database")
                return True

            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                # Start a transaction
                trans = conn.begin()

                try:
                    # Check if tasks table exists
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'tasks'
                        );
                    """))
                    table_exists = result.scalar()

                    if not table_exists:
                        logger.info("Tasks table doesn't exist. Skipping migration.")
                        trans.commit()
                        return True

                    # Migration 1: Add progress_history columns
                    logger.info("Checking for progress_history columns...")

                    # Check if columns already exist
                    result = conn.execute(text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'tasks'
                        AND column_name IN ('progress_history', 'progress_count', 'details');
                    """))

                    existing_columns = {row[0] for row in result}

                    # Add progress_history if it doesn't exist
                    if 'progress_history' not in existing_columns:
                        logger.info("Adding progress_history column...")
                        conn.execute(text("""
                            ALTER TABLE tasks
                            ADD COLUMN progress_history JSON DEFAULT '{}';
                        """))

                    # Add progress_count if it doesn't exist
                    if 'progress_count' not in existing_columns:
                        logger.info("Adding progress_count column...")
                        conn.execute(text("""
                            ALTER TABLE tasks
                            ADD COLUMN progress_count INTEGER DEFAULT 0;
                        """))

                    # Migrate data from details column if it exists
                    if 'details' in existing_columns:
                        logger.info("Migrating data from details to progress_history...")

                        # First, check if there are any non-null details to migrate
                        result = conn.execute(text("""
                            SELECT COUNT(*) FROM tasks
                            WHERE details IS NOT NULL
                            AND (progress_history IS NULL OR progress_history::text = '{}');
                        """))
                        count_to_migrate = result.scalar()

                        if count_to_migrate > 0:
                            logger.info(f"Migrating {count_to_migrate} tasks with details...")
                            conn.execute(text("""
                                UPDATE tasks
                                SET progress_history = jsonb_build_object(
                                    'entry_1', jsonb_build_object(
                                        'content', CONCAT('=== Progress 1 ===', E'\\n', details),
                                        'timestamp', COALESCE(updated_at::text, created_at::text),
                                        'progress_number', 1
                                    )
                                ),
                                progress_count = 1
                                WHERE details IS NOT NULL
                                AND (progress_history IS NULL OR progress_history::text = '{}');
                            """))

                        # Drop the details column
                        logger.info("Dropping old details column...")
                        conn.execute(text("ALTER TABLE tasks DROP COLUMN details;"))

                    # Create indexes
                    logger.info("Creating indexes...")
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_tasks_progress_count
                        ON tasks(progress_count);
                    """))

                    # Commit the transaction
                    trans.commit()
                    logger.info("✅ Database migrations completed successfully!")
                    return True

                except Exception as e:
                    trans.rollback()
                    logger.error(f"Migration failed, rolling back: {e}")
                    raise

        except Exception as e:
            logger.error(f"❌ Database migration error: {e}")
            # Don't fail the entire application if migration fails
            # Just log the error and continue
            return False

    def initialize_database(self) -> bool:
        """Initialize database with required extensions and settings"""
        try:
            logger.info("Initializing database...")

            if 'postgresql' not in self.database_url:
                logger.info("Skipping initialization for non-PostgreSQL database")
                return True

            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                # Create UUID extension if it doesn't exist
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                conn.commit()

                logger.info("✅ Database initialization completed!")
                return True

        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            return False

    def ensure_database_ready(self) -> bool:
        """Ensure database is ready with all migrations applied"""
        try:
            # First initialize database
            if not self.initialize_database():
                logger.warning("Database initialization had issues but continuing...")

            # Then run migrations
            if not self.run_migrations():
                logger.warning("Some migrations failed but continuing...")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to ensure database ready: {e}")
            return False


# Singleton instance
_migrator = None

def get_migrator(database_url: Optional[str] = None) -> DatabaseMigrator:
    """Get or create the singleton migrator instance"""
    global _migrator
    if _migrator is None:
        _migrator = DatabaseMigrator(database_url)
    return _migrator

def run_startup_migrations(database_url: Optional[str] = None) -> bool:
    """Run migrations on application startup"""
    migrator = get_migrator(database_url)
    success = migrator.ensure_database_ready()

    # Run auto migrations (table renames, column additions)
    if success:
        try:
            logger.info("Running automatic database migrations...")
            from fastmcp.task_management.infrastructure.database.auto_migration import run_auto_migrations
            if run_auto_migrations():
                logger.info("✅ Automatic migrations completed successfully")
            else:
                logger.warning("⚠️ Some automatic migrations failed, but continuing...")
        except Exception as e:
            logger.warning(f"Could not run automatic migrations: {e}")
            # Continue anyway - don't block server startup for migration issues

    # Also run initialization if migrations succeeded
    if success:
        try:
            from fastmcp.database_init import initialize_database_for_current_user
            if initialize_database_for_current_user():
                logger.info("✅ Database initialization completed")
            else:
                logger.info("Database initialization skipped or already done")
        except Exception as e:
            logger.warning(f"Could not run database initialization: {e}")

    return success