#!/usr/bin/env python3
"""
Simple Migration Applier: Add Missing Foreign Key Constraints
Uses existing database infrastructure from the application
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
        """Apply the foreign key constraints migration using existing infrastructure"""
        
        # Read migration SQL
        migration_file = Path(__file__).parent / "005_add_missing_foreign_keys.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        try:
            # Get database instance
            db_config = DatabaseConfig.get_instance()
            
            # Create a session
            with db_config.get_session() as session:
                logger.info("Applying foreign key constraints migration...")
                
                # Execute the migration SQL
                session.execute(text(migration_sql))
                session.commit()
                
                logger.info("✅ Migration applied successfully")
                
                # Verify constraints were created
                verify_sql = """
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
                ORDER BY ccu.column_name;
                """
                
                result = session.execute(text(verify_sql))
                constraints = result.fetchall()
                
                logger.info("Verification - Foreign key constraints:")
                for constraint in constraints:
                    logger.info(f"  ✓ {constraint[0]}: {constraint[1]} -> {constraint[2]}.{constraint[3]}")
                
                if len(constraints) >= 2:
                    logger.info("🎉 All required foreign key constraints created successfully")
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
        logger.info("Applying Foreign Key Constraints Migration")
        logger.info("=" * 60)
        
        success = apply_migration()
        
        if success:
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("Migration failed!")
            sys.exit(1)
            
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)