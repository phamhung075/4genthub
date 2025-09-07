"""Test suite for ProjectFacadeFactory.

Tests the project facade factory including:
- Facade creation with authentication
- Dependency injection
- Caching mechanisms
- Error handling
- Authentication validation
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.application.services.project_management_service import ProjectManagementService
from fastmcp.task_management.infrastructure.repositories.project_repository_factory import (
    ProjectRepositoryFactory,
    GlobalRepositoryManager
)
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError,
    InvalidUserIdError
)
# Import logger for patching in tests
from fastmcp.task_management.application.factories import project_facade_factory


class TestProjectFacadeFactory:
    """Test cases for ProjectFacadeFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_project_repository_factory = Mock(spec=ProjectRepositoryFactory)
        self.mock_project_repository = Mock()
        self.mock_project_repository_factory.create.return_value = self.mock_project_repository
        
        self.factory = ProjectFacadeFactory(self.mock_project_repository_factory)
    
    def test_init(self):
        """Test factory initialization."""
        factory = ProjectFacadeFactory()
        assert factory._project_repository_factory is None
        assert factory._facades_cache == {}
        
        factory = ProjectFacadeFactory(self.mock_project_repository_factory)
        assert factory._project_repository_factory == self.mock_project_repository_factory
        assert factory._facades_cache == {}
    
    def test_create_project_facade_success(self):
        """Test successful facade creation with valid user."""
        user_id = "valid_user_123"
        
        # Create facade
        facade = self.factory.create_project_facade(user_id)
        
        # Verify facade was created
        assert isinstance(facade, ProjectApplicationFacade)
        
        # Verify repository factory was called
        self.mock_project_repository_factory.create.assert_called_once_with(user_id=user_id)
        
        # Verify facade was cached
        assert user_id in self.factory._facades_cache
        assert self.factory._facades_cache[user_id] == facade
    
    def test_create_project_facade_cached(self):
        """Test that subsequent calls return cached facade."""
        user_id = "cached_user_123"
        
        # First call
        facade1 = self.factory.create_project_facade(user_id)
        
        # Second call should return cached version
        facade2 = self.factory.create_project_facade(user_id)
        
        # Should be the same instance
        assert facade1 is facade2
        
        # Repository factory should only be called once
        assert self.mock_project_repository_factory.create.call_count == 1
    
    def test_create_project_facade_invalid_user_id(self):
        """Test facade creation with invalid user ID."""
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.create_project_facade("")
        
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.create_project_facade(None)
        
        # Cache should remain empty
        assert len(self.factory._facades_cache) == 0
    
    def test_create_project_facade_default_user_prohibited(self):
        """Test that default user ID is prohibited."""
        with patch('fastmcp.task_management.domain.constants.validate_user_id') as mock_validate:
            mock_validate.side_effect = DefaultUserProhibitedError()
            
            with pytest.raises(DefaultUserProhibitedError):
                self.factory.create_project_facade("default_user")
    
    def test_create_project_facade_without_repository_factory(self):
        """Test facade creation without repository factory uses global manager."""
        factory = ProjectFacadeFactory()  # No repository factory
        user_id = "test_user_123"
        
        with patch('fastmcp.task_management.application.factories.project_facade_factory.GlobalRepositoryManager') as mock_global_mgr:
            mock_repo = Mock()
            mock_global_mgr.get_for_user.return_value = mock_repo
            
            facade = factory.create_project_facade(user_id)
            
            # Verify global manager was used
            mock_global_mgr.get_for_user.assert_called_once_with(user_id)
            assert isinstance(facade, ProjectApplicationFacade)
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        user_id = "cache_test_user"
        
        # Create a facade to populate cache
        self.factory.create_project_facade(user_id)
        assert len(self.factory._facades_cache) == 1
        
        # Clear cache
        self.factory.clear_cache()
        assert len(self.factory._facades_cache) == 0
    
    def test_get_cached_facade_exists(self):
        """Test getting cached facade that exists."""
        user_id = "cached_user_456"
        
        # Create facade first
        original_facade = self.factory.create_project_facade(user_id)
        
        # Get cached facade
        cached_facade = self.factory.get_cached_facade(user_id)
        
        assert cached_facade is original_facade
    
    def test_get_cached_facade_not_exists(self):
        """Test getting cached facade that doesn't exist."""
        user_id = "non_cached_user"
        
        # Get non-existent cached facade
        cached_facade = self.factory.get_cached_facade(user_id)
        
        assert cached_facade is None
    
    def test_get_cached_facade_invalid_user_id(self):
        """Test getting cached facade with invalid user ID."""
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.get_cached_facade("")
        
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.get_cached_facade(None)
    
    def test_multiple_users_isolation(self):
        """Test that facades for different users are isolated."""
        user1 = "user_1"
        user2 = "user_2"
        
        # Create facades for different users
        facade1 = self.factory.create_project_facade(user1)
        facade2 = self.factory.create_project_facade(user2)
        
        # Should be different instances
        assert facade1 is not facade2
        
        # Both should be cached separately
        assert self.factory.get_cached_facade(user1) is facade1
        assert self.factory.get_cached_facade(user2) is facade2
        
        # Repository factory should be called for each user
        assert self.mock_project_repository_factory.create.call_count == 2
    
    def test_logging_behavior(self):
        """Test that appropriate logging occurs."""
        user_id = "logging_test_user"
        
        with patch.object(project_facade_factory.logger, 'info') as mock_info:
            with patch.object(project_facade_factory.logger, 'debug') as mock_debug:
                # First call - should log creation
                self.factory.create_project_facade(user_id)
                mock_info.assert_called_with(f"Created new project facade for {user_id}")
                
                # Second call - should log cache hit
                self.factory.create_project_facade(user_id)
                mock_debug.assert_called_with(f"Returning cached project facade for {user_id}")
    
    def test_factory_initialization_logging(self):
        """Test that factory initialization is logged."""
        with patch.object(project_facade_factory.logger, 'info') as mock_info:
            ProjectFacadeFactory()
            mock_info.assert_called_with("ProjectFacadeFactory initialized")
    
    def test_cache_clearing_logging(self):
        """Test that cache clearing is logged."""
        with patch.object(project_facade_factory.logger, 'info') as mock_info:
            self.factory.clear_cache()
            mock_info.assert_called_with("Project facades cache cleared")
    
    def test_repository_factory_dependency_injection(self):
        """Test proper dependency injection through repository factory."""
        user_id = "dependency_test_user"
        
        # Create facade
        facade = self.factory.create_project_facade(user_id)
        
        # Verify the dependency chain
        assert isinstance(facade, ProjectApplicationFacade)
        
        # Verify service was created with repository
        assert facade._project_service is not None
        assert isinstance(facade._project_service, ProjectManagementService)
        
        # Verify repository was injected into service
        self.mock_project_repository_factory.create.assert_called_once_with(user_id=user_id)
    
    def test_authentication_validation_integration(self):
        """Test integration with authentication validation."""
        # Test various invalid user IDs that should be caught by validation
        invalid_user_ids = [
            "",
            None,
            "   ",  # whitespace
            "default_id",  # prohibited ID from PROHIBITED_DEFAULT_IDS
            "00000000-0000-0000-0000-000000000000",  # zero UUID
            "default",  # prohibited
            "system",  # prohibited
        ]
        
        for invalid_id in invalid_user_ids:
            with pytest.raises((UserAuthenticationRequiredError, InvalidUserIdError, DefaultUserProhibitedError)):
                self.factory.create_project_facade(invalid_id)
        
        # Verify no facades were cached for invalid IDs
        assert len(self.factory._facades_cache) == 0
    
    @patch('fastmcp.task_management.application.factories.project_facade_factory.validate_user_id')
    def test_user_id_validation_called(self, mock_validate):
        """Test that user ID validation is properly called."""
        user_id = "validation_test_user"
        mock_validate.return_value = user_id
        
        self.factory.create_project_facade(user_id)
        
        # Verify validation was called
        mock_validate.assert_called_with(user_id, "Project facade creation")
    
    def test_error_handling_during_facade_creation(self):
        """Test error handling when facade creation fails."""
        user_id = "error_test_user"
        
        # Mock repository factory to raise exception
        self.mock_project_repository_factory.create.side_effect = Exception("Repository creation failed")
        
        with pytest.raises(Exception, match="Repository creation failed"):
            self.factory.create_project_facade(user_id)
        
        # Verify nothing was cached on error
        assert user_id not in self.factory._facades_cache
    
    def test_facade_reuse_across_operations(self):
        """Test that facade can be reused across multiple operations."""
        user_id = "reuse_test_user"
        
        # Create facade
        facade = self.factory.create_project_facade(user_id)
        
        # Simulate multiple operations using the same facade
        for i in range(5):
            cached_facade = self.factory.get_cached_facade(user_id)
            assert cached_facade is facade
        
        # Repository should only be created once
        assert self.mock_project_repository_factory.create.call_count == 1


class TestProjectFacadeFactoryEdgeCases:
    """Test edge cases and error scenarios for ProjectFacadeFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_project_repository_factory = Mock(spec=ProjectRepositoryFactory)
        self.mock_project_repository = Mock()
        self.mock_project_repository_factory.create.return_value = self.mock_project_repository
        
        self.factory = ProjectFacadeFactory(self.mock_project_repository_factory)
    
    def test_factory_with_none_repository_factory(self):
        """Test factory behavior with None repository factory."""
        factory = ProjectFacadeFactory(None)
        assert factory._project_repository_factory is None
        
        # Should still work using GlobalRepositoryManager
        with patch('fastmcp.task_management.application.factories.project_facade_factory.GlobalRepositoryManager') as mock_global:
            mock_repo = Mock()
            mock_global.get_for_user.return_value = mock_repo
            
            facade = factory.create_project_facade("test_user")
            assert isinstance(facade, ProjectApplicationFacade)
    
    def test_cache_key_collision_prevention(self):
        """Test that cache keys don't collide for different users."""
        factory = ProjectFacadeFactory()
        
        # Users with similar IDs
        users = ["user_1", "user_10", "user_11"]
        
        with patch('fastmcp.task_management.application.factories.project_facade_factory.GlobalRepositoryManager'):
            facades = []
            for user in users:
                facade = factory.create_project_facade(user)
                facades.append(facade)
            
            # All facades should be different
            assert len(set(id(f) for f in facades)) == len(users)
            
            # Each user should have their own cached facade
            for user in users:
                cached = factory.get_cached_facade(user)
                assert cached is not None

    def test_create_project_facade_default_user_prohibited(self):
        """Test facade creation with prohibited default user ID."""
        with pytest.raises(DefaultUserProhibitedError):
            self.factory.create_project_facade(user_id="default_id")
        
        with pytest.raises(DefaultUserProhibitedError):
            self.factory.create_project_facade(user_id="00000000-0000-0000-0000-000000000000")
    
    def test_create_project_facade_cache_hit(self):
        """Test facade creation returns cached instance."""
        user_id = "user-123"
        
        # Create first facade
        facade1 = self.factory.create_project_facade(user_id=user_id)
        
        # Create second facade with same parameters
        facade2 = self.factory.create_project_facade(user_id=user_id)
        
        # Should be the same instance
        assert facade1 is facade2
        # Repository factory should only be called once
        self.mock_project_repository_factory.create.assert_called_once()
    
    @patch('fastmcp.task_management.application.factories.project_facade_factory.GlobalRepositoryManager')
    def test_create_project_facade_no_factory_uses_global(self, mock_global_manager):
        """Test facade creation without repository factory uses global manager."""
        factory = ProjectFacadeFactory()  # No repository factory
        mock_repo = Mock()
        mock_global_manager.get_for_user.return_value = mock_repo
        
        user_id = "user-123"
        facade = factory.create_project_facade(user_id=user_id)
        
        assert isinstance(facade, ProjectApplicationFacade)
        mock_global_manager.get_for_user.assert_called_once_with(user_id)
    
    def test_clear_cache(self):
        """Test clearing the facade cache."""
        user_id = "user-123"
        
        # Create facade to populate cache
        self.factory.create_project_facade(user_id=user_id)
        assert len(self.factory._facades_cache) == 1
        
        # Clear cache
        self.factory.clear_cache()
        assert len(self.factory._facades_cache) == 0
    
    def test_get_cached_facade_exists(self):
        """Test getting cached facade when it exists."""
        user_id = "user-123"
        
        # Create facade first
        original_facade = self.factory.create_project_facade(user_id=user_id)
        
        # Get from cache
        cached_facade = self.factory.get_cached_facade(user_id=user_id)
        
        assert cached_facade is original_facade
    
    def test_get_cached_facade_not_exists(self):
        """Test getting cached facade when it doesn't exist."""
        user_id = "user-123"
        
        cached_facade = self.factory.get_cached_facade(user_id=user_id)
        
        assert cached_facade is None
    
    def test_get_cached_facade_requires_auth(self):
        """Test getting cached facade requires authentication."""
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.get_cached_facade(user_id=None)
        
        with pytest.raises(UserAuthenticationRequiredError):
            self.factory.get_cached_facade(user_id="")
        
        with pytest.raises(DefaultUserProhibitedError):
            self.factory.get_cached_facade(user_id="default_id")
    
    def test_facade_service_injection(self):
        """Test that facades are created with proper service injection."""
        user_id = "user-123"
        
        # Spy on service creation
        with patch('fastmcp.task_management.application.factories.project_facade_factory.ProjectManagementService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            facade = self.factory.create_project_facade(user_id=user_id)
            
            # Verify service was created with repository
            mock_service_class.assert_called_once_with(project_repo=self.mock_project_repository)
    
    def test_cache_key_generation(self):
        """Test cache key generation for different users."""
        user1 = "user-123"
        user2 = "user-456"
        
        facade1 = self.factory.create_project_facade(user_id=user1)
        facade2 = self.factory.create_project_facade(user_id=user2)
        
        # Different facades for different users
        assert facade1 is not facade2
        assert len(self.factory._facades_cache) == 2
        assert user1 in self.factory._facades_cache
        assert user2 in self.factory._facades_cache
    
    def test_special_characters_in_user_id(self):
        """Test handling of special characters in user ID."""
        special_user_ids = [
            "user@example.com",
            "user-with-dashes",
            "user_with_underscores",
            "user.with.dots",
            "user+plus@example.com"
        ]
        
        for user_id in special_user_ids:
            facade = self.factory.create_project_facade(user_id=user_id)
            assert isinstance(facade, ProjectApplicationFacade)
            assert user_id in self.factory._facades_cache


if __name__ == "__main__":
    pytest.main([__file__])