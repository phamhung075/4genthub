"""Unit tests for Subtask entity."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.enums.agent_roles import AgentRole
from fastmcp.task_management.domain.events.task_events import TaskUpdated

class TestSubtaskCreation:
    """Test entity."""
    
    def test_create_subtask_with_factory_method(self):
        """Test creating subtask with factory method."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        subtask_id = SubtaskId("550e8400e29b41d4a716446655440001")
        
        subtask = Subtask.create(
            id=subtask_id,
            title="Implement validation",
            description="Add input validation for the form",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo(),
            priority=Priority.high()
        )
        
        assert subtask.id == subtask_id
        assert subtask.title == "Implement validation"
        assert subtask.description == "Add input validation for the form"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == "todo"
        assert subtask.priority.value == "high"
        assert isinstance(subtask.created_at, datetime)
        assert isinstance(subtask.updated_at, datetime)
        assert subtask.created_at.tzinfo == timezone.utc
        assert subtask.updated_at.tzinfo == timezone.utc
        assert subtask.created_at == subtask.updated_at
        assert subtask.assignees == []
    
    def test_create_subtask_minimal(self):
        """Test creating subtask with minimal data."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask(
            title="Quick fix",
            description="A quick fix",
            parent_task_id=parent_task_id
        )
        
        assert subtask.title == "Quick fix"
        assert subtask.description == "A quick fix"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == "todo"  # Default
        assert subtask.priority.value == "medium"  # Default
        assert subtask.assignees == []
    
    def test_subtask_post_init_timezone_handling(self):
        """Test that __post_init__ ensures timestamps are timezone-aware."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        # Create subtask with naive timestamps
        naive_time = datetime(2024, 1, 1, 12, 0, 0)
        subtask = Subtask(
            title="Test subtask",
            description="Test",
            parent_task_id=parent_task_id,
            created_at=naive_time,
            updated_at=naive_time
        )
        
        # Timestamps should be made timezone-aware
        assert subtask.created_at.tzinfo == timezone.utc
        assert subtask.updated_at.tzinfo == timezone.utc
    
    def test_subtask_validation_empty_title(self):
        """Test that empty title raises ValueError."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            Subtask(
                title="",
                description="Test",
                parent_task_id=parent_task_id
            )
    
    def test_subtask_validation_whitespace_title(self):
        """Test that whitespace-only title raises ValueError."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            Subtask(
                title="   ",
                description="Test",
                parent_task_id=parent_task_id
            )
    
    def test_subtask_validation_title_too_long(self):
        """Test that title exceeding 200 characters raises ValueError."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(ValueError, match="Subtask title cannot exceed 200 characters"):
            Subtask(
                title="A" * 201,
                description="Test",
                parent_task_id=parent_task_id
            )
    
    def test_subtask_validation_description_too_long(self):
        """Test that description exceeding 500 characters raises ValueError."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(ValueError, match="Subtask description cannot exceed 500 characters"):
            Subtask(
                title="Test",
                description="A" * 501,
                parent_task_id=parent_task_id
            )
    
    def test_subtask_validation_no_parent_task_id(self):
        """Test that missing parent_task_id raises ValueError."""
        with pytest.raises(ValueError, match="Subtask must have a parent task ID"):
            Subtask(
                title="Test",
                description="Test",
                parent_task_id=None
            )
    
    def test_subtask_equality(self):
        """Test subtask equality based on ID."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        subtask_id = SubtaskId("550e8400e29b41d4a716446655440001")
        
        subtask1 = Subtask.create(
            id=subtask_id,
            title="Test 1",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask2 = Subtask.create(
            id=subtask_id,
            title="Test 2",
            description="Different",
            parent_task_id=parent_task_id
        )
        
        subtask3 = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440002"),
            title="Test 3",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Same ID = equal
        assert subtask1 == subtask2
        # Different ID = not equal
        assert subtask1 != subtask3
        # Not a subtask = not equal
        assert subtask1 != "not a subtask"
    
    def test_subtask_hashable(self):
        """Test that subtasks are hashable based on ID."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        subtask1 = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test 1",
            description="Test",
            parent_task_id=parent_task_id
        )
        subtask2 = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440002"),
            title="Test 2",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Should be able to use in sets
        subtask_set = {subtask1, subtask2}
        assert len(subtask_set) == 2
        assert subtask1 in subtask_set
        assert subtask2 in subtask_set

class TestSubtaskProperties:
    """Test entity."""
    
    def test_is_completed_property(self):
        """Test is_completed property."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        
        assert not subtask.is_completed
        
        subtask.status = TaskStatus.done()
        assert subtask.is_completed
    
    def test_can_be_assigned_property(self):
        """Test can_be_assigned property."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        
        # Can be assigned when todo
        assert subtask.can_be_assigned
        
        # Cannot be assigned when completed
        subtask.status = TaskStatus.done()
        assert not subtask.can_be_assigned
        
        # Cannot be assigned when cancelled
        subtask.status = TaskStatus.cancelled()
        assert not subtask.can_be_assigned

class TestSubtaskStatusManagement:
    """Test entity."""
    
    def test_update_status_valid_transition(self):
        """Test updating status with valid transition."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        
        # Valid transition: todo -> in_progress
        subtask.update_status(TaskStatus.in_progress())
        assert subtask.status.value == "in_progress"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
        assert subtask._events[0].task_id == parent_task_id
        assert subtask._events[0].field_name == "subtask_status"
    
    def test_update_status_invalid_transition(self):
        """Test updating status with invalid transition."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")

        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()  # Start from DONE status (final state)
        )

        # Invalid transition: done -> in_progress (DONE is final state)
        with pytest.raises(ValueError, match="Cannot transition from"):
            subtask.update_status(TaskStatus.in_progress())
    
    def test_complete_subtask(self):
        """Test completing a subtask."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress()
        )
        
        subtask.complete()
        assert subtask.status.value == "done"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
    
    def test_complete_already_completed_subtask(self):
        """Test completing an already completed subtask."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()
        )
        
        subtask.complete()
        # Should not raise error, just do nothing
        assert subtask.status.value == "done"
        assert len(subtask._events) == 0
    
    def test_reopen_subtask(self):
        """Test reopening a completed subtask."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()
        )
        
        subtask.reopen()
        assert subtask.status.value == "todo"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
    
    def test_reopen_not_completed_subtask(self):
        """Test reopening a subtask that's not completed."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress()
        )
        
        subtask.reopen()
        # Should not raise error, just do nothing
        assert subtask.status.value == "in_progress"
        assert len(subtask._events) == 0

class TestSubtaskPriorityManagement:
    """Test entity."""
    
    def test_update_priority(self):
        """Test updating subtask priority."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            priority=Priority.medium()
        )
        
        subtask.update_priority(Priority.high())
        assert subtask.priority.value == "high"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
        assert subtask._events[0].field_name == "subtask_priority"

class TestSubtaskContentManagement:
    """Test entity."""
    
    def test_update_title(self):
        """Test updating subtask title."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Original title",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.update_title("New title")
        assert subtask.title == "New title"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
        assert subtask._events[0].field_name == "subtask_title"
    
    def test_update_title_empty(self):
        """Test updating title with empty string raises error."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Original title",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            subtask.update_title("")
    
    def test_update_description(self):
        """Test updating subtask description."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Original description",
            parent_task_id=parent_task_id
        )
        
        subtask.update_description("New description")
        assert subtask.description == "New description"
        assert len(subtask._events) == 1
        assert isinstance(subtask._events[0], TaskUpdated)
        assert subtask._events[0].field_name == "subtask_description"

class TestSubtaskAssigneeManagement:
    """Test entity."""
    
    def test_update_assignees(self):
        """Test updating assignees list."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Update with valid agent roles
        subtask.update_assignees(["coding-agent", "devops-agent"])
        assert len(subtask.assignees) == 2
        assert "@coding-agent" in subtask.assignees
        assert "@devops-agent" in subtask.assignees
        assert len(subtask._events) == 1
    
    def test_update_assignees_with_legacy_roles(self):
        """Test updating assignees with legacy role names."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Legacy roles should be resolved
        subtask.update_assignees(["senior_developer", "qa_engineer"])
        assert "@coding-agent" in subtask.assignees  # senior_developer -> coding-agent
        assert "@test-orchestrator-agent" in subtask.assignees  # qa_engineer -> test-orchestrator-agent
    
    def test_update_assignees_empty_strings_filtered(self):
        """Test that empty strings are filtered from assignees."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.update_assignees(["", "  ", "coding-agent", ""])
        assert len(subtask.assignees) == 1
        assert "@coding-agent" in subtask.assignees
    
    def test_add_assignee_string(self):
        """Test adding a single assignee."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.add_assignee("coding-agent")
        assert "@coding-agent" in subtask.assignees
        assert len(subtask._events) == 1
    
    def test_add_assignee_enum(self):
        """Test adding assignee using AgentRole enum."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.add_assignee(AgentRole.DEVOPS)
        assert "@devops-agent" in subtask.assignees
    
    def test_add_assignee_duplicate(self):
        """Test adding duplicate assignee doesn't create duplicates."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.add_assignee("coding-agent")
        subtask.add_assignee("coding-agent")
        assert subtask.assignees.count("@coding-agent") == 1
    
    def test_remove_assignee_string(self):
        """Test removing an assignee."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            assignees=["coding-agent", "devops-agent"]
        )
        
        subtask.remove_assignee("@coding-agent")
        assert "@coding-agent" not in subtask.assignees
        assert "@devops-agent" in subtask.assignees
        assert len(subtask._events) == 1
    
    def test_remove_assignee_enum(self):
        """Test removing assignee using AgentRole enum."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            assignees=["coding-agent", "devops-agent"]
        )
        
        subtask.remove_assignee(AgentRole.DEVOPS)
        assert "@devops-agent" not in subtask.assignees
        assert "@coding-agent" in subtask.assignees
    
    def test_remove_assignee_not_present(self):
        """Test removing assignee that's not present."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            assignees=["coding-agent"]
        )
        
        subtask.remove_assignee("devops-agent")
        # Should not raise error
        assert "@coding-agent" in subtask.assignees
        assert len(subtask._events) == 0  # No event since nothing was removed

class TestSubtaskEventManagement:
    """Test entity."""
    
    def test_get_events_clears_events(self):
        """Test that get_events returns and clears events."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Generate some events
        subtask.update_title("New title")
        subtask.update_priority(Priority.high())
        
        events = subtask.get_events()
        assert len(events) == 2
        assert all(isinstance(event, TaskUpdated) for event in events)
        
        # Events should be cleared
        assert len(subtask._events) == 0
        assert subtask.get_events() == []

class TestSubtaskSerialization:
    """Test entity."""
    
    def test_to_dict(self):
        """Test converting subtask to dictionary."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        subtask_id = SubtaskId("550e8400e29b41d4a716446655440001")
        
        subtask = Subtask.create(
            id=subtask_id,
            title="Test subtask",
            description="Test description",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["coding-agent", "devops-agent"]
        )
        
        data = subtask.to_dict()
        
        assert data["id"] == subtask_id.value
        assert data["title"] == "Test subtask"
        assert data["description"] == "Test description"
        assert data["parent_task_id"] == str(parent_task_id)
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"
        assert data["assignees"] == ["coding-agent", "devops-agent"]
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
    
    def test_from_dict(self):
        """Test creating subtask from dictionary."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        data = {
            "id": "550e8400e29b41d4a716446655440001",
            "title": "Test subtask",
            "description": "Test description",
            "status": "in_progress",
            "priority": "high",
            "assignees": ["coding-agent", "devops-agent"],
            "created_at": "2024-01-01T12:00:00+00:00",
            "updated_at": "2024-01-01T13:00:00+00:00"
        }
        
        subtask = Subtask.from_dict(data, parent_task_id)
        
        assert subtask.id.value == "550e8400-e29b-41d4-a716-446655440001"
        assert subtask.title == "Test subtask"
        assert subtask.description == "Test description"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == "in_progress"
        assert subtask.priority.value == "high"
        # Check that assignees are normalized internally with @ prefix
        assert subtask.assignees == ["@coding-agent", "@devops-agent"]
        # But to_dict should return them in external format (without @)
        data_out = subtask.to_dict()
        assert data_out["assignees"] == ["coding-agent", "devops-agent"]
        assert subtask.created_at == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert subtask.updated_at == datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    
    def test_from_dict_minimal(self):
        """Test creating subtask from minimal dictionary data."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        data = {
            "title": "Minimal subtask",
            "description": "Minimal description"
        }
        
        subtask = Subtask.from_dict(data, parent_task_id)
        
        assert subtask.title == "Minimal subtask"
        assert subtask.description == "Minimal description"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == "todo"  # Default
        assert subtask.priority.value == "medium"  # Default
        assert subtask.assignees == []

class TestSubtaskIntegration:
    """Test entity."""
    
    def test_subtask_workflow(self):
        """Test complete subtask workflow."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        # Create subtask
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Implement feature",
            description="Add new feature to the system",
            parent_task_id=parent_task_id
        )
        
        # Assign team
        subtask.add_assignee(AgentRole.CODING)
        subtask.add_assignee("code-reviewer-agent")
        
        # Start work
        subtask.update_status(TaskStatus.in_progress())
        
        # Update progress
        subtask.update_description("Add new feature to the system - IN PROGRESS")
        
        # Complete subtask
        subtask.complete()
        
        # Verify final state
        assert subtask.is_completed
        assert "@coding-agent" in subtask.assignees
        assert "@code-reviewer-agent" in subtask.assignees
        assert subtask.description == "Add new feature to the system - IN PROGRESS"
        
        # Check events
        events = subtask.get_events()
        assert len(events) == 5  # assignee, assignee, status, description, complete
        assert all(event.task_id == parent_task_id for event in events)
    
    def test_subtask_with_multiple_status_transitions(self):
        """Test subtask with multiple valid status transitions."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Complex task",
            description="Task with multiple transitions",
            parent_task_id=parent_task_id
        )
        
        # todo -> in_progress
        subtask.update_status(TaskStatus.in_progress())
        assert subtask.status.value == "in_progress"
        
        # in_progress -> review
        subtask.update_status(TaskStatus.review())
        assert subtask.status.value == "review"
        
        # review -> testing
        subtask.update_status(TaskStatus.testing())
        assert subtask.status.value == "testing"
        
        # testing -> done
        subtask.update_status(TaskStatus.done())
        assert subtask.status.value == "done"
        
        events = subtask.get_events()
        assert len(events) == 4
        assert all(isinstance(event, TaskUpdated) for event in events)
    
    def test_subtask_timestamp_updates(self):
        """Test that updated_at changes with each update."""
        parent_task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        
        subtask = Subtask.create(
            id=SubtaskId("550e8400e29b41d4a716446655440001"),
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        original_updated = subtask.updated_at
        
        # Wait a tiny bit to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        subtask.update_title("New title")
        assert subtask.updated_at > original_updated
        
        previous_updated = subtask.updated_at
        time.sleep(0.001)
        
        subtask.update_priority(Priority.high())
        assert subtask.updated_at > previous_updated