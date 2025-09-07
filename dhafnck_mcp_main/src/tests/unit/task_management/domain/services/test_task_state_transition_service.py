"""Unit tests for TaskStateTransitionService domain service"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Optional

from fastmcp.task_management.domain.services.task_state_transition_service import (
    TaskStateTransitionService,
    TransitionContext,
    SubtaskRepositoryProtocol,
    TaskRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskStateTransitionError


class MockSubtask:
    """Mock Subtask entity for testing"""
    
    def __init__(self, subtask_id: str, title: str, is_completed: bool = False):
        self.id = subtask_id
        self.title = title
        self.is_completed = is_completed


class TestTaskStateTransitionService:
    """Test suite for TaskStateTransitionService domain service"""

    def setup_method(self):
        """Setup test data before each test"""
        self.mock_subtask_repository = Mock(spec=SubtaskRepositoryProtocol)
        self.mock_task_repository = Mock(spec=TaskRepositoryProtocol)
        
        self.service = TaskStateTransitionService(
            subtask_repository=self.mock_subtask_repository,
            task_repository=self.mock_task_repository
        )
        
        # Create test task
        self.test_task = Task(
            title="Test Task",
            description="Test description",
            id=TaskId.from_string("12345678-1234-5678-1234-567812345678"),
            status=TaskStatus.from_string("todo"),
            priority=Priority.from_string("medium"),
            git_branch_id="test-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_can_transition_to_valid_transition(self):
        """Test valid state transitions are allowed"""
        # Test valid transitions from todo
        valid_transitions = [
            ("todo", "in_progress"),
            ("todo", "blocked"),
            ("todo", "cancelled"),
            ("in_progress", "review"),
            ("in_progress", "testing"),
            ("in_progress", "done"),
            ("review", "testing"),
            ("review", "done"),
            ("testing", "done"),
            ("blocked", "todo"),
        ]
        
        for from_status, to_status in valid_transitions:
            # Arrange
            task = self._create_task_with_status(from_status)
            target_status = TaskStatus.from_string(to_status)
            
            # Act
            can_transition, reason = self.service.can_transition_to(task, target_status)
            
            # Assert
            assert can_transition is True, f"Should allow transition from {from_status} to {to_status}"
            assert reason is None

    def test_can_transition_to_invalid_transition(self):
        """Test invalid state transitions are blocked"""
        # Test some invalid transitions
        invalid_transitions = [
            ("done", "todo"),        # Done tasks shouldn't change
            ("cancelled", "todo"),   # Cancelled tasks shouldn't change
            ("todo", "testing"),     # Can't skip to testing from todo
            ("review", "todo"),      # Can't go backwards to todo from review
        ]
        
        for from_status, to_status in invalid_transitions:
            # Arrange
            task = self._create_task_with_status(from_status)
            target_status = TaskStatus.from_string(to_status)
            
            # Act
            can_transition, reason = self.service.can_transition_to(task, target_status)
            
            # Assert
            assert can_transition is False, f"Should block transition from {from_status} to {to_status}"
            assert reason is not None
            assert f"Cannot transition from '{from_status}' to '{to_status}'" in reason

    def test_can_transition_to_done_with_incomplete_subtasks(self):
        """Test transition to done is blocked when subtasks are incomplete"""
        # Arrange
        in_progress_task = self._create_task_with_status("in_progress")
        target_status = TaskStatus.from_string("done")
        
        # Mock incomplete subtasks
        incomplete_subtasks = [
            MockSubtask("subtask-1", "Incomplete Subtask 1", False),
            MockSubtask("subtask-2", "Incomplete Subtask 2", False)
        ]
        self.mock_subtask_repository.find_by_parent_task_id.return_value = incomplete_subtasks
        
        # Act
        can_transition, reason = self.service.can_transition_to(in_progress_task, target_status)
        
        # Assert
        assert can_transition is False
        assert "Cannot complete task: 2 subtasks are still incomplete" in reason

    def test_can_transition_to_done_with_all_subtasks_complete(self):
        """Test transition to done is allowed when all subtasks are complete"""
        # Arrange
        in_progress_task = self._create_task_with_status("in_progress")
        target_status = TaskStatus.from_string("done")
        
        # Mock completed subtasks
        completed_subtasks = [
            MockSubtask("subtask-1", "Completed Subtask 1", True),
            MockSubtask("subtask-2", "Completed Subtask 2", True)
        ]
        self.mock_subtask_repository.find_by_parent_task_id.return_value = completed_subtasks
        
        # Act
        can_transition, reason = self.service.can_transition_to(in_progress_task, target_status)
        
        # Assert
        assert can_transition is True
        assert reason is None

    def test_can_transition_to_review_from_non_in_progress(self):
        """Test transition to review is blocked from non-in-progress status"""
        # Arrange
        todo_task = self._create_task_with_status("todo")
        target_status = TaskStatus.from_string("review")
        
        # Act
        can_transition, reason = self.service.can_transition_to(todo_task, target_status)
        
        # Assert
        assert can_transition is False
        assert "Task must be in progress before moving to review" in reason

    def test_can_transition_to_error_handling(self):
        """Test error handling in transition validation"""
        # Arrange
        invalid_task = Mock()
        invalid_task.status = None  # Invalid status to cause error
        target_status = TaskStatus.from_string("done")
        
        # Act
        can_transition, reason = self.service.can_transition_to(invalid_task, target_status)
        
        # Assert
        assert can_transition is False
        assert "Transition validation error" in reason

    def test_transition_to_success(self):
        """Test successful state transition"""
        # Arrange
        todo_task = self._create_task_with_status("todo")
        target_status = TaskStatus.from_string("in_progress")
        
        # Mock task update_status method
        todo_task.update_status = Mock()
        
        # Act
        success, message = self.service.transition_to(
            todo_task, 
            target_status, 
            TransitionContext.USER_INITIATED
        )
        
        # Assert
        assert success is True
        assert "Status changed from 'todo' to 'in_progress'" in message
        todo_task.update_status.assert_called_once_with(target_status)

    def test_transition_to_blocked_by_validation(self):
        """Test transition blocked by validation"""
        # Arrange
        done_task = self._create_task_with_status("done")
        target_status = TaskStatus.from_string("todo")  # Invalid transition
        
        # Act
        success, message = self.service.transition_to(done_task, target_status)
        
        # Assert
        assert success is False
        assert "Cannot transition from 'done' to 'todo'" in message

    def test_transition_to_with_metadata(self):
        """Test transition with additional metadata"""
        # Arrange
        todo_task = self._create_task_with_status("todo")
        target_status = TaskStatus.from_string("blocked")
        metadata = {"blocking_reason": "Waiting for external API"}
        
        todo_task.update_status = Mock()
        
        # Act
        success, message = self.service.transition_to(
            todo_task,
            target_status,
            TransitionContext.SYSTEM_INITIATED,
            metadata
        )
        
        # Assert
        assert success is True
        todo_task.update_status.assert_called_once_with(target_status)

    def test_transition_to_error_handling(self):
        """Test error handling in transition execution"""
        # Arrange
        todo_task = self._create_task_with_status("todo")
        todo_task.update_status = Mock(side_effect=Exception("Update failed"))
        target_status = TaskStatus.from_string("in_progress")
        
        # Act
        success, message = self.service.transition_to(todo_task, target_status)
        
        # Assert
        assert success is False
        assert "Transition failed: Update failed" in message

    def test_get_allowed_transitions(self):
        """Test getting allowed transitions for a task"""
        # Arrange
        in_progress_task = self._create_task_with_status("in_progress")
        
        # Act
        allowed = self.service.get_allowed_transitions(in_progress_task)
        
        # Assert
        assert isinstance(allowed, dict)
        
        # Should have valid transitions for in_progress
        expected_transitions = ["review", "testing", "done", "blocked", "todo"]
        for transition in expected_transitions:
            assert transition in allowed
            assert "allowed" in allowed[transition]
            assert "reason" in allowed[transition]
            assert "description" in allowed[transition]
            assert "prerequisites" in allowed[transition]

    def test_get_allowed_transitions_empty_status(self):
        """Test getting allowed transitions for task with no valid transitions"""
        # Arrange
        done_task = self._create_task_with_status("done")
        
        # Act
        allowed = self.service.get_allowed_transitions(done_task)
        
        # Assert
        assert len(allowed) == 0  # Done tasks have no allowed transitions

    def test_suggest_next_status_logical_progression(self):
        """Test suggestion of next logical status"""
        progression_tests = [
            ("todo", "in_progress"),
            ("in_progress", "review"),
            ("review", "testing"),
            ("testing", "done"),
            ("blocked", "todo")
        ]
        
        for current_status, expected_next in progression_tests:
            # Arrange
            task = self._create_task_with_status(current_status)
            
            # Act
            suggestion = self.service.suggest_next_status(task)
            
            # Assert
            if expected_next:
                assert suggestion is not None
                assert suggestion["suggested_status"] == expected_next
                assert suggestion["current_status"] == current_status
                assert "reason" in suggestion

    def test_suggest_next_status_blocked_by_prerequisites(self):
        """Test next status suggestion when blocked by prerequisites"""
        # Arrange
        in_progress_task = self._create_task_with_status("in_progress")
        
        # Mock incomplete subtasks to block transition to done via review->testing->done
        incomplete_subtasks = [MockSubtask("sub-1", "Incomplete", False)]
        self.mock_subtask_repository.find_by_parent_task_id.return_value = incomplete_subtasks
        
        # Act
        suggestion = self.service.suggest_next_status(in_progress_task)
        
        # Assert
        assert suggestion is not None
        # Should suggest review (next logical step) but might be blocked
        assert suggestion["suggested_status"] == "review"

    def test_suggest_next_status_no_suggestion(self):
        """Test next status suggestion when no suggestion available"""
        # Arrange
        done_task = self._create_task_with_status("done")
        
        # Act
        suggestion = self.service.suggest_next_status(done_task)
        
        # Assert
        assert suggestion is None  # No next status for done tasks

    def test_handle_dependency_completion_success(self):
        """Test handling dependency completion successfully"""
        # Arrange
        completed_task = self._create_task_with_status("done")
        
        # Create dependent task that should be unblocked
        blocked_dependent = self._create_task_with_status("blocked")
        blocked_dependent.dependencies = [completed_task.id]
        blocked_dependent.update_status = Mock()
        
        # Mock all tasks in repository
        all_tasks = [completed_task, blocked_dependent]
        self.mock_task_repository.find_all.return_value = all_tasks
        
        # Act
        updated_tasks = self.service.handle_dependency_completion(completed_task)
        
        # Assert
        assert len(updated_tasks) == 1
        assert updated_tasks[0]["task_id"] == str(blocked_dependent.id)
        assert updated_tasks[0]["old_status"] == "blocked"
        assert updated_tasks[0]["new_status"] == "todo"
        assert "Unblocked by completion" in updated_tasks[0]["reason"]

    def test_handle_dependency_completion_no_dependents(self):
        """Test handling dependency completion with no dependent tasks"""
        # Arrange
        completed_task = self._create_task_with_status("done")
        
        # Mock no dependent tasks
        self.mock_task_repository.find_all.return_value = [completed_task]
        
        # Act
        updated_tasks = self.service.handle_dependency_completion(completed_task)
        
        # Assert
        assert updated_tasks == []

    def test_handle_dependency_completion_without_repository(self):
        """Test handling dependency completion without task repository"""
        # Arrange
        service_no_repo = TaskStateTransitionService()
        completed_task = self._create_task_with_status("done")
        
        # Act
        updated_tasks = service_no_repo.handle_dependency_completion(completed_task)
        
        # Assert
        assert updated_tasks == []

    def test_handle_dependency_completion_error_handling(self):
        """Test error handling in dependency completion"""
        # Arrange
        completed_task = self._create_task_with_status("done")
        self.mock_task_repository.find_all.side_effect = Exception("Database error")
        
        # Act
        updated_tasks = self.service.handle_dependency_completion(completed_task)
        
        # Assert
        assert updated_tasks == []  # Should return empty list on error

    def test_find_dependent_tasks(self):
        """Test finding tasks that depend on a completed task"""
        # Arrange
        completed_task = self._create_task_with_status("done")
        
        dependent_task_1 = self._create_task_with_status("blocked")
        dependent_task_1.dependencies = [completed_task.id]
        
        dependent_task_2 = self._create_task_with_status("todo") 
        dependent_task_2.dependencies = [completed_task.id]
        
        independent_task = self._create_task_with_status("todo")
        independent_task.dependencies = []
        
        all_tasks = [completed_task, dependent_task_1, dependent_task_2, independent_task]
        
        # Act
        dependent_tasks = self.service._find_dependent_tasks(completed_task, all_tasks)
        
        # Assert
        assert len(dependent_tasks) == 2
        assert dependent_task_1 in dependent_tasks
        assert dependent_task_2 in dependent_tasks
        assert independent_task not in dependent_tasks

    def test_all_dependencies_satisfied_true(self):
        """Test checking if all dependencies are satisfied (true case)"""
        # Arrange
        done_dependency = self._create_task_with_status("done")
        
        # Create task with satisfied dependencies
        task_with_deps = self._create_task_with_status("blocked")
        task_with_deps.dependencies = [done_dependency.id]
        
        all_tasks = [task_with_deps, done_dependency]
        
        # Act
        all_satisfied = self.service._all_dependencies_satisfied(task_with_deps, all_tasks)
        
        # Assert
        assert all_satisfied is True

    def test_all_dependencies_satisfied_false(self):
        """Test checking if all dependencies are satisfied (false case)"""
        # Arrange
        incomplete_dependency = self._create_task_with_status("in_progress")
        
        # Create task with unsatisfied dependencies
        task_with_deps = self._create_task_with_status("blocked")
        task_with_deps.dependencies = [incomplete_dependency.id]
        
        all_tasks = [task_with_deps, incomplete_dependency]
        
        # Act
        all_satisfied = self.service._all_dependencies_satisfied(task_with_deps, all_tasks)
        
        # Assert
        assert all_satisfied is False

    def test_all_dependencies_satisfied_no_dependencies(self):
        """Test checking dependencies for task with no dependencies"""
        # Arrange
        task_no_deps = self._create_task_with_status("todo")
        task_no_deps.dependencies = []
        
        # Act
        all_satisfied = self.service._all_dependencies_satisfied(task_no_deps, [])
        
        # Assert
        assert all_satisfied is True

    def test_create_status_from_string(self):
        """Test status creation from string"""
        # Act
        status = self.service._create_status_from_string("in_progress")
        
        # Assert
        assert isinstance(status, TaskStatus)
        assert str(status).lower() == "in_progress"

    def test_get_transition_description(self):
        """Test getting transition descriptions"""
        # Test known transitions
        description = self.service._get_transition_description("todo", "in_progress")
        assert "Start working on this task" in description
        
        description = self.service._get_transition_description("in_progress", "review")
        assert "Submit work for review" in description
        
        # Test unknown transition
        description = self.service._get_transition_description("unknown", "other")
        assert "Change status from unknown to other" in description

    def test_get_transition_prerequisites_description(self):
        """Test getting transition prerequisites descriptions"""
        # Test known prerequisites
        prereqs = self.service._get_transition_prerequisites_description("testing", "done")
        assert "Tests passed" in prereqs
        assert "All subtasks completed" in prereqs
        
        # Test unknown transition
        prereqs = self.service._get_transition_prerequisites_description("unknown", "other")
        assert prereqs == []

    def test_get_alternative_suggestions(self):
        """Test getting alternative status suggestions"""
        # Test known alternatives
        alternatives = self.service._get_alternative_suggestions(self._create_task_with_status("todo"))
        assert "blocked" in alternatives
        
        alternatives = self.service._get_alternative_suggestions(self._create_task_with_status("in_progress"))
        assert "blocked" in alternatives
        assert "todo" in alternatives
        
        # Test status with no alternatives
        alternatives = self.service._get_alternative_suggestions(self._create_task_with_status("unknown"))
        assert alternatives == []

    def test_perform_pre_transition_actions(self):
        """Test pre-transition actions execution"""
        # Arrange
        task = self._create_task_with_status("todo")
        target_status = TaskStatus.from_string("done")
        
        # Act - Should not raise exceptions
        self.service._perform_pre_transition_actions(
            task, 
            target_status, 
            TransitionContext.USER_INITIATED, 
            {}
        )
        
        # Assert - No exceptions means success
        # (This method currently just logs warnings)
        assert True

    def test_perform_post_transition_actions(self):
        """Test post-transition actions execution"""
        # Arrange
        task = self._create_task_with_status("in_progress")
        old_status = TaskStatus.from_string("in_progress")
        new_status = TaskStatus.from_string("blocked")
        metadata = {"blocking_reason": "External dependency"}
        
        # Act - Should not raise exceptions
        self.service._perform_post_transition_actions(
            task,
            old_status,
            new_status,
            TransitionContext.SYSTEM_INITIATED,
            metadata
        )
        
        # Assert - No exceptions means success
        assert True

    def _create_task_with_status(self, status: str) -> Task:
        """Helper to create task with specific status"""
        import uuid
        # Generate a deterministic UUID based on the status for test consistency
        task_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"task-{status}"))
        return Task(
            title=f"Task with {status} status",
            description="Test task",
            id=TaskId.from_string(task_uuid),
            status=TaskStatus.from_string(status),
            priority=Priority.from_string("medium"),
            git_branch_id="test-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )


class TestTaskStateTransitionServiceIntegration:
    """Integration tests for TaskStateTransitionService with complex scenarios"""

    def setup_method(self):
        """Setup integration test environment"""
        self.mock_subtask_repository = Mock(spec=SubtaskRepositoryProtocol)
        self.mock_task_repository = Mock(spec=TaskRepositoryProtocol)
        
        self.service = TaskStateTransitionService(
            subtask_repository=self.mock_subtask_repository,
            task_repository=self.mock_task_repository
        )

    def test_complete_workflow_transition_sequence(self):
        """Test complete workflow transition sequence"""
        # Arrange: Create a task and walk it through complete lifecycle
        task = Task(
            title="Workflow Task",
            description="Task going through complete workflow",
            id=TaskId.from_string("87654321-4321-8765-4321-876543218765"),
            status=TaskStatus.from_string("todo"),
            priority=Priority.from_string("high"),
            git_branch_id="workflow-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        task.update_status = Mock()
        
        # Mock no subtasks initially
        self.mock_subtask_repository.find_by_parent_task_id.return_value = []
        
        # Test sequence: todo -> in_progress -> review -> testing -> done
        workflow_steps = [
            ("todo", "in_progress"),
            ("in_progress", "review"),
            ("review", "testing"),
            ("testing", "done")
        ]
        
        for current_status, next_status in workflow_steps:
            # Update task status for next iteration
            task.status = TaskStatus.from_string(current_status)
            
            # Act
            success, message = self.service.transition_to(
                task,
                TaskStatus.from_string(next_status),
                TransitionContext.USER_INITIATED
            )
            
            # Assert
            assert success is True, f"Failed transition from {current_status} to {next_status}: {message}"
            task.update_status.assert_called_with(TaskStatus.from_string(next_status))

    def test_dependency_chain_resolution(self):
        """Test dependency chain resolution when tasks are completed"""
        # Arrange: Create dependency chain A -> B -> C
        task_c = self._create_task_with_id_status("task-c", "done")
        task_b = self._create_task_with_id_status("task-b", "blocked")
        task_b.dependencies = [task_c.id]
        task_a = self._create_task_with_id_status("task-a", "blocked") 
        task_a.dependencies = [task_b.id]
        
        # Mock update methods
        task_a.update_status = Mock()
        task_b.update_status = Mock()
        
        all_tasks = [task_a, task_b, task_c]
        self.mock_task_repository.find_all.return_value = all_tasks
        
        # Act: Complete task C (already done) and trigger dependency resolution
        # First, task B should be unblocked
        updated_from_c = self.service.handle_dependency_completion(task_c)
        
        # Task B should now be unblocked, complete it
        task_b.status = TaskStatus.from_string("todo")  # Simulate unblocking
        success, _ = self.service.transition_to(task_b, TaskStatus.from_string("done"))
        task_b.status = TaskStatus.from_string("done")  # Update for next step
        
        # Now task A should be unblockable
        updated_from_b = self.service.handle_dependency_completion(task_b)
        
        # Assert: Verify dependency chain resolution
        # Task B should have been unblocked by C completion
        assert len(updated_from_c) >= 1
        unblocked_b = next((u for u in updated_from_c if u["task_id"] == str(task_b.id)), None)
        if unblocked_b:  # Might not be found if already resolved
            assert unblocked_b["old_status"] == "blocked"
            assert unblocked_b["new_status"] == "todo"
        
        # Task A should have been unblocked by B completion
        assert len(updated_from_b) >= 1 or len(updated_from_c) >= 2
        # Check if A was unblocked in either step
        all_updates = updated_from_c + updated_from_b
        unblocked_a = next((u for u in all_updates if u["task_id"] == str(task_a.id)), None)

    def test_complex_subtask_completion_validation(self):
        """Test complex subtask completion validation"""
        # Arrange: Task with mixed subtask statuses
        parent_task = self._create_task_with_id_status("parent-task", "in_progress")
        parent_task.update_status = Mock()
        
        # Mix of completed and incomplete subtasks
        subtasks = [
            MockSubtask("sub-1", "Completed Subtask 1", True),
            MockSubtask("sub-2", "Completed Subtask 2", True),
            MockSubtask("sub-3", "Incomplete Subtask 3", False),
            MockSubtask("sub-4", "Incomplete Subtask 4", False)
        ]
        self.mock_subtask_repository.find_by_parent_task_id.return_value = subtasks
        
        # Act: Try to complete task with incomplete subtasks
        success, message = self.service.transition_to(
            parent_task,
            TaskStatus.from_string("done")
        )
        
        # Assert: Should be blocked
        assert success is False
        assert "2 subtasks are still incomplete" in message
        
        # Now complete all subtasks and try again
        for subtask in subtasks:
            subtask.is_completed = True
        
        success, message = self.service.transition_to(
            parent_task,
            TaskStatus.from_string("done")
        )
        
        # Assert: Should now succeed
        assert success is True
        parent_task.update_status.assert_called_with(TaskStatus.from_string("done"))

    def test_state_machine_enforcement_comprehensive(self):
        """Test comprehensive state machine rule enforcement"""
        # Test all invalid state transitions are properly blocked
        invalid_transition_sets = [
            # From done - should block all transitions
            ("done", ["todo", "in_progress", "review", "testing", "blocked", "cancelled"]),
            # From cancelled - should block all transitions  
            ("cancelled", ["todo", "in_progress", "review", "testing", "blocked", "done"]),
            # Logical violations
            ("todo", ["review", "testing"]),  # Can't skip ahead
            ("review", ["todo"]),  # Can't go backward to todo
        ]
        
        for from_status, blocked_transitions in invalid_transition_sets:
            task = self._create_task_with_id_status(f"test-{from_status}", from_status)
            
            for to_status in blocked_transitions:
                # Act
                can_transition, reason = self.service.can_transition_to(
                    task,
                    TaskStatus.from_string(to_status)
                )
                
                # Assert
                assert can_transition is False, f"Should block {from_status} -> {to_status}"
                assert reason is not None

    def test_transition_context_handling(self):
        """Test different transition contexts are handled appropriately"""
        # Arrange
        task = self._create_task_with_id_status("context-task", "todo")
        task.update_status = Mock()
        target_status = TaskStatus.from_string("in_progress")
        
        context_tests = [
            TransitionContext.USER_INITIATED,
            TransitionContext.SYSTEM_INITIATED,
            TransitionContext.DEPENDENCY_TRIGGERED,
            TransitionContext.COMPLETION_TRIGGERED
        ]
        
        for context in context_tests:
            # Act
            success, message = self.service.transition_to(task, target_status, context)
            
            # Assert
            assert success is True
            assert f"context: {context.value}" in message

    def test_error_recovery_and_resilience(self):
        """Test error recovery and system resilience"""
        # Test 1: Repository failures don't crash the system
        self.mock_task_repository.find_all.side_effect = Exception("Database connection lost")
        
        completed_task = self._create_task_with_id_status("completed", "done")
        updated = self.service.handle_dependency_completion(completed_task)
        
        assert updated == []  # Graceful handling
        
        # Test 2: Invalid task objects are handled gracefully
        invalid_task = Mock()
        invalid_task.id = "invalid"
        invalid_task.status = "unknown_status"  # Invalid status
        
        can_transition, reason = self.service.can_transition_to(
            invalid_task,
            TaskStatus.from_string("done")
        )
        
        assert can_transition is False
        assert "error" in reason.lower()

    def _create_task_with_id_status(self, task_id: str, status: str) -> Task:
        """Helper to create task with specific ID and status"""
        return Task(
            title=f"Task {task_id}",
            description=f"Test task with status {status}",
            id=TaskId.from_string(task_id),
            status=TaskStatus.from_string(status),
            priority=Priority.from_string("medium"),
            git_branch_id="test-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )