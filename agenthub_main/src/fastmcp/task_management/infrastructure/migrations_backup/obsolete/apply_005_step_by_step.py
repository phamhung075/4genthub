#!/usr/bin/env python3
"""
Step-by-step Migration Applier: Add Missing Foreign Key Constraints
Executes migration commands one by one for better error handling
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
    from sqlalchemy import text
    
    def apply_migration():
        """Apply the foreign key constraints migration step by step"""
        
        try:
            # Get database instance
            db_config = DatabaseConfig.get_instance()
            
            # Create a session
            with db_config.get_session() as session:
                logger.info("Starting foreign key constraints migration...")
                
                # Step 1: Create migration tracking table
                logger.info("Step 1: Creating migration tracking table...")
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS migration_history (
                        id SERIAL PRIMARY KEY,
                        migration_name VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                session.commit()
                
                # Step 2: Check if migration already applied
                logger.info("Step 2: Checking if migration already applied...")
                result = session.execute(text("""
                    SELECT COUNT(*) FROM migration_history 
                    WHERE migration_name = '005_add_missing_foreign_keys'
                """))
                
                if result.scalar() > 0:
                    logger.info("Migration 005 already applied - skipping")
                    return True
                
                # Step 3: Record migration start
                logger.info("Step 3: Recording migration start...")
                session.execute(text("""
                    INSERT INTO migration_history (migration_name) 
                    VALUES ('005_add_missing_foreign_keys')
                    ON CONFLICT (migration_name) DO NOTHING
                """))
                session.commit()
                
                # Step 4: Check current foreign key status
                logger.info("Step 4: Checking current foreign key constraints...")
                
                task_id_fk_result = session.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints tc
                        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.table_name = 'task_contexts' 
                        AND tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.column_name = 'task_id'
                        AND ccu.table_name = 'task_contexts'
                    )
                """))
                
                parent_branch_fk_result = session.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints tc
                        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.table_name = 'task_contexts' 
                        AND tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.column_name = 'parent_branch_id'
                        AND ccu.table_name = 'task_contexts'
                    )
                """))
                
                task_id_fk_exists = task_id_fk_result.scalar()
                parent_branch_fk_exists = parent_branch_fk_result.scalar()
                
                logger.info(f"  - task_id FK exists: {task_id_fk_exists}")
                logger.info(f"  - parent_branch_id FK exists: {parent_branch_fk_exists}")
                
                # Step 5: Check for orphaned records
                logger.info("Step 5: Checking for orphaned records...")
                
                orphan_task_result = session.execute(text("""
                    SELECT COUNT(*) FROM task_contexts tc
                    WHERE tc.task_id IS NOT NULL 
                    AND NOT EXISTS (
                        SELECT 1 FROM tasks t 
                        WHERE t.id = tc.task_id
                    )
                """))
                
                orphan_branch_result = session.execute(text("""
                    SELECT COUNT(*) FROM task_contexts tc
                    WHERE tc.parent_branch_id IS NOT NULL 
                    AND NOT EXISTS (
                        SELECT 1 FROM project_git_branchs pgb 
                        WHERE pgb.id = tc.parent_branch_id
                    )
                """))
                
                orphan_task_count = orphan_task_result.scalar()
                orphan_branch_count = orphan_branch_result.scalar()
                
                logger.info(f"  - Orphaned task_id references: {orphan_task_count}")
                logger.info(f"  - Orphaned parent_branch_id references: {orphan_branch_count}")
                
                # Step 6: Clean up orphaned records
                if orphan_task_count > 0:
                    logger.info("Step 6a: Cleaning up orphaned task_id records...")
                    result = session.execute(text("""
                        DELETE FROM task_contexts 
                        WHERE task_id IS NOT NULL 
                        AND NOT EXISTS (
                            SELECT 1 FROM tasks t 
                            WHERE t.id = task_contexts.task_id
                        )
                    """))
                    logger.info(f"  - Deleted {result.rowcount} orphaned task_id records")
                    session.commit()
                
                if orphan_branch_count > 0:
                    logger.info("Step 6b: Cleaning up orphaned parent_branch_id records...")
                    result = session.execute(text("""
                        DELETE FROM task_contexts 
                        WHERE parent_branch_id IS NOT NULL 
                        AND NOT EXISTS (
                            SELECT 1 FROM project_git_branchs pgb 
                            WHERE pgb.id = task_contexts.parent_branch_id
                        )
                    """))
                    logger.info(f"  - Deleted {result.rowcount} orphaned parent_branch_id records")
                    session.commit()
                
                # Step 7: Add foreign key constraints
                constraints_added = 0
                
                if not task_id_fk_exists:
                    logger.info("Step 7a: Adding task_id foreign key constraint...")
                    session.execute(text("""
                        ALTER TABLE task_contexts
                        ADD CONSTRAINT fk_task_contexts_task_id 
                        FOREIGN KEY (task_id) 
                        REFERENCES tasks(id) 
                        ON DELETE CASCADE
                    """))
                    constraints_added += 1
                    logger.info("  ✓ Added task_id foreign key constraint")
                else:
                    logger.info("  ✓ task_id foreign key constraint already exists")
                
                if not parent_branch_fk_exists:
                    logger.info("Step 7b: Adding parent_branch_id foreign key constraint...")
                    session.execute(text("""
                        ALTER TABLE task_contexts
                        ADD CONSTRAINT fk_task_contexts_parent_branch_id 
                        FOREIGN KEY (parent_branch_id) 
                        REFERENCES project_git_branchs(id) 
                        ON DELETE CASCADE
                    """))
                    constraints_added += 1
                    logger.info("  ✓ Added parent_branch_id foreign key constraint")
                else:
                    logger.info("  ✓ parent_branch_id foreign key constraint already exists")
                
                session.commit()
                
                # Step 8: Add performance indexes
                logger.info("Step 8: Creating performance indexes...")
                
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_task_contexts_task_id ON task_contexts (task_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_task_contexts_parent_branch_id ON task_contexts (parent_branch_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_task_contexts_user_id ON task_contexts (user_id)"))
                
                session.commit()
                logger.info("  ✓ Performance indexes created")
                
                # Step 9: Verify constraints
                logger.info("Step 9: Verifying foreign key constraints...")
                
                verify_result = session.execute(text("""
                    SELECT 
                        tc.constraint_name,
                        ccu.column_name,
                        kcu.table_name as target_table,
                        kcu.column_name as target_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = 'task_contexts' 
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.column_name IN ('task_id', 'parent_branch_id')
                    ORDER BY ccu.column_name
                """))
                
                constraints = verify_result.fetchall()
                
                logger.info("  Foreign key constraints verified:")
                for constraint in constraints:
                    logger.info(f"    ✓ {constraint[0]}: {constraint[1]} -> {constraint[2]}.{constraint[3]}")
                
                # Step 10: Record completion
                session.execute(text("""
                    INSERT INTO migration_history (migration_name, applied_at) 
                    VALUES ('005_add_missing_foreign_keys_completed', CURRENT_TIMESTAMP)
                    ON CONFLICT (migration_name) DO NOTHING
                """))
                session.commit()
                
                if len(constraints) >= 2:
                    logger.info("🎉 All required foreign key constraints created successfully!")
                    logger.info(f"Migration summary: {constraints_added} constraints added, {len(constraints)} total constraints verified")
                    return True
                else:
                    logger.warning(f"⚠️  Expected 2 constraints, found {len(constraints)}")
                    return False
                
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return False
    
    if __name__ == "__main__":
        logger.info("=" * 60)
        logger.info("Applying Foreign Key Constraints Migration (Step by Step)")
        logger.info("=" * 60)
        
        success = apply_migration()
        
        if success:
            logger.info("=" * 60)
            logger.info("✅ Migration completed successfully!")
            logger.info("Database foreign key constraints now match SQLAlchemy models")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.error("=" * 60)
            logger.error("❌ Migration failed!")
            logger.error("=" * 60)
            sys.exit(1)
            
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)