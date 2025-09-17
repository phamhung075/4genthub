"""
Centralized Database Initializer for 4genthub

This module provides a single point of truth for initializing the database,
ensuring that all required schemas are created consistently.
Uses SQLAlchemy ORM with support for PostgreSQL (recommended) and SQLite (legacy).
"""

import os
import logging
import threading
from pathlib import Path
from typing import Optional

from .database_config import get_db_config
from .init_database import init_database as sqlalchemy_init_database

logger = logging.getLogger(__name__)

# Use a lock to prevent race conditions during initialization
db_init_lock = threading.Lock()

# Keep track of initialized databases to avoid redundant IO
_initialized_dbs = set()


def _find_project_root() -> str:
    """Find project root by looking for 4genthub_main directory"""
    # Primary approach - use the directory containing 4genthub_main
    current_path = os.path.abspath(__file__)
    while os.path.dirname(current_path) != current_path:
        if os.path.basename(current_path) == "4genthub_main":
            return os.path.dirname(current_path)
        current_path = os.path.dirname(current_path)
    
    # Fallback 1: Walk up the directory tree looking for 4genthub_main as a subdirectory
    current_path = os.path.abspath(__file__)
    while os.path.dirname(current_path) != current_path:
        if os.path.exists(os.path.join(current_path, "4genthub_main")):
            return current_path
        current_path = os.path.dirname(current_path)
    
    # Fallback 2: use current working directory if it contains 4genthub_main
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "4genthub_main")):
        return cwd
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('4GENTHUB_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, "4genthub_main")):
            return cwd
        # Fall back to temp directory for safety
        return "/tmp/4genthub_project"
    return data_path


def initialize_database(db_path: Optional[str] = None):
    """
    Initialize the database with all required schemas.
    
    This function now uses SQLAlchemy ORM to create tables,
    supporting both SQLite and PostgreSQL based on DATABASE_TYPE.
    
    Args:
        db_path: Optional database path (for backward compatibility with SQLite)
                 Ignored when using PostgreSQL.
    """
    database_type = os.getenv("DATABASE_TYPE", "postgresql").lower()
    
    # Check if we're in test mode
    import sys
    is_test_mode = 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os.environ
    
    # Validate database type
    if database_type == "sqlite":
        if not is_test_mode:
            # SQLite not allowed in production
            logger.error(
                "Database type 'sqlite' is not supported for production. "
                "PostgreSQL is required for this system. "
                "Set DATABASE_TYPE=postgresql or supabase to use PostgreSQL."
            )
            raise ValueError("PostgreSQL is required for production. Set DATABASE_TYPE=postgresql or supabase.")
        else:
            # SQLite allowed for tests
            logger.info("📦 Using SQLite database for test execution")
    
    # For PostgreSQL/Supabase, we don't need db_path as it uses DATABASE_URL
    if database_type in ["postgresql", "supabase"]:
        db_identifier = database_type
    else:
        # For SQLite, use provided path or default
        if not db_path:
            from .database_source_manager import DatabaseSourceManager
            manager = DatabaseSourceManager()
            db_path = manager.get_database_path()
        db_identifier = os.path.abspath(db_path)
    
    # Skip if already initialized (thread-safe check)
    with db_init_lock:
        if db_identifier in _initialized_dbs:
            logger.debug(f"Database already initialized: {db_identifier}")
            return
        
        logger.info(f"Initializing database: {db_identifier}")
        
        try:
            # Use SQLAlchemy to initialize database
            sqlalchemy_init_database()
            
            # Mark as initialized
            _initialized_dbs.add(db_identifier)
            logger.info(f"Database initialized successfully: {db_identifier}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise


def reset_initialization_cache():
    """Reset the initialization cache - useful for testing"""
    global _initialized_dbs
    _initialized_dbs = set()


# DEPRECATED: Removed schema path function as SQL schemas are no longer used with ORM
# The get_schema_path() function has been removed as it's no longer needed
# after migration to SQLAlchemy ORM. All database initialization now uses
# ORM models defined in models.py