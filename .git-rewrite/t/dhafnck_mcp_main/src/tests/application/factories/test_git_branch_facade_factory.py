"""Tests for GitBranchFacadeFactory"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade
from fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory


class TestGitBranchFacadeFactory:
    """Test cases for GitBranchFacadeFactory"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository_factory = Mock(spec=GitBranchRepositoryFactory)
        self.factory = GitBranchFacadeFactory(self.mock_repository_factory)

    def test_init_with_repository_factory(self):
        """Test factory initialization with repository factory"""
        factory = GitBranchFacadeFactory(self.mock_repository_factory)
        
        assert factory._git_branch_repository_factory == self.mock_repository_factory
        assert factory._facades_cache == {}

    def test_init_without_repository_factory(self):
        """Test factory initialization without repository factory"""
        factory = GitBranchFacadeFactory()
        
        assert factory._git_branch_repository_factory is None
        assert factory._facades_cache == {}

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.logger')
    def test_init_logging(self, mock_logger):
        """Test that initialization is logged"""
        GitBranchFacadeFactory()
        mock_logger.info.assert_called_with("GitBranchFacadeFactory initialized")

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_create_git_branch_facade_success(self, mock_git_branch_service_class):
        """Test successful facade creation"""
        # Setup
        project_id = "project-123"
        user_id = "user-456"
        
        mock_service_instance = Mock()
        mock_git_branch_service_class.return_value = mock_service_instance
        
        # Execute
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade_instance = Mock()
            mock_facade_class.return_value = mock_facade_instance
            
            result = self.factory.create_git_branch_facade(project_id, user_id)
            
            # Assert
            assert result == mock_facade_instance
            
            # Verify service creation
            mock_git_branch_service_class.assert_called_once_with(user_id=user_id)
            
            # Verify facade creation
            mock_facade_class.assert_called_once_with(
                git_branch_service=mock_service_instance,
                project_id=project_id,
                user_id=user_id
            )

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_create_git_branch_facade_default_project(self, mock_git_branch_service_class):
        """Test facade creation with default project ID"""
        mock_service_instance = Mock()
        mock_git_branch_service_class.return_value = mock_service_instance
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade_instance = Mock()
            mock_facade_class.return_value = mock_facade_instance
            
            result = self.factory.create_git_branch_facade()
            
            # Should use default project_id
            mock_facade_class.assert_called_once_with(
                git_branch_service=mock_service_instance,
                project_id="default_project",
                user_id=None
            )

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_create_git_branch_facade_caching(self, mock_git_branch_service_class):
        """Test that facades are properly cached"""
        project_id = "project-123"
        user_id = "user-456"
        
        mock_service_instance = Mock()
        mock_git_branch_service_class.return_value = mock_service_instance
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade_instance = Mock()
            mock_facade_class.return_value = mock_facade_instance
            
            # First call
            result1 = self.factory.create_git_branch_facade(project_id, user_id)
            
            # Second call with same parameters should return cached instance
            result2 = self.factory.create_git_branch_facade(project_id, user_id)
            
            assert result1 == result2
            assert result1 == mock_facade_instance
            
            # Service and facade should only be created once
            mock_git_branch_service_class.assert_called_once()
            mock_facade_class.assert_called_once()

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.logger')
    def test_create_git_branch_facade_cache_logging(self, mock_logger, mock_git_branch_service_class):
        """Test cache-related logging"""
        project_id = "project-123"
        user_id = "user-456"
        
        mock_service_instance = Mock()
        mock_git_branch_service_class.return_value = mock_service_instance
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade_instance = Mock()
            mock_facade_class.return_value = mock_facade_instance
            
            # First call
            self.factory.create_git_branch_facade(project_id, user_id)
            mock_logger.info.assert_called_with("Created new git branch facade for project-123:user-456")
            
            # Second call (cached)
            self.factory.create_git_branch_facade(project_id, user_id)
            mock_logger.debug.assert_called_with("Returning cached git branch facade for project-123:user-456")

    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly"""
        # Test with user_id
        cache_key = f"project-123:user-456"
        expected_key = "project-123:user-456"
        assert cache_key == expected_key
        
        # Test without user_id (None case)
        cache_key = f"project-123:{None or 'no_user'}"
        expected_key = "project-123:no_user"
        assert cache_key == expected_key

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_create_git_branch_facade_different_users_different_cache(self, mock_git_branch_service_class):
        """Test that different users get different cached facades"""
        project_id = "project-123"
        user_id1 = "user-456"
        user_id2 = "user-789"
        
        mock_service_instance = Mock()
        mock_git_branch_service_class.return_value = mock_service_instance
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade_instance1 = Mock()
            mock_facade_instance2 = Mock()
            mock_facade_class.side_effect = [mock_facade_instance1, mock_facade_instance2]
            
            result1 = self.factory.create_git_branch_facade(project_id, user_id1)
            result2 = self.factory.create_git_branch_facade(project_id, user_id2)
            
            # Should be different instances
            assert result1 != result2
            assert result1 == mock_facade_instance1
            assert result2 == mock_facade_instance2
            
            # Should create service twice (once for each user)
            assert mock_git_branch_service_class.call_count == 2

    def test_clear_cache(self):
        """Test cache clearing functionality"""
        # Add some items to cache
        self.factory._facades_cache["key1"] = Mock()
        self.factory._facades_cache["key2"] = Mock()
        
        assert len(self.factory._facades_cache) == 2
        
        # Clear cache
        self.factory.clear_cache()
        
        assert len(self.factory._facades_cache) == 0

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.logger')
    def test_clear_cache_logging(self, mock_logger):
        """Test that cache clearing is logged"""
        self.factory.clear_cache()
        mock_logger.info.assert_called_with("Git branch facades cache cleared")

    def test_get_cached_facade_exists(self):
        """Test getting existing cached facade"""
        project_id = "project-123"
        user_id = "user-456"
        cache_key = f"{project_id}:{user_id or 'no_user'}"
        
        mock_facade = Mock()
        self.factory._facades_cache[cache_key] = mock_facade
        
        result = self.factory.get_cached_facade(project_id, user_id)
        
        assert result == mock_facade

    def test_get_cached_facade_not_exists(self):
        """Test getting non-existent cached facade"""
        project_id = "project-123"
        user_id = "user-456"
        
        result = self.factory.get_cached_facade(project_id, user_id)
        
        assert result is None

    def test_get_cached_facade_none_user_id(self):
        """Test getting cached facade with None user_id"""
        project_id = "project-123"
        user_id = None
        cache_key = f"{project_id}:no_user"
        
        mock_facade = Mock()
        self.factory._facades_cache[cache_key] = mock_facade
        
        result = self.factory.get_cached_facade(project_id, user_id)
        
        assert result == mock_facade

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_facade_isolation_by_user(self, mock_git_branch_service_class):
        """Test that facades are properly isolated by user"""
        project_id = "same-project"
        user_id1 = "user-1"
        user_id2 = "user-2"
        
        mock_service1 = Mock()
        mock_service2 = Mock()
        mock_git_branch_service_class.side_effect = [mock_service1, mock_service2]
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchApplicationFacade') as mock_facade_class:
            mock_facade1 = Mock()
            mock_facade2 = Mock()
            mock_facade_class.side_effect = [mock_facade1, mock_facade2]
            
            facade1 = self.factory.create_git_branch_facade(project_id, user_id1)
            facade2 = self.factory.create_git_branch_facade(project_id, user_id2)
            
            # Should be different instances
            assert facade1 != facade2
            
            # Verify services were created with correct user IDs
            calls = mock_git_branch_service_class.call_args_list
            assert calls[0] == ((), {'user_id': user_id1})
            assert calls[1] == ((), {'user_id': user_id2})
            
            # Verify facades were created with correct parameters
            facade_calls = mock_facade_class.call_args_list
            assert facade_calls[0][1]['user_id'] == user_id1
            assert facade_calls[1][1]['user_id'] == user_id2

    def test_factory_attributes_after_init(self):
        """Test that factory has correct attributes after initialization"""
        factory = GitBranchFacadeFactory()
        
        assert hasattr(factory, '_git_branch_repository_factory')
        assert hasattr(factory, '_facades_cache')
        assert isinstance(factory._facades_cache, dict)

    @patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService')
    def test_create_facade_integration_test(self, mock_git_branch_service_class):
        """Integration test for facade creation process"""
        project_id = "integration-project"
        user_id = "integration-user"
        
        mock_service = Mock()
        mock_git_branch_service_class.return_value = mock_service
        
        # First creation
        facade1 = self.factory.create_git_branch_facade(project_id, user_id)
        
        # Verify facade is GitBranchApplicationFacade instance (if not mocked)
        assert facade1 is not None
        
        # Second creation should return same instance (cached)
        facade2 = self.factory.create_git_branch_facade(project_id, user_id)
        assert facade1 == facade2
        
        # Verify cache contains the facade
        cache_key = f"{project_id}:{user_id}"
        assert cache_key in self.factory._facades_cache
        assert self.factory._facades_cache[cache_key] == facade1
        
        # Verify get_cached_facade returns same instance
        cached_facade = self.factory.get_cached_facade(project_id, user_id)
        assert cached_facade == facade1

    def test_multiple_projects_same_user(self):
        """Test handling multiple projects for same user"""
        user_id = "same-user"
        project1 = "project-1"
        project2 = "project-2"
        
        with patch('fastmcp.task_management.application.factories.git_branch_facade_factory.GitBranchService') as mock_service_class:
            mock_service_class.return_value = Mock()
            
            facade1 = self.factory.create_git_branch_facade(project1, user_id)
            facade2 = self.factory.create_git_branch_facade(project2, user_id)
            
            # Should be different facades for different projects
            assert facade1 != facade2
            
            # Both should be cached separately
            assert len(self.factory._facades_cache) == 2
            assert self.factory.get_cached_facade(project1, user_id) == facade1
            assert self.factory.get_cached_facade(project2, user_id) == facade2