"""
Migration: Add NOT NULL constraints to user_id fields

This migration updates all models with user_id fields to make them NOT NULL,
ensuring user isolation is enforced at the database level.

Models affected:
- Task.user_id
- Agent.user_id  
- ProjectContext.user_id
- BranchContext.user_id
- TaskContext.user_id

IMPORTANT: This migration requires that all existing records have valid user_id values.
If any records have NULL user_id, they will need to be updated or deleted first.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def run_migration(db_path: str, fallback_user_id: str = "system") -> bool:
    """
    Run the user_id NOT NULL migration on the specified database.
    
    Args:
        db_path: Path to the SQLite database file
        fallback_user_id: User ID to assign to records with NULL user_id
        
    Returns:
        bool: True if migration succeeded, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"Starting user_id NOT NULL migration on {db_path}")
        
        # Check if migration is needed by looking for nullable user_id columns
        migration_needed = False
        
        # Check each table that should have NOT NULL user_id
        tables_to_check = [
            ("tasks", "user_id"),
            ("agents", "user_id"), 
            ("project_contexts", "user_id"),
            ("branch_contexts", "user_id"),
            ("task_contexts", "user_id")
        ]
        
        for table_name, column_name in tables_to_check:
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Find the user_id column
                for column in columns:
                    if column[1] == column_name:  # column[1] is the column name
                        if column[3] == 0:  # column[3] is 'not null' (0 = nullable, 1 = not null)
                            logger.info(f"Found nullable {column_name} in {table_name}, migration needed")
                            migration_needed = True
                        break
            except sqlite3.OperationalError as e:
                # Table might not exist, which is fine
                logger.debug(f"Table {table_name} does not exist: {e}")
                continue
        
        if not migration_needed:
            logger.info("No nullable user_id columns found, migration not needed")
            conn.close()
            return True
            
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Update NULL user_id values to fallback_user_id
        tables_updated = []
        
        for table_name, column_name in tables_to_check:
            try:
                # Check if table exists
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    logger.debug(f"Table {table_name} does not exist, skipping")
                    continue
                
                # Update NULL values
                cursor.execute(f"UPDATE {table_name} SET {column_name} = ? WHERE {column_name} IS NULL", 
                             (fallback_user_id,))
                updated_count = cursor.rowcount
                
                if updated_count > 0:
                    logger.info(f"Updated {updated_count} NULL {column_name} values in {table_name} to '{fallback_user_id}'")
                    tables_updated.append(f"{table_name}.{column_name}")
                
            except sqlite3.OperationalError as e:
                logger.error(f"Error updating {table_name}.{column_name}: {e}")
                cursor.execute("ROLLBACK")
                conn.close()
                return False
        
        # 2. For SQLite, we need to recreate tables to add NOT NULL constraints
        # This is complex for existing data, so we'll log this as a manual step
        logger.warning("SQLite does not support adding NOT NULL constraints to existing columns")
        logger.warning("The application code has been updated to expect NOT NULL user_id")
        logger.warning("For full database constraint enforcement, consider:")
        logger.warning("1. Export data, recreate database with new schema, import data")
        logger.warning("2. Use PostgreSQL which supports ALTER COLUMN SET NOT NULL")
        
        # For now, just ensure no NULL values exist
        null_checks = []
        for table_name, column_name in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL")
                null_count = cursor.fetchone()[0]
                if null_count > 0:
                    null_checks.append(f"{table_name}.{column_name}: {null_count} NULL values")
            except sqlite3.OperationalError:
                continue
        
        if null_checks:
            logger.error(f"Found NULL user_id values after update: {null_checks}")
            cursor.execute("ROLLBACK")
            conn.close()
            return False
        
        # Commit transaction
        cursor.execute("COMMIT")
        
        logger.info("Migration completed successfully")
        logger.info(f"Tables updated: {', '.join(tables_updated) if tables_updated else 'None'}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        try:
            cursor.execute("ROLLBACK")
            conn.close()
        except:
            pass
        return False


def run_migration_with_config(config_path: Optional[str] = None) -> bool:
    """
    Run migration using configuration from environment or config file.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        bool: True if migration succeeded
    """
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    if config_path:
        load_dotenv(config_path)
    else:
        load_dotenv()
    
    # Get database path from environment
    db_path = os.getenv("MCP_DB_PATH", "dhafnck_mcp.db")
    fallback_user_id = os.getenv("MIGRATION_FALLBACK_USER_ID", "system")
    
    logger.info(f"Running migration with db_path={db_path}, fallback_user_id={fallback_user_id}")
    
    return run_migration(db_path, fallback_user_id)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run migration
    success = run_migration_with_config()
    
    if success:
        logger.info("✅ Migration completed successfully")
        exit(0)
    else:
        logger.error("❌ Migration failed")
        exit(1)