"""Tests for UnifiedContextFacadeFactory"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService


class TestUnifiedContextFacadeFactory:
    """Test cases for UnifiedContextFacadeFactory"""

    def setup_method(self):
        """Set up test fixtures"""
        # Reset singleton state before each test
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False

    def teardown_method(self):
        """Clean up after each test"""
        # Reset singleton state after each test
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False

    def test_singleton_pattern(self):
        """Test that factory implements singleton pattern"""
        factory1 = UnifiedContextFacadeFactory()
        factory2 = UnifiedContextFacadeFactory()
        
        assert factory1 is factory2
        assert UnifiedContextFacadeFactory._instance is factory1

    def test_get_instance_method(self):
        """Test get_instance class method"""
        factory1 = UnifiedContextFacadeFactory.get_instance()
        factory2 = UnifiedContextFacadeFactory.get_instance()
        
        assert factory1 is factory2
        assert isinstance(factory1, UnifiedContextFacadeFactory)

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_init_with_database_success(self, mock_get_db_config):
        """Test successful initialization with database"""
        # Setup mock database config
        mock_db_config = Mock()
        mock_session_factory = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        # Mock all repository classes
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository') as mock_global_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ProjectContextRepository') as mock_project_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.BranchContextRepository') as mock_branch_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.TaskContextRepository') as mock_task_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextCacheService') as mock_cache_service, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextInheritanceService') as mock_inheritance_service, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextDelegationService') as mock_delegation_service, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextValidationService') as mock_validation_service, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService') as mock_unified_service:
            
            factory = UnifiedContextFacadeFactory()
            
            # Verify repositories were created
            mock_global_repo.assert_called_once_with(mock_session_factory)
            mock_project_repo.assert_called_once_with(mock_session_factory)
            mock_branch_repo.assert_called_once_with(mock_session_factory)
            mock_task_repo.assert_called_once_with(mock_session_factory)
            
            # Verify services were created
            mock_cache_service.assert_called_once()
            mock_inheritance_service.assert_called_once()
            mock_delegation_service.assert_called_once()
            mock_validation_service.assert_called_once()
            mock_unified_service.assert_called_once()
            
            assert factory.session_factory == mock_session_factory
            assert factory.unified_service is not None

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_init_with_database_failure(self, mock_get_db_config):
        """Test initialization when database is not available"""
        mock_get_db_config.side_effect = Exception("Database connection failed")
        
        with patch.object(UnifiedContextFacadeFactory, '_create_mock_service') as mock_create_mock:
            factory = UnifiedContextFacadeFactory()
            
            mock_create_mock.assert_called_once()
            assert UnifiedContextFacadeFactory._initialized is True

    def test_init_with_custom_session_factory(self):
        """Test initialization with custom session factory"""
        custom_session_factory = Mock()
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository') as mock_global_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ProjectContextRepository') as mock_project_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.BranchContextRepository') as mock_branch_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.TaskContextRepository') as mock_task_repo, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextCacheService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextInheritanceService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextDelegationService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextValidationService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService'):
            
            factory = UnifiedContextFacadeFactory(custom_session_factory)
            
            # Verify custom session factory was used
            mock_global_repo.assert_called_once_with(custom_session_factory)
            mock_project_repo.assert_called_once_with(custom_session_factory)
            mock_branch_repo.assert_called_once_with(custom_session_factory)
            mock_task_repo.assert_called_once_with(custom_session_factory)
            
            assert factory.session_factory == custom_session_factory

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService')
    def test_create_mock_service(self, mock_mock_service_class):
        """Test creation of mock service"""
        mock_service_instance = Mock()
        mock_mock_service_class.return_value = mock_service_instance
        
        factory = UnifiedContextFacadeFactory()
        factory._create_mock_service()
        
        assert factory.unified_service == mock_service_instance
        mock_mock_service_class.assert_called_once()

    def test_create_facade_without_user_id(self):
        """Test facade creation without user ID"""
        # Setup factory with mock service
        factory = UnifiedContextFacadeFactory()
        mock_unified_service = Mock()
        factory.unified_service = mock_unified_service
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
            mock_facade = Mock()
            mock_facade_class.return_value = mock_facade
            
            result = factory.create_facade(project_id="proj-123", git_branch_id="branch-456")
            
            mock_facade_class.assert_called_once_with(
                unified_service=mock_unified_service,
                user_id=None,
                project_id="proj-123",
                git_branch_id="branch-456"
            )
            
            assert result == mock_facade

    def test_create_facade_with_user_id_and_real_repositories(self):
        """Test facade creation with user ID and real repositories"""
        user_id = "user-123"
        project_id = "proj-456"
        git_branch_id = "branch-789"
        
        # Setup factory with mock repositories
        factory = UnifiedContextFacadeFactory()
        
        # Mock repositories with with_user method
        mock_global_repo = Mock()
        mock_global_repo.with_user.return_value = Mock()
        mock_project_repo = Mock()
        mock_project_repo.with_user.return_value = Mock()
        mock_branch_repo = Mock()
        mock_branch_repo.with_user.return_value = Mock()
        mock_task_repo = Mock()
        mock_task_repo.with_user.return_value = Mock()
        
        factory.global_repo = mock_global_repo
        factory.project_repo = mock_project_repo
        factory.branch_repo = mock_branch_repo
        factory.task_repo = mock_task_repo
        factory.cache_service = Mock()
        factory.validation_service = Mock()
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextInheritanceService') as mock_inheritance_class, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextDelegationService') as mock_delegation_class, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService') as mock_unified_service_class, \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
            
            # Setup mocks
            mock_scoped_service = Mock()
            mock_scoped_service.with_user.return_value = mock_scoped_service
            mock_unified_service_class.return_value = mock_scoped_service
            
            mock_facade = Mock()
            mock_facade_class.return_value = mock_facade
            
            result = factory.create_facade(
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            # Verify user-scoped repositories were created
            mock_global_repo.with_user.assert_called_once_with(user_id)
            mock_project_repo.with_user.assert_called_once_with(user_id)
            mock_branch_repo.with_user.assert_called_once_with(user_id)
            mock_task_repo.with_user.assert_called_once_with(user_id)
            
            # Verify facade was created with scoped service
            mock_facade_class.assert_called_once_with(
                unified_service=mock_scoped_service,
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            assert result == mock_facade

    def test_create_unified_service(self):
        """Test getting unified service directly"""
        factory = UnifiedContextFacadeFactory()
        mock_service = Mock()
        factory.unified_service = mock_service
        
        result = factory.create_unified_service()
        
        assert result == mock_service

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GLOBAL_SINGLETON_UUID', 'global-uuid')
    def test_auto_create_global_context_already_exists(self):
        """Test auto-creation when global context already exists"""
        factory = UnifiedContextFacadeFactory()
        
        # Mock global repo with existing context
        mock_global_repo = Mock()
        mock_context = Mock()
        mock_global_repo.get.return_value = mock_context
        factory.global_repo = mock_global_repo
        
        result = factory.auto_create_global_context()
        
        assert result is True
        mock_global_repo.get.assert_called_once_with('global-uuid')

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GLOBAL_SINGLETON_UUID', 'global-uuid')
    def test_auto_create_global_context_creation_success(self):
        """Test successful auto-creation of global context"""
        factory = UnifiedContextFacadeFactory()
        
        # Mock global repo without existing context
        mock_global_repo = Mock()
        mock_global_repo.get.side_effect = Exception("Context doesn't exist")
        factory.global_repo = mock_global_repo
        
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_facade = Mock()
            mock_facade.create_context.return_value = {"success": True}
            mock_create_facade.return_value = mock_facade
            
            result = factory.auto_create_global_context()
            
            assert result is True
            
            # Verify facade was created with system user
            mock_create_facade.assert_called_once_with(user_id="00000000-0000-0000-0000-000000000000")
            
            # Verify context creation was called
            mock_facade.create_context.assert_called_once()
            call_args = mock_facade.create_context.call_args
            assert call_args[1]['level'] == 'global'
            assert call_args[1]['context_id'] == 'global-uuid'
            assert 'data' in call_args[1]

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GLOBAL_SINGLETON_UUID', 'global-uuid')
    def test_auto_create_global_context_creation_failure(self):
        """Test failed auto-creation of global context"""
        factory = UnifiedContextFacadeFactory()
        
        # Mock global repo without existing context
        mock_global_repo = Mock()
        mock_global_repo.get.side_effect = Exception("Context doesn't exist")
        factory.global_repo = mock_global_repo
        
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_facade = Mock()
            mock_facade.create_context.return_value = {"success": False, "error": "Creation failed"}
            mock_create_facade.return_value = mock_facade
            
            result = factory.auto_create_global_context()
            
            assert result is False

    def test_auto_create_global_context_exception_handling(self):
        """Test exception handling in auto-creation"""
        factory = UnifiedContextFacadeFactory()
        
        # Mock global repo that raises exception
        mock_global_repo = Mock()
        mock_global_repo.get.side_effect = Exception("Database error")
        factory.global_repo = mock_global_repo
        
        with patch.object(factory, 'create_facade') as mock_create_facade:
            mock_create_facade.side_effect = Exception("Facade creation failed")
            
            result = factory.auto_create_global_context()
            
            assert result is False

    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.logger')
    def test_logging_during_initialization(self, mock_logger):
        """Test that initialization events are logged"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_db_config = Mock()
            mock_session_factory = Mock()
            mock_db_config.SessionLocal = mock_session_factory
            mock_get_db_config.return_value = mock_db_config
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ProjectContextRepository'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.BranchContextRepository'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.TaskContextRepository'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextCacheService'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextInheritanceService'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextDelegationService'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextValidationService'), \
                 patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService'):
                
                UnifiedContextFacadeFactory()
                
                mock_logger.info.assert_called_with("UnifiedContextFacadeFactory initialized with database")

    def test_singleton_prevents_reinitialization(self):
        """Test that singleton pattern prevents reinitialization"""
        # Create first instance with mock to track initialization
        with patch.object(UnifiedContextFacadeFactory, '_create_mock_service') as mock_init:
            factory1 = UnifiedContextFacadeFactory()
            init_calls_after_first = mock_init.call_count
            
            # Create second instance - should not reinitialize
            factory2 = UnifiedContextFacadeFactory()
            init_calls_after_second = mock_init.call_count
            
            assert factory1 is factory2
            assert init_calls_after_second == init_calls_after_first  # No additional initialization

    def test_get_instance_with_session_factory(self):
        """Test get_instance with session factory parameter"""
        custom_session_factory = Mock()
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ProjectContextRepository'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.BranchContextRepository'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.TaskContextRepository'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextCacheService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextInheritanceService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextDelegationService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.ContextValidationService'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService'):
            
            factory = UnifiedContextFacadeFactory.get_instance(custom_session_factory)
            
            assert factory.session_factory == custom_session_factory

    def test_repository_map_creation(self):
        """Test that repository map is correctly created"""
        factory = UnifiedContextFacadeFactory()
        
        # Mock repositories
        mock_global_repo = Mock()
        mock_project_repo = Mock()
        mock_branch_repo = Mock()
        mock_task_repo = Mock()
        
        factory.global_repo = mock_global_repo
        factory.project_repo = mock_project_repo
        factory.branch_repo = mock_branch_repo
        factory.task_repo = mock_task_repo
        
        # Test that services can access repositories through the factory
        assert hasattr(factory, 'global_repo')
        assert hasattr(factory, 'project_repo')
        assert hasattr(factory, 'branch_repo')
        assert hasattr(factory, 'task_repo')

    def test_create_facade_parameter_forwarding(self):
        """Test that create_facade forwards all parameters correctly"""
        factory = UnifiedContextFacadeFactory()
        factory.unified_service = Mock()
        
        user_id = "user-123"
        project_id = "project-456" 
        git_branch_id = "branch-789"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
            mock_facade = Mock()
            mock_facade_class.return_value = mock_facade
            
            result = factory.create_facade(
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            # Verify all parameters were forwarded
            mock_facade_class.assert_called_once_with(
                unified_service=factory.unified_service,
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            assert result == mock_facade