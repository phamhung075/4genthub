"""
Tests for TaskCompletionService integration with Unified Context System.

Verifies that task completion properly validates against the unified context
repository instead of the hierarchical context service.
"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.services.task_completion_service import TaskCompletionService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskCompletionError
from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
from fastmcp.task_management.domain.entities.context import TaskContextUnified


class TestTaskCompletionWithUnifiedContext:
    """Test TaskCompletionService with unified context system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock repositories
        self.subtask_repo = Mock()
        self.task_context_repo = Mock(spec=TaskContextRepository)
        
        # Create service
        self.service = TaskCompletionService(
            subtask_repository=self.subtask_repo,
            task_context_repository=self.task_context_repo
        )
        
        # Create test task with valid UUID
        self.task = Task(
            id=TaskId("12345678-1234-5678-1234-567812345678"),
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            status=TaskStatus(TaskStatusEnum.IN_PROGRESS.value),
            priority=Priority(PriorityLevel.HIGH.label),
            context_id=None  # No context initially
        )
    
    def test_can_complete_task_without_context(self):
        """Test task can be completed without context (auto-created)."""
        # Mock no context exists
        self.task_context_repo.get = Mock(return_value=None)
        
        # Mock no subtasks
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=[])
        
        # Check if can complete
        can_complete, error_msg = self.service.can_complete_task(self.task)
        
        # Verify CAN complete (context is auto-created now)
        assert can_complete is True
        assert error_msg is None
    
    def test_can_complete_task_with_context(self):
        """Test task can be completed when context exists."""
        # Mock context exists
        context = TaskContextUnified(
            id="12345678-1234-5678-1234-567812345678",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=100,

            next_steps=[],
            metadata={}
        )
        
        self.task_context_repo.get = Mock(return_value=context)
        
        # Mock no subtasks
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=[])
        
        # Check if can complete
        can_complete, error_msg = self.service.can_complete_task(self.task)
        
        # Verify can complete
        assert can_complete is True
        assert error_msg is None
    
    def test_can_complete_task_with_incomplete_subtasks(self):
        """Test task cannot be completed with incomplete subtasks."""
        # Mock context exists
        context = TaskContextUnified(
            id="12345678-1234-5678-1234-567812345678",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=50,

            next_steps=[],
            metadata={}
        )
        
        self.task_context_repo.get = Mock(return_value=context)
        
        # Mock incomplete subtasks
        subtasks = [
            Subtask(
                id="sub-1",
                parent_task_id=TaskId("12345678-1234-5678-1234-567812345678"),
                title="Subtask 1",
                description="",
                status=TaskStatus(TaskStatusEnum.DONE.value)
            ),
            Subtask(
                id="sub-2",
                parent_task_id=TaskId("12345678-1234-5678-1234-567812345678"),
                title="Subtask 2",
                description="",
                status=TaskStatus(TaskStatusEnum.IN_PROGRESS.value)  # Not complete
            ),
            Subtask(
                id="sub-3",
                parent_task_id=TaskId("12345678-1234-5678-1234-567812345678"),
                title="Subtask 3",
                description="",
                status=TaskStatus(TaskStatusEnum.TODO.value)  # Not complete
            )
        ]
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=subtasks)
        
        # Check if can complete
        can_complete, error_msg = self.service.can_complete_task(self.task)
        
        # Verify cannot complete
        assert can_complete is False
        assert "2 of 3 subtasks are incomplete" in error_msg
        assert "Subtask 2" in error_msg
        assert "Subtask 3" in error_msg
    
    def test_validate_task_completion_raises_error(self):
        """Test validate_task_completion raises error when validation fails."""
        # Mock no context
        self.task_context_repo.get = Mock(return_value=None)
        
        # Mock incomplete subtasks to trigger error
        subtasks = [
            Subtask(
                id="sub-1",
                parent_task_id=TaskId("12345678-1234-5678-1234-567812345678"),
                title="Incomplete Subtask",
                description="",
                status=TaskStatus(TaskStatusEnum.IN_PROGRESS.value)
            )
        ]
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=subtasks)
        
        # Validate should raise error
        with pytest.raises(TaskCompletionError) as exc_info:
            self.service.validate_task_completion(self.task)
        
        assert "1 of 1 subtasks are incomplete" in str(exc_info.value)
    
    def test_get_completion_blockers(self):
        """Test getting list of completion blockers."""
        # Mock no context
        self.task_context_repo.get = Mock(return_value=None)
        
        # Mock incomplete subtasks
        subtasks = [
            Subtask(
                id="sub-1",
                parent_task_id=TaskId("12345678-1234-5678-1234-567812345678"),
                title="Incomplete Subtask",
                description="",
                status=TaskStatus(TaskStatusEnum.IN_PROGRESS.value)
            )
        ]
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=subtasks)
        
        # Get blockers
        blockers = self.service.get_completion_blockers(self.task)
        
        # Verify blockers (only subtask blocker since context is auto-created)
        assert len(blockers) == 1
        assert any("1 of 1 subtasks are incomplete" in b for b in blockers)
    
    def test_task_with_existing_context_id(self):
        """Test task with context_id already set doesn't check repository."""
        # Set context_id on task
        self.task.context_id = "existing-context-id"
        
        # Mock no subtasks
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=[])
        
        # Check if can complete
        can_complete, error_msg = self.service.can_complete_task(self.task)
        
        # Verify can complete and repository was NOT called
        assert can_complete is True
        assert error_msg is None
        self.task_context_repo.get.assert_not_called()
    
    def test_context_required_error_format(self):
        """Test the context required error message format."""
        error = self.service._create_context_required_error(self.task)
        
        assert error["error"] == "Task completion requires context to be created first."
        assert "Context stores task progress" in error["explanation"]
        assert len(error["recovery_instructions"]) == 3
        assert len(error["step_by_step_fix"]) == 3
        
        # Check manage_context commands
        create_cmd = error["step_by_step_fix"][0]["command"]
        assert "manage_context" in create_cmd
        assert "action='create'" in create_cmd
        assert "level='task'" in create_cmd
        assert f"context_id='{self.task.id.value}'" in create_cmd
    
    def test_service_without_context_repository(self):
        """Test service behavior when context repository is not provided."""
        # Create service without context repository
        service = TaskCompletionService(
            subtask_repository=self.subtask_repo,
            task_context_repository=None  # No repository
        )
        
        # Mock no subtasks
        self.subtask_repo.find_by_parent_task_id = Mock(return_value=[])
        
        # Should be able to complete (no context check)
        can_complete, error_msg = service.can_complete_task(self.task)
        
        assert can_complete is True
        assert error_msg is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])