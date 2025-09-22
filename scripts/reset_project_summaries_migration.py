#!/usr/bin/env python3
"""
Reset project_summaries_mv migration and test it
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_migration():
    """Reset the migration using synchronous SQLAlchemy"""
    try:
        # Import the regular SQLAlchemy components
        from sqlalchemy import create_engine, text

        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL", "sqlite:///./data/agenthub.db")

        # For PostgreSQL, use the synchronous driver
        if database_url.startswith("postgresql://"):
            # Use psycopg2 for synchronous access
            pass
        elif database_url.startswith("sqlite:///"):
            # SQLite is already synchronous
            pass

        logger.info(f"Using database: {database_url}")

        # Create synchronous engine
        engine = create_engine(database_url, echo=True)

        with engine.begin() as conn:
            # Delete failed migration record
            result = conn.execute(text("""
                DELETE FROM applied_migrations
                WHERE migration_name = 'project_summaries_mv'
            """))

            logger.info(f"Deleted {result.rowcount} migration records for project_summaries_mv")

            # Try to drop the existing view if it exists
            try:
                conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS project_summaries_mv CASCADE;"))
                logger.info("Dropped existing project_summaries_mv")
            except Exception as e:
                logger.info(f"No existing view to drop: {e}")

        logger.info("Migration reset completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration reset failed: {e}")
        return False

def test_migration():
    """Test the migration by running it manually"""
    try:
        from fastmcp.task_management.infrastructure.database.migration_runner import AutoMigrationRunner
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncio

        # Get database URL
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/agenthub.db")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

        async def run_test():
            engine = create_async_engine(database_url, echo=True)

            try:
                runner = AutoMigrationRunner(engine)

                # Run only the project summaries migration
                logger.info("Testing project_summaries_mv migration...")
                await runner._create_project_summaries_view()
                await runner._record_migration("project_summaries_mv", success=True)

                logger.info("Migration test completed successfully!")

                # Test the view
                async with engine.begin() as conn:
                    from sqlalchemy import text
                    result = await conn.execute(text("""
                        SELECT project_id, project_name, total_branches, total_tasks,
                               completed_tasks, overall_progress_percentage
                        FROM project_summaries_mv
                        LIMIT 3
                    """))

                    rows = result.fetchall()
                    logger.info(f"View test successful! Found {len(rows)} projects:")
                    for row in rows:
                        logger.info(f"  {row.project_name}: {row.total_tasks} tasks, {row.overall_progress_percentage}% complete")

                return True

            finally:
                await engine.dispose()

        return asyncio.run(run_test())

    except Exception as e:
        logger.error(f"Migration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Resetting project_summaries_mv migration...")

    # Reset the migration record
    if reset_migration():
        print("✅ Migration record reset successfully")

        # Test the migration
        print("🧪 Testing migration...")
        if test_migration():
            print("✅ Migration test passed!")
            print("🎉 project_summaries_mv should now work correctly!")
        else:
            print("❌ Migration test failed")
            sys.exit(1)
    else:
        print("❌ Migration reset failed")
        sys.exit(1)