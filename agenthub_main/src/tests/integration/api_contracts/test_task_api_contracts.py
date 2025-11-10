"""
Backend API Contract Tests - Task Management Endpoints

TDD Approach: These tests document the expected API contract between backend and frontend.
Tests are based on comparison matrix analysis and will initially FAIL for known mismatches.

Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md

Known Mismatches (Tests WILL FAIL):
1. project_id missing from backend response
2. subtask_count missing from backend response
3. completed_subtasks missing from backend response
4. Field naming inconsistencies (estimatedEffort vs estimated_effort)
5. Field naming inconsistencies (dueDate vs due_date)

Tests SHOULD PASS:
- Core fields: id, title, description, status, priority
- Arrays: assignees, labels
- Timestamps: created_at, updated_at (ISO 8601)
- Progress: progress_percentage
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.subtask import AddSubtaskRequest
from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest,
    TaskResponse,
)
from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase

# Note: user_id, project_id, and git_branch_id fixtures are provided by conftest.py
# These fixtures create actual database records with valid IDs, not random UUIDs
# The conftest.py _initialize_test_database_with_basic_data() creates:
# - project_id: "default_project"
# - git_branch_id: created from UUID and stored in database
# - user_id: "default_id"

@pytest.fixture
def task_repository(shared_test_db, user_id):
    """Create real task repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
        ORMTaskRepository,
    )
    return ORMTaskRepository(session=None, user_id=user_id)


@pytest.fixture
def subtask_repository(shared_test_db, user_id):
    """Create real subtask repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import (
        ORMSubtaskRepository,
    )
    return ORMSubtaskRepository(session=None, user_id=user_id)


@pytest.fixture
def git_branch_repository(shared_test_db, user_id):
    """Create real git branch repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import (
        ORMGitBranchRepository,
    )
    return ORMGitBranchRepository(session=None, user_id=user_id)


@pytest.fixture
def create_task_use_case(task_repository):
    """Create CreateTaskUseCase with real repositories."""
    from fastmcp.task_management.application.use_cases.create_task import (
        CreateTaskUseCase,
    )
    return CreateTaskUseCase(task_repository=task_repository)


@pytest.fixture
def add_subtask_use_case(task_repository, subtask_repository):
    """Create AddSubtaskUseCase with real repositories."""
    from fastmcp.task_management.application.use_cases.add_subtask import (
        AddSubtaskUseCase,
    )
    return AddSubtaskUseCase(
        task_repository=task_repository,
        subtask_repository=subtask_repository
    )


@pytest.fixture
def sample_task(
    create_task_use_case: CreateTaskUseCase,
    user_id: str,
    project_id: str,
    git_branch_id: str,
) -> TaskResponse:
    """Create a sample task for testing API contract."""
    request = CreateTaskRequest(
        title="Sample Task for API Contract Testing",
        description="Test task with multiple fields populated",
        git_branch_id=git_branch_id,
        user_id=user_id,
        assignees=["@coding-agent", "@test-orchestrator-agent"],
        priority="high",
        labels=["api-contract", "testing"],
        estimated_effort="2 hours",
        due_date="2025-12-31",
    )
    result = create_task_use_case.execute(request)
    return result.task if hasattr(result, 'task') else result


@pytest.fixture
def task_with_subtasks(
    sample_task: TaskResponse,
    add_subtask_use_case: AddSubtaskUseCase,
    user_id: str,
) -> TaskResponse:
    """Create a task with multiple subtasks for count testing."""
    # Create 3 subtasks
    for i in range(3):
        request = AddSubtaskRequest(
            task_id=sample_task.id,
            title=f"Subtask {i+1}",
            description=f"Test subtask {i+1}",
            user_id=user_id,
        )
        add_subtask_use_case.execute(request)

    # Return refreshed task (in real scenario would re-fetch)
    return sample_task


class TestTaskAPIContractBasicFields:
    """Test basic fields that SHOULD PASS - these are confirmed working."""

    def test_task_has_required_id_field(self, sample_task: TaskResponse):
        """
        Verify task response includes UUID id field.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "id"), "Task must have 'id' field"
        assert isinstance(sample_task.id, str), "Task id must be string"
        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(sample_task.id)  # Will raise ValueError if invalid
        except ValueError:
            pytest.fail(f"Task id '{sample_task.id}' is not a valid UUID")

    def test_task_has_required_title_field(self, sample_task: TaskResponse):
        """
        Verify task response includes title field.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "title"), "Task must have 'title' field"
        assert isinstance(sample_task.title, str), "Task title must be string"
        assert len(sample_task.title) > 0, "Task title must not be empty"

    def test_task_has_status_field(self, sample_task: TaskResponse):
        """
        Verify task response includes status field with valid value.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "status"), "Task must have 'status' field"
        assert isinstance(sample_task.status, str), "Task status must be string"
        valid_statuses = ["todo", "in_progress", "done", "blocked", "cancelled"]
        assert sample_task.status in valid_statuses, (
            f"Task status '{sample_task.status}' must be one of {valid_statuses}"
        )

    def test_task_has_priority_field(self, sample_task: TaskResponse):
        """
        Verify task response includes priority field with valid value.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "priority"), "Task must have 'priority' field"
        assert isinstance(sample_task.priority, str), "Task priority must be string"
        valid_priorities = ["low", "medium", "high", "urgent", "critical"]
        assert sample_task.priority in valid_priorities, (
            f"Task priority '{sample_task.priority}' must be one of {valid_priorities}"
        )

    def test_task_has_assignees_array(self, sample_task: TaskResponse):
        """
        Verify task response includes assignees as string array.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "assignees"), "Task must have 'assignees' field"
        assert isinstance(sample_task.assignees, list), "Task assignees must be array"
        for assignee in sample_task.assignees:
            assert isinstance(assignee, str), "Each assignee must be string"

    def test_task_has_labels_array(self, sample_task: TaskResponse):
        """
        Verify task response includes labels as string array.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "labels"), "Task must have 'labels' field"
        assert isinstance(sample_task.labels, list), "Task labels must be array"
        for label in sample_task.labels:
            assert isinstance(label, str), "Each label must be string"

    def test_task_has_progress_percentage(self, sample_task: TaskResponse):
        """
        Verify task response includes progress_percentage as integer.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.
        """
        assert hasattr(sample_task, "progress_percentage"), (
            "Task must have 'progress_percentage' field"
        )
        assert isinstance(sample_task.progress_percentage, int), (
            "Task progress_percentage must be integer"
        )
        assert 0 <= sample_task.progress_percentage <= 100, (
            f"Task progress_percentage must be 0-100, got {sample_task.progress_percentage}"
        )


class TestTaskAPIContractTimestamps:
    """Test timestamp fields that SHOULD PASS - ISO 8601 format."""

    def test_task_created_at_is_iso8601_string(self, sample_task: TaskResponse):
        """
        Verify created_at is ISO 8601 formatted timestamp string.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.

        Frontend expects: created_at?: string
        Backend returns: created_at: datetime | None → serialized as ISO string
        """
        assert hasattr(sample_task, "created_at"), "Task must have 'created_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_task.created_at, datetime):
            # If it's a datetime object, verify it can be serialized to ISO format
            iso_string = sample_task.created_at.isoformat()
            assert "T" in iso_string, "created_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_task.created_at, str):
            # If it's already a string, verify ISO 8601 format
            assert "T" in sample_task.created_at, "created_at must be ISO 8601 format (contains 'T')"
            # Try to parse it to verify it's valid
            try:
                datetime.fromisoformat(sample_task.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(f"created_at '{sample_task.created_at}' is not valid ISO 8601 format")
        else:
            pytest.fail(f"created_at must be datetime or string, got {type(sample_task.created_at)}")

    def test_task_updated_at_is_iso8601_string(self, sample_task: TaskResponse):
        """
        Verify updated_at is ISO 8601 formatted timestamp string.
        Status: ✅ SHOULD PASS - Confirmed match in comparison matrix.

        Frontend expects: updated_at?: string
        Backend returns: updated_at: datetime | None → serialized as ISO string
        """
        assert hasattr(sample_task, "updated_at"), "Task must have 'updated_at' field"

        # Handle both datetime objects and string representations
        if isinstance(sample_task.updated_at, datetime):
            # If it's a datetime object, verify it can be serialized to ISO format
            iso_string = sample_task.updated_at.isoformat()
            assert "T" in iso_string, "updated_at datetime must serialize to ISO 8601 format"
        elif isinstance(sample_task.updated_at, str):
            # If it's already a string, verify ISO 8601 format
            assert "T" in sample_task.updated_at, "updated_at must be ISO 8601 format (contains 'T')"
            # Try to parse it to verify it's valid
            try:
                datetime.fromisoformat(sample_task.updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(f"updated_at '{sample_task.updated_at}' is not valid ISO 8601 format")
        else:
            pytest.fail(f"updated_at must be datetime or string, got {type(sample_task.updated_at)}")


class TestTaskAPIContractAssigneeFormat:
    """Test assignee @ prefix that SHOULD PASS."""

    def test_task_assignees_have_at_prefix(self, sample_task: TaskResponse):
        """
        Verify all assignees have @ prefix consistently.
        Status: ✅ SHOULD PASS - Confirmed requirement from comparison matrix.

        Frontend expects: assignees with @ prefix (e.g., "@coding-agent")
        Backend should return: Same format consistently
        """
        assert hasattr(sample_task, "assignees"), "Task must have 'assignees' field"
        assert len(sample_task.assignees) > 0, "Sample task should have assignees"

        for assignee in sample_task.assignees:
            assert assignee.startswith("@"), (
                f"Assignee '{assignee}' must start with @ prefix"
            )


class TestTaskAPIContractMissingFields:
    """
    Test fields that WILL FAIL - documented mismatches from comparison matrix.
    These tests document what the backend SHOULD return but currently doesn't.
    """

    @pytest.mark.xfail(reason="MISMATCH #1: project_id not returned by backend (see comparison matrix)")
    def test_task_has_project_id_field(self, sample_task: TaskResponse):
        """
        Verify task response includes project_id field.
        Status: ❌ WILL FAIL - Backend doesn't return project_id.

        Frontend expects: project_id: string (required)
        Backend returns: Only git_branch_id

        Impact: Frontend cannot filter/group tasks by project without additional query.
        Fix required: Add project_id to TaskResponse DTO.

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-1
        """
        assert hasattr(sample_task, "project_id"), (
            "Task MUST have 'project_id' field for frontend to filter by project"
        )
        assert isinstance(sample_task.project_id, str), "Task project_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(sample_task.project_id)
        except ValueError:
            pytest.fail(f"Task project_id '{sample_task.project_id}' is not a valid UUID")

    @pytest.mark.xfail(reason="MISMATCH #2: subtask_count not returned by backend (see comparison matrix)")
    def test_task_has_subtask_count_field(self, task_with_subtasks: TaskResponse):
        """
        Verify task response includes computed subtask_count field.
        Status: ❌ WILL FAIL - Backend returns full subtasks array, not count.

        Frontend expects: subtask_count: number
        Backend returns: subtasks: list[dict[str, Any]] (full array)

        Impact: Frontend must count array length (inefficient, especially for large lists).
        Fix required: Add computed subtask_count field to TaskResponse.

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-2
        """
        assert hasattr(task_with_subtasks, "subtask_count"), (
            "Task MUST have 'subtask_count' field for efficient frontend display"
        )
        assert isinstance(task_with_subtasks.subtask_count, int), (
            "Task subtask_count must be integer"
        )
        # Verify count matches actual subtasks
        if hasattr(task_with_subtasks, "subtasks") and task_with_subtasks.subtasks:
            assert task_with_subtasks.subtask_count == len(task_with_subtasks.subtasks), (
                f"subtask_count ({task_with_subtasks.subtask_count}) must match "
                f"actual subtasks length ({len(task_with_subtasks.subtasks)})"
            )

    @pytest.mark.xfail(reason="MISMATCH #3: completed_subtasks not returned by backend (see comparison matrix)")
    def test_task_has_completed_subtasks_field(self, task_with_subtasks: TaskResponse):
        """
        Verify task response includes computed completed_subtasks field.
        Status: ❌ WILL FAIL - Backend doesn't compute completed count.

        Frontend expects: completed_subtasks: number
        Backend returns: Only full subtasks array

        Impact: Frontend must iterate and count status='done' (inefficient).
        Fix required: Add computed completed_subtasks field to TaskResponse.

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-3
        """
        assert hasattr(task_with_subtasks, "completed_subtasks"), (
            "Task MUST have 'completed_subtasks' field for progress tracking"
        )
        assert isinstance(task_with_subtasks.completed_subtasks, int), (
            "Task completed_subtasks must be integer"
        )
        assert 0 <= task_with_subtasks.completed_subtasks <= task_with_subtasks.subtask_count, (
            f"completed_subtasks ({task_with_subtasks.completed_subtasks}) must be "
            f"between 0 and subtask_count ({task_with_subtasks.subtask_count})"
        )


class TestTaskAPIContractFieldNaming:
    """
    Test field naming conventions that WILL FAIL.
    Backend uses camelCase in JSON but snake_case in Python types.
    """

    @pytest.mark.xfail(reason="MISMATCH #4: Field naming inconsistency (see comparison matrix)")
    def test_task_uses_snake_case_for_estimated_effort(self, sample_task: TaskResponse):
        """
        Verify estimated_effort field uses snake_case naming consistently.
        Status: ❌ WILL FAIL - Backend serializes as 'estimatedEffort' (camelCase).

        Backend Python: estimated_effort (snake_case)
        Backend JSON: estimatedEffort (camelCase via to_dict())
        Frontend TypeScript: estimated_effort (snake_case)

        Impact: Inconsistent API contract - frontend expects snake_case.
        Fix options:
        1. Change backend to_dict() to use snake_case (preferred for Python API)
        2. Change frontend to use camelCase (matches backend JSON)

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-5
        """
        # Serialize to dict to check JSON field names
        task_dict = sample_task.to_dict() if hasattr(sample_task, "to_dict") else sample_task.__dict__

        # Should use snake_case for Python/TypeScript consistency
        assert "estimated_effort" in task_dict, (
            "Task JSON should use 'estimated_effort' (snake_case), not 'estimatedEffort'"
        )
        assert "estimatedEffort" not in task_dict, (
            "Task JSON should NOT use 'estimatedEffort' (camelCase)"
        )

    @pytest.mark.xfail(reason="MISMATCH #5: Field naming inconsistency (see comparison matrix)")
    def test_task_uses_snake_case_for_due_date(self, sample_task: TaskResponse):
        """
        Verify due_date field uses snake_case naming consistently.
        Status: ❌ WILL FAIL - Backend serializes as 'dueDate' (camelCase).

        Backend Python: due_date (snake_case)
        Backend JSON: dueDate (camelCase via to_dict())
        Frontend TypeScript: due_date (snake_case)

        Impact: Inconsistent API contract - frontend expects snake_case.
        Fix options:
        1. Change backend to_dict() to use snake_case (preferred)
        2. Change frontend to use camelCase

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-6
        """
        # Serialize to dict to check JSON field names
        task_dict = sample_task.to_dict() if hasattr(sample_task, "to_dict") else sample_task.__dict__

        # Should use snake_case for Python/TypeScript consistency
        assert "due_date" in task_dict, (
            "Task JSON should use 'due_date' (snake_case), not 'dueDate'"
        )
        assert "dueDate" not in task_dict, (
            "Task JSON should NOT use 'dueDate' (camelCase)"
        )


class TestTaskAPIContractOptionalFields:
    """Test optional fields that should be present when populated."""

    def test_task_has_description_when_provided(self, sample_task: TaskResponse):
        """Verify description is included when provided."""
        assert hasattr(sample_task, "description"), "Task must have 'description' field"
        # Description is optional but should be string when present
        if sample_task.description is not None:
            assert isinstance(sample_task.description, str), "Task description must be string"

    def test_task_has_git_branch_id(self, sample_task: TaskResponse):
        """Verify git_branch_id is included (required for task creation)."""
        assert hasattr(sample_task, "git_branch_id"), "Task must have 'git_branch_id' field"
        assert isinstance(sample_task.git_branch_id, str), "Task git_branch_id must be string"

    def test_task_has_context_id_when_context_exists(self, sample_task: TaskResponse):
        """Verify context_id is included when task has context."""
        assert hasattr(sample_task, "context_id"), "Task must have 'context_id' field"
        # context_id is optional but should be string when present
        if sample_task.context_id is not None:
            assert isinstance(sample_task.context_id, str), "Task context_id must be string"


class TestTaskAPIContractCompleteResponse:
    """Test that task response matches complete frontend Task interface."""

    def test_task_response_matches_frontend_task_interface(self, sample_task: TaskResponse):
        """
        Verify task response includes ALL fields expected by frontend Task interface.

        This is a comprehensive test that documents the complete contract.
        Sub-tests above provide detailed failure messages for specific fields.
        """
        required_fields = [
            "id",
            "title",
            "status",
            "priority",
            "git_branch_id",
        ]

        optional_fields = [
            "description",
            "assignees",
            "labels",
            "created_at",
            "updated_at",
            "progress_percentage",
            "estimated_effort",
            "due_date",
            "details",
            "context_id",
            "context_data",
        ]

        # Fields that are currently missing (xfail tests document these)
        expected_but_missing_fields = [
            "project_id",  # MISMATCH #1
            "subtask_count",  # MISMATCH #2
            "completed_subtasks",  # MISMATCH #3
        ]

        # Verify required fields
        for field in required_fields:
            assert hasattr(sample_task, field), f"Task MUST have required field '{field}'"

        # Verify optional fields exist (even if None)
        for field in optional_fields:
            assert hasattr(sample_task, field), f"Task should have optional field '{field}'"

        # Document missing fields (these will cause test to fail until implemented)
        missing_fields = [
            field for field in expected_but_missing_fields
            if not hasattr(sample_task, field)
        ]

        if missing_fields:
            pytest.fail(
                f"Task response missing {len(missing_fields)} expected fields: {missing_fields}\n"
                f"See comparison matrix: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md"
            )
