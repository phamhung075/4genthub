"""
Test suite for AddSubtask use case

Tests the business logic for adding subtasks to tasks.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
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
    InvalidTaskStateError,
    ValidationError
)


class TestAddSubtaskUseCase:
    """Test suite for AddSubtask use case"""

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
        return AddSubtaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Parent Task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user1"), UserID("user2")],
            labels=["backend"]
        )
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        return task

    def test_add_subtask_success(self, use_case, mock_task_repo, mock_subtask_repo, mock_event_bus, sample_task):
        """Test successfully adding a subtask"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Implement validation",
            "description": "Add input validation",
            "priority": "high",
            "assignees": ["user1"]
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.create.return_value = None
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert isinstance(result, Subtask)
        assert result.title == "Implement validation"
        assert result.description == "Add input validation"
        assert result.priority == TaskPriority.HIGH
        assert result.status == TaskStatus.TODO  # Default status
        assert result.task_id == sample_task.id
        assert result.assignees == [UserID("user1")]
        
        # Verify repository calls
        mock_task_repo.get_by_id.assert_called_once_with(TaskID(task_id))
        mock_subtask_repo.create.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()

    def test_add_subtask_inherits_parent_assignees(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test subtask inherits parent assignees when none specified"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Subtask without assignees",
            "priority": "medium"
            # No assignees specified
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert result.assignees == sample_task.assignees  # Inherited from parent
        assert len(result.assignees) == 2
        assert UserID("user1") in result.assignees
        assert UserID("user2") in result.assignees

    def test_add_subtask_task_not_found(self, use_case, mock_task_repo):
        """Test adding subtask when task doesn't exist"""
        # Arrange
        task_id = str(uuid4())
        subtask_data = {"title": "Subtask"}
        
        mock_task_repo.get_by_id.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError):
            use_case.execute(task_id, subtask_data)

    def test_add_subtask_to_completed_task_fails(self, use_case, mock_task_repo, sample_task):
        """Test cannot add subtask to completed task"""
        # Arrange
        sample_task.status = TaskStatus.DONE
        task_id = sample_task.id.value
        subtask_data = {"title": "Late subtask"}
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(InvalidTaskStateError, match="Cannot add subtask to completed task"):
            use_case.execute(task_id, subtask_data)

    def test_add_subtask_to_cancelled_task_fails(self, use_case, mock_task_repo, sample_task):
        """Test cannot add subtask to cancelled task"""
        # Arrange
        sample_task.status = TaskStatus.CANCELLED
        task_id = sample_task.id.value
        subtask_data = {"title": "Late subtask"}
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(InvalidTaskStateError, match="Cannot add subtask to cancelled task"):
            use_case.execute(task_id, subtask_data)

    def test_add_subtask_with_all_fields(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test adding subtask with all optional fields"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Complete subtask",
            "description": "Full description",
            "priority": "urgent",
            "assignees": ["user3", "user4"],
            "labels": ["frontend", "urgent"],
            "details": "Additional implementation details",
            "estimated_effort": "4 hours",
            "progress_notes": "Starting implementation"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert result.title == "Complete subtask"
        assert result.description == "Full description"
        assert result.priority == TaskPriority.URGENT
        assert result.assignees == [UserID("user3"), UserID("user4")]
        assert result.labels == ["frontend", "urgent"]
        assert result.details == "Additional implementation details"
        assert result.estimated_effort == "4 hours"
        assert result.progress_notes == "Starting implementation"

    def test_add_subtask_invalid_priority(self, use_case, mock_task_repo, sample_task):
        """Test adding subtask with invalid priority"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Subtask",
            "priority": "invalid_priority"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid priority"):
            use_case.execute(task_id, subtask_data)

    def test_add_subtask_empty_title_fails(self, use_case, mock_task_repo, sample_task):
        """Test adding subtask with empty title fails"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "",  # Empty
            "priority": "medium"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            use_case.execute(task_id, subtask_data)

    def test_add_subtask_updates_parent_task(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test parent task is updated when subtask is added"""
        # Arrange
        original_updated_at = sample_task.updated_at
        task_id = sample_task.id.value
        subtask_data = {"title": "New subtask"}
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        use_case.execute(task_id, subtask_data)
        
        # Assert
        mock_task_repo.update.assert_called_once_with(sample_task)
        assert sample_task.updated_at > original_updated_at

    def test_add_multiple_subtasks(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test adding multiple subtasks to same task"""
        # Arrange
        task_id = sample_task.id.value
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act - Add 3 subtasks
        for i in range(3):
            subtask_data = {
                "title": f"Subtask {i+1}",
                "priority": "medium"
            }
            result = use_case.execute(task_id, subtask_data)
            assert result.title == f"Subtask {i+1}"
        
        # Assert
        assert mock_subtask_repo.create.call_count == 3
        assert mock_event_bus.publish.call_count == 3

    def test_add_subtask_with_initial_progress(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test adding subtask with initial progress"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Partially done subtask",
            "progress_percentage": 25,
            "status": "in_progress"
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert result.progress_percentage == 25
        assert result.status == TaskStatus.IN_PROGRESS

    def test_subtask_id_generation(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test subtask gets valid UUID"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {"title": "Test subtask"}
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert isinstance(result.id, SubtaskID)
        # Verify it's a valid UUID
        uuid4(result.id.value)  # Will raise if not valid

    def test_add_subtask_rollback_on_error(self, use_case, mock_task_repo, mock_subtask_repo, mock_event_bus, sample_task):
        """Test transaction rollback on error"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {"title": "Failing subtask"}
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.create.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            use_case.execute(task_id, subtask_data)
        
        # Verify event was not published due to error
        mock_event_bus.publish.assert_not_called()

    def test_add_subtask_preserves_parent_labels(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test subtask can have different labels than parent"""
        # Arrange
        task_id = sample_task.id.value
        subtask_data = {
            "title": "Frontend subtask",
            "labels": ["frontend", "ui"]  # Different from parent's ["backend"]
        }
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act
        result = use_case.execute(task_id, subtask_data)
        
        # Assert
        assert result.labels == ["frontend", "ui"]
        assert sample_task.labels == ["backend"]  # Parent unchanged