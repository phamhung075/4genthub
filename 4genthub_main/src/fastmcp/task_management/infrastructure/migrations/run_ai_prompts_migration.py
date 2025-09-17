#!/usr/bin/env python3
"""
Run migration to add AI prompts columns to tasks and subtasks tables.

This script applies the migration that adds system prompts and AI context
columns to enable AI agents to work on tasks with proper instructions.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from fastmcp.task_management.infrastructure.database.migrations.add_ai_prompts_columns import upgrade, downgrade
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run AI prompts migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration instead of applying it"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force run even if columns already exist"
    )
    
    args = parser.parse_args()
    
    try:
        db_config = get_db_config()
        engine = db_config.get_engine()
        
        if args.rollback:
            logger.info("Starting rollback of AI prompts migration...")
            downgrade(engine)
            logger.info("Rollback completed successfully")
        else:
            logger.info("Starting AI prompts migration...")
            upgrade(engine)
            logger.info("Migration completed successfully")
            
            # Verify the migration
            from sqlalchemy import inspect
            inspector = inspect(engine)
            
            # Check tasks table
            task_columns = [col['name'] for col in inspector.get_columns('tasks')]
            ai_columns = [c for c in task_columns if c.startswith('ai_')]
            logger.info(f"AI columns in tasks table: {ai_columns}")
            
            # Check task_subtasks table
            subtask_columns = [col['name'] for col in inspector.get_columns('task_subtasks')]
            ai_subtask_columns = [c for c in subtask_columns if c.startswith('ai_')]
            logger.info(f"AI columns in task_subtasks table: {ai_subtask_columns}")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()