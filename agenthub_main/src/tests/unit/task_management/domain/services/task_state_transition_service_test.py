"""Unit tests for TaskStateTransitionService."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.task_state_transition_service import (
    TaskStateTransitionService,
    TransitionContext,
    SubtaskRepositoryProtocol,
    TaskRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestTaskStateTransitionService:
    """Test cases for TaskStateTransitionService."""

    @pytest.fixture
    def mock_subtask_repository(self):
        """Create a mock subtask repository."""
        repo = Mock(spec=SubtaskRepositoryProtocol)
        repo.find_by_parent_task_id.return_value = []
        return repo

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        repo = Mock(spec=TaskRepositoryProtocol)
        repo.find_all.return_value = []
        return repo

    @pytest.fixture
    def service(self, mock_subtask_repository, mock_task_repository):
        """Create a TaskStateTransitionService instance."""
        return TaskStateTransitionService(
            subtask_repository=mock_subtask_repository,
            task_repository=mock_task_repository
        )

    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        task = Mock(spec=Task)
        task.id = TaskId.generate()
        task.title = "Test Task"
        task.status = TaskStatus("todo")
        task.dependencies = []
        return task

    def test_init(self, mock_subtask_repository, mock_task_repository):
        """Test service initialization."""
        service = TaskStateTransitionService(
            subtask_repository=mock_subtask_repository,
            task_repository=mock_task_repository
        )
        
        assert service._subtask_repository == mock_subtask_repository
        assert service._task_repository == mock_task_repository
        assert isinstance(service._transition_rules, dict)
        assert len(service._transition_rules) > 0

    def test_can_transition_to_valid_transition(self, service, mock_task):
        """Test checking valid transition from todo to in_progress."""
        mock_task.status = TaskStatus("todo")
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("in_progress")
        )
        
        assert can_transition is True
        assert reason is None

    def test_can_transition_to_invalid_transition(self, service, mock_task):
        """Test checking invalid transition from todo to done."""
        mock_task.status = TaskStatus("todo")
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("done")
        )
        
        assert can_transition is False
        assert "Cannot transition from 'todo' to 'done'" in reason

    def test_can_transition_to_done_with_incomplete_subtasks(self, service, mock_task, mock_subtask_repository):
        """Test cannot transition to done with incomplete subtasks."""
        mock_task.status = TaskStatus("in_progress")
        
        # Create incomplete subtasks
        incomplete_subtask = Mock(spec=Subtask)
        incomplete_subtask.is_completed = False
        mock_subtask_repository.find_by_parent_task_id.return_value = [incomplete_subtask]
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("done")
        )
        
        assert can_transition is False
        assert "subtasks are still incomplete" in reason

    def test_can_transition_to_done_with_completed_subtasks(self, service, mock_task, mock_subtask_repository):
        """Test can transition to done when all subtasks are completed."""
        mock_task.status = TaskStatus("in_progress")
        
        # Create completed subtasks
        completed_subtask = Mock(spec=Subtask)
        completed_subtask.is_completed = True
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask]
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("done")
        )
        
        assert can_transition is True
        assert reason is None

    def test_transition_to_success(self, service, mock_task):
        """Test successful transition."""
        mock_task.status = TaskStatus("todo")
        mock_task.update_status = Mock()
        
        success, message = service.transition_to(
            mock_task, 
            TaskStatus("in_progress")
        )
        
        assert success is True
        assert "Status changed from" in message
        mock_task.update_status.assert_called_once()

    def test_transition_to_failure_invalid_transition(self, service, mock_task):
        """Test failed transition due to invalid state change."""
        mock_task.status = TaskStatus("todo")
        mock_task.update_status = Mock()
        
        success, message = service.transition_to(
            mock_task, 
            TaskStatus("done")
        )
        
        assert success is False
        assert "Cannot transition" in message
        mock_task.update_status.assert_not_called()

    def test_get_allowed_transitions(self, service, mock_task):
        """Test getting allowed transitions for a task."""
        mock_task.status = TaskStatus("todo")
        
        allowed = service.get_allowed_transitions(mock_task)
        
        assert isinstance(allowed, dict)
        assert "in_progress" in allowed
        assert "blocked" in allowed
        assert "cancelled" in allowed
        assert "done" not in allowed  # Not allowed from todo
        
        # Check transition details
        in_progress_transition = allowed["in_progress"]
        assert in_progress_transition["allowed"] is True
        assert in_progress_transition["reason"] is None
        assert "description" in in_progress_transition
        assert "prerequisites" in in_progress_transition

    def test_suggest_next_status_normal_progression(self, service, mock_task):
        """Test suggesting next status in normal progression."""
        mock_task.status = TaskStatus("todo")
        
        suggestion = service.suggest_next_status(mock_task)
        
        assert suggestion is not None
        assert suggestion["suggested_status"] == "in_progress"
        assert suggestion["current_status"] == "todo"
        assert "Natural progression" in suggestion["reason"]

    def test_suggest_next_status_blocked(self, service, mock_task, mock_subtask_repository):
        """Test suggesting next status when transition is blocked."""
        mock_task.status = TaskStatus("in_progress")
        
        # Create incomplete subtasks to block done transition
        incomplete_subtask = Mock(spec=Subtask)
        incomplete_subtask.is_completed = False
        mock_subtask_repository.find_by_parent_task_id.return_value = [incomplete_subtask]
        
        # The natural progression is to review
        suggestion = service.suggest_next_status(mock_task)
        
        assert suggestion is not None
        assert suggestion["suggested_status"] == "review"
        assert suggestion["current_status"] == "in_progress"

    def test_suggest_next_status_no_suggestion(self, service, mock_task):
        """Test suggesting next status when no progression exists."""
        mock_task.status = TaskStatus("done")
        
        suggestion = service.suggest_next_status(mock_task)
        
        assert suggestion is None

    def test_handle_dependency_completion_unblocks_task(self, service, mock_task_repository):
        """Test handling dependency completion that unblocks a task."""
        # Create completed task
        completed_task = Mock(spec=Task)
        completed_task.id = TaskId.generate()
        completed_task.status = TaskStatus("done")
        
        # Create blocked task that depends on completed task
        blocked_task = Mock(spec=Task)
        blocked_task.id = TaskId.generate()
        blocked_task.title = "Blocked Task"
        blocked_task.status = TaskStatus("blocked")
        blocked_task.dependencies = [completed_task.id]
        blocked_task.update_status = Mock()
        
        # Mock repository to return both tasks
        mock_task_repository.find_all.return_value = [completed_task, blocked_task]
        
        updated_tasks = service.handle_dependency_completion(completed_task)
        
        assert len(updated_tasks) == 1
        assert updated_tasks[0]["task_id"] == str(blocked_task.id)
        assert updated_tasks[0]["old_status"] == "blocked"
        assert updated_tasks[0]["new_status"] == "todo"
        blocked_task.update_status.assert_called_once()

    def test_handle_dependency_completion_multiple_dependencies(self, service, mock_task_repository):
        """Test handling dependency when task has multiple dependencies."""
        # Create completed task
        completed_task = Mock(spec=Task)
        completed_task.id = TaskId.generate()
        completed_task.status = TaskStatus("done")
        
        # Create another incomplete dependency
        incomplete_dependency = Mock(spec=Task)
        incomplete_dependency.id = TaskId.generate()
        incomplete_dependency.status = TaskStatus("in_progress")
        
        # Create blocked task that depends on both
        blocked_task = Mock(spec=Task)
        blocked_task.id = TaskId.generate()
        blocked_task.title = "Multi-dependency Task"
        blocked_task.status = TaskStatus("blocked")
        blocked_task.dependencies = [completed_task.id, incomplete_dependency.id]
        blocked_task.update_status = Mock()
        
        # Mock repository to return all tasks
        mock_task_repository.find_all.return_value = [
            completed_task, 
            incomplete_dependency, 
            blocked_task
        ]
        
        updated_tasks = service.handle_dependency_completion(completed_task)
        
        # Should not unblock because one dependency is still incomplete
        assert len(updated_tasks) == 0
        blocked_task.update_status.assert_not_called()

    def test_handle_dependency_completion_no_repository(self):
        """Test handling dependency completion without repository."""
        service = TaskStateTransitionService()  # No repository
        
        completed_task = Mock(spec=Task)
        completed_task.id = TaskId.generate()
        
        updated_tasks = service.handle_dependency_completion(completed_task)
        
        assert updated_tasks == []

    def test_transition_context_types(self, service, mock_task):
        """Test different transition contexts."""
        mock_task.status = TaskStatus("todo")
        mock_task.update_status = Mock()
        
        # Test with different contexts
        contexts = [
            TransitionContext.USER_INITIATED,
            TransitionContext.SYSTEM_INITIATED,
            TransitionContext.DEPENDENCY_TRIGGERED,
            TransitionContext.COMPLETION_TRIGGERED
        ]
        
        for context in contexts:
            success, message = service.transition_to(
                mock_task, 
                TaskStatus("in_progress"),
                context=context
            )
            
            assert success is True
            mock_task.update_status.assert_called()
            mock_task.update_status.reset_mock()

    def test_transition_rules_completeness(self, service):
        """Test that all status values have transition rules."""
        rules = service._transition_rules
        
        expected_statuses = ['todo', 'in_progress', 'review', 'testing', 'blocked', 'done', 'cancelled']
        
        for status in expected_statuses:
            assert status in rules, f"Missing transition rules for status: {status}"

    def test_transition_to_review_requires_in_progress(self, service, mock_task):
        """Test that review status requires task to be in progress first."""
        # First test that todo->review is not allowed
        mock_task.status = TaskStatus("todo")
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("review")
        )
        
        assert can_transition is False
        assert "Cannot transition from 'todo' to 'review'" in reason
        
        # Now test a valid transition from blocked to review (which is allowed but should fail prerequisite)
        mock_task.status = TaskStatus("blocked")
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("review")
        )
        
        # blocked->review is not in transition rules, so it should fail
        assert can_transition is False

    def test_error_handling_in_can_transition_to(self, service):
        """Test error handling in can_transition_to method."""
        # Create a task with status that will cause __str__ to raise an exception
        mock_task = Mock()
        mock_status = Mock()
        # Make the status conversion to string raise an exception
        mock_status.__str__ = Mock(side_effect=Exception("Status error"))
        mock_status.lower = Mock(side_effect=Exception("Status error"))
        mock_task.status = mock_status
        mock_task.id = "test-id"
        
        can_transition, reason = service.can_transition_to(
            mock_task, 
            TaskStatus("in_progress")
        )
        
        assert can_transition is False
        assert "Transition validation error" in reason

    def test_error_handling_in_transition_to(self, service):
        """Test error handling in transition_to method."""
        # Create a task that will cause an error during transition
        mock_task = Mock()
        mock_task.status = TaskStatus("todo")
        mock_task.id = "test-id"
        mock_task.update_status = Mock(side_effect=Exception("Update error"))
        
        success, message = service.transition_to(
            mock_task, 
            TaskStatus("in_progress")
        )
        
        assert success is False
        assert "Transition failed" in message