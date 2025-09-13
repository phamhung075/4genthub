"""
Tests for Context Operation Handler

Focus on parameter handling and normalization for git_branch_id -> branch_id.
"""

import pytest
from unittest.mock import Mock, patch
from fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler import ContextOperationHandler
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter


class TestContextOperationHandler:
    """Test Context Operation Handler parameter normalization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.response_formatter = StandardResponseFormatter()
        self.handler = ContextOperationHandler(self.response_formatter)

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_create_task_context_git_branch_id_normalization(self, mock_get_user_id):
        """Test that git_branch_id parameter is normalized to branch_id in task context data."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "task-123", "branch_id": "branch-456"},
            "message": "Context created"
        }

        # Test data
        git_branch_id = "branch-456"
        task_id = "task-123"
        data = {"task_data": {"title": "Test Task"}}

        # Call handler
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="task",
            context_id=task_id,
            git_branch_id=git_branch_id,
            data=data
        )

        # Verify facade was called with normalized data
        mock_facade.create_context.assert_called_once()
        call_args = mock_facade.create_context.call_args[1]

        assert call_args["level"] == "task"
        assert call_args["context_id"] == task_id
        assert call_args["user_id"] == "test-user-id"

        # Verify git_branch_id was normalized to branch_id
        context_data = call_args["data"]
        assert context_data["branch_id"] == git_branch_id
        assert context_data["parent_branch_id"] == git_branch_id
        assert context_data["parent_branch_context_id"] == git_branch_id
        assert context_data["task_data"]["title"] == "Test Task"

        # Verify successful response
        assert result is not None

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_create_task_context_existing_branch_id_preserved(self, mock_get_user_id):
        """Test that existing branch_id in data is preserved."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "task-123", "branch_id": "existing-branch"},
            "message": "Context created"
        }

        # Test data with existing branch_id
        git_branch_id = "branch-456"
        task_id = "task-123"
        data = {
            "branch_id": "existing-branch", # This should be preserved
            "task_data": {"title": "Test Task"}
        }

        # Call handler
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="task",
            context_id=task_id,
            git_branch_id=git_branch_id,
            data=data
        )

        # Verify facade was called
        mock_facade.create_context.assert_called_once()
        call_args = mock_facade.create_context.call_args[1]

        # Verify existing branch_id was preserved
        context_data = call_args["data"]
        assert context_data["branch_id"] == "existing-branch"  # Original preserved
        # Parent references should still be added
        assert context_data["parent_branch_id"] == git_branch_id
        assert context_data["parent_branch_context_id"] == git_branch_id

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_create_task_context_existing_parent_branch_id_preserved(self, mock_get_user_id):
        """Test that existing parent_branch_id in data is preserved."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "task-123", "branch_id": "branch-456"},
            "message": "Context created"
        }

        # Test data with existing parent_branch_id
        git_branch_id = "branch-456"
        task_id = "task-123"
        data = {
            "parent_branch_id": "existing-parent", # This should be preserved
            "task_data": {"title": "Test Task"}
        }

        # Call handler
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="task",
            context_id=task_id,
            git_branch_id=git_branch_id,
            data=data
        )

        # Verify facade was called
        mock_facade.create_context.assert_called_once()
        call_args = mock_facade.create_context.call_args[1]

        # Verify existing parent_branch_id was preserved
        context_data = call_args["data"]
        # Since parent_branch_id exists, branch_id should still be added
        assert context_data["branch_id"] == git_branch_id
        assert context_data["parent_branch_id"] == "existing-parent"  # Original preserved
        # Only parent_branch_context_id should be added
        assert context_data["parent_branch_context_id"] == git_branch_id

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_create_non_task_context_no_normalization(self, mock_get_user_id):
        """Test that non-task contexts don't get git_branch_id normalization."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "branch-123"},
            "message": "Context created"
        }

        # Test data
        git_branch_id = "branch-456"
        branch_id = "branch-123"
        data = {"branch_workflow": {"steps": ["analyze", "implement"]}}

        # Call handler for branch level (not task)
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="branch",
            context_id=branch_id,
            git_branch_id=git_branch_id,
            data=data
        )

        # Verify facade was called
        mock_facade.create_context.assert_called_once()
        call_args = mock_facade.create_context.call_args[1]

        # Verify no normalization was done (data unchanged)
        context_data = call_args["data"]
        assert "branch_id" not in context_data
        assert "parent_branch_id" not in context_data
        assert "parent_branch_context_id" not in context_data
        assert context_data["branch_workflow"]["steps"] == ["analyze", "implement"]

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_create_task_context_no_data_provided(self, mock_get_user_id):
        """Test that handler works correctly when no data is provided."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "task-123"},
            "message": "Context created"
        }

        # Call handler without data
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="task",
            context_id="task-123",
            git_branch_id="branch-456",
            data=None  # No data provided
        )

        # Verify facade was called
        mock_facade.create_context.assert_called_once()
        call_args = mock_facade.create_context.call_args[1]

        # Verify data is None (no normalization attempted)
        assert call_args["data"] is None

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_error_handling(self, mock_get_user_id):
        """Test error handling in context operations."""
        mock_get_user_id.return_value = "test-user"
        
        # Mock facade that raises exception
        mock_facade = Mock()
        mock_facade.create_context.side_effect = Exception("Test error")
        
        # Call handler
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="create",
            level="task",
            context_id="task-123",
            git_branch_id="branch-456",
            data={"task_data": {"title": "Test Task"}}
        )
        
        # Verify error response
        assert result["success"] is False
        assert "Test error" in result["error"]["message"]
        assert result["error"]["code"] == "INTERNAL_ERROR"

    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.handlers.context_operation_handler.get_authenticated_user_id')
    def test_unknown_action_error(self, mock_get_user_id):
        """Test that unknown actions return appropriate error."""
        # Mock authentication
        mock_get_user_id.return_value = "test-user-id"

        # Mock facade
        mock_facade = Mock()

        # Call handler with unknown action
        result = self.handler.handle_context_operation(
            facade=mock_facade,
            action="unknown_action",
            level="task",
            context_id="task-123"
        )

        # Verify error response
        assert result["success"] is False
        assert "Unknown action: unknown_action" in result["error"]["message"]
        assert result["error"]["code"] == "OPERATION_FAILED"
        assert "Valid actions:" in result["error"]["message"]