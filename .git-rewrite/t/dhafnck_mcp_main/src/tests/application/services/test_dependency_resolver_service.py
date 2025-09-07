"""Tests for DependencyResolverService"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from collections import defaultdict

from fastmcp.task_management.application.services.dependency_resolver_service import DependencyResolverService
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.application.dtos.task.dependency_info import DependencyInfo, DependencyChain, DependencyRelationships


class TestDependencyResolverService:
    """Test cases for DependencyResolverService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_task_repository = Mock()
        self.user_id = "user-123"
        self.service = DependencyResolverService(self.mock_task_repository, self.user_id)

    def test_init(self):
        """Test service initialization"""
        assert self.service.task_repository == self.mock_task_repository
        assert self.service._user_id == self.user_id

    def test_init_without_user_id(self):
        """Test service initialization without user_id"""
        service = DependencyResolverService(self.mock_task_repository)
        
        assert service.task_repository == self.mock_task_repository
        assert service._user_id is None

    def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository when repository has with_user method"""
        mock_scoped_repo = Mock()
        self.mock_task_repository.with_user.return_value = mock_scoped_repo
        
        result = self.service._get_user_scoped_repository()
        
        assert result == mock_scoped_repo
        self.mock_task_repository.with_user.assert_called_once_with(self.user_id)

    def test_get_user_scoped_repository_with_user_id_attribute(self):
        """Test getting user-scoped repository when repository has user_id attribute"""
        # Remove with_user method
        del self.mock_task_repository.with_user
        
        # Setup repository with user_id attribute and session
        self.mock_task_repository.user_id = "different-user"
        self.mock_task_repository.session = Mock()
        
        # Mock repository class constructor
        with patch.object(type(self.mock_task_repository), '__call__') as mock_constructor:
            mock_new_repo = Mock()
            mock_constructor.return_value = mock_new_repo
            
            result = self.service._get_user_scoped_repository()
            
            assert result == mock_new_repo
            mock_constructor.assert_called_once_with(
                self.mock_task_repository.session, 
                user_id=self.user_id
            )

    def test_get_user_scoped_repository_fallback(self):
        """Test fallback when repository doesn't support user scoping"""
        # Remove with_user method
        del self.mock_task_repository.with_user
        
        result = self.service._get_user_scoped_repository()
        
        assert result == self.mock_task_repository

    def test_with_user(self):
        """Test creating user-scoped service instance"""
        new_user_id = "new-user-456"
        
        new_service = self.service.with_user(new_user_id)
        
        assert isinstance(new_service, DependencyResolverService)
        assert new_service.task_repository == self.mock_task_repository
        assert new_service._user_id == new_user_id

    def test_resolve_dependencies_task_not_found(self):
        """Test resolving dependencies when task is not found"""
        task_id = "task-123"
        
        # Setup repository to return None (task not found)
        self.mock_task_repository.find_by_id.return_value = None
        
        with pytest.raises(TaskNotFoundError):
            self.service.resolve_dependencies(task_id)

    def test_resolve_dependencies_success(self):
        """Test successful dependency resolution"""
        task_id = "task-123"
        
        # Setup main task
        mock_main_task = Mock()
        mock_main_task.get_dependency_ids.return_value = ["dep-1", "dep-2"]
        mock_main_task.status.value = "todo"
        mock_main_task.title = "Main Task"
        mock_main_task.priority.value = "high"
        mock_main_task.overall_progress = 0
        mock_main_task.estimated_effort = "2 hours"
        mock_main_task.assignees = ["user1"]
        mock_main_task.updated_at = datetime.now()
        
        # Setup dependency tasks
        mock_dep1 = Mock()
        mock_dep1.id = "dep-1"
        mock_dep1.title = "Dependency 1"
        mock_dep1.status.value = "done"
        mock_dep1.priority.value = "medium"
        mock_dep1.overall_progress = 100
        mock_dep1.estimated_effort = "1 hour"
        mock_dep1.assignees = ["user1"]
        mock_dep1.updated_at = datetime.now()
        mock_dep1.get_dependency_ids.return_value = []
        
        mock_dep2 = Mock()
        mock_dep2.id = "dep-2"
        mock_dep2.title = "Dependency 2"
        mock_dep2.status.value = "in_progress"
        mock_dep2.priority.value = "low"
        mock_dep2.overall_progress = 50
        mock_dep2.estimated_effort = "3 hours"
        mock_dep2.assignees = ["user2"]
        mock_dep2.updated_at = datetime.now()
        mock_dep2.get_dependency_ids.return_value = []
        
        # Setup repository responses
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == task_id:
                return mock_main_task
            elif task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                return mock_dep2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        self.mock_task_repository.find_all.return_value = [mock_main_task, mock_dep1, mock_dep2]
        
        result = self.service.resolve_dependencies(task_id)
        
        assert isinstance(result, DependencyRelationships)
        assert result.task_id == task_id
        assert result.total_dependencies == 2
        assert result.completed_dependencies == 1
        assert result.blocked_dependencies == 0
        assert result.can_start is False  # dep-2 is not done
        assert result.is_blocked is False  # no blocked dependencies
        assert result.is_blocking_others is False  # no blocking tasks in this simple case

    def test_resolve_dependencies_exception_handling(self):
        """Test exception handling during dependency resolution"""
        task_id = "task-123"
        
        # Setup main task
        mock_main_task = Mock()
        mock_main_task.get_dependency_ids.return_value = []
        
        # Setup repository to raise exception on second call
        self.mock_task_repository.find_by_id.side_effect = [mock_main_task, Exception("Database error")]
        
        result = self.service.resolve_dependencies(task_id)
        
        # Should return empty relationships on error
        assert isinstance(result, DependencyRelationships)
        assert result.task_id == task_id
        assert result.depends_on == []
        assert result.blocks == []
        assert result.total_dependencies == 0
        assert result.can_start is True
        assert result.dependency_summary == "Unable to resolve dependencies"

    def test_build_dependency_graph_simple(self):
        """Test building dependency graph with simple structure"""
        root_task_id = "task-1"
        
        # Setup tasks with dependencies
        mock_task1 = Mock()
        mock_task1.get_dependency_ids.return_value = ["task-2", "task-3"]
        
        mock_task2 = Mock()
        mock_task2.get_dependency_ids.return_value = []
        
        mock_task3 = Mock()
        mock_task3.get_dependency_ids.return_value = ["task-4"]
        
        mock_task4 = Mock()
        mock_task4.get_dependency_ids.return_value = []
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            task_map = {
                "task-1": mock_task1,
                "task-2": mock_task2,
                "task-3": mock_task3,
                "task-4": mock_task4
            }
            return task_map.get(task_id_str)
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        graph = self.service._build_dependency_graph(root_task_id)
        
        expected_graph = {
            "task-1": ["task-2", "task-3"],
            "task-2": [],
            "task-3": ["task-4"],
            "task-4": []
        }
        
        assert graph == expected_graph

    def test_build_dependency_graph_infinite_loop_prevention(self):
        """Test that dependency graph building prevents infinite loops"""
        root_task_id = "task-1"
        
        # Setup circular dependency
        mock_task1 = Mock()
        mock_task1.get_dependency_ids.return_value = ["task-2"]
        
        mock_task2 = Mock()
        mock_task2.get_dependency_ids.return_value = ["task-1"]  # Circular
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "task-1":
                return mock_task1
            elif task_id_str == "task-2":
                return mock_task2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        graph = self.service._build_dependency_graph(root_task_id)
        
        # Should handle circular dependency gracefully
        assert "task-1" in graph
        assert "task-2" in graph

    def test_resolve_direct_dependencies(self):
        """Test resolving direct dependencies"""
        dependency_ids = ["dep-1", "dep-2"]
        
        # Setup dependency tasks
        mock_dep1 = Mock()
        mock_dep1.title = "Dependency 1"
        mock_dep1.status.value = "done"
        mock_dep1.priority.value = "high"
        mock_dep1.overall_progress = 100
        mock_dep1.estimated_effort = "2 hours"
        mock_dep1.assignees = ["user1"]
        mock_dep1.updated_at = datetime.now()
        mock_dep1.get_dependency_ids.return_value = []
        
        mock_dep2 = Mock()
        mock_dep2.title = "Dependency 2"
        mock_dep2.status.value = "in_progress"
        mock_dep2.priority.value = "medium"
        mock_dep2.overall_progress = 50
        mock_dep2.estimated_effort = "1 hour"
        mock_dep2.assignees = []
        mock_dep2.updated_at = datetime.now()
        mock_dep2.get_dependency_ids.return_value = []
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                return mock_dep2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        result = self.service._resolve_direct_dependencies(dependency_ids)
        
        assert len(result) == 2
        assert result[0].task_id == "dep-1"
        assert result[0].title == "Dependency 1"
        assert result[0].status == "done"
        assert result[1].task_id == "dep-2"
        assert result[1].title == "Dependency 2"
        assert result[1].status == "in_progress"

    def test_resolve_direct_dependencies_with_exception(self):
        """Test resolving direct dependencies when exception occurs"""
        dependency_ids = ["dep-1", "dep-2"]
        
        # Setup one successful, one exception
        mock_dep1 = Mock()
        mock_dep1.title = "Dependency 1"
        mock_dep1.status.value = "done"
        mock_dep1.priority.value = "high"
        mock_dep1.overall_progress = 100
        mock_dep1.estimated_effort = "2 hours"
        mock_dep1.assignees = ["user1"]
        mock_dep1.updated_at = datetime.now()
        mock_dep1.get_dependency_ids.return_value = []
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                raise Exception("Task not found")
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        result = self.service._resolve_direct_dependencies(dependency_ids)
        
        # Should only return the successful one
        assert len(result) == 1
        assert result[0].task_id == "dep-1"

    def test_resolve_blocking_tasks(self):
        """Test finding tasks that are blocked by a given task"""
        task_id = "task-1"
        
        # Setup tasks where some depend on task-1
        mock_task1 = Mock()
        mock_task1.id = "task-1"
        mock_task1.get_dependency_ids.return_value = []
        
        mock_task2 = Mock()
        mock_task2.id = "task-2"
        mock_task2.title = "Blocked Task 1"
        mock_task2.status.value = "todo"
        mock_task2.priority.value = "high"
        mock_task2.overall_progress = 0
        mock_task2.estimated_effort = "3 hours"
        mock_task2.assignees = ["user1"]
        mock_task2.updated_at = datetime.now()
        mock_task2.get_dependency_ids.return_value = ["task-1"]  # Depends on task-1
        
        mock_task3 = Mock()
        mock_task3.id = "task-3"
        mock_task3.title = "Independent Task"
        mock_task3.status.value = "done"
        mock_task3.priority.value = "low"
        mock_task3.overall_progress = 100
        mock_task3.estimated_effort = "1 hour"
        mock_task3.assignees = []
        mock_task3.updated_at = datetime.now()
        mock_task3.get_dependency_ids.return_value = []  # No dependencies
        
        self.mock_task_repository.find_all.return_value = [mock_task1, mock_task2, mock_task3]
        
        result = self.service._resolve_blocking_tasks(task_id)
        
        # Should only return task-2 since it depends on task-1
        assert len(result) == 1
        assert result[0].task_id == "task-2"
        assert result[0].title == "Blocked Task 1"
        assert result[0].is_blocking is True

    def test_can_task_start(self):
        """Test checking if task can start based on dependencies"""
        # All dependencies completed
        deps_completed = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="done", priority="medium",
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        # Some dependencies not completed
        deps_incomplete = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="in_progress", priority="medium",
                          completion_percentage=50, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        assert self.service._can_task_start(deps_completed) is True
        assert self.service._can_task_start(deps_incomplete) is False
        assert self.service._can_task_start([]) is True  # No dependencies

    def test_is_task_blocked(self):
        """Test checking if task is blocked by dependencies"""
        # No blocked dependencies
        deps_not_blocked = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="in_progress", priority="medium",
                          completion_percentage=50, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        # Some dependencies blocked
        deps_blocked = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="blocked", priority="medium",
                          completion_percentage=0, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        assert self.service._is_task_blocked(deps_not_blocked) is False
        assert self.service._is_task_blocked(deps_blocked) is True
        assert self.service._is_task_blocked([]) is False  # No dependencies

    def test_is_task_blocked_by_dependencies(self):
        """Test checking if a task is blocked by its dependencies"""
        # Setup task with dependencies
        mock_task = Mock()
        mock_task.get_dependency_ids.return_value = ["dep-1", "dep-2"]
        
        # Setup dependency tasks
        mock_dep1 = Mock()
        mock_dep1.status.value = "done"
        
        mock_dep2 = Mock()
        mock_dep2.status.value = "in_progress"  # Not done, so blocking
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                return mock_dep2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        result = self.service._is_task_blocked_by_dependencies(mock_task)
        
        assert result is True  # dep-2 is in_progress, so task is blocked

    def test_is_task_blocked_by_dependencies_all_done(self):
        """Test task not blocked when all dependencies are done"""
        mock_task = Mock()
        mock_task.get_dependency_ids.return_value = ["dep-1", "dep-2"]
        
        mock_dep1 = Mock()
        mock_dep1.status.value = "done"
        
        mock_dep2 = Mock()
        mock_dep2.status.value = "done"
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                return mock_dep2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        result = self.service._is_task_blocked_by_dependencies(mock_task)
        
        assert result is False

    def test_generate_dependency_summary(self):
        """Test generating dependency summary"""
        depends_on = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="in_progress", priority="medium",
                          completion_percentage=50, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        blocks = [
            DependencyInfo(task_id="block1", title="Blocked 1", status="todo", priority="high", 
                          completion_percentage=0, is_blocking=True, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now())
        ]
        
        summary = self.service._generate_dependency_summary(depends_on, blocks)
        
        assert "Depends on 2 task(s) (1/2 completed)" in summary
        assert "Blocks 1 task(s)" in summary

    def test_generate_dependency_summary_no_dependencies(self):
        """Test generating summary when there are no dependencies"""
        summary = self.service._generate_dependency_summary([], [])
        assert summary == "No dependencies"

    def test_generate_next_actions(self):
        """Test generating next actions"""
        depends_on_ready = []  # No dependencies
        blocks = []
        
        actions = self.service._generate_next_actions(depends_on_ready, blocks, True)
        
        assert "✅ Ready to start - no blocking dependencies" in actions

    def test_generate_next_actions_with_incomplete_dependencies(self):
        """Test generating next actions with incomplete dependencies"""
        depends_on = [
            DependencyInfo(task_id="dep1", title="Dep 1", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Dep 2", status="todo", priority="medium",
                          completion_percentage=0, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        blocks = [
            DependencyInfo(task_id="block1", title="Blocked 1", status="todo", priority="high", 
                          completion_percentage=0, is_blocking=True, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now())
        ]
        
        actions = self.service._generate_next_actions(depends_on, blocks, False)
        
        assert any("Wait for 1 dependencies to complete" in action for action in actions)
        assert any("Consider working on 1 unstarted dependencies" in action for action in actions)
        assert any("Completing this task will unblock 1 other task(s)" in action for action in actions)

    def test_generate_blocking_reasons(self):
        """Test generating blocking reasons"""
        depends_on = [
            DependencyInfo(task_id="dep1", title="Completed Dep", status="done", priority="high", 
                          completion_percentage=100, is_blocking=False, is_blocked=False, 
                          estimated_effort="1h", assignees=[], updated_at=datetime.now()),
            DependencyInfo(task_id="dep2", title="Blocking Dep", status="in_progress", priority="medium",
                          completion_percentage=50, is_blocking=False, is_blocked=False, 
                          estimated_effort="2h", assignees=[], updated_at=datetime.now())
        ]
        
        reasons = self.service._generate_blocking_reasons(depends_on)
        
        # Should only include non-done dependencies
        assert len(reasons) == 1
        assert "'Blocking Dep' (in_progress)" in reasons

    def test_build_upstream_chains(self):
        """Test building upstream dependency chains"""
        task_id = "task-1"
        dependency_graph = {
            "task-1": ["dep-1"],
            "dep-1": ["dep-2"],
            "dep-2": []
        }
        
        # Setup dependency tasks
        mock_dep1 = Mock()
        mock_dep1.title = "Dependency 1"
        mock_dep1.status.value = "in_progress"
        mock_dep1.priority.value = "high"
        mock_dep1.overall_progress = 50
        mock_dep1.estimated_effort = "2 hours"
        mock_dep1.assignees = ["user1"]
        mock_dep1.updated_at = datetime.now()
        mock_dep1.get_dependency_ids.return_value = ["dep-2"]
        
        mock_dep2 = Mock()
        mock_dep2.title = "Dependency 2"
        mock_dep2.status.value = "done"
        mock_dep2.priority.value = "medium"
        mock_dep2.overall_progress = 100
        mock_dep2.estimated_effort = "1 hour"
        mock_dep2.assignees = ["user2"]
        mock_dep2.updated_at = datetime.now()
        mock_dep2.get_dependency_ids.return_value = []
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dep-1":
                return mock_dep1
            elif task_id_str == "dep-2":
                return mock_dep2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        chains = self.service._build_upstream_chains(task_id, dependency_graph)
        
        assert len(chains) == 1
        chain = chains[0]
        assert chain.chain_id == "upstream_dep-1"
        assert chain.total_tasks >= 1
        assert chain.chain_status == "in_progress"

    def test_build_downstream_chains(self):
        """Test building downstream dependency chains"""
        task_id = "task-1"
        dependency_graph = {
            "task-1": [],
            "dependent-1": ["task-1"],  # depends on task-1
            "dependent-2": ["task-1"]   # also depends on task-1
        }
        
        # Setup dependent tasks
        mock_dependent1 = Mock()
        mock_dependent1.title = "Dependent 1"
        mock_dependent1.status.value = "todo"
        mock_dependent1.priority.value = "high"
        mock_dependent1.overall_progress = 0
        mock_dependent1.estimated_effort = "3 hours"
        mock_dependent1.assignees = ["user1"]
        mock_dependent1.updated_at = datetime.now()
        
        mock_dependent2 = Mock()
        mock_dependent2.title = "Dependent 2"
        mock_dependent2.status.value = "in_progress"
        mock_dependent2.priority.value = "medium"
        mock_dependent2.overall_progress = 25
        mock_dependent2.estimated_effort = "2 hours"
        mock_dependent2.assignees = ["user2"]
        mock_dependent2.updated_at = datetime.now()
        
        def find_by_id_side_effect(task_id_obj):
            task_id_str = str(task_id_obj)
            if task_id_str == "dependent-1":
                return mock_dependent1
            elif task_id_str == "dependent-2":
                return mock_dependent2
            return None
        
        self.mock_task_repository.find_by_id.side_effect = find_by_id_side_effect
        
        chains = self.service._build_downstream_chains(task_id, dependency_graph)
        
        assert len(chains) == 2
        chain_ids = [chain.chain_id for chain in chains]
        assert "downstream_dependent-1" in chain_ids
        assert "downstream_dependent-2" in chain_ids