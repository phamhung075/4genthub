#!/usr/bin/env python3
"""
Test to simulate MCP server validation error with FastMCP.

This test checks if the MCP server level validation is what's causing
the "Input validation error: '3' is not valid under any of the given schemas" error.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Try to import FastMCP server components
try:
    from fastmcp.server.server import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False


@pytest.mark.skipif(not HAS_FASTMCP, reason="FastMCP not available")
class TestMCPServerValidation:
    
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

    """Test MCP server level validation."""
    
    def test_mcp_tool_registration_with_limit_parameter(self):
        """Test how the manage_task tool is registered with limit parameter."""
        from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
        from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
        
        # Create mock dependencies
        mock_facade_factory = Mock(spec=TaskFacadeFactory)
        
        # Create controller
        controller = TaskMCPController(task_facade_factory=mock_facade_factory)
        
        # Create a mock MCP server
        mock_mcp = Mock()
        registered_tools = {}
        
        def mock_tool_decorator(name, description):
            def decorator(func):
                # Store the function and its metadata
                registered_tools[name] = {
                    'func': func,
                    'description': description,
                    'annotations': func.__annotations__
                }
                return func
            return decorator
        
        mock_mcp.tool = mock_tool_decorator
        
        # Register tools
        controller.register_tools(mock_mcp)
        
        # Check if manage_task was registered
        assert 'manage_task' in registered_tools
        
        # Get the registered function
        manage_task_info = registered_tools['manage_task']
        func = manage_task_info['func']
        annotations = manage_task_info['annotations']
        
        # Check the limit parameter annotation
        print(f"\nRegistered annotations: {annotations}")
        if 'limit' in annotations:
            print(f"Limit annotation: {annotations['limit']}")
        
        # The annotation should accept Optional[int]
        # This is where the schema validation might be happening


class TestDirectParameterValidation:
    
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

    """Test parameter validation at different levels."""
    
    def test_dto_creation_with_string_limit(self):
        """Test creating ListTasksRequest with string limit."""
        from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
        
        # Try to create DTO with string limit
        try:
            request = ListTasksRequest(
                git_branch_id=None,
                status=None,
                priority=None,
                assignees=None,
                labels=None,
                limit="3"  # String instead of int
            )
            print(f"\nDTO created successfully with limit={request.limit} (type: {type(request.limit)})")
        except Exception as e:
            print(f"\nDTO creation failed: {e}")
            pytest.fail(f"DTO creation should not fail with string limit: {e}")


if __name__ == "__main__":
    # Run a quick test
    test = TestDirectParameterValidation()
    test.test_dto_creation_with_string_limit()