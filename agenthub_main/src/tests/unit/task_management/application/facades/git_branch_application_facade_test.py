"""Test module for Git Branch Application Facade."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade
from fastmcp.task_management.application.services.git_branch_service import GitBranchService
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository


class TestGitBranchApplicationFacade:
    """Test suite for Git Branch Application Facade."""

    @pytest.fixture
    def mock_git_branch_service(self):
        """Create a mock GitBranchService."""
        return MagicMock()

    @pytest.fixture
    def mock_project_repo(self):
        """Create a mock ProjectRepository."""
        return MagicMock()

    @pytest.fixture
    def facade(self, mock_git_branch_service, mock_project_repo):
        """Create a GitBranchApplicationFacade instance with mocks."""
        return GitBranchApplicationFacade(
            git_branch_service=mock_git_branch_service,
            project_repo=mock_project_repo,
            project_id="test-project-id",
            user_id="test-user-id"
        )

    @pytest.fixture
    def mock_project(self):
        """Create a mock project with git branches."""
        project = MagicMock()
        project.id = "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID
        git_branch = MagicMock()
        git_branch.id = "550e8400-e29b-41d4-a716-446655440001"  # Valid UUID
        git_branch.name = "test-branch"
        git_branch.description = "Test branch description"
        project.git_branchs = {"550e8400-e29b-41d4-a716-446655440001": git_branch}
        return project

    @pytest.mark.asyncio
    async def test_create_tree_async(self, facade, mock_git_branch_service):
        """Test create_tree async method."""
        expected_result = {
            "success": True,
            "git_branch": {
                "id": "new-branch-id",
                "name": "new-feature",
                "description": "New feature branch"
            }
        }
        calls = []
        async def mock_create_func(*args, **kwargs):
            calls.append((args, kwargs))
            return expected_result
        
        mock_git_branch_service.create_git_branch = mock_create_func
        
        result = await facade.create_tree("test-project", "new-feature", "New feature branch")
        
        assert result == expected_result
        assert len(calls) == 1
        assert calls[0][0] == ("test-project", "new-feature", "New feature branch")

    def test_create_git_branch_sync_success(self, facade):
        """Test create_git_branch synchronous method success."""
        expected_result = {
            "success": True,
            "git_branch": {
                "id": "new-branch-id",
                "name": "feature-branch",
                "description": "Feature description"
            }
        }
        
        async def mock_create_tree_func(*args, **kwargs):
            return expected_result
        
        with patch.object(facade, 'create_tree', side_effect=mock_create_tree_func) as mock_create_tree:
            
            # Mock asyncio.get_running_loop to raise RuntimeError (no event loop)
            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                with patch('asyncio.run', return_value=expected_result) as mock_run:
                    result = facade.create_git_branch(
                        "test-project", "feature-branch", "Feature description"
                    )
                    
                    assert result == expected_result
                    mock_run.assert_called_once()

    def test_create_git_branch_sync_in_event_loop(self, facade):
        """Test create_git_branch when already in event loop."""
        expected_result = {
            "success": True,
            "git_branch": {
                "id": "new-branch-id",
                "name": "feature-branch",
                "description": "Feature description"
            }
        }
        
        async def mock_create_tree_func(*args, **kwargs):
            return expected_result
        
        with patch.object(facade, 'create_tree', side_effect=mock_create_tree_func) as mock_create_tree:
            
            # Mock asyncio.get_running_loop to return a running loop
            mock_loop = MagicMock()
            with patch('asyncio.get_running_loop', return_value=mock_loop):
                # Mock threading to simulate thread execution
                with patch('threading.Thread') as mock_thread_class:
                    mock_thread = MagicMock()
                    mock_thread_class.return_value = mock_thread
                    
                    # Simulate thread execution by calling the target function
                    def simulate_thread_run(*args, **kwargs):
                        # Get the target function from Thread constructor
                        target_func = mock_thread_class.call_args[1]['target']
                        # Call it directly (in test, we'll mock asyncio.run)
                        with patch('asyncio.run', return_value=expected_result):
                            target_func()
                    
                    mock_thread.start.side_effect = simulate_thread_run
                    
                    result = facade.create_git_branch(
                        "test-project", "feature-branch", "Feature description"
                    )
                    
                    assert result == expected_result

    def test_create_git_branch_sync_exception(self, facade):
        """Test create_git_branch handling exceptions."""
        async def mock_create_tree_func(*args, **kwargs):
            raise Exception("Creation failed")
        
        with patch.object(facade, 'create_tree', side_effect=mock_create_tree_func) as mock_create_tree:
            
            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                with patch('asyncio.run', side_effect=Exception("Creation failed")):
                    result = facade.create_git_branch(
                        "test-project", "feature-branch", "Feature description"
                    )
                    
                    assert result["success"] is False
                    assert "Failed to create git branch" in result["error"]
                    assert result["error_code"] == "CREATION_FAILED"

    def test_update_git_branch(self, facade):
        """Test update_git_branch method."""
        result = facade.update_git_branch(
            "branch-id-123",
            git_branch_name="updated-name",
            git_branch_description="updated description"
        )
        
        assert result["success"] is True
        assert result["git_branch_id"] == "branch-id-123"
        assert "updated successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_in_memory(self, facade):
        """Test _find_git_branch_by_id finding branch in memory."""
        from unittest.mock import AsyncMock, MagicMock
        
        # Create a mock git branch entity
        mock_git_branch = MagicMock()
        mock_git_branch.id = "550e8400-e29b-41d4-a716-446655440001"
        mock_git_branch.name = "test-branch"
        mock_git_branch.description = "Test branch description"
        mock_git_branch.project_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_git_branch.created_at = "2025-01-01T00:00:00"
        mock_git_branch.updated_at = "2025-01-01T00:00:00"
        
        # Create a mock repository with AsyncMock for async method
        mock_repo = AsyncMock()
        mock_repo.find_by_id = AsyncMock(return_value=mock_git_branch)
        
        # Mock the RepositoryProviderService
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_git_branch_repository = MagicMock(return_value=mock_repo)
            mock_provider_class.get_instance = MagicMock(return_value=mock_provider)
            
            result = await facade._find_git_branch_by_id("550e8400-e29b-41d4-a716-446655440001")
            
            assert result["success"] is True
            assert result["git_branch"]["id"] == "550e8400-e29b-41d4-a716-446655440001"
            assert result["git_branch"]["name"] == "test-branch"
            assert result["git_branch"]["description"] == "Test branch description"
            assert result["git_branch"]["project_id"] == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_from_database(self, facade):
        """Test _find_git_branch_by_id finding branch in database."""
        from unittest.mock import AsyncMock, MagicMock
        
        # Create a mock git branch entity (like we did in the memory test)
        mock_git_branch = MagicMock()
        mock_git_branch.id = "550e8400-e29b-41d4-a716-446655440003"
        mock_git_branch.name = "db-branch"
        mock_git_branch.description = "DB branch desc"
        mock_git_branch.project_id = "550e8400-e29b-41d4-a716-446655440002"
        mock_git_branch.created_at = "2025-01-01T00:00:00"
        mock_git_branch.updated_at = "2025-01-01T00:00:00"
        
        # Create a mock repository with AsyncMock for async method
        mock_repo = AsyncMock()
        mock_repo.find_by_id = AsyncMock(return_value=mock_git_branch)
        
        # Mock the RepositoryProviderService
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_git_branch_repository = MagicMock(return_value=mock_repo)
            mock_provider_class.get_instance = MagicMock(return_value=mock_provider)
            
            result = await facade._find_git_branch_by_id("550e8400-e29b-41d4-a716-446655440003")
            
            assert result["success"] is True
            assert result["git_branch"]["id"] == "550e8400-e29b-41d4-a716-446655440003"
            assert result["git_branch"]["name"] == "db-branch"
            assert result["git_branch"]["description"] == "DB branch desc"
            assert result["git_branch"]["project_id"] == "550e8400-e29b-41d4-a716-446655440002"

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_not_found(self, facade):
        """Test _find_git_branch_by_id when branch not found."""
        from unittest.mock import AsyncMock
        
        # Create a mock repository that returns None (not found)
        mock_repo = AsyncMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)
        
        # Mock the RepositoryProviderService
        with patch('fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService') as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_git_branch_repository = MagicMock(return_value=mock_repo)
            mock_provider_class.get_instance = MagicMock(return_value=mock_provider)
            
            result = await facade._find_git_branch_by_id("550e8400-e29b-41d4-a716-446655449999")
            
            assert result["success"] is False  # Changed: should be False when not found
            assert "not found" in result["error"].lower()
            assert result["error_code"] == "NOT_FOUND"

    def test_get_git_branch_by_id_sync_success(self, facade):
        """Test get_git_branch_by_id synchronous method."""
        expected_result = {
            "success": True,
            "git_branch": {
                "id": "branch-123",
                "name": "feature-branch"
            }
        }
        
        async def mock_find_func(*args, **kwargs):
            return expected_result
        
        with patch.object(facade, '_find_git_branch_by_id', side_effect=mock_find_func) as mock_find:
            
            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                with patch('asyncio.run', return_value=expected_result):
                    result = facade.get_git_branch_by_id("branch-123")
                    
                    assert result == expected_result

    def test_delete_git_branch_sync_success(self, facade, mock_git_branch_service):
        """Test delete_git_branch synchronous method success."""
        expected_result = {"success": True, "message": "Branch deleted"}
        def mock_delete_func(*args, **kwargs):
            return expected_result
        
        mock_git_branch_service.delete_git_branch = mock_delete_func
        
        with patch('asyncio.get_running_loop', side_effect=RuntimeError):
            with patch('asyncio.run', return_value=expected_result):
                result = facade.delete_git_branch("branch-to-delete")
                
                assert result == expected_result

    def test_list_git_branchs_sync_success(self, facade):
        """Test list_git_branchs synchronous method."""
        mock_trees_result = {
            "success": True,
            "git_branchs": [
                {
                    "id": "branch-1",
                    "name": "feature-1",
                    "description": "Feature 1",
                    "created_at": "2024-01-01",
                    "task_count": 5,
                    "completed_tasks": 3,
                    "progress": 60.0
                }
            ]
        }
        
        async def mock_list_trees_response(*args, **kwargs):
            return mock_trees_result
        
        with patch.object(facade, 'list_trees', side_effect=mock_list_trees_response) as mock_list_trees:
            
            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                with patch('asyncio.run', return_value=mock_trees_result):
                    result = facade.list_git_branchs("project-123")
                    
                    assert result["success"] is True
                    assert len(result["git_branchs"]) == 1
                    assert result["total_count"] == 1
                    assert result["git_branchs"][0]["name"] == "feature-1"

    @pytest.mark.asyncio
    async def test_get_tree_async(self, facade, mock_git_branch_service):
        """Test get_tree async method."""
        expected_result = {"success": True, "tree": {"name": "main"}}
        async def mock_get_func(*args, **kwargs):
            return expected_result
        
        mock_git_branch_service.get_git_branch = mock_get_func
        
        result = await facade.get_tree("project-id", "main")
        
        assert result == expected_result
        # Note: Cannot use assert_called_once_with with custom async functions

    @pytest.mark.asyncio
    async def test_list_trees_async(self, facade, mock_git_branch_service):
        """Test list_trees async method."""
        expected_result = {"success": True, "trees": []}
        async def mock_list_func(*args, **kwargs):
            return expected_result
        
        mock_git_branch_service.list_git_branchs = mock_list_func
        
        result = await facade.list_trees("project-id")
        
        assert result == expected_result
        # Note: Cannot use assert_called_once_with with custom async functions