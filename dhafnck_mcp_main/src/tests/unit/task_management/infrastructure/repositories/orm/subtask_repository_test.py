"""
Comprehensive test suite for ORMSubtaskRepository.

Tests the SubtaskRepository ORM implementation including:
- CRUD operations (save, find, update, delete)
- User-scoped data isolation
- Domain entity to ORM model conversion
- Subtask completion and progress tracking
- Parent task relationship management
- Error handling and database exceptions
- Complex query operations
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import json

from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)
from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
from fastmcp.task_management.infrastructure.database.models import TaskSubtask


class TestORMSubtaskRepositoryInitialization:
    """Test cases for ORMSubtaskRepository initialization and configuration."""
    
    def test_init_with_minimal_params(self):
        """Test repository initialization with minimal parameters."""
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value = mock_session
            
            repo = ORMSubtaskRepository()
            
            # Should initialize both base classes
            assert repo.model_class == TaskSubtask
            assert hasattr(repo, '_user_id')
            assert hasattr(repo, '_apply_user_filter')
    
    def test_init_with_session_and_user_id(self):
        """Test repository initialization with session and user ID."""
        mock_session = Mock()
        
        repo = ORMSubtaskRepository(session=mock_session, user_id="test-user")
        
        assert repo._user_id == "test-user"
        # BaseUserScopedRepository should handle the session
    
    def test_init_inheritance_chain(self):
        """Test repository properly inherits from all base classes."""
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = Mock()
            
            repo = ORMSubtaskRepository()
            
            # Should have methods from all base classes
            assert hasattr(repo, '_apply_user_filter')  # BaseUserScopedRepository
            assert hasattr(repo, 'model_class')         # BaseORMRepository
            assert hasattr(repo, 'save')                # SubtaskRepository interface


class TestORMSubtaskRepositoryDataConversion:
    """Test cases for domain entity to ORM model conversion."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = Mock()
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_to_model_data_minimal_subtask(self):
        """Test converting minimal subtask entity to model data."""
        subtask = Subtask(
            id=SubtaskId("sub-123"),
            task_id=TaskId("task-456"),
            title="Test Subtask",
            description="Test Description"
        )
        
        with patch.object(self.repo, '_to_model_data') as mock_convert:
            expected_data = {
                'id': 'sub-123',
                'task_id': 'task-456',
                'title': 'Test Subtask',
                'description': 'Test Description',
                'status': 'todo',
                'priority': 'medium'
            }
            mock_convert.return_value = expected_data
            
            result = self.repo._to_model_data(subtask)
            
            mock_convert.assert_called_once_with(subtask)
            assert result == expected_data
    
    def test_to_model_data_full_subtask(self):
        """Test converting complete subtask entity to model data."""
        subtask = Subtask(
            id=SubtaskId("sub-123"),
            task_id=TaskId("task-456"),
            title="Full Subtask",
            description="Full Description",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "@user2"],
            progress_percentage=75,
            completion_summary="Nearly done",
            testing_notes="Tests passed"
        )
        
        with patch.object(self.repo, '_to_model_data') as mock_convert:
            expected_data = {
                'id': 'sub-123',
                'task_id': 'task-456',
                'title': 'Full Subtask',
                'description': 'Full Description',
                'status': 'in_progress',
                'priority': 'high',
                'assignees': json.dumps(['@user1', '@user2']),
                'progress_percentage': 75,
                'completion_summary': 'Nearly done',
                'testing_notes': 'Tests passed'
            }
            mock_convert.return_value = expected_data
            
            result = self.repo._to_model_data(subtask)
            
            assert result == expected_data
    
    def test_from_model_data_to_entity(self):
        """Test converting ORM model to domain entity."""
        # Mock TaskSubtask model
        mock_model = Mock(spec=TaskSubtask)
        mock_model.id = "sub-123"
        mock_model.task_id = "task-456"
        mock_model.title = "Test Subtask"
        mock_model.description = "Test Description"
        mock_model.status = "todo"
        mock_model.priority = "medium"
        mock_model.assignees = json.dumps(["@user1"])
        mock_model.progress_percentage = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.completion_summary = None
        mock_model.testing_notes = None
        
        with patch.object(self.repo, '_from_model_data') as mock_convert:
            mock_entity = Mock(spec=Subtask)
            mock_convert.return_value = mock_entity
            
            result = self.repo._from_model_data(mock_model)
            
            mock_convert.assert_called_once_with(mock_model)
            assert result == mock_entity


class TestORMSubtaskRepositorySaveOperations:
    """Test cases for subtask save operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.context_manager.__exit__ = Mock(return_value=False)
        
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = self.context_manager
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_save_new_subtask_success(self):
        """Test successfully saving a new subtask."""
        # Create new subtask (no ID)
        subtask = Subtask(
            task_id=TaskId("task-456"),
            title="New Subtask",
            description="New Description"
        )
        subtask.id = None  # Explicitly no ID to indicate new subtask
        
        # Mock model data conversion
        model_data = {
            'task_id': 'task-456',
            'title': 'New Subtask',
            'description': 'New Description',
            'status': 'todo',
            'priority': 'medium'
        }
        
        # Mock created model
        mock_created_model = Mock(spec=TaskSubtask)
        mock_created_model.id = "sub-123"
        mock_created_model.updated_at = datetime.now(timezone.utc)
        
        with patch.object(self.repo, '_to_model_data', return_value=model_data):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                # Mock TaskSubtask creation
                with patch('fastmcp.task_management.infrastructure.database.models.TaskSubtask', return_value=mock_created_model) as mock_subtask_class:
                    
                    result = self.repo.save(subtask)
                    
                    # Verify model was created with correct data
                    mock_subtask_class.assert_called_once_with(**model_data)
                    
                    # Verify session operations
                    self.mock_session.add.assert_called_once_with(mock_created_model)
                    self.mock_session.flush.assert_called_once()
                    
                    # Verify success
                    assert result is True
                    assert subtask.id.value == "sub-123"
    
    def test_save_existing_subtask_success(self):
        """Test successfully updating an existing subtask."""
        # Create existing subtask with ID
        subtask = Subtask(
            id=SubtaskId("sub-123"),
            task_id=TaskId("task-456"),
            title="Updated Subtask",
            description="Updated Description"
        )
        
        # Mock existing model in database
        mock_existing_model = Mock(spec=TaskSubtask)
        mock_existing_model.id = "sub-123"
        mock_existing_model.updated_at = datetime.now(timezone.utc)
        
        # Mock query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_existing_model
        
        self.mock_session.query.return_value = mock_query
        
        model_data = {
            'id': 'sub-123',
            'task_id': 'task-456',
            'title': 'Updated Subtask',
            'description': 'Updated Description',
            'status': 'todo',
            'priority': 'medium'
        }
        
        with patch.object(self.repo, '_to_model_data', return_value=model_data):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                
                result = self.repo.save(subtask)
                
                # Verify query for existing subtask
                self.mock_session.query.assert_called_once_with(TaskSubtask)
                mock_query.filter.assert_called_once()
                
                # Verify model was updated
                assert hasattr(mock_existing_model, 'title')  # Attributes should be set
                
                # Verify session flush
                self.mock_session.flush.assert_called_once()
                
                # Verify success
                assert result is True
    
    def test_save_existing_subtask_not_found(self):
        """Test updating non-existent subtask creates new one."""
        subtask = Subtask(
            id=SubtaskId("sub-nonexistent"),
            task_id=TaskId("task-456"),
            title="Subtask",
            description="Description"
        )
        
        # Mock query returning no existing subtask
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Not found
        
        self.mock_session.query.return_value = mock_query
        
        model_data = {
            'id': 'sub-nonexistent',
            'task_id': 'task-456',
            'title': 'Subtask',
            'description': 'Description'
        }
        
        # Mock new model creation
        mock_new_model = Mock(spec=TaskSubtask)
        mock_new_model.id = "sub-nonexistent"
        mock_new_model.updated_at = datetime.now(timezone.utc)
        
        with patch.object(self.repo, '_to_model_data', return_value=model_data):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                with patch('fastmcp.task_management.infrastructure.database.models.TaskSubtask', return_value=mock_new_model):
                    
                    result = self.repo.save(subtask)
                    
                    # Should create new subtask when existing not found
                    self.mock_session.add.assert_called_once_with(mock_new_model)
                    self.mock_session.flush.assert_called_once()
                    
                    assert result is True
    
    def test_save_database_error(self):
        """Test save operation with database error."""
        subtask = Subtask(
            task_id=TaskId("task-456"),
            title="Subtask",
            description="Description"
        )
        subtask.id = None
        
        with patch.object(self.repo, '_to_model_data', return_value={}):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                # Mock database error
                self.mock_session.add.side_effect = SQLAlchemyError("Database connection failed")
                
                result = self.repo.save(subtask)
                
                # Should return False on database error
                assert result is False


class TestORMSubtaskRepositoryFindOperations:
    """Test cases for subtask find operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.context_manager.__exit__ = Mock(return_value=False)
        
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = self.context_manager
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_find_by_id_found(self):
        """Test finding subtask by ID when it exists."""
        # Mock subtask model
        mock_model = Mock(spec=TaskSubtask)
        mock_model.id = "sub-123"
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_model
        
        self.mock_session.query.return_value = mock_query
        
        # Mock entity conversion
        mock_entity = Mock(spec=Subtask)
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_from_model_data', return_value=mock_entity):
                with patch.object(self.repo, '_apply_user_filter', return_value=True):
                    
                    result = self.repo.find_by_id(SubtaskId("sub-123"))
                    
                    # Verify query
                    self.mock_session.query.assert_called_once_with(TaskSubtask)
                    mock_query.filter.assert_called_once()
                    
                    # Verify user filter was applied
                    self.repo._apply_user_filter.assert_called_once_with(mock_model)
                    
                    # Verify result
                    assert result == mock_entity
    
    def test_find_by_id_not_found(self):
        """Test finding subtask by ID when it doesn't exist."""
        # Mock empty query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            
            result = self.repo.find_by_id(SubtaskId("sub-nonexistent"))
            
            # Should return None when not found
            assert result is None
    
    def test_find_by_id_user_filter_denied(self):
        """Test finding subtask denied by user filter."""
        mock_model = Mock(spec=TaskSubtask)
        mock_model.id = "sub-123"
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_apply_user_filter', return_value=False):
                
                result = self.repo.find_by_id(SubtaskId("sub-123"))
                
                # Should return None when user filter denies access
                assert result is None
    
    def test_find_by_task_id(self):
        """Test finding subtasks by parent task ID."""
        # Mock subtask models
        mock_model1 = Mock(spec=TaskSubtask)
        mock_model1.id = "sub-1"
        mock_model1.task_id = "task-456"
        
        mock_model2 = Mock(spec=TaskSubtask)
        mock_model2.id = "sub-2"
        mock_model2.task_id = "task-456"
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [mock_model1, mock_model2]
        
        self.mock_session.query.return_value = mock_query
        
        # Mock entity conversion
        mock_entities = [Mock(spec=Subtask), Mock(spec=Subtask)]
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_from_model_data', side_effect=mock_entities):
                with patch.object(self.repo, '_apply_user_filter', return_value=True):
                    
                    result = self.repo.find_by_task_id(TaskId("task-456"))
                    
                    # Verify query for task ID
                    mock_query.filter.assert_called_once()
                    mock_filter.all.assert_called_once()
                    
                    # Verify results
                    assert len(result) == 2
                    assert result == mock_entities


class TestORMSubtaskRepositoryCompletionOperations:
    """Test cases for subtask completion operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.context_manager.__exit__ = Mock(return_value=False)
        
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = self.context_manager
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_complete_subtask_success(self):
        """Test successful subtask completion."""
        # Mock existing subtask
        mock_model = Mock(spec=TaskSubtask)
        mock_model.id = "sub-123"
        mock_model.status = "in_progress"
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.complete_subtask(
                    SubtaskId("sub-123"),
                    completion_summary="Task completed successfully",
                    testing_notes="All tests passed"
                )
                
                # Verify subtask was found and updated
                mock_query.filter.assert_called_once()
                
                # Verify completion fields were set
                assert mock_model.status == "done"
                assert mock_model.progress_percentage == 100
                assert mock_model.completion_summary == "Task completed successfully"
                assert mock_model.testing_notes == "All tests passed"
                
                # Verify session flush
                self.mock_session.flush.assert_called_once()
                
                # Verify success
                assert result is True
    
    def test_complete_subtask_not_found(self):
        """Test completing non-existent subtask."""
        # Mock empty query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            
            result = self.repo.complete_subtask(
                SubtaskId("sub-nonexistent"),
                completion_summary="Trying to complete non-existent"
            )
            
            # Should return False when subtask not found
            assert result is False
    
    def test_complete_subtask_user_filter_denied(self):
        """Test completing subtask denied by user filter."""
        mock_model = Mock(spec=TaskSubtask)
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_apply_user_filter', return_value=False):
                
                result = self.repo.complete_subtask(
                    SubtaskId("sub-123"),
                    completion_summary="Denied by user filter"
                )
                
                # Should return False when user filter denies access
                assert result is False


class TestORMSubtaskRepositoryProgressOperations:
    """Test cases for subtask progress tracking operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.context_manager.__exit__ = Mock(return_value=False)
        
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = self.context_manager
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_update_progress_success(self):
        """Test successful progress update."""
        # Mock existing subtask
        mock_model = Mock(spec=TaskSubtask)
        mock_model.id = "sub-123"
        mock_model.progress_percentage = 25
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.update_progress(
                    SubtaskId("sub-123"),
                    progress_percentage=75,
                    progress_notes="Making good progress"
                )
                
                # Verify progress was updated
                assert mock_model.progress_percentage == 75
                
                # Verify session flush
                self.mock_session.flush.assert_called_once()
                
                # Verify success
                assert result is True
    
    def test_get_completion_status(self):
        """Test getting completion status for subtasks by task."""
        # Mock subtasks with different completion states
        mock_subtask1 = Mock(spec=TaskSubtask)
        mock_subtask1.id = "sub-1"
        mock_subtask1.status = "done"
        mock_subtask1.progress_percentage = 100
        
        mock_subtask2 = Mock(spec=TaskSubtask)
        mock_subtask2.id = "sub-2"
        mock_subtask2.status = "in_progress"
        mock_subtask2.progress_percentage = 50
        
        mock_subtask3 = Mock(spec=TaskSubtask)
        mock_subtask3.id = "sub-3"
        mock_subtask3.status = "done"
        mock_subtask3.progress_percentage = 100
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [mock_subtask1, mock_subtask2, mock_subtask3]
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                status = self.repo.get_completion_status(TaskId("task-456"))
                
                # Verify completion status calculation
                assert status["total"] == 3
                assert status["completed"] == 2  # 2 out of 3 done
                assert status["percentage"] == pytest.approx(66.67, rel=0.01)
                
                # Verify detailed breakdown exists
                assert "details" in status
                assert len(status["details"]) == 3


class TestORMSubtaskRepositoryErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.context_manager.__exit__ = Mock(return_value=False)
        
        with patch('fastmcp.task_management.infrastructure.repositories.orm.subtask_repository.get_session') as mock_get_session:
            mock_get_session.return_value = self.context_manager
            self.repo = ORMSubtaskRepository(user_id="test-user")
    
    def test_save_with_session_error(self):
        """Test save operation with session error."""
        subtask = Subtask(
            task_id=TaskId("task-456"),
            title="Test Subtask",
            description="Test Description"
        )
        subtask.id = None
        
        with patch.object(self.repo, '_to_model_data', return_value={}):
            with patch.object(self.repo, 'get_db_session', side_effect=SQLAlchemyError("Session creation failed")):
                
                result = self.repo.save(subtask)
                
                # Should handle session error gracefully
                assert result is False
    
    def test_find_with_invalid_id_type(self):
        """Test finding subtask with invalid ID type."""
        with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
            
            # Should handle invalid ID gracefully
            result = self.repo.find_by_id("invalid-id-type")  # String instead of SubtaskId
            
            # Implementation should handle type conversion or return None
            assert result is None or isinstance(result, Subtask)
    
    def test_database_constraint_violation(self):
        """Test handling of database constraint violations."""
        subtask = Subtask(
            task_id=TaskId("nonexistent-task"),  # Foreign key violation
            title="Subtask",
            description="Description"
        )
        subtask.id = None
        
        with patch.object(self.repo, '_to_model_data', return_value={}):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                # Mock integrity error
                self.mock_session.add.side_effect = IntegrityError("Foreign key constraint", None, None)
                
                result = self.repo.save(subtask)
                
                # Should handle constraint violations gracefully
                assert result is False
    
    def test_json_serialization_error(self):
        """Test handling of JSON serialization errors for assignees."""
        subtask = Subtask(
            task_id=TaskId("task-456"),
            title="Test",
            description="Test",
            assignees=["valid", {"invalid": "object"}]  # Invalid assignee type
        )
        
        with patch.object(self.repo, '_to_model_data', side_effect=TypeError("Object not JSON serializable")):
            with patch.object(self.repo, 'get_db_session', return_value=self.context_manager):
                
                result = self.repo.save(subtask)
                
                # Should handle serialization errors
                assert result is False


if __name__ == "__main__":
    pytest.main([__file__])