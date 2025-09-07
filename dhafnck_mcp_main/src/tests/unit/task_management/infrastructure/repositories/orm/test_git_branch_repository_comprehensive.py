"""Comprehensive test suite for ORM Git Branch Repository"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock, AsyncMock
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, func

from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)
from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch, Project, Task


class TestORMGitBranchRepository:
    """Test suite for ORMGitBranchRepository"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create an ORMGitBranchRepository instance"""
        repo = ORMGitBranchRepository(user_id="test-user")
        # Mock the get_db_session method
        repo.get_db_session = Mock(return_value=mock_session)
        return repo
    
    @pytest.fixture
    def sample_git_branch(self):
        """Create a sample GitBranch entity"""
        branch = GitBranch(
            id="branch-123",
            name="feature/test",
            description="Test branch",
            project_id="project-456",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        branch.assigned_agent_id = "agent-789"
        branch.priority = Priority.high()
        branch.status = TaskStatus.in_progress()
        return branch
    
    @pytest.fixture
    def sample_model(self):
        """Create a sample ProjectGitBranch model"""
        model = ProjectGitBranch()
        model.id = "branch-123"
        model.name = "feature/test"
        model.description = "Test branch"
        model.project_id = "project-456"
        model.created_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        model.assigned_agent_id = "agent-789"
        model.priority = "high"
        model.status = "in_progress"
        model.task_count = 10
        model.completed_task_count = 3
        model.user_id = "test-user"
        model.model_metadata = {}
        return model
    
    def test_init(self):
        """Test repository initialization"""
        repo = ORMGitBranchRepository(user_id="test-user")
        assert repo.user_id == "test-user"
        assert repo.model_class == ProjectGitBranch
    
    def test_model_to_git_branch(self, repository, sample_model):
        """Test converting model to domain entity"""
        git_branch = repository._model_to_git_branch(sample_model)
        
        assert isinstance(git_branch, GitBranch)
        assert git_branch.id == sample_model.id
        assert git_branch.name == sample_model.name
        assert git_branch.description == sample_model.description
        assert git_branch.project_id == sample_model.project_id
        assert git_branch.assigned_agent_id == sample_model.assigned_agent_id
        assert git_branch.priority == Priority.high()
        assert git_branch.status == TaskStatus.in_progress()
        # Note: Task counts are calculated dynamically by the entity,
        # not stored as private attributes from the model
        assert git_branch.get_task_count() == 0  # No tasks added to the branch yet
        assert git_branch.get_completed_task_count() == 0
    
    def test_git_branch_to_model_data(self, repository, sample_git_branch):
        """Test converting domain entity to model data"""
        # Mock get_task_count and get_completed_task_count
        sample_git_branch.get_task_count = Mock(return_value=5)
        sample_git_branch.get_completed_task_count = Mock(return_value=2)
        
        data = repository._git_branch_to_model_data(sample_git_branch)
        
        assert data["id"] == sample_git_branch.id
        assert data["project_id"] == sample_git_branch.project_id
        assert data["name"] == sample_git_branch.name
        assert data["description"] == sample_git_branch.description
        assert data["assigned_agent_id"] == sample_git_branch.assigned_agent_id
        assert data["priority"] == "high"
        assert data["status"] == "in_progress"
        assert data["task_count"] == 5
        assert data["completed_task_count"] == 2
        assert data["user_id"] == "test-user"
        assert data["model_metadata"] == {}
    
    @pytest.mark.asyncio
    async def test_save_create_new(self, repository, mock_session, sample_git_branch):
        """Test saving a new git branch"""
        # Mock query to return no existing branch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Mock task count methods
        sample_git_branch.get_task_count = Mock(return_value=0)
        sample_git_branch.get_completed_task_count = Mock(return_value=0)
        
        # Save branch
        await repository.save(sample_git_branch)
        
        # Verify query was called
        mock_session.query.assert_called_with(ProjectGitBranch)
        
        # Verify new branch was added
        mock_session.add.assert_called_once()
        added_branch = mock_session.add.call_args[0][0]
        assert isinstance(added_branch, ProjectGitBranch)
        assert added_branch.id == sample_git_branch.id
        assert added_branch.name == sample_git_branch.name
        
        # Verify flush was called
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_update_existing(self, repository, mock_session, sample_git_branch, sample_model):
        """Test updating an existing git branch"""
        # Mock query to return existing branch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Update branch data
        sample_git_branch.name = "feature/updated"
        sample_git_branch.get_task_count = Mock(return_value=15)
        sample_git_branch.get_completed_task_count = Mock(return_value=10)
        
        # Save branch
        await repository.save(sample_git_branch)
        
        # Verify existing model was updated
        assert sample_model.name == "feature/updated"
        assert sample_model.task_count == 15
        assert sample_model.completed_task_count == 10
        assert sample_model.updated_at != sample_git_branch.created_at
        
        # Verify no new branch was added
        mock_session.add.assert_not_called()
        
        # Verify flush was called
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_database_error(self, repository, mock_session, sample_git_branch):
        """Test save with database error"""
        # Mock session to raise SQLAlchemyError
        mock_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Attempt save and expect DatabaseException
        with pytest.raises(DatabaseException) as exc_info:
            await repository.save(sample_git_branch)
        
        assert "Failed to save git branch" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "save"
        assert exc_info.value.context["table"] == "project_git_branchs"
    
    @pytest.mark.asyncio
    async def test_find_by_id_found(self, repository, mock_session, sample_model):
        """Test finding git branch by ID when found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Find branch
        result = await repository.find_by_id("project-456", "branch-123")
        
        # Verify query
        mock_session.query.assert_called_with(ProjectGitBranch)
        
        # Verify result
        assert isinstance(result, GitBranch)
        assert result.id == "branch-123"
        assert result.project_id == "project-456"
    
    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_session):
        """Test finding git branch by ID when not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Find branch
        result = await repository.find_by_id("project-456", "nonexistent-branch")
        
        # Verify result is None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_by_id_database_error(self, repository, mock_session):
        """Test find_by_id with database error"""
        # Mock session to raise SQLAlchemyError
        mock_session.query.side_effect = SQLAlchemyError("Query error")
        
        # Attempt find and expect DatabaseException
        with pytest.raises(DatabaseException) as exc_info:
            await repository.find_by_id("project-456", "branch-123")
        
        assert "Failed to find git branch" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "find_by_id"
    
    @pytest.mark.asyncio
    async def test_find_by_name_found(self, repository, mock_session, sample_model):
        """Test finding git branch by name when found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Find branch
        result = await repository.find_by_name("project-456", "feature/test")
        
        # Verify result
        assert isinstance(result, GitBranch)
        assert result.name == "feature/test"
        assert result.project_id == "project-456"
    
    @pytest.mark.asyncio
    async def test_find_by_name_not_found(self, repository, mock_session):
        """Test finding git branch by name when not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Find branch
        result = await repository.find_by_name("project-456", "nonexistent-branch")
        
        # Verify result is None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_all_by_project(self, repository, mock_session):
        """Test finding all branches for a project"""
        # Create multiple models
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "branch-1"
        model1.name = "feature/1"
        model1.project_id = "project-456"
        model1.priority = "high"
        model1.status = "todo"
        model1.task_count = 5
        model1.completed_task_count = 0
        
        model2 = Mock(spec=ProjectGitBranch)
        model2.id = "branch-2"
        model2.name = "feature/2"
        model2.project_id = "project-456"
        model2.priority = "medium"
        model2.status = "in_progress"
        model2.task_count = 10
        model2.completed_task_count = 5
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1, model2]
        mock_session.query.return_value = mock_query
        
        # Find branches
        result = await repository.find_all_by_project("project-456")
        
        # Verify result
        assert len(result) == 2
        assert all(isinstance(b, GitBranch) for b in result)
        assert result[0].id == "branch-1"
        assert result[1].id == "branch-2"
    
    @pytest.mark.asyncio
    async def test_find_all_by_project_with_conversion_error(self, repository, mock_session, caplog):
        """Test find_all_by_project with model conversion error"""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Create models, one will fail conversion
        good_model = Mock(spec=ProjectGitBranch)
        good_model.id = "branch-1"
        good_model.name = "feature/1"
        good_model.project_id = "project-456"
        good_model.priority = "high"
        good_model.status = "todo"
        good_model.task_count = 5
        good_model.completed_task_count = 0
        
        bad_model = Mock(spec=ProjectGitBranch)
        bad_model.id = "branch-bad"
        # Missing required attributes will cause conversion error
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [good_model, bad_model]
        mock_session.query.return_value = mock_query
        
        # Find branches
        result = await repository.find_all_by_project("project-456")
        
        # Only good model should be converted
        assert len(result) == 1
        assert result[0].id == "branch-1"
        assert "Error converting model branch-bad" in caplog.text
    
    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        """Test successful branch deletion"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 1  # 1 row deleted
        mock_session.query.return_value = mock_query
        
        # Delete branch
        result = await repository.delete("project-456", "branch-123")
        
        # Verify result
        assert result is True
        mock_query.filter.return_value.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test deleting non-existent branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 0  # No rows deleted
        mock_session.query.return_value = mock_query
        
        # Delete branch
        result = await repository.delete("project-456", "nonexistent-branch")
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_branch_with_cascade(self, repository, mock_session):
        """Test deleting branch with cascading task deletion"""
        # Mock queries
        mock_query = Mock()
        
        # First query for tasks
        mock_session.query.side_effect = [
            mock_query,  # For Task query
            mock_query   # For ProjectGitBranch query
        ]
        
        mock_query.filter.return_value.delete.side_effect = [5, 1]  # 5 tasks, 1 branch deleted
        
        # Delete branch
        result = await repository.delete_branch("branch-123")
        
        # Verify both deletions occurred
        assert result is True
        assert mock_query.filter.return_value.delete.call_count == 2
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session, sample_model):
        """Test checking if branch exists - found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Check existence
        result = await repository.exists("project-456", "branch-123")
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """Test checking if branch exists - not found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Check existence
        result = await repository.exists("project-456", "nonexistent-branch")
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update(self, repository, sample_git_branch):
        """Test updating a branch"""
        # Mock save method
        repository.save = AsyncMock()
        
        original_updated_at = sample_git_branch.updated_at
        
        # Update branch
        await repository.update(sample_git_branch)
        
        # Verify updated_at was changed
        assert sample_git_branch.updated_at != original_updated_at
        
        # Verify save was called
        repository.save.assert_called_once_with(sample_git_branch)
    
    @pytest.mark.asyncio
    async def test_count_by_project(self, repository, mock_session):
        """Test counting branches by project"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 5
        mock_session.query.return_value = mock_query
        
        # Count branches
        result = await repository.count_by_project("project-456")
        
        # Verify result
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_session):
        """Test counting all branches"""
        # Mock query
        mock_query = Mock()
        mock_query.count.return_value = 10
        mock_session.query.return_value = mock_query
        
        # Count all branches
        result = await repository.count_all()
        
        # Verify result
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_find_by_assigned_agent(self, repository, mock_session):
        """Test finding branches by assigned agent"""
        # Create models
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "branch-1"
        model1.assigned_agent_id = "agent-789"
        model1.priority = "high"
        model1.status = "todo"
        model1.task_count = 5
        model1.completed_task_count = 0
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]
        mock_session.query.return_value = mock_query
        
        # Find branches
        result = await repository.find_by_assigned_agent("agent-789")
        
        # Verify result
        assert len(result) == 1
        assert result[0].assigned_agent_id == "agent-789"
    
    @pytest.mark.asyncio
    async def test_find_by_status(self, repository, mock_session):
        """Test finding branches by status"""
        # Create models
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "branch-1"
        model1.status = "in_progress"
        model1.priority = "high"
        model1.task_count = 5
        model1.completed_task_count = 2
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]
        mock_session.query.return_value = mock_query
        
        # Find branches
        result = await repository.find_by_status("project-456", "in_progress")
        
        # Verify result
        assert len(result) == 1
        assert result[0].status == TaskStatus.in_progress()
    
    @pytest.mark.asyncio
    async def test_find_available_for_assignment(self, repository, mock_session):
        """Test finding branches available for assignment"""
        # Create models
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "branch-1"
        model1.assigned_agent_id = None
        model1.status = "todo"
        model1.priority = "high"
        model1.task_count = 5
        model1.completed_task_count = 0
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]
        mock_session.query.return_value = mock_query
        
        # Find available branches
        result = await repository.find_available_for_assignment("project-456")
        
        # Verify result
        assert len(result) == 1
        assert result[0].assigned_agent_id is None
    
    @pytest.mark.asyncio
    async def test_assign_agent(self, repository, mock_session):
        """Test assigning agent to branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1  # 1 row updated
        mock_session.query.return_value = mock_query
        
        # Assign agent
        result = await repository.assign_agent("project-456", "branch-123", "agent-789")
        
        # Verify result
        assert result is True
        
        # Verify update was called with correct data
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["assigned_agent_id"] == "agent-789"
        assert "updated_at" in update_data
    
    @pytest.mark.asyncio
    async def test_unassign_agent(self, repository, mock_session):
        """Test unassigning agent from branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1  # 1 row updated
        mock_session.query.return_value = mock_query
        
        # Unassign agent
        result = await repository.unassign_agent("project-456", "branch-123")
        
        # Verify result
        assert result is True
        
        # Verify update was called with None
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["assigned_agent_id"] is None
    
    @pytest.mark.asyncio
    async def test_get_project_branch_summary(self, repository, mock_session):
        """Test getting project branch summary"""
        # Mock aggregate query result
        stats_result = Mock()
        stats_result.total_branches = 10
        stats_result.completed_branches = 3
        stats_result.active_branches = 5
        stats_result.assigned_branches = 7
        stats_result.total_tasks = 100
        stats_result.total_completed_tasks = 40
        
        # Mock status breakdown
        status_row1 = Mock()
        status_row1.status = "todo"
        status_row1.count = 2
        
        status_row2 = Mock()
        status_row2.status = "in_progress"
        status_row2.count = 5
        
        status_row3 = Mock()
        status_row3.status = "done"
        status_row3.count = 3
        
        # Mock queries
        mock_query = Mock()
        mock_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=stats_result)))),
            Mock(filter=Mock(return_value=Mock(
                group_by=Mock(return_value=Mock(all=Mock(return_value=[status_row1, status_row2, status_row3])))
            )))
        ]
        
        # Get summary
        result = await repository.get_project_branch_summary("project-456")
        
        # Verify result
        assert result["project_id"] == "project-456"
        assert result["summary"]["total_branches"] == 10
        assert result["summary"]["completed_branches"] == 3
        assert result["summary"]["active_branches"] == 5
        assert result["summary"]["assigned_branches"] == 7
        assert result["tasks"]["total_tasks"] == 100
        assert result["tasks"]["completed_tasks"] == 40
        assert result["tasks"]["overall_progress_percentage"] == 40.0
        assert result["status_breakdown"]["todo"] == 2
        assert result["status_breakdown"]["in_progress"] == 5
        assert result["status_breakdown"]["done"] == 3
        assert result["user_id"] == "test-user"
    
    @pytest.mark.asyncio
    @patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.uuid')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.datetime')
    async def test_create_branch(self, mock_datetime, mock_uuid, repository):
        """Test creating a new branch"""
        # Mock UUID generation
        mock_uuid.uuid4.return_value = "generated-uuid"
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Mock save method
        repository.save = AsyncMock()
        
        # Create branch
        result = await repository.create_branch("project-456", "feature/new", "New feature branch")
        
        # Verify result
        assert isinstance(result, GitBranch)
        assert result.id == "generated-uuid"
        assert result.name == "feature/new"
        assert result.description == "New feature branch"
        assert result.project_id == "project-456"
        assert result.created_at == mock_now
        assert result.updated_at == mock_now
        
        # Verify save was called
        repository.save.assert_called_once_with(result)
    
    @pytest.mark.asyncio
    async def test_create_git_branch_success(self, repository):
        """Test create_git_branch interface method - success"""
        # Mock create_branch
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        mock_branch.name = "feature/test"
        mock_branch.description = "Test branch"
        mock_branch.project_id = "project-456"
        mock_branch.created_at = datetime.now(timezone.utc)
        mock_branch.updated_at = datetime.now(timezone.utc)
        
        repository.create_branch = AsyncMock(return_value=mock_branch)
        
        # Create branch
        result = await repository.create_git_branch("project-456", "feature/test", "Test branch")
        
        # Verify result
        assert result["success"] is True
        assert result["git_branch"]["id"] == "branch-123"
        assert result["git_branch"]["name"] == "feature/test"
    
    @pytest.mark.asyncio
    async def test_create_git_branch_error(self, repository):
        """Test create_git_branch interface method - error"""
        # Mock create_branch to raise exception
        repository.create_branch = Mock(side_effect=Exception("Creation failed"))
        
        # Create branch
        result = await repository.create_git_branch("project-456", "feature/test", "Test branch")
        
        # Verify error result
        assert result["success"] is False
        assert "Creation failed" in result["error"]
        assert result["error_code"] == "CREATE_FAILED"
    
    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_found(self, repository, mock_session, sample_model):
        """Test get_git_branch_by_id - found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Get branch
        result = await repository.get_git_branch_by_id("branch-123")
        
        # Verify result
        assert result["success"] is True
        assert result["git_branch"]["id"] == "branch-123"
        assert result["git_branch"]["name"] == "feature/test"
    
    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_not_found(self, repository, mock_session):
        """Test get_git_branch_by_id - not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Get branch
        result = await repository.get_git_branch_by_id("nonexistent-branch")
        
        # Verify error result
        assert result["success"] is False
        assert "Git branch not found" in result["error"]
        assert result["error_code"] == "NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_list_git_branchs(self, repository):
        """Test listing git branches"""
        # Mock find_all_by_project
        branch1 = Mock(spec=GitBranch)
        branch1.id = "branch-1"
        branch1.name = "feature/1"
        branch1.description = "Feature 1"
        branch1.project_id = "project-456"
        branch1.created_at = datetime.now(timezone.utc)
        branch1.updated_at = datetime.now(timezone.utc)
        branch1.assigned_agent_id = None
        branch1.status = TaskStatus.todo()
        branch1.priority = Priority.medium()
        
        repository.find_all_by_project = AsyncMock(return_value=[branch1])
        
        # List branches
        result = await repository.list_git_branchs("project-456")
        
        # Verify result
        assert result["success"] is True
        assert len(result["git_branchs"]) == 1
        assert result["git_branchs"][0]["id"] == "branch-1"
        assert result["count"] == 1
    
    @pytest.mark.asyncio
    async def test_update_git_branch(self, repository, mock_session, sample_model):
        """Test updating git branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query
        
        # Update branch
        result = await repository.update_git_branch(
            "branch-123",
            git_branch_name="feature/updated",
            git_branch_description="Updated description"
        )
        
        # Verify model was updated
        assert sample_model.name == "feature/updated"
        assert sample_model.description == "Updated description"
        
        # Verify result
        assert result["success"] is True
        assert result["message"] == "Git branch updated successfully"
        assert result["git_branch"]["name"] == "feature/updated"
    
    @pytest.mark.asyncio
    async def test_delete_git_branch(self, repository):
        """Test deleting git branch"""
        # Mock delete method
        repository.delete = AsyncMock(return_value=True)
        
        # Delete branch
        result = await repository.delete_git_branch("project-456", "branch-123")
        
        # Verify result
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_assign_agent_to_branch(self, repository):
        """Test assigning agent to branch by name"""
        # Mock find_by_name and assign_agent
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        repository.find_by_name = AsyncMock(return_value=mock_branch)
        repository.assign_agent = AsyncMock(return_value=True)
        
        # Assign agent
        result = await repository.assign_agent_to_branch("project-456", "agent-789", "feature/test")
        
        # Verify result
        assert result["success"] is True
        assert "assigned to branch" in result["message"]
    
    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch(self, repository):
        """Test unassigning agent from branch by name"""
        # Mock find_by_name and unassign_agent
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        repository.find_by_name = AsyncMock(return_value=mock_branch)
        repository.unassign_agent = AsyncMock(return_value=True)
        
        # Unassign agent
        result = await repository.unassign_agent_from_branch("project-456", "agent-789", "feature/test")
        
        # Verify result
        assert result["success"] is True
        assert "unassigned from branch" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_branch_statistics(self, repository, mock_session):
        """Test getting branch statistics"""
        # Create model with statistics
        model = Mock(spec=ProjectGitBranch)
        model.id = "branch-123"
        model.name = "feature/test"
        model.project_id = "project-456"
        model.status = "in_progress"
        model.priority = "high"
        model.assigned_agent_id = "agent-789"
        model.task_count = 20
        model.completed_task_count = 8
        model.created_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = model
        mock_session.query.return_value = mock_query
        
        # Get statistics
        result = await repository.get_branch_statistics("project-456", "branch-123")
        
        # Verify result
        assert result["branch_id"] == "branch-123"
        assert result["branch_name"] == "feature/test"
        assert result["task_count"] == 20
        assert result["completed_task_count"] == 8
        assert result["progress_percentage"] == 40.0
    
    @pytest.mark.asyncio
    async def test_archive_branch(self, repository, mock_session):
        """Test archiving a branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1
        mock_session.query.return_value = mock_query
        
        # Archive branch
        result = await repository.archive_branch("project-456", "branch-123")
        
        # Verify update was called with cancelled status
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["status"] == "cancelled"
        
        # Verify result
        assert result["success"] is True
        assert "archived successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_restore_branch(self, repository, mock_session):
        """Test restoring an archived branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1
        mock_session.query.return_value = mock_query
        
        # Restore branch
        result = await repository.restore_branch("project-456", "branch-123")
        
        # Verify update was called with todo status
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["status"] == "todo"
        
        # Verify result
        assert result["success"] is True
        assert "restored successfully" in result["message"]