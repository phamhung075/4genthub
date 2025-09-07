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
        project.id = "test-project-id"
        git_branch = MagicMock()
        git_branch.id = "test-branch-id"
        git_branch.name = "test-branch"
        git_branch.description = "Test branch description"
        project.git_branchs = {"test-branch-id": git_branch}
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
    async def test_find_git_branch_by_id_in_memory(self, facade, mock_project):
        """Test _find_git_branch_by_id finding branch in memory."""
        with patch('fastmcp.task_management.infrastructure.repositories.project_repository_factory.GlobalRepositoryManager') as mock_manager:
            mock_repo = MagicMock()
            async def mock_find_all_func():
                return [mock_project]
            
            mock_repo.find_all = mock_find_all_func
            mock_manager.get_default.return_value = mock_repo
            
            result = await facade._find_git_branch_by_id("test-branch-id")
            
            assert result["success"] is True
            assert result["git_branch"]["id"] == "test-branch-id"
            assert result["git_branch"]["name"] == "test-branch"
            assert result["git_branch"]["description"] == "Test branch description"
            assert result["git_branch"]["project_id"] == "test-project-id"

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_from_database(self, facade):
        """Test _find_git_branch_by_id finding branch in database."""
        with patch('fastmcp.task_management.infrastructure.repositories.project_repository_factory.GlobalRepositoryManager') as mock_manager:
            mock_repo = MagicMock()
            async def mock_find_all_empty_func():
                return []  # No projects in memory
            
            mock_repo.find_all = mock_find_all_empty_func
            mock_manager.get_default.return_value = mock_repo
            
            with patch('fastmcp.task_management.infrastructure.database.database_source_manager.get_database_path') as mock_get_path:
                mock_get_path.return_value = "/path/to/db"
                
                with patch('sqlite3.connect') as mock_connect:
                    mock_conn = MagicMock()
                    mock_cursor = MagicMock()
                    mock_cursor.fetchone.return_value = ("project-123", "db-branch", "DB branch desc")
                    mock_conn.execute.return_value = mock_cursor
                    mock_connect.return_value.__enter__.return_value = mock_conn
                    
                    result = await facade._find_git_branch_by_id("db-branch-id")
                    
                    assert result["success"] is True
                    assert result["git_branch"]["id"] == "db-branch-id"
                    assert result["git_branch"]["name"] == "db-branch"
                    assert result["git_branch"]["description"] == "DB branch desc"
                    assert result["git_branch"]["project_id"] == "project-123"

    @pytest.mark.asyncio
    async def test_find_git_branch_by_id_not_found(self, facade):
        """Test _find_git_branch_by_id when branch not found."""
        with patch('fastmcp.task_management.infrastructure.repositories.project_repository_factory.GlobalRepositoryManager') as mock_manager:
            mock_repo = MagicMock()
            async def mock_find_all_empty2_func():
                return []
            
            mock_repo.find_all = mock_find_all_empty2_func
            mock_manager.get_default.return_value = mock_repo
            
            with patch('fastmcp.task_management.infrastructure.database.database_source_manager.get_database_path') as mock_get_path:
                mock_get_path.return_value = "/path/to/db"
                
                with patch('sqlite3.connect') as mock_connect:
                    mock_conn = MagicMock()
                    mock_cursor = MagicMock()
                    mock_cursor.fetchone.return_value = None
                    mock_conn.execute.return_value = mock_cursor
                    mock_connect.return_value.__enter__.return_value = mock_conn
                    
                    result = await facade._find_git_branch_by_id("unknown-branch-id")
                    
                    assert result["success"] is True
                    assert result["git_branch"]["id"] == "unknown-branch-id"
                    assert result["git_branch"]["name"] == "branch-unknown-"  # Truncated ID
                    assert result["git_branch"]["description"] == "Git branch description"
                    assert "project_id" not in result["git_branch"]  # No project_id for not found

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