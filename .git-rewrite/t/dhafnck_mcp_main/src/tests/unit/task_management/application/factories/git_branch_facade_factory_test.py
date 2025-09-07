"""Test module for Git Branch Facade Factory."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Optional

from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade
from fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory


class TestGitBranchFacadeFactory:
    """Test suite for Git Branch Facade Factory."""

    @pytest.fixture
    def mock_git_branch_repository_factory(self):
        """Create a mock GitBranchRepositoryFactory."""
        return MagicMock(spec=GitBranchRepositoryFactory)

    @pytest.fixture
    def factory(self, mock_git_branch_repository_factory):
        """Create a GitBranchFacadeFactory instance with mocks."""
        return GitBranchFacadeFactory(
            git_branch_repository_factory=mock_git_branch_repository_factory
        )

    def test_init(self, mock_git_branch_repository_factory):
        """Test GitBranchFacadeFactory initialization."""
        factory = GitBranchFacadeFactory(
            git_branch_repository_factory=mock_git_branch_repository_factory
        )
        
        assert factory._git_branch_repository_factory == mock_git_branch_repository_factory
        assert factory._facades_cache == {}

    def test_init_without_repository_factory(self):
        """Test GitBranchFacadeFactory initialization without repository factory."""
        factory = GitBranchFacadeFactory()
        
        assert factory._git_branch_repository_factory is None
        assert factory._facades_cache == {}

    def test_create_git_branch_facade_new(self, factory):
        """Test creating a new git branch facade."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            facade = factory.create_git_branch_facade(
                project_id="test-project",
                user_id="test-user"
            )
            
            # Verify facade is created
            assert isinstance(facade, GitBranchApplicationFacade)
            
            # Verify service was created with user_id
            mock_service_class.assert_called_once_with(user_id="test-user")
            
            # Verify facade is cached
            cache_key = "test-project:test-user"
            assert factory._facades_cache[cache_key] == facade

    def test_create_git_branch_facade_cached(self, factory):
        """Test returning cached git branch facade."""
        # Create first facade
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            facade1 = factory.create_git_branch_facade(
                project_id="test-project",
                user_id="test-user"
            )
            
            # Create second facade with same parameters
            facade2 = factory.create_git_branch_facade(
                project_id="test-project",
                user_id="test-user"
            )
            
            # Should return cached facade
            assert facade1 is facade2
            
            # Service should only be created once
            mock_service_class.assert_called_once()

    def test_create_git_branch_facade_different_users(self, factory):
        """Test creating facades for different users."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            mock_service1 = MagicMock()
            mock_service2 = MagicMock()
            mock_service_class.side_effect = [mock_service1, mock_service2]
            
            # Create facade for user1
            facade1 = factory.create_git_branch_facade(
                project_id="test-project",
                user_id="user1"
            )
            
            # Create facade for user2
            facade2 = factory.create_git_branch_facade(
                project_id="test-project",
                user_id="user2"
            )
            
            # Should create different facades
            assert facade1 is not facade2
            
            # Service should be created twice with different user_ids
            assert mock_service_class.call_count == 2
            mock_service_class.assert_any_call(user_id="user1")
            mock_service_class.assert_any_call(user_id="user2")

    def test_create_git_branch_facade_no_user(self, factory):
        """Test creating facade without user_id."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            facade = factory.create_git_branch_facade(
                project_id="test-project"
            )
            
            # Verify service was created with None user_id
            mock_service_class.assert_called_once_with(user_id=None)
            
            # Verify cache key includes 'no_user'
            cache_key = "test-project:no_user"
            assert factory._facades_cache[cache_key] == facade

    def test_create_git_branch_facade_default_project(self, factory):
        """Test creating facade with default project_id."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            facade = factory.create_git_branch_facade()
            
            # Should use default project_id
            cache_key = "default_project:no_user"
            assert factory._facades_cache[cache_key] == facade

    def test_clear_cache(self, factory):
        """Test clearing the facades cache."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService'):
            # Create some facades
            facade1 = factory.create_git_branch_facade(project_id="project1")
            facade2 = factory.create_git_branch_facade(project_id="project2")
            
            # Verify cache has entries
            assert len(factory._facades_cache) == 2
            
            # Clear cache
            factory.clear_cache()
            
            # Verify cache is empty
            assert factory._facades_cache == {}

    def test_get_cached_facade_exists(self, factory):
        """Test getting a cached facade that exists."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService'):
            # Create a facade
            created_facade = factory.create_git_branch_facade(project_id="test-project")
            
            # Get cached facade with matching cache key (no user_id)
            cached_facade = factory.get_cached_facade("test-project", user_id=None)
            
            # Should return the cached facade
            assert cached_facade is created_facade

    def test_get_cached_facade_not_exists(self, factory):
        """Test getting a cached facade that doesn't exist."""
        # Get cached facade for non-existent project
        cached_facade = factory.get_cached_facade("non-existent-project")
        
        # Should return None
        assert cached_facade is None

    def test_facade_isolation_by_user(self, factory):
        """Test that facades are properly isolated by user."""
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService') as mock_service_class:
            # Create facades for same project but different users
            facade_user1 = factory.create_git_branch_facade(
                project_id="shared-project",
                user_id="user1"
            )
            facade_user2 = factory.create_git_branch_facade(
                project_id="shared-project",
                user_id="user2"
            )
            
            # Facades should be different
            assert facade_user1 is not facade_user2
            
            # Each user should have their own cache entry
            assert factory._facades_cache["shared-project:user1"] == facade_user1
            assert factory._facades_cache["shared-project:user2"] == facade_user2

    def test_logging_messages(self, factory, caplog):
        """Test that appropriate log messages are generated."""
        import logging
        # Set logging level for the specific logger
        caplog.set_level(logging.DEBUG, logger="fastmcp.task_management.application.factories.git_branch_facade_factory")
        
        with patch('fastmcp.task_management.application.services.git_branch_service.GitBranchService'):
            # Create new facade
            factory.create_git_branch_facade(project_id="log-test", user_id="user1")
            assert "Created new git branch facade for log-test:user1" in caplog.text
            
            # Get cached facade
            caplog.clear()
            factory.create_git_branch_facade(project_id="log-test", user_id="user1")
            assert "Returning cached git branch facade for log-test:user1" in caplog.text
            
            # Clear cache
            caplog.clear()
            factory.clear_cache()
            assert "Git branch facades cache cleared" in caplog.text