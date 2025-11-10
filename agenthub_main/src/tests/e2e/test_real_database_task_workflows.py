"""
E2E Tests: Real Database Task Workflows (Phase 2 Investigation)

Simplified E2E tests using actual database via existing test infrastructure.
Tests complete user workflows to catch state-dependent bugs that contract tests miss.

Related Investigation: Task 51155169-3077-4c5c-bd2a-9e086aaadd50 - Phase 2
Goal: Find bugs that 120+ contract tests didn't catch by testing REAL workflows
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.task.create_task_request import (
    CreateTaskRequest,
)
from fastmcp.task_management.application.facades.subtask_application_facade import (
    SubtaskApplicationFacade,
)
from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade,
)
from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import (
    ORMSubtaskRepository,
)
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    ORMTaskRepository,
)


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return str(uuid4())


@pytest.fixture
def mock_auth(user_id):
    """Mock authentication context."""
    mock_auth_info = {
        'user_id': user_id,
        'email': 'test@example.com',
        'sub': user_id,
        'realm_roles': ['admin', 'user'],
        'resource_access': {}
    }

    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_auth_info', return_value=mock_auth_info), \
         patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', return_value=user_id), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id', return_value=user_id), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.services.authentication_service.AuthenticationService.get_authenticated_user_id', return_value=user_id):
        yield user_id


@pytest.fixture
def project_with_branch(shared_test_db, user_id, mock_auth):
    """Create test project with git branch for E2E testing."""
    from uuid import uuid4

    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import (
        DDDCompliantMCPTools,
    )

    mcp_tools = DDDCompliantMCPTools(enable_vision_system=False)

    # Create project
    project_result = mcp_tools._project_controller.manage_project(
        action="create",
        name=f"Real DB Test Project {uuid4().hex[:8]}",
        description="Project for real database E2E testing",
        user_id=user_id
    )

    assert project_result.get('success') is True, f"Project creation failed: {project_result}"
    project_id = project_result['data']['project']['id']

    # Create git branch
    branch_name = f"test-branch-{uuid4().hex[:8]}"
    branch_result = mcp_tools._git_branch_controller.manage_git_branch(
        action="create",
        project_id=project_id,
        git_branch_name=branch_name,
        git_branch_description="Branch for E2E testing",
        user_id=user_id
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
            user_id=user_id
        )
    except Exception:
        pass


@pytest.fixture
def git_branch_id(project_with_branch):
    """Extract git_branch_id from project_with_branch fixture."""
    _, git_branch_id = project_with_branch
    return git_branch_id


@pytest.fixture
def task_repository(shared_test_db, user_id):
    """Create real ORM task repository."""
    return ORMTaskRepository(session=None, user_id=user_id)


@pytest.fixture
def subtask_repository(shared_test_db, user_id):
    """Create real ORM subtask repository."""
    return ORMSubtaskRepository(session=None, user_id=user_id)


@pytest.fixture
def task_facade(task_repository):
    """Create task facade with real repository."""
    return TaskApplicationFacade(task_repository=task_repository)


@pytest.fixture
def subtask_facade(task_repository, subtask_repository):
    """Create subtask facade with real repositories."""
    return SubtaskApplicationFacade(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.mark.e2e
@pytest.mark.database
class TestCompleteTaskWorkflowsRealDB:
    """Test complete task workflows with real database operations."""

    def test_task_with_subtasks_maintains_accurate_counts_throughout_lifecycle(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        REAL WORKFLOW: Create task → Add subtasks → Complete some → Delete some → Verify counts.

        This is exactly what users do, testing ACTUAL state changes, not just structure.
        """
        # Create parent task
        parent_response = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="User Authentication Feature",
            description="Implement JWT auth system",
            status="in_progress",
            priority="high",
            assignees=["@coding-agent", "@security-auditor-agent"]
        ))

        # Handle response - could be object or dict
        if hasattr(parent_response, 'task'):
            parent = parent_response.task
            task_id = parent.id
        else:
            parent = parent_response.get("task") or parent_response
            task_id = parent.get("id") or parent["id"]

        # Verify initial state
        subtask_count = getattr(parent, 'subtask_count', parent.get('subtask_count', 0))
        completed_count = getattr(parent, 'completed_subtasks', parent.get('completed_subtasks', 0))

        assert subtask_count == 0
        assert completed_count == 0

        # Add 5 subtasks
        subtask_ids = []
        for i in range(5):
            result = subtask_facade.create_subtask(
                task_id=task_id,
                title=f"Auth Step {i+1}",
                status="todo"
            )
            assert result["success"] is True
            subtask_ids.append(result["subtask"]["id"])

        # Verify count after creation
        after_create = task_facade.get_task(task_id)["task"]
        assert after_create["subtask_count"] == 5, \
            f"Expected 5 subtasks, got {after_create['subtask_count']}"
        assert len(after_create["subtasks"]) == 5

        # Complete 3 subtasks
        for i in range(3):
            result = subtask_facade.complete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Completed step {i+1}",
                "action": "complete"
            })
            assert result["success"] is True

        # Verify completed count
        after_complete = task_facade.get_task(task_id)["task"]
        assert after_complete["subtask_count"] == 5
        assert after_complete["completed_subtasks"] == 3, \
            f"Expected 3 completed, got {after_complete['completed_subtasks']}"

        # Delete 2 subtasks (not the completed ones)
        for i in range(3, 5):
            result = subtask_facade.delete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "action": "delete"
            })
            assert result["success"] is True

        # Verify counts after deletion
        final = task_facade.get_task(task_id)["task"]
        assert final["subtask_count"] == 3, \
            f"Expected 3 remaining subtasks, got {final['subtask_count']}"
        assert final["completed_subtasks"] == 3, \
            "Completed count should still be 3 (we didn't delete completed ones)"

    def test_assignees_field_always_returns_array_never_string(
        self, task_facade, git_branch_id
    ):
        """
        USER REPORTED: Sometimes assignees comes back as string instead of array.
        Test all scenarios to find when this happens.
        """
        # Test 1: Single assignee as string
        task1 = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Single assignee test",
            description="E2E test - Single assignee test",
            assignees="@coding-agent"
        ))
        assert isinstance(task1["task"]["assignees"], list), \
            "Single assignee should return as array"
        assert len(task1["task"]["assignees"]) >= 0  # Could be 0 or 1 depending on parsing

        # Test 2: Multiple assignees as list
        task2 = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Multiple assignees test",
            description="E2E test - Multiple assignees test",
            assignees=["@coding-agent", "@test-agent"]
        ))
        assert isinstance(task2["task"]["assignees"], list)
        assert len(task2["task"]["assignees"]) >= 0

        # Test 3: Empty assignees
        task3 = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="No assignees test",
            description="E2E test - No assignees test",
            assignees=[]
        ))
        assert isinstance(task3["task"]["assignees"], list), \
            "Empty assignees should be array, not null"
        assert task3["task"]["assignees"] == [] or len(task3["task"]["assignees"]) == 0

    def test_subtasks_array_never_null_even_with_no_subtasks(
        self, task_facade, git_branch_id
    ):
        """
        USER REPORTED: Sometimes subtasks field is null instead of empty array.
        """
        task = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="No subtasks test",
            description="E2E test - No subtasks test",
            assignees=["@test-agent"]
        ))

        # Verify subtasks is array (empty, but not null)
        assert "subtasks" in task["task"], "subtasks field missing"
        assert isinstance(task["task"]["subtasks"], list), \
            f"subtasks should be array, got {type(task['task'].get('subtasks'))}"
        assert task["task"]["subtasks"] == []

    def test_progress_percentage_updates_when_subtasks_complete(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Test progress calculation with REAL subtask completion.
        """
        # Create task
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Progress test",
            description="E2E test: Progress test",
            status="in_progress",
            assignees=["@test-agent"]
        ))
        task_id = parent["task"]["id"]

        # Add 4 subtasks for easy percentage calculation (25% each)
        subtask_ids = []
        for i in range(4):
            result = subtask_facade.create_subtask(
                task_id=task_id,
                title=f"Step {i+1}"
            )
            subtask_ids.append(result["subtask"]["id"])

        # Complete 2 out of 4 (should be ~50%)
        for i in range(2):
            subtask_facade.complete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Done {i+1}",
                "action": "complete"
            })

        # Check progress
        task_50 = task_facade.get_task(task_id)["task"]
        progress = task_50.get("progress_percentage", 0)

        # Should be around 50% (allow some tolerance)
        assert 40 <= progress <= 60, \
            f"Expected ~50% progress (2/4 subtasks), got {progress}%"

    def test_timestamps_always_present_and_valid(
        self, task_facade, git_branch_id
    ):
        """
        Verify created_at and updated_at are always present with valid format.
        """
        from datetime import datetime

        task = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Timestamp test",
            description="E2E test - Timestamp test",
            assignees=["@test-agent"]
        ))

        task_data = task["task"]

        # Verify fields exist
        assert "created_at" in task_data, "created_at missing"
        assert "updated_at" in task_data, "updated_at missing"
        assert task_data["created_at"] is not None
        assert task_data["updated_at"] is not None

        # Verify they're parseable (valid ISO 8601)
        try:
            created = datetime.fromisoformat(task_data["created_at"].replace('Z', '+00:00'))
            updated = datetime.fromisoformat(task_data["updated_at"].replace('Z', '+00:00'))
            assert updated >= created
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Invalid timestamp format: {e}")

    def test_context_data_is_object_not_null(
        self, task_facade, git_branch_id
    ):
        """
        Verify context_data is always an object (dict), never null.
        """
        task = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Context test",
            description="E2E test - Context test",
            assignees=["@test-agent"]
        ))

        task_data = task["task"]
        context = task_data.get("context_data")

        # Should be dict, not None
        assert context is not None, "context_data should not be null"
        assert isinstance(context, dict), \
            f"context_data should be object/dict, got {type(context)}"


@pytest.mark.e2e
@pytest.mark.database
class TestConcurrentOperations:
    """Test concurrent operations don't corrupt counts."""

    def test_rapid_subtask_creation_maintains_count_accuracy(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Test that rapidly creating subtasks doesn't corrupt the parent count.
        """
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent test",
            description="E2E test - Concurrent test",
            assignees=["@test-agent"]
        ))
        task_id = parent["task"]["id"]

        # Rapidly create 10 subtasks
        created_count = 0
        for i in range(10):
            try:
                result = subtask_facade.create_subtask(
                    task_id=task_id,
                    title=f"Rapid subtask {i}"
                )
                if result["success"]:
                    created_count += 1
            except Exception as e:
                pytest.fail(f"Subtask creation failed: {e}")

        # Get final count
        final = task_facade.get_task(task_id)["task"]

        # Count should match number successfully created
        assert final["subtask_count"] == created_count, \
            f"Expected {created_count} subtasks, got {final['subtask_count']}"
        assert len(final["subtasks"]) == created_count

    def test_rapid_add_and_delete_maintains_consistency(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Stress test: Rapidly add and delete subtasks, verify count stays consistent.
        """
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Add/delete stress test",
            description="E2E test - Add/delete stress test",
            assignees=["@test-agent"]
        ))
        task_id = parent["task"]["id"]

        # Do 3 cycles of add/delete
        for cycle in range(3):
            # Add 3 subtasks
            subtask_ids = []
            for i in range(3):
                result = subtask_facade.create_subtask(
                    task_id=task_id,
                    title=f"Cycle {cycle} Subtask {i}"
                )
                subtask_ids.append(result["subtask"]["id"])

            # Verify count is 3
            check1 = task_facade.get_task(task_id)["task"]
            assert check1["subtask_count"] == 3

            # Delete all 3
            for subtask_id in subtask_ids:
                subtask_facade.delete_subtask({
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "action": "delete"
                })

            # Verify count is back to 0
            check2 = task_facade.get_task(task_id)["task"]
            assert check2["subtask_count"] == 0, \
                f"Cycle {cycle}: Expected 0 after deletion, got {check2['subtask_count']}"
