"""
Migration to add AI system prompts and context columns to tasks and subtasks tables.

This migration adds columns for storing AI-related prompts and execution context
to enable AI agents to work on tasks with proper context and instructions.
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging
from typing import Any

logger = logging.getLogger(__name__)


def upgrade(engine: Any) -> None:
    """Add AI prompt columns to tasks and task_subtasks tables."""
    
    with engine.begin() as conn:
        inspector = inspect(engine)
        
        # Check if we're using PostgreSQL or SQLite
        dialect_name = engine.dialect.name
        
        # Define the new columns to add
        task_columns = [
            ("ai_system_prompt", "TEXT", "''"),
            ("ai_request_prompt", "TEXT", "''"),
            ("ai_work_context", "JSON" if dialect_name == 'postgresql' else "TEXT", "'{}'" if dialect_name == 'postgresql' else "'{}'"),
            ("ai_completion_criteria", "TEXT", "''"),
            ("ai_execution_history", "JSON" if dialect_name == 'postgresql' else "TEXT", "'[]'" if dialect_name == 'postgresql' else "'[]'"),
            ("ai_last_execution", "TIMESTAMP", "NULL"),
            ("ai_model_preferences", "JSON" if dialect_name == 'postgresql' else "TEXT", "'{}'" if dialect_name == 'postgresql' else "'{}'")
        ]
        
        # Add columns to tasks table
        existing_task_columns = [col['name'] for col in inspector.get_columns('tasks')]
        for col_name, col_type, default_val in task_columns:
            if col_name not in existing_task_columns:
                try:
                    alter_sql = f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"
                    logger.info(f"Adding column {col_name} to tasks table")
                    conn.execute(text(alter_sql))
                except (OperationalError, ProgrammingError) as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        logger.info(f"Column {col_name} already exists in tasks table")
                    else:
                        raise
        
        # Add columns to task_subtasks table
        existing_subtask_columns = [col['name'] for col in inspector.get_columns('task_subtasks')]
        for col_name, col_type, default_val in task_columns:
            if col_name not in existing_subtask_columns:
                try:
                    alter_sql = f"ALTER TABLE task_subtasks ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"
                    logger.info(f"Adding column {col_name} to task_subtasks table")
                    conn.execute(text(alter_sql))
                except (OperationalError, ProgrammingError) as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        logger.info(f"Column {col_name} already exists in task_subtasks table")
                    else:
                        raise
        
        logger.info("Successfully added AI prompt columns to tasks and subtasks tables")


def downgrade(engine: Any) -> None:
    """Remove AI prompt columns from tasks and task_subtasks tables."""
    
    with engine.begin() as conn:
        columns_to_remove = [
            "ai_system_prompt",
            "ai_request_prompt",
            "ai_work_context",
            "ai_completion_criteria",
            "ai_execution_history",
            "ai_last_execution",
            "ai_model_preferences"
        ]
        
        for col_name in columns_to_remove:
            try:
                # Remove from tasks table
                conn.execute(text(f"ALTER TABLE tasks DROP COLUMN {col_name}"))
                logger.info(f"Removed column {col_name} from tasks table")
            except (OperationalError, ProgrammingError) as e:
                logger.warning(f"Could not remove column {col_name} from tasks: {e}")
            
            try:
                # Remove from task_subtasks table  
                conn.execute(text(f"ALTER TABLE task_subtasks DROP COLUMN {col_name}"))
                logger.info(f"Removed column {col_name} from task_subtasks table")
            except (OperationalError, ProgrammingError) as e:
                logger.warning(f"Could not remove column {col_name} from task_subtasks: {e}")


if __name__ == "__main__":
    # This can be run directly for testing
    import sys
    sys.path.append("../../../../../../")
    
    from fastmcp.task_management.infrastructure.database.database_config import get_engine
    
    engine = get_engine()
    upgrade(engine)
    print("Migration completed successfully")