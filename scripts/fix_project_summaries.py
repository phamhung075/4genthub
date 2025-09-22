#!/usr/bin/env python3
"""
Quick script to create the missing project_summaries_mv materialized view
"""

import sys
import os
import asyncio
import asyncpg
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from fastmcp.settings import Settings

async def create_project_summaries_view():
    """Create the project_summaries_mv materialized view"""

    # Load settings
    settings = Settings()

    # Connect to database using environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env.dev')

    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=int(os.getenv('DATABASE_PORT', 5432)),
        user=os.getenv('DATABASE_USER', 'agenthub_user'),
        password=os.getenv('DATABASE_PASSWORD', 'agenthub_password'),
        database=os.getenv('DATABASE_NAME', 'agenthub')
    )

    try:
        db_name = os.getenv('DATABASE_NAME', 'postgresdb')
        print(f"✅ Connected to database: {db_name}")

        # Check if materialized view already exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_matviews
                WHERE matviewname = 'project_summaries_mv'
            )
        """)

        if exists:
            print("✅ project_summaries_mv already exists!")
            return

        print("🔧 Creating project_summaries_mv materialized view...")

        # Create the materialized view
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
                FROM git_branches
                GROUP BY project_id
            ) branch_stats ON p.id = branch_stats.project_id
            LEFT JOIN (
                SELECT
                    gb.project_id,
                    COUNT(t.id) as total_tasks,
                    COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks
                FROM git_branches gb
                LEFT JOIN tasks t ON gb.id = t.git_branch_id
                GROUP BY gb.project_id
            ) task_stats ON p.id = task_stats.project_id;
        """)

        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX idx_project_summaries_mv_project_id
            ON project_summaries_mv (project_id);
        """)

        # Add to applied migrations table
        await conn.execute("""
            INSERT INTO applied_migrations (migration_name, applied_at)
            VALUES ('add_project_summaries_materialized_view', NOW())
            ON CONFLICT (migration_name) DO NOTHING;
        """)

        print("✅ project_summaries_mv created successfully!")

        # Test the view
        result = await conn.fetchrow("SELECT COUNT(*) as count FROM project_summaries_mv")
        print(f"✅ View contains {result['count']} project summaries")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_project_summaries_view())