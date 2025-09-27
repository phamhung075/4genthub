"""
Database Initialization Script using SQLAlchemy

This module initializes the database schema using SQLAlchemy,
supporting both SQLite and PostgreSQL databases.
"""

import logging
import os
import asyncio
from pathlib import Path

from .database_config import get_db_config, Base
from .models import (
    Project, ProjectGitBranch, Task, Subtask, TaskAssignee,
    TaskDependency, Agent, Label, TaskLabel, Template,
    GlobalContext, ProjectContext, BranchContext, TaskContext, ContextDelegation, ContextInheritanceCache,
    APIToken
)

logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize database schema.

    This function creates all tables defined in the models
    if they don't already exist, then runs automatic migrations.
    """
    try:
        # Get database configuration
        db_config = get_db_config()

        # Log database info
        db_info = db_config.get_database_info()
        logger.info(f"Initializing database: {db_info['type']}")

        # Create all tables
        db_config.create_tables()

        # Run automatic migrations after table creation
        try:
            logger.info("Running automatic database migrations...")
            asyncio.run(_run_migrations(db_config))
            logger.info("Automatic migrations completed successfully")
        except Exception as migration_e:
            logger.error(f"Migration failed: {migration_e}")
            # Don't fail the entire initialization - server can continue without migrations
            logger.warning("Server will continue without migrations - some features may not work optimally")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def _run_migrations(db_config):
    """
    Run automatic database migrations using AsyncEngine.

    This function creates an async engine from the existing database configuration
    and runs all pending migrations.
    """
    # Get the database URL from the existing configuration
    database_url = db_config._get_database_url()

    # Check if async drivers are available and convert URL accordingly
    async_database_url = None

    if database_url.startswith("sqlite:///"):
        # For SQLite, try aiosqlite
        try:
            import aiosqlite
            async_database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        except ImportError:
            logger.warning("aiosqlite not available - skipping async migrations for SQLite")
            logger.info("Install aiosqlite with: pip install aiosqlite")
            return

    elif database_url.startswith("postgresql://") or "postgresql" in database_url:
        # For PostgreSQL, try asyncpg
        try:
            import asyncpg
            if database_url.startswith("postgresql://"):
                async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                async_database_url = database_url
                if not async_database_url.startswith("postgresql+asyncpg://"):
                    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://")
        except ImportError:
            logger.warning("asyncpg not available - skipping async migrations for PostgreSQL")
            logger.info("Install asyncpg with: pip install asyncpg")
            return
    else:
        logger.warning(f"Unsupported database type for async migrations: {database_url}")
        return

    if not async_database_url:
        logger.warning("Could not create async database URL - skipping migrations")
        return

    # Create async engine
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from .migration_runner import initialize_database as run_migrations

        async_engine = create_async_engine(
            async_database_url,
            echo=False,  # Set to True for debugging SQL queries
            # Connection pool settings for reliability
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        try:
            # Run the migration initialization
            await run_migrations(async_engine)
            logger.info("Migration runner completed successfully")
        finally:
            # Clean up the async engine
            await async_engine.dispose()

    except ImportError as e:
        logger.warning(f"Async SQLAlchemy not available: {e}")
        logger.info("Install async support with: pip install sqlalchemy[asyncio]")
    except Exception as e:
        logger.error(f"Failed to create async engine: {e}")
        raise


def migrate_from_sqlite_to_postgresql(sqlite_path: str):
    """
    Migrate data from SQLite to PostgreSQL.
    
    Args:
        sqlite_path: Path to SQLite database file
    """
    import sqlite3
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    logger.info(f"Starting migration from SQLite: {sqlite_path}")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Get PostgreSQL session
    db_config = get_db_config()
    if db_config.database_type != "postgresql":
        raise ValueError("DATABASE_TYPE must be set to 'postgresql' for migration")
    
    session = db_config.get_session()
    
    try:
        # Migrate projects
        logger.info("Migrating projects...")
        cursor = sqlite_conn.execute("SELECT * FROM projects")
        for row in cursor:
            project = Project(
                id=row['id'],
                name=row['name'],
                description=row['description'] or '',
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                user_id=row['user_id'],
                status=row['status'] or 'active',
                metadata=row['metadata'] or {}
            )
            session.merge(project)
        
        # Migrate project_git_branchs
        logger.info("Migrating git branches...")
        cursor = sqlite_conn.execute("SELECT * FROM project_git_branchs")
        for row in cursor:
            branch = ProjectGitBranch(
                id=row['id'],
                project_id=row['project_id'],
                name=row['name'],
                description=row['description'] or '',
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                assigned_agent_id=row['assigned_agent_id'],
                priority=row['priority'] or 'medium',
                status=row['status'] or 'todo',
                metadata=row['metadata'] or {},
                task_count=row['task_count'] or 0,
                completed_task_count=row['completed_task_count'] or 0
            )
            session.merge(branch)
        
        # Migrate tasks
        logger.info("Migrating tasks...")
        cursor = sqlite_conn.execute("SELECT * FROM tasks")
        for row in cursor:
            task = Task(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                git_branch_id=row['git_branch_id'],
                status=row['status'] or 'todo',
                priority=row['priority'] or 'medium',
                details=row['details'] or '',
                estimated_effort=row['estimated_effort'] or '',
                due_date=row['due_date'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                context_id=row['context_id']
            )
            session.merge(task)
        
        # Migrate subtasks
        logger.info("Migrating subtasks...")
        cursor = sqlite_conn.execute("SELECT * FROM subtasks")
        for row in cursor:
            subtask = Subtask(
                id=row['id'],
                task_id=row['task_id'],
                title=row['title'],
                description=row['description'] or '',
                status=row['status'] or 'todo',
                priority=row['priority'] or 'medium',
                assignees=row['assignees'] or [],
                estimated_effort=row['estimated_effort'],
                progress_percentage=row['progress_percentage'] or 0,
                progress_notes=row['progress_notes'] or '',
                blockers=row['blockers'] or '',
                completion_summary=row['completion_summary'] or '',
                impact_on_parent=row['impact_on_parent'] or '',
                insights_found=row['insights_found'] or [],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at']
            )
            session.merge(subtask)
        
        # Note: HierarchicalContext has been removed and replaced with granular context models
        # (GlobalContext, ProjectContext, BranchContext, TaskContext)
        # If you need to migrate old hierarchical_context data, you'll need to map it to the new models
        
        # Commit all changes
        session.commit()
        logger.info("Migration completed successfully")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        session.close()
        sqlite_conn.close()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    init_database()