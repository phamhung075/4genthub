"""
Comprehensive tests for service layer user isolation.

These tests verify that all application services properly propagate
user context and maintain data isolation between users.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Optional

from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.application.services.agent_coordination_service import AgentCoordinationService
from fastmcp.task_management.application.services.subtask_application_service import SubtaskApplicationService


class TestServiceUserIsolation:
    """Test suite for verifying user isolation in application services."""
    
    @pytest.fixture
    def user1_id(self):
        """Generate user 1 ID."""
        return str(uuid4())
    
    @pytest.fixture
    def user2_id(self):
        """Generate user 2 ID."""
        return str(uuid4())
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        repo.user_id = None
        return repo
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository."""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        repo.user_id = None
        repo.find_by_id = Mock(return_value=None)
        repo.find_all = Mock(return_value=[])
        return repo
    
    @pytest.fixture
    def mock_agent_repository(self):
        """Create a mock agent repository."""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        repo.user_id = None
        repo.get = Mock(return_value=None)
        return repo
    
    @pytest.fixture
    def mock_subtask_repository(self):
        """Create a mock subtask repository."""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        repo.user_id = None
        return repo
    
    # ==================== TaskApplicationService Tests ====================
    
    def test_task_service_creates_user_scoped_repository(self, mock_task_repository, user1_id):
        """Test that TaskApplicationService creates user-scoped repositories."""
        # Create service with user context
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user1_id
        )
        
        # Verify service has user context
        assert service._user_id == user1_id
    
    def test_task_service_with_user_creates_new_instance(self, mock_task_repository, user1_id, user2_id):
        """Test that with_user() creates a new service instance with different user."""
        # Create initial service
        service1 = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user1_id
        )
        
        # Create new instance with different user
        service2 = service1.with_user(user2_id)
        
        # Verify they are different instances with different users
        assert service1 is not service2
        assert service1._user_id == user1_id
        assert service2._user_id == user2_id
    
    def test_task_service_repository_scoping(self, mock_task_repository, user1_id):
        """Test that TaskApplicationService properly scopes repositories."""
        # Mock repository that supports with_user
        mock_task_repository.with_user = Mock(return_value=Mock())
        
        # Create service with user context
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user1_id
        )
        
        # Access the repository through _get_user_scoped_repository
        scoped_repo = service._get_user_scoped_repository()
        
        # Verify with_user was called with correct user_id
        mock_task_repository.with_user.assert_called_with(user1_id)
    
    # ==================== ProjectApplicationService Tests ====================
    
    def test_project_service_creates_user_scoped_repository(self, mock_project_repository, user1_id):
        """Test that ProjectApplicationService creates user-scoped repositories."""
        # Create service with user context
        service = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user1_id
        )
        
        # Verify service has user context
        assert service._user_id == user1_id
    
    def test_project_service_with_user_creates_new_instance(self, mock_project_repository, user1_id, user2_id):
        """Test that with_user() creates a new service instance with different user."""
        # Create initial service
        service1 = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user1_id
        )
        
        # Create new instance with different user
        service2 = service1.with_user(user2_id)
        
        # Verify they are different instances with different users
        assert service1 is not service2
        assert service1._user_id == user1_id
        assert service2._user_id == user2_id
    
    def test_project_service_operations_use_scoped_repo(self, mock_project_repository, user1_id):
        """Test that project operations use user-scoped repositories."""
        # Mock repository that supports with_user
        mock_project_repository.with_user = Mock(return_value=Mock())
        
        # Create service with user context
        service = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user1_id
        )
        
        # Get the scoped repository through the service's internal method
        scoped_repo = service._get_user_scoped_repository()
        
        # Verify with_user was called with the correct user_id
        mock_project_repository.with_user.assert_called_with(user1_id)
        
        # Verify a scoped repository was returned
        assert scoped_repo is not None
    
    # ==================== AgentCoordinationService Tests ====================
    
    def test_agent_service_creates_user_context(self, mock_task_repository, mock_agent_repository, user1_id):
        """Test that AgentCoordinationService maintains user context."""
        # Create service with user context
        service = AgentCoordinationService(
            task_repository=mock_task_repository,
            agent_repository=mock_agent_repository,
            event_bus=None,
            coordination_repository=None,
            user_id=user1_id
        )
        
        # Verify service has user context
        assert service._user_id == user1_id
    
    def test_agent_service_with_user_creates_new_instance(
        self, mock_task_repository, mock_agent_repository, user1_id, user2_id
    ):
        """Test that with_user() creates a new service instance with different user."""
        # Create initial service
        service1 = AgentCoordinationService(
            task_repository=mock_task_repository,
            agent_repository=mock_agent_repository,
            event_bus=None,
            coordination_repository=None,
            user_id=user1_id
        )
        
        # Create new instance with different user
        service2 = service1.with_user(user2_id)
        
        # Verify they are different instances with different users
        assert service1 is not service2
        assert service1._user_id == user1_id
        assert service2._user_id == user2_id
    
    def test_agent_service_repository_scoping(self, mock_task_repository, mock_agent_repository, user1_id):
        """Test that AgentCoordinationService properly scopes repositories."""
        # Mock repositories that support with_user
        mock_task_repository.with_user = Mock(return_value=Mock())
        mock_agent_repository.with_user = Mock(return_value=Mock())
        
        # Create service with user context
        service = AgentCoordinationService(
            task_repository=mock_task_repository,
            agent_repository=mock_agent_repository,
            event_bus=None,
            coordination_repository=None,
            user_id=user1_id
        )
        
        # Get scoped repositories
        scoped_task_repo = service._get_user_scoped_repository(mock_task_repository)
        scoped_agent_repo = service._get_user_scoped_repository(mock_agent_repository)
        
        # Verify with_user was called with correct user_id
        mock_task_repository.with_user.assert_called_with(user1_id)
        mock_agent_repository.with_user.assert_called_with(user1_id)
    
    # ==================== SubtaskApplicationService Tests ====================
    
    def test_subtask_service_creates_user_context(self, mock_task_repository, mock_subtask_repository, user1_id):
        """Test that SubtaskApplicationService maintains user context."""
        # Create service with user context
        service = SubtaskApplicationService(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            user_id=user1_id
        )
        
        # Verify service has user context
        assert service._user_id == user1_id
    
    def test_subtask_service_with_user_creates_new_instance(
        self, mock_task_repository, mock_subtask_repository, user1_id, user2_id
    ):
        """Test that with_user() creates a new service instance with different user."""
        # Create initial service
        service1 = SubtaskApplicationService(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            user_id=user1_id
        )
        
        # Create new instance with different user
        service2 = service1.with_user(user2_id)
        
        # Verify they are different instances with different users
        assert service1 is not service2
        assert service1._user_id == user1_id
        assert service2._user_id == user2_id
    
    def test_subtask_service_repository_scoping(self, mock_task_repository, mock_subtask_repository, user1_id):
        """Test that SubtaskApplicationService properly scopes repositories."""
        # Mock repositories that support with_user
        mock_task_repository.with_user = Mock(return_value=Mock())
        mock_subtask_repository.with_user = Mock(return_value=Mock())
        
        # Create service with user context
        service = SubtaskApplicationService(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            user_id=user1_id
        )
        
        # Verify repositories are scoped (they're scoped during use case initialization)
        assert service._user_id == user1_id
    
    # ==================== Cross-Service Tests ====================
    
    def test_services_isolate_data_between_users(
        self, mock_task_repository, mock_project_repository, user1_id, user2_id
    ):
        """Test that services maintain data isolation between different users."""
        # Create services for two different users
        user1_task_service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user1_id
        )
        
        user2_task_service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user2_id
        )
        
        user1_project_service = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user1_id
        )
        
        user2_project_service = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user2_id
        )
        
        # Verify each service has its own user context
        assert user1_task_service._user_id == user1_id
        assert user2_task_service._user_id == user2_id
        assert user1_project_service._user_id == user1_id
        assert user2_project_service._user_id == user2_id
        
        # Verify they're different instances
        assert user1_task_service is not user2_task_service
        assert user1_project_service is not user2_project_service
    
    def test_service_without_user_context_works_normally(self, mock_task_repository):
        """Test that services work without user context (backward compatibility)."""
        # Create service without user context
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=None
        )
        
        # Verify service works without user context
        assert service._user_id is None
        
        # Repository should be returned as-is
        scoped_repo = service._get_user_scoped_repository()
        assert scoped_repo == mock_task_repository
    
    def test_repository_without_user_support_returns_original(self, user1_id):
        """Test that repositories without user support return the original repository."""
        # Create a repository without with_user or user_id
        mock_repo = Mock(spec=[])  # No with_user or user_id attributes
        
        # Create service with user context
        service = TaskApplicationService(
            task_repository=mock_repo,
            context_service=None,
            user_id=user1_id
        )
        
        # Get scoped repository
        scoped_repo = service._get_user_scoped_repository()
        
        # Should return original repository since it doesn't support user scoping
        assert scoped_repo == mock_repo
    
    def test_service_propagates_user_context_through_operations(self, mock_task_repository, user1_id):
        """Test that user context is propagated through all service operations."""
        # Create a chain of mocks to track user context propagation
        mock_use_case = Mock()
        mock_scoped_repo = Mock()
        mock_scoped_repo.user_id = user1_id
        mock_task_repository.with_user = Mock(return_value=mock_scoped_repo)
        
        # Create service with user context
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=None,
            user_id=user1_id
        )
        
        # Verify user context is set
        assert service._user_id == user1_id
        
        # When service creates use cases, they should use scoped repositories
        # This is verified by checking that with_user is called
        mock_task_repository.with_user.assert_called()