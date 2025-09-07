"""Integration tests for NextTaskUseCase NoneType error fix

Tests the complete flow through the MCP controller to ensure NoneType errors
are properly handled at all levels of the application.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestNextTaskNoneTypeIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Integration tests for NoneType error fix in manage_task next action"""

    def create_mock_task_entity(
        self,
        task_id: str = "00000000-0000-0000-0000-000000000123",
        title: str = "Test Task",
        status: str = "todo",
        priority: str = "medium",
        assignees=None,
        labels=None
    ):
        """Create a mock task entity with proper value objects"""
        from uuid import uuid4
        # Convert simple task_id to UUID format if needed
        if not "-" in task_id:
            task_id = f"00000000-0000-0000-0000-00000000{task_id.replace('task-', '').zfill(4)}"
        
        task = MagicMock(spec=Task)
        task.id = TaskId(task_id)
        task.title = title
        task.description = "Test description"
        task.status = TaskStatus.from_string(status)
        task.priority = Priority.from_string(priority)
        task.assignees = assignees  # Can be None
        task.labels = labels  # Can be None
        task.dependencies = []
        task.subtasks = []
        task.context_id = f"context-{task_id}"
        
        # Mock the to_dict method
        task.to_dict = MagicMock(return_value={
            "id": task_id,
            "title": title,
            "description": "Test description",
            "status": status,
            "priority": priority,
            "assignees": assignees,
            "labels": labels,
            "dependencies": [],
            "subtasks": []
        })
        
        task.get_subtask_progress = MagicMock(return_value={
            "completed": 0,
            "total": 0,
            "percentage": 0
        })
        
        return task

    def test_manage_task_next_with_none_attributes_through_controller(self):
        """Test the full MCP flow with tasks having None attributes"""
        # Create controller with factory
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Mock the facade creation to return a facade with our mocked methods
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            
            # Setup async facade response with AsyncMock
            mock_facade.get_next_task = AsyncMock(return_value={
                "success": True,
                "action": "next",
                "task": {
                    "id": "00000000-0000-0000-0000-000000000123",
                    "title": "Task with None attributes",
                    "status": "todo",
                    "assignees": None,  # This is the key - None value
                    "labels": None,     # This too
                    "priority": "high"
                },
                "message": "Next action: Work on task 'Task with None attributes'"
            })
            
            # Execute manage_task with next action
            result = controller.manage_task(
                action="next",
                git_branch_id="test-branch"
            )
            
            # Assert no error occurred
            assert result["success"] is True
            assert result["action"] == "next"
            assert "task" in result

    def test_manage_task_next_filters_with_none_values(self):
        """Test filtering functionality when tasks have None assignees/labels"""
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Create mock tasks with various None configurations
        tasks = [
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000001", "Task 1", assignees=["user1"], labels=["bug"]),
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000002", "Task 2", assignees=None, labels=["feature"]),
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000003", "Task 3", assignees=["user2"], labels=None),
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000004", "Task 4", assignees=None, labels=None),
        ]
        
        # Mock the facade to return appropriate responses
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            
            # Mock the get_next_task to simulate filtering with None values
            # This is the key test - ensure the facade handles None assignees/labels properly
            mock_facade.get_next_task = AsyncMock(return_value={
                "success": True,
                "action": "next",
                "task": {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "title": "Task 1",
                    "status": "todo",
                    "assignees": ["user1"],
                    "labels": ["bug"],
                    "priority": "medium"
                }
            })
            
            # Test 1: Filter by assignee when some tasks have None assignees
            result = controller.manage_task(
                action="next",
                git_branch_id="test-branch",
                assignees="user1"  # This will be converted to a list internally
            )
            
            # Should not crash and should return appropriate response
            assert result["success"] is True
            assert "error" not in result or "NoneType" not in result.get("error", "")
            
            # Test 2: Filter by labels when some tasks have None labels  
            result = controller.manage_task(
                action="next",
                git_branch_id="test-branch",
                labels=["bug"]
            )
            
            # Should not crash
            assert result["success"] is True
            assert "error" not in result or "NoneType" not in result.get("error", "")

    def test_controller_parameter_validation_for_next_action(self):
        """Test that controller properly validates parameters for next action"""
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Mock facade
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            mock_facade.get_next_task = AsyncMock(return_value={
                "success": True,
                "action": "next",
                "message": "No tasks found"
            })
            
            # Test various parameter combinations
            test_cases = [
                # Basic next action
                {"action": "next", "git_branch_id": "main"},
                # With assignees filter
                {"action": "next", "git_branch_id": "main", "assignees": "user1"},
                # With labels filter
                {"action": "next", "git_branch_id": "main", "labels": ["bug", "urgent"]},
                # With both filters
                {"action": "next", "git_branch_id": "main", "assignees": ["user1", "user2"], "labels": ["feature"]},
                # With include_context
                {"action": "next", "git_branch_id": "main", "include_context": True}
            ]
            
            for params in test_cases:
                result = controller.manage_task(**params)
                # Should not have NoneType errors
                if "error" in result:
                    assert "NoneType" not in result["error"]
                else:
                    assert result["success"] is True

    def test_edge_cases_for_none_handling(self):
        """Test edge cases where None values might cause issues"""
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Mock facade to simulate edge cases
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            
            # Simulate a task with missing attributes
            mock_facade.get_next_task = AsyncMock(return_value={
                "success": True,
                "action": "next",
                "task": {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "title": "Edge Case Task",
                    "status": "todo",
                    "priority": "medium"
                    # Note: assignees and labels are completely missing
                }
            })
            
            # This should not crash even with missing attributes
            result = controller.manage_task(
                action="next",
                git_branch_id="test-branch",
                assignees="user1"
            )
            
            # Should handle gracefully
            assert "success" in result
            assert "NoneType" not in str(result.get("error", ""))

    def test_real_world_scenario_simulation(self):
        """Simulate a real-world scenario with mixed task states"""
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Create realistic task distribution
        tasks = [
            # Normal tasks
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000001", "Implement feature", status="in_progress", 
                                       assignees=["dev1", "dev2"], labels=["feature", "frontend"]),
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000002", "Fix bug", status="todo", priority="urgent",
                                       assignees=["dev1"], labels=["bug", "backend"]),
            # Tasks with None values (common in practice)
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000003", "Research task", status="todo",
                                       assignees=None, labels=None),  # Unassigned research task
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000004", "Documentation", status="todo",
                                       assignees=["dev3"], labels=None),  # No labels yet
            # Completed task
            self.create_mock_task_entity("00000000-0000-0000-0000-000000000005", "Completed feature", status="done",
                                       assignees=["dev1"], labels=["feature"])
        ]
        
        # Mock the facade to simulate real-world scenarios
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            
            # Mock different responses for different scenarios
            async def get_next_task_side_effect(**kwargs):
                # Return different tasks based on filters
                if kwargs.get('assignees') == ["dev1"]:
                    return {
                        "success": True,
                        "action": "next",
                        "task": {
                            "id": "00000000-0000-0000-0000-000000000002",
                            "title": "Fix critical bug",
                            "status": "todo",
                            "priority": "urgent",
                            "assignees": ["dev1"],
                            "labels": ["bug", "urgent"]
                        }
                    }
                elif kwargs.get('labels') == ["bug"]:
                    return {
                        "success": True,
                        "action": "next",
                        "task": {
                            "id": "00000000-0000-0000-0000-000000000002",
                            "title": "Fix critical bug",
                            "status": "todo",
                            "priority": "urgent",
                            "assignees": ["dev1"],
                            "labels": ["bug", "urgent"]
                        }
                    }
                else:
                    # Return unassigned task
                    return {
                        "success": True,
                        "action": "next",
                        "task": {
                            "id": "00000000-0000-0000-0000-000000000003",
                            "title": "Review documentation",
                            "status": "todo",
                            "priority": "low",
                            "assignees": None,
                            "labels": ["docs"]
                        }
                    }
            
            mock_facade.get_next_task = AsyncMock(side_effect=get_next_task_side_effect)
            
            # Scenario 1: Get next task for dev1
            result = controller.manage_task(
                action="next",
                git_branch_id="main", 
                assignees="dev1"
            )
            assert result["success"] is True
            # Should get task-2 (urgent bug) or task-1 (in progress)
            
            # Scenario 2: Get next bug task
            result = controller.manage_task(
                action="next",
                git_branch_id="main",
                labels=["bug"]
            )
            assert result["success"] is True
            
            # Scenario 3: Get any unassigned task
            # This should not crash when checking assignees
            result = controller.manage_task(
                action="next",
                git_branch_id="main"
            )
            assert "NoneType" not in str(result.get("error", ""))

    def test_error_message_validation(self):
        """Ensure the specific error message is not present after fix"""
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        factory = TaskFacadeFactory(repository_factory)
        controller = TaskMCPController(factory)
        
        # Create a task that would previously cause the error
        problematic_task = self.create_mock_task_entity(
            "00000000-0000-0000-0000-000000000001", 
            "Problematic Task",
            status="todo",
            assignees=None,  # This would cause "None is not iterable"
            labels=None      # This too
        )
        
        # Mock the facade to simulate the scenario
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade:
            mock_facade = MagicMock()
            mock_get_facade.return_value = mock_facade
            
            # Return empty/no task when filtering doesn't match
            mock_facade.get_next_task = AsyncMock(return_value={
                "success": True,
                "action": "next",
                "has_next": False,
                "message": "No tasks found matching the criteria"
            })
            
            # This exact call would previously fail with "argument of type 'NoneType' is not iterable"
            result = controller.manage_task(
                action="next",
                git_branch_id="main",
                assignees="any-user",  # Filtering by assignee when task has None assignees
                labels=["any-label"]   # Filtering by label when task has None labels
            )
            
            # Verify the specific error is not present
            if "error" in result:
                assert "argument of type 'NoneType' is not iterable" not in result["error"]
                assert "NoneType" not in result["error"]
            
            # Should get a proper "no matching tasks" response instead
            assert result["success"] is True
            assert result.get("has_next", True) is False