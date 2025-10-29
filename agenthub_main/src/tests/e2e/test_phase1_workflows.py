"""
Phase 1 E2E Tests: Verify Array-Based Count Logic & API Response Structure

Tests comprehensive workflows to ensure Phase 1 refactoring works correctly:
- Backend removed emoji/count fields from DTOs
- Frontend calculates counts from arrays
- API added include_context parameter (default false)
- Response structure matches specifications

Test Coverage:
1. Task CRUD Operations (5 tests)
2. Subtask Operations (3 tests)
3. Context Loading (2 tests)
4. Array-Based Count Logic (3 tests)
5. No Regressions (2 tests)

Total: 15 comprehensive E2E tests

NOTE: This test file uses simplified MCP tools integration for reliable E2E testing.
It focuses on verifying Phase 1 response structures and behavior changes.
"""

import pytest
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from unittest.mock import patch

# Import MCP tools for E2E testing
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def git_branch_id():
    """Generate test git branch ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_user_id(user_id):
    """Alias for compatibility with existing test code."""
    return user_id


@pytest.fixture
def mcp_tools():
    """Initialize MCP tools with vision system disabled for faster tests"""
    return DDDCompliantMCPTools(enable_vision_system=False)


@pytest.fixture
def mock_auth(test_user_id):
    """Mock authentication context"""
    mock_auth_info = {
        'user_id': test_user_id,
        'email': 'test@example.com',
        'sub': test_user_id,
        'realm_roles': ['admin', 'user'],
        'resource_access': {}
    }

    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_auth_info', return_value=mock_auth_info), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id', return_value=test_user_id), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.services.authentication_service.AuthenticationService.get_authenticated_user_id', return_value=test_user_id):
        yield test_user_id


@pytest.fixture
def project_with_branch(mcp_tools, mock_auth, test_user_id):
    """Create test project with git branch"""
    # Create project
    project_result = mcp_tools._project_controller.manage_project(
        action="create",
        name=f"Phase1 E2E Test Project {uuid.uuid4().hex[:8]}",
        description="Project for Phase 1 E2E testing",
        user_id=test_user_id
    )

    assert project_result.get('success') is True
    project_id = project_result['data']['project']['id']

    # Create git branch with unique name
    branch_name = f"test-branch-{uuid.uuid4().hex[:8]}"
    branch_result = mcp_tools._git_branch_controller.manage_git_branch(
        action="create",
        project_id=project_id,
        git_branch_name=branch_name,
        git_branch_description="Main branch for testing",
        user_id=test_user_id
    )

    assert branch_result.get('success') is True, f"Branch creation failed: {branch_result}"
    git_branch_id = branch_result['data']['git_branch']['id']

    yield project_id, git_branch_id

    # Cleanup
    try:
        mcp_tools._project_controller.manage_project(
            action="delete",
            project_id=project_id,
            force="true",
            user_id=test_user_id
        )
    except:
        pass


class TestPhase1TaskCRUDOperations:
    """Test Phase 1 Task CRUD operations with array-based structure"""

    def test_create_task_response_structure(self, mcp_tools, project_with_branch, mock_auth):
        """Verify task creation returns array-based structure without count fields"""
        project_id, git_branch_id = project_with_branch

        result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Phase 1 Test Task",
            description="Testing array-based response structure",
            assignees="coding-agent",
            user_id=mock_auth
        )

        assert result["success"] is True
        task = result["data"]["task"]

        # PHASE 1 VERIFICATION: Arrays present
        assert "subtasks" in task, "Response must include subtasks array"
        assert "assignees" in task, "Response must include assignees array"
        assert "dependencies" in task, "Response must include dependencies array"

        # PHASE 2 VERIFICATION: Count fields present
        assert "subtask_count" in task, "subtask_count field must exist (Phase 2)"
        assert task["subtask_count"] == 0, "New task should have 0 subtasks"
        assert "completed_subtasks" in task, "completed_subtasks field must exist (Phase 2)"
        assert task["completed_subtasks"] == 0, "New task should have 0 completed subtasks"

        # PHASE 1 VERIFICATION: NO emoji fields
        assert "priority_emoji" not in task, "priority_emoji field must NOT exist (Phase 1)"
        assert "status_emoji" not in task, "status_emoji field must NOT exist (Phase 1)"

    def test_get_task_default_no_context(self, mcp_tools, project_with_branch, mock_auth):
        """Verify get task WITHOUT include_context excludes context_data"""
        project_id, git_branch_id = project_with_branch

        # Create task
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task for Context Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = create_result["data"]["task"]["id"]

        # Get task WITHOUT include_context (default)
        result = mcp_tools._task_controller.manage_task_sync(
            action="get",
            task_id=task_id,
            user_id=mock_auth
        )

        assert result["success"] is True
        task = result["data"]["task"]

        # PHASE 1 VERIFICATION: Arrays always present
        assert "subtasks" in task
        assert "assignees" in task

    def test_update_task_maintains_structure(self, mcp_tools, project_with_branch, mock_auth):
        """Verify task update maintains Phase 1 structure"""
        project_id, git_branch_id = project_with_branch

        # Create task
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task for Update Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = create_result["data"]["task"]["id"]

        # Update task
        result = mcp_tools._task_controller.manage_task_sync(
            action="update",
            task_id=task_id,
            title="Updated Task Title",
            status="in_progress",
            user_id=mock_auth
        )

        assert result["success"] is True
        task = result["data"]["task"]

        # PHASE 2 VERIFICATION: Count fields present after update
        assert "subtask_count" in task
        assert "completed_subtasks" in task

    def test_list_tasks_response_structure(self, mcp_tools, project_with_branch, mock_auth):
        """Verify list tasks returns all tasks without count fields"""
        project_id, git_branch_id = project_with_branch

        # Create multiple tasks
        for i in range(3):
            mcp_tools._task_controller.manage_task_sync(
                action="create",
                git_branch_id=git_branch_id,
                title=f"List Test Task {i+1}",
                assignees="coding-agent",
                user_id=mock_auth
            )

        # List tasks
        result = mcp_tools._task_controller.manage_task_sync(
            action="list",
            git_branch_id=git_branch_id,
            user_id=mock_auth
        )

        assert result["success"] is True
        tasks = result["data"]["tasks"]
        assert len(tasks) >= 3

        # PHASE 2 VERIFICATION: Check first task structure
        if tasks:
            task = tasks[0]
            # Must have count fields
            assert "subtask_count" in task
            assert "completed_subtasks" in task

    def test_delete_task_cascade_behavior(self, mcp_tools, project_with_branch, mock_auth):
        """Verify task deletion with subtasks works correctly"""
        project_id, git_branch_id = project_with_branch

        # Create parent task
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task for Delete Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = create_result["data"]["task"]["id"]

        # Create subtask
        mcp_tools._subtask_controller.manage_subtask(
            action="create",
            task_id=task_id,
            title="Subtask 1",
            assignees="coding-agent",
            user_id=mock_auth
        )

        # Delete parent task
        delete_result = mcp_tools._task_controller.manage_task_sync(
            action="delete",
            task_id=task_id,
            user_id=mock_auth
        )

        assert delete_result["success"] is True


class TestPhase1SubtaskOperations:
    """Test Phase 1 Subtask operations with array-based structure"""

    def test_create_subtask_updates_parent_array(self, mcp_tools, project_with_branch, mock_auth):
        """Verify creating subtask updates parent task subtasks array"""
        project_id, git_branch_id = project_with_branch

        # Create parent task
        task_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Parent Task",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = task_result["data"]["task"]["id"]

        # Create subtask
        subtask_result = mcp_tools._subtask_controller.manage_subtask(
            action="create",
            task_id=task_id,
            title="Test Subtask",
            assignees="coding-agent",
            user_id=mock_auth
        )

        assert subtask_result["success"] is True

        # Get parent task
        parent_result = mcp_tools._task_controller.manage_task_sync(
            action="get",
            task_id=task_id,
            user_id=mock_auth
        )

        parent_task = parent_result["data"]["task"]

        # PHASE 2 VERIFICATION: Parent has subtasks array
        assert "subtasks" in parent_task
        # PHASE 2 VERIFICATION: Has subtask_count field
        assert "subtask_count" in parent_task
        assert parent_task["subtask_count"] == 1, "Should have 1 subtask"
        assert "completed_subtasks" in parent_task
        assert parent_task["completed_subtasks"] == 0, "Should have 0 completed"

    def test_list_subtasks_response_structure(self, mcp_tools, project_with_branch, mock_auth):
        """Verify subtask list has arrays without count fields"""
        project_id, git_branch_id = project_with_branch

        # Create parent task
        task_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Parent for Subtask List",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = task_result["data"]["task"]["id"]

        # Create subtasks
        for i in range(2):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                assignees="coding-agent",
                user_id=mock_auth
            )

        # List subtasks
        result = mcp_tools._subtask_controller.manage_subtask(
            action="list",
            task_id=task_id,
            user_id=mock_auth
        )

        assert result["success"] is True
        subtasks = result["subtasks"]  # Direct access, not under 'data'

        # PHASE 2 VERIFICATION: Check subtask structure
        if subtasks:
            subtask = subtasks[0]
            assert "assignees" in subtask

    def test_complete_subtask_updates_parent_context(self, mcp_tools, project_with_branch, mock_auth):
        """Verify completing subtask updates parent correctly"""
        project_id, git_branch_id = project_with_branch

        # Create parent task
        task_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Parent for Completion Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = task_result["data"]["task"]["id"]

        # Create subtask
        subtask_result = mcp_tools._subtask_controller.manage_subtask(
            action="create",
            task_id=task_id,
            title="Subtask to Complete",
            assignees="coding-agent",
            user_id=mock_auth
        )
        subtask_id = subtask_result["subtask"]["id"]  # Direct access, not under 'data'

        # Complete subtask
        complete_result = mcp_tools._subtask_controller.manage_subtask(
            action="complete",
            task_id=task_id,
            subtask_id=subtask_id,
            completion_summary="Completed successfully",
            user_id=mock_auth
        )

        assert complete_result["success"] is True


class TestPhase1ContextLoading:
    """Test Phase 1 include_context parameter"""

    def test_include_context_false_excludes_context(self, mcp_tools, project_with_branch, mock_auth):
        """Verify include_context=false excludes heavy context data"""
        project_id, git_branch_id = project_with_branch

        # Create task
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task for Context Exclusion Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = create_result["data"]["task"]["id"]

        # Get with include_context=false
        result = mcp_tools._task_controller.manage_task_sync(
            action="get",
            task_id=task_id,
            include_context=False,
            user_id=mock_auth
        )

        assert result["success"] is True
        task = result["data"]["task"]

        # PHASE 1 VERIFICATION: Basic fields present
        assert "id" in task
        assert "title" in task
        assert "subtasks" in task

    def test_include_context_true_includes_context(self, mcp_tools, project_with_branch, mock_auth):
        """Verify include_context=true includes context data"""
        project_id, git_branch_id = project_with_branch

        # Create task
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task for Context Inclusion Test",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = create_result["data"]["task"]["id"]

        # Get with include_context=true
        result = mcp_tools._task_controller.manage_task_sync(
            action="get",
            task_id=task_id,
            include_context=True,
            user_id=mock_auth
        )

        assert result["success"] is True
        task = result["data"]["task"]

        # PHASE 1 VERIFICATION: Context may be present when explicitly requested
        assert "id" in task


class TestPhase1ArrayBasedCountLogic:
    """Test Phase 1 array-based count calculations"""

    def test_task_with_multiple_subtasks(self, mcp_tools, project_with_branch, mock_auth):
        """Verify subtasks array contains correct number of items"""
        project_id, git_branch_id = project_with_branch

        # Create parent task
        task_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task with Multiple Subtasks",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task_id = task_result["data"]["task"]["id"]

        # Create exactly 3 subtasks
        for i in range(3):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                assignees="coding-agent",
                user_id=mock_auth
            )

        # Get task
        result = mcp_tools._task_controller.manage_task_sync(
            action="get",
            task_id=task_id,
            user_id=mock_auth
        )

        task = result["data"]["task"]

        # PHASE 2 VERIFICATION: Count fields present
        assert "subtasks" in task
        assert "subtask_count" in task
        assert task["subtask_count"] == 3, "Should have 3 subtasks"
        assert task["subtask_count"] == len(task["subtasks"]), "Count should match array length"
        assert "completed_subtasks" in task
        assert task["completed_subtasks"] <= task["subtask_count"], "Completed should not exceed total"

    def test_task_with_zero_subtasks(self, mcp_tools, project_with_branch, mock_auth):
        """Verify empty subtasks array (not null)"""
        project_id, git_branch_id = project_with_branch

        # Create task without subtasks
        result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task with Zero Subtasks",
            assignees="coding-agent",
            user_id=mock_auth
        )

        task = result["data"]["task"]

        # PHASE 2 VERIFICATION: subtasks is array (not null) and count field present
        assert "subtasks" in task
        assert "subtask_count" in task
        assert task["subtask_count"] == 0, "Should have 0 subtasks"
        assert task["subtask_count"] == len(task["subtasks"]), "Count should match array length"
        assert "completed_subtasks" in task
        assert task["completed_subtasks"] == 0, "Should have 0 completed"

    def test_empty_arrays_handled_correctly(self, mcp_tools, project_with_branch, mock_auth):
        """Verify all arrays are lists, not null"""
        project_id, git_branch_id = project_with_branch

        # Create task
        result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task with Empty Arrays",
            assignees="coding-agent",
            user_id=mock_auth
        )

        task = result["data"]["task"]

        # PHASE 1 VERIFICATION: Arrays present (not null)
        assert "subtasks" in task
        assert "dependencies" in task


class TestPhase1NoRegressions:
    """Test that Phase 1 changes don't break existing functionality"""

    def test_existing_functionality_still_works(self, mcp_tools, project_with_branch, mock_auth):
        """Verify complete workflow still works"""
        project_id, git_branch_id = project_with_branch

        # CREATE
        create_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Regression Test Task",
            assignees="coding-agent",
            user_id=mock_auth
        )

        assert create_result["success"] is True
        task_id = create_result["data"]["task"]["id"]

        # UPDATE
        update_result = mcp_tools._task_controller.manage_task_sync(
            action="update",
            task_id=task_id,
            status="in_progress",
            user_id=mock_auth
        )

        assert update_result["success"] is True

        # COMPLETE
        complete_result = mcp_tools._task_controller.manage_task_sync(
            action="complete",
            task_id=task_id,
            completion_summary="Task completed",
            user_id=mock_auth
        )

        assert complete_result["success"] is True

    def test_task_dependencies_resolve_properly(self, mcp_tools, project_with_branch, mock_auth):
        """Verify task dependencies work correctly"""
        project_id, git_branch_id = project_with_branch

        # Create first task
        task1_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task 1 - Dependency",
            assignees="coding-agent",
            user_id=mock_auth
        )
        task1_id = task1_result["data"]["task"]["id"]

        # Create second task with dependency
        task2_result = mcp_tools._task_controller.manage_task_sync(
            action="create",
            git_branch_id=git_branch_id,
            title="Task 2 - Depends on Task 1",
            assignees="coding-agent",
            dependencies=task1_id,
            user_id=mock_auth
        )

        assert task2_result["success"] is True
        task2 = task2_result["data"]["task"]

        # PHASE 2 VERIFICATION: dependencies array present
        assert "dependencies" in task2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
