"""
Tests for Create Git Branch Use Case

This module tests the CreateGitBranchUseCase functionality including:
- Git branch creation within projects
- Project validation and error handling
- Branch context creation integration
- Authentication and user validation
- Domain logic integration and repository updates
- Error scenarios and edge cases
"""

import pytest
import sys
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestCreateGitBranchUseCase:
    """Test suite for CreateGitBranchUseCase"""
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def use_case(self, mock_project_repository):
        """Create use case instance with mocked dependencies"""
        return CreateGitBranchUseCase(mock_project_repository)
    
    @pytest.fixture
    def mock_project_entity(self):
        """Create a mock project entity"""
        project = Mock(spec=Project)
        project.id = "project-123"
        project.name = "Test Project"
        project.description = "Test Description"
        project.created_at = datetime.now(timezone.utc)
        project.create_git_branch = Mock()
        return project
    
    @pytest.fixture
    def mock_git_branch_entity(self):
        """Create a mock git branch entity"""
        git_branch = Mock(spec=GitBranch)
        git_branch.id = "branch-123"
        git_branch.name = "feature/test-branch"
        git_branch.description = "Test branch description"
        git_branch.project_id = "project-123"
        git_branch.created_at = datetime.now(timezone.utc)
        git_branch.get_task_count.return_value = 0
        git_branch.get_completed_task_count.return_value = 0
        git_branch.get_progress_percentage.return_value = 0.0
        return git_branch
    
    def test_use_case_initialization(self, mock_project_repository):
        """Test use case initialization with repository"""
        use_case = CreateGitBranchUseCase(mock_project_repository)
        
        assert use_case._project_repository == mock_project_repository


class TestCreateGitBranchUseCaseExecute:
    """Test suite for execute method"""
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def use_case(self, mock_project_repository):
        """Create use case instance with mocked dependencies"""
        return CreateGitBranchUseCase(mock_project_repository)
    
    @pytest.fixture
    def mock_project_entity(self):
        """Create a mock project entity"""
        project = Mock(spec=Project)
        project.id = "project-123"
        project.name = "Test Project"
        project.create_git_branch = Mock()
        return project
    
    @pytest.fixture
    def mock_git_branch_entity(self):
        """Create a mock git branch entity"""
        git_branch = Mock(spec=GitBranch)
        git_branch.id = "branch-123"
        git_branch.name = "feature/test-branch"
        git_branch.description = "Test branch description"
        git_branch.project_id = "project-123"
        git_branch.created_at = datetime.now(timezone.utc)
        git_branch.get_task_count.return_value = 0
        git_branch.get_completed_task_count.return_value = 0
        git_branch.get_progress_percentage.return_value = 0.0
        return git_branch
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test successful git branch creation"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup project domain logic
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                with patch('fastmcp.task_management.domain.constants.validate_user_id') as mock_validate_user:
                    # Setup authentication
                    mock_auth_config.is_default_user_allowed.return_value = True
                    mock_auth_config.get_fallback_user_id.return_value = "default_user"
                    mock_validate_user.return_value = "default_user"
                    
                    # Setup context facade
                    mock_factory = Mock()
                    mock_context_facade = Mock()
                    mock_context_facade.create_context.return_value = {"success": True}
                    mock_factory.create_facade.return_value = mock_context_facade
                    mock_factory_class.return_value = mock_factory
                    
                    result = await use_case.execute(
                        project_id="project-123",
                        git_branch_name="feature/test-branch",
                        branch_name="feature/test-branch",
                        branch_description="Test branch description"
                    )
                    
                    assert result["success"] is True
                    assert result["git_branch"]["id"] == "branch-123"
                    assert result["git_branch"]["name"] == "feature/test-branch"
                    assert result["git_branch"]["description"] == "Test branch description"
                    assert result["git_branch"]["project_id"] == "project-123"
                    assert "Git branch 'feature/test-branch' created successfully" in result["message"]
                    
                    # Verify domain logic was called
                    mock_project_entity.create_git_branch.assert_called_once_with(
                        git_branch_name="feature/test-branch",
                        name="feature/test-branch",
                        description="Test branch description"
                    )
                    
                    # Verify repository update was called
                    mock_project_repository.update.assert_called_once_with(mock_project_entity)
    
    @pytest.mark.asyncio
    async def test_execute_project_not_found(self, use_case, mock_project_repository):
        """Test git branch creation when project is not found"""
        mock_project_repository.find_by_id.return_value = None
        
        result = await use_case.execute(
            project_id="nonexistent-project",
            git_branch_name="feature/test",
            branch_name="feature/test"
        )
        
        assert result["success"] is False
        assert "Project with ID 'nonexistent-project' not found" in result["error"]
        mock_project_repository.find_by_id.assert_called_once_with("nonexistent-project")
    
    @pytest.mark.asyncio
    async def test_execute_domain_validation_error(self, use_case, mock_project_repository, mock_project_entity):
        """Test git branch creation with domain validation error"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup project domain logic to raise ValueError
        mock_project_entity.create_git_branch.side_effect = ValueError("Branch name already exists")
        
        result = await use_case.execute(
            project_id="project-123",
            git_branch_name="existing-branch",
            branch_name="existing-branch"
        )
        
        assert result["success"] is False
        assert "Branch name already exists" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_success_without_description(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test successful git branch creation without description"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup project domain logic
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                # Setup authentication
                mock_auth_config.is_default_user_allowed.return_value = True
                mock_auth_config.get_fallback_user_id.return_value = "default_user"
                
                # Setup context facade
                mock_factory = Mock()
                mock_context_facade = Mock()
                mock_context_facade.create_context.return_value = {"success": True}
                mock_factory.create_facade.return_value = mock_context_facade
                mock_factory_class.return_value = mock_factory
                
                result = await use_case.execute(
                    project_id="project-123",
                    git_branch_name="feature/minimal",
                    branch_name="feature/minimal"
                )
                
                assert result["success"] is True
                
                # Verify domain logic was called with empty description
                mock_project_entity.create_git_branch.assert_called_once_with(
                    git_branch_name="feature/minimal",
                    name="feature/minimal",
                    description=""
                )
    
    @pytest.mark.asyncio
    async def test_execute_includes_branch_statistics(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test that execute includes branch statistics in response"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup git branch with statistics
        mock_git_branch_entity.get_task_count.return_value = 5
        mock_git_branch_entity.get_completed_task_count.return_value = 3
        mock_git_branch_entity.get_progress_percentage.return_value = 60.0
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                # Setup authentication
                mock_auth_config.is_default_user_allowed.return_value = True
                mock_auth_config.get_fallback_user_id.return_value = "default_user"
                
                # Setup context facade
                mock_factory = Mock()
                mock_context_facade = Mock()
                mock_context_facade.create_context.return_value = {"success": True}
                mock_factory.create_facade.return_value = mock_context_facade
                mock_factory_class.return_value = mock_factory
                
                result = await use_case.execute(
                    project_id="project-123",
                    git_branch_name="feature/stats",
                    branch_name="feature/stats"
                )
                
                assert result["success"] is True
                assert result["git_branch"]["task_count"] == 5
                assert result["git_branch"]["completed_tasks"] == 3
                assert result["git_branch"]["progress"] == 60.0


class TestCreateGitBranchUseCaseContextCreation:
    """Test suite for branch context creation"""
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def use_case(self, mock_project_repository):
        """Create use case instance with mocked dependencies"""
        return CreateGitBranchUseCase(mock_project_repository)
    
    @pytest.fixture
    def mock_project_entity(self):
        """Create a mock project entity"""
        project = Mock(spec=Project)
        project.id = "project-123"
        project.name = "Test Project"
        project.create_git_branch = Mock()
        return project
    
    @pytest.fixture
    def mock_git_branch_entity(self):
        """Create a mock git branch entity"""
        git_branch = Mock(spec=GitBranch)
        git_branch.id = "branch-123"
        git_branch.name = "feature/context-test"
        git_branch.description = "Context test branch"
        git_branch.project_id = "project-123"
        git_branch.created_at = datetime.now(timezone.utc)
        git_branch.get_task_count.return_value = 0
        git_branch.get_completed_task_count.return_value = 0
        git_branch.get_progress_percentage.return_value = 0.0
        return git_branch
    
    @pytest.mark.asyncio
    async def test_execute_context_creation_success(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test successful branch context creation"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                with patch('fastmcp.task_management.domain.constants.validate_user_id') as mock_validate_user:
                    # Setup authentication
                    mock_auth_config.is_default_user_allowed.return_value = True
                    mock_auth_config.get_fallback_user_id.return_value = "default_user"
                    mock_validate_user.return_value = "default_user"
                    
                    # Setup context facade
                    mock_factory = Mock()
                    mock_context_facade = Mock()
                    mock_context_facade.create_context.return_value = {"success": True}
                    mock_factory.create_facade.return_value = mock_context_facade
                    mock_factory_class.return_value = mock_factory
                    
                    result = await use_case.execute(
                        project_id="project-123",
                        git_branch_name="feature/context-test",
                        branch_name="feature/context-test",
                        branch_description="Context test branch"
                    )
                    
                    assert result["success"] is True
                    
                    # Verify context facade creation
                    mock_factory.create_facade.assert_called_once_with(
                        user_id="default_user",
                        project_id="project-123",
                        git_branch_id="branch-123"
                    )
                    
                    # Verify context creation was called
                    mock_context_facade.create_context.assert_called_once()
                    call_args = mock_context_facade.create_context.call_args
                    
                    assert call_args[1]["level"] == "branch"
                    assert call_args[1]["context_id"] == "branch-123"
                    
                    context_data = call_args[1]["data"]
                    assert context_data["branch_id"] == "branch-123"
                    assert context_data["branch_name"] == "feature/context-test"
                    assert context_data["project_id"] == "project-123"
                    assert context_data["description"] == "Context test branch"
                    assert "created_at" in context_data
                    assert "workflow_state" in context_data
                    assert "branch_settings" in context_data
    
    @pytest.mark.asyncio
    async def test_execute_context_creation_with_user_authentication(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test branch context creation with user authentication"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                with patch('fastmcp.task_management.domain.constants.validate_user_id') as mock_validate_user:
                    # Setup authentication - no default user allowed
                    mock_auth_config.is_default_user_allowed.return_value = False
                    mock_validate_user.return_value = "authenticated_user"
                    
                    # Mock flask module and request with user_id (this would normally come from request context)
                    mock_flask_module = Mock()
                    mock_request = Mock()
                    mock_request.user_id = "authenticated_user"
                    mock_flask_module.request = mock_request
                    
                    with patch.dict('sys.modules', {'flask': mock_flask_module}):
                        
                        # Setup context facade
                        mock_factory = Mock()
                        mock_context_facade = Mock()
                        mock_context_facade.create_context.return_value = {"success": True}
                        mock_factory.create_facade.return_value = mock_context_facade
                        mock_factory_class.return_value = mock_factory
                        
                        result = await use_case.execute(
                            project_id="project-123",
                            git_branch_name="feature/auth-test",
                            branch_name="feature/auth-test"
                        )
                        
                        assert result["success"] is True
                        mock_validate_user.assert_called_once_with("authenticated_user", "Branch context creation")
    
    @pytest.mark.asyncio
    async def test_execute_context_creation_authentication_required_error(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test branch creation when context authentication fails but branch creation succeeds"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                # Setup authentication - no default user allowed and no user provided
                mock_auth_config.is_default_user_allowed.return_value = False
                
                # Mock request without user_id
                mock_flask_module = Mock()
                mock_request = Mock()
                mock_request.user_id = None
                mock_flask_module.request = mock_request
                
                with patch.dict('sys.modules', {'flask': mock_flask_module}):
                    
                    result = await use_case.execute(
                        project_id="project-123",
                        git_branch_name="feature/no-auth",
                        branch_name="feature/no-auth"
                    )
                    
                    # Branch creation should succeed even if context creation fails
                    assert result["success"] is True
                    assert result["git_branch"]["id"] == "branch-123"
    
    @pytest.mark.asyncio
    async def test_execute_context_creation_failure_does_not_fail_branch_creation(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test that context creation failure doesn't fail branch creation"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                # Setup authentication
                mock_auth_config.is_default_user_allowed.return_value = True
                mock_auth_config.get_fallback_user_id.return_value = "default_user"
                
                # Setup context facade to fail
                mock_factory = Mock()
                mock_context_facade = Mock()
                mock_context_facade.create_context.return_value = {"success": False, "error": "Context creation failed"}
                mock_factory.create_facade.return_value = mock_context_facade
                mock_factory_class.return_value = mock_factory
                
                result = await use_case.execute(
                    project_id="project-123",
                    git_branch_name="feature/context-fail",
                    branch_name="feature/context-fail"
                )
                
                # Branch creation should succeed despite context creation failure
                assert result["success"] is True
                assert result["git_branch"]["id"] == "branch-123"
    
    @pytest.mark.asyncio
    async def test_execute_context_creation_exception_does_not_fail_branch_creation(self, use_case, mock_project_repository, mock_project_entity, mock_git_branch_entity):
        """Test that context creation exception doesn't fail branch creation"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_entity.create_git_branch.return_value = mock_git_branch_entity
        
        # Mock context creation dependencies to raise exception
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory_class.side_effect = Exception("Context factory error")
            
            result = await use_case.execute(
                project_id="project-123",
                git_branch_name="feature/context-exception",
                branch_name="feature/context-exception"
            )
            
            # Branch creation should succeed despite context creation exception
            assert result["success"] is True
            assert result["git_branch"]["id"] == "branch-123"


class TestCreateGitBranchUseCaseErrorHandling:
    """Test suite for error handling scenarios"""
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def use_case(self, mock_project_repository):
        """Create use case instance with mocked dependencies"""
        return CreateGitBranchUseCase(mock_project_repository)
    
    @pytest.fixture
    def mock_project_entity(self):
        """Create a mock project entity"""
        project = Mock(spec=Project)
        project.id = "project-123"
        project.create_git_branch = Mock()
        return project
    
    @pytest.mark.asyncio
    async def test_execute_repository_find_error(self, use_case, mock_project_repository):
        """Test git branch creation when repository find raises exception"""
        mock_project_repository.find_by_id.side_effect = Exception("Database connection failed")
        
        # Exception should propagate since it's not specifically handled
        with pytest.raises(Exception, match="Database connection failed"):
            await use_case.execute(
                project_id="project-123",
                git_branch_name="feature/db-error",
                branch_name="feature/db-error"
            )
    
    @pytest.mark.asyncio
    async def test_execute_repository_update_error(self, use_case, mock_project_repository, mock_project_entity):
        """Test git branch creation when repository update raises exception"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        mock_project_repository.update.side_effect = Exception("Update failed")
        
        # Setup project domain logic
        mock_git_branch = Mock()
        mock_git_branch.id = "branch-123"
        mock_project_entity.create_git_branch.return_value = mock_git_branch
        
        # Exception should propagate since it's not specifically handled
        with pytest.raises(Exception, match="Update failed"):
            await use_case.execute(
                project_id="project-123",
                git_branch_name="feature/update-error",
                branch_name="feature/update-error"
            )
    
    @pytest.mark.asyncio
    async def test_execute_invalid_branch_parameters(self, use_case, mock_project_repository, mock_project_entity):
        """Test git branch creation with invalid parameters"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup project domain logic to raise ValueError for invalid parameters
        mock_project_entity.create_git_branch.side_effect = ValueError("Invalid branch name format")
        
        result = await use_case.execute(
            project_id="project-123",
            git_branch_name="invalid branch name!",
            branch_name="invalid branch name!"
        )
        
        assert result["success"] is False
        assert "Invalid branch name format" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_branch_name(self, use_case, mock_project_repository, mock_project_entity):
        """Test git branch creation with duplicate branch name"""
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project_entity
        
        # Setup project domain logic to raise ValueError for duplicate name
        mock_project_entity.create_git_branch.side_effect = ValueError("Branch name 'main' already exists")
        
        result = await use_case.execute(
            project_id="project-123",
            git_branch_name="main",
            branch_name="main"
        )
        
        assert result["success"] is False
        assert "Branch name 'main' already exists" in result["error"]


class TestCreateGitBranchUseCaseIntegration:
    """Test suite for integration scenarios"""
    
    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def use_case(self, mock_project_repository):
        """Create use case instance with mocked dependencies"""
        return CreateGitBranchUseCase(mock_project_repository)
    
    @pytest.mark.asyncio
    async def test_execute_complete_workflow(self, use_case, mock_project_repository):
        """Test complete workflow from project lookup to branch creation and context setup"""
        # Setup project entity
        mock_project = Mock()
        mock_project.id = "project-123"
        mock_project.name = "Integration Test Project"
        
        # Setup git branch entity
        mock_git_branch = Mock()
        mock_git_branch.id = "branch-456"
        mock_git_branch.name = "feature/integration-test"
        mock_git_branch.description = "Integration test branch"
        mock_git_branch.project_id = "project-123"
        mock_git_branch.created_at = datetime.now(timezone.utc)
        mock_git_branch.get_task_count.return_value = 0
        mock_git_branch.get_completed_task_count.return_value = 0
        mock_git_branch.get_progress_percentage.return_value = 0.0
        
        # Setup project repository
        mock_project_repository.find_by_id.return_value = mock_project
        mock_project.create_git_branch.return_value = mock_git_branch
        
        # Mock context creation workflow
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            with patch('fastmcp.config.auth_config.AuthConfig') as mock_auth_config:
                # Setup authentication
                mock_auth_config.is_default_user_allowed.return_value = True
                mock_auth_config.get_fallback_user_id.return_value = "integration_user"
                
                # Setup context facade
                mock_factory = Mock()
                mock_context_facade = Mock()
                mock_context_facade.create_context.return_value = {"success": True, "context_id": "branch-456"}
                mock_factory.create_facade.return_value = mock_context_facade
                mock_factory_class.return_value = mock_factory
                
                result = await use_case.execute(
                    project_id="project-123",
                    git_branch_name="feature/integration-test",
                    branch_name="feature/integration-test",
                    branch_description="Integration test branch"
                )
                
                # Verify complete workflow
                assert result["success"] is True
                
                # Verify project lookup
                mock_project_repository.find_by_id.assert_called_once_with("project-123")
                
                # Verify domain logic
                mock_project.create_git_branch.assert_called_once_with(
                    git_branch_name="feature/integration-test",
                    name="feature/integration-test",
                    description="Integration test branch"
                )
                
                # Verify repository update
                mock_project_repository.update.assert_called_once_with(mock_project)
                
                # Verify context creation
                mock_context_facade.create_context.assert_called_once()
                
                # Verify response structure
                assert result["git_branch"]["id"] == "branch-456"
                assert result["git_branch"]["name"] == "feature/integration-test"
                assert result["git_branch"]["project_id"] == "project-123"
                assert result["git_branch"]["task_count"] == 0
                assert result["git_branch"]["completed_tasks"] == 0
                assert result["git_branch"]["progress"] == 0.0