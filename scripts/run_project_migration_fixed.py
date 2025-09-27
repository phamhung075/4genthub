#!/usr/bin/env python3
"""
Run the fixed project summaries migration directly
"""

import sys
import os
import asyncio
import asyncpg
from pathlib import Path

# Load environment
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env.dev')

async def create_project_summaries_view():
    """Create the project_summaries_mv materialized view"""

    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=int(os.getenv('DATABASE_PORT', 5432)),
        user=os.getenv('DATABASE_USER', 'agenthub_user'),
        password=os.getenv('DATABASE_PASSWORD', 'agenthub_password'),
        database=os.getenv('DATABASE_NAME', 'agenthub')
    )

    try:
        print(f"✅ Connected to database")

        # Drop existing materialized view if exists
        await conn.execute("DROP MATERIALIZED VIEW IF EXISTS project_summaries_mv CASCADE;")
        print("Dropped existing view if it existed")

        # Create the materialized view (fixed version without CONCURRENTLY)
        await conn.execute("""
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
                STRING_AGG(DISTINCT ta.agent_id::text, ', ') as all_agent_ids,

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
        """)
        print("Created materialized view")

        # Create indexes (WITHOUT CONCURRENTLY - fixed version)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_summaries_user
            ON project_summaries_mv(user_id);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_summaries_status
            ON project_summaries_mv(project_status);
        """)

        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_project_summaries_id
            ON project_summaries_mv(project_id);
        """)
        print("Created indexes")

        # Create refresh function (also without CONCURRENTLY)
        await conn.execute("""
            CREATE OR REPLACE FUNCTION refresh_project_summaries()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW project_summaries_mv;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("Created refresh function")

        # Initial refresh
        await conn.execute("REFRESH MATERIALIZED VIEW project_summaries_mv;")
        print("Performed initial refresh")

        # Mark migration as applied
        await conn.execute("""
            INSERT INTO applied_migrations (migration_name, applied_at, success)
            VALUES ('project_summaries_mv', NOW(), true)
            ON CONFLICT (migration_name) DO UPDATE SET success = true, applied_at = NOW();
        """)
        print("Marked migration as applied")

        # Test the view
        result = await conn.fetchrow("SELECT COUNT(*) as count FROM project_summaries_mv")
        print(f"✅ project_summaries_mv created successfully! Contains {result['count']} project summaries")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_project_summaries_view())