"""
Test suite for BaseORMRepository.

Tests the core functionality of the base ORM repository including
CRUD operations, session management, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from fastmcp.task_management.infrastructure.repositories.base_orm_repository import BaseORMRepository
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    DatabaseException,
    DatabaseIntegrityException,
    ValidationException
)


# Mock model for testing
class MockModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    __tablename__ = "mock_table"
    id = None


class TestBaseORMRepository:
    """Test suite for BaseORMRepository functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = BaseORMRepository(MockModel)
        self.mock_session = Mock(spec=Session)

    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.get_session')
    def test_get_db_session_new_session(self, mock_get_session):
        """Test get_db_session creates new session when none exists."""
        mock_get_session.return_value = self.mock_session
        
        with self.repo.get_db_session() as session:
            assert session == self.mock_session
            
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()

    def test_get_db_session_existing_session(self):
        """Test get_db_session uses existing session when available."""
        self.repo._session = self.mock_session
        
        with self.repo.get_db_session() as session:
            assert session == self.mock_session
            
        # Should not commit or close existing session
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_not_called()

    def test_get_db_session_with_user_scoped_session(self):
        """Test get_db_session uses session attribute from user-scoped repo."""
        self.repo.session = self.mock_session
        
        with self.repo.get_db_session() as session:
            assert session == self.mock_session
            
        # Should not commit or close user-scoped session
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_not_called()

    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.get_session')
    def test_get_db_session_sql_error(self, mock_get_session):
        """Test get_db_session handles SQLAlchemy errors."""
        mock_get_session.return_value = self.mock_session
        self.mock_session.commit.side_effect = SQLAlchemyError("Test error")
        
        with pytest.raises(DatabaseException) as exc_info:
            with self.repo.get_db_session():
                pass
                
        assert "Database operation failed" in str(exc_info.value)
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()

    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.get_session')
    def test_transaction_success(self, mock_get_session):
        """Test successful transaction handling."""
        mock_get_session.return_value = self.mock_session

        with self.repo.transaction() as transaction_session:
            assert transaction_session == self.mock_session
            assert self.repo._session == self.mock_session
            
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
        assert self.repo._session is None

    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.get_session')
    def test_transaction_failure(self, mock_get_session):
        """Test transaction rollback on failure."""
        mock_get_session.return_value = self.mock_session
        self.mock_session.commit.side_effect = SQLAlchemyError("Transaction error")
        
        with pytest.raises(DatabaseException) as exc_info:
            with self.repo.transaction():
                pass
                
        assert "Transaction failed" in str(exc_info.value)
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()
        assert self.repo._session is None

    def test_create_success(self):
        """Test successful record creation."""
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.create(id=1, name="test")
        
        assert isinstance(result, MockModel)
        assert result.id == 1
        assert result.name == "test"
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once()

    def test_create_integrity_error(self):
        """Test creation with integrity constraint violation."""
        self.repo.get_db_session = self._mock_session_context
        self.mock_session.add.side_effect = IntegrityError("", "", "")
        
        with pytest.raises(ValidationException) as exc_info:
            self.repo.create(id=1, name="test")
            
        assert "Integrity constraint violation" in str(exc_info.value)

    def test_get_by_id_found(self):
        """Test getting record by ID when found."""
        mock_instance = MockModel(id=1, name="test")
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_instance
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.get_by_id(1)
        
        assert result == mock_instance
        self.mock_session.query.assert_called_once_with(MockModel)

    def test_get_by_id_not_found(self):
        """Test getting record by ID when not found."""
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.get_by_id(999)
        
        assert result is None

    def test_get_all_no_pagination(self):
        """Test getting all records without pagination."""
        mock_instances = [MockModel(id=1), MockModel(id=2)]
        query_mock = Mock()
        query_mock.all.return_value = mock_instances
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.get_all()
        
        assert result == mock_instances
        query_mock.offset.assert_not_called()
        query_mock.limit.assert_not_called()

    def test_get_all_with_pagination(self):
        """Test getting all records with pagination."""
        mock_instances = [MockModel(id=1)]
        query_mock = Mock()
        query_mock.offset.return_value.limit.return_value.all.return_value = mock_instances
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.get_all(limit=10, offset=5)
        
        assert result == mock_instances
        query_mock.offset.assert_called_once_with(5)
        query_mock.offset.return_value.limit.assert_called_once_with(10)

    def test_update_success(self):
        """Test successful record update."""
        mock_instance = MockModel(id=1, name="old")
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_instance
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.update(1, name="new")
        
        assert result.name == "new"
        self.mock_session.flush.assert_called_once()
        self.mock_session.refresh.assert_called_once()

    def test_update_not_found(self):
        """Test updating non-existent record."""
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.update(999, name="new")
        
        assert result is None

    def test_delete_success(self):
        """Test successful record deletion."""
        mock_instance = MockModel(id=1)
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = mock_instance
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.delete(1)
        
        assert result is True
        self.mock_session.delete.assert_called_once_with(mock_instance)

    def test_delete_not_found(self):
        """Test deleting non-existent record."""
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = None
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.delete(999)
        
        assert result is False

    def test_exists_true(self):
        """Test exists method when record exists."""
        query_mock = Mock()
        query_mock.filter.return_value.first.return_value = MockModel(id=1)
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.exists(name="test")
        
        assert result is True

    def test_exists_false(self):
        """Test exists method when record doesn't exist."""
        query_mock = Mock()
        # Set up filter to return itself for chaining, then first() returns None
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.exists(name="nonexistent")
        
        assert result is False

    def test_count_with_filters(self):
        """Test count method with filters."""
        query_mock = Mock()
        # Set up filter to return itself for chaining, then count() returns 5
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 5
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.count(status="active")
        
        assert result == 5

    def test_find_by_filters(self):
        """Test find_by method with filters."""
        mock_instances = [MockModel(id=1), MockModel(id=2)]
        query_mock = Mock()
        # Set up filter to return itself for chaining, then all() returns mock_instances
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = mock_instances
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.find_by(status="active")
        
        assert result == mock_instances

    def test_find_one_by_filters(self):
        """Test find_one_by method with filters."""
        mock_instance = MockModel(id=1)
        query_mock = Mock()
        # Set up filter to return itself for chaining, then first() returns mock_instance
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mock_instance
        self.mock_session.query.return_value = query_mock
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.find_one_by(name="test")
        
        assert result == mock_instance

    def test_bulk_create_success(self):
        """Test bulk creation of records."""
        records = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.bulk_create(records)
        
        assert len(result) == 2
        assert self.mock_session.add.call_count == 2
        self.mock_session.flush.assert_called_once()
        assert self.mock_session.refresh.call_count == 2

    def test_execute_query(self):
        """Test execute_query method."""
        def query_func(session, param=None):
            return f"query result with {param}"
        
        self.repo.get_db_session = self._mock_session_context
        
        result = self.repo.execute_query(query_func, param="test")
        
        assert result == "query result with test"

    @contextmanager
    def _mock_session_context(self):
        """Helper to mock session context manager."""
        yield self.mock_session


class TestBaseORMRepositoryFeatureFlag:
    """Test suite for FEATURE_CLEAN_REPOSITORIES feature flag behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = BaseORMRepository(MockModel)
        self.mock_session = Mock(spec=Session)
        # Store original flag value to restore after tests
        self.original_flag = BaseORMRepository.FEATURE_CLEAN_REPOSITORIES

    def teardown_method(self):
        """Restore original flag value after each test."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = self.original_flag

    @contextmanager
    def _mock_session_context(self):
        """Helper to mock session context manager."""
        yield self.mock_session

    def test_feature_flag_defaults_to_false(self):
        """Test that FEATURE_CLEAN_REPOSITORIES defaults to False for backward compatibility."""
        # Reset to environment default
        import os
        original_env = os.environ.get("FEATURE_CLEAN_REPOSITORIES")
        if "FEATURE_CLEAN_REPOSITORIES" in os.environ:
            del os.environ["FEATURE_CLEAN_REPOSITORIES"]

        # Create new instance to get default value
        from importlib import reload
        import fastmcp.task_management.infrastructure.repositories.base_orm_repository as repo_module
        reload(repo_module)

        assert repo_module.BaseORMRepository.FEATURE_CLEAN_REPOSITORIES is False

        # Restore environment
        if original_env:
            os.environ["FEATURE_CLEAN_REPOSITORIES"] = original_env

    def test_create_integrity_error_flag_false_raises_validation_exception(self):
        """Test that IntegrityError raises ValidationException when flag is False (backward compatible)."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = False
        self.repo.get_db_session = self._mock_session_context
        self.mock_session.add.side_effect = IntegrityError("", "", "UNIQUE constraint failed: mock_table.id")

        with pytest.raises(ValidationException) as exc_info:
            self.repo.create(id=1, name="test")

        # Verify it's a business validation exception (old behavior)
        assert "Integrity constraint violation" in str(exc_info.value)
        assert exc_info.value.error_code == "VALIDATION_ERROR"

    def test_create_integrity_error_flag_true_raises_database_integrity_exception(self):
        """Test that IntegrityError raises DatabaseIntegrityException when flag is True (clean separation)."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = True
        self.repo.get_db_session = self._mock_session_context
        self.mock_session.add.side_effect = IntegrityError("", "", "UNIQUE constraint failed: mock_table.id")

        with pytest.raises(DatabaseIntegrityException) as exc_info:
            self.repo.create(id=1, name="test")

        # Verify it's a technical database exception (new clean behavior)
        assert "Database integrity constraint violation" in str(exc_info.value)
        assert exc_info.value.error_code == "DATABASE_INTEGRITY_ERROR"

    def test_extract_constraint_name_unique_constraint(self):
        """Test extracting constraint name from UNIQUE constraint error."""
        error_msg = "UNIQUE constraint failed: mock_table.id"
        constraint_name = self.repo._extract_constraint_name(error_msg)
        assert constraint_name == "mock_table.id"

    def test_extract_constraint_name_not_null_constraint(self):
        """Test extracting constraint name from NOT NULL constraint error."""
        error_msg = "NOT NULL constraint failed: mock_table.name"
        constraint_name = self.repo._extract_constraint_name(error_msg)
        assert constraint_name == "mock_table.name"

    def test_extract_constraint_name_foreign_key_constraint(self):
        """Test extracting constraint name from FOREIGN KEY constraint error."""
        error_msg = "FOREIGN KEY constraint failed"
        constraint_name = self.repo._extract_constraint_name(error_msg)
        # Foreign key errors may not have detailed constraint name
        assert constraint_name is None or isinstance(constraint_name, str)

    def test_extract_constraint_name_check_constraint(self):
        """Test extracting constraint name from CHECK constraint error."""
        error_msg = "CHECK constraint failed: mock_table.status"
        constraint_name = self.repo._extract_constraint_name(error_msg)
        assert constraint_name == "mock_table.status"

    def test_extract_constraint_name_unknown_format(self):
        """Test extracting constraint name from unknown error format."""
        error_msg = "Some unknown database error"
        constraint_name = self.repo._extract_constraint_name(error_msg)
        assert constraint_name is None

    def test_create_success_flag_true_still_works(self):
        """Test that successful creation still works with flag=True."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = True
        self.repo.get_db_session = self._mock_session_context

        result = self.repo.create(id=1, name="test")

        assert isinstance(result, MockModel)
        assert result.id == 1
        assert result.name == "test"

    def test_create_success_flag_false_still_works(self):
        """Test that successful creation still works with flag=False."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = False
        self.repo.get_db_session = self._mock_session_context

        result = self.repo.create(id=1, name="test")

        assert isinstance(result, MockModel)
        assert result.id == 1
        assert result.name == "test"

    def test_flag_can_be_toggled_at_runtime(self):
        """Test that feature flag can be toggled at runtime for testing."""
        # Test toggling from False to True
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = False
        assert BaseORMRepository.FEATURE_CLEAN_REPOSITORIES is False

        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = True
        assert BaseORMRepository.FEATURE_CLEAN_REPOSITORIES is True

        # Test toggling back
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = False
        assert BaseORMRepository.FEATURE_CLEAN_REPOSITORIES is False

    def test_database_integrity_exception_includes_constraint_details(self):
        """Test that DatabaseIntegrityException includes constraint details when flag=True."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = True
        self.repo.get_db_session = self._mock_session_context
        self.mock_session.add.side_effect = IntegrityError(
            "", "", "UNIQUE constraint failed: tasks.title"
        )

        with pytest.raises(DatabaseIntegrityException) as exc_info:
            self.repo.create(title="duplicate")

        # Verify exception has constraint information
        exception = exc_info.value
        assert exception.context.get("constraint") == "tasks.title"

    def test_validation_exception_backward_compatible_structure(self):
        """Test that ValidationException maintains backward compatible structure when flag=False."""
        BaseORMRepository.FEATURE_CLEAN_REPOSITORIES = False
        self.repo.get_db_session = self._mock_session_context
        self.mock_session.add.side_effect = IntegrityError("", "", "constraint violation")

        with pytest.raises(ValidationException) as exc_info:
            self.repo.create(id=1, name="test")

        # Verify backward compatible structure
        exception = exc_info.value
        assert exception.context.get("field") == "unknown"
        assert "id" in str(exception.context.get("value"))  # Contains kwargs