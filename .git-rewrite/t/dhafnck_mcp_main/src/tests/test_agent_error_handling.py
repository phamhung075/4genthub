#!/usr/bin/env python3
"""
Test script for improved agent registration error handling

This script tests the enhanced error handling for agent registration:
1. Better error messages for duplicate agents
2. Pre-registration validation
3. Helpful hints and suggested actions
"""

import sys
import logging
from pathlib import Path
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_agent_error_handling():
    """Test improved agent registration error handling"""
    
    try:
        # Set environment to use SQLite for testing BEFORE importing any database modules
        import os
        # Clear any existing database type configuration
        if "DATABASE_TYPE" in os.environ:
            del os.environ["DATABASE_TYPE"]
        os.environ["DHAFNCK_DATABASE_TYPE"] = "sqlite"
        os.environ["MCP_DB_PATH"] = "/tmp/test_agent_errors.db"
        
        # Import required modules AFTER setting environment
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository
        from fastmcp.task_management.application.facades.agent_application_facade import AgentApplicationFacade
        from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException
        
        logger.info("=" * 60)
        logger.info("TESTING IMPROVED AGENT ERROR HANDLING")
        logger.info("=" * 60)
        
        # Get database configuration
        db_config = get_db_config()
        if not db_config:
            logger.error("Could not get database configuration")
            assert False, "Could not get database configuration"
        
        # Use a valid UUID for project_id (required by current validation)
        test_project_id = "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID format
        
        # Create repository and facade
        agent_repo = ORMAgentRepository(project_id=test_project_id)
        agent_facade = AgentApplicationFacade(agent_repo)
        
        # Test 1: Register a new agent successfully
        logger.info("\nTest 1: Register new agent successfully...")
        test_agent_id = str(uuid.uuid4())
        
        result1 = agent_facade.register_agent(
            project_id=test_project_id,
            agent_id=test_agent_id,
            name="test_agent_unique",
            call_agent="@test_agent"
        )
        
        logger.info(f"Result: {result1}")
        assert result1["success"], "Registration should succeed"
        assert "hint" in result1, "Success response should include hint"
        logger.info(f"✓ Agent registered with hint: {result1.get('hint')}")
        
        # Test 2: Try to register the same agent ID again
        logger.info("\nTest 2: Register duplicate agent by ID...")
        result2 = agent_facade.register_agent(
            project_id=test_project_id,
            agent_id=test_agent_id,
            name="different_name",
            call_agent="@different"
        )
        
        logger.info(f"Result: {result2}")
        assert not result2["success"], "Duplicate registration should fail"
        assert result2.get("error_code") == "DUPLICATE_AGENT", "Should have DUPLICATE_AGENT error code"
        assert "suggested_actions" in result2, "Should provide suggested actions"
        logger.info(f"✓ Got helpful error: {result2.get('error')}")
        logger.info(f"✓ Hint provided: {result2.get('hint')}")
        if "suggested_actions" in result2:
            logger.info(f"✓ Suggested actions: {result2['suggested_actions']}")
        
        # Test 3: Try to register an agent with duplicate name
        logger.info("\nTest 3: Register agent with duplicate name...")
        try:
            # Direct repository call to test pre-validation
            result3 = agent_repo.register_agent(
                project_id=test_project_id,
                agent_id=str(uuid.uuid4()),
                name="test_agent_unique",  # Same name as Test 1
                call_agent="@another"
            )
            logger.error("Should have raised ValidationException for duplicate name")
            assert False, "Should have raised ValidationException for duplicate name"
        except ValidationException as e:
            logger.info(f"✓ Got expected ValidationException: {e}")
            error_msg = str(e)
            assert "already exists" in error_msg, "Error should mention existing agent"
            assert "Consider using the existing agent" in error_msg, "Should suggest using existing"
            logger.info("✓ Pre-registration validation caught duplicate name")
        
        # Test 4: Test error message quality for missing project
        logger.info("\nTest 4: Register agent with non-existent project...")
        non_existent_project_id = "550e8400-e29b-41d4-a716-446655440999"  # Different valid UUID
        result4 = agent_facade.register_agent(
            project_id=non_existent_project_id,
            agent_id=str(uuid.uuid4()),
            name="test_agent_4",
            call_agent="@test4"
        )
        
        logger.info(f"Result: {result4}")
        # Note: This might succeed if projects aren't enforced by foreign keys
        if not result4["success"]:
            logger.info(f"✓ Error message: {result4.get('error')}")
            if result4.get("error_code") == "PROJECT_NOT_FOUND":
                logger.info(f"✓ Got PROJECT_NOT_FOUND error code")
                logger.info(f"✓ Hint: {result4.get('hint')}")
        
        # Test 5: Test helpful error for missing required fields
        logger.info("\nTest 5: Register agent with missing name...")
        result5 = agent_facade.register_agent(
            project_id=test_project_id,
            agent_id=str(uuid.uuid4()),
            name="",  # Empty name
            call_agent="@test5"
        )
        
        logger.info(f"Result: {result5}")
        if not result5["success"]:
            logger.info(f"✓ Error for empty name: {result5.get('error')}")
            if result5.get("error_code") == "MISSING_FIELD":
                logger.info(f"✓ Got MISSING_FIELD error code")
                logger.info(f"✓ Hint: {result5.get('hint')}")
        
        # Test 6: Verify the error messages are user-friendly
        logger.info("\nTest 6: Checking error message quality...")
        
        # Try to register duplicate again and check message quality
        duplicate_result = agent_facade.register_agent(
            project_id=test_project_id,
            agent_id=test_agent_id,
            name="test_agent_unique",
            call_agent="@duplicate"
        )
        
        if not duplicate_result["success"]:
            error_msg = duplicate_result.get("error", "")
            logger.info(f"Error message: {error_msg}")
            
            # Check for user-friendly elements
            checks = [
                ("already exists" in error_msg.lower(), "Mentions agent already exists"),
                ("use" in error_msg.lower() or "try" in error_msg.lower(), "Suggests alternative action"),
                (duplicate_result.get("hint") is not None, "Provides hint"),
                (duplicate_result.get("error_code") is not None, "Has error code"),
                (len(error_msg) > 20, "Error message is descriptive")
            ]
            
            for check, description in checks:
                if check:
                    logger.info(f"✓ {description}")
                else:
                    logger.warning(f"✗ {description}")
        
        logger.info("=" * 60)
        logger.info("✅ ALL ERROR HANDLING TESTS COMPLETED")
        logger.info("=" * 60)
        
        # Test completed successfully
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        assert False, f"Test failed with error: {e}"


def main():
    """Main entry point"""
    success = test_agent_error_handling()
    
    if success:
        logger.info("✅ Agent error handling test PASSED")
        sys.exit(0)
    else:
        logger.error("❌ Agent error handling test FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()