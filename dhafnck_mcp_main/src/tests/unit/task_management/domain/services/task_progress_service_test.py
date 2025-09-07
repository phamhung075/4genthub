"""Unit tests for TaskProgressService - Domain Service for Task Progress Calculations"""

import pytest
from unittest.mock import Mock
from decimal import Decimal
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.task_progress_service import (
    TaskProgressService,
    SubtaskRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


class TestTaskProgressService:
    """Test suite for TaskProgressService following DDD patterns."""

    @pytest.fixture
    def mock_subtask_repository(self) -> Mock:
        """Mock subtask repository for testing."""
        return Mock(spec=SubtaskRepositoryProtocol)

    @pytest.fixture
    def progress_service(self) -> TaskProgressService:
        """Create TaskProgressService instance without repository."""
        return TaskProgressService()

    @pytest.fixture
    def progress_service_with_repo(self, mock_subtask_repository: Mock) -> TaskProgressService:
        """Create TaskProgressService instance with repository."""
        return TaskProgressService(subtask_repository=mock_subtask_repository)

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task for testing."""
        return Task(
            id=TaskId.generate(),
            title="Sample Task",
            description="A sample task for progress testing",
            status="in_progress",
            priority="medium"
        )

    def create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
        """Helper method to create a subtask."""
        subtask = Subtask(
            id=SubtaskId.generate(),
            parent_task_id=parent_task_id,
            title=title,
            description=f"Description for {title}",
            status="done" if is_completed else "todo"
        )
        if is_completed:
            subtask._is_completed = True
        return subtask

    class TestCalculateTaskProgress:
        """Test cases for calculate_task_progress method."""

        def test_calculate_progress_no_subtasks(
            self, progress_service: TaskProgressService, sample_task: Task
        ):
            """Test progress calculation for task without subtasks."""
            # Act
            progress = progress_service.calculate_task_progress(sample_task)

            # Assert
            assert progress["task_id"] == str(sample_task.id)
            assert progress["base_progress"]["status"] == "in_progress"
            assert progress["base_progress"]["progress_percentage"] == 50.0  # in_progress = 50%
            assert progress["subtask_progress"] is None
            assert progress["overall_progress"]["percentage"] == 50.0
            assert progress["overall_progress"]["calculation_method"] == "task_status_only"
            assert progress["can_complete"] is True  # No subtasks blocking
            assert len(progress["blocking_factors"]) == 0

        def test_calculate_progress_with_completed_subtasks(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test progress calculation with all subtasks completed."""
            # Arrange
            completed_subtasks = [
                self.create_subtask(sample_task.id, "Subtask 1", is_completed=True),
                self.create_subtask(sample_task.id, "Subtask 2", is_completed=True)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = completed_subtasks

            # Act
            progress = progress_service_with_repo.calculate_task_progress(sample_task)

            # Assert
            assert progress["task_id"] == str(sample_task.id)
            assert progress["base_progress"]["progress_percentage"] == 50.0  # in_progress
            assert progress["subtask_progress"]["completion_percentage"] == 100.0
            assert progress["subtask_progress"]["total"] == 2
            assert progress["subtask_progress"]["completed"] == 2
            assert progress["overall_progress"]["calculation_method"] == "weighted_combination"
            # Weighted: (50 * 0.6) + (100 * 0.4) = 30 + 40 = 70
            assert progress["overall_progress"]["percentage"] == 70.0
            assert progress["can_complete"] is True

        def test_calculate_progress_with_incomplete_subtasks(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test progress calculation with incomplete subtasks."""
            # Arrange
            subtasks = [
                self.create_subtask(sample_task.id, "Complete Task", is_completed=True),
                self.create_subtask(sample_task.id, "Incomplete Task 1", is_completed=False),
                self.create_subtask(sample_task.id, "Incomplete Task 2", is_completed=False)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            progress = progress_service_with_repo.calculate_task_progress(sample_task)

            # Assert
            assert progress["subtask_progress"]["completion_percentage"] == 33.3  # 1 of 3 completed
            assert progress["subtask_progress"]["incomplete"] == 2
            assert progress["can_complete"] is False  # Blocked by incomplete subtasks
            assert len(progress["blocking_factors"]) > 0
            assert any("2 of 3 subtasks incomplete" in factor for factor in progress["blocking_factors"])

        def test_calculate_progress_blocked_task(
            self, progress_service: TaskProgressService
        ):
            """Test progress calculation for blocked task."""
            # Arrange
            blocked_task = Task(
                id=TaskId.generate(),
                title="Blocked Task",
                description="A blocked task",
                status="blocked",
                priority="high"
            )

            # Act
            progress = progress_service.calculate_task_progress(blocked_task)

            # Assert
            assert progress["base_progress"]["progress_percentage"] == 0.0  # blocked = 0%
            assert progress["base_progress"]["is_blocked"] is True
            assert len(progress["blocking_factors"]) > 0
            assert any("Task status is blocked" in factor for factor in progress["blocking_factors"])

        def test_calculate_progress_done_task(
            self, progress_service: TaskProgressService
        ):
            """Test progress calculation for completed task."""
            # Arrange
            done_task = Task(
                id=TaskId.generate(),
                title="Done Task",
                description="A completed task",
                status="done",
                priority="medium"
            )

            # Act
            progress = progress_service.calculate_task_progress(done_task)

            # Assert
            assert progress["base_progress"]["progress_percentage"] == 100.0  # done = 100%
            assert progress["base_progress"]["is_completed"] is True
            assert progress["overall_progress"]["percentage"] == 100.0
            assert progress["can_complete"] is True

        def test_calculate_progress_exception_handling(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test exception handling during progress calculation."""
            # Arrange
            mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("Database error")

            # Act
            progress = progress_service_with_repo.calculate_task_progress(sample_task)

            # Assert
            assert "error" in progress
            assert progress["can_complete"] is False
            assert any("Calculation error" in factor for factor in progress["blocking_factors"])

        def create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
            """Helper method to create a subtask."""
            subtask = Subtask(
                id=SubtaskId.generate(),
                parent_task_id=parent_task_id,
                title=title,
                description=f"Description for {title}",
                status="done" if is_completed else "todo"
            )
            if is_completed:
                subtask._is_completed = True
            return subtask

    class TestCalculateSubtaskCompletionPercentage:
        """Test cases for calculate_subtask_completion_percentage method."""

        def test_no_subtask_repository(
            self, progress_service: TaskProgressService, sample_task: Task
        ):
            """Test percentage calculation without subtask repository."""
            # Act
            percentage = progress_service.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 100.0

        def test_no_subtasks(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test percentage calculation when no subtasks exist."""
            # Arrange
            mock_subtask_repository.find_by_parent_task_id.return_value = []

            # Act
            percentage = progress_service_with_repo.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 100.0

        def test_all_subtasks_completed(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test percentage when all subtasks are completed."""
            # Arrange
            subtasks = [
                self.create_subtask(sample_task.id, "Task 1", is_completed=True),
                self.create_subtask(sample_task.id, "Task 2", is_completed=True)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            percentage = progress_service_with_repo.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 100.0

        def test_partial_completion(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test percentage with partial completion."""
            # Arrange
            subtasks = [
                self.create_subtask(sample_task.id, "Complete 1", is_completed=True),
                self.create_subtask(sample_task.id, "Complete 2", is_completed=True),
                self.create_subtask(sample_task.id, "Incomplete 1", is_completed=False)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            percentage = progress_service_with_repo.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 66.7  # 2 of 3 = 66.666... rounded to 66.7

        def test_decimal_precision(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test decimal precision in percentage calculation."""
            # Arrange - 1 out of 7 subtasks completed = 14.285714...%
            subtasks = [self.create_subtask(sample_task.id, "Complete", is_completed=True)]
            subtasks.extend([
                self.create_subtask(sample_task.id, f"Incomplete {i}", is_completed=False)
                for i in range(6)
            ])
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            percentage = progress_service_with_repo.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 14.3  # Rounded to 1 decimal place

        def test_exception_handling(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test exception handling in percentage calculation."""
            # Arrange
            mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("DB error")

            # Act
            percentage = progress_service_with_repo.calculate_subtask_completion_percentage(sample_task)

            # Assert
            assert percentage == 0.0

        def create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
            """Helper method to create a subtask."""
            subtask = Subtask(
                id=SubtaskId.generate(),
                parent_task_id=parent_task_id,
                title=title,
                description=f"Description for {title}",
                status="done" if is_completed else "todo"
            )
            if is_completed:
                subtask._is_completed = True
            return subtask

    class TestGetSubtaskSummary:
        """Test cases for get_subtask_summary method."""

        def test_no_subtask_repository(
            self, progress_service: TaskProgressService, sample_task: Task
        ):
            """Test subtask summary without repository."""
            # Act
            summary = progress_service.get_subtask_summary(sample_task)

            # Assert
            assert summary["total"] == 0
            assert summary["completed"] == 0
            assert summary["incomplete"] == 0
            assert summary["completion_percentage"] == 100.0
            assert summary["can_complete_parent"] is True
            assert summary["details"] == []

        def test_no_subtasks(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test summary when no subtasks exist."""
            # Arrange
            mock_subtask_repository.find_by_parent_task_id.return_value = []

            # Act
            summary = progress_service_with_repo.get_subtask_summary(sample_task)

            # Assert
            assert summary["total"] == 0
            assert summary["can_complete_parent"] is True

        def test_mixed_subtask_summary(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test summary with mixed completed and incomplete subtasks."""
            # Arrange
            subtasks = [
                self.create_subtask(sample_task.id, "Completed Task 1", is_completed=True),
                self.create_subtask(sample_task.id, "Completed Task 2", is_completed=True),
                self.create_subtask(sample_task.id, "Incomplete Task 1", is_completed=False),
                self.create_subtask(sample_task.id, "Incomplete Task 2", is_completed=False),
                self.create_subtask(sample_task.id, "Incomplete Task 3", is_completed=False)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            summary = progress_service_with_repo.get_subtask_summary(sample_task)

            # Assert
            assert summary["total"] == 5
            assert summary["completed"] == 2
            assert summary["incomplete"] == 3
            assert summary["completion_percentage"] == 40.0  # 2 of 5
            assert summary["can_complete_parent"] is False
            assert len(summary["details"]) == 5
            assert len(summary["incomplete_titles"]) == 3
            assert len(summary["completed_titles"]) == 2

        def test_summary_with_progress_percentage(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test summary includes subtask progress percentage."""
            # Arrange
            subtask = self.create_subtask(sample_task.id, "Test Task", is_completed=False)
            subtask.progress_percentage = 75  # Partially complete
            mock_subtask_repository.find_by_parent_task_id.return_value = [subtask]

            # Act
            summary = progress_service_with_repo.get_subtask_summary(sample_task)

            # Assert
            assert summary["details"][0]["progress_percentage"] == 75

        def test_summary_title_truncation(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test that title lists are truncated to 5 items for UI display."""
            # Arrange
            subtasks = [
                self.create_subtask(sample_task.id, f"Incomplete {i}", is_completed=False)
                for i in range(7)
            ]
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            summary = progress_service_with_repo.get_subtask_summary(sample_task)

            # Assert
            assert len(summary["incomplete_titles"]) == 5  # Truncated
            assert len(summary["completed_titles"]) == 0

        def test_summary_exception_handling(
            self, progress_service_with_repo: TaskProgressService, sample_task: Task, mock_subtask_repository: Mock
        ):
            """Test exception handling in summary generation."""
            # Arrange
            mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("DB error")

            # Act
            summary = progress_service_with_repo.get_subtask_summary(sample_task)

            # Assert
            assert summary["total"] == 0
            assert summary["can_complete_parent"] is False
            assert "error" in summary
            assert summary["error"] == "DB error"

        def create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
            """Helper method to create a subtask."""
            subtask = Subtask(
                id=SubtaskId.generate(),
                parent_task_id=parent_task_id,
                title=title,
                description=f"Description for {title}",
                status="done" if is_completed else "todo"
            )
            if is_completed:
                subtask._is_completed = True
            return subtask

    class TestCalculateProgressScore:
        """Test cases for calculate_progress_score method."""

        def test_todo_task_score(self, progress_service: TaskProgressService):
            """Test progress score for todo task."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Todo Task",
                description="Not started",
                status="todo",
                priority="medium"
            )

            # Act
            score = progress_service.calculate_progress_score(task)

            # Assert
            # todo status = 0.0, no subtasks = 100% = 1.0
            # Weighted: (0.0 * 0.6) + (1.0 * 0.4) = 0.4
            assert score == 0.4

        def test_in_progress_task_score(self, progress_service: TaskProgressService):
            """Test progress score for in-progress task."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="In Progress Task",
                description="Currently working",
                status="in_progress",
                priority="medium"
            )

            # Act
            score = progress_service.calculate_progress_score(task)

            # Assert
            # in_progress status = 0.5, no subtasks = 100% = 1.0
            # Weighted: (0.5 * 0.6) + (1.0 * 0.4) = 0.3 + 0.4 = 0.7
            assert score == 0.7

        def test_done_task_score(self, progress_service: TaskProgressService):
            """Test progress score for completed task."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Done Task",
                description="Completed",
                status="done",
                priority="medium"
            )

            # Act
            score = progress_service.calculate_progress_score(task)

            # Assert
            # done status = 1.0, no subtasks = 100% = 1.0
            # Weighted: (1.0 * 0.6) + (1.0 * 0.4) = 0.6 + 0.4 = 1.0
            assert score == 1.0

        def test_task_with_incomplete_subtasks_score(
            self, progress_service_with_repo: TaskProgressService, mock_subtask_repository: Mock
        ):
            """Test progress score with incomplete subtasks."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Task with Subtasks",
                description="Has subtasks",
                status="in_progress",
                priority="medium"
            )
            
            # 1 of 4 subtasks complete = 25%
            subtasks = [self.create_subtask(task.id, "Complete", is_completed=True)]
            subtasks.extend([
                self.create_subtask(task.id, f"Incomplete {i}", is_completed=False)
                for i in range(3)
            ])
            mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

            # Act
            score = progress_service_with_repo.calculate_progress_score(task)

            # Assert
            # in_progress status = 0.5, subtasks = 25% = 0.25
            # Weighted: (0.5 * 0.6) + (0.25 * 0.4) = 0.3 + 0.1 = 0.4
            assert score == 0.4

        def test_score_bounds_clamping(self, progress_service: TaskProgressService):
            """Test that score is clamped to [0.0, 1.0] bounds."""
            # This test ensures the clamping logic works, though normal calculation shouldn't exceed bounds
            
            # Test with cancelled task (edge case)
            task = Task(
                id=TaskId.generate(),
                title="Cancelled Task",
                description="Cancelled work",
                status="cancelled",
                priority="medium"
            )

            # Act
            score = progress_service.calculate_progress_score(task)

            # Assert
            assert 0.0 <= score <= 1.0

        def test_score_exception_handling(
            self, progress_service_with_repo: TaskProgressService, mock_subtask_repository: Mock
        ):
            """Test exception handling in score calculation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Error Task",
                description="Will cause error",
                status="in_progress",
                priority="medium"
            )
            mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("DB error")

            # Act
            score = progress_service_with_repo.calculate_progress_score(task)

            # Assert
            assert score == 0.0

        def create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
            """Helper method to create a subtask."""
            subtask = Subtask(
                id=SubtaskId.generate(),
                parent_task_id=parent_task_id,
                title=title,
                description=f"Description for {title}",
                status="done" if is_completed else "todo"
            )
            if is_completed:
                subtask._is_completed = True
            return subtask

    class TestStatusProgressMapping:
        """Test cases for status to progress value mapping."""

        def test_get_status_progress_value_all_statuses(self, progress_service: TaskProgressService):
            """Test progress values for all status types."""
            # Create tasks with different statuses and test their progress values
            test_cases = [
                ("todo", 0.0),
                ("in_progress", 0.5),
                ("review", 0.8),
                ("testing", 0.9),
                ("done", 1.0),
                ("blocked", 0.0),
                ("cancelled", 0.0)
            ]

            for status_str, expected_value in test_cases:
                # Create task with specific status
                task = Task(
                    id=TaskId.generate(),
                    title=f"Task with {status_str} status",
                    description="Test task",
                    status=status_str,
                    priority="medium"
                )

                # Get base progress
                progress = progress_service._calculate_base_task_progress(task)
                
                # Assert expected progress percentage
                assert progress["progress_percentage"] == expected_value * 100

        def test_is_status_in_progress_detection(self, progress_service: TaskProgressService):
            """Test detection of in-progress statuses."""
            in_progress_statuses = ["in_progress", "review", "testing"]
            not_in_progress_statuses = ["todo", "done", "blocked", "cancelled"]

            for status_str in in_progress_statuses:
                task = Task(
                    id=TaskId.generate(),
                    title="Test Task",
                    description="Test",
                    status=status_str,
                    priority="medium"
                )
                progress = progress_service._calculate_base_task_progress(task)
                assert progress["is_in_progress"] is True

            for status_str in not_in_progress_statuses:
                task = Task(
                    id=TaskId.generate(),
                    title="Test Task",
                    description="Test",
                    status=status_str,
                    priority="medium"
                )
                progress = progress_service._calculate_base_task_progress(task)
                assert progress["is_in_progress"] is False

        def test_is_status_blocked_detection(self, progress_service: TaskProgressService):
            """Test detection of blocked status."""
            blocked_task = Task(
                id=TaskId.generate(),
                title="Blocked Task",
                description="Test",
                status="blocked",
                priority="medium"
            )
            
            not_blocked_task = Task(
                id=TaskId.generate(),
                title="Active Task",
                description="Test",
                status="in_progress",
                priority="medium"
            )

            blocked_progress = progress_service._calculate_base_task_progress(blocked_task)
            active_progress = progress_service._calculate_base_task_progress(not_blocked_task)

            assert blocked_progress["is_blocked"] is True
            assert active_progress["is_blocked"] is False


# Integration tests for realistic scenarios
class TestTaskProgressServiceIntegration:
    """Integration tests for TaskProgressService with realistic scenarios."""

    def test_complex_project_progress_calculation(self):
        """Test progress calculation for a complex project scenario."""
        # Arrange
        mock_repo = Mock(spec=SubtaskRepositoryProtocol)
        service = TaskProgressService(subtask_repository=mock_repo)

        # Main task: "Implement user authentication system"
        main_task = Task(
            id=TaskId.generate(),
            title="Implement user authentication system",
            description="Complete auth system with login, logout, and session management",
            status="in_progress",
            priority="high"
        )

        # Subtasks with varying completion
        subtasks = [
            # Backend tasks
            self._create_subtask(main_task.id, "Create user model", is_completed=True),
            self._create_subtask(main_task.id, "Implement password hashing", is_completed=True),
            self._create_subtask(main_task.id, "Create login API endpoint", is_completed=True),
            self._create_subtask(main_task.id, "Create logout API endpoint", is_completed=False),
            
            # Frontend tasks
            self._create_subtask(main_task.id, "Design login form UI", is_completed=True),
            self._create_subtask(main_task.id, "Implement login form logic", is_completed=False),
            self._create_subtask(main_task.id, "Add session management", is_completed=False),
            
            # Testing tasks
            self._create_subtask(main_task.id, "Write unit tests", is_completed=False),
            self._create_subtask(main_task.id, "Write integration tests", is_completed=False),
            self._create_subtask(main_task.id, "Manual testing", is_completed=False)
        ]

        mock_repo.find_by_parent_task_id.return_value = subtasks

        # Act
        progress = service.calculate_task_progress(main_task)

        # Assert
        # 4 of 10 subtasks completed = 40%
        # Task status "in_progress" = 50%
        # Weighted: (50 * 0.6) + (40 * 0.4) = 30 + 16 = 46%
        
        assert progress["subtask_progress"]["total"] == 10
        assert progress["subtask_progress"]["completed"] == 4
        assert progress["subtask_progress"]["completion_percentage"] == 40.0
        assert progress["overall_progress"]["percentage"] == 46.0
        assert progress["can_complete"] is False  # 6 incomplete subtasks block completion
        
        # Should have blocking factors
        blocking_factors = progress["blocking_factors"]
        assert len(blocking_factors) > 0
        assert any("6 of 10 subtasks incomplete" in factor for factor in blocking_factors)

        # Get detailed summary
        summary = service.get_subtask_summary(main_task)
        assert len(summary["incomplete_titles"]) == 5  # Truncated to 5 for UI
        assert len(summary["completed_titles"]) == 4

    def test_project_completion_workflow(self):
        """Test the complete workflow of a project from start to finish."""
        mock_repo = Mock(spec=SubtaskRepositoryProtocol)
        service = TaskProgressService(subtask_repository=mock_repo)

        task = Task(
            id=TaskId.generate(),
            title="Small feature implementation",
            description="Simple feature with 3 steps",
            status="todo",
            priority="medium"
        )

        # Phase 1: Project starts - no subtasks yet
        mock_repo.find_by_parent_task_id.return_value = []
        
        phase1_progress = service.calculate_task_progress(task)
        assert phase1_progress["overall_progress"]["percentage"] == 0.0  # todo status
        assert phase1_progress["can_complete"] is True  # No subtasks blocking

        # Phase 2: Subtasks added, work begins
        task.status = "in_progress"
        subtasks = [
            self._create_subtask(task.id, "Step 1", is_completed=False),
            self._create_subtask(task.id, "Step 2", is_completed=False),
            self._create_subtask(task.id, "Step 3", is_completed=False)
        ]
        mock_repo.find_by_parent_task_id.return_value = subtasks

        phase2_progress = service.calculate_task_progress(task)
        assert phase2_progress["overall_progress"]["percentage"] == 30.0  # (50*0.6) + (0*0.4)
        assert phase2_progress["can_complete"] is False

        # Phase 3: First subtask completed
        subtasks[0]._is_completed = True
        subtasks[0].status = "done"

        phase3_progress = service.calculate_task_progress(task)
        # Subtasks: 33.3% complete, Task: 50% (in_progress)
        # Weighted: (50 * 0.6) + (33.3 * 0.4) = 30 + 13.32 = 43.32
        assert abs(phase3_progress["overall_progress"]["percentage"] - 43.3) < 0.1

        # Phase 4: All subtasks completed, task moves to review
        for subtask in subtasks:
            subtask._is_completed = True
            subtask.status = "done"
        task.status = "review"

        phase4_progress = service.calculate_task_progress(task)
        # Subtasks: 100%, Task: 80% (review)
        # Weighted: (80 * 0.6) + (100 * 0.4) = 48 + 40 = 88
        assert phase4_progress["overall_progress"]["percentage"] == 88.0
        assert phase4_progress["can_complete"] is True  # All subtasks done

        # Phase 5: Project completed
        task.status = "done"

        phase5_progress = service.calculate_task_progress(task)
        assert phase5_progress["overall_progress"]["percentage"] == 100.0
        assert phase5_progress["can_complete"] is True

    def _create_subtask(self, parent_task_id: TaskId, title: str, is_completed: bool = False) -> Subtask:
        """Helper to create subtasks for integration tests."""
        subtask = Subtask(
            id=SubtaskId.generate(),
            parent_task_id=parent_task_id,
            title=title,
            description=f"Description for {title}",
            status="done" if is_completed else "todo"
        )
        if is_completed:
            subtask._is_completed = True
        return subtask