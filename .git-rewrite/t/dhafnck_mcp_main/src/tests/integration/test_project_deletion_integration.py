"""
Integration tests for project deletion functionality

Tests the complete project deletion workflow including cascade deletion
of all related entities through the MCP interface.
"""

import pytest
import uuid
from typing import Dict, Any

from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.infrastructure.repositories.project_repository_factory import GlobalRepositoryManager


@pytest.fixture
def project_controller():
    """Create a project controller for testing."""
    facade_factory = ProjectFacadeFactory()
    return ProjectMCPController(facade_factory)


@pytest.fixture
async def test_project_with_data(project_controller):
    """Create a test project with branches, tasks, and contexts."""
    # Create project
    project_result = project_controller.handle_crud_operations(
        action="create",
        name=f"Test Delete Project {uuid.uuid4()}",
        description="Project for deletion testing"
    )
    
    assert project_result["success"] is True
    project_id = project_result["project"]["id"]
    
    # Create branches
    from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
    branch_use_case = CreateGitBranchUseCase()
    
    branch1 = await branch_use_case.execute(
        project_id=project_id,
        name="main",
        description="Main branch"
    )
    
    branch2 = await branch_use_case.execute(
        project_id=project_id,
        name="feature/test",
        description="Feature branch"
    )
    
    # Create tasks
    from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
    task_use_case = CreateTaskUseCase()
    
    task1 = await task_use_case.execute(
        git_branch_id=branch1["git_branch"]["id"],
        title="Task 1",
        description="Test task 1",
        priority="high"
    )
    
    task2 = await task_use_case.execute(
        git_branch_id=branch2["git_branch"]["id"],
        title="Task 2",
        description="Test task 2",
        priority="medium"
    )
    
    return {
        "project_id": project_id,
        "project_name": project_result["project"]["name"],
        "branch_ids": [branch1["git_branch"]["id"], branch2["git_branch"]["id"]],
        "task_ids": [task1["data"]["task"]["id"], task2["data"]["task"]["id"]]
    }


@pytest.mark.asyncio
async def test_delete_project_with_force(project_controller, test_project_with_data):
    """Test force deletion of project with all related data."""
    project_id = test_project_with_data["project_id"]
    
    # Delete project with force
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=True
    )
    
    # Verify deletion was successful
    assert result["success"] is True
    assert "successfully" in result["message"].lower()
    assert result["statistics"]["project_id"] == project_id
    assert result["statistics"]["git_branches_deleted"] >= 2
    assert result["statistics"]["tasks_deleted"] >= 2
    
    # Verify project no longer exists
    get_result = project_controller.handle_crud_operations(
        action="get",
        project_id=project_id
    )
    assert get_result["success"] is False


@pytest.mark.asyncio
async def test_delete_project_without_force_blocked(project_controller):
    """Test that deletion without force is blocked when active tasks exist."""
    # Create project with active task
    project_result = project_controller.handle_crud_operations(
        action="create",
        name=f"Active Project {uuid.uuid4()}",
        description="Project with active tasks"
    )
    
    project_id = project_result["project"]["id"]
    
    # Create branch and task
    from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
    from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
    from fastmcp.task_management.application.use_cases.update_task import UpdateTaskUseCase
    
    branch_use_case = CreateGitBranchUseCase()
    branch = await branch_use_case.execute(
        project_id=project_id,
        name="main",
        description="Main branch"
    )
    
    task_use_case = CreateTaskUseCase()
    task = await task_use_case.execute(
        git_branch_id=branch["git_branch"]["id"],
        title="Active Task",
        description="Task in progress"
    )
    
    # Update task to in_progress
    update_use_case = UpdateTaskUseCase()
    await update_use_case.execute(
        task_id=task["data"]["task"]["id"],
        status="in_progress"
    )
    
    # Try to delete without force
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=False
    )
    
    # Should fail due to active tasks
    assert result["success"] is False
    assert "active tasks" in result.get("error", "").lower() or "active tasks" in str(result).lower()
    
    # Clean up with force
    cleanup_result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=True
    )
    assert cleanup_result["success"] is True


@pytest.mark.asyncio
async def test_delete_nonexistent_project(project_controller):
    """Test deletion of non-existent project."""
    fake_project_id = str(uuid.uuid4())
    
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=fake_project_id,
        force=True
    )
    
    assert result["success"] is False
    assert "not found" in result.get("error", "").lower() or "not found" in str(result).lower()


@pytest.mark.asyncio
async def test_delete_project_cascade_verification(project_controller, test_project_with_data):
    """Test that cascade deletion removes all related entities."""
    project_id = test_project_with_data["project_id"]
    branch_ids = test_project_with_data["branch_ids"]
    task_ids = test_project_with_data["task_ids"]
    
    # Delete project
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=True
    )
    
    assert result["success"] is True
    
    # Verify branches are deleted
    from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
    branch_repo = ORMGitBranchRepository()
    
    for branch_id in branch_ids:
        branch = await branch_repo.find_by_id(branch_id)
        assert branch is None
    
    # Verify tasks are deleted
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    task_repo = ORMTaskRepository()
    
    for task_id in task_ids:
        task = await task_repo.find_by_id(task_id)
        assert task is None


@pytest.mark.asyncio
async def test_delete_project_statistics_accuracy(project_controller):
    """Test that deletion statistics are accurate."""
    # Create project with known entities
    project_result = project_controller.handle_crud_operations(
        action="create",
        name=f"Stats Test Project {uuid.uuid4()}",
        description="Project for statistics testing"
    )
    
    project_id = project_result["project"]["id"]
    
    # Create exactly 3 branches
    from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
    branch_use_case = CreateGitBranchUseCase()
    
    branch_ids = []
    for i in range(3):
        branch = await branch_use_case.execute(
            project_id=project_id,
            name=f"branch-{i}",
            description=f"Branch {i}"
        )
        branch_ids.append(branch["git_branch"]["id"])
    
    # Create exactly 2 tasks per branch
    from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
    task_use_case = CreateTaskUseCase()
    
    task_count = 0
    for branch_id in branch_ids:
        for j in range(2):
            await task_use_case.execute(
                git_branch_id=branch_id,
                title=f"Task {task_count}",
                description=f"Task {task_count}"
            )
            task_count += 1
    
    # Delete and verify statistics
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=True
    )
    
    assert result["success"] is True
    stats = result["statistics"]
    assert stats["git_branches_deleted"] == 3
    assert stats["tasks_deleted"] == 6  # 3 branches * 2 tasks each


@pytest.mark.asyncio
async def test_delete_project_error_recovery(project_controller):
    """Test that deletion continues despite partial failures."""
    # This test would require mocking internal components to simulate failures
    # For now, we'll test that the statistics include error tracking
    
    project_result = project_controller.handle_crud_operations(
        action="create",
        name=f"Error Test Project {uuid.uuid4()}",
        description="Project for error recovery testing"
    )
    
    project_id = project_result["project"]["id"]
    
    # Delete project
    result = project_controller.handle_crud_operations(
        action="delete",
        project_id=project_id,
        force=True
    )
    
    # Verify statistics include error tracking
    assert result["success"] is True
    assert "errors" in result["statistics"]
    assert isinstance(result["statistics"]["errors"], list)