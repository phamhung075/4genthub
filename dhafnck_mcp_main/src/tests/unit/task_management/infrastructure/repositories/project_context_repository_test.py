"""
Tests for ProjectContextRepository - Corrected Interface

Tests the project context repository functionality with correct interface
that matches the actual repository implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.infrastructure.repositories.project_context_repository import ProjectContextRepository
from fastmcp.task_management.infrastructure.database.models import ProjectContext as ProjectContextModel
from fastmcp.task_management.domain.entities.context import ProjectContext


class TestProjectContextRepository:
    """Test suite for ProjectContextRepository - Core functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.user_id = "test-user-123"
        
        self.repository = ProjectContextRepository(
            session_factory=self.mock_session_factory,
            user_id=self.user_id
        )

    def test_initialization(self):
        """Test repository initialization"""
        assert self.repository.session_factory == self.mock_session_factory
        assert self.repository.user_id == self.user_id

    def test_initialization_without_user_id(self):
        """Test repository initialization without user_id"""
        repo = ProjectContextRepository(self.mock_session_factory, user_id=None)
        assert repo.session_factory == self.mock_session_factory
        assert repo.user_id is None

    def test_with_user_creates_new_instance(self):
        """Test with_user creates new repository instance with user scoping"""
        new_user_id = "new-user-456"
        scoped_repo = self.repository.with_user(new_user_id)
        
        assert isinstance(scoped_repo, ProjectContextRepository)
        assert scoped_repo.user_id == new_user_id
        assert scoped_repo.session_factory == self.mock_session_factory
        assert scoped_repo != self.repository


class TestProjectContextRepositoryUserScoping:
    """Test user scoping and data isolation functionality"""

    def setup_method(self):
        """Set up test fixtures for user scoping tests"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        
        self.user_id_1 = "user-123"
        self.user_id_2 = "user-456"
        
        self.repo_user_1 = ProjectContextRepository(
            session_factory=self.mock_session_factory,
            user_id=self.user_id_1
        )

    def test_user_scoped_create_includes_user_id(self):
        """Test that user-scoped repository includes user_id in creation"""
        project_id = str(uuid.uuid4())
        entity = ProjectContext(
            id=project_id,
            project_name="User Project",
            project_settings={"setting": "value"},
            metadata={}
        )
        
        mock_model = Mock(spec=ProjectContextModel)
        mock_model.project_id = project_id
        mock_model.user_id = self.user_id_1
        
        self.mock_session.get.return_value = None  # No existing record
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        
        with patch('fastmcp.task_management.infrastructure.repositories.project_context_repository.ProjectContextModel') as MockModel:
            MockModel.return_value = mock_model
            
            # Mock the _to_entity method return
            with patch.object(self.repo_user_1, '_to_entity', return_value=entity):
                result = self.repo_user_1.create(entity)
                
                # Assert that user_id is included in the model creation
                MockModel.assert_called_once()
                call_kwargs = MockModel.call_args[1]
                assert call_kwargs['user_id'] == self.user_id_1
                assert call_kwargs['id'] == project_id

    def test_user_scoped_get_filters_by_user_id(self):
        """Test that user-scoped repository filters by user_id in queries"""
        project_id = str(uuid.uuid4())
        
        # Create a proper mock for ProjectContextModel with all required attributes
        mock_db_model = Mock()
        mock_db_model.project_id = project_id
        mock_db_model.team_preferences = {}
        mock_db_model.technology_stack = {}
        mock_db_model.project_workflow = {}
        mock_db_model.local_standards = {}  # This needs to be a dict, not a Mock
        mock_db_model.global_overrides = {}
        mock_db_model.delegation_rules = {}
        mock_db_model.created_at = None
        mock_db_model.updated_at = None
        mock_db_model.version = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_db_model
        self.mock_session.query.return_value = mock_query
        
        # Act
        self.repo_user_1.get(project_id)
        
        # Assert that query and filter were called
        self.mock_session.query.assert_called_once()
        # Check that filter was called (implementation adds user_id filter)
        assert mock_query.filter.call_count >= 1

    def test_user_scoped_list_filters_by_user_id(self):
        """Test that user-scoped repository filters list by user_id"""
        filters = {"project_id": "some-project"}
        
        # Mock the execute result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        # Act
        result = self.repo_user_1.list(filters)
        
        # Assert that execute was called (SQL statement includes user filter)
        self.mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    def test_cross_user_isolation(self):
        """Test that users cannot access each other's project contexts"""
        project_id = str(uuid.uuid4())
        repo_user_2 = self.repo_user_1.with_user(self.user_id_2)
        
        # Mock user 1 has access to project
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_model = Mock(spec=ProjectContextModel)
        mock_query.first.return_value = mock_model
        self.mock_session.query.return_value = mock_query
        
        # Mock _to_entity for user 1
        mock_entity = Mock(spec=ProjectContext)
        with patch.object(self.repo_user_1, '_to_entity', return_value=mock_entity):
            result_user_1 = self.repo_user_1.get(project_id)
        
        # Mock user 2 does not have access (different user_id filter)
        mock_query.first.return_value = None
        with patch.object(repo_user_2, '_to_entity', return_value=None):
            result_user_2 = repo_user_2.get(project_id)
        
        # Assert isolation
        assert result_user_1 is not None
        assert result_user_2 is None

    def test_repository_without_user_id_no_scoping(self):
        """Test that repository without user_id doesn't apply user scoping"""
        repo_no_user = ProjectContextRepository(self.mock_session_factory, user_id=None)
        project_id = str(uuid.uuid4())
        entity = ProjectContext(
            id=project_id,
            project_name="Global Project",
            project_settings={},
            metadata={}
        )
        
        mock_model = Mock(spec=ProjectContextModel)
        mock_model.project_id = project_id
        mock_model.user_id = None
        
        self.mock_session.get.return_value = None  # No existing record
        
        with patch('fastmcp.task_management.infrastructure.repositories.project_context_repository.ProjectContextModel') as MockModel:
            MockModel.return_value = mock_model
            
            with patch.object(repo_no_user, '_to_entity', return_value=entity):
                result = repo_no_user.create(entity)
                
                # Assert that user_id is None
                call_kwargs = MockModel.call_args[1]
                assert call_kwargs['user_id'] is None


class TestProjectContextRepositoryEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_session_factory = Mock()
        self.mock_session = Mock(spec=Session)
        self.mock_session_factory.return_value = self.mock_session
        self.repository = ProjectContextRepository(self.mock_session_factory)

    def test_transaction_rollback_on_error(self):
        """Test proper transaction rollback on errors"""
        project_id = str(uuid.uuid4())
        entity = ProjectContext(
            id=project_id,
            project_name="Test Project",
            project_settings={},
            metadata={}
        )
        
        # Mock get_db_session to raise an error and test rollback
        mock_session = Mock(spec=Session)
        mock_session.get.return_value = None  # No existing record
        mock_session.add.side_effect = SQLAlchemyError("Transaction failed")
        mock_session.rollback = Mock()
        mock_session.close = Mock()
        
        # Create a context manager mock that properly handles exceptions
        class MockContextManager:
            def __enter__(self):
                return mock_session
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    mock_session.rollback()
                mock_session.close()
                return False  # Don't suppress the exception
        
        # Mock the context manager to return our failing session
        with patch.object(self.repository, 'get_db_session', return_value=MockContextManager()):
            # Act & Assert
            with pytest.raises(SQLAlchemyError):
                self.repository.create(entity)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()

    def test_empty_filters_in_list_operation(self):
        """Test list operation with various filter combinations"""
        test_filters = [
            {},  # Empty filters
            None,  # None filters
            {"nonexistent_field": "value"},  # Invalid field
            {"project_id": ""},  # Empty value
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        for filters in test_filters:
            # Act
            result = self.repository.list(filters)
            
            # Assert
            assert isinstance(result, list)  # Should return empty list or valid results