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

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.application.dtos.subtask.create_subtask_request import CreateSubtaskRequest
from fastmcp.task_management.infrastructure.repositories.sqlalchemy_task_repository import SQLAlchemyTaskRepository
from fastmcp.task_management.infrastructure.repositories.sqlalchemy_subtask_repository import SQLAlchemySubtaskRepository
from fastmcp.task_management.infrastructure.database.database_config import get_db_config


@pytest.fixture
def db_config():
    """Get database configuration."""
    return get_db_config()


@pytest.fixture
def task_repository(db_config):
    """Create real task repository."""
    return SQLAlchemyTaskRepository(db_config)


@pytest.fixture
def subtask_repository(db_config):
    """Create real subtask repository."""
    return SQLAlchemySubtaskRepository(db_config)


@pytest.fixture
def task_facade(task_repository):
    """Create task facade."""
    return TaskApplicationFacade(task_repository=task_repository)


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
        self, task_facade, invalid_git_branch_id
    ):
        """
        Verify foreign key constraint prevents creating task with non-existent branch.

        This catches bugs where:
        - Foreign key constraints not properly set up
        - Invalid references slip through validation
        """
        # Try to create task with non-existent branch
        with pytest.raises(Exception) as exc_info:
            task_facade.create_task(CreateTaskRequest(
                git_branch_id=invalid_git_branch_id,
                title="Invalid branch task",
                assignees=["@test-agent"]
            ))

        # Should fail due to foreign key constraint
        error_message = str(exc_info.value).lower()
        assert "foreign key" in error_message or "constraint" in error_message or "violates" in error_message, \
            "Should enforce foreign key constraint for git_branch_id"

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
        self, task_facade, subtask_facade, test_project_data, db_config
    ):
        """
        Verify ON DELETE CASCADE works for task → subtasks relationship.
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create parent with subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Parent to test cascade",
            assignees=["@test-agent"]
        ))
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
        self, task_facade, subtask_facade, test_project_data, db_config
    ):
        """
        Verify counts in application layer match actual database counts.

        This catches bugs where:
        - Cached counts get stale
        - Count updates don't persist to database
        - Application and database state diverge
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create task with 5 subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Count consistency test",
            assignees=["@test-agent"]
        ))
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


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.concurrency
class TestConcurrentOperations:
    """Test system behavior under concurrent modifications."""

    def test_concurrent_subtask_creation_maintains_accurate_count(
        self, task_facade, subtask_facade, test_project_data, db_config
    ):
        """
        Verify parent subtask_count is accurate when multiple subtasks created concurrently.

        This catches race conditions in count updates.
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create parent
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent creation test",
            assignees=["@test-agent"]
        ))
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
        self, task_facade, subtask_facade, test_project_data
    ):
        """
        Verify completed_subtasks count is accurate when multiple subtasks completed concurrently.
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create parent with 10 subtasks
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent completion test",
            assignees=["@test-agent"]
        ))
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
        self, task_facade, test_project_data
    ):
        """
        Verify concurrent updates to same task don't corrupt data.

        This tests transaction isolation and locking.
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create task
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Concurrent update test",
            status="todo",
            priority="low",
            assignees=["@test-agent"]
        ))
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
        self, task_facade, subtask_facade, test_project_data
    ):
        """
        Verify rapid add/delete operations maintain count consistency.

        This stresses the cascade update mechanisms.
        """
        git_branch_id = test_project_data['git_branch_id']

        # Create parent
        parent = task_facade.create_task(CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Rapid operations test",
            assignees=["@test-agent"]
        ))
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
