"""MCP Message Fixtures for Protocol Testing

This module provides sample MCP protocol requests and responses for testing
all MCP tool types. Includes valid messages, invalid messages for error testing,
protocol version variations, and message serialization helpers.

Usage Examples:
    # Get a valid task creation request
    >>> request = MCPMessageFixtures.get_task_create_request()
    >>> assert request["action"] == "create"

    # Get an invalid request for error testing
    >>> invalid = MCPMessageFixtures.get_invalid_request("missing_action")
    >>> # Use in tests to verify error handling

    # Get a complete request/response pair
    >>> req, resp = MCPMessageFixtures.get_request_response_pair("task_create")
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any


class MCPMessageFixtures:
    """Fixtures for MCP protocol message testing."""

    # =========================================================================
    # TASK MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_task_create_request(
        title: str = "Test Task",
        assignees: str = "coding-agent",
        git_branch_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a valid task creation request."""
        return {
            "action": "create",
            "title": title,
            "assignees": assignees,
            "git_branch_id": git_branch_id or str(uuid.uuid4()),
            "description": "Test task description",
            "details": "Detailed implementation notes",
            "priority": "high",
            "estimated_effort": "2 hours",
            "labels": ["testing", "infrastructure"],
        }

    @staticmethod
    def get_task_create_response(task_id: str | None = None) -> dict[str, Any]:
        """Generate a valid task creation response."""
        task_id = task_id or str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        return {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "title": "Test Task",
                    "description": "Test task description",
                    "status": "todo",
                    "priority": "high",
                    "details": "Detailed implementation notes",
                    "estimated_effort": "2 hours",
                    "assignees": "coding-agent",
                    "labels": ["testing", "infrastructure"],
                    "created_at": now,
                    "updated_at": now,
                    "progress_percentage": 0,
                }
            },
            "meta": {
                "persisted": True,
                "id": str(uuid.uuid4()),
                "timestamp": now,
                "operation": "create",
            },
        }

    @staticmethod
    def get_task_update_request(task_id: str | None = None) -> dict[str, Any]:
        """Generate a valid task update request."""
        return {
            "action": "update",
            "task_id": task_id or str(uuid.uuid4()),
            "status": "in_progress",
            "progress_percentage": 50,
            "details": "Updated progress notes",
        }

    @staticmethod
    def get_task_complete_request(task_id: str | None = None) -> dict[str, Any]:
        """Generate a valid task completion request."""
        return {
            "action": "complete",
            "task_id": task_id or str(uuid.uuid4()),
            "completion_summary": "Task completed successfully",
            "testing_notes": "All tests passing",
        }

    @staticmethod
    def get_task_list_request(git_branch_id: str | None = None) -> dict[str, Any]:
        """Generate a valid task list request."""
        return {
            "action": "list",
            "git_branch_id": git_branch_id or str(uuid.uuid4()),
            "status": "in_progress",
            "limit": 50,
        }

    # =========================================================================
    # SUBTASK MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_subtask_create_request(
        task_id: str | None = None, title: str = "Test Subtask"
    ) -> dict[str, Any]:
        """Generate a valid subtask creation request."""
        return {
            "action": "create",
            "task_id": task_id or str(uuid.uuid4()),
            "title": title,
            "description": "Subtask description",
            "priority": "medium",
            "progress_notes": "Initial setup",
        }

    @staticmethod
    def get_subtask_update_request(
        task_id: str | None = None, subtask_id: str | None = None
    ) -> dict[str, Any]:
        """Generate a valid subtask update request."""
        return {
            "action": "update",
            "task_id": task_id or str(uuid.uuid4()),
            "subtask_id": subtask_id or str(uuid.uuid4()),
            "progress_percentage": 75,
            "progress_notes": "Nearly complete",
        }

    # =========================================================================
    # CONTEXT MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_context_create_request(
        level: str = "task", context_id: str | None = None
    ) -> dict[str, Any]:
        """Generate a valid context creation request."""
        return {
            "action": "create",
            "level": level,
            "context_id": context_id or str(uuid.uuid4()),
            "data": json.dumps(
                {
                    "metadata": {"version": 1},
                    "objective": {"title": "Test Objective"},
                    "progress": {"completion_percentage": 0},
                }
            ),
        }

    @staticmethod
    def get_context_get_request(
        level: str = "task",
        context_id: str | None = None,
        include_inherited: bool = False,
    ) -> dict[str, Any]:
        """Generate a valid context get request."""
        return {
            "action": "get",
            "level": level,
            "context_id": context_id or str(uuid.uuid4()),
            "include_inherited": "true" if include_inherited else "false",
        }

    @staticmethod
    def get_context_update_request(
        level: str = "task", context_id: str | None = None
    ) -> dict[str, Any]:
        """Generate a valid context update request."""
        return {
            "action": "update",
            "level": level,
            "context_id": context_id or str(uuid.uuid4()),
            "data": json.dumps({"progress": {"completion_percentage": 50}}),
            "propagate_changes": "true",
        }

    # =========================================================================
    # PROJECT MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_project_create_request(name: str = "Test Project") -> dict[str, Any]:
        """Generate a valid project creation request."""
        return {
            "action": "create",
            "name": name,
            "description": "Test project description",
        }

    @staticmethod
    def get_project_get_request(project_id: str | None = None) -> dict[str, Any]:
        """Generate a valid project get request."""
        return {"action": "get", "project_id": project_id or str(uuid.uuid4())}

    @staticmethod
    def get_project_list_request() -> dict[str, Any]:
        """Generate a valid project list request."""
        return {"action": "list"}

    # =========================================================================
    # GIT BRANCH MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_branch_create_request(
        project_id: str | None = None, name: str = "feature/test"
    ) -> dict[str, Any]:
        """Generate a valid branch creation request."""
        return {
            "action": "create",
            "project_id": project_id or str(uuid.uuid4()),
            "git_branch_name": name,
            "git_branch_description": "Test branch description",
        }

    @staticmethod
    def get_branch_list_request(project_id: str | None = None) -> dict[str, Any]:
        """Generate a valid branch list request."""
        return {"action": "list", "project_id": project_id or str(uuid.uuid4())}

    # =========================================================================
    # AGENT MANAGEMENT FIXTURES
    # =========================================================================

    @staticmethod
    def get_agent_register_request(
        project_id: str | None = None, name: str = "test-agent"
    ) -> dict[str, Any]:
        """Generate a valid agent registration request."""
        return {
            "action": "register",
            "project_id": project_id or str(uuid.uuid4()),
            "name": name,
            "agent_id": f"{name}-{uuid.uuid4()}",
        }

    @staticmethod
    def get_agent_assign_request(
        project_id: str | None = None,
        agent_id: str | None = None,
        git_branch_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a valid agent assignment request."""
        return {
            "action": "assign",
            "project_id": project_id or str(uuid.uuid4()),
            "agent_id": agent_id or f"agent-{uuid.uuid4()}",
            "git_branch_id": git_branch_id or str(uuid.uuid4()),
        }

    # =========================================================================
    # INVALID MESSAGE FIXTURES (for error testing)
    # =========================================================================

    @staticmethod
    def get_invalid_request(error_type: str) -> dict[str, Any]:
        """Generate invalid requests for error handling tests.

        Args:
            error_type: Type of error to simulate:
                - "missing_action": Request without action field
                - "invalid_action": Request with unknown action
                - "missing_required": Missing required parameters
                - "invalid_uuid": Invalid UUID format
                - "invalid_json": Malformed JSON in data field
                - "unauthorized": Request without proper auth
                - "forbidden": Request with insufficient permissions

        Returns:
            Invalid request dictionary
        """
        if error_type == "missing_action":
            return {"title": "Task without action", "assignees": "coding-agent"}

        elif error_type == "invalid_action":
            return {"action": "nonexistent_action", "task_id": str(uuid.uuid4())}

        elif error_type == "missing_required":
            return {
                "action": "create"
                # Missing required fields like title, assignees
            }

        elif error_type == "invalid_uuid":
            return {"action": "get", "task_id": "not-a-valid-uuid"}

        elif error_type == "invalid_json":
            return {"action": "create", "data": "{'malformed': json, missing quotes}"}

        elif error_type == "unauthorized":
            return {
                "action": "list",
                # No auth token provided
                "_error_hint": "missing_auth",
            }

        elif error_type == "forbidden":
            return {
                "action": "delete",
                "task_id": str(uuid.uuid4()),
                # User doesn't have delete permission
                "_error_hint": "insufficient_permissions",
            }

        else:
            raise ValueError(f"Unknown error type: {error_type}")

    @staticmethod
    def get_error_response(
        error_type: str, detail: str | None = None
    ) -> dict[str, Any]:
        """Generate error response for testing error handling.

        Args:
            error_type: Type of error
            detail: Optional error detail message

        Returns:
            Error response dictionary
        """
        error_messages = {
            "missing_action": "Missing required parameter: action",
            "invalid_action": "Unknown action type",
            "missing_required": "Missing required parameters",
            "invalid_uuid": "Invalid UUID format",
            "unauthorized": "Authentication required",
            "forbidden": "Insufficient permissions",
        }

        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": detail or error_messages.get(error_type, "Unknown error"),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }

    # =========================================================================
    # REQUEST/RESPONSE PAIRS (for integration testing)
    # =========================================================================

    @staticmethod
    def get_request_response_pair(
        operation: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get matching request/response pair for integration tests.

        Args:
            operation: Operation name (e.g., "task_create", "task_update", etc.)

        Returns:
            Tuple of (request, response) dictionaries
        """
        if operation == "task_create":
            request = MCPMessageFixtures.get_task_create_request()
            response = MCPMessageFixtures.get_task_create_response()
            return request, response

        elif operation == "task_update":
            task_id = str(uuid.uuid4())
            request = MCPMessageFixtures.get_task_update_request(task_id)
            response = {
                "success": True,
                "data": {
                    "task": {
                        "id": task_id,
                        "status": "in_progress",
                        "progress_percentage": 50,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                },
            }
            return request, response

        elif operation == "context_create":
            context_id = str(uuid.uuid4())
            request = MCPMessageFixtures.get_context_create_request(
                context_id=context_id
            )
            response = {
                "success": True,
                "data": {
                    "context_id": context_id,
                    "level": "task",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            }
            return request, response

        else:
            raise ValueError(f"Unknown operation: {operation}")

    # =========================================================================
    # MESSAGE SERIALIZATION HELPERS
    # =========================================================================

    @staticmethod
    def serialize_message(message: dict[str, Any], pretty: bool = False) -> str:
        """Serialize message to JSON string.

        Args:
            message: Message dictionary
            pretty: Whether to pretty-print (default False)

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(message, indent=2, default=str)
        return json.dumps(message, default=str)

    @staticmethod
    def deserialize_message(json_str: str) -> dict[str, Any]:
        """Deserialize JSON string to message dictionary.

        Args:
            json_str: JSON string

        Returns:
            Message dictionary
        """
        return json.loads(json_str)

    @staticmethod
    def validate_message_structure(
        message: dict[str, Any], required_fields: list[str]
    ) -> tuple[bool, str | None]:
        """Validate that a message has required fields.

        Args:
            message: Message to validate
            required_fields: List of required field names

        Returns:
            Tuple of (is_valid, error_message)
        """
        missing_fields = [field for field in required_fields if field not in message]

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        return True, None


# Convenience functions for quick access


def get_sample_task_request() -> dict[str, Any]:
    """Quick helper to get a sample task creation request."""
    return MCPMessageFixtures.get_task_create_request()


def get_sample_task_response() -> dict[str, Any]:
    """Quick helper to get a sample task creation response."""
    return MCPMessageFixtures.get_task_create_response()


def get_sample_error_response(error_type: str = "missing_required") -> dict[str, Any]:
    """Quick helper to get a sample error response."""
    return MCPMessageFixtures.get_error_response(error_type)
