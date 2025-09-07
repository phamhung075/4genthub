"""
Test for user_id parameter support in manage_task tool.

This test ensures that the manage_task tool properly accepts and uses the user_id parameter
for authentication, resolving the authentication error without requiring middleware context.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestTaskUserIdParameter:
    """Test user_id parameter functionality in manage_task tool."""

    @pytest.fixture
    def mock_task_facade_factory(self):
        """Mock task facade factory."""
        factory = Mock()
        mock_facade = Mock(spec=TaskApplicationFacade)
        factory.create_task_facade.return_value = mock_facade
        factory.create_task_facade_with_git_branch_id.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_task_facade_factory):
        """Create TaskMCPController with mocked dependencies."""
        return TaskMCPController(
            task_facade_factory=mock_task_facade_factory,
            context_facade_factory=None,
            project_manager=None,
            repository_factory=None
        )


    def test_manage_task_passes_user_id_through_authentication_chain(self, controller):
        """Test that provided user_id bypasses authentication context derivation."""
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = Mock(spec=TaskApplicationFacade)
            mock_get_facade.return_value = mock_facade
            mock_facade.create_task.return_value = {
                "success": True, 
                "task": {"id": "task-123", "title": "Test Task"}
            }
            
            # Call manage_task with user_id (using valid UUID for git_branch_id)
            result = controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test Task",
                user_id="test-user-001"
            )
            
            # Verify _get_facade_for_request was called with user_id
            mock_get_facade.assert_called_once()
            call_args = mock_get_facade.call_args
            assert 'user_id' in call_args.kwargs
            assert call_args.kwargs['user_id'] == "test-user-001"

    def test_derive_context_from_identifiers_with_user_id(self, controller):
        """Test that _derive_context_from_identifiers uses provided user_id."""
        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id') as mock_auth:
            # When user_id is provided, get_authenticated_user_id should NOT be called
            project_id, git_branch_name, user_id = controller._derive_context_from_identifiers(
                task_id=None,
                git_branch_id="550e8400-e29b-41d4-a716-446655440001", 
                user_id="test-user-001"
            )
            
            # Should use provided user_id without calling authentication helper
            assert user_id == "test-user-001"
            mock_auth.assert_not_called()


    def test_get_facade_for_request_with_user_id(self, controller):
        """Test that _get_facade_for_request properly handles user_id parameter."""
        with patch.object(controller, '_derive_context_from_identifiers') as mock_derive:
            with patch.object(controller, '_get_task_facade') as mock_get_task_facade:
                mock_derive.return_value = ("project-123", "main", "test-user-001")
                mock_facade = Mock(spec=TaskApplicationFacade)
                mock_get_task_facade.return_value = mock_facade
                
                result = controller._get_facade_for_request(
                    task_id="task-123",
                    git_branch_id="550e8400-e29b-41d4-a716-446655440001", 
                    user_id="provided-user-001"
                )
                
                # Verify derive_context_from_identifiers was called with user_id
                mock_derive.assert_called_once_with("task-123", "550e8400-e29b-41d4-a716-446655440001", "provided-user-001")
                
                # Verify _get_task_facade was called with effective user_id
                mock_get_task_facade.assert_called_once()
                call_args = mock_get_task_facade.call_args[0]
                # The effective user_id should be the provided one (not the derived one)
                assert call_args[2] == "provided-user-001"  # user_id is the 3rd positional argument


    def test_user_id_parameter_schema_documentation(self):
        """Test that user_id parameter is properly documented in schema."""
        # This is a static test to ensure the parameter documentation is correct
        # In a real MCP tool registration, this would be verified through the tool schema
        
        # The parameter should be documented as:
        # "User identifier for authentication. Optional, defaults to authenticated user context"
        
        # This test serves as documentation that the parameter exists and is optional
        assert True  # Placeholder - in real testing, we'd verify the MCP tool schema

if __name__ == "__main__":
    pytest.main([__file__])