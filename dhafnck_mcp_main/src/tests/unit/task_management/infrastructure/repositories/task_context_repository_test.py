"""Test suite for TaskContextRepository - Corrected Interface

Tests the task context repository with correct interface that matches 
the actual repository implementation using TaskContext entities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from contextlib import contextmanager
import uuid

from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
from fastmcp.task_management.domain.entities.context import TaskContextUnified as TaskContext
from fastmcp.task_management.infrastructure.database.models import TaskContext as TaskContextModel
from sqlalchemy.exc import SQLAlchemyError


class TestTaskContextRepository:
    """Test cases for TaskContextRepository - Core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock session factory
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Setup session methods
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.refresh = Mock()
        self.mock_session.get = Mock()
        self.mock_session.query = Mock()
        
        # Create repository instance
        self.repository = TaskContextRepository(self.mock_session_factory)
        
        # Test data
        self.test_context_id = str(uuid.uuid4())
        self.test_branch_id = str(uuid.uuid4())
        
        self.test_entity = TaskContext(
            id=self.test_context_id,
            branch_id=self.test_branch_id,
            task_data={'title': 'Test Task', 'status': 'in_progress'},
            progress=75,
            insights=['Test insight'],
            next_steps=['Test step'],
            metadata={'user_id': 'test-user'}
        )
    
    def test_init(self):
        """Test repository initialization."""
        assert self.repository.session_factory == self.mock_session_factory
        assert self.repository.model_class == TaskContextModel

    def test_with_user_creates_new_instance(self):
        """Test with_user creates new repository instance with user scoping"""
        new_user_id = "new-user-456"
        scoped_repo = self.repository.with_user(new_user_id)
        
        assert isinstance(scoped_repo, TaskContextRepository)
        assert scoped_repo.user_id == new_user_id
        assert scoped_repo.session_factory == self.mock_session_factory

    def test_create_success(self):
        """Test successful task context creation."""
        # Mock that no existing context exists
        self.mock_session.get.return_value = None
        
        mock_model = Mock(spec=TaskContextModel)
        mock_model.id = self.test_context_id
        
        with patch('fastmcp.task_management.infrastructure.repositories.task_context_repository.TaskContextModel') as MockModel:
            MockModel.return_value = mock_model
            
            # Mock the _to_entity method
            with patch.object(self.repository, '_to_entity', return_value=self.test_entity):
                result = self.repository.create(self.test_entity)
                
                # Assert model was created with correct data
                MockModel.assert_called_once()
                self.mock_session.add.assert_called_once_with(mock_model)
                self.mock_session.flush.assert_called_once()
                assert result == self.test_entity

    def test_create_already_exists(self):
        """Test creating when task context already exists."""
        # Mock existing context
        existing_model = Mock(spec=TaskContextModel)
        self.mock_session.get.return_value = existing_model
        
        with pytest.raises(ValueError) as exc_info:
            self.repository.create(self.test_entity)
        
        assert "already exists" in str(exc_info.value)

    def test_get_success(self):
        """Test successful task context retrieval."""
        mock_model = Mock(spec=TaskContextModel)
        mock_model.id = self.test_context_id
        
        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_model
        self.mock_session.query.return_value = mock_query
        
        # Mock _to_entity conversion
        with patch.object(self.repository, '_to_entity', return_value=self.test_entity):
            result = self.repository.get(self.test_context_id)
            
            assert result == self.test_entity
            self.mock_session.query.assert_called_once_with(TaskContextModel)

    def test_get_not_found(self):
        """Test get when context doesn't exist."""
        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter.return_value = mock_query  
        mock_query.first.return_value = None
        self.mock_session.query.return_value = mock_query
        
        result = self.repository.get(self.test_context_id)
        assert result is None

    def test_update_success(self):
        """Test successful task context update."""
        mock_model = Mock(spec=TaskContextModel)
        # Set up mock attributes that will be modified
        mock_model.version = 1  # Set initial version as integer, not Mock
        mock_model.user_id = "test-user"
        self.mock_session.get.return_value = mock_model
        
        updated_entity = TaskContext(
            id=self.test_context_id,
            branch_id=self.test_branch_id,
            task_data={'title': 'Updated Task', 'status': 'completed'},
            progress=100,
            insights=['Updated insight'],
            next_steps=['Updated step'],
            metadata={'user_id': 'test-user'}
        )
        
        # Mock _to_entity conversion
        with patch.object(self.repository, '_to_entity', return_value=updated_entity):
            result = self.repository.update(self.test_context_id, updated_entity)
            
            assert result == updated_entity
            # Verify version was incremented
            assert mock_model.version == 2
            # Verify model attributes were updated
            expected_task_data = updated_entity.task_data.copy()
            expected_task_data.update({
                'progress': updated_entity.progress,
                'insights': updated_entity.insights,
                'next_steps': updated_entity.next_steps
            })
            assert mock_model.task_data == expected_task_data

    def test_update_not_found(self):
        """Test update when context doesn't exist."""
        self.mock_session.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            self.repository.update(self.test_context_id, self.test_entity)
        
        assert "not found" in str(exc_info.value)

    def test_delete_success(self):
        """Test successful task context deletion."""
        mock_model = Mock(spec=TaskContextModel)
        self.mock_session.get.return_value = mock_model
        
        result = self.repository.delete(self.test_context_id)
        
        assert result is True
        self.mock_session.delete.assert_called_once_with(mock_model)

    def test_delete_not_found(self):
        """Test delete when context doesn't exist."""
        self.mock_session.get.return_value = None
        
        result = self.repository.delete(self.test_context_id)
        assert result is False


class TestTaskContextRepositoryErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        self.repository = TaskContextRepository(self.mock_session_factory)
        
        self.test_entity = TaskContext(
            id=str(uuid.uuid4()),
            branch_id=str(uuid.uuid4()),
            task_data={'title': 'Test'},
            progress=0,
            insights=[],
            next_steps=[],
            metadata={}
        )

    def test_session_rollback_on_error(self):
        """Test proper session rollback on database errors."""
        # Mock session that will fail on add
        mock_session = Mock()
        mock_session.get.return_value = None  # No existing record
        mock_session.add.side_effect = SQLAlchemyError("Database error")
        mock_session.rollback = Mock()
        mock_session.close = Mock()
        
        # Create proper context manager mock
        @contextmanager
        def mock_session_context():
            try:
                yield mock_session
                mock_session.commit()
            except SQLAlchemyError:
                mock_session.rollback()
                raise
            finally:
                mock_session.close()
        
        # Mock the get_db_session context manager
        with patch.object(self.repository, 'get_db_session', side_effect=mock_session_context):
            # Act & Assert
            with pytest.raises(SQLAlchemyError):
                self.repository.create(self.test_entity)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()

    def test_user_scoped_operations(self):
        """Test user scoping is applied in operations."""
        user_repo = self.repository.with_user("test-user")
        
        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        self.mock_session.query.return_value = mock_query
        
        # Test that user scoping is applied in get operation
        user_repo.get("test-id")
        
        # Verify that query and filters were called
        self.mock_session.query.assert_called_once()
        # The implementation should add user filter when user_id is set
        assert mock_query.filter.call_count >= 1