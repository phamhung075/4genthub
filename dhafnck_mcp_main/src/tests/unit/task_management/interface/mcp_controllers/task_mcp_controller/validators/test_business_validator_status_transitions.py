"""
Test for Business Validator status transition fix.

Tests the fix for allowing in_progress to in_progress status transitions
that was needed to allow task detail updates without status changes.
"""

import pytest
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.validators.business_validator import BusinessValidator
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter


class TestBusinessValidatorStatusTransitions:
    """Test business validator status transition validation."""

    @pytest.fixture
    def response_formatter(self):
        """Create response formatter for tests."""
        return StandardResponseFormatter()

    @pytest.fixture
    def validator(self, response_formatter):
        """Create business validator instance."""
        return BusinessValidator(response_formatter)

    def test_in_progress_to_in_progress_transition_allowed(self, validator):
        """Test that in_progress to in_progress transition is allowed."""
        # This is the specific fix - allowing in_progress tasks to be updated
        # while remaining in_progress status
        assert validator._is_valid_status_transition("in_progress", "in_progress") == True

    def test_in_progress_valid_transitions_includes_in_progress(self, validator):
        """Test that valid transitions from in_progress includes in_progress."""
        valid_transitions = validator._get_valid_transitions("in_progress")
        assert "in_progress" in valid_transitions
        assert "completed" in valid_transitions
        assert "blocked" in valid_transitions
        assert "pending" in valid_transitions

    def test_task_update_with_in_progress_to_in_progress_succeeds(self, validator):
        """Test that task update validation succeeds for in_progress to in_progress."""
        current_task_data = {
            "status": "in_progress",
            "priority": "medium",
            "title": "Test task"
        }

        # This should NOT create a business rule violation
        is_valid, error = validator.validate_task_update_rules(
            task_id="test-123",
            current_task_data=current_task_data,
            status="in_progress"  # Same status - this should be allowed now
        )

        assert is_valid == True
        assert error is None

    def test_other_status_transitions_still_work(self, validator):
        """Test that other valid status transitions still work."""
        # Test pending to in_progress
        assert validator._is_valid_status_transition("pending", "in_progress") == True

        # Test in_progress to completed
        assert validator._is_valid_status_transition("in_progress", "completed") == True

        # Test blocked to in_progress
        assert validator._is_valid_status_transition("blocked", "in_progress") == True

    def test_invalid_transitions_still_blocked(self, validator):
        """Test that invalid transitions are still properly blocked."""
        # Test some invalid transitions to ensure we didn't break validation
        assert validator._is_valid_status_transition("completed", "blocked") == False
        assert validator._is_valid_status_transition("cancelled", "completed") == False

    def test_case_insensitive_status_transitions(self, validator):
        """Test that status transitions are case insensitive."""
        # Test case variations
        assert validator._is_valid_status_transition("IN_PROGRESS", "in_progress") == True
        assert validator._is_valid_status_transition("In_Progress", "IN_PROGRESS") == True
        assert validator._is_valid_status_transition("in_progress", "COMPLETED") == True