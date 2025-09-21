#!/usr/bin/env python3
"""Test script to verify progress_history fix in TaskResponse DTO"""

import unittest
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.application.dtos.task.task_response import TaskResponse
from datetime import datetime, timezone

class TestProgressHistoryFix(unittest.TestCase):
    """Test that progress_history is properly returned in TaskResponse"""

    def test_progress_history_in_response(self):
        """Test that progress_history is properly returned in TaskResponse"""
        # Create a task with progress history
        task = Task(
            id=TaskId.from_string("test-task-123"),
            title="Test Task",
            description="Test task with progress history",
            assignees=["coding-agent"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Add progress entries
        task.append_progress("Started working on authentication system")
        task.append_progress("Implemented JWT token generation")
        task.append_progress("Added user login endpoint")

        # Verify task has progress
        self.assertEqual(task.progress_count, 3)
        self.assertEqual(len(task.progress_history), 3)

        # Create TaskResponse from domain entity
        response = TaskResponse.from_domain(task)

        # Verify progress_history is included
        self.assertIsNotNone(response.progress_history)
        self.assertEqual(response.progress_count, 3)

        # Verify details field has formatted text
        self.assertNotEqual(response.details, "")
        self.assertIn("Started working on authentication", response.details)

        # Convert to dict and verify fields are included
        response_dict = response.to_dict()
        self.assertIn("progress_history", response_dict)
        self.assertIn("progress_count", response_dict)
        self.assertIn("details", response_dict)

        self.assertEqual(len(response_dict["progress_history"]), 3)
        self.assertEqual(response_dict["progress_count"], 3)
        self.assertGreater(len(response_dict["details"]), 0)

    def test_empty_progress_history(self):
        """Test TaskResponse with empty progress history"""
        task = Task(
            id=TaskId.from_string("test-task-456"),
            title="Empty Task",
            description="Task with no progress",
            assignees=["coding-agent"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        response = TaskResponse.from_domain(task)

        # Should have empty progress_history but not None
        self.assertEqual(response.progress_history, {})
        self.assertEqual(response.progress_count, 0)
        self.assertEqual(response.details, "")

        response_dict = response.to_dict()
        self.assertEqual(response_dict["progress_history"], {})
        self.assertEqual(response_dict["progress_count"], 0)
        self.assertEqual(response_dict["details"], "")

if __name__ == "__main__":
    unittest.main()