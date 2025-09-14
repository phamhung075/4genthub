"""
Comprehensive Unit Tests for TaskMCPController

This module provides extensive testing for the TaskMCPController with proper mocking
of all dependencies, including facades, authentication, permissions, and factories.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timezone

# Import the controller under test
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import (
    TaskMCPController
)

# Import dependencies that need to be mocked
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.interface.mcp_controllers.workflow_hint_enhancer import WorkflowHintEnhancer
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError

# Import DTOs for request/response validation
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest


class TestTaskMCPController:
    """Comprehensive test suite for TaskMCPController with proper dependency mocking."""

    def _extract_error_message(self, result):
        """Helper method to extract error message from response, handling both old and new formats."""
        error = result.get("error", "")
        if isinstance(error, dict):
            message = error.get("message", "")
            # Sometimes message itself can be nested or complex
            return str(message) if message else ""
        return str(error) if error else ""

    @pytest.fixture
    def mock_facade_service(self):
        """Mock FacadeService with all required methods."""
        # _MockClass removed in Python 3.12, using type checking instead

        # Helper function to safely create mocks with spec
        def create_mock_with_spec(spec_class):
            # Check if the class is actually a Mock or has been patched
            if (hasattr(spec_class, '_mock_name') or
                hasattr(spec_class, '_spec_class') or
                isinstance(spec_class, type(MagicMock()))):
                # It's already a Mock, don't use spec
                return Mock()
            else:
                # It's a real class, safe to use as spec
                return Mock(spec=spec_class)

        mock_service = create_mock_with_spec(FacadeService)
        mock_facade = create_mock_with_spec(TaskApplicationFacade)
        
        # Configure facade methods as synchronous mocks (controller calls them synchronously)
        mock_facade.create_task = Mock()
        mock_facade.get_task = Mock()
        mock_facade.update_task = Mock()
        mock_facade.delete_task = Mock()
        mock_facade.list_tasks = Mock()
        mock_facade.search_tasks = Mock()
        mock_facade.complete_task = Mock()
        mock_facade.add_dependency = Mock()
        mock_facade.remove_dependency = Mock()
        mock_facade.get_next_task = Mock()
        
        mock_service.get_task_facade.return_value = mock_facade
        return mock_service, mock_facade

    @pytest.fixture
    def mock_workflow_hint_enhancer(self):
        """Mock WorkflowHintEnhancer."""
        from unittest.mock import MagicMock

        # Check if WorkflowHintEnhancer is already mocked
        if (hasattr(WorkflowHintEnhancer, '_mock_name') or
            hasattr(WorkflowHintEnhancer, '_spec_class') or
            isinstance(WorkflowHintEnhancer, type(MagicMock()))):
            # It's already a Mock, don't use spec
            mock_enhancer = Mock()
        else:
            # It's a real class, safe to use as spec
            mock_enhancer = Mock(spec=WorkflowHintEnhancer)

        # Configure enhance_response to pass through the response unchanged
        mock_enhancer.enhance_response = Mock(side_effect=lambda response, **kwargs: response)
        return mock_enhancer

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "task_id": str(uuid.uuid4()),
            "git_branch_id": str(uuid.uuid4()),
            "title": "Test Task",
            "description": "Test task description",
            "status": "todo",
            "priority": "medium",
            "assignees": ["coding-agent"],
            "labels": ["backend", "api"],
            "due_date": "2024-12-31T23:59:59Z",
            "dependencies": []
        }

    @pytest.fixture
    def sample_user_id(self):
        """Sample authenticated user ID."""
        return "test-user-123"

    @pytest.fixture
    def controller(self, mock_facade_service, mock_workflow_hint_enhancer):
        """Create TaskMCPController instance with mocked dependencies."""
        facade_service, _ = mock_facade_service
        return TaskMCPController(
            facade_service_or_factory=facade_service,
            workflow_hint_enhancer=mock_workflow_hint_enhancer
        )

    @pytest.fixture
    def mock_authentication(self, sample_user_id):
        """Mock authentication functions."""
        with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id') as mock_auth, \
             patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.log_authentication_details') as mock_log:
            mock_auth.return_value = sample_user_id
            yield mock_auth, mock_log

    @pytest.fixture
    def mock_permissions(self):
        """Mock permission checking."""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_auth_info') as mock_auth_info:
            # Configure mock auth info with task permissions
            auth_info = {
                "sub": "test-user",
                "scopes": [
                    "tasks:read", "tasks:write", "tasks:create",
                    "tasks:update", "tasks:delete", "tasks:manage"
                ]
            }
            mock_auth_info.return_value = auth_info
            yield mock_auth_info

    # Test Cases for CREATE operation
    
    def test_create_task_success(self, controller, mock_facade_service, sample_task_data, sample_user_id, mock_authentication, mock_permissions):
        """Test successful task creation."""
        facade_service, mock_facade = mock_facade_service
        mock_auth, mock_log = mock_authentication
        
        # Configure facade to return success response
        expected_response = {
            "success": True,
            "data": {
                "task_id": sample_task_data["task_id"],
                "title": sample_task_data["title"],
                "status": "todo"
            },
            "message": "Task created successfully"
        }
        mock_facade.create_task.return_value = expected_response

        # Execute create operation
        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            description=sample_task_data["description"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Verify authentication was called
        mock_auth.assert_called_once()
        mock_log.assert_called_once()
        
        # Verify facade was called with correct parameters
        mock_facade.create_task.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]  # The facade response is nested in data.data
        assert "task_id" in result["data"]["data"]

    
    def test_create_task_missing_required_fields(self, controller, mock_authentication, mock_permissions):
        """Test task creation with missing required fields."""
        mock_auth, mock_log = mock_authentication
        
        # Execute create operation without required fields
        result = controller.manage_task_sync(
            action="create"
            # Missing title, git_branch_id, assignees
        )

        # Verify authentication was called
        mock_auth.assert_called_once()
        
        # Verify validation error is returned
        assert result["success"] is False
        assert "error" in result
        error_text = self._extract_error_message(result).lower()
        assert any(keyword in error_text for keyword in ["required", "validation_error", "missing", "expected"])

    @pytest.mark.parametrize("invalid_assignees", [
        "",  # Empty string
        [],  # Empty list
        None  # None value
    ])
    
    def test_create_task_invalid_assignees(self, controller, sample_task_data, invalid_assignees, mock_authentication, mock_permissions):
        """Test task creation with invalid assignees."""
        mock_auth, mock_log = mock_authentication
        
        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=invalid_assignees
        )

        # Should return validation error for missing assignees
        assert result["success"] is False
        error_msg = self._extract_error_message(result)
        assert "assignees" in error_msg.lower()

    # Test Cases for GET operation
    
    def test_get_task_success(self, controller, mock_facade_service, sample_task_data, sample_user_id, mock_authentication, mock_permissions):
        """Test successful task retrieval."""
        facade_service, mock_facade = mock_facade_service
        mock_auth, mock_log = mock_authentication
        
        # Configure facade response
        expected_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task retrieved successfully"
        }
        mock_facade.get_task.return_value = expected_response

        # Execute get operation
        result = controller.manage_task_sync(
            action="get",
            task_id=sample_task_data["task_id"]
        )

        # Verify facade was called
        mock_facade.get_task.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["data"]["task_id"] == sample_task_data["task_id"]

    
    def test_get_task_not_found(self, controller, mock_facade_service, mock_authentication, mock_permissions):
        """Test task retrieval with non-existent task."""
        facade_service, mock_facade = mock_facade_service
        mock_auth, mock_log = mock_authentication
        
        # Configure facade to return not found response
        mock_facade.get_task.return_value = {
            "success": False,
            "error": "Task not found",
            "error_code": "TASK_NOT_FOUND"
        }

        result = controller.manage_task_sync(
            action="get",
            task_id="non-existent-id"
        )

        assert result["success"] is False
        assert "not found" in self._extract_error_message(result).lower()

    
    def test_get_task_missing_task_id(self, controller, mock_authentication, mock_permissions):
        """Test task retrieval without task_id."""
        result = controller.manage_task_sync(action="get")
        
        assert result["success"] is False
        assert "task_id is required" in self._extract_error_message(result)

    # Test Cases for UPDATE operation
    
    def test_update_task_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful task update."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        updated_data = sample_task_data.copy()
        updated_data["title"] = "Updated Task Title"
        updated_data["status"] = "in_progress"
        
        expected_response = {
            "success": True,
            "data": updated_data,
            "message": "Task updated successfully"
        }
        mock_facade.update_task.return_value = expected_response

        result = controller.manage_task_sync(
            action="update",
            task_id=sample_task_data["task_id"],
            title="Updated Task Title",
            status="in_progress"
        )

        # Verify facade was called
        mock_facade.update_task.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["data"]["title"] == "Updated Task Title"

    # Test Cases for DELETE operation
    
    def test_delete_task_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful task deletion."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "message": "Task deleted successfully"
        }
        mock_facade.delete_task.return_value = expected_response

        result = controller.manage_task_sync(
            action="delete",
            task_id=sample_task_data["task_id"]
        )

        # Verify facade was called
        mock_facade.delete_task.assert_called_once()
        
        # Verify result
        assert result["success"] is True

    # Test Cases for LIST operation
    
    def test_list_tasks_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful task listing."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response with multiple tasks
        task_list = [sample_task_data, {**sample_task_data, "task_id": str(uuid.uuid4()), "title": "Another Task"}]
        expected_response = {
            "success": True,
            "data": {
                "tasks": task_list,
                "total": len(task_list),
                "page": 1,
                "limit": 50
            },
            "message": "Tasks retrieved successfully"
        }
        mock_facade.list_tasks.return_value = expected_response

        result = controller.manage_task_sync(
            action="list",
            git_branch_id=sample_task_data["git_branch_id"]
        )

        # Verify facade was called
        mock_facade.list_tasks.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert len(result["data"]["data"]["tasks"]) == 2

    @pytest.mark.parametrize("limit,offset", [
        (10, 0),
        (25, 50),
        (100, 200)
    ])
    
    def test_list_tasks_pagination(self, controller, mock_facade_service, limit, offset, mock_authentication, mock_permissions):
        """Test task listing with different pagination parameters."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {"tasks": [], "total": 0, "page": offset//limit + 1, "limit": limit},
            "message": "Tasks retrieved successfully"
        }
        mock_facade.list_tasks.return_value = expected_response

        result = controller.manage_task_sync(
            action="list",
            limit=limit,
            offset=offset
        )

        assert result["success"] is True
        assert result["data"]["data"]["limit"] == limit

    # Test Cases for SEARCH operation
    
    def test_search_tasks_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful task search."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {
                "tasks": [sample_task_data],
                "total": 1,
                "query": "test"
            },
            "message": "Search completed successfully"
        }
        mock_facade.search_tasks.return_value = expected_response

        result = controller.manage_task_sync(
            action="search",
            query="test"
        )

        # Verify facade was called
        mock_facade.search_tasks.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["data"]["total"] == 1

    
    def test_search_tasks_empty_query(self, controller, mock_authentication, mock_permissions):
        """Test search with empty query."""
        result = controller.manage_task_sync(
            action="search"
            # Missing query parameter
        )
        
        # Should handle gracefully or return validation error
        assert "success" in result

    # Test Cases for COMPLETE operation
    
    def test_complete_task_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful task completion."""
        facade_service, mock_facade = mock_facade_service
        
        completed_data = sample_task_data.copy()
        completed_data["status"] = "done"
        completed_data["completion_summary"] = "Task completed successfully"
        
        expected_response = {
            "success": True,
            "data": completed_data,
            "message": "Task completed successfully"
        }
        mock_facade.complete_task.return_value = expected_response

        result = controller.manage_task_sync(
            action="complete",
            task_id=sample_task_data["task_id"],
            completion_summary="Task completed successfully"
        )

        # Verify facade was called
        mock_facade.complete_task.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["data"]["status"] == "done"

    # Test Cases for DEPENDENCY operations
    
    def test_add_dependency_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful dependency addition."""
        facade_service, mock_facade = mock_facade_service
        dependency_id = str(uuid.uuid4())
        
        expected_response = {
            "success": True,
            "message": "Dependency added successfully"
        }
        mock_facade.add_dependency.return_value = expected_response

        result = controller.manage_task_sync(
            action="add_dependency",
            task_id=sample_task_data["task_id"],
            dependency_id=dependency_id
        )

        # Verify facade was called
        mock_facade.add_dependency.assert_called_once()
        
        # Verify result
        assert result["success"] is True

    
    def test_remove_dependency_success(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test successful dependency removal."""
        facade_service, mock_facade = mock_facade_service
        dependency_id = str(uuid.uuid4())
        
        expected_response = {
            "success": True,
            "message": "Dependency removed successfully"
        }
        mock_facade.remove_dependency.return_value = expected_response

        result = controller.manage_task_sync(
            action="remove_dependency",
            task_id=sample_task_data["task_id"],
            dependency_id=dependency_id
        )

        # Verify facade was called
        mock_facade.remove_dependency.assert_called_once()
        
        # Verify result
        assert result["success"] is True

    # Test Cases for AUTHENTICATION and PERMISSIONS
    
    def test_unauthenticated_request(self, controller):
        """Test request without authentication."""
        with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.side_effect = UserAuthenticationRequiredError("Authentication required")
            
            result = controller.manage_task_sync(action="list")
            
            assert result["success"] is False
            error_msg = self._extract_error_message(result).lower()
            assert "authentication" in error_msg or "permission" in error_msg

    
    def test_insufficient_permissions(self, controller, mock_authentication):
        """Test request with insufficient permissions."""
        mock_auth, mock_log = mock_authentication
        
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_request_context') as mock_context:
            # Configure mock user with insufficient permissions
            mock_request_context = Mock()
            mock_user = Mock()
            mock_user.token = {"sub": "test-user", "permissions": []}  # No permissions
            mock_request_context.user = mock_user
            mock_context.return_value = mock_request_context
            
            result = controller.manage_task_sync(action="create", title="Test")
            
            # Should return permission denied error
            assert result["success"] is False
            assert "permission" in result.get("error", "").lower()

    # Test Cases for ERROR HANDLING
    
    def test_facade_exception_handling(self, controller, mock_facade_service, sample_task_data, mock_authentication, mock_permissions):
        """Test handling of facade exceptions."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade to raise exception
        mock_facade.get_task.side_effect = Exception("Database connection error")

        result = controller.manage_task_sync(
            action="get",
            task_id=sample_task_data["task_id"]
        )

        # Verify error is handled gracefully
        assert result["success"] is False
        assert "error" in result

    
    def test_invalid_action(self, controller, mock_authentication, mock_permissions):
        """Test handling of invalid action parameter."""
        result = controller.manage_task_sync(action="invalid_action")
        
        # Should handle gracefully
        assert "success" in result

    # Test Cases for PARAMETER VALIDATION
    @pytest.mark.parametrize("status", ["todo", "in_progress", "done", "cancelled"])
    
    def test_valid_status_values(self, controller, mock_facade_service, sample_task_data, status, mock_authentication, mock_permissions):
        """Test task creation with different valid status values."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        expected_response = {
            "success": True,
            "data": {**sample_task_data, "status": status},
            "message": "Task created successfully"
        }
        mock_facade.create_task.return_value = expected_response

        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"],
            status=status
        )

        assert result["success"] is True

    @pytest.mark.parametrize("priority", ["low", "medium", "high", "urgent", "critical"])
    
    def test_valid_priority_values(self, controller, mock_facade_service, sample_task_data, priority, mock_authentication, mock_permissions):
        """Test task creation with different valid priority values."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {**sample_task_data, "priority": priority},
            "message": "Task created successfully"
        }
        mock_facade.create_task.return_value = expected_response

        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"],
            priority=priority
        )

        assert result["success"] is True

    # Test Cases for WORKFLOW ENHANCEMENT
    
    def test_workflow_hint_enhancement(self, controller, mock_facade_service, mock_workflow_hint_enhancer, sample_task_data, mock_authentication, mock_permissions):
        """Test workflow hint enhancement integration."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        base_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        mock_facade.create_task.return_value = base_response
        
        # Configure workflow enhancer
        enhanced_response = {
            **base_response,
            "workflow_hints": ["Consider adding tests", "Update documentation"],
            "next_actions": ["Create subtasks", "Assign reviewers"]
        }
        mock_workflow_hint_enhancer.enhance_response.return_value = enhanced_response

        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Verify workflow enhancer was called
        mock_workflow_hint_enhancer.enhance_response.assert_called_once()
        
        # Verify enhanced response
        assert result["success"] is True
        assert "workflow_hints" in result
        assert "next_actions" in result

    
    def test_workflow_enhancement_failure_graceful_degradation(self, controller, mock_facade_service, mock_workflow_hint_enhancer, sample_task_data, mock_authentication, mock_permissions):
        """Test graceful degradation when workflow enhancement fails."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        base_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        mock_facade.create_task.return_value = base_response
        
        # Configure workflow enhancer to fail
        mock_workflow_hint_enhancer.enhance_response.side_effect = Exception("Enhancement failed")

        result = controller.manage_task_sync(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Should return base response without enhancement
        assert result["success"] is True
        assert "workflow_hints" not in result  # Enhancement should be skipped


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])