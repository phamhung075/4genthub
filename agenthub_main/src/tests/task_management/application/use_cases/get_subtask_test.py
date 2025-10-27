"""
Test suite for GetSubtask use case

Tests the business logic for retrieving individual subtask details.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.get_subtask import GetSubtaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskTitle,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    UserID
)
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    SubtaskNotFoundError,
    UnauthorizedAccessError
)


class TestGetSubtaskUseCase:
    """Test suite for GetSubtask use case"""

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_task_repo, mock_subtask_repo):
        """Create use case instance with mocks"""
        return GetSubtaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample parent task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Parent Task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            labels=["backend"]
        )
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        return task

    @pytest.fixture
    def sample_subtask(self, sample_task):
        """Create a sample subtask"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Implement validation logic",
            description="Add input validation for user data",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            progress_percentage=60,
            details="Using zod schema validation",
            estimated_effort="2 hours"
        )
        subtask.created_at = datetime.now(timezone.utc)
        subtask.updated_at = datetime.now(timezone.utc)
        return subtask

    def test_get_subtask_success(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test successfully getting a subtask"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id
        )
        
        # Assert
        assert result == sample_subtask
        assert result.id.value == subtask_id
        assert result.title == "Implement validation logic"
        assert result.progress_percentage == 60
        
        # Verify repository calls
        mock_task_repo.get_by_id.assert_called_once_with(TaskID(task_id))
        mock_subtask_repo.get_by_id.assert_called_once_with(SubtaskID(subtask_id))

    def test_get_subtask_task_not_found(self, use_case, mock_task_repo):
        """Test getting subtask when parent task doesn't exist"""
        # Arrange
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        
        mock_task_repo.get_by_id.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                user_id="user123"
            )

    def test_get_subtask_not_found(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting non-existent subtask"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = str(uuid4())
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.side_effect = SubtaskNotFoundError(f"Subtask {subtask_id} not found")
        
        # Act & Assert
        with pytest.raises(SubtaskNotFoundError):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                user_id="user123"
            )

    def test_get_subtask_unauthorized_user(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test getting subtask by unauthorized user"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        unauthorized_user = "user999"  # Not in task assignees
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert
        with pytest.raises(UnauthorizedAccessError, match="not authorized to access"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                user_id=unauthorized_user
            )

    def test_get_subtask_wrong_parent_task(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting subtask that belongs to different task"""
        # Arrange
        task_id = sample_task.id.value
        
        # Create subtask for different task
        different_task_id = TaskID(str(uuid4()))
        wrong_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=different_task_id,  # Different parent
            title="Wrong subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")]
        )
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = wrong_subtask
        
        # Act & Assert
        with pytest.raises(ValueError, match="does not belong to task"):
            use_case.execute(
                task_id=task_id,
                subtask_id=wrong_subtask.id.value,
                user_id="user123"
            )

    def test_get_subtask_with_all_fields(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting subtask with all optional fields populated"""
        # Arrange
        complete_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Complete subtask",
            description="Full description",
            status=TaskStatus.REVIEW,
            priority=TaskPriority.URGENT,
            assignees=[UserID("user1"), UserID("user2"), UserID("user3")],
            labels=["feature", "api", "security"],
            progress_percentage=90,
            details="Comprehensive implementation details",
            estimated_effort="5 hours",
            progress_notes="Almost complete, in final review",
            blockers="Waiting for security team approval",
            completion_summary="N/A - not yet complete"
        )
        complete_subtask.created_at = datetime.now(timezone.utc)
        complete_subtask.updated_at = datetime.now(timezone.utc)
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = complete_subtask
        
        # Act
        result = use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=complete_subtask.id.value,
            user_id="user123"
        )
        
        # Assert all fields
        assert result.title == "Complete subtask"
        assert result.description == "Full description"
        assert result.status == TaskStatus.REVIEW
        assert result.priority == TaskPriority.URGENT
        assert len(result.assignees) == 3
        assert result.labels == ["feature", "api", "security"]
        assert result.progress_percentage == 90
        assert result.details == "Comprehensive implementation details"
        assert result.estimated_effort == "5 hours"
        assert result.progress_notes == "Almost complete, in final review"
        assert result.blockers == "Waiting for security team approval"

    def test_get_subtask_completed_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting completed subtask"""
        # Arrange
        completed_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Completed subtask",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")],
            progress_percentage=100,
            completion_summary="Successfully implemented all features"
        )
        completed_subtask.completion_date = datetime.now(timezone.utc)
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = completed_subtask
        
        # Act
        result = use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=completed_subtask.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.status == TaskStatus.DONE
        assert result.progress_percentage == 100
        assert result.completion_summary == "Successfully implemented all features"
        assert result.completion_date is not None

    def test_get_subtask_blocked_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting blocked subtask"""
        # Arrange
        blocked_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Blocked subtask",
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            blockers="Waiting for external API documentation",
            progress_percentage=30
        )
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = blocked_subtask
        
        # Act
        result = use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=blocked_subtask.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.status == TaskStatus.BLOCKED
        assert result.blockers == "Waiting for external API documentation"
        assert result.progress_percentage == 30

    def test_get_subtask_minimal_fields(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting subtask with minimal fields"""
        # Arrange
        minimal_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Minimal subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[UserID("user123")]
        )
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = minimal_subtask
        
        # Act
        result = use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=minimal_subtask.id.value,
            user_id="user123"
        )
        
        # Assert
        assert result.title == "Minimal subtask"
        assert result.description is None
        assert result.details is None
        assert result.progress_percentage is None
        assert result.labels == []

    def test_get_subtask_authorized_by_subtask_assignee(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test user authorized if they're assigned to subtask but not parent task"""
        # Arrange
        # Create task without user456
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Parent Task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],  # Only user123
            labels=["backend"]
        )
        
        # Create subtask with user456
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=task.id,
            title="Subtask for user456",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user456")]  # Different user
        )
        
        mock_task_repo.get_by_id.return_value = task
        mock_subtask_repo.get_by_id.return_value = subtask
        
        # Act - Should succeed because user456 is assigned to subtask
        result = use_case.execute(
            task_id=task.id.value,
            subtask_id=subtask.id.value,
            user_id="user456"
        )
        
        # Assert
        assert result == subtask