"""Tests for SubtaskFacadeFactory"""

import pytest
from unittest.mock import Mock, MagicMock

from fastmcp.task_management.application.factories.subtask_facade_factory import SubtaskFacadeFactory
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.services.repository_provider_service import RepositoryProviderService


class TestSubtaskFacadeFactory:
    """Test suite for SubtaskFacadeFactory"""

    @pytest.fixture
    def mock_repository_provider(self):
        """Create mock repository provider service"""
        provider = Mock(spec=RepositoryProviderService)
        provider.get_task_repository.return_value = Mock()
        provider.get_subtask_repository.return_value = Mock()
        return provider

    @pytest.fixture
    def factory(self, mock_repository_provider):
        """Create factory instance with mocked dependencies"""
        return SubtaskFacadeFactory(repository_provider=mock_repository_provider)

    def test_factory_initialization(self, mock_repository_provider):
        """Test factory initializes correctly with dependencies"""
        factory = SubtaskFacadeFactory(repository_provider=mock_repository_provider)
        
        assert factory._repository_provider == mock_repository_provider

    def test_factory_initialization_minimal(self, mock_repository_provider):
        """Test factory initialization with repository provider"""
        factory = SubtaskFacadeFactory(repository_provider=mock_repository_provider)
        
        assert factory._repository_provider == mock_repository_provider

    def test_create_subtask_facade_basic(self, factory):
        """Test basic subtask facade creation"""
        facade = factory.create_subtask_facade()
        
        assert isinstance(facade, SubtaskApplicationFacade)
        # Verify the facade has access to repositories (through the provider)
        factory._repository_provider.get_task_repository.assert_called_once()
        factory._repository_provider.get_subtask_repository.assert_called_once()

    def test_create_subtask_facade_with_parameters(self, factory):
        """Test subtask facade creation with specific parameters"""
        project_id = "project-123"
        user_id = "user-456"
        
        facade = factory.create_subtask_facade(project_id=project_id, user_id=user_id)
        
        assert isinstance(facade, SubtaskApplicationFacade)
        # Verify parameters were passed to repository provider
        factory._repository_provider.get_task_repository.assert_called_with(
            project_id=project_id, user_id=user_id
        )
        factory._repository_provider.get_subtask_repository.assert_called_with(
            project_id=project_id, user_id=user_id
        )

    def test_create_subtask_facade_default_project(self, factory):
        """Test subtask facade creation with default project"""
        facade = factory.create_subtask_facade()
        
        assert isinstance(facade, SubtaskApplicationFacade)

    def test_create_subtask_facade_user_id_only(self, factory):
        """Test subtask facade creation with user_id only"""
        user_id = "user-789"
        
        facade = factory.create_subtask_facade(user_id=user_id)
        
        assert isinstance(facade, SubtaskApplicationFacade)

    def test_create_subtask_facade_project_id_only(self, factory):
        """Test subtask facade creation with project_id only"""
        project_id = "project-456"
        
        facade = factory.create_subtask_facade(project_id=project_id)
        
        assert isinstance(facade, SubtaskApplicationFacade)

    def test_facade_dependencies_injection(self, factory):
        """Test that facade receives proper dependencies"""
        facade = factory.create_subtask_facade()
        
        # Verify facade has repositories injected (they should be Mock objects from our provider)
        assert facade._task_repository is not None
        assert facade._subtask_repository is not None

    def test_multiple_facade_creation(self, factory):
        """Test creating multiple facades from same factory"""
        facade1 = factory.create_subtask_facade(project_id="project-1", user_id="user-1")
        facade2 = factory.create_subtask_facade(project_id="project-2", user_id="user-2")
        
        assert isinstance(facade1, SubtaskApplicationFacade)
        assert isinstance(facade2, SubtaskApplicationFacade)
        
        # Should be different instances
        assert facade1 is not facade2

    def test_factory_with_none_task_repository_factory(self, mock_repository_provider):
        """Test factory behavior - always requires repository provider"""
        factory = SubtaskFacadeFactory(repository_provider=mock_repository_provider)
        
        facade = factory.create_subtask_facade()
        
        assert isinstance(facade, SubtaskApplicationFacade)
        assert factory._repository_provider == mock_repository_provider

    def test_factory_method_parameters(self, factory):
        """Test factory method parameters and defaults"""
        import inspect
        
        sig = inspect.signature(factory.create_subtask_facade)
        params = sig.parameters
        
        assert 'project_id' in params
        assert 'user_id' in params
        assert 'task_id' in params
        
        # Check default values
        assert params['project_id'].default is None
        assert params['user_id'].default is None
        assert params['task_id'].default is None

    def test_factory_docstring_compliance(self, factory):
        """Test that factory methods have proper documentation"""
        assert factory.create_subtask_facade.__doc__ is not None
        assert "Create a subtask application facade" in factory.create_subtask_facade.__doc__
        
        # Check class docstring
        assert SubtaskFacadeFactory.__doc__ is not None
        assert "Factory for creating subtask application facades" in SubtaskFacadeFactory.__doc__

    def test_factory_dependency_validation(self, mock_repository_provider):
        """Test factory behavior with repository provider"""
        # Test with valid repository provider
        factory = SubtaskFacadeFactory(repository_provider=mock_repository_provider)
        
        assert factory._repository_provider is not None
        assert factory._repository_provider == mock_repository_provider

    def test_facade_creation_consistency(self, factory):
        """Test that facade creation is consistent"""
        facade1 = factory.create_subtask_facade(project_id="test-project", user_id="test-user")
        facade2 = factory.create_subtask_facade(project_id="test-project", user_id="test-user")
        
        # Should create different instances
        assert facade1 is not facade2
        
        # But both should be proper SubtaskApplicationFacade instances
        assert isinstance(facade1, SubtaskApplicationFacade)
        assert isinstance(facade2, SubtaskApplicationFacade)

    def test_factory_init_parameter_storage(self, mock_repository_provider):
        """Test that factory stores initialization parameters correctly"""
        factory = SubtaskFacadeFactory(repository_provider=mock_repository_provider)
        
        # Verify repository provider is stored correctly
        assert factory._repository_provider is mock_repository_provider

    def test_factory_facade_type_verification(self, factory):
        """Test that factory creates correct facade type"""
        facade = factory.create_subtask_facade()
        
        # Verify it's the correct type
        assert type(facade).__name__ == "SubtaskApplicationFacade"
        assert hasattr(facade, '_task_repository')
        assert hasattr(facade, '_subtask_repository')

    def test_factory_parameter_passing_behavior(self, factory):
        """Test parameter passing behavior in factory method"""
        project_id = "specific-project"
        user_id = "specific-user"
        task_id = "specific-task"
        
        facade = factory.create_subtask_facade(
            project_id=project_id, 
            user_id=user_id, 
            task_id=task_id
        )
        
        # Facade should be created successfully
        assert isinstance(facade, SubtaskApplicationFacade)
        
        # Verify parameters were passed to repository provider calls
        factory._repository_provider.get_task_repository.assert_called_with(
            project_id=project_id, user_id=user_id
        )
        factory._repository_provider.get_subtask_repository.assert_called_with(
            project_id=project_id, user_id=user_id
        )

    def test_get_instance_singleton_pattern(self):
        """Test the singleton pattern of get_instance method"""
        instance1 = SubtaskFacadeFactory.get_instance()
        instance2 = SubtaskFacadeFactory.get_instance()
        
        # Should return the same instance
        assert instance1 is instance2
        assert isinstance(instance1, SubtaskFacadeFactory)

    def test_create_facade_alias_method(self, factory):
        """Test that create_facade method works as alias"""
        facade = factory.create_facade(project_id="test-project")
        
        assert isinstance(facade, SubtaskApplicationFacade)
        # Should call same underlying method
        factory._repository_provider.get_task_repository.assert_called()
        factory._repository_provider.get_subtask_repository.assert_called()