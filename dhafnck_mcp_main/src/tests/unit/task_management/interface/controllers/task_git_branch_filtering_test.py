"""
Git Branch Task Filtering Test Suite

Tests to verify that task listing properly filters tasks by git branch ID.
This test file specifically addresses the issue where clicking on a git branch
in the sidebar shows all tasks instead of just the tasks for that specific branch.

Test cases:
1. List tasks for specific branch returns only tasks for that branch
2. List tasks for different branches returns different task sets
3. Tasks from other branches are not included in branch-specific queries
4. Empty branches return no tasks
5. Invalid branch IDs handle appropriately
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import uuid

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.handlers.search_handler import SearchHandler
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter


class TestTaskGitBranchFiltering:
    """Test cases for git branch-specific task filtering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=TaskFacadeFactory)
        self.mock_facade = Mock(spec=TaskApplicationFacade)
        self.mock_facade_factory.create_task_facade.return_value = self.mock_facade
        self.mock_facade_factory.create_task_facade_with_git_branch_id.return_value = self.mock_facade
        
        self.controller = TaskMCPController(self.mock_facade_factory)
        self.response_formatter = StandardResponseFormatter()
        self.search_handler = SearchHandler(self.response_formatter)
        
        # Sample test data
        self.branch_a_id = "550e8400-e29b-41d4-a716-446655440001"
        self.branch_b_id = "550e8400-e29b-41d4-a716-446655440002"
        self.branch_c_id = "550e8400-e29b-41d4-a716-446655440003"
        
        self.tasks_branch_a = [
            {"id": "task-a1", "title": "Task A1", "git_branch_id": self.branch_a_id, "status": "todo"},
            {"id": "task-a2", "title": "Task A2", "git_branch_id": self.branch_a_id, "status": "in_progress"}
        ]
        
        self.tasks_branch_b = [
            {"id": "task-b1", "title": "Task B1", "git_branch_id": self.branch_b_id, "status": "todo"},
            {"id": "task-b2", "title": "Task B2", "git_branch_id": self.branch_b_id, "status": "done"}
        ]
        
        self.all_tasks = self.tasks_branch_a + self.tasks_branch_b
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_list_tasks_filters_by_branch_id(self, mock_get_auth_user_id):
        """Test that listing tasks with git_branch_id returns only tasks for that branch.
        
        This is the core test that should FAIL initially, demonstrating the bug
        where all tasks are returned regardless of branch filter.
        """
        mock_get_auth_user_id.return_value = "user-123"
        
        # Configure mock to return only branch A tasks when filtered by branch A
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": self.tasks_branch_a  # Should return only branch A tasks
        }
        
        # Act: List tasks for branch A
        result = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None,
            priority=None,
            assignee=None,
            tag=None,
            git_branch_id=self.branch_a_id,  # Filter by branch A
            limit=50,
            offset=0
        )
        
        # Assert: Verify the facade was called with the correct git_branch_id filter
        self.mock_facade.list_tasks.assert_called_once()
        call_args = self.mock_facade.list_tasks.call_args[0][0]  # Get the ListTasksRequest object
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.git_branch_id == self.branch_a_id, "The git_branch_id filter was not applied correctly"
        
        # Assert: Result should contain only branch A tasks
        assert result["success"] is True
        assert "tasks" in result
        returned_tasks = result["tasks"]
        
        # Critical assertion: Should only contain tasks from branch A
        assert len(returned_tasks) == 2, f"Expected 2 tasks for branch A, got {len(returned_tasks)}"
        
        # Verify all returned tasks belong to branch A
        for task in returned_tasks:
            assert task["git_branch_id"] == self.branch_a_id, \
                f"Task {task['id']} has wrong branch_id: {task.get('git_branch_id')} (expected {self.branch_a_id})"
        
        # Verify no tasks from other branches are included
        task_ids = [task["id"] for task in returned_tasks]
        assert "task-a1" in task_ids
        assert "task-a2" in task_ids
        assert "task-b1" not in task_ids, "Task from branch B should not be in branch A results"
        assert "task-b2" not in task_ids, "Task from branch B should not be in branch A results"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_list_tasks_different_branches_return_different_results(self, mock_get_auth_user_id):
        """Test that different branches return different task sets."""
        mock_get_auth_user_id.return_value = "user-123"
        
        # Configure mock to return different results for different branches
        def mock_list_tasks_side_effect(request):
            if pytest_request.git_branch_id == self.branch_a_id:
                return {"success": True, "tasks": self.tasks_branch_a}
            elif pytest_request.git_branch_id == self.branch_b_id:
                return {"success": True, "tasks": self.tasks_branch_b}
            else:
                return {"success": True, "tasks": []}
        
        self.mock_facade.list_tasks.side_effect = mock_list_tasks_side_effect
        
        # Test branch A
        result_a = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None, priority=None, assignee=None, tag=None,
            git_branch_id=self.branch_a_id,
            limit=50, offset=0
        )
        
        # Test branch B  
        result_b = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None, priority=None, assignee=None, tag=None,
            git_branch_id=self.branch_b_id,
            limit=50, offset=0
        )
        
        # Assert: Results should be different for different branches
        assert result_a["success"] is True
        assert result_b["success"] is True
        
        tasks_a = result_a["tasks"]
        tasks_b = result_b["tasks"]
        
        # Should have different number of tasks (both have 2 in our test data, but contents differ)
        assert len(tasks_a) == 2
        assert len(tasks_b) == 2
        
        # Tasks should be completely different sets
        task_ids_a = {task["id"] for task in tasks_a}
        task_ids_b = {task["id"] for task in tasks_b}
        
        assert task_ids_a.isdisjoint(task_ids_b), "Branch A and B should have completely different tasks"
        assert task_ids_a == {"task-a1", "task-a2"}
        assert task_ids_b == {"task-b1", "task-b2"}
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_list_tasks_empty_branch_returns_no_tasks(self, mock_get_auth_user_id):
        """Test that an empty branch returns no tasks."""
        mock_get_auth_user_id.return_value = "user-123"
        
        # Configure mock to return empty result for branch C (empty branch)
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": []
        }
        
        # Act: List tasks for empty branch
        result = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None, priority=None, assignee=None, tag=None,
            git_branch_id=self.branch_c_id,  # Empty branch
            limit=50, offset=0
        )
        
        # Assert: Should return success with empty task list
        assert result["success"] is True
        assert "tasks" in result
        assert len(result["tasks"]) == 0
        
        # Verify the facade was called with the correct git_branch_id
        self.mock_facade.list_tasks.assert_called_once()
        call_args = self.mock_facade.list_tasks.call_args[0][0]
        assert call_args.git_branch_id == self.branch_c_id
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')  
    def test_list_tasks_without_branch_filter_may_return_all_tasks(self, mock_get_auth_user_id):
        """Test that listing without branch filter may return tasks from all branches.
        
        This is acceptable behavior - when no branch is specified, it's reasonable
        to return all tasks. The bug is specifically when a branch IS specified
        but tasks from other branches are still returned.
        """
        mock_get_auth_user_id.return_value = "user-123"
        
        # Configure mock to return all tasks when no branch filter is applied
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": self.all_tasks
        }
        
        # Act: List tasks without branch filter
        result = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None, priority=None, assignee=None, tag=None,
            git_branch_id=None,  # No branch filter
            limit=50, offset=0
        )
        
        # Assert: Should return all tasks (this behavior is acceptable)
        assert result["success"] is True
        assert len(result["tasks"]) == 4  # All tasks from both branches
        
        # Verify the facade was called with no git_branch_id filter
        self.mock_facade.list_tasks.assert_called_once()
        call_args = self.mock_facade.list_tasks.call_args[0][0]
        assert call_args.git_branch_id is None
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_list_tasks_invalid_branch_id_returns_empty_or_error(self, mock_get_auth_user_id):
        """Test handling of invalid branch IDs."""
        mock_get_auth_user_id.return_value = "user-123"
        
        invalid_branch_id = "invalid-branch-id-12345"
        
        # Configure mock to return empty result for invalid branch
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": []
        }
        
        # Act: List tasks for invalid branch
        result = self.search_handler.list_tasks(
            facade=self.mock_facade,
            status=None, priority=None, assignee=None, tag=None,
            git_branch_id=invalid_branch_id,
            limit=50, offset=0
        )
        
        # Assert: Should handle gracefully (empty result is acceptable)
        assert result["success"] is True
        assert len(result["tasks"]) == 0
        
        # Verify the facade was called with the invalid git_branch_id
        self.mock_facade.list_tasks.assert_called_once()
        call_args = self.mock_facade.list_tasks.call_args[0][0]
        assert call_args.git_branch_id == invalid_branch_id


class TestTaskGitBranchFilteringIntegration:
    """Integration tests for the full MCP controller task filtering."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_facade_factory = Mock(spec=TaskFacadeFactory)
        self.mock_facade = Mock(spec=TaskApplicationFacade)
        self.mock_facade_factory.create_task_facade_with_git_branch_id.return_value = self.mock_facade
        
        self.controller = TaskMCPController(self.mock_facade_factory)
        
        self.test_branch_id = "550e8400-e29b-41d4-a716-446655440001"
        self.test_tasks = [
            {"id": "task-1", "title": "Test Task 1", "git_branch_id": self.test_branch_id}
        ]
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_full_mcp_controller_list_action_filters_by_branch(self, mock_get_auth_user_id):
        """Integration test for full MCP controller list action with branch filtering.
        
        This test simulates the exact MCP call that would come from the frontend
        when clicking on a git branch in the sidebar.
        """
        mock_get_auth_user_id.return_value = "user-123"
        
        # Configure mock facade to return branch-specific tasks
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": self.test_tasks
        }
        
        # Simulate the MCP call parameters that come from the frontend
        mcp_params = {
            "action": "list",
            "git_branch_id": self.test_branch_id,
            "status": None,
            "priority": None,
            "assignees": None,
            "labels": None,
            "limit": 50
        }
        
        # Act: Call the controller's manage_task method (this is what MCP calls)
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = self.controller.manage_task(**mcp_params)
        
        # Assert: Verify the list_tasks was called on the facade
        self.mock_facade.list_tasks.assert_called_once()
        
        # Verify the ListTasksRequest was created with correct git_branch_id
        call_args = self.mock_facade.list_tasks.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.git_branch_id == self.test_branch_id, \
            f"Expected git_branch_id {self.test_branch_id}, got {call_args.git_branch_id}"
        
        # Assert: Result should be successful and contain the filtered tasks
        assert result["success"] is True
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == "task-1"


if __name__ == "__main__":
    # Run the specific failing test to demonstrate the issue
    pytest.main([
        __file__ + "::TestTaskGitBranchFiltering::test_list_tasks_filters_by_branch_id",
        "-v", "--tb=short"
    ])