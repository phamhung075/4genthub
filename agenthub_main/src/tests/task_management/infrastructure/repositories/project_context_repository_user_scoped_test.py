"""Tests for ProjectContextRepository with user scoping"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid

from fastmcp.task_management.infrastructure.repositories.project_context_repository import ProjectContextRepository
from fastmcp.task_management.domain.entities.context import ProjectContext
from fastmcp.task_management.infrastructure.database.models import ProjectContext as ProjectContextModel


class TestProjectContextRepository:
    """Test suite for ProjectContextRepository"""
    
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
        return ProjectContextRepository(mock_session_factory, user_id="test-user")
    
    def test_initialization_with_user_id(self, mock_session_factory):
        """Test repository initialization with user ID"""
        user_id = "test-user-123"
        repo = ProjectContextRepository(mock_session_factory, user_id=user_id)
        
        assert repo.user_id == user_id
        assert repo.session_factory == mock_session_factory
        assert repo.model_class == ProjectContextModel
    
    def test_initialization_without_user_id(self, mock_session_factory):
        """Test repository initialization without user ID"""
        repo = ProjectContextRepository(mock_session_factory)
        
        assert repo.user_id is None
        assert repo.session_factory == mock_session_factory
        assert repo.model_class == ProjectContextModel
    
    def test_with_user_creates_new_instance(self, repository):
        """Test with_user creates new scoped repository instance"""
        new_user_id = "new-user-456"
        
        new_repo = repository.with_user(new_user_id)
        
        assert new_repo is not repository
        assert new_repo.user_id == new_user_id
        assert new_repo.session_factory == repository.session_factory
        assert new_repo.model_class == repository.model_class
    
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
    
    def test_create_project_context_success(self, repository, mock_session):
        """Test successful project context creation"""
        # Create entity
        entity = ProjectContext(
            id="project-123",
            project_name="Test Project",
            project_settings={
                "build_tools": ["npm", "webpack"],
                "code_standards": {"eslint": "enabled"},
                "team_conventions": {"naming": "camelCase"}
            }
        )
        
        # Mock database operations
        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            # Mock that no existing entity is found
            mock_session.get.return_value = None

            result = repository.create(entity)

            # Verify session operations
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()
            # Note: session.refresh is commented out in the implementation to avoid UUID conversion issues with SQLite
            # mock_session.refresh.assert_called_once()
    
    def test_get_project_context_found(self, repository, mock_session):
        """Test get retrieves project context successfully"""
        # Mock database model
        mock_model = Mock(
            project_id="project-123",
            project_info={"name": "Test Project"},
            project_settings={
                "build_tools": ["npm"],
                "code_standards": {"eslint": "enabled"}
            },
            team_preferences={},
            technology_stack={},
            project_workflow={},
            local_standards={},
            technical_specifications={},
            global_overrides={},
            delegation_rules={},
            created_at=None,
            updated_at=None
        )
        
        # Mock query - the implementation uses filter().filter().first()
        mock_query = Mock()
        mock_query.filter.return_value.filter.return_value.first.return_value = mock_model
        mock_session.query.return_value = mock_query
        
        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = repository.get("project-123")
            
            assert result is not None
            assert isinstance(result, ProjectContext)
            assert result.id == "project-123"
    
    def test_get_project_context_not_found(self, repository, mock_session):
        """Test get returns None when context not found"""
        mock_query = Mock()
        mock_query.filter.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = repository.get("nonexistent-123")
            
            assert result is None
    
    def test_update_project_context_success(self, repository, mock_session):
        """Test successful project context update"""
        # Create update entity
        entity = ProjectContext(
            id="project-123",
            project_name="Test Project Updated",
            project_settings={
                "build_tools": ["npm", "yarn"],
                "new_setting": "new_value"
            }
        )

        # Mock existing model
        existing_model = Mock(
            id="project-123",
            project_name="Test Project",
            project_settings={"old_setting": "old_value"},
            project_info={},
            team_preferences={},
            technology_stack={},
            project_workflow={},
            local_standards={},
            technical_specifications={},
            global_overrides={},
            delegation_rules={},
            updated_at=None
        )

        # Mock session.get() call (update method uses session.get, not query filters)
        mock_session.get.return_value = existing_model

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = repository.update("project-123", entity)
            
            # Verify updates
            assert existing_model.project_settings == entity.project_settings
            
            mock_session.flush.assert_called_once()
            # Note: session.refresh is commented out in the implementation to avoid UUID conversion issues with SQLite
            # mock_session.refresh.assert_called_once()
    
    def test_update_project_context_not_found(self, repository, mock_session):
        """Test update raises error when context not found"""
        entity = ProjectContext(id="project-123", project_name="Test Project")

        # Mock session.get() to return None (not found)
        mock_session.get.return_value = None

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            with pytest.raises(ValueError) as exc_info:
                repository.update("project-123", entity)
                
            assert "not found" in str(exc_info.value)
    
    def test_delete_project_context_success(self, repository, mock_session):
        """Test successful project context deletion"""
        existing_model = Mock(id="project-123")

        # Mock session.get() to return the existing model
        mock_session.get.return_value = existing_model

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            repository.delete("project-123")

            mock_session.delete.assert_called_once_with(existing_model)
            mock_session.flush.assert_called_once()
    
    def test_delete_project_context_not_found(self, repository, mock_session):
        """Test delete returns False when context not found"""
        # Mock session.get() to return None (not found)
        mock_session.get.return_value = None

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = repository.delete("project-123")

            assert result is False
    
    def test_list_project_contexts(self, repository, mock_session):
        """Test listing project contexts"""
        mock_models = [
            Mock(
                project_id="project-1",
                project_info={"name": "Project 1"},
                project_settings={},
                team_preferences={},
                technology_stack={},
                project_workflow={},
                local_standards={},
                technical_specifications={},
                global_overrides={},
                delegation_rules={},
                created_at=None,
                updated_at=None
            ),
            Mock(
                project_id="project-2",
                project_info={"name": "Project 2"},
                project_settings={},
                team_preferences={},
                technology_stack={},
                project_workflow={},
                local_standards={},
                technical_specifications={},
                global_overrides={},
                delegation_rules={},
                created_at=None,
                updated_at=None
            )
        ]

        # Mock the session.execute() pattern used by the list method
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_models
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = repository.list()

            assert len(result) == 2
            assert all(isinstance(ctx, ProjectContext) for ctx in result)
    
    def test_exists_returns_true(self, repository, mock_session):
        """Test exists returns True when context exists"""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = repository.exists(id="project-123")

            assert result is True
    
    def test_exists_returns_false(self, repository, mock_session):
        """Test exists returns False when context doesn't exist"""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        with patch.object(repository, 'get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = repository.exists(id="project-123")

            assert result is False
    
    def test_repository_isolation_between_users(self, mock_session_factory):
        """Test repositories for different users are isolated"""
        user1_repo = ProjectContextRepository(mock_session_factory, user_id="user1")
        user2_repo = ProjectContextRepository(mock_session_factory, user_id="user2")
        
        assert user1_repo.user_id == "user1"
        assert user2_repo.user_id == "user2"
        assert user1_repo is not user2_repo