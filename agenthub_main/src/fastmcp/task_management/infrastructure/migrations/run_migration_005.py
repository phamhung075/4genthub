#!/usr/bin/env python3
"""
Migration Runner: Add Missing Foreign Key Constraints
Date: 2025-08-26
Description: Applies migration 005 to add missing foreign key constraints for TaskContext
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to the path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastmcp.task_management.infrastructure.database.database_config import get_database_url
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Run the foreign key constraints migration"""
    
    # Read the migration SQL file
    migration_file = current_dir / "005_add_missing_foreign_keys.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Reading migration file: {migration_file}")
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Get database connection
    database_url = get_database_url()
    logger.info(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        logger.info("Database connection established")
        
        # Check if migration has already been applied
        check_sql = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'migration_history'
        )
        """
        
        table_exists = await conn.fetchval(check_sql)
        
        if table_exists:
            # Check if this specific migration was already applied
            migration_check = """
            SELECT EXISTS (
                SELECT 1 FROM migration_history 
                WHERE migration_name = '005_add_missing_foreign_keys'
            )
            """
            
            already_applied = await conn.fetchval(migration_check)
            
            if already_applied:
                logger.info("Migration 005 has already been applied")
                await conn.close()
                return True
        
        # Apply the migration
        logger.info("Applying migration 005: Add Missing Foreign Key Constraints")
        
        # Execute the migration SQL
        await conn.execute(migration_sql)
        
        logger.info("Migration 005 applied successfully")
        
        # Verify the constraints were created
        verify_sql = """
        SELECT 
            tc.constraint_name,
            ccu.column_name,
            ccu.table_name as source_table,
            kcu.table_name as target_table,
            kcu.column_name as target_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.column_name IN ('task_id', 'parent_branch_id')
        ORDER BY ccu.column_name;
        """
        
        constraints = await conn.fetch(verify_sql)
        
        logger.info("Verification - Foreign key constraints created:")
        for constraint in constraints:
            logger.info(f"  - {constraint['constraint_name']}: {constraint['source_table']}.{constraint['column_name']} -> {constraint['target_table']}.{constraint['target_column']}")
        
        if len(constraints) >= 2:
            logger.info("✅ All required foreign key constraints have been successfully created")
        else:
            logger.warning(f"⚠️  Expected 2 constraints, found {len(constraints)}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        if 'conn' in locals():
            await conn.close()
        return False


async def verify_model_consistency():
    """Verify that the database schema matches the SQLAlchemy models"""
    
    database_url = get_database_url()
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check if TaskContext foreign keys exist and match model definitions
        check_sql = """
        SELECT 
            tc.constraint_name,
            ccu.column_name,
            ccu.table_name,
            kcu.table_name as references_table,
            kcu.column_name as references_column,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY ccu.column_name;
        """
        
        constraints = await conn.fetch(check_sql)
        
        logger.info("Model Consistency Verification:")
        logger.info("TaskContext foreign key constraints in database:")
        
        task_id_constraint = None
        parent_branch_id_constraint = None
        
        for constraint in constraints:
            column = constraint['column_name']
            ref_table = constraint['references_table']
            ref_column = constraint['references_column']
            delete_rule = constraint['delete_rule']
            
            logger.info(f"  - {column} -> {ref_table}.{ref_column} (ON DELETE {delete_rule})")
            
            if column == 'task_id':
                task_id_constraint = constraint
            elif column == 'parent_branch_id':
                parent_branch_id_constraint = constraint
        
        # Verify expected constraints
        success = True
        
        if task_id_constraint:
            if task_id_constraint['references_table'] == 'tasks' and task_id_constraint['references_column'] == 'id':
                logger.info("✅ task_id constraint matches SQLAlchemy model")
            else:
                logger.error("❌ task_id constraint does not match SQLAlchemy model")
                success = False
        else:
            logger.error("❌ task_id foreign key constraint missing")
            success = False
        
        if parent_branch_id_constraint:
            if parent_branch_id_constraint['references_table'] == 'project_git_branchs' and parent_branch_id_constraint['references_column'] == 'id':
                logger.info("✅ parent_branch_id constraint matches SQLAlchemy model")
            else:
                logger.error("❌ parent_branch_id constraint does not match SQLAlchemy model")
                success = False
        else:
            logger.error("❌ parent_branch_id foreign key constraint missing")
            success = False
        
        await conn.close()
        
        if success:
            logger.info("🎉 Database schema is consistent with SQLAlchemy models")
        else:
            logger.error("💥 Database schema inconsistencies found")
        
        return success
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False


async def main():
    """Main migration runner"""
    
    logger.info("=" * 60)
    logger.info("TaskContext Foreign Key Migration - Starting")
    logger.info("=" * 60)
    
    # Step 1: Apply migration
    migration_success = await run_migration()
    
    if not migration_success:
        logger.error("Migration failed - aborting")
        sys.exit(1)
    
    # Step 2: Verify model consistency
    logger.info("-" * 60)
    verification_success = await verify_model_consistency()
    
    if verification_success:
        logger.info("=" * 60)
        logger.info("✅ Migration 005 completed successfully!")
        logger.info("Database foreign key constraints now match SQLAlchemy models")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ Migration completed but verification failed")
        logger.error("Manual investigation required")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())