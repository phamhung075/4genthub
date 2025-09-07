#!/usr/bin/env python3
"""
Utility script to fix task_count synchronization issues in git branches.

This script recalculates the actual task count for each branch based on 
the tasks in the database and updates the task_count field accordingly.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_task_counts():
    """Fix task_count synchronization for all branches"""
    # Set database mode from environment or default to supabase
    db_mode = os.environ.get('DATABASE_MODE', 'supabase')
    os.environ['DATABASE_MODE'] = db_mode
    logger.info(f"Using database mode: {db_mode}")
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session as get_db_session
        from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch, Task
        
        with get_db_session() as session:
            # Get all branches
            branches = session.query(ProjectGitBranch).all()
            logger.info(f"Found {len(branches)} branches to check")
            
            fixed_count = 0
            for branch in branches:
                # Count actual tasks in this branch
                actual_task_count = session.query(Task).filter(
                    Task.git_branch_id == branch.id
                ).count()
                
                # Check if task_count needs updating
                if branch.task_count != actual_task_count:
                    logger.warning(
                        f"Branch '{branch.name}' (id={branch.id}): "
                        f"task_count={branch.task_count} but actual={actual_task_count}"
                    )
                    
                    # Update task_count
                    branch.task_count = actual_task_count
                    fixed_count += 1
                    logger.info(f"  -> Fixed: task_count set to {actual_task_count}")
                else:
                    logger.debug(
                        f"Branch '{branch.name}' (id={branch.id}): "
                        f"task_count={branch.task_count} is correct"
                    )
            
            if fixed_count > 0:
                session.commit()
                logger.info(f"✅ Fixed task_count for {fixed_count} branches")
            else:
                logger.info("✅ All task_counts are already synchronized")
                
            # Print summary
            logger.info("\n=== Summary ===")
            for branch in branches:
                actual_task_count = session.query(Task).filter(
                    Task.git_branch_id == branch.id
                ).count()
                logger.info(
                    f"  {branch.name}: {actual_task_count} tasks "
                    f"(project_id={branch.project_id})"
                )
                
    except Exception as e:
        logger.error(f"Error fixing task counts: {e}")
        return 1
    
    return 0


def check_specific_project(project_id: str):
    """Check task counts for a specific project"""
    db_mode = os.environ.get('DATABASE_MODE', 'supabase')
    os.environ['DATABASE_MODE'] = db_mode
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session as get_db_session
        from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch, Task
        
        with get_db_session() as session:
            # Get project
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return 1
                
            logger.info(f"Project: {project.name} (id={project.id})")
            
            # Get branches
            branches = session.query(ProjectGitBranch).filter(
                ProjectGitBranch.project_id == project_id
            ).all()
            
            for branch in branches:
                actual_task_count = session.query(Task).filter(
                    Task.git_branch_id == branch.id
                ).count()
                
                status = "✅" if branch.task_count == actual_task_count else "❌"
                logger.info(
                    f"  {status} Branch '{branch.name}' (id={branch.id}): "
                    f"task_count={branch.task_count}, actual={actual_task_count}"
                )
                
                if branch.task_count != actual_task_count:
                    logger.info(f"     -> Run fix_task_counts() to synchronize")
                    
    except Exception as e:
        logger.error(f"Error checking project: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix task_count synchronization issues")
    parser.add_argument(
        "--check", 
        metavar="PROJECT_ID",
        help="Check task counts for a specific project (doesn't fix)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix all task_count synchronization issues"
    )
    parser.add_argument(
        "--database",
        choices=['sqlite', 'supabase', 'postgres'],
        default='supabase',
        help="Database mode to use (default: supabase)"
    )
    
    args = parser.parse_args()
    
    # Set database mode
    os.environ['DATABASE_MODE'] = args.database
    
    if args.check:
        exit_code = check_specific_project(args.check)
    elif args.fix:
        exit_code = fix_task_counts()
    else:
        # Default action: check and report but don't fix
        logger.info("Checking task_count synchronization (use --fix to repair)...")
        os.environ['DATABASE_MODE'] = args.database
        
        from fastmcp.task_management.infrastructure.database.database_config import get_session as get_db_session
        from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch, Task
        
        with get_db_session() as session:
            branches = session.query(ProjectGitBranch).all()
            issues_found = 0
            
            for branch in branches:
                actual = session.query(Task).filter(Task.git_branch_id == branch.id).count()
                if branch.task_count != actual:
                    logger.warning(
                        f"Branch '{branch.name}': task_count={branch.task_count} "
                        f"but actual={actual}"
                    )
                    issues_found += 1
            
            if issues_found > 0:
                logger.info(f"\n⚠️  Found {issues_found} branches with incorrect task_count")
                logger.info("Run with --fix to repair these issues")
                exit_code = 1
            else:
                logger.info("\n✅ All task_counts are synchronized correctly")
                exit_code = 0
    
    sys.exit(exit_code)