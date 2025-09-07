"""
Unit tests for DeleteProjectUseCase

Tests the project deletion use case with cascade deletion functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from fastmcp.task_management.application.use_cases.delete_project import DeleteProjectUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)


@pytest.fixture
def mock_repositories():
    """Create mock repositories for testing."""
    mock_project_repo = Mock()
    mock_git_branch_repo = Mock()
    mock_task_repo = Mock()
    mock_context_repo = Mock()
    
    return {
        "project_repo": mock_project_repo,
        "git_branch_repo": mock_git_branch_repo,
        "task_repo": mock_task_repo,
        "context_repo": mock_context_repo
    }


@pytest.fixture
def delete_project_use_case(mock_repositories):
    """Create DeleteProjectUseCase with mocked dependencies."""
    use_case = DeleteProjectUseCase(
        project_repo=mock_repositories["project_repo"],
        git_branch_repo=mock_repositories["git_branch_repo"],
        task_repo=mock_repositories["task_repo"],
        context_repo=mock_repositories["context_repo"]
    )
    return use_case


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="Test project for deletion",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_branches():
    """Create sample git branches for testing."""
    project_id = str(uuid.uuid4())
    return [
        GitBranch(
            id=str(uuid.uuid4()),
            name="main",
            description="Main branch",
            project_id=project_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        GitBranch(
            id=str(uuid.uuid4()),
            name="feature/test",
            description="Feature branch",
            project_id=project_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    branch_id = str(uuid.uuid4())
    return [
        Task(
            id=str(uuid.uuid4()),
            title="Task 1",
            description="Test task 1",
            status="todo",
            priority="medium",
            git_branch_id=branch_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Task 2",
            description="Test task 2",
            status="in_progress",
            priority="high",
            git_branch_id=branch_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]


@pytest.mark.asyncio
async def test_delete_project_success(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test successful project deletion with cascade."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["git_branch_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=sample_tasks)
    mock_repositories["task_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["context_repo"].delete = AsyncMock(return_value=True)
    
    # Execute
    result = await delete_project_use_case.execute(sample_project.id, force=True)
    
    # Assert
    assert result["success"] is True
    assert "successfully" in result["message"]
    assert result["statistics"]["project_id"] == sample_project.id
    assert result["statistics"]["git_branches_deleted"] == 2  # Two branches deleted
    assert result["statistics"]["tasks_deleted"] == 4  # Two tasks per branch
    assert len(result["statistics"]["errors"]) == 0


@pytest.mark.asyncio
async def test_delete_project_not_found(delete_project_use_case, mock_repositories):
    """Test deletion of non-existent project."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=None)
    
    # Execute and assert
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await delete_project_use_case.execute("non-existent-id", force=False)
    
    assert "non-existent-id" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_project_with_multiple_branches_no_force(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test deletion blocked when multiple branches exist and force=False."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=sample_tasks)
    
    # Execute and assert
    with pytest.raises(ValidationException) as exc_info:
        await delete_project_use_case.execute(sample_project.id, force=False)
    
    assert "multiple branches" in str(exc_info.value).lower()
    assert "force=True" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_project_with_force_ignores_active_tasks(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test force deletion ignores active tasks."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["git_branch_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=sample_tasks)
    mock_repositories["task_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["context_repo"].delete = AsyncMock(return_value=True)
    
    # Execute
    result = await delete_project_use_case.execute(sample_project.id, force=True)
    
    # Assert - should succeed despite active tasks
    assert result["success"] is True
    assert result["statistics"]["tasks_deleted"] > 0


@pytest.mark.asyncio
async def test_delete_project_continues_on_partial_failure(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test deletion continues even if some operations fail."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["git_branch_repo"].delete = AsyncMock(side_effect=[True, False])  # Second branch fails
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=sample_tasks)
    mock_repositories["task_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["context_repo"].delete = AsyncMock(side_effect=Exception("Context deletion failed"))
    
    # Execute
    result = await delete_project_use_case.execute(sample_project.id, force=True)
    
    # Assert - should succeed with errors logged
    assert result["success"] is True
    assert len(result["statistics"]["errors"]) > 0
    assert result["statistics"]["git_branches_deleted"] == 1  # Only one branch deleted successfully


@pytest.mark.asyncio
async def test_delete_project_database_error(delete_project_use_case, mock_repositories, sample_project):
    """Test database error during project deletion."""
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(return_value=False)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=[])
    
    # Execute and assert
    with pytest.raises(DatabaseException) as exc_info:
        await delete_project_use_case.execute(sample_project.id, force=True)
    
    assert "Failed to delete project" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_project_cascade_order(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test that deletion happens in correct order."""
    call_order = []
    
    # Setup mocks with tracking
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(
        side_effect=lambda x: call_order.append("project") or True
    )
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["git_branch_repo"].delete = AsyncMock(
        side_effect=lambda x: call_order.append("branch") or True
    )
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=sample_tasks)
    mock_repositories["task_repo"].delete = AsyncMock(
        side_effect=lambda x: call_order.append("task") or True
    )
    mock_repositories["context_repo"].delete = AsyncMock(
        side_effect=lambda x: call_order.append("context") or True
    )
    
    # Execute
    await delete_project_use_case.execute(sample_project.id, force=True)
    
    # Assert order: contexts should be deleted before tasks, tasks before branches, branches before project
    context_indices = [i for i, x in enumerate(call_order) if x == "context"]
    task_indices = [i for i, x in enumerate(call_order) if x == "task"]
    branch_indices = [i for i, x in enumerate(call_order) if x == "branch"]
    project_indices = [i for i, x in enumerate(call_order) if x == "project"]
    
    # Verify project is deleted last
    assert all(project_indices[-1] > idx for idx in branch_indices)
    assert all(project_indices[-1] > idx for idx in task_indices)


@pytest.mark.asyncio
async def test_delete_project_statistics_tracking(delete_project_use_case, mock_repositories, sample_project, sample_branches, sample_tasks):
    """Test that deletion statistics are accurately tracked."""
    # Create tasks with subtasks
    tasks_with_subtasks = sample_tasks.copy()
    tasks_with_subtasks[0].subtasks = ["subtask1", "subtask2"]
    
    # Setup mocks
    mock_repositories["project_repo"].find_by_id = AsyncMock(return_value=sample_project)
    mock_repositories["project_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["git_branch_repo"].find_by_project = AsyncMock(return_value=sample_branches)
    mock_repositories["git_branch_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["task_repo"].find_by_git_branch = AsyncMock(return_value=tasks_with_subtasks)
    mock_repositories["task_repo"].delete = AsyncMock(return_value=True)
    mock_repositories["context_repo"].delete = AsyncMock(return_value=True)
    
    # Execute
    result = await delete_project_use_case.execute(sample_project.id, force=True)
    
    # Assert statistics
    stats = result["statistics"]
    assert stats["project_name"] == sample_project.name
    assert stats["git_branches_deleted"] == len(sample_branches)
    assert stats["tasks_deleted"] == len(tasks_with_subtasks) * len(sample_branches)
    assert stats["subtasks_deleted"] == 2 * len(sample_branches)  # 2 subtasks on first task
    assert "deleted_at" in stats