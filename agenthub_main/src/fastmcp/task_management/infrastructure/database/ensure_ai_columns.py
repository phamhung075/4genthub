"""
Ensure AI columns exist in the database.
This module ensures that AI-related columns are present in tasks and subtasks tables.
Called during application startup to guarantee database schema consistency.
"""

from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def ensure_ai_columns_exist(engine: Engine) -> bool:
    """
    Ensure AI columns exist in tasks and subtasks tables.
    This is called on every application startup to guarantee schema consistency.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        bool: True if columns exist or were created, False on error
    """
    try:
        with engine.begin() as conn:
            inspector = inspect(engine)
            dialect_name = engine.dialect.name
            
            # Define the AI columns that must exist
            ai_columns: List[Tuple[str, str, str]] = [
                ("ai_system_prompt", "TEXT", "''"),
                ("ai_request_prompt", "TEXT", "''"),
                ("ai_work_context", "JSON" if dialect_name == 'postgresql' else "TEXT", "'{}'" if dialect_name == 'postgresql' else "'{}'"),
                ("ai_completion_criteria", "TEXT", "''"),
                ("ai_execution_history", "JSON" if dialect_name == 'postgresql' else "TEXT", "'[]'" if dialect_name == 'postgresql' else "'[]'"),
                ("ai_last_execution", "TIMESTAMP", "NULL"),
                ("ai_model_preferences", "JSON" if dialect_name == 'postgresql' else "TEXT", "'{}'" if dialect_name == 'postgresql' else "'{}'")
            ]
            
            tables_to_update = ['tasks', 'subtasks']
            columns_added = 0
            
            for table_name in tables_to_update:
                if table_name not in inspector.get_table_names():
                    logger.warning(f"Table {table_name} does not exist yet. Will be created by ORM.")
                    continue
                
                existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                
                for col_name, col_type, default_val in ai_columns:
                    if col_name not in existing_columns:
                        try:
                            # Add the column if it doesn't exist
                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"
                            logger.info(f"Adding AI column {col_name} to {table_name} table")
                            conn.execute(text(alter_sql))
                            columns_added += 1
                        except (OperationalError, ProgrammingError) as e:
                            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                                logger.debug(f"Column {col_name} already exists in {table_name} table")
                            else:
                                logger.error(f"Error adding column {col_name} to {table_name}: {e}")
                                raise
            
            if columns_added > 0:
                logger.info(f"✅ Successfully added {columns_added} AI columns to database")
            else:
                logger.debug("✅ All AI columns already exist in database")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to ensure AI columns exist: {e}")
        return False


def verify_ai_columns(engine: Engine) -> dict:
    """
    Verify that AI columns exist and return their status.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        dict: Status of AI columns in each table
    """
    try:
        inspector = inspect(engine)
        status = {}
        
        for table_name in ['tasks', 'subtasks']:
            if table_name not in inspector.get_table_names():
                status[table_name] = "Table not found"
                continue
            
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            ai_columns = [c for c in columns if c.startswith('ai_')]
            
            status[table_name] = {
                'exists': True,
                'ai_columns': ai_columns,
                'ai_columns_count': len(ai_columns)
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Error verifying AI columns: {e}")
        return {'error': str(e)}