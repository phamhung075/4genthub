"""
Test suite for subtask assignees update functionality
This test ensures that assignees can be properly updated for subtasks
without encountering the 'str' object has no attribute 'copy' error

NOTE: Updated to follow new architecture where Task entities only store subtask IDs,
and subtasks are managed through SubtaskRepository.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
import uuid

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.application.use_cases.update_subtask import UpdateSubtaskUseCase
from fastmcp.task_management.application.dtos.subtask import UpdateSubtaskRequest


class TestSubtaskAssigneesUpdate:
    
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

    """Test suite for updating subtask assignees"""
    
    def _create_task_and_subtask(self, subtask_assignees=None):
        """Helper method to create task and subtask following new architecture"""
        # Create task
        task_id = TaskId.from_string("12345678-1234-5678-1234-567812345678")
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create subtask with proper UUID
        subtask_id = str(uuid.uuid4())
        subtask = Subtask(
            id=SubtaskId(subtask_id),
            parent_task_id=task_id,
            title="Test Subtask",
            description="Test subtask description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            assignees=subtask_assignees or ["user1"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Task only stores subtask ID
        task.subtasks.append(subtask_id)
        
        return task, subtask, subtask_id
    
    def _setup_repositories(self, task, subtask):
        """Helper method to setup mock repositories"""
        # Create mock repositories
        task_repository = Mock()
        task_repository.find_by_id.return_value = task
        task_repository.save.return_value = task
        
        subtask_repository = Mock()
        subtask_repository.find_by_id.return_value = subtask
        subtask_repository.save.return_value = subtask
        
        return task_repository, subtask_repository
    
    def test_update_subtask_assignees_with_list(self):
        """Test updating subtask assignees with a list of strings"""
        # Arrange
        task, subtask, subtask_id = self._create_task_and_subtask(["user1"])
        task_repository, subtask_repository = self._setup_repositories(task, subtask)
        
        # Create use case with subtask repository
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request with new assignees
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id=subtask_id,
            assignees=["user2", "user3"]
        )
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert response.subtask["assignees"] == ["user2", "user3"]
        assert subtask_repository.save.called
        assert subtask.assignees == ["user2", "user3"]
        
    def test_update_subtask_assignees_with_empty_list(self):
        """Test updating subtask assignees with an empty list"""
        # Arrange
        task, subtask, subtask_id = self._create_task_and_subtask(["user1", "user2"])
        task_repository, subtask_repository = self._setup_repositories(task, subtask)
        
        # Create use case
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request with empty assignees
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id=subtask_id,
            assignees=[]
        )
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert response.subtask["assignees"] == []
        assert subtask_repository.save.called
        
    def test_update_subtask_assignees_preserves_other_fields(self):
        """Test that updating assignees preserves other subtask fields"""
        # Arrange
        task, subtask, subtask_id = self._create_task_and_subtask(["user1"])
        
        # Set some custom fields on subtask
        subtask.title = "Original Title"
        subtask.description = "Original Description"
        subtask.status = TaskStatus.in_progress()
        subtask.priority = Priority.high()
        
        task_repository, subtask_repository = self._setup_repositories(task, subtask)
        
        # Create use case
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request - only update assignees
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id=subtask_id,
            assignees=["user2", "user3"]
        )
        
        # Act
        response = use_case.execute(request)
        
        # Assert
        assert response.subtask["assignees"] == ["user2", "user3"]
        assert response.subtask["title"] == "Original Title"
        assert response.subtask["description"] == "Original Description"
        assert response.subtask["status"] == "in_progress"
        assert response.subtask["priority"] == "high"
        
    def test_update_subtask_with_string_subtasks_in_list(self):
        """Test that string subtasks in task list don't cause errors"""
        # Arrange
        task, subtask, subtask_id = self._create_task_and_subtask()
        
        # Mix of valid UUID and invalid string subtasks
        task.subtasks = [
            "invalid string subtask",  # This should be ignored
            subtask_id,  # Valid UUID
            123,  # Invalid type
            None  # Invalid type
        ]
        
        task_repository, subtask_repository = self._setup_repositories(task, subtask)
        
        # Create use case
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id=subtask_id,
            assignees=["user2", "user3"]
        )
        
        # Act
        response = use_case.execute(request)
        
        # Assert - Should still work despite invalid entries
        assert response.subtask["assignees"] == ["user2", "user3"]
        assert subtask_repository.save.called
        
    def test_update_subtask_assignees_with_none_value(self):
        """Test that None value for assignees is handled properly"""
        # Arrange
        task, subtask, subtask_id = self._create_task_and_subtask(["user1"])
        task_repository, subtask_repository = self._setup_repositories(task, subtask)
        
        # Create use case
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request with None assignees (should not update)
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id=subtask_id,
            assignees=None
        )
        
        # Act
        response = use_case.execute(request)
        
        # Assert - assignees should remain unchanged
        assert response.subtask["assignees"] == ["user1"]
        # Save is still called because the request went through
        assert subtask_repository.save.called
        
    def test_update_nonexistent_subtask_raises_error(self):
        """Test that updating non-existent subtask raises error"""
        # Arrange
        task, _, _ = self._create_task_and_subtask()
        task_repository = Mock()
        task_repository.find_by_id.return_value = task
        
        subtask_repository = Mock()
        subtask_repository.find_by_id.return_value = None  # Subtask not found
        
        # Create use case
        use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        # Create update request
        request = UpdateSubtaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            id="non-existent-subtask-id",
            assignees=["user2"]
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask non-existent-subtask-id not found"):
            use_case.execute(request)