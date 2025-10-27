"""
Test suite for UpdateSubtask use case

Tests the business logic for updating subtask properties.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.update_subtask import UpdateSubtaskUseCase
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
    InvalidTaskStateError,
    ValidationError
)


class TestUpdateSubtaskUseCase:
    """Test suite for UpdateSubtask use case"""

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_task_repo, mock_subtask_repo, mock_event_bus):
        """Create use case instance with mocks"""
        return UpdateSubtaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_task(self):
        """Create sample parent task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Parent Task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["backend"]
        )
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        return task

    @pytest.fixture
    def sample_subtask(self, sample_task):
        """Create sample subtask"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Original subtask title",
            description="Original description",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")],
            progress_percentage=0
        )
        subtask.created_at = datetime.now(timezone.utc)
        subtask.updated_at = datetime.now(timezone.utc)
        return subtask

    def test_update_subtask_basic_fields(self, use_case, mock_task_repo, mock_subtask_repo, mock_event_bus, sample_task, sample_subtask):
        """Test updating basic subtask fields"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "title": "Updated subtask title",
            "description": "Updated description",
            "priority": "high",
            "status": "in_progress"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.title == "Updated subtask title"
        assert result.description == "Updated description"
        assert result.priority == TaskPriority.HIGH
        assert result.status == TaskStatus.IN_PROGRESS
        
        # Verify updates were saved
        mock_subtask_repo.update.assert_called_once_with(sample_subtask)
        mock_event_bus.publish.assert_called_once()

    def test_update_subtask_progress_percentage(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating progress percentage"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "progress_percentage": 75,
            "progress_notes": "Completed main implementation"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.progress_percentage == 75
        assert result.progress_notes == "Completed main implementation"
        # Status should auto-update to in_progress
        assert result.status == TaskStatus.IN_PROGRESS

    def test_update_subtask_100_percent_auto_completes(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test setting progress to 100% auto-completes subtask"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "progress_percentage": 100
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.progress_percentage == 100
        assert result.status == TaskStatus.DONE
        assert result.completion_date is not None

    def test_update_subtask_assignees(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating subtask assignees"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "assignees": ["user456", "user789"]
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert len(result.assignees) == 2
        assert UserID("user456") in result.assignees
        assert UserID("user789") in result.assignees

    def test_update_subtask_labels(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating subtask labels"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "labels": ["frontend", "urgent", "bug"]
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.labels == ["frontend", "urgent", "bug"]

    def test_update_subtask_blocked_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating subtask to blocked status"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        update_data = {
            "status": "blocked",
            "blockers": "Waiting for API documentation"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.status == TaskStatus.BLOCKED
        assert result.blockers == "Waiting for API documentation"

    def test_update_subtask_task_not_found(self, use_case, mock_task_repo):
        """Test updating subtask when parent task doesn't exist"""
        # Arrange
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        
        mock_task_repo.get_by_id.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={"title": "New title"}
            )

    def test_update_subtask_not_found(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test updating non-existent subtask"""
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
                update_data={"title": "New title"}
            )

    def test_update_subtask_wrong_parent_task(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test updating subtask that belongs to different task"""
        # Arrange
        task_id = sample_task.id.value
        different_task_id = TaskID(str(uuid4()))
        
        wrong_subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=different_task_id,  # Different parent
            title="Wrong subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = wrong_subtask
        
        # Act & Assert
        with pytest.raises(ValueError, match="does not belong to task"):
            use_case.execute(
                task_id=task_id,
                subtask_id=wrong_subtask.id.value,
                update_data={"title": "New title"}
            )

    def test_update_subtask_of_completed_parent_task(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test cannot update subtask of completed parent task"""
        # Arrange
        sample_task.status = TaskStatus.DONE  # Parent is completed
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert
        with pytest.raises(InvalidTaskStateError, match="Cannot modify subtask of completed task"):
            use_case.execute(
                task_id=sample_task.id.value,
                subtask_id=sample_subtask.id.value,
                update_data={"title": "New title"}
            )

    def test_update_subtask_invalid_priority(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating with invalid priority value"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid priority"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={"priority": "invalid_priority"}
            )

    def test_update_subtask_invalid_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating with invalid status value"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid status"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={"status": "invalid_status"}
            )

    def test_update_subtask_invalid_progress(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test updating with invalid progress percentage"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert - Negative progress
        with pytest.raises(ValidationError, match="Progress must be between 0 and 100"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={"progress_percentage": -10}
            )
        
        # Act & Assert - Progress over 100
        with pytest.raises(ValidationError, match="Progress must be between 0 and 100"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={"progress_percentage": 150}
            )

    def test_update_subtask_partial_update(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test partial update only changes specified fields"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        original_description = sample_subtask.description
        original_assignees = sample_subtask.assignees.copy()
        
        update_data = {
            "title": "Only update title"
            # Other fields not specified
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data=update_data
        )
        
        # Assert
        assert result.title == "Only update title"
        assert result.description == original_description  # Unchanged
        assert result.assignees == original_assignees  # Unchanged
        assert result.priority == TaskPriority.MEDIUM  # Unchanged

    def test_update_subtask_empty_update(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test update with empty data"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act & Assert
        with pytest.raises(ValidationError, match="No update data provided"):
            use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                update_data={}
            )

    def test_update_subtask_updates_parent_task(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtask):
        """Test parent task is updated when subtask changes"""
        # Arrange
        task_id = sample_task.id.value
        subtask_id = sample_subtask.id.value
        original_task_updated_at = sample_task.updated_at
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_id.return_value = sample_subtask
        
        # Act
        use_case.execute(
            task_id=task_id,
            subtask_id=subtask_id,
            update_data={"title": "Updated"}
        )
        
        # Assert
        mock_task_repo.update.assert_called_once_with(sample_task)
        assert sample_task.updated_at > original_task_updated_at