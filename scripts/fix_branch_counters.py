#!/usr/bin/env python3
"""
Branch Counter Data Repair Script

This script recalculates and fixes the task_count and completed_task_count fields
in the project_git_branchs table by counting actual tasks in the database.

Usage:
    python scripts/fix_branch_counters.py [--dry-run]

Options:
    --dry-run    Show what would be changed without making actual changes
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch, Task
from fastmcp.task_management.infrastructure.database.database_config import get_session

def main():
    parser = argparse.ArgumentParser(description='Fix branch task counters')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show changes without applying them')
    args = parser.parse_args()

    # Use the existing session factory
    session = get_session()

    print("🔧 Branch Counter Repair Script")
    print("=" * 50)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  LIVE MODE - Changes will be applied")

    print()

    try:
        # Get all branches
        branches = session.query(ProjectGitBranch).all()

        print(f"📊 Found {len(branches)} branches to analyze")
        print()

        fixed_count = 0
        total_task_diff = 0
        total_completed_diff = 0

        for branch in branches:
            # Count actual tasks for this branch
            actual_task_count = session.query(func.count(Task.id)).filter(
                Task.git_branch_id == branch.id
            ).scalar() or 0

            # Count actual completed tasks
            actual_completed_count = session.query(func.count(Task.id)).filter(
                Task.git_branch_id == branch.id,
                Task.status == 'done'
            ).scalar() or 0

            # Get current stored counts
            stored_task_count = branch.task_count or 0
            stored_completed_count = branch.completed_task_count or 0

            # Check if fix is needed
            task_diff = actual_task_count - stored_task_count
            completed_diff = actual_completed_count - stored_completed_count

            if task_diff != 0 or completed_diff != 0:
                fixed_count += 1
                total_task_diff += abs(task_diff)
                total_completed_diff += abs(completed_diff)

                print(f"🔧 Branch: {branch.name[:30]:<30} (ID: {branch.id[:8]}...)")
                print(f"   Task count:      {stored_task_count:>3} → {actual_task_count:>3} ({task_diff:+d})")
                print(f"   Completed count: {stored_completed_count:>3} → {actual_completed_count:>3} ({completed_diff:+d})")

                if not args.dry_run:
                    # Apply the fix
                    branch.task_count = actual_task_count
                    branch.completed_task_count = actual_completed_count
                    branch.updated_at = datetime.now(timezone.utc)
                    print(f"   ✅ Fixed!")
                else:
                    print(f"   🔍 Would fix (dry run)")
                print()

        if not args.dry_run and fixed_count > 0:
            # Commit all changes
            session.commit()
            print(f"💾 Committed {fixed_count} branch fixes to database")
        elif args.dry_run and fixed_count > 0:
            print(f"🔍 DRY RUN: Would fix {fixed_count} branches")
        else:
            print("✅ All branch counters are already correct!")

        print()
        print("📈 Summary:")
        print(f"   Branches analyzed: {len(branches)}")
        print(f"   Branches needing fixes: {fixed_count}")
        print(f"   Total task count discrepancy: {total_task_diff}")
        print(f"   Total completed count discrepancy: {total_completed_diff}")

        if not args.dry_run and fixed_count > 0:
            print()
            print("🎉 Branch counter repair completed successfully!")
        elif args.dry_run and fixed_count > 0:
            print()
            print("💡 Run without --dry-run to apply these fixes")

    finally:
        session.close()

if __name__ == "__main__":
    main()