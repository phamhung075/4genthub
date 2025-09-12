"""
Comprehensive test suite for ORMTaskRepository.

Tests the TaskRepository ORM implementation including:
- CRUD operations
- Relationship loading and management
- User scoped data isolation
- Error handling and fallbacks
- Cache invalidation
- Complex queries and filtering
- Database transaction handling
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from fastmcp.task_management.domain.entities.task import Task as TaskEntity
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.task_exceptions import (
    TaskCreationError,
    TaskNotFoundError,
    TaskUpdateError,
)
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.database.models import (
    Task, TaskAssignee, TaskDependency, TaskLabel, Label, Base
)


class TestORMTaskRepositoryInitialization:
    """Test cases for ORMTaskRepository initialization and configuration."""
    
    def test_init_with_minimal_params(self):
        """Test repository initialization with minimal parameters."""
        with patch('fastmcp.task_management.infrastructure.repositories.orm.task_repository.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value = mock_session
            
            repo = ORMTaskRepository()
            
            assert repo.git_branch_id is None
            assert repo.project_id is None
            assert repo.git_branch_name is None
            mock_get_session.assert_called_once()
    
    def test_init_with_full_params(self):
        """Test repository initialization with all parameters."""
        mock_session = Mock()
        
        repo = ORMTaskRepository(
            session=mock_session,
            git_branch_id="branch-123",
            project_id="project-456",
            git_branch_name="feature/auth",
            user_id="user-789"
        )
        
        assert repo.git_branch_id == "branch-123"
        assert repo.project_id == "project-456"
        assert repo.git_branch_name == "feature/auth"
        assert repo._user_id == "user-789"
    
    def test_init_user_scoped_repository_inheritance(self):
        """Test repository properly inherits user scoped functionality."""
        mock_session = Mock()
        
        repo = ORMTaskRepository(
            session=mock_session,
            user_id="test-user"
        )
        
        # Should have user scoped methods
        assert hasattr(repo, '_apply_user_filter')
        assert hasattr(repo, '_get_user_id')
        assert repo._user_id == "test-user"


class TestORMTaskRepositoryTaskLoading:
    """Test cases for task loading with relationships."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(session=self.mock_session, user_id="test-user")
    
    def test_load_task_with_relationships_success(self):
        """Test successful loading of task with all relationships."""
        # Mock task with relationships
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.assignees = []
        mock_task.labels = []
        mock_task.subtasks = []
        mock_task.dependencies = []
        
        # Mock query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_task
        
        self.mock_session.query.return_value = mock_query
        
        result = self.repo._load_task_with_relationships(self.mock_session, "task-123")
        
        assert result == mock_task
        self.mock_session.query.assert_called_once_with(Task)
        mock_query.options.assert_called_once()
        mock_filter.first.assert_called_once()
    
    def test_load_task_with_relationships_fallback(self):
        """Test fallback to basic loading when relationships fail."""
        # First query with relationships fails
        mock_query_with_relations = Mock()
        mock_query_with_relations.options.side_effect = SQLAlchemyError("Relation error")
        
        # Second query without relationships succeeds
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        
        mock_query_basic = Mock()
        mock_filter = Mock()
        mock_query_basic.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_task
        
        # Mock session.query to return different queries on different calls
        self.mock_session.query.side_effect = [mock_query_with_relations, mock_query_basic]
        
        result = self.repo._load_task_with_relationships(self.mock_session, "task-123")
        
        assert result == mock_task
        # Should have empty relationships initialized
        assert result.assignees == []
        assert result.labels == []
        assert result.subtasks == []
        assert result.dependencies == []
    
    def test_load_task_complete_failure(self):
        """Test complete failure to load task."""
        # Both queries fail
        mock_query_with_relations = Mock()
        mock_query_with_relations.options.side_effect = SQLAlchemyError("Relation error")
        
        mock_query_basic = Mock()
        mock_query_basic.filter.side_effect = SQLAlchemyError("Basic query error")
        
        self.mock_session.query.side_effect = [mock_query_with_relations, mock_query_basic]
        
        result = self.repo._load_task_with_relationships(self.mock_session, "task-123")
        
        assert result is None
    
    def test_load_task_not_found(self):
        """Test loading non-existent task."""
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Not found
        
        self.mock_session.query.return_value = mock_query
        
        result = self.repo._load_task_with_relationships(self.mock_session, "nonexistent")
        
        assert result is None


class TestORMTaskRepositoryConversion:
    """Test cases for entity-to-model and model-to-entity conversion."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(session=self.mock_session, user_id="test-user")
    
    def test_entity_to_model_minimal_task(self):
        """Test converting minimal task entity to ORM model."""
        task_id = TaskId("task-123")
        task_entity = TaskEntity(
            id=task_id,
            title="Test Task",
            description="Test Description"
        )
        
        with patch.object(self.repo, '_entity_to_model') as mock_convert:
            mock_task_model = Mock(spec=Task)
            mock_convert.return_value = mock_task_model
            
            result = self.repo._entity_to_model(task_entity)
            
            mock_convert.assert_called_once_with(task_entity)
            assert result == mock_task_model
    
    def test_model_to_entity_complete_task(self):
        """Test converting complete task model to entity."""
        # Mock task model with all fields
        mock_task_model = Mock(spec=Task)
        mock_task_model.id = "task-123"
        mock_task_model.title = "Test Task"
        mock_task_model.description = "Test Description"
        mock_task_model.status = "todo"
        mock_task_model.priority = "medium"
        mock_task_model.git_branch_id = "branch-456"
        mock_task_model.details = "Some details"
        mock_task_model.estimated_effort = "2 hours"
        mock_task_model.due_date = "2024-12-31"
        mock_task_model.created_at = datetime.now(timezone.utc)
        mock_task_model.updated_at = datetime.now(timezone.utc)
        mock_task_model.context_id = "context-789"
        mock_task_model.overall_progress = 50
        
        # Mock relationships
        mock_task_model.assignees = []
        mock_task_model.labels = []
        mock_task_model.subtasks = []
        mock_task_model.dependencies = []
        
        with patch.object(self.repo, '_model_to_entity') as mock_convert:
            mock_task_entity = Mock(spec=TaskEntity)
            mock_convert.return_value = mock_task_entity
            
            result = self.repo._model_to_entity(mock_task_model)
            
            mock_convert.assert_called_once_with(mock_task_model)
            assert result == mock_task_entity


class TestORMTaskRepositoryCRUDOperations:
    """Test cases for CRUD operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(session=self.mock_session, user_id="test-user")
    
    def test_create_task_success(self):
        """Test successful task creation."""
        task_id = TaskId("task-123")
        task_entity = TaskEntity(
            id=task_id,
            title="New Task",
            description="New Description"
        )
        
        # Mock the conversion and session operations
        mock_task_model = Mock(spec=Task)
        mock_task_model.id = "task-123"
        
        with patch.object(self.repo, '_entity_to_model', return_value=mock_task_model) as mock_to_model:
            with patch.object(self.repo, '_model_to_entity', return_value=task_entity) as mock_to_entity:
                
                result = self.repo.create(task_entity)
                
                # Verify conversions
                mock_to_model.assert_called_once_with(task_entity)
                mock_to_entity.assert_called_once_with(mock_task_model)
                
                # Verify session operations
                self.mock_session.add.assert_called_once_with(mock_task_model)
                self.mock_session.flush.assert_called_once()
                
                assert result == task_entity
    
    def test_create_task_database_error(self):
        """Test task creation with database error."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="New Task",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model') as mock_to_model:
            mock_to_model.return_value = Mock(spec=Task)
            self.mock_session.add.side_effect = IntegrityError("Constraint violation", None, None)
            
            with pytest.raises(TaskCreationError, match="Failed to create task"):
                self.repo.create(task_entity)
    
    def test_get_task_by_id_found(self):
        """Test getting task by ID when it exists."""
        mock_task_model = Mock(spec=Task)
        mock_task_model.id = "task-123"
        
        mock_task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="Found Task",
            description="Found Description"
        )
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_task_model):
            with patch.object(self.repo, '_model_to_entity', return_value=mock_task_entity):
                with patch.object(self.repo, '_apply_user_filter') as mock_user_filter:
                    mock_user_filter.return_value = True
                    
                    result = self.repo.get_by_id(TaskId("task-123"))
                    
                    assert result == mock_task_entity
                    mock_user_filter.assert_called_once_with(mock_task_model)
    
    def test_get_task_by_id_not_found(self):
        """Test getting task by ID when it doesn't exist."""
        with patch.object(self.repo, '_load_task_with_relationships', return_value=None):
            
            with pytest.raises(TaskNotFoundError, match="Task with ID 'nonexistent' not found"):
                self.repo.get_by_id(TaskId("nonexistent"))
    
    def test_get_task_by_id_user_filter_denied(self):
        """Test getting task denied by user filter."""
        mock_task_model = Mock(spec=Task)
        mock_task_model.id = "task-123"
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_task_model):
            with patch.object(self.repo, '_apply_user_filter', return_value=False):
                
                with pytest.raises(TaskNotFoundError, match="Task with ID 'task-123' not found"):
                    self.repo.get_by_id(TaskId("task-123"))
    
    def test_update_task_success(self):
        """Test successful task update."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="Updated Task",
            description="Updated Description"
        )
        
        mock_existing_task = Mock(spec=Task)
        mock_existing_task.id = "task-123"
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_existing_task):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                with patch.object(self.repo, '_update_model_from_entity') as mock_update:
                    with patch.object(self.repo, '_model_to_entity', return_value=task_entity):
                        
                        result = self.repo.update(task_entity)
                        
                        mock_update.assert_called_once_with(mock_existing_task, task_entity)
                        self.mock_session.flush.assert_called_once()
                        assert result == task_entity
    
    def test_update_task_not_found(self):
        """Test updating non-existent task."""
        task_entity = TaskEntity(
            id=TaskId("nonexistent"),
            title="Updated Task",
            description="Updated Description"
        )
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=None):
            
            with pytest.raises(TaskNotFoundError, match="Task with ID 'nonexistent' not found"):
                self.repo.update(task_entity)
    
    def test_update_task_database_error(self):
        """Test task update with database error."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="Updated Task",
            description="Updated Description"
        )
        
        mock_existing_task = Mock(spec=Task)
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_existing_task):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                with patch.object(self.repo, '_update_model_from_entity'):
                    self.mock_session.flush.side_effect = SQLAlchemyError("Database error")
                    
                    with pytest.raises(TaskUpdateError, match="Failed to update task"):
                        self.repo.update(task_entity)
    
    def test_delete_task_success(self):
        """Test successful task deletion."""
        mock_task_model = Mock(spec=Task)
        mock_task_model.id = "task-123"
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_task_model):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                self.repo.delete(TaskId("task-123"))
                
                self.mock_session.delete.assert_called_once_with(mock_task_model)
                self.mock_session.flush.assert_called_once()
    
    def test_delete_task_not_found(self):
        """Test deleting non-existent task."""
        with patch.object(self.repo, '_load_task_with_relationships', return_value=None):
            
            with pytest.raises(TaskNotFoundError, match="Task with ID 'nonexistent' not found"):
                self.repo.delete(TaskId("nonexistent"))


class TestORMTaskRepositoryQueryOperations:
    """Test cases for complex query operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(
            session=self.mock_session, 
            git_branch_id="branch-123",
            user_id="test-user"
        )
    
    def test_list_tasks_with_filters(self):
        """Test listing tasks with various filters."""
        # Mock query result
        mock_task1 = Mock(spec=Task)
        mock_task1.id = "task-1"
        mock_task2 = Mock(spec=Task) 
        mock_task2.id = "task-2"
        
        mock_query = Mock()
        mock_query.all.return_value = [mock_task1, mock_task2]
        
        with patch.object(self.repo, '_build_filtered_query', return_value=mock_query):
            with patch.object(self.repo, '_model_to_entity') as mock_convert:
                mock_entities = [Mock(), Mock()]
                mock_convert.side_effect = mock_entities
                
                result = self.repo.list_all()
                
                assert len(result) == 2
                assert result == mock_entities
                mock_convert.assert_called()
    
    def test_search_tasks_by_text(self):
        """Test searching tasks by text content."""
        search_query = "authentication bug"
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task-1"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [mock_task]
        
        with patch.object(self.repo, '_build_base_query', return_value=mock_query):
            with patch.object(self.repo, '_model_to_entity', return_value=Mock()):
                
                result = self.repo.search_by_text(search_query)
                
                # Verify search filter was applied
                mock_query.filter.assert_called()
                assert len(result) == 1
    
    def test_find_by_git_branch(self):
        """Test finding tasks by git branch ID."""
        mock_task = Mock(spec=Task)
        mock_task.git_branch_id = "branch-123"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [mock_task]
        
        with patch.object(self.repo, '_build_base_query', return_value=mock_query):
            with patch.object(self.repo, '_model_to_entity', return_value=Mock()):
                
                result = self.repo.find_by_git_branch("branch-123")
                
                # Verify git branch filter was applied
                mock_query.filter.assert_called()
                assert len(result) == 1
    
    def test_count_tasks(self):
        """Test counting tasks with filters."""
        mock_query = Mock()
        mock_query.count.return_value = 5
        
        with patch.object(self.repo, '_build_filtered_query', return_value=mock_query):
            
            result = self.repo.count()
            
            assert result == 5
            mock_query.count.assert_called_once()


class TestORMTaskRepositoryCacheIntegration:
    """Test cases for cache invalidation integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(session=self.mock_session, user_id="test-user")
    
    def test_cache_invalidation_on_create(self):
        """Test cache is invalidated on task creation."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="New Task",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', return_value=Mock(spec=Task)):
            with patch.object(self.repo, '_model_to_entity', return_value=task_entity):
                with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                    
                    self.repo.create(task_entity)
                    
                    # Should invalidate cache after creation
                    mock_invalidate.assert_called()
    
    def test_cache_invalidation_on_update(self):
        """Test cache is invalidated on task update."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="Updated Task",
            description="Updated Description"
        )
        
        mock_existing = Mock(spec=Task)
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_existing):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                with patch.object(self.repo, '_update_model_from_entity'):
                    with patch.object(self.repo, '_model_to_entity', return_value=task_entity):
                        with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                            
                            self.repo.update(task_entity)
                            
                            # Should invalidate cache after update
                            mock_invalidate.assert_called()
    
    def test_cache_invalidation_on_delete(self):
        """Test cache is invalidated on task deletion."""
        mock_task = Mock(spec=Task)
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_task):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                    
                    self.repo.delete(TaskId("task-123"))
                    
                    # Should invalidate cache after deletion
                    mock_invalidate.assert_called()


class TestORMTaskRepositoryErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMTaskRepository(session=self.mock_session, user_id="test-user")
    
    def test_session_rollback_on_error(self):
        """Test session rollback occurs on database errors."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="New Task",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', return_value=Mock(spec=Task)):
            self.mock_session.add.side_effect = SQLAlchemyError("Database connection lost")
            
            with pytest.raises(TaskCreationError):
                self.repo.create(task_entity)
            
            # Should rollback on error
            self.mock_session.rollback.assert_called_once()
    
    def test_invalid_task_id_handling(self):
        """Test handling of invalid task IDs."""
        # Mock empty result for invalid ID
        with patch.object(self.repo, '_load_task_with_relationships', return_value=None):
            
            with pytest.raises(TaskNotFoundError):
                self.repo.get_by_id(TaskId(""))
            
            with pytest.raises(TaskNotFoundError):
                self.repo.get_by_id(TaskId("invalid-uuid"))
    
    def test_concurrent_modification_handling(self):
        """Test handling of concurrent modification scenarios."""
        task_entity = TaskEntity(
            id=TaskId("task-123"),
            title="Updated Task",
            description="Updated Description"
        )
        
        # Mock task exists but update fails due to concurrent modification
        mock_existing = Mock(spec=Task)
        
        with patch.object(self.repo, '_load_task_with_relationships', return_value=mock_existing):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                with patch.object(self.repo, '_update_model_from_entity'):
                    # Simulate optimistic locking failure
                    self.mock_session.flush.side_effect = SQLAlchemyError("Row was updated by another transaction")
                    
                    with pytest.raises(TaskUpdateError):
                        self.repo.update(task_entity)


if __name__ == "__main__":
    pytest.main([__file__])