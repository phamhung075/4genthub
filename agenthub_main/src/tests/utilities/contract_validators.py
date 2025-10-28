"""
Contract Validation Utilities for API Response Testing

This module provides reusable validators, assertion helpers, and test utilities
for contract testing between backend and frontend. All contract tests should use
these utilities to ensure consistency and reduce duplication.

Usage:
    from tests.utilities.contract_validators import (
        assert_has_required_fields,
        assert_field_type,
        validate_uuid_field,
        validate_iso8601_timestamp,
        assert_valid_enum_value,
        validate_assignee_format,
        validate_complete_task_contract,
    )

Categories:
    1. Field Presence Validators - Check fields exist
    2. Type Validators - Validate field types
    3. Format Validators - Validate field formats (UUID, ISO8601, etc.)
    4. Enum Validators - Validate enum values
    5. Complete Contract Validators - Validate entire response objects
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import pytest


# ============================================================================
# FIELD PRESENCE VALIDATORS
# ============================================================================

def assert_has_required_fields(obj: Any, fields: List[str]) -> None:
    """
    Assert that an object has all required fields.

    Args:
        obj: Object to validate (DTO, dict, etc.)
        fields: List of required field names

    Raises:
        AssertionError: If any required field is missing

    Example:
        assert_has_required_fields(task_response, ['id', 'title', 'status'])
    """
    missing_fields = []
    for field in fields:
        if not hasattr(obj, field):
            missing_fields.append(field)

    if missing_fields:
        pytest.fail(
            f"Object missing {len(missing_fields)} required fields: {missing_fields}\n"
            f"Expected fields: {fields}"
        )


def assert_has_optional_fields(obj: Any, fields: List[str]) -> List[str]:
    """
    Check which optional fields are present on an object.

    Args:
        obj: Object to validate
        fields: List of optional field names to check

    Returns:
        List of field names that are missing

    Example:
        missing = assert_has_optional_fields(task, ['description', 'due_date'])
        if 'description' not in missing:
            # Process description
    """
    missing_fields = []
    for field in fields:
        if not hasattr(obj, field):
            missing_fields.append(field)
    return missing_fields


# ============================================================================
# TYPE VALIDATORS
# ============================================================================

def assert_field_type(obj: Any, field: str, expected_type: type) -> None:
    """
    Assert that a field has the expected type.

    Args:
        obj: Object containing the field
        field: Field name to validate
        expected_type: Expected Python type

    Raises:
        AssertionError: If field doesn't exist or has wrong type

    Example:
        assert_field_type(task, 'title', str)
        assert_field_type(task, 'progress_percentage', int)
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)

    # Allow None for optional fields
    if value is None:
        return

    assert isinstance(value, expected_type), (
        f"Field '{field}' must be {expected_type.__name__}, got {type(value).__name__}"
    )


def assert_field_types(obj: Any, field_type_map: Dict[str, type]) -> None:
    """
    Assert multiple fields have expected types.

    Args:
        obj: Object to validate
        field_type_map: Dictionary mapping field names to expected types

    Example:
        assert_field_types(task, {
            'id': str,
            'title': str,
            'progress_percentage': int,
            'assignees': list
        })
    """
    for field, expected_type in field_type_map.items():
        assert_field_type(obj, field, expected_type)


def assert_list_item_type(obj: Any, field: str, item_type: type) -> None:
    """
    Assert that all items in a list field have the expected type.

    Args:
        obj: Object containing the list field
        field: Name of the list field
        item_type: Expected type for each item

    Raises:
        AssertionError: If field is not a list or items have wrong type

    Example:
        assert_list_item_type(task, 'assignees', str)
        assert_list_item_type(task, 'subtasks', dict)
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)
    assert isinstance(value, list), f"Field '{field}' must be a list"

    for i, item in enumerate(value):
        assert isinstance(item, item_type), (
            f"Item {i} in '{field}' must be {item_type.__name__}, got {type(item).__name__}"
        )


# ============================================================================
# FORMAT VALIDATORS
# ============================================================================

def validate_uuid_field(obj: Any, field: str) -> None:
    """
    Validate that a field contains a valid UUID string.

    Args:
        obj: Object containing the UUID field
        field: Name of the UUID field

    Raises:
        AssertionError: If field doesn't exist or is not a valid UUID

    Example:
        validate_uuid_field(task, 'id')
        validate_uuid_field(task, 'project_id')
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)

    if value is None:
        return  # Allow None for optional UUID fields

    assert isinstance(value, str), f"Field '{field}' must be string (UUID format)"

    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError) as e:
        pytest.fail(f"Field '{field}' value '{value}' is not a valid UUID: {e}")


def validate_iso8601_timestamp(obj: Any, field: str) -> None:
    """
    Validate that a timestamp field is in ISO 8601 format.

    Handles both datetime objects and ISO 8601 strings.

    Args:
        obj: Object containing the timestamp field
        field: Name of the timestamp field

    Raises:
        AssertionError: If field is not valid ISO 8601 format

    Example:
        validate_iso8601_timestamp(task, 'created_at')
        validate_iso8601_timestamp(task, 'updated_at')
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)

    if value is None:
        return  # Allow None for optional timestamp fields

    if isinstance(value, datetime):
        # Verify datetime can be serialized to ISO format
        iso_string = value.isoformat()
        assert "T" in iso_string, (
            f"Field '{field}' datetime must serialize to ISO 8601 format"
        )
    elif isinstance(value, str):
        # Verify string is valid ISO 8601 format
        assert "T" in value, (
            f"Field '{field}' must be ISO 8601 format (contains 'T' separator)"
        )
        try:
            # Try parsing to verify validity
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Field '{field}' value '{value}' is not valid ISO 8601: {e}")
    else:
        pytest.fail(
            f"Field '{field}' must be datetime or ISO string, got {type(value).__name__}"
        )


def validate_assignee_format(assignee: str) -> None:
    """
    Validate that an assignee string has the @ prefix.

    Args:
        assignee: Assignee string to validate

    Raises:
        AssertionError: If assignee doesn't start with @

    Example:
        validate_assignee_format('@coding-agent')
    """
    assert isinstance(assignee, str), "Assignee must be string"
    assert assignee.startswith("@"), (
        f"Assignee '{assignee}' must start with @ prefix"
    )


def validate_assignees_format(obj: Any, field: str = "assignees") -> None:
    """
    Validate that all assignees have the @ prefix.

    Args:
        obj: Object containing assignees field
        field: Name of the assignees field (default: 'assignees')

    Raises:
        AssertionError: If any assignee doesn't have @ prefix

    Example:
        validate_assignees_format(task)
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    assignees = getattr(obj, field)
    assert isinstance(assignees, list), f"Field '{field}' must be a list"

    for assignee in assignees:
        validate_assignee_format(assignee)


# ============================================================================
# ENUM VALIDATORS
# ============================================================================

def assert_valid_enum_value(
    obj: Any,
    field: str,
    valid_values: List[str],
    enum_name: Optional[str] = None
) -> None:
    """
    Assert that a field value is one of the valid enum values.

    Args:
        obj: Object containing the field
        field: Field name to validate
        valid_values: List of valid enum values
        enum_name: Optional name for the enum (for error messages)

    Raises:
        AssertionError: If field value is not in valid_values

    Example:
        assert_valid_enum_value(task, 'status', ['todo', 'in_progress', 'done'])
        assert_valid_enum_value(task, 'priority', ['low', 'medium', 'high'], 'Priority')
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)

    if value is None:
        return  # Allow None for optional enum fields

    assert isinstance(value, str), f"Field '{field}' must be string"

    enum_label = enum_name or field
    assert value in valid_values, (
        f"{enum_label} '{value}' must be one of {valid_values}"
    )


def validate_task_status(obj: Any, field: str = "status") -> None:
    """
    Validate that a task status field has a valid value.

    Args:
        obj: Object containing the status field
        field: Name of the status field (default: 'status')

    Example:
        validate_task_status(task)
    """
    valid_statuses = ["todo", "in_progress", "done", "blocked", "cancelled"]
    assert_valid_enum_value(obj, field, valid_statuses, "Task status")


def validate_task_priority(obj: Any, field: str = "priority") -> None:
    """
    Validate that a task priority field has a valid value.

    Args:
        obj: Object containing the priority field
        field: Name of the priority field (default: 'priority')

    Example:
        validate_task_priority(task)
    """
    valid_priorities = ["low", "medium", "high", "urgent", "critical"]
    assert_valid_enum_value(obj, field, valid_priorities, "Task priority")


# ============================================================================
# RANGE VALIDATORS
# ============================================================================

def assert_value_in_range(
    obj: Any,
    field: str,
    min_value: Union[int, float],
    max_value: Union[int, float]
) -> None:
    """
    Assert that a numeric field value is within a specified range.

    Args:
        obj: Object containing the field
        field: Field name to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)

    Raises:
        AssertionError: If value is outside the range

    Example:
        assert_value_in_range(task, 'progress_percentage', 0, 100)
    """
    assert hasattr(obj, field), f"Object must have '{field}' field"
    value = getattr(obj, field)

    if value is None:
        return  # Allow None for optional fields

    assert min_value <= value <= max_value, (
        f"Field '{field}' value {value} must be between {min_value} and {max_value}"
    )


def validate_progress_percentage(obj: Any, field: str = "progress_percentage") -> None:
    """
    Validate that a progress percentage is 0-100.

    Args:
        obj: Object containing the progress field
        field: Name of the progress field (default: 'progress_percentage')

    Example:
        validate_progress_percentage(task)
    """
    assert_field_type(obj, field, int)
    assert_value_in_range(obj, field, 0, 100)


# ============================================================================
# COMPLETE CONTRACT VALIDATORS
# ============================================================================

def validate_complete_task_contract(
    task: Any,
    expect_project_id: bool = False,
    expect_subtask_counts: bool = False
) -> None:
    """
    Validate that a task response matches the complete frontend Task contract.

    This validator checks all fields that the frontend expects in a Task response.
    Use expect_* flags to control validation of fields that may be missing in
    current implementation (documented as mismatches).

    Args:
        task: Task response object to validate
        expect_project_id: If True, require project_id field (MISMATCH #1)
        expect_subtask_counts: If True, require subtask_count and completed_subtasks (MISMATCH #2, #3)

    Raises:
        AssertionError: If any required field is missing or invalid

    Example:
        # Basic validation (passes with current implementation)
        validate_complete_task_contract(task)

        # Strict validation (fails for known mismatches)
        validate_complete_task_contract(task, expect_project_id=True, expect_subtask_counts=True)
    """
    # Required fields that SHOULD always be present
    required_fields = ["id", "title", "status", "priority", "git_branch_id"]
    assert_has_required_fields(task, required_fields)

    # Validate field types
    assert_field_types(task, {
        "id": str,
        "title": str,
        "status": str,
        "priority": str,
        "git_branch_id": str,
    })

    # Validate UUID fields
    validate_uuid_field(task, "id")
    validate_uuid_field(task, "git_branch_id")

    # Validate enum values
    validate_task_status(task)
    validate_task_priority(task)

    # Validate optional fields if present
    optional_fields = [
        "description", "assignees", "labels", "created_at", "updated_at",
        "progress_percentage", "estimated_effort", "due_date", "details",
        "context_id", "context_data"
    ]

    for field in optional_fields:
        if hasattr(task, field):
            value = getattr(task, field)

            # Type validation for specific fields
            if field == "assignees" and value is not None:
                assert_list_item_type(task, field, str)
                validate_assignees_format(task)
            elif field == "labels" and value is not None:
                assert_list_item_type(task, field, str)
            elif field in ["created_at", "updated_at"] and value is not None:
                validate_iso8601_timestamp(task, field)
            elif field == "progress_percentage" and value is not None:
                validate_progress_percentage(task)

    # Validate fields that are known mismatches (optional based on flags)
    if expect_project_id:
        assert hasattr(task, "project_id"), (
            "Task MUST have 'project_id' field for frontend to filter by project"
        )
        validate_uuid_field(task, "project_id")

    if expect_subtask_counts:
        assert hasattr(task, "subtask_count"), (
            "Task MUST have 'subtask_count' field for efficient frontend display"
        )
        assert_field_type(task, "subtask_count", int)

        assert hasattr(task, "completed_subtasks"), (
            "Task MUST have 'completed_subtasks' field for progress tracking"
        )
        assert_field_type(task, "completed_subtasks", int)

        # Validate count relationships
        if hasattr(task, "subtasks") and task.subtasks is not None:
            assert task.subtask_count == len(task.subtasks), (
                f"subtask_count ({task.subtask_count}) must match "
                f"actual subtasks length ({len(task.subtasks)})"
            )


def validate_complete_subtask_contract(subtask: Any) -> None:
    """
    Validate that a subtask response matches the complete frontend Subtask contract.

    Args:
        subtask: Subtask response object to validate

    Raises:
        AssertionError: If any required field is missing or invalid

    Example:
        validate_complete_subtask_contract(subtask)
    """
    # Required fields
    required_fields = ["id", "task_id", "title", "status"]
    assert_has_required_fields(subtask, required_fields)

    # Validate field types
    assert_field_types(subtask, {
        "id": str,
        "task_id": str,
        "title": str,
        "status": str,
    })

    # Validate UUID fields
    validate_uuid_field(subtask, "id")
    validate_uuid_field(subtask, "task_id")

    # Validate status
    validate_task_status(subtask)

    # Validate optional fields if present
    if hasattr(subtask, "description") and subtask.description is not None:
        assert_field_type(subtask, "description", str)

    if hasattr(subtask, "priority") and subtask.priority is not None:
        validate_task_priority(subtask)

    if hasattr(subtask, "assignees") and subtask.assignees is not None:
        assert_list_item_type(subtask, "assignees", str)
        validate_assignees_format(subtask)

    if hasattr(subtask, "progress_percentage") and subtask.progress_percentage is not None:
        validate_progress_percentage(subtask)

    if hasattr(subtask, "created_at") and subtask.created_at is not None:
        validate_iso8601_timestamp(subtask, "created_at")

    if hasattr(subtask, "updated_at") and subtask.updated_at is not None:
        validate_iso8601_timestamp(subtask, "updated_at")


# ============================================================================
# NAMING CONVENTION VALIDATORS
# ============================================================================

def validate_snake_case_fields(obj_dict: Dict[str, Any], expected_snake_case: List[str]) -> None:
    """
    Validate that serialized object uses snake_case for specified fields.

    This validator checks that JSON serialization uses snake_case naming,
    not camelCase. Used to catch naming inconsistencies.

    Args:
        obj_dict: Dictionary representation of the object (from to_dict() or JSON)
        expected_snake_case: List of field names that should use snake_case

    Raises:
        AssertionError: If any field uses camelCase instead of snake_case

    Example:
        task_dict = task.to_dict()
        validate_snake_case_fields(task_dict, ['estimated_effort', 'due_date'])
    """
    for field in expected_snake_case:
        # Convert to camelCase for comparison
        camel_case = snake_to_camel(field)

        assert field in obj_dict or field not in obj_dict, (
            f"If field exists, it should use snake_case '{field}', not camelCase '{camel_case}'"
        )

        if camel_case in obj_dict and field not in obj_dict:
            pytest.fail(
                f"Field should use snake_case '{field}', not camelCase '{camel_case}'"
            )


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ============================================================================
# WEBSOCKET MESSAGE VALIDATORS
# ============================================================================

def validate_websocket_message_structure(message: Dict[str, Any]) -> None:
    """
    Validate that a WebSocket message has the expected structure.

    Args:
        message: WebSocket message dictionary to validate

    Raises:
        AssertionError: If message structure is invalid

    Example:
        validate_websocket_message_structure(ws_message)
    """
    required_fields = ["type", "data"]
    for field in required_fields:
        assert field in message, f"WebSocket message must have '{field}' field"

    assert isinstance(message["type"], str), "Message type must be string"
    assert isinstance(message["data"], dict), "Message data must be dictionary"


def validate_websocket_task_message(
    message: Dict[str, Any],
    expect_complete_task: bool = True
) -> None:
    """
    Validate that a WebSocket task message contains complete task data.

    Args:
        message: WebSocket message containing task data
        expect_complete_task: If True, validate task data completeness

    Raises:
        AssertionError: If message or task data is invalid

    Example:
        validate_websocket_task_message(ws_message)
    """
    validate_websocket_message_structure(message)

    assert "task" in message["data"] or "id" in message["data"], (
        "WebSocket message data must contain task information"
    )

    # If complete task is expected, validate it
    if expect_complete_task:
        task_data = message["data"].get("task", message["data"])

        # Create a simple object for validation
        class TaskObject:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        task_obj = TaskObject(task_data)
        validate_complete_task_contract(task_obj)
