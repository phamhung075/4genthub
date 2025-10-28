"""
E2E Tests: Database Integrity and Concurrent Operations

This test suite validates database consistency under real-world conditions:
- Foreign key constraints are enforced
- Referential integrity maintained across operations
- Concurrent modifications don't corrupt data
- Race conditions are handled properly
- Transaction isolation works correctly

These tests use REAL database operations to catch issues that mocks miss.

Related Investigation: Task 51155169-3077-4c5c-bd2a-9e086aaadd50 Phase 2
"""

import pytest
from uuid import uuid4
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
import threading
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
def db_config():
    """Get database configuration."""
    return get_db_config()


@pytest.fixture
def task_repository(db_config, user_id):
    """Create real task repository with authenticated user."""
    return ORMTaskRepository(db_config, user_id=user_id)


@pytest.fixture
def subtask_repository(db_config, user_id):
    """Create real subtask repository with authenticated user."""
    return ORMSubtaskRepository(db_config, user_id=user_id)


@pytest.fixture(autouse=True)
def mock_auth_context(user_id):
    """Mock authentication context for all tests in this file."""
    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', return_value=user_id):
        yield


@pytest.fixture
def git_branch_repository(user_id):
    """Create real git branch repository with authenticated user."""
    from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
    return ORMGitBranchRepository(user_id=user_id)


@pytest.fixture
def task_facade(task_repository, git_branch_repository):
    """Create task facade with git branch repository for auto-creation support."""
    return TaskApplicationFacade(
        task_repository=task_repository,
        git_branch_repository=git_branch_repository
    )


@pytest.fixture
def subtask_facade(task_repository, subtask_repository):
    """Create subtask facade."""
    return SubtaskApplicationFacade(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.integrity
class TestDatabaseIntegrityConstraints:
    """Test that database constraints are properly enforced."""

    def test_cannot_create_task_with_invalid_git_branch_id(
        self, task_facade
    ):
        """
        DEPRECATED: This test is no longer valid due to context auto-creation.

        With context auto-creation enabled, tasks can be created even if the branch
        context doesn't exist - it will be automatically created. This test now
        expects SUCCESS instead of failure.

        See test_context_auto_creation_on_task_creation() for the new behavior.
        """
        # Generate a non-existent git branch ID
        invalid_git_branch_id = str(uuid4())

        # With auto-creation, this should now SUCCEED
        result = task_facade.create_task(CreateTaskRequest(
            git_branch_id=invalid_git_branch_id,
            title="Task with auto-created branch context",
            description="E2E test for context auto-creation with invalid branch ID",
            assignees=["@test-agent"]
        ))

        # Should succeed due to context auto-creation
        assert result["success"] is True, \
            "Task creation should succeed with auto-created branch context"
        assert result["task"]["git_branch_id"] == invalid_git_branch_id, \
            "Task should have the specified git_branch_id"

    def test_cannot_create_subtask_for_non_existent_parent(
        self, subtask_facade
    ):
        """
        Verify cannot create subtask if parent task doesn't exist.
        """
        fake_task_id = str(uuid4())

        # Try to create subtask for non-existent parent
        with pytest.raises(Exception) as exc_info:
            subtask_facade.create_subtask(CreateSubtaskRequest(
                task_id=fake_task_id,
                title="Orphan subtask"
            ))

        # Should fail due to missing parent
        error_message = str(exc_info.value).lower()
        assert "not found" in error_message or "does not exist" in error_message or "invalid" in error_message, \
            "Should reject subtask creation for non-existent parent"

    def test_deleting_task_cascades_to_subtasks(
        self, task_facade, subtask_facade, git_branch_id, db_config
    ):
        """
        Verify ON DELETE CASCADE works for task → subtasks relationship.
        """

        # Create parent with subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Parent to test cascade",
            description="E2E test for cascade deletion of subtasks",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        # Create 3 subtasks
        for i in range(3):
            subtask_facade.create_subtask(CreateSubtaskRequest(
                task_id=task_id,
                title=f"Subtask {i}"
            ))

        # Verify subtasks exist
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM subtasks WHERE parent_task_id = :task_id"),
                {"task_id": task_id}
            )
            assert result.scalar() == 3

        # Delete parent
        task_facade.delete_task(task_id)

        # Verify cascade deletion
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM subtasks WHERE parent_task_id = :task_id"),
                {"task_id": task_id}
            )
            assert result.scalar() == 0, \
                "Subtasks should be cascade deleted with parent"

    def test_database_counts_match_application_counts(
        self, task_facade, subtask_facade, git_branch_id, db_config
    ):
        """
        Verify counts in application layer match actual database counts.

        This catches bugs where:
        - Cached counts get stale
        - Count updates don't persist to database
        - Application and database state diverge
        """

        # Create task with 5 subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Count consistency test",
            description="E2E test for database and application count consistency",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        subtask_ids = []
        for i in range(5):
            result = subtask_facade.create_subtask(CreateSubtaskRequest(
                task_id=task_id,
                title=f"Subtask {i}",
                status="todo"
            ))
            subtask_ids.append(result["subtask"]["id"])

        # Complete 3 subtasks
        for i in range(3):
            subtask_facade.complete_subtask({
                "task_id": task_id,
                "subtask_id": subtask_ids[i],
                "completion_summary": f"Done {i}",
                "action": "complete"
            })

        # Get application counts
        task_data = task_facade.get_task(task_id)["task"]
        app_total = task_data["subtask_count"]
        app_completed = task_data["completed_subtasks"]

        # Get database counts
        with db_config.get_session() as session:
            result = session.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed
                    FROM subtasks
                    WHERE parent_task_id = :task_id
                """),
                {"task_id": task_id}
            )
            row = result.fetchone()
            db_total = row[0]
            db_completed = row[1] if row[1] is not None else 0

        # CRITICAL: Application and database must match
        assert app_total == db_total, \
            f"Application shows {app_total} subtasks, database shows {db_total}"
        assert app_completed == db_completed, \
            f"Application shows {app_completed} completed, database shows {db_completed}"

    def test_context_auto_creation_on_task_creation(
        self, task_facade, db_config
    ):
        """
        Verify that branch context is automatically created when creating a task
        with a git_branch_id that has no existing context.

        This is the primary test for Phase 2 context auto-creation feature.
        """
        # Generate a new git branch ID that doesn't exist in database
        new_branch_id = str(uuid4())

        # Verify context doesn't exist yet
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM branch_contexts WHERE id = :id"),
                {"id": new_branch_id}
            )
            assert result.scalar() == 0, "Context should not exist before task creation"

        # Create task - should auto-create branch context
        task_result = task_facade.create_task(CreateTaskRequest(
            git_branch_id=new_branch_id,
            title="Task triggering context auto-creation",
            description="Testing context auto-creation when creating task with non-existent git_branch_id",
            assignees=["@test-agent"]
        ))

        # Verify task created successfully
        if not task_result["success"]:
            print(f"Task creation failed: {task_result}")
        assert task_result["success"] is True, \
            f"Task creation should succeed with auto-created context. Error: {task_result.get('error', 'Unknown')}"
        assert task_result["task"]["git_branch_id"] == new_branch_id

        # Verify branch context was auto-created
        with db_config.get_session() as session:
            result = session.execute(
                text("""
                    SELECT id, data
                    FROM branch_contexts
                    WHERE id = :id
                """),
                {"id": new_branch_id}
            )
            row = result.fetchone()

            assert row is not None, "Branch context should be auto-created"
            assert row[0] == new_branch_id, "Context ID should match branch ID"

            # Verify auto-creation metadata
            import json
            context_data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            assert context_data.get("auto_created") is True, \
                "Context should be marked as auto-created"
            assert context_data.get("source") == "task_creation_auto_create", \
                "Context should have correct source metadata"

    def test_context_auto_creation_includes_metadata(
        self, task_facade, db_config
    ):
        """
        Verify auto-created contexts include proper metadata for traceability.
        """
        new_branch_id = str(uuid4())

        # Create task to trigger auto-creation
        task_facade.create_task(CreateTaskRequest(
            git_branch_id=new_branch_id,
            title="Metadata test task",
            description="E2E test for auto-created context metadata",
            assignees=["@test-agent"]
        ))

        # Retrieve auto-created context
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT data FROM branch_contexts WHERE id = :id"),
                {"id": new_branch_id}
            )
            row = result.fetchone()
            assert row is not None

            import json
            context_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]

            # Verify required metadata fields
            assert "auto_created" in context_data, "Should have auto_created flag"
            assert context_data["auto_created"] is True
            assert "created_at" in context_data, "Should have created_at timestamp"
            assert "source" in context_data, "Should have source field"
            assert context_data["source"] == "task_creation_auto_create"
            assert "git_branch_id" in context_data, "Should store git_branch_id"
            assert context_data["git_branch_id"] == new_branch_id

    def test_existing_context_not_recreated(
        self, task_facade, git_branch_id, db_config
    ):
        """
        Verify that if branch context already exists, it's not recreated.
        This tests the "create if not exists" logic.
        """
        # Get initial context creation time
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT created_at FROM branch_contexts WHERE id = :id"),
                {"id": git_branch_id}
            )
            row = result.fetchone()
            initial_created_at = row[0] if row else None

        # Create task with existing branch context
        task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Task with existing context",
            description="E2E test for existing context preservation",
            assignees=["@test-agent"]
        ))

        # Verify context creation time unchanged
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT created_at FROM branch_contexts WHERE id = :id"),
                {"id": git_branch_id}
            )
            row = result.fetchone()
            final_created_at = row[0] if row else None

            if initial_created_at:
                assert final_created_at == initial_created_at, \
                    "Existing context should not be recreated"

    def test_multiple_tasks_share_auto_created_context(
        self, task_facade
    ):
        """
        Verify multiple tasks can be created with the same auto-created branch context.
        """
        shared_branch_id = str(uuid4())

        # Create 3 tasks with same branch ID
        task_ids = []
        for i in range(3):
            result = task_facade.create_task(CreateTaskRequest(
                git_branch_id=shared_branch_id,
                title=f"Task {i} sharing context",
                description=f"E2E test for shared context - task {i}",
                assignees=["@test-agent"]
            ))
            assert result["success"] is True
            task_ids.append(result["task"]["id"])

        # Verify all tasks have same branch ID
        for task_id in task_ids:
            task_data = task_facade.get_task(task_id)["task"]
            assert task_data["git_branch_id"] == shared_branch_id, \
                "All tasks should share the same git_branch_id"

    def test_context_auto_creation_preserves_foreign_key_integrity(
        self, task_facade, db_config
    ):
        """
        Verify that auto-created contexts maintain proper foreign key relationships.
        This ensures the auto-creation doesn't bypass database constraints.
        """
        new_branch_id = str(uuid4())

        # Create task with auto-created context
        task_result = task_facade.create_task(CreateTaskRequest(
            git_branch_id=new_branch_id,
            title="Foreign key integrity test",
            description="E2E test for foreign key integrity with auto-created context",
            assignees=["@test-agent"]
        ))
        task_id = task_result["task"]["id"]

        # Verify foreign key relationship exists
        with db_config.get_session() as session:
            # Check task references the context
            result = session.execute(
                text("""
                    SELECT t.git_branch_id, c.context_id
                    FROM tasks t
                    LEFT JOIN contexts c ON t.git_branch_id = c.context_id AND c.level = 'branch'
                    WHERE t.id = :task_id
                """),
                {"task_id": task_id}
            )
            row = result.fetchone()

            assert row is not None, "Task should exist"
            assert row[0] == new_branch_id, "Task should have correct git_branch_id"
            assert row[1] == new_branch_id, "Context should exist with matching ID"


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.concurrency
class TestConcurrentOperations:
    """Test system behavior under concurrent modifications."""

    def test_concurrent_subtask_creation_maintains_accurate_count(
        self, task_facade, subtask_facade, git_branch_id, db_config
    ):
        """
        Verify parent subtask_count is accurate when multiple subtasks created concurrently.

        This catches race conditions in count updates.
        """

        # Create parent
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent creation test",
            description="E2E test for concurrent subtask creation",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        # Create 10 subtasks concurrently
        num_subtasks = 10

        def create_subtask(index):
            """Create a subtask."""
            try:
                result = subtask_facade.create_subtask(CreateSubtaskRequest(
                    task_id=task_id,
                    title=f"Concurrent subtask {index}"
                ))
                return result["success"]
            except Exception as e:
                print(f"Error creating subtask {index}: {e}")
                return False

        # Use ThreadPoolExecutor for concurrent creation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_subtask, i) for i in range(num_subtasks)]
            results = [f.result() for f in as_completed(futures)]

        # Verify all succeeded
        assert all(results), "All concurrent creations should succeed"

        # Brief delay to allow count updates to settle
        sleep(0.2)

        # Get final count
        final_task = task_facade.get_task(task_id)["task"]
        final_count = final_task["subtask_count"]

        # CRITICAL: Count should match number created
        assert final_count == num_subtasks, \
            f"Expected {num_subtasks} subtasks, got {final_count}"

        # Verify database matches
        with db_config.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM subtasks WHERE parent_task_id = :task_id"),
                {"task_id": task_id}
            )
            db_count = result.scalar()
            assert db_count == num_subtasks, \
                f"Database shows {db_count} subtasks, expected {num_subtasks}"

    def test_concurrent_subtask_completion_maintains_accurate_completed_count(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify completed_subtasks count is accurate when multiple subtasks completed concurrently.
        """

        # Create parent with 10 subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent completion test",
            description="E2E test for concurrent subtask completion",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        subtask_ids = []
        for i in range(10):
            result = subtask_facade.create_subtask(CreateSubtaskRequest(
                task_id=task_id,
                title=f"Subtask {i}",
                status="todo"
            ))
            subtask_ids.append(result["subtask"]["id"])

        # Complete all subtasks concurrently
        def complete_subtask(subtask_id, index):
            """Complete a subtask."""
            try:
                result = subtask_facade.complete_subtask({
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "completion_summary": f"Completed {index}",
                    "action": "complete"
                })
                return result["success"]
            except Exception as e:
                print(f"Error completing subtask {index}: {e}")
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(complete_subtask, subtask_id, i)
                for i, subtask_id in enumerate(subtask_ids)
            ]
            results = [f.result() for f in as_completed(futures)]

        assert all(results), "All concurrent completions should succeed"

        # Allow count updates to settle
        sleep(0.2)

        # Verify final completed count
        final_task = task_facade.get_task(task_id)["task"]
        completed_count = final_task["completed_subtasks"]

        assert completed_count == 10, \
            f"Expected 10 completed subtasks, got {completed_count}"

    def test_concurrent_task_updates_dont_corrupt_data(
        self, task_facade, git_branch_id
    ):
        """
        Verify concurrent updates to same task don't corrupt data.

        This tests transaction isolation and locking.
        """

        # Create task
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent update test",
            description="E2E test for concurrent task updates",
            status="todo",
            priority="low",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        # Track update results
        update_results = []
        lock = threading.Lock()

        def update_task(update_num):
            """Update the task."""
            try:
                result = task_facade.update_task(UpdateTaskRequest(
                    task_id=task_id,
                    title=f"Updated by thread {update_num}",
                    status="in_progress" if update_num % 2 == 0 else "todo",
                    priority="high" if update_num > 5 else "medium",
                    details=f"Update #{update_num}"
                ))
                with lock:
                    update_results.append({
                        "success": result["success"],
                        "update_num": update_num
                    })
                return result["success"]
            except Exception as e:
                print(f"Error in update {update_num}: {e}")
                with lock:
                    update_results.append({
                        "success": False,
                        "update_num": update_num,
                        "error": str(e)
                    })
                return False

        # Perform 20 concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_task, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All updates should complete (even if some fail due to conflicts)
        assert len(update_results) == 20, \
            "All update attempts should complete"

        # At least some should succeed
        successful_updates = sum(1 for r in update_results if r["success"])
        assert successful_updates > 0, \
            "At least some concurrent updates should succeed"

        # Final task should be in valid state (not corrupted)
        final_task = task_facade.get_task(task_id)["task"]

        # Verify critical fields are not corrupted
        assert final_task["id"] == task_id, "Task ID should not change"
        assert final_task["git_branch_id"] == git_branch_id, "Branch ID should not change"
        assert final_task["status"] in ["todo", "in_progress", "done"], \
            "Status should be valid value"
        assert final_task["priority"] in ["low", "medium", "high", "critical"], \
            "Priority should be valid value"

    def test_rapid_subtask_add_delete_maintains_consistency(
        self, task_facade, subtask_facade, git_branch_id
    ):
        """
        Verify rapid add/delete operations maintain count consistency.

        This stresses the cascade update mechanisms.
        """

        # Create parent
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Rapid operations test",
            description="E2E test for rapid add/delete operations consistency",
            assignees=["@test-agent"]
        ))
        assert parent["success"] is True
        task_id = parent["task"]["id"]

        # Rapidly create and delete subtasks
        for cycle in range(5):
            # Create 5 subtasks
            subtask_ids = []
            for i in range(5):
                result = subtask_facade.create_subtask(CreateSubtaskRequest(
                    task_id=task_id,
                    title=f"Cycle {cycle} Subtask {i}"
                ))
                subtask_ids.append(result["subtask"]["id"])

            # Verify count is 5
            check1 = task_facade.get_task(task_id)["task"]
            assert check1["subtask_count"] == 5, \
                f"Cycle {cycle}: Expected 5 subtasks after creation"

            # Delete 3 subtasks
            for i in range(3):
                subtask_facade.delete_subtask({
                    "task_id": task_id,
                    "subtask_id": subtask_ids[i],
                    "action": "delete"
                })

            # Verify count is 2
            check2 = task_facade.get_task(task_id)["task"]
            assert check2["subtask_count"] == 2, \
                f"Cycle {cycle}: Expected 2 subtasks after deletion"

            # Delete remaining
            for i in range(3, 5):
                subtask_facade.delete_subtask({
                    "task_id": task_id,
                    "subtask_id": subtask_ids[i],
                    "action": "delete"
                })

            # Verify count is 0
            check3 = task_facade.get_task(task_id)["task"]
            assert check3["subtask_count"] == 0, \
                f"Cycle {cycle}: Expected 0 subtasks after all deleted"

        # Final verification
        final = task_facade.get_task(task_id)["task"]
        assert final["subtask_count"] == 0, \
            "Final count should be 0 after all cycles"
        assert final["completed_subtasks"] == 0, \
            "Final completed count should be 0"
