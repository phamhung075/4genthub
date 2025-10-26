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
        # Configure mocks - mock list_trees async method
        async def mock_list_trees(project_id):
            return {
                "success": True,
                "git_branchs": [{
                    "id": "branch-123",
                    "name": "feature/user-auth",  # list_git_branchs expects 'name' field
                    "description": "Implement user authentication",
                    "created_at": datetime.now(timezone.utc),
                    "task_count": 5,
                    "completed_tasks": 2,
                    "progress": 40.0
                }]
            }

        with patch.object(facade, 'list_trees', side_effect=mock_list_trees):
            # Execute - using correct method name
            result = facade.list_git_branchs("proj-123")

        # Verify
        assert result["success"] is True
        assert len(result["git_branchs"]) == 1
        # list_git_branchs transforms the response
        assert result["git_branchs"][0]["name"] == "feature/user-auth"

    def test_update_git_branch(self, facade, sample_git_branch):
        """Test updating git branch"""
        # Mock get_git_branch_by_id to return successful response
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Execute - update method now just returns success with WebSocket notification
            result = facade.update_git_branch(
                git_branch_id="branch-123",
                git_branch_name="feature/updated-auth",
                git_branch_description="Updated description"
            )

        # Verify - update now returns success immediately
        assert result["success"] is True
        assert result["git_branch_id"] == "branch-123"

    def test_delete_git_branch(self, facade, sample_git_branch, mock_git_branch_service):
        """Test deleting git branch"""
        # Mock get_git_branch_by_id to return successful response
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Mock the service delete method
            mock_git_branch_service.delete_git_branch.return_value = {
                "success": True,
                "message": "Git branch deleted successfully"
            }

            # Execute
            result = facade.delete_git_branch(git_branch_id="branch-123")

        # Verify
        assert result["success"] is True
        assert "deleted successfully" in result.get("message", "")

    def test_assign_agent(self, facade, sample_git_branch):
        """Test assigning agent to git branch"""
        # Mock FacadeService and AgentFacade - patch at the correct import location
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService') as mock_facade_service:
            mock_agent_facade = Mock()
            mock_agent_facade.assign_agent.return_value = {
                "success": True,
                "message": "Agent assigned successfully"
            }
            mock_facade_service.get_instance.return_value.get_agent_facade.return_value = mock_agent_facade

            # Execute - new signature uses git_branch_id instead of git_branch_name
            result = facade.assign_agent(
                git_branch_id="branch-123",
                agent_id="agent-123",
                project_id="proj-123"
            )

        # Verify
        assert result["success"] is True
        mock_agent_facade.assign_agent.assert_called_once()

    def test_unassign_agent(self, facade, sample_git_branch):
        """Test unassigning agent from git branch"""
        # Mock FacadeService and AgentFacade - patch at the correct import location
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService') as mock_facade_service:
            mock_agent_facade = Mock()
            mock_agent_facade.unassign_agent.return_value = {
                "success": True,
                "message": "Agent unassigned successfully"
            }
            mock_facade_service.get_instance.return_value.get_agent_facade.return_value = mock_agent_facade

            # Execute - new signature uses git_branch_id instead of git_branch_name
            result = facade.unassign_agent(
                git_branch_id="branch-123",
                agent_id="agent-123",
                project_id="proj-123"
            )

        # Verify
        assert result["success"] is True
        mock_agent_facade.unassign_agent.assert_called_once()

    def test_get_statistics(self, facade, sample_git_branch):
        """Test getting git branch statistics with denormalized fields"""
        # Mock get_tasks_by_git_branch_id which returns task dicts
        mock_tasks = [
            {"status": "done", "progress_percentage": 100},  # completed
            {"status": "done", "progress_percentage": 100},  # completed
            {"status": "in_progress", "progress_percentage": 50},
            {"status": "in_progress", "progress_percentage": 50},
            {"status": "in_progress", "progress_percentage": 50}
        ]

        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            # Mock repositories
            mock_task_repo = Mock()
            mock_task_repo.get_tasks_by_git_branch_id.return_value = mock_tasks

            # Mock RepositoryProviderService
            provider_instance = mock_provider.return_value
            provider_instance.get_task_repository.return_value = mock_task_repo

            # Mock the async _get_branch_entity call
            with patch.object(facade, '_get_branch_entity', new_callable=AsyncMock, return_value=sample_git_branch):
                # Execute - new signature requires project_id
                result = facade.get_statistics(
                    project_id="proj-123",
                    git_branch_id="branch-123"
                )

        # Verify statistics use denormalized fields
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["task_count"] == 5  # From branch.task_count
        assert stats["completed_tasks"] == 2  # From branch.completed_task_count
        assert stats["in_progress_tasks"] == 3  # Calculated

    def test_get_statistics_no_tasks(self, facade, sample_git_branch):
        """Test statistics when no tasks exist"""
        # Configure branch with zero counts
        sample_git_branch.task_count = 0
        sample_git_branch.completed_task_count = 0

        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            # Mock repositories
            mock_task_repo = Mock()
            mock_task_repo.get_tasks_by_git_branch_id.return_value = []

            # Mock RepositoryProviderService
            provider_instance = mock_provider.return_value
            provider_instance.get_task_repository.return_value = mock_task_repo

            # Mock the async _get_branch_entity call
            with patch.object(facade, '_get_branch_entity', new_callable=AsyncMock, return_value=sample_git_branch):
                # Execute - new signature requires project_id
                result = facade.get_statistics(
                    project_id="proj-123",
                    git_branch_id="branch-123"
                )

        # Verify zero statistics
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["task_count"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["progress_percentage"] == 0

    def test_error_handling_git_branch_not_found(self, facade):
        """Test error handling for non-existent git branch"""
        # Mock get_git_branch_by_id to return not found
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": False,
            "error": "Git branch not found: branch-999"
        }):
            # Test delete - delete checks if branch exists first
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
        # Need to provide repos with mock service to avoid ValueError
        mock_service = Mock()
        facade = GitBranchApplicationFacade(user_id=None, git_branch_service=mock_service)

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

        # Test assign_agent also requires user_id
        result = facade.assign_agent(
            git_branch_id="branch-123",
            agent_id="agent-123"
        )
        assert result["success"] is False
        assert "authentication" in result["error"].lower()

    def test_get_statistics_branch_not_found(self, facade):
        """Test statistics when branch doesn't exist"""
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
            # Mock task repository
            mock_task_repo = Mock()
            mock_task_repo.get_tasks_by_git_branch_id.return_value = []

            provider_instance = mock_provider.return_value
            provider_instance.get_task_repository.return_value = mock_task_repo

            # Mock _get_branch_entity to return None (branch not found)
            with patch.object(facade, '_get_branch_entity', new_callable=AsyncMock, return_value=None):
                # Execute - new signature requires project_id
                result = facade.get_statistics(
                    project_id="proj-123",
                    git_branch_id="branch-999"
                )

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

    def test_create_git_branch_with_running_event_loop(self, facade, sample_git_branch):
        """Test create_git_branch when already in a running event loop"""
        # Mock validation
        with patch('fastmcp.task_management.domain.services.git_branch_name_validator.GitBranchNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_branch_name = AsyncMock()
            mock_validator_class.return_value = mock_validator

            # Mock WebSocket notification
            with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
                mock_ws.sync_broadcast_branch_event = Mock()

                # Create a running event loop to trigger the threading path
                async def run_test():
                    facade._git_branch_service.create_git_branch = AsyncMock(return_value={
                        "success": True,
                        "git_branch": sample_git_branch.to_dict()
                    })

                    # This should use the threading path since we're in an event loop
                    result = facade.create_git_branch(
                        project_id="proj-123",
                        git_branch_name="feature/test",
                        git_branch_description="Test"
                    )
                    return result

                # Run in an event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(run_test())
                finally:
                    loop.close()

        # Verify
        assert result["success"] is True

    def test_create_git_branch_error_handling(self, facade):
        """Test create_git_branch error handling"""
        # Mock to raise exception
        with patch.object(facade, 'create_tree', side_effect=Exception("Test error")):
            # Execute
            result = facade.create_git_branch(
                project_id="proj-123",
                git_branch_name="feature/test",
                git_branch_description="Test"
            )

        # Verify error response
        assert result["success"] is False
        assert "Failed to create git branch" in result["error"]
        assert result["error_code"] == "CREATION_FAILED"

    def test_get_git_branch_with_project_validation(self, facade, sample_git_branch):
        """Test get_git_branch with project ID validation"""
        # Mock get_git_branch_by_id
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Execute
            result = facade.get_git_branch(
                project_id="proj-123",
                git_branch_id="branch-123"
            )

        # Verify
        assert result["success"] is True
        assert result["git_branch"]["project_id"] == "proj-123"

    def test_get_git_branch_project_mismatch_warning(self, facade, sample_git_branch):
        """Test get_git_branch logs warning on project ID mismatch"""
        # Mock branch with different project
        wrong_project_branch = sample_git_branch.to_dict()
        wrong_project_branch["project_id"] = "proj-999"

        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": wrong_project_branch
        }):
            # Execute - should log warning but still return data
            result = facade.get_git_branch(
                project_id="proj-123",
                git_branch_id="branch-123"
            )

        # Verify - still successful but project doesn't match
        assert result["success"] is True
        assert result["git_branch"]["project_id"] == "proj-999"

    def test_get_git_branch_error(self, facade):
        """Test get_git_branch error handling"""
        with patch.object(facade, 'get_git_branch_by_id', side_effect=Exception("Test error")):
            # Execute
            result = facade.get_git_branch(
                project_id="proj-123",
                git_branch_id="branch-123"
            )

        # Verify
        assert result["success"] is False
        assert "Failed to get git branch" in result["error"]
        assert result["error_code"] == "GET_FAILED"

    def test_delete_git_branch_project_mismatch(self, facade, sample_git_branch):
        """Test delete_git_branch with project ID mismatch"""
        # Mock branch belonging to different project
        wrong_project_branch = sample_git_branch.to_dict()
        wrong_project_branch["project_id"] = "proj-999"

        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": wrong_project_branch
        }):
            # Execute with different project_id
            result = facade.delete_git_branch(
                git_branch_id="branch-123",
                project_id="proj-123"  # Doesn't match
            )

        # Verify
        assert result["success"] is False
        assert "PROJECT_MISMATCH" in result["error_code"]

    def test_delete_git_branch_with_running_event_loop(self, facade, sample_git_branch, mock_git_branch_service):
        """Test delete_git_branch when already in a running event loop"""
        # Mock get_git_branch_by_id
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Mock service delete
            mock_git_branch_service.delete_git_branch.return_value = {
                "success": True,
                "message": "Deleted successfully"
            }

            # Run in event loop to trigger threading path
            async def run_test():
                return facade.delete_git_branch(git_branch_id="branch-123")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(run_test())
            finally:
                loop.close()

        # Verify
        assert result["success"] is True

    def test_list_git_branchs_with_running_event_loop(self, facade):
        """Test list_git_branchs when already in a running event loop"""
        # Mock list_trees
        async def mock_list_trees(project_id):
            return {
                "success": True,
                "git_branchs": [{
                    "id": "branch-123",
                    "name": "feature/test",
                    "description": "Test branch",
                    "created_at": datetime.now(timezone.utc),
                    "task_count": 3,
                    "completed_tasks": 1,
                    "progress": 33.3
                }]
            }

        with patch.object(facade, 'list_trees', side_effect=mock_list_trees):
            # Run in event loop
            async def run_test():
                return facade.list_git_branchs("proj-123")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(run_test())
            finally:
                loop.close()

        # Verify
        assert result["success"] is True
        assert result["total_count"] == 1

    def test_list_git_branchs_error(self, facade):
        """Test list_git_branchs error handling"""
        with patch.object(facade, 'list_trees', side_effect=Exception("Test error")):
            # Execute
            result = facade.list_git_branchs("proj-123")

        # Verify
        assert result["success"] is False
        assert "Failed to list git branches" in result["error"]
        assert result["error_code"] == "LIST_FAILED"

    def test_get_branches_with_task_counts(self, facade, sample_git_branch):
        """Test get_branches_with_task_counts method"""
        # Mock list_git_branchs
        with patch.object(facade, 'list_git_branchs', return_value={
            "success": True,
            "git_branchs": [sample_git_branch.to_dict()]
        }):
            # Mock task repository
            with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.TaskRepositoryFactory') as mock_factory:
                mock_task_repo = Mock()
                mock_task_repo.get_tasks_by_git_branch_id.return_value = [
                    {"status": "done", "progress_percentage": 100},
                    {"status": "in_progress", "progress_percentage": 50}
                ]
                mock_factory.return_value.create_repository.return_value = mock_task_repo

                # Execute
                result = facade.get_branches_with_task_counts("proj-123")

        # Verify
        assert result["success"] is True
        assert len(result["branches"]) == 1
        assert result["branches"][0]["task_count"] == 5  # From sample_git_branch

    def test_get_branches_with_task_counts_error(self, facade):
        """Test get_branches_with_task_counts error handling"""
        with patch.object(facade, 'list_git_branchs', return_value={
            "success": False,
            "error": "List failed"
        }):
            # Execute
            result = facade.get_branches_with_task_counts("proj-123")

        # Verify
        assert result["success"] is False

    def test_get_project_branch_summary(self, facade):
        """Test get_project_branch_summary method"""
        # Mock get_branches_with_task_counts
        with patch.object(facade, 'get_branches_with_task_counts', return_value={
            "success": True,
            "branches": [
                {
                    "id": "branch-1",
                    "name": "feature/test",
                    "task_count": 10,
                    "completed_tasks": 5,
                    "in_progress_tasks": 3,
                    "todo_tasks": 2,
                    "blocked_tasks": 0
                },
                {
                    "id": "branch-2",
                    "name": "feature/other",
                    "task_count": 5,
                    "completed_tasks": 2,
                    "in_progress_tasks": 2,
                    "todo_tasks": 1,
                    "blocked_tasks": 0
                }
            ]
        }):
            # Execute
            result = facade.get_project_branch_summary("proj-123")

        # Verify
        assert result["success"] is True
        summary = result["summary"]
        assert summary["total_branches"] == 2
        assert summary["task_count"] == 15
        assert summary["completed_tasks"] == 7
        assert summary["most_active_branch"]["id"] == "branch-1"

    def test_get_project_branch_summary_error(self, facade):
        """Test get_project_branch_summary error handling"""
        with patch.object(facade, 'get_branches_with_task_counts', return_value={
            "success": False,
            "error": "Failed"
        }):
            # Execute
            result = facade.get_project_branch_summary("proj-123")

        # Verify
        assert result["success"] is False
        assert "error" in result

    def test_get_branch_summary(self, facade, sample_git_branch):
        """Test get_branch_summary method"""
        # Mock get_git_branch_by_id
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Mock task repository
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider:
                mock_task_repo = Mock()
                mock_task_repo.get_tasks_by_git_branch_id.return_value = [
                    {"status": "done", "progress_percentage": 100},
                    {"status": "in_progress", "progress_percentage": 50}
                ]
                mock_provider.get_task_repository.return_value = mock_task_repo

                # Execute
                result = facade.get_branch_summary("branch-123")

        # Verify
        assert result["success"] is True
        assert result["branch"]["id"] == "branch-123"
        assert result["branch"]["task_count"] == 5

    def test_get_branch_summary_not_found(self, facade):
        """Test get_branch_summary when branch not found"""
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": False,
            "error": "Branch not found"
        }):
            # Execute
            result = facade.get_branch_summary("branch-999")

        # Verify
        assert result["success"] is False
        assert result["branch"] is None

    @pytest.mark.asyncio
    async def test_get_tree(self, facade, mock_git_branch_service, sample_git_branch):
        """Test get_tree async method"""
        # Configure mock
        mock_git_branch_service.get_git_branch.return_value = {
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }

        # Execute
        result = await facade.get_tree("proj-123", "feature/test")

        # Verify
        assert result["success"] is True
        mock_git_branch_service.get_git_branch.assert_called_once_with("proj-123", "feature/test")

    @pytest.mark.asyncio
    async def test_list_trees(self, facade, mock_git_branch_service):
        """Test list_trees async method"""
        # Configure mock
        mock_git_branch_service.list_git_branchs.return_value = {
            "success": True,
            "git_branchs": []
        }

        # Execute
        result = await facade.list_trees("proj-123")

        # Verify
        assert result["success"] is True
        mock_git_branch_service.list_git_branchs.assert_called_once_with("proj-123")

    def test_create_git_branch_websocket_failure_non_blocking(self, facade, sample_git_branch):
        """Test create_git_branch continues even if WebSocket fails"""
        # Mock validation
        with patch('fastmcp.task_management.domain.services.git_branch_name_validator.GitBranchNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_branch_name = AsyncMock()
            mock_validator_class.return_value = mock_validator

            # Mock repository provider
            with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_repo_provider:
                mock_repo_provider.get_instance.return_value = Mock()

                # Mock service to return success
                facade._git_branch_service.create_git_branch = AsyncMock(return_value={
                    "success": True,
                    "git_branch": sample_git_branch.to_dict()
                })

                # Mock WebSocket to fail
                with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
                    mock_ws.sync_broadcast_branch_event = Mock(side_effect=Exception("WebSocket error"))

                    # Execute - should succeed despite WebSocket failure
                    result = facade.create_git_branch(
                        project_id="proj-123",
                        git_branch_name="feature/test",
                        git_branch_description="Test"
                    )

        # Verify - still successful
        assert result["success"] is True

    def test_update_git_branch_websocket_failure_non_blocking(self, facade, sample_git_branch):
        """Test update continues even if WebSocket fails"""
        # Mock get_git_branch_by_id
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": True,
            "git_branch": sample_git_branch.to_dict()
        }):
            # Mock WebSocket to fail
            with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
                mock_ws.sync_broadcast_branch_event = Mock(side_effect=Exception("WebSocket error"))

                # Execute - should succeed
                result = facade.update_git_branch(
                    git_branch_id="branch-123",
                    git_branch_name="feature/updated"
                )

        # Verify - still successful
        assert result["success"] is True

    def test_update_git_branch_get_branch_fails(self, facade):
        """Test update when get_git_branch_by_id fails"""
        # Mock get_git_branch_by_id to fail
        with patch.object(facade, 'get_git_branch_by_id', return_value={
            "success": False,
            "error": "Branch not found"
        }):
            # Mock WebSocket
            with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
                mock_ws.sync_broadcast_branch_event = Mock()

                # Execute - update still returns success (simplified implementation)
                result = facade.update_git_branch(
                    git_branch_id="branch-999",
                    git_branch_name="feature/test"
                )

                # WebSocket should not be called
                assert not mock_ws.sync_broadcast_branch_event.called

        # Verify
        assert result["success"] is True

    def test_assign_agent_no_user_id(self, facade):
        """Test assign_agent without user_id"""
        # Create facade without user_id
        facade_no_user = GitBranchApplicationFacade(
            git_branch_service=Mock(),
            user_id=None
        )

        # Execute
        result = facade_no_user.assign_agent(
            git_branch_id="branch-123",
            agent_id="agent-123"
        )

        # Verify
        assert result["success"] is False
        assert "AUTHENTICATION_REQUIRED" in result["error_code"]

    def test_unassign_agent_no_user_id(self, facade):
        """Test unassign_agent without user_id"""
        # Create facade without user_id
        facade_no_user = GitBranchApplicationFacade(
            git_branch_service=Mock(),
            user_id=None
        )

        # Execute
        result = facade_no_user.unassign_agent(
            git_branch_id="branch-123",
            agent_id="agent-123"
        )

        # Verify
        assert result["success"] is False
        assert "AUTHENTICATION_REQUIRED" in result["error_code"]

    def test_assign_agent_error_handling(self, facade):
        """Test assign_agent error handling"""
        # Mock FacadeService to raise exception
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService') as mock_facade_service:
            mock_facade_service.get_instance.side_effect = Exception("Service error")

            # Execute
            result = facade.assign_agent(
                git_branch_id="branch-123",
                agent_id="agent-123"
            )

        # Verify
        assert result["success"] is False
        assert "ASSIGNMENT_FAILED" in result["error_code"]

    def test_unassign_agent_error_handling(self, facade):
        """Test unassign_agent error handling"""
        # Mock FacadeService to raise exception
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService') as mock_facade_service:
            mock_facade_service.get_instance.side_effect = Exception("Service error")

            # Execute
            result = facade.unassign_agent(
                git_branch_id="branch-123",
                agent_id="agent-123"
            )

        # Verify
        assert result["success"] is False
        assert "UNASSIGNMENT_FAILED" in result["error_code"]

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_no_user(self, facade):
        """Test _find_git_branch_by_id without user_id"""
        # Create facade without user_id
        facade_no_user = GitBranchApplicationFacade(
            git_branch_service=Mock(),
            user_id=None
        )

        # Execute
        result = await facade_no_user._find_git_branch_by_id("branch-123")

        # Verify
        assert result["success"] is False
        assert "User authentication required" in result["error"]

    def test_get_branches_with_task_counts_exception(self, facade):
        """Test get_branches_with_task_counts with exception"""
        # Mock to raise exception
        with patch.object(facade, 'list_git_branchs', side_effect=Exception("Test error")):
            # Execute
            result = facade.get_branches_with_task_counts("proj-123")

        # Verify
        assert result["success"] is False
        assert "branches" in result
        assert result["branches"] == []

    def test_get_project_branch_summary_no_branches(self, facade):
        """Test get_project_branch_summary with no branches"""
        # Mock to return empty branches
        with patch.object(facade, 'get_branches_with_task_counts', return_value={
            "success": True,
            "branches": []
        }):
            # Execute
            result = facade.get_project_branch_summary("proj-123")

        # Verify
        assert result["success"] is True
        summary = result["summary"]
        assert summary["total_branches"] == 0
        assert summary["task_count"] == 0
        assert summary["most_active_branch"] is None

    def test_get_project_branch_summary_exception(self, facade):
        """Test get_project_branch_summary with exception"""
        # Mock to raise exception
        with patch.object(facade, 'get_branches_with_task_counts', side_effect=Exception("Test error")):
            # Execute
            result = facade.get_project_branch_summary("proj-123")

        # Verify
        assert result["success"] is False
        assert "error" in result

    def test_get_branch_summary_exception(self, facade):
        """Test get_branch_summary with exception"""
        # Mock to raise exception
        with patch.object(facade, 'get_git_branch_by_id', side_effect=Exception("Test error")):
            # Execute
            result = facade.get_branch_summary("branch-123")

        # Verify
        assert result["success"] is False
        assert result["branch"] is None

    def test_get_statistics_exception_handling(self, facade):
        """Test get_statistics with exception"""
        # Mock to raise exception
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService', side_effect=Exception("Test error")):
            # Execute
            result = facade.get_statistics(
                project_id="proj-123",
                git_branch_id="branch-123"
            )

        # Verify
        assert result["success"] is False
        assert "STATISTICS_FAILED" in result["error_code"]

    @pytest.mark.asyncio
    async def test_get_branch_entity_error(self, facade):
        """Test _get_branch_entity with error"""
        # Mock repo to raise exception
        mock_repo = Mock()
        mock_repo.find_by_id = AsyncMock(side_effect=Exception("Test error"))

        # Execute
        result = await facade._get_branch_entity("branch-123", mock_repo)

        # Verify
        assert result is None