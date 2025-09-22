#!/usr/bin/env python3
"""
Create a simplified project_summaries_mv materialized view
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

        # Create a SIMPLIFIED materialized view that should work
        await conn.execute("""
            CREATE MATERIALIZED VIEW project_summaries_mv AS
            SELECT
                p.id as project_id,
                p.name as project_name,
                p.description as project_description,
                COALESCE(branch_stats.total_branches, 0) as total_branches,
                COALESCE(branch_stats.active_branches, 0) as active_branches,
                COALESCE(task_stats.total_tasks, 0) as total_tasks,
                COALESCE(task_stats.completed_tasks, 0) as completed_tasks,
                CASE
                    WHEN COALESCE(task_stats.total_tasks, 0) = 0 THEN 0
                    ELSE ROUND((COALESCE(task_stats.completed_tasks, 0)::numeric / task_stats.total_tasks) * 100, 2)
                END as overall_progress_percentage
            FROM projects p
            LEFT JOIN (
                SELECT
                    project_id,
                    COUNT(*) as total_branches,
                    COUNT(CASE WHEN status != 'archived' THEN 1 END) as active_branches
                FROM project_git_branchs
                GROUP BY project_id
            ) branch_stats ON p.id = branch_stats.project_id
            LEFT JOIN (
                SELECT
                    gb.project_id,
                    COUNT(t.id) as total_tasks,
                    COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks
                FROM project_git_branchs gb
                LEFT JOIN tasks t ON gb.id = t.git_branch_id
                GROUP BY gb.project_id
            ) task_stats ON p.id = task_stats.project_id
        """)
        print("Created simplified materialized view")

        # Create index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_summaries_mv_project_id
            ON project_summaries_mv (project_id);
        """)
        print("Created index")

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

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_project_summaries_view())