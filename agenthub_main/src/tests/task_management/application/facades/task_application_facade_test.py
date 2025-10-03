"""
Tests for Task Application Facade

This test suite covers the Task Application Facade functionality including:
- Task creation with validation
- Task retrieval and listing
- Task updates and progress tracking
- Task completion and deletion
- Dependency management
- Search functionality
- Next task recommendation
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade
)
from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.application.dtos.task.search_tasks_request import SearchTasksRequest
from fastmcp.task_management.domain.entities import Task, GitBranch, TaskStatus, TaskPriority
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    ProjectNotFoundError
)
from fastmcp.task_management.application.exceptions import (
    ValidationError
)


class TestTaskApplicationFacade:
    """Test Task Application Facade functionality"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        repo = Mock(spec=TaskRepository)
        repo.save = AsyncMock()
        repo.find_by_id = AsyncMock()
        repo.find_all_by_git_branch = AsyncMock()
        repo.delete = AsyncMock()
        repo.search = AsyncMock()
        return repo

    @pytest.fixture
    def mock_subtask_repository(self):
        """Create mock subtask repository"""
        repo = Mock(spec=SubtaskRepository)
        repo.find_all_by_task = AsyncMock()
        repo.count_by_task = AsyncMock()
        return repo

    @pytest.fixture
    def mock_git_branch_repository(self):
        """Create mock git branch repository"""
        repo = Mock(spec=GitBranchRepository)
        repo.find_by_id = AsyncMock()
        repo.find_by_name_and_project = AsyncMock()
        return repo

    @pytest.fixture
    def mock_task_application_service(self):
        """Create mock task application service"""
        service = Mock(spec=TaskApplicationService)
        service.create_task = AsyncMock()
        service.update_task = AsyncMock()
        service.get_task = AsyncMock()
        service.delete_task = AsyncMock()
        service.complete_task = AsyncMock()
        service.list_tasks = AsyncMock()
        service.search_tasks = AsyncMock()
        service.get_next_task = AsyncMock()
        service.add_dependency = AsyncMock()
        service.remove_dependency = AsyncMock()
        return service

    @pytest.fixture
    def sample_task(self):
        """Create sample task"""
        task = Mock(spec=Task)
        task.id = "task-123"
        task.title = "Implement user authentication"
        task.description = "Add JWT-based authentication system"
        task.status = TaskStatus.TODO
        task.priority = "high"
        task.assignees = ["coding-agent", "@test-orchestrator-agent"]
        task.git_branch_id = "branch-123"
        task.estimated_effort = "3 days"
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        task.to_dict = Mock(return_value={
            "id": "task-123",
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication system",
            "status": "todo",
            "priority": "high",
            "assignees": ["coding-agent", "@test-orchestrator-agent"],
            "git_branch_id": "branch-123",
            "estimated_effort": "3 days"
        })
        return task

    @pytest.fixture
    def sample_git_branch(self):
        """Create sample git branch"""
        branch = Mock(spec=GitBranch)
        branch.id = "branch-123"
        branch.project_id = "proj-123"
        branch.git_branch_name = "feature/user-auth"
        branch.git_branch_description = "Authentication feature"
        branch.to_dict = Mock(return_value={
            "id": "branch-123",
            "project_id": "proj-123",
            "git_branch_name": "feature/user-auth",
            "git_branch_description": "Authentication feature"
        })
        return branch

    @pytest.fixture
    def facade(self, mock_task_repository, mock_subtask_repository, mock_git_branch_repository):
        """Create facade instance with mocks"""
        return TaskApplicationFacade(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            git_branch_repository=mock_git_branch_repository,
            user_id="user-123"
        )

    @pytest.mark.asyncio
    async def test_create_task(self, facade, sample_task, sample_git_branch):
        """Test creating a task"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.create_task.return_value = {
                "success": True,
                "task": sample_task.to_dict()
            }
            
            # Execute
            request = CreateTaskRequest(
                git_branch_id="branch-123",
                title="Implement user authentication",
                description="Add JWT-based authentication system",
                assignees=["coding-agent", "@test-orchestrator-agent"],
                priority="high",
                estimated_effort="3 days"
            )
            
            result = await facade.create_task(request)
        
        # Verify
        assert result["success"] is True
        assert result["task"]["title"] == "Implement user authentication"
        mock_service.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_validation_error(self, facade):
        """Test creating task with validation error"""
        # Configure mocks for validation failure
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.create_task.side_effect = ValidationError("Title cannot be empty")
            
            # Execute
            request = CreateTaskRequest(
                git_branch_id="branch-123",
                title="",  # Empty title should fail validation
                assignees=["coding-agent"]
            )
            
            result = await facade.create_task(request)
        
        # Verify
        assert result["success"] is False
        assert "Title cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_get_task(self, facade, sample_task):
        """Test retrieving a task by ID"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.get_task.return_value = {
                "success": True,
                "task": sample_task.to_dict()
            }
            
            # Execute
            result = await facade.get_task("task-123")
        
        # Verify
        assert result["success"] is True
        assert result["task"]["id"] == "task-123"
        assert result["task"]["title"] == "Implement user authentication"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, facade):
        """Test retrieving non-existent task"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.get_task.side_effect = TaskNotFoundError("Task not found: task-999")
            
            # Execute
            result = await facade.get_task("task-999")
        
        # Verify
        assert result["success"] is False
        assert "Task not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_task(self, facade, sample_task):
        """Test updating a task"""
        # Configure mocks
        updated_task = sample_task.to_dict()
        updated_task["title"] = "Updated authentication system"
        updated_task["status"] = "in_progress"
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.update_task.return_value = {
                "success": True,
                "task": updated_task
            }
            
            # Execute
            request = UpdateTaskRequest(
                task_id="task-123",
                title="Updated authentication system",
                status="in_progress"
            )
            
            result = await facade.update_task(request)
        
        # Verify
        assert result["success"] is True
        assert result["task"]["title"] == "Updated authentication system"
        assert result["task"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_complete_task(self, facade, sample_task):
        """Test completing a task"""
        # Configure mocks
        completed_task = sample_task.to_dict()
        completed_task["status"] = "done"
        completed_task["progress_percentage"] = 100
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.complete_task.return_value = {
                "success": True,
                "task": completed_task,
                "completion_summary": "Authentication system implemented successfully"
            }
            
            # Execute
            result = await facade.complete_task(
                task_id="task-123",
                completion_summary="Authentication system implemented successfully",
                testing_notes="All tests passing"
            )
        
        # Verify
        assert result["success"] is True
        assert result["task"]["status"] == "done"
        assert result["completion_summary"] == "Authentication system implemented successfully"

    @pytest.mark.asyncio
    async def test_delete_task(self, facade):
        """Test deleting a task"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.delete_task.return_value = {
                "success": True,
                "message": "Task deleted successfully"
            }
            
            # Execute
            result = await facade.delete_task("task-123")
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Task deleted successfully"

    @pytest.mark.asyncio
    async def test_list_tasks(self, facade, sample_task):
        """Test listing tasks with filters"""
        # Configure mocks
        task_list = [sample_task.to_dict()]
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.list_tasks.return_value = {
                "success": True,
                "tasks": task_list,
                "total_count": 1,
                "page": 1,
                "limit": 10
            }
            
            # Execute
            request = ListTasksRequest(
                git_branch_id="branch-123",
                status="todo",
                priority="high",
                limit=10
            )
            
            result = await facade.list_tasks(request)
        
        # Verify
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Implement user authentication"
        assert result["total_count"] == 1

    @pytest.mark.asyncio
    async def test_search_tasks(self, facade, sample_task):
        """Test searching tasks by query"""
        # Configure mocks
        search_results = [sample_task.to_dict()]
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.search_tasks.return_value = {
                "success": True,
                "tasks": search_results,
                "total_count": 1,
                "query": "authentication"
            }
            
            # Execute
            request = SearchTasksRequest(
                query="authentication",
                git_branch_id="branch-123",
                limit=10
            )
            
            result = await facade.search_tasks(request)
        
        # Verify
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Implement user authentication"
        assert result["query"] == "authentication"

    @pytest.mark.asyncio
    async def test_get_next_task(self, facade, sample_task):
        """Test getting next recommended task"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.get_next_task.return_value = {
                "success": True,
                "task": sample_task.to_dict(),
                "recommendation_reason": "High priority task with no dependencies"
            }
            
            # Execute
            result = await facade.get_next_task(
                git_branch_id="branch-123",
                include_context=True
            )
        
        # Verify
        assert result["success"] is True
        assert result["task"]["id"] == "task-123"
        assert "recommendation_reason" in result

    @pytest.mark.asyncio
    async def test_get_next_task_no_tasks(self, facade):
        """Test getting next task when no tasks available"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.get_next_task.return_value = {
                "success": True,
                "task": None,
                "message": "No available tasks"
            }
            
            # Execute
            result = await facade.get_next_task(git_branch_id="branch-123")
        
        # Verify
        assert result["success"] is True
        assert result["task"] is None
        assert "No available tasks" in result["message"]

    @pytest.mark.asyncio
    async def test_add_dependency(self, facade):
        """Test adding task dependency"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.add_dependency.return_value = {
                "success": True,
                "message": "Dependency added successfully",
                "dependency": {
                    "task_id": "task-123",
                    "dependency_id": "task-456"
                }
            }
            
            # Execute
            result = await facade.add_dependency(
                task_id="task-123",
                dependency_id="task-456"
            )
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Dependency added successfully"
        assert result["dependency"]["task_id"] == "task-123"

    @pytest.mark.asyncio
    async def test_remove_dependency(self, facade):
        """Test removing task dependency"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.remove_dependency.return_value = {
                "success": True,
                "message": "Dependency removed successfully"
            }
            
            # Execute
            result = await facade.remove_dependency(
                task_id="task-123",
                dependency_id="task-456"
            )
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Dependency removed successfully"

    @pytest.mark.asyncio
    async def test_ai_plan_task_breakdown(self, facade):
        """Test AI-powered task planning and breakdown"""
        # Configure mocks for AI planning
        planned_tasks = [
            {
                "title": "Design authentication API",
                "description": "Create API endpoints for login/logout",
                "priority": "high",
                "estimated_effort": "1 day"
            },
            {
                "title": "Implement JWT token service",
                "description": "Service for generating and validating JWT tokens",
                "priority": "high",
                "estimated_effort": "2 days"
            }
        ]
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.ai_plan_tasks.return_value = {
                "success": True,
                "planned_tasks": planned_tasks,
                "requirements_analysis": "User authentication system with JWT tokens",
                "auto_create_tasks": True
            }
            
            # Execute
            result = await facade.ai_plan_tasks(
                requirements="Implement user authentication with JWT",
                title="User Authentication System",
                git_branch_id="branch-123",
                auto_create_tasks=True
            )
        
        # Verify
        assert result["success"] is True
        assert len(result["planned_tasks"]) == 2
        assert result["planned_tasks"][0]["title"] == "Design authentication API"

    @pytest.mark.asyncio
    async def test_ai_create_enhanced_task(self, facade, sample_task):
        """Test AI-enhanced task creation"""
        # Configure mocks
        enhanced_task = sample_task.to_dict()
        enhanced_task["ai_breakdown"] = [
            "Research JWT implementation",
            "Design authentication flow",
            "Implement login endpoint",
            "Add token validation",
            "Write tests"
        ]
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.ai_create_task.return_value = {
                "success": True,
                "task": enhanced_task,
                "ai_enhancements": {
                    "breakdown_applied": True,
                    "smart_assignment": True,
                    "complexity_analysis": "Medium complexity - requires authentication knowledge"
                }
            }
            
            # Execute
            result = await facade.ai_create_task(
                title="Implement user authentication",
                git_branch_id="branch-123",
                enable_ai_breakdown=True,
                enable_smart_assignment=True
            )
        
        # Verify
        assert result["success"] is True
        assert result["task"]["title"] == "Implement user authentication"
        assert "ai_breakdown" in result["task"]
        assert result["ai_enhancements"]["breakdown_applied"] is True

    @pytest.mark.asyncio
    async def test_ai_enhance_existing_task(self, facade, sample_task):
        """Test AI enhancement of existing task"""
        # Configure mocks
        enhanced_task = sample_task.to_dict()
        enhanced_task["complexity_analysis"] = "Medium complexity task"
        enhanced_task["optimization_suggestions"] = [
            "Consider using existing auth library",
            "Implement rate limiting",
            "Add comprehensive logging"
        ]
        enhanced_task["risk_analysis"] = [
            "Security vulnerability if not properly implemented",
            "Performance impact on large user base"
        ]
        
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.ai_enhance_task.return_value = {
                "success": True,
                "task": enhanced_task,
                "ai_insights": {
                    "complexity_analyzed": True,
                    "optimizations_suggested": True,
                    "risks_identified": True
                }
            }
            
            # Execute
            result = await facade.ai_enhance_task(
                task_id="task-123",
                analyze_complexity=True,
                suggest_optimizations=True,
                identify_risks=True
            )
        
        # Verify
        assert result["success"] is True
        assert "complexity_analysis" in result["task"]
        assert len(result["task"]["optimization_suggestions"]) == 3
        assert len(result["task"]["risk_analysis"]) == 2

    @pytest.mark.asyncio
    async def test_error_handling_project_not_found(self, facade):
        """Test error handling for non-existent project"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.create_task.side_effect = ProjectNotFoundError("Project not found: proj-999")
            
            # Execute
            request = CreateTaskRequest(
                git_branch_id="branch-999",
                title="Test Task",
                assignees=["coding-agent"]
            )
            
            result = await facade.create_task(request)
        
        # Verify
        assert result["success"] is False
        assert "Project not found" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_validation_error(self, facade):
        """Test error handling for validation errors"""
        # Configure mocks
        with patch.object(facade, '_task_application_service') as mock_service:
            mock_service.create_task.side_effect = ValidationError("Task with similar title already exists")
            
            # Execute
            request = CreateTaskRequest(
                git_branch_id="branch-123",
                title="Duplicate Task",
                assignees=["coding-agent"]
            )
            
            result = await facade.create_task(request)
        
        # Verify
        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_context_integration(self, facade, sample_task):
        """Test context service integration"""
        # Configure mocks for context service
        with patch.object(facade, '_unified_context_service') as mock_context_service:
            mock_context_service.get_task_context.return_value = {
                "context_data": {"key": "value"},
                "inheritance_chain": ["global", "project", "branch", "task"]
            }
            
            with patch.object(facade, '_task_application_service') as mock_service:
                mock_service.get_task.return_value = {
                    "success": True,
                    "task": sample_task.to_dict()
                }
                
                # Execute with context
                result = await facade.get_task("task-123", include_context=True)
        
        # Verify
        assert result["success"] is True
        mock_context_service.get_task_context.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_websocket_notification_integration(self, facade, sample_task):
        """Test WebSocket notification service integration"""
        # Configure mocks
        with patch.object(facade, '_websocket_service') as mock_websocket:
            mock_websocket.notify_task_created = AsyncMock()
            
            with patch.object(facade, '_task_application_service') as mock_service:
                mock_service.create_task.return_value = {
                    "success": True,
                    "task": sample_task.to_dict()
                }
                
                # Execute
                request = CreateTaskRequest(
                    git_branch_id="branch-123",
                    title="Test Task",
                    assignees=["coding-agent"]
                )
                
                result = await facade.create_task(request)
        
        # Verify
        assert result["success"] is True
        # WebSocket notification should be sent for task creation
        mock_websocket.notify_task_created.assert_called_once()

    def test_facade_initialization(self):
        """Test proper facade initialization"""
        facade = TaskApplicationFacade(
            task_repository=Mock(),
            subtask_repository=Mock(),
            git_branch_repository=Mock(),
            user_id="user-123"
        )
        
        # Verify initialization
        assert facade._user_id == "user-123"
        assert facade._task_repository is not None
        assert facade._subtask_repository is not None
        assert facade._git_branch_repository is not None

    def test_facade_initialization_without_optional_repos(self):
        """Test facade initialization without optional repositories"""
        facade = TaskApplicationFacade(
            task_repository=Mock(),
            user_id="user-123"
        )
        
        # Verify initialization with defaults
        assert facade._user_id == "user-123"
        assert facade._task_repository is not None
        # Optional repositories should be None or have defaults
        assert hasattr(facade, '_subtask_repository')
        assert hasattr(facade, '_git_branch_repository')