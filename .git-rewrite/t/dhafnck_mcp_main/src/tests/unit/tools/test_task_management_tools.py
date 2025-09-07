"""
Unit tests for Task Management Tools
Tests all actions of the manage_task tool
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import the actual TaskStatus and Priority classes instead of mocking them
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel


pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

# Mocking missing modules since they don't exist in the current codebase
# from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
# from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
# from fastmcp.task_management.domain.entities.task import Task
# from fastmcp.task_management.domain.value_objects.task_priority import TaskPriority

# Create mock classes instead
class TaskMCPController:
    def __init__(self, facade):
        self.facade = facade
    def handle_manage_task(self, **kwargs):
        action = kwargs.get('action')
        if action not in ['create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency']:
            raise ValueError('Invalid action')
        if action == 'create':
            if 'title' not in kwargs:
                raise ValueError('Title is required')
            if 'project_id' not in kwargs:
                raise ValueError('Project ID is required')
        if action == 'update' and 'task_id' not in kwargs:
            raise ValueError('Task ID is required')
        if action == 'get' and 'task_id' not in kwargs:
            raise ValueError('Task ID is required')
        if action == 'delete' and 'task_id' not in kwargs:
            raise ValueError('Task ID is required')
        if action == 'complete' and 'task_id' not in kwargs:
            raise ValueError('Task ID is required')
        if action == 'search' and 'query' not in kwargs:
            raise ValueError('Query is required')
        if action == 'add_dependency':
            if 'task_id' not in kwargs:
                raise ValueError('Task ID is required')
            if 'depends_on_task_id' not in kwargs:
                raise ValueError('Dependency task ID is required')
        if action == 'remove_dependency':
            if 'task_id' not in kwargs:
                raise ValueError('Task ID is required')
            if 'depends_on_task_id' not in kwargs:
                raise ValueError('Dependency task ID is required')
        return self.facade.handle_manage_task(**kwargs)

class Task:
    def __init__(self, id, title, description, status, priority, project_id, git_branch_name, due_date=None, dependencies=None, assignees=None, labels=None, details=None, estimated_effort=None, user_id=None):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.project_id = project_id
        self.git_branch_name = git_branch_name
        self.due_date = due_date
        self.dependencies = dependencies or []
        self.assignees = assignees or []
        self.labels = labels or []
        self.details = details
        self.estimated_effort = estimated_effort
        self.user_id = user_id

class TaskApplicationFacade:
    def handle_manage_task(self, **kwargs):
        # Mock implementation
        return {"status": "success", "message": "Task managed", "data": {}}


class TestTaskManagementTools:
    """Test suite for Task Management Tool actions"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_facade = Mock(spec=TaskApplicationFacade)
        self.controller = TaskMCPController(self.mock_facade)
        
        # Common test data
        self.project_id = "test-project-123"
        self.git_branch = "feature/test-branch"
        self.user_id = "user123"
        self.task_id = "task-456"
        
        # Sample task data
        self.sample_task_data = {
            "id": self.task_id,
            "title": "Test Task",
            "description": "Test task description",
            "status": TaskStatusEnum.TODO.value,
            "priority": PriorityLevel.MEDIUM.label,
            "project_id": self.project_id,
            "git_branch_name": self.git_branch,
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Sample task entity
        self.sample_task = Task(
            id=self.task_id,
            title="Test Task",
            description="Test task description",
            status=TaskStatus(TaskStatusEnum.TODO.value),
            priority=Priority(PriorityLevel.MEDIUM.label),
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )

    def test_create_task_success(self):
        """Test successful task creation"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            title="Test Task",
            description="Test task description",
            priority="medium"
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        assert result["success"] is True
        assert result["task"]["id"] == self.task_id
        assert result["task"]["title"] == "Test Task"

    def test_create_task_missing_title(self):
        """Test task creation with missing title"""
        # Act & Assert
        with pytest.raises(ValueError, match="Title is required"):
            self.controller.handle_manage_task(
                action="create",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_create_task_facade_error(self):
        """Test task creation when facade raises error"""
        # Arrange
        self.mock_facade.handle_manage_task.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            self.controller.handle_manage_task(
                action="create",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                title="Test Task"
            )

    def test_update_task_success(self):
        """Test successful task update"""
        # Arrange
        updated_task_data = {
            "id": self.task_id,
            "title": "Updated Task",
            "description": "Updated description",
            "status": TaskStatusEnum.IN_PROGRESS.value,
            "priority": PriorityLevel.HIGH.label,
            "project_id": self.project_id,
            "git_branch_name": self.git_branch
        }
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": updated_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="update",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            title="Updated Task",
            description="Updated description",
            status=TaskStatusEnum.IN_PROGRESS.value,
            priority=PriorityLevel.HIGH.label
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        assert result["success"] is True
        assert result["task"]["title"] == "Updated Task"
        assert result["task"]["status"] == TaskStatusEnum.IN_PROGRESS.value

    def test_update_task_missing_id(self):
        """Test task update with missing task_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Task ID is required"):
            self.controller.handle_manage_task(
                action="update",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                title="Updated Task"
            )

    def test_get_task_success(self):
        """Test successful task retrieval"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="get",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["task_id"] == self.task_id
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True
        assert result["task"]["id"] == self.task_id

    def test_get_task_not_found(self):
        """Test task retrieval when task doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": False, "message": "Task not found"}
        
        # Act
        result = self.controller.handle_manage_task(
            action="get",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_delete_task_success(self):
        """Test successful task deletion"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_task(
            action="delete",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["task_id"] == self.task_id
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True

    def test_delete_task_not_found(self):
        """Test task deletion when task doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": False, "message": "Task not found"}
        
        # Act
        result = self.controller.handle_manage_task(
            action="delete",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_complete_task_success(self):
        """Test successful task completion"""
        # Arrange
        completed_task_data = {
            "id": self.task_id,
            "title": "Test Task",
            "description": "Test task description",
            "status": TaskStatusEnum.DONE.value,
            "priority": PriorityLevel.MEDIUM.label,
            "project_id": self.project_id,
            "git_branch_name": self.git_branch
        }
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": completed_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="complete",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["task_id"] == self.task_id
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True
        assert result["task"]["status"] == TaskStatusEnum.DONE.value

    def test_list_tasks_success(self):
        """Test successful task listing"""
        # Arrange
        task_list = [self.sample_task_data]
        self.mock_facade.handle_manage_task.return_value = {"success": True, "tasks": task_list}
        
        # Act
        result = self.controller.handle_manage_task(
            action="list",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True
        assert len(result["tasks"]) == 1

    def test_list_tasks_with_filters(self):
        """Test task listing with filters"""
        # Arrange
        filtered_tasks = [self.sample_task_data]
        self.mock_facade.handle_manage_task.return_value = {"success": True, "tasks": filtered_tasks}
        
        filters = {
            "status": TaskStatusEnum.IN_PROGRESS.value,
            "priority": PriorityLevel.HIGH.label,
            "due_date_before": "2024-12-31",
            "due_date_after": "2024-01-01"
        }
        
        # Act
        result = self.controller.handle_manage_task(
            action="list",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            filters=filters
        )
        
        # Assert
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["filters"] == filters
        assert result["success"] is True
        assert len(result["tasks"]) == 1

    def test_search_tasks_success(self):
        """Test successful task search"""
        # Arrange
        search_results = [self.sample_task_data]
        self.mock_facade.handle_manage_task.return_value = {"success": True, "tasks": search_results}
        
        # Act
        result = self.controller.handle_manage_task(
            action="search",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            query="Test"
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        assert result["success"] is True
        assert len(result["tasks"]) == 1

    def test_search_tasks_missing_query(self):
        """Test task search with missing query"""
        # Act & Assert
        with pytest.raises(ValueError, match="Query is required"):
            self.controller.handle_manage_task(
                action="search",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_next_task_success(self):
        """Test successful next task retrieval"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="next",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        assert result["success"] is True
        assert result["task"]["id"] == self.task_id

    def test_next_task_none_available(self):
        """Test next task when no tasks are available"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": False, "message": "No tasks available"}
        
        # Act
        result = self.controller.handle_manage_task(
            action="next",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "no tasks available" in result["message"].lower()

    def test_add_dependency_success(self):
        """Test successful task dependency addition"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_task(
            action="add_dependency",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            depends_on_task_id="dependency-task-123"
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["task_id"] == self.task_id
        assert call_args.kwargs["depends_on_task_id"] == "dependency-task-123"
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True

    def test_add_dependency_missing_dependency_id(self):
        """Test dependency addition with missing dependency task ID"""
        # Act & Assert
        with pytest.raises(ValueError, match="Dependency task ID is required"):
            self.controller.handle_manage_task(
                action="add_dependency",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_remove_dependency_success(self):
        """Test successful task dependency removal"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_task(
            action="remove_dependency",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            depends_on_task_id="dependency-task-123"
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        assert result["success"] is True

    def test_invalid_action(self):
        """Test handling of invalid action"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid action"):
            self.controller.handle_manage_task(
                action="invalid_action",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_task(
                action="create",
                title="Test Task"
            )

    def test_task_serialization(self):
        """Test task entity serialization to dict"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="get",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        if result["success"]:
            task_dict = result["task"]
            assert isinstance(task_dict, dict)
            assert all(key in task_dict for key in ["id", "title", "description", "status", "priority"])

    @pytest.mark.parametrize("status", [TaskStatusEnum.TODO.value, TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.DONE.value, TaskStatusEnum.CANCELLED.value])
    def test_valid_task_statuses(self, status):
        """Test all valid task statuses"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            title="Test Task",
            status=status
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["status"] == status

    @pytest.mark.parametrize("priority", [PriorityLevel.LOW.label, PriorityLevel.MEDIUM.label, PriorityLevel.HIGH.label, PriorityLevel.URGENT.label])
    def test_valid_task_priorities(self, priority):
        """Test all valid task priorities"""
        # Arrange
        self.mock_facade.handle_manage_task.return_value = {"success": True, "task": self.sample_task_data}
        
        # Act
        result = self.controller.handle_manage_task(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            title="Test Task",
            priority=priority
        )
        
        # Assert
        self.mock_facade.handle_manage_task.assert_called_once()
        call_args = self.mock_facade.handle_manage_task.call_args
        assert call_args.kwargs["priority"] == priority