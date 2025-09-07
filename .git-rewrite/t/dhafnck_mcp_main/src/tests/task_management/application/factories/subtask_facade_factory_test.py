"""Tests for SubtaskFacadeFactory"""

import pytest
from unittest.mock import Mock, MagicMock

from fastmcp.task_management.application.factories.subtask_facade_factory import SubtaskFacadeFactory
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade


class TestSubtaskFacadeFactory:
    """Test suite for SubtaskFacadeFactory"""

    @pytest.fixture
    def mock_subtask_repository_factory(self):
        """Create mock subtask repository factory"""
        factory = Mock()
        factory.create_repository.return_value = Mock()
        return factory

    @pytest.fixture
    def mock_task_repository_factory(self):
        """Create mock task repository factory"""
        factory = Mock()
        factory.create_repository.return_value = Mock()
        return factory

    @pytest.fixture
    def factory(self, mock_subtask_repository_factory, mock_task_repository_factory):
        """Create factory instance with mocked dependencies"""
        return SubtaskFacadeFactory(
            subtask_repository_factory=mock_subtask_repository_factory,
            task_repository_factory=mock_task_repository_factory
        )

    def test_factory_initialization(self, mock_subtask_repository_factory, mock_task_repository_factory):
        """Test factory initializes correctly with dependencies"""
        factory = SubtaskFacadeFactory(
            subtask_repository_factory=mock_subtask_repository_factory,
            task_repository_factory=mock_task_repository_factory
        )
        
        assert factory._subtask_repository_factory == mock_subtask_repository_factory
        assert factory._task_repository_factory == mock_task_repository_factory

    def test_factory_initialization_minimal(self, mock_subtask_repository_factory):
        """Test factory initialization with minimal parameters"""
        factory = SubtaskFacadeFactory(
            subtask_repository_factory=mock_subtask_repository_factory
        )
        
        assert factory._subtask_repository_factory == mock_subtask_repository_factory
        assert factory._task_repository_factory is None

    def test_create_subtask_facade_basic(self, factory):
        """Test basic subtask facade creation"""
        facade = factory.create_subtask_facade()
        
        assert isinstance(facade, SubtaskApplicationFacade)
        assert hasattr(facade, '_task_repository_factory')
        assert hasattr(facade, '_subtask_repository_factory')

    def test_create_subtask_facade_with_parameters(self, factory):
        """Test subtask facade creation with specific parameters"""
        project_id = "project-123"
        user_id = "user-456"
        
        facade = factory.create_subtask_facade(project_id=project_id, user_id=user_id)
        
        assert isinstance(facade, SubtaskApplicationFacade)
        # Parameters are passed but facade stores the factory references, not the specific values

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
        
        # Verify facade has access to the repository factories
        assert facade._task_repository_factory == factory._task_repository_factory
        assert facade._subtask_repository_factory == factory._subtask_repository_factory

    def test_multiple_facade_creation(self, factory):
        """Test creating multiple facades from same factory"""
        facade1 = factory.create_subtask_facade("project-1", "user-1")
        facade2 = factory.create_subtask_facade("project-2", "user-2")
        
        assert isinstance(facade1, SubtaskApplicationFacade)
        assert isinstance(facade2, SubtaskApplicationFacade)
        
        # Should be different instances
        assert facade1 is not facade2
        
        # But should have same repository factories
        assert facade1._task_repository_factory == facade2._task_repository_factory
        assert facade1._subtask_repository_factory == facade2._subtask_repository_factory

    def test_factory_with_none_task_repository_factory(self, mock_subtask_repository_factory):
        """Test factory behavior when task repository factory is None"""
        factory = SubtaskFacadeFactory(
            subtask_repository_factory=mock_subtask_repository_factory,
            task_repository_factory=None
        )
        
        facade = factory.create_subtask_facade()
        
        assert isinstance(facade, SubtaskApplicationFacade)
        assert facade._task_repository_factory is None
        assert facade._subtask_repository_factory == mock_subtask_repository_factory

    def test_factory_method_parameters(self, factory):
        """Test factory method parameters and defaults"""
        import inspect
        
        sig = inspect.signature(factory.create_subtask_facade)
        params = sig.parameters
        
        assert 'project_id' in params
        assert 'user_id' in params
        
        # Check default values
        assert params['project_id'].default == "default_project"
        assert params['user_id'].default is None

    def test_factory_docstring_compliance(self, factory):
        """Test that factory methods have proper documentation"""
        assert factory.create_subtask_facade.__doc__ is not None
        assert "Create a subtask application facade" in factory.create_subtask_facade.__doc__
        
        # Check class docstring
        assert SubtaskFacadeFactory.__doc__ is not None
        assert "Factory for creating subtask application facades" in SubtaskFacadeFactory.__doc__

    def test_factory_dependency_validation(self):
        """Test factory behavior with invalid dependencies"""
        # Test with None subtask repository factory (should be allowed to initialize)
        factory = SubtaskFacadeFactory(
            subtask_repository_factory=None,
            task_repository_factory=Mock()
        )
        
        assert factory._subtask_repository_factory is None
        assert factory._task_repository_factory is not None

    def test_facade_creation_consistency(self, factory):
        """Test that facade creation is consistent"""
        facade1 = factory.create_subtask_facade("test-project", "test-user")
        facade2 = factory.create_subtask_facade("test-project", "test-user")
        
        # Should create different instances
        assert facade1 is not facade2
        
        # But with same factory dependencies
        assert facade1._subtask_repository_factory is facade2._subtask_repository_factory
        assert facade1._task_repository_factory is facade2._task_repository_factory

    def test_factory_init_parameter_storage(self, mock_subtask_repository_factory, mock_task_repository_factory):
        """Test that factory stores initialization parameters correctly"""
        factory = SubtaskFacadeFactory(
            subtask_repository_factory=mock_subtask_repository_factory,
            task_repository_factory=mock_task_repository_factory
        )
        
        # Verify references are stored correctly
        assert factory._subtask_repository_factory is mock_subtask_repository_factory
        assert factory._task_repository_factory is mock_task_repository_factory

    def test_factory_facade_type_verification(self, factory):
        """Test that factory creates correct facade type"""
        facade = factory.create_subtask_facade()
        
        # Verify it's the correct type
        assert type(facade).__name__ == "SubtaskApplicationFacade"
        assert hasattr(facade, '_subtask_repository_factory')
        assert hasattr(facade, '_task_repository_factory')

    def test_factory_parameter_passing_behavior(self, factory):
        """Test parameter passing behavior in factory method"""
        # The current implementation passes parameters to factory creation but
        # the facade stores factory references, not the specific parameter values
        # This test verifies the current behavior
        
        facade = factory.create_subtask_facade(project_id="specific-project", user_id="specific-user")
        
        # Facade should still have factory references
        assert facade._subtask_repository_factory == factory._subtask_repository_factory
        assert facade._task_repository_factory == factory._task_repository_factory
        
        # Note: The project_id and user_id parameters are accepted but not directly stored
        # on the facade in the current implementation. They would be used when
        # creating repositories through the factories.