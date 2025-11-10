"""Unit tests for TaskStateTransitionService."""

from unittest.mock import Mock

import pytest

from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.services.task_state_transition_service import (
    SubtaskRepositoryProtocol,
    TaskRepositoryProtocol,
    TaskStateTransitionService,
    TransitionContext,
)
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


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

    def test_get_allowed_transitions_exception_handling(self, service):
        """Test exception handling in get_allowed_transitions (lines 175-177)."""
        # Create a task that will raise an exception
        mock_task = Mock()
        mock_status = Mock()
        mock_status.__str__ = Mock(side_effect=Exception("Status error"))
        mock_task.status = mock_status
        mock_task.id = "test-id"

        result = service.get_allowed_transitions(mock_task)

        # Should return empty dict on exception
        assert result == {}

    def test_suggest_next_status_blocked_with_alternative_suggestions(self, service, mock_task):
        """Test suggest_next_status when suggestion is blocked (lines 217-227)."""
        # Set task to in_progress and configure to block review transition
        mock_task.status = TaskStatus("in_progress")

        # Mock can_transition_to to return False (transition is blocked)
        original_can_transition = service.can_transition_to

        def mock_can_transition(task, target_status, context=None):
            if str(target_status).lower() == 'review':
                return False, "Review not ready"
            return original_can_transition(task, target_status)

        service.can_transition_to = mock_can_transition

        result = service.suggest_next_status(mock_task)

        # Restore original method
        service.can_transition_to = original_can_transition

        assert result is not None
        assert result["suggested_status"] == "review"
        assert result["blocked"] is True
        assert result["blocked_reason"] == "Review not ready"
        assert "alternative_suggestions" in result
        assert len(result["alternative_suggestions"]) > 0

    def test_check_transition_prerequisites_review_from_non_in_progress(self, service, mock_task):
        """Test transition to review from status other than in_progress (line 314)."""
        # Use a status that CAN transition to review according to state machine (testing)
        # but will fail the prerequisite check
        mock_task.status = TaskStatus("testing")

        can_transition, reason = service.can_transition_to(
            mock_task,
            TaskStatus("review")
        )

        # Should fail because review requires in_progress status
        assert can_transition is False
        assert "must be in progress before moving to review" in reason

    def test_partial_branch_251_249_blocked_dependency_not_all_satisfied(self, service, mock_task, mock_task_repository):
        """Test handle_dependency_completion partial branch 251->249 (task not blocked)."""
        completed_task = Mock(spec=Task)
        completed_task.id = TaskId.generate()
        completed_task.title = "Completed Task"

        # Create a dependent task that is NOT blocked
        dependent_task = Mock(spec=Task)
        dependent_task.id = TaskId.generate()
        dependent_task.title = "Dependent Task"
        dependent_task.status = TaskStatus("todo")  # Not blocked
        dependent_task.dependencies = [str(completed_task.id)]

        mock_task_repository.find_all.return_value = [completed_task, dependent_task]

        updated_tasks = service.handle_dependency_completion(completed_task)

        # Should return empty list because dependent task is not blocked
        assert updated_tasks == []

    def test_partial_branch_261_249_all_dependencies_not_satisfied(self, service, mock_task, mock_task_repository):
        """Test handle_dependency_completion partial branch 261->249 (dependencies not satisfied)."""
        completed_task = Mock(spec=Task)
        completed_task.id = TaskId.generate()

        # Create a blocked task with multiple dependencies where one is not satisfied
        other_dep = Mock(spec=Task)
        other_dep.id = TaskId.generate()
        other_dep.status = TaskStatus("in_progress")  # Not done

        dependent_task = Mock(spec=Task)
        dependent_task.id = TaskId.generate()
        dependent_task.status = TaskStatus("blocked")
        dependent_task.dependencies = [str(completed_task.id), str(other_dep.id)]

        mock_task_repository.find_all.return_value = [completed_task, other_dep, dependent_task]

        updated_tasks = service.handle_dependency_completion(completed_task)

        # Should return empty list because not all dependencies are satisfied
        assert updated_tasks == []

    def test_partial_branch_296_304_done_with_no_subtask_repo(self, service, mock_task):
        """Test transition to done when _subtask_repository is None (partial branch 296->304)."""
        # Create service without subtask repository
        service_no_subtasks = TaskStateTransitionService(
            subtask_repository=None,
            task_repository=None
        )

        mock_task.status = TaskStatus("testing")

        # Should allow transition to done when no subtask repository
        can_transition, reason = service_no_subtasks.can_transition_to(
            mock_task,
            TaskStatus("done")
        )

        assert can_transition is True
        assert reason is None

    def test_partial_branch_330_exit_no_completion_summary(self, service, mock_task):
        """Test _perform_pre_transition_actions for done without completion_summary (branch 330->exit)."""
        mock_task.status = TaskStatus("testing")
        # Don't set _completion_summary attribute

        # This should log a warning but not fail the transition
        success, message = service.transition_to(
            mock_task,
            TaskStatus("done"),
            metadata={}
        )

        assert success is True
        assert "Status changed" in message

    def test_partial_branch_341_345_post_transition_with_task_repo(self, service, mock_task, mock_task_repository):
        """Test _perform_post_transition_actions when transitioning to done with task_repository (branch 341->345)."""
        mock_task.status = TaskStatus("testing")
        mock_task_repository.find_all.return_value = [mock_task]

        # Perform transition to done
        success, message = service.transition_to(
            mock_task,
            TaskStatus("done"),
            metadata={}
        )

        assert success is True
        # Verify handle_dependency_completion was called by checking find_all was called
        assert mock_task_repository.find_all.called

    def test_partial_branch_372_378_all_dependencies_satisfied_status_check(self, service):
        """Test _all_dependencies_satisfied using status.is_done() method (branch 372->378)."""
        task = Mock(spec=Task)
        task.dependencies = ["dep-id-1"]

        dep_task = Mock(spec=Task)
        dep_task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")

        # Test with status having is_done method
        dep_task.status = Mock()
        dep_task.status.is_done = Mock(return_value=True)

        # Create mock id that matches
        dep_task.id = Mock()
        dep_task.id.__str__ = Mock(return_value="dep-id-1")

        all_tasks = [dep_task]

        result = service._all_dependencies_satisfied(task, all_tasks)

        assert result is True
        dep_task.status.is_done.assert_called_once()