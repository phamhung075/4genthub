"""
Test suite for GetTask use case

Tests the business logic for retrieving task details.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastmcp.task_management.application.use_cases.get_task import GetTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskTitle,
    TaskDescription,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    UserID,
    TaskDetails,
    EstimatedEffort
)
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    UnauthorizedAccessError
)


class TestGetTaskUseCase:
    """Test suite for GetTask use case"""

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock()

    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_task_repo, mock_subtask_repo, mock_context_service):
        """Create use case instance with mocks"""
        return GetTaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            context_service=mock_context_service
        )

    @pytest.fixture
    def sample_task(self):
        """Create a comprehensive sample task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Implement User Authentication"),
            description=TaskDescription("Add JWT-based authentication system"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["security", "backend", "api"],
            details=TaskDetails("Using RS256 algorithm for JWT"),
            estimated_effort=EstimatedEffort("5 days"),
            dependencies=[TaskID(str(uuid4())), TaskID(str(uuid4()))],
            progress_percentage=45,
            due_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        task.created_at = datetime.now(timezone.utc) - timedelta(days=3)
        task.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        return task

    @pytest.fixture
    def sample_subtasks(self, sample_task):
        """Create sample subtasks"""
        return [
            Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_task.id,
                title="Create user model",
                status=TaskStatus.DONE,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")]
            ),
            Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_task.id,
                title="Implement JWT generation",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user456")]
            )
        ]

    def test_get_task_success(self, use_case, mock_task_repo, sample_task):
        """Test successfully getting a task"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id=task_id, user_id=user_id)
        
        # Assert
        assert result == sample_task
        assert result.id.value == task_id
        assert result.title.value == "Implement User Authentication"
        assert result.progress_percentage == 45
        
        # Verify repository call
        mock_task_repo.get_by_id.assert_called_once_with(TaskID(task_id))

    def test_get_task_not_found(self, use_case, mock_task_repo):
        """Test getting non-existent task"""
        # Arrange
        task_id = str(uuid4())
        
        mock_task_repo.get_by_id.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError):
            use_case.execute(task_id=task_id, user_id="user123")

    def test_get_task_unauthorized_user(self, use_case, mock_task_repo, sample_task):
        """Test accessing task by unauthorized user"""
        # Arrange
        task_id = sample_task.id.value
        unauthorized_user = "user999"  # Not in assignees
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(UnauthorizedAccessError, match="not authorized to access"):
            use_case.execute(task_id=task_id, user_id=unauthorized_user)

    def test_get_task_with_subtasks(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test getting task with subtasks included"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            include_subtasks=True
        )
        
        # Assert
        assert result == sample_task
        assert hasattr(result, 'subtasks')
        assert len(result.subtasks) == 2
        assert result.subtasks[0].title == "Create user model"
        assert result.subtasks[1].title == "Implement JWT generation"
        
        # Verify subtask repository was called
        mock_subtask_repo.get_by_task_id.assert_called_once_with(sample_task.id)

    def test_get_task_without_subtasks(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting task without subtasks"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            include_subtasks=False
        )
        
        # Assert
        assert result == sample_task
        # Subtask repository should not be called
        mock_subtask_repo.get_by_task_id.assert_not_called()

    def test_get_task_with_context(self, use_case, mock_task_repo, mock_context_service, sample_task):
        """Test getting task with context data"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        context_data = {
            "feature": "authentication",
            "tech_stack": ["JWT", "bcrypt", "PostgreSQL"],
            "related_docs": ["RFC 7519"]
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_context_service.get_task_context.return_value = context_data
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            include_context=True
        )
        
        # Assert
        assert result == sample_task
        assert hasattr(result, 'context_data')
        assert result.context_data == context_data
        mock_context_service.get_task_context.assert_called_once_with(sample_task.id)

    def test_get_task_completed_status(self, use_case, mock_task_repo):
        """Test getting completed task"""
        # Arrange
        completed_task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Completed Task"),
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")],
            labels=["completed"],
            progress_percentage=100,
            completion_summary="All features implemented successfully",
            testing_notes="Unit tests: 100%, Integration tests: 100%"
        )
        completed_task.completion_date = datetime.now(timezone.utc)
        
        mock_task_repo.get_by_id.return_value = completed_task
        
        # Act
        result = use_case.execute(
            task_id=completed_task.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.status == TaskStatus.DONE
        assert result.progress_percentage == 100
        assert result.completion_summary == "All features implemented successfully"
        assert result.completion_date is not None

    def test_get_task_blocked_status(self, use_case, mock_task_repo):
        """Test getting blocked task"""
        # Arrange
        blocked_task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Blocked Task"),
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            labels=["blocked", "urgent"],
            blocked_reason="Waiting for third-party API access"
        )
        blocked_task.blocked_at = datetime.now(timezone.utc) - timedelta(days=2)
        
        mock_task_repo.get_by_id.return_value = blocked_task
        
        # Act
        result = use_case.execute(
            task_id=blocked_task.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.status == TaskStatus.BLOCKED
        assert result.blocked_reason == "Waiting for third-party API access"
        assert result.blocked_at is not None

    def test_get_task_with_dependencies(self, use_case, mock_task_repo, sample_task):
        """Test getting task with dependency information"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        # Create dependency tasks
        dep_tasks = [
            Task(
                id=dep_id,
                git_branch_id=sample_task.git_branch_id,
                title=TaskTitle(f"Dependency {i}"),
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                labels=[]
            )
            for i, dep_id in enumerate(sample_task.dependencies)
        ]
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_task_repo.get_by_ids.return_value = dep_tasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            expand_dependencies=True
        )
        
        # Assert
        assert result == sample_task
        assert hasattr(result, 'dependency_details')
        assert len(result.dependency_details) == 2
        assert all(dep.status == TaskStatus.DONE for dep in result.dependency_details)

    def test_get_task_minimal_fields(self, use_case, mock_task_repo):
        """Test getting task with minimal fields"""
        # Arrange
        minimal_task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Minimal Task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[UserID("user123")],
            labels=[]
        )
        
        mock_task_repo.get_by_id.return_value = minimal_task
        
        # Act
        result = use_case.execute(
            task_id=minimal_task.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.title.value == "Minimal Task"
        assert result.description is None
        assert result.details is None
        assert result.estimated_effort is None
        assert result.progress_percentage is None

    def test_get_task_with_insights(self, use_case, mock_task_repo, sample_task):
        """Test getting task with insights and learnings"""
        # Arrange
        sample_task.insights_found = [
            "JWT library has built-in refresh token support",
            "Consider rate limiting for auth endpoints"
        ]
        sample_task.challenges_overcome = [
            "Resolved CORS issues with credentials",
            "Optimized token validation performance"
        ]
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(
            task_id=sample_task.id.value,
            user_id="user123"
        )
        
        # Assert
        assert len(result.insights_found) == 2
        assert len(result.challenges_overcome) == 2

    def test_get_task_with_statistics(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test getting task with computed statistics"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            include_statistics=True
        )
        
        # Assert
        assert hasattr(result, 'statistics')
        assert result.statistics.subtask_count == 2
        assert result.statistics.completed_subtasks == 1
        assert result.statistics.time_spent_days == 3  # Created 3 days ago

    def test_get_task_invalid_uuid(self, use_case):
        """Test with invalid UUID format"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid task ID format"):
            use_case.execute(task_id="not-a-uuid", user_id="user123")

    def test_get_task_none_user_id(self, use_case):
        """Test with None user_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="User ID is required"):
            use_case.execute(task_id=str(uuid4()), user_id=None)