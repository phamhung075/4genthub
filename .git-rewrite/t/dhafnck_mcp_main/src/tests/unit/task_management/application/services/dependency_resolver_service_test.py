"""Tests for DependencyResolverService"""

import pytest
from unittest.mock import Mock, create_autospec
from datetime import datetime
from typing import List, Optional

from fastmcp.task_management.application.services.dependency_resolver_service import DependencyResolverService
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.application.dtos.task.dependency_info import DependencyInfo, DependencyChain, DependencyRelationships


class TestDependencyResolverService:
    """Test suite for DependencyResolverService"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return create_autospec(TaskRepository, instance=True)

    @pytest.fixture
    def service(self, mock_task_repository):
        """Create a DependencyResolverService instance"""
        return DependencyResolverService(mock_task_repository)

    @pytest.fixture
    def mock_task(self):
        """Create a mock task"""
        task = Mock(spec=Task)
        task.id = TaskId("task-1")
        task.title = "Test Task"
        task.status = TaskStatus(TaskStatus.TODO)
        task.priority = Priority.medium()
        task.overall_progress = 0
        task.estimated_effort = "2 hours"
        task.assignees = ["user1"]
        task.updated_at = datetime.now()
        task.get_dependency_ids = Mock(return_value=[])
        return task

    def test_init(self, mock_task_repository):
        """Test service initialization"""
        service = DependencyResolverService(mock_task_repository)
        assert service.task_repository == mock_task_repository
        assert service._user_id is None

    def test_init_with_user_id(self, mock_task_repository):
        """Test service initialization with user ID"""
        service = DependencyResolverService(mock_task_repository, user_id="user-123")
        assert service.task_repository == mock_task_repository
        assert service._user_id == "user-123"

    def test_with_user(self, service):
        """Test creating user-scoped service"""
        user_scoped_service = service.with_user("user-456")
        assert isinstance(user_scoped_service, DependencyResolverService)
        assert user_scoped_service._user_id == "user-456"
        assert user_scoped_service.task_repository == service.task_repository

    def test_get_user_scoped_repository_no_user(self, service):
        """Test getting repository when no user is set"""
        repo = service._get_user_scoped_repository()
        assert repo == service.task_repository

    def test_get_user_scoped_repository_with_user_method(self, service, mock_task_repository):
        """Test getting repository with with_user method"""
        service._user_id = "user-789"
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        repo = service._get_user_scoped_repository()
        
        mock_task_repository.with_user.assert_called_once_with("user-789")
        assert repo == mock_task_repository

    def test_resolve_dependencies_task_not_found(self, service, mock_task_repository):
        """Test resolve_dependencies when task is not found"""
        mock_task_repository.find_by_id.return_value = None
        
        with pytest.raises(TaskNotFoundError, match="Task task-999 not found"):
            service.resolve_dependencies("task-999")

    def test_resolve_dependencies_simple_task(self, service, mock_task_repository, mock_task):
        """Test resolve_dependencies for task with no dependencies"""
        mock_task_repository.find_by_id.return_value = mock_task
        mock_task_repository.find_all.return_value = []
        
        result = service.resolve_dependencies("task-1")
        
        assert isinstance(result, DependencyRelationships)
        assert result.task_id == "task-1"
        assert result.depends_on == []
        assert result.blocks == []
        assert result.total_dependencies == 0
        assert result.completed_dependencies == 0
        assert result.blocked_dependencies == 0
        assert result.can_start is True
        assert result.is_blocked is False
        assert result.is_blocking_others is False

    def test_resolve_dependencies_with_dependencies(self, service, mock_task_repository):
        """Test resolve_dependencies for task with dependencies"""
        # Create main task
        main_task = Mock(spec=Task)
        main_task.id = TaskId("task-1")
        main_task.get_dependency_ids = Mock(return_value=["dep-1", "dep-2"])
        
        # Create dependency tasks
        dep1 = Mock(spec=Task)
        dep1.id = TaskId("dep-1")
        dep1.title = "Dependency 1"
        dep1.status = TaskStatus(TaskStatus.DONE)
        dep1.priority = Priority.high()
        dep1.overall_progress = 100
        dep1.estimated_effort = "1 hour"
        dep1.assignees = ["user1"]
        dep1.updated_at = datetime.now()
        dep1.get_dependency_ids = Mock(return_value=[])
        
        dep2 = Mock(spec=Task)
        dep2.id = TaskId("dep-2")
        dep2.title = "Dependency 2"
        dep2.status = TaskStatus(TaskStatus.IN_PROGRESS)
        dep2.priority = Priority.medium()
        dep2.overall_progress = 50
        dep2.estimated_effort = "3 hours"
        dep2.assignees = ["user2"]
        dep2.updated_at = datetime.now()
        dep2.get_dependency_ids = Mock(return_value=[])
        
        # Setup repository mock
        def find_by_id_side_effect(task_id):
            if str(task_id) == "task-1":
                return main_task
            elif str(task_id) == "dep-1":
                return dep1
            elif str(task_id) == "dep-2":
                return dep2
            return None
            
        mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        mock_task_repository.find_all.return_value = []
        
        result = service.resolve_dependencies("task-1")
        
        assert result.task_id == "task-1"
        assert len(result.depends_on) == 2
        assert result.total_dependencies == 2
        assert result.completed_dependencies == 1
        assert result.blocked_dependencies == 0
        assert result.can_start is False  # One dependency is not done
        assert result.is_blocked is False
        assert result.is_blocking_others is False

    def test_resolve_dependencies_with_blocking_tasks(self, service, mock_task_repository):
        """Test resolve_dependencies when task blocks other tasks"""
        # Create main task
        main_task = Mock(spec=Task)
        main_task.id = TaskId("task-1")
        main_task.get_dependency_ids = Mock(return_value=[])
        
        # Create blocked task
        blocked_task = Mock(spec=Task)
        blocked_task.id = TaskId("blocked-1")
        blocked_task.title = "Blocked Task"
        blocked_task.status = TaskStatus(TaskStatus.TODO)
        blocked_task.priority = Priority.high()
        blocked_task.overall_progress = 0
        blocked_task.estimated_effort = "4 hours"
        blocked_task.assignees = ["user3"]
        blocked_task.updated_at = datetime.now()
        blocked_task.get_dependency_ids = Mock(return_value=["task-1"])
        
        # Setup repository mock
        mock_task_repository.find_by_id.return_value = main_task
        mock_task_repository.find_all.return_value = [blocked_task]
        
        result = service.resolve_dependencies("task-1")
        
        assert result.task_id == "task-1"
        assert len(result.blocks) == 1
        assert result.blocks[0].task_id == "blocked-1"
        assert result.blocks[0].is_blocking is True
        assert result.is_blocking_others is True

    def test_resolve_dependencies_error_handling(self, service, mock_task_repository):
        """Test resolve_dependencies error handling"""
        mock_task_repository.find_by_id.side_effect = Exception("Database error")
        
        result = service.resolve_dependencies("task-1")
        
        # Should return empty relationships on error
        assert result.task_id == "task-1"
        assert result.depends_on == []
        assert result.blocks == []
        assert result.total_dependencies == 0
        assert result.dependency_summary == "Unable to resolve dependencies"
        assert result.next_actions == ["Check task dependencies manually"]

    def test_build_dependency_graph(self, service, mock_task_repository):
        """Test building dependency graph"""
        # Create tasks with dependencies
        task1 = Mock(spec=Task)
        task1.get_dependency_ids = Mock(return_value=["task-2", "task-3"])
        
        task2 = Mock(spec=Task)
        task2.get_dependency_ids = Mock(return_value=["task-4"])
        
        task3 = Mock(spec=Task)
        task3.get_dependency_ids = Mock(return_value=[])
        
        task4 = Mock(spec=Task)
        task4.get_dependency_ids = Mock(return_value=[])
        
        # Setup repository mock
        def find_by_id_side_effect(task_id):
            task_map = {
                "task-1": task1,
                "task-2": task2,
                "task-3": task3,
                "task-4": task4
            }
            return task_map.get(str(task_id))
            
        mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        graph = service._build_dependency_graph("task-1")
        
        assert graph == {
            "task-1": ["task-2", "task-3"],
            "task-2": ["task-4"],
            "task-3": [],
            "task-4": []
        }

    def test_build_dependency_graph_circular_dependency(self, service, mock_task_repository):
        """Test building dependency graph with circular dependencies"""
        # Create circular dependency
        task1 = Mock(spec=Task)
        task1.get_dependency_ids = Mock(return_value=["task-2"])
        
        task2 = Mock(spec=Task)
        task2.get_dependency_ids = Mock(return_value=["task-1"])
        
        # Setup repository mock
        def find_by_id_side_effect(task_id):
            task_map = {
                "task-1": task1,
                "task-2": task2
            }
            return task_map.get(str(task_id))
            
        mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        # Should handle circular dependencies gracefully
        graph = service._build_dependency_graph("task-1")
        
        # Should visit each task only once
        assert "task-1" in graph
        assert "task-2" in graph

    def test_can_task_start(self, service):
        """Test _can_task_start logic"""
        # All dependencies done
        deps_done = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="done", priority="medium", completion_percentage=100)
        ]
        assert service._can_task_start(deps_done) is True
        
        # Some dependencies not done
        deps_mixed = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="in_progress", priority="medium", completion_percentage=50)
        ]
        assert service._can_task_start(deps_mixed) is False
        
        # No dependencies
        assert service._can_task_start([]) is True

    def test_is_task_blocked(self, service):
        """Test _is_task_blocked logic"""
        # No blocked dependencies
        deps_not_blocked = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="in_progress", priority="medium", completion_percentage=50)
        ]
        assert service._is_task_blocked(deps_not_blocked) is False
        
        # Has blocked dependency
        deps_blocked = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="blocked", priority="medium", completion_percentage=0)
        ]
        assert service._is_task_blocked(deps_blocked) is True

    def test_generate_dependency_summary(self, service):
        """Test dependency summary generation"""
        # No dependencies
        summary = service._generate_dependency_summary([], [])
        assert summary == "No dependencies"
        
        # Only depends on
        deps = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="todo", priority="medium", completion_percentage=0)
        ]
        summary = service._generate_dependency_summary(deps, [])
        assert summary == "Depends on 2 task(s) (1/2 completed)"
        
        # Only blocks
        blocks = [
            DependencyInfo(task_id="3", title="Task 3", status="todo", priority="high", completion_percentage=0)
        ]
        summary = service._generate_dependency_summary([], blocks)
        assert summary == "Blocks 1 task(s)"
        
        # Both depends on and blocks
        summary = service._generate_dependency_summary(deps, blocks)
        assert summary == "Depends on 2 task(s) (1/2 completed) | Blocks 1 task(s)"

    def test_generate_next_actions(self, service):
        """Test next actions generation"""
        # Can start
        actions = service._generate_next_actions([], [], True)
        assert "✅ Ready to start - no blocking dependencies" in actions
        
        # Cannot start with incomplete dependencies
        incomplete_deps = [
            DependencyInfo(task_id="1", title="Dep 1", status="in_progress", priority="high", completion_percentage=50),
            DependencyInfo(task_id="2", title="Dep 2", status="todo", priority="medium", completion_percentage=0)
        ]
        actions = service._generate_next_actions(incomplete_deps, [], False)
        assert any("⏳ Wait for 2 dependencies to complete" in action for action in actions)
        assert any("💡 Consider working on 1 unstarted dependencies" in action for action in actions)
        
        # Blocking other tasks
        blocks = [
            DependencyInfo(task_id="3", title="Task 3", status="todo", priority="high", completion_percentage=0)
        ]
        actions = service._generate_next_actions([], blocks, True)
        assert any("🚧 Completing this task will unblock 1 other task(s)" in action for action in actions)

    def test_generate_blocking_reasons(self, service):
        """Test blocking reasons generation"""
        # No blocking dependencies
        deps_done = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100)
        ]
        reasons = service._generate_blocking_reasons(deps_done)
        assert reasons == []
        
        # Has blocking dependencies
        deps_incomplete = [
            DependencyInfo(task_id="1", title="Dep 1", status="done", priority="high", completion_percentage=100),
            DependencyInfo(task_id="2", title="Dep 2", status="in_progress", priority="medium", completion_percentage=50),
            DependencyInfo(task_id="3", title="Dep 3", status="todo", priority="low", completion_percentage=0)
        ]
        reasons = service._generate_blocking_reasons(deps_incomplete)
        assert len(reasons) == 2
        assert "'Dep 2' (in_progress)" in reasons
        assert "'Dep 3' (todo)" in reasons

    def test_build_upstream_chains(self, service, mock_task_repository):
        """Test building upstream dependency chains"""
        # Create tasks
        task1 = Mock(spec=Task)
        task1.id = TaskId("task-1")
        task1.title = "Main Task"
        task1.status = TaskStatus(TaskStatus.TODO)
        task1.priority = Priority.high()
        task1.overall_progress = 0
        task1.estimated_effort = "2 hours"
        task1.assignees = []
        task1.updated_at = datetime.now()
        task1.get_dependency_ids = Mock(return_value=["dep-1"])
        
        dep1 = Mock(spec=Task)
        dep1.id = TaskId("dep-1")
        dep1.title = "Dependency 1"
        dep1.status = TaskStatus(TaskStatus.DONE)
        dep1.priority = Priority.medium()
        dep1.overall_progress = 100
        dep1.estimated_effort = "1 hour"
        dep1.assignees = ["user1"]
        dep1.updated_at = datetime.now()
        dep1.get_dependency_ids = Mock(return_value=[])
        
        # Setup repository mock
        def find_by_id_side_effect(task_id):
            task_map = {
                "task-1": task1,
                "dep-1": dep1
            }
            return task_map.get(str(task_id))
            
        mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        # Build dependency graph
        graph = {"task-1": ["dep-1"], "dep-1": []}
        
        chains = service._build_upstream_chains("task-1", graph)
        
        assert len(chains) == 1
        assert chains[0].chain_id == "upstream_dep-1"
        assert chains[0].total_tasks == 1
        assert chains[0].completed_tasks == 1
        assert chains[0].chain_status == "completed"

    def test_build_downstream_chains(self, service, mock_task_repository):
        """Test building downstream dependency chains"""
        # Create tasks
        task1 = Mock(spec=Task)
        task1.id = TaskId("task-1")
        task1.title = "Main Task"
        task1.status = TaskStatus(TaskStatus.TODO)
        task1.priority = Priority.high()
        task1.overall_progress = 0
        task1.estimated_effort = "2 hours"
        task1.assignees = []
        task1.updated_at = datetime.now()
        task1.get_dependency_ids = Mock(return_value=[])
        
        blocked_task = Mock(spec=Task)
        blocked_task.id = TaskId("blocked-1")
        blocked_task.title = "Blocked Task"
        blocked_task.status = TaskStatus(TaskStatus.TODO)
        blocked_task.priority = Priority.medium()
        blocked_task.overall_progress = 0
        blocked_task.estimated_effort = "3 hours"
        blocked_task.assignees = ["user2"]
        blocked_task.updated_at = datetime.now()
        blocked_task.get_dependency_ids = Mock(return_value=["task-1"])
        
        # Setup repository mock
        def find_by_id_side_effect(task_id):
            task_map = {
                "task-1": task1,
                "blocked-1": blocked_task
            }
            return task_map.get(str(task_id))
            
        mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        # Build dependency graph
        graph = {"task-1": [], "blocked-1": ["task-1"]}
        
        chains = service._build_downstream_chains("task-1", graph)
        
        assert len(chains) == 1
        assert chains[0].chain_id == "downstream_blocked-1"
        assert chains[0].total_tasks == 1
        assert chains[0].completed_tasks == 0
        assert chains[0].chain_status == "in_progress"