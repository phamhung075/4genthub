"""
Unit tests for ORM Label Repository

This module contains comprehensive tests for the ORMLabelRepository class,
covering all CRUD operations and label-task relationships.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fastmcp.task_management.infrastructure.repositories.orm.label_repository import ORMLabelRepository
from fastmcp.task_management.infrastructure.database.models import Label, TaskLabel, Task
from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
from fastmcp.task_management.domain.entities.label import Label as LabelEntity
from fastmcp.task_management.domain.entities.task import Task as TaskEntity
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    RepositoryError,
    NotFoundError,
    ValidationError
)


class TestORMLabelRepository:
    
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

    """Test cases for ORMLabelRepository"""
    
    @pytest.fixture
    def mock_db_adapter(self):
        """Create mock database adapter"""
        mock_adapter = Mock(spec=DatabaseAdapter)
        mock_session = Mock(spec=Session)
        
        # Create a proper context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        
        # Make get_session return the context manager
        mock_adapter.get_session.return_value = mock_context_manager
        
        return mock_adapter, mock_session
    
    @pytest.fixture
    def label_repository(self, mock_db_adapter):
        """Create label repository with mock adapter"""
        mock_adapter, _ = mock_db_adapter
        return ORMLabelRepository(mock_adapter)
    
    @pytest.fixture
    def sample_label_model(self):
        """Create sample label model"""
        return Label(
            id=1,
            name="bug",
            color="#ff0000",
            description="Bug reports",
            created_at=datetime(2025, 1, 1, 12, 0, 0)
        )
    
    @pytest.fixture
    def sample_task_model(self):
        """Create sample task model"""
        return Task(
            id="12345678-1234-1234-1234-123456789abc",
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            status="todo",
            priority="medium",
            details="",
            estimated_effort="",
            due_date=None,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            context_id=None
        )
    
    def test_create_label_success(self, label_repository, mock_db_adapter):
        """Test successful label creation"""
        _, mock_session = mock_db_adapter
        
        # Mock no existing label
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock label creation
        mock_label = Mock()
        mock_label.id = 1
        mock_label.name = "bug"
        mock_label.color = "#ff0000"
        mock_label.description = "Bug reports"
        mock_label.created_at = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        # Mock the label after refresh
        mock_session.add.side_effect = lambda label: setattr(label, 'id', 1)
        
        result = label_repository.create_label("bug", "#ff0000", "Bug reports")
        
        # Verify result
        assert isinstance(result, LabelEntity)
        assert result.name == "bug"
        assert result.color == "#ff0000"
        assert result.description == "Bug reports"
        
        # Verify database interactions
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    def test_create_label_duplicate_name(self, label_repository, mock_db_adapter):
        """Test creating label with duplicate name"""
        _, mock_session = mock_db_adapter
        
        # Mock existing label
        existing_label = Mock()
        existing_label.name = "bug"
        mock_session.query.return_value.filter.return_value.first.return_value = existing_label
        
        with pytest.raises(ValidationError, match="Label with name 'bug' already exists"):
            label_repository.create_label("bug")
    
    def test_create_label_database_error(self, label_repository, mock_db_adapter):
        """Test label creation with database error"""
        _, mock_session = mock_db_adapter
        
        # Mock no existing label
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock database error
        mock_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(RepositoryError, match="Failed to create label"):
            label_repository.create_label("bug")
    
    def test_get_label_success(self, label_repository, mock_db_adapter, sample_label_model):
        """Test successful label retrieval"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = sample_label_model
        
        result = label_repository.get_label(1)
        
        assert isinstance(result, LabelEntity)
        assert result.id == 1
        assert result.name == "bug"
        assert result.color == "#ff0000"
        assert result.description == "Bug reports"
    
    def test_get_label_not_found(self, label_repository, mock_db_adapter):
        """Test getting non-existent label"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = label_repository.get_label(999)
        
        assert result is None
    
    def test_get_label_by_name_success(self, label_repository, mock_db_adapter, sample_label_model):
        """Test successful label retrieval by name"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = sample_label_model
        
        result = label_repository.get_label_by_name("bug")
        
        assert isinstance(result, LabelEntity)
        assert result.name == "bug"
    
    def test_get_label_by_name_not_found(self, label_repository, mock_db_adapter):
        """Test getting non-existent label by name"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = label_repository.get_label_by_name("nonexistent")
        
        assert result is None
    
    def test_update_label_success(self, label_repository, mock_db_adapter, sample_label_model):
        """Test successful label update"""
        _, mock_session = mock_db_adapter
        
        # Mock finding the label
        mock_session.query.return_value.filter.return_value.first.return_value = sample_label_model
        
        # Mock no duplicate name check
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            sample_label_model,  # First call for finding the label
            None  # Second call for duplicate name check
        ]
        
        result = label_repository.update_label(1, name="critical-bug", color="#ff4444")
        
        assert isinstance(result, LabelEntity)
        assert sample_label_model.name == "critical-bug"
        assert sample_label_model.color == "#ff4444"
        
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    def test_update_label_not_found(self, label_repository, mock_db_adapter):
        """Test updating non-existent label"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(NotFoundError, match="Label with id '999' not found"):
            label_repository.update_label(999, name="new-name")
    
    def test_update_label_duplicate_name(self, label_repository, mock_db_adapter, sample_label_model):
        """Test updating label with duplicate name"""
        _, mock_session = mock_db_adapter
        
        # Mock finding the label and duplicate name
        existing_label = Mock()
        existing_label.name = "duplicate"
        
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            sample_label_model,  # First call for finding the label
            existing_label  # Second call for duplicate name check
        ]
        
        with pytest.raises(ValidationError, match="Label with name 'duplicate' already exists"):
            label_repository.update_label(1, name="duplicate")
    
    def test_delete_label_success(self, label_repository, mock_db_adapter, sample_label_model):
        """Test successful label deletion"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = sample_label_model
        
        result = label_repository.delete_label(1)
        
        assert result is True
        mock_session.delete.assert_called_once_with(sample_label_model)
        mock_session.commit.assert_called_once()
    
    def test_delete_label_not_found(self, label_repository, mock_db_adapter):
        """Test deleting non-existent label"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = label_repository.delete_label(999)
        
        assert result is False
        mock_session.delete.assert_not_called()
    
    def test_list_labels_success(self, label_repository, mock_db_adapter, sample_label_model):
        """Test successful label listing"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.order_by.return_value.all.return_value = [sample_label_model]
        
        result = label_repository.list_labels()
        
        assert len(result) == 1
        assert isinstance(result[0], LabelEntity)
        assert result[0].name == "bug"
    
    def test_list_labels_with_pagination(self, label_repository, mock_db_adapter, sample_label_model):
        """Test label listing with pagination"""
        _, mock_session = mock_db_adapter
        
        mock_query = Mock()
        mock_session.query.return_value.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_label_model]
        
        result = label_repository.list_labels(limit=10, offset=5)
        
        assert len(result) == 1
        mock_query.offset.assert_called_once_with(5)
        mock_query.limit.assert_called_once_with(10)
    
    def test_assign_label_to_task_success(self, label_repository, mock_db_adapter, sample_task_model, sample_label_model):
        """Test successful label assignment to task"""
        _, mock_session = mock_db_adapter
        
        # Mock finding task and label
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            sample_task_model,  # Task exists
            sample_label_model,  # Label exists
            None  # No existing assignment
        ]
        
        result = label_repository.assign_label_to_task("12345678-1234-1234-1234-123456789abc", 1)
        
        assert result is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_assign_label_to_task_already_assigned(self, label_repository, mock_db_adapter, sample_task_model, sample_label_model):
        """Test assigning label to task that already has it"""
        _, mock_session = mock_db_adapter
        
        existing_assignment = Mock()
        
        # Mock finding task, label, and existing assignment
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            sample_task_model,  # Task exists
            sample_label_model,  # Label exists
            existing_assignment  # Existing assignment
        ]
        
        result = label_repository.assign_label_to_task("12345678-1234-1234-1234-123456789abc", 1)
        
        assert result is False
        mock_session.add.assert_not_called()
    
    def test_assign_label_to_task_task_not_found(self, label_repository, mock_db_adapter):
        """Test assigning label to non-existent task"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        task_id = "12345678-1234-1234-1234-123456789abc"
        with pytest.raises(NotFoundError, match=f"Task with id '{task_id}' not found"):
            label_repository.assign_label_to_task(task_id, 1)
    
    def test_assign_label_to_task_label_not_found(self, label_repository, mock_db_adapter, sample_task_model):
        """Test assigning non-existent label to task"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            sample_task_model,  # Task exists
            None  # Label doesn't exist
        ]
        
        with pytest.raises(NotFoundError, match="Label with id '999' not found"):
            label_repository.assign_label_to_task("12345678-1234-1234-1234-123456789abc", 999)
    
    def test_remove_label_from_task_success(self, label_repository, mock_db_adapter):
        """Test successful label removal from task"""
        _, mock_session = mock_db_adapter
        
        task_label = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = task_label
        
        result = label_repository.remove_label_from_task("12345678-1234-1234-1234-123456789abc", 1)
        
        assert result is True
        mock_session.delete.assert_called_once_with(task_label)
        mock_session.commit.assert_called_once()
    
    def test_remove_label_from_task_not_assigned(self, label_repository, mock_db_adapter):
        """Test removing label from task that doesn't have it"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = label_repository.remove_label_from_task("12345678-1234-1234-1234-123456789abc", 1)
        
        assert result is False
        mock_session.delete.assert_not_called()
    
    def test_get_tasks_by_label_success(self, label_repository, mock_db_adapter, sample_label_model, sample_task_model):
        """Test getting tasks by label"""
        _, mock_session = mock_db_adapter
        
        # Mock finding label and tasks
        mock_session.query.return_value.filter.return_value.first.return_value = sample_label_model
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [sample_task_model]
        
        result = label_repository.get_tasks_by_label(1)
        
        assert len(result) == 1
        assert isinstance(result[0], TaskEntity)
        assert result[0].id == "12345678-1234-1234-1234-123456789abc"
        assert result[0].title == "Test Task"
    
    def test_get_tasks_by_label_not_found(self, label_repository, mock_db_adapter):
        """Test getting tasks by non-existent label"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(NotFoundError, match="Label with id '999' not found"):
            label_repository.get_tasks_by_label(999)
    
    def test_get_labels_by_task_success(self, label_repository, mock_db_adapter, sample_task_model, sample_label_model):
        """Test getting labels by task"""
        _, mock_session = mock_db_adapter
        
        # Mock finding task and labels
        mock_session.query.return_value.filter.return_value.first.return_value = sample_task_model
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [sample_label_model]
        
        result = label_repository.get_labels_by_task("12345678-1234-1234-1234-123456789abc")
        
        assert len(result) == 1
        assert isinstance(result[0], LabelEntity)
        assert result[0].id == 1
        assert result[0].name == "bug"
    
    def test_get_labels_by_task_not_found(self, label_repository, mock_db_adapter):
        """Test getting labels by non-existent task"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        task_id = "12345678-1234-1234-1234-123456789abc"
        with pytest.raises(NotFoundError, match=f"Task with id '{task_id}' not found"):
            label_repository.get_labels_by_task(task_id)
    
    def test_database_error_handling(self, label_repository, mock_db_adapter):
        """Test general database error handling"""
        _, mock_session = mock_db_adapter
        
        mock_session.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(RepositoryError, match="Failed to get label"):
            label_repository.get_label(1)
    
    def test_model_to_entity_conversion(self, label_repository, sample_label_model):
        """Test model to entity conversion"""
        entity = label_repository._model_to_entity(sample_label_model)
        
        assert isinstance(entity, LabelEntity)
        assert entity.id == sample_label_model.id
        assert entity.name == sample_label_model.name
        assert entity.color == sample_label_model.color
        assert entity.description == sample_label_model.description
        assert entity.created_at == sample_label_model.created_at
    
    def test_task_model_to_entity_conversion(self, label_repository, sample_task_model):
        """Test task model to entity conversion"""
        entity = label_repository._task_model_to_entity(sample_task_model)
        
        assert isinstance(entity, TaskEntity)
        assert entity.id == sample_task_model.id
        assert entity.title == sample_task_model.title
        assert entity.description == sample_task_model.description
        assert entity.git_branch_id == sample_task_model.git_branch_id
        assert entity.status == sample_task_model.status
        assert entity.priority == sample_task_model.priority


if __name__ == "__main__":
    pytest.main([__file__])