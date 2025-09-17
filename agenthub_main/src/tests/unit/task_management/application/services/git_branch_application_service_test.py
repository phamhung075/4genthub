"""Tests for GitBranchService"""

import pytest
from unittest.mock import AsyncMock, Mock, create_autospec
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastmcp.task_management.application.services.git_branch_service import GitBranchService
from fastmcp.task_management.domain.entities.git_branch import GitBranch


class TestGitBranchService:
    """Test suite for GitBranchService"""

    @pytest.fixture
    def mock_git_branch_repo(self):
        """Create a mock git branch repository"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_project_repo(self):
        """Create a mock project repository"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_project(self, mock_git_branch):
        """Create a mock project"""
        project = Mock()
        project.id = "project-123"
        project.name = "Test Project"
        # Add git_branchs dict that the service expects
        project.git_branchs = {"branch-456": mock_git_branch}
        return project

    @pytest.fixture
    def mock_git_branch(self):
        """Create a mock git branch"""
        branch = Mock(spec=GitBranch)
        branch.id = "branch-456"
        branch.name = "feature/test"
        branch.description = "Test branch"
        branch.project_id = "project-123"
        branch.created_at = datetime.now()
        branch.updated_at = datetime.now()
        # Initialize assigned_agents as a regular list (not a mock)
        branch.assigned_agents = []
        branch.assigned_agent_id = None
        branch.archived = False
        
        # Add the to_dict method that GitBranchService.get_git_branch_by_id() calls
        def mock_to_dict():
            return {
                'id': branch.id,
                'name': branch.name,
                'description': branch.description,
                'project_id': branch.project_id,
                'created_at': branch.created_at.isoformat(),
                'updated_at': branch.updated_at.isoformat(),
                'assigned_agent_id': getattr(branch, 'assigned_agent_id', None),
                'assigned_agents': getattr(branch, 'assigned_agents', []).copy(),
                'archived': getattr(branch, 'archived', False),
                'priority': 'medium',
                'status': 'todo',
                'task_count': 0,
                'completed_task_count': 0,
                'progress_percentage': 0.0
            }
        
        branch.to_dict = Mock(side_effect=mock_to_dict)
        return branch

    @pytest.fixture
    def mock_hierarchical_context_service(self):
        """Create a mock hierarchical context service"""
        service = Mock()
        service.create_context = Mock(return_value={"success": True, "context": {}})
        service.delete_context = Mock(return_value={"success": True})
        return service

    @pytest.fixture
    def service(self, mock_project_repo, mock_git_branch_repo, mock_hierarchical_context_service, monkeypatch):
        """Create a GitBranchService instance with mocked repositories"""
        # Mock the RepositoryFactory to return our mock git_branch_repo
        def mock_get_git_branch_repository(user_id=None):
            return mock_git_branch_repo
        
        monkeypatch.setattr(
            "fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_git_branch_repository",
            mock_get_git_branch_repository
        )
        
        service = GitBranchService(
            project_repo=mock_project_repo,
            git_branch_repo=mock_git_branch_repo,
            hierarchical_context_service=mock_hierarchical_context_service,
            user_id=None
        )
        return service

    def test_init(self, mock_project_repo, mock_git_branch_repo, monkeypatch):
        """Test service initialization"""
        # Mock the RepositoryFactory
        def mock_get_git_branch_repository(user_id=None):
            return mock_git_branch_repo
        
        monkeypatch.setattr(
            "fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_git_branch_repository",
            mock_get_git_branch_repository
        )
        
        service = GitBranchService(
            project_repo=mock_project_repo,
            git_branch_repo=mock_git_branch_repo,
            hierarchical_context_service=None,
            user_id=None
        )
        assert service._project_repo == mock_project_repo
        assert service._user_id is None
        assert hasattr(service, '_git_branch_repo')  # Initialized internally

    def test_init_with_user_id(self, mock_project_repo, mock_git_branch_repo, monkeypatch):
        """Test service initialization with user ID"""
        # Mock the RepositoryFactory
        def mock_get_git_branch_repository(user_id=None):
            return mock_git_branch_repo
        
        monkeypatch.setattr(
            "fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_git_branch_repository",
            mock_get_git_branch_repository
        )
        
        service = GitBranchService(
            project_repo=mock_project_repo,
            git_branch_repo=mock_git_branch_repo,
            hierarchical_context_service=None,
            user_id="user-123"
        )
        assert service._user_id == "user-123"

    def test_with_user(self, service, mock_git_branch_repo, monkeypatch):
        """Test creating user-scoped service"""
        # Mock the RepositoryFactory for the new instance
        def mock_get_git_branch_repository(user_id=None):
            return mock_git_branch_repo
        
        monkeypatch.setattr(
            "fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_git_branch_repository",
            mock_get_git_branch_repository
        )
        
        user_scoped_service = service.with_user("user-456")
        assert isinstance(user_scoped_service, GitBranchService)
        assert user_scoped_service._user_id == "user-456"
        assert user_scoped_service._project_repo == service._project_repo

    def test_get_user_scoped_repository_no_user(self, service):
        """Test getting repository when no user is set"""
        mock_repo = Mock()
        repo = service._get_user_scoped_repository(mock_repo)
        assert repo == mock_repo

    def test_get_user_scoped_repository_with_user_method(self, service):
        """Test getting repository with with_user method"""
        service._user_id = "user-789"
        mock_repo = Mock()
        mock_repo.with_user = Mock(return_value=mock_repo)
        
        repo = service._get_user_scoped_repository(mock_repo)
        
        mock_repo.with_user.assert_called_once_with("user-789")
        assert repo == mock_repo

    def test_get_user_scoped_repository_none(self, service):
        """Test getting repository when repository is None"""
        repo = service._get_user_scoped_repository(None)
        assert repo is None

    @pytest.mark.asyncio
    async def test_create_git_branch_success(
        self, service, mock_project_repo, mock_git_branch_repo, mock_project, mock_git_branch
    ):
        """Test successful git branch creation"""
        # Setup mocks
        mock_project_repo.find_by_id.return_value = mock_project
        mock_git_branch_repo.find_by_name.return_value = None  # Branch doesn't exist
        mock_git_branch_repo.create_branch.return_value = mock_git_branch

        result = await service.create_git_branch(
            project_id="project-123",
            branch_name="feature/test",
            description="Test branch"
        )

        assert result["success"] is True
        assert result["git_branch"]["id"] == "branch-456"
        assert result["git_branch"]["name"] == "feature/test"
        assert result["git_branch"]["project_id"] == "project-123"
        assert result["message"] == "Git branch 'feature/test' created successfully"

        mock_project_repo.find_by_id.assert_called_once_with("project-123")
        mock_git_branch_repo.find_by_name.assert_called_once_with("project-123", "feature/test")
        mock_git_branch_repo.create_branch.assert_called_once_with("project-123", "feature/test", "Test branch")

    @pytest.mark.asyncio
    async def test_create_git_branch_project_not_found(self, service, mock_project_repo, mock_git_branch_repo):
        """Test git branch creation when project is not found"""
        mock_project_repo.find_by_id.return_value = None

        result = await service.create_git_branch(
            project_id="project-999",
            branch_name="feature/test"
        )

        assert result["success"] is False
        assert result["error"] == "Project project-999 not found"

    @pytest.mark.asyncio
    async def test_create_git_branch_already_exists(
        self, service, mock_project_repo, mock_git_branch_repo, mock_project, mock_git_branch
    ):
        """Test git branch creation when branch already exists"""
        mock_project_repo.find_by_id.return_value = mock_project
        mock_git_branch_repo.find_by_name.return_value = mock_git_branch

        result = await service.create_git_branch(
            project_id="project-123",
            branch_name="feature/test"
        )

        assert result["success"] is False
        assert result["error"] == "Git branch 'feature/test' already exists in project project-123"

    @pytest.mark.asyncio
    async def test_create_git_branch_exception(self, service, mock_project_repo):
        """Test git branch creation exception handling"""
        mock_project_repo.find_by_id.side_effect = Exception("Database error")

        result = await service.create_git_branch(
            project_id="project-123",
            branch_name="feature/test"
        )

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_success(self, service, mock_git_branch_repo, mock_git_branch):
        """Test successful get git branch by ID"""
        mock_git_branch_repo.find_all.return_value = [mock_git_branch]

        result = await service.get_git_branch_by_id("branch-456")

        assert result["success"] is True
        assert result["project_id"] == "project-123"
        assert result["branch_name"] == "feature/test"
        assert result["git_branch"]["id"] == "branch-456"

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_not_found(self, service, mock_git_branch_repo):
        """Test get git branch by ID when branch is not found"""
        mock_git_branch_repo.find_all.return_value = []

        result = await service.get_git_branch_by_id("branch-999")

        assert result["success"] is False
        assert result["error"] == "Git branch branch-999 not found"

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_exception(self, service, mock_git_branch_repo):
        """Test get git branch by ID exception handling"""
        mock_git_branch_repo.find_all.side_effect = Exception("Database error")

        result = await service.get_git_branch_by_id("branch-456")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_list_git_branchs_success(
        self, service, mock_project_repo, mock_git_branch_repo, mock_project, mock_git_branch
    ):
        """Test successful git branches listing"""
        mock_project_repo.find_by_id.return_value = mock_project
        mock_git_branch_repo.find_all_by_project.return_value = [mock_git_branch]

        result = await service.list_git_branchs("project-123")

        assert result["success"] is True
        assert result["project_id"] == "project-123"
        assert result["count"] == 1
        assert len(result["git_branchs"]) == 1
        assert result["git_branchs"][0]["id"] == "branch-456"
        assert result["git_branchs"][0]["name"] == "feature/test"

    @pytest.mark.asyncio
    async def test_list_git_branchs_project_not_found(self, service, mock_project_repo):
        """Test git branches listing when project is not found"""
        mock_project_repo.find_by_id.return_value = None

        result = await service.list_git_branchs("project-999")

        assert result["success"] is False
        assert result["error"] == "Project project-999 not found"

    @pytest.mark.asyncio
    async def test_list_git_branchs_empty(
        self, service, mock_project_repo, mock_git_branch_repo, mock_project
    ):
        """Test git branches listing when no branches exist"""
        # Override the git_branchs to be empty for this test
        mock_project.git_branchs = {}
        mock_project_repo.find_by_id.return_value = mock_project
        mock_git_branch_repo.find_all_by_project.return_value = []

        result = await service.list_git_branchs("project-123")

        assert result["success"] is True
        assert result["count"] == 0
        assert result["git_branchs"] == []

    @pytest.mark.asyncio
    async def test_list_git_branchs_exception(self, service, mock_project_repo):
        """Test git branches listing exception handling"""
        mock_project_repo.find_by_id.side_effect = Exception("Database error")

        result = await service.list_git_branchs("project-123")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_update_git_branch_success(self, service, mock_git_branch_repo, mock_git_branch):
        """Test successful git branch update"""
        mock_git_branch_repo.find_all.return_value = [mock_git_branch]
        mock_git_branch_repo.update.return_value = True

        result = await service.update_git_branch(
            git_branch_id="branch-456",
            branch_name="feature/updated",
            description="Updated description"
        )

        assert result["success"] is True
        assert result["git_branch"]["name"] == "feature/updated"
        assert result["git_branch"]["description"] == "Updated description"
        assert result["updated_fields"] == ["name", "description"]

    @pytest.mark.asyncio
    async def test_update_git_branch_name_only(self, service, mock_git_branch_repo, mock_git_branch):
        """Test git branch update with name only"""
        mock_git_branch_repo.find_all.return_value = [mock_git_branch]
        mock_git_branch_repo.update.return_value = True

        result = await service.update_git_branch(
            git_branch_id="branch-456",
            branch_name="feature/new-name"
        )

        assert result["success"] is True
        assert result["updated_fields"] == ["name"]

    @pytest.mark.asyncio
    async def test_update_git_branch_description_only(self, service, mock_git_branch_repo, mock_git_branch):
        """Test git branch update with description only"""
        mock_git_branch_repo.find_all.return_value = [mock_git_branch]
        mock_git_branch_repo.update.return_value = True

        result = await service.update_git_branch(
            git_branch_id="branch-456",
            description="New description"
        )

        assert result["success"] is True
        assert result["updated_fields"] == ["description"]

    @pytest.mark.asyncio
    async def test_update_git_branch_not_found(self, service, mock_git_branch_repo):
        """Test git branch update when branch is not found"""
        mock_git_branch_repo.find_all.return_value = []

        result = await service.update_git_branch(
            git_branch_id="branch-999",
            branch_name="feature/updated"
        )

        assert result["success"] is False
        assert result["error"] == "Git branch with ID branch-999 not found"

    @pytest.mark.asyncio
    async def test_update_git_branch_no_fields(self, service, mock_git_branch_repo, mock_git_branch):
        """Test git branch update with no fields provided"""
        mock_git_branch_repo.find_all.return_value = [mock_git_branch]

        result = await service.update_git_branch(git_branch_id="branch-456")

        assert result["success"] is False
        assert result["error"] == "No fields to update. Provide branch_name and/or description."

    @pytest.mark.asyncio
    async def test_update_git_branch_exception(self, service, mock_git_branch_repo):
        """Test git branch update exception handling"""
        mock_git_branch_repo.find_all.side_effect = Exception("Database error")

        result = await service.update_git_branch(
            git_branch_id="branch-456",
            branch_name="feature/updated"
        )

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_delete_git_branch_success(self, service, mock_git_branch_repo, mock_git_branch):
        """Test successful git branch deletion"""
        mock_git_branch_repo.find_by_id.return_value = mock_git_branch
        mock_git_branch_repo.delete_branch.return_value = True

        result = await service.delete_git_branch("project-123", "branch-456")

        assert result["success"] is True
        assert result["message"] == "Git branch branch-456 deleted successfully"

        mock_git_branch_repo.find_by_id.assert_called_once_with("branch-456")
        mock_git_branch_repo.delete_branch.assert_called_once_with("branch-456")

    @pytest.mark.asyncio
    async def test_delete_git_branch_not_found(self, service, mock_git_branch_repo):
        """Test git branch deletion when branch is not found"""
        mock_git_branch_repo.find_by_id.return_value = None

        result = await service.delete_git_branch("project-123", "branch-999")

        assert result["success"] is False
        assert result["error"] == "Git branch with ID branch-999 not found"

    @pytest.mark.asyncio
    async def test_delete_git_branch_failed(self, service, mock_git_branch_repo, mock_git_branch):
        """Test git branch deletion failure"""
        mock_git_branch_repo.find_by_id.return_value = mock_git_branch
        mock_git_branch_repo.delete_branch.return_value = False

        result = await service.delete_git_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Failed to delete git branch branch-456"

    @pytest.mark.asyncio
    async def test_delete_git_branch_exception(self, service, mock_git_branch_repo):
        """Test git branch deletion exception handling"""
        mock_git_branch_repo.find_by_id.side_effect = Exception("Database error")

        result = await service.delete_git_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch_success(self, service, mock_git_branch_repo, mock_git_branch):
        """Test successful agent assignment to branch"""
        mock_git_branch_repo.find_by_name.return_value = mock_git_branch
        mock_git_branch_repo.assign_agent.return_value = True

        result = await service.assign_agent_to_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is True
        assert result["message"] == "Agent agent-1 assigned to git branch feature/test"

        mock_git_branch_repo.find_by_name.assert_called_once_with("project-123", "feature/test")
        mock_git_branch_repo.assign_agent.assert_called_once_with("project-123", "branch-456", "agent-1")

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch_not_found(self, service, mock_git_branch_repo):
        """Test agent assignment when branch is not found"""
        mock_git_branch_repo.find_by_name.return_value = None

        result = await service.assign_agent_to_branch("project-123", "agent-1", "feature/nonexistent")

        assert result["success"] is False
        assert result["error"] == "Git branch feature/nonexistent not found in project project-123"

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch_failed(self, service, mock_git_branch_repo, mock_git_branch):
        """Test agent assignment failure"""
        mock_git_branch_repo.find_by_name.return_value = mock_git_branch
        mock_git_branch_repo.assign_agent.return_value = False

        result = await service.assign_agent_to_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is False
        assert result["error"] == "Failed to assign agent agent-1 to git branch feature/test"

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch_exception(self, service, mock_git_branch_repo):
        """Test agent assignment exception handling"""
        mock_git_branch_repo.find_by_name.side_effect = Exception("Database error")

        result = await service.assign_agent_to_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch_success(self, service, mock_git_branch_repo, mock_git_branch):
        """Test successful agent unassignment from branch"""
        mock_git_branch_repo.find_by_name.return_value = mock_git_branch
        mock_git_branch_repo.unassign_agent.return_value = True

        result = await service.unassign_agent_from_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is True
        assert result["message"] == "Agent agent-1 unassigned from git branch feature/test"

        mock_git_branch_repo.find_by_name.assert_called_once_with("project-123", "feature/test")
        mock_git_branch_repo.unassign_agent.assert_called_once_with("project-123", "branch-456")

    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch_not_found(self, service, mock_git_branch_repo):
        """Test agent unassignment when branch is not found"""
        mock_git_branch_repo.find_by_name.return_value = None

        result = await service.unassign_agent_from_branch("project-123", "agent-1", "feature/nonexistent")

        assert result["success"] is False
        assert result["error"] == "Git branch feature/nonexistent not found in project project-123"

    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch_failed(self, service, mock_git_branch_repo, mock_git_branch):
        """Test agent unassignment failure"""
        mock_git_branch_repo.find_by_name.return_value = mock_git_branch
        mock_git_branch_repo.unassign_agent.return_value = False

        result = await service.unassign_agent_from_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is False
        assert result["error"] == "Failed to unassign agent agent-1 from git branch feature/test"

    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch_exception(self, service, mock_git_branch_repo):
        """Test agent unassignment exception handling"""
        mock_git_branch_repo.find_by_name.side_effect = Exception("Database error")

        result = await service.unassign_agent_from_branch("project-123", "agent-1", "feature/test")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_get_branch_statistics_success(self, service, mock_git_branch_repo):
        """Test successful branch statistics retrieval"""
        stats_data = {
            "total_tasks": 10,
            "completed_tasks": 7,
            "progress_percentage": 70
        }
        mock_git_branch_repo.get_branch_statistics.return_value = stats_data

        result = await service.get_branch_statistics("project-123", "branch-456")

        assert result["success"] is True
        assert result["statistics"] == stats_data

        mock_git_branch_repo.get_branch_statistics.assert_called_once_with("project-123", "branch-456")

    @pytest.mark.asyncio
    async def test_get_branch_statistics_error(self, service, mock_git_branch_repo):
        """Test branch statistics retrieval with error"""
        mock_git_branch_repo.get_branch_statistics.return_value = {"error": "Branch not found"}

        result = await service.get_branch_statistics("project-123", "branch-999")

        assert result["success"] is False
        assert result["error"] == "Branch not found"

    @pytest.mark.asyncio
    async def test_get_branch_statistics_exception(self, service, mock_git_branch_repo):
        """Test branch statistics retrieval exception handling"""
        mock_git_branch_repo.get_branch_statistics.side_effect = Exception("Database error")

        result = await service.get_branch_statistics("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_archive_branch_success(self, service, mock_git_branch_repo):
        """Test successful branch archiving"""
        mock_git_branch_repo.archive_branch.return_value = True

        result = await service.archive_branch("project-123", "branch-456")

        assert result["success"] is True
        assert result["message"] == "Git branch branch-456 archived successfully"

        mock_git_branch_repo.archive_branch.assert_called_once_with("project-123", "branch-456")

    @pytest.mark.asyncio
    async def test_archive_branch_failed(self, service, mock_git_branch_repo):
        """Test branch archiving failure"""
        mock_git_branch_repo.archive_branch.return_value = False

        result = await service.archive_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Failed to archive git branch branch-456"

    @pytest.mark.asyncio
    async def test_archive_branch_exception(self, service, mock_git_branch_repo):
        """Test branch archiving exception handling"""
        mock_git_branch_repo.archive_branch.side_effect = Exception("Database error")

        result = await service.archive_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_restore_branch_success(self, service, mock_git_branch_repo):
        """Test successful branch restoration"""
        mock_git_branch_repo.restore_branch.return_value = True

        result = await service.restore_branch("project-123", "branch-456")

        assert result["success"] is True
        assert result["message"] == "Git branch branch-456 restored successfully"

        mock_git_branch_repo.restore_branch.assert_called_once_with("project-123", "branch-456")

    @pytest.mark.asyncio
    async def test_restore_branch_failed(self, service, mock_git_branch_repo):
        """Test branch restoration failure"""
        mock_git_branch_repo.restore_branch.return_value = False

        result = await service.restore_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Failed to restore git branch branch-456"

    @pytest.mark.asyncio
    async def test_restore_branch_exception(self, service, mock_git_branch_repo):
        """Test branch restoration exception handling"""
        mock_git_branch_repo.restore_branch.side_effect = Exception("Database error")

        result = await service.restore_branch("project-123", "branch-456")

        assert result["success"] is False
        assert result["error"] == "Database error"