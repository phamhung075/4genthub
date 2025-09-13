"""
Test suite for global_context_repository_user_scoped.py - Global Context Repository User Scoped

Tests the user-scoped global context repository with proper user isolation,
context normalization, and database operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid

from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
from fastmcp.task_management.domain.entities.context import GlobalContext
from fastmcp.task_management.infrastructure.database.models import GlobalContext as GlobalContextModel, GLOBAL_SINGLETON_UUID

class TestGlobalContextRepository:
    """Test GlobalContextRepository class initialization and basic functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.user_id = "test-user-123"
    
    def test_init_with_user_id(self):
        """Test repository initialization with user ID"""
        repository = GlobalContextRepository(self.mock_session_factory, self.user_id)
        
        assert repository.user_id == self.user_id
        assert repository.session_factory == self.mock_session_factory
        assert repository.model_class == GlobalContextModel
    
    def test_init_without_user_id(self):
        """Test repository initialization without user ID (system mode)"""
        repository = GlobalContextRepository(self.mock_session_factory)
        
        assert repository.user_id is None
        assert repository.session_factory == self.mock_session_factory
    
    def test_normalize_context_id_with_global_singleton_and_user(self):
        """Test context ID normalization for global_singleton with user"""
        repository = GlobalContextRepository(self.mock_session_factory, self.user_id)

        # The base class should have a method to normalize context IDs
        normalized_id = repository._normalize_context_id("global_singleton")

        # For global contexts, it should create user-specific IDs
        assert normalized_id != "global_singleton"
        assert normalized_id != GLOBAL_SINGLETON_UUID
        # Should be a valid UUID
        uuid.UUID(normalized_id)  # Should not raise ValueError
    
    def test_normalize_context_id_with_global_singleton_no_user(self):
        """Test context ID normalization for global_singleton without user"""
        repository = GlobalContextRepository(self.mock_session_factory)
        
        normalized_id = repository._normalize_context_id("global_singleton")
        
        assert normalized_id == GLOBAL_SINGLETON_UUID
    
    def test_normalize_context_id_regular_id(self):
        """Test context ID normalization for regular IDs"""
        repository = GlobalContextRepository(self.mock_session_factory, self.user_id)
        
        test_id = "regular-context-123"
        normalized_id = repository._normalize_context_id(test_id)
        
        assert normalized_id == test_id
    
    def test_normalize_context_id_user_object_with_user_id_attr(self):
        """Test context ID normalization when user_id is object with user_id attribute"""
        mock_user = Mock()
        mock_user.user_id = "user-object-123"
        
        repository = GlobalContextRepository(self.mock_session_factory, mock_user)
        
        normalized_id = repository._normalize_context_id("global_singleton")
        
        # Should create a valid UUID based on the user_id attribute
        uuid.UUID(normalized_id)  # Should not raise ValueError
        assert normalized_id != GLOBAL_SINGLETON_UUID
    
    def test_normalize_context_id_user_object_with_id_attr(self):
        """Test context ID normalization when user_id is object with id attribute"""
        mock_user = Mock()
        mock_user.id = "user-id-123"
        # Remove user_id attribute to test fallback
        if hasattr(mock_user, 'user_id'):
            delattr(mock_user, 'user_id')
        
        repository = GlobalContextRepository(self.mock_session_factory, mock_user)
        
        normalized_id = repository._normalize_context_id("global_singleton")
        
        # Should create a valid UUID based on the id attribute
        uuid.UUID(normalized_id)  # Should not raise ValueError
        assert normalized_id != GLOBAL_SINGLETON_UUID
    
    def test_normalize_context_id_user_uuid_string(self):
        """Test context ID normalization when user_id is a valid UUID string"""
        user_uuid = str(uuid.uuid4())
        
        repository = GlobalContextRepository(self.mock_session_factory, user_uuid)
        
        normalized_id = repository._normalize_context_id("global_singleton")
        
        # Should create a valid UUID
        uuid.UUID(normalized_id)  # Should not raise ValueError
        assert normalized_id != GLOBAL_SINGLETON_UUID
        assert normalized_id != user_uuid  # Should be transformed
    
    def test_normalize_context_id_user_non_uuid_string(self):
        """Test context ID normalization when user_id is a non-UUID string"""
        user_string = "non-uuid-user-string"
        
        repository = GlobalContextRepository(self.mock_session_factory, user_string)
        
        normalized_id = repository._normalize_context_id("global_singleton")
        
        # Should create a valid UUID using UUID5
        uuid.UUID(normalized_id)  # Should not raise ValueError
        assert normalized_id != GLOBAL_SINGLETON_UUID
    
    def test_normalize_context_id_deterministic(self):
        """Test that context ID normalization is deterministic for same user"""
        repository1 = GlobalContextRepository(self.mock_session_factory, self.user_id)
        repository2 = GlobalContextRepository(self.mock_session_factory, self.user_id)
        
        normalized_id1 = repository1._normalize_context_id("global_singleton")
        normalized_id2 = repository2._normalize_context_id("global_singleton")
        
        # Same user should always get the same normalized ID
        assert normalized_id1 == normalized_id2
    
    def test_normalize_context_id_different_users(self):
        """Test that different users get different normalized IDs"""
        user1 = "user-123"
        user2 = "user-456"
        
        repository1 = GlobalContextRepository(self.mock_session_factory, user1)
        repository2 = GlobalContextRepository(self.mock_session_factory, user2)
        
        normalized_id1 = repository1._normalize_context_id("global_singleton")
        normalized_id2 = repository2._normalize_context_id("global_singleton")
        
        # Different users should get different normalized IDs
        assert normalized_id1 != normalized_id2
    
    def test_normalize_context_id_exception_handling(self):
        """Test exception handling in context ID normalization"""
        # Create a problematic user object that will cause UUID creation to fail
        problematic_user = Mock()
        problematic_user.user_id = Mock()
        problematic_user.user_id.__str__ = Mock(side_effect=Exception("String conversion failed"))
        
        repository = GlobalContextRepository(self.mock_session_factory, problematic_user)
        
        # Should fallback to GLOBAL_SINGLETON_UUID when UUID creation fails
        normalized_id = repository._normalize_context_id("global_singleton")
        assert normalized_id == GLOBAL_SINGLETON_UUID

class TestSessionManagement:
    """Test database session management"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
    
    def test_get_db_session_normal_operation(self):
        """Test normal database session operation"""
        with self.repository.get_db_session() as session:
            assert session == self.mock_session
            session.some_operation = Mock()
            session.some_operation()
        
        # Session should be committed and closed
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_get_db_session_with_exception(self):
        """Test database session with exception handling"""
        self.mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            with self.repository.get_db_session() as session:
                pass
        
        # Session should be rolled back and closed
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_get_db_session_with_existing_session(self):
        """Test get_db_session when repository already has a session"""
        existing_session = Mock(spec=Session)
        self.repository._session = existing_session
        
        with self.repository.get_db_session() as session:
            assert session == existing_session
        
        # Existing session should not be committed or closed
        existing_session.commit.assert_not_called()
        existing_session.close.assert_not_called()

class TestCreateOperation:
    """Test create operation for global contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods
        self.repository.log_access = Mock()
    
    def test_create_new_global_context(self):
        """Test creating a new global context"""
        # Mock no existing context
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create test entity
        entity = GlobalContext(
            id="global_singleton",
            organization_name="Test Org",
            global_settings={
                "autonomous_rules": {"rule1": "value1"},
                "security_policies": {"policy1": "value1"},
                "custom_field": "custom_value"
            }
        )
        
        # Mock database operations
        saved_model = Mock(spec=GlobalContextModel)
        saved_model.id = "normalized-user-global-id"
        saved_model.organization_id = "Test Org"
        saved_model.autonomous_rules = {"rule1": "value1"}
        saved_model.security_policies = {"policy1": "value1"}
        saved_model.workflow_templates = {"_custom": {"custom_field": "custom_value"}}
        saved_model.created_at = datetime.now(timezone.utc)
        saved_model.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.refresh = Mock()
        
        # Mock _to_entity method
        expected_entity = GlobalContext(id="normalized-user-global-id", organization_name="Test Org")
        self.repository._to_entity = Mock(return_value=expected_entity)
        
        # Execute create
        result = self.repository.create(entity)
        
        # Verify session operations
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once()
        
        # Verify access logging
        self.repository.log_access.assert_called_once_with("create", "global_context", mock_any_normalized_id())
        
        assert result == expected_entity
    
    def test_create_existing_context_error(self):
        """Test creating context when one already exists"""
        # Mock existing context
        existing_model = Mock(spec=GlobalContextModel)
        self.mock_session.query.return_value.filter.return_value.first.return_value = existing_model

        entity = GlobalContext(id="global_singleton", organization_name="test-org")

        with pytest.raises(ValueError, match="Global context already exists"):
            self.repository.create(entity)
        
        # Should not add to session
        self.mock_session.add.assert_not_called()
    
    def test_create_without_user_system_mode(self):
        """Test creating context in system mode (no user_id)"""
        repository = GlobalContextRepository(self.mock_session_factory)
        repository.log_access = Mock()
        repository._to_entity = Mock()
        
        # Mock no existing context
        self.mock_session.get.return_value = None
        
        entity = GlobalContext(id="global_singleton", organization_name="test-org")
        
        repository.create(entity)
        
        # Should use get instead of query with filter
        self.mock_session.get.assert_called_once_with(GlobalContextModel, GLOBAL_SINGLETON_UUID)
    
    def test_create_with_complex_global_settings(self):
        """Test creating context with complex global settings"""
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        self.repository.log_access = Mock()
        self.repository._to_entity = Mock()
        
        complex_settings = {
            "autonomous_rules": {"ai_behavior": "collaborative", "decision_threshold": 0.8},
            "security_policies": {"data_encryption": True, "access_control": "role_based"},
            "coding_standards": {"style_guide": "pep8", "test_coverage": 90},
            "workflow_templates": {"default_review": {"reviewers": 2, "auto_merge": False}},
            "delegation_rules": {"max_depth": 3, "approval_required": True},
            "custom_integration": {"api_keys": ["key1", "key2"]},
            "notification_settings": {"email": True, "slack": False}
        }
        
        entity = GlobalContext(
            id="global_singleton",
            global_settings=complex_settings
        )
        
        result = self.repository.create(entity)
        
        # Verify that add was called (creation attempted)
        self.mock_session.add.assert_called_once()
        
        # Verify the model that was added has the correct structure
        added_model = self.mock_session.add.call_args[0][0]
        assert isinstance(added_model, GlobalContextModel)
        assert added_model.autonomous_rules == complex_settings["autonomous_rules"]
        assert added_model.security_policies == complex_settings["security_policies"]
        assert added_model.coding_standards == complex_settings["coding_standards"]
        
        # Custom fields should be stored in workflow_templates._custom
        expected_custom = {
            "custom_integration": {"api_keys": ["key1", "key2"]},
            "notification_settings": {"email": True, "slack": False}
        }
        assert added_model.workflow_templates["_custom"] == expected_custom

class TestGetOperation:
    """Test get operation for global contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods
        self.repository.log_access = Mock()
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
    
    def test_get_existing_context(self):
        """Test getting an existing global context"""
        # Mock database model
        db_model = Mock(spec=GlobalContextModel)
        db_model.id = "user-specific-global-id"
        db_model.organization_id = "Test Org"
        db_model.autonomous_rules = {"rule1": "value1"}
        
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        
        # Mock entity conversion
        expected_entity = GlobalContext(id="user-specific-global-id")
        self.repository._to_entity = Mock(return_value=expected_entity)
        
        result = self.repository.get("global_singleton")
        
        # Verify query construction
        self.mock_session.query.assert_called_once_with(GlobalContextModel)
        self.repository.apply_user_filter.assert_called_once()
        
        # Verify access logging
        self.repository.log_access.assert_called_once_with("read", "global_context", mock_any_normalized_id())
        
        # Verify entity conversion
        self.repository._to_entity.assert_called_once_with(db_model)
        
        assert result == expected_entity
    
    def test_get_nonexistent_context(self):
        """Test getting a non-existent global context"""
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = None
        
        result = self.repository.get("global_singleton")
        
        assert result is None
        # Access should not be logged for non-existent contexts
        self.repository.log_access.assert_not_called()
    
    def test_get_with_regular_context_id(self):
        """Test getting context with regular (non-singleton) ID"""
        regular_id = "regular-context-123"
        
        db_model = Mock(spec=GlobalContextModel)
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        
        expected_entity = GlobalContext(id=regular_id)
        self.repository._to_entity = Mock(return_value=expected_entity)
        
        result = self.repository.get(regular_id)
        
        # Should use the regular ID as-is (no normalization)
        assert result == expected_entity

class TestUpdateOperation:
    """Test update operation for global contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods
        self.repository.log_access = Mock()
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
        self.repository.ensure_user_ownership = Mock()
    
    def test_update_existing_context(self):
        """Test updating an existing global context"""
        # Mock existing database model
        db_model = Mock(spec=GlobalContextModel)
        db_model.id = "user-specific-global-id"
        
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        
        # Create update entity
        update_entity = GlobalContext(
            id="global_singleton",
            organization_name="Updated Org",
            global_settings={
                "autonomous_rules": {"updated_rule": "new_value"},
                "custom_field": "updated_custom"
            }
        )
        
        # Mock entity conversion
        updated_entity = GlobalContext(id="user-specific-global-id", organization_name="Updated Org")
        self.repository._to_entity = Mock(return_value=updated_entity)
        
        result = self.repository.update("global_singleton", update_entity)
        
        # Verify ownership check
        self.repository.ensure_user_ownership.assert_called_once_with(db_model)
        
        # Verify model updates
        assert db_model.organization_id == "Updated Org"
        assert db_model.autonomous_rules == {"updated_rule": "new_value"}
        assert db_model.workflow_templates == {"_custom": {"custom_field": "updated_custom"}}
        assert db_model.updated_at is not None
        
        # Verify session operations
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(db_model)
        
        # Verify access logging
        self.repository.log_access.assert_called_once_with("update", "global_context", mock_any_normalized_id())
        
        assert result == updated_entity
    
    def test_update_nonexistent_context(self):
        """Test updating a non-existent context"""
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = None
        
        update_entity = GlobalContext(id="global_singleton", organization_name="test-org")
        
        with pytest.raises(ValueError, match="Global context not found"):
            self.repository.update("global_singleton", update_entity)
        
        # Should not attempt session operations
        self.mock_session.flush.assert_not_called()
    
    def test_update_with_complex_settings(self):
        """Test updating context with complex global settings"""
        db_model = Mock(spec=GlobalContextModel)
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        self.repository._to_entity = Mock()
        
        complex_settings = {
            "autonomous_rules": {"new_rule": "new_value"},
            "security_policies": {"updated_policy": "updated_value"},
            "coding_standards": {"style": "black"},
            "workflow_templates": {"template1": {"setting": "value"}},
            "delegation_rules": {"rule": "value"},
            "custom_setting1": "value1",
            "custom_setting2": {"nested": "value2"}
        }
        
        update_entity = GlobalContext(
            id="global_singleton",
            global_settings=complex_settings
        )
        
        self.repository.update("global_singleton", update_entity)
        
        # Verify all standard fields are updated
        assert db_model.autonomous_rules == {"new_rule": "new_value"}
        assert db_model.security_policies == {"updated_policy": "updated_value"}
        assert db_model.coding_standards == {"style": "black"}
        assert db_model.delegation_rules == {"rule": "value"}
        
        # Verify custom fields are stored correctly
        expected_workflow = {
            "template1": {"setting": "value"},
            "_custom": {
                "custom_setting1": "value1",
                "custom_setting2": {"nested": "value2"}
            }
        }
        assert db_model.workflow_templates == expected_workflow

class TestDeleteOperation:
    """Test delete operation for global contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods
        self.repository.log_access = Mock()
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
        self.repository.ensure_user_ownership = Mock()
    
    def test_delete_existing_context(self):
        """Test deleting an existing global context"""
        db_model = Mock(spec=GlobalContextModel)
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        
        result = self.repository.delete("global_singleton")
        
        # Verify ownership check
        self.repository.ensure_user_ownership.assert_called_once_with(db_model)
        
        # Verify deletion
        self.mock_session.delete.assert_called_once_with(db_model)
        
        # Verify access logging
        self.repository.log_access.assert_called_once_with("delete", "global_context", mock_any_normalized_id())
        
        assert result is True
    
    def test_delete_nonexistent_context(self):
        """Test deleting a non-existent context"""
        self.mock_session.query.return_value.filter.return_value = self.repository.apply_user_filter.return_value
        self.repository.apply_user_filter.return_value.first.return_value = None
        
        result = self.repository.delete("global_singleton")
        
        # Should not attempt deletion
        self.mock_session.delete.assert_not_called()
        self.repository.log_access.assert_not_called()
        
        assert result is False

class TestListOperation:
    """Test list operation for global contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods
        self.repository.log_access = Mock()
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
        self.repository._to_entity = Mock()
    
    def test_list_all_contexts(self):
        """Test listing all global contexts for user"""
        # Mock database models
        db_models = [Mock(spec=GlobalContextModel), Mock(spec=GlobalContextModel)]
        self.repository.apply_user_filter.return_value.all.return_value = db_models
        
        # Mock entity conversion
        entities = [Mock(spec=GlobalContext), Mock(spec=GlobalContext)]
        self.repository._to_entity.side_effect = entities
        
        result = self.repository.list()
        
        # Verify query construction
        self.mock_session.query.assert_called_once_with(GlobalContextModel)
        self.repository.apply_user_filter.assert_called_once()
        
        # Verify access logging
        self.repository.log_access.assert_called_once_with("list", "global_context", "count=2")
        
        # Verify entity conversion
        assert self.repository._to_entity.call_count == 2
        
        assert result == entities
    
    def test_list_with_filters(self):
        """Test listing contexts with additional filters"""
        db_models = [Mock(spec=GlobalContextModel)]
        query_mock = self.repository.apply_user_filter.return_value
        query_mock.filter.return_value.all.return_value = db_models
        
        filters = {"organization_id": "test-org"}
        
        self.repository._to_entity.return_value = Mock(spec=GlobalContext)
        
        result = self.repository.list(filters)
        
        # Verify filter was applied
        query_mock.filter.assert_called_once()
        
        assert len(result) == 1
    
    def test_list_empty_results(self):
        """Test listing when no contexts exist"""
        self.repository.apply_user_filter.return_value.all.return_value = []
        
        result = self.repository.list()
        
        # Verify access logging shows count=0
        self.repository.log_access.assert_called_once_with("list", "global_context", "count=0")
        
        assert result == []

class TestConvenienceMethods:
    """Test convenience methods"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
    
    def test_get_user_global_context(self):
        """Test get_user_global_context convenience method"""
        expected_context = Mock(spec=GlobalContext)
        
        # Mock the get method
        self.repository.get = Mock(return_value=expected_context)
        
        result = self.repository.get_user_global_context()
        
        # Verify it calls get with global_singleton
        self.repository.get.assert_called_once_with("global_singleton")
        
        assert result == expected_context
    
    def test_count_user_contexts(self):
        """Test count_user_contexts method"""
        # Mock base class method
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
        self.mock_session.query.return_value.count.return_value = 1
        
        result = self.repository.count_user_contexts()
        
        # Verify query construction
        self.mock_session.query.assert_called_once_with(GlobalContextModel)
        self.repository.apply_user_filter.assert_called_once()
        self.mock_session.query.return_value.count.assert_called_once()
        
        assert result == 1

class TestEntityConversion:
    """Test entity conversion between domain and database models"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
    
    def test_to_entity_basic(self):
        """Test converting database model to domain entity"""
        db_model = Mock(spec=GlobalContextModel)
        db_model.id = "context-123"
        db_model.organization_id = "org-123"
        db_model.autonomous_rules = {"rule1": "value1"}
        db_model.security_policies = {"policy1": "value1"}
        db_model.coding_standards = {"standard1": "value1"}
        db_model.workflow_templates = {"template1": "value1"}
        db_model.delegation_rules = {"delegation1": "value1"}
        db_model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        db_model.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
        db_model.version = 1
        db_model.user_id = "user-123"
        
        result = self.repository._to_entity(db_model)
        
        assert isinstance(result, GlobalContext)
        assert result.id == "context-123"
        assert result.organization_name == "org-123"
        
        # Verify global_settings structure
        assert result.global_settings["autonomous_rules"] == {"rule1": "value1"}
        assert result.global_settings["security_policies"] == {"policy1": "value1"}
        assert result.global_settings["coding_standards"] == {"standard1": "value1"}
        assert result.global_settings["workflow_templates"] == {"template1": "value1"}
        assert result.global_settings["delegation_rules"] == {"delegation1": "value1"}
        
        # Verify metadata
        assert result.metadata["created_at"] == "2024-01-01T00:00:00+00:00"
        assert result.metadata["updated_at"] == "2024-01-02T00:00:00+00:00"
        assert result.metadata["version"] == 1
        assert result.metadata["user_id"] == "user-123"
    
    def test_to_entity_with_custom_fields(self):
        """Test converting database model with custom fields in workflow_templates"""
        db_model = Mock(spec=GlobalContextModel)
        db_model.id = "context-123"
        db_model.organization_id = "org-123"
        db_model.autonomous_rules = {}
        db_model.security_policies = {}
        db_model.coding_standards = {}
        db_model.workflow_templates = {
            "template1": "value1",
            "_custom": {
                "custom_field1": "custom_value1",
                "custom_field2": {"nested": "value"}
            }
        }
        db_model.delegation_rules = {}
        db_model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        db_model.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
        db_model.version = 1
        db_model.user_id = "user-123"
        
        result = self.repository._to_entity(db_model)
        
        # Verify custom fields are extracted to top level
        assert result.global_settings["custom_field1"] == "custom_value1"
        assert result.global_settings["custom_field2"] == {"nested": "value"}
        
        # Verify workflow_templates no longer contains _custom
        assert result.global_settings["workflow_templates"] == {"template1": "value1"}
        assert "_custom" not in result.global_settings["workflow_templates"]
    
    def test_to_entity_with_none_values(self):
        """Test converting database model with None values"""
        db_model = Mock(spec=GlobalContextModel)
        db_model.id = "context-123"
        db_model.organization_id = None
        db_model.autonomous_rules = None
        db_model.security_policies = None
        db_model.coding_standards = None
        db_model.workflow_templates = None
        db_model.delegation_rules = None
        db_model.created_at = None
        db_model.updated_at = None
        db_model.version = None
        db_model.user_id = "user-123"
        
        result = self.repository._to_entity(db_model)
        
        # Verify None values are converted to empty dicts
        assert result.global_settings["autonomous_rules"] == {}
        assert result.global_settings["security_policies"] == {}
        assert result.global_settings["coding_standards"] == {}
        assert result.global_settings["workflow_templates"] == {}
        assert result.global_settings["delegation_rules"] == {}
        
        # Verify None timestamps
        assert result.metadata["created_at"] is None
        assert result.metadata["updated_at"] is None

class TestMigrationMethods:
    """Test migration methods for user-scoped contexts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
    
    def test_migrate_to_user_scoped_with_contexts(self):
        """Test migrating existing contexts to user-scoped"""
        # Mock contexts without user_id
        context1 = Mock(spec=GlobalContextModel)
        context1.id = "context-1"
        context1.user_id = None
        
        context2 = Mock(spec=GlobalContextModel)
        context2.id = "context-2"
        context2.user_id = None
        
        contexts_to_migrate = [context1, context2]
        self.mock_session.query.return_value.filter.return_value.all.return_value = contexts_to_migrate
        
        result = self.repository.migrate_to_user_scoped()
        
        # Verify contexts were updated with system user
        system_user_id = "00000000-0000-0000-0000-000000000000"
        assert context1.user_id == system_user_id
        assert context2.user_id == system_user_id
        
        # Verify commit was called
        self.mock_session.commit.assert_called_once()
        
        assert result == 2
    
    def test_migrate_to_user_scoped_no_contexts(self):
        """Test migration when no contexts need migrating"""
        self.mock_session.query.return_value.filter.return_value.all.return_value = []
        
        result = self.repository.migrate_to_user_scoped()
        
        # Should not commit when nothing to migrate
        self.mock_session.commit.assert_not_called()
        
        assert result == 0

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple operations"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = GlobalContextRepository(self.mock_session_factory, "user-123")
        
        # Mock base class methods for all tests
        self.repository.log_access = Mock()
        self.repository.apply_user_filter = Mock(return_value=self.mock_session.query.return_value)
        self.repository.ensure_user_ownership = Mock()
    
    def test_create_get_update_delete_workflow(self):
        """Test complete CRUD workflow"""
        # Setup for create
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create entity
        entity = GlobalContext(
            id="global_singleton",
            organization_name="Test Org",
            global_settings={"autonomous_rules": {"rule1": "value1"}}
        )
        
        created_entity = GlobalContext(id="normalized-id")
        self.repository._to_entity = Mock(return_value=created_entity)
        
        # 1. Create
        create_result = self.repository.create(entity)
        assert create_result == created_entity
        
        # Setup for get
        db_model = Mock(spec=GlobalContextModel)
        self.repository.apply_user_filter.return_value.first.return_value = db_model
        
        # 2. Get
        get_result = self.repository.get("global_singleton")
        assert get_result == created_entity
        
        # 3. Update
        update_entity = GlobalContext(id="global_singleton", organization_name="Updated Org")
        update_result = self.repository.update("global_singleton", update_entity)
        assert update_result == created_entity
        
        # 4. Delete
        delete_result = self.repository.delete("global_singleton")
        assert delete_result is True
        
        # Verify all operations were logged
        assert self.repository.log_access.call_count == 4

# Helper function for mocking normalized IDs
def mock_any_normalized_id():
    """Mock matcher for any normalized ID"""
    from unittest.mock import ANY
    return ANY

if __name__ == "__main__":
    pytest.main([__file__])