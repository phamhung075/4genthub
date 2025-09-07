"""
Test cases for BaseUserScopedRepository

Tests the base repository class that handles user-based data isolation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.repositories.base_user_scoped_repository import (
    BaseUserScopedRepository,
    UserScopedError,
    InsufficientPermissionsError,
    CrossUserAccessError
)


class MockEntity:
    """Mock entity for testing"""
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id


class MockModel:
    """Mock model for testing"""
    user_id = Mock()
    __name__ = "MockModel"


class TestBaseUserScopedRepository:
    """Test cases for BaseUserScopedRepository"""

    def setup_method(self):
        """Set up test fixtures"""
        self.session = Mock(spec=Session)
        self.user_id = "test-user-123"
        self.system_user_id = None

    def test_init_with_user_id(self):
        """Test repository initialization with user ID"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        
        assert repo.session == self.session
        assert repo.user_id == self.user_id
        assert not repo._is_system_mode
        assert not repo.is_system_mode()

    def test_init_system_mode(self, caplog):
        """Test repository initialization in system mode"""
        with caplog.at_level(logging.INFO):
            repo = BaseUserScopedRepository(self.session, None)
        
        assert repo.session == self.session
        assert repo.user_id is None
        assert repo._is_system_mode
        assert repo.is_system_mode()
        assert "Repository initialized in system mode" in caplog.text

    def test_with_user_basic(self):
        """Test with_user method without session_factory"""
        repo = BaseUserScopedRepository(self.session, None)
        new_repo = repo.with_user("new-user-456")
        
        assert new_repo.user_id == "new-user-456"
        assert new_repo.session == self.session
        assert not new_repo.is_system_mode()

    def test_with_user_with_session_factory(self):
        """Test with_user method with session_factory"""
        mock_session_factory = Mock()
        mock_new_session = Mock()
        mock_session_factory.return_value = mock_new_session
        
        repo = BaseUserScopedRepository(self.session, None)
        repo.session_factory = mock_session_factory
        
        new_repo = repo.with_user("new-user-456")
        
        mock_session_factory.assert_called_once_with("new-user-456")
        assert new_repo.user_id == "new-user-456"
        assert new_repo.session == mock_new_session

    def test_get_user_filter_with_user(self):
        """Test get_user_filter with user ID"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        filter_dict = repo.get_user_filter()
        
        assert filter_dict == {"user_id": self.user_id}

    def test_get_user_filter_system_mode(self):
        """Test get_user_filter in system mode"""
        repo = BaseUserScopedRepository(self.session, None)
        filter_dict = repo.get_user_filter()
        
        assert filter_dict == {}

    def test_apply_user_filter_system_mode(self):
        """Test apply_user_filter in system mode returns query unchanged"""
        repo = BaseUserScopedRepository(self.session, None)
        mock_query = Mock()
        
        result = repo.apply_user_filter(mock_query)
        
        assert result == mock_query

    def test_apply_user_filter_string_with_where(self):
        """Test apply_user_filter with string query containing WHERE"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        query = "SELECT * FROM tasks WHERE status = 'active'"
        
        result = repo.apply_user_filter(query)
        
        expected = f"SELECT * FROM tasks WHERE status = 'active' AND user_id = '{self.user_id}'"
        assert result == expected

    def test_apply_user_filter_string_without_where(self):
        """Test apply_user_filter with string query without WHERE"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        query = "SELECT * FROM tasks"
        
        result = repo.apply_user_filter(query)
        
        expected = f"SELECT * FROM tasks WHERE user_id = '{self.user_id}'"
        assert result == expected

    def test_apply_user_filter_sqlalchemy_query_with_user_id(self):
        """Test apply_user_filter with SQLAlchemy query on model with user_id"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        mock_query = Mock()
        mock_model = MockModel()
        mock_query.column_descriptions = [{"entity": mock_model}]
        mock_query.filter.return_value = mock_query
        
        result = repo.apply_user_filter(mock_query)
        
        mock_query.filter.assert_called_once()
        assert result == mock_query

    def test_apply_user_filter_sqlalchemy_query_without_user_id(self, caplog):
        """Test apply_user_filter with SQLAlchemy query on model without user_id"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        mock_query = Mock()
        mock_model = Mock()
        mock_model.__name__ = "TestModel"
        # Remove user_id attribute
        if hasattr(mock_model, 'user_id'):
            delattr(mock_model, 'user_id')
        mock_query.column_descriptions = [{"entity": mock_model}]
        
        with caplog.at_level(logging.WARNING):
            result = repo.apply_user_filter(mock_query)
        
        assert result == mock_query
        assert "does not have user_id attribute" in caplog.text

    def test_apply_user_filter_exception_handling(self, caplog):
        """Test apply_user_filter exception handling"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        mock_query = Mock()
        mock_query.column_descriptions = None  # This will cause TypeError when accessing [0]
        
        with caplog.at_level(logging.WARNING):
            result = repo.apply_user_filter(mock_query)
        
        assert result == mock_query
        assert "Could not apply user filter" in caplog.text

    def test_ensure_user_ownership_system_mode(self):
        """Test ensure_user_ownership in system mode"""
        repo = BaseUserScopedRepository(self.session, None)
        entity = MockEntity("other-user")
        
        # Should not raise exception in system mode
        repo.ensure_user_ownership(entity)

    def test_ensure_user_ownership_correct_user(self):
        """Test ensure_user_ownership with correct user"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        entity = MockEntity(self.user_id)
        
        # Should not raise exception
        repo.ensure_user_ownership(entity)

    def test_ensure_user_ownership_wrong_user(self):
        """Test ensure_user_ownership with wrong user"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        entity = MockEntity("other-user")
        
        with pytest.raises(PermissionError) as exc_info:
            repo.ensure_user_ownership(entity)
        
        assert "Access denied" in str(exc_info.value)
        assert self.user_id in str(exc_info.value)

    def test_ensure_user_ownership_no_user_id_attribute(self, caplog):
        """Test ensure_user_ownership with entity without user_id"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        entity = Mock()
        if hasattr(entity, 'user_id'):
            delattr(entity, 'user_id')
        
        with caplog.at_level(logging.WARNING):
            repo.ensure_user_ownership(entity)
        
        assert "does not have user_id attribute" in caplog.text

    def test_set_user_id_normal_mode(self, caplog):
        """Test set_user_id in normal mode"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        data = {"title": "Test Task"}
        
        with caplog.at_level(logging.DEBUG):
            result = repo.set_user_id(data)
        
        assert result["user_id"] == self.user_id
        assert result["title"] == "Test Task"
        assert "Setting user_id in data" in caplog.text

    def test_set_user_id_system_mode(self, caplog):
        """Test set_user_id in system mode"""
        repo = BaseUserScopedRepository(self.session, None)
        data = {"title": "Test Task"}
        
        with caplog.at_level(logging.ERROR):
            result = repo.set_user_id(data)
        
        assert "user_id" not in result
        assert result["title"] == "Test Task"
        assert "Repository in system mode" in caplog.text

    def test_validate_bulk_operation_system_mode(self):
        """Test validate_bulk_operation in system mode"""
        repo = BaseUserScopedRepository(self.session, None)
        entities = [MockEntity("user1"), MockEntity("user2")]
        
        # Should not raise exception in system mode
        repo.validate_bulk_operation(entities)

    def test_validate_bulk_operation_valid(self):
        """Test validate_bulk_operation with valid entities"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        entities = [MockEntity(self.user_id), MockEntity(self.user_id)]
        
        # Should not raise exception
        repo.validate_bulk_operation(entities)

    def test_validate_bulk_operation_invalid(self):
        """Test validate_bulk_operation with invalid entities"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        entities = [MockEntity(self.user_id), MockEntity("other-user")]
        
        with pytest.raises(PermissionError):
            repo.validate_bulk_operation(entities)

    def test_create_system_context(self, caplog):
        """Test create_system_context"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        
        with caplog.at_level(logging.WARNING):
            system_repo = repo.create_system_context()
        
        assert system_repo.is_system_mode()
        assert system_repo.user_id is None
        assert "Creating system context" in caplog.text

    def test_get_current_user_id(self):
        """Test get_current_user_id"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        assert repo.get_current_user_id() == self.user_id
        
        system_repo = BaseUserScopedRepository(self.session, None)
        assert system_repo.get_current_user_id() is None

    def test_log_access_with_user(self, caplog):
        """Test log_access with user ID"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        
        with caplog.at_level(logging.INFO):
            repo.log_access("create", "task", "task-123")
        
        assert f"User {self.user_id} performed create on task task-123" in caplog.text

    def test_log_access_system_mode(self, caplog):
        """Test log_access in system mode"""
        repo = BaseUserScopedRepository(self.session, None)
        
        with caplog.at_level(logging.INFO):
            repo.log_access("create", "task", "task-123")
        
        assert "System performed create on task task-123" in caplog.text

    def test_log_access_no_entity_id(self, caplog):
        """Test log_access without entity ID"""
        repo = BaseUserScopedRepository(self.session, self.user_id)
        
        with caplog.at_level(logging.INFO):
            repo.log_access("create", "task")
        
        assert f"User {self.user_id} performed create on task new" in caplog.text


class TestUserScopedExceptions:
    """Test custom exception classes"""

    def test_user_scoped_error(self):
        """Test UserScopedError exception"""
        with pytest.raises(UserScopedError):
            raise UserScopedError("Test error")

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError exception"""
        with pytest.raises(InsufficientPermissionsError):
            raise InsufficientPermissionsError("Insufficient permissions")
        
        # Test inheritance
        with pytest.raises(UserScopedError):
            raise InsufficientPermissionsError("Insufficient permissions")

    def test_cross_user_access_error(self):
        """Test CrossUserAccessError exception"""
        with pytest.raises(CrossUserAccessError):
            raise CrossUserAccessError("Cross user access denied")
        
        # Test inheritance
        with pytest.raises(UserScopedError):
            raise CrossUserAccessError("Cross user access denied")


class TestIntegration:
    """Integration tests for BaseUserScopedRepository"""

    def test_complete_workflow(self, caplog):
        """Test a complete workflow with user scoping"""
        session = Mock(spec=Session)
        user_id = "integration-test-user"
        
        # Initialize repository
        repo = BaseUserScopedRepository(session, user_id)
        
        # Test user filter
        filter_dict = repo.get_user_filter()
        assert filter_dict == {"user_id": user_id}
        
        # Test data preparation
        data = {"title": "Integration Test"}
        data_with_user = repo.set_user_id(data.copy())
        assert data_with_user["user_id"] == user_id
        
        # Test entity ownership validation
        valid_entity = MockEntity(user_id)
        repo.ensure_user_ownership(valid_entity)  # Should not raise
        
        # Test access logging
        with caplog.at_level(logging.INFO):
            repo.log_access("create", "task", "integration-test-123")
        
        assert f"User {user_id} performed create on task integration-test-123" in caplog.text
        
        # Test system context creation
        system_repo = repo.create_system_context()
        assert system_repo.is_system_mode()
        assert system_repo.get_current_user_id() is None

    def test_user_isolation(self):
        """Test that user isolation works correctly"""
        session = Mock(spec=Session)
        user1_id = "user-1"
        user2_id = "user-2"
        
        # Create repositories for different users
        repo1 = BaseUserScopedRepository(session, user1_id)
        repo2 = BaseUserScopedRepository(session, user2_id)
        
        # Test that each repo has correct user ID
        assert repo1.get_current_user_id() == user1_id
        assert repo2.get_current_user_id() == user2_id
        
        # Test that entities from different users are rejected
        entity1 = MockEntity(user1_id)
        entity2 = MockEntity(user2_id)
        
        # repo1 should accept entity1 but reject entity2
        repo1.ensure_user_ownership(entity1)  # Should not raise
        with pytest.raises(PermissionError):
            repo1.ensure_user_ownership(entity2)
        
        # repo2 should accept entity2 but reject entity1
        repo2.ensure_user_ownership(entity2)  # Should not raise
        with pytest.raises(PermissionError):
            repo2.ensure_user_ownership(entity1)