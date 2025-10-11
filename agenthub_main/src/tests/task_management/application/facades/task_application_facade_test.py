"""
Tests for Task Application Facade

This test suite covers the Task Application Facade functionality including:
- Task creation with validation
- Task retrieval and listing
- Task updates and progress tracking
- Task completion and deletion
- Dependency management
- Search functionality
- Next task recommendation
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade
)
from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.application.dtos.task.search_tasks_request import SearchTasksRequest
from fastmcp.task_management.domain.entities import Task, GitBranch, TaskStatus, TaskPriority
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    ProjectNotFoundError
)
from fastmcp.task_management.application.exceptions import (
    ValidationError
)


class TestTaskApplicationFacade:
    """Test Task Application Facade functionality"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        repo = Mock(spec=TaskRepository)
        # Facade calls these synchronously, not async
        repo.save = Mock()
        repo.find_by_id = Mock()
        repo.find_all_by_git_branch = Mock()
        repo.delete = Mock()
        repo.search = Mock()
        return repo

    @pytest.fixture
    def mock_subtask_repository(self):
        """Create mock subtask repository"""
        repo = Mock(spec=SubtaskRepository)
        repo.find_all_by_task = AsyncMock()
        repo.count_by_task = AsyncMock()
        return repo

    @pytest.fixture
    def mock_git_branch_repository(self):
        """Create mock git branch repository"""
        repo = Mock(spec=GitBranchRepository)
        repo.find_by_id = AsyncMock()
        repo.find_by_name_and_project = AsyncMock()
        return repo

    @pytest.fixture
    def mock_task_application_service(self):
        """Create mock task application service"""
        service = Mock(spec=TaskApplicationService)
        service.create_task = AsyncMock()
        service.update_task = AsyncMock()
        service.get_task = AsyncMock()
        service.delete_task = AsyncMock()
        service.complete_task = AsyncMock()
        service.list_tasks = AsyncMock()
        service.search_tasks = AsyncMock()
        service.get_next_task = AsyncMock()
        service.add_dependency = AsyncMock()
        service.remove_dependency = AsyncMock()
        return service

    @pytest.fixture
    def sample_task(self):
        """Create sample task"""
        task = Mock(spec=Task)
        task.id = "task-123"
        task.title = "Implement user authentication"
        task.description = "Add JWT-based authentication system"
        task.status = TaskStatus.TODO
        task.priority = "high"
        task.assignees = ["coding-agent", "@test-orchestrator-agent"]
        task.git_branch_id = "branch-123"
        task.estimated_effort = "3 days"
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        task.to_dict = Mock(return_value={
            "id": "task-123",
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication system",
            "status": "todo",
            "priority": "high",
            "assignees": ["coding-agent", "@test-orchestrator-agent"],
            "git_branch_id": "branch-123",
            "estimated_effort": "3 days"
        })
        # Add dependency methods
        task.add_dependency = Mock()
        task.remove_dependency = Mock()
        return task

    @pytest.fixture
    def sample_git_branch(self):
        """Create sample git branch"""
        branch = Mock(spec=GitBranch)
        branch.id = "branch-123"
        branch.project_id = "proj-123"
        branch.git_branch_name = "feature/user-auth"
        branch.git_branch_description = "Authentication feature"
        branch.to_dict = Mock(return_value={
            "id": "branch-123",
            "project_id": "proj-123",
            "git_branch_name": "feature/user-auth",
            "git_branch_description": "Authentication feature"
        })
        return branch

    @pytest.fixture
    def facade(self, mock_task_repository, mock_subtask_repository, mock_git_branch_repository):
        """Create facade instance with mocks"""
        return TaskApplicationFacade(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            git_branch_repository=mock_git_branch_repository
        )

    def test_create_task(self, facade, sample_task, sample_git_branch, mock_task_repository):
        """Test creating a task"""
        # Configure mocks - mock the use case instead of non-existent service
        from fastmcp.task_management.application.use_cases.create_task import CreateTaskResponse

        mock_response = Mock(spec=CreateTaskResponse)
        mock_response.success = True
        mock_response.task = sample_task
        mock_response.message = "Task created successfully"

        with patch.object(facade._create_task_use_case, 'execute', return_value=mock_response):
            with patch.object(facade, '_derive_context_from_git_branch_id', return_value={"project_id": "proj-123", "git_branch_name": "feature/user-auth"}):
                with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="user-123"):
                    with patch('fastmcp.task_management.application.facades.task_application_facade.WebSocketNotificationService'):
                        # Execute
                        request = CreateTaskRequest(
                            git_branch_id="branch-123",
                            title="Implement user authentication",
                            description="Add JWT-based authentication system",
                            assignees=["coding-agent", "@test-orchestrator-agent"],
                            priority="high",
                            estimated_effort="3 days"
                        )

                        result = facade.create_task(request)

        # Verify
        assert result["success"] is True
        assert result["task"]["title"] == "Implement user authentication"

    def test_create_task_validation_error(self, facade):
        """Test creating task with validation error"""
        # Configure mocks for validation failure - mock the use case to raise error
        with patch.object(facade._create_task_use_case, 'execute', side_effect=ValueError("Title cannot be empty")):
            with patch.object(facade, '_derive_context_from_git_branch_id', return_value={"project_id": "proj-123", "git_branch_name": "feature/user-auth"}):
                with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="user-123"):
                    # Execute
                    request = CreateTaskRequest(
                        git_branch_id="branch-123",
                        title="",  # Empty title should fail validation
                        assignees=["coding-agent"]
                    )

                    result = facade.create_task(request)

        # Verify
        assert result["success"] is False
        assert "Title cannot be empty" in result["error"]

    def test_get_task(self, facade, sample_task, mock_task_repository):
        """Test retrieving a task by ID"""
        # Configure mocks - facade uses repository and use case
        from fastmcp.task_management.domain.value_objects.task_id import TaskId
        from fastmcp.task_management.application.dtos.task import TaskResponse

        mock_task_repository.find_by_id.return_value = sample_task
        mock_response = Mock(spec=TaskResponse)
        mock_response.to_dict = Mock(return_value=sample_task.to_dict())

        with patch.object(facade._get_task_use_case, 'execute', return_value=mock_response):
            with patch('fastmcp.task_management.application.facades.task_application_facade.ContextResponseFactory.apply_to_task_response', side_effect=lambda x: x):
                # Execute
                result = facade.get_task("task-123")

        # Verify
        assert result["success"] is True
        assert result["task"]["id"] == "task-123"
        assert result["task"]["title"] == "Implement user authentication"

    def test_get_task_not_found(self, facade, mock_task_repository):
        """Test retrieving non-existent task"""
        # Configure mocks - repository returns None for not found
        from fastmcp.task_management.domain.value_objects.task_id import TaskId

        mock_task_repository.find_by_id.return_value = None

        # Execute
        result = facade.get_task("task-999")

        # Verify
        assert result["success"] is False
        assert "Task" in result["error"] and "not found" in result["error"]

    def test_update_task(self, facade, sample_task, mock_task_repository):
        """Test updating a task"""
        # Configure mocks
        from fastmcp.task_management.application.use_cases.update_task import UpdateTaskResponse

        updated_task = Mock(spec=Task)
        updated_task.id = "task-123"
        updated_task.title = "Updated authentication system"
        updated_task.status = "in_progress"
        updated_task.to_dict = Mock(return_value={
            "id": "task-123",
            "title": "Updated authentication system",
            "status": "in_progress",
            "priority": "high"
        })

        mock_response = Mock(spec=UpdateTaskResponse)
        mock_response.success = True
        mock_response.task = updated_task

        # Mock _get_task_for_update_comparison to return current task
        with patch.object(facade, '_get_task_for_update_comparison', return_value=sample_task):
            with patch.object(facade._update_task_use_case, 'execute', return_value=mock_response):
                with patch('fastmcp.task_management.application.facades.task_application_facade.WebSocketNotificationService'):
                    # Execute
                    request = UpdateTaskRequest(
                        task_id="task-123",
                        title="Updated authentication system",
                        status="in_progress"
                    )

                    result = facade.update_task("task-123", request)

        # Verify
        assert result["success"] is True
        assert result["task"]["title"] == "Updated authentication system"
        assert result["task"]["status"] == "in_progress"

    def test_complete_task(self, facade, sample_task):
        """Test completing a task"""
        # Configure mocks
        completed_task_dict = sample_task.to_dict()
        completed_task_dict["status"] = "done"
        completed_task_dict["progress_percentage"] = 100

        with patch.object(facade._complete_task_use_case, 'execute') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "task": completed_task_dict,
                "completion_summary": "Authentication system implemented successfully",
                "message": "Task completed successfully"
            }

            with patch('fastmcp.task_management.application.facades.task_application_facade.WebSocketNotificationService'):
                # Execute
                result = facade.complete_task(
                    task_id="task-123",
                    completion_summary="Authentication system implemented successfully",
                    testing_notes="All tests passing"
                )

        # Verify
        assert result["success"] is True
        assert result["task"]["status"] == "done"

    def test_delete_task(self, facade, sample_task, mock_task_repository):
        """Test deleting a task"""
        # Configure mocks
        from fastmcp.task_management.domain.value_objects.task_id import TaskId

        # Mock repository to return task before deletion
        mock_task_repository.find_by_id.return_value = sample_task

        with patch.object(facade._delete_task_use_case, 'execute') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "message": "Task deleted successfully",
                "subtasks_deleted": 0,
                "contexts_deleted": 0
            }

            with patch('fastmcp.task_management.application.facades.task_application_facade.WebSocketNotificationService'):
                # Execute
                result = facade.delete_task("task-123")

        # Verify
        assert result["success"] is True
        assert "deleted successfully" in result["message"]

    def test_list_tasks(self, facade, sample_task):
        """Test listing tasks with filters"""
        # Configure mocks
        from fastmcp.task_management.application.dtos.task import TaskListResponse, TaskResponse

        # Create mock TaskResponse
        task_response = Mock(spec=TaskResponse)
        task_response.id = sample_task.id
        task_response.title = sample_task.title
        task_response.status = sample_task.status
        task_response.priority = sample_task.priority
        task_response.to_dict = Mock(return_value=sample_task.to_dict())

        mock_list_response = Mock(spec=TaskListResponse)
        mock_list_response.tasks = [task_response]
        mock_list_response.count = 1
        mock_list_response.filters_applied = {"status": "todo", "priority": "high"}

        with patch.object(facade._list_tasks_use_case, 'execute', return_value=mock_list_response):
            # Execute
            request = ListTasksRequest(
                git_branch_id="branch-123",
                status="todo",
                priority="high",
                limit=10
            )

            result = facade.list_tasks(request, minimal=False)

        # Verify
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Implement user authentication"
        assert result["count"] == 1

    def test_search_tasks(self, facade, sample_task):
        """Test searching tasks by query"""
        # Configure mocks
        from fastmcp.task_management.application.dtos.task import TaskListResponse, TaskResponse

        task_response = Mock(spec=TaskResponse)
        task_response.id = sample_task.id
        task_response.title = sample_task.title
        task_response.to_dict = Mock(return_value=sample_task.to_dict())

        mock_search_response = Mock(spec=TaskListResponse)
        mock_search_response.tasks = [task_response]
        mock_search_response.count = 1
        mock_search_response.query = "authentication"  # SearchTasks adds this

        with patch.object(facade._search_tasks_use_case, 'execute', return_value=mock_search_response):
            # Execute
            request = SearchTasksRequest(
                query="authentication",
                git_branch_id="branch-123",
                limit=10
            )

            result = facade.search_tasks(request)

        # Verify
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Implement user authentication"
        assert result["query"] == "authentication"

    @pytest.mark.asyncio
    async def test_get_next_task(self, facade, sample_task):
        """Test getting next recommended task"""
        # Configure mocks
        from fastmcp.task_management.application.use_cases.next_task import NextTaskResponse

        mock_next_response = Mock(spec=NextTaskResponse)
        mock_next_response.has_next = True
        mock_next_response.next_item = sample_task.to_dict()
        mock_next_response.context = {}
        mock_next_response.context_info = "High priority task"
        mock_next_response.message = "Next task found"

        with patch.object(facade._do_next_use_case, 'execute', return_value=mock_next_response):
            # Execute
            result = await facade.get_next_task(
                git_branch_id="branch-123",
                include_context=True
            )

        # Verify
        assert result["success"] is True
        assert result["task"]["next_item"]["id"] == "task-123"

    @pytest.mark.asyncio
    async def test_get_next_task_no_tasks(self, facade):
        """Test getting next task when no tasks available"""
        # Configure mocks - return None to indicate no tasks
        with patch.object(facade._do_next_use_case, 'execute', return_value=None):
            # Execute
            result = await facade.get_next_task(git_branch_id="branch-123")

        # Verify
        assert result["success"] is False
        assert "No tasks found" in result["message"] or "error" in result

    def test_add_dependency(self, facade, sample_task, mock_task_repository):
        """Test adding task dependency"""
        # Configure mocks
        from fastmcp.task_management.domain.value_objects.task_id import TaskId

        # Mock both tasks exist
        dependency_task = Mock(spec=Task)
        dependency_task.id = TaskId("task-456")

        mock_task_repository.find_by_id.side_effect = [sample_task, dependency_task]

        # Mock the save operation
        mock_task_repository.save = Mock()

        # Execute
        result = facade.add_dependency(
            task_id="task-123",
            dependency_id="task-456"
        )

        # Verify
        assert result["success"] is True
        assert "added" in result["message"] or "exists" in result["message"]

    def test_remove_dependency(self, facade, sample_task, mock_task_repository):
        """Test removing task dependency"""
        # Configure mocks
        from fastmcp.task_management.domain.value_objects.task_id import TaskId

        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save = Mock()

        # Execute
        result = facade.remove_dependency(
            task_id="task-123",
            dependency_id="task-456"
        )

        # Verify
        assert result["success"] is True
        assert "removed" in result["message"] or "not found" in result["message"]

    # NOTE: AI-enhanced methods (ai_plan_tasks, ai_create_task, ai_enhance_task) removed
    # These methods don't exist in the current TaskApplicationFacade implementation

    def test_error_handling_project_not_found(self, facade):
        """Test error handling for non-existent project"""
        # Configure mocks - facade doesn't throw ProjectNotFoundError directly
        # but returns error dict instead
        with patch.object(facade, '_derive_context_from_git_branch_id', return_value={"project_id": None, "git_branch_name": None}):
            with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="user-123"):
                with patch.object(facade._create_task_use_case, 'execute', side_effect=ProjectNotFoundError("Project not found: proj-999")):
                    # Execute
                    request = CreateTaskRequest(
                        git_branch_id="branch-999",
                        title="Test Task",
                        assignees=["coding-agent"]
                    )

                    result = facade.create_task(request)

        # Verify
        assert result["success"] is False
        assert "error" in result

    def test_error_handling_validation_error(self, facade):
        """Test error handling for validation errors"""
        # Configure mocks - use ValueError which is caught by facade
        with patch.object(facade._create_task_use_case, 'execute', side_effect=ValueError("Task with similar title already exists")):
            with patch.object(facade, '_derive_context_from_git_branch_id', return_value={"project_id": "proj-123", "git_branch_name": "main"}):
                with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="user-123"):
                    # Execute
                    request = CreateTaskRequest(
                        git_branch_id="branch-123",
                        title="Duplicate Task",
                        assignees=["coding-agent"]
                    )

                    result = facade.create_task(request)

        # Verify
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_context_integration(self, facade, sample_task, mock_task_repository):
        """Test context service integration"""
        # Configure mocks for context service
        from fastmcp.task_management.application.dtos.task import TaskResponse

        mock_task_repository.find_by_id.return_value = sample_task

        # Mock the response with context data
        mock_response = Mock(spec=TaskResponse)
        task_dict_with_context = sample_task.to_dict()
        task_dict_with_context["context_data"] = {"key": "value"}
        task_dict_with_context["inheritance_chain"] = ["global", "project", "branch", "task"]
        mock_response.to_dict = Mock(return_value=task_dict_with_context)

        with patch.object(facade._get_task_use_case, 'execute', return_value=mock_response):
            with patch('fastmcp.task_management.application.facades.task_application_facade.ContextResponseFactory.apply_to_task_response', side_effect=lambda x: x):
                # Execute with context
                result = facade.get_task("task-123", include_context=True)

        # Verify
        assert result["success"] is True
        assert result["task"]["context_data"] == {"key": "value"}

    def test_websocket_notification_integration(self, facade, sample_task):
        """Test WebSocket notification service integration"""
        # Configure mocks
        from fastmcp.task_management.application.use_cases.create_task import CreateTaskResponse

        mock_response = Mock(spec=CreateTaskResponse)
        mock_response.success = True
        mock_response.task = sample_task
        mock_response.message = "Task created successfully"

        with patch('fastmcp.task_management.application.facades.task_application_facade.WebSocketNotificationService') as mock_websocket:
            mock_websocket.sync_broadcast_task_event = Mock()

            with patch.object(facade._create_task_use_case, 'execute', return_value=mock_response):
                with patch.object(facade, '_derive_context_from_git_branch_id', return_value={"project_id": "proj-123", "git_branch_name": "feature/user-auth"}):
                    with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="user-123"):
                        # Execute
                        request = CreateTaskRequest(
                            git_branch_id="branch-123",
                            title="Test Task",
                            assignees=["coding-agent"]
                        )

                        result = facade.create_task(request)

        # Verify
        assert result["success"] is True
        # WebSocket notification should be sent for task creation
        mock_websocket.sync_broadcast_task_event.assert_called_once()

    def test_facade_initialization(self):
        """Test proper facade initialization"""
        facade = TaskApplicationFacade(
            task_repository=Mock(),
            subtask_repository=Mock(),
            git_branch_repository=Mock()
        )

        # Verify initialization
        assert facade._task_repository is not None
        assert facade._subtask_repository is not None
        assert facade._git_branch_repository is not None

    def test_facade_initialization_without_optional_repos(self):
        """Test facade initialization without optional repositories"""
        facade = TaskApplicationFacade(
            task_repository=Mock()
        )

        # Verify initialization with defaults
        assert facade._task_repository is not None
        # Optional repositories should be None or have defaults
        assert hasattr(facade, '_subtask_repository')
        assert hasattr(facade, '_git_branch_repository')