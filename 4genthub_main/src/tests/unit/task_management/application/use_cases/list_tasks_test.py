"""
Tests for List Tasks Use Case
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.list_tasks import ListTasksUseCase
from fastmcp.task_management.application.dtos.task import (
    ListTasksRequest,
    TaskListResponse
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestListTasksUseCase:
    """Test the ListTasksUseCase class"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def use_case(self, mock_task_repository):
        """Create a use case instance"""
        return ListTasksUseCase(task_repository=mock_task_repository)
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task entity"""
        return Task(
            id=TaskId("12345678-1234-5678-1234-567812345678"),
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            status=TaskStatus.todo(),
            priority=Priority.high(),
            assignees=["user-1", "user-2"],
            labels=["bug", "urgent"],
            subtasks=[],
            dependencies=[],
            context_id="context-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def test_list_tasks_no_filters(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks without any filters"""
        # Arrange
        request = ListTasksRequest()
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.count == 1
        assert response.tasks[0].id == "12345678-1234-5678-1234-567812345678"
        assert response.tasks[0].title == "Test Task"
        
        # Verify repository was called with empty filters
        mock_task_repository.find_by_criteria.assert_called_once_with({}, limit=None)
    
    def test_list_tasks_with_git_branch_filter(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with git branch filter"""
        # Arrange
        request = ListTasksRequest(git_branch_id="branch-123")
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {"git_branch_id": "branch-123"}
        
        # Verify repository was called with git_branch_id filter
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {"git_branch_id": "branch-123"}, 
            limit=None
        )
    
    def test_list_tasks_with_status_filter(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with status filter"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            status="todo"
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "status": "todo"
        }
        
        # Verify repository was called with status filter as TaskStatus instance
        call_args, call_kwargs = mock_task_repository.find_by_criteria.call_args
        filter_dict = call_args[0]
        
        assert filter_dict["git_branch_id"] == "branch-123" 
        assert isinstance(filter_dict["status"], TaskStatus)
        assert filter_dict["status"].value == "todo"
        assert call_kwargs["limit"] is None
    
    def test_list_tasks_with_priority_filter(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with priority filter"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            priority="high"
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "priority": "high"
        }
        
        # Verify repository was called with priority filter as Priority enum
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {
                "git_branch_id": "branch-123",
                "priority": Priority.high()
            }, 
            limit=None
        )
    
    def test_list_tasks_with_assignees_filter(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with assignees filter"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            assignees=["user-1", "user-2"]
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "assignees": ["user-1", "user-2"]
        }
        
        # Verify repository was called with assignees filter
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {
                "git_branch_id": "branch-123",
                "assignees": ["user-1", "user-2"]
            }, 
            limit=None
        )
    
    def test_list_tasks_with_labels_filter(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with labels filter"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            labels=["bug", "urgent"]
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "labels": ["bug", "urgent"]
        }
        
        # Verify repository was called with labels filter
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {
                "git_branch_id": "branch-123",
                "labels": ["bug", "urgent"]
            }, 
            limit=None
        )
    
    def test_list_tasks_with_limit(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with limit"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            limit=10
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "limit": 10
        }
        
        # Verify repository was called with limit
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {"git_branch_id": "branch-123"}, 
            limit=10
        )
    
    def test_list_tasks_with_all_filters(self, use_case, mock_task_repository, sample_task):
        """Test listing tasks with all filters applied"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            status="todo",
            priority="high",
            assignees=["user-1"],
            labels=["bug"],
            limit=5
        )
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 1
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "status": "todo",
            "priority": "high",
            "assignees": ["user-1"],
            "labels": ["bug"],
            "limit": 5
        }
        
        # Verify repository was called with all filters converted to value objects
        call_args, call_kwargs = mock_task_repository.find_by_criteria.call_args
        filter_dict = call_args[0]
        
        assert filter_dict["git_branch_id"] == "branch-123"
        assert isinstance(filter_dict["status"], TaskStatus)
        assert filter_dict["status"].value == "todo"
        assert isinstance(filter_dict["priority"], Priority)
        assert filter_dict["priority"].value == "high"
        assert filter_dict["assignees"] == ["user-1"]
        assert filter_dict["labels"] == ["bug"]
        assert call_kwargs["limit"] == 5
    
    def test_list_tasks_empty_result(self, use_case, mock_task_repository):
        """Test listing tasks when no tasks match filters"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-999",
            status="done"
        )
        mock_task_repository.find_by_criteria.return_value = []
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 0
        assert response.count == 0
        assert response.filters_applied == {
            "git_branch_id": "branch-999",
            "status": "done"
        }
    
    def test_list_tasks_multiple_results(self, use_case, mock_task_repository):
        """Test listing tasks with multiple results"""
        # Arrange
        task1 = Task(
            id=TaskId("11111111-1111-1111-1111-111111111111"),
            title="Task 1",
            description="Description 1",
            git_branch_id="branch-123",
            status=TaskStatus.todo(),
            priority=Priority.high(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        task2 = Task(
            id=TaskId("22222222-2222-2222-2222-222222222222"),
            title="Task 2",
            description="Description 2",
            git_branch_id="branch-123",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.medium(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        request = ListTasksRequest(git_branch_id="branch-123")
        mock_task_repository.find_by_criteria.return_value = [task1, task2]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert len(response.tasks) == 2
        assert response.count == 2
        assert response.tasks[0].id == "11111111-1111-1111-1111-111111111111"
        assert response.tasks[1].id == "22222222-2222-2222-2222-222222222222"
    
    def test_list_tasks_preserves_task_details(self, use_case, mock_task_repository, sample_task):
        """Test that task details are preserved in the response"""
        # Arrange
        request = ListTasksRequest(git_branch_id="branch-123")
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        task_response = response.tasks[0]
        assert task_response.id == "12345678-1234-5678-1234-567812345678"
        assert task_response.title == "Test Task"
        assert task_response.description == "Test description"
        assert task_response.git_branch_id == "branch-123"
        assert task_response.status == "todo"
        assert task_response.priority == "high"
        assert task_response.assignees == ["user-1-agent", "user-2-agent"]
        assert task_response.labels == ["bug", "urgent"]
        assert task_response.context_id == "context-123"
    
    def test_list_tasks_handles_none_filters(self, use_case, mock_task_repository):
        """Test that None filter values are handled correctly"""
        # Arrange
        request = ListTasksRequest(
            git_branch_id="branch-123",
            status=None,
            priority=None,
            assignees=None,
            labels=None,
            limit=None
        )
        mock_task_repository.find_by_criteria.return_value = []
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert response.filters_applied == {"git_branch_id": "branch-123"}
        
        # Verify repository was called with only git_branch_id filter
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {"git_branch_id": "branch-123"}, 
            limit=None
        )
    
    def test_list_tasks_legacy_assignee_field_support(self, use_case, mock_task_repository, sample_task):
        """Test that legacy assignee field is supported"""
        # Arrange
        request = Mock(spec=ListTasksRequest)
        request.git_branch_id = "branch-123"
        request.status = None
        request.priority = None
        request.assignees = None  # New field not set
        request.assignee = "user-1"  # Legacy field set
        request.labels = None
        request.limit = None
        
        mock_task_repository.find_by_criteria.return_value = [sample_task]
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert isinstance(response, TaskListResponse)
        assert response.filters_applied == {
            "git_branch_id": "branch-123",
            "assignee": "user-1"
        }
        
        # Verify repository was called with assignee filter
        mock_task_repository.find_by_criteria.assert_called_once_with(
            {
                "git_branch_id": "branch-123",
                "assignee": "user-1"
            }, 
            limit=None
        )