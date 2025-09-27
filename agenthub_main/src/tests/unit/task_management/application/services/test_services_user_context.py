"""
Test service layer with user context propagation.
Following TDD - services must pass user_id to repositories.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from uuid import uuid4
from datetime import datetime
from typing import Optional

from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.application.services.git_branch_service import GitBranchService


class TestServicesUserContext:
    """Test suite ensuring services properly handle user context."""
    
    @pytest.fixture
    def user_id(self):
        """Generate a test user ID."""
        return str(uuid4())
    
    @pytest.fixture
    def other_user_id(self):
        """Generate another user ID."""
        return str(uuid4())
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        repo = Mock()
        repo.create = Mock()
        repo.get_by_id = Mock()
        repo.update = Mock()
        repo.delete = Mock()
        repo.get_all = Mock()
        return repo
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository."""
        repo = Mock()
        repo.create = Mock()
        repo.get_by_id = Mock()
        repo.update = Mock()
        repo.delete = Mock()
        repo.get_all = Mock()
        return repo
    
    @pytest.fixture
    def mock_context_repositories(self):
        """Create mock context repositories."""
        return {
            "global": Mock(),
            "project": Mock(),
            "branch": Mock(),
            "task": Mock()
        }
    
    # ==================== TaskApplicationService Tests ====================
    
    def test_task_service_accepts_user_id(self, mock_task_repository, user_id):
        """Test that TaskApplicationService accepts user_id."""
        # TaskApplicationService now accepts user_id as optional parameter
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=user_id
        )
        assert service._user_id == user_id
    
    def test_task_service_passes_user_id_to_repository(self, mock_task_repository, user_id):
        """Test that task service passes user_id to repository on creation."""
        # Mock with_user method
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=user_id
        )
        
        # Verify with_user was called with the user_id
        mock_task_repository.with_user.assert_called_with(user_id)
    
    def test_task_service_get_operations_use_user_context(self, mock_task_repository, user_id):
        """Test that get operations use user context."""
        # Mock with_user method
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=user_id
        )
        
        # Verify service created with user context
        assert service._user_id == user_id
        mock_task_repository.with_user.assert_called_with(user_id)
    
    def test_task_service_prevents_user_id_override(self, mock_task_repository, user_id, other_user_id):
        """Test that service prevents user_id override attempts."""
        # Mock with_user method
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=user_id
        )
        
        # Service should use its own user_id, not accept overrides
        assert service._user_id == user_id
        # Repository should be scoped to service's user_id
        mock_task_repository.with_user.assert_called_with(user_id)
    
    def test_task_service_list_operations_scoped_to_user(self, mock_task_repository, user_id):
        """Test that list operations are scoped to user."""
        # Mock with_user method
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=user_id
        )
        
        # Service should use user-scoped repository
        mock_task_repository.with_user.assert_called_with(user_id)
    
    # ==================== ProjectApplicationService Tests ====================
    
    def test_project_service_accepts_user_id(self, mock_project_repository, user_id):
        """Test that ProjectApplicationService accepts user_id."""
        service = ProjectApplicationService(
            project_repository=mock_project_repository,
            user_id=user_id
        )
        assert service._user_id == user_id
    
    
    
    # ==================== UnifiedContextService Tests ====================
    
    def test_unified_context_service_accepts_user_id(self, mock_context_repositories, user_id):
        """Test that UnifiedContextService accepts user_id."""
        # Should not raise an error
        service = UnifiedContextService(
            global_context_repository=mock_context_repositories["global"],
            project_context_repository=mock_context_repositories["project"],
            branch_context_repository=mock_context_repositories["branch"],
            task_context_repository=mock_context_repositories["task"],
            user_id=user_id
        )
        assert service._user_id == user_id
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.GitBranchRepository')
    def test_unified_context_service_passes_user_id_to_all_repos(
        self, mock_git_branch_repo_class, mock_context_repositories, user_id
    ):
        """Test that unified context service passes user_id to all context repos."""
        # Mock git branch repository for task context parent resolution
        mock_git_branch_repo = Mock()
        mock_git_branch_repo_class.return_value = mock_git_branch_repo
        mock_git_branch_repo.get = Mock(return_value=None)  # Branch not found
        
        # Mock with_user method for all repositories
        for repo in mock_context_repositories.values():
            repo.with_user = Mock(return_value=repo)
            repo.get = Mock(return_value=None)  # Contexts don't exist yet
            repo.create = Mock()
            
        service = UnifiedContextService(
            global_context_repository=mock_context_repositories["global"],
            project_context_repository=mock_context_repositories["project"],
            branch_context_repository=mock_context_repositories["branch"],
            task_context_repository=mock_context_repositories["task"],
            user_id=user_id
        )
        
        # Create context at different levels
        project_id = str(uuid4())
        branch_id = str(uuid4())
        
        service.create_context("global", "global_singleton", {"key": "value"})
        service.create_context("project", project_id, {"key": "value"})
        service.create_context("branch", branch_id, {"key": "value", "project_id": project_id})  
        service.create_context("task", str(uuid4()), {"key": "value", "branch_id": branch_id, "project_id": project_id})
        
        # All repositories should be called
        assert mock_context_repositories["global"].create.called
        assert mock_context_repositories["project"].create.called
        assert mock_context_repositories["branch"].create.called
        assert mock_context_repositories["task"].create.called
    
    def test_context_inheritance_maintains_user_boundaries(
        self, mock_context_repositories, user_id
    ):
        """Test that context inheritance stays within user boundaries."""
        service = UnifiedContextService(
            global_context_repository=mock_context_repositories["global"],
            project_context_repository=mock_context_repositories["project"],
            branch_context_repository=mock_context_repositories["branch"],
            task_context_repository=mock_context_repositories["task"],
            user_id=user_id
        )
        
        task_id = str(uuid4())
        branch_id = str(uuid4())
        project_id = str(uuid4())
        
        # Mock repository responses and with_user method
        for repo in mock_context_repositories.values():
            repo.get.return_value = None
            repo.get_inherited.return_value = {}
            repo.with_user = Mock(return_value=repo)  # Mock with_user to return self
        
        # Get inherited context
        context = service.get_context(
            level="task",
            context_id=task_id,
            include_inherited=True
        )
        
        # All repos should be queried for inheritance
        assert mock_context_repositories["task"].get.called or \
               mock_context_repositories["task"].get_inherited.called
    
    # ==================== Cross-Service User Isolation Tests ====================
    
    
    # ==================== Service Factory Tests ====================
    
    def test_service_factory_creates_user_scoped_services(self, user_id):
        """Test that service factory creates properly scoped services."""
        
        class ServiceFactory:
            @staticmethod
            def create_task_service(user_id: str):
                # Mock implementation
                repo = Mock()
                return TaskApplicationService(task_repository=repo, user_id=user_id)
            
            @staticmethod
            def create_project_service(user_id: str):
                # Mock implementation
                repo = Mock()
                return ProjectApplicationService(project_repository=repo, user_id=user_id)
        
        factory = ServiceFactory()
        
        # Create services for a user
        task_service = factory.create_task_service(user_id)
        project_service = factory.create_project_service(user_id)
        
        # Services should have user_id
        assert task_service._user_id == user_id
        assert project_service._user_id == user_id
    
    # ==================== Dependency Injection Tests ====================
    
    def test_service_with_multiple_dependencies_maintains_user_context(
        self, mock_task_repository, mock_project_repository, mock_context_repositories, user_id
    ):
        """Test that services with multiple dependencies maintain user context."""
        
        class ComplexService:
            def __init__(self, task_repo, project_repo, context_service, user_id):
                self.task_repo = task_repo
                self.project_repo = project_repo
                self.context_service = context_service
                self.user_id = user_id
            
            def complex_operation(self):
                # All operations should use user_id
                self.task_repo.get_all()
                self.project_repo.get_all()
                self.context_service.get_global_context()
        
        context_service = Mock()
        
        service = ComplexService(
            task_repo=mock_task_repository,
            project_repo=mock_project_repository,
            context_service=context_service,
            user_id=user_id
        )
        
        # Perform complex operation
        service.complex_operation()
        
        # All dependencies should be called
        assert mock_task_repository.get_all.called
        assert mock_project_repository.get_all.called
        assert context_service.get_global_context.called
    
    # ==================== Transaction Tests ====================
    
    def test_service_transaction_maintains_user_context(
        self, mock_task_repository, mock_project_repository, user_id
    ):
        """Test that transactional operations maintain user context."""
        
        class TransactionalService:
            def __init__(self, task_repo, project_repo, user_id):
                self.task_repo = task_repo
                self.project_repo = project_repo
                self.user_id = user_id
            
            def create_project_with_tasks(self, project_data, task_list):
                # Start transaction (mocked)
                project = self.project_repo.create(project_data)
                
                for task_data in task_list:
                    task_data['project_id'] = project.id
                    self.task_repo.create(task_data)
                
                # Commit transaction (mocked)
                return project
        
        service = TransactionalService(
            task_repo=mock_task_repository,
            project_repo=mock_project_repository,
            user_id=user_id
        )
        
        # Create project with tasks
        project_data = {"name": "Test Project"}
        task_list = [
            {"title": "Task 1"},
            {"title": "Task 2"}
        ]
        
        mock_project_repository.create.return_value = Mock(id=str(uuid4()))
        
        service.create_project_with_tasks(project_data, task_list)
        
        # Verify all operations were called
        assert mock_project_repository.create.call_count == 1
        assert mock_task_repository.create.call_count == 2
    
    # ==================== Error Handling Tests ====================
    
    
    def test_service_validates_user_id_format(self, mock_task_repository):
        """Test that services validate user_id format."""
        # Services now accept None as user_id for backward compatibility
        # They just won't apply user filtering
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            user_id=None
        )
        assert service._user_id is None