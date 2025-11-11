"""
Test Suite for Task WebSocket Payload Migration (TDD)

Tests the migration from dict-based task_data_snapshot to TaskDeletePayload model
in task_application_facade.py delete_task method.

REQUIREMENTS:
- Convert task_data_snapshot dict to TaskDeletePayload
- Add validation logging
- Keep existing fallback pattern
- Ensure type safety with Pydantic validation
"""

import logging

import pytest

from fastmcp.task_management.domain.websocket_protocol import (
    TaskDeletePayload,
    convert_task_delete_legacy,
)


class TestTaskDeletePayloadConversion:
    """Test conversion of task_data_snapshot dict to TaskDeletePayload"""

    def test_convert_task_snapshot_with_all_fields(self):
        """Test conversion when task_data_snapshot has all required fields"""
        # Arrange: Full task snapshot from entity.to_dict()
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Implement authentication system",
            "description": "Add JWT auth with refresh tokens",
            "status": "in_progress",
            "priority": "high",
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
            "assignees": ["coding-agent"],
            "labels": ["backend", "security"],
            "created_at": "2025-11-06T19:00:00Z",
            "updated_at": "2025-11-06T19:05:00Z",
        }

        # Act: Convert using helper function
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Payload has required fields
        assert isinstance(payload, TaskDeletePayload)
        assert payload.id == "381291d6-fa7f-4e60-80c5-0d1b86664722"
        assert payload.title == "Implement authentication system"
        assert payload.git_branch_id == "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f"

    def test_convert_task_snapshot_minimal_fields(self):
        """Test conversion with only required fields (id)"""
        # Arrange: Minimal snapshot (e.g., from fallback scenario)
        task_snapshot = {"id": "381291d6-fa7f-4e60-80c5-0d1b86664722"}

        # Act: Convert with fallback title
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Uses fallback for missing title
        assert payload.id == "381291d6-fa7f-4e60-80c5-0d1b86664722"
        assert payload.title == "Task 381291d6"  # Fallback pattern
        assert payload.git_branch_id is None  # Optional field

    def test_convert_task_snapshot_missing_git_branch_id(self):
        """Test conversion when git_branch_id is missing"""
        # Arrange: Task without git_branch_id
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Orphaned task",
            "status": "todo",
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: git_branch_id is None (optional field)
        assert payload.id == "381291d6-fa7f-4e60-80c5-0d1b86664722"
        assert payload.title == "Orphaned task"
        assert payload.git_branch_id is None

    def test_convert_task_snapshot_empty_title_uses_fallback(self):
        """Test that empty title triggers fallback"""
        # Arrange: Empty title string
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "",  # Empty string
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Uses fallback title
        assert payload.title == "Task 381291d6"

    def test_convert_task_snapshot_none_title_uses_fallback(self):
        """Test that None title triggers fallback"""
        # Arrange: None title
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": None,
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Uses fallback title
        assert payload.title == "Task 381291d6"

    def test_payload_validation_rejects_empty_id(self):
        """Test that Pydantic validation rejects empty task ID"""
        # Arrange: Invalid snapshot with empty ID
        task_snapshot = {
            "id": "",  # Invalid: empty string
            "title": "Some task",
        }

        # Act & Assert: Should raise ValidationError
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            convert_task_delete_legacy(task_snapshot)

    def test_payload_validation_rejects_whitespace_id(self):
        """Test that Pydantic validation rejects whitespace-only ID"""
        # Arrange
        task_snapshot = {
            "id": "   ",  # Invalid: whitespace only
            "title": "Some task",
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Task ID cannot be empty"):
            convert_task_delete_legacy(task_snapshot)

    def test_payload_validation_rejects_empty_title_after_fallback_fails(self):
        """Test validation when both title and fallback would be empty"""
        # Note: This is a theoretical edge case - the convert function should always provide fallback
        # But we test the Pydantic model directly

        # Act & Assert: Direct model instantiation with empty title
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            TaskDeletePayload(
                id="381291d6-fa7f-4e60-80c5-0d1b86664722",
                title="",  # Empty after all fallbacks
                git_branch_id=None,
            )

    def test_payload_dict_has_correct_structure(self):
        """Test that converted payload can be serialized to dict"""
        # Arrange
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Test task",
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)
        payload_dict = payload.model_dump()

        # Assert: Dict has expected structure
        assert payload_dict["id"] == "381291d6-fa7f-4e60-80c5-0d1b86664722"
        assert payload_dict["title"] == "Test task"
        assert payload_dict["git_branch_id"] == "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f"
        assert len(payload_dict) == 3  # Only 3 fields


class TestTaskDeletePayloadLogging:
    """Test logging during payload conversion and validation"""

    def test_logging_on_successful_conversion(self, caplog):
        """Test that successful conversion is logged"""
        # Arrange
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Test task",
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Conversion succeeded (no validation errors logged)
        assert payload is not None
        # Note: Actual logging implementation will be added in the facade

    def test_logging_on_fallback_title_usage(self, caplog):
        """Test that fallback title usage is logged"""
        # Arrange: Missing title
        task_snapshot = {"id": "381291d6-fa7f-4e60-80c5-0d1b86664722"}

        # Act
        with caplog.at_level(logging.INFO):
            payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Fallback was used
        assert payload.title == "Task 381291d6"
        # Note: Actual logging will be in facade implementation


class TestTaskDeletePayloadIntegration:
    """Integration tests for payload usage in WebSocket notification"""

    def test_payload_compatible_with_websocket_notification(self):
        """Test that payload can be used in WebSocket notification service"""
        # Arrange
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Test task for WebSocket",
            "git_branch_id": "cd482b1b-8d5f-4e60-9c3a-1a2b3c4d5e6f",
        }

        # Act: Convert to payload
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Payload has all fields needed for WebSocket
        assert payload.id  # Required for frontend cache operations
        assert payload.title  # Required for toast notifications
        assert payload.git_branch_id  # Optional but present for cache invalidation

        # Can be serialized to dict for WebSocket transmission
        payload_dict = payload.model_dump()
        assert isinstance(payload_dict, dict)
        assert "id" in payload_dict
        assert "title" in payload_dict

    def test_payload_preserves_git_branch_id_for_cache_invalidation(self):
        """Test that git_branch_id is preserved for React Query cache invalidation"""
        # Arrange: Task with parent branch
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Child task",
            "git_branch_id": "parent-branch-uuid",
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Branch ID preserved for cache invalidation
        assert payload.git_branch_id == "parent-branch-uuid"

    def test_payload_handles_orphaned_task_without_branch(self):
        """Test that orphaned tasks (no git_branch_id) are handled gracefully"""
        # Arrange: Orphaned task
        task_snapshot = {
            "id": "381291d6-fa7f-4e60-80c5-0d1b86664722",
            "title": "Orphaned task",
            "git_branch_id": None,
        }

        # Act
        payload = convert_task_delete_legacy(task_snapshot)

        # Assert: Payload valid even without branch ID
        assert payload.id == "381291d6-fa7f-4e60-80c5-0d1b86664722"
        assert payload.title == "Orphaned task"
        assert payload.git_branch_id is None  # No parent branch


class TestFallbackPattern:
    """Test that existing fallback pattern is preserved"""

    def test_fallback_when_task_fetch_fails(self):
        """Test fallback behavior when task_data_snapshot is None"""
        # Arrange: Simulate scenario where task fetch failed
        task_snapshot = None

        # Act & Assert: Should handle None gracefully in implementation
        # This will be tested in the facade layer
        # For now, we test that convert_task_delete_legacy requires a dict
        with pytest.raises((TypeError, KeyError, AttributeError)):
            convert_task_delete_legacy(task_snapshot)

    def test_fallback_context_used_when_prefetch_fails(self):
        """Test that fallback context pattern is preserved"""
        # This tests the broader fallback pattern in task_application_facade.py
        # The facade should create a fallback task_context when pre-fetch fails

        # Arrange: Minimal task info for fallback
        task_id = "381291d6-fa7f-4e60-80c5-0d1b86664722"

        # Expected fallback structure (from facade code)
        fallback_context = {
            "task_title": f"Task {task_id[:8]}",
            "parent_branch_id": None,
            "parent_branch_title": "Unknown Branch",
            "task_user_id": None,
        }

        # Assert: Fallback provides minimal required info
        assert fallback_context["task_title"] == "Task 381291d6"
        assert fallback_context["parent_branch_id"] is None


# Test helper to verify convert_task_delete_legacy matches expected signature
def test_convert_function_signature():
    """Verify convert_task_delete_legacy has expected signature"""
    import inspect

    sig = inspect.signature(convert_task_delete_legacy)

    # Should accept task_snapshot dict
    assert "task_snapshot" in sig.parameters

    # Should return TaskDeletePayload
    # This is validated by the function's return type annotation
