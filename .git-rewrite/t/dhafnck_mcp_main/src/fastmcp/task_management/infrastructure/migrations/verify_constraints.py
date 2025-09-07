#!/usr/bin/env python3
"""
Verify Foreign Key Constraints for TaskContext
"""

import logging
from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_constraints():
    """Verify the foreign key constraints exist"""
    
    try:
        db_config = DatabaseConfig.get_instance()
        
        with db_config.get_session() as session:
            logger.info("Checking foreign key constraints on task_contexts table...")
            
            # Simple check for all constraints
            result = session.execute(text("""
                SELECT 
                    constraint_name,
                    constraint_type
                FROM information_schema.table_constraints 
                WHERE table_name = 'task_contexts' 
                AND constraint_type = 'FOREIGN KEY'
            """))
            
            all_constraints = result.fetchall()
            logger.info(f"Found {len(all_constraints)} foreign key constraints:")
            for constraint in all_constraints:
                logger.info(f"  - {constraint[0]} ({constraint[1]})")
            
            # Detailed check
            result2 = session.execute(text("""
                SELECT 
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = 'task_contexts'
            """))
            
            detailed_constraints = result2.fetchall()
            logger.info(f"\nDetailed constraint information:")
            for constraint in detailed_constraints:
                logger.info(f"  - {constraint[0]}: {constraint[2]} -> {constraint[3]}.{constraint[4]}")
            
            # Check specifically for our constraints
            task_id_result = session.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'task_contexts' 
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%task_id%'
            """))
            
            parent_branch_result = session.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'task_contexts' 
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%parent_branch_id%'
            """))
            
            task_id_constraints = task_id_result.fetchall()
            parent_branch_constraints = parent_branch_result.fetchall()
            
            logger.info(f"\nSpecific constraint checks:")
            logger.info(f"  - task_id constraints: {[c[0] for c in task_id_constraints]}")
            logger.info(f"  - parent_branch_id constraints: {[c[0] for c in parent_branch_constraints]}")
            
            if len(task_id_constraints) >= 1 and len(parent_branch_constraints) >= 1:
                logger.info("✅ Both required foreign key constraints exist!")
                return True
            else:
                logger.error("❌ Some foreign key constraints are missing")
                return False
                
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    verify_constraints()