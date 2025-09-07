#!/usr/bin/env python3
"""
Test Foreign Key Constraints for TaskContext
"""

import logging
import uuid
from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_constraints():
    """Test that the foreign key constraints work correctly"""
    
    try:
        db_config = DatabaseConfig.get_instance()
        
        with db_config.get_session() as session:
            logger.info("Testing foreign key constraints...")
            
            # Test 1: Try to insert task_context with invalid task_id (should fail)
            test_id_1 = str(uuid.uuid4())
            invalid_task_id = str(uuid.uuid4())
            
            logger.info("Test 1: Inserting task_context with invalid task_id (should fail)...")
            
            try:
                session.execute(text("""
                    INSERT INTO task_contexts (id, task_id, user_id, created_at) 
                    VALUES (:id, :task_id, 'test-user', CURRENT_TIMESTAMP)
                """), {"id": test_id_1, "task_id": invalid_task_id})
                session.commit()
                
                # If we get here, the constraint didn't work
                logger.error("❌ FAILED: task_id constraint is not working - invalid record was inserted")
                
                # Clean up
                session.execute(text("DELETE FROM task_contexts WHERE id = :id"), {"id": test_id_1})
                session.commit()
                return False
                
            except IntegrityError as e:
                if "foreign key constraint" in str(e).lower():
                    logger.info("  ✅ PASSED: task_id foreign key constraint is working correctly")
                    session.rollback()
                else:
                    logger.error(f"❌ Unexpected error: {e}")
                    session.rollback()
                    return False
            
            # Test 2: Try to insert task_context with invalid parent_branch_id (should fail)
            test_id_2 = str(uuid.uuid4())
            invalid_branch_id = str(uuid.uuid4())
            
            logger.info("Test 2: Inserting task_context with invalid parent_branch_id (should fail)...")
            
            try:
                session.execute(text("""
                    INSERT INTO task_contexts (id, parent_branch_id, user_id, created_at) 
                    VALUES (:id, :parent_branch_id, 'test-user', CURRENT_TIMESTAMP)
                """), {"id": test_id_2, "parent_branch_id": invalid_branch_id})
                session.commit()
                
                # If we get here, the constraint didn't work
                logger.error("❌ FAILED: parent_branch_id constraint is not working - invalid record was inserted")
                
                # Clean up
                session.execute(text("DELETE FROM task_contexts WHERE id = :id"), {"id": test_id_2})
                session.commit()
                return False
                
            except IntegrityError as e:
                if "foreign key constraint" in str(e).lower():
                    logger.info("  ✅ PASSED: parent_branch_id foreign key constraint is working correctly")
                    session.rollback()
                else:
                    logger.error(f"❌ Unexpected error: {e}")
                    session.rollback()
                    return False
            
            # Test 3: Insert valid task_context record (should succeed)
            test_id_3 = str(uuid.uuid4())
            
            logger.info("Test 3: Inserting valid task_context with no foreign key references (should succeed)...")
            
            try:
                session.execute(text("""
                    INSERT INTO task_contexts (id, user_id, created_at) 
                    VALUES (:id, 'test-user', CURRENT_TIMESTAMP)
                """), {"id": test_id_3})
                session.commit()
                
                logger.info("  ✅ PASSED: Valid task_context record inserted successfully")
                
                # Clean up
                session.execute(text("DELETE FROM task_contexts WHERE id = :id"), {"id": test_id_3})
                session.commit()
                
            except Exception as e:
                logger.error(f"❌ FAILED: Valid insert should have succeeded: {e}")
                session.rollback()
                return False
            
            logger.info("🎉 All foreign key constraint tests PASSED!")
            return True
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Testing TaskContext Foreign Key Constraints")
    logger.info("=" * 60)
    
    success = test_constraints()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ All tests passed! Foreign key constraints are working correctly.")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("❌ Some tests failed! Foreign key constraints may not be working properly.")
        logger.error("=" * 60)