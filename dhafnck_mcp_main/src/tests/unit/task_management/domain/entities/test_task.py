"""Unit tests for Task entity."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.events.task_events import (
    TaskCreated, TaskUpdated, TaskDeleted
)


class TestTaskCreation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task entity creation."""
    
    def test_create_task_with_required_fields(self):
        """Test creating task with only required fields."""
        task = Task(
            title="Test Task",
            description="Test Description"
        )
        
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status.value == TaskStatusEnum.TODO.value
        assert task.priority.value in [p.label for p in PriorityLevel]  # Any valid priority
        assert task.assignees == []
        assert task.labels == []
        assert task.created_at is not None
        assert task.updated_at is not None
        # Timestamps should be very close but may not be exactly equal
        assert abs((task.updated_at - task.created_at).total_seconds()) < 1
    
    def test_create_task_with_all_fields(self):
        """Test creating task with all fields specified."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        status = TaskStatus.in_progress()
        priority = Priority.high()
        created_at = datetime.now(timezone.utc) - timedelta(days=1)
        updated_at = datetime.now(timezone.utc)
        
        task = Task(
            id=task_id,
            title="Complete Task",
            description="Detailed Description",
            status=status,
            priority=priority,
            git_branch_id="branch-123",
            details="Additional details",
            estimated_effort="2 days",
            assignees=["@agent1", "@agent2"],
            labels=["feature", "backend"],
            due_date="2024-12-31",
            created_at=created_at,
            updated_at=updated_at,
            context_id="context-123"
        )
        
        assert task.id == task_id
        assert task.title == "Complete Task"
        assert task.description == "Detailed Description"
        assert task.status == status
        assert task.priority == priority
        assert task.git_branch_id == "branch-123"
        assert task.details == "Additional details"
        assert task.estimated_effort == "2 days"
        assert task.assignees == ["@agent1", "@agent2"]
        assert task.labels == ["feature", "backend"]
        assert task.due_date == "2024-12-31"
        assert task.created_at == created_at
        assert task.updated_at == updated_at
        assert task.context_id == "context-123"
    
    def test_create_task_with_factory_method(self):
        """Test creating task using factory method."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        task = Task.create(
            id=task_id,
            title="Factory Task",
            description="Created via factory",
            git_branch_id="branch-123"
        )
        
        assert task.id == task_id
        assert task.title == "Factory Task"
        assert task.description == "Created via factory"
        assert task.git_branch_id == "branch-123"
        assert len(task._events) == 1
        assert isinstance(task._events[0], TaskCreated)
    
    def test_create_task_with_subtasks(self):
        """Test creating task with subtask IDs only."""
        import uuid
        subtask_ids = [
            str(uuid.uuid4()),  # Subtask ID 1
            str(uuid.uuid4())   # Subtask ID 2
        ]
        
        task = Task(
            title="Parent Task",
            description="Task with subtasks",
            subtasks=subtask_ids
        )
        
        assert len(task.subtasks) == 2
        assert task.subtasks[0] == subtask_ids[0]
        assert task.subtasks[1] == subtask_ids[1]
    
    def test_create_task_with_dependencies(self):
        """Test creating task with dependencies."""
        dep1 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        dep2 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        
        task = Task(
            title="Dependent Task",
            description="Task with dependencies",
            dependencies=[dep1, dep2]
        )
        
        assert len(task.dependencies) == 2
        assert dep1 in task.dependencies
        assert dep2 in task.dependencies


class TestTaskValidation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task entity validation."""
    
    def test_task_title_required(self):
        """Test that task title is required."""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(title="", description="Test Description")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task(title="   ", description="Test Description")
    
    def test_task_description_required(self):
        """Test that task description is required."""
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task(title="Test Task", description="")
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task(title="Test Task", description="   ")
    
    def test_task_title_max_length(self):
        """Test task title maximum length."""
        long_title = "x" * 201
        with pytest.raises(ValueError, match="Task title cannot exceed 200 characters"):
            Task(title=long_title, description="Test Description")
    
    def test_task_description_max_length(self):
        """Test task description maximum length."""
        long_description = "x" * 1001
        with pytest.raises(ValueError, match="Task description cannot exceed 1000 characters"):
            Task(title="Test Task", description=long_description)
    
    def test_task_title_edge_cases(self):
        """Test task title edge cases."""
        # Exactly 200 characters should work
        title_200 = "x" * 200
        task = Task(title=title_200, description="Test")
        assert len(task.title) == 200
        
        # Title with only spaces after strip should fail
        with pytest.raises(ValueError):
            Task(title="\n\t  \n", description="Test")


class TestTaskProperties:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task entity properties."""
    
    def test_is_blocked_property(self):
        """Test is_blocked property."""
        task = Task(title="Test", description="Test")
        assert not task.is_blocked
        
        task.status = TaskStatus.blocked()
        assert task.is_blocked
    
    def test_is_completed_property(self):
        """Test is_completed property."""
        task = Task(title="Test", description="Test")
        assert not task.is_completed
        
        task.status = TaskStatus.done()
        assert task.is_completed
    
    def test_can_be_assigned_property(self):
        """Test can_be_assigned property."""
        task = Task(title="Test", description="Test")
        assert task.can_be_assigned
        
        task.status = TaskStatus.done()
        assert not task.can_be_assigned
        
        task.status = TaskStatus.cancelled()
        assert not task.can_be_assigned
        
        task.status = TaskStatus.in_progress()
        assert task.can_be_assigned


class TestTaskStatusUpdates:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task status update operations."""
    
    def test_update_status_valid_transition(self):
        """Test valid status transitions."""
        task = Task(title="Test", description="Test")
        
        # Todo -> In Progress
        task.update_status(TaskStatus.in_progress())
        assert task.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert task.context_id is None  # Should be cleared
        assert len(task._events) == 1
        assert isinstance(task._events[0], TaskUpdated)
        assert task._events[0].field_name == "status"
    
    def test_update_status_invalid_transition(self):
        """Test invalid status transitions."""
        task = Task(title="Test", description="Test")
        
        # Todo -> Done (invalid)
        with pytest.raises(ValueError, match="Cannot transition from"):
            task.update_status(TaskStatus.done())
    
    def test_update_status_updates_timestamp(self):
        """Test that status update changes updated_at."""
        task = Task(title="Test", description="Test")
        original_updated = task.updated_at
        
        # Wait a tiny bit to ensure timestamp differs
        import time
        time.sleep(0.001)
        
        task.update_status(TaskStatus.in_progress())
        assert task.updated_at > original_updated
    
    def test_status_transition_chain(self):
        """Test a chain of valid status transitions."""
        task = Task(title="Test", description="Test")
        
        # Todo -> In Progress
        task.update_status(TaskStatus.in_progress())
        assert task.status.value == TaskStatusEnum.IN_PROGRESS.value
        
        # In Progress -> Review
        task.update_status(TaskStatus.review())
        assert task.status.value == TaskStatusEnum.REVIEW.value
        
        # Review -> Done
        task.update_status(TaskStatus.done())
        assert task.status.value == TaskStatusEnum.DONE.value
        
        # Should have 3 update events
        update_events = [e for e in task._events if isinstance(e, TaskUpdated)]
        assert len(update_events) == 3


class TestTaskFieldUpdates:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task field update operations."""
    
    def test_update_priority(self):
        """Test updating task priority."""
        task = Task(title="Test", description="Test")
        original_priority = task.priority
        original_updated = task.updated_at
        
        task.update_priority(Priority.high())
        
        assert task.priority.value == 'high'
        assert task.updated_at > original_updated
        assert task.context_id is None
        
        events = task.get_events()
        assert len(events) == 1
        assert events[0].field_name == "priority"
        assert events[0].old_value == str(original_priority)
        assert events[0].new_value == str(Priority.high())
    
    def test_update_title(self):
        """Test updating task title."""
        task = Task(title="Original Title", description="Test")
        original_updated = task.updated_at
        
        task.update_title("New Title")
        
        assert task.title == "New Title"
        assert task.updated_at > original_updated
        assert task.context_id is None
        assert len(task._events) == 1
        assert task._events[0].field_name == "title"
        assert task._events[0].old_value == "Original Title"
        assert task._events[0].new_value == "New Title"
    
    def test_update_title_validation(self):
        """Test title update validation."""
        task = Task(title="Test", description="Test")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task.update_title("")
        
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task.update_title("   ")
    
    def test_update_description(self):
        """Test updating task description."""
        task = Task(title="Test", description="Original Description")
        original_updated = task.updated_at
        
        task.update_description("New Description")
        
        assert task.description == "New Description"
        assert task.updated_at > original_updated
        assert task.context_id is None
        assert len(task._events) == 1
        assert task._events[0].field_name == "description"
    
    def test_update_description_validation(self):
        """Test description update validation."""
        task = Task(title="Test", description="Test")
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            task.update_description("")


class TestTaskAssignees:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task assignee management."""
    
    def test_add_assignee(self):
        """Test adding assignee to task."""
        task = Task(title="Test", description="Test")
        
        task.add_assignee("@agent1")
        
        assert "@agent1" in task.assignees
        assert len(task._events) == 1
        assert task._events[0].field_name == "assignees"
    
    def test_add_duplicate_assignee(self):
        """Test adding duplicate assignee."""
        task = Task(title="Test", description="Test", assignees=["@agent1"])
        
        task.add_assignee("@agent1")
        
        # Should not add duplicate
        assert task.assignees.count("@agent1") == 1
        assert len(task._events) == 0  # No event for duplicate
    
    def test_remove_assignee(self):
        """Test removing assignee from task."""
        task = Task(title="Test", description="Test", assignees=["@agent1", "@agent2"])
        
        task.remove_assignee("@agent1")
        
        assert "@agent1" not in task.assignees
        assert "@agent2" in task.assignees
        assert len(task._events) == 1
    
    def test_remove_non_existent_assignee(self):
        """Test removing non-existent assignee."""
        task = Task(title="Test", description="Test")
        
        # Should not raise error
        task.remove_assignee("@agent1")
        assert len(task._events) == 0
    
    def test_validate_assignees(self):
        """Test assignee validation."""
        task = Task(title="Test", description="Test")
        
        # Legacy role should be resolved via update_assignees
        task.update_assignees(["coding-agent"])
        # Check if it was resolved or kept as is
        assert any("@" in assignee for assignee in task.assignees)


class TestTaskLabels:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task label management."""
    
    def test_add_label(self):
        """Test adding label to task."""
        task = Task(title="Test", description="Test")
        
        task.add_label("feature")
        
        assert "feature" in task.labels
        
        # add_label doesn't create events, only update_labels does
        events = task.get_events()
        assert len(events) == 0
    
    def test_add_duplicate_label(self):
        """Test adding duplicate label."""
        task = Task(title="Test", description="Test", labels=["feature"])
        
        task.add_label("feature")
        
        # Should not add duplicate
        assert task.labels.count("feature") == 1
        events = task.get_events()
        assert len(events) == 0
    
    def test_remove_label(self):
        """Test removing label from task."""
        task = Task(title="Test", description="Test", labels=["feature", "bug"])
        
        task.remove_label("feature")
        
        assert "feature" not in task.labels
        assert "bug" in task.labels
        
        # remove_label doesn't create events, only update_labels does
        events = task.get_events()
        assert len(events) == 0
    
    def test_validate_labels(self):
        """Test label validation with CommonLabel enum."""
        task = Task(title="Test", description="Test")
        
        # Update labels should validate them
        task.update_labels(["feat", "backend"])
        # Should have valid labels
        assert "backend" in task.labels


class TestTaskDependencies:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task dependency management."""
    
    def test_add_dependency(self):
        """Test adding dependency to task."""
        task = Task(title="Test", description="Test")
        dep_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        task.add_dependency(dep_id)
        
        assert dep_id in task.dependencies
        
        # add_dependency doesn't create events
        events = task.get_events()
        assert len(events) == 0
    
    def test_add_duplicate_dependency(self):
        """Test adding duplicate dependency."""
        dep_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task = Task(title="Test", description="Test", dependencies=[dep_id])
        
        task.add_dependency(dep_id)
        
        # Should not add duplicate
        assert task.dependencies.count(dep_id) == 1
        events = task.get_events()
        assert len(events) == 0
    
    def test_remove_dependency(self):
        """Test removing dependency from task."""
        dep1 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        dep2 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        task = Task(title="Test", description="Test", dependencies=[dep1, dep2])
        
        task.remove_dependency(dep1)
        
        assert dep1 not in task.dependencies
        assert dep2 in task.dependencies
        
        # remove_dependency doesn't create events
        events = task.get_events()
        assert len(events) == 0
    
    def test_has_dependency(self):
        """Test checking if task has dependency."""
        dep_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task = Task(title="Test", description="Test", dependencies=[dep_id])
        
        assert task.has_dependency(dep_id) is True
        
        other_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        assert task.has_dependency(other_id) is False
    
    def test_get_dependencies(self):
        """Test getting task dependencies."""
        dep1 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        dep2 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        task = Task(title="Test", description="Test", dependencies=[dep1, dep2])
        
        # Dependencies are stored directly
        deps = task.dependencies
        assert len(deps) == 2
        assert dep1 in deps
        assert dep2 in deps


class TestTaskProgress:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task progress tracking."""
    
    def test_update_progress(self):
        """Test updating task progress."""
        task = Task(title="Test", description="Test")
        
        # The update_progress method requires ProgressType
        from fastmcp.task_management.domain.value_objects.progress import ProgressType
        task.update_progress(ProgressType.IMPLEMENTATION, 50)
        
        assert task.overall_progress == 50
        events = task.get_events()
        assert len(events) >= 1
    
    def test_update_progress_validation(self):
        """Test progress update validation."""
        task = Task(title="Test", description="Test")
        
        # Progress must be 0-100
        from fastmcp.task_management.domain.value_objects.progress import ProgressType
        with pytest.raises(ValueError, match="percentage must be between 0 and 100"):
            task.update_progress(ProgressType.IMPLEMENTATION, -10)
        
        with pytest.raises(ValueError, match="percentage must be between 0 and 100"):
            task.update_progress(ProgressType.IMPLEMENTATION, 110)
    
    
    def test_is_milestone_reached(self):
        """Test milestone detection."""
        task = Task(title="Test", description="Test")
        
        # Add milestone
        task.add_progress_milestone("Quarter Complete", 25.0)
        
        # Update progress to reach milestone
        from fastmcp.task_management.domain.value_objects.progress import ProgressType
        task.update_progress(ProgressType.IMPLEMENTATION, 25.0)
        
        # Check if milestone event was triggered
        events = task.get_events()
        assert any(hasattr(e, 'milestone_percentage') for e in events)


class TestTaskCompletion:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task completion operations."""
    
    def test_complete_task(self):
        """Test completing a task."""
        task = Task(title="Test", description="Test")
        task.status = TaskStatus.in_progress()
        
        # Set context_id to satisfy completion requirements
        task.set_context_id("context-123")
        
        task.complete_task("Task completed successfully")
        
        assert task.is_completed
        # Note: complete_task doesn't automatically set overall_progress to 100
        # Progress is tracked separately via update_progress
        assert task.get_completion_summary() == "Task completed successfully"
        
        events = task.get_events()
        status_events = [e for e in events if hasattr(e, 'field_name') and e.field_name == "status"]
        assert len(status_events) >= 1
    
    def test_complete_task_without_summary(self):
        """Test completing task without summary raises error."""
        task = Task(title="Test", description="Test")
        task.status = TaskStatus.in_progress()
        
        # Set context_id to satisfy completion requirements
        task.set_context_id("context-123")
        
        with pytest.raises(Exception):  # MissingCompletionSummaryError
            task.complete_task("")
    
    def test_complete_already_completed_task(self):
        """Test completing already completed task."""
        task = Task(title="Test", description="Test", status=TaskStatus.done())
        
        # Set context_id to satisfy completion requirements
        task.set_context_id("context-123")
        
        # Should not raise error
        task.complete_task("Already done")
        
        # Even when already done, complete_task still creates a status event (done -> done)
        events = task.get_events()
        status_events = [e for e in events if hasattr(e, 'field_name') and e.field_name == "status"]
        assert len(status_events) == 1  # Still creates event even for done -> done


class TestTaskEquality:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task equality and hashing."""
    
    def test_task_equality(self):
        """Test task equality based on ID."""
        id1 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        
        task1 = Task(id=id1, title="Task 1", description="Test")
        task2 = Task(id=id1, title="Task 2", description="Different")
        task3 = Task(id=id2, title="Task 1", description="Test")
        
        # Same ID = equal (even with different data)
        assert task1 == task2
        
        # Different ID = not equal
        assert task1 != task3
        
        # Not equal to non-Task
        assert task1 != "not a task"
    
    def test_task_hashing(self):
        """Test task hashing for use in sets."""
        id1 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        
        task1 = Task(id=id1, title="Task 1", description="Test")
        task2 = Task(id=id1, title="Task 2", description="Different")
        task3 = Task(id=id2, title="Task 3", description="Test")
        
        # Can use in sets
        task_set = {task1, task2, task3}
        assert len(task_set) == 2  # task1 and task2 are considered same


class TestTaskTimezoneHandling:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task timezone handling."""
    
    def test_timezone_aware_timestamps(self):
        """Test that timestamps are timezone aware."""
        task = Task(title="Test", description="Test")
        
        assert task.created_at.tzinfo is not None
        assert task.updated_at.tzinfo is not None
        assert task.created_at.tzinfo == timezone.utc
        assert task.updated_at.tzinfo == timezone.utc
    
    def test_naive_timestamp_conversion(self):
        """Test conversion of naive timestamps to UTC."""
        naive_created = datetime.now()  # Naive datetime
        naive_updated = datetime.now()
        
        task = Task(
            title="Test",
            description="Test",
            created_at=naive_created,
            updated_at=naive_updated
        )
        
        assert task.created_at.tzinfo == timezone.utc
        assert task.updated_at.tzinfo == timezone.utc


class TestTaskDomainEvents:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test Task domain event generation."""
    
    def test_get_events(self):
        """Test getting domain events."""
        task = Task(title="Test", description="Test")
        
        # Update various fields
        task.update_status(TaskStatus.in_progress())
        task.update_priority(Priority.high())
        task.add_assignee("@agent1")
        
        events = task.get_events()
        assert len(events) == 3
        assert any(isinstance(e, TaskUpdated) and e.field_name == "status" for e in events)
        assert any(isinstance(e, TaskUpdated) and e.field_name == "priority" for e in events)
        assert any(isinstance(e, TaskUpdated) and e.field_name == "assignees" for e in events)
    
    def test_clear_events(self):
        """Test clearing domain events."""
        task = Task(title="Test", description="Test")
        task.update_status(TaskStatus.in_progress())
        
        assert len(task._events) == 1
        
        # Clear events by getting them (which clears the list)
        events = task.get_events()
        assert len(events) == 1
        assert len(task._events) == 0
    
    def test_event_ordering(self):
        """Test that events maintain order."""
        task = Task(title="Test", description="Test")
        
        task.update_title("Title 1")
        task.update_title("Title 2")
        task.update_title("Title 3")
        
        events = task.get_events()
        assert events[0].new_value == "Title 1"
        assert events[1].new_value == "Title 2"
        assert events[2].new_value == "Title 3"