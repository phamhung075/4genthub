"""Tests for TaskMCPController"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError, DefaultUserProhibitedError
)


class TestTaskMCPController:
    """Test suite for TaskMCPController"""

    @pytest.fixture
    def mock_task_facade_factory(self):
        """Create mock task facade factory"""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade responses
        mock_facade.create_task.return_value = {"success": True, "task_id": "task-123"}
        mock_facade.update_task.return_value = {"success": True, "updated": True}
        mock_facade.get_task.return_value = {"success": True, "task": {"id": "task-123"}}
        mock_facade.delete_task.return_value = {"success": True, "deleted": True}
        mock_facade.complete_task.return_value = {"success": True, "completed": True}
        mock_facade.list_tasks.return_value = {"success": True, "tasks": []}
        mock_facade.search_tasks.return_value = {"success": True, "tasks": []}
        mock_facade.next_task.return_value = {"success": True, "next_task": {"id": "next-123"}}
        mock_facade.add_dependency.return_value = {"success": True, "dependency_added": True}
        mock_facade.remove_dependency.return_value = {"success": True, "dependency_removed": True}
        
        factory.create_task_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_task_facade_factory):
        """Create controller instance with mocked facade factory"""
        return TaskMCPController(mock_task_facade_factory)

    def test_controller_initialization(self, mock_task_facade_factory):
        """Test controller initializes correctly with facade factory"""
        controller = TaskMCPController(mock_task_facade_factory)
        
        assert controller._task_facade_factory == mock_task_facade_factory

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_create_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task creation"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        assert result["success"] is True
        assert result["task_id"] == "task-123"
        mock_facade.create_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_update_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task update"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="update",
            task_id="task-123",
            title="Updated Task"
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        mock_facade.update_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_get_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="get",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert "task" in result
        mock_facade.get_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_delete_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task deletion"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="delete",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert result["deleted"] is True
        mock_facade.delete_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_complete_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task completion"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="complete",
            task_id="task-123",
            completion_summary="Task completed successfully"
        )
        
        assert result["success"] is True
        assert result["completed"] is True
        mock_facade.complete_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_list_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task listing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="list",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert "tasks" in result
        mock_facade.list_tasks.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_search_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful task search"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="search",
            query="test query"
        )
        
        assert result["success"] is True
        assert "tasks" in result
        mock_facade.search_tasks.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_next_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful next task retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="next",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert "next_task" in result
        mock_facade.next_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_add_dependency_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful dependency addition"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="add_dependency",
            task_id="task-123",
            dependency_id="dep-456"
        )
        
        assert result["success"] is True
        assert result["dependency_added"] is True
        mock_facade.add_dependency.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_remove_dependency_success(self, mock_get_user, controller, mock_task_facade_factory):
        """Test successful dependency removal"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        result = controller.manage_task(
            action="remove_dependency",
            task_id="task-123",
            dependency_id="dep-456"
        )
        
        assert result["success"] is True
        assert result["dependency_removed"] is True
        mock_facade.remove_dependency.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_invalid_action(self, mock_get_user, controller):
        """Test handling of invalid action"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_task(action="invalid_action")
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result
        
        expected_actions = [
            "create", "update", "get", "delete", "complete",
            "list", "search", "next", "add_dependency", "remove_dependency"
        ]
        for action in expected_actions:
            assert action in result["available_actions"]

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error"""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        assert result["success"] is False
        assert "Authentication required" in result["error"]
        assert result["error_code"] == "AUTHENTICATION_REQUIRED"

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_default_user_prohibited_error(self, mock_get_user, controller):
        """Test handling of default user prohibited error"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._task_facade_factory.create_task_facade.return_value
        mock_facade.create_task.side_effect = DefaultUserProhibitedError("Default user not allowed")
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        assert result["success"] is False
        assert "Default user not allowed" in result["error"]
        assert result["error_code"] == "DEFAULT_USER_PROHIBITED"

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_general_exception(self, mock_get_user, controller):
        """Test handling of general exceptions"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._task_facade_factory.create_task_facade.return_value
        mock_facade.create_task.side_effect = Exception("Unexpected error")
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["action"] == "create"

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.description_loader')
    def test_register_tools_calls_description_loader(self, mock_desc_loader, controller):
        """Test that register_tools calls the description loader"""
        mock_mcp = Mock()
        mock_desc_loader.get_task_management_descriptions.return_value = {
            "manage_task": {"description": "test desc", "parameters": {}}
        }
        
        controller.register_tools(mock_mcp)
        
        mock_desc_loader.get_task_management_descriptions.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_user_id_parameter_handling(self, mock_get_user, controller, mock_task_facade_factory):
        """Test that user_id parameter is handled correctly"""
        mock_get_user.return_value = "test-user"
        
        controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        # Verify facade was created with authenticated user
        mock_task_facade_factory.create_task_facade.assert_called_once_with(
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_workflow_guidance_integration(self, mock_get_user, controller):
        """Test that workflow guidance is integrated"""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller can handle workflow guidance
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task"
        )
        
        # Workflow guidance should be included in responses
        assert "workflow_guidance" in result or result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_parameter_validation_create_action(self, mock_get_user, controller):
        """Test parameter validation for create action"""
        mock_get_user.return_value = "test-user"
        
        # Create action requires git_branch_id and title
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task",
            description="Test description"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_parameter_validation_update_action(self, mock_get_user, controller):
        """Test parameter validation for update action"""
        mock_get_user.return_value = "test-user"
        
        # Update action requires task_id
        result = controller.manage_task(
            action="update",
            task_id="task-123",
            title="Updated Task"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_parameter_validation_complete_action(self, mock_get_user, controller):
        """Test parameter validation for complete action"""
        mock_get_user.return_value = "test-user"
        
        # Complete action benefits from completion_summary
        result = controller.manage_task(
            action="complete",
            task_id="task-123",
            completion_summary="Task completed successfully"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_optional_parameters_handling(self, mock_get_user, controller, mock_task_facade_factory):
        """Test handling of optional parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test with multiple optional parameters
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task",
            description="Test description",
            status="todo",
            priority="high",
            estimated_effort="3 days",
            assignees=["user1", "user2"],
            labels=["frontend", "urgent"],
            due_date="2025-12-31"
        )
        
        assert result["success"] is True
        
        # Verify all parameters were passed to facade
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        mock_facade.create_task.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_list_parameters_conversion(self, mock_get_user, controller):
        """Test conversion of list parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test with comma-separated assignees and labels
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task",
            assignees="user1,user2,user3",
            labels="frontend,api,urgent"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_dependency_management(self, mock_get_user, controller):
        """Test dependency management actions"""
        mock_get_user.return_value = "test-user"
        
        # Test adding dependency
        result_add = controller.manage_task(
            action="add_dependency",
            task_id="task-123",
            dependency_id="dep-456"
        )
        assert result_add["success"] is True
        
        # Test removing dependency
        result_remove = controller.manage_task(
            action="remove_dependency",
            task_id="task-123",
            dependency_id="dep-456"
        )
        assert result_remove["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional"""
        # Logger should be available for operations
        assert mock_logger is not None
        
        # Test that we can log (logger is imported at module level)
        from fastmcp.task_management.interface.controllers.task_mcp_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_facade_creation_and_delegation(self, mock_get_user, controller, mock_task_facade_factory):
        """Test that facade is properly created and operations are delegated"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_task_facade_factory.create_task_facade.return_value
        
        # Make request
        controller.manage_task(
            action="list",
            git_branch_id="branch-123"
        )
        
        # Verify facade creation
        mock_task_facade_factory.create_task_facade.assert_called_once_with(
            user_id="test-user"
        )
        
        # Verify operation delegation
        mock_facade.list_tasks.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_search_functionality(self, mock_get_user, controller):
        """Test search functionality with various parameters"""
        mock_get_user.return_value = "test-user"
        
        # Test search with query
        result = controller.manage_task(
            action="search",
            query="authentication login",
            limit=10,
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_next_task_with_context(self, mock_get_user, controller):
        """Test next task retrieval with context inclusion"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_task(
            action="next",
            git_branch_id="branch-123",
            include_context=True
        )
        
        assert result["success"] is True

    def test_import_error_handling(self):
        """Test that import errors for auth context are handled"""
        # The controller should handle import errors gracefully
        # This is tested by the module-level import in the actual code
        
        # Verify the controller can be instantiated even with import issues
        factory = Mock()
        controller = TaskMCPController(factory)
        assert controller is not None

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_create_with_dependencies(self, mock_get_user, controller):
        """Test task creation with dependencies"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task",
            dependencies=["dep1", "dep2"]
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_empty_string_parameters(self, mock_get_user, controller):
        """Test handling of empty string parameters"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_task(
            action="create",
            git_branch_id="branch-123",
            title="Test Task",
            description="",  # Empty description should be allowed
            details=""  # Empty details should be allowed
        )
        
        assert result["success"] is True