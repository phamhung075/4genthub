"""
Test suite for NextTask use case

Tests the business logic for finding the next task to work on.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.next_task import NextTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskTitle,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    GitBranchName,
    ProjectID,
    UserID
)
from fastmcp.task_management.domain.exceptions import (
    GitBranchNotFoundError,
    NoTasksAvailableError
)


class TestNextTaskUseCase:
    """Test suite for NextTask use case"""

    @pytest.fixture
    def mock_git_branch_repo(self):
        """Create mock git branch repository"""
        return Mock()

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock()

    @pytest.fixture
    def mock_dependency_service(self):
        """Create mock dependency service"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_git_branch_repo, mock_task_repo, mock_subtask_repo, mock_dependency_service):
        """Create use case instance with mocks"""
        return NextTaskUseCase(
            git_branch_repository=mock_git_branch_repo,
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo,
            dependency_service=mock_dependency_service
        )

    @pytest.fixture
    def sample_git_branch(self):
        """Create sample git branch"""
        branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=ProjectID(str(uuid4())),
            git_branch_name=GitBranchName("feature/user-auth"),
            user_id=UserID("user123")
        )
        return branch

    @pytest.fixture
    def sample_tasks(self, sample_git_branch):
        """Create sample tasks with different priorities and statuses"""
        tasks = []
        
        # Task 1 - High priority, in progress
        t1 = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_git_branch.id,
            title=TaskTitle("Complete authentication"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            labels=["auth"],
            progress_percentage=60
        )
        tasks.append(t1)
        
        # Task 2 - Urgent priority, todo
        t2 = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_git_branch.id,
            title=TaskTitle("Fix security vulnerability"),
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignees=[UserID("user123")],
            labels=["security"]
        )
        tasks.append(t2)
        
        # Task 3 - Medium priority, blocked
        t3 = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_git_branch.id,
            title=TaskTitle("Add OAuth integration"),
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")],
            labels=["auth"],
            blocked_reason="Waiting for API keys"
        )
        tasks.append(t3)
        
        # Task 4 - Critical priority, todo with dependencies
        t4 = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=sample_git_branch.id,
            title=TaskTitle("Deploy to production"),
            status=TaskStatus.TODO,
            priority=TaskPriority.CRITICAL,
            assignees=[UserID("user123")],
            labels=["deployment"],
            dependencies=[t1.id, t2.id]  # Depends on tasks 1 and 2
        )
        tasks.append(t4)
        
        return tasks

    def test_next_task_highest_priority_available(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch, sample_tasks):
        """Test getting next task returns highest priority available task"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = sample_tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False  # No blocking deps
        
        # Act
        result = use_case.execute(git_branch_id=git_branch_id)
        
        # Assert
        assert result is not None
        assert result.id == sample_tasks[1].id  # Task 2 - Urgent priority TODO
        assert result.priority == TaskPriority.URGENT
        assert result.status == TaskStatus.TODO

    def test_next_task_skip_blocked_tasks(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch, sample_tasks):
        """Test next task skips blocked tasks"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Remove urgent task to test blocked task handling
        available_tasks = [sample_tasks[0], sample_tasks[2], sample_tasks[3]]  # No urgent task
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = available_tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(git_branch_id=git_branch_id)
        
        # Assert - Should return in-progress task, not blocked one
        assert result.id == sample_tasks[0].id  # High priority in-progress
        assert result.status == TaskStatus.IN_PROGRESS

    def test_next_task_respects_dependencies(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch, sample_tasks):
        """Test next task respects task dependencies"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = sample_tasks
        
        # Task 4 has unmet dependencies
        def check_dependencies(task_id):
            return task_id == sample_tasks[3].id
        
        mock_dependency_service.has_unmet_dependencies.side_effect = check_dependencies
        
        # Act
        result = use_case.execute(git_branch_id=git_branch_id)
        
        # Assert - Should skip task 4 (critical but has deps)
        assert result.id != sample_tasks[3].id
        assert result.id == sample_tasks[1].id  # Urgent task without deps

    def test_next_task_no_tasks_available(self, use_case, mock_git_branch_repo, mock_task_repo, sample_git_branch):
        """Test when no tasks are available"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = []  # No tasks
        
        # Act & Assert
        with pytest.raises(NoTasksAvailableError):
            use_case.execute(git_branch_id=git_branch_id)

    def test_next_task_all_tasks_completed(self, use_case, mock_git_branch_repo, mock_task_repo, sample_git_branch):
        """Test when all tasks are completed"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Create completed tasks
        completed_tasks = [
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle(f"Completed task {i}"),
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                labels=[],
                progress_percentage=100
            )
            for i in range(3)
        ]
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = completed_tasks
        
        # Act & Assert
        with pytest.raises(NoTasksAvailableError, match="All tasks completed"):
            use_case.execute(git_branch_id=git_branch_id)

    def test_next_task_git_branch_not_found(self, use_case, mock_git_branch_repo):
        """Test when git branch doesn't exist"""
        # Arrange
        git_branch_id = str(uuid4())
        
        mock_git_branch_repo.get_by_id.side_effect = GitBranchNotFoundError(f"Branch {git_branch_id} not found")
        
        # Act & Assert
        with pytest.raises(GitBranchNotFoundError):
            use_case.execute(git_branch_id=git_branch_id)

    def test_next_task_with_subtasks(self, use_case, mock_git_branch_repo, mock_task_repo, mock_subtask_repo, mock_dependency_service, sample_git_branch, sample_tasks):
        """Test getting next task includes subtask check"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Create subtasks for task 1
        subtasks = [
            Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_tasks[0].id,
                title="Implement login",
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")]
            ),
            Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_tasks[0].id,
                title="Implement logout",
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")]
            )
        ]
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = sample_tasks
        mock_subtask_repo.get_incomplete_by_task_ids.return_value = subtasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(
            git_branch_id=git_branch_id,
            include_subtasks=True
        )
        
        # Assert - Should suggest subtask from in-progress task
        assert hasattr(result, 'suggested_subtask')
        assert result.suggested_subtask.id == subtasks[0].id
        assert result.suggested_subtask.title == "Implement login"

    def test_next_task_priority_order(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch):
        """Test tasks are returned in correct priority order"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Create tasks with all priority levels
        priority_tasks = []
        for priority in [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, 
                        TaskPriority.URGENT, TaskPriority.CRITICAL]:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle(f"{priority.value} priority task"),
                status=TaskStatus.TODO,
                priority=priority,
                assignees=[UserID("user123")],
                labels=[]
            )
            priority_tasks.append(task)
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = priority_tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(git_branch_id=git_branch_id)
        
        # Assert - Should return critical priority first
        assert result.priority == TaskPriority.CRITICAL

    def test_next_task_in_progress_preferred(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch):
        """Test in-progress tasks are preferred over todo tasks of same priority"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Create two high priority tasks - one todo, one in progress
        tasks = [
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle("Todo high priority"),
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")],
                labels=[]
            ),
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle("In progress high priority"),
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user123")],
                labels=[],
                progress_percentage=30
            )
        ]
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(git_branch_id=git_branch_id)
        
        # Assert - Should return in-progress task
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.title.value == "In progress high priority"

    def test_next_task_filter_by_assignee(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch):
        """Test filtering next task by assignee"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        # Create tasks with different assignees
        tasks = [
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle("Task for user456"),
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assignees=[UserID("user456")],
                labels=[]
            ),
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=sample_git_branch.id,
                title=TaskTitle("Task for user123"),
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                labels=[]
            )
        ]
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(
            git_branch_id=git_branch_id,
            assignee_filter="user123"
        )
        
        # Assert - Should return task for user123 even though lower priority
        assert result.title.value == "Task for user123"
        assert UserID("user123") in result.assignees

    def test_next_task_with_context(self, use_case, mock_git_branch_repo, mock_task_repo, mock_dependency_service, sample_git_branch, sample_tasks):
        """Test getting next task with context information"""
        # Arrange
        git_branch_id = sample_git_branch.id.value
        
        mock_git_branch_repo.get_by_id.return_value = sample_git_branch
        mock_task_repo.get_by_branch_id.return_value = sample_tasks
        mock_dependency_service.has_unmet_dependencies.return_value = False
        
        # Act
        result = use_case.execute(
            git_branch_id=git_branch_id,
            include_context=True
        )
        
        # Assert
        assert hasattr(result, 'context')
        assert result.context.get('branch_name') == "feature/user-auth"
        assert result.context.get('total_tasks') == len(sample_tasks)
        assert result.context.get('recommendation') is not None