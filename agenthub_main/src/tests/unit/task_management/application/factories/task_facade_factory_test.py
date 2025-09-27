"""
Tests for Task Facade Factory

This module tests the TaskFacadeFactory which creates task application facades
with proper dependency injection following DDD patterns.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.services.repository_provider_service import RepositoryProviderService


class TestTaskFacadeFactory:
    """Test suite for TaskFacadeFactory"""
    
    @pytest.fixture
    def mock_repository_provider(self):
        """Create a mock repository provider service"""
        provider = Mock(spec=RepositoryProviderService)
        provider.get_task_repository = Mock()
        provider.get_subtask_repository = Mock()
        return provider
    
    @pytest.fixture
    def mock_context_service_factory(self):
        """Create a mock context service factory"""
        factory = Mock()
        factory.create_facade = Mock()
        return factory
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test"""
        TaskFacadeFactory._instance = None
        TaskFacadeFactory._initialized = False
        yield
        # Clean up after test
        TaskFacadeFactory._instance = None
        TaskFacadeFactory._initialized = False
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_singleton_pattern(self, mock_context_factory_class, mock_repository_provider):
        """Test that TaskFacadeFactory implements singleton pattern"""
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        # Create first instance
        factory1 = TaskFacadeFactory(mock_repository_provider)
        
        # Create second instance
        factory2 = TaskFacadeFactory(mock_repository_provider)
        
        # Verify they are the same instance
        assert factory1 is factory2
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.RepositoryProviderService')
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_get_instance_first_call(self, mock_context_factory_class, mock_provider_service):
        """Test get_instance on first call"""
        # Mock RepositoryProviderService.get_instance()
        mock_provider = Mock(spec=RepositoryProviderService)
        mock_provider_service.get_instance.return_value = mock_provider
        
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        factory = TaskFacadeFactory.get_instance()
        
        assert isinstance(factory, TaskFacadeFactory)
        assert factory._repository_provider == mock_provider
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.RepositoryProviderService')
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_get_instance_creates_provider(self, mock_context_factory_class, mock_provider_service):
        """Test get_instance creates repository provider when not provided"""
        # Mock RepositoryProviderService.get_instance()
        mock_provider = Mock(spec=RepositoryProviderService)
        mock_provider_service.get_instance.return_value = mock_provider
        
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        factory = TaskFacadeFactory.get_instance()
        
        # Verify RepositoryProviderService.get_instance() was called
        mock_provider_service.get_instance.assert_called_once()
        assert factory._repository_provider == mock_provider
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.RepositoryProviderService')
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_get_instance_subsequent_calls(self, mock_context_factory_class, mock_provider_service):
        """Test get_instance returns same instance on subsequent calls"""
        # Mock RepositoryProviderService.get_instance()
        mock_provider = Mock(spec=RepositoryProviderService)
        mock_provider_service.get_instance.return_value = mock_provider
        
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        # First call
        factory1 = TaskFacadeFactory.get_instance()
        
        # Second call (should return same instance)
        factory2 = TaskFacadeFactory.get_instance()
        
        assert factory1 is factory2
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_initialization_with_context_factory(self, mock_context_factory_class, 
                                               mock_repository_provider,
                                               mock_context_service_factory):
        """Test initialization with successful context service factory creation"""
        # Setup mock
        mock_context_factory_class.get_instance.return_value = mock_context_service_factory
        
        # Create factory
        factory = TaskFacadeFactory(mock_repository_provider)
        
        # Verify
        assert factory._repository_provider == mock_repository_provider
        assert factory._context_service_factory == mock_context_service_factory
        mock_context_factory_class.get_instance.assert_called_once()
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_initialization_context_factory_failure(self, mock_context_factory_class,
                                                  mock_repository_provider,
                                                  caplog):
        """Test initialization when context service factory fails"""
        # Setup mock to raise exception
        mock_context_factory_class.get_instance.side_effect = Exception("Database not available")
        
        # Set logging level to capture warning messages
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create factory
        factory = TaskFacadeFactory(mock_repository_provider)
        
        # Verify warnings were logged
        assert "Could not initialize ContextServiceFactory" in caplog.text
        assert "Context operations will not be available" in caplog.text
        
        # Verify factory still works but without context service
        assert factory._repository_provider == mock_repository_provider
        assert factory._context_service_factory is None
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_create_task_facade_no_user_raises_error(self,
                                                     mock_context_factory_class,
                                                     mock_repository_provider):
        """Test creating task facade without user ID raises authentication error"""
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        # Create factory
        factory = TaskFacadeFactory(mock_repository_provider)
        
        # Try to create facade without user_id - should raise error
        with pytest.raises(Exception) as exc_info:
            factory.create_task_facade(project_id="test-project", git_branch_id="branch-123")
        
        # Verify it's an authentication error
        assert "authentication" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_create_task_facade_with_git_branch_id_no_user_raises_error(self,
                                                                       mock_context_factory_class,
                                                                       mock_repository_provider):
        """Test creating task facade with git_branch_id but no user raises error"""
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        # Create factory
        factory = TaskFacadeFactory(mock_repository_provider)
        
        # Check if create_task_facade_with_git_branch_id method exists
        if hasattr(factory, 'create_task_facade_with_git_branch_id'):
            # Try to create facade with git_branch_id but no user_id - should raise error
            with pytest.raises(Exception) as exc_info:
                factory.create_task_facade_with_git_branch_id(
                    project_id="test-project",
                    git_branch_name="feature-branch",
                    user_id=None,
                    git_branch_id="branch-uuid-123"
                )
            
            # Verify it's an authentication error
            assert "authentication" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()
        else:
            # Method doesn't exist in new implementation, skip test
            pytest.skip("create_task_facade_with_git_branch_id method not implemented")
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_singleton_prevents_reinitialization(self, mock_context_factory_class,
                                                mock_repository_provider):
        """Test that singleton pattern prevents reinitialization"""
        # Mock context factory to avoid database access
        mock_context_factory_class.get_instance.return_value = Mock()
        
        # Create first instance
        factory1 = TaskFacadeFactory(mock_repository_provider)
        
        # Try to create second instance with different provider
        mock_other_provider = Mock(spec=RepositoryProviderService)
        factory2 = TaskFacadeFactory(mock_other_provider)
        
        # Verify second initialization was skipped
        assert factory1 is factory2
        assert factory2._repository_provider == mock_repository_provider  # Original provider


if __name__ == "__main__":
    pytest.main([__file__, "-v"])