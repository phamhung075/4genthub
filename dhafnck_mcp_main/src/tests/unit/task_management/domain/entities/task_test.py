"""Test suite for Task domain entity.

Tests the Task entity including:
- Creation and initialization
- Property validation
- Status transitions
- Priority updates
- Assignee management
- Label management  
- Dependency management
- Subtask management
- Progress tracking
- Task completion
- Domain events
- Business rules enforcement
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.progress import ProgressType, ProgressTimeline
from fastmcp.task_management.domain.enums.agent_roles import AgentRole
from fastmcp.task_management.domain.enums.common_labels import CommonLabel
from fastmcp.task_management.domain.exceptions.vision_exceptions import MissingCompletionSummaryError
from fastmcp.task_management.domain.events.task_events import TaskCreated, TaskUpdated, TaskDeleted
from fastmcp.task_management.domain.events.progress_events import ProgressUpdated


class TestTaskCreation:
    """Test cases for Task creation and initialization."""
    
    def test_create_task_with_minimal_data(self):
        """Test creating a task with minimal required data."""
        task = Task(
            title="Test Task",
            description="Test Description"
        )
        
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.id is None
        assert task.status.value == TaskStatusEnum.TODO.value
        assert task.priority.value == "medium"
        assert task.assignees == []
        assert task.labels == []
        assert task.dependencies == []
        assert task.subtasks == []
        assert task.context_id is None
        assert task.overall_progress == 0
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.created_at == task.updated_at
    
    def test_create_task_with_full_data(self):
        """Test creating a task with all fields specified."""
        task_id = TaskId("test-123")
        created_at = datetime.now(timezone.utc)
        
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            git_branch_id="branch-123",
            details="Additional details",
            estimated_effort="2 hours",
            assignees=["@user1", "@user2"],
            labels=["feature", "bug"],
            dependencies=[TaskId("dep-1"), TaskId("dep-2")],
            subtasks=["sub-1", "sub-2"],
            due_date="2024-12-31",
            created_at=created_at,
            updated_at=created_at,
            context_id="context-123",
            overall_progress=50
        )
        
        assert task.id == task_id
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert task.priority.value == "high"
        assert task.git_branch_id == "branch-123"
        assert task.details == "Additional details"
        assert task.estimated_effort == "2 hours"
        assert task.assignees == ["@user1", "@user2"]
        assert task.labels == ["feature", "bug"]
        assert len(task.dependencies) == 2
        assert task.subtasks == ["sub-1", "sub-2"]
        assert task.due_date == "2024-12-31"
        assert task.context_id == "context-123"
        assert task.overall_progress == 50
    
    def test_create_task_with_factory_method(self):
        """Test creating a task using the factory method."""
        task_id = TaskId("test-456")
        
        task = Task.create(
            id=task_id,
            title="Factory Task",
            description="Created with factory",
            priority=Priority.urgent()
        )
        
        assert task.id == task_id
        assert task.title == "Factory Task"
        assert task.description == "Created with factory"
        assert task.status.value == TaskStatusEnum.TODO.value
        assert task.priority.value == "urgent"
        
        # Check domain event was raised
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskCreated)
        assert events[0].task_id == task_id
        assert events[0].title == "Factory Task"
    
    def test_task_validation_empty_title(self):
        """Test task validation rejects empty title."""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(title="", description="Valid description")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(title="   ", description="Valid description")
    
    def test_task_validation_empty_description(self):
        """Test task validation rejects empty description."""
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task(title="Valid title", description="")
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task(title="Valid title", description="   ")
    
    def test_task_validation_title_too_long(self):
        """Test task validation rejects title exceeding 200 characters."""
        long_title = "a" * 201
        with pytest.raises(ValueError, match="Task title cannot exceed 200 characters"):
            Task(title=long_title, description="Valid description")
    
    def test_task_validation_description_too_long(self):
        """Test task validation rejects description exceeding 1000 characters."""
        long_description = "a" * 1001
        with pytest.raises(ValueError, match="Task description cannot exceed 1000 characters"):
            Task(title="Valid title", description=long_description)
    
    def test_task_equality(self):
        """Test task equality based on ID."""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440789")
        task1 = Task(id=task_id, title="Task 1", description="Description 1")
        task2 = Task(id=task_id, title="Task 2", description="Description 2")
        task3 = Task(id=TaskId("550e8400-e29b-41d4-a716-446655440111"), title="Task 3", description="Description 3")
        
        assert task1 == task2  # Same ID
        assert task1 != task3  # Different ID
        assert task1 != "not a task"  # Different type
    
    def test_task_hash(self):
        """Test task can be hashed for use in sets/dicts."""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440999")
        task = Task(id=task_id, title="Test", description="Test")
        
        # Should be hashable
        task_set = {task}
        assert task in task_set
        
        # Hash should be based on ID
        assert hash(task) == hash(task_id.value)
    
    def test_timezone_handling(self):
        """Test timezone handling for timestamps."""
        # Test with naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        task = Task(
            title="Test",
            description="Test",
            created_at=naive_dt,
            updated_at=naive_dt
        )
        
        # Should be converted to UTC
        assert task.created_at.tzinfo == timezone.utc
        assert task.updated_at.tzinfo == timezone.utc
        
        # Test with aware datetime
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        task2 = Task(
            title="Test2",
            description="Test2",
            created_at=aware_dt,
            updated_at=aware_dt
        )
        
        assert task2.created_at.tzinfo == timezone.utc
        assert task2.updated_at.tzinfo == timezone.utc


class TestTaskProperties:
    """Test cases for Task properties and computed fields."""
    
    def test_is_blocked_property(self):
        """Test is_blocked property."""
        task = Task(title="Test", description="Test")
        assert not task.is_blocked
        
        task.status = TaskStatus(TaskStatusEnum.BLOCKED.value)
        assert task.is_blocked
    
    def test_is_completed_property(self):
        """Test is_completed property."""
        task = Task(title="Test", description="Test")
        assert not task.is_completed
        
        task.status = TaskStatus.done()
        assert task.is_completed
        
        task.status = TaskStatus(TaskStatusEnum.CANCELLED.value)
        assert not task.is_completed  # Cancelled tasks are not considered completed
    
    def test_can_be_assigned_property(self):
        """Test can_be_assigned property."""
        task = Task(title="Test", description="Test")
        assert task.can_be_assigned
        
        task.status = TaskStatus.done()
        assert not task.can_be_assigned
        
        task.status = TaskStatus(TaskStatusEnum.CANCELLED.value)
        assert not task.can_be_assigned
    
    def test_can_be_started_property(self):
        """Test can_be_started method."""
        task = Task(title="Test", description="Test")
        assert task.can_be_started()  # Call method, not property
        
        task.status = TaskStatus.in_progress()
        assert not task.can_be_started()  # Call method, not property
    
    def test_is_overdue_property(self):
        """Test is_overdue property."""
        task = Task(title="Test", description="Test")
        
        # No due date - not overdue
        assert not task.is_overdue()
        
        # Future due date - not overdue
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        task.due_date = future
        assert not task.is_overdue()
        
        # Past due date - overdue
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        task.due_date = past
        assert task.is_overdue()
        
        # Completed task - not overdue even if past due
        task.status = TaskStatus.done()
        assert not task.is_overdue()


class TestTaskStatusUpdates:
    """Test cases for Task status updates."""
    
    def test_update_status_valid_transition(self):
        """Test valid status transitions."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        # TODO -> IN_PROGRESS
        task.update_status(TaskStatus.in_progress())
        assert task.status.value == TaskStatusEnum.IN_PROGRESS.value
        
        # Check event was raised
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskUpdated)
        assert events[0].field_name == "status"
        assert events[0].old_value == TaskStatusEnum.TODO.value
        assert events[0].new_value == TaskStatusEnum.IN_PROGRESS.value
    
    def test_update_status_invalid_transition(self):
        """Test invalid status transitions are rejected."""
        task = Task(title="Test", description="Test")
        task.status = TaskStatus.done()
        
        # DONE -> TODO is invalid
        with pytest.raises(ValueError, match="Cannot transition"):
            task.update_status(TaskStatus.todo())
    
    def test_update_status_updates_timestamp(self):
        """Test status update changes updated_at."""
        task = Task(id=TaskId("test-2"), title="Test", description="Test")
        original_updated = task.updated_at
        
        # Wait a tiny bit to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        task.update_status(TaskStatus.in_progress())
        assert task.updated_at > original_updated
    
    def test_update_status_preserves_context_id(self):
        """Test status update preserves context_id."""
        task = Task(
            id=TaskId("test-3"),
            title="Test",
            description="Test",
            context_id="context-123"
        )
        
        task.update_status(TaskStatus.in_progress())
        assert task.context_id == "context-123"


class TestTaskPriorityUpdates:
    """Test cases for Task priority updates."""
    
    def test_update_priority(self):
        """Test updating task priority."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        assert task.priority.value == "medium"
        
        task.update_priority(Priority.high())
        assert task.priority.value == "high"
        
        # Check event was raised
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskUpdated)
        assert events[0].field_name == "priority"
        assert events[0].old_value == "medium"
        assert events[0].new_value == "high"
    
    def test_update_priority_updates_timestamp(self):
        """Test priority update changes updated_at."""
        task = Task(id=TaskId("test-2"), title="Test", description="Test")
        original_updated = task.updated_at
        
        import time
        time.sleep(0.001)
        
        task.update_priority(Priority.urgent())
        assert task.updated_at > original_updated
    
    def test_update_priority_preserves_context_id(self):
        """Test priority update preserves context_id."""
        task = Task(
            id=TaskId("test-3"),
            title="Test",
            description="Test",
            context_id="context-123"
        )
        
        task.update_priority(Priority.low())
        assert task.context_id == "context-123"


class TestTaskFieldUpdates:
    """Test cases for updating various Task fields."""
    
    def test_update_title(self):
        """Test updating task title."""
        task = Task(id=TaskId("test-1"), title="Original", description="Test")
        
        task.update_title("Updated Title")
        assert task.title == "Updated Title"
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "title"
        assert events[0].old_value == "Original"
        assert events[0].new_value == "Updated Title"
    
    def test_update_title_validation(self):
        """Test title update validation."""
        task = Task(title="Original", description="Test")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task.update_title("")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task.update_title("   ")
    
    def test_update_description(self):
        """Test updating task description."""
        task = Task(id=TaskId("test-1"), title="Test", description="Original")
        
        task.update_description("Updated Description")
        assert task.description == "Updated Description"
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "description"
        assert events[0].old_value == "Original"
        assert events[0].new_value == "Updated Description"
    
    def test_update_description_validation(self):
        """Test description update validation."""
        task = Task(title="Test", description="Original")
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            task.update_description("")
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            task.update_description("   ")
    
    def test_update_details(self):
        """Test updating task details."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        task.update_details("Some implementation details")
        assert task.details == "Some implementation details"
        
        # Can be empty
        task.update_details("")
        assert task.details == ""
    
    def test_update_estimated_effort(self):
        """Test updating estimated effort."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        task.update_estimated_effort("3 hours")
        assert task.estimated_effort == "3 hours"
        
        # Invalid effort defaults to medium
        task.update_estimated_effort("invalid")
        assert task.estimated_effort == "medium"
    
    def test_update_due_date(self):
        """Test updating due date."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        task.update_due_date("2024-12-31")
        assert task.due_date == "2024-12-31"
        
        # Can be None
        task.update_due_date(None)
        assert task.due_date is None
        
        # Invalid format
        with pytest.raises(ValueError, match="Invalid due date format"):
            task.update_due_date("31-12-2024")
    
    def test_update_details_legacy(self):
        """Test the legacy update_details method."""
        task = Task(id=TaskId("test-1"), title="Original", description="Original")
        
        task.update_details_legacy(
            title="New Title",
            description="New Description",
            details="New Details",
            assignees=["@user1"]
        )
        
        assert task.title == "New Title"
        assert task.description == "New Description"
        assert task.details == "New Details"
        assert task.assignees == ["@user1"]
        
        # Check multiple events raised
        events = task.get_events()
        assert len(events) == 4


class TestTaskAssigneeManagement:
    """Test cases for Task assignee management."""
    
    def test_update_assignees(self):
        """Test updating task assignees."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        task.update_assignees(["@user1", "@user2"])
        assert task.assignees == ["@user1", "@user2"]
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "assignees"
    
    def test_update_assignees_validation(self):
        """Test assignee validation and normalization."""
        task = Task(title="Test", description="Test")
        
        # Empty strings are filtered out
        task.update_assignees(["@user1", "", "  ", "@user2"])
        assert task.assignees == ["@user1", "@user2"]
        
        # @ prefix is added to valid roles
        with patch('fastmcp.task_management.domain.enums.agent_roles.AgentRole.is_valid_role', return_value=True):
            task.update_assignees(["coding_agent"])
            assert "@coding_agent" in task.assignees
    
    def test_add_assignee(self):
        """Test adding individual assignee."""
        task = Task(title="Test", description="Test")
        
        task.add_assignee("@user1")
        assert task.assignees == ["@user1"]
        
        # Duplicate not added
        task.add_assignee("@user1")
        assert task.assignees == ["@user1"]
        
        # Add another
        task.add_assignee("@user2")
        assert task.assignees == ["@user1", "@user2"]
    
    def test_add_assignee_with_enum(self):
        """Test adding assignee using AgentRole enum."""
        task = Task(title="Test", description="Test")
        
        # Mock the AgentRole enum
        mock_role = Mock(spec=AgentRole)
        mock_role.value = "coding_agent"
        
        task.add_assignee(mock_role)
        assert "@coding_agent" in task.assignees
    
    def test_remove_assignee(self):
        """Test removing assignee."""
        task = Task(title="Test", description="Test", assignees=["@user1", "@user2"])
        
        task.remove_assignee("@user1")
        assert task.assignees == ["@user2"]
        
        # Removing non-existent does nothing
        task.remove_assignee("@user3")
        assert task.assignees == ["@user2"]
    
    def test_has_assignee(self):
        """Test checking if task has assignee."""
        task = Task(title="Test", description="Test", assignees=["@user1", "@user2"])
        
        assert task.has_assignee("@user1")
        assert task.has_assignee("@user2")
        assert not task.has_assignee("@user3")
    
    def test_get_primary_assignee(self):
        """Test getting primary assignee."""
        task = Task(title="Test", description="Test")
        
        # No assignees
        assert task.get_primary_assignee() is None
        
        # With assignees
        task.assignees = ["@user1", "@user2"]
        assert task.get_primary_assignee() == "@user1"
    
    def test_assignee_count_methods(self):
        """Test assignee count related methods."""
        task = Task(title="Test", description="Test")
        
        assert task.get_assignees_count() == 0
        assert not task.is_multi_assignee()
        
        task.assignees = ["@user1"]
        assert task.get_assignees_count() == 1
        assert not task.is_multi_assignee()
        
        task.assignees = ["@user1", "@user2"]
        assert task.get_assignees_count() == 2
        assert task.is_multi_assignee()
    
    def test_get_assignees_info(self):
        """Test getting assignee role information."""
        task = Task(title="Test", description="Test", assignees=["@user1"])
        
        # Mock the role lookup
        with patch('fastmcp.task_management.domain.enums.agent_roles.AgentRole.get_role_by_slug', return_value=None):
            info = task.get_assignees_info()
            assert len(info) == 1
            assert info[0]["role"] == "@user1"
            assert info[0]["display_name"] == "@User1"


class TestTaskLabelManagement:
    """Test cases for Task label management."""
    
    def test_update_labels(self):
        """Test updating task labels."""
        task = Task(id=TaskId("test-1"), title="Test", description="Test")
        
        task.update_labels(["feature", "bug", "urgent"])
        assert task.labels == ["feature", "bug", "urgent"]
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "labels"
    
    def test_update_labels_validation(self):
        """Test label validation."""
        task = Task(title="Test", description="Test")
        
        # Empty strings filtered out
        task.update_labels(["valid", "", "  ", "another"])
        assert task.labels == ["valid", "another"]
        
        # Long labels rejected
        long_label = "a" * 51
        task.update_labels(["valid", long_label])
        assert task.labels == ["valid"]
    
    def test_add_label(self):
        """Test adding individual label."""
        task = Task(title="Test", description="Test")
        
        task.add_label("feature")
        assert task.labels == ["feature"]
        
        # Duplicate not added
        task.add_label("feature")
        assert task.labels == ["feature"]
        
        # Add another
        task.add_label("bug")
        assert task.labels == ["feature", "bug"]
    
    def test_add_label_with_enum(self):
        """Test adding label using CommonLabel enum."""
        task = Task(title="Test", description="Test")
        
        # Mock the CommonLabel enum
        mock_label = Mock(spec=CommonLabel)
        mock_label.value = "feature"
        
        task.add_label(mock_label)
        assert "feature" in task.labels
    
    def test_remove_label(self):
        """Test removing label."""
        task = Task(title="Test", description="Test", labels=["feature", "bug"])
        
        task.remove_label("feature")
        assert task.labels == ["bug"]
        
        # Removing non-existent does nothing
        task.remove_label("urgent")
        assert task.labels == ["bug"]
    
    def test_get_suggested_labels(self):
        """Test getting suggested labels."""
        task = Task(
            title="Fix authentication bug",
            description="Login fails for users"
        )
        
        # Mock the CommonLabel enum methods
        with patch('fastmcp.task_management.domain.enums.common_labels.CommonLabel') as mock_enum:
            mock_label = Mock()
            mock_label.value = "bug"
            mock_label.get_keywords.return_value = ["bug", "fix", "error"]
            mock_enum.__iter__.return_value = [mock_label]
            
            suggestions = task.get_suggested_labels()
            assert "bug" in suggestions


class TestTaskDependencyManagement:
    """Test cases for Task dependency management."""
    
    def test_add_dependency(self):
        """Test adding task dependency."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        dep_id = TaskId("dep-1")
        
        task.add_dependency(dep_id)
        assert len(task.dependencies) == 1
        assert task.dependencies[0] == dep_id
        
        # Duplicate not added
        task.add_dependency(dep_id)
        assert len(task.dependencies) == 1
    
    def test_add_dependency_self_reference(self):
        """Test task cannot depend on itself."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        with pytest.raises(ValueError, match="Task cannot depend on itself"):
            task.add_dependency(task.id)
    
    def test_remove_dependency(self):
        """Test removing task dependency."""
        dep1 = TaskId("dep-1")
        dep2 = TaskId("dep-2")
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            dependencies=[dep1, dep2]
        )
        
        task.remove_dependency(dep1)
        assert len(task.dependencies) == 1
        assert task.dependencies[0] == dep2
    
    def test_has_dependency(self):
        """Test checking if task has dependency."""
        dep1 = TaskId("dep-1")
        dep2 = TaskId("dep-2")
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            dependencies=[dep1]
        )
        
        assert task.has_dependency(dep1)
        assert not task.has_dependency(dep2)
    
    def test_get_dependency_ids(self):
        """Test getting dependency IDs as strings."""
        dep1 = TaskId("dep-1")
        dep2 = TaskId("dep-2")
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            dependencies=[dep1, dep2]
        )
        
        dep_ids = task.get_dependency_ids()
        assert dep_ids == ["dep-1", "dep-2"]
    
    def test_clear_dependencies(self):
        """Test clearing all dependencies."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            dependencies=[TaskId("dep-1"), TaskId("dep-2")]
        )
        
        task.clear_dependencies()
        assert task.dependencies == []
    
    def test_has_circular_dependency(self):
        """Test circular dependency check."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        # Self reference
        assert task.has_circular_dependency(task.id)
        
        # Already exists
        dep = TaskId("dep-1")
        task.add_dependency(dep)
        assert task.has_circular_dependency(dep)
        
        # New dependency
        assert not task.has_circular_dependency(TaskId("dep-2"))


class TestTaskSubtaskManagement:
    """Test cases for Task subtask management."""
    
    def test_add_subtask(self):
        """Test adding subtask."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        subtask_id = task.add_subtask("sub-1")
        assert subtask_id == "sub-1"
        assert task.subtasks == ["sub-1"]
        
        # Duplicate not added
        task.add_subtask("sub-1")
        assert task.subtasks == ["sub-1"]
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtasks"
        assert events[0].old_value == "subtask_added"
        assert events[0].new_value == "sub-1"
    
    def test_add_subtask_validation(self):
        """Test subtask ID validation."""
        task = Task(title="Test", description="Test")
        
        with pytest.raises(ValueError, match="Subtask ID must be a non-empty string"):
            task.add_subtask("")
        
        with pytest.raises(ValueError, match="Subtask ID must be a non-empty string"):
            task.add_subtask(None)
    
    def test_remove_subtask(self):
        """Test removing subtask."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            subtasks=["sub-1", "sub-2"]
        )
        
        result = task.remove_subtask("sub-1")
        assert result is True
        assert task.subtasks == ["sub-2"]
        
        # Remove non-existent
        result = task.remove_subtask("sub-3")
        assert result is False
        assert task.subtasks == ["sub-2"]
    
    def test_get_subtask(self):
        """Test getting subtask."""
        task = Task(
            title="Test",
            description="Test",
            subtasks=["sub-1", "sub-2"]
        )
        
        assert task.get_subtask("sub-1") == "sub-1"
        assert task.get_subtask("sub-3") is None
        
        # Test alias method
        assert task.get_subtask_by_id("sub-1") == "sub-1"
    
    def test_subtask_progress_methods(self):
        """Test subtask progress methods return basic info."""
        task = Task(
            title="Test",
            description="Test",
            subtasks=["sub-1", "sub-2"]
        )
        
        progress = task.get_subtask_progress()
        assert progress["total"] == 2
        assert progress["completed"] == 0  # Cannot determine without repository
        assert progress["percentage"] == 0
        
        # Test with no subtasks
        task.subtasks = []
        progress = task.get_subtask_progress()
        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["percentage"] == 0
    
    def test_all_subtasks_completed(self):
        """Test all_subtasks_completed method."""
        task = Task(title="Test", description="Test")
        
        # No subtasks = all completed
        assert task.all_subtasks_completed()
        
        # With subtasks = cannot determine, return False
        task.subtasks = ["sub-1", "sub-2"]
        assert not task.all_subtasks_completed()
    
    def test_clean_invalid_subtasks(self):
        """Test cleaning invalid subtasks."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            subtasks=["sub-1", 123, None, "sub-2", {}]  # Mix of valid and invalid
        )
        
        removed = task.clean_invalid_subtasks()
        assert removed == 3  # 123, None, and {} removed
        assert task.subtasks == ["sub-1", "sub-2"]
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtasks"
        assert "removed_3_invalid_subtasks" in events[0].old_value


class TestTaskCompletion:
    """Test cases for Task completion."""
    
    def test_complete_task_success(self):
        """Test successful task completion."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            context_id="context-123"
        )
        
        task.complete_task(
            completion_summary="Task completed successfully",
            context_updated_at=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        
        assert task.status.value == TaskStatusEnum.DONE.value
        assert task.get_completion_summary() == "Task completed successfully"
        
        # Check events
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "status"
        assert events[0].metadata["completion_summary"] == "Task completed successfully"
    
    def test_complete_task_missing_summary(self):
        """Test completion fails without summary."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary=None)
        
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary="")
        
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary="   ")
    
    def test_complete_task_without_context_allowed(self):
        """Test completion is allowed without context (with warning)."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        # Should not raise error
        task.complete_task(completion_summary="Completed without context")
        assert task.status.value == TaskStatusEnum.DONE.value
    
    def test_complete_task_context_timing_validation(self):
        """Test context timing validation."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            context_id="context-123",
            updated_at=now
        )
        
        # Context updated before task - should fail
        with pytest.raises(ValueError, match="Context must be updated AFTER"):
            task.complete_task(
                completion_summary="Summary",
                context_updated_at=now - timedelta(seconds=10)
            )
        
        # Context updated after task - should succeed
        task.complete_task(
            completion_summary="Summary",
            context_updated_at=now + timedelta(seconds=10)
        )
        assert task.status.value == TaskStatusEnum.DONE.value
    
    def test_complete_task_with_subtasks(self):
        """Test completing task with subtasks."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test",
            subtasks=["sub-1", "sub-2"],
            context_id="context-123"
        )
        
        task.complete_task(
            completion_summary="All done",
            context_updated_at=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        
        # Check subtask event
        events = task.get_events()
        assert len(events) == 2  # Status update + subtasks completion
        assert events[1].field_name == "subtasks"
        assert events[1].old_value == "all_subtasks_completed"
    
    def test_can_be_completed_method(self):
        """Test can_be_completed validation."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        # No subtasks - can complete
        assert task.can_be_completed()
        
        # With subtasks - cannot complete (no repository access)
        task.subtasks = ["sub-1"]
        assert not task.can_be_completed()
        
        # Test with context timing
        task.subtasks = []
        now = datetime.now(timezone.utc)
        task.updated_at = now
        
        # Context older than task
        assert not task.can_be_completed(context_updated_at=now - timedelta(seconds=1))
        
        # Context newer than task
        assert task.can_be_completed(context_updated_at=now + timedelta(seconds=1))


class TestTaskProgress:
    """Test cases for Task progress tracking."""
    
    def test_update_progress(self):
        """Test updating task progress."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        task.update_progress(
            progress_type=ProgressType.IMPLEMENTATION,
            percentage=50.0,
            description="Half way done",
            metadata={"notes": "Making good progress"},
            agent_id="agent-1"
        )
        
        assert task.overall_progress == 50.0
        assert task.progress_timeline is not None
        
        # Check event
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], ProgressUpdated)
        assert events[0].progress_type == ProgressType.IMPLEMENTATION
        assert events[0].new_percentage == 50.0
    
    def test_update_progress_validation(self):
        """Test progress percentage validation."""
        task = Task(title="Test", description="Test")
        
        with pytest.raises(ValueError, match="Progress percentage must be between"):
            task.update_progress(ProgressType.DESIGN, -10)
        
        with pytest.raises(ValueError, match="Progress percentage must be between"):
            task.update_progress(ProgressType.DESIGN, 110)
    
    def test_progress_milestone_tracking(self):
        """Test progress milestone tracking."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        # Add milestones
        task.add_progress_milestone("Half Way", 50.0)
        task.add_progress_milestone("Almost Done", 90.0)
        
        # Update progress to trigger milestone
        task.update_progress(ProgressType.IMPLEMENTATION, 50.0)
        
        events = task.get_events()
        # Should have progress update and milestone reached events
        assert any(hasattr(e, 'milestone_name') for e in events)
    
    def test_get_progress_by_type(self):
        """Test getting progress by type."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        # No progress yet
        assert task.get_progress_by_type(ProgressType.DESIGN) == 0.0
        
        # Add progress
        task.update_progress(ProgressType.DESIGN, 75.0)
        assert task.get_progress_by_type(ProgressType.DESIGN) == 75.0
        assert task.get_progress_by_type(ProgressType.TESTING) == 0.0
    
    def test_has_progress_type(self):
        """Test checking if progress type exists."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        assert not task.has_progress_type(ProgressType.DESIGN)
        
        task.update_progress(ProgressType.DESIGN, 25.0)
        assert task.has_progress_type(ProgressType.DESIGN)
        assert not task.has_progress_type(ProgressType.REVIEW)
    
    def test_get_progress_timeline_data(self):
        """Test getting progress timeline data."""
        task = Task(id=TaskId("task-1"), title="Test", description="Test")
        
        # No timeline yet
        data = task.get_progress_timeline_data(hours=24)
        assert data == []
        
        # Add progress
        task.update_progress(ProgressType.IMPLEMENTATION, 30.0)
        data = task.get_progress_timeline_data(hours=24)
        assert len(data) > 0
        assert data[0]["percentage"] == 30.0


class TestTaskContext:
    """Test cases for Task context management."""
    
    def test_set_context_id(self):
        """Test setting context ID."""
        task = Task(title="Test", description="Test")
        
        task.set_context_id("context-123")
        assert task.context_id == "context-123"
    
    def test_clear_context_id(self):
        """Test clearing context ID."""
        task = Task(title="Test", description="Test", context_id="context-123")
        
        task.clear_context_id()
        assert task.context_id is None
    
    def test_has_updated_context(self):
        """Test checking if context is updated."""
        task = Task(title="Test", description="Test")
        
        assert not task.has_updated_context()
        
        task.context_id = "context-123"
        assert task.has_updated_context()


class TestTaskSerialization:
    """Test cases for Task serialization."""
    
    def test_to_dict_minimal(self):
        """Test converting minimal task to dict."""
        task = Task(
            id=TaskId("task-1"),
            title="Test Task",
            description="Test Description"
        )
        
        data = task.to_dict()
        
        assert data["id"] == "task-1"
        assert data["title"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert data["assignees"] == []
        assert data["labels"] == []
        assert data["dependencies"] == []
        assert data["subtasks"] == []
        assert data["overall_progress"] == 0
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
    
    def test_to_dict_with_progress(self):
        """Test converting task with progress to dict."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        task.update_progress(ProgressType.IMPLEMENTATION, 75.0)
        
        data = task.to_dict()
        assert "progress_timeline" in data
        assert data["overall_progress"] == 75.0


class TestTaskEvents:
    """Test cases for Task domain events."""
    
    def test_mark_as_deleted(self):
        """Test marking task as deleted."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        task.mark_as_deleted()
        
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskDeleted)
        assert events[0].task_id == task.id
        assert events[0].title == "Test"
    
    def test_mark_as_retrieved(self):
        """Test marking task as retrieved."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        task.mark_as_retrieved()
        
        events = task.get_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "TaskRetrieved"
        assert events[0].task_id == task.id
    
    def test_get_events_clears_list(self):
        """Test get_events returns and clears event list."""
        task = Task(
            id=TaskId("task-1"),
            title="Test",
            description="Test"
        )
        
        task.update_title("New Title")
        task.update_priority(Priority.high())
        
        # First call gets events
        events = task.get_events()
        assert len(events) == 2
        
        # Second call gets empty list
        events = task.get_events()
        assert len(events) == 0


class TestTaskHelperMethods:
    """Test cases for Task helper methods."""
    
    def test_get_effort_level(self):
        """Test getting effort level."""
        task = Task(title="Test", description="Test")
        
        # Default
        assert task.get_effort_level() == "medium"
        
        # Valid effort
        task.estimated_effort = "1 hour"
        with patch('fastmcp.task_management.domain.enums.estimated_effort.EstimatedEffort') as mock_enum:
            mock_effort = Mock()
            mock_effort.get_level.return_value = "small"  # Use the actual return value
            mock_enum.return_value = mock_effort
            assert task.get_effort_level() == "small"
        
        # Invalid effort
        task.estimated_effort = "invalid"
        assert task.get_effort_level() == "medium"
    
    def test_get_assignee_role_info(self):
        """Test getting assignee role info."""
        task = Task(title="Test", description="Test")
        
        # No assignees
        assert task.get_assignee_role_info() is None
        
        # With assignee
        task.assignees = ["@user1"]
        with patch('fastmcp.task_management.domain.enums.agent_roles.AgentRole.get_role_by_slug', return_value=None):
            info = task.get_assignee_role_info()
            assert info["role"] == "@user1"
            assert info["display_name"] == "@User1"


if __name__ == "__main__":
    pytest.main([__file__])