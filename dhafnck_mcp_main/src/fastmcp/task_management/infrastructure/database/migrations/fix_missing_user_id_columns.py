"""
Migration: Fix missing user_id columns in context tables

This migration adds the missing user_id column to task_contexts table
and ensures both task_contexts and branch_contexts have proper user_id
columns with NOT NULL constraints.

Tables fixed:
- task_contexts: Add missing user_id column
- branch_contexts: Make user_id NOT NULL (already exists but nullable)

IMPORTANT: This migration sets default user_id values for existing records.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def run_migration(db_path: str, fallback_user_id: str = "system") -> bool:
    """
    Run the missing user_id column migration on the specified database.
    
    Args:
        db_path: Path to the SQLite database file
        fallback_user_id: User ID to assign to existing records
        
    Returns:
        bool: True if migration succeeded, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"Starting missing user_id columns migration on {db_path}")
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Check if task_contexts table has user_id column
        cursor.execute("PRAGMA table_info(task_contexts)")
        task_context_columns = {col[1]: col for col in cursor.fetchall()}
        
        if 'user_id' not in task_context_columns:
            logger.info("Adding missing user_id column to task_contexts table")
            cursor.execute(f"ALTER TABLE task_contexts ADD COLUMN user_id TEXT DEFAULT '{fallback_user_id}'")
            
            # Update existing records to have the fallback user_id
            cursor.execute("UPDATE task_contexts SET user_id = ? WHERE user_id IS NULL", (fallback_user_id,))
            updated_count = cursor.rowcount
            logger.info(f"Updated {updated_count} task_contexts records with user_id = '{fallback_user_id}'")
        else:
            logger.info("task_contexts.user_id column already exists")
            
            # Still update NULL values if any exist
            cursor.execute("UPDATE task_contexts SET user_id = ? WHERE user_id IS NULL", (fallback_user_id,))
            updated_count = cursor.rowcount
            if updated_count > 0:
                logger.info(f"Updated {updated_count} NULL user_id values in task_contexts to '{fallback_user_id}'")
        
        # 2. Check if branch_contexts table has user_id column and fix NULL values
        cursor.execute("PRAGMA table_info(branch_contexts)")
        branch_context_columns = {col[1]: col for col in cursor.fetchall()}
        
        if 'user_id' in branch_context_columns:
            logger.info("branch_contexts.user_id column exists, updating NULL values")
            cursor.execute("UPDATE branch_contexts SET user_id = ? WHERE user_id IS NULL", (fallback_user_id,))
            updated_count = cursor.rowcount
            if updated_count > 0:
                logger.info(f"Updated {updated_count} NULL user_id values in branch_contexts to '{fallback_user_id}'")
        else:
            logger.info("Adding missing user_id column to branch_contexts table")
            cursor.execute(f"ALTER TABLE branch_contexts ADD COLUMN user_id TEXT DEFAULT '{fallback_user_id}'")
            
            # Update existing records to have the fallback user_id
            cursor.execute("UPDATE branch_contexts SET user_id = ? WHERE user_id IS NULL", (fallback_user_id,))
            updated_count = cursor.rowcount
            logger.info(f"Updated {updated_count} branch_contexts records with user_id = '{fallback_user_id}'")
        
        # 3. Verify no NULL user_id values remain
        null_checks = []
        for table_name in ['task_contexts', 'branch_contexts']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE user_id IS NULL OR user_id = ''")
                null_count = cursor.fetchone()[0]
                if null_count > 0:
                    null_checks.append(f"{table_name}: {null_count} NULL/empty user_id values")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not check {table_name}: {e}")
                continue
        
        if null_checks:
            logger.error(f"Found NULL/empty user_id values after update: {null_checks}")
            cursor.execute("ROLLBACK")
            conn.close()
            return False
        
        # 4. For SQLite, we can't add NOT NULL constraints to existing columns easily
        # But we've ensured no NULL values exist and the ORM will enforce it
        logger.info("NOTE: SQLite does not support adding NOT NULL constraints to existing columns")
        logger.info("All NULL user_id values have been updated, ORM will enforce NOT NULL in application")
        
        # Commit transaction
        cursor.execute("COMMIT")
        
        logger.info("✅ Migration completed successfully")
        logger.info("Both task_contexts and branch_contexts now have user_id columns with valid values")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
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
    
    # Get database path from environment or use default
    db_path = os.getenv("MCP_DB_PATH")
    if not db_path:
        # Try to find the database in common locations
        possible_paths = [
            "/home/daihungpham/agentic-project/dhafnck_mcp_main/database/data/dhafnck_mcp.db",
            "/home/daihungpham/agentic-project/dhafnck_mcp_main/database/data/dhafnck_mcp_test.db",
            "dhafnck_mcp.db",
            "dhafnck_mcp_test.db"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                logger.info(f"Found database at: {db_path}")
                break
        
        if not db_path:
            logger.error("Could not find database file. Please set MCP_DB_PATH environment variable")
            return False
    
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