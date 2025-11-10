"""
Unit Tests for WebSocket Message Logger

Tests the WebSocket message validation logic.
"""

import pytest

from fastmcp.middleware.websocket_message_logger import (
    WebSocketMessageLogger,
    WebSocketMessageValidator,
)


class TestWebSocketMessageValidator:
    """Test WebSocket message validation"""

    def test_validate_complete_task_event(self):
        """Test validation of complete task event message"""
        message = {
            "event": "task.created",
            "data": {
                "id": "task-123",
                "title": "Test Task",
                "status": "todo",
                "priority": "high",
                "assignees": ["@coding-agent"],
                "subtask_count": 0,
                "completed_subtasks": 0,
                "progress_percentage": 0,
                "progress_count": 0,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
                "project_id": "project-456",
                "git_branch_id": "branch-789",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) == 0, f"Valid message should have no errors: {errors}"

    def test_validate_missing_event_field(self):
        """Test validation detects missing event field"""
        message = {
            # Missing: event
            "data": {
                "id": "task-123",
                "title": "Test Task",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) > 0, "Should detect missing event field"
        assert any("event" in error for error in errors)

    def test_validate_missing_data_field(self):
        """Test validation detects missing data field"""
        message = {
            "event": "task.created",
            # Missing: data
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) > 0, "Should detect missing data field"
        assert any("data" in error for error in errors)

    def test_validate_task_event_missing_required_fields(self):
        """Test validation detects missing required fields in task event data"""
        message = {
            "event": "task.updated",
            "data": {
                "id": "task-123",
                "title": "Test Task",
                # Missing: status, priority, assignees, subtask_count, etc.
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) > 0, "Should detect missing required fields"

        # Should detect multiple missing fields
        assert any("status" in error for error in errors)
        assert any("priority" in error for error in errors)
        assert any("assignees" in error for error in errors)
        assert any("subtask_count" in error for error in errors)

    def test_validate_task_event_wrong_types(self):
        """Test validation detects wrong data types in task events"""
        message = {
            "event": "task.created",
            "data": {
                "id": "task-123",
                "title": "Test Task",
                "status": "todo",
                "priority": "high",
                "assignees": "@coding-agent",  # Wrong: should be list
                "subtask_count": "5",  # Wrong: should be int
                "completed_subtasks": "2",  # Wrong: should be int
                "progress_percentage": "40",  # Wrong: should be int
                "progress_count": 1,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) >= 4, f"Should detect at least 4 type errors, got {len(errors)}: {errors}"

    def test_validate_subtask_event_complete(self):
        """Test validation of complete subtask event"""
        message = {
            "event": "subtask.created",
            "data": {
                "id": "subtask-123",
                "title": "Test Subtask",
                "status": "todo",
                "priority": "medium",
                "parent_task_id": "task-456",
                "assignees": [],
                "progress_percentage": 0,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) == 0, f"Valid subtask message should have no errors: {errors}"

    def test_validate_subtask_event_missing_parent(self):
        """Test validation detects missing parent_task_id in subtask events"""
        message = {
            "event": "subtask.updated",
            "data": {
                "id": "subtask-123",
                "title": "Test Subtask",
                "status": "in_progress",
                "priority": "medium",
                # Missing: parent_task_id (critical for subtasks!)
                "assignees": [],
                "progress_percentage": 50,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T11:00:00Z",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) > 0, "Should detect missing parent_task_id"
        assert any("parent_task_id" in error for error in errors)

    def test_validate_invalid_subtask_counts(self):
        """Test validation detects when completed_subtasks > subtask_count"""
        message = {
            "event": "task.updated",
            "data": {
                "id": "task-123",
                "title": "Test Task",
                "status": "in_progress",
                "priority": "high",
                "assignees": [],
                "subtask_count": 5,
                "completed_subtasks": 10,  # Invalid: more completed than total!
                "progress_percentage": 200,  # Also wrong
                "progress_count": 1,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T11:00:00Z",
            }
        }

        errors = WebSocketMessageValidator.validate_message(message)

        assert len(errors) > 0, "Should detect invalid subtask counts"
        assert any("completed_subtasks" in error and "exceeds" in error for error in errors)


class TestWebSocketMessageLogger:
    """Test WebSocket message logger"""

    def test_log_message_valid(self):
        """Test logging a valid message"""
        logger = WebSocketMessageLogger()

        errors = logger.log_message(
            event="task.created",
            data={
                "id": "task-123",
                "title": "Test Task",
                "status": "todo",
                "priority": "high",
                "assignees": [],
                "subtask_count": 0,
                "completed_subtasks": 0,
                "progress_percentage": 0,
                "progress_count": 0,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
            },
            user_id="user-456",
            validate=True
        )

        assert len(errors) == 0, f"Valid message should have no errors: {errors}"
        assert logger.message_count == 1
        assert logger.error_count == 0

    def test_log_message_invalid(self):
        """Test logging an invalid message increments error count"""
        logger = WebSocketMessageLogger()

        errors = logger.log_message(
            event="task.created",
            data={
                "id": "task-123",
                # Missing many required fields
            },
            user_id="user-456",
            validate=True
        )

        assert len(errors) > 0, "Invalid message should have errors"
        assert logger.message_count == 1
        assert logger.error_count == 1

    def test_get_stats(self):
        """Test getting logger statistics"""
        logger = WebSocketMessageLogger()

        # Log some messages
        logger.log_message("task.created", {"id": "1", "title": "Task 1", "status": "todo", "priority": "high", "assignees": [], "subtask_count": 0, "completed_subtasks": 0, "progress_percentage": 0, "progress_count": 0, "created_at": "2025-01-15T10:00:00Z", "updated_at": "2025-01-15T10:00:00Z"}, validate=True)
        logger.log_message("task.updated", {"id": "2"}, validate=True)  # Invalid
        logger.log_message("task.deleted", {"id": "3", "title": "Task 3", "status": "done", "priority": "low", "assignees": [], "subtask_count": 0, "completed_subtasks": 0, "progress_percentage": 100, "progress_count": 1, "created_at": "2025-01-15T10:00:00Z", "updated_at": "2025-01-15T11:00:00Z"}, validate=True)

        stats = logger.get_stats()

        assert stats["total_messages"] == 3
        assert stats["validation_errors"] == 1
        assert "error_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
