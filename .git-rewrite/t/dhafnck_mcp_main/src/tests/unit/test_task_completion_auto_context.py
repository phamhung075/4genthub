"""Unit test for auto-context creation during task completion.

This test verifies that Issue #1 is fixed: tasks can now be completed
without manually creating context first.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import uuid

from fastmcp.task_management.application.use_cases.complete_task import CompleteTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import TaskStatus, Priority, TaskId


class TestTaskCompletionAutoContext:
    
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

    """Test that task completion auto-creates context if needed."""
    
    def test_complete_task_auto_creates_context_when_missing(self):
        """Test that completing a task without context auto-creates it."""
        # Create mock repositories
        task_id = str(uuid.uuid4())
        
        # Create a mock task
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId(task_id)
        mock_task.title = "Test Task"
        mock_task.description = "Test description"
        mock_task.status = TaskStatus("todo")
        mock_task.git_branch_id = str(uuid.uuid4())
        mock_task.context_id = None
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.get_events.return_value = []
        mock_task.get_subtask_progress.return_value = {"total": 0, "completed": 0}
        
        # Mock the complete_task method to update status
        def mock_complete_task(completion_summary, context_updated_at=None):
            mock_task.status = TaskStatus("done")
            mock_task.completion_summary = completion_summary
        mock_task.complete_task = Mock(side_effect=mock_complete_task)
        
        # Mock task repository
        mock_task_repo = Mock()
        mock_task_repo.find_by_id.return_value = mock_task
        mock_task_repo.save.return_value = True
        mock_task_repo.find_all.return_value = []
        
        # Mock subtask repository
        mock_subtask_repo = Mock()
        mock_subtask_repo.find_by_parent_task_id.return_value = []
        
        # Mock context repository that returns None (no context exists)
        mock_context_repo = Mock()
        mock_context_repo.get.return_value = None
        
        # Create use case
        use_case = CompleteTaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            task_context_repository=mock_context_repo
        )
        
        # Mock the UnifiedContextFacadeFactory to verify context creation
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            # Create mock facade
            mock_facade = Mock()
            mock_facade.create_context.return_value = {"success": True}
            # CRITICAL: Mock get_context to return failure/no context to trigger auto-creation
            mock_facade.get_context.return_value = {
                "success": False,
                "error": "Context not found"
            }
            mock_facade.merge_context.return_value = {"success": True}
            
            # Configure factory to return mock facade
            mock_factory_instance = Mock()
            mock_factory_instance.create_facade.return_value = mock_facade
            mock_factory.return_value = mock_factory_instance
            
            # Execute task completion
            result = use_case.execute(
                task_id=task_id,
                completion_summary="Task completed with auto-created context",
                testing_notes="Verified auto context creation"
            )
            
            # Verify the task was marked as complete
            assert result["success"] is True
            assert result["status"] == "done"
            assert f"task {task_id} done, can next_task" in result["message"]
            
            # Verify context was checked (called twice - once for check, once after creation)
            assert mock_context_repo.get.call_count >= 1
            # First call should be the check for existing context
            first_call = mock_context_repo.get.call_args_list[0]
            assert first_call[0][0] == task_id
            
            # Verify context was auto-created (hierarchy: branch + task)
            assert mock_facade.create_context.call_count >= 1
            
            # Check that the task context was created
            task_context_calls = [call for call in mock_facade.create_context.call_args_list 
                                 if call[1]["level"] == "task"]
            assert len(task_context_calls) >= 1, "Task context should have been created"
            
            task_call = task_context_calls[0]
            assert task_call[1]["context_id"] == task_id
            assert task_call[1]["data"]["task_data"]["title"] == "Test Task"
    
    def test_complete_task_with_existing_context_no_auto_create(self):
        """Test that completing a task with existing context doesn't create another."""
        # Create mock repositories
        task_id = str(uuid.uuid4())
        
        # Create a mock task
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId(task_id)
        mock_task.title = "Test Task"
        mock_task.status = TaskStatus("todo")
        mock_task.git_branch_id = str(uuid.uuid4())
        mock_task.context_id = task_id  # Context exists
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.get_events.return_value = []
        mock_task.get_subtask_progress.return_value = {"total": 0, "completed": 0}
        
        # Mock the complete_task method to update status
        def mock_complete_task(completion_summary, context_updated_at=None):
            mock_task.status = TaskStatus("done")
            mock_task.completion_summary = completion_summary
        mock_task.complete_task = Mock(side_effect=mock_complete_task)
        
        # Mock task repository
        mock_task_repo = Mock()
        mock_task_repo.find_by_id.return_value = mock_task
        mock_task_repo.save.return_value = True
        mock_task_repo.find_all.return_value = []
        
        # Mock subtask repository
        mock_subtask_repo = Mock()
        mock_subtask_repo.find_by_parent_task_id.return_value = []
        
        # Mock context repository that returns existing context
        mock_context_repo = Mock()
        mock_context_repo.get.return_value = {
            "id": task_id,
            "task_data": {"title": "Test Task", "status": "todo"}
        }
        
        # Create use case
        use_case = CompleteTaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            task_context_repository=mock_context_repo
        )
        
        # Mock the UnifiedContextFacadeFactory
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            # Create mock facade
            mock_facade = Mock()
            mock_facade.create_context.return_value = {"success": True}
            mock_facade.get_context.return_value = {
                "success": True,
                "context": {
                    "updated_at": "2025-07-19 10:00:00"
                }
            }
            mock_facade.merge_context.return_value = {"success": True}
            
            # Configure factory to return mock facade
            mock_factory_instance = Mock()
            mock_factory_instance.create_facade.return_value = mock_facade
            mock_factory.return_value = mock_factory_instance
            
            # Execute task completion
            result = use_case.execute(
                task_id=task_id,
                completion_summary="Task completed with existing context",
                testing_notes="Verified existing context flow"
            )
            
            # Verify the task was marked as complete
            assert result["success"] is True
            assert result["status"] == "done"
            
            # Verify context was checked
            assert mock_context_repo.get.call_count >= 1
            
            # Verify context was NOT created (already exists)
            mock_facade.create_context.assert_not_called()
    
    def test_complete_task_continues_even_if_auto_context_fails(self):
        """Test that task completion continues even if auto-context creation fails."""
        # Create mock repositories
        task_id = str(uuid.uuid4())
        
        # Create a mock task
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId(task_id)
        mock_task.title = "Test Task"
        mock_task.status = TaskStatus("todo")
        mock_task.git_branch_id = str(uuid.uuid4())
        mock_task.context_id = None
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.get_events.return_value = []
        mock_task.get_subtask_progress.return_value = {"total": 0, "completed": 0}
        
        # Mock the complete_task method to update status
        def mock_complete_task(completion_summary, context_updated_at=None):
            mock_task.status = TaskStatus("done")
            mock_task.completion_summary = completion_summary
        mock_task.complete_task = Mock(side_effect=mock_complete_task)
        
        # Mock task repository
        mock_task_repo = Mock()
        mock_task_repo.find_by_id.return_value = mock_task
        mock_task_repo.save.return_value = True
        mock_task_repo.find_all.return_value = []
        
        # Mock subtask repository
        mock_subtask_repo = Mock()
        mock_subtask_repo.find_by_parent_task_id.return_value = []
        
        # Mock context repository that returns None (no context exists)
        mock_context_repo = Mock()
        mock_context_repo.get.return_value = None
        
        # Create use case
        use_case = CompleteTaskUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            task_context_repository=mock_context_repo
        )
        
        # Mock the UnifiedContextFacadeFactory to simulate failure
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            # Simulate context creation failure
            mock_factory.side_effect = Exception("Failed to create facade")
            
            # Execute task completion
            result = use_case.execute(
                task_id=task_id,
                completion_summary="Task completed despite context issues",
                testing_notes="Testing graceful handling"
            )
            
            # Verify the task was still marked as complete
            assert result["success"] is True
            assert result["status"] == "done"
            assert f"task {task_id} done, can next_task" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])