"""Test suite for Subtask domain entity.

Tests the Subtask entity including:
- Creation and initialization
- Validation and business rules
- Status transitions and updates
- Priority and assignee management
- Progress tracking
- Domain events
- Completion and reopening
- Serialization and deserialization
- Agent role integration
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import uuid

from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.enums.agent_roles import AgentRole
from fastmcp.task_management.domain.events.task_events import TaskUpdated


class TestSubtaskCreation:
    """Test cases for Subtask creation and initialization."""
    
    def test_create_subtask_minimal(self):
        """Test creating a subtask with minimal data."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test Subtask",
            description="A test subtask",
            parent_task_id=parent_task_id
        )
        
        assert subtask.title == "Test Subtask"
        assert subtask.description == "A test subtask"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.id is None  # Not set yet
        assert subtask.status.value == TaskStatusEnum.TODO.value
        assert subtask.priority.value == PriorityLevel.MEDIUM.label
        assert subtask.assignees == []
        assert subtask.progress_percentage == 0
        assert subtask.created_at is not None
        assert subtask.updated_at is not None
        assert subtask.created_at.tzinfo == timezone.utc
        assert subtask.updated_at.tzinfo == timezone.utc
    
    def test_create_subtask_with_factory(self):
        """Test creating subtask with factory method."""
        subtask_id = SubtaskId("subtask-456")
        parent_task_id = TaskId("parent-789")
        
        subtask = Subtask.create(
            id=subtask_id,
            title="Factory Subtask",
            description="Created with factory",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "@user2"],
            progress_percentage=50
        )
        
        assert subtask.id == subtask_id
        assert subtask.title == "Factory Subtask"
        assert subtask.description == "Created with factory"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert subtask.priority.value == "high"
        assert subtask.assignees == ["@user1", "@user2"]
        assert subtask.progress_percentage == 50
    
    def test_create_subtask_full_data(self):
        """Test creating subtask with all data."""
        subtask_id = SubtaskId("subtask-full")
        parent_task_id = TaskId("parent-full")
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        subtask = Subtask(
            id=subtask_id,
            title="Full Subtask",
            description="Complete subtask",
            parent_task_id=parent_task_id,
            status=TaskStatus.review(),
            priority=Priority.urgent(),
            assignees=["coding-agent", "@reviewer"],
            progress_percentage=80,
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert subtask.id == subtask_id
        assert subtask.title == "Full Subtask"
        assert subtask.description == "Complete subtask"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == TaskStatusEnum.REVIEW.value
        assert subtask.priority.value == "urgent"
        assert subtask.assignees == ["coding-agent", "@reviewer"]
        assert subtask.progress_percentage == 80
        assert subtask.created_at == created_at
        assert subtask.updated_at == updated_at
    
    def test_subtask_validation_empty_title(self):
        """Test validation fails for empty title."""
        parent_task_id = TaskId("parent-123")
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            Subtask(title="", description="Valid", parent_task_id=parent_task_id)
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            Subtask(title="   ", description="Valid", parent_task_id=parent_task_id)
    
    def test_subtask_validation_title_too_long(self):
        """Test validation fails for title exceeding 200 characters."""
        parent_task_id = TaskId("parent-123")
        long_title = "a" * 201
        
        with pytest.raises(ValueError, match="Subtask title cannot exceed 200 characters"):
            Subtask(title=long_title, description="Valid", parent_task_id=parent_task_id)
    
    def test_subtask_validation_description_too_long(self):
        """Test validation fails for description exceeding 500 characters."""
        parent_task_id = TaskId("parent-123")
        long_description = "a" * 501
        
        with pytest.raises(ValueError, match="Subtask description cannot exceed 500 characters"):
            Subtask(title="Valid", description=long_description, parent_task_id=parent_task_id)
    
    def test_subtask_validation_missing_parent(self):
        """Test validation fails for missing parent task ID."""
        with pytest.raises(ValueError, match="Subtask must have a parent task ID"):
            Subtask(title="Valid", description="Valid", parent_task_id=None)
    
    def test_subtask_timezone_handling(self):
        """Test timezone handling for timestamps."""
        parent_task_id = TaskId("parent-123")
        
        # Test with naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            created_at=naive_dt,
            updated_at=naive_dt
        )
        
        # Should be converted to UTC
        assert subtask.created_at.tzinfo == timezone.utc
        assert subtask.updated_at.tzinfo == timezone.utc


class TestSubtaskEquality:
    """Test cases for subtask equality and hashing."""
    
    def test_subtask_equality_with_id(self):
        """Test subtask equality based on ID."""
        subtask_id = SubtaskId("same-id")
        parent_task_id = TaskId("parent-123")
        
        subtask1 = Subtask(
            id=subtask_id,
            title="First",
            description="First subtask",
            parent_task_id=parent_task_id
        )
        subtask2 = Subtask(
            id=subtask_id,
            title="Second",
            description="Second subtask",
            parent_task_id=parent_task_id
        )
        
        assert subtask1 == subtask2  # Same ID
        assert hash(subtask1) == hash(subtask2)
    
    def test_subtask_equality_without_id(self):
        """Test subtask equality when IDs are None."""
        parent_task_id = TaskId("parent-123")
        
        subtask1 = Subtask(
            title="Same Title",
            description="First subtask",
            parent_task_id=parent_task_id
        )
        subtask2 = Subtask(
            title="Same Title",
            description="Second subtask",
            parent_task_id=parent_task_id
        )
        
        assert subtask1 != subtask2  # Different objects, no ID
        # Hash should be based on title when ID is None
        assert hash(subtask1) == hash(subtask2)  # Same title
    
    def test_subtask_inequality(self):
        """Test subtask inequality."""
        parent_task_id = TaskId("parent-123")
        subtask1 = Subtask(
            id=SubtaskId("id-1"),
            title="First",
            description="First",
            parent_task_id=parent_task_id
        )
        subtask2 = Subtask(
            id=SubtaskId("id-2"),
            title="Second",
            description="Second",
            parent_task_id=parent_task_id
        )
        
        assert subtask1 != subtask2
        assert subtask1 != "not a subtask"


class TestSubtaskProperties:
    """Test cases for subtask properties."""
    
    def test_is_completed_property(self):
        """Test is_completed property."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        assert not subtask.is_completed
        
        subtask.status = TaskStatus.done()
        assert subtask.is_completed
        
        subtask.status = TaskStatus.in_progress()
        assert not subtask.is_completed
    
    def test_can_be_assigned_property(self):
        """Test can_be_assigned property."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        assert subtask.can_be_assigned
        
        subtask.status = TaskStatus.done()
        assert not subtask.can_be_assigned
        
        subtask.status = TaskStatus(TaskStatusEnum.CANCELLED.value)
        assert not subtask.can_be_assigned
        
        subtask.status = TaskStatus.in_progress()
        assert subtask.can_be_assigned


class TestSubtaskStatusUpdates:
    """Test cases for status updates."""
    
    def test_update_status_valid_transition(self):
        """Test valid status transition."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo()
        )
        
        original_updated = subtask.updated_at
        subtask.update_status(TaskStatus.in_progress())
        
        assert subtask.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert subtask.updated_at > original_updated
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskUpdated)
        assert events[0].task_id == parent_task_id
        assert events[0].field_name == "subtask_status"
    
    def test_update_status_invalid_transition(self):
        """Test invalid status transition fails."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()
        )
        
        with pytest.raises(ValueError, match="Cannot transition"):
            subtask.update_status(TaskStatus.todo())
    
    def test_update_priority(self):
        """Test updating priority."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            priority=Priority.medium()
        )
        
        original_updated = subtask.updated_at
        subtask.update_priority(Priority.high())
        
        assert subtask.priority.value == "high"
        assert subtask.updated_at > original_updated
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_priority"


class TestSubtaskFieldUpdates:
    """Test cases for field updates."""
    
    def test_update_title(self):
        """Test updating title."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Original",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.update_title("New Title")
        
        assert subtask.title == "New Title"
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_title"
    
    def test_update_title_validation(self):
        """Test title update validation."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Original",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            subtask.update_title("")
        
        with pytest.raises(ValueError, match="Subtask title cannot be empty"):
            subtask.update_title("   ")
    
    def test_update_description(self):
        """Test updating description."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Original",
            parent_task_id=parent_task_id
        )
        
        subtask.update_description("New Description")
        
        assert subtask.description == "New Description"
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_description"


class TestSubtaskAssigneeManagement:
    """Test cases for assignee management."""
    
    def test_update_assignees(self):
        """Test updating assignees."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        with patch('fastmcp.task_management.domain.enums.agent_roles.AgentRole.is_valid_role', return_value=True):
            subtask.update_assignees(["@user1", "coding-agent", "@user2"])
        
        # Should normalize agent roles
        assert "@user1" in subtask.assignees
        assert "coding-agent" in subtask.assignees  # Should add @ prefix
        assert "@user2" in subtask.assignees
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_assignees"
    
    def test_add_assignee_string(self):
        """Test adding individual assignee as string."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.add_assignee("@user1")
        
        assert "@user1" in subtask.assignees
        
        # Add duplicate - should not duplicate
        subtask.add_assignee("@user1")
        assert subtask.assignees.count("@user1") == 1
    
    def test_add_assignee_enum(self):
        """Test adding assignee using AgentRole enum."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Mock AgentRole enum
        mock_role = Mock(spec=AgentRole)
        mock_role.value = "coding-agent"
        
        subtask.add_assignee(mock_role)
        
        assert "coding-agent" in subtask.assignees
    
    def test_remove_assignee(self):
        """Test removing assignee."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            assignees=["@user1", "@user2"]
        )
        
        subtask.remove_assignee("@user1")
        
        assert "@user1" not in subtask.assignees
        assert "@user2" in subtask.assignees
        
        # Remove non-existent - should not error
        subtask.remove_assignee("@user3")
        assert subtask.assignees == ["@user2"]
    
    def test_remove_assignee_enum(self):
        """Test removing assignee using AgentRole enum."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            assignees=["coding-agent", "@user1"]
        )
        
        # Mock AgentRole enum
        mock_role = Mock(spec=AgentRole)
        mock_role.value = "coding-agent"
        
        subtask.remove_assignee(mock_role)
        
        assert "coding-agent" not in subtask.assignees
        assert "@user1" in subtask.assignees


class TestSubtaskProgressTracking:
    """Test cases for progress tracking."""
    
    def test_update_progress_percentage_valid(self):
        """Test updating progress percentage with valid values."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # Test 50% progress
        subtask.update_progress_percentage(50)
        
        assert subtask.progress_percentage == 50
        assert subtask.status.value == TaskStatusEnum.IN_PROGRESS.value
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_progress"
    
    def test_update_progress_percentage_auto_status_update(self):
        """Test automatic status updates based on progress."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        # 0% should set to TODO
        subtask.update_progress_percentage(0)
        assert subtask.status.value == TaskStatusEnum.TODO.value
        
        # 1-99% should set to IN_PROGRESS
        subtask.update_progress_percentage(75)
        assert subtask.status.value == TaskStatusEnum.IN_PROGRESS.value
        
        # 100% should set to DONE
        subtask.update_progress_percentage(100)
        assert subtask.status.value == TaskStatusEnum.DONE.value
    
    def test_update_progress_percentage_invalid(self):
        """Test updating progress percentage with invalid values."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        with pytest.raises(ValueError, match="Progress percentage must be integer between 0-100"):
            subtask.update_progress_percentage(-10)
        
        with pytest.raises(ValueError, match="Progress percentage must be integer between 0-100"):
            subtask.update_progress_percentage(150)
        
        with pytest.raises(ValueError, match="Progress percentage must be integer between 0-100"):
            subtask.update_progress_percentage("50")


class TestSubtaskCompletion:
    """Test cases for subtask completion and reopening."""
    
    def test_complete_subtask(self):
        """Test completing a subtask."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress()
        )
        
        assert not subtask.is_completed
        
        subtask.complete()
        
        assert subtask.is_completed
        assert subtask.status.value == TaskStatusEnum.DONE.value
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_status"
    
    def test_complete_already_completed(self):
        """Test completing an already completed subtask does nothing."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()
        )
        
        original_updated = subtask.updated_at
        subtask.complete()
        
        assert subtask.status.value == TaskStatusEnum.DONE.value
        assert subtask.updated_at == original_updated  # No change
        
        # No events should be raised
        events = subtask.get_events()
        assert len(events) == 0
    
    def test_reopen_subtask(self):
        """Test reopening a completed subtask."""
        subtask_id = SubtaskId("subtask-1")
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            id=subtask_id,
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.done()
        )
        
        assert subtask.is_completed
        
        subtask.reopen()
        
        assert not subtask.is_completed
        assert subtask.status.value == TaskStatusEnum.TODO.value
        
        # Check domain event
        events = subtask.get_events()
        assert len(events) == 1
        assert events[0].field_name == "subtask_status"
    
    def test_reopen_not_completed(self):
        """Test reopening a non-completed subtask does nothing."""
        parent_task_id = TaskId("parent-123")
        
        subtask = Subtask(
            title="Test",
            description="Test",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress()
        )
        
        original_updated = subtask.updated_at
        subtask.reopen()
        
        assert subtask.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert subtask.updated_at == original_updated  # No change
        
        # No events should be raised
        events = subtask.get_events()
        assert len(events) == 0


class TestSubtaskSerialization:
    """Test cases for serialization and deserialization."""
    
    def test_to_dict(self):
        """Test converting subtask to dictionary."""
        subtask_id = SubtaskId("subtask-123")
        parent_task_id = TaskId("parent-456")
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        subtask = Subtask(
            id=subtask_id,
            title="Test Subtask",
            description="A test subtask",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "coding-agent"],
            progress_percentage=75,
            created_at=created_at,
            updated_at=updated_at
        )
        
        data = subtask.to_dict()
        
        assert data["id"] == "subtask-123"
        assert data["title"] == "Test Subtask"
        assert data["description"] == "A test subtask"
        assert data["parent_task_id"] == "parent-456"
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"
        assert data["assignees"] == ["@user1", "coding-agent"]
        assert data["progress_percentage"] == 75
        assert data["created_at"] == created_at.isoformat()
        assert data["updated_at"] == updated_at.isoformat()
    
    def test_to_dict_no_id(self):
        """Test to_dict with no ID."""
        parent_task_id = TaskId("parent-456")
        
        subtask = Subtask(
            title="No ID Subtask",
            description="Subtask without ID",
            parent_task_id=parent_task_id
        )
        
        data = subtask.to_dict()
        
        assert data["id"] is None
        assert data["title"] == "No ID Subtask"
    
    def test_from_dict(self):
        """Test creating subtask from dictionary."""
        parent_task_id = TaskId("parent-789")
        
        data = {
            "id": "subtask-fromdict",
            "title": "From Dict",
            "description": "Created from dict",
            "status": "review",
            "priority": "urgent",
            "assignees": ["@user1", "@reviewer"],
            "progress_percentage": 90,
            "created_at": "2024-01-01T12:00:00+00:00",
            "updated_at": "2024-01-02T12:00:00+00:00"
        }
        
        subtask = Subtask.from_dict(data, parent_task_id)
        
        assert subtask.id.value == "subtask-fromdict"
        assert subtask.title == "From Dict"
        assert subtask.description == "Created from dict"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == TaskStatusEnum.REVIEW.value
        assert subtask.priority.value == "urgent"
        assert subtask.assignees == ["@user1", "@reviewer"]
        assert subtask.progress_percentage == 90
        assert subtask.created_at.year == 2024
        assert subtask.created_at.month == 1
        assert subtask.created_at.day == 1
    
    def test_from_dict_minimal(self):
        """Test creating subtask from minimal dict."""
        parent_task_id = TaskId("parent-minimal")
        
        data = {
            "title": "Minimal",
            "description": "Minimal subtask"
        }
        
        subtask = Subtask.from_dict(data, parent_task_id)
        
        assert subtask.id is None
        assert subtask.title == "Minimal"
        assert subtask.description == "Minimal subtask"
        assert subtask.parent_task_id == parent_task_id
        assert subtask.status.value == TaskStatusEnum.TODO.value
        assert subtask.priority.value == PriorityLevel.MEDIUM.label
        assert subtask.assignees == []
        assert subtask.progress_percentage == 0
    
    def test_roundtrip_serialization(self):
        """Test that to_dict/from_dict roundtrip preserves data."""
        subtask_id = SubtaskId("roundtrip-123")
        parent_task_id = TaskId("parent-roundtrip")
        
        original_subtask = Subtask(
            id=subtask_id,
            title="Roundtrip Test",
            description="Test roundtrip serialization",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "coding-agent"],
            progress_percentage=60
        )
        
        # Serialize and deserialize
        data = original_subtask.to_dict()
        restored_subtask = Subtask.from_dict(data, parent_task_id)
        
        assert restored_subtask.id.value == original_subtask.id.value
        assert restored_subtask.title == original_subtask.title
        assert restored_subtask.description == original_subtask.description
        assert restored_subtask.parent_task_id == original_subtask.parent_task_id
        assert restored_subtask.status.value == original_subtask.status.value
        assert restored_subtask.priority.value == original_subtask.priority.value
        assert restored_subtask.assignees == original_subtask.assignees
        assert restored_subtask.progress_percentage == original_subtask.progress_percentage


class TestSubtaskDomainEvents:
    """Test cases for domain events."""
    
    def test_get_events_clears_list(self):
        """Test that get_events returns and clears event list."""
        subtask_id = SubtaskId("event-test")
        parent_task_id = TaskId("parent-events")
        
        subtask = Subtask(
            id=subtask_id,
            title="Event Test",
            description="Test events",
            parent_task_id=parent_task_id
        )
        
        subtask.update_title("New Title")
        subtask.update_priority(Priority.high())
        
        # First call gets events
        events = subtask.get_events()
        assert len(events) == 2
        
        # Second call gets empty list
        events = subtask.get_events()
        assert len(events) == 0
    
    def test_event_content(self):
        """Test event content and structure."""
        subtask_id = SubtaskId("event-content")
        parent_task_id = TaskId("parent-events")
        
        subtask = Subtask(
            id=subtask_id,
            title="Original Title",
            description="Test",
            parent_task_id=parent_task_id
        )
        
        subtask.update_title("Updated Title")
        
        events = subtask.get_events()
        assert len(events) == 1
        
        event = events[0]
        assert isinstance(event, TaskUpdated)
        assert event.task_id == parent_task_id
        assert event.field_name == "subtask_title"
        assert f"{subtask_id}:Original Title" in event.old_value
        assert f"{subtask_id}:Updated Title" in event.new_value


if __name__ == "__main__":
    pytest.main([__file__])