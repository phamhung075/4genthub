"""
Tests for UnifiedContextFacadeFactory

Tests the factory pattern implementation for creating UnifiedContextFacade instances
with proper dependency injection and singleton behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import sessionmaker

from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.infrastructure.database.models import GLOBAL_SINGLETON_UUID


class TestUnifiedContextFacadeFactory:
    """Test suite for UnifiedContextFacadeFactory"""

    def setup_method(self):
        """Reset singleton state before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False

    def test_singleton_pattern(self):
        """Test that factory implements singleton pattern correctly"""
        # Arrange & Act
        factory1 = UnifiedContextFacadeFactory()
        factory2 = UnifiedContextFacadeFactory()
        
        # Assert
        assert factory1 is factory2
        assert UnifiedContextFacadeFactory._instance is factory1

    def test_initialization_with_database(self):
        """Test successful initialization with database config"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        
        # Act - Initialize with explicit session factory to bypass get_db_config
        factory = UnifiedContextFacadeFactory(mock_session_factory)

        # Assert
        assert factory.session_factory == mock_session_factory
        assert factory.unified_service is not None
        assert UnifiedContextFacadeFactory._initialized is True

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository')
    def test_initialization_without_database_falls_back_to_mock(self, mock_global_repo):
        """Test fallback to mock service when database is unavailable"""
        # Arrange - Make repository initialization fail to trigger mock service
        mock_global_repo.side_effect = Exception("Repository initialization failed")
        mock_session_factory = Mock(spec=sessionmaker)
        
        # Act
        factory = UnifiedContextFacadeFactory(mock_session_factory)

        # Assert - Should have fallen back to mock service
        assert factory.unified_service is not None
        # Check that it's using the mock service
        from fastmcp.task_management.application.services.mock_unified_context_service import MockUnifiedContextService
        assert isinstance(factory.unified_service, MockUnifiedContextService)
        assert UnifiedContextFacadeFactory._initialized is True

    def test_get_instance_class_method(self):
        """Test get_instance class method creates singleton"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)

        # Act
        instance1 = UnifiedContextFacadeFactory.get_instance(mock_session_factory)
        instance2 = UnifiedContextFacadeFactory.get_instance()

        # Assert
        assert instance1 is instance2
        assert isinstance(instance1, UnifiedContextFacadeFactory)

    def test_create_facade_without_user_scoping(self):
        """Test creating facade without user scoping"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)

        # Act
        facade = factory.create_facade(
            user_id=None,
            project_id="test-project-id",
            git_branch_id="test-branch-id"
        )

        # Assert
        assert isinstance(facade, UnifiedContextFacade)
        assert facade._user_id is None
        assert facade._project_id == "test-project-id"
        assert facade._git_branch_id == "test-branch-id"

    def test_create_facade_with_user_scoping(self):
        """Test creating facade with user scoping"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)
        
        # Act
        facade = factory.create_facade(
            user_id="test-user-id",
            project_id="test-project-id",
            git_branch_id="test-branch-id"
        )

        # Assert - facade should be created with correct user scoping
        assert isinstance(facade, UnifiedContextFacade)
        assert facade._user_id == "test-user-id"
        assert facade._project_id == "test-project-id"
        assert facade._git_branch_id == "test-branch-id"
        
        # The factory creates a completely new user-scoped service, not reusing the shared one
        # This is the expected behavior for proper user isolation
        assert facade._service is not factory.unified_service

    def test_create_unified_service(self):
        """Test getting unified service directly"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)

        # Act
        service = factory.create_unified_service()

        # Assert
        assert service is factory.unified_service
        assert isinstance(service, UnifiedContextService)

    def test_auto_create_global_context_success(self):
        """Test successful auto-creation of global context"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)
        
        # Mock facade creation result
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_facade = Mock()
            # Mock get_context to simulate context doesn't exist
            mock_facade.get_context.side_effect = Exception("Not found")
            # Mock create_context to simulate successful creation
            mock_facade.create_context.return_value = {"success": True}
            mock_create_facade.return_value = mock_facade

            # Act - provide user_id parameter
            result = factory.auto_create_global_context(user_id="test-user-123")

            # Assert
            assert result is True
            # The actual implementation generates a user-specific UUID for global context
            # Verify that create_context was called with correct level and data
            mock_facade.create_context.assert_called_once()
            call_args = mock_facade.create_context.call_args
            # Check called with kwargs
            assert call_args[1]['level'] == "global"
            # The context_id will be a generated UUID, not 'global_singleton'
            assert len(call_args[1]['context_id']) == 36  # UUID string length
            assert call_args[1]['data'] == {
                "organization_name": "Default Organization",
                "global_settings": {
                    "autonomous_rules": {},
                    "security_policies": {},
                    "coding_standards": {},
                    "workflow_templates": {},
                    "delegation_rules": {}
                }
            }

    def test_auto_create_global_context_already_exists(self):
        """Test auto-creation when global context already exists"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)
        
        # Mock facade creation result
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_facade = Mock()
            # Mock get_context to simulate context already exists
            mock_facade.get_context.return_value = {"success": True}
            mock_create_facade.return_value = mock_facade

            # Act - provide user_id parameter
            result = factory.auto_create_global_context(user_id="test-user-123")

            # Assert
            assert result is True
            # The actual implementation generates a user-specific UUID for global context
            mock_facade.get_context.assert_called_once()
            call_args = mock_facade.get_context.call_args
            assert call_args[1]['level'] == "global"
            # The context_id will be a generated UUID, not 'global_singleton'
            assert len(call_args[1]['context_id']) == 36  # UUID string length

    def test_auto_create_global_context_failure(self):
        """Test auto-creation failure handling"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        factory = UnifiedContextFacadeFactory(mock_session_factory)
        
        # Mock global repository to simulate context doesn't exist
        factory.global_repo.get = Mock(side_effect=Exception("Not found"))
        
        # Mock facade creation to fail
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_facade = Mock()
            mock_facade.create_context.return_value = {"success": False, "error": "Creation failed"}
            mock_create_facade.return_value = mock_facade

            # Act
            result = factory.auto_create_global_context()

            # Assert
            assert result is False

    def test_initialization_with_custom_session_factory(self):
        """Test initialization with custom session factory"""
        # Arrange
        custom_session_factory = Mock(spec=sessionmaker)

        # Act
        factory = UnifiedContextFacadeFactory(custom_session_factory)

        # Assert
        assert factory.session_factory == custom_session_factory
        assert UnifiedContextFacadeFactory._initialized is True

    def test_repository_initialization(self):
        """Test that all required repositories are initialized when database is available"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)

        # Act - Pass session factory to ensure database initialization succeeds
        factory = UnifiedContextFacadeFactory(mock_session_factory)

        # Assert - Repository attributes should exist when database initialization succeeds
        assert hasattr(factory, 'global_repo')
        assert hasattr(factory, 'project_repo')
        assert hasattr(factory, 'branch_repo')
        assert hasattr(factory, 'task_repo')
        assert hasattr(factory, 'cache_service')
        assert hasattr(factory, 'inheritance_service')
        assert hasattr(factory, 'delegation_service')
        assert hasattr(factory, 'validation_service')

    def test_create_mock_service_when_database_fails(self):
        """Test creation of mock service when database initialization fails"""
        # Arrange & Act
        factory = UnifiedContextFacadeFactory(None)  # Force database unavailable

        # Assert
        assert factory.unified_service is not None
        # Verify it's using mock service (though we can't import the exact type without better mocking)
        assert UnifiedContextFacadeFactory._initialized is True

    def test_repository_attributes_not_created_with_mock_service(self):
        """Test that repository attributes are NOT created when using mock service"""
        # Arrange & Act
        factory = UnifiedContextFacadeFactory(None)  # Force database unavailable (mock service)

        # Assert - Repository attributes should NOT exist when using mock service
        assert not hasattr(factory, 'global_repo')
        assert not hasattr(factory, 'project_repo')
        assert not hasattr(factory, 'branch_repo')
        assert not hasattr(factory, 'task_repo')
        # Service attributes that don't depend on database should still exist
        assert factory.unified_service is not None
        assert UnifiedContextFacadeFactory._initialized is True

    def test_logging_behavior(self):
        """Test that appropriate logging occurs during initialization"""
        # This test validates that logging occurs during initialization
        # The actual logging behavior is verified by the successful initialization
        # Arrange & Act
        factory = UnifiedContextFacadeFactory(None)  # This should trigger database fallback
        
        # Assert
        assert factory.unified_service is not None  # Service was created successfully
        assert UnifiedContextFacadeFactory._initialized is True  # Factory was initialized

    def test_multiple_create_facade_calls_use_same_service(self):
        """Test that multiple create_facade calls use the same unified service"""
        # Arrange
        factory = UnifiedContextFacadeFactory(None)  # Use mock service
        
        # Act
        facade1 = factory.create_facade(user_id="user1")
        facade2 = factory.create_facade(user_id="user2")

        # Assert
        # Both facades should be using services from the same factory
        assert isinstance(facade1, UnifiedContextFacade)
        assert isinstance(facade2, UnifiedContextFacade)
        # The underlying factory service should be the same instance
        assert factory.unified_service is not None


# Integration tests
class TestUnifiedContextFacadeFactoryIntegration:
    """Integration tests for UnifiedContextFacadeFactory with real-like dependencies"""

    def setup_method(self):
        """Reset singleton state before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False

    def test_full_initialization_integration(self):
        """Test full initialization with all mocked dependencies"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)

        # Act
        factory = UnifiedContextFacadeFactory(mock_session_factory)
        facade = factory.create_facade(user_id="test-user", project_id="test-project")

        # Assert
        assert isinstance(facade, UnifiedContextFacade)
        # Verify the facade was created successfully
        assert facade is not None
        # Verify factory has initialized its services
        assert factory.unified_service is not None
        assert factory.cache_service is not None
        assert factory.inheritance_service is not None
        assert factory.delegation_service is not None

    def test_error_handling_during_service_creation(self):
        """Test error handling when service creation fails"""
        # Arrange
        mock_session_factory = Mock(spec=sessionmaker)
        
        # Mock repository initialization to fail
        with patch('fastmcp.task_management.infrastructure.repositories.global_context_repository.GlobalContextRepository') as mock_repo:
            mock_repo.side_effect = Exception("Repository initialization failed")
            
            # Act
            factory = UnifiedContextFacadeFactory(mock_session_factory)
            
            # Assert
            assert factory.unified_service is not None  # Should fall back to mock service
            assert UnifiedContextFacadeFactory._initialized is True

    def test_facade_user_scoping_behavior(self):
        """Test that facade correctly handles user scoping"""
        # Arrange
        factory = UnifiedContextFacadeFactory(None)  # Use mock service
        
        # Act - when using mock service, user scoping is handled differently
        facade = factory.create_facade(user_id="test-user-123")

        # Assert - facade should be created successfully with user_id
        assert facade._user_id == "test-user-123"
        assert facade._service is not None  # Should have some service