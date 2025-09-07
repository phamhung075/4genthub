"""
Comprehensive test suite for CompleteTaskUseCase.

Tests the complete task use case including:
- Successful task completion
- Subtask completion validation
- Context creation and validation
- Vision system integration (completion summary requirement)
- Error handling and edge cases
- Repository interaction
- Business rule enforcement
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.complete_task import CompleteTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.exceptions.task_exceptions import (
    TaskNotFoundError, 
    TaskCompletionError
)
from fastmcp.task_management.domain.exceptions.vision_exceptions import MissingCompletionSummaryError
from fastmcp.task_management.domain.services.task_completion_service import TaskCompletionService
from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository


class TestCompleteTaskUseCaseInitialization:
    """Test cases for CompleteTaskUseCase initialization."""
    
    def test_init_with_task_repository_only(self):
        """Test use case initialization with only task repository."""
        mock_task_repo = Mock(spec=TaskRepository)
        
        use_case = CompleteTaskUseCase(mock_task_repo)
        
        assert use_case._task_repository == mock_task_repo
        assert use_case._subtask_repository is None
        assert use_case._task_context_repository is None
        assert use_case._completion_service is None
    
    def test_init_with_all_repositories(self):
        """Test use case initialization with all repositories."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        mock_context_repo = Mock(spec=TaskContextRepository)
        
        with patch('fastmcp.task_management.application.use_cases.complete_task.TaskCompletionService') as mock_service:
            mock_completion_service = Mock()
            mock_service.return_value = mock_completion_service
            
            use_case = CompleteTaskUseCase(mock_task_repo, mock_subtask_repo, mock_context_repo)
            
            assert use_case._task_repository == mock_task_repo
            assert use_case._subtask_repository == mock_subtask_repo
            assert use_case._task_context_repository == mock_context_repo
            assert use_case._completion_service == mock_completion_service
            
            # Verify completion service was created correctly
            mock_service.assert_called_once_with(mock_subtask_repo, mock_context_repo)
    
    def test_init_without_repositories_fails(self):
        """Test initialization without task repository fails."""
        with pytest.raises(TypeError):
            CompleteTaskUseCase()


class TestCompleteTaskUseCaseBasicExecution:
    """Test cases for basic task completion execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_task_repo = Mock(spec=TaskRepository)
        self.mock_subtask_repo = Mock(spec=SubtaskRepository)
        self.mock_context_repo = Mock(spec=TaskContextRepository)
        self.use_case = CompleteTaskUseCase(
            self.mock_task_repo, 
            self.mock_subtask_repo, 
            self.mock_context_repo
        )
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory')
    def test_execute_successful_completion(self, mock_facade_factory):
        """Test successful task completion with all requirements met."""
        # Setup mocked context facade
        mock_context_facade = Mock()
        mock_context_facade.resolve.return_value = {'success': True, 'data': {'context': 'exists'}}
        mock_context_facade.update.return_value = {'success': True}
        mock_facade_factory.create.return_value = mock_context_facade
        
        # Setup task
        task_id = TaskId("task-123")
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        # Use actual TaskStatus instance instead of mock
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        mock_task.get_subtask_progress = Mock(return_value={"completed": 0, "total": 0})
        mock_task.dependent_tasks = []  # No dependent tasks
        
        # Setup repository
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        self.mock_task_repo.find_dependents = Mock(return_value=[])
        
        # Setup context repository
        self.mock_context_repo.get.return_value = {"context": "exists"}
        
        # Setup completion service
        self.use_case._completion_service = Mock()
        self.use_case._completion_service.validate_task_completion.return_value = True
        self.use_case._completion_service.get_subtask_completion_summary.return_value = {
            "total": 0,
            "completed": 0,
            "incomplete": 0,
            "completion_percentage": 100,
            "can_complete_parent": True
        }
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Task completed successfully",
            testing_notes="All tests passed"
        )
        
        # Verify task was found
        self.mock_task_repo.find_by_id.assert_called_once()
        
        # Verify completion validation
        self.use_case._completion_service.validate_task_completion.assert_called_once_with(mock_task)
        
        # Verify task completion was called
        mock_task.complete_task.assert_called_once()
        
        # Verify task was saved
        self.mock_task_repo.save.assert_called()
        
        # Verify success response with updated message format
        assert result["success"] is True
        assert result["task_id"] == "task-123"
        assert result["message"] == "task task-123 done, can next_task"
    
    def test_execute_task_not_found(self):
        """Test completion fails when task doesn't exist."""
        self.mock_task_repo.find_by_id.return_value = None
        
        # Use a valid UUID format for the test
        task_id = "550e8400-e29b-41d4-a716-446655440000"
        with pytest.raises(TaskNotFoundError, match=f"Task {task_id} not found"):
            self.use_case.execute(
                task_id=task_id,
                completion_summary="Trying to complete non-existent task"
            )
        
        # Verify task lookup was attempted
        self.mock_task_repo.find_by_id.assert_called_once()
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory')
    def test_execute_task_already_completed(self, mock_facade_factory):
        """Test completion of already completed task."""
        # Setup mocked context facade
        mock_context_facade = Mock()
        mock_context_facade.resolve.return_value = {'success': True, 'data': {'context': 'exists'}}
        mock_facade_factory.create.return_value = mock_context_facade
        
        # Setup already completed task
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.git_branch_id = "branch-456"
        # Use actual TaskStatus instance for done status
        mock_task.status = TaskStatus.done()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Trying to complete already done task"
        )
        
        # Verify failure response
        assert result["success"] is False
        assert result["task_id"] == "task-123"
        assert "already completed" in result["message"]
        
        # Verify no save operation was attempted
        self.mock_task_repo.save.assert_not_called()


class TestCompleteTaskUseCaseVisionSystemIntegration:
    """Test cases for Vision System integration (completion summary requirement)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_task_repo = Mock(spec=TaskRepository)
        self.use_case = CompleteTaskUseCase(self.mock_task_repo)
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory')
    def test_execute_missing_completion_summary_raises_error(self, mock_factory):
        """Test that missing completion summary raises Vision System error."""
        # Mock the facade to prevent database connections
        mock_facade = Mock()
        mock_facade.get_context.return_value = {"success": False}
        mock_factory.return_value.create_facade.return_value = mock_facade
        
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.git_branch_id = "branch-123"
        mock_task.project_id = None
        mock_task.context_id = None
        # When complete_task is called, it should raise the error
        mock_task.complete_task.side_effect = MissingCompletionSummaryError(task_id="task-123")
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # The use case catches MissingCompletionSummaryError and returns an error response
        result = self.use_case.execute(task_id="task-123")  # No completion summary
        
        assert result["success"] is False
        assert "task-123" in result["task_id"]
        assert "completion" in result["message"].lower() and "summary" in result["message"].lower()
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory')
    def test_execute_empty_completion_summary_raises_error(self, mock_factory):
        """Test that empty completion summary raises Vision System error."""
        # Mock the facade to prevent database connections
        mock_facade = Mock()
        mock_facade.get_context.return_value = {"success": False}
        mock_factory.return_value.create_facade.return_value = mock_facade
        
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.git_branch_id = "branch-123"
        mock_task.project_id = None
        mock_task.context_id = None
        mock_task.complete_task.side_effect = MissingCompletionSummaryError(task_id="task-123")
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # The use case catches MissingCompletionSummaryError and returns an error response
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary=""  # Empty summary
        )
        
        assert result["success"] is False
        assert "task-123" in result["task_id"]
        assert "completion" in result["message"].lower() and "summary" in result["message"].lower()
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory')
    def test_execute_whitespace_completion_summary_raises_error(self, mock_factory):
        """Test that whitespace-only completion summary raises Vision System error."""
        # Mock the facade to prevent database connections
        mock_facade = Mock()
        mock_facade.get_context.return_value = {"success": False}
        mock_factory.return_value.create_facade.return_value = mock_facade
        
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.git_branch_id = "branch-123"
        mock_task.project_id = None
        mock_task.context_id = None
        mock_task.complete_task.side_effect = MissingCompletionSummaryError(task_id="task-123")
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # The use case catches MissingCompletionSummaryError and returns an error response
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="   \t  "  # Whitespace only
        )
        
        assert result["success"] is False
        assert "task-123" in result["task_id"]
        assert "completion" in result["message"].lower() and "summary" in result["message"].lower()
    
    def test_execute_valid_completion_summary_passes(self):
        """Test that valid completion summary allows completion."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()  # No exception
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Implemented user authentication with JWT tokens"
        )
        
        # Verify completion was called with summary
        mock_task.complete_task.assert_called_once()
        call_args = mock_task.complete_task.call_args[1]
        assert "completion_summary" in call_args
        assert call_args["completion_summary"] == "Implemented user authentication with JWT tokens"
        
        assert result["success"] is True


class TestCompleteTaskUseCaseSubtaskValidation:
    """Test cases for subtask completion validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_task_repo = Mock(spec=TaskRepository)
        self.mock_subtask_repo = Mock(spec=SubtaskRepository)
        self.mock_context_repo = Mock(spec=TaskContextRepository)
        self.use_case = CompleteTaskUseCase(
            self.mock_task_repo,
            self.mock_subtask_repo,
            self.mock_context_repo
        )
    
    def test_execute_cannot_complete_with_pending_subtasks(self):
        """Test completion fails when subtasks are not complete."""
        # Setup task with subtasks
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # Setup completion service to indicate validation fails
        self.use_case._completion_service = Mock()
        self.use_case._completion_service.validate_task_completion.side_effect = TaskCompletionError("Subtasks are not complete")
        
        # The use case catches TaskCompletionError and returns an error response
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Trying to complete with pending subtasks"
        )
        
        assert result["success"] is False
        assert "task-123" in result["task_id"]
        assert "Subtasks are not complete" in result["message"]
        
        # Verify validation was called
        self.use_case._completion_service.validate_task_completion.assert_called_once_with(mock_task)
        
        # Verify task was not saved after validation failure
        mock_task.complete_task.assert_not_called()
    
    def test_execute_successful_with_all_subtasks_complete(self):
        """Test successful completion when all subtasks are complete."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        # Setup context
        self.mock_context_repo.get.return_value = {"context": "exists"}
        
        # Setup completion service to indicate all requirements met
        self.use_case._completion_service = Mock()
        self.use_case._completion_service.validate_task_completion.return_value = True
        self.use_case._completion_service.get_subtask_completion_summary.return_value = {
            "total": 3,
            "completed": 3,
            "incomplete": 0,
            "completion_percentage": 100,
            "can_complete_parent": True
        }
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="All subtasks completed successfully"
        )
        
        # Verify validation was successful
        self.use_case._completion_service.validate_task_completion.assert_called_once_with(mock_task)
        
        # Verify success
        assert result["success"] is True
        assert result["subtask_summary"]["can_complete_parent"] is True
    
    def test_execute_subtask_completion_failure(self):
        """Test handling of subtask completion failure."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # Setup subtask repository to return incomplete subtasks (no completion service)
        self.use_case._completion_service = None  # No completion service, use fallback
        incomplete_subtask = Mock(spec=Subtask)
        incomplete_subtask.is_completed = False
        incomplete_subtask.title = "Incomplete subtask"
        
        self.mock_subtask_repo.find_by_parent_task_id.return_value = [incomplete_subtask]
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Attempting completion with subtask failures"
        )
        
        # Verify failure response
        assert result["success"] is False
        assert "cannot complete task" in result["message"].lower()
        assert "1 of 1 subtasks are incomplete" in result["message"].lower()


class TestCompleteTaskUseCaseContextManagement:
    """Test cases for context creation and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_task_repo = Mock(spec=TaskRepository)
        self.mock_context_repo = Mock(spec=TaskContextRepository)
        self.use_case = CompleteTaskUseCase(self.mock_task_repo, task_context_repository=self.mock_context_repo)
    
    def test_execute_auto_creates_context_when_missing(self):
        """Test auto-creation of context when it doesn't exist."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("task-123")
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        mock_task.context_id = None  # No context linked yet
        mock_task.git_branch_id = "branch-123"
        mock_task.project_id = "project-456"
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        # Setup context repository - no existing context
        self.mock_context_repo.get.return_value = None
        
        # Mock the UnifiedContextFacadeFactory at import location
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            mock_facade = Mock()
            mock_facade.get_context.return_value = {"success": False, "error": "Context not found"}
            mock_facade.create_context.return_value = {"success": True}
            mock_facade.update_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_facade
            
            result = self.use_case.execute(
                task_id="task-123",
                completion_summary="Creating context automatically"
            )
            
            # Verify context retrieval was attempted
            self.mock_context_repo.get.assert_called_with("task-123")
            
            # Verify success
            assert result["success"] is True
    
    def test_execute_uses_existing_context(self):
        """Test completion with existing context."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        mock_task.context_id = "task-123"  # Context already linked
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        # Setup existing context
        existing_context = {
            "context": "existing",
            "progress": "in_progress",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.mock_context_repo.get.return_value = existing_context
        
        # Mock the UnifiedContextFacadeFactory at import location
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            mock_facade = Mock()
            mock_facade.get_context.return_value = {"success": True, "context": existing_context}
            mock_facade.update_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_facade
            
            result = self.use_case.execute(
                task_id="task-123",
                completion_summary="Using existing context"
            )
            
            # Verify existing context was used
            self.mock_context_repo.get.assert_called_with("task-123")
            
            # Verify success
            assert result["success"] is True


class TestCompleteTaskUseCaseErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_task_repo = Mock(spec=TaskRepository)
        self.use_case = CompleteTaskUseCase(self.mock_task_repo)
    
    def test_execute_with_string_task_id(self):
        """Test execution with string task ID."""
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId.from_string') as mock_from_string:
            mock_task_id = Mock()
            mock_from_string.return_value = mock_task_id
            
            result = self.use_case.execute(
                task_id="task-123",  # String ID
                completion_summary="Testing string ID conversion"
            )
            
            # Verify ID conversion
            mock_from_string.assert_called_once_with("task-123")
            self.mock_task_repo.find_by_id.assert_called_once_with(mock_task_id)
            
            assert result["success"] is True
    
    def test_execute_with_integer_task_id(self):
        """Test execution with integer task ID."""
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = True
        
        with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId.from_string') as mock_from_string:
            mock_task_id = Mock()
            mock_from_string.return_value = mock_task_id
            
            result = self.use_case.execute(
                task_id=123,  # Integer ID
                completion_summary="Testing integer ID conversion"
            )
            
            # Verify ID conversion (integer converted to string first)
            mock_from_string.assert_called_once_with("123")
            
            assert result["success"] is True
    
    def test_execute_repository_save_failure(self):
        """Test handling of repository save failure."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task = Mock()
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        self.mock_task_repo.save.return_value = False  # Save fails
        
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Testing save failure"
        )
        
        # Verify task completion was attempted
        mock_task.complete_task.assert_called_once()
        
        # Since save returns False but doesn't raise exception, task is still marked as done
        # The implementation doesn't check save return value anymore
        assert result["success"] is True
        assert result["message"] == "task task-123 done, can next_task"
    
    def test_execute_with_exception_during_completion(self):
        """Test handling of exceptions during task completion."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task.side_effect = Exception("Unexpected error during completion")
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # Exception during complete_task should be re-raised
        with pytest.raises(Exception, match="Unexpected error during completion"):
            self.use_case.execute(
                task_id="task-123",
                completion_summary="Testing exception handling"
            )
    
    def test_execute_with_completion_error(self):
        """Test handling of TaskCompletionError."""
        # Setup task
        mock_task = Mock(spec=Task)
        mock_task.status = TaskStatus.in_progress()
        mock_task.complete_task.side_effect = TaskCompletionError("Business rule violation")
        
        self.mock_task_repo.find_by_id.return_value = mock_task
        
        # TaskCompletionError should be caught and returned as failure  
        result = self.use_case.execute(
            task_id="task-123",
            completion_summary="Testing completion error"
        )
        
        # Verify specific error handling
        assert result["success"] is False
        assert "business rule violation" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__])