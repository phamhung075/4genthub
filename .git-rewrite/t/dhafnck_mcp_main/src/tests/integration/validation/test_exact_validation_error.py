#!/usr/bin/env python3
"""
Test to reproduce the exact validation error:
"Input validation error: '3' is not valid under any of the given schemas"

This test should FAIL before the fix is implemented.
"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory


class TestExactValidationError:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test to reproduce the exact validation error before fix."""
    
    @pytest.fixture
    def controller(self):
        """Create a TaskMCPController without parameter validation fix."""
        facade = Mock(spec=TaskApplicationFacade)
        facade.list_tasks.return_value = {"success": True, "tasks": []}
        
        factory = Mock(spec=TaskFacadeFactory)
        factory.create_task_facade.return_value = facade
        factory.create_task_facade_with_git_branch_id.return_value = facade
        
        return TaskMCPController(task_facade_factory=factory)
    
    def test_reproduce_exact_error_limit_3(self, controller):
        """
        This test should reproduce the exact error:
        "Input validation error: '3' is not valid under any of the given schemas"
        
        WITHOUT the fix, this should fail with a validation error.
        WITH the fix, this should pass.
        """
        # Attempt to call with limit="3" which was causing the error
        result = controller.manage_task(
            action="list",
            limit="3"  # String "3" instead of integer 3
        )
        
        # WITHOUT fix: Should get validation error
        # WITH fix: Should succeed
        
        # For now, let's check what actually happens
        print(f"\nResult: {result}")
        print(f"Success: {result.get('success')}")
        print(f"Error: {result.get('error', 'No error')}")
        
        # The test should check if we get the specific error
        if not result["success"]:
            # Check if it's the specific validation error we're trying to fix
            error_msg = result.get("error", "")
            assert "is not valid under any of the given schemas" not in error_msg, \
                f"Got the validation error we're trying to fix: {error_msg}"
        
        # With the fix, it should succeed
        assert result["success"] is True, f"Expected success but got: {result}"