"""
Automatic Database Migration Runner
Runs all necessary migrations on server startup
"""

import logging
import os
from typing import List, Dict, Any
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoMigrationRunner:
    """Automatically runs database migrations on server startup"""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.migrations_table = "applied_migrations"

    async def initialize(self):
        """Initialize migration tracking table and run all pending migrations"""
        try:
            # Create migrations tracking table if it doesn't exist
            await self._create_migrations_table()

            # Run all pending migrations
            await self.run_pending_migrations()

            logger.info("Database migration check completed")
        except Exception as e:
            logger.error(f"Migration initialization failed: {e}")
            # Don't fail server startup - log and continue

    async def _create_migrations_table(self):
        """Create table to track applied migrations"""
        async with self.engine.begin() as conn:
            # Check database type first
            is_postgres = await self._is_postgresql(conn)

            # Check if table exists with database-specific query
            if is_postgres:
                # PostgreSQL check
                result = await conn.execute(text("""
                    SELECT tablename FROM pg_tables
                    WHERE tablename=:table_name
                """), {"table_name": self.migrations_table})
            else:
                # SQLite check
                result = await conn.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=:table_name
                """), {"table_name": self.migrations_table})

            if not result.first():
                # Create migrations table with database-specific syntax
                is_postgres = await self._is_postgresql(conn)

                if is_postgres:
                    # PostgreSQL syntax
                    await conn.execute(text(f"""
                        CREATE TABLE {self.migrations_table} (
                            id SERIAL PRIMARY KEY,
                            migration_name VARCHAR(255) UNIQUE NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            success BOOLEAN DEFAULT TRUE,
                            error_message TEXT
                        )
                    """))
                else:
                    # SQLite syntax
                    await conn.execute(text(f"""
                        CREATE TABLE {self.migrations_table} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            migration_name VARCHAR(255) UNIQUE NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            success BOOLEAN DEFAULT TRUE,
                            error_message TEXT
                        )
                    """))

                logger.info(f"Created migrations tracking table: {self.migrations_table}")

    async def _is_migration_applied(self, migration_name: str) -> bool:
        """Check if a migration has already been applied"""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(f"""
                SELECT COUNT(*) FROM {self.migrations_table}
                WHERE migration_name = :name AND success = TRUE
            """), {"name": migration_name})
            count = result.scalar()
            return count > 0

    async def _record_migration(self, migration_name: str, success: bool = True, error: str = None):
        """Record that a migration has been applied"""
        async with self.engine.begin() as conn:
            await conn.execute(text(f"""
                INSERT INTO {self.migrations_table}
                (migration_name, applied_at, success, error_message)
                VALUES (:name, :timestamp, :success, :error)
            """), {
                "name": migration_name,
                "timestamp": datetime.utcnow(),
                "success": success,
                "error": error
            })

    async def run_pending_migrations(self):
        """Run all migrations that haven't been applied yet"""

        # Define migrations in order
        migrations = [
            ("branch_summaries_mv", self._create_branch_summaries_view),
            ("project_summaries_mv", self._create_project_summaries_view),
            ("websocket_indexes", self._create_websocket_indexes),
            ("cascade_indexes", self._create_cascade_indexes)
        ]

        for migration_name, migration_func in migrations:
            try:
                if not await self._is_migration_applied(migration_name):
                    logger.info(f"Running migration: {migration_name}")
                    await migration_func()
                    await self._record_migration(migration_name, success=True)
                    logger.info(f"Successfully applied migration: {migration_name}")
                else:
                    logger.debug(f"Migration already applied: {migration_name}")
            except Exception as e:
                logger.error(f"Failed to apply migration {migration_name}: {e}")
                await self._record_migration(migration_name, success=False, error=str(e))

    async def _create_branch_summaries_view(self):
        """Create branch summaries materialized view or regular view"""
        async with self.engine.begin() as conn:
            # Detect database type
            is_postgres = await self._is_postgresql(conn)

            if is_postgres:
                # PostgreSQL materialized view
                await conn.execute(text("""
                    DROP MATERIALIZED VIEW IF EXISTS branch_summaries_mv CASCADE;
                """))

                await conn.execute(text("""
                    CREATE MATERIALIZED VIEW branch_summaries_mv AS
                    SELECT
                        b.id as branch_id,
                        b.project_id,
                        b.name as branch_name,
                        b.description as branch_description,
                        b.status as branch_status,
                        b.priority as branch_priority,
                        COUNT(DISTINCT t.id) as total_tasks,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') as completed_tasks,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'in_progress') as in_progress_tasks,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'blocked') as blocked_tasks,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'todo') as todo_tasks,
                        CASE
                            WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                            ELSE ROUND(100.0 * COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') / COUNT(DISTINCT t.id))
                        END as progress_percentage,
                        COUNT(DISTINCT s.id) as total_subtasks,
                        COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'done') as completed_subtasks,
                        MAX(t.updated_at) as last_task_activity,
                        MIN(t.created_at) as first_task_created
                    FROM project_git_branchs b
                    LEFT JOIN tasks t ON t.git_branch_id = b.id
                    LEFT JOIN subtasks s ON s.task_id = t.id
                    GROUP BY b.id, b.project_id, b.name, b.description, b.status, b.priority
                """))

                # Create indexes
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_branch_summaries_project
                    ON branch_summaries_mv(project_id);
                """))

                # Initial refresh
                await conn.execute(text("REFRESH MATERIALIZED VIEW branch_summaries_mv;"))

                # Create auto-refresh function
                await conn.execute(text("""
                    CREATE OR REPLACE FUNCTION refresh_branch_summaries()
                    RETURNS void AS $$
                    BEGIN
                        REFRESH MATERIALIZED VIEW CONCURRENTLY branch_summaries_mv;
                    END;
                    $$ LANGUAGE plpgsql;
                """))

            else:
                # SQLite regular view
                await conn.execute(text("DROP VIEW IF EXISTS branch_summaries_mv;"))

                await conn.execute(text("""
                    CREATE VIEW branch_summaries_mv AS
                    SELECT
                        b.id as branch_id,
                        b.project_id,
                        b.name as branch_name,
                        b.description as branch_description,
                        b.status as branch_status,
                        b.priority as branch_priority,
                        COUNT(DISTINCT t.id) as total_tasks,
                        COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
                        COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
                        COUNT(DISTINCT CASE WHEN t.status = 'blocked' THEN t.id END) as blocked_tasks,
                        COUNT(DISTINCT CASE WHEN t.status = 'todo' THEN t.id END) as todo_tasks,
                        CASE
                            WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                            ELSE ROUND(100.0 * COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) / COUNT(DISTINCT t.id))
                        END as progress_percentage,
                        COUNT(DISTINCT s.id) as total_subtasks,
                        COUNT(DISTINCT CASE WHEN s.status = 'done' THEN s.id END) as completed_subtasks,
                        MAX(t.updated_at) as last_task_activity,
                        MIN(t.created_at) as first_task_created
                    FROM project_git_branchs b
                    LEFT JOIN tasks t ON t.git_branch_id = b.id
                    LEFT JOIN subtasks s ON s.task_id = t.id
                    GROUP BY b.id, b.project_id, b.name, b.description, b.status, b.priority
                """))

                # Create indexes for better performance
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_branch_mv ON tasks(git_branch_id);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subtasks_task_mv ON subtasks(task_id);"))

    async def _create_project_summaries_view(self):
        """Create comprehensive project summaries view with all required columns"""
        async with self.engine.begin() as conn:
            is_postgres = await self._is_postgresql(conn)

            if is_postgres:
                # PostgreSQL materialized view with comprehensive schema
                await conn.execute(text("""
                    DROP MATERIALIZED VIEW IF EXISTS project_summaries_mv CASCADE;
                """))

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

                        -- Overall project progress (named to match expected schema)
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
                        STRING_AGG(DISTINCT ta.agent_id::text, ', ') as all_agent_ids,

                        -- Label statistics
                        COUNT(DISTINCT l.name) as unique_labels_count,
                        STRING_AGG(DISTINCT l.name, ', ') as all_labels,

                        -- Branch summary aggregation
                        STRING_AGG(DISTINCT b.name || ' (' ||
                            COALESCE(
                                (SELECT COUNT(*) FROM tasks WHERE git_branch_id = b.id)::text, '0'
                            ) || ' tasks)', ', ') as branch_summary,

                        -- Active work indicators
                        COUNT(DISTINCT t.id) FILTER (WHERE t.updated_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as tasks_updated_24h,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.updated_at > CURRENT_TIMESTAMP - INTERVAL '7 days') as tasks_updated_7d,

                        -- Effort metrics
                        COUNT(DISTINCT t.id) FILTER (WHERE t.estimated_effort IS NOT NULL) as tasks_with_estimates,
                        STRING_AGG(DISTINCT t.estimated_effort, ', ') as effort_distribution

                    FROM projects p
                    LEFT JOIN project_git_branchs b ON b.project_id = p.id
                    LEFT JOIN tasks t ON t.git_branch_id = b.id
                    LEFT JOIN subtasks s ON s.task_id = t.id
                    LEFT JOIN task_assignees ta ON ta.task_id = t.id
                    LEFT JOIN task_labels tl ON tl.task_id = t.id
                    LEFT JOIN labels l ON l.id = tl.label_id
                    GROUP BY
                        p.id, p.name, p.description, p.status, p.user_id,
                        p.created_at, p.updated_at
                """))

                # Create indexes for performance
                await conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_summaries_user
                    ON project_summaries_mv(user_id);
                """))

                await conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_summaries_status
                    ON project_summaries_mv(project_status);
                """))

                await conn.execute(text("""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_project_summaries_id
                    ON project_summaries_mv(project_id);
                """))

                # Create refresh function
                await conn.execute(text("""
                    CREATE OR REPLACE FUNCTION refresh_project_summaries()
                    RETURNS void AS $$
                    BEGIN
                        REFRESH MATERIALIZED VIEW CONCURRENTLY project_summaries_mv;
                    END;
                    $$ LANGUAGE plpgsql;
                """))

                # Initial refresh
                await conn.execute(text("REFRESH MATERIALIZED VIEW project_summaries_mv;"))

            else:
                # SQLite view with comprehensive schema
                await conn.execute(text("DROP VIEW IF EXISTS project_summaries_mv;"))

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

                        -- Overall project progress (named to match expected schema)
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
                        COUNT(DISTINCT l.name) as unique_labels_count,
                        GROUP_CONCAT(DISTINCT l.name) as all_labels,

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
                    LEFT JOIN labels l ON l.id = tl.label_id
                    GROUP BY
                        p.id, p.name, p.description, p.status, p.user_id,
                        p.created_at, p.updated_at
                """))

    async def _create_websocket_indexes(self):
        """Create indexes for WebSocket performance"""
        async with self.engine.begin() as conn:
            # Indexes for real-time updates
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_subtasks_updated_at ON subtasks(updated_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_branches_updated_at ON project_git_branchs(updated_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);"
            ]

            for index_sql in indexes:
                await conn.execute(text(index_sql))

    async def _create_cascade_indexes(self):
        """Create indexes for cascade data fetching"""
        async with self.engine.begin() as conn:
            # Indexes for efficient cascade queries
            cascade_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(git_branch_id, project_id);",
                "CREATE INDEX IF NOT EXISTS idx_subtasks_parent ON subtasks(task_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_task_dependencies ON task_dependencies(task_id, depends_on_task_id);",
                "CREATE INDEX IF NOT EXISTS idx_task_assignees_compound ON task_assignees(task_id, agent_id);",
                "CREATE INDEX IF NOT EXISTS idx_task_labels_compound ON task_labels(task_id, label);"
            ]

            for index_sql in cascade_indexes:
                try:
                    await conn.execute(text(index_sql))
                except Exception as e:
                    # Index might already exist with different name
                    logger.debug(f"Index creation skipped (may already exist): {e}")

    async def _is_postgresql(self, conn) -> bool:
        """Check if we're using PostgreSQL"""
        try:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            return "PostgreSQL" in str(version)
        except:
            return False

    async def refresh_materialized_views(self):
        """Manually refresh all materialized views (PostgreSQL only)"""
        async with self.engine.begin() as conn:
            if await self._is_postgresql(conn):
                try:
                    await conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY branch_summaries_mv;"))
                    await conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY project_summaries_mv;"))
                    logger.info("Materialized views refreshed successfully")
                except Exception as e:
                    logger.error(f"Failed to refresh materialized views: {e}")


# Singleton instance
_migration_runner = None

async def get_migration_runner(engine: AsyncEngine) -> AutoMigrationRunner:
    """Get or create the migration runner singleton"""
    global _migration_runner
    if _migration_runner is None:
        _migration_runner = AutoMigrationRunner(engine)
    return _migration_runner


async def initialize_database(engine: AsyncEngine):
    """Initialize database with all necessary migrations - call this on server startup"""
    runner = await get_migration_runner(engine)
    await runner.initialize()
    logger.info("Database initialization completed")