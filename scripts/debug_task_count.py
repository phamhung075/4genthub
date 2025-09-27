#!/usr/bin/env python3
"""
Debug Task Count Discrepancy

This script checks the actual task count vs materialized view to identify
why frontend shows 39 tasks when database should have 11.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def debug_task_counts():
    """Check actual vs materialized view task counts"""

    # Use PostgreSQL database from .env.dev configuration
    DATABASE_URL = "postgresql+asyncpg://postgres:P02tqbj016p9@localhost:5432/postgresdb"

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            print("🔍 Debugging Task Count Discrepancy")
            print("=" * 50)

            # 1. Check total task count in tasks table
            result = await conn.execute(text("SELECT COUNT(*) FROM tasks"))
            total_tasks = result.scalar()
            print(f"📊 Total tasks in database: {total_tasks}")

            # 2. Check task count by branch from tasks table directly
            result = await conn.execute(text("""
                SELECT
                    b.name as branch_name,
                    b.id as branch_id,
                    COUNT(t.id) as task_count
                FROM project_git_branchs b
                LEFT JOIN tasks t ON t.git_branch_id = b.id
                GROUP BY b.id, b.name
                ORDER BY task_count DESC
            """))

            print("\n📋 Task count by branch (direct query):")
            direct_counts = {}
            for row in result:
                branch_name, branch_id, count = row
                direct_counts[branch_id] = count
                print(f"  - {branch_name}: {count} tasks")

            # 3. Check if materialized view exists and get counts from it
            try:
                result = await conn.execute(text("""
                    SELECT
                        branch_name,
                        branch_id,
                        total_tasks
                    FROM branch_summaries_mv
                    ORDER BY total_tasks DESC
                """))

                print("\n📊 Task count from materialized view:")
                mv_counts = {}
                for row in result:
                    branch_name, branch_id, count = row
                    mv_counts[branch_id] = count
                    print(f"  - {branch_name}: {count} tasks")

                # 4. Compare direct vs materialized view
                print("\n⚖️ Comparison (Direct vs Materialized View):")
                all_branches = set(direct_counts.keys()) | set(mv_counts.keys())
                discrepancies = 0

                for branch_id in all_branches:
                    direct = direct_counts.get(branch_id, 0)
                    mv = mv_counts.get(branch_id, 0)
                    if direct != mv:
                        discrepancies += 1
                        status = "❌ MISMATCH"
                    else:
                        status = "✅ MATCH"
                    print(f"  Branch {branch_id}: Direct={direct}, MV={mv} {status}")

                if discrepancies > 0:
                    print(f"\n🚨 Found {discrepancies} discrepancies!")
                    print("💡 Solution: Refresh materialized view")
                else:
                    print("\n✅ No discrepancies found in materialized view")

            except Exception as e:
                print(f"\n❌ Materialized view error: {e}")
                print("💡 Materialized view may not exist or need to be created")

            # 5. Check for deleted/orphaned tasks
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM tasks t
                LEFT JOIN project_git_branchs b ON t.git_branch_id = b.id
                WHERE b.id IS NULL
            """))
            orphaned_tasks = result.scalar()
            if orphaned_tasks > 0:
                print(f"\n⚠️ Found {orphaned_tasks} orphaned tasks (referencing deleted branches)")

            # 6. Check database type
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            print(f"\n🗄️ Database: {db_version}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(debug_task_counts())