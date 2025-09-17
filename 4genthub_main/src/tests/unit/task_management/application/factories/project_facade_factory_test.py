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
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    InvalidUserIdError
)


class TestProjectFacadeFactory:
    """Test cases for ProjectFacadeFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset singleton for testing
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        # Create a mock repository provider
        self.mock_repository_provider = Mock()
        self.mock_project_repository = Mock()
        self.mock_repository_provider.get_project_repository.return_value = self.mock_project_repository
        
        self.factory = ProjectFacadeFactory(self.mock_repository_provider)
    
    def teardown_method(self):
        """Clean up after tests."""
        # Reset singleton
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
    
    def test_init(self):
        """Test factory initialization."""
        # Reset singleton for this test
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        factory = ProjectFacadeFactory()
        assert factory._repository_provider is None
        assert factory._facades_cache == {}
        assert factory._initialized is True
        
        # Test with repository provider
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        factory = ProjectFacadeFactory(self.mock_repository_provider)
        assert factory._repository_provider == self.mock_repository_provider
        assert factory._facades_cache == {}
        assert factory._initialized is True
    
    def test_singleton_pattern(self):
        """Test that factory follows singleton pattern."""
        # Reset singleton
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        factory1 = ProjectFacadeFactory(self.mock_repository_provider)
        factory2 = ProjectFacadeFactory()  # Should return same instance
        
        assert factory1 is factory2
        assert factory1._repository_provider == self.mock_repository_provider
    
    @patch('fastmcp.task_management.application.factories.project_facade_factory.RepositoryProviderService')
    def test_get_instance(self, mock_repo_provider_service):
        """Test get_instance class method."""
        # Reset singleton
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        # Mock RepositoryProviderService.get_instance()
        mock_repo_provider_service.get_instance.return_value = self.mock_repository_provider
        
        instance = ProjectFacadeFactory.get_instance()
        assert isinstance(instance, ProjectFacadeFactory)
        assert instance._repository_provider == self.mock_repository_provider
        
        # Subsequent calls should return same instance
        instance2 = ProjectFacadeFactory.get_instance()
        assert instance is instance2
    
    def test_create_project_facade_success(self):
        """Test successful facade creation with valid user."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock repository provider to return project repository
        self.mock_repository_provider.get_project_repository.return_value = self.mock_project_repository
        
        facade = self.factory.create_project_facade(user_id)
        
        assert isinstance(facade, ProjectApplicationFacade)
        assert self.factory._facades_cache[user_id] == facade
        self.mock_repository_provider.get_project_repository.assert_called_once_with(user_id)
    
    def test_create_project_facade_cached(self):
        """Test that facades are cached per user."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Create first facade
        facade1 = self.factory.create_project_facade(user_id)
        
        # Create second facade for same user - should return cached
        facade2 = self.factory.create_project_facade(user_id)
        
        assert facade1 is facade2
        # Repository should only be called once due to caching
        self.mock_repository_provider.get_project_repository.assert_called_once()
    
    def test_create_project_facade_different_users(self):
        """Test that different users get different facades."""
        user_id1 = "550e8400-e29b-41d4-a716-446655440001"
        user_id2 = "550e8400-e29b-41d4-a716-446655440002"
        
        facade1 = self.factory.create_project_facade(user_id1)
        facade2 = self.factory.create_project_facade(user_id2)
        
        assert facade1 is not facade2
        assert self.factory._facades_cache[user_id1] == facade1
        assert self.factory._facades_cache[user_id2] == facade2
    
    def test_create_project_facade_invalid_user_id(self):
        """Test facade creation with invalid user ID."""
        # validate_user_id raises ValueError for empty/None user_id
        with pytest.raises(ValueError, match="requires user authentication"):
            self.factory.create_project_facade("")
        
        with pytest.raises(ValueError, match="requires user authentication"):
            self.factory.create_project_facade(None)
        
        # "invalid-uuid" gets normalized to a valid UUID using uuid5, so it won't raise
        # Test with whitespace-only string instead
        with pytest.raises(ValueError, match="requires user authentication"):
            self.factory.create_project_facade("   ")
    
    def test_create_project_facade_with_repository_error(self):
        """Test facade creation when repository creation fails."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock repository provider to raise error
        self.mock_repository_provider.get_project_repository.side_effect = Exception("Repository error")
        
        with pytest.raises(Exception, match="Repository error"):
            self.factory.create_project_facade(user_id)
    
    @patch('fastmcp.task_management.application.factories.project_facade_factory.logger')
    def test_logging(self, mock_logger):
        """Test that factory logs appropriately."""
        # Reset singleton for clean test
        ProjectFacadeFactory._instance = None
        ProjectFacadeFactory._initialized = False
        
        factory = ProjectFacadeFactory(self.mock_repository_provider)
        mock_logger.info.assert_called_with("ProjectFacadeFactory initialized")
        
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        facade = factory.create_project_facade(user_id)
        
        # Check that facade creation is logged
        mock_logger.info.assert_any_call(f"Created new project facade for {user_id}")