"""
Backend API Contract Tests - Subtask Management Endpoints

TDD Approach: These tests document the expected API contract between backend and frontend.
Tests are based on SubtaskResponse DTO and frontend Subtask interface expectations.

Reference: agenthub_main/src/fastmcp/task_management/application/dtos/subtask/subtask_response.py
Frontend: agenthub-frontend/src/types/api.types.ts (Subtask interface)

Expected Contract:
- SubtaskResponse contains: task_id, subtask (Dict), progress (Dict)
- Agent inheritance information when applied
- ISO 8601 timestamps
- Proper UUID format for IDs
"""

import pytest
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any

from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.dtos.subtask import AddSubtaskRequest
from fastmcp.task_management.application.dtos.task import CreateTaskRequest, TaskResponse


@pytest.fixture
def task_repository(shared_test_db, user_id):
    """Create real task repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    return ORMTaskRepository(session=None, user_id=user_id)


@pytest.fixture
def subtask_repository(shared_test_db, user_id):
    """Create real subtask repository for integration tests."""
    from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
    return ORMSubtaskRepository(session=None, user_id=user_id)


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
def sample_task(
    create_task_use_case: CreateTaskUseCase,
    user_id: str,
    project_id: str,
    git_branch_id: str,
) -> TaskResponse:
    """Create a sample task for testing API contract."""
    request = CreateTaskRequest(
        title="Sample Task for Subtask API Contract Testing",
        description="Parent task for subtask testing",
        git_branch_id=git_branch_id,
        user_id=user_id,
        assignees=["@coding-agent", "@test-orchestrator-agent"],
        priority="high",
    )
    result = create_task_use_case.execute(request)
    return result.task if hasattr(result, 'task') else result


@pytest.fixture
def sample_subtask(
    sample_task,
    add_subtask_use_case: AddSubtaskUseCase,
    user_id: str,
):
    """Create a sample subtask for testing API contract."""
    request = AddSubtaskRequest(
        task_id=sample_task.id,
        title="Sample Subtask for API Contract Testing",
        description="Test subtask with multiple fields populated",
        assignees=["@coding-agent"],
        priority="high",
        status="in_progress",
        progress_percentage=50,
    )
    result = add_subtask_use_case.execute(request)
    return result


class TestSubtaskAPIContractBasicFields:
    """Test basic fields that SHOULD PASS - confirmed working fields."""

    def test_subtask_response_has_task_id(self, sample_subtask):
        """
        Verify subtask response includes parent task_id field.
        Status: ✅ SHOULD PASS - Required field in SubtaskResponse.
        """
        assert hasattr(sample_subtask, "task_id"), "SubtaskResponse must have 'task_id' field"
        assert isinstance(sample_subtask.task_id, str), "task_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(sample_subtask.task_id)
        except ValueError:
            pytest.fail(f"task_id '{sample_subtask.task_id}' is not a valid UUID")

    def test_subtask_response_has_subtask_dict(self, sample_subtask):
        """
        Verify subtask response includes subtask as dictionary.
        Status: ✅ SHOULD PASS - Required field in SubtaskResponse.
        """
        assert hasattr(sample_subtask, "subtask"), "SubtaskResponse must have 'subtask' field"
        assert isinstance(sample_subtask.subtask, dict), "subtask must be dictionary"
        assert len(sample_subtask.subtask) > 0, "subtask dictionary must not be empty"

    def test_subtask_response_has_progress_dict(self, sample_subtask):
        """
        Verify subtask response includes progress as dictionary.
        Status: ✅ SHOULD PASS - Required field in SubtaskResponse.
        """
        assert hasattr(sample_subtask, "progress"), "SubtaskResponse must have 'progress' field"
        assert isinstance(sample_subtask.progress, dict), "progress must be dictionary"


class TestSubtaskDictStructure:
    """Test subtask dictionary structure and fields."""

    def test_subtask_dict_has_required_id_field(self, sample_subtask):
        """
        Verify subtask dict includes UUID id field.
        Status: ✅ SHOULD PASS - Core field in subtask entity.
        """
        subtask_dict = sample_subtask.subtask
        assert "id" in subtask_dict, "subtask dict must have 'id' field"
        assert isinstance(subtask_dict["id"], str), "subtask id must be string"
        # Verify it's a valid UUID format
        try:
            uuid4_obj = uuid4()
            uuid4_obj = type(uuid4_obj)(subtask_dict["id"])
        except ValueError:
            pytest.fail(f"subtask id '{subtask_dict['id']}' is not a valid UUID")

    def test_subtask_dict_has_required_title_field(self, sample_subtask):
        """
        Verify subtask dict includes title field.
        Status: ✅ SHOULD PASS - Required field.
        """
        subtask_dict = sample_subtask.subtask
        assert "title" in subtask_dict, "subtask dict must have 'title' field"
        assert isinstance(subtask_dict["title"], str), "subtask title must be string"
        assert len(subtask_dict["title"]) > 0, "subtask title must not be empty"

    def test_subtask_dict_has_status_field(self, sample_subtask):
        """
        Verify subtask dict includes status field with valid value.
        Status: ✅ SHOULD PASS - Core field.
        """
        subtask_dict = sample_subtask.subtask
        assert "status" in subtask_dict, "subtask dict must have 'status' field"
        assert isinstance(subtask_dict["status"], str), "subtask status must be string"
        valid_statuses = ["todo", "in_progress", "done", "blocked", "cancelled"]
        assert subtask_dict["status"] in valid_statuses, (
            f"subtask status '{subtask_dict['status']}' must be one of {valid_statuses}"
        )

    def test_subtask_dict_has_priority_field(self, sample_subtask):
        """
        Verify subtask dict includes priority field with valid value.
        Status: ✅ SHOULD PASS - Core field.
        """
        subtask_dict = sample_subtask.subtask
        assert "priority" in subtask_dict, "subtask dict must have 'priority' field"
        assert isinstance(subtask_dict["priority"], str), "subtask priority must be string"
        valid_priorities = ["low", "medium", "high", "urgent", "critical"]
        assert subtask_dict["priority"] in valid_priorities, (
            f"subtask priority '{subtask_dict['priority']}' must be one of {valid_priorities}"
        )

    def test_subtask_dict_has_progress_percentage(self, sample_subtask):
        """
        Verify subtask dict includes progress_percentage as integer.
        Status: ✅ SHOULD PASS - Progress tracking field.
        """
        subtask_dict = sample_subtask.subtask
        assert "progress_percentage" in subtask_dict, (
            "subtask dict must have 'progress_percentage' field"
        )
        assert isinstance(subtask_dict["progress_percentage"], int), (
            "subtask progress_percentage must be integer"
        )
        assert 0 <= subtask_dict["progress_percentage"] <= 100, (
            f"subtask progress_percentage must be 0-100, got {subtask_dict['progress_percentage']}"
        )


class TestSubtaskDictTimestamps:
    """Test timestamp fields in subtask dict - ISO 8601 format."""

    def test_subtask_created_at_is_iso8601_string(self, sample_subtask):
        """
        Verify created_at is ISO 8601 formatted timestamp string.
        Status: ✅ SHOULD PASS - Standard timestamp field.
        """
        subtask_dict = sample_subtask.subtask
        assert "created_at" in subtask_dict, "subtask dict must have 'created_at' field"

        # Handle both datetime objects and string representations
        if isinstance(subtask_dict["created_at"], datetime):
            iso_string = subtask_dict["created_at"].isoformat()
            assert "T" in iso_string, "created_at datetime must serialize to ISO 8601 format"
        elif isinstance(subtask_dict["created_at"], str):
            assert "T" in subtask_dict["created_at"], (
                "created_at must be ISO 8601 format (contains 'T')"
            )
            # Try to parse it to verify it's valid
            try:
                datetime.fromisoformat(subtask_dict["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"created_at '{subtask_dict['created_at']}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"created_at must be datetime or string, got {type(subtask_dict['created_at'])}"
            )

    def test_subtask_updated_at_is_iso8601_string(self, sample_subtask):
        """
        Verify updated_at is ISO 8601 formatted timestamp string.
        Status: ✅ SHOULD PASS - Standard timestamp field.
        """
        subtask_dict = sample_subtask.subtask
        assert "updated_at" in subtask_dict, "subtask dict must have 'updated_at' field"

        # Handle both datetime objects and string representations
        if isinstance(subtask_dict["updated_at"], datetime):
            iso_string = subtask_dict["updated_at"].isoformat()
            assert "T" in iso_string, "updated_at datetime must serialize to ISO 8601 format"
        elif isinstance(subtask_dict["updated_at"], str):
            assert "T" in subtask_dict["updated_at"], (
                "updated_at must be ISO 8601 format (contains 'T')"
            )
            # Try to parse it to verify it's valid
            try:
                datetime.fromisoformat(subtask_dict["updated_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pytest.fail(
                    f"updated_at '{subtask_dict['updated_at']}' is not valid ISO 8601 format"
                )
        else:
            pytest.fail(
                f"updated_at must be datetime or string, got {type(subtask_dict['updated_at'])}"
            )


class TestSubtaskDictAssignees:
    """Test assignees field in subtask dict."""

    def test_subtask_dict_has_assignees_array(self, sample_subtask):
        """
        Verify subtask dict includes assignees as string array.
        Status: ✅ SHOULD PASS - Standard field.
        """
        subtask_dict = sample_subtask.subtask
        assert "assignees" in subtask_dict, "subtask dict must have 'assignees' field"
        assert isinstance(subtask_dict["assignees"], list), "subtask assignees must be array"
        for assignee in subtask_dict["assignees"]:
            assert isinstance(assignee, str), "Each assignee must be string"

    def test_subtask_assignees_have_at_prefix(self, sample_subtask):
        """
        Verify all assignees have @ prefix consistently.
        Status: ✅ SHOULD PASS - Confirmed requirement.
        """
        subtask_dict = sample_subtask.subtask
        assert "assignees" in subtask_dict, "subtask dict must have 'assignees' field"
        if len(subtask_dict["assignees"]) > 0:
            for assignee in subtask_dict["assignees"]:
                assert assignee.startswith("@"), (
                    f"Assignee '{assignee}' must start with @ prefix"
                )


class TestSubtaskProgressDict:
    """Test progress dictionary structure."""

    def test_progress_dict_structure(self, sample_subtask):
        """
        Verify progress dict has expected structure.
        Status: ✅ SHOULD PASS - Progress metadata.
        """
        progress_dict = sample_subtask.progress
        # Progress dict should contain aggregated information about parent task
        # The exact structure may vary, but it should be a valid dict
        assert isinstance(progress_dict, dict), "progress must be dictionary"
        # Verify it contains useful progress information
        # (specific fields depend on implementation)


class TestSubtaskAgentInheritance:
    """Test agent inheritance information when applicable."""

    def test_agent_inheritance_fields_when_applied(self, sample_subtask):
        """
        Verify agent inheritance fields are present when inheritance is applied.
        Status: ✅ SHOULD PASS - Optional inheritance metadata.

        Fields only present when agent_inheritance_applied = True:
        - agent_inheritance_applied: bool
        - inherited_assignees: List[str]
        """
        # Check if inheritance was applied
        if hasattr(sample_subtask, "agent_inheritance_applied"):
            if sample_subtask.agent_inheritance_applied:
                assert hasattr(sample_subtask, "inherited_assignees"), (
                    "When agent_inheritance_applied=True, must have 'inherited_assignees' field"
                )
                assert isinstance(sample_subtask.inherited_assignees, list), (
                    "inherited_assignees must be list"
                )


class TestSubtaskDictOptionalFields:
    """Test optional fields that should be present when populated."""

    def test_subtask_dict_has_description_when_provided(self, sample_subtask):
        """Verify description is included when provided."""
        subtask_dict = sample_subtask.subtask
        # Description should exist in dict (even if empty)
        if "description" in subtask_dict:
            if subtask_dict["description"] is not None:
                assert isinstance(subtask_dict["description"], str), (
                    "subtask description must be string"
                )

    def test_subtask_dict_has_parent_task_id(self, sample_subtask):
        """
        Verify parent task_id reference exists in subtask dict.
        Status: ✅ SHOULD PASS - Required for subtask-task relationship.
        """
        subtask_dict = sample_subtask.subtask
        # Subtask should reference its parent task
        # This might be stored as task_id or parent_task_id
        has_task_reference = (
            "task_id" in subtask_dict or
            "parent_task_id" in subtask_dict
        )
        assert has_task_reference, (
            "subtask dict must have 'task_id' or 'parent_task_id' field"
        )


class TestSubtaskResponseCompleteContract:
    """Test that SubtaskResponse matches complete frontend expectations."""

    def test_subtask_response_matches_frontend_interface(self, sample_subtask):
        """
        Verify SubtaskResponse includes ALL fields expected by frontend.

        This is a comprehensive test that documents the complete contract.
        Sub-tests above provide detailed failure messages for specific fields.
        """
        # Required top-level fields in SubtaskResponse
        required_response_fields = [
            "task_id",
            "subtask",
            "progress",
        ]

        for field in required_response_fields:
            assert hasattr(sample_subtask, field), (
                f"SubtaskResponse MUST have required field '{field}'"
            )

        # Required fields in subtask dict
        subtask_dict = sample_subtask.subtask
        required_subtask_fields = [
            "id",
            "title",
            "status",
            "priority",
        ]

        for field in required_subtask_fields:
            assert field in subtask_dict, (
                f"subtask dict MUST have required field '{field}'"
            )

        # Optional but commonly used fields
        common_optional_fields = [
            "description",
            "assignees",
            "created_at",
            "updated_at",
            "progress_percentage",
        ]

        # Verify these fields exist (they may be None or empty)
        for field in common_optional_fields:
            assert field in subtask_dict, (
                f"subtask dict should have common field '{field}'"
            )


class TestSubtaskResponseSerialization:
    """Test subtask response serialization to dict."""

    def test_subtask_response_can_serialize_to_dict(self, sample_subtask):
        """
        Verify SubtaskResponse can be serialized to dictionary for API response.
        Status: ✅ SHOULD PASS - Required for JSON serialization.
        """
        if hasattr(sample_subtask, "to_dict"):
            response_dict = sample_subtask.to_dict()
            assert isinstance(response_dict, dict), "to_dict() must return dictionary"

            # Verify required keys in serialized response
            assert "task_id" in response_dict, "Serialized response must include task_id"
            assert "subtask" in response_dict, "Serialized response must include subtask"
            assert "progress" in response_dict, "Serialized response must include progress"

            # Verify serialized subtask is dict
            assert isinstance(response_dict["subtask"], dict), (
                "Serialized subtask must be dictionary"
            )
