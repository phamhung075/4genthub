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
    """Initialize PostgreSQL database schema and populate agent templates"""

    try:
        logger.info("=" * 60)
        logger.info("Database Initialization Starting...")
        logger.info("=" * 60)

        # Check database type
        db_type = os.getenv("DATABASE_TYPE", "postgresql")
        logger.info(f"Database Type: {db_type}")
        logger.info(f"Database Host: {os.getenv('DATABASE_HOST', 'localhost')}")
        logger.info(f"Database Name: {os.getenv('DATABASE_NAME', 'agenthub')}")

        # Import the database initializer
        from fastmcp.task_management.infrastructure.database.db_initializer import (
            initialize_database_on_startup,
        )

        # Initialize the database (creates tables if missing)
        logger.info("Checking database tables...")
        if not initialize_database_on_startup():
            logger.error("=" * 60)
            logger.error("❌ DATABASE INITIALIZATION FAILED!")
            logger.error("Some tables could not be created")
            logger.error("The server will continue with limited functionality")
            logger.error("=" * 60)
            # Return 0 anyway to not break container startup
            return 0

        logger.info("✅ Database tables verified")

        # Populate agent templates if they don't exist
        logger.info("\n" + "=" * 60)
        logger.info("Checking Agent Templates...")
        logger.info("=" * 60)

        try:
            from fastmcp.agent_management.application.services import (
                YAMLAgentTemplateLoader,
            )
            from fastmcp.agent_management.infrastructure.repositories import (
                ORMAgentTemplateRepository,
            )

            # Check if templates already exist
            repository = ORMAgentTemplateRepository()
            existing_templates = repository.find_all()

            if existing_templates and len(existing_templates) > 0:
                logger.info(f"✅ Found {len(existing_templates)} existing agent templates")
                logger.info("Skipping agent population (already populated)")
            else:
                logger.info("No agent templates found, populating from YAML files...")

                # Load agent library path
                agent_library_path = Path(__file__).parent.parent / "agent-library"

                if not agent_library_path.exists():
                    logger.warning(f"⚠️  Agent library not found at: {agent_library_path}")
                    logger.warning("Skipping agent population")
                else:
                    # Load and populate templates
                    loader = YAMLAgentTemplateLoader(str(agent_library_path))
                    templates = loader.load_all_agents()

                    if templates:
                        logger.info(f"📖 Loaded {len(templates)} agent templates from YAML")

                        saved_count = 0
                        for template in templates:
                            try:
                                repository.save(template)
                                saved_count += 1
                            except Exception as e:
                                logger.error(f"❌ Error saving template {template.slug}: {e}")

                        logger.info(f"✅ Successfully populated {saved_count} agent templates")
                    else:
                        logger.warning("⚠️  No agent templates found in YAML files")

        except Exception as e:
            logger.error(f"⚠️  Agent template population failed: {e}")
            logger.error("Continuing without agent templates...")
            import traceback
            traceback.print_exc()

        logger.info("=" * 60)
        logger.info("✅ DATABASE INITIALIZATION SUCCESSFUL!")
        logger.info("All required tables are present and verified")
        logger.info("=" * 60)
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