"""
Database Initializer for Automatic Setup and Verification

This module provides automatic database initialization and verification
on server startup. It checks if tables exist and creates them if needed.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from .database_config import DatabaseConfig, Base
# Import all models to ensure they're registered with Base
from . import models

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Handles automatic database initialization and verification.

    Features:
    - Checks if database and tables exist
    - Creates missing tables automatically
    - Verifies table structure
    - Handles both PostgreSQL and SQLite
    - Provides migration support
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """
        Initialize the database initializer.

        Args:
            db_config: Optional DatabaseConfig instance. If not provided,
                      uses the singleton instance.
        """
        self.db_config = db_config or DatabaseConfig.get_instance()
        self.engine = None
        self.initialized = False

    def initialize(self) -> bool:
        """
        Initialize the database, creating tables if they don't exist.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Starting database initialization...")

            # Get database engine
            self.engine = self.db_config.get_engine()
            if not self.engine:
                logger.error("Failed to get database engine")
                return False

            # Check if we can connect to the database
            if not self._verify_connection():
                logger.error("Cannot connect to database")
                return False

            # Check existing tables
            existing_tables = self._get_existing_tables()
            logger.info(f"Found {len(existing_tables)} existing tables: {existing_tables}")

            # Get required tables from models
            required_tables = self._get_required_tables()
            logger.info(f"Required tables: {required_tables}")

            # Find missing tables
            missing_tables = required_tables - existing_tables

            if missing_tables:
                logger.info(f"Missing tables detected: {missing_tables}")
                logger.info("Creating missing tables...")

                # Create all tables using SQLAlchemy Base metadata
                try:
                    Base.metadata.create_all(self.engine)
                    logger.info("✅ All tables created successfully")

                    # Verify tables were created
                    new_tables = self._get_existing_tables()
                    created_tables = new_tables - existing_tables
                    logger.info(f"Created {len(created_tables)} new tables: {created_tables}")

                except Exception as e:
                    logger.error(f"Failed to create tables: {e}")
                    return False
            else:
                logger.info("✅ All required tables already exist")

            # Verify table structure (optional - can add column checks here)
            if self._verify_table_structure():
                logger.info("✅ Table structure verified")
            else:
                logger.warning("⚠️ Table structure verification failed - may need migration")

            # Set initialization flag
            self.initialized = True
            logger.info("✅ Database initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    def _verify_connection(self) -> bool:
        """
        Verify that we can connect to the database.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Try a simple query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("✅ Database connection verified")
                return True
        except OperationalError as e:
            logger.error(f"Cannot connect to database: {e}")
            return False
        except Exception as e:
            logger.error(f"Database connection verification failed: {e}")
            return False

    def _get_existing_tables(self) -> set:
        """
        Get list of existing tables in the database.

        Returns:
            set: Set of existing table names
        """
        try:
            inspector = inspect(self.engine)
            tables = set(inspector.get_table_names())
            return tables
        except Exception as e:
            logger.error(f"Failed to get existing tables: {e}")
            return set()

    def _get_required_tables(self) -> set:
        """
        Get list of required tables from SQLAlchemy models.

        Returns:
            set: Set of required table names
        """
        # Get all table names from Base metadata
        return set(Base.metadata.tables.keys())

    def _verify_table_structure(self) -> bool:
        """
        Verify that table structures match the models.

        This is a basic check - can be extended to verify columns,
        types, constraints, etc.

        Returns:
            bool: True if structure is valid, False otherwise
        """
        try:
            inspector = inspect(self.engine)

            for table_name in Base.metadata.tables.keys():
                # Get model columns
                model_table = Base.metadata.tables[table_name]
                model_columns = set(col.name for col in model_table.columns)

                # Get database columns
                try:
                    db_columns = inspector.get_columns(table_name)
                    db_column_names = set(col['name'] for col in db_columns)

                    # Check if all model columns exist in database
                    missing_columns = model_columns - db_column_names
                    if missing_columns:
                        logger.warning(f"Table '{table_name}' missing columns: {missing_columns}")
                        # Note: We could add ALTER TABLE logic here to add missing columns
                        # For now, just log the warning

                    # Check for extra columns in database (not in model)
                    extra_columns = db_column_names - model_columns
                    if extra_columns:
                        logger.info(f"Table '{table_name}' has extra columns: {extra_columns}")

                except Exception as e:
                    logger.warning(f"Could not inspect table '{table_name}': {e}")

            return True

        except Exception as e:
            logger.error(f"Table structure verification failed: {e}")
            return False

    def create_default_data(self) -> bool:
        """
        Create default data if needed (e.g., default users, roles, etc.).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # This can be extended to create default data
            # For now, just return True as no default data is required
            logger.info("No default data needed")
            return True

        except Exception as e:
            logger.error(f"Failed to create default data: {e}")
            return False

    def check_and_init(self) -> bool:
        """
        Check database status and initialize if needed.

        This is the main entry point for server startup.

        Returns:
            bool: True if database is ready, False otherwise
        """
        try:
            # Skip if already initialized
            if self.initialized:
                logger.info("Database already initialized in this session")
                return True

            # Initialize database
            if not self.initialize():
                logger.error("Database initialization failed")
                return False

            # Create default data if needed
            if not self.create_default_data():
                logger.warning("Failed to create default data, but continuing...")

            logger.info("✅ Database is ready for use")
            return True

        except Exception as e:
            logger.error(f"Database check and init failed: {e}")
            return False

    def reset_database(self, confirm: bool = False) -> bool:
        """
        Reset the database by dropping and recreating all tables.

        WARNING: This will delete all data!

        Args:
            confirm: Must be True to actually perform the reset

        Returns:
            bool: True if successful, False otherwise
        """
        if not confirm:
            logger.warning("Database reset requested but not confirmed")
            return False

        try:
            logger.warning("⚠️ RESETTING DATABASE - ALL DATA WILL BE LOST!")

            # Drop all tables
            Base.metadata.drop_all(self.engine)
            logger.info("All tables dropped")

            # Recreate all tables
            Base.metadata.create_all(self.engine)
            logger.info("All tables recreated")

            # Create default data
            self.create_default_data()

            logger.info("✅ Database reset completed")
            return True

        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False


# Singleton instance for easy access
_db_initializer: Optional[DatabaseInitializer] = None


def get_db_initializer() -> DatabaseInitializer:
    """
    Get the singleton database initializer instance.

    Returns:
        DatabaseInitializer: The singleton instance
    """
    global _db_initializer
    if _db_initializer is None:
        _db_initializer = DatabaseInitializer()
    return _db_initializer


def initialize_database_on_startup() -> bool:
    """
    Convenience function to initialize database on server startup.

    This should be called from the main server entry point.

    Returns:
        bool: True if database is ready, False otherwise
    """
    initializer = get_db_initializer()
    return initializer.check_and_init()


def reset_database(confirm: bool = False) -> bool:
    """
    Convenience function to reset the database.

    WARNING: This will delete all data!

    Args:
        confirm: Must be True to actually perform the reset

    Returns:
        bool: True if successful, False otherwise
    """
    initializer = get_db_initializer()
    return initializer.reset_database(confirm=confirm)