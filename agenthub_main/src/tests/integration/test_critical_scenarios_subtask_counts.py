"""
Critical Scenario Tests: Subtask Count Accuracy

These tests focus on verifying subtask_count and completed_subtasks fields
are accurately computed and returned in ALL scenarios where users reported issues.

Test Strategy:
1. Test with REAL database state (not mocks)
2. Test complete workflows (create → add → update → complete)
3. Test edge cases (0 subtasks, all completed, mixed states)
4. Verify counts match between backend calculation and actual DB state

Reference: Task 51155169 - Phase 3 Investigation
User reported: Badge counts incorrect, subtask_count/completed_subtasks missing or wrong
"""

import pytest
from typing import Dict, Any

from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.application.use_cases.update_subtask import UpdateSubtaskUseCase
from fastmcp.task_management.application.use_cases.get_task import GetTaskUseCase
from fastmcp.task_management.application.dtos.task import CreateTaskRequest
from fastmcp.task_management.application.dtos.subtask import AddSubtaskRequest, UpdateSubtaskRequest


@pytest.fixture
def task_repository(shared_test_db, user_id):
    """Create real task repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    return ORMTaskRepository(user_id=user_id)


@pytest.fixture
def subtask_repository(shared_test_db, user_id):
    """Create real subtask repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
    return ORMSubtaskRepository(user_id=user_id)


@pytest.fixture
def git_branch_repository(shared_test_db, user_id):
    """Create real git branch repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
    return ORMGitBranchRepository(user_id=user_id)


@pytest.fixture
def create_task_use_case(task_repository):
    """Create CreateTaskUseCase with real repositories."""
    return CreateTaskUseCase(task_repository=task_repository)


@pytest.fixture
def add_subtask_use_case(task_repository, subtask_repository):
    """Create AddSubtaskUseCase with real repositories."""
    return AddSubtaskUseCase(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.fixture
def update_subtask_use_case(task_repository, subtask_repository):
    """Create UpdateSubtaskUseCase with real repositories."""
    return UpdateSubtaskUseCase(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.fixture
def get_task_use_case(task_repository, git_branch_repository):
    """Create GetTaskUseCase with real repositories."""
    return GetTaskUseCase(
        task_repository=task_repository,
        git_branch_repository=git_branch_repository
    )


class TestSubtaskCountAccuracy:
    """Test subtask_count and completed_subtasks accuracy in various scenarios"""

    def test_new_task_has_zero_subtasks(
        self,
        create_task_use_case: CreateTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Create new task without subtasks
        EXPECTED: subtask_count=0, completed_subtasks=0
        USER IMPACT: Badge should show nothing or "0"
        """
        # Create task without subtasks
        request = CreateTaskRequest(
            title="Task without subtasks",
            description="Testing zero subtask scenario",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        result = create_task_use_case.execute(request)
        task = result.task if hasattr(result, 'task') else result

        # CRITICAL: These fields must exist and be zero
        assert hasattr(task, 'subtask_count'), "subtask_count field MUST exist"
        assert hasattr(task, 'completed_subtasks'), "completed_subtasks field MUST exist"
        assert task.subtask_count == 0, f"Expected 0 subtasks, got {task.subtask_count}"
        assert task.completed_subtasks == 0, f"Expected 0 completed, got {task.completed_subtasks}"
        assert isinstance(task.subtasks, list), "subtasks must be list (not None)"
        assert len(task.subtasks) == 0, "subtasks array should be empty"

    def test_task_with_five_subtasks_shows_correct_count(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Create parent task → Add 5 subtasks → Verify count is 5
        EXPECTED: subtask_count=5, completed_subtasks=0
        USER REPORT: Previously reported badge count incorrect
        """
        # Create parent task
        parent_request = CreateTaskRequest(
            title="Parent task with subtasks",
            description="Testing subtask counting",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Add exactly 5 subtasks
        subtask_ids = []
        for i in range(5):
            subtask_request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                description=f"Testing subtask {i+1}",
                user_id=user_id,
            )
            subtask_result = add_subtask_use_case.execute(subtask_request)
            subtask = subtask_result.subtask if hasattr(subtask_result, 'subtask') else subtask_result
            subtask_ids.append(subtask.id)

        # Retrieve parent task with fresh data
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        fresh_task_result = get_task_use_case.execute(get_request)
        fresh_task = fresh_task_result.task if hasattr(fresh_task_result, 'task') else fresh_task_result

        # CRITICAL CHECKS
        assert fresh_task.subtask_count == 5, (
            f"Expected subtask_count=5, got {fresh_task.subtask_count}. "
            f"User sees incorrect badge count!"
        )
        assert fresh_task.completed_subtasks == 0, (
            f"Expected completed_subtasks=0, got {fresh_task.completed_subtasks}"
        )
        assert len(fresh_task.subtasks) == 5, (
            f"Expected 5 items in subtasks array, got {len(fresh_task.subtasks)}"
        )
        # Verify subtask_count matches array length
        assert fresh_task.subtask_count == len(fresh_task.subtasks), (
            f"subtask_count ({fresh_task.subtask_count}) MUST match "
            f"len(subtasks) ({len(fresh_task.subtasks)})"
        )

    def test_deleting_subtasks_updates_count_correctly(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        subtask_repository,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Create 5 subtasks → Delete 2 → Verify count is 3
        EXPECTED: subtask_count=3, completed_subtasks=0
        USER IMPACT: Badge should update when subtasks deleted
        """
        # Create parent with 5 subtasks
        parent_request = CreateTaskRequest(
            title="Parent for deletion test",
            description="Testing subtask deletion counting",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Add 5 subtasks
        subtask_ids = []
        for i in range(5):
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                description=f"Will delete some",
                user_id=user_id,
            )
            result = add_subtask_use_case.execute(request)
            subtask = result.subtask if hasattr(result, 'subtask') else result
            subtask_ids.append(subtask.id)

        # Delete 2 subtasks
        subtask_repository.delete(subtask_ids[0])
        subtask_repository.delete(subtask_ids[1])

        # Get fresh task data
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        fresh_result = get_task_use_case.execute(get_request)
        fresh_task = fresh_result.task if hasattr(fresh_result, 'task') else fresh_result

        # CRITICAL: Count should be 3 (5 - 2 deleted)
        assert fresh_task.subtask_count == 3, (
            f"After deleting 2 subtasks, count should be 3, got {fresh_task.subtask_count}"
        )
        assert len(fresh_task.subtasks) == 3, (
            f"Subtasks array should have 3 items, got {len(fresh_task.subtasks)}"
        )

    def test_completing_subtasks_updates_completed_count(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        update_subtask_use_case: UpdateSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Create 5 subtasks → Complete 2 → Verify completed_subtasks=2
        EXPECTED: subtask_count=5, completed_subtasks=2
        USER IMPACT: Progress bar and badge should reflect completion
        """
        # Create parent
        parent_request = CreateTaskRequest(
            title="Parent for completion test",
            description="Testing completed subtask counting",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Add 5 subtasks
        subtask_ids = []
        for i in range(5):
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                description=f"Will complete some",
                user_id=user_id,
            )
            result = add_subtask_use_case.execute(request)
            subtask = result.subtask if hasattr(result, 'subtask') else result
            subtask_ids.append(subtask.id)

        # Complete 2 subtasks
        for i in range(2):
            update_request = UpdateSubtaskRequest(
                task_id=parent_id,
                subtask_id=subtask_ids[i],
                status="done",
                user_id=user_id,
            )
            update_subtask_use_case.execute(update_request)

        # Get fresh task data
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        fresh_result = get_task_use_case.execute(get_request)
        fresh_task = fresh_result.task if hasattr(fresh_result, 'task') else fresh_result

        # CRITICAL CHECKS
        assert fresh_task.subtask_count == 5, (
            f"Total subtasks should be 5, got {fresh_task.subtask_count}"
        )
        assert fresh_task.completed_subtasks == 2, (
            f"Completed subtasks should be 2, got {fresh_task.completed_subtasks}. "
            f"Frontend progress bar will be incorrect!"
        )
        # Progress should reflect completion
        expected_progress = (2 / 5) * 100  # 40%
        assert fresh_task.completed_subtasks <= fresh_task.subtask_count, (
            "completed_subtasks cannot exceed subtask_count"
        )

    def test_all_subtasks_completed_shows_full_count(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        update_subtask_use_case: UpdateSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Create 3 subtasks → Complete all → Verify completed_subtasks=3
        EXPECTED: subtask_count=3, completed_subtasks=3 (100% complete)
        USER IMPACT: Task should show as fully complete
        """
        # Create parent
        parent_request = CreateTaskRequest(
            title="Parent for full completion test",
            description="Testing all subtasks completed",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Add 3 subtasks
        subtask_ids = []
        for i in range(3):
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                description=f"Will complete all",
                user_id=user_id,
            )
            result = add_subtask_use_case.execute(request)
            subtask = result.subtask if hasattr(result, 'subtask') else result
            subtask_ids.append(subtask.id)

        # Complete ALL subtasks
        for subtask_id in subtask_ids:
            update_request = UpdateSubtaskRequest(
                task_id=parent_id,
                subtask_id=subtask_id,
                status="done",
                user_id=user_id,
            )
            update_subtask_use_case.execute(update_request)

        # Get fresh task data
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        fresh_result = get_task_use_case.execute(get_request)
        fresh_task = fresh_result.task if hasattr(fresh_result, 'task') else fresh_result

        # CRITICAL: Should show 100% completion
        assert fresh_task.subtask_count == 3
        assert fresh_task.completed_subtasks == 3, (
            f"All 3 subtasks completed, should show completed_subtasks=3, "
            f"got {fresh_task.completed_subtasks}"
        )
        assert fresh_task.completed_subtasks == fresh_task.subtask_count, (
            "When all subtasks done, completed should equal total"
        )

    def test_mixed_subtask_states_counts_only_done(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        update_subtask_use_case: UpdateSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: 5 subtasks with mixed states (todo, in_progress, done)
        EXPECTED: Only 'done' status counts as completed
        USER IMPACT: Progress calculation must be accurate
        """
        # Create parent
        parent_request = CreateTaskRequest(
            title="Parent with mixed subtask states",
            description="Testing mixed status counting",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Add 5 subtasks with different statuses
        subtask_statuses = ["todo", "todo", "in_progress", "done", "done"]
        subtask_ids = []

        for i, status in enumerate(subtask_statuses):
            # Add subtask
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1} - {status}",
                description=f"Testing status {status}",
                user_id=user_id,
            )
            result = add_subtask_use_case.execute(request)
            subtask = result.subtask if hasattr(result, 'subtask') else result
            subtask_ids.append(subtask.id)

            # Set status
            if status != "todo":  # todo is default
                update_request = UpdateSubtaskRequest(
                    task_id=parent_id,
                    subtask_id=subtask.id,
                    status=status,
                    user_id=user_id,
                )
                update_subtask_use_case.execute(update_request)

        # Get fresh task data
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        fresh_result = get_task_use_case.execute(get_request)
        fresh_task = fresh_result.task if hasattr(fresh_result, 'task') else fresh_result

        # CRITICAL: Only 'done' status should count (2 out of 5)
        assert fresh_task.subtask_count == 5
        assert fresh_task.completed_subtasks == 2, (
            f"Expected 2 completed (done status), got {fresh_task.completed_subtasks}. "
            f"Statuses: {subtask_statuses}"
        )


class TestSubtaskCountEdgeCases:
    """Test edge cases that users might encounter"""

    def test_rapid_subtask_addition_maintains_count_accuracy(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Rapidly add 10 subtasks in sequence
        EXPECTED: Count accurate despite rapid operations
        USER IMPACT: No count drift during active task management
        """
        # Create parent
        parent_request = CreateTaskRequest(
            title="Parent for rapid addition test",
            description="Testing count accuracy under rapid operations",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        # Rapidly add 10 subtasks
        for i in range(10):
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Rapid subtask {i+1}",
                description="Testing rapid addition",
                user_id=user_id,
            )
            add_subtask_use_case.execute(request)

        # Verify count
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
        result = get_task_use_case.execute(get_request)
        task = result.task if hasattr(result, 'task') else result

        assert task.subtask_count == 10, (
            f"After rapid addition of 10 subtasks, count should be 10, got {task.subtask_count}"
        )

    def test_subtask_counts_persist_across_multiple_retrievals(
        self,
        create_task_use_case: CreateTaskUseCase,
        add_subtask_use_case: AddSubtaskUseCase,
        get_task_use_case: GetTaskUseCase,
        user_id: str,
        git_branch_id: str,
    ):
        """
        SCENARIO: Add subtasks, retrieve multiple times, verify consistency
        EXPECTED: Same counts on every retrieval
        USER IMPACT: Frontend sees consistent data on refresh
        """
        # Create parent with 3 subtasks
        parent_request = CreateTaskRequest(
            title="Parent for persistence test",
            description="Testing count persistence",
            git_branch_id=git_branch_id,
            user_id=user_id,
            assignees=["@test-orchestrator-agent"],
        )
        parent_result = create_task_use_case.execute(parent_request)
        parent_task = parent_result.task if hasattr(parent_result, 'task') else parent_result
        parent_id = parent_task.id

        for i in range(3):
            request = AddSubtaskRequest(
                task_id=parent_id,
                title=f"Subtask {i+1}",
                description="Testing persistence",
                user_id=user_id,
            )
            add_subtask_use_case.execute(request)

        # Retrieve 5 times and verify consistency
        from fastmcp.task_management.application.dtos.task import GetTaskRequest
        counts = []
        for _ in range(5):
            get_request = GetTaskRequest(task_id=parent_id, user_id=user_id)
            result = get_task_use_case.execute(get_request)
            task = result.task if hasattr(result, 'task') else result
            counts.append((task.subtask_count, task.completed_subtasks))

        # All retrievals should return same counts
        assert all(count == (3, 0) for count in counts), (
            f"Counts should be consistent across retrievals: {counts}"
        )
