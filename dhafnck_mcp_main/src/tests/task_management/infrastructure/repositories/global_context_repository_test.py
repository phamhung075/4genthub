"""Tests for GlobalContextRepository"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid

from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
from fastmcp.task_management.domain.entities.context import GlobalContext
from fastmcp.task_management.infrastructure.database.models import GlobalContext as GlobalContextModel


class TestGlobalContextRepository:
    """Test suite for GlobalContextRepository"""
    
    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory"""
        session_factory = Mock()
        mock_session = Mock(spec=Session)
        session_factory.return_value = mock_session
        return session_factory
    
    @pytest.fixture
    def mock_session(self, mock_session_factory):
        """Get mock session from factory"""
        return mock_session_factory.return_value
    
    @pytest.fixture
    def repository(self, mock_session_factory):
        """Create repository instance"""
        # Reset call count after repository creation
        repo = GlobalContextRepository(mock_session_factory, user_id="test-user")
        mock_session_factory.reset_mock()
        return repo
    
    def test_initialization_with_user_id(self, mock_session_factory):
        """Test repository initialization with user ID"""
        user_id = "test-user-123"
        repo = GlobalContextRepository(mock_session_factory, user_id=user_id)
        
        assert repo.user_id == user_id
        assert repo.session_factory == mock_session_factory
        assert repo.model_class == GlobalContextModel
        mock_session_factory.assert_called_once()
    
    def test_initialization_without_user_id(self, mock_session_factory):
        """Test repository initialization without user ID (system mode)"""
        repo = GlobalContextRepository(mock_session_factory)
        
        assert repo.user_id is None
        assert repo.session_factory == mock_session_factory
        assert repo.model_class == GlobalContextModel
    
    def test_get_db_session_with_existing_session(self, repository):
        """Test get_db_session when _session exists"""
        mock_session = Mock()
        repository._session = mock_session
        
        with repository.get_db_session() as session:
            assert session == mock_session
            
        # Should not create new session
        repository.session_factory.assert_not_called()
    
    def test_get_db_session_creates_new_session(self, repository, mock_session):
        """Test get_db_session creates new session when needed"""
        repository._session = None
        
        with repository.get_db_session() as session:
            assert session == mock_session
            
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    def test_get_db_session_handles_error(self, repository, mock_session):
        """Test get_db_session handles SQLAlchemy errors"""
        repository._session = None
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            with repository.get_db_session() as session:
                pass
                
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    
    def test_create_global_context_success(self, repository, mock_session):
        """Test successful global context creation"""
        # Create entity
        entity = GlobalContext(
            id="global-123",
            organization_name="test-org",
            global_settings={
                "organization_standards": {"rule1": "value1"},
                "security_policies": {"policy1": "value1"}
            }
        )

        # Mock database query (no existing context)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock required methods
        repository.log_access = Mock()
        repository.invalidate_cache_for_entity = Mock()
        repository._to_entity = Mock(return_value=entity)

        result = repository.create(entity)

        # Verify session operations were called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Basic verification that a model was created
        assert mock_session.add.call_args[0][0] is not None
        created_model = mock_session.add.call_args[0][0]
        assert hasattr(created_model, 'id')
        assert hasattr(created_model, 'user_id')

        # Verify log_access was called
        repository.log_access.assert_called_once_with("create", "global_context", "global-123")
    
    def test_create_global_context_already_exists(self, repository, mock_session):
        """Test create fails when global context already exists for user"""
        entity = GlobalContext(id="global-123", organization_name="test-org")
        
        # Mock existing context
        existing_model = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_model
        
        with pytest.raises(ValueError) as exc_info:
            repository.create(entity)
            
        assert "Global context already exists" in str(exc_info.value)
    
    def test_create_global_context_without_user_id(self, mock_session_factory):
        """Test create behavior without user_id raises error"""
        repo = GlobalContextRepository(mock_session_factory)
        entity = GlobalContext(id="global-123", organization_name="test-org")

        mock_session = mock_session_factory.return_value
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Should raise ValueError requiring user_id
        with pytest.raises(ValueError, match="user_id is required"):
            repo.create(entity)
    
    def test_get_global_context_found(self, repository, mock_session):
        """Test get retrieves global context successfully"""
        # Mock database model
        mock_model = Mock(
            id="global-123",
            user_id="test-user",
            autonomous_rules={"rule1": "value1"},
            security_policies={},
            coding_standards={},
            workflow_templates={"_custom": {"field": "value"}},
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Mock apply_user_filter
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = mock_model
        
        # Mock log_access
        repository.log_access = Mock()
        
        result = repository.get("global-123")
        
        assert result is not None
        assert isinstance(result, GlobalContext)
        assert result.id == "global-123"
        
        # Verify user filter was applied
        repository.apply_user_filter.assert_called_once()
        repository.log_access.assert_called_once_with("read", "global_context", "global-123")
    
    def test_get_global_context_not_found(self, repository, mock_session):
        """Test get returns None when context not found"""
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = None
        
        result = repository.get("nonexistent-123")
        
        assert result is None
    
    def test_to_entity_conversion(self, repository):
        """Test _to_entity converts database model to domain entity"""
        mock_model = Mock(
            id="global-123",
            autonomous_rules={"rule1": "value1"},
            security_policies={"policy1": "value1"},
            coding_standards={},
            workflow_templates={"_custom": {"custom_field": "custom_value"}},
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = repository._to_entity(mock_model)
        
        assert isinstance(result, GlobalContext)
        assert result.id == "global-123"
        assert result.global_settings["autonomous_rules"] == {"rule1": "value1"}
        assert result.global_settings["security_policies"] == {"policy1": "value1"}
        assert result.global_settings["custom_field"] == "custom_value"
    
    def test_to_entity_without_custom_fields(self, repository):
        """Test _to_entity handles models without custom fields"""
        mock_model = Mock(
            id="global-123",
            autonomous_rules={"rule1": "value1"},
            security_policies={},
            coding_standards={},
            workflow_templates={},  # No _custom
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = repository._to_entity(mock_model)
        
        assert isinstance(result, GlobalContext)
        assert result.global_settings["autonomous_rules"] == {"rule1": "value1"}
        assert "custom_field" not in result.global_settings
    
    def test_update_global_context_success(self, repository, mock_session):
        """Test successful global context update"""
        # Create update entity
        entity = GlobalContext(
            id="global-123",
            organization_name="test-org",
            global_settings={
                "organization_standards": {"updated_rule": "new_value"},
                "new_custom": "new_custom_value"
            }
        )

        # Store original time for comparison
        original_time = datetime.now(timezone.utc)

        # Mock existing model with proper attributes
        existing_model = Mock()
        existing_model.id = "global-123"
        existing_model.user_id = "test-user"
        existing_model.organization_standards = {"old_rule": "old_value"}
        existing_model.security_policies = {}
        existing_model.compliance_requirements = {}
        existing_model.shared_resources = {}
        existing_model.reusable_patterns = {}
        existing_model.global_preferences = {}
        existing_model.delegation_rules = {}
        existing_model.nested_structure = {}
        existing_model.updated_at = original_time

        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        repository.ensure_user_ownership = Mock()
        repository.log_access = Mock()
        repository.invalidate_cache_for_entity = Mock()
        repository._to_entity = Mock(return_value=entity)
        mock_query.first.return_value = existing_model

        result = repository.update("global-123", entity)

        # Verify database operations were called
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
        repository.log_access.assert_called_with("update", "global_context", "global-123")

        # Check that updated_at was modified by checking it's not None
        assert existing_model.updated_at is not None
    
    def test_update_global_context_not_found(self, repository, mock_session):
        """Test update raises error when context not found"""
        entity = GlobalContext(id="global-123", organization_name="test-org")
        
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            repository.update("global-123", entity)
            
        assert "not found" in str(exc_info.value)
    
    def test_delete_global_context_success(self, repository, mock_session):
        """Test successful global context deletion"""
        existing_model = Mock(id="global-123")
        
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = existing_model
        
        repository.log_access = Mock()
        
        repository.delete("global-123")
        
        mock_session.delete.assert_called_once_with(existing_model)
        mock_session.flush.assert_called_once()
        repository.log_access.assert_called_with("delete", "global_context", "global-123")
    
    def test_delete_global_context_not_found(self, repository, mock_session):
        """Test delete raises error when context not found"""
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            repository.delete("global-123")
            
        assert "not found" in str(exc_info.value)
    
    def test_list_global_contexts(self, repository, mock_session):
        """Test listing global contexts for user"""
        mock_models = [
            Mock(id="global-1", user_id="test-user"),
            Mock(id="global-2", user_id="test-user")
        ]
        
        mock_query = Mock()
        mock_query.all.return_value = mock_models
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_session.query.return_value = mock_query
        
        # Mock _to_entity
        repository._to_entity = Mock(side_effect=lambda m: Mock(id=m.id))
        
        result = repository.list()
        
        assert len(result) == 2
        repository.apply_user_filter.assert_called_once()
        assert repository._to_entity.call_count == 2
    
    def test_list_with_filters(self, repository, mock_session):
        """Test listing with filters"""
        filters = {"status": "active"}
        
        mock_query = Mock()
        mock_query.all.return_value = []
        repository.apply_user_filter = Mock(return_value=mock_query)
        repository.apply_filters = Mock(return_value=mock_query)
        mock_session.query.return_value = mock_query
        
        result = repository.list(filters=filters)
        
        repository.apply_filters.assert_called_once_with(mock_query, filters)
        repository.apply_user_filter.assert_called_once()
    
    def test_exists_returns_true(self, repository, mock_session):
        """Test exists returns True when context exists"""
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = Mock()
        
        result = repository.exists("global-123")
        
        assert result is True
    
    def test_exists_returns_false(self, repository, mock_session):
        """Test exists returns False when context doesn't exist"""
        mock_query = Mock()
        mock_session.query.return_value.filter.return_value = mock_query
        repository.apply_user_filter = Mock(return_value=mock_query)
        mock_query.first.return_value = None
        
        result = repository.exists("global-123")
        
        assert result is False