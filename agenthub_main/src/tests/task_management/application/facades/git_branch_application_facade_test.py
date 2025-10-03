"""
Tests for Git Branch Application Facade

This test suite covers the Git Branch Application Facade functionality including:
- Git branch creation with validation
- Git branch retrieval and listing
- Agent assignment/unassignment
- Statistics calculation with denormalized fields
- Archive/restore operations
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
import uuid
import asyncio
from datetime import datetime, timezone

from fastmcp.task_management.application.facades.git_branch_application_facade import (
    GitBranchApplicationFacade
)
from fastmcp.task_management.application.services.git_branch_service import GitBranchService
from fastmcp.task_management.domain.entities import GitBranch, Project
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    ProjectNotFoundError
)
from fastmcp.task_management.application.exceptions import (
    ValidationError
)


class TestGitBranchApplicationFacade:
    """Test Git Branch Application Facade functionality"""

    @pytest.fixture
    def mock_git_branch_service(self):
        """Create mock git branch service"""
        service = Mock(spec=GitBranchService)
        service.create_git_branch = AsyncMock()
        service.get_git_branch = AsyncMock()
        service.list_git_branches = AsyncMock()
        service.update_git_branch = AsyncMock()
        service.delete_git_branch = AsyncMock()
        service.assign_agent_to_branch = AsyncMock()
        service.unassign_agent_from_branch = AsyncMock()
        service.get_branch_statistics = AsyncMock()
        service.archive_branch = AsyncMock()
        service.restore_branch = AsyncMock()
        return service

    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        repo = Mock(spec=ProjectRepository)
        repo.find_by_id = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def sample_project(self):
        """Create sample project"""
        project = Mock(spec=Project)
        project.id = "proj-123"
        project.name = "Test Project"
        project.description = "Test project description"
        project.to_dict = Mock(return_value={
            "id": "proj-123",
            "name": "Test Project",
            "description": "Test project description"
        })
        return project

    @pytest.fixture
    def sample_git_branch(self):
        """Create sample git branch"""
        branch = Mock(spec=GitBranch)
        branch.id = "branch-123"
        branch.project_id = "proj-123"
        branch.git_branch_name = "feature/user-auth"
        branch.git_branch_description = "Implement user authentication"
        branch.is_archived = False
        branch.created_at = datetime.now(timezone.utc)
        branch.updated_at = datetime.now(timezone.utc)
        # Add denormalized count fields used in statistics
        branch.task_count = 5
        branch.completed_task_count = 2
        branch.to_dict = Mock(return_value={
            "id": "branch-123",
            "project_id": "proj-123",
            "git_branch_name": "feature/user-auth",
            "git_branch_description": "Implement user authentication",
            "is_archived": False,
            "task_count": 5,
            "completed_task_count": 2
        })
        return branch

    @pytest.fixture
    def facade(self, mock_git_branch_service, mock_project_repo):
        """Create facade instance with mocks"""
        return GitBranchApplicationFacade(
            git_branch_service=mock_git_branch_service,
            project_repo=mock_project_repo,
            user_id="user-123"
        )

    @pytest.mark.asyncio
    async def test_create_tree(self, facade, mock_git_branch_service, sample_git_branch):
        """Test creating a task tree (git branch) with validation"""
        # Configure mocks
        mock_git_branch_service.create_git_branch.return_value = {
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }
        
        # Mock the validator
        with patch('fastmcp.task_management.domain.services.git_branch_name_validator.GitBranchNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_branch_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            # Execute
            result = await facade.create_tree(
                project_id="proj-123",
                tree_name="feature/user-auth",
                description="Implement user authentication"
            )
        
        # Verify
        assert result["success"] is True
        assert result["git_branch"]["git_branch_name"] == "feature/user-auth"
        mock_validator.validate_branch_name.assert_called_once_with("feature/user-auth", "proj-123")
        mock_git_branch_service.create_git_branch.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tree_validation_error(self, facade, mock_git_branch_service):
        """Test creating task tree with validation error"""
        # Mock the validator to raise error
        with patch('fastmcp.task_management.domain.services.git_branch_name_validator.GitBranchNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_branch_name = AsyncMock(side_effect=ValidationError("Invalid branch name format"))
            mock_validator_class.return_value = mock_validator
            
            # Execute
            result = await facade.create_tree(
                project_id="proj-123",
                tree_name="invalid branch name",  # Contains spaces
                description="Test"
            )
        
        # Verify
        assert result["success"] is False
        assert "Invalid branch name format" in result["error"]
        mock_git_branch_service.create_git_branch.assert_not_called()

    def test_create_git_branch_sync(self, facade, mock_git_branch_service, sample_git_branch):
        """Test synchronous git branch creation for MCP controller"""
        # Configure mocks
        mock_git_branch_service.create_git_branch.return_value = {
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }
        
        # Execute
        result = facade.create_git_branch(
            project_id="proj-123",
            git_branch_name="feature/user-auth",
            git_branch_description="Implement user authentication"
        )
        
        # Verify
        assert result["success"] is True
        assert result["git_branch"]["git_branch_name"] == "feature/user-auth"

    def test_get_git_branch_by_id(self, facade, sample_git_branch):
        """Test getting git branch by ID"""
        # Configure mocks to return proper response format
        expected_response = {
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }
        
        with patch.object(facade, '_find_git_branch_by_id', return_value=expected_response):
            # Execute
            result = facade.get_git_branch_by_id("branch-123")
        
        # Verify
        assert result["success"] is True
        assert result["git_branch"]["id"] == "branch-123"

    def test_get_git_branch_by_id_not_found(self, facade):
        """Test getting non-existent git branch"""
        # Configure mocks to return error response
        error_response = {
            "success": False,
            "error": "Git branch with ID branch-999 not found",
            "error_code": "NOT_FOUND"
        }
        
        with patch.object(facade, '_find_git_branch_by_id', return_value=error_response):
            # Execute
            result = facade.get_git_branch_by_id("branch-999")
        
        # Verify
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_list_git_branches_for_project(self, facade, sample_git_branch):
        """Test listing git branches for a project"""
        # Configure mocks - need to mock the repository service
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            mock_repo = Mock()
            mock_repo.find_all_by_project = AsyncMock(return_value=[sample_git_branch])
            mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
            
            # Execute
            result = facade.list_git_branches_for_project("proj-123")
        
        # Verify
        assert result["success"] is True
        assert len(result["git_branches"]) == 1
        assert result["git_branches"][0]["git_branch_name"] == "feature/user-auth"

    def test_update_git_branch(self, facade, sample_git_branch):
        """Test updating git branch"""
        # Configure mocks
        updated_branch = Mock(spec=GitBranch)
        updated_branch.id = "branch-123"
        updated_branch.git_branch_name = "feature/updated-auth"
        updated_branch.git_branch_description = "Updated description"
        updated_branch.to_dict = Mock(return_value={
            "id": "branch-123",
            "git_branch_name": "feature/updated-auth",
            "git_branch_description": "Updated description"
        })
        
        with patch.object(facade, '_find_git_branch_by_id', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.save = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.update_git_branch(
                    git_branch_id="branch-123",
                    git_branch_name="feature/updated-auth",
                    git_branch_description="Updated description"
                )
        
        # Verify
        assert result["success"] is True
        sample_git_branch.update_name.assert_called_once_with("feature/updated-auth")
        sample_git_branch.update_description.assert_called_once_with("Updated description")

    def test_delete_git_branch(self, facade, sample_git_branch):
        """Test deleting git branch"""
        # Configure mocks
        with patch.object(facade, '_find_git_branch_by_id', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.delete = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.delete_git_branch(git_branch_id="branch-123")
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Git branch deleted successfully"

    def test_assign_agent(self, facade, sample_git_branch):
        """Test assigning agent to git branch"""
        # Configure mocks
        sample_git_branch.assign_agent = Mock()
        
        with patch.object(facade, '_find_git_branch', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.save = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.assign_agent(
                    project_id="proj-123",
                    agent_id="agent-123",
                    git_branch_name="feature/user-auth"
                )
        
        # Verify
        assert result["success"] is True
        sample_git_branch.assign_agent.assert_called_once_with("agent-123")

    def test_unassign_agent(self, facade, sample_git_branch):
        """Test unassigning agent from git branch"""
        # Configure mocks
        sample_git_branch.unassign_agent = Mock()
        
        with patch.object(facade, '_find_git_branch', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.save = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.unassign_agent(
                    project_id="proj-123",
                    agent_id="agent-123",
                    git_branch_name="feature/user-auth"
                )
        
        # Verify
        assert result["success"] is True
        sample_git_branch.unassign_agent.assert_called_once_with("agent-123")

    def test_get_statistics(self, facade, sample_git_branch):
        """Test getting git branch statistics with denormalized fields"""
        # Configure mocks
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            # Mock repositories
            mock_git_branch_repo = Mock()
            mock_task_repo = Mock()
            
            # Mock the branch entity with denormalized fields
            mock_git_branch_repo.find_by_id = AsyncMock(return_value=sample_git_branch)
            
            # Mock tasks for the branch (should match denormalized counts)
            mock_tasks = [
                Mock(status="done", progress_percentage=100) for _ in range(2)  # 2 completed
            ] + [
                Mock(status="in_progress", progress_percentage=50) for _ in range(3)  # 3 in progress
            ]
            mock_task_repo.find_all_by_git_branch = AsyncMock(return_value=mock_tasks)
            
            # Configure provider
            provider_instance = mock_provider.get_instance.return_value
            provider_instance.get_git_branch_repository.return_value = mock_git_branch_repo
            provider_instance.get_task_repository.return_value = mock_task_repo
            
            # Execute
            result = facade.get_statistics(git_branch_id="branch-123")
        
        # Verify statistics use denormalized fields
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["total_tasks"] == 5  # From branch.task_count
        assert stats["completed_tasks"] == 2  # From branch.completed_task_count
        assert stats["in_progress_tasks"] == 3  # Calculated
        assert stats["completion_percentage"] == 40  # (2/5) * 100

    def test_get_statistics_no_tasks(self, facade, sample_git_branch):
        """Test statistics when no tasks exist"""
        # Configure branch with zero counts
        sample_git_branch.task_count = 0
        sample_git_branch.completed_task_count = 0
        
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            mock_git_branch_repo = Mock()
            mock_task_repo = Mock()
            
            mock_git_branch_repo.find_by_id = AsyncMock(return_value=sample_git_branch)
            mock_task_repo.find_all_by_git_branch = AsyncMock(return_value=[])
            
            provider_instance = mock_provider.get_instance.return_value
            provider_instance.get_git_branch_repository.return_value = mock_git_branch_repo
            provider_instance.get_task_repository.return_value = mock_task_repo
            
            # Execute
            result = facade.get_statistics(git_branch_id="branch-123")
        
        # Verify zero statistics
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["total_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["completion_percentage"] == 0

    def test_archive_git_branch(self, facade, sample_git_branch):
        """Test archiving git branch"""
        # Configure mocks
        sample_git_branch.archive = Mock()
        
        with patch.object(facade, '_find_git_branch_by_id', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.save = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.archive_git_branch(git_branch_id="branch-123")
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Git branch archived successfully"
        sample_git_branch.archive.assert_called_once()

    def test_restore_git_branch(self, facade, sample_git_branch):
        """Test restoring archived git branch"""
        # Configure mocks
        sample_git_branch.is_archived = True
        sample_git_branch.restore = Mock()
        
        with patch.object(facade, '_find_git_branch_by_id', return_value=sample_git_branch):
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_repo = Mock()
                mock_repo.save = AsyncMock()
                mock_provider.get_instance.return_value.get_git_branch_repository.return_value = mock_repo
                
                # Execute
                result = facade.restore_git_branch(git_branch_id="branch-123")
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Git branch restored successfully"
        sample_git_branch.restore.assert_called_once()

    def test_error_handling_git_branch_not_found(self, facade):
        """Test error handling for non-existent git branch"""
        # Configure mocks
        with patch.object(facade, '_find_git_branch_by_id', return_value=None):
            # Test update
            result = facade.update_git_branch(
                git_branch_id="branch-999",
                git_branch_name="new-name"
            )
            assert result["success"] is False
            assert "not found" in result["error"]
            
            # Test delete
            result = facade.delete_git_branch(git_branch_id="branch-999")
            assert result["success"] is False
            assert "not found" in result["error"]

    def test_error_handling_duplicate_branch_name(self, facade):
        """Test error handling for duplicate branch name"""
        # Configure mocks
        with patch('fastmcp.task_management.domain.services.git_branch_name_validator.GitBranchNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_branch_name = AsyncMock(
                side_effect=ValidationError("Branch name already exists")
            )
            mock_validator_class.return_value = mock_validator
            
            # Execute
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    facade.create_tree(
                        project_id="proj-123",
                        tree_name="existing-branch",
                        description="Test"
                    )
                )
            finally:
                loop.close()
        
        # Verify
        assert result["success"] is False
        assert "Branch name already exists" in result["error"]

    def test_no_user_id_error(self):
        """Test operations without user_id fail appropriately"""
        facade = GitBranchApplicationFacade(user_id=None)
        
        # Test create tree
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                facade.create_tree(
                    project_id="proj-123",
                    tree_name="test",
                    description="Test"
                )
            )
        finally:
            loop.close()
            
        assert result["success"] is False
        assert "User authentication required" in result["error"]

    def test_get_statistics_branch_not_found(self, facade):
        """Test statistics when branch doesn't exist"""
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            mock_git_branch_repo = Mock()
            mock_git_branch_repo.find_by_id = AsyncMock(return_value=None)
            
            provider_instance = mock_provider.get_instance.return_value
            provider_instance.get_git_branch_repository.return_value = mock_git_branch_repo
            
            # Execute
            result = facade.get_statistics(git_branch_id="branch-999")
        
        # Verify
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_async_helper_get_branch_entity(self, facade, sample_git_branch):
        """Test the async helper method _get_branch_entity"""
        # Configure mocks
        mock_repo = Mock()
        mock_repo.find_by_id = AsyncMock(return_value=sample_git_branch)
        
        # Execute
        result = await facade._get_branch_entity("branch-123", mock_repo)
        
        # Verify
        assert result == sample_git_branch
        mock_repo.find_by_id.assert_called_once_with("branch-123")