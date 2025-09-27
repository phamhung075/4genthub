"""
Tests for Project Service Factory

This module tests the ProjectServiceFactory functionality including:
- Service creation with dependency injection
- Repository configuration and selection
- User-specific service creation
- Legacy support functions
- Environment-based configuration
- SQLite service creation
"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.task_management.infrastructure.factories.project_service_factory import (
    ProjectServiceFactory,
    create_project_service_factory,
    create_default_project_service,
    create_project_service_for_user,
    create_sqlite_project_service
)
from fastmcp.task_management.application.services.project_management_service import ProjectManagementService
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.infrastructure.utilities.path_resolver import PathResolver
from fastmcp.task_management.infrastructure.repositories.project_repository_factory import RepositoryConfig


class TestProjectServiceFactory:
    """Test suite for ProjectServiceFactory"""
    
    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver"""
        return Mock(spec=PathResolver)
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        return Mock()
    
    @pytest.fixture
    def factory(self, mock_path_resolver, mock_project_repository):
        """Create factory instance with mocked dependencies"""
        return ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=mock_project_repository
        )
    
    @pytest.fixture
    def factory_no_repo(self, mock_path_resolver):
        """Create factory instance without repository (will use defaults)"""
        return ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=None
        )
    
    def test_factory_initialization(self, factory, mock_path_resolver, mock_project_repository):
        """Test factory initialization with dependencies"""
        assert factory._path_resolver == mock_path_resolver
        assert factory._project_repository == mock_project_repository
    
    def test_create_project_service_with_repository(self, factory, mock_project_repository):
        """Test creating project management service with provided repository"""
        service = factory.create_project_service()
        
        assert isinstance(service, ProjectManagementService)
        # Verify the service was created with the provided repository
        assert service._project_repo == mock_project_repository
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.get_default_repository')
    def test_create_project_service_without_repository(self, mock_get_default_repo, factory_no_repo):
        """Test creating project management service without provided repository"""
        mock_default_repo = Mock()
        mock_get_default_repo.return_value = mock_default_repo
        
        service = factory_no_repo.create_project_service()
        
        assert isinstance(service, ProjectManagementService)
        mock_get_default_repo.assert_called_once()
        assert service._project_repo == mock_default_repo
    
    def test_create_project_application_service_with_repository(self, factory, mock_project_repository):
        """Test creating project application service with provided repository"""
        service = factory.create_project_application_service(user_id="user-123")
        
        assert isinstance(service, ProjectApplicationService)
        assert service._project_repository == mock_project_repository
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.ProjectRepositoryFactory')
    def test_create_project_application_service_without_repository(self, mock_repo_factory, factory_no_repo):
        """Test creating project application service without provided repository"""
        mock_repo = Mock()
        mock_repo_factory.create.return_value = mock_repo
        
        service = factory_no_repo.create_project_application_service(user_id="user-123")
        
        assert isinstance(service, ProjectApplicationService)
        mock_repo_factory.create.assert_called_once_with(user_id="user-123")
        assert service._project_repository == mock_repo
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.get_sqlite_repository')
    def test_create_sqlite_service(self, mock_get_sqlite_repo, factory):
        """Test creating SQLite service"""
        mock_sqlite_repo = Mock()
        mock_get_sqlite_repo.return_value = mock_sqlite_repo
        
        service = factory.create_sqlite_service(user_id="user-123", db_path="/test/db.sqlite")
        
        assert isinstance(service, ProjectApplicationService)
        mock_get_sqlite_repo.assert_called_once_with(user_id="user-123", db_path="/test/db.sqlite")
        assert service._project_repository == mock_sqlite_repo
    
    def test_create_service_from_config(self, factory):
        """Test creating service from repository configuration"""
        mock_config = Mock(spec=RepositoryConfig)
        mock_repo = Mock()
        mock_config.create_repository.return_value = mock_repo
        
        service = factory.create_service_from_config(mock_config)
        
        assert isinstance(service, ProjectApplicationService)
        mock_config.create_repository.assert_called_once()
        assert service._project_repository == mock_repo
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.RepositoryConfig')
    def test_create_service_from_environment(self, mock_repo_config, factory):
        """Test creating service from environment configuration"""
        mock_config_instance = Mock(spec=RepositoryConfig)
        mock_repo_config.from_environment.return_value = mock_config_instance
        mock_repo = Mock()
        mock_config_instance.create_repository.return_value = mock_repo
        
        service = factory.create_service_from_environment(user_id="user-123")
        
        assert isinstance(service, ProjectApplicationService)
        mock_repo_config.from_environment.assert_called_once()
        assert mock_config_instance.user_id == "user-123"
        assert service._project_repository == mock_repo
    
    def test_set_project_repository(self, factory):
        """Test setting project repository"""
        new_repo = Mock()
        factory.set_project_repository(new_repo)
        
        assert factory._project_repository == new_repo
    
    def test_get_project_repository(self, factory, mock_project_repository):
        """Test getting project repository"""
        assert factory.get_project_repository() == mock_project_repository
    
    def test_get_project_repository_none(self, factory_no_repo):
        """Test getting project repository when none set"""
        assert factory_no_repo.get_project_repository() is None
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.get_default_repository')
    def test_get_default_repository_with_repo(self, mock_get_default, factory):
        """Test _get_default_repository when repository is already set"""
        result = factory._get_default_repository()
        
        assert result == factory._project_repository
        mock_get_default.assert_not_called()
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.get_default_repository')
    def test_get_default_repository_without_repo(self, mock_get_default, factory_no_repo):
        """Test _get_default_repository when no repository is set"""
        mock_default_repo = Mock()
        mock_get_default.return_value = mock_default_repo
        
        result = factory_no_repo._get_default_repository()
        
        assert result == mock_default_repo
        mock_get_default.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.ProjectRepositoryFactory')
    def test_get_repository_for_user_with_repo(self, mock_repo_factory, factory):
        """Test _get_repository_for_user when repository is already set"""
        result = factory._get_repository_for_user("user-123")
        
        assert result == factory._project_repository
        mock_repo_factory.create.assert_not_called()
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.ProjectRepositoryFactory')
    def test_get_repository_for_user_without_repo(self, mock_repo_factory, factory_no_repo):
        """Test _get_repository_for_user when no repository is set"""
        mock_user_repo = Mock()
        mock_repo_factory.create.return_value = mock_user_repo
        
        result = factory_no_repo._get_repository_for_user("user-123")
        
        assert result == mock_user_repo
        mock_repo_factory.create.assert_called_once_with(user_id="user-123")


class TestProjectServiceFactoryConvenienceFunctions:
    """Test suite for convenience factory functions"""
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.PathResolver')
    def test_create_project_service_factory_default(self, mock_path_resolver_class):
        """Test creating factory with default dependencies"""
        mock_path_resolver_instance = Mock()
        mock_path_resolver_class.return_value = mock_path_resolver_instance
        
        factory = create_project_service_factory()
        
        assert isinstance(factory, ProjectServiceFactory)
        assert factory._path_resolver == mock_path_resolver_instance
        assert factory._project_repository is None
    
    def test_create_project_service_factory_with_dependencies(self):
        """Test creating factory with provided dependencies"""
        mock_path_resolver = Mock(spec=PathResolver)
        mock_repo = Mock()
        
        factory = create_project_service_factory(
            path_resolver=mock_path_resolver,
            project_repository=mock_repo
        )
        
        assert isinstance(factory, ProjectServiceFactory)
        assert factory._path_resolver == mock_path_resolver
        assert factory._project_repository == mock_repo
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.create_project_service_factory')
    def test_create_default_project_service(self, mock_create_factory):
        """Test creating default project service"""
        mock_factory = Mock()
        mock_service = Mock(spec=ProjectApplicationService)
        mock_factory.create_project_application_service.return_value = mock_service
        mock_create_factory.return_value = mock_factory
        
        service = create_default_project_service()
        
        assert service == mock_service
        mock_create_factory.assert_called_once()
        mock_factory.create_project_application_service.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.create_project_service_factory')
    def test_create_project_service_for_user(self, mock_create_factory):
        """Test creating project service for specific user"""
        mock_factory = Mock()
        mock_service = Mock(spec=ProjectApplicationService)
        mock_factory.create_project_application_service.return_value = mock_service
        mock_create_factory.return_value = mock_factory
        
        service = create_project_service_for_user("user-123")
        
        assert service == mock_service
        mock_create_factory.assert_called_once()
        mock_factory.create_project_application_service.assert_called_once_with(user_id="user-123")
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.create_project_service_factory')
    def test_create_sqlite_project_service(self, mock_create_factory):
        """Test creating SQLite project service"""
        mock_factory = Mock()
        mock_service = Mock(spec=ProjectApplicationService)
        mock_factory.create_sqlite_service.return_value = mock_service
        mock_create_factory.return_value = mock_factory
        
        service = create_sqlite_project_service(user_id="user-123", db_path="/test/db.sqlite")
        
        assert service == mock_service
        mock_create_factory.assert_called_once()
        mock_factory.create_sqlite_service.assert_called_once_with(
            user_id="user-123", 
            db_path="/test/db.sqlite"
        )
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.create_project_service_factory')
    def test_create_sqlite_project_service_defaults(self, mock_create_factory):
        """Test creating SQLite project service with defaults"""
        mock_factory = Mock()
        mock_service = Mock(spec=ProjectApplicationService)
        mock_factory.create_sqlite_service.return_value = mock_service
        mock_create_factory.return_value = mock_factory
        
        service = create_sqlite_project_service()
        
        assert service == mock_service
        mock_create_factory.assert_called_once()
        mock_factory.create_sqlite_service.assert_called_once_with(
            user_id=None, 
            db_path=None
        )


class TestProjectServiceFactoryIntegration:
    """Test suite for integration scenarios"""
    
    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver"""
        return Mock(spec=PathResolver)
    
    def test_dependency_injection_flow(self, mock_path_resolver):
        """Test complete dependency injection flow"""
        # Create factory with path resolver but no repository
        factory = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=None
        )
        
        # Inject a repository
        mock_repo = Mock()
        factory.set_project_repository(mock_repo)
        
        # Create service - should use injected repository
        service = factory.create_project_application_service()
        
        assert isinstance(service, ProjectApplicationService)
        assert service._project_repository == mock_repo
        assert factory.get_project_repository() == mock_repo
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.get_default_repository')
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.ProjectRepositoryFactory')
    def test_repository_selection_priority(self, mock_repo_factory, mock_get_default, mock_path_resolver):
        """Test repository selection priority order"""
        # Setup mocks
        mock_injected_repo = Mock()
        mock_user_repo = Mock()
        mock_default_repo = Mock()
        
        mock_repo_factory.create.return_value = mock_user_repo
        mock_get_default.return_value = mock_default_repo
        
        # Test 1: With injected repository - should use injected
        factory = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=mock_injected_repo
        )
        
        service = factory.create_project_application_service(user_id="user-123")
        assert service._project_repository == mock_injected_repo
        
        # Test 2: Without injected repository - should create user-specific
        factory_no_repo = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=None
        )
        
        service = factory_no_repo.create_project_application_service(user_id="user-123")
        assert service._project_repository == mock_user_repo
        mock_repo_factory.create.assert_called_with(user_id="user-123")
    
    def test_legacy_and_modern_service_creation(self, mock_path_resolver):
        """Test both legacy and modern service creation methods"""
        mock_repo = Mock()
        factory = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=mock_repo
        )
        
        # Legacy service creation
        legacy_service = factory.create_project_service()
        assert isinstance(legacy_service, ProjectManagementService)
        
        # Modern service creation
        modern_service = factory.create_project_application_service()
        assert isinstance(modern_service, ProjectApplicationService)
        
        # Both should use the same repository
        assert legacy_service._project_repo == mock_repo
        assert modern_service._project_repository == mock_repo


class TestProjectServiceFactoryErrorHandling:
    """Test suite for error handling scenarios"""
    
    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver"""
        return Mock(spec=PathResolver)
    
    def test_factory_with_none_path_resolver(self):
        """Test factory behavior with None path resolver"""
        # This should not raise an error during initialization
        factory = ProjectServiceFactory(
            path_resolver=None,
            project_repository=None
        )
        
        assert factory._path_resolver is None
        assert factory._project_repository is None
    
    @patch('fastmcp.task_management.infrastructure.factories.project_service_factory.RepositoryConfig')
    def test_create_service_from_environment_error_handling(self, mock_repo_config, mock_path_resolver):
        """Test error handling in create_service_from_environment"""
        # Mock config creation failure
        mock_repo_config.from_environment.side_effect = Exception("Environment error")
        
        factory = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=None
        )
        
        with pytest.raises(Exception, match="Environment error"):
            factory.create_service_from_environment(user_id="user-123")
    
    def test_create_service_from_config_with_invalid_config(self, mock_path_resolver):
        """Test creating service with invalid config"""
        invalid_config = Mock()
        invalid_config.create_repository.side_effect = Exception("Invalid config")
        
        factory = ProjectServiceFactory(
            path_resolver=mock_path_resolver,
            project_repository=None
        )
        
        with pytest.raises(Exception, match="Invalid config"):
            factory.create_service_from_config(invalid_config)


class TestProjectServiceFactoryModuleExports:
    """Test suite for module exports"""
    
    def test_module_exports(self):
        """Test that all expected functions and classes are exported"""
        from fastmcp.task_management.infrastructure.factories.project_service_factory import __all__
        
        expected_exports = [
            "ProjectServiceFactory",
            "create_project_service_factory",
            "create_default_project_service",
            "create_project_service_for_user",
            "create_sqlite_project_service"
        ]
        
        assert __all__ == expected_exports
    
    def test_all_exports_are_importable(self):
        """Test that all exported functions and classes can be imported"""
        from fastmcp.task_management.infrastructure.factories.project_service_factory import (
            ProjectServiceFactory,
            create_project_service_factory,
            create_default_project_service,
            create_project_service_for_user,
            create_sqlite_project_service
        )
        
        # All imports should succeed without errors
        assert ProjectServiceFactory is not None
        assert create_project_service_factory is not None
        assert create_default_project_service is not None
        assert create_project_service_for_user is not None
        assert create_sqlite_project_service is not None