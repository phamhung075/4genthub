"""
Unit Tests for Response Validator Middleware

Tests the validation logic for HTTP responses and data structures.
"""

import pytest

from fastmcp.middleware.response_validator_middleware import (
    ResponseValidator,
)


class TestResponseValidator:
    """Test the ResponseValidator class"""

    def test_validate_complete_task(self):
        """Test validation of a complete, valid task"""
        task_data = {
            "id": "task-123",
            "title": "Test Task",
            "status": "in_progress",
            "priority": "high",
            "assignees": ["@coding-agent"],
            "labels": ["bug", "urgent"],
            "subtask_count": 5,
            "completed_subtasks": 2,
            "progress_percentage": 40,
            "progress_count": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
            "git_branch_id": "branch-456",
            "project_id": "project-789",
        }

        issues = ResponseValidator.validate_task_response(task_data)

        # Should have no errors for complete, valid task
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Valid task should have no errors: {[e.message for e in errors]}"

    def test_validate_task_missing_required_field(self):
        """Test validation detects missing required fields"""
        task_data = {
            # Missing: id (required, no default)
            "title": "Test Task",
            "status": "in_progress",
            "priority": "high",
            "assignees": [],
            "labels": [],
            "subtask_count": 5,
            "completed_subtasks": 2,
            "progress_percentage": 40,
            "progress_count": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
        }

        issues = ResponseValidator.validate_task_response(task_data)

        # Should detect missing id field
        errors = [i for i in issues if i.severity == "error" and "id" in i.field_path]
        assert len(errors) > 0, "Should detect missing id field"
        assert errors[0].issue_type == "missing"

    def test_validate_task_wrong_type(self):
        """Test validation detects wrong data types"""
        task_data = {
            "id": "task-123",
            "title": "Test Task",
            "status": "in_progress",
            "priority": "high",
            "assignees": "@coding-agent",  # Wrong: should be list, not string
            "labels": [],
            "subtask_count": "5",  # Wrong: should be int, not string
            "completed_subtasks": 2,
            "progress_percentage": 40,
            "progress_count": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
        }

        issues = ResponseValidator.validate_task_response(task_data)

        # Should detect wrong types
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 2, "Should detect at least 2 type errors"

        # Check for specific errors
        assignees_error = [i for i in errors if "assignees" in i.field_path]
        assert len(assignees_error) > 0, "Should detect assignees type error"

        subtask_count_error = [i for i in errors if "subtask_count" in i.field_path]
        assert len(subtask_count_error) > 0, "Should detect subtask_count type error"

    def test_validate_task_null_required_field(self):
        """Test validation detects null values in required fields"""
        task_data = {
            "id": "task-123",
            "title": None,  # Required field is null
            "status": "in_progress",
            "priority": "high",
            "assignees": [],
            "labels": [],
            "subtask_count": 5,
            "completed_subtasks": 2,
            "progress_percentage": 40,
            "progress_count": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
        }

        issues = ResponseValidator.validate_task_response(task_data)

        # Should detect null title
        errors = [i for i in issues if i.severity == "error" and "title" in i.field_path]
        assert len(errors) > 0, "Should detect null title"

    def test_validate_subtask_complete(self):
        """Test validation of complete, valid subtask"""
        subtask_data = {
            "id": "subtask-123",
            "title": "Test Subtask",
            "status": "done",
            "priority": "medium",
            "parent_task_id": "task-456",
            "assignees": ["@test-agent"],
            "progress_percentage": 100,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
        }

        issues = ResponseValidator.validate_subtask_response(subtask_data)

        # Should have no errors
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Valid subtask should have no errors: {[e.message for e in errors]}"

    def test_validate_subtask_missing_parent_task_id(self):
        """Test validation detects missing parent_task_id in subtask"""
        subtask_data = {
            "id": "subtask-123",
            "title": "Test Subtask",
            "status": "done",
            "priority": "medium",
            # Missing: parent_task_id (required for subtasks)
            "assignees": [],
            "progress_percentage": 100,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
        }

        issues = ResponseValidator.validate_subtask_response(subtask_data)

        # Should detect missing parent_task_id
        errors = [i for i in issues if i.severity == "error" and "parent_task_id" in i.field_path]
        assert len(errors) > 0, "Should detect missing parent_task_id"

    def test_validate_list_response(self):
        """Test validation of list responses"""
        tasks = [
            {
                "id": "task-1",
                "title": "Task 1",
                "status": "todo",
                "priority": "low",
                "assignees": [],
                "labels": [],
                "subtask_count": 0,
                "completed_subtasks": 0,
                "progress_percentage": 0,
                "progress_count": 0,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
            },
            {
                "id": "task-2",
                # Missing title - should be caught
                "status": "in_progress",
                "priority": "high",
                "assignees": ["@coding-agent"],
                "labels": [],
                "subtask_count": 3,
                "completed_subtasks": 1,
                "progress_percentage": 33,
                "progress_count": 1,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T11:00:00Z",
            },
        ]

        issues = ResponseValidator.validate_list_response(
            tasks,
            ResponseValidator.TASK_SCHEMA,
            "task"
        )

        # Should find error in second task
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0, "Should detect error in second task"

        # Check it's from the second task
        task1_errors = [i for i in errors if "task[1]" in i.field_path]
        assert len(task1_errors) > 0, "Error should be from task[1]"

    def test_validate_unexpected_fields(self):
        """Test that unexpected fields are flagged as info"""
        task_data = {
            "id": "task-123",
            "title": "Test Task",
            "status": "in_progress",
            "priority": "high",
            "assignees": [],
            "labels": [],
            "subtask_count": 5,
            "completed_subtasks": 2,
            "progress_percentage": 40,
            "progress_count": 1,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
            "unexpected_field": "This field is not in schema",  # Not in schema
        }

        issues = ResponseValidator.validate_task_response(task_data)

        # Should flag unexpected field as info
        info_issues = [i for i in issues if i.severity == "info"]
        assert len(info_issues) > 0, "Should flag unexpected field"
        assert any("unexpected_field" in i.field_path for i in info_issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
