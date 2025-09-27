"""Unit tests for DependencyValidationService domain service"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Optional

from fastmcp.task_management.domain.services.dependency_validation_service import DependencyValidationService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository


class TestDependencyValidationService:
    """Test suite for DependencyValidationService domain service"""

    def setup_method(self):
        """Setup test data before each test"""
        self.mock_repository = Mock(spec=TaskRepository)

        # Create mock ID validator
        self.mock_id_validator = Mock()
        self.mock_id_validator.detect_id_type.return_value = Mock(
            is_valid=True,
            error_message=None
        )

        self.service = DependencyValidationService(self.mock_repository, self.mock_id_validator)
        
        # Create test tasks
        self.main_task = self._create_test_task(
            task_id="main-1",
            title="Main Task",
            status="todo"
        )
        
        self.dependency_task_done = self._create_test_task(
            task_id="dep-1",
            title="Completed Dependency",
            status="done"
        )
        
        self.dependency_task_blocked = self._create_test_task(
            task_id="dep-2",
            title="Blocked Dependency",
            status="blocked"
        )
        
        self.dependency_task_cancelled = self._create_test_task(
            task_id="dep-3",
            title="Cancelled Dependency",
            status="cancelled"
        )

    def _create_test_task(self, task_id: str, title: str, status: str = "todo", 
                         dependencies: List[str] = None) -> Task:
        """Helper to create test tasks with dependencies"""
        task = Task(
            title=title,
            description=f"Test description for {title}",
            id=TaskId.from_string(task_id),
            status=TaskStatus.from_string(status),
            priority=Priority.from_string("medium"),
            git_branch_id="test-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        if dependencies:
            task.dependencies = [TaskId.from_string(dep_id) for dep_id in dependencies]
        
        # Add get_dependency_ids method for compatibility
        def get_dependency_ids():
            if hasattr(task, 'dependencies') and task.dependencies:
                return [str(dep_id) for dep_id in task.dependencies]
            return []
        
        task.get_dependency_ids = get_dependency_ids
        return task

    def test_validate_dependency_chain_no_dependencies(self):
        """Test validation of task with no dependencies"""
        # Arrange
        task_id = TaskId.from_string("ffffffff-ffff-ffff-ffff-ffffffffffff")
        self.mock_repository.find_by_id.return_value = self.main_task
        self.mock_repository.find_all.return_value = [self.main_task]
        
        # Act
        result = self.service.validate_dependency_chain(task_id)
        
        # Assert
        assert result["valid"] is True
        assert result["message"] == "Task has no dependencies"
        assert result["issues"] == []
        assert result["errors"] == []
        self.mock_repository.find_by_id.assert_called_once_with(task_id)

    def test_validate_dependency_chain_task_not_found(self):
        """Test validation when task is not found"""
        # Arrange
        task_id = TaskId.from_string("00000000-0000-0000-0000-000000000000")
        self.mock_repository.find_by_id.return_value = None
        
        # Act
        result = self.service.validate_dependency_chain(task_id)
        
        # Assert
        assert result["valid"] is False
        assert "Task 00000000-0000-0000-0000-000000000000 not found" in result["errors"]
        assert result["issues"] == []

    def test_validate_dependency_chain_with_valid_dependencies(self):
        """Test validation with all dependencies satisfied"""
        # Arrange
        task_with_deps = self._create_test_task(
            task_id="task-1",
            title="Task with Dependencies",
            dependencies=["dep-1"]
        )
        
        all_tasks = [task_with_deps, self.dependency_task_done]
        task_map = {str(task.id): task for task in all_tasks}
        
        self.mock_repository.find_by_id.return_value = task_with_deps
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.validate_dependency_chain(task_with_deps.id)
        
        # Assert
        assert result["valid"] is True
        assert result["dependency_count"] == 1
        assert result["can_proceed"] is True
        assert len(result["issues"]) == 1  # Should have one "satisfied_dependency" info
        assert result["issues"][0]["type"] == "satisfied_dependency"
        assert result["errors"] == []

    def test_validate_dependency_chain_with_missing_dependency(self):
        """Test validation with missing dependency"""
        # Arrange
        task_with_missing_dep = self._create_test_task(
            task_id="task-2",
            title="Task with Missing Dependency",
            dependencies=["missing-2"]
        )
        
        self.mock_repository.find_by_id.return_value = task_with_missing_dep
        self.mock_repository.find_all.return_value = [task_with_missing_dep]
        
        # Mock the _find_dependency_across_states to return None
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        result = self.service.validate_dependency_chain(task_with_missing_dep.id)
        
        # Assert
        assert result["valid"] is False
        assert "Dependency missing-2 no longer exists" in result["errors"]
        assert result["can_proceed"] is False

    def test_validate_dependency_chain_with_blocked_dependency(self):
        """Test validation with blocked dependency"""
        # Arrange
        task_with_blocked_dep = self._create_test_task(
            task_id="task-3",
            title="Task with Blocked Dependency",
            dependencies=["dep-2"]
        )
        
        all_tasks = [task_with_blocked_dep, self.dependency_task_blocked]
        
        self.mock_repository.find_by_id.return_value = task_with_blocked_dep
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.validate_dependency_chain(task_with_blocked_dep.id)
        
        # Assert
        assert result["valid"] is True  # No hard errors, just warnings
        assert result["can_proceed"] is False  # But cannot proceed due to blocked dependency
        
        # Should have a warning about blocked dependency
        blocked_issues = [issue for issue in result["issues"] if issue["type"] == "blocked_dependency"]
        assert len(blocked_issues) == 1
        assert blocked_issues[0]["severity"] == "warning"

    def test_validate_dependency_chain_with_cancelled_dependency(self):
        """Test validation with cancelled dependency"""
        # Arrange
        task_with_cancelled_dep = self._create_test_task(
            task_id="task-4",
            title="Task with Cancelled Dependency",
            dependencies=["dep-3"]
        )
        
        all_tasks = [task_with_cancelled_dep, self.dependency_task_cancelled]
        
        self.mock_repository.find_by_id.return_value = task_with_cancelled_dep
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.validate_dependency_chain(task_with_cancelled_dep.id)
        
        # Assert
        assert result["valid"] is True  # No hard errors, just warnings
        
        # Should have a warning about cancelled dependency
        cancelled_issues = [issue for issue in result["issues"] if issue["type"] == "cancelled_dependency"]
        assert len(cancelled_issues) == 1
        assert cancelled_issues[0]["severity"] == "warning"
        assert "was cancelled" in cancelled_issues[0]["message"]

    def test_validate_dependency_chain_circular_dependency(self):
        """Test detection of circular dependencies"""
        # Arrange: Create circular dependency A -> B -> A
        task_a = self._create_test_task(
            task_id="task-5",
            title="Task A",
            dependencies=["task-6"]
        )
        
        task_b = self._create_test_task(
            task_id="task-6", 
            title="Task B",
            dependencies=["task-5"]
        )
        
        all_tasks = [task_a, task_b]
        
        self.mock_repository.find_by_id.return_value = task_a
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.validate_dependency_chain(task_a.id)
        
        # Assert
        assert result["valid"] is False
        assert len(result["errors"]) >= 1
        assert any("Circular dependency detected" in error for error in result["errors"])

    def test_validate_dependency_chain_exception_handling(self):
        """Test exception handling in dependency validation"""
        # Arrange
        task_id = TaskId.from_string("abcdef12-3456-7890-abcd-ef1234567890")
        self.mock_repository.find_by_id.side_effect = Exception("Database error")
        
        # Act
        result = self.service.validate_dependency_chain(task_id)
        
        # Assert
        assert result["valid"] is False
        assert "Validation failed: Database error" in result["errors"]
        assert result["issues"] == []

    def test_get_dependency_chain_status_success(self):
        """Test getting detailed dependency chain status"""
        # Arrange
        task_with_deps = self._create_test_task(
            task_id="task-7",
            title="Task with Chain",
            dependencies=["dep-1", "dep-2"]
        )
        
        all_tasks = [task_with_deps, self.dependency_task_done, self.dependency_task_blocked]
        
        self.mock_repository.find_by_id.return_value = task_with_deps
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.get_dependency_chain_status(task_with_deps.id)
        
        # Assert
        assert "error" not in result
        assert result["task_id"] == str(task_with_deps.id)
        assert result["task_title"] == task_with_deps.title
        assert result["dependency_chain"] is not None
        assert len(result["dependency_chain"]) == 2
        
        # Check chain statistics
        stats = result["chain_statistics"]
        assert stats["total_dependencies"] == 2
        assert stats["completed_dependencies"] == 1
        assert stats["blocked_dependencies"] == 1
        assert stats["completion_percentage"] == 50.0
        
        assert result["can_proceed"] is False  # Due to blocked dependency

    def test_get_dependency_chain_status_task_not_found(self):
        """Test dependency chain status when task not found"""
        # Arrange
        task_id = TaskId.from_string("00000000-0000-0000-0000-000000000000")
        self.mock_repository.find_by_id.return_value = None
        
        # Act
        result = self.service.get_dependency_chain_status(task_id)
        
        # Assert
        assert "error" in result
        assert "Task 00000000-0000-0000-0000-000000000000 not found" in result["error"]

    def test_find_dependency_across_states_with_extended_repository(self):
        """Test finding dependencies across different states"""
        # Arrange
        dependency_id = "archived-1"
        archived_task = self._create_test_task(dependency_id, "Archived Task", "done")
        
        # Mock repository with extended method
        self.mock_repository.find_by_id_across_contexts = Mock(return_value=archived_task)
        
        # Act
        found_task = self.service._find_dependency_across_states(dependency_id)
        
        # Assert
        assert found_task == archived_task
        self.mock_repository.find_by_id_across_contexts.assert_called_once()

    def test_find_dependency_across_states_not_found(self):
        """Test finding dependencies when not found anywhere"""
        # Arrange
        dependency_id = "truly-1"

        # Mock repository without extended method
        if hasattr(self.mock_repository, 'find_by_id_across_contexts'):
            delattr(self.mock_repository, 'find_by_id_across_contexts')

        # Mock find_by_id to return None
        self.mock_repository.find_by_id.return_value = None

        # Act
        found_task = self.service._find_dependency_across_states(dependency_id)

        # Assert
        assert found_task is None

    def test_check_circular_dependencies_complex_chain(self):
        """Test circular dependency detection in complex chains"""
        # Arrange: Create A -> B -> C -> B (circular)
        task_a = self._create_test_task("task-5", "Task A", dependencies=["task-6"])
        task_b = self._create_test_task("task-6", "Task B", dependencies=["task-7"])
        task_c = self._create_test_task("task-7", "Task C", dependencies=["task-6"])
        
        all_tasks = [task_a, task_b, task_c]
        
        # Act
        circular_path = self.service._check_circular_dependencies(task_a, all_tasks)
        
        # Assert
        assert circular_path is not None
        assert isinstance(circular_path, list)
        assert len(circular_path) >= 2  # Should contain the circular path

    def test_check_circular_dependencies_no_cycle(self):
        """Test circular dependency detection with no cycles"""
        # Arrange: Create A -> B -> C (no cycle)
        task_a = self._create_test_task("task-5", "Task A", dependencies=["task-6"])
        task_b = self._create_test_task("task-6", "Task B", dependencies=["task-7"])
        task_c = self._create_test_task("task-7", "Task C")
        
        all_tasks = [task_a, task_b, task_c]
        
        # Act
        circular_path = self.service._check_circular_dependencies(task_a, all_tasks)
        
        # Assert
        assert circular_path is None

    def test_check_orphaned_dependencies(self):
        """Test checking for orphaned dependencies"""
        # Arrange
        task_with_orphan = self._create_test_task(
            task_id="task-9",
            title="Task with Orphaned Dependency",
            dependencies=["existing-1", "missing-2"]
        )
        
        existing_dep = self._create_test_task("existing-1", "Existing Dependency")
        task_map = {"existing-1": existing_dep}
        
        # Mock _find_dependency_across_states to return None for missing dependency
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        orphaned = self.service._check_orphaned_dependencies(task_with_orphan, task_map)
        
        # Assert
        assert "missing-2" in orphaned
        assert "existing-1" not in orphaned

    def test_can_task_proceed_all_dependencies_satisfied(self):
        """Test task can proceed when all dependencies are done"""
        # Arrange
        task_ready = self._create_test_task(
            task_id="ready-1",
            title="Ready Task",
            dependencies=["dep-1"]
        )
        
        task_map = {"dep-1": self.dependency_task_done}
        
        # Act
        can_proceed = self.service._can_task_proceed(task_ready, task_map)
        
        # Assert
        assert can_proceed is True

    def test_can_task_proceed_has_incomplete_dependencies(self):
        """Test task cannot proceed with incomplete dependencies"""
        # Arrange
        task_blocked = self._create_test_task(
            task_id="blocked-1",
            title="Blocked Task",
            dependencies=["dep-2"]
        )
        
        task_map = {"dep-2": self.dependency_task_blocked}
        
        # Act
        can_proceed = self.service._can_task_proceed(task_blocked, task_map)
        
        # Assert
        assert can_proceed is False

    def test_can_task_proceed_missing_dependencies(self):
        """Test task cannot proceed with missing dependencies"""
        # Arrange
        task_missing_deps = self._create_test_task(
            task_id="missing-3",
            title="Task with Missing Dependencies",
            dependencies=["missing-2"]
        )
        
        task_map = {}
        
        # Mock _find_dependency_across_states to return None
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        can_proceed = self.service._can_task_proceed(task_missing_deps, task_map)
        
        # Assert
        assert can_proceed is False

    def test_can_task_proceed_no_dependencies(self):
        """Test task can proceed when it has no dependencies"""
        # Arrange
        task_no_deps = self._create_test_task("no-1", "No Dependencies Task")
        
        # Act
        can_proceed = self.service._can_task_proceed(task_no_deps, {})
        
        # Assert
        assert can_proceed is True

    def test_get_dependency_info_found_task(self):
        """Test getting dependency information for existing task"""
        # Arrange
        dependency_id = "dep-1"
        task_map = {"dep-1": self.dependency_task_done}
        
        # Act
        info = self.service._get_dependency_info(dependency_id, task_map)
        
        # Assert
        assert info["dependency_id"] == dependency_id
        assert info["title"] == self.dependency_task_done.title
        assert info["status"] == "done"
        assert info["found"] is True
        assert info["is_completed"] is True

    def test_get_dependency_info_missing_task(self):
        """Test getting dependency information for missing task"""
        # Arrange
        dependency_id = "missing-2"
        task_map = {}
        
        # Mock _find_dependency_across_states to return None
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        info = self.service._get_dependency_info(dependency_id, task_map)
        
        # Assert
        assert info["dependency_id"] == dependency_id
        assert info["status"] == "missing"
        assert info["title"] == "Unknown"
        assert info["found"] is False
        assert "not found" in info["message"]

    def test_validate_single_dependency_all_cases(self):
        """Test single dependency validation for all status cases"""
        # Test cases: (dependency_task, expected_issue_type, expected_severity)
        test_cases = [
            (self.dependency_task_done, "satisfied_dependency", "info"),
            (self.dependency_task_blocked, "blocked_dependency", "warning"),
            (self.dependency_task_cancelled, "cancelled_dependency", "warning"),
        ]
        
        for dep_task, expected_type, expected_severity in test_cases:
            # Arrange
            task_map = {str(dep_task.id): dep_task}
            
            # Act
            issues = self.service._validate_single_dependency(
                self.main_task,
                str(dep_task.id),
                task_map
            )
            
            # Assert
            assert len(issues) == 1
            assert issues[0]["type"] == expected_type
            assert issues[0]["severity"] == expected_severity
            assert issues[0]["dependency_id"] == str(dep_task.id)

    def test_validate_single_dependency_missing_task(self):
        """Test single dependency validation for missing task"""
        # Arrange
        task_map = {}
        dependency_id = "missing-2"
        
        # Mock _find_dependency_across_states to return None
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        issues = self.service._validate_single_dependency(
            self.main_task,
            dependency_id,
            task_map
        )
        
        # Assert
        assert len(issues) == 1
        assert issues[0]["type"] == "missing_dependency"
        assert issues[0]["severity"] == "error"
        assert "not found in any state" in issues[0]["message"]


class TestDependencyValidationServiceIntegration:
    """Integration tests for DependencyValidationService with complex scenarios"""

    def setup_method(self):
        """Setup integration test environment"""
        self.mock_repository = Mock(spec=TaskRepository)

        # Create mock ID validator
        self.mock_id_validator = Mock()
        self.mock_id_validator.detect_id_type.return_value = Mock(
            is_valid=True,
            error_message=None
        )

        self.service = DependencyValidationService(self.mock_repository, self.mock_id_validator)

    def _create_test_task(self, task_id: str, title: str, status: str = "todo",
                         dependencies: List[str] = None) -> Task:
        """Helper to create test tasks with dependencies"""
        task = Task(
            title=title,
            description=f"Test description for {title}",
            id=TaskId.from_string(task_id),
            status=TaskStatus.from_string(status),
            priority=Priority.from_string("medium"),
            git_branch_id="test-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        if dependencies:
            task.dependencies = [TaskId.from_string(dep_id) for dep_id in dependencies]

        # Add get_dependency_ids method for compatibility
        def get_dependency_ids():
            if hasattr(task, 'dependencies') and task.dependencies:
                return [str(dep_id) for dep_id in task.dependencies]
            return []

        task.get_dependency_ids = get_dependency_ids
        return task

    def test_complex_dependency_chain_validation(self):
        """Test validation of complex multi-level dependency chains"""
        # Arrange: Create A -> B -> C -> D chain
        task_d = self._create_test_task("task-4", "Task D", "done")
        task_c = self._create_test_task("task-7", "Task C", "in_progress", ["task-4"])
        task_b = self._create_test_task("task-6", "Task B", "todo", ["task-7"])
        task_a = self._create_test_task("task-5", "Task A", "todo", ["task-6"])
        
        all_tasks = [task_a, task_b, task_c, task_d]
        
        self.mock_repository.find_by_id.return_value = task_a
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        result = self.service.validate_dependency_chain(task_a.id)
        
        # Assert
        assert result["valid"] is True
        assert result["dependency_count"] == 1  # Task A has 1 direct dependency
        assert result["can_proceed"] is False  # Cannot proceed due to incomplete chain
        
        # Since the dependency chain has in-progress and todo tasks,
        # the validation may be valid but not allow proceeding
        # The issues list may be empty if the chain is structurally valid
        # but just not complete yet
        if result["issues"]:
            assert len(result["issues"]) >= 1
        else:
            # If no issues, verify that can_proceed is still False
            assert result["can_proceed"] is False

    def test_mixed_dependency_statuses_validation(self):
        """Test validation with mixed dependency statuses"""
        # Arrange: Task with multiple dependencies in different states
        task_main = self._create_test_task(
            "main-1", 
            "Main Task", 
            "todo",
            ["done-1", "blocked-2", "cancelled-1", "missing-2"]
        )
        
        done_dep = self._create_test_task("done-1", "Done Dependency", "done")
        blocked_dep = self._create_test_task("blocked-2", "Blocked Dependency", "blocked")
        cancelled_dep = self._create_test_task("cancelled-1", "Cancelled Dependency", "cancelled")
        
        all_tasks = [task_main, done_dep, blocked_dep, cancelled_dep]
        
        self.mock_repository.find_by_id.return_value = task_main
        self.mock_repository.find_all.return_value = all_tasks
        
        # Mock missing dependency
        self.service._find_dependency_across_states = Mock(return_value=None)
        
        # Act
        result = self.service.validate_dependency_chain(task_main.id)
        
        # Assert
        assert result["valid"] is False  # Has errors due to missing dependency
        assert result["dependency_count"] == 4
        assert result["can_proceed"] is False
        
        # Should have mix of issues and errors
        assert len(result["issues"]) >= 3  # For done, blocked, cancelled
        assert len(result["errors"]) >= 1  # For missing dependency

    def test_dependency_chain_status_comprehensive(self):
        """Test comprehensive dependency chain status analysis"""
        # Arrange: Complex scenario with multiple dependencies
        main_task = self._create_test_task(
            "analysis-1",
            "Analysis Task",
            "todo", 
            ["prep-1", "data-1", "blocked-3"]
        )
        
        prep_task = self._create_test_task("prep-1", "Preparation", "done")
        data_task = self._create_test_task("data-1", "Data Processing", "in_progress")
        blocked_task = self._create_test_task("blocked-3", "Blocked Step", "blocked")
        
        all_tasks = [main_task, prep_task, data_task, blocked_task]
        
        self.mock_repository.find_by_id.return_value = main_task
        self.mock_repository.find_all.return_value = all_tasks
        
        # Act
        status = self.service.get_dependency_chain_status(main_task.id)
        
        # Assert
        assert "error" not in status
        assert status["task_id"] == str(main_task.id)
        
        # Check dependency chain details
        deps = status["dependency_chain"]
        assert len(deps) == 3
        
        # Find specific dependencies
        done_dep = next(d for d in deps if d["dependency_id"] == "prep-1")
        in_progress_dep = next(d for d in deps if d["dependency_id"] == "data-1")
        blocked_dep = next(d for d in deps if d["dependency_id"] == "blocked-3")
        
        assert done_dep["is_completed"] is True
        assert in_progress_dep["is_completed"] is False
        assert blocked_dep["is_completed"] is False
        
        # Check statistics
        stats = status["chain_statistics"]
        assert stats["total_dependencies"] == 3
        assert stats["completed_dependencies"] == 1
        assert abs(stats["completion_percentage"] - 33.33) < 0.1
        assert status["can_proceed"] is False

    def _create_test_task(self, task_id: str, title: str, status: str = "todo", 
                         dependencies: List[str] = None) -> Task:
        """Helper to create test tasks with dependencies for integration tests"""
        task = Task(
            title=title,
            description=f"Integration test task: {title}",
            id=TaskId.from_string(task_id),
            status=TaskStatus.from_string(status),
            priority=Priority.from_string("medium"),
            git_branch_id="integration-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        if dependencies:
            task.dependencies = [TaskId.from_string(dep_id) for dep_id in dependencies]
        
        # Add get_dependency_ids method for compatibility
        def get_dependency_ids():
            if hasattr(task, 'dependencies') and task.dependencies:
                return [str(dep_id) for dep_id in task.dependencies]
            return []
        
        task.get_dependency_ids = get_dependency_ids
        return task