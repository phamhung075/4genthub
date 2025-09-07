"""
Tests for Supabase Optimized Repository
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import uuid

from fastmcp.task_management.infrastructure.repositories.orm.supabase_optimized_repository import SupabaseOptimizedRepository
from fastmcp.task_management.infrastructure.database.models import Task
from fastmcp.task_management.domain.entities.task import Task as TaskEntity


class TestSupabaseOptimizedRepository:
    """Test the SupabaseOptimizedRepository class"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create a repository instance"""
        with patch('fastmcp.task_management.infrastructure.repositories.orm.supabase_optimized_repository.logger'):
            # Mock BaseORMRepository and BaseUserScopedRepository to avoid their initialization
            with patch('fastmcp.task_management.infrastructure.repositories.orm.task_repository.BaseORMRepository.__init__'):
                with patch('fastmcp.task_management.infrastructure.repositories.orm.task_repository.BaseUserScopedRepository.__init__'):
                    repo = SupabaseOptimizedRepository(git_branch_id="branch-123")
                    repo.get_db_session = Mock(return_value=mock_session)
                    return repo
    
    def test_list_tasks_minimal_basic(self, repository, mock_session):
        """Test list_tasks_minimal with basic parameters"""
        # Arrange
        mock_result = Mock()
        mock_result.id = "task-123"
        mock_result.title = "Test Task"
        mock_result.status = "todo"
        mock_result.priority = "high"
        mock_result.created_at = datetime.now(timezone.utc)
        mock_result.updated_at = datetime.now(timezone.utc)
        mock_result.subtask_count = 2
        mock_result.assignee_count = 1
        mock_result.dependency_count = 0
        
        mock_session.execute.return_value = [mock_result]
        
        # Act
        result = repository.list_tasks_minimal(limit=10, offset=0)
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "task-123"
        assert result[0]["title"] == "Test Task"
        assert result[0]["status"] == "todo"
        assert result[0]["priority"] == "high"
        assert result[0]["subtask_count"] == 2
        assert result[0]["assignee_count"] == 1
        assert result[0]["dependency_count"] == 0
        assert result[0]["has_relationships"] is True
        
        # Verify SQL query was executed
        mock_session.execute.assert_called_once()
        sql_query = mock_session.execute.call_args[0][0]
        params = mock_session.execute.call_args[0][1]
        
        assert "git_branch_id = :git_branch_id" in str(sql_query)
        assert params["git_branch_id"] == "branch-123"
        assert params["limit"] == 10
        assert params["offset"] == 0
    
    def test_list_tasks_minimal_with_filters(self, repository, mock_session):
        """Test list_tasks_minimal with all filters applied"""
        # Arrange
        mock_session.execute.return_value = []
        
        # Act
        result = repository.list_tasks_minimal(
            status="in_progress",
            priority="medium",
            assignee_id="user-456",
            limit=20,
            offset=10
        )
        
        # Assert
        assert result == []
        
        # Verify SQL query includes all filters
        sql_query = mock_session.execute.call_args[0][0]
        params = mock_session.execute.call_args[0][1]
        
        assert "status = :status" in str(sql_query)
        assert "priority = :priority" in str(sql_query)
        assert "EXISTS (SELECT 1 FROM task_assignees" in str(sql_query)
        assert params["status"] == "in_progress"
        assert params["priority"] == "medium"
        assert params["assignee_id"] == "user-456"
        assert params["limit"] == 20
        assert params["offset"] == 10
    
    def test_list_tasks_minimal_handles_none_parameters(self, repository, mock_session):
        """Test list_tasks_minimal handles None parameters correctly"""
        # Arrange
        mock_session.execute.return_value = []
        
        # Act
        result = repository.list_tasks_minimal(
            status=None,
            priority=None,
            assignee_id=None,
            limit=None,
            offset=None
        )
        
        # Assert
        assert result == []
        
        # Verify defaults were used
        params = mock_session.execute.call_args[0][1]
        assert params["limit"] == 20  # Default
        assert params["offset"] == 0  # Default
        assert "status" not in params
        assert "priority" not in params
        assert "assignee_id" not in params
    
    def test_list_tasks_minimal_validates_parameters(self, repository, mock_session):
        """Test list_tasks_minimal validates input parameters"""
        # Arrange
        mock_session.execute.return_value = []
        
        # Act
        result = repository.list_tasks_minimal(
            status=123,  # Invalid type
            priority=None,
            limit=-10,  # Invalid value
            offset=-5  # Invalid value
        )
        
        # Assert
        params = mock_session.execute.call_args[0][1]
        assert params["limit"] == 20  # Reset to default
        assert params["offset"] == 0  # Reset to default
        assert "status" not in params  # Invalid type ignored
    
    def test_list_tasks_minimal_caps_large_limit(self, repository, mock_session):
        """Test list_tasks_minimal caps excessively large limit"""
        # Arrange
        mock_session.execute.return_value = []
        
        # Act
        result = repository.list_tasks_minimal(limit=5000)
        
        # Assert
        params = mock_session.execute.call_args[0][1]
        assert params["limit"] == 1000  # Capped at 1000
    
    def test_list_tasks_no_relations(self, repository, mock_session):
        """Test list_tasks_no_relations returns entities without relationships"""
        # Arrange
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_task.description = "Test description"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.git_branch_id = "branch-123"
        mock_task.context_id = None
        mock_task.details = None
        mock_task.estimated_effort = None
        mock_task.due_date = None
        
        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_task]
        
        mock_session.query.return_value = mock_query
        
        # Act
        result = repository.list_tasks_no_relations(status="todo", limit=10)
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TaskEntity)
        assert result[0].id == "task-123"
        assert result[0].title == "Test Task"
        assert result[0].assignees == []  # Empty
        assert result[0].labels == []  # Empty
        assert result[0].subtasks == []  # Empty
        assert result[0].dependencies == []  # Empty
        
        # Verify noload was used
        mock_query.options.assert_called_once()
    
    def test_list_tasks_no_relations_applies_filters(self, repository, mock_session):
        """Test list_tasks_no_relations applies all filters"""
        # Arrange
        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_session.query.return_value = mock_query
        
        # Act
        repository.list_tasks_no_relations(
            status="in_progress",
            priority="low",
            assignee_id="user-789",
            limit=5,
            offset=20
        )
        
        # Assert
        # Verify filter was called
        mock_query.filter.assert_called()
        # Verify pagination
        mock_query.offset.assert_called_once_with(20)
        mock_query.limit.assert_called_once_with(5)
    
    def test_get_task_with_counts_valid_uuid(self, repository, mock_session):
        """Test get_task_with_counts with valid task ID"""
        # Arrange
        task_id = str(uuid.uuid4())
        
        mock_result = Mock()
        mock_result.id = task_id
        mock_result.title = "Test Task"
        mock_result.description = "Description"
        mock_result.status = "todo"
        mock_result.priority = "high"
        mock_result.created_at = datetime.now(timezone.utc)
        mock_result.updated_at = datetime.now(timezone.utc)
        mock_result.subtask_count = 3
        mock_result.assignee_count = 2
        mock_result.dependency_count = 1
        mock_result.label_count = 4
        mock_result.git_branch_id = "branch-123"
        mock_result.context_id = None
        mock_result.details = "Details"
        mock_result.estimated_effort = "2 hours"
        mock_result.due_date = None
        
        mock_execute_result = Mock()
        mock_execute_result.first.return_value = mock_result
        mock_session.execute.return_value = mock_execute_result
        
        # Act
        result = repository.get_task_with_counts(task_id)
        
        # Assert
        assert result is not None
        assert result["id"] == task_id
        assert result["title"] == "Test Task"
        assert result["subtask_count"] == 3
        assert result["assignee_count"] == 2
        assert result["dependency_count"] == 1
        assert result["label_count"] == 4
        assert result["details"] == "Details"
        assert result["estimated_effort"] == "2 hours"
    
    def test_get_task_with_counts_invalid_uuid(self, repository, mock_session):
        """Test get_task_with_counts with invalid UUID"""
        # Act
        result = repository.get_task_with_counts("not-a-uuid")
        
        # Assert
        assert result is None
        mock_session.execute.assert_not_called()
    
    def test_get_task_with_counts_not_found(self, repository, mock_session):
        """Test get_task_with_counts when task not found"""
        # Arrange
        task_id = str(uuid.uuid4())
        
        mock_execute_result = Mock()
        mock_execute_result.first.return_value = None
        mock_session.execute.return_value = mock_execute_result
        
        # Act
        result = repository.get_task_with_counts(task_id)
        
        # Assert
        assert result is None
    
    def test_get_task_with_counts_handles_null_dates(self, repository, mock_session):
        """Test get_task_with_counts handles null date values"""
        # Arrange
        task_id = str(uuid.uuid4())
        
        mock_result = Mock()
        mock_result.id = task_id
        mock_result.title = "Test Task"
        mock_result.description = "Description"
        mock_result.status = "todo"
        mock_result.priority = "high"
        mock_result.created_at = None  # Null date
        mock_result.updated_at = None  # Null date
        mock_result.due_date = None  # Null date
        mock_result.subtask_count = 0
        mock_result.assignee_count = 0
        mock_result.dependency_count = 0
        mock_result.label_count = 0
        mock_result.git_branch_id = "branch-123"
        mock_result.context_id = None
        mock_result.details = None
        mock_result.estimated_effort = None
        
        mock_execute_result = Mock()
        mock_execute_result.first.return_value = mock_result
        mock_session.execute.return_value = mock_execute_result
        
        # Act
        result = repository.get_task_with_counts(task_id)
        
        # Assert
        assert result is not None
        assert result["created_at"] is None
        assert result["updated_at"] is None
        assert result["due_date"] is None
    
    def test_model_to_entity_minimal(self, repository):
        """Test _model_to_entity_minimal conversion"""
        # Arrange
        mock_task = Mock(spec=Task)
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_task.description = "Description"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.git_branch_id = "branch-123"
        mock_task.context_id = "context-123"
        mock_task.details = "Details"
        mock_task.estimated_effort = "1 day"
        mock_task.due_date = datetime.now(timezone.utc)
        
        # Act
        entity = repository._model_to_entity_minimal(mock_task)
        
        # Assert
        assert isinstance(entity, TaskEntity)
        assert entity.id == "task-123"
        assert entity.title == "Test Task"
        assert entity.description == "Description"
        assert entity.status == "todo"
        assert entity.priority == "high"
        assert entity.assignees == []  # Empty
        assert entity.labels == []  # Empty
        assert entity.subtasks == []  # Empty
        assert entity.dependencies == []  # Empty
        assert entity.git_branch_id == "branch-123"
        assert entity.context_id == "context-123"
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.supabase_optimized_repository.logger')
    def test_repository_initialization(self, mock_logger):
        """Test repository initialization with git_branch_id"""
        # Arrange & Act
        # Patch entire inheritance chain to avoid complexity
        with patch('fastmcp.task_management.infrastructure.repositories.orm.supabase_optimized_repository.ORMTaskRepository'):
            # Create repository instance
            repo = SupabaseOptimizedRepository(git_branch_id="test-branch-456")
            
            # Since we're mocking the parent, we need to manually set the attribute
            # that would have been set by the parent
            repo.git_branch_id = "test-branch-456"
            
            # Assert - Check that logger was called with expected message
            mock_logger.info.assert_called_once_with(
                "Using Supabase-optimized repository for minimal latency, git_branch_id: test-branch-456"
            )