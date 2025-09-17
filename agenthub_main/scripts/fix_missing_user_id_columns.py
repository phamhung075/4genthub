#!/usr/bin/env python3
"""
Fix Missing User ID Columns Script

This script adds missing user_id columns to database tables that need them
for user isolation but don't have them due to incomplete migration.
"""

import os
import sys
import logging
import traceback
from sqlalchemy import create_engine, text, MetaData, Table, Column, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url() -> str:
    """Get database URL from environment variables."""
    # Try to get DATABASE_URL first (used in production)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Fallback to individual Supabase components
    host = os.getenv('SUPABASE_DB_HOST')
    user = os.getenv('SUPABASE_DB_USER') 
    password = os.getenv('SUPABASE_DB_PASSWORD')
    port = os.getenv('SUPABASE_DB_PORT', '5432')
    database = os.getenv('SUPABASE_DB_NAME', 'postgres')
    
    if host and user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
    
    raise ValueError("No valid database configuration found in environment variables")

def check_column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        with engine.connect() as conn:
            # Query information_schema to check if column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            
            count = result.scalar()
            return count > 0
    except Exception as e:
        logger.error(f"Error checking if column {column_name} exists in {table_name}: {e}")
        return False

def add_user_id_column(engine: Engine, table_name: str) -> bool:
    """Add user_id column to a table if it doesn't exist."""
    try:
        # Check if column already exists
        if check_column_exists(engine, table_name, 'user_id'):
            logger.info(f"✅ Column user_id already exists in {table_name}")
            return True
        
        logger.info(f"🔧 Adding user_id column to {table_name}")
        
        with engine.connect() as conn:
            # Begin transaction
            trans = conn.begin()
            
            try:
                # Add the column
                conn.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN user_id VARCHAR
                """))
                
                # Set default value for existing rows
                conn.execute(text(f"""
                    UPDATE {table_name} 
                    SET user_id = '00000000-0000-0000-0000-000000000000' 
                    WHERE user_id IS NULL
                """))
                
                # Make column NOT NULL
                conn.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN user_id SET NOT NULL
                """))
                
                # Create index for performance
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id 
                    ON {table_name}(user_id)
                """))
                
                # Commit transaction
                trans.commit()
                logger.info(f"✅ Successfully added user_id column to {table_name}")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"❌ Failed to add user_id column to {table_name}: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error adding user_id column to {table_name}: {e}")
        return False

def main():
    """Main function to fix missing user_id columns."""
    try:
        logger.info("🚀 Starting fix for missing user_id columns")
        
        # Get database URL
        database_url = get_database_url()
        logger.info("📡 Database URL configured")
        
        # Create engine
        engine = create_engine(database_url)
        logger.info("🔌 Database engine created")
        
        # List of tables that need user_id columns based on the errors we saw
        tables_to_fix = [
            'task_subtasks',        # TaskSubtask model - was missing user_id
            'branch_contexts',      # BranchContext model - was missing user_id  
            'task_contexts',        # TaskContext model - was missing user_id
            'global_contexts',      # GlobalContext model - was missing user_id
            'task_assignees',       # TaskAssignee model - was missing user_id
            'task_labels',          # TaskLabel model - was missing user_id
            'context_delegations',  # ContextDelegation model - was missing user_id
            'context_inheritance_cache',  # ContextInheritanceCache model - was missing user_id
            'labels',               # Label model - was missing user_id (optional)
            'templates',            # Template model - was missing user_id (optional)
        ]
        
        success_count = 0
        failure_count = 0
        
        for table_name in tables_to_fix:
            logger.info(f"🔧 Processing table: {table_name}")
            
            if add_user_id_column(engine, table_name):
                success_count += 1
            else:
                failure_count += 1
        
        logger.info(f"📊 Summary: {success_count} tables fixed, {failure_count} failed")
        
        if failure_count == 0:
            logger.info("🎉 All tables have been successfully fixed!")
            return 0
        else:
            logger.error(f"❌ {failure_count} tables could not be fixed")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())