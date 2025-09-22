#!/usr/bin/env python3
"""
Migration: Add Materialized View for Project Summaries
Phase 1: Database Optimization for API Performance

This migration creates a materialized view to optimize project summary queries,
providing aggregated data across all branches and tasks in a project.
"""

import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class ProjectSummariesMaterializedViewMigration:
    """Migration to create and manage project_summaries_mv materialized view"""

    @staticmethod
    async def up(engine: AsyncEngine) -> None:
        """Create materialized view for project summaries"""
        async with engine.begin() as conn:
            # Check if we're using PostgreSQL
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            is_postgres = "PostgreSQL" in str(db_version)

            if is_postgres:
                await ProjectSummariesMaterializedViewMigration._create_postgres_mv(conn)
            else:
                await ProjectSummariesMaterializedViewMigration._create_sqlite_view(conn)

    @staticmethod
    async def _create_postgres_mv(conn: Any) -> None:
        """Create PostgreSQL materialized view for project summaries"""

        # Drop existing materialized view if exists
        await conn.execute(text("""
            DROP MATERIALIZED VIEW IF EXISTS project_summaries_mv CASCADE;
        """))

        # Create the materialized view
        await conn.execute(text("""
            CREATE MATERIALIZED VIEW project_summaries_mv AS
            SELECT
                p.id as project_id,
                p.name as project_name,
                p.description as project_description,
                p.status as project_status,
                p.user_id,
                p.created_at as project_created_at,
                p.updated_at as project_updated_at,

                -- Branch statistics
                COUNT(DISTINCT b.id) as total_branches,
                COUNT(DISTINCT b.id) FILTER (WHERE b.status = 'active') as active_branches,
                COUNT(DISTINCT b.id) FILTER (WHERE b.status = 'archived') as archived_branches,

                -- Task statistics across all branches
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') as completed_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'in_progress') as in_progress_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'blocked') as blocked_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'todo') as todo_tasks,

                -- Overall project progress
                CASE
                    WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                    ELSE ROUND(100.0 * COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') / COUNT(DISTINCT t.id))
                END as overall_progress_percentage,

                -- Subtask statistics across project
                COUNT(DISTINCT s.id) as total_subtasks,
                COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'done') as completed_subtasks,

                -- Priority distribution across project
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'critical') as critical_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'high') as high_priority_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'medium') as medium_priority_tasks,
                COUNT(DISTINCT t.id) FILTER (WHERE t.priority = 'low') as low_priority_tasks,

                -- Time metrics
                MAX(t.updated_at) as last_activity,
                MIN(t.created_at) as first_task_created,
                MAX(t.created_at) as last_task_created,

                -- Agent statistics
                COUNT(DISTINCT ta.agent_id) as unique_agents_assigned,
                STRING_AGG(DISTINCT ta.agent_id, ', ') as all_agent_ids,

                -- Label statistics
                COUNT(DISTINCT tl.label) as unique_labels_count,
                STRING_AGG(DISTINCT tl.label, ', ' ORDER BY tl.label) as all_labels,

                -- Branch summary aggregation
                STRING_AGG(DISTINCT b.name || ' (' ||
                    COALESCE(
                        (SELECT COUNT(*) FROM tasks WHERE git_branch_id = b.id)::text, '0'
                    ) || ' tasks)', ', ' ORDER BY b.name) as branch_summary,

                -- Active work indicators
                COUNT(DISTINCT t.id) FILTER (WHERE t.updated_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as tasks_updated_24h,
                COUNT(DISTINCT t.id) FILTER (WHERE t.updated_at > CURRENT_TIMESTAMP - INTERVAL '7 days') as tasks_updated_7d,

                -- Effort metrics
                COUNT(DISTINCT t.id) FILTER (WHERE t.estimated_effort IS NOT NULL) as tasks_with_estimates,
                STRING_AGG(DISTINCT t.estimated_effort, ', ' ORDER BY t.estimated_effort) as effort_distribution

            FROM projects p
            LEFT JOIN project_git_branchs b ON b.project_id = p.id
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            LEFT JOIN task_assignees ta ON ta.task_id = t.id
            LEFT JOIN task_labels tl ON tl.task_id = t.id
            GROUP BY
                p.id, p.name, p.description, p.status, p.user_id,
                p.created_at, p.updated_at
        """))

        # Create indexes for performance
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_project_summaries_user
            ON project_summaries_mv(user_id);
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_project_summaries_status
            ON project_summaries_mv(project_status);
        """))

        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_project_summaries_id
            ON project_summaries_mv(project_id);
        """))

        # Create refresh function
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION refresh_project_summaries()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW project_summaries_mv;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # Initial refresh
        await conn.execute(text("REFRESH MATERIALIZED VIEW project_summaries_mv;"))

        logger.info("PostgreSQL materialized view 'project_summaries_mv' created successfully")

    @staticmethod
    async def _create_sqlite_view(conn: Any) -> None:
        """Create SQLite view for project summaries"""

        # Drop existing view if exists
        await conn.execute(text("DROP VIEW IF EXISTS project_summaries_mv;"))

        # Create regular view for SQLite
        await conn.execute(text("""
            CREATE VIEW project_summaries_mv AS
            SELECT
                p.id as project_id,
                p.name as project_name,
                p.description as project_description,
                p.status as project_status,
                p.user_id,
                p.created_at as project_created_at,
                p.updated_at as project_updated_at,

                -- Branch statistics
                COUNT(DISTINCT b.id) as total_branches,
                COUNT(DISTINCT CASE WHEN b.status = 'active' THEN b.id END) as active_branches,
                COUNT(DISTINCT CASE WHEN b.status = 'archived' THEN b.id END) as archived_branches,

                -- Task statistics across all branches
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'blocked' THEN t.id END) as blocked_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'todo' THEN t.id END) as todo_tasks,

                -- Overall project progress
                CASE
                    WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                    ELSE ROUND(100.0 * COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) / COUNT(DISTINCT t.id))
                END as overall_progress_percentage,

                -- Subtask statistics across project
                COUNT(DISTINCT s.id) as total_subtasks,
                COUNT(DISTINCT CASE WHEN s.status = 'done' THEN s.id END) as completed_subtasks,

                -- Priority distribution across project
                COUNT(DISTINCT CASE WHEN t.priority = 'critical' THEN t.id END) as critical_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'high' THEN t.id END) as high_priority_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'medium' THEN t.id END) as medium_priority_tasks,
                COUNT(DISTINCT CASE WHEN t.priority = 'low' THEN t.id END) as low_priority_tasks,

                -- Time metrics
                MAX(t.updated_at) as last_activity,
                MIN(t.created_at) as first_task_created,
                MAX(t.created_at) as last_task_created,

                -- Agent statistics
                COUNT(DISTINCT ta.agent_id) as unique_agents_assigned,
                GROUP_CONCAT(DISTINCT ta.agent_id) as all_agent_ids,

                -- Label statistics
                COUNT(DISTINCT tl.label) as unique_labels_count,
                GROUP_CONCAT(DISTINCT tl.label) as all_labels,

                -- Branch summary aggregation
                GROUP_CONCAT(DISTINCT b.name || ' (' ||
                    COALESCE(
                        (SELECT COUNT(*) FROM tasks WHERE git_branch_id = b.id), 0
                    ) || ' tasks)') as branch_summary,

                -- Active work indicators (SQLite doesn't have INTERVAL, using datetime)
                COUNT(DISTINCT CASE
                    WHEN datetime(t.updated_at) > datetime('now', '-1 day')
                    THEN t.id END) as tasks_updated_24h,
                COUNT(DISTINCT CASE
                    WHEN datetime(t.updated_at) > datetime('now', '-7 days')
                    THEN t.id END) as tasks_updated_7d,

                -- Effort metrics
                COUNT(DISTINCT CASE WHEN t.estimated_effort IS NOT NULL THEN t.id END) as tasks_with_estimates,
                GROUP_CONCAT(DISTINCT t.estimated_effort) as effort_distribution

            FROM projects p
            LEFT JOIN project_git_branchs b ON b.project_id = p.id
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            LEFT JOIN task_assignees ta ON ta.task_id = t.id
            LEFT JOIN task_labels tl ON tl.task_id = t.id
            GROUP BY
                p.id, p.name, p.description, p.status, p.user_id,
                p.created_at, p.updated_at
        """))

        logger.info("SQLite view 'project_summaries_mv' created successfully")

    @staticmethod
    async def down(engine: AsyncEngine) -> None:
        """Remove materialized view"""
        async with engine.begin() as conn:
            # Check database type
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            is_postgres = "PostgreSQL" in str(db_version) if db_version else False

            if is_postgres:
                # Drop function
                await conn.execute(text("DROP FUNCTION IF EXISTS refresh_project_summaries() CASCADE;"))
                # Drop materialized view
                await conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS project_summaries_mv CASCADE;"))
            else:
                # Drop SQLite view
                await conn.execute(text("DROP VIEW IF EXISTS project_summaries_mv;"))

            logger.info("Materialized view 'project_summaries_mv' removed successfully")


async def migrate_up(engine: AsyncEngine) -> None:
    """Run the migration"""
    migration = ProjectSummariesMaterializedViewMigration()
    await migration.up(engine)


async def migrate_down(engine: AsyncEngine) -> None:
    """Rollback the migration"""
    migration = ProjectSummariesMaterializedViewMigration()
    await migration.down(engine)


if __name__ == "__main__":
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    import os

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/agenthub.db")

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