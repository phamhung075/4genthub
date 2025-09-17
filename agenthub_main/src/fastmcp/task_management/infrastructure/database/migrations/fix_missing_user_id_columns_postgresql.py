"""
Migration: Fix missing user_id columns in context tables for PostgreSQL

This migration adds the missing user_id column to task_contexts table
and ensures both task_contexts and branch_contexts have proper user_id
columns with NOT NULL constraints for PostgreSQL/Supabase.

Tables fixed:
- task_contexts: Add missing user_id column
- branch_contexts: Make user_id NOT NULL (already exists but nullable)

IMPORTANT: This migration sets default user_id values for existing records.
"""

import logging
from typing import Optional
from sqlalchemy import text
from src.fastmcp.task_management.infrastructure.database.database_config import get_session

logger = logging.getLogger(__name__)

def run_postgresql_migration(fallback_user_id: str = "system") -> bool:
    """
    Run the missing user_id column migration on PostgreSQL database.
    
    Args:
        fallback_user_id: User ID to assign to existing records
        
    Returns:
        bool: True if migration succeeded, False otherwise
    """
    try:
        session = get_session()
        
        logger.info(f"Starting missing user_id columns migration on PostgreSQL database")
        
        # Start transaction
        session.begin()
        
        try:
            # 1. Check if task_contexts table has user_id column
            logger.info("Checking task_contexts table structure...")
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'task_contexts' AND column_name = 'user_id'
            """))
            task_context_has_user_id = result.fetchone() is not None
            
            if not task_context_has_user_id:
                logger.info("Adding missing user_id column to task_contexts table")
                session.execute(text(f"ALTER TABLE task_contexts ADD COLUMN user_id TEXT DEFAULT '{fallback_user_id}'"))
                
                # Update existing records to have the fallback user_id
                result = session.execute(text(f"UPDATE task_contexts SET user_id = '{fallback_user_id}' WHERE user_id IS NULL"))
                updated_count = result.rowcount
                logger.info(f"Updated {updated_count} task_contexts records with user_id = '{fallback_user_id}'")
                
                # Make the column NOT NULL
                session.execute(text("ALTER TABLE task_contexts ALTER COLUMN user_id SET NOT NULL"))
                logger.info("Made task_contexts.user_id column NOT NULL")
            else:
                logger.info("task_contexts.user_id column already exists")
                
                # Still update NULL values if any exist
                result = session.execute(text(f"UPDATE task_contexts SET user_id = '{fallback_user_id}' WHERE user_id IS NULL"))
                updated_count = result.rowcount
                if updated_count > 0:
                    logger.info(f"Updated {updated_count} NULL user_id values in task_contexts to '{fallback_user_id}'")
            
            # 2. Check if branch_contexts table has user_id column and fix NULL values
            logger.info("Checking branch_contexts table structure...")
            result = session.execute(text("""
                SELECT column_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'branch_contexts' AND column_name = 'user_id'
            """))
            branch_context_result = result.fetchone()
            
            if branch_context_result:
                is_nullable = branch_context_result[1] == 'YES'
                logger.info(f"branch_contexts.user_id column exists (nullable: {is_nullable})")
                
                # Update NULL values
                result = session.execute(text(f"UPDATE branch_contexts SET user_id = '{fallback_user_id}' WHERE user_id IS NULL"))
                updated_count = result.rowcount
                if updated_count > 0:
                    logger.info(f"Updated {updated_count} NULL user_id values in branch_contexts to '{fallback_user_id}'")
                
                # Make NOT NULL if it's currently nullable
                if is_nullable:
                    session.execute(text("ALTER TABLE branch_contexts ALTER COLUMN user_id SET NOT NULL"))
                    logger.info("Made branch_contexts.user_id column NOT NULL")
            else:
                logger.info("Adding missing user_id column to branch_contexts table")
                session.execute(text(f"ALTER TABLE branch_contexts ADD COLUMN user_id TEXT DEFAULT '{fallback_user_id}' NOT NULL"))
                
                # Update existing records to have the fallback user_id (shouldn't be needed due to default)
                result = session.execute(text(f"UPDATE branch_contexts SET user_id = '{fallback_user_id}' WHERE user_id IS NULL"))
                updated_count = result.rowcount
                logger.info(f"Updated {updated_count} branch_contexts records with user_id = '{fallback_user_id}'")
            
            # 3. Verify no NULL user_id values remain
            null_checks = []
            for table_name in ['task_contexts', 'branch_contexts']:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE user_id IS NULL OR user_id = ''"))
                    null_count = result.fetchone()[0]
                    if null_count > 0:
                        null_checks.append(f"{table_name}: {null_count} NULL/empty user_id values")
                except Exception as e:
                    logger.warning(f"Could not check {table_name}: {e}")
                    continue
            
            if null_checks:
                logger.error(f"Found NULL/empty user_id values after update: {null_checks}")
                session.rollback()
                session.close()
                return False
            
            # Commit transaction
            session.commit()
            
            logger.info("✅ PostgreSQL migration completed successfully")
            logger.info("Both task_contexts and branch_contexts now have user_id columns with NOT NULL constraints")
            
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed during execution: {e}")
            session.rollback()
            session.close()
            return False
        
    except Exception as e:
        logger.error(f"❌ Migration failed to connect: {e}")
        return False


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run migration
    success = run_postgresql_migration()
    
    if success:
        logger.info("✅ PostgreSQL migration completed successfully")
        exit(0)
    else:
        logger.error("❌ PostgreSQL migration failed")
        exit(1)