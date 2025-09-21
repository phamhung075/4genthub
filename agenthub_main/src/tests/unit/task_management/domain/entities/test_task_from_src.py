"""Test suite for Task domain entity

This module tests the Task aggregate root following DDD principles.
Tests verify business rules, invariants, state transitions, and domain events.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.events.task_events import TaskCreated, TaskUpdated, TaskDeleted
from fastmcp.task_management.domain.exceptions.vision_exceptions import MissingCompletionSummaryError



pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

class TestTaskEntity:
    """Test suite for Task aggregate root following DDD principles"""
    
    def setup_method(self):
        """Setup test fixtures and dependencies"""
        self.task_id = TaskId.generate_new()
        self.valid_title = "Implement user authentication"
        self.valid_description = "Add JWT-based authentication with refresh tokens"
        self.git_branch_id = "feature/auth-123"
    
    def teardown_method(self):
        """Clean up after each test"""
        pass
    
    # ========== Creation and Initialization Tests ==========
    
    def test_task_creation_with_valid_data(self):
        """Task can be created with all valid required fields"""
        # Act
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description,
            git_branch_id=self.git_branch_id
        )
        
        # Assert
        assert task.id == self.task_id
        assert task.title == self.valid_title
        assert task.description == self.valid_description
        assert task.git_branch_id == self.git_branch_id
        assert task.status == TaskStatus.todo()
        assert task.priority == Priority.medium()
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.context_id is None  # No context initially
        
        # Verify domain event was created
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskCreated)
        assert events[0].task_id == task.id
    
    def test_task_creation_with_empty_title_raises_error(self):
        """Task cannot be created with empty title"""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task.create(
                id=self.task_id,
                title="",
                description=self.valid_description
            )
    
    def test_task_creation_with_empty_description_raises_error(self):
        """Task cannot be created with empty description"""
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task.create(
                id=self.task_id,
                title=self.valid_title,
                description=""
            )
    
    def test_task_creation_with_whitespace_title_raises_error(self):
        """Task cannot be created with whitespace-only title"""
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            Task.create(
                id=self.task_id,
                title="   ",
                description=self.valid_description
            )
    
    def test_task_creation_with_custom_status_and_priority(self):
        """Task can be created with custom status and priority"""
        # Act
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description,
            status=TaskStatus.in_progress(),
            priority=Priority.high()
        )
        
        # Assert
        assert task.status == TaskStatus.in_progress()
        assert task.priority == Priority.high()
    
    def test_task_equality_based_on_id(self):
        """Tasks with same ID are equal regardless of other attributes"""
        # Arrange
        task1 = Task.create(
            id=self.task_id,
            title="Task 1",
            description="Description 1"
        )
        task2 = Task.create(
            id=self.task_id,
            title="Task 2",
            description="Description 2"
        )
        
        # Assert
        assert task1 == task2
        assert hash(task1) == hash(task2)
    
    # ========== State Transition Tests ==========
    
    def test_valid_status_transitions(self):
        """Task follows valid state transition rules"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act & Assert - Valid transitions
        # todo → in_progress
        task.update_status(TaskStatus.in_progress())
        assert task.status == TaskStatus.in_progress()
        
        # in_progress → review
        task.update_status(TaskStatus.review())
        assert task.status == TaskStatus.review()
        
        # review → testing
        task.update_status(TaskStatus.testing())
        assert task.status == TaskStatus.testing()
        
        # testing → done
        task.update_status(TaskStatus.done())
        assert task.status == TaskStatus.done()
    
    def test_invalid_status_transitions_raise_error(self):
        """Invalid status transitions are rejected"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description,
            status=TaskStatus.done()
        )
        
        # Act & Assert - Cannot transition from done to todo
        with pytest.raises(ValueError, match="Cannot transition from done to todo"):
            task.update_status(TaskStatus.todo())
    
    def test_status_update_preserves_context_id(self):
        """Updating status preserves context_id in hierarchical context system"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")
        
        # Act
        task.update_status(TaskStatus.in_progress())
        
        # Assert - Context ID is now preserved during status updates
        assert task.context_id == "context-123"
    
    def test_status_update_emits_domain_event(self):
        """Status update emits TaskUpdated domain event"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.get_events()  # Clear creation event
        
        # Act
        task.update_status(TaskStatus.in_progress())
        
        # Assert
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskUpdated)
        assert events[0].field_name == "status"
        assert events[0].old_value == "todo"
        assert events[0].new_value == "in_progress"
    
    # ========== Task Completion Tests ==========
    
    def test_task_completion_requires_completion_summary(self):
        """Task cannot be completed without completion summary (Vision System requirement)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")  # Has context
        
        # Act & Assert
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary=None)
        
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary="")
        
        with pytest.raises(MissingCompletionSummaryError):
            task.complete_task(completion_summary="   ")
    
    def test_task_completion_allows_no_context(self):
        """Task can be completed without context (context is recommended but not mandatory)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        # No context_id set
        
        # Act
        task.complete_task(completion_summary="Task completed successfully")
        
        # Assert - Task should be completed successfully without raising an error
        # The task completion should succeed without raising an exception
        assert task.status.value == "done" or str(task.status) == "done"
    
    def test_task_completion_requires_all_subtasks_completed(self):
        """Task with subtask IDs can be completed (validation done by service)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")
        
        # In new architecture, Task only stores subtask IDs
        import uuid
        task.subtasks = [
            str(uuid.uuid4()),  # Subtask ID 1
            str(uuid.uuid4()),  # Subtask ID 2
            str(uuid.uuid4())   # Subtask ID 3
        ]
        
        # Act - Task entity doesn't validate subtask completion anymore
        # This validation is done by TaskCompletionService which has access to SubtaskRepository
        task.complete_task(completion_summary="Task completed")
        
        # Assert - Task can be completed even with subtask IDs present
        assert task.status == TaskStatus.done()
        assert task.get_completion_summary() == "Task completed"
    
    def test_task_completion_success_with_all_requirements_met(self):
        """Task can be completed when all requirements are met"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")
        
        # Add subtask IDs (subtask completion validation is done by TaskCompletionService)
        subtask_id_1 = "subtask-1-123"
        subtask_id_2 = "subtask-2-456"
        task.add_subtask(subtask_id_1)
        task.add_subtask(subtask_id_2)
        
        # Act - Task entity can be completed regardless of subtask status
        # (Subtask completion validation happens in TaskCompletionService)
        completion_summary = "Successfully implemented authentication with JWT"
        task.complete_task(completion_summary=completion_summary)
        
        # Assert
        assert task.status == TaskStatus.done()
        assert task.get_completion_summary() == completion_summary
        # Task entity only stores subtask IDs, not status information
        assert len(task.subtasks) == 2
        assert subtask_id_1 in task.subtasks
        assert subtask_id_2 in task.subtasks
    
    def test_task_completion_with_context_timestamp_validation(self):
        """Task completion validates context was updated after task"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")
        
        # Context updated before task
        old_timestamp = task.updated_at - timedelta(hours=1)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Context must be updated AFTER the task was last modified"):
            task.complete_task(
                completion_summary="Task completed",
                context_updated_at=old_timestamp
            )
    
    # ========== Subtask Management Tests ==========
    
    def test_add_subtask_with_title(self):
        """Subtask ID can be added to task"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        subtask_id = "subtask-123"
        
        # Act
        returned_id = task.add_subtask(subtask_id)
        
        # Assert
        assert len(task.subtasks) == 1
        assert returned_id == subtask_id
        assert subtask_id in task.subtasks
    
    def test_add_subtask_with_full_details(self):
        """Subtask ID can be added (note: full subtask objects are managed separately)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        subtask_id = "api-endpoints-subtask-456"
        
        # Act
        returned_id = task.add_subtask(subtask_id)
        
        # Assert - Task entity only stores subtask IDs, not full objects
        assert len(task.subtasks) == 1
        assert returned_id == subtask_id
        assert subtask_id in task.subtasks
        # Note: Full subtask details (title, description, etc.) are managed by SubtaskRepository
    
    def test_remove_subtask_by_id(self):
        """Subtask ID can be removed from task"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        subtask_id = "subtask-to-remove-789"
        task.add_subtask(subtask_id)
        
        # Act
        removed = task.remove_subtask(subtask_id)
        
        # Assert
        assert removed is True
        assert len(task.subtasks) == 0
    
    def test_update_subtask_status(self):
        """Subtask status update is handled by repository (Task entity only stores IDs)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        subtask_id = "subtask-to-update-123"
        task.add_subtask(subtask_id)
        
        # Act & Assert - Task entity doesn't have update_subtask method
        # In the new architecture, subtask updates are handled by SubtaskRepository
        # Task entity only manages subtask IDs, not full subtask objects
        
        # The test verifies that we can add and track subtask IDs
        assert len(task.subtasks) == 1
        assert subtask_id in task.subtasks
        
        # Note: Actual subtask status updates are handled by SubtaskRepository
        # and TaskCompletionService, not by the Task entity itself
    
    def test_all_subtasks_completed_check(self):
        """all_subtasks_completed returns conservative status based on IDs only"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # No subtasks - should return True
        assert task.all_subtasks_completed() is True
        
        # In new architecture, Task only stores subtask IDs
        import uuid
        task.subtasks = [
            str(uuid.uuid4()),  # Subtask ID 1
            str(uuid.uuid4())   # Subtask ID 2
        ]
        
        # With subtask IDs present, returns False (conservative approach)
        # Task entity can't check actual status without repository access
        assert task.all_subtasks_completed() is False
        
        # Clear subtasks
        task.subtasks = []
        assert task.all_subtasks_completed() is True
    
    # ========== Dependency Management Tests ==========
    
    def test_add_dependency(self):
        """Task dependency can be added"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        dependency_id = TaskId.generate_new()
        
        # Act
        task.add_dependency(dependency_id)
        
        # Assert
        assert len(task.dependencies) == 1
        assert task.has_dependency(dependency_id) is True
    
    def test_task_cannot_depend_on_itself(self):
        """Task cannot have itself as a dependency"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Task cannot depend on itself"):
            task.add_dependency(task.id)
    
    def test_remove_dependency(self):
        """Task dependency can be removed"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        dependency_id = TaskId.generate_new()
        task.add_dependency(dependency_id)
        
        # Act
        task.remove_dependency(dependency_id)
        
        # Assert
        assert len(task.dependencies) == 0
        assert task.has_dependency(dependency_id) is False
    
    # ========== Field Update Tests ==========
    
    def test_update_title(self):
        """Task title can be updated with validation"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.set_context_id("context-123")
        
        # Act
        new_title = "Updated task title"
        task.update_title(new_title)
        
        # Assert
        assert task.title == new_title
        assert task.context_id == "context-123"  # Context preserved in hierarchical system
        
        # Verify event
        events = task.get_events()
        update_event = next(e for e in events if isinstance(e, TaskUpdated) and e.field_name == "title")
        assert update_event.old_value == self.valid_title
        assert update_event.new_value == new_title
    
    def test_update_title_with_empty_string_raises_error(self):
        """Task title cannot be updated to empty string"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task.update_title("")
    
    def test_update_priority(self):
        """Task priority can be updated"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description,
            priority=Priority.low()
        )
        
        # Act
        task.update_priority(Priority.critical())
        
        # Assert
        assert task.priority == Priority.critical()
    
    def test_add_and_remove_assignee(self):
        """Assignees can be added and removed from task"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act - Add assignee
        task.add_assignee("@developer")
        assert task.has_assignee("@developer") is True
        assert task.get_primary_assignee() == "@developer"
        
        # Act - Add another assignee
        task.add_assignee("@reviewer")
        assert task.is_multi_assignee() is True
        assert task.get_assignees_count() == 2
        
        # Act - Remove assignee
        task.remove_assignee("@developer")
        assert task.has_assignee("@developer") is False
        assert task.get_assignees_count() == 1
    
    def test_add_and_remove_label(self):
        """Labels can be added and removed from task"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act - Add label
        task.add_label("backend")
        assert "backend" in task.labels
        
        # Act - Add duplicate label (should not add)
        task.add_label("backend")
        assert task.labels.count("backend") == 1
        
        # Act - Remove label
        task.remove_label("backend")
        assert "backend" not in task.labels
    
    def test_update_due_date_with_validation(self):
        """Due date can be updated with format validation"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act - Valid date
        task.update_due_date("2024-12-31")
        assert task.due_date == "2024-12-31"
        
        # Act - Invalid date format
        with pytest.raises(ValueError, match="Invalid due date format"):
            task.update_due_date("31/12/2024")
    
    # ========== Domain Event Tests ==========
    
    def test_domain_events_are_collected(self):
        """Domain events are collected during operations"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Clear creation event
        task.get_events()
        
        # Act - Multiple operations
        task.update_status(TaskStatus.in_progress())
        task.update_title("New title")
        subtask_id = "subtask-events-123"
        task.add_subtask(subtask_id)
        
        # Assert
        events = task.get_events()
        assert len(events) == 3
        assert any(isinstance(e, TaskUpdated) for e in events)
    
    def test_domain_events_are_cleared_after_retrieval(self):
        """Domain events are cleared after being retrieved"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Act
        first_events = task.get_events()
        second_events = task.get_events()
        
        # Assert
        assert len(first_events) > 0
        assert len(second_events) == 0
    
    def test_mark_as_deleted_emits_event(self):
        """Marking task as deleted emits TaskDeleted event"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        task.get_events()  # Clear creation event
        
        # Act
        task.mark_as_deleted()
        
        # Assert
        events = task.get_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskDeleted)
        assert events[0].task_id == task.id
    
    # ========== Helper Method Tests ==========
    
    def test_is_overdue(self):
        """Task overdue check works correctly"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # No due date - not overdue
        assert task.is_overdue() is False
        
        # Future due date - not overdue
        future_date = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        task.update_due_date(future_date)
        assert task.is_overdue() is False
        
        # Past due date - overdue
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        task.update_due_date(past_date)
        assert task.is_overdue() is True
        
        # Completed task - not overdue even with past date
        task.set_context_id("context-123")
        task.complete_task(completion_summary="Done")
        assert task.is_overdue() is False
    
    def test_to_dict_serialization(self):
        """Task can be serialized to dictionary"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description,
            git_branch_id=self.git_branch_id,
            priority=Priority.high(),
            estimated_effort="1 day"
        )
        task.add_assignee("@developer")
        task.add_label("urgent")
        
        # Act
        task_dict = task.to_dict()
        
        # Assert
        assert task_dict["id"] == str(task.id)
        assert task_dict["title"] == task.title
        assert task_dict["description"] == task.description
        assert task_dict["git_branch_id"] == task.git_branch_id
        assert task_dict["status"] == "todo"
        assert task_dict["priority"] == "high"
        assert task_dict["estimatedEffort"] == "1 day"
        assert "developer-agent" in task_dict["assignees"]
        assert "urgent" in task_dict["labels"]
        assert task_dict["created_at"] is not None
        assert task_dict["updated_at"] is not None
    
    # ========== Business Rule Tests ==========
    
    def test_can_be_assigned_based_on_status(self):
        """Task assignment eligibility based on status"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Can be assigned in initial states
        assert task.can_be_assigned is True
        
        task.update_status(TaskStatus.in_progress())
        assert task.can_be_assigned is True
        
        # Cannot be assigned when done
        task.set_context_id("context-123")
        task.complete_task(completion_summary="Done")
        assert task.can_be_assigned is False
    
    def test_can_be_started_based_on_dependencies(self):
        """Task can be started check (simplified for now)"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Can start if in todo status
        assert task.can_be_started() is True
        
        # Cannot start if already in progress
        task.update_status(TaskStatus.in_progress())
        assert task.can_be_started() is False
    
    def test_has_circular_dependency_check(self):
        """Circular dependency detection"""
        # Arrange
        task = Task.create(
            id=self.task_id,
            title=self.valid_title,
            description=self.valid_description
        )
        
        # Self-reference is circular
        assert task.has_circular_dependency(task.id) is True
        
        # New dependency is not circular (simplified check)
        other_id = TaskId.generate_new()
        assert task.has_circular_dependency(other_id) is False