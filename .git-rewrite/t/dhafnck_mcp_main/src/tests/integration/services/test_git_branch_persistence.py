#!/usr/bin/env python3
"""
Unit tests for GitBranchService persistence fixes.

Tests the fix that ensures git branches are properly persisted to the database.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.application.services.git_branch_application_service import GitBranchApplicationService
from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
from fastmcp.task_management.domain.entities.git_branch import GitBranch


class TestGitBranchPersistence:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test GitBranchApplicationService properly persists branches to database"""
    
    @pytest.fixture
    def service(self):
        """Create GitBranchApplicationService instance"""
        return GitBranchApplicationService(user_id="test-user-123")
    
    def test_service_has_repository(self, service):
        """Test that GitBranchService has the ORM repository"""
        assert hasattr(service, '_git_branch_repo'), \
            "GitBranchService should have _git_branch_repo attribute"
        assert isinstance(service._git_branch_repo, ORMGitBranchRepository), \
            "Should use ORMGitBranchRepository for persistence"
    
    @pytest.mark.asyncio
    async def test_create_branch_uses_repository(self, service):
        """Test that create_git_branch uses the repository to persist"""
        # Mock the repository
        mock_repo = Mock(spec=ORMGitBranchRepository)
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = str(uuid.uuid4())
        mock_branch.project_id = "test-project"
        mock_branch.name = "test-branch"
        mock_branch.description = "Test description"
        mock_branch.created_at = datetime.now(timezone.utc)
        mock_branch.updated_at = datetime.now(timezone.utc)
        
        # Make create_branch return a mock branch
        mock_repo.create_branch = AsyncMock(return_value=mock_branch)
        mock_repo.find_by_name = AsyncMock(return_value=None)  # No existing branch
        
        # Mock project repository
        mock_project_repo = Mock()
        mock_project = Mock()
        mock_project_repo.find_by_id = AsyncMock(return_value=mock_project)
        
        # Replace the repositories
        service._git_branch_repo = mock_repo
        service._project_repo = mock_project_repo
        
        # Call create_git_branch
        result = await service.create_git_branch(
            project_id="test-project",
            git_branch_name="test-branch",
            git_branch_description="Test description"
        )
        
        # Verify repository was called
        mock_repo.create_branch.assert_called_once_with(
            "test-project",
            "test-branch",
            "Test description"
        )
        
        # Verify result
        assert result["success"]
        assert result["git_branch"]["id"] == mock_branch.id
    
    @pytest.mark.asyncio
    async def test_get_statistics_finds_persisted_branch(self, service):
        """Test that get_branch_statistics can find branches created by create_git_branch"""
        # Create a mock branch that will be "found"
        branch_id = str(uuid.uuid4())
        mock_stats = {
            "total_tasks": 5,
            "completed_tasks": 2,
            "progress_percentage": 40.0
        }
        
        # Mock the repository methods
        mock_repo = Mock(spec=ORMGitBranchRepository)
        mock_repo.get_branch_statistics = AsyncMock(return_value=mock_stats)
        
        # Replace the repository
        service._git_branch_repo = mock_repo
        
        # Get statistics for the branch
        result = await service.get_branch_statistics("test-project", branch_id)
        
        # Verify repository was called
        mock_repo.get_branch_statistics.assert_called_once_with("test-project", branch_id)
        
        # Verify result
        assert result["success"]
        assert "statistics" in result
        assert result["statistics"]["total_tasks"] == 5
        assert result["statistics"]["completed_tasks"] == 2
    
    @pytest.mark.asyncio
    async def test_get_statistics_branch_not_found(self, service):
        """Test proper error when branch is not found"""
        # Mock repository to return error
        mock_repo = Mock(spec=ORMGitBranchRepository)
        mock_repo.get_branch_statistics = AsyncMock(return_value={"error": "Branch not found"})
        
        service._git_branch_repo = mock_repo
        
        # Try to get statistics for non-existent branch
        result = await service.get_branch_statistics("test-project", "non-existent-id")
        
        # Should fail with not found error
        assert not result["success"]
        assert "not found" in result["error"].lower()
    
    def test_repository_initialization(self):
        """Test that repository is properly initialized in __init__"""
        # Create a new service instance
        service = GitBranchApplicationService()
        
        # Check repository is initialized
        assert service._git_branch_repo is not None
        assert isinstance(service._git_branch_repo, ORMGitBranchRepository)
    
    @pytest.mark.asyncio
    async def test_persistence_through_full_cycle(self, service):
        """Test that branches persist through create -> get cycle"""
        # Mock the full cycle
        branch_id = str(uuid.uuid4())
        created_branch = Mock()
        created_branch.id = branch_id
        created_branch.project_id = "test-project"
        created_branch.name = "feature/persistence-test"
        created_branch.description = "Testing persistence"
        created_branch.created_at = datetime.now(timezone.utc)
        created_branch.updated_at = datetime.now(timezone.utc)
        
        mock_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "progress_percentage": 0.0
        }
        
        mock_repo = Mock(spec=ORMGitBranchRepository)
        mock_repo.create_branch = AsyncMock(return_value=created_branch)
        mock_repo.find_by_name = AsyncMock(return_value=None)  # No existing branch
        mock_repo.get_branch_statistics = AsyncMock(return_value=mock_stats)
        
        # Mock project repo
        mock_project_repo = Mock()
        mock_project = Mock()
        mock_project_repo.find_by_id = AsyncMock(return_value=mock_project)
        
        service._git_branch_repo = mock_repo
        service._project_repo = mock_project_repo
        
        # Create branch
        create_result = await service.create_git_branch(
            project_id="test-project",
            git_branch_name="feature/persistence-test",
            git_branch_description="Testing persistence"
        )
        
        assert create_result["success"]
        branch_id = create_result["git_branch"]["id"]
        
        # Get statistics for the same branch
        stats_result = await service.get_branch_statistics("test-project", branch_id)
        
        assert stats_result["success"]
        assert "not found" not in stats_result.get("error", "")
        
        # Verify both repository methods were called
        mock_repo.create_branch.assert_called_once()
        mock_repo.get_branch_statistics.assert_called_once_with("test-project", branch_id)