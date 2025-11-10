"""Tests for TaskPriorityService domain service"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.services.task_priority_service import (
    TaskPriorityService,
    TaskRepositoryProtocol,
)
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


class TestTaskPriorityService:
    """Test suite for TaskPriorityService"""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepositoryProtocol)

    @pytest.fixture
    def service(self, mock_repository):
        """Create TaskPriorityService instance"""
        return TaskPriorityService(task_repository=mock_repository)

    @pytest.fixture
    def basic_task(self):
        """Create a basic task for testing"""
        task = Mock(spec=Task)
        task.id = TaskId("test-task-123")
        task.title = "Test Task"
        task.priority = Priority.medium()
        task.status = TaskStatus.TODO
        task.created_at = datetime.now(UTC) - timedelta(days=5)
        task.due_date = None
        task.dependencies = []
        return task

    def test_calculate_priority_score_basic(self, service, basic_task):
        """Test basic priority score calculation"""
        score = service.calculate_priority_score(basic_task)
        
        # Medium priority base (50) * 0.30 = 15
        # No due date urgency (30) * 0.25 = 7.5
        # No blocking (20) * 0.20 = 4
        # 5-day age (40) * 0.15 = 6
        # Todo status (50) * 0.10 = 5
        # Total: ~37.5
        assert 35 <= score <= 40
    
    def test_calculate_priority_score_critical_priority(self, service, basic_task):
        """Test critical priority results in highest base score"""
        basic_task.priority = Priority.critical()
        score = service.calculate_priority_score(basic_task)
        
        # Critical priority base (100) * 0.30 = 30
        # Higher base score should result in overall higher score
        assert score > 45
    
    def test_calculate_priority_score_overdue_task(self, service, basic_task):
        """Test overdue task gets maximum urgency score"""
        basic_task.due_date = datetime.now(UTC) - timedelta(days=1)
        score = service.calculate_priority_score(basic_task)
        
        # Maximum urgency score (100) * 0.25 = 25
        # Should significantly increase overall score
        assert score > 50
    
    def test_calculate_priority_score_with_blocking_factor(self, service, basic_task):
        """Test task that blocks many others gets higher score"""
        context_factors = {"dependent_task_count": 6}
        score = service.calculate_priority_score(basic_task, context_factors)
        
        # High blocking factor (100) * 0.20 = 20
        # Should increase score significantly
        assert score > 45
    
    def test_calculate_priority_score_old_task(self, service, basic_task):
        """Test very old task gets higher age score"""
        basic_task.created_at = datetime.now(UTC) - timedelta(days=100)
        score = service.calculate_priority_score(basic_task)
        
        # Very stale age score (100) * 0.15 = 15
        # Should increase overall score
        assert score > 40
    
    def test_calculate_priority_score_in_progress(self, service, basic_task):
        """Test in-progress task gets highest progress score"""
        basic_task.status = TaskStatus.IN_PROGRESS
        score = service.calculate_priority_score(basic_task)
        
        # In progress status (100) * 0.10 = 10
        # Should increase score
        assert score > 40
    
    def test_calculate_priority_score_blocked(self, service, basic_task):
        """Test blocked task gets zero progress score"""
        basic_task.status = TaskStatus.BLOCKED
        score = service.calculate_priority_score(basic_task)
        
        # Blocked status (0) * 0.10 = 0
        # Should decrease score compared to TODO
        assert score < 35
    
    def test_calculate_priority_score_error_handling(self, service, basic_task):
        """Test error handling in priority score calculation"""
        # Create a task that will cause an error by having str() throw
        basic_task.priority = Mock()
        basic_task.priority.__str__ = Mock(side_effect=Exception("Priority error"))
        
        score = service.calculate_priority_score(basic_task)
        
        # Should return 0.0 on error
        assert score == 0.0
    
    def test_order_tasks_by_priority(self, service):
        """Test ordering tasks by priority score"""
        # Create tasks with different priorities
        high_priority_task = Mock(spec=Task)
        high_priority_task.id = TaskId("high-123")
        high_priority_task.title = "High Priority Task"
        high_priority_task.priority = Priority.high()
        high_priority_task.status = TaskStatus.TODO
        high_priority_task.created_at = datetime.now(UTC)
        
        low_priority_task = Mock(spec=Task)
        low_priority_task.id = TaskId("low-123")
        low_priority_task.title = "Low Priority Task"
        low_priority_task.priority = Priority.low()
        low_priority_task.status = TaskStatus.TODO
        low_priority_task.created_at = datetime.now(UTC)
        
        in_progress_task = Mock(spec=Task)
        in_progress_task.id = TaskId("progress-123")
        in_progress_task.title = "In Progress Task"
        in_progress_task.priority = Priority.medium()
        in_progress_task.status = TaskStatus.IN_PROGRESS
        in_progress_task.created_at = datetime.now(UTC)
        
        tasks = [low_priority_task, high_priority_task, in_progress_task]
        ordered = service.order_tasks_by_priority(tasks)
        
        assert len(ordered) == 3
        # Check that higher priority scores come first
        assert ordered[0]["priority_score"] >= ordered[1]["priority_score"]
        assert ordered[1]["priority_score"] >= ordered[2]["priority_score"]
        
        # Verify task details are included
        assert "task" in ordered[0]
        assert "task_id" in ordered[0]
        assert "title" in ordered[0]
        assert "priority_factors" in ordered[0]
    
    def test_order_tasks_by_priority_error_handling(self, service):
        """Test error handling in task ordering"""
        # Create a task that will cause error
        bad_task = Mock()
        bad_task.id = Mock()
        bad_task.id.__str__ = Mock(side_effect=Exception("ID conversion error"))
        bad_task.title = "Bad Task"
        bad_task.priority = Priority.medium()
        bad_task.status = TaskStatus.TODO
        bad_task.created_at = datetime.now(UTC)
        
        result = service.order_tasks_by_priority([bad_task])
        
        assert len(result) == 1
        assert result[0]["priority_score"] == 0.0
        assert "error" in result[0]
    
    def test_get_next_task_recommendation_no_repository(self, service):
        """Test recommendation without repository returns None"""
        service._task_repository = None
        result = service.get_next_task_recommendation("branch-123")
        assert result is None
    
    def test_get_next_task_recommendation_no_tasks(self, service, mock_repository):
        """Test recommendation with no tasks returns None"""
        mock_repository.find_by_git_branch_id.return_value = []
        result = service.get_next_task_recommendation("branch-123")
        assert result is None
    
    def test_get_next_task_recommendation_all_done(self, service, mock_repository, basic_task):
        """Test recommendation with all tasks done returns None"""
        basic_task.status = TaskStatus.DONE
        mock_repository.find_by_git_branch_id.return_value = [basic_task]
        
        result = service.get_next_task_recommendation("branch-123")
        assert result is None
    
    def test_get_next_task_recommendation_success(self, service, mock_repository):
        """Test successful task recommendation"""
        # Create multiple tasks
        task1 = Mock(spec=Task)
        task1.id = TaskId("task-1")
        task1.title = "Task 1"
        task1.priority = Priority.low()
        task1.status = TaskStatus.TODO
        task1.created_at = datetime.now(UTC)
        task1.due_date = None
        task1.dependencies = []
        
        task2 = Mock(spec=Task)
        task2.id = TaskId("task-2") 
        task2.title = "Task 2"
        task2.priority = Priority.high()
        task2.status = TaskStatus.TODO
        task2.created_at = datetime.now(UTC)
        task2.due_date = None
        task2.dependencies = []
        
        task3 = Mock(spec=Task)
        task3.id = TaskId("task-3")
        task3.title = "Task 3"
        task3.priority = Priority.medium()
        task3.status = TaskStatus.IN_PROGRESS
        task3.created_at = datetime.now(UTC)
        task3.due_date = None
        task3.dependencies = []
        
        mock_repository.find_by_git_branch_id.return_value = [task1, task2, task3]
        
        result = service.get_next_task_recommendation("branch-123")
        
        assert result is not None
        assert "task" in result
        assert "task_id" in result
        assert "title" in result
        assert "priority_score" in result
        assert "recommendation_reason" in result
        assert "alternative_tasks" in result
        assert "total_eligible_tasks" in result
        assert result["total_eligible_tasks"] == 3
    
    def test_get_next_task_recommendation_exclude_statuses(self, service, mock_repository):
        """Test task recommendation with custom excluded statuses"""
        task1 = Mock(spec=Task)
        task1.id = TaskId("task-1")
        task1.title = "Review Task"
        task1.priority = Priority.high()
        task1.status = TaskStatus.REVIEW
        task1.created_at = datetime.now(UTC)
        task1.due_date = None
        task1.dependencies = []
        
        task2 = Mock(spec=Task)
        task2.id = TaskId("task-2")
        task2.title = "Todo Task"
        task2.priority = Priority.medium()
        task2.status = TaskStatus.TODO
        task2.created_at = datetime.now(UTC)
        task2.due_date = None
        task2.dependencies = []
        
        mock_repository.find_by_git_branch_id.return_value = [task1, task2]
        
        result = service.get_next_task_recommendation("branch-123", exclude_statuses=['review', 'done'])
        
        assert result is not None
        assert result["task_id"] == "task-2"  # Todo task should be recommended
    
    def test_get_next_task_recommendation_error_handling(self, service, mock_repository):
        """Test error handling in recommendation"""
        mock_repository.find_by_git_branch_id.side_effect = Exception("Database error")
        
        result = service.get_next_task_recommendation("branch-123")
        assert result is None
    
    def test_adjust_priority_for_dependencies_no_deps(self, service, basic_task):
        """Test priority adjustment with no dependencies"""
        multiplier = service.adjust_priority_for_dependencies(basic_task)
        assert multiplier == 1.0  # No adjustment
    
    def test_adjust_priority_for_dependencies_incomplete_deps(self, service, basic_task):
        """Test priority adjustment with incomplete dependencies"""
        basic_task.dependencies = ["dep-1", "dep-2"]
        
        # Create dependent tasks that are not done
        dep_task1 = Mock(spec=Task)
        dep_task1.id = TaskId("dep-1")
        dep_task1.status = TaskStatus.IN_PROGRESS
        
        dep_task2 = Mock(spec=Task)
        dep_task2.id = TaskId("dep-2")
        dep_task2.status = TaskStatus.TODO
        
        all_tasks = [basic_task, dep_task1, dep_task2]
        
        multiplier = service.adjust_priority_for_dependencies(basic_task, all_tasks)
        assert multiplier < 1.0  # Should be reduced
        assert multiplier >= 0.5  # But not below minimum
    
    def test_adjust_priority_for_dependencies_task_is_blocker(self, service, basic_task):
        """Test priority adjustment when task blocks others"""
        # Create tasks that depend on basic_task
        dependent1 = Mock(spec=Task)
        dependent1.id = TaskId("dependent-1")
        dependent1.dependencies = [str(basic_task.id)]
        
        dependent2 = Mock(spec=Task)
        dependent2.id = TaskId("dependent-2")
        dependent2.dependencies = [str(basic_task.id)]
        
        all_tasks = [basic_task, dependent1, dependent2]
        
        multiplier = service.adjust_priority_for_dependencies(basic_task, all_tasks)
        assert multiplier > 1.0  # Should be increased
        assert multiplier <= 2.0  # But not above maximum
    
    def test_adjust_priority_for_dependencies_error_handling(self, service, basic_task):
        """Test error handling in dependency adjustment"""
        basic_task.dependencies = None
        basic_task.id = None  # Will cause error
        
        multiplier = service.adjust_priority_for_dependencies(basic_task)
        assert multiplier == 1.0  # Should return default on error
    
    @patch('fastmcp.task_management.domain.services.task_priority_service.datetime')
    def test_calculate_urgency_score_due_dates(self, mock_datetime, service, basic_task):
        """Test urgency scores for various due dates"""
        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        # Mock datetime.now to return our controlled 'now' time
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Due today (set to end of today to ensure it's treated as "today")
        basic_task.due_date = now.replace(hour=23, minute=59)
        score = service._calculate_urgency_score(basic_task)
        assert score == 90.0  # Due today
        
        # Due tomorrow (add exactly 1 day)
        basic_task.due_date = now + timedelta(days=1)
        score = service._calculate_urgency_score(basic_task)
        assert score == 80.0  # Due tomorrow
        
        # Due in 1 day and 6 hours (should still be "tomorrow" since .days = 1)
        basic_task.due_date = now + timedelta(days=1, hours=6)
        score = service._calculate_urgency_score(basic_task)
        assert score == 80.0  # Still counts as due tomorrow
        
        # Due in exactly 3 days
        basic_task.due_date = now + timedelta(days=3)
        score = service._calculate_urgency_score(basic_task)
        assert score == 70.0  # Due within 3 days
        
        # Due in exactly 7 days
        basic_task.due_date = now + timedelta(days=7)
        score = service._calculate_urgency_score(basic_task)
        assert score == 50.0  # Due within a week
        
        # Due in 30 days
        basic_task.due_date = now + timedelta(days=30)
        score = service._calculate_urgency_score(basic_task)
        assert score == 30.0  # Due within a month
        
        # Due in 60 days
        basic_task.due_date = now + timedelta(days=60)
        score = service._calculate_urgency_score(basic_task)
        assert score == 10.0  # Due later
    
    def test_calculate_urgency_score_naive_datetime(self, service, basic_task):
        """Test urgency score with naive datetime"""
        # Create naive datetime (no timezone)
        basic_task.due_date = datetime.now().replace(tzinfo=None)
        score = service._calculate_urgency_score(basic_task)
        
        # Should handle gracefully and return a score
        assert 80 <= score <= 100  # Should be high urgency since it's "today"
    
    def test_get_priority_factors(self, service, basic_task):
        """Test getting detailed priority factors"""
        # Set due date to exactly 2 days from now
        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        basic_task.due_date = now + timedelta(days=2)
        context_factors = {"dependent_task_count": 3}
        
        factors = service._get_priority_factors(basic_task, context_factors)
        
        assert "base_priority" in factors
        assert factors["base_priority"]["value"] == "medium"
        assert factors["base_priority"]["score"] == 50.0
        
        assert "urgency" in factors
        assert factors["urgency"]["due_date"] is not None
        # Due date calculation may result in 1 or 2 days depending on exact timing
        # Accept either 70.0 (2 days) or 80.0 (1 day) due to timing edge cases
        assert factors["urgency"]["score"] in [70.0, 80.0]
        
        assert "blocking_factor" in factors
        assert factors["blocking_factor"]["dependent_tasks"] == 3
        assert factors["blocking_factor"]["score"] == 60.0
        
        assert "age_factor" in factors
        assert "progress_factor" in factors
    
    def test_generate_recommendation_reason(self, service, basic_task):
        """Test generating human-readable recommendation reasons"""
        # Test high priority score
        recommended = {
            "task": basic_task,
            "priority_score": 85.0
        }
        reason = service._generate_recommendation_reason(recommended)
        assert "high priority score" in reason
        
        # Test overdue task
        basic_task.due_date = datetime.now(UTC) - timedelta(days=1)
        reason = service._generate_recommendation_reason(recommended)
        assert "overdue" in reason
        
        # Test due soon
        basic_task.due_date = datetime.now(UTC) + timedelta(hours=12)
        reason = service._generate_recommendation_reason(recommended)
        assert "due soon" in reason
        
        # Test in progress
        basic_task.status = TaskStatus.IN_PROGRESS
        basic_task.due_date = None
        reason = service._generate_recommendation_reason(recommended)
        assert "already in progress" in reason
        
        # Test high priority
        basic_task.status = TaskStatus.TODO
        basic_task.priority = Priority.urgent()
        recommended["priority_score"] = 50.0  # Lower score
        reason = service._generate_recommendation_reason(recommended)
        assert "urgent priority" in reason
        
        # Test default
        basic_task.priority = Priority.low()
        reason = service._generate_recommendation_reason(recommended)
        assert "best available option" in reason
    
    def test_count_incomplete_dependencies(self, service, basic_task):
        """Test counting incomplete dependencies"""
        # No dependencies
        count = service._count_incomplete_dependencies(basic_task, [])
        assert count == 0
        
        # Has dependencies
        basic_task.dependencies = ["dep-1", "dep-2", "dep-3"]
        
        # Create dependency tasks
        dep1 = Mock(spec=Task)
        dep1.id = TaskId("dep-1")
        dep1.status = TaskStatus.DONE
        
        dep2 = Mock(spec=Task)
        dep2.id = TaskId("dep-2")
        dep2.status = TaskStatus.IN_PROGRESS
        
        dep3 = Mock(spec=Task)
        dep3.id = TaskId("dep-3")
        dep3.status = TaskStatus.TODO
        
        all_tasks = [dep1, dep2, dep3]
        
        count = service._count_incomplete_dependencies(basic_task, all_tasks)
        assert count == 2  # dep-2 and dep-3 are incomplete
    
    def test_count_tasks_depending_on(self, service, basic_task):
        """Test counting tasks that depend on a given task"""
        task_id_str = str(basic_task.id)
        
        # Create tasks that depend on basic_task
        dependent1 = Mock(spec=Task)
        dependent1.id = TaskId("dependent-1")
        dependent1.dependencies = [task_id_str]
        
        dependent2 = Mock(spec=Task)
        dependent2.id = TaskId("dependent-2")
        dependent2.dependencies = ["other-dep", task_id_str]
        
        independent = Mock(spec=Task)
        independent.id = TaskId("independent")
        independent.dependencies = ["other-dep"]
        
        no_deps = Mock(spec=Task)
        no_deps.id = TaskId("no-deps")
        no_deps.dependencies = []
        
        all_tasks = [basic_task, dependent1, dependent2, independent, no_deps]
        
        count = service._count_tasks_depending_on(basic_task, all_tasks)
        assert count == 2  # dependent1 and dependent2
    
    def test_score_clamping(self, service, basic_task):
        """Test that priority scores are clamped to [0, 100]"""
        # Create extreme case that would exceed 100
        basic_task.priority = Priority.critical()  # 100 base
        basic_task.due_date = datetime.now(UTC) - timedelta(days=7)  # Overdue
        basic_task.status = TaskStatus.IN_PROGRESS
        basic_task.created_at = datetime.now(UTC) - timedelta(days=365)
        
        context_factors = {"dependent_task_count": 10}
        
        score = service.calculate_priority_score(basic_task, context_factors)
        
        # Score should be clamped to 100
        assert score == 100.0
    
    def test_service_without_repository(self):
        """Test service can be created without repository"""
        service = TaskPriorityService()
        assert service._task_repository is None
        
        # Basic calculations should still work
        task = Mock(spec=Task)
        task.id = TaskId("test")
        task.priority = Priority.high()
        task.status = TaskStatus.TODO
        task.created_at = datetime.now(UTC)
        
        score = service.calculate_priority_score(task)
        assert score > 0