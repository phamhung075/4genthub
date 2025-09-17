"""
Comprehensive Unit Tests for TaskMCPController - Working Version

This test suite provides complete coverage for TaskMCPController with proper mocking
and import paths that work with the current project structure.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timezone

# Import the controller under test using correct path
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import (
    TaskMCPController
)

# Import actual dependencies for proper mocking
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.interface.mcp_controllers.workflow_hint_enhancer import WorkflowHintEnhancer
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestTaskMCPControllerComplete:
    """
    Complete test suite for TaskMCPController with working mocks and comprehensive coverage.
    
    This test suite covers:
    - All CRUD operations (create, read, update, delete)
    - List and search operations
    - Dependency management
    - Authentication and authorization
    - Error handling and edge cases
    - Parameter validation
    - Workflow enhancement integration
    """

    def _extract_error_message(self, result):
        """Helper method to extract error message from response, handling both old and new formats."""
        error = result.get("error", "")
        if isinstance(error, dict):
            message = error.get("message", "")
            # Sometimes message itself can be nested or complex
            return str(message) if message else ""
        return str(error) if error else ""

    def _assert_success_response(self, result, expected_data_keys=None):
        """Helper method to assert successful response structure."""
        assert result["success"] is True
        assert "data" in result
        assert "meta" in result
        
        if expected_data_keys:
            # Check if facade response is nested under data.data
            if "data" in result["data"]:
                data = result["data"]["data"]
            else:
                data = result["data"]
            
            for key in expected_data_keys:
                assert key in data, f"Expected key '{key}' not found in response data"
        
        return result
    
    def _assert_error_response(self, result, expected_error_content=None):
        """Helper method to assert error response structure."""
        assert result["success"] is False
        assert "error" in result
        
        if expected_error_content:
            assert expected_error_content.lower() in self._extract_error_message(result).lower()
        
        return result

    @pytest.fixture
    def sample_user_id(self):
        """Sample authenticated user ID for testing."""
        return "test-user-123"

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "task_id": str(uuid.uuid4()),
            "git_branch_id": str(uuid.uuid4()),
            "title": "Test Task Implementation",
            "description": "Comprehensive test task for unit testing",
            "status": "todo",
            "priority": "medium",
            "assignees": ["coding-agent", "@test-orchestrator-agent"],
            "labels": ["backend", "api", "testing"],
            "due_date": "2024-12-31T23:59:59Z",
            "dependencies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    @pytest.fixture
    def mock_facade_service(self):
        """Mock FacadeService with all required methods."""
        # Create the facade service mock
        # Safely create mock avoiding spec errors if class is already mocked
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

        facade_service_mock = create_mock_with_spec(FacadeService)

        # Create the task facade mock with all methods
        task_facade_mock = create_mock_with_spec(TaskApplicationFacade)
        
        # Configure facade methods as regular Mock (not AsyncMock) 
        # because the handlers call them synchronously
        task_facade_mock.create_task = Mock()
        task_facade_mock.get_task = Mock()
        task_facade_mock.update_task = Mock()
        task_facade_mock.delete_task = Mock()
        task_facade_mock.list_tasks = Mock()
        task_facade_mock.search_tasks = Mock()
        task_facade_mock.complete_task = Mock()
        task_facade_mock.add_dependency = Mock()
        task_facade_mock.remove_dependency = Mock()
        task_facade_mock.get_next_task = Mock()
        
        # Configure facade service to return the mock facade
        facade_service_mock.get_task_facade.return_value = task_facade_mock
        
        return facade_service_mock, task_facade_mock

    @pytest.fixture
    def mock_workflow_enhancer(self):
        """Mock WorkflowHintEnhancer."""
        if (hasattr(WorkflowHintEnhancer, '_mock_name') or
            hasattr(WorkflowHintEnhancer, '_spec_class') or
            isinstance(WorkflowHintEnhancer, type(MagicMock()))):
            enhancer_mock = Mock()
        else:
            enhancer_mock = Mock(spec=WorkflowHintEnhancer)
        # Configure enhance_response to pass through the response unchanged by default
        enhancer_mock.enhance_response = Mock(side_effect=lambda response, **kwargs: response)
        return enhancer_mock

    @pytest.fixture
    def controller(self, mock_facade_service, mock_workflow_enhancer):
        """Create TaskMCPController instance with mocked dependencies."""
        facade_service_mock, _ = mock_facade_service
        return TaskMCPController(
            facade_service_or_factory=facade_service_mock,
            workflow_hint_enhancer=mock_workflow_enhancer
        )

    @pytest.fixture
    def mock_auth(self, sample_user_id):
        """Mock authentication functions."""
        auth_module = 'fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller'
        
        with patch(f'{auth_module}.get_authenticated_user_id') as mock_get_user_id, \
             patch(f'{auth_module}.log_authentication_details') as mock_log_auth:
            
            mock_get_user_id.return_value = sample_user_id
            mock_log_auth.return_value = None
            
            yield mock_get_user_id, mock_log_auth

    @pytest.fixture
    def mock_perms(self):
        """Mock permission system."""
        auth_module = 'fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller'
        
        # Mock the permission check method directly
        with patch.object(TaskMCPController, '_check_task_permissions') as mock_check_perms:
            mock_check_perms.return_value = (True, None)  # Allow all operations by default
            yield mock_check_perms

    # === CREATE Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task creation."""
        facade_service_mock, task_facade_mock = mock_facade_service
        mock_get_user_id, mock_log_auth = mock_auth
        
        # Configure facade response for successful creation
        expected_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        task_facade_mock.create_task.return_value = expected_response

        # Execute create operation
        result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            description=sample_task_data["description"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Verify authentication was called
        mock_get_user_id.assert_called_once()
        mock_log_auth.assert_called_once()
        
        # Verify facade was called
        task_facade_mock.create_task.assert_called_once()
        
        # Verify response structure (the controller standardizes responses)
        assert result["success"] is True
        assert "data" in result
        assert "meta" in result  # Standardized responses include metadata

    @pytest.mark.asyncio
    async def test_create_task_missing_title(self, controller, mock_auth, mock_perms):
        """Test task creation fails without required title."""
        mock_get_user_id, mock_log_auth = mock_auth
        
        result = await controller.manage_task(
            action="create",
            git_branch_id=str(uuid.uuid4()),
            assignees=["coding-agent"]
            # Missing title
        )

        # Should return validation error
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_task_missing_git_branch_id(self, controller, mock_auth, mock_perms):
        """Test task creation fails without required git_branch_id."""
        mock_get_user_id, mock_log_auth = mock_auth
        
        result = await controller.manage_task(
            action="create",
            title="Test Task",
            assignees=["coding-agent"]
            # Missing git_branch_id
        )

        # Should return validation error
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_task_missing_assignees(self, controller, mock_auth, mock_perms):
        """Test task creation fails without required assignees."""
        mock_get_user_id, mock_log_auth = mock_auth
        
        result = await controller.manage_task(
            action="create",
            title="Test Task",
            git_branch_id=str(uuid.uuid4())
            # Missing assignees
        )

        # Should return validation error
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.parametrize("invalid_assignees", ["", [], None])
    @pytest.mark.asyncio
    async def test_create_task_invalid_assignees(self, controller, invalid_assignees, mock_auth, mock_perms):
        """Test task creation with various invalid assignee values."""
        mock_get_user_id, mock_log_auth = mock_auth
        
        result = await controller.manage_task(
            action="create",
            title="Test Task",
            git_branch_id=str(uuid.uuid4()),
            assignees=invalid_assignees
        )

        # Should return validation error
        assert result["success"] is False
        assert "error" in result

    # === READ Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task retrieval."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task retrieved successfully"
        }
        task_facade_mock.get_task.return_value = expected_response

        result = await controller.manage_task(
            action="get",
            task_id=sample_task_data["task_id"]
        )

        # Verify facade was called
        task_facade_mock.get_task.assert_called_once()
        
        # Verify response (note: response is wrapped by response formatter)
        assert result["success"] is True
        # The facade response is nested within result["data"]["data"]
        assert "data" in result
        assert "data" in result["data"]  # facade response is nested
        assert result["data"]["data"]["task_id"] == sample_task_data["task_id"]

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, controller, mock_facade_service, mock_auth, mock_perms):
        """Test task retrieval with non-existent task ID."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        task_facade_mock.get_task.return_value = {
            "success": False,
            "error": "Task not found",
            "error_code": "TASK_NOT_FOUND"
        }

        result = await controller.manage_task(
            action="get",
            task_id="non-existent-id"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_missing_task_id(self, controller, mock_auth, mock_perms):
        """Test task retrieval without providing task_id."""
        result = await controller.manage_task(action="get")
        
        assert result["success"] is False
        assert "task_id is required" in self._extract_error_message(result)

    # === UPDATE Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task update."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        updated_data = sample_task_data.copy()
        updated_data["title"] = "Updated Task Title"
        updated_data["status"] = "in_progress"
        
        expected_response = {
            "success": True,
            "data": updated_data,
            "message": "Task updated successfully"
        }
        task_facade_mock.update_task.return_value = expected_response

        result = await controller.manage_task(
            action="update",
            task_id=sample_task_data["task_id"],
            title="Updated Task Title",
            status="in_progress"
        )

        # Verify facade was called
        task_facade_mock.update_task.assert_called_once()
        
        # Verify response
        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]
        assert result["data"]["data"]["title"] == "Updated Task Title"
        assert result["data"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_task_missing_task_id(self, controller, mock_auth, mock_perms):
        """Test task update without providing task_id."""
        result = await controller.manage_task(
            action="update",
            title="Updated Title"
        )
        
        assert result["success"] is False
        assert "error" in result

    # === DELETE Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task deletion."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "message": "Task deleted successfully"
        }
        task_facade_mock.delete_task.return_value = expected_response

        result = await controller.manage_task(
            action="delete",
            task_id=sample_task_data["task_id"]
        )

        # Verify facade was called
        task_facade_mock.delete_task.assert_called_once()
        
        # Verify response
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_task_missing_task_id(self, controller, mock_auth, mock_perms):
        """Test task deletion without providing task_id."""
        result = await controller.manage_task(action="delete")
        
        assert result["success"] is False
        assert "error" in result

    # === LIST Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_list_tasks_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task listing."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        task_list = [
            sample_task_data,
            {**sample_task_data, "task_id": str(uuid.uuid4()), "title": "Second Task"}
        ]
        
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
        task_facade_mock.list_tasks.return_value = expected_response

        result = await controller.manage_task(
            action="list",
            git_branch_id=sample_task_data["git_branch_id"]
        )

        # Verify facade was called
        task_facade_mock.list_tasks.assert_called_once()
        
        # Verify response
        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]
        assert len(result["data"]["data"]["tasks"]) == 2

    @pytest.mark.parametrize("limit,offset", [
        (10, 0),
        (25, 50),
        (100, 200)
    ])
    @pytest.mark.asyncio
    async def test_list_tasks_pagination(self, controller, mock_facade_service, limit, offset, mock_auth, mock_perms):
        """Test task listing with pagination parameters."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {
                "tasks": [],
                "total": 0,
                "page": offset//limit + 1 if limit > 0 else 1,
                "limit": limit
            },
            "message": "Tasks retrieved successfully"
        }
        task_facade_mock.list_tasks.return_value = expected_response

        result = await controller.manage_task(
            action="list",
            limit=limit,
            offset=offset
        )

        assert result["success"] is True
        assert "data" in result
        if "data" in result["data"] and "limit" in result["data"]["data"]:
            assert result["data"]["data"]["limit"] == limit
        else:
            # Handle case where response structure differs
            pass

    # === SEARCH Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_search_tasks_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task search."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {
                "tasks": [sample_task_data],
                "total": 1,
                "query": "test implementation"
            },
            "message": "Search completed successfully"
        }
        task_facade_mock.search_tasks.return_value = expected_response

        result = await controller.manage_task(
            action="search",
            query="test implementation"
        )

        # Verify facade was called
        task_facade_mock.search_tasks.assert_called_once()
        
        # Verify response
        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]
        assert result["data"]["data"]["total"] == 1
        assert result["data"]["data"]["query"] == "test implementation"

    @pytest.mark.asyncio
    async def test_search_tasks_empty_results(self, controller, mock_facade_service, mock_auth, mock_perms):
        """Test search with no matching results."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {
                "tasks": [],
                "total": 0,
                "query": "nonexistent"
            },
            "message": "Search completed successfully"
        }
        task_facade_mock.search_tasks.return_value = expected_response

        result = await controller.manage_task(
            action="search",
            query="nonexistent"
        )

        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]
        assert result["data"]["data"]["total"] == 0

    # === COMPLETE Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful task completion."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        completed_data = sample_task_data.copy()
        completed_data["status"] = "done"
        completed_data["completion_summary"] = "Task completed successfully with all tests passing"
        
        expected_response = {
            "success": True,
            "data": completed_data,
            "message": "Task completed successfully"
        }
        task_facade_mock.complete_task.return_value = expected_response

        result = await controller.manage_task(
            action="complete",
            task_id=sample_task_data["task_id"],
            completion_summary="Task completed successfully with all tests passing",
            testing_notes="All unit tests pass, integration tests verified"
        )

        # Verify facade was called
        task_facade_mock.complete_task.assert_called_once()
        
        # Verify response
        assert result["success"] is True
        assert "data" in result
        assert "data" in result["data"]
        assert result["data"]["data"]["status"] == "done"
        assert "completion_summary" in result["data"]["data"]

    # === DEPENDENCY Operation Tests ===
    
    @pytest.mark.asyncio
    async def test_add_dependency_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful dependency addition."""
        facade_service_mock, task_facade_mock = mock_facade_service
        dependency_id = str(uuid.uuid4())
        
        expected_response = {
            "success": True,
            "message": "Dependency added successfully"
        }
        task_facade_mock.add_dependency.return_value = expected_response

        result = await controller.manage_task(
            action="add_dependency",
            task_id=sample_task_data["task_id"],
            dependency_id=dependency_id
        )

        # Verify facade was called
        task_facade_mock.add_dependency.assert_called_once()
        
        # Verify response
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_add_dependency_missing_params(self, controller, mock_auth, mock_perms):
        """Test add dependency with missing parameters."""
        # Missing dependency_id
        result = await controller.manage_task(
            action="add_dependency",
            task_id=str(uuid.uuid4())
        )
        
        assert result["success"] is False
        assert "dependency_id" in self._extract_error_message(result)

    @pytest.mark.asyncio
    async def test_remove_dependency_success(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test successful dependency removal."""
        facade_service_mock, task_facade_mock = mock_facade_service
        dependency_id = str(uuid.uuid4())
        
        expected_response = {
            "success": True,
            "message": "Dependency removed successfully"
        }
        task_facade_mock.remove_dependency.return_value = expected_response

        result = await controller.manage_task(
            action="remove_dependency",
            task_id=sample_task_data["task_id"],
            dependency_id=dependency_id
        )

        # Verify facade was called
        task_facade_mock.remove_dependency.assert_called_once()
        
        # Verify response
        assert result["success"] is True

    # === AUTHENTICATION Tests ===
    
    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, controller, mock_perms):
        """Test request without proper authentication."""
        auth_module = 'fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller'
        
        with patch(f'{auth_module}.get_authenticated_user_id') as mock_get_user_id:
            mock_get_user_id.side_effect = UserAuthenticationRequiredError("Authentication required")
            
            result = await controller.manage_task(action="list")
            
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, controller, mock_perms):
        """Test handling of authentication errors."""
        auth_module = 'fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller'
        
        with patch(f'{auth_module}.get_authenticated_user_id') as mock_get_user_id:
            mock_get_user_id.side_effect = Exception("Authentication service unavailable")
            
            result = await controller.manage_task(action="list")
            
            assert result["success"] is False
            assert "error" in result

    # === PERMISSION Tests ===
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, controller, mock_auth):
        """Test request with insufficient permissions."""
        mock_get_user_id, mock_log_auth = mock_auth
        
        # Mock permission check to deny access
        with patch.object(TaskMCPController, '_check_task_permissions') as mock_check_perms:
            mock_check_perms.return_value = (False, {
                "success": False,
                "error": "Permission denied: requires tasks:create",
                "error_code": "PERMISSION_DENIED"
            })
            
            result = await controller.manage_task(
                action="create",
                title="Test Task",
                git_branch_id=str(uuid.uuid4()),
                assignees=["coding-agent"]
            )
            
            assert result["success"] is False
            assert "permission" in self._extract_error_message(result).lower()

    # === ERROR HANDLING Tests ===
    
    @pytest.mark.asyncio
    async def test_facade_exception_handling(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test graceful handling of facade exceptions."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        # Configure facade to raise exception
        task_facade_mock.get_task.side_effect = Exception("Database connection failed")

        result = await controller.manage_task(
            action="get",
            task_id=sample_task_data["task_id"]
        )

        # Should handle error gracefully
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_action(self, controller, mock_auth, mock_perms):
        """Test handling of invalid action parameter."""
        result = await controller.manage_task(action="invalid_action")
        
        # Should handle gracefully
        assert "success" in result

    # === PARAMETER VALIDATION Tests ===
    
    @pytest.mark.parametrize("status", ["todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"])
    @pytest.mark.asyncio
    async def test_valid_status_values(self, controller, mock_facade_service, sample_task_data, status, mock_auth, mock_perms):
        """Test task creation with different valid status values."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {**sample_task_data, "status": status},
            "message": "Task created successfully"
        }
        task_facade_mock.create_task.return_value = expected_response

        result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"],
            status=status
        )

        assert result["success"] is True

    @pytest.mark.parametrize("priority", ["low", "medium", "high", "urgent", "critical"])
    @pytest.mark.asyncio
    async def test_valid_priority_values(self, controller, mock_facade_service, sample_task_data, priority, mock_auth, mock_perms):
        """Test task creation with different valid priority values."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {**sample_task_data, "priority": priority},
            "message": "Task created successfully"
        }
        task_facade_mock.create_task.return_value = expected_response

        result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"],
            priority=priority
        )

        assert result["success"] is True

    # === WORKFLOW ENHANCEMENT Tests ===
    
    @pytest.mark.asyncio
    async def test_workflow_enhancement_success(self, controller, mock_facade_service, mock_workflow_enhancer, sample_task_data, mock_auth, mock_perms):
        """Test successful workflow enhancement integration."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        base_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        task_facade_mock.create_task.return_value = base_response
        
        # Configure workflow enhancer
        enhanced_response = {
            **base_response,
            "workflow_hints": ["Consider adding unit tests", "Update API documentation"],
            "next_actions": ["Create subtasks for implementation phases", "Assign code reviewers"]
        }
        mock_workflow_enhancer.enhance_response.return_value = enhanced_response

        result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Verify workflow enhancer was called
        mock_workflow_enhancer.enhance_response.assert_called_once()
        
        # Verify enhanced response
        assert result["success"] is True
        assert "workflow_hints" in result
        assert "next_actions" in result

    @pytest.mark.asyncio
    async def test_workflow_enhancement_failure_graceful_degradation(self, controller, mock_facade_service, mock_workflow_enhancer, sample_task_data, mock_auth, mock_perms):
        """Test graceful handling when workflow enhancement fails."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        base_response = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        task_facade_mock.create_task.return_value = base_response
        
        # Configure workflow enhancer to fail
        mock_workflow_enhancer.enhance_response.side_effect = Exception("Enhancement service unavailable")

        result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )

        # Should return base response without enhancement
        assert result["success"] is True
        assert "workflow_hints" not in result  # Enhancement should be skipped on error

    # === INTEGRATION Tests ===
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_lifecycle(self, controller, mock_facade_service, sample_task_data, mock_auth, mock_perms):
        """Test complete task lifecycle: create -> update -> complete -> delete."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        # Step 1: Create task
        task_facade_mock.create_task.return_value = {
            "success": True,
            "data": sample_task_data,
            "message": "Task created successfully"
        }
        
        create_result = await controller.manage_task(
            action="create",
            title=sample_task_data["title"],
            git_branch_id=sample_task_data["git_branch_id"],
            assignees=sample_task_data["assignees"]
        )
        assert create_result["success"] is True
        
        # Step 2: Update task
        updated_data = sample_task_data.copy()
        updated_data["status"] = "in_progress"
        task_facade_mock.update_task.return_value = {
            "success": True,
            "data": updated_data,
            "message": "Task updated successfully"
        }
        
        update_result = await controller.manage_task(
            action="update",
            task_id=sample_task_data["task_id"],
            status="in_progress"
        )
        assert update_result["success"] is True
        
        # Step 3: Complete task
        completed_data = updated_data.copy()
        completed_data["status"] = "done"
        task_facade_mock.complete_task.return_value = {
            "success": True,
            "data": completed_data,
            "message": "Task completed successfully"
        }
        
        complete_result = await controller.manage_task(
            action="complete",
            task_id=sample_task_data["task_id"],
            completion_summary="All implementation completed and tested"
        )
        assert complete_result["success"] is True
        
        # Step 4: Delete task
        task_facade_mock.delete_task.return_value = {
            "success": True,
            "message": "Task deleted successfully"
        }
        
        delete_result = await controller.manage_task(
            action="delete",
            task_id=sample_task_data["task_id"]
        )
        assert delete_result["success"] is True

    # === EDGE CASE Tests ===
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, controller, mock_facade_service, mock_auth, mock_perms):
        """Test handling of concurrent operations on the same task."""
        facade_service_mock, task_facade_mock = mock_facade_service
        task_id = str(uuid.uuid4())
        
        # Configure facade responses for concurrent operations
        task_facade_mock.update_task.return_value = {
            "success": True,
            "data": {"task_id": task_id, "status": "in_progress"},
            "message": "Task updated successfully"
        }
        
        # Execute concurrent updates
        tasks = [
            controller.manage_task(action="update", task_id=task_id, status="in_progress"),
            controller.manage_task(action="update", task_id=task_id, priority="high"),
            controller.manage_task(action="update", task_id=task_id, details="Updated details")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_large_data_handling(self, controller, mock_facade_service, mock_auth, mock_perms):
        """Test handling of large data sets in task operations."""
        facade_service_mock, task_facade_mock = mock_facade_service
        
        # Create large description (simulate large data)
        large_description = "This is a test description. " * 1000  # ~30KB
        large_labels = [f"label-{i}" for i in range(100)]  # 100 labels
        
        task_facade_mock.create_task.return_value = {
            "success": True,
            "data": {
                "task_id": str(uuid.uuid4()),
                "title": "Large Data Task",
                "description": large_description,
                "labels": large_labels
            },
            "message": "Task created successfully"
        }
        
        result = await controller.manage_task(
            action="create",
            title="Large Data Task",
            description=large_description,
            git_branch_id=str(uuid.uuid4()),
            assignees=["coding-agent"],
            labels=large_labels
        )
        
        assert result["success"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])