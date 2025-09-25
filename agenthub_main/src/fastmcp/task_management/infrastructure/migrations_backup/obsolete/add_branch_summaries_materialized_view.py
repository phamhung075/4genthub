#!/usr/bin/env python3
"""
Migration: Add Materialized View for Branch Summaries
Phase 1: Database Optimization for API Performance

This migration creates a materialized view to optimize branch summary queries,
reducing the need for multiple API calls by pre-calculating aggregated data.
"""

import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BranchSummariesMaterializedViewMigration:
    """Migration to create and manage branch_summaries_mv materialized view"""

    @staticmethod
    async def up(engine: AsyncEngine) -> None:
        """Create materialized view and supporting infrastructure"""
        async with engine.begin() as conn:
            # Check if we're using PostgreSQL
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            is_postgres = "PostgreSQL" in str(db_version)

            if is_postgres:
                await BranchSummariesMaterializedViewMigration._create_postgres_mv(conn)
            else:
                # For SQLite, create a regular view or table that mimics materialized view
                await BranchSummariesMaterializedViewMigration._create_sqlite_view(conn)

    @staticmethod
    async def _create_postgres_mv(conn: Any) -> None:
        """Create PostgreSQL materialized view"""

        # Drop existing materialized view if exists
        await conn.execute(text("""
            DROP MATERIALIZED VIEW IF EXISTS branch_summaries_mv CASCADE;
        """))

        # Create the materialized view
        await conn.execute(text("""
            CREATE MATERIALIZED VIEW branch_summaries_mv AS
            SELECT
                b.id as branch_id,
                b.project_id,
                b.name as branch_name,
                b.description as branch_description,
                b.status as branch_status,
                b.priority as branch_priority,
                b.assigned_agent_id,
                b.user_id,
                b.created_at as branch_created_at,
                b.updated_at as branch_updated_at,

                -- Task statistics
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') as completed_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'in_progress') as in_progress_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'blocked') as blocked_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'todo') as todo_tasks,

                -- Progress calculations
                CASE
                    WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                    ELSE ROUND(100.0 * COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') / COUNT(DISTINCT t.id))
                END as progress_percentage,

                -- Subtask statistics
                COUNT(DISTINCT s.id) as total_subtasks,
                COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'done') as completed_subtasks,

                -- Priority distribution
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'critical') as critical_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'high') as high_priority_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'medium') as medium_priority_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'low') as low_priority_tasks,

                -- Time metrics
                MAX(t.updated_at) as last_task_activity,
                MIN(t.created_at) as first_task_created,

                -- Aggregate effort estimation
                STRING_AGG(DISTINCT t.estimated_effort, ', ') as effort_estimates,

                -- Agent assignments
                COUNT(DISTINCT ta.agent_id) as assigned_agents_count,
                STRING_AGG(DISTINCT ta.agent_id::text, ', ') as assigned_agent_ids,

                -- Labels aggregation
                COUNT(DISTINCT l.name) as unique_labels_count,
                STRING_AGG(DISTINCT l.name, ', ') as all_labels

            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            LEFT JOIN task_assignees ta ON ta.task_id = t.id
            LEFT JOIN task_labels tl ON tl.task_id = t.id
            LEFT JOIN labels l ON l.id = tl.label_id
            GROUP BY
                b.id, b.project_id, b.name, b.description, b.status,
                b.priority, b.assigned_agent_id, b.user_id,
                b.created_at, b.updated_at
        """))

        # Create indexes for performance (non-concurrent to work within transaction)
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_branch_summaries_project
            ON branch_summaries_mv(project_id);
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_branch_summaries_user
            ON branch_summaries_mv(user_id);
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_branch_summaries_status
            ON branch_summaries_mv(branch_status);
        """))

        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_branch_summaries_branch_id
            ON branch_summaries_mv(branch_id);
        """))

        # Create refresh function
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION refresh_branch_summaries()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW branch_summaries_mv;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # Create trigger function to auto-refresh on changes
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION trigger_refresh_branch_summaries()
            RETURNS trigger AS $$
            BEGIN
                -- Async refresh to avoid blocking
                PERFORM pg_notify('refresh_branch_summaries', 'refresh');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # Create triggers on related tables
        for table in ['tasks', 'subtasks', 'task_assignees', 'task_labels']:
            # Drop trigger first
            await conn.execute(text(f"""
                DROP TRIGGER IF EXISTS refresh_branch_summaries_on_{table} ON {table};
            """))

            # Create trigger
            await conn.execute(text(f"""
                CREATE TRIGGER refresh_branch_summaries_on_{table}
                AFTER INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH STATEMENT
                EXECUTE FUNCTION trigger_refresh_branch_summaries();
            """))

        # Initial refresh
        await conn.execute(text("REFRESH MATERIALIZED VIEW branch_summaries_mv;"))

        logger.info("PostgreSQL materialized view 'branch_summaries_mv' created successfully")

    @staticmethod
    async def _create_sqlite_view(conn: Any) -> None:
        """Create SQLite view (regular view as SQLite doesn't support materialized views)"""

        # Drop existing view if exists
        await conn.execute(text("DROP VIEW IF EXISTS branch_summaries_mv;"))

        # Create regular view for SQLite
        await conn.execute(text("""
            CREATE VIEW branch_summaries_mv AS
            SELECT
                b.id as branch_id,
                b.project_id,
                b.name as branch_name,
                b.description as branch_description,
                b.status as branch_status,
                b.priority as branch_priority,
                b.assigned_agent_id,
                b.user_id,
                b.created_at as branch_created_at,
                b.updated_at as branch_updated_at,

                -- Task statistics
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'blocked' THEN t.id END) as blocked_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'todo' THEN t.id END) as todo_tasks,

                -- Progress calculations
                CASE
                    WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                    ELSE ROUND(100.0 * COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) / COUNT(DISTINCT t.id))
                END as progress_percentage,

                -- Subtask statistics
                COUNT(DISTINCT s.id) as total_subtasks,
                COUNT(DISTINCT CASE WHEN s.status = 'done' THEN s.id END) as completed_subtasks,

                -- Priority distribution
                COUNT(DISTINCT CASE WHEN t.priority = 'critical' THEN t.id END) as critical_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'high' THEN t.id END) as high_priority_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'medium' THEN t.id END) as medium_priority_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'low' THEN t.id END) as low_priority_tasks,

                -- Time metrics
                MAX(t.updated_at) as last_task_activity,
                MIN(t.created_at) as first_task_created,

                -- Aggregate effort estimation
                GROUP_CONCAT(DISTINCT t.estimated_effort) as effort_estimates,

                -- Agent assignments
                COUNT(DISTINCT ta.agent_id) as assigned_agents_count,
                GROUP_CONCAT(DISTINCT CAST(ta.agent_id AS TEXT)) as assigned_agent_ids,

                -- Labels aggregation
                COUNT(DISTINCT l.name) as unique_labels_count,
                GROUP_CONCAT(DISTINCT l.name) as all_labels

            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            LEFT JOIN task_assignees ta ON ta.task_id = t.id
            LEFT JOIN task_labels tl ON tl.task_id = t.id
            LEFT JOIN labels l ON l.id = tl.label_id
            GROUP BY
                b.id, b.project_id, b.name, b.description, b.status,
                b.priority, b.assigned_agent_id, b.user_id,
                b.created_at, b.updated_at
        """))

        # Create indexes for better performance
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_branch_mv ON tasks(git_branch_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_task_mv ON subtasks(task_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_assignees_mv ON task_assignees(task_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_labels_mv ON task_labels(task_id);"))

        logger.info("SQLite view 'branch_summaries_mv' created successfully")

    @staticmethod
    async def down(engine: AsyncEngine) -> None:
        """Remove materialized view and related infrastructure"""
        async with engine.begin() as conn:
            # Check database type
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            is_postgres = "PostgreSQL" in str(db_version) if db_version else False

            if is_postgres:
                # Drop triggers
                for table in ['tasks', 'subtasks', 'task_assignees', 'task_labels']:
                    await conn.execute(text(f"DROP TRIGGER IF EXISTS refresh_branch_summaries_on_{table} ON {table};"))

                # Drop functions
                await conn.execute(text("DROP FUNCTION IF EXISTS trigger_refresh_branch_summaries() CASCADE;"))
                await conn.execute(text("DROP FUNCTION IF EXISTS refresh_branch_summaries() CASCADE;"))

                # Drop materialized view
                await conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS branch_summaries_mv CASCADE;"))
            else:
                # Drop SQLite view
                await conn.execute(text("DROP VIEW IF EXISTS branch_summaries_mv;"))

            logger.info("Materialized view 'branch_summaries_mv' removed successfully")


async def migrate_up(engine: AsyncEngine) -> None:
    """Run the migration"""
    migration = BranchSummariesMaterializedViewMigration()
    await migration.up(engine)


async def migrate_down(engine: AsyncEngine) -> None:
    """Rollback the migration"""
    migration = BranchSummariesMaterializedViewMigration()
    await migration.down(engine)


if __name__ == "__main__":
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    import os

    # Get database URL from environment
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/agenthub.db")

    # Convert to async URL if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    elif DATABASE_URL.startswith("sqlite:///"):
        DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

    async def run_migration():
        engine = create_async_engine(DATABASE_URL, echo=True)
        try:
            await migrate_up(engine)
            print("Migration completed successfully!")
        finally:
            await engine.dispose()

    asyncio.run(run_migration())