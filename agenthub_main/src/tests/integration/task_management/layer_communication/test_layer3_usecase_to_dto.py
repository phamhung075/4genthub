"""
Layer 3 Tests: Use Case → DTO (Serialization)
==============================================

CRITICAL TEST FILE - Proves root cause of all 4 data loss issues at DTO transformation layer.

This file tests the transformation from Task Entity to TaskResponse DTO.
This is where ALL 4 identified issues originate:
1. project_id is None (not traversed from git_branch_id)
2. subtask_count is None (not computed)
3. completed_subtasks is None (not computed)
4. assignees missing @ prefix (not formatted)

Expected Results:
- 3 tests PASS (basic entity field mapping works)
- 4 tests XFAIL (expected failures that prove the root cause)

Test Strategy:
- All XFAIL tests document the EXACT missing behavior
- Once fixes are implemented, change @pytest.mark.xfail to normal tests
- Tests serve as specification for correct DTO transformation
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.task.task_response import TaskResponse
from fastmcp.task_management.domain.entities.label import Label
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def sample_task_entity():
    """Create a fully populated Task entity for testing"""
    # Create IDs for parent task and subtasks
    parent_task_id = TaskId(str(uuid4()))
    git_branch_id = TaskId(str(uuid4()))

    # Create subtasks with proper parent reference
    subtasks = [
        Subtask(
            id=TaskId(str(uuid4())),
            title="Subtask 1",
            description="First subtask",
            parent_task_id=parent_task_id,
            status=TaskStatus.done(),
            priority=Priority.medium(),
        ),
        Subtask(
            id=TaskId(str(uuid4())),
            title="Subtask 2",
            description="Second subtask",
            parent_task_id=parent_task_id,
            status=TaskStatus.in_progress(),
            priority=Priority.low(),
        ),
        Subtask(
            id=TaskId(str(uuid4())),
            title="Subtask 3",
            description="Third subtask",
            parent_task_id=parent_task_id,
            status=TaskStatus.todo(),
            priority=Priority.high(),
        ),
    ]

    # Create labels (Note: Label entity doesn't have user_id field)
    labels = [
        Label(id=1, name="backend", color="#ff0000"),
        Label(id=2, name="urgent", color="#00ff00"),
    ]

    # Create task entity
    return Task(
        id=parent_task_id,
        title="Test Task",
        description="Test description",
        status=TaskStatus.in_progress(),
        priority=Priority.high(),
        assignees=["coding-agent", "test-orchestrator-agent"],
        labels=labels,
        subtasks=subtasks,
        dependencies=[],
        git_branch_id=git_branch_id,
        estimated_effort="2 hours",
        created_at=datetime(2025, 10, 27, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 10, 27, 12, 0, 0, tzinfo=UTC),
    )


# ============================================================================
# TEST 1: Basic Entity Field Mapping (SHOULD PASS)
# ============================================================================


def test_dto_includes_basic_entity_fields(sample_task_entity):
    """
    Test: TaskResponse DTO includes all basic entity fields

    Expected: PASS

    Validates that basic fields (id, title, status, priority, etc.) are
    correctly mapped from Task entity to TaskResponse DTO.
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: Basic fields are present and correct
    assert dto.id == str(
        sample_task_entity.id
    ), "ID should match (DTO converts TaskId to string)"
    assert dto.title == sample_task_entity.title, "Title should match"
    assert dto.description == sample_task_entity.description, "Description should match"
    assert (
        dto.status == sample_task_entity.status.value
    ), "Status should match (DTO converts TaskStatus to string)"
    assert (
        dto.priority == sample_task_entity.priority.value
    ), "Priority should match (DTO converts Priority to string)"
    assert (
        dto.git_branch_id == sample_task_entity.git_branch_id
    ), "git_branch_id should match"
    assert (
        dto.estimated_effort == sample_task_entity.estimated_effort
    ), "estimated_effort should match"
    # Note: details field is on DTO but not on Task entity - it's populated from context_data


# ============================================================================
# TEST 2: Nested Objects Serialization (SHOULD PASS)
# ============================================================================


def test_dto_serializes_nested_objects_correctly(sample_task_entity):
    """
    Test: Nested objects (labels, subtasks) are serialized correctly

    Expected: PASS

    Validates that complex nested structures (labels with user_id, subtasks
    with their own properties) are properly included in the DTO.
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: Labels are serialized
    assert len(dto.labels) == 2, "Should have 2 labels"
    assert all(
        isinstance(label, Label) for label in dto.labels
    ), "Labels should be Label objects"
    assert all(
        hasattr(label, "name") and label.name for label in dto.labels
    ), "All labels should have name"

    # Assert: Subtasks are serialized
    assert len(dto.subtasks) == 3, "Should have 3 subtasks"
    assert all(
        isinstance(subtask, Subtask) for subtask in dto.subtasks
    ), "Subtasks should be Subtask objects"


# ============================================================================
# TEST 3: Datetime Field Formatting (SHOULD PASS)
# ============================================================================


def test_dto_formats_datetime_fields_correctly(sample_task_entity):
    """
    Test: Datetime fields are properly formatted in DTO

    Expected: PASS

    Validates that datetime fields maintain timezone information and are
    ready for ISO 8601 serialization.
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: Datetime fields are present
    assert dto.created_at is not None, "created_at should be present"
    assert dto.updated_at is not None, "updated_at should be present"

    # Assert: Datetime objects maintain timezone info
    assert dto.created_at.tzinfo is not None, "created_at should have timezone"
    assert dto.updated_at.tzinfo is not None, "updated_at should have timezone"

    # Assert: Datetime values match entity
    assert dto.created_at == sample_task_entity.created_at, "created_at should match"
    assert dto.updated_at == sample_task_entity.updated_at, "updated_at should match"


# ============================================================================
# TEST 4: project_id Traversal from git_branch_id (EXPECTED FAILURE)
# ============================================================================


@pytest.mark.xfail(
    reason="TaskResponse.from_domain() does not traverse git_branch relationship to fetch project_id",
    strict=True,
)
def test_dto_includes_project_id_from_git_branch_relationship(sample_task_entity):
    """
    Test: project_id is computed from git_branch_id relationship

    Expected: XFAIL (documents missing functionality)

    ROOT CAUSE PROOF #1:
    - Task entity has git_branch_id
    - GitBranch entity has project_id
    - TaskResponse.from_domain() does NOT traverse this relationship
    - Result: project_id is always None in API responses

    Fix Required:
    In TaskResponse.from_domain(), add:
        if task.git_branch_id and git_branch_repository:
            git_branch = git_branch_repository.get_by_id(task.git_branch_id)
            if git_branch:
                project_id = git_branch.project_id
    """
    # Arrange: Simulate git_branch with project_id
    # (In real implementation, would mock git_branch_repository)
    str(uuid4())

    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: project_id should be present (WILL FAIL)
    assert (
        dto.project_id is not None
    ), "project_id should be computed from git_branch_id relationship"

    # This assertion would pass after fix:
    # assert dto.project_id == expected_project_id


# ============================================================================
# TEST 5: subtask_count Computation (EXPECTED FAILURE)
# ============================================================================


def test_dto_computes_subtask_count_from_subtasks_array(sample_task_entity):
    """
    Test: subtask_count is computed from subtasks array length

    Expected: PASS

    Validates that TaskResponse.from_domain() correctly computes subtask_count.
    - Task entity has subtasks array with 3 items
    - TaskResponse.from_domain() computes subtask_count from array length
    - Result: subtask_count = 3
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: subtask_count should equal length of subtasks array
    assert (
        dto.subtask_count is not None
    ), "subtask_count should be computed from subtasks array"
    assert dto.subtask_count == 3, f"Expected subtask_count=3, got {dto.subtask_count}"


# ============================================================================
# TEST 6: completed_subtasks Computation (EXPECTED FAILURE)
# ============================================================================


@pytest.mark.xfail(
    reason="TaskResponse.from_domain() does not compute completed_subtasks from subtask statuses",
    strict=True,
)
def test_dto_computes_completed_subtasks_from_subtask_statuses(sample_task_entity):
    """
    Test: completed_subtasks is computed from subtask statuses

    Expected: XFAIL (documents missing functionality)

    ROOT CAUSE PROOF #3:
    - Task entity has 3 subtasks: 1 done, 1 in_progress, 1 todo
    - TaskResponse.from_domain() does NOT count completed subtasks
    - Result: completed_subtasks is always None in API responses

    Fix Required:
    In TaskResponse.from_domain(), add:
        completed_subtasks=len([s for s in task.subtasks if s.status == "done"]) if task.subtasks else 0
    """
    # Arrange: sample_task_entity has 1 completed subtask
    expected_completed = 1

    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: completed_subtasks should be computed (WILL FAIL)
    assert (
        dto.completed_subtasks is not None
    ), "completed_subtasks should be computed from subtask statuses"
    assert (
        dto.completed_subtasks == expected_completed
    ), f"Expected completed_subtasks={expected_completed}, got {dto.completed_subtasks}"


# ============================================================================
# TEST 7: Assignee @ Prefix Formatting (EXPECTED FAILURE)
# ============================================================================


def test_dto_adds_prefix_to_assignees(sample_task_entity):
    """
    Test: Assignees have @ prefix in DTO

    Expected: PASS

    Validates that TaskResponse.from_domain() correctly adds @ prefix to assignees.
    - Task entity has assignees: ["coding-agent", "test-orchestrator-agent"]
    - TaskResponse.from_domain() adds @ prefix
    - Result: Frontend receives assignees with @ prefix: ["@coding-agent", "@test-orchestrator-agent"]
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert: All assignees should have @ prefix
    assert all(
        assignee.startswith("@") for assignee in dto.assignees
    ), f"All assignees should have @ prefix. Got: {dto.assignees}"

    # Verify expected values after fix:
    expected_assignees = ["@coding-agent", "@test-orchestrator-agent"]
    assert (
        dto.assignees == expected_assignees
    ), f"Expected {expected_assignees}, got {dto.assignees}"


# ============================================================================
# SUMMARY TEST: Verify All 4 Issues Together
# ============================================================================


@pytest.mark.xfail(
    reason="Documents all 4 data loss issues in one comprehensive test", strict=True
)
def test_dto_transformation_includes_all_missing_fields(sample_task_entity):
    """
    Test: Comprehensive validation of all 4 missing fields

    Expected: XFAIL (documents all issues in one test)

    This test will PASS once all 4 fixes are implemented:
    1. project_id traversal
    2. subtask_count computation
    3. completed_subtasks computation
    4. assignee @ prefix formatting

    Use this test to verify the complete fix is working.
    """
    # Act: Convert entity to DTO
    dto = TaskResponse.from_domain(sample_task_entity)

    # Assert all 4 issues together
    issues = []

    # Issue 1: project_id
    if dto.project_id is None:
        issues.append("project_id is None (should be computed from git_branch_id)")

    # Issue 2: subtask_count
    if dto.subtask_count is None or dto.subtask_count != 3:
        issues.append(f"subtask_count is {dto.subtask_count} (should be 3)")

    # Issue 3: completed_subtasks
    if dto.completed_subtasks is None or dto.completed_subtasks != 1:
        issues.append(f"completed_subtasks is {dto.completed_subtasks} (should be 1)")

    # Issue 4: assignee @ prefix
    if not all(a.startswith("@") for a in dto.assignees):
        issues.append(f"assignees missing @ prefix: {dto.assignees}")

    # Assert: Should have NO issues (WILL FAIL with all 4 issues)
    assert len(issues) == 0, (
        f"DTO transformation has {len(issues)} issues:\n"
        + "\n".join(f"  - {issue}" for issue in issues)
    )


# ============================================================================
# TEST EXECUTION INSTRUCTIONS
# ============================================================================

"""
How to Run These Tests:
-----------------------

1. Run all Layer 3 tests:
   pytest src/tests/integration/task_management/layer_communication/test_layer3_usecase_to_dto.py -v

2. Expected output:
   - 3 PASSED (basic field mapping works)
   - 4 XFAIL (expected failures that document the issues)

3. After implementing fixes:
   - Remove @pytest.mark.xfail decorators
   - Run tests again
   - All 7 tests should PASS

Test Results Interpretation:
----------------------------

PASSED (3 tests):
✓ test_dto_includes_basic_entity_fields
✓ test_dto_serializes_nested_objects_correctly
✓ test_dto_formats_datetime_fields_correctly

XFAIL (4 tests) - Documents missing functionality:
✗ test_dto_includes_project_id_from_git_branch_relationship
✗ test_dto_computes_subtask_count_from_subtasks_array
✗ test_dto_computes_completed_subtasks_from_subtask_statuses
✗ test_dto_adds_prefix_to_assignees

These XFAIL tests prove that Layer 3 (Entity → DTO) is where ALL data loss occurs.
"""
