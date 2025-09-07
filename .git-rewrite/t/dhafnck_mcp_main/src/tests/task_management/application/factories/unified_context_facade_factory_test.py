"""
Test suite for unified_context_facade_factory.py - Unified Context Facade Factory

Tests the factory pattern for creating UnifiedContextFacade instances with proper 
dependency injection and singleton behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.infrastructure.repositories.global_context_repository_user_scoped import GlobalContextRepositoryUserScoped

class TestUnifiedContextFacadeFactory:
    """Test UnifiedContextFacadeFactory class"""
    
    def setup_method(self):
        """Reset factory singleton before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False
    
    def test_singleton_pattern(self):
        """Test that factory implements singleton pattern correctly"""
        factory1 = UnifiedContextFacadeFactory()
        factory2 = UnifiedContextFacadeFactory()
        
        assert factory1 is factory2
        assert UnifiedContextFacadeFactory._instance is factory1
    
    def test_get_instance_creates_singleton(self):
        """Test get_instance class method creates singleton"""
        factory1 = UnifiedContextFacadeFactory.get_instance()
        factory2 = UnifiedContextFacadeFactory.get_instance()
        
        assert factory1 is factory2
        assert isinstance(factory1, UnifiedContextFacadeFactory)
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_init_with_database_config(self, mock_get_db_config):
        """Test initialization with available database configuration"""
        # Mock database config
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        # Mock all repository classes
        with patch.multiple(
            'fastmcp.task_management.application.factories.unified_context_facade_factory',
            GlobalContextRepository=Mock(),
            ProjectContextRepository=Mock(),
            BranchContextRepository=Mock(),
            TaskContextRepository=Mock(),
            ContextCacheService=Mock(),
            ContextInheritanceService=Mock(),
            ContextDelegationService=Mock(),
            ContextValidationService=Mock(),
            UnifiedContextService=Mock()
        ) as mocks:
            factory = UnifiedContextFacadeFactory()
            
            # Verify database config was called
            mock_get_db_config.assert_called_once()
            
            # Verify session factory was set
            assert factory.session_factory == mock_session_factory
            
            # Verify repositories were created
            mocks['GlobalContextRepository'].assert_called_once_with(mock_session_factory)
            mocks['ProjectContextRepository'].assert_called_once_with(mock_session_factory)
            mocks['BranchContextRepository'].assert_called_once_with(mock_session_factory)
            mocks['TaskContextRepository'].assert_called_once_with(mock_session_factory)
            
            # Verify services were created
            mocks['ContextCacheService'].assert_called_once()
            mocks['ContextInheritanceService'].assert_called_once()
            mocks['ContextDelegationService'].assert_called_once()
            mocks['ContextValidationService'].assert_called_once()
            mocks['UnifiedContextService'].assert_called_once()
            
            assert factory._initialized is True
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_init_database_unavailable_fallback(self, mock_get_db_config):
        """Test initialization fallback when database is unavailable"""
        # Mock database config to raise exception
        mock_get_db_config.side_effect = Exception("Database not available")
        
        # Mock the mock service
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            factory = UnifiedContextFacadeFactory()
            
            # Verify database config was attempted
            mock_get_db_config.assert_called_once()
            
            # Verify session factory is None
            assert factory.session_factory is None
            
            # Verify mock service was created
            mock_service_class.assert_called_once()
            assert factory.unified_service == mock_service
            assert factory._initialized is True
    
    def test_init_with_explicit_session_factory(self):
        """Test initialization with explicitly provided session factory"""
        mock_session_factory = Mock()
        
        with patch.multiple(
            'fastmcp.task_management.application.factories.unified_context_facade_factory',
            GlobalContextRepository=Mock(),
            ProjectContextRepository=Mock(),
            BranchContextRepository=Mock(),
            TaskContextRepository=Mock(),
            ContextCacheService=Mock(),
            ContextInheritanceService=Mock(),
            ContextDelegationService=Mock(),
            ContextValidationService=Mock(),
            UnifiedContextService=Mock()
        ):
            factory = UnifiedContextFacadeFactory(session_factory=mock_session_factory)
            
            assert factory.session_factory == mock_session_factory
            assert factory._initialized is True
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_init_repository_creation_failure(self, mock_get_db_config):
        """Test handling of repository creation failure"""
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        # Mock repository creation to fail
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.GlobalContextRepository') as mock_repo:
            mock_repo.side_effect = Exception("Repository creation failed")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                factory = UnifiedContextFacadeFactory()
                
                # Verify fallback to mock service
                assert factory.unified_service == mock_service
                assert factory._initialized is True
    
    def test_create_mock_service(self):
        """Test _create_mock_service method"""
        factory = UnifiedContextFacadeFactory()
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            factory._create_mock_service()
            
            mock_service_class.assert_called_once()
            assert factory.unified_service == mock_service

class TestFacadeCreation:
    """Test facade creation methods"""
    
    def setup_method(self):
        """Reset factory singleton before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_create_facade_without_user_id(self, mock_get_db_config):
        """Test creating facade without user_id uses shared service"""
        # Setup mocks
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        mock_unified_service = Mock()
        
        with patch.multiple(
            'fastmcp.task_management.application.factories.unified_context_facade_factory',
            GlobalContextRepository=Mock(),
            ProjectContextRepository=Mock(),
            BranchContextRepository=Mock(),
            TaskContextRepository=Mock(),
            ContextCacheService=Mock(),
            ContextInheritanceService=Mock(),
            ContextDelegationService=Mock(),
            ContextValidationService=Mock(),
            UnifiedContextService=Mock(return_value=mock_unified_service),
            UnifiedContextFacade=Mock()
        ) as mocks:
            factory = UnifiedContextFacadeFactory()
            
            result = factory.create_facade(
                project_id="project-123",
                git_branch_id="branch-456"
            )
            
            # Verify facade was created with shared service
            mocks['UnifiedContextFacade'].assert_called_once_with(
                unified_service=mock_unified_service,
                user_id=None,
                project_id="project-123",
                git_branch_id="branch-456"
            )
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_create_facade_with_user_id(self, mock_get_db_config):
        """Test creating facade with user_id creates user-scoped service"""
        # Setup mocks
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        mock_global_repo = Mock()
        mock_project_repo = Mock()
        mock_branch_repo = Mock()
        mock_task_repo = Mock()
        
        # Mock user-scoped repositories
        mock_user_global_repo = Mock()
        mock_user_project_repo = Mock()
        mock_user_branch_repo = Mock()
        mock_user_task_repo = Mock()
        
        mock_global_repo.with_user.return_value = mock_user_global_repo
        mock_project_repo.with_user.return_value = mock_user_project_repo
        mock_branch_repo.with_user.return_value = mock_user_branch_repo
        mock_task_repo.with_user.return_value = mock_user_task_repo
        
        mock_scoped_service = Mock()
        mock_scoped_service.with_user.return_value = mock_scoped_service
        
        with patch.multiple(
            'fastmcp.task_management.application.factories.unified_context_facade_factory',
            GlobalContextRepository=Mock(return_value=mock_global_repo),
            ProjectContextRepository=Mock(return_value=mock_project_repo),
            BranchContextRepository=Mock(return_value=mock_branch_repo),
            TaskContextRepository=Mock(return_value=mock_task_repo),
            ContextCacheService=Mock(),
            ContextInheritanceService=Mock(),
            ContextDelegationService=Mock(),
            ContextValidationService=Mock(),
            UnifiedContextService=Mock(return_value=mock_scoped_service),
            UnifiedContextFacade=Mock()
        ) as mocks:
            factory = UnifiedContextFacadeFactory()
            
            result = factory.create_facade(
                user_id="user-123",
                project_id="project-456",
                git_branch_id="branch-789"
            )
            
            # Verify user-scoped repositories were created
            mock_global_repo.with_user.assert_called_once_with("user-123")
            mock_project_repo.with_user.assert_called_once_with("user-123")
            mock_branch_repo.with_user.assert_called_once_with("user-123")
            mock_task_repo.with_user.assert_called_once_with("user-123")
            
            # Verify user-scoped services were created
            assert mocks['ContextInheritanceService'].call_count == 2  # Factory init + user-scoped
            assert mocks['ContextDelegationService'].call_count == 2  # Factory init + user-scoped
            assert mocks['UnifiedContextService'].call_count == 2  # Factory init + user-scoped
            
            # Verify facade was created with user-scoped service
            mocks['UnifiedContextFacade'].assert_called_once_with(
                unified_service=mock_scoped_service,
                user_id="user-123",
                project_id="project-456",
                git_branch_id="branch-789"
            )
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_create_facade_with_user_id_no_repos(self, mock_get_db_config):
        """Test creating facade with user_id when no repositories available (mock service)"""
        # Mock database unavailable
        mock_get_db_config.side_effect = Exception("Database not available")
        
        mock_unified_service = Mock()
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
            mock_service_class.return_value = mock_unified_service
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
                factory = UnifiedContextFacadeFactory()
                
                result = factory.create_facade(
                    user_id="user-123",
                    project_id="project-456"
                )
                
                # Verify facade was created with shared mock service (no user scoping)
                mock_facade_class.assert_called_once_with(
                    unified_service=mock_unified_service,
                    user_id="user-123",
                    project_id="project-456",
                    git_branch_id=None
                )
    
    def test_create_unified_service(self):
        """Test create_unified_service method"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            mock_unified_service = Mock()
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
                mock_service_class.return_value = mock_unified_service
                
                factory = UnifiedContextFacadeFactory()
                
                result = factory.create_unified_service()
                
                assert result == mock_unified_service

class TestAutoCreateGlobalContext:
    """Test auto_create_global_context method"""
    
    def setup_method(self):
        """Reset factory singleton before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False
    
    def test_auto_create_global_context_success(self):
        """Test successful auto-creation of global context"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade methods
                mock_facade = Mock()
                mock_facade.get_context.side_effect = Exception("Context doesn't exist")
                mock_facade.create_context.return_value = {"success": True}
                
                with patch.object(factory, 'create_facade', return_value=mock_facade):
                    result = factory.auto_create_global_context(user_id="user-123")
                    
                    assert result is True
                    
                    # Verify facade creation with user_id
                    factory.create_facade.assert_called_once_with(user_id="user-123")
                    
                    # Verify context creation was called
                    assert mock_facade.create_context.called
                    # Get the call arguments
                    call_args = mock_facade.create_context.call_args
                    assert call_args[1]["level"] == "global"
                    # Context ID will be generated dynamically based on user_id
                    assert call_args[1]["data"]["organization_name"] == "Default Organization"
                    assert "global_settings" in call_args[1]["data"]
    
    def test_auto_create_global_context_already_exists(self):
        """Test auto-creation when global context already exists"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade with existing context
                mock_facade = Mock()
                mock_facade.get_context.return_value = {"success": True, "context": {"data": "existing"}}
                
                with patch.object(factory, 'create_facade', return_value=mock_facade):
                    result = factory.auto_create_global_context(user_id="user-123")
                    
                    assert result is True
                    
                    # Verify context creation was not called
                    mock_facade.create_context.assert_not_called()
    
    def test_auto_create_global_context_no_user_id(self):
        """Test auto-creation fails when no user_id is provided"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                result = factory.auto_create_global_context()
                
                assert result is False
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_current_user_context')
    def test_auto_create_global_context_from_middleware(self, mock_get_current_user):
        """Test auto-creation gets user_id from middleware when not provided"""
        # Mock current user from middleware
        mock_user = Mock()
        mock_user.user_id = "middleware-user-123"
        mock_get_current_user.return_value = mock_user
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade methods
                mock_facade = Mock()
                mock_facade.get_context.side_effect = Exception("Context doesn't exist")
                mock_facade.create_context.return_value = {"success": True}
                
                with patch.object(factory, 'create_facade', return_value=mock_facade):
                    result = factory.auto_create_global_context()
                    
                    assert result is True
                    
                    # Verify facade creation with middleware user_id
                    factory.create_facade.assert_called_once_with(user_id="middleware-user-123")
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_current_user_context')
    def test_auto_create_global_context_middleware_user_with_id_attr(self, mock_get_current_user):
        """Test auto-creation with user object having 'id' attribute instead of 'user_id'"""
        # Mock current user with 'id' attribute
        mock_user = Mock()
        mock_user.id = "middleware-user-456"
        # Make sure user doesn't have user_id attribute
        mock_user.configure_mock(spec=['id'])
        mock_get_current_user.return_value = mock_user
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade methods
                mock_facade = Mock()
                mock_facade.get_context.side_effect = Exception("Context doesn't exist")
                mock_facade.create_context.return_value = {"success": True}
                
                with patch.object(factory, 'create_facade', return_value=mock_facade):
                    result = factory.auto_create_global_context()
                    
                    assert result is True
                    
                    # Verify facade creation with user.id
                    factory.create_facade.assert_called_once_with(user_id="middleware-user-456")
    
    def test_auto_create_global_context_creation_failure(self):
        """Test auto-creation when context creation fails"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade with failed context creation
                mock_facade = Mock()
                mock_facade.get_context.side_effect = Exception("Context doesn't exist")
                mock_facade.create_context.return_value = {"success": False, "error": "Creation failed"}
                
                with patch.object(factory, 'create_facade', return_value=mock_facade):
                    result = factory.auto_create_global_context(user_id="user-123")
                    
                    assert result is False
    
    def test_auto_create_global_context_exception_handling(self):
        """Test auto-creation handles exceptions gracefully"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService'):
                factory = UnifiedContextFacadeFactory()
                
                # Mock facade creation to raise exception
                with patch.object(factory, 'create_facade', side_effect=Exception("Facade creation failed")):
                    result = factory.auto_create_global_context(user_id="user-123")
                    
                    assert result is False

class TestFactoryIntegration:
    """Test factory integration scenarios"""
    
    def setup_method(self):
        """Reset factory singleton before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False
    
    @patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config')
    def test_factory_lifecycle_database_available(self, mock_get_db_config):
        """Test complete factory lifecycle with database available"""
        # Setup database config
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        mock_get_db_config.return_value = mock_db_config
        
        with patch.multiple(
            'fastmcp.task_management.application.factories.unified_context_facade_factory',
            GlobalContextRepository=Mock(),
            ProjectContextRepository=Mock(),
            BranchContextRepository=Mock(),
            TaskContextRepository=Mock(),
            ContextCacheService=Mock(),
            ContextInheritanceService=Mock(),
            ContextDelegationService=Mock(),
            ContextValidationService=Mock(),
            UnifiedContextService=Mock(),
            UnifiedContextFacade=Mock()
        ) as mocks:
            # 1. Create factory instance
            factory = UnifiedContextFacadeFactory.get_instance()
            assert factory is not None
            assert factory._initialized is True
            
            # 2. Create facade without user
            facade1 = factory.create_facade(project_id="project-1")
            assert mocks['UnifiedContextFacade'].called
            
            # 3. Create facade with user
            facade2 = factory.create_facade(user_id="user-1", project_id="project-1")
            assert mocks['UnifiedContextFacade'].call_count == 2
            
            # 4. Get unified service directly
            service = factory.create_unified_service()
            assert service is not None
            
            # 5. Auto-create global context
            with patch.object(factory, 'create_facade') as mock_create_facade:
                mock_facade = Mock()
                mock_facade.get_context.side_effect = Exception("Not found")
                mock_facade.create_context.return_value = {"success": True}
                mock_create_facade.return_value = mock_facade
                
                result = factory.auto_create_global_context("user-1")
                assert result is True
    
    def test_factory_lifecycle_database_unavailable(self):
        """Test complete factory lifecycle with database unavailable"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
                    # 1. Create factory instance
                    factory = UnifiedContextFacadeFactory.get_instance()
                    assert factory is not None
                    assert factory._initialized is True
                    assert factory.unified_service == mock_service
                    
                    # 2. Create facade
                    facade = factory.create_facade(project_id="project-1")
                    mock_facade_class.assert_called_once_with(
                        unified_service=mock_service,
                        user_id=None,
                        project_id="project-1",
                        git_branch_id=None
                    )
                    
                    # 3. Get unified service directly
                    service = factory.create_unified_service()
                    assert service == mock_service
    
    def test_multiple_factory_instances_same_singleton(self):
        """Test that multiple factory creations return same singleton"""
        factory1 = UnifiedContextFacadeFactory()
        factory2 = UnifiedContextFacadeFactory.get_instance()
        factory3 = UnifiedContextFacadeFactory()
        
        assert factory1 is factory2 is factory3
        assert UnifiedContextFacadeFactory._instance is factory1

class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    def setup_method(self):
        """Reset factory singleton before each test"""
        UnifiedContextFacadeFactory._instance = None
        UnifiedContextFacadeFactory._initialized = False
    
    def test_repository_with_user_not_available(self):
        """Test handling when repository doesn't have with_user method"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("Database not available")
            
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                factory = UnifiedContextFacadeFactory()
                
                # Create facade with user_id when no real repositories
                with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacade') as mock_facade_class:
                    result = factory.create_facade(user_id="user-123")
                    
                    # Should use shared service since no repositories available
                    mock_facade_class.assert_called_once_with(
                        unified_service=mock_service,
                        user_id="user-123",
                        project_id=None,
                        git_branch_id=None
                    )
    
    def test_service_creation_failure_during_init(self):
        """Test handling of service creation failure during initialization"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.get_db_config') as mock_get_db_config:
            mock_session_factory = Mock()
            mock_db_config = Mock()
            mock_db_config.SessionLocal = mock_session_factory
            mock_get_db_config.return_value = mock_db_config
            
            # Mock UnifiedContextService to fail
            with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextService') as mock_service_class:
                mock_service_class.side_effect = Exception("Service creation failed")
                
                with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.MockUnifiedContextService') as mock_mock_service_class:
                    mock_mock_service = Mock()
                    mock_mock_service_class.return_value = mock_mock_service
                    
                    # Mock other dependencies
                    with patch.multiple(
                        'fastmcp.task_management.application.factories.unified_context_facade_factory',
                        GlobalContextRepository=Mock(),
                        ProjectContextRepository=Mock(),
                        BranchContextRepository=Mock(),
                        TaskContextRepository=Mock(),
                        ContextCacheService=Mock(),
                        ContextInheritanceService=Mock(),
                        ContextDelegationService=Mock(),
                        ContextValidationService=Mock()
                    ):
                        factory = UnifiedContextFacadeFactory()
                        
                        # Should fallback to mock service
                        assert factory.unified_service == mock_mock_service
                        assert factory._initialized is True

if __name__ == "__main__":
    pytest.main([__file__])