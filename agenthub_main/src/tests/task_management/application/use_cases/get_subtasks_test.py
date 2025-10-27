"""
Test suite for GetSubtasks use case

Tests the business logic for retrieving all subtasks for a task.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.get_subtasks import GetSubtasksUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskTitle,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    UserID
)
from fastmcp.task_management.domain.exceptions import (
    TaskNotFoundError,
    UnauthorizedAccessError
)


class TestGetSubtasksUseCase:
    """Test suite for GetSubtasks use case"""

    @pytest.fixture
    def mock_task_repo(self):
        """Create mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_task_repo, mock_subtask_repo):
        """Create use case instance with mocks"""
        return GetSubtasksUseCase(
            task_repository=mock_task_repo,
            subtask_repository=mock_subtask_repo
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample parent task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Parent Task with Subtasks"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["feature", "backend"]
        )
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        return task

    @pytest.fixture
    def sample_subtasks(self, sample_task):
        """Create sample subtasks for the task"""
        subtasks = []
        
        # Subtask 1 - Completed
        sub1 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Design database schema",
            description="Create tables for user authentication",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            progress_percentage=100,
            completion_summary="Schema created and migrated"
        )
        sub1.created_at = datetime.now(timezone.utc)
        sub1.order = 0
        subtasks.append(sub1)
        
        # Subtask 2 - In Progress
        sub2 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Implement API endpoints",
            description="Create REST API for auth operations",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user456")],
            progress_percentage=60,
            progress_notes="Login endpoint complete, working on registration"
        )
        sub2.created_at = datetime.now(timezone.utc)
        sub2.order = 1
        subtasks.append(sub2)
        
        # Subtask 3 - Blocked
        sub3 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Add OAuth integration",
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123"), UserID("user456")],
            blockers="Waiting for OAuth provider credentials"
        )
        sub3.created_at = datetime.now(timezone.utc)
        sub3.order = 2
        subtasks.append(sub3)
        
        # Subtask 4 - Todo
        sub4 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Write documentation",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[UserID("user789")],
            estimated_effort="3 hours"
        )
        sub4.created_at = datetime.now(timezone.utc)
        sub4.order = 3
        subtasks.append(sub4)
        
        return subtasks

    def test_get_all_subtasks_success(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test successfully getting all subtasks for a task"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(task_id=task_id, user_id=user_id)
        
        # Assert
        assert len(result) == 4
        assert result[0].title == "Design database schema"
        assert result[1].title == "Implement API endpoints"
        assert result[2].title == "Add OAuth integration"
        assert result[3].title == "Write documentation"
        
        # Verify correct order
        assert result[0].order == 0
        assert result[1].order == 1
        assert result[2].order == 2
        assert result[3].order == 3
        
        # Verify repository calls
        mock_task_repo.get_by_id.assert_called_once_with(TaskID(task_id))
        mock_subtask_repo.get_by_task_id.assert_called_once_with(TaskID(task_id))

    def test_get_subtasks_empty_list(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test getting subtasks when task has none"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = []
        
        # Act
        result = use_case.execute(task_id=task_id, user_id=user_id)
        
        # Assert
        assert result == []
        assert len(result) == 0

    def test_get_subtasks_task_not_found(self, use_case, mock_task_repo):
        """Test getting subtasks for non-existent task"""
        # Arrange
        task_id = str(uuid4())
        
        mock_task_repo.get_by_id.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError):
            use_case.execute(task_id=task_id, user_id="user123")

    def test_get_subtasks_unauthorized_user(self, use_case, mock_task_repo, sample_task):
        """Test getting subtasks by unauthorized user"""
        # Arrange
        task_id = sample_task.id.value
        unauthorized_user = "user999"  # Not in task assignees
        
        mock_task_repo.get_by_id.return_value = sample_task
        
        # Act & Assert
        with pytest.raises(UnauthorizedAccessError, match="not authorized to access"):
            use_case.execute(task_id=task_id, user_id=unauthorized_user)

    def test_get_subtasks_filtered_by_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test filtering subtasks by status"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            status_filter="in_progress"
        )
        
        # Assert
        assert len(result) == 1
        assert result[0].title == "Implement API endpoints"
        assert result[0].status == TaskStatus.IN_PROGRESS

    def test_get_subtasks_filtered_by_multiple_statuses(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test filtering subtasks by multiple statuses"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            status_filter=["todo", "blocked"]
        )
        
        # Assert
        assert len(result) == 2
        assert result[0].status == TaskStatus.BLOCKED
        assert result[1].status == TaskStatus.TODO

    def test_get_subtasks_filtered_by_assignee(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test filtering subtasks by assignee"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            assignee_filter="user456"
        )
        
        # Assert
        assert len(result) == 2  # user456 is assigned to subtask 2 and 3
        assert any(UserID("user456") in subtask.assignees for subtask in result)

    def test_get_subtasks_with_progress_summary(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test getting subtasks with progress summary"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            include_summary=True
        )
        
        # Assert
        assert hasattr(result, 'subtasks')
        assert hasattr(result, 'summary')
        assert result.summary.total == 4
        assert result.summary.completed == 1  # Only sub1 is done
        assert result.summary.in_progress == 1
        assert result.summary.blocked == 1
        assert result.summary.todo == 1
        assert result.summary.completion_percentage == 25  # 1 of 4 done

    def test_get_subtasks_sorted_by_priority(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test sorting subtasks by priority"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            sort_by="priority"
        )
        
        # Assert
        # HIGH priority tasks should come first
        assert result[0].priority == TaskPriority.HIGH
        assert result[1].priority == TaskPriority.HIGH
        assert result[2].priority == TaskPriority.MEDIUM
        assert result[3].priority == TaskPriority.LOW

    def test_get_subtasks_sorted_by_status(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test sorting subtasks by status"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            sort_by="status"
        )
        
        # Assert - Status order: TODO, IN_PROGRESS, BLOCKED, DONE
        assert result[0].status == TaskStatus.TODO
        assert result[1].status == TaskStatus.IN_PROGRESS
        assert result[2].status == TaskStatus.BLOCKED
        assert result[3].status == TaskStatus.DONE

    def test_get_subtasks_pagination(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test paginating subtasks results"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act - Get first page
        page1 = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            offset=0,
            limit=2
        )
        
        # Act - Get second page
        page2 = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            offset=2,
            limit=2
        )
        
        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].order == 0
        assert page1[1].order == 1
        assert page2[0].order == 2
        assert page2[1].order == 3

    def test_get_subtasks_with_details_expansion(self, use_case, mock_task_repo, mock_subtask_repo, sample_task, sample_subtasks):
        """Test expanding subtask details"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        # Add more details to subtasks
        for subtask in sample_subtasks:
            subtask.insights_found = ["Insight 1", "Insight 2"]
            subtask.challenges_overcome = ["Challenge 1"]
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = sample_subtasks
        
        # Act
        result = use_case.execute(
            task_id=task_id,
            user_id=user_id,
            expand_details=True
        )
        
        # Assert
        assert all(hasattr(s, 'insights_found') for s in result)
        assert all(hasattr(s, 'challenges_overcome') for s in result)

    def test_get_subtasks_large_count(self, use_case, mock_task_repo, mock_subtask_repo, sample_task):
        """Test handling large number of subtasks"""
        # Arrange
        task_id = sample_task.id.value
        user_id = "user123"
        
        # Create 100 subtasks
        large_subtask_list = []
        for i in range(100):
            sub = Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_task.id,
                title=f"Subtask {i}",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID("user123")],
                order=i
            )
            large_subtask_list.append(sub)
        
        mock_task_repo.get_by_id.return_value = sample_task
        mock_subtask_repo.get_by_task_id.return_value = large_subtask_list
        
        # Act
        result = use_case.execute(task_id=task_id, user_id=user_id)
        
        # Assert
        assert len(result) == 100
        assert result[0].title == "Subtask 0"
        assert result[99].title == "Subtask 99"