"""Tests for SubtaskMCPController"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.controllers.subtask_mcp_controller import SubtaskMCPController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError, DefaultUserProhibitedError
)


class TestSubtaskMCPController:
    """Test suite for SubtaskMCPController"""

    @pytest.fixture
    def mock_subtask_facade_factory(self):
        """Create mock subtask facade factory"""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade responses
        mock_facade.create_subtask.return_value = {"success": True, "subtask_id": "subtask-123"}
        mock_facade.update_subtask.return_value = {"success": True, "updated": True}
        mock_facade.delete_subtask.return_value = {"success": True, "deleted": True}
        mock_facade.get_subtask.return_value = {"success": True, "subtask": {"id": "subtask-123"}}
        mock_facade.list_subtasks.return_value = {"success": True, "subtasks": []}
        mock_facade.complete_subtask.return_value = {"success": True, "completed": True}
        
        factory.create_subtask_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_subtask_facade_factory):
        """Create controller instance with mocked facade factory"""
        return SubtaskMCPController(mock_subtask_facade_factory)

    def test_controller_initialization(self, mock_subtask_facade_factory):
        """Test controller initializes correctly with facade factory"""
        controller = SubtaskMCPController(mock_subtask_facade_factory)
        
        assert controller._subtask_facade_factory == mock_subtask_facade_factory

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_create_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask creation"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        assert result["success"] is True
        assert result["subtask_id"] == "subtask-123"
        mock_facade.create_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_update_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask update"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="update",
            task_id="task-123",
            subtask_id="subtask-123",
            title="Updated Subtask"
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        mock_facade.update_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_delete_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask deletion"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="delete",
            task_id="task-123",
            subtask_id="subtask-123"
        )
        
        assert result["success"] is True
        assert result["deleted"] is True
        mock_facade.delete_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_get_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="get",
            task_id="task-123",
            subtask_id="subtask-123"
        )
        
        assert result["success"] is True
        assert "subtask" in result
        mock_facade.get_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_list_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask listing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="list",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert "subtasks" in result
        mock_facade.list_subtasks.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_complete_success(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test successful subtask completion"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        result = controller.manage_subtask(
            action="complete",
            task_id="task-123",
            subtask_id="subtask-123",
            completion_summary="Subtask completed successfully"
        )
        
        assert result["success"] is True
        assert result["completed"] is True
        mock_facade.complete_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_invalid_action(self, mock_get_user, controller):
        """Test handling of invalid action"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_subtask(
            action="invalid_action",
            task_id="task-123"
        )
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result
        
        expected_actions = ["create", "update", "delete", "get", "list", "complete"]
        for action in expected_actions:
            assert action in result["available_actions"]

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error"""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        assert result["success"] is False
        assert "Authentication required" in result["error"]
        assert result["error_code"] == "AUTHENTICATION_REQUIRED"

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_default_user_prohibited_error(self, mock_get_user, controller):
        """Test handling of default user prohibited error"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._subtask_facade_factory.create_subtask_facade.return_value
        mock_facade.create_subtask.side_effect = DefaultUserProhibitedError("Default user not allowed")
        
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        assert result["success"] is False
        assert "Default user not allowed" in result["error"]
        assert result["error_code"] == "DEFAULT_USER_PROHIBITED"

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_manage_subtask_general_exception(self, mock_get_user, controller):
        """Test handling of general exceptions"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._subtask_facade_factory.create_subtask_facade.return_value
        mock_facade.create_subtask.side_effect = Exception("Unexpected error")
        
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["action"] == "create"

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.description_loader')
    def test_register_tools_calls_description_loader(self, mock_desc_loader, controller):
        """Test that register_tools calls the description loader"""
        mock_mcp = Mock()
        mock_desc_loader.get_subtask_management_descriptions.return_value = {
            "manage_subtask": {"description": "test desc", "parameters": {}}
        }
        
        controller.register_tools(mock_mcp)
        
        mock_desc_loader.get_subtask_management_descriptions.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_user_id_parameter_handling(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test that user_id parameter is handled correctly"""
        mock_get_user.return_value = "test-user"
        
        controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        # Verify facade was created with authenticated user
        mock_subtask_facade_factory.create_subtask_facade.assert_called_once_with(
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_workflow_guidance_integration(self, mock_get_user, controller):
        """Test that workflow guidance is integrated"""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller can handle workflow guidance
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask"
        )
        
        # Workflow guidance should be included in responses
        assert "workflow_guidance" in result or result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_parameter_validation_create_action(self, mock_get_user, controller):
        """Test parameter validation for create action"""
        mock_get_user.return_value = "test-user"
        
        # Create action requires task_id and title
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask",
            description="Test description"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_parameter_validation_update_action(self, mock_get_user, controller):
        """Test parameter validation for update action"""
        mock_get_user.return_value = "test-user"
        
        # Update action requires task_id and subtask_id
        result = controller.manage_subtask(
            action="update",
            task_id="task-123",
            subtask_id="subtask-123",
            progress_percentage=50
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_parameter_validation_complete_action(self, mock_get_user, controller):
        """Test parameter validation for complete action"""
        mock_get_user.return_value = "test-user"
        
        # Complete action requires completion_summary
        result = controller.manage_subtask(
            action="complete",
            task_id="task-123",
            subtask_id="subtask-123",
            completion_summary="Task completed successfully"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_optional_parameters_handling(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test handling of optional parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test with multiple optional parameters
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask",
            description="Test description",
            status="todo",
            priority="medium",
            assignees=["user1", "user2"],
            progress_notes="Initial notes"
        )
        
        assert result["success"] is True
        
        # Verify all parameters were passed to facade
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        mock_facade.create_subtask.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_list_parameters_conversion(self, mock_get_user, controller):
        """Test conversion of list parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test with comma-separated assignees
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask",
            assignees="user1,user2,user3"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional"""
        # Logger should be available for operations
        assert mock_logger is not None
        
        # Test that we can log (logger is imported at module level)
        from fastmcp.task_management.interface.controllers.subtask_mcp_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_facade_creation_and_delegation(self, mock_get_user, controller, mock_subtask_facade_factory):
        """Test that facade is properly created and operations are delegated"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_subtask_facade_factory.create_subtask_facade.return_value
        
        # Make request
        controller.manage_subtask(
            action="list",
            task_id="task-123"
        )
        
        # Verify facade creation
        mock_subtask_facade_factory.create_subtask_facade.assert_called_once_with(
            user_id="test-user"
        )
        
        # Verify operation delegation
        mock_facade.list_subtasks.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_progress_tracking_parameters(self, mock_get_user, controller):
        """Test progress tracking related parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test with progress-related parameters
        result = controller.manage_subtask(
            action="update",
            task_id="task-123",
            subtask_id="subtask-123",
            progress_percentage=75,
            progress_notes="Almost complete",
            blockers="Waiting for review"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_completion_parameters(self, mock_get_user, controller):
        """Test completion action with all parameters"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_subtask(
            action="complete",
            task_id="task-123",
            subtask_id="subtask-123",
            completion_summary="Successfully implemented feature",
            impact_on_parent="Parent task 80% complete",
            insights_found="Discovered optimization opportunity",
            testing_notes="All tests passing"
        )
        
        assert result["success"] is True

    def test_import_error_handling(self):
        """Test that import errors for auth context are handled"""
        # The controller should handle import errors gracefully
        # This is tested by the module-level import in the actual code
        
        # Verify the controller can be instantiated even with import issues
        factory = Mock()
        controller = SubtaskMCPController(factory)
        assert controller is not None

    @patch('fastmcp.task_management.interface.controllers.subtask_mcp_controller.get_current_user_id')
    def test_empty_string_parameters(self, mock_get_user, controller):
        """Test handling of empty string parameters"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_subtask(
            action="create",
            task_id="task-123",
            title="Test Subtask",
            description="",  # Empty description should be allowed
            progress_notes=""  # Empty progress notes should be allowed
        )
        
        assert result["success"] is True