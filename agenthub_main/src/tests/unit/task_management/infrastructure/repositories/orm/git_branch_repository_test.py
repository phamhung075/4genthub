"""
Test suite for ORMGitBranchRepository.

Tests the ORM implementation of GitBranchRepository including
CRUD operations, domain entity conversions, and specialized git branch operations.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.base_exceptions import DatabaseException
from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch, Task


class TestORMGitBranchRepository:
    """Test suite for ORM Git Branch Repository functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = ORMGitBranchRepository(user_id="test_user")
        self.mock_session = Mock(spec=Session)
        
        # Sample test data
        self.project_id = str(uuid.uuid4())
        self.branch_id = str(uuid.uuid4())
        self.agent_id = "test_agent"
        
        # Mock model instance
        self.mock_model = Mock(spec=ProjectGitBranch)
        self.mock_model.id = self.branch_id
        self.mock_model.name = "feature/test"
        self.mock_model.description = "Test branch"
        self.mock_model.project_id = self.project_id
        self.mock_model.created_at = datetime.now(timezone.utc)
        self.mock_model.updated_at = datetime.now(timezone.utc)
        self.mock_model.assigned_agent_id = self.agent_id
        self.mock_model.priority = "medium"
        self.mock_model.status = "todo"
        
        # Mock domain entity
        self.mock_git_branch = GitBranch(
            id=self.branch_id,
            name="feature/test",
            description="Test branch",
            project_id=self.project_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_initialization(self):
        """Test repository initialization."""
        repo = ORMGitBranchRepository(user_id="test_user")
        assert repo.user_id == "test_user"
        assert repo.model_class == ProjectGitBranch

    def test_model_to_git_branch_conversion(self):
        """Test conversion from model to domain entity."""
        git_branch = self.repo._model_to_git_branch(self.mock_model)
        
        assert git_branch.id == self.branch_id
        assert git_branch.name == "feature/test"
        assert git_branch.description == "Test branch"
        assert git_branch.project_id == self.project_id
        assert git_branch.assigned_agent_id == self.agent_id
        assert git_branch.priority == Priority("medium")
        assert git_branch.status == TaskStatus("todo")

    def test_git_branch_to_model_data_conversion(self):
        """Test conversion from domain entity to model data."""
        model_data = self.repo._git_branch_to_model_data(self.mock_git_branch)
        
        assert model_data['id'] == self.branch_id
        assert model_data['name'] == "feature/test"
        assert model_data['description'] == "Test branch"
        assert model_data['project_id'] == self.project_id
        assert model_data['user_id'] == "test_user"
        assert 'task_count' in model_data
        assert 'completed_task_count' in model_data

    @pytest.mark.asyncio
    async def test_save_new_branch(self):
        """Test saving a new git branch."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            self.mock_session.query.return_value = mock_query
            
            await self.repo.save(self.mock_git_branch)
            
            self.mock_session.add.assert_called_once()
            self.mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_existing_branch(self):
        """Test updating an existing git branch."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            await self.repo.save(self.mock_git_branch)
            
            self.mock_session.add.assert_not_called()
            self.mock_session.flush.assert_called_once()
            assert hasattr(self.mock_model, 'updated_at')

    @pytest.mark.asyncio
    async def test_save_with_database_error(self):
        """Test save operation with database error."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            self.mock_session.query.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(DatabaseException) as exc_info:
                await self.repo.save(self.mock_git_branch)
            
            assert "Failed to save git branch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_by_id_success(self):
        """Test finding branch by ID when it exists."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_by_id(self.project_id, self.branch_id)
            
            assert result is not None
            assert result.id == self.branch_id
            assert result.name == "feature/test"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self):
        """Test finding branch by ID when it doesn't exist."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_by_id(self.project_id, "nonexistent")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_find_by_name_success(self):
        """Test finding branch by name when it exists."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_by_name(self.project_id, "feature/test")
            
            assert result is not None
            assert result.name == "feature/test"

    @pytest.mark.asyncio
    async def test_find_all_by_project(self):
        """Test finding all branches for a project."""
        mock_models = [self.mock_model]
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = mock_models
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_all_by_project(self.project_id)
            
            assert len(result) == 1
            assert result[0].id == self.branch_id

    @pytest.mark.asyncio
    async def test_find_all_by_project_with_conversion_error(self):
        """Test handling conversion errors during find_all_by_project."""
        # Mock model that will cause conversion error
        bad_model = Mock()
        bad_model.id = "bad_id"
        bad_model.priority = "invalid_priority"  # This will cause error
        
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = [bad_model]
            self.mock_session.query.return_value = mock_query
            
            # Should continue despite conversion error
            result = await self.repo.find_all_by_project(self.project_id)
            
            assert len(result) == 0  # Bad model filtered out

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful branch deletion."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.delete.return_value = 1
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.delete(self.project_id, self.branch_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test deletion of non-existent branch."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.delete.return_value = 0
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.delete(self.project_id, "nonexistent")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_branch_with_cascade(self):
        """Test branch deletion with cascade delete of tasks."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_task_query = Mock()
            mock_branch_query = Mock()
            
            # Mock task deletion
            mock_task_query.filter.return_value.delete.return_value = 2
            # Mock branch deletion
            mock_branch_query.filter.return_value.delete.return_value = 1
            
            self.mock_session.query.side_effect = [mock_task_query, mock_branch_query]
            
            result = await self.repo.delete_branch(self.branch_id)
            
            assert result is True
            assert self.mock_session.query.call_count == 2
            self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists check when branch exists."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.exists(self.project_id, self.branch_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists check when branch doesn't exist."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.exists(self.project_id, "nonexistent")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_assign_agent_success(self):
        """Test successful agent assignment."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.update.return_value = 1
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.assign_agent(self.project_id, self.branch_id, self.agent_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_assign_agent_failure(self):
        """Test agent assignment failure."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.update.return_value = 0
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.assign_agent(self.project_id, "nonexistent", self.agent_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_unassign_agent_success(self):
        """Test successful agent unassignment."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.update.return_value = 1
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.unassign_agent(self.project_id, self.branch_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_find_by_assigned_agent(self):
        """Test finding branches assigned to specific agent."""
        mock_models = [self.mock_model]
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = mock_models
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_by_assigned_agent(self.agent_id)
            
            assert len(result) == 1
            assert result[0].assigned_agent_id == self.agent_id

    @pytest.mark.asyncio
    async def test_find_by_status(self):
        """Test finding branches by status."""
        mock_models = [self.mock_model]
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = mock_models
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_by_status(self.project_id, "todo")
            
            assert len(result) == 1
            assert result[0].status == TaskStatus("todo")

    @pytest.mark.asyncio
    async def test_find_available_for_assignment(self):
        """Test finding branches available for assignment."""
        mock_models = [self.mock_model]
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = mock_models
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.find_available_for_assignment(self.project_id)
            
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_by_project(self):
        """Test counting branches by project."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.count.return_value = 5
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.count_by_project(self.project_id)
            
            assert result == 5

    @pytest.mark.asyncio
    async def test_get_project_branch_summary(self):
        """Test getting project branch summary."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            
            # Mock stats query result
            mock_stats = Mock()
            mock_stats.total_branches = 5
            mock_stats.completed_branches = 2
            mock_stats.active_branches = 2
            mock_stats.assigned_branches = 3
            mock_stats.total_tasks = 10
            mock_stats.total_completed_tasks = 6
            
            # Mock status breakdown query result
            mock_status_rows = [
                Mock(status="todo", count=2),
                Mock(status="in_progress", count=2),
                Mock(status="done", count=1)
            ]
            
            self.mock_session.query.side_effect = [
                Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_stats)))),
                Mock(filter=Mock(return_value=Mock(group_by=Mock(return_value=Mock(all=Mock(return_value=mock_status_rows))))))
            ]
            
            result = await self.repo.get_project_branch_summary(self.project_id)
            
            assert result["project_id"] == self.project_id
            assert result["summary"]["total_branches"] == 5
            assert result["summary"]["completed_branches"] == 2
            assert result["tasks"]["total_tasks"] == 10
            assert result["tasks"]["completed_tasks"] == 6
            assert result["tasks"]["overall_progress_percentage"] == 60.0

    @pytest.mark.asyncio
    async def test_create_branch(self):
        """Test creating a new branch."""
        with patch.object(self.repo, 'save') as mock_save:
            mock_save.return_value = None
            
            result = await self.repo.create_branch(self.project_id, "feature/new", "New feature")
            
            assert result.name == "feature/new"
            assert result.description == "New feature"
            assert result.project_id == self.project_id
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_git_branch_success(self):
        """Test create_git_branch interface method success."""
        with patch.object(self.repo, 'create_branch') as mock_create:
            mock_create.return_value = self.mock_git_branch
            
            result = await self.repo.create_git_branch(self.project_id, "feature/test", "Test branch")
            
            assert result["success"] is True
            assert result["git_branch"]["id"] == self.branch_id
            assert result["git_branch"]["name"] == "feature/test"

    @pytest.mark.asyncio
    async def test_create_git_branch_failure(self):
        """Test create_git_branch interface method failure."""
        with patch.object(self.repo, 'create_branch') as mock_create:
            mock_create.side_effect = Exception("Creation failed")
            
            result = await self.repo.create_git_branch(self.project_id, "feature/test", "Test branch")
            
            assert result["success"] is False
            assert "Creation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_success(self):
        """Test get_git_branch_by_id interface method success."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.get_git_branch_by_id(self.branch_id)
            
            assert result["success"] is True
            assert result["git_branch"]["id"] == self.branch_id

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_not_found(self):
        """Test get_git_branch_by_id interface method when not found."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.get_git_branch_by_id("nonexistent")
            
            assert result["success"] is False
            assert result["error_code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_git_branchs_success(self):
        """Test list_git_branchs interface method success."""
        with patch.object(self.repo, 'find_all_by_project') as mock_find:
            mock_find.return_value = [self.mock_git_branch]
            
            result = await self.repo.list_git_branchs(self.project_id)
            
            assert result["success"] is True
            assert result["count"] == 1
            assert len(result["git_branchs"]) == 1

    @pytest.mark.asyncio
    async def test_update_git_branch_success(self):
        """Test update_git_branch interface method success."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.update_git_branch(
                self.branch_id,
                git_branch_name="updated_name",
                git_branch_description="updated_description"
            )
            
            assert result["success"] is True
            assert "updated successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_git_branch_success(self):
        """Test delete_git_branch interface method success."""
        with patch.object(self.repo, 'delete') as mock_delete:
            mock_delete.return_value = True
            
            result = await self.repo.delete_git_branch(self.project_id, self.branch_id)
            
            assert result["success"] is True
            assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch_success(self):
        """Test assign_agent_to_branch interface method success."""
        with patch.object(self.repo, 'find_by_name') as mock_find:
            mock_find.return_value = self.mock_git_branch
            
            with patch.object(self.repo, 'assign_agent') as mock_assign:
                mock_assign.return_value = True
                
                result = await self.repo.assign_agent_to_branch(
                    self.project_id,
                    self.agent_id,
                    "feature/test"
                )
                
                assert result["success"] is True
                assert "assigned" in result["message"]

    @pytest.mark.asyncio
    async def test_get_branch_statistics_success(self):
        """Test get_branch_statistics interface method success."""
        # Update mock model with task counts
        self.mock_model.task_count = 10
        self.mock_model.completed_task_count = 6
        
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = self.mock_model
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.get_branch_statistics(self.project_id, self.branch_id)
            
            assert result["branch_id"] == self.branch_id
            assert result["task_count"] == 10
            assert result["completed_task_count"] == 6
            assert result["progress_percentage"] == 60.0

    @pytest.mark.asyncio
    async def test_archive_branch_success(self):
        """Test archive_branch interface method success."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.update.return_value = 1
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.archive_branch(self.project_id, self.branch_id)
            
            assert result["success"] is True
            assert "archived successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_restore_branch_success(self):
        """Test restore_branch interface method success."""
        with patch.object(self.repo, 'get_db_session') as mock_session_context:
            mock_session_context.return_value.__enter__.return_value = self.mock_session
            mock_query = Mock()
            mock_query.filter.return_value.update.return_value = 1
            self.mock_session.query.return_value = mock_query
            
            result = await self.repo.restore_branch(self.project_id, self.branch_id)
            
            assert result["success"] is True
            assert "restored successfully" in result["message"]