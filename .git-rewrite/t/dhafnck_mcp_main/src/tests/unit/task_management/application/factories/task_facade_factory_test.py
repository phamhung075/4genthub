"""
Tests for Task Facade Factory

This module tests the TaskFacadeFactory which creates task application facades
with proper dependency injection following DDD patterns.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory


class TestTaskFacadeFactory:
    """Test suite for TaskFacadeFactory"""
    
    @pytest.fixture
    def mock_task_repository_factory(self):
        """Create a mock task repository factory"""
        factory = Mock(spec=TaskRepositoryFactory)
        factory.create_repository = Mock()
        factory.create_repository_with_git_branch_id = Mock()
        return factory
    
    @pytest.fixture
    def mock_subtask_repository_factory(self):
        """Create a mock subtask repository factory"""
        factory = Mock(spec=SubtaskRepositoryFactory)
        factory.create_subtask_repository = Mock()
        return factory
    
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
    
    def test_singleton_pattern(self, mock_task_repository_factory, mock_subtask_repository_factory):
        """Test that TaskFacadeFactory implements singleton pattern"""
        # Create first instance
        factory1 = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Create second instance
        factory2 = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Verify they are the same instance
        assert factory1 is factory2
    
    def test_get_instance_first_call(self, mock_task_repository_factory, mock_subtask_repository_factory):
        """Test get_instance on first call with required parameters"""
        factory = TaskFacadeFactory.get_instance(
            repository_factory=mock_task_repository_factory,
            subtask_repository_factory=mock_subtask_repository_factory
        )
        
        assert isinstance(factory, TaskFacadeFactory)
        assert factory._repository_factory == mock_task_repository_factory
        assert factory._subtask_repository_factory == mock_subtask_repository_factory
    
    def test_get_instance_without_required_factory(self):
        """Test get_instance on first call without required repository_factory"""
        with pytest.raises(ValueError, match="repository_factory is required for first initialization"):
            TaskFacadeFactory.get_instance()
    
    def test_get_instance_subsequent_calls(self, mock_task_repository_factory):
        """Test get_instance returns same instance on subsequent calls"""
        # First call with factory
        factory1 = TaskFacadeFactory.get_instance(repository_factory=mock_task_repository_factory)
        
        # Second call without factory (should return same instance)
        factory2 = TaskFacadeFactory.get_instance()
        
        assert factory1 is factory2
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_initialization_with_context_factory(self, mock_context_factory_class, 
                                               mock_task_repository_factory, 
                                               mock_subtask_repository_factory,
                                               mock_context_service_factory):
        """Test initialization with successful context service factory creation"""
        # Setup mock
        mock_context_factory_class.get_instance.return_value = mock_context_service_factory
        
        # Create factory
        factory = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Verify
        assert factory._repository_factory == mock_task_repository_factory
        assert factory._subtask_repository_factory == mock_subtask_repository_factory
        assert factory._context_service_factory == mock_context_service_factory
        mock_context_factory_class.get_instance.assert_called_once()
    
    @patch('fastmcp.task_management.application.factories.task_facade_factory.ContextServiceFactory')
    def test_initialization_context_factory_failure(self, mock_context_factory_class,
                                                  mock_task_repository_factory,
                                                  mock_subtask_repository_factory,
                                                  caplog):
        """Test initialization when context service factory fails"""
        # Setup mock to raise exception
        mock_context_factory_class.get_instance.side_effect = Exception("Database not available")
        
        # Set logging level to capture warning messages
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create factory
        factory = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Verify warnings were logged
        assert "Could not initialize ContextServiceFactory" in caplog.text
        assert "Context operations will not be available" in caplog.text
        
        # Verify factory still works but without context service
        assert factory._repository_factory == mock_task_repository_factory
        assert factory._subtask_repository_factory == mock_subtask_repository_factory
        assert factory._context_service_factory is None
    
    def test_create_task_facade_no_user_raises_error(self,
                                                     mock_task_repository_factory,
                                                     mock_subtask_repository_factory):
        """Test creating task facade without user ID raises authentication error"""
        # Create factory
        factory = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Try to create facade without user_id - should raise error
        with pytest.raises(Exception) as exc_info:
            factory.create_task_facade(project_id="test-project", git_branch_id="branch-123")
        
        # Verify it's an authentication error
        assert "authentication" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()
    
    
    def test_create_task_facade_with_git_branch_id_no_user_raises_error(self,
                                                                       mock_task_repository_factory,
                                                                       mock_subtask_repository_factory):
        """Test creating task facade with git_branch_id but no user raises error"""
        # Create factory
        factory = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
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
    
    
    def test_singleton_prevents_reinitialization(self, mock_task_repository_factory, 
                                                mock_subtask_repository_factory):
        """Test that singleton pattern prevents reinitialization"""
        # Create first instance
        factory1 = TaskFacadeFactory(mock_task_repository_factory, mock_subtask_repository_factory)
        
        # Try to create second instance with different factories
        mock_other_task_factory = Mock(spec=TaskRepositoryFactory)
        mock_other_subtask_factory = Mock(spec=SubtaskRepositoryFactory)
        factory2 = TaskFacadeFactory(mock_other_task_factory, mock_other_subtask_factory)
        
        # Verify second initialization was skipped
        assert factory1 is factory2
        assert factory2._repository_factory == mock_task_repository_factory  # Original factory
        assert factory2._subtask_repository_factory == mock_subtask_repository_factory  # Original factory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])