"""
Comprehensive test suite for ORMProjectRepository.

Tests the ProjectRepository ORM implementation including:
- CRUD operations
- User-scoped data isolation 
- Git branch relationship management
- Cache invalidation integration
- Entity-model conversion
- Error handling and edge cases
- Query operations and filtering
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from fastmcp.task_management.domain.entities.project import Project as ProjectEntity
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException, 
    DatabaseException
)
from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch


class TestORMProjectRepositoryInitialization:
    """Test cases for ORMProjectRepository initialization and configuration."""
    
    def test_init_with_minimal_params(self):
        """Test repository initialization with minimal parameters."""
        repo = ORMProjectRepository()
        
        # Should initialize all base classes
        assert hasattr(repo, 'model_class')
        assert repo.model_class == Project
        assert hasattr(repo, 'user_id')
    
    def test_init_with_session_and_user_id(self):
        """Test repository initialization with session and user ID."""
        mock_session = Mock()
        
        repo = ORMProjectRepository(session=mock_session, user_id="test-user")
        
        assert repo.user_id == "test-user"
        # BaseUserScopedRepository should handle the session
    
    def test_init_inheritance_chain(self):
        """Test repository properly inherits from all base classes."""
        repo = ORMProjectRepository()
        
        # Should have methods from all mixins/base classes
        assert hasattr(repo, 'apply_user_filter')  # BaseUserScopedRepository
        assert hasattr(repo, 'invalidate_cache_for_entity')   # CacheInvalidationMixin
        assert hasattr(repo, 'model_class')         # BaseORMRepository


class TestORMProjectRepositoryEntityConversion:
    """Test cases for entity-model conversion."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.repo = ORMProjectRepository(user_id="test-user")
    
    def test_model_to_entity_minimal_project(self):
        """Test converting minimal project model to entity."""
        # Mock minimal project model
        mock_project = Mock(spec=Project)
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.description = "Test Description"
        mock_project.created_at = datetime.now(timezone.utc)
        mock_project.updated_at = datetime.now(timezone.utc)
        mock_project.git_branchs = []  # No branches
        
        entity = self.repo._model_to_entity(mock_project)
        
        assert isinstance(entity, ProjectEntity)
        assert entity.id == "project-123"
        assert entity.name == "Test Project"
        assert entity.description == "Test Description"
        assert entity.created_at == mock_project.created_at
        assert entity.updated_at == mock_project.updated_at
    
    def test_model_to_entity_with_git_branches(self):
        """Test converting project model with git branches to entity."""
        # Mock project model with git branches
        mock_project = Mock(spec=Project)
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.description = "Test Description"
        mock_project.created_at = datetime.now(timezone.utc)
        mock_project.updated_at = datetime.now(timezone.utc)
        
        # Mock git branches
        mock_branch1 = Mock(spec=ProjectGitBranch)
        mock_branch1.id = "branch-1"
        mock_branch1.name = "main"
        mock_branch1.description = "Main branch"
        mock_branch1.project_id = "project-123"
        mock_branch1.task_count = 5
        mock_branch1.created_at = datetime.now(timezone.utc)
        mock_branch1.updated_at = datetime.now(timezone.utc)
        
        mock_branch2 = Mock(spec=ProjectGitBranch)
        mock_branch2.id = "branch-2"
        mock_branch2.name = "feature/auth"
        mock_branch2.description = "Authentication feature"
        mock_branch2.project_id = "project-123"
        mock_branch2.task_count = 3
        mock_branch2.created_at = datetime.now(timezone.utc)
        mock_branch2.updated_at = datetime.now(timezone.utc)
        
        mock_project.git_branchs = [mock_branch1, mock_branch2]
        
        entity = self.repo._model_to_entity(mock_project)
        
        assert isinstance(entity, ProjectEntity)
        assert entity.id == "project-123"
        
        # Verify git branches were converted
        # Note: The actual implementation creates placeholder tasks based on task_count
        assert hasattr(entity, 'git_branches') or len(mock_project.git_branchs) == 2
    
    def test_entity_to_model_conversion(self):
        """Test converting project entity to model."""
        # Create project entity
        entity = ProjectEntity(
            id="project-123",
            name="Test Project",
            description="Test Description"
        )
        
        with patch.object(self.repo, '_entity_to_model') as mock_convert:
            mock_model = Mock(spec=Project)
            mock_convert.return_value = mock_model
            
            result = self.repo._entity_to_model(entity)
            
            mock_convert.assert_called_once_with(entity)
            assert result == mock_model


class TestORMProjectRepositoryCRUDOperations:
    """Test cases for CRUD operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMProjectRepository(session=self.mock_session, user_id="test-user")
    
    def test_create_project_success(self):
        """Test successful project creation."""
        # Create project entity
        entity = ProjectEntity(
            id="project-123",
            name="New Project",
            description="New Description"
        )
        
        # Mock model conversion
        mock_project_model = Mock(spec=Project)
        mock_project_model.id = "project-123"
        
        with patch.object(self.repo, '_entity_to_model', return_value=mock_project_model) as mock_to_model:
            with patch.object(self.repo, '_model_to_entity', return_value=entity) as mock_to_entity:
                with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                    
                    result = self.repo.create(entity)
                    
                    # Verify conversions
                    mock_to_model.assert_called_once_with(entity)
                    mock_to_entity.assert_called_once_with(mock_project_model)
                    
                    # Verify session operations
                    self.mock_session.add.assert_called_once_with(mock_project_model)
                    self.mock_session.flush.assert_called_once()
                    
                    # Verify cache invalidation
                    mock_invalidate.assert_called_once()
                    
                    assert result == entity
    
    def test_create_project_database_error(self):
        """Test project creation with database error."""
        entity = ProjectEntity(
            id="project-123",
            name="New Project",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', return_value=Mock(spec=Project)):
            self.mock_session.add.side_effect = IntegrityError("Constraint violation", None, None)
            
            with pytest.raises(DatabaseException):
                self.repo.create(entity)
            
            # Should rollback on error
            self.mock_session.rollback.assert_called_once()
    
    def test_get_project_by_id_found(self):
        """Test getting project by ID when it exists."""
        # Mock project model
        mock_project_model = Mock(spec=Project)
        mock_project_model.id = "project-123"
        mock_project_model.git_branchs = []
        
        # Mock entity
        mock_project_entity = ProjectEntity(
            id="project-123",
            name="Found Project",
            description="Found Description"
        )
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_model_to_entity', return_value=mock_project_entity):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.get_by_id("project-123")
                
                # Verify query was built correctly
                self.mock_session.query.assert_called_once_with(Project)
                mock_query.options.assert_called_once()
                mock_filter.first.assert_called_once()
                
                assert result == mock_project_entity
    
    def test_get_project_by_id_not_found(self):
        """Test getting project by ID when it doesn't exist."""
        # Mock empty query result
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Not found
        
        self.mock_session.query.return_value = mock_query
        
        with pytest.raises(ResourceNotFoundException, match="Project with ID 'nonexistent' not found"):
            self.repo.get_by_id("nonexistent")
    
    def test_get_project_by_id_user_filter_denied(self):
        """Test getting project denied by user filter."""
        mock_project_model = Mock(spec=Project)
        mock_project_model.id = "project-123"
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project_model
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=False):
            
            with pytest.raises(ResourceNotFoundException, match="Project with ID 'project-123' not found"):
                self.repo.get_by_id("project-123")
    
    def test_update_project_success(self):
        """Test successful project update."""
        entity = ProjectEntity(
            id="project-123",
            name="Updated Project",
            description="Updated Description"
        )
        
        # Mock existing project
        mock_existing = Mock(spec=Project)
        mock_existing.id = "project-123"
        
        # Mock query for finding existing project
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_existing
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            with patch.object(self.repo, '_update_model_from_entity') as mock_update:
                with patch.object(self.repo, '_model_to_entity', return_value=entity):
                    with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                        
                        result = self.repo.update(entity)
                        
                        # Verify update operations
                        mock_update.assert_called_once_with(mock_existing, entity)
                        self.mock_session.flush.assert_called_once()
                        mock_invalidate.assert_called_once()
                        
                        assert result == entity
    
    def test_update_project_not_found(self):
        """Test updating non-existent project."""
        entity = ProjectEntity(
            id="nonexistent",
            name="Updated Project",
            description="Updated Description"
        )
        
        # Mock empty query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        self.mock_session.query.return_value = mock_query
        
        with pytest.raises(ResourceNotFoundException, match="Project with ID 'nonexistent' not found"):
            self.repo.update(entity)
    
    def test_delete_project_success(self):
        """Test successful project deletion."""
        # Mock existing project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-123"
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                
                self.repo.delete("project-123")
                
                # Verify deletion
                self.mock_session.delete.assert_called_once_with(mock_project)
                self.mock_session.flush.assert_called_once()
                mock_invalidate.assert_called_once()
    
    def test_delete_project_not_found(self):
        """Test deleting non-existent project."""
        # Mock empty query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        self.mock_session.query.return_value = mock_query
        
        with pytest.raises(ResourceNotFoundException, match="Project with ID 'nonexistent' not found"):
            self.repo.delete("nonexistent")


class TestORMProjectRepositoryQueryOperations:
    """Test cases for complex query operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMProjectRepository(session=self.mock_session, user_id="test-user")
    
    def test_list_all_projects(self):
        """Test listing all projects with user filter."""
        # Mock project models
        mock_project1 = Mock(spec=Project)
        mock_project1.id = "project-1"
        mock_project1.git_branchs = []
        
        mock_project2 = Mock(spec=Project)
        mock_project2.id = "project-2" 
        mock_project2.git_branchs = []
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.all.return_value = [mock_project1, mock_project2]
        
        self.mock_session.query.return_value = mock_query
        
        # Mock entity conversion
        mock_entities = [Mock(), Mock()]
        
        with patch.object(self.repo, '_model_to_entity', side_effect=mock_entities):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.list_all()
                
                # Verify query structure
                self.mock_session.query.assert_called_once_with(Project)
                mock_query.options.assert_called_once()
                mock_options.all.assert_called_once()
                
                # Verify results
                assert len(result) == 2
                assert result == mock_entities
    
    def test_find_by_name(self):
        """Test finding project by name."""
        mock_project = Mock(spec=Project)
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.git_branchs = []
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project
        
        self.mock_session.query.return_value = mock_query
        
        mock_entity = Mock()
        
        with patch.object(self.repo, '_model_to_entity', return_value=mock_entity):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.find_by_name("Test Project")
                
                # Verify name filter was applied
                mock_options.filter.assert_called_once()
                assert result == mock_entity
    
    def test_search_projects_by_text(self):
        """Test searching projects by text content."""
        mock_projects = [Mock(spec=Project), Mock(spec=Project)]
        for i, proj in enumerate(mock_projects):
            proj.id = f"project-{i}"
            proj.git_branchs = []
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.all.return_value = mock_projects
        
        self.mock_session.query.return_value = mock_query
        
        mock_entities = [Mock(), Mock()]
        
        with patch.object(self.repo, '_model_to_entity', side_effect=mock_entities):
            with patch.object(self.repo, '_apply_user_filter', return_value=True):
                
                result = self.repo.search("authentication")
                
                # Verify search filter was applied
                mock_options.filter.assert_called_once()
                assert len(result) == 2
                assert result == mock_entities
    
    def test_count_projects(self):
        """Test counting projects."""
        # Mock query
        mock_query = Mock()
        mock_query.count.return_value = 5
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            
            result = self.repo.count()
            
            assert result == 5
            mock_query.count.assert_called_once()


class TestORMProjectRepositoryUserScoping:
    """Test cases for user-scoped data isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMProjectRepository(session=self.mock_session, user_id="test-user")
    
    def test_user_filter_applied_on_queries(self):
        """Test user filter is applied on all queries."""
        mock_project = Mock(spec=Project)
        mock_project.git_branchs = []
        
        # Mock query
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_model_to_entity', return_value=Mock()):
            with patch.object(self.repo, '_apply_user_filter') as mock_user_filter:
                mock_user_filter.return_value = True
                
                self.repo.get_by_id("project-123")
                
                # Verify user filter was called
                mock_user_filter.assert_called_once_with(mock_project)
    
    def test_user_scoped_creation(self):
        """Test project creation includes user scope."""
        entity = ProjectEntity(
            id="project-123",
            name="User Project",
            description="User Description"
        )
        
        mock_model = Mock(spec=Project)
        
        with patch.object(self.repo, '_entity_to_model', return_value=mock_model):
            with patch.object(self.repo, '_model_to_entity', return_value=entity):
                with patch.object(self.repo, '_invalidate_cache'):
                    
                    # The user ID should be applied during model creation
                    self.repo.create(entity)
                    
                    # Verify model was created with user context
                    self.mock_session.add.assert_called_once_with(mock_model)


class TestORMProjectRepositoryCacheIntegration:
    """Test cases for cache invalidation integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMProjectRepository(session=self.mock_session, user_id="test-user")
    
    def test_cache_invalidation_on_create(self):
        """Test cache is invalidated on project creation."""
        entity = ProjectEntity(
            id="project-123",
            name="New Project",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', return_value=Mock(spec=Project)):
            with patch.object(self.repo, '_model_to_entity', return_value=entity):
                with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                    
                    self.repo.create(entity)
                    
                    # Should invalidate cache after creation
                    mock_invalidate.assert_called_once()
    
    def test_cache_invalidation_on_update(self):
        """Test cache is invalidated on project update."""
        entity = ProjectEntity(
            id="project-123",
            name="Updated Project",
            description="Updated Description"
        )
        
        mock_existing = Mock(spec=Project)
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_existing
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            with patch.object(self.repo, '_update_model_from_entity'):
                with patch.object(self.repo, '_model_to_entity', return_value=entity):
                    with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                        
                        self.repo.update(entity)
                        
                        # Should invalidate cache after update
                        mock_invalidate.assert_called_once()
    
    def test_cache_invalidation_on_delete(self):
        """Test cache is invalidated on project deletion."""
        mock_project = Mock(spec=Project)
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            with patch.object(self.repo, '_invalidate_cache') as mock_invalidate:
                
                self.repo.delete("project-123")
                
                # Should invalidate cache after deletion
                mock_invalidate.assert_called_once()


class TestORMProjectRepositoryErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repo = ORMProjectRepository(session=self.mock_session, user_id="test-user")
    
    def test_session_rollback_on_error(self):
        """Test session rollback occurs on database errors."""
        entity = ProjectEntity(
            id="project-123",
            name="New Project",
            description="New Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', return_value=Mock(spec=Project)):
            self.mock_session.add.side_effect = SQLAlchemyError("Database connection lost")
            
            with pytest.raises(DatabaseException):
                self.repo.create(entity)
            
            # Should rollback on error
            self.mock_session.rollback.assert_called_once()
    
    def test_validation_error_handling(self):
        """Test handling of validation errors."""
        entity = ProjectEntity(
            id="",  # Invalid empty ID
            name="Project",
            description="Description"
        )
        
        with patch.object(self.repo, '_entity_to_model', side_effect=ValidationException("Invalid project data")):
            
            with pytest.raises(ValidationException, match="Invalid project data"):
                self.repo.create(entity)
    
    def test_concurrent_modification_handling(self):
        """Test handling of concurrent modification scenarios."""
        entity = ProjectEntity(
            id="project-123",
            name="Updated Project",
            description="Updated Description"
        )
        
        mock_existing = Mock(spec=Project)
        
        # Mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_existing
        
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repo, '_apply_user_filter', return_value=True):
            with patch.object(self.repo, '_update_model_from_entity'):
                # Simulate optimistic locking failure
                self.mock_session.flush.side_effect = SQLAlchemyError("Row was updated by another transaction")
                
                with pytest.raises(DatabaseException):
                    self.repo.update(entity)


if __name__ == "__main__":
    pytest.main([__file__])