"""
E2E Tests: Complete Task Lifecycle with Real Database State

This test suite implements comprehensive end-to-end testing for complete task workflows
using REAL database operations (not mocks) to catch state-dependent bugs that unit tests miss.

Key Differences from Contract Tests:
- Uses REAL database via test fixtures (not mocks)
- Tests ACTUAL state changes and cascade effects
- Verifies counts, progress, and synchronization in real-world scenarios
- Tests complete user workflows from start to finish

Related Investigation: Task 51155169-3077-4c5c-bd2a-9e086aaadd50
"""

import pytest
from uuid import uuid4
from sqlalchemy import text
from unittest.mock import patch

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.application.dtos.subtask.create_subtask_request import CreateSubtaskRequest
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
from fastmcp.task_management.infrastructure.database.database_config import get_db_config


@pytest.fixture
def task_repository(shared_test_db, user_id):
    """Create real ORM task repository."""
    return ORMTaskRepository(session=None, user_id=user_id)


@pytest.fixture
def subtask_repository(shared_test_db, user_id):
    """Create real ORM subtask repository."""
    return ORMSubtaskRepository(session=None, user_id=user_id)


@pytest.fixture(autouse=True)
def mock_auth_context(user_id):
    """Mock authentication context for all tests in this file."""
    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', return_value=user_id):
        yield


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
class TestCompleteTaskLifecycleWithRealDatabase:
    """Test complete task workflows with actual database operations."""

    def test_create_task_with_subtasks_then_complete_verifies_all_counts(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Complete user workflow: Create task → Add 5 subtasks → Complete 3 → Verify counts.

        This catches bugs where:
        - subtask_count doesn't match actual count
        - completed_subtasks doesn't update
        - Database state gets out of sync with application state
        """

        # === STEP 1: CREATE PARENT TASK ===
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Feature: User Authentication System",
            description="Implement complete auth with JWT",
            status="in_progress",
            priority="high",
            assignees=["@coding-agent", "@security-auditor-agent"],
            estimated_effort="3 days"
        )

        create_result = task_facade.create_task(create_request)
        assert create_result["success"] is True
        task_id = create_result["task"]["id"]

        # Verify initial state from database
        task_data = create_result["task"]
        assert task_data["subtask_count"] == 0
        assert task_data["completed_subtasks"] == 0
        assert task_data["status"] == "in_progress"

        # === STEP 2: ADD 5 SUBTASKS ===
        subtask_titles = [
            "Design database schema",
            "Implement JWT token generation",
            "Create login endpoint",
            "Create registration endpoint",
            "Add password hashing"
        ]

        subtask_ids = []
        for title in subtask_titles:
            subtask_request = CreateSubtaskRequest(
                task_id=task_id,
                title=title,
                description=f"Implementation of {title.lower()}",
                status="todo",
                priority="medium"
            )
            subtask_result = subtask_facade.create_subtask(subtask_request)
            assert subtask_result["success"] is True
            subtask_ids.append(subtask_result["subtask"]["id"])

        # === STEP 3: VERIFY TASK COUNTS AFTER SUBTASK CREATION ===
        # Get task from database to verify real state
        get_result = task_facade.get_task(task_id)
        task_after_subtasks = get_result["task"]

        # CRITICAL: These counts must match reality
        assert task_after_subtasks["subtask_count"] == 5, \
            f"Expected 5 subtasks, got {task_after_subtasks['subtask_count']}"
        assert task_after_subtasks["completed_subtasks"] == 0, \
            f"Expected 0 completed, got {task_after_subtasks['completed_subtasks']}"
        assert len(task_after_subtasks["subtasks"]) == 5, \
            f"Expected 5 subtasks in array, got {len(task_after_subtasks['subtasks'])}"

        # === STEP 4: COMPLETE 3 SUBTASKS ===
        for i in range(3):
            complete_request = {
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Completed {subtask_titles[i]}",
                "action": "complete"
            }
            complete_result = subtask_facade.complete_subtask(complete_request)
            assert complete_result["success"] is True

        # === STEP 5: VERIFY COMPLETED COUNT UPDATED ===
        get_result_after_completion = task_facade.get_task(task_id)
        task_after_completion = get_result_after_completion["task"]

        # CRITICAL: Completed count must reflect actual completions
        assert task_after_completion["subtask_count"] == 5, \
            "Total subtask count should remain 5"
        assert task_after_completion["completed_subtasks"] == 3, \
            f"Expected 3 completed subtasks, got {task_after_completion['completed_subtasks']}"

        # Verify actual subtask statuses from database
        completed_count = sum(
            1 for st in task_after_completion["subtasks"]
            if st["status"] == "done"
        )
        assert completed_count == 3, \
            f"Expected 3 subtasks with status 'done', found {completed_count}"

        # === STEP 6: DELETE 2 SUBTASKS ===
        for i in range(2):
            delete_request = {
                "task_id": task_id,
                "subtask_id": subtask_ids[i + 3],  # Delete the last 2
                "action": "delete"
            }
            delete_result = subtask_facade.delete_subtask(delete_request)
            assert delete_result["success"] is True

        # === STEP 7: VERIFY COUNTS AFTER DELETION ===
        get_result_after_deletion = task_facade.get_task(task_id)
        task_after_deletion = get_result_after_deletion["task"]

        # CRITICAL: Counts must adjust after deletion
        assert task_after_deletion["subtask_count"] == 3, \
            f"Expected 3 subtasks after deletion, got {task_after_deletion['subtask_count']}"
        assert task_after_deletion["completed_subtasks"] == 3, \
            f"Expected 3 completed (none deleted were completed), got {task_after_deletion['completed_subtasks']}"

        # === STEP 8: VERIFY DATABASE CONSISTENCY ===
        # Directly query database to ensure counts match
        with db_config.get_session() as session:
            result = session.execute(
                text("""
                    SELECT
                        COUNT(*) as total_count,
                        SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed_count
                    FROM subtasks
                    WHERE parent_task_id = :task_id
                """),
                {"task_id": task_id}
            )
            row = result.fetchone()
            db_total_count = row[0]
            db_completed_count = row[1] if row[1] is not None else 0

            assert db_total_count == 3, \
                f"Database shows {db_total_count} subtasks, expected 3"
            assert db_completed_count == 3, \
                f"Database shows {db_completed_count} completed, expected 3"

    def test_progress_percentage_updates_with_subtask_completion(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify parent task progress updates correctly when subtasks are completed.

        Tests progress calculation accuracy in real scenarios:
        - 0 subtasks = progress based on task status
        - Mixed subtask statuses = correct percentage
        - All subtasks done = 100% (if task is done)
        """

        # Create parent task
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Feature: Payment Integration",
            description="Integrate Stripe payment processing",
            status="in_progress",
            priority="critical",
            assignees=["@coding-agent"]
        )

        create_result = task_facade.create_task(create_request)
        task_id = create_result["task"]["id"]

        # Initial progress (no subtasks)
        get_result = task_facade.get_task(task_id)
        initial_progress = get_result["task"]["progress_percentage"]
        # Progress should be based on task status, not 0
        assert initial_progress >= 0

        # Add 4 subtasks
        subtask_ids = []
        for i in range(4):
            subtask_request = CreateSubtaskRequest(
                task_id=task_id,
                title=f"Payment step {i+1}",
                description=f"Step {i+1} of integration"
            )
            result = subtask_facade.create_subtask(subtask_request)
            subtask_ids.append(result["subtask"]["id"])

        # Complete 2 out of 4 subtasks (50%)
        for i in range(2):
            subtask_facade.complete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Completed step {i+1}",
                "action": "complete"
            })

        # Verify 50% progress
        get_result_50 = task_facade.get_task(task_id)
        progress_50 = get_result_50["task"]["progress_percentage"]

        # Progress should reflect 50% completion (2/4)
        # Allow some tolerance for rounding
        assert 45 <= progress_50 <= 55, \
            f"Expected ~50% progress, got {progress_50}%"

        # Complete all remaining subtasks
        for i in range(2, 4):
            subtask_facade.complete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Completed step {i+1}",
                "action": "complete"
            })

        # Complete the parent task
        task_facade.complete_task(
            task_id=task_id,
            completion_summary="All payment integration complete",
            testing_notes="Tested with Stripe test keys"
        )

        # Verify 100% progress
        get_result_100 = task_facade.get_task(task_id)
        final_progress = get_result_100["task"]["progress_percentage"]

        assert final_progress == 100, \
            f"Expected 100% progress when all done, got {final_progress}%"

    def test_task_update_preserves_subtask_data_integrity(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify updating parent task doesn't corrupt subtask relationships.

        Tests that changing parent task properties doesn't:
        - Lose subtask references
        - Corrupt subtask counts
        - Break cascade updates
        """

        # Create task with subtasks
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Original Title",
            description="E2E test for task update data integrity",
            status="todo",
            assignees=["@test-agent"]
        )

        create_result = task_facade.create_task(create_request)
        task_id = create_result["task"]["id"]

        # Add 3 subtasks
        for i in range(3):
            subtask_facade.create_subtask(CreateSubtaskRequest(
                task_id=task_id,
                title=f"Subtask {i+1}"
            ))

        # Verify initial state
        initial_state = task_facade.get_task(task_id)["task"]
        assert initial_state["subtask_count"] == 3
        initial_subtask_ids = {st["id"] for st in initial_state["subtasks"]}

        # Update parent task multiple times
        for i in range(5):
            update_request = UpdateTaskRequest(
                task_id=task_id,
                title=f"Updated Title #{i+1}",
                status="in_progress" if i % 2 == 0 else "todo",
                priority="high" if i > 2 else "medium",
                details=f"Details update #{i+1}"
            )
            update_result = task_facade.update_task(update_request)
            assert update_result["success"] is True

        # Verify subtasks preserved after all updates
        final_state = task_facade.get_task(task_id)["task"]
        assert final_state["subtask_count"] == 3, \
            "Subtask count changed after parent updates"

        final_subtask_ids = {st["id"] for st in final_state["subtasks"]}
        assert final_subtask_ids == initial_subtask_ids, \
            "Subtask IDs changed after parent updates"

        # Verify all subtasks still accessible
        for subtask_id in initial_subtask_ids:
            get_subtask_result = subtask_facade.get_subtask({
                "task_id": task_id,
                "subtask_id": subtask_id,
                "action": "get"
            })
            assert get_subtask_result["success"] is True, \
                f"Subtask {subtask_id} not accessible after parent updates"


@pytest.mark.e2e
@pytest.mark.database
class TestTaskFieldConsistencyAcrossLifecycle:
    """Test that critical fields remain consistent throughout task lifecycle."""

    def test_assignees_always_array_never_null_or_string(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify assignees field is ALWAYS an array, never null or string.

        User reported seeing string values instead of arrays in some scenarios.
        """

        # Test 1: Single assignee (should be array with one element)
        single_assignee = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Single assignee test",
            description="E2E test for single assignee field consistency",
            assignees="@coding-agent"  # String input
        )
        result1 = task_facade.create_task(single_assignee)
        task1 = result1["task"]

        assert isinstance(task1["assignees"], list), \
            f"Single assignee should return array, got {type(task1['assignees'])}"
        assert len(task1["assignees"]) == 1
        assert task1["assignees"][0] == "@coding-agent"

        # Test 2: Multiple assignees (should be array)
        multiple_assignees = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Multiple assignees test",
            description="E2E test for multiple assignees field consistency",
            assignees=["@coding-agent", "@test-orchestrator-agent"]
        )
        result2 = task_facade.create_task(multiple_assignees)
        task2 = result2["task"]

        assert isinstance(task2["assignees"], list)
        assert len(task2["assignees"]) == 2

        # Test 3: No assignees (should be empty array, NOT null)
        no_assignees = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="No assignees test",
            description="E2E test for empty assignees field consistency",
            assignees=[]
        )
        result3 = task_facade.create_task(no_assignees)
        task3 = result3["task"]

        assert isinstance(task3["assignees"], list), \
            "Empty assignees should be [], not null"
        assert len(task3["assignees"]) == 0

    def test_timestamps_always_present_and_valid_iso8601(
        self, task_facade, git_branch_id
    ):
        """
        Verify created_at and updated_at are always present with valid ISO 8601 format.
        """
        from datetime import datetime

        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Timestamp test",
            description="E2E test for timestamp field consistency",
            assignees=["@test-agent"]
        )

        result = task_facade.create_task(create_request)
        task = result["task"]

        # Verify presence
        assert "created_at" in task, "created_at missing from response"
        assert "updated_at" in task, "updated_at missing from response"
        assert task["created_at"] is not None
        assert task["updated_at"] is not None

        # Verify ISO 8601 format (should be parseable)
        try:
            created = datetime.fromisoformat(task["created_at"].replace('Z', '+00:00'))
            updated = datetime.fromisoformat(task["updated_at"].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Timestamp not valid ISO 8601: {e}")

        # Verify updated_at >= created_at
        assert updated >= created, "updated_at should be >= created_at"

    def test_nested_objects_never_null(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify nested objects like subtasks and context_data are never null.
        """

        # Create task without subtasks
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Nested object test",
            description="E2E test for nested objects field consistency",
            assignees=["@test-agent"]
        )

        result = task_facade.create_task(create_request)
        task = result["task"]

        # Verify subtasks is array (empty, but not null)
        assert isinstance(task["subtasks"], list), \
            f"subtasks should be array, got {type(task.get('subtasks'))}"
        assert task["subtasks"] == [], \
            "Empty subtasks should be [], not null"

        # Verify context_data is object (not null)
        assert isinstance(task.get("context_data"), dict), \
            f"context_data should be object, got {type(task.get('context_data'))}"
