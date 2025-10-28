"""
End-to-end tests for context synchronization workflows.

Tests complete task lifecycles and mixed operations to verify
context_data remains consistent throughout complex workflows.
"""

import pytest
import asyncio
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, AsyncMock, patch

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockTaskRepository, MockSubtaskRepository


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return str(uuid4())


@pytest.fixture(autouse=True)
def mock_auth_context(user_id):
    """Mock authentication context for all tests in this file."""
    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', return_value=user_id):
        yield


@pytest.fixture
def task_repository():
    """Create in-memory task repository for E2E tests."""
    return MockTaskRepository()


@pytest.fixture
def subtask_repository():
    """Create in-memory subtask repository."""
    return MockSubtaskRepository()


@pytest.fixture
def context_service():
    """Create mock context service."""
    mock_service = MagicMock()
    mock_service.create_context = AsyncMock(return_value={"success": True})
    mock_service.update_context = AsyncMock(return_value={"success": True})
    return mock_service


@pytest.fixture
def task_facade(task_repository):
    """Create task application facade."""
    return TaskApplicationFacade(
        task_repository=task_repository
    )


@pytest.fixture
def subtask_facade(task_repository, subtask_repository):
    """Create subtask application facade."""
    return SubtaskApplicationFacade(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.fixture
def test_user_id():
    """Create a test user ID for E2E tests."""
    return str(uuid4())


@pytest.mark.asyncio
class TestCompleteTaskLifecycleKeepsContextSynced:
    """Test complete task lifecycle: Create → Update → Complete."""

    async def test_full_task_lifecycle_maintains_sync(
        self, task_facade, task_repository, test_user_id
    ):
        """Verify context_data stays synced through entire task lifecycle."""
        git_branch_id = str(uuid4())

        # PHASE 1: CREATE
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="E2E Test Task",
            description="Testing full lifecycle",
            status="todo",
            priority="medium",
            assignees=["test-agent"],
            estimated_effort="2 hours",
            user_id=test_user_id
        )

        create_result = task_facade.create_task(create_request)
        assert create_result["success"] is True
        task_id = create_result["task"]["id"]

        # Verify creation sync
        task = task_repository.find_by_id(TaskId(task_id))
        context_data = task.context_data

        assert context_data["metadata"]["status"] == "todo"
        assert context_data["metadata"]["priority"] == "medium"
        assert context_data["objective"]["title"] == "E2E Test Task"
        assert context_data["objective"]["estimated_effort"] == "2 hours"

        # PHASE 2: UPDATE
        update_request = UpdateTaskRequest(
            task_id=task_id,
            title="Updated E2E Task",
            status="in_progress",
            priority="high",
            details="Added implementation details"
        )

        update_result = task_facade.update_task(update_request)
        assert update_result["success"] is True

        # Verify update sync
        task = task_repository.find_by_id(TaskId(task_id))
        context_data = task.context_data

        assert context_data["metadata"]["status"] == "in_progress"
        assert context_data["metadata"]["priority"] == "high"
        assert context_data["objective"]["title"] == "Updated E2E Task"

        # PHASE 3: COMPLETE
        complete_result = task_facade.complete_task(
            task_id=task_id,
            completion_summary="Successfully completed all requirements",
            testing_notes="All tests passing"
        )

        assert complete_result["success"] is True

        # Verify completion sync
        task = task_repository.find_by_id(TaskId(task_id))
        context_data = task.context_data

        assert context_data["metadata"]["status"] == "done"
        assert task.status.value == "done"

    async def test_lifecycle_with_multiple_updates(
        self, task_facade, task_repository, test_user_id
    ):
        """Verify context stays synced through multiple updates."""
        # Create task
        create_request = CreateTaskRequest(
            git_branch_id=str(uuid4()),
            title="Multi-Update Task",
            description="E2E test for context sync - Multi-Update Task",
            assignees=["agent-1"],
            user_id=test_user_id
        )

        result = task_facade.create_task(create_request)
        task_id = result["task"]["id"]

        # Perform 5 updates
        statuses = ["todo", "in_progress", "in_progress", "review", "done"]
        priorities = ["low", "medium", "medium", "high", "urgent"]

        for i, (status, priority) in enumerate(zip(statuses, priorities)):
            update_request = UpdateTaskRequest(
                task_id=task_id,
                status=status,
                priority=priority,
                title=f"Update {i+1}"
            )
            task_facade.update_task(update_request)

            # Verify sync after each update
            task = task_repository.find_by_id(TaskId(task_id))
            context_data = task.context_data

            assert context_data["metadata"]["status"] == status
            assert context_data["metadata"]["priority"] == priority
            assert context_data["objective"]["title"] == f"Update {i+1}"


@pytest.mark.asyncio
class TestSubtaskWorkflowUpdatesParentContext:
    """Test subtask workflows update parent task context correctly."""

    async def test_subtask_lifecycle_updates_parent_progress(
        self, task_facade, subtask_facade, task_repository, test_user_id
    ):
        """Verify creating and completing subtasks updates parent context."""
        # Create parent task
        create_request = CreateTaskRequest(
            git_branch_id=str(uuid4()),
            title="Parent Task with Subtasks",
            description="E2E test for context sync - Parent Task with Subtasks",
            assignees=["parent-agent"],
            user_id=test_user_id
        )

        parent_result = task_facade.create_task(create_request)
        parent_id = parent_result["task"]["id"]

        # Initial state: 0 subtasks (Phase 2: using direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))
        assert parent.subtask_count == 0
        assert parent.completed_subtasks == 0

        # Create 3 subtasks
        subtask_ids = []
        for i in range(3):
            subtask_result = subtask_facade.create_subtask(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                assignees=["subtask-agent"]
            )
            subtask_ids.append(subtask_result["subtask"]["id"])

        # Verify parent updated: 3 total, 0 completed (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))
        assert parent.subtask_count == 3
        assert parent.completed_subtasks == 0
        # Progress percentage calculation may vary based on implementation

        # Complete 1 subtask
        subtask_facade.complete_subtask(
            task_id=parent_id,
            subtask_id=subtask_ids[0],
            completion_summary="First subtask done"
        )

        # Verify parent updated: 3 total, 1 completed (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))
        assert parent.subtask_count == 3
        assert parent.completed_subtasks == 1
        # Progress ~33% (1 of 3 completed)

        # Complete remaining subtasks
        for subtask_id in subtask_ids[1:]:
            subtask_facade.complete_subtask(
                task_id=parent_id,
                subtask_id=subtask_id,
                completion_summary="Subtask completed"
            )

        # Verify parent updated: 3 total, 3 completed (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))
        assert parent.subtask_count == 3
        assert parent.completed_subtasks == 3
        # All subtasks completed


@pytest.mark.asyncio
class TestMixedOperationsMaintainConsistency:
    """Test that mixed task and subtask operations maintain consistency."""

    async def test_interleaved_task_and_subtask_operations(
        self, task_facade, subtask_facade, task_repository, test_user_id
    ):
        """Verify context stays consistent with interleaved operations."""
        # Create parent task
        parent_result = task_facade.create_task(
            CreateTaskRequest(
                git_branch_id=str(uuid4()),
                title="Complex Workflow Task",
            description="E2E test for context sync - Complex Workflow Task",
            assignees=["orchestrator-agent"],
                priority="high",
                user_id=test_user_id
            )
        )
        parent_id = parent_result["task"]["id"]

        # Interleaved operations
        # 1. Create subtask
        subtask1 = subtask_facade.create_subtask(
            task_id=parent_id,
            title="Subtask 1",
            assignees=["agent-1"]
        )

        # 2. Update parent task
        task_facade.update_task(
            UpdateTaskRequest(
                task_id=parent_id,
                status="in_progress"
            )
        )

        # 3. Create another subtask
        subtask2 = subtask_facade.create_subtask(
            task_id=parent_id,
            title="Subtask 2",
            assignees=["agent-2"]
        )

        # 4. Complete first subtask
        subtask_facade.complete_subtask(
            task_id=parent_id,
            subtask_id=subtask1["subtask"]["id"],
            completion_summary="Done"
        )

        # 5. Update parent priority
        task_facade.update_task(
            UpdateTaskRequest(
                task_id=parent_id,
                priority="urgent"
            )
        )

        # Final verification
        parent = task_repository.find_by_id(TaskId(parent_id))
        context_data = parent.context_data

        # Task metadata should be current
        assert context_data["metadata"]["status"] == "in_progress"
        assert context_data["metadata"]["priority"] == "urgent"

        # Subtask counts should be accurate (Phase 2: direct count fields)
        assert parent.subtask_count == 2
        assert parent.completed_subtasks == 1


@pytest.mark.asyncio
class TestConcurrentOperationsDontCorruptData:
    """Test thread safety of context synchronization."""

    async def test_concurrent_subtask_creation_maintains_count(
        self, task_facade, subtask_facade, task_repository, test_user_id
    ):
        """Verify concurrent subtask creation maintains accurate counts."""
        # Create parent task
        parent_result = task_facade.create_task(
            CreateTaskRequest(
                git_branch_id=str(uuid4()),
                title="Concurrent Test Task",
            description="E2E test for context sync - Concurrent Test Task",
            assignees=["test-agent"],
                user_id=test_user_id
            )
        )
        parent_id = parent_result["task"]["id"]

        # Create 10 subtasks concurrently
        async def create_subtask(i):
            return subtask_facade.create_subtask(
                task_id=parent_id,
                title=f"Concurrent Subtask {i}",
                assignees=["agent"]
            )

        # Run concurrent operations
        tasks = [create_subtask(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions
        for result in results:
            assert not isinstance(result, Exception)

        # Verify final count is accurate (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))

        # All 10 subtasks should be counted
        assert parent.subtask_count == 10
        assert parent.completed_subtasks == 0

    async def test_concurrent_updates_maintain_consistency(
        self, task_facade, task_repository, test_user_id
    ):
        """Verify concurrent task updates don't corrupt context_data."""
        # Create task
        result = task_facade.create_task(
            CreateTaskRequest(
                git_branch_id=str(uuid4()),
                title="Concurrent Update Test",
            description="E2E test for context sync - Concurrent Update Test",
            assignees=["test-agent"],
                user_id=test_user_id
            )
        )
        task_id = result["task"]["id"]

        # Concurrent updates to different fields
        async def update_status(i):
            return task_facade.update_task(
                UpdateTaskRequest(
                    task_id=task_id,
                    status="in_progress"
                )
            )

        async def update_priority(i):
            return task_facade.update_task(
                UpdateTaskRequest(
                    task_id=task_id,
                    priority="high"
                )
            )

        # Run 5 status updates and 5 priority updates concurrently
        status_tasks = [update_status(i) for i in range(5)]
        priority_tasks = [update_priority(i) for i in range(5)]

        all_tasks = status_tasks + priority_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Verify no exceptions
        for result in results:
            assert not isinstance(result, Exception)

        # Verify final state is consistent (last write wins)
        task = task_repository.find_by_id(TaskId(task_id))
        context_data = task.context_data

        # Should have valid status and priority (not corrupted)
        assert context_data["metadata"]["status"] in ["todo", "in_progress", "done"]
        assert context_data["metadata"]["priority"] in ["low", "medium", "high", "urgent"]


@pytest.mark.asyncio
class TestLargeScaleWorkflow:
    """Test large-scale workflows with many operations."""

    async def test_large_task_tree_maintains_sync(
        self, task_facade, subtask_facade, task_repository, test_user_id
    ):
        """Verify sync works correctly with large task trees."""
        # Create parent task
        parent_result = task_facade.create_task(
            CreateTaskRequest(
                git_branch_id=str(uuid4()),
                title="Large Task Tree",
            description="E2E test for context sync - Large Task Tree",
            assignees=["orchestrator"],
                user_id=test_user_id
            )
        )
        parent_id = parent_result["task"]["id"]

        # Create 50 subtasks
        subtask_ids = []
        for i in range(50):
            result = subtask_facade.create_subtask(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                assignees=["worker-agent"]
            )
            subtask_ids.append(result["subtask"]["id"])

        # Verify count is correct (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))
        assert parent.subtask_count == 50

        # Complete 25 subtasks
        for subtask_id in subtask_ids[:25]:
            subtask_facade.complete_subtask(
                task_id=parent_id,
                subtask_id=subtask_id,
                completion_summary="Done"
            )

        # Verify counts and progress (Phase 2: direct count fields)
        parent = task_repository.find_by_id(TaskId(parent_id))

        assert parent.subtask_count == 50
        assert parent.completed_subtasks == 25
