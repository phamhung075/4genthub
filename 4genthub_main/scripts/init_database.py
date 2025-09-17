#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script

This script manages PostgreSQL database initialization.
The system uses PostgreSQL locally and Supabase for cloud deployment.

FOR DATABASE SETUP:
1. Local: Configure PostgreSQL connection in environment
2. Cloud: Use Supabase dashboard to manage schema
3. All tables are created automatically via SQLAlchemy ORM
"""

import logging
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize PostgreSQL database schema"""

    try:
        logger.info("=" * 60)
        logger.info("Database Initialization Starting...")
        logger.info("=" * 60)

        # Check database type
        db_type = os.getenv("DATABASE_TYPE", "postgresql")
        logger.info(f"Database Type: {db_type}")
        logger.info(f"Database Host: {os.getenv('DATABASE_HOST', 'localhost')}")
        logger.info(f"Database Name: {os.getenv('DATABASE_NAME', '4genthub')}")

        # Import the database initializer
        from fastmcp.task_management.infrastructure.database.db_initializer import (
            initialize_database_on_startup
        )

        # Initialize the database (creates tables if missing)
        logger.info("Checking database tables...")
        if initialize_database_on_startup():
            logger.info("=" * 60)
            logger.info("✅ DATABASE INITIALIZATION SUCCESSFUL!")
            logger.info("All required tables are present and verified")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("❌ DATABASE INITIALIZATION FAILED!")
            logger.error("Some tables could not be created")
            logger.error("The server will continue with limited functionality")
            logger.error("=" * 60)
            # Return 0 anyway to not break container startup
            return 0

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Could not import database initializer")
        logger.info("Continuing without database initialization...")
        return 0

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ CRITICAL ERROR: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        # Return 0 anyway to not break container startup
        return 0

if __name__ == "__main__":
    sys.exit(initialize_database())