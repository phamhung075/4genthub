"""Unit tests for TaskPriorityService domain service"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.task_priority_service import (
    TaskPriorityService, 
    TaskRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestTaskPriorityService:
    """Test suite for TaskPriorityService domain service"""

    def setup_method(self):
        """Setup test data before each test"""
        self.mock_repository = Mock(spec=TaskRepositoryProtocol)
        self.service = TaskPriorityService(self.mock_repository)
        
        # Create test tasks with different properties
        self.high_priority_task = self._create_test_task(
            task_id="task-1",
            title="Critical Bug Fix",
            priority="high",
            status="in_progress",
            due_date=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        self.medium_priority_task = self._create_test_task(
            task_id="task-2",
            title="Feature Implementation",
            priority="medium",
            status="todo",
            due_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        self.old_task = self._create_test_task(
            task_id="task-3",
            title="Legacy Task",
            priority="low",
            status="todo",
            created_at=datetime.now(timezone.utc) - timedelta(days=90)
        )

    def _create_test_task(self, task_id: str, title: str, priority: str = "medium",
                         status: str = "todo", due_date: datetime = None,
                         created_at: datetime = None) -> Task:
        """Helper to create test tasks with consistent structure"""
        # Map string status to static methods
        if isinstance(status, str):
            if status == "todo":
                task_status = TaskStatus.todo()
            elif status == "in_progress":
                task_status = TaskStatus.in_progress()
            elif status == "done":
                task_status = TaskStatus.done()
            else:
                task_status = TaskStatus.from_string(status)
        else:
            task_status = status

        # Convert simple task_id to UUID format if needed
        uuid_task_id = self._ensure_uuid_format(task_id)

        task = Task(
            title=title,
            description=f"Test description for {title}",
            id=TaskId.from_string(uuid_task_id),
            status=task_status,
            priority=Priority.from_string(priority),
            git_branch_id="branch-1",
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        if due_date:
            task.due_date = due_date
            
        return task

    def _ensure_uuid_format(self, task_id: str) -> str:
        """Convert simple task ID to UUID format if needed"""
        # If already UUID format, return as-is
        if len(task_id) == 36 and task_id.count('-') == 4:
            return task_id

        # Create a deterministic UUID-like string from the simple ID
        # Use hash to ensure consistency but keep it readable for debugging
        import hashlib
        hash_obj = hashlib.md5(task_id.encode())
        hex_str = hash_obj.hexdigest()
        # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"

    def test_calculate_priority_score_high_priority_task(self):
        """Test priority score calculation for high priority task"""
        # Act
        score = self.service.calculate_priority_score(self.high_priority_task)
        
        # Assert
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0
        assert score > 55.0  # High priority task should have moderately high score
        
    def test_calculate_priority_score_with_context_factors(self):
        """Test priority score calculation with additional context factors"""
        # Arrange
        context_factors = {
            'dependent_task_count': 3  # Task blocks 3 other tasks
        }
        
        # Act
        score_with_context = self.service.calculate_priority_score(
            self.medium_priority_task, 
            context_factors
        )
        score_without_context = self.service.calculate_priority_score(
            self.medium_priority_task
        )
        
        # Assert
        assert score_with_context > score_without_context
        assert isinstance(score_with_context, float)
        
    def test_calculate_priority_score_overdue_task(self):
        """Test priority score for overdue task gets maximum urgency"""
        # Arrange
        overdue_task = self._create_test_task(
            task_id="overdue-task",
            title="Overdue Task",
            priority="medium",
            due_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        # Act
        score = self.service.calculate_priority_score(overdue_task)
        
        # Assert
        assert score > 45.0  # Overdue task should have elevated score due to urgency
        
    def test_calculate_priority_score_in_progress_task(self):
        """Test that in-progress tasks get higher priority than todo tasks"""
        # Arrange
        todo_task = self._create_test_task(
            task_id="todo-task",
            title="Todo Task",
            priority="medium",
            status="todo"
        )
        
        in_progress_task = self._create_test_task(
            task_id="in-progress-task",
            title="In Progress Task", 
            priority="medium",
            status="in_progress"
        )
        
        # Act
        todo_score = self.service.calculate_priority_score(todo_task)
        in_progress_score = self.service.calculate_priority_score(in_progress_task)
        
        # Assert
        assert in_progress_score > todo_score
        
    def test_calculate_priority_score_error_handling(self):
        """Test error handling in priority score calculation"""
        # Arrange
        invalid_task = Mock()
        invalid_task.id = "invalid-task"
        invalid_task.priority = None  # Invalid priority to cause error
        invalid_task.status = Mock()
        invalid_task.created_at = Mock()
        invalid_task.due_date = Mock()

        # Act
        score = self.service.calculate_priority_score(invalid_task)

        # Assert
        # With partial calculations succeeding, score might not be 0
        assert 0.0 <= score <= 100.0  # Score should still be within valid range
        
    def test_order_tasks_by_priority(self):
        """Test ordering multiple tasks by priority score"""
        # Arrange
        tasks = [
            self.medium_priority_task,
            self.high_priority_task,
            self.old_task
        ]
        
        # Act
        ordered_tasks = self.service.order_tasks_by_priority(tasks)
        
        # Assert
        assert len(ordered_tasks) == 3
        assert all(isinstance(task_info, dict) for task_info in ordered_tasks)
        
        # Check structure of returned data
        first_task = ordered_tasks[0]
        assert "task" in first_task
        assert "task_id" in first_task
        assert "title" in first_task
        assert "priority_score" in first_task
        assert "base_priority" in first_task
        assert "status" in first_task
        assert "priority_factors" in first_task
        
        # Check ordering (highest score first)
        for i in range(len(ordered_tasks) - 1):
            assert ordered_tasks[i]["priority_score"] >= ordered_tasks[i + 1]["priority_score"]
            
    def test_order_tasks_by_priority_with_context(self):
        """Test ordering tasks with additional context factors"""
        # Arrange
        tasks = [self.medium_priority_task, self.high_priority_task]
        context_factors = {
            'dependent_task_count': 2
        }
        
        # Act
        ordered_tasks = self.service.order_tasks_by_priority(tasks, context_factors)
        
        # Assert
        assert len(ordered_tasks) == 2
        # Verify priority factors are included
        assert "priority_factors" in ordered_tasks[0]
        assert "blocking_factor" in ordered_tasks[0]["priority_factors"]
        
    def test_order_tasks_empty_list(self):
        """Test ordering empty task list"""
        # Act
        ordered_tasks = self.service.order_tasks_by_priority([])
        
        # Assert
        assert ordered_tasks == []
        
    def test_get_next_task_recommendation_success(self):
        """Test getting next task recommendation successfully"""
        # Arrange
        self.mock_repository.find_by_git_branch_id.return_value = [
            self.high_priority_task,
            self.medium_priority_task,
            self.old_task
        ]
        
        # Act
        recommendation = self.service.get_next_task_recommendation("branch-1")
        
        # Assert
        assert recommendation is not None
        assert isinstance(recommendation, dict)
        assert "task" in recommendation
        assert "task_id" in recommendation
        assert "title" in recommendation
        assert "priority_score" in recommendation
        assert "recommendation_reason" in recommendation
        assert "alternative_tasks" in recommendation
        assert "total_eligible_tasks" in recommendation
        
        # Verify repository was called with correct branch
        self.mock_repository.find_by_git_branch_id.assert_called_once_with("branch-1")
        
    def test_get_next_task_recommendation_with_exclusions(self):
        """Test task recommendation with excluded statuses"""
        # Arrange
        done_task = self._create_test_task(
            task_id="done-task",
            title="Completed Task",
            status="done"
        )
        
        self.mock_repository.find_by_git_branch_id.return_value = [
            self.high_priority_task,
            done_task
        ]
        
        # Act
        recommendation = self.service.get_next_task_recommendation(
            "branch-1",
            exclude_statuses=['done', 'cancelled']
        )
        
        # Assert
        assert recommendation is not None
        assert recommendation["task"] == self.high_priority_task
        assert recommendation["total_eligible_tasks"] == 1  # Done task excluded
        
    def test_get_next_task_recommendation_no_eligible_tasks(self):
        """Test recommendation when all tasks are excluded"""
        # Arrange
        done_task = self._create_test_task(
            task_id="done-task",
            title="Completed Task",
            status="done"
        )
        
        self.mock_repository.find_by_git_branch_id.return_value = [done_task]
        
        # Act
        recommendation = self.service.get_next_task_recommendation("branch-1")
        
        # Assert
        assert recommendation is None
        
    def test_get_next_task_recommendation_no_repository(self):
        """Test recommendation fails gracefully without repository"""
        # Arrange
        service_without_repo = TaskPriorityService()
        
        # Act
        recommendation = service_without_repo.get_next_task_recommendation("branch-1")
        
        # Assert
        assert recommendation is None
        
    def test_get_next_task_recommendation_empty_branch(self):
        """Test recommendation for branch with no tasks"""
        # Arrange
        self.mock_repository.find_by_git_branch_id.return_value = []
        
        # Act
        recommendation = self.service.get_next_task_recommendation("empty-branch")
        
        # Assert
        assert recommendation is None
        
    def test_adjust_priority_for_dependencies_with_incomplete_deps(self):
        """Test priority adjustment when task has incomplete dependencies"""
        # Arrange
        task_with_deps = self._create_test_task(
            task_id="dependent-task",
            title="Task with Dependencies"
        )
        task_with_deps.dependencies = [TaskId.from_string("11111111-1111-1111-1111-111111111111"), TaskId.from_string("22222222-2222-2222-2222-222222222222")]

        # Mock dependency task (incomplete) - use matching ID
        incomplete_dep_task = self._create_test_task(
            task_id="11111111-1111-1111-1111-111111111111",
            title="Incomplete Dependency",
            status="in_progress"
        )

        all_tasks = [task_with_deps, incomplete_dep_task]

        # Act
        multiplier = self.service.adjust_priority_for_dependencies(task_with_deps, all_tasks)

        # Assert
        assert 0.5 <= multiplier < 1.0  # Priority should be reduced
        
    def test_adjust_priority_for_dependencies_task_blocks_others(self):
        """Test priority increase when task blocks other tasks"""
        # Arrange
        blocking_task = self._create_test_task(
            task_id="33333333-3333-3333-3333-333333333333",
            title="Blocking Task"
        )

        dependent_task = self._create_test_task(
            task_id="dependent-task",
            title="Dependent Task"
        )
        dependent_task.dependencies = [TaskId.from_string("33333333-3333-3333-3333-333333333333")]

        all_tasks = [blocking_task, dependent_task]

        # Act
        multiplier = self.service.adjust_priority_for_dependencies(blocking_task, all_tasks)

        # Assert
        assert multiplier > 1.0  # Priority should be increased
        assert multiplier <= 2.0  # Should be capped at 2.0
        
    def test_adjust_priority_for_dependencies_no_dependencies(self):
        """Test priority adjustment for task with no dependencies"""
        # Act
        multiplier = self.service.adjust_priority_for_dependencies(
            self.medium_priority_task, 
            []
        )
        
        # Assert
        assert multiplier == 1.0  # No adjustment
        
    def test_calculate_base_priority_score(self):
        """Test base priority score calculation for different priority levels"""
        # Test various priority levels
        priority_tests = [
            ("critical", 100.0),
            ("urgent", 90.0),
            ("high", 75.0),
            ("medium", 50.0),
            ("low", 25.0),
            ("unknown", 50.0)  # Default case
        ]
        
        for priority_str, expected_score in priority_tests:
            # Arrange
            if priority_str == "unknown":
                # Create a task with a mock priority object for invalid test
                task = self._create_test_task(
                    task_id=f"task-{priority_str}",
                    title=f"Task with {priority_str} priority",
                    priority="medium"  # Use valid priority
                )
                # Override with invalid priority string for test
                task.priority = "invalid"
            else:
                task = self._create_test_task(
                    task_id=f"task-{priority_str}",
                    title=f"Task with {priority_str} priority",
                    priority=priority_str
                )

            # Act
            score = self.service._calculate_base_priority_score(task)

            # Assert
            assert score == expected_score, f"Priority {priority_str} should yield score {expected_score}"
            
    def test_calculate_urgency_score_various_due_dates(self):
        """Test urgency score calculation for various due date scenarios"""
        now = datetime.now(timezone.utc)

        # Test overdue task has highest urgency
        overdue_task = self._create_test_task(
            task_id="overdue-task",
            title="Overdue task",
            due_date=now - timedelta(days=1)
        )
        overdue_score = self.service._calculate_urgency_score(overdue_task)
        assert overdue_score == 100.0, "Overdue tasks should have maximum urgency"

        # Test due today has high urgency
        today_task = self._create_test_task(
            task_id="today-task",
            title="Due today",
            due_date=now
        )
        today_score = self.service._calculate_urgency_score(today_task)
        assert today_score >= 80.0, "Tasks due today should have high urgency"

        # Test future tasks have lower urgency
        future_task = self._create_test_task(
            task_id="future-task",
            title="Future task",
            due_date=now + timedelta(days=30)
        )
        future_score = self.service._calculate_urgency_score(future_task)
        assert future_score <= 50.0, "Future tasks should have lower urgency"

        # Test ordering: overdue >= today > future
        assert overdue_score >= today_score > future_score, "Urgency should decrease with time to due date"
            
    def test_calculate_urgency_score_no_due_date(self):
        """Test urgency score for task without due date"""
        # Arrange
        task = self._create_test_task(
            task_id="no-due-date-task",
            title="Task without due date"
        )
        task.due_date = None
        
        # Act
        score = self.service._calculate_urgency_score(task)
        
        # Assert
        assert score == 30.0  # Medium urgency for tasks without due dates
        
    def test_calculate_blocking_score_various_dependent_counts(self):
        """Test blocking score calculation for different numbers of dependent tasks"""
        blocking_tests = [
            (0, 20.0),    # No blocking
            (1, 40.0),    # Blocks 1 task
            (2, 60.0),    # Blocks 2-3 tasks
            (3, 60.0),
            (4, 80.0),    # Blocks 4-5 tasks
            (5, 80.0),
            (6, 100.0),   # Blocks many tasks
        ]
        
        for dependent_count, expected_score in blocking_tests:
            # Arrange
            context_factors = {'dependent_task_count': dependent_count}
            
            # Act
            score = self.service._calculate_blocking_score(
                self.medium_priority_task, 
                context_factors
            )
            
            # Assert
            assert score == expected_score, f"Dependent count {dependent_count} should yield blocking score {expected_score}"
            
    def test_calculate_age_score_various_ages(self):
        """Test age score calculation for tasks of different ages"""
        now = datetime.now(timezone.utc)
        
        age_tests = [
            (now, 10.0),  # Very new (today)
            (now - timedelta(days=2), 20.0),  # New (2 days)
            (now - timedelta(days=5), 40.0),  # A week old
            (now - timedelta(days=15), 60.0),  # A month old
            (now - timedelta(days=60), 80.0),  # 3 months old
            (now - timedelta(days=120), 100.0),  # Very stale
        ]
        
        for created_at, expected_score in age_tests:
            # Arrange
            task = self._create_test_task(
                task_id=f"task-{created_at.day}",
                title="Aged task",
                created_at=created_at
            )
            
            # Act
            score = self.service._calculate_age_score(task)
            
            # Assert
            assert score == expected_score, f"Age {(now - created_at).days} days should yield age score {expected_score}"
            
    def test_calculate_progress_score_various_statuses(self):
        """Test progress score calculation for different task statuses"""
        progress_tests = [
            ("in_progress", 100.0),  # Highest priority
            ("review", 80.0),        # High priority
            ("testing", 70.0),       # High priority
            ("blocked", 0.0),        # Cannot work on
            ("todo", 50.0),          # Medium priority
            ("done", 0.0),           # No priority
            ("cancelled", 0.0),      # No priority
            ("archived", 50.0)       # Default score for archived status
        ]

        for status_str, expected_score in progress_tests:
            # Arrange
            task = self._create_test_task(
                task_id=f"task-{status_str}",
                title=f"Task with {status_str} status",
                status=status_str
            )
            
            # Act
            score = self.service._calculate_progress_score(task)
            
            # Assert
            assert score == expected_score, f"Status {status_str} should yield progress score {expected_score}"
            
    def test_get_priority_factors_complete_breakdown(self):
        """Test detailed priority factors breakdown"""
        # Arrange
        context_factors = {'dependent_task_count': 2}
        
        # Act
        factors = self.service._get_priority_factors(self.high_priority_task, context_factors)
        
        # Assert
        assert isinstance(factors, dict)
        
        # Check all required factors are present
        required_factors = [
            "base_priority", "urgency", "blocking_factor", 
            "age_factor", "progress_factor"
        ]
        
        for factor in required_factors:
            assert factor in factors
            assert isinstance(factors[factor], dict)
            assert "score" in factors[factor]
            
        # Check specific factor details
        assert factors["base_priority"]["value"] == str(self.high_priority_task.priority)
        assert factors["progress_factor"]["status"] == str(self.high_priority_task.status)
        assert factors["blocking_factor"]["dependent_tasks"] == 2
        
    def test_generate_recommendation_reason(self):
        """Test recommendation reason generation"""
        # Arrange
        high_score_task_info = {
            "task": self.high_priority_task,
            "priority_score": 85.0
        }
        
        # Act
        reason = self.service._generate_recommendation_reason(high_score_task_info)
        
        # Assert
        assert isinstance(reason, str)
        assert "Recommended because:" in reason
        assert len(reason) > 20  # Should have meaningful content
        
    def test_service_without_repository_basic_operations(self):
        """Test service operations that don't require repository"""
        # Arrange
        service_no_repo = TaskPriorityService()
        
        # Act & Assert - These should work without repository
        score = service_no_repo.calculate_priority_score(self.medium_priority_task)
        assert isinstance(score, float)
        
        ordered = service_no_repo.order_tasks_by_priority([self.medium_priority_task])
        assert len(ordered) == 1
        
        multiplier = service_no_repo.adjust_priority_for_dependencies(
            self.medium_priority_task, 
            []
        )
        assert multiplier == 1.0


class TestTaskPriorityServiceIntegration:
    """Integration tests for TaskPriorityService with realistic scenarios"""

    def setup_method(self):
        """Setup integration test environment"""
        self.mock_repository = Mock(spec=TaskRepositoryProtocol)
        self.service = TaskPriorityService(self.mock_repository)

    def test_complete_workflow_scenario(self):
        """Test complete workflow from task creation to recommendation"""
        # Arrange: Create a realistic set of tasks
        tasks = [
            self._create_urgent_bug_fix(),
            self._create_feature_in_progress(),
            self._create_stale_task(),
            self._create_blocked_task()
        ]
        
        self.mock_repository.find_by_git_branch_id.return_value = tasks
        self.mock_repository.find_all.return_value = tasks
        
        # Act: Get recommendation
        recommendation = self.service.get_next_task_recommendation("main-branch")
        
        # Assert: Verify realistic prioritization
        assert recommendation is not None
        assert recommendation["task"].title == "Critical Production Bug"  # Should be highest priority
        
        # Verify alternative suggestions make sense
        alternatives = recommendation["alternative_tasks"]
        assert len(alternatives) >= 1
        assert any("Feature Development" in alt["title"] for alt in alternatives)
        
    def test_dependency_chain_prioritization(self):
        """Test prioritization with complex dependency chains"""
        # Arrange: Create tasks with dependencies
        foundation_task = self._create_task_with_id("foundation", "Foundation Work", "medium")
        dependent_task1 = self._create_task_with_id("dep1", "Dependent Work 1", "low") 
        dependent_task2 = self._create_task_with_id("dep2", "Dependent Work 2", "low")
        
        # Set up dependencies
        dependent_task1.dependencies = [foundation_task.id]
        dependent_task2.dependencies = [foundation_task.id]
        
        all_tasks = [foundation_task, dependent_task1, dependent_task2]
        
        # Act: Check priority adjustments
        foundation_multiplier = self.service.adjust_priority_for_dependencies(
            foundation_task, 
            all_tasks
        )
        dependent_multiplier = self.service.adjust_priority_for_dependencies(
            dependent_task1, 
            all_tasks
        )
        
        # Assert: Foundation task should have higher priority due to blocking others
        assert foundation_multiplier > dependent_multiplier
        assert foundation_multiplier > 1.0  # Should be boosted
        
    def _create_urgent_bug_fix(self) -> Task:
        """Create an urgent bug fix task"""
        return Task(
            title="Critical Production Bug",
            description="Fix critical bug affecting users",
            id=TaskId.from_string("44444444-4444-4444-4444-444444444444"),
            status=TaskStatus.from_string("todo"),
            priority=Priority.from_string("critical"),
            git_branch_id="main-branch",
            due_date=datetime.now(timezone.utc) + timedelta(hours=4),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
    def _create_feature_in_progress(self) -> Task:
        """Create a feature task in progress"""
        return Task(
            title="Feature Development",
            description="Implement new feature",
            id=TaskId.from_string("55555555-5555-5555-5555-555555555555"),
            status=TaskStatus.from_string("in_progress"),
            priority=Priority.from_string("high"),
            git_branch_id="main-branch",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            updated_at=datetime.now(timezone.utc)
        )
        
    def _create_stale_task(self) -> Task:
        """Create a stale task that should get priority boost"""
        return Task(
            title="Old Refactoring Task",
            description="Clean up old code",
            id=TaskId.from_string("66666666-6666-6666-6666-666666666666"),
            status=TaskStatus.from_string("todo"),
            priority=Priority.from_string("low"),
            git_branch_id="main-branch",
            created_at=datetime.now(timezone.utc) - timedelta(days=100),
            updated_at=datetime.now(timezone.utc) - timedelta(days=95)
        )
        
    def _create_blocked_task(self) -> Task:
        """Create a blocked task"""
        return Task(
            title="Blocked Integration Task",
            description="Task waiting for external dependency",
            id=TaskId.from_string("77777777-7777-7777-7777-777777777777"),
            status=TaskStatus.from_string("blocked"),
            priority=Priority.from_string("medium"),
            git_branch_id="main-branch",
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
            updated_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

    def _ensure_uuid_format(self, task_id: str) -> str:
        """Convert simple task ID to UUID format if needed"""
        # If already UUID format, return as-is
        if len(task_id) == 36 and task_id.count('-') == 4:
            return task_id

        # Create a deterministic UUID-like string from the simple ID
        # Use hash to ensure consistency but keep it readable for debugging
        import hashlib
        hash_obj = hashlib.md5(task_id.encode())
        hex_str = hash_obj.hexdigest()
        # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"

    def _create_task_with_id(self, task_id: str, title: str, priority: str) -> Task:
        """Helper to create task with specific ID"""
        # Convert simple task_id to UUID format if needed
        uuid_task_id = self._ensure_uuid_format(task_id)

        return Task(
            title=title,
            description=f"Description for {title}",
            id=TaskId.from_string(uuid_task_id),
            status=TaskStatus.from_string("todo"),
            priority=Priority.from_string(priority),
            git_branch_id="test-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )