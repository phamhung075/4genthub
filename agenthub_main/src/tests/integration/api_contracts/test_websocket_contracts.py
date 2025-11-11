"""
WebSocket Contract Tests - Real-time Message Format Validation

TDD Approach: These tests document the expected WebSocket message format between backend and frontend.
Tests verify that WebSocket broadcasts match frontend expectations for real-time updates.

Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md

WebSocket Message Types:
1. task.created - New task created
2. task.updated - Task modified
3. task.completed - Task marked as done
4. subtask.created - New subtask added
5. subtask.updated - Subtask modified
6. context.synced - Context synchronized after changes

Expected Message Structure:
{
    "type": "task.created",
    "payload": {
        // Task object matching Task interface
        "id": "uuid",
        "title": "string",
        "status": "string",
        // ... all Task fields
    },
    "timestamp": "ISO 8601 string"
}
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from fastmcp.auth.domain.value_objects.user_id import UserId
from fastmcp.task_management.domain.value_objects import (
    GitBranchId,
    ProjectId,
)


# Mock WebSocket broadcast function for testing
class MockWebSocketBroadcaster:
    """Mock WebSocket broadcaster to capture sent messages."""

    def __init__(self):
        self.messages: list[dict[str, Any]] = []

    async def broadcast(self, message: dict[str, Any]):
        """Capture broadcast messages for verification."""
        self.messages.append(message)

    def get_messages_by_type(self, message_type: str) -> list[dict[str, Any]]:
        """Get all messages of specific type."""
        return [msg for msg in self.messages if msg.get("type") == message_type]

    def get_latest_message(
        self, message_type: str | None = None
    ) -> dict[str, Any | None]:
        """Get the most recent message, optionally filtered by type."""
        if message_type:
            filtered = self.get_messages_by_type(message_type)
            return filtered[-1] if filtered else None
        return self.messages[-1] if self.messages else None

    def clear(self):
        """Clear all captured messages."""
        self.messages.clear()


@pytest.fixture
def ws_broadcaster():
    """Fixture providing mock WebSocket broadcaster."""
    return MockWebSocketBroadcaster()


@pytest.fixture
def user_id():
    """Test user identifier."""
    return UserId(str(uuid4()))


@pytest.fixture
def project_id():
    """Test project identifier."""
    return ProjectId(str(uuid4()))


@pytest.fixture
def git_branch_id():
    """Test git branch identifier."""
    return GitBranchId(str(uuid4()))


class TestWebSocketMessageStructure:
    """Test basic WebSocket message structure that SHOULD PASS."""

    @pytest.mark.asyncio
    async def test_websocket_message_has_required_fields(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify all WebSocket messages have required structure fields.
        Status: ✅ SHOULD PASS - Basic message structure.

        Expected structure:
        {
            "type": "string",  // Message type (e.g., "task.created")
            "payload": {},     // Message payload (data)
            "timestamp": "ISO 8601 string"  // When message was sent
        }
        """
        # Simulate message broadcast
        test_message = {
            "type": "task.created",
            "payload": {"id": str(uuid4()), "title": "Test Task"},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        await ws_broadcaster.broadcast(test_message)

        # Verify message structure
        message = ws_broadcaster.get_latest_message()
        assert message is not None, "Message should be captured"
        assert "type" in message, "Message must have 'type' field"
        assert "payload" in message, "Message must have 'payload' field"
        assert "timestamp" in message, "Message must have 'timestamp' field"

        # Verify timestamp is ISO 8601
        assert "T" in message["timestamp"], "Timestamp must be ISO 8601 format"
        try:
            datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid ISO 8601 timestamp: {message['timestamp']}")


class TestTaskCreatedMessage:
    """Test task.created WebSocket message format."""

    @pytest.mark.asyncio
    async def test_task_created_message_type(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify task.created message has correct type field.
        Status: ✅ SHOULD PASS - Message type verification.
        """
        await ws_broadcaster.broadcast(
            {
                "type": "task.created",
                "payload": {"id": str(uuid4())},
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.created")
        assert message is not None, "task.created message should be broadcast"
        assert message["type"] == "task.created", "Message type must be 'task.created'"

    @pytest.mark.asyncio
    async def test_task_created_payload_has_all_task_fields(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify task.created payload includes all Task interface fields.
        Status: ⚠️ MAY FAIL - Depends on backend implementing all fields.

        Frontend expects complete Task object in payload.
        Backend should include:
        - All required fields: id, title, status, priority, git_branch_id
        - All optional fields that were set
        - Computed fields: subtask_count, completed_subtasks
        - project_id (currently missing - MISMATCH #1)
        """
        task_payload = {
            "id": str(uuid4()),
            "title": "New Task",
            "description": "Task description",
            "status": "todo",
            "priority": "high",
            "assignees": ["@coding-agent"],
            "labels": ["feature"],
            "git_branch_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "progress_percentage": 0,
        }

        await ws_broadcaster.broadcast(
            {
                "type": "task.created",
                "payload": task_payload,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.created")
        payload = message["payload"]

        # Verify required fields
        required_fields = ["id", "title", "status", "priority", "git_branch_id"]
        for field in required_fields:
            assert field in payload, f"task.created payload must include '{field}'"

        # Verify assignees array format
        if "assignees" in payload:
            assert isinstance(payload["assignees"], list), "assignees must be array"
            for assignee in payload["assignees"]:
                assert assignee.startswith("@"), (
                    f"Assignee '{assignee}' must have @ prefix"
                )

    @pytest.mark.xfail(
        reason="MISMATCH #1: project_id not included in WebSocket messages"
    )
    @pytest.mark.asyncio
    async def test_task_created_payload_includes_project_id(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify task.created payload includes project_id field.
        Status: ❌ WILL FAIL - Backend doesn't include project_id in messages.

        Frontend needs project_id to:
        - Filter tasks by project
        - Update project-specific UI components
        - Maintain consistent state

        Fix required: Include project_id in all task-related WebSocket messages.
        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-1
        """
        await ws_broadcaster.broadcast(
            {
                "type": "task.created",
                "payload": {
                    "id": str(uuid4()),
                    "title": "New Task",
                    "git_branch_id": str(uuid4()),
                    # project_id is missing!
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.created")
        payload = message["payload"]

        assert "project_id" in payload, (
            "task.created payload MUST include 'project_id' for frontend filtering"
        )
        assert isinstance(payload["project_id"], str), "project_id must be string"


class TestTaskUpdatedMessage:
    """Test task.updated WebSocket message format."""

    @pytest.mark.asyncio
    async def test_task_updated_message_includes_changed_fields(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify task.updated message includes all changed fields.
        Status: ✅ SHOULD PASS - Message should contain updated task state.

        Frontend expects complete updated task object to:
        - Update UI with new values
        - Maintain consistency
        - Show real-time changes to other users
        """
        updated_task = {
            "id": str(uuid4()),
            "title": "Updated Task Title",
            "status": "in_progress",
            "progress_percentage": 50,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        await ws_broadcaster.broadcast(
            {
                "type": "task.updated",
                "payload": updated_task,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.updated")
        payload = message["payload"]

        # Verify critical update fields are present
        assert "id" in payload, "task.updated must include task id"
        assert "updated_at" in payload, "task.updated must include updated_at timestamp"

    @pytest.mark.xfail(reason="MISMATCH #2/#3: Subtask counts not included in messages")
    @pytest.mark.asyncio
    async def test_task_updated_includes_subtask_counts(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify task.updated includes computed subtask count fields.
        Status: ❌ WILL FAIL - Backend doesn't compute subtask counts.

        Frontend needs:
        - subtask_count: Total number of subtasks
        - completed_subtasks: Number of completed subtasks

        These fields are critical for:
        - Progress visualization
        - Task list display
        - Completion percentage calculation

        Fix required: Compute and include subtask counts in WebSocket messages.
        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-2-3
        """
        await ws_broadcaster.broadcast(
            {
                "type": "task.updated",
                "payload": {
                    "id": str(uuid4()),
                    "title": "Task with Subtasks",
                    "status": "in_progress",
                    "progress_percentage": 33,
                    # subtask_count is missing!
                    # completed_subtasks is missing!
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.updated")
        payload = message["payload"]

        assert "subtask_count" in payload, (
            "task.updated MUST include 'subtask_count' for progress tracking"
        )
        assert "completed_subtasks" in payload, (
            "task.updated MUST include 'completed_subtasks' for progress visualization"
        )
        assert isinstance(payload["subtask_count"], int), (
            "subtask_count must be integer"
        )
        assert isinstance(payload["completed_subtasks"], int), (
            "completed_subtasks must be integer"
        )


class TestSubtaskMessages:
    """Test subtask-related WebSocket message formats."""

    @pytest.mark.asyncio
    async def test_subtask_created_message_structure(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify subtask.created message has correct structure.
        Status: ✅ SHOULD PASS - Basic subtask message structure.
        """
        subtask_payload = {
            "id": str(uuid4()),
            "task_id": str(uuid4()),
            "title": "New Subtask",
            "status": "todo",
            "priority": "medium",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        await ws_broadcaster.broadcast(
            {
                "type": "subtask.created",
                "payload": subtask_payload,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("subtask.created")
        assert message is not None, "subtask.created message should be broadcast"
        assert message["type"] == "subtask.created"

        payload = message["payload"]
        assert "id" in payload, "subtask must have id"
        assert "task_id" in payload, "subtask must have task_id (parent reference)"
        assert "title" in payload, "subtask must have title"

    @pytest.mark.asyncio
    async def test_subtask_created_triggers_parent_update(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify creating subtask triggers parent task update message.
        Status: ⚠️ MAY FAIL - Depends on backend implementing cascade updates.

        When a subtask is created:
        1. subtask.created message sent
        2. task.updated message sent (parent task with updated counts)

        This ensures frontend has consistent state.
        """
        task_id = str(uuid4())

        # Subtask created
        await ws_broadcaster.broadcast(
            {
                "type": "subtask.created",
                "payload": {
                    "id": str(uuid4()),
                    "task_id": task_id,
                    "title": "New Subtask",
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        # Parent task should be updated
        await ws_broadcaster.broadcast(
            {
                "type": "task.updated",
                "payload": {
                    "id": task_id,
                    "subtask_count": 1,  # Updated count
                    "completed_subtasks": 0,  # Updated count
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        # Verify both messages were sent
        subtask_messages = ws_broadcaster.get_messages_by_type("subtask.created")
        task_messages = ws_broadcaster.get_messages_by_type("task.updated")

        assert len(subtask_messages) > 0, "subtask.created message should be sent"
        assert len(task_messages) > 0, (
            "task.updated message should be sent when subtask is created (cascade update)"
        )


class TestContextSyncedMessage:
    """Test context.synced WebSocket message format."""

    @pytest.mark.asyncio
    async def test_context_synced_message_after_subtask_changes(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify context.synced message is sent after subtask changes.
        Status: ⚠️ MAY FAIL - Depends on context sync implementation.

        When subtasks are created/updated/deleted:
        1. Subtask operation completes
        2. Parent task context is updated
        3. context.synced message broadcast with updated task data

        This keeps frontend task context in sync with backend.
        """
        task_id = str(uuid4())

        # Simulate context sync after subtask change
        await ws_broadcaster.broadcast(
            {
                "type": "context.synced",
                "payload": {
                    "task_id": task_id,
                    "context_data": {
                        "subtask_count": 3,
                        "completed_subtasks": 1,
                        "progress_percentage": 33,
                    },
                    "synced_at": datetime.utcnow().isoformat() + "Z",
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("context.synced")
        assert message is not None, "context.synced message should be broadcast"
        assert message["type"] == "context.synced"

        payload = message["payload"]
        assert "task_id" in payload, "context.synced must include task_id"
        assert "context_data" in payload, "context.synced must include context_data"

    @pytest.mark.xfail(reason="Context sync implementation may not include all fields")
    @pytest.mark.asyncio
    async def test_context_synced_includes_critical_counts(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify context.synced includes critical count fields.
        Status: ❌ MAY FAIL - Context sync may not include computed counts.

        context.synced should include:
        - subtask_count: Updated total count
        - completed_subtasks: Updated completed count
        - progress_percentage: Recalculated progress

        This ensures frontend has accurate data after any context changes.
        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-2-3
        """
        await ws_broadcaster.broadcast(
            {
                "type": "context.synced",
                "payload": {
                    "task_id": str(uuid4()),
                    "context_data": {
                        # These fields might be missing!
                        "subtask_count": 5,
                        "completed_subtasks": 3,
                        "progress_percentage": 60,
                    },
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("context.synced")
        context_data = message["payload"]["context_data"]

        assert "subtask_count" in context_data, (
            "context.synced MUST include subtask_count"
        )
        assert "completed_subtasks" in context_data, (
            "context.synced MUST include completed_subtasks"
        )
        assert "progress_percentage" in context_data, (
            "context.synced MUST include progress_percentage"
        )


class TestWebSocketFieldNaming:
    """Test WebSocket message field naming conventions."""

    @pytest.mark.xfail(
        reason="MISMATCH #4/#5: Field naming inconsistency (camelCase vs snake_case)"
    )
    @pytest.mark.asyncio
    async def test_websocket_uses_snake_case_consistently(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify WebSocket messages use snake_case for all fields consistently.
        Status: ❌ WILL FAIL - Backend may use camelCase in some fields.

        Backend to_dict() converts:
        - estimated_effort → estimatedEffort (camelCase)
        - due_date → dueDate (camelCase)

        Frontend expects snake_case:
        - estimated_effort (snake_case)
        - due_date (snake_case)

        Impact: Inconsistent naming causes frontend parsing issues.
        Fix required: Use snake_case consistently in WebSocket messages.

        Reference: ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md#mismatch-4-5
        """
        await ws_broadcaster.broadcast(
            {
                "type": "task.created",
                "payload": {
                    "id": str(uuid4()),
                    "title": "Task",
                    "estimated_effort": "2 hours",  # Should be snake_case
                    "due_date": "2025-12-31",  # Should be snake_case
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.created")
        payload = message["payload"]

        # Verify snake_case is used
        if "estimated_effort" in payload or "estimatedEffort" in payload:
            assert "estimated_effort" in payload, (
                "WebSocket messages should use 'estimated_effort' (snake_case)"
            )
            assert "estimatedEffort" not in payload, (
                "WebSocket messages should NOT use 'estimatedEffort' (camelCase)"
            )

        if "due_date" in payload or "dueDate" in payload:
            assert "due_date" in payload, (
                "WebSocket messages should use 'due_date' (snake_case)"
            )
            assert "dueDate" not in payload, (
                "WebSocket messages should NOT use 'dueDate' (camelCase)"
            )


class TestWebSocketAssigneeFormat:
    """Test assignee format in WebSocket messages."""

    @pytest.mark.asyncio
    async def test_websocket_assignees_have_at_prefix(
        self, ws_broadcaster: MockWebSocketBroadcaster
    ):
        """
        Verify assignees in WebSocket messages have @ prefix.
        Status: ✅ SHOULD PASS - Confirmed requirement.

        All assignees should have @ prefix consistently:
        - "@coding-agent"
        - "@test-orchestrator-agent"
        - etc.
        """
        await ws_broadcaster.broadcast(
            {
                "type": "task.created",
                "payload": {
                    "id": str(uuid4()),
                    "title": "Task",
                    "assignees": ["@coding-agent", "@debugger-agent"],
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        message = ws_broadcaster.get_latest_message("task.created")
        payload = message["payload"]

        if "assignees" in payload:
            for assignee in payload["assignees"]:
                assert assignee.startswith("@"), (
                    f"Assignee '{assignee}' in WebSocket message must have @ prefix"
                )
