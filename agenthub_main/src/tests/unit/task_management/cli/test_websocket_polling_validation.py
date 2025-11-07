"""
Unit tests for WebSocket polling CLI Pydantic validation

Tests that poll_mcp_websocket_parallel.py correctly validates
subtask completion payloads using SubtaskCompletePayload Pydantic model.
"""

import pytest
from pydantic import ValidationError

from fastmcp.task_management.domain.websocket_protocol import SubtaskCompletePayload


class TestSubtaskCompletePayloadValidation:
    """Test Pydantic validation for subtask completion payloads"""

    def test_valid_subtask_complete_payload(self):
        """Should validate correct subtask completion payload"""
        valid_payload = SubtaskCompletePayload(
            id="subtask-uuid-123",
            title="Test Subtask",
            status="done",
            task_id="task-uuid-456",
            completion_summary="Successfully completed the feature",
            progress_percentage=100,
            completed_at="2025-11-06T22:00:00Z"
        )

        assert valid_payload.id == "subtask-uuid-123"
        assert valid_payload.title == "Test Subtask"
        assert valid_payload.status == "done"
        assert valid_payload.task_id == "task-uuid-456"
        assert valid_payload.progress_percentage == 100

    def test_minimal_subtask_complete_payload(self):
        """Should validate minimal required fields (id, title, task_id)"""
        minimal_payload = SubtaskCompletePayload(
            id="subtask-uuid-123",
            title="Test Subtask",
            task_id="task-uuid-456"
        )

        # Optional fields should use defaults
        assert minimal_payload.status == "done"  # Default from Literal
        assert minimal_payload.progress_percentage == 100  # Default from Literal
        assert minimal_payload.completion_summary is None
        assert minimal_payload.completed_at is None

    def test_invalid_status_rejected(self):
        """Should reject invalid status (not 'done')"""
        with pytest.raises(ValidationError) as exc_info:
            SubtaskCompletePayload(
                id="subtask-uuid-123",
                title="Test Subtask",
                status="in_progress",  # Invalid - must be 'done'
                task_id="task-uuid-456"
            )

        error = exc_info.value
        assert "status" in str(error)

    def test_invalid_progress_percentage_rejected(self):
        """Should reject progress_percentage not equal to 100"""
        with pytest.raises(ValidationError) as exc_info:
            SubtaskCompletePayload(
                id="subtask-uuid-123",
                title="Test Subtask",
                task_id="task-uuid-456",
                progress_percentage=50  # Invalid - must be 100
            )

        error = exc_info.value
        assert "progress_percentage" in str(error)

    def test_missing_required_id_rejected(self):
        """Should reject payload missing required 'id' field"""
        with pytest.raises(ValidationError) as exc_info:
            SubtaskCompletePayload(
                # Missing id
                title="Test Subtask",
                task_id="task-uuid-456"
            )

        error = exc_info.value
        assert "id" in str(error)

    def test_missing_required_title_rejected(self):
        """Should reject payload missing required 'title' field"""
        with pytest.raises(ValidationError) as exc_info:
            SubtaskCompletePayload(
                id="subtask-uuid-123",
                # Missing title
                task_id="task-uuid-456"
            )

        error = exc_info.value
        assert "title" in str(error)

    def test_missing_required_task_id_rejected(self):
        """Should reject payload missing required 'task_id' field"""
        with pytest.raises(ValidationError) as exc_info:
            SubtaskCompletePayload(
                id="subtask-uuid-123",
                title="Test Subtask"
                # Missing task_id
            )

        error = exc_info.value
        assert "task_id" in str(error)

    def test_cli_simulation_valid_completion(self):
        """Simulate CLI extraction from WebSocket message (valid case)"""
        # Simulated WebSocket message data
        websocket_data = {
            "id": "subtask-abc-123",
            "title": "Implement feature X",
            "status": "done",
            "task_id": "task-def-456",
            "completion_summary": "Feature X implemented with tests",
            "progress_percentage": 100,
            "completed_at": "2025-11-06T22:10:00Z"
        }

        # CLI would extract and validate like this
        try:
            validated_payload = SubtaskCompletePayload(
                id=websocket_data.get("id"),
                title=websocket_data.get("title"),
                status=websocket_data.get("status", "done"),
                task_id=websocket_data.get("task_id"),
                completion_summary=websocket_data.get("completion_summary"),
                progress_percentage=websocket_data.get("progress_percentage", 100),
                completed_at=websocket_data.get("completed_at")
            )

            # Should succeed
            assert validated_payload.id == "subtask-abc-123"
            assert validated_payload.completion_summary == "Feature X implemented with tests"
        except ValidationError:
            pytest.fail("Valid payload should not raise ValidationError")

    def test_cli_simulation_fallback_on_invalid_data(self):
        """Simulate CLI fallback when WebSocket data is invalid"""
        # Malformed WebSocket message (missing task_id)
        websocket_data = {
            "id": "subtask-abc-123",
            "title": "Implement feature X",
            "status": "done",
            # Missing task_id - should fail validation
            "completion_summary": "Feature X implemented"
        }

        # CLI should catch ValidationError and fallback to legacy extraction
        with pytest.raises(ValidationError):
            SubtaskCompletePayload(
                id=websocket_data.get("id"),
                title=websocket_data.get("title"),
                status=websocket_data.get("status", "done"),
                task_id=websocket_data.get("task_id"),  # Will be None - validation fails
                completion_summary=websocket_data.get("completion_summary")
            )

    def test_optional_fields_can_be_none(self):
        """Should allow optional fields to be None"""
        payload = SubtaskCompletePayload(
            id="subtask-uuid-123",
            title="Test Subtask",
            task_id="task-uuid-456",
            completion_summary=None,  # Explicitly None
            completed_at=None  # Explicitly None
        )

        assert payload.completion_summary is None
        assert payload.completed_at is None
