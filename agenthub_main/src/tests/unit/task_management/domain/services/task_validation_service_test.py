"""Unit tests for TaskValidationService - Domain Service for Complex Task Business Validation"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from fastmcp.task_management.domain.services.task_validation_service import (
    TaskValidationService,
    GitBranchRepositoryProtocol,
    ProjectRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestTaskValidationService:
    """Test suite for TaskValidationService following DDD patterns."""

    @pytest.fixture
    def mock_git_branch_repository(self) -> Mock:
        """Mock git branch repository for testing."""
        return Mock(spec=GitBranchRepositoryProtocol)

    @pytest.fixture
    def mock_project_repository(self) -> Mock:
        """Mock project repository for testing."""
        return Mock(spec=ProjectRepositoryProtocol)

    @pytest.fixture
    def validation_service(self) -> TaskValidationService:
        """Create TaskValidationService instance without repositories."""
        return TaskValidationService()

    @pytest.fixture
    def validation_service_with_repos(
        self, 
        mock_git_branch_repository: Mock, 
        mock_project_repository: Mock
    ) -> TaskValidationService:
        """Create TaskValidationService instance with repositories."""
        return TaskValidationService(
            git_branch_repository=mock_git_branch_repository,
            project_repository=mock_project_repository
        )

    @pytest.fixture
    def valid_task(self) -> Task:
        """Create a valid task for testing."""
        task = Task(
            id=TaskId.generate(),
            title="Implement user authentication",
            description="Add JWT-based authentication to the system",
            status="todo",
            priority="medium"
        )
        task.git_branch_id = "test-branch-id"
        task.project_id = "test-project-id"
        task.assignees = ["developer1"]
        task.labels = ["feature", "auth"]
        task.dependencies = []
        task.estimated_effort = "2 days"
        return task

    @pytest.fixture
    def invalid_task(self) -> Task:
        """Create an invalid task for testing."""
        task = Task(
            id=TaskId.generate(),
            title="",  # Invalid: empty title
            description="",
            status="invalid_status",  # Invalid status
            priority="invalid_priority"  # Invalid priority
        )
        task.assignees = [""] * 10  # Invalid: too many empty assignees
        task.labels = [""] * 15  # Invalid: too many empty labels
        return task

    class TestValidateTaskCreation:
        """Test cases for validate_task_creation method."""

        def test_valid_task_creation(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test that a valid task passes creation validation."""
            # Act
            errors = validation_service.validate_task_creation(valid_task)

            # Assert
            assert errors == []

        def test_invalid_task_creation_core_fields(
            self, validation_service: TaskValidationService
        ):
            """Test validation of core fields during task creation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),  # Create valid task first
                title="Valid title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            # Modify after creation to create invalid state
            task.id = None
            task.title = ""
            task.status = ""
            task.priority = ""

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("Task ID is required" in error for error in errors)
            assert any("Task title is required" in error for error in errors)
            assert any("Task status is required" in error for error in errors)
            assert any("Task priority is required" in error for error in errors)

        def test_task_creation_with_invalid_title_length(
            self, validation_service: TaskValidationService
        ):
            """Test title length validation during creation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",  # Create valid task first
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.title = "A" * 250  # Modify after creation to bypass entity validation

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot exceed 200 characters" in error for error in errors)

        def test_task_creation_with_short_title(
            self, validation_service: TaskValidationService
        ):
            """Test minimum title length validation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="AB",  # Invalid: too short
                description="Valid description",
                status="todo",
                priority="medium"
            )

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("must be at least 3 characters long" in error for error in errors)

        def test_task_creation_with_placeholder_title(
            self, validation_service: TaskValidationService
        ):
            """Test detection of placeholder titles."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="TODO: Fix this test placeholder",
                description="Valid description",
                status="todo",
                priority="medium"
            )

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("placeholder text" in error for error in errors)

        def test_task_creation_with_too_many_assignees(
            self, validation_service: TaskValidationService
        ):
            """Test assignee limit validation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.assignees = [f"user{i}" for i in range(6)]  # Invalid: too many

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot have more than 5 assignees" in error for error in errors)

        def test_task_creation_with_too_many_labels(
            self, validation_service: TaskValidationService
        ):
            """Test label limit validation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.labels = [f"label{i}" for i in range(11)]  # Invalid: too many

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot have more than 10 labels" in error for error in errors)

        def test_task_creation_with_future_due_date_limit(
            self, validation_service: TaskValidationService
        ):
            """Test due date future limit validation."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            # Set due date 3 years in the future (invalid)
            task.due_date = datetime.now(timezone.utc) + timedelta(days=365 * 3)

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot be more than 2 years in the future" in error for error in errors)

        def test_task_creation_with_similar_title_context(
            self, validation_service: TaskValidationService
        ):
            """Test detection of similar titles in context."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Implement user authentication",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            
            context = {
                'similar_tasks': [
                    {'title': 'Implement user authentication', 'id': 'other-task-id'}
                ]
            }

            # Act
            errors = validation_service.validate_task_creation(task, context)

            # Assert
            assert len(errors) > 0
            assert any("similar title already exists" in error for error in errors)

        def test_task_creation_exception_handling(
            self, validation_service: TaskValidationService
        ):
            """Test exception handling during validation."""
            # Arrange
            task = Mock()
            task.title = "Valid Title"
            task.id = TaskId.generate()
            # Make accessing a property raise an exception
            type(task).status = Mock(side_effect=Exception("Test error"))

            # Act
            errors = validation_service.validate_task_creation(task)

            # Assert
            assert len(errors) > 0
            assert any("validation error" in error.lower() for error in errors)

    class TestValidateTaskUpdate:
        """Test cases for validate_task_update method."""

        def test_valid_task_update(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test that a valid task update passes validation."""
            # Arrange
            current_task = valid_task
            updated_task = Task(
                id=current_task.id,
                title="Updated: Implement user authentication",
                description="Updated description",
                status="in_progress",
                priority="high"
            )
            updated_task.git_branch_id = current_task.git_branch_id

            # Act
            errors = validation_service.validate_task_update(current_task, updated_task)

            # Assert
            assert errors == []

        def test_invalid_id_change_in_update(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test that ID cannot be changed during update."""
            # Arrange
            current_task = valid_task
            updated_task = Task(
                id=TaskId.generate(),  # Different ID - invalid
                title=current_task.title,
                description=current_task.description,
                status=current_task.status,
                priority=current_task.priority
            )

            # Act
            errors = validation_service.validate_task_update(current_task, updated_task)

            # Assert
            assert len(errors) > 0
            assert any("cannot be modified after creation" in error for error in errors)

        def test_invalid_status_transition(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test invalid status transition validation."""
            # Arrange
            current_task = valid_task
            current_task.status = "done"
            
            updated_task = Task(
                id=current_task.id,
                title=current_task.title,
                description=current_task.description,
                status="todo",  # Invalid transition from 'done' to 'todo'
                priority=current_task.priority
            )

            # Act
            errors = validation_service.validate_task_update(current_task, updated_task)

            # Assert
            assert len(errors) > 0
            assert any("Invalid status transition" in error for error in errors)

        def test_valid_status_transitions(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test valid status transitions."""
            # Test todo -> in_progress
            current_task = valid_task
            current_task.status = "todo"
            
            updated_task = Task(
                id=current_task.id,
                title=current_task.title,
                description=current_task.description,
                status="in_progress",
                priority=current_task.priority
            )
            updated_task.git_branch_id = current_task.git_branch_id

            errors = validation_service.validate_task_update(current_task, updated_task)
            assert errors == []

            # Test in_progress -> review
            current_task.status = "in_progress"
            updated_task.status = "review"
            
            errors = validation_service.validate_task_update(current_task, updated_task)
            assert errors == []

    class TestValidateTaskRelationships:
        """Test cases for validate_task_relationships method."""

        def test_valid_relationships(
            self, validation_service_with_repos: TaskValidationService, valid_task: Task
        ):
            """Test validation of valid relationships."""
            # Arrange
            validation_service_with_repos._git_branch_repository.exists.return_value = True
            validation_service_with_repos._project_repository.exists.return_value = True

            # Act
            is_valid, errors = validation_service_with_repos.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is True
            assert errors == []
            validation_service_with_repos._git_branch_repository.exists.assert_called_once_with(valid_task.git_branch_id)
            validation_service_with_repos._project_repository.exists.assert_called_once_with(valid_task.project_id)

        def test_missing_git_branch(
            self, validation_service_with_repos: TaskValidationService, valid_task: Task
        ):
            """Test validation when git branch doesn't exist."""
            # Arrange
            validation_service_with_repos._git_branch_repository.exists.return_value = False
            validation_service_with_repos._project_repository.exists.return_value = True

            # Act
            is_valid, errors = validation_service_with_repos.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is False
            assert len(errors) > 0
            assert any("does not exist" in error for error in errors)

        def test_missing_git_branch_id(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test validation when git branch ID is missing."""
            # Arrange
            valid_task.git_branch_id = None

            # Act
            is_valid, errors = validation_service.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is False
            assert len(errors) > 0
            assert any("must be associated with a valid git branch" in error for error in errors)

        def test_too_many_dependencies(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test validation of too many dependencies."""
            # Arrange
            valid_task.dependencies = [f"dep-{i}" for i in range(11)]  # Too many

            # Act
            is_valid, errors = validation_service.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is False
            assert len(errors) > 0
            assert any("cannot have more than 10 dependencies" in error for error in errors)

        def test_self_dependency(
            self, validation_service: TaskValidationService, valid_task: Task
        ):
            """Test validation of self-dependency."""
            # Arrange
            valid_task.dependencies = [str(valid_task.id)]

            # Act
            is_valid, errors = validation_service.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is False
            assert len(errors) > 0
            assert any("cannot depend on itself" in error for error in errors)

        def test_relationship_validation_exception(
            self, validation_service_with_repos: TaskValidationService, valid_task: Task
        ):
            """Test exception handling in relationship validation."""
            # Arrange
            validation_service_with_repos._git_branch_repository.exists.side_effect = Exception("DB error")

            # Act
            is_valid, errors = validation_service_with_repos.validate_task_relationships(valid_task)

            # Assert
            assert is_valid is False
            assert len(errors) > 0
            assert any("Relationship validation error" in error for error in errors)

    class TestValidateBusinessConstraints:
        """Test cases for validate_business_constraints method."""

        def test_empty_title_constraint(
            self, validation_service: TaskValidationService
        ):
            """Test empty title business constraint."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",  # Create valid task first
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.title = ""  # Modify after creation to bypass entity validation

            # Act
            errors = validation_service.validate_business_constraints(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot be empty" in error for error in errors)

        def test_whitespace_only_title_constraint(
            self, validation_service: TaskValidationService
        ):
            """Test whitespace-only title constraint."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",  # Create valid task first
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.title = "   "  # Modify after creation to bypass entity validation

            # Act
            errors = validation_service.validate_business_constraints(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot be empty" in error for error in errors)

        def test_long_description_constraint(
            self, validation_service: TaskValidationService
        ):
            """Test long description constraint."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",
                description="Valid description",  # Create valid task first
                status="todo",
                priority="medium"
            )
            task.description = "A" * 2001  # Modify after creation to bypass entity validation

            # Act
            errors = validation_service.validate_business_constraints(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot exceed 2000 characters" in error for error in errors)

        def test_empty_assignee_constraint(
            self, validation_service: TaskValidationService
        ):
            """Test empty assignee constraint."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.assignees = ["", "   ", "valid_user"]  # Contains empty assignees

            # Act
            errors = validation_service.validate_business_constraints(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot be empty" in error for error in errors)

        def test_long_assignee_name_constraint(
            self, validation_service: TaskValidationService
        ):
            """Test long assignee name constraint."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.assignees = ["A" * 51]  # Too long

            # Act
            errors = validation_service.validate_business_constraints(task)

            # Assert
            assert len(errors) > 0
            assert any("cannot exceed 50 characters" in error for error in errors)

        def test_critical_priority_todo_status_warning(
            self, validation_service: TaskValidationService
        ):
            """Test warning for critical priority tasks in todo status."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Critical task",
                description="Valid description",
                status="todo",
                priority="critical"
            )

            # Act
            errors = validation_service.validate_business_constraints(task, 'create')

            # Assert
            assert len(errors) > 0
            assert any("should be started immediately" in error for error in errors)

        def test_high_priority_done_without_summary(
            self, validation_service: TaskValidationService
        ):
            """Test validation of high priority done tasks without completion summary."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Urgent task",
                description="Valid description",
                status="done",
                priority="urgent"
            )
            # No completion summary

            # Act
            errors = validation_service.validate_business_constraints(task, 'update')

            # Assert
            assert len(errors) > 0
            assert any("must include completion summary" in error for error in errors)

    class TestValidateContentAppropriateness:
        """Test cases for validate_content_appropriateness method."""

        def test_repetitive_title_validation(
            self, validation_service: TaskValidationService
        ):
            """Test detection of repetitive titles."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="test test test test",  # Too much repetition
                description="Valid description",
                status="todo",
                priority="medium"
            )

            # Act
            errors = validation_service.validate_content_appropriateness(task)

            # Assert
            assert len(errors) > 0
            assert any("too much repetition" in error for error in errors)

        def test_brief_description_validation(
            self, validation_service: TaskValidationService
        ):
            """Test detection of too brief descriptions."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Brief",  # Too brief
                status="todo",
                priority="medium"
            )

            # Act
            errors = validation_service.validate_content_appropriateness(task)

            # Assert
            assert len(errors) > 0
            assert any("too brief to be meaningful" in error for error in errors)

        def test_invalid_estimated_effort_format(
            self, validation_service: TaskValidationService
        ):
            """Test validation of estimated effort format."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            task.estimated_effort = "sometime"  # Invalid format

            # Act
            errors = validation_service.validate_content_appropriateness(task)

            # Assert
            assert len(errors) > 0
            assert any("should include time units" in error for error in errors)

        def test_valid_estimated_effort_formats(
            self, validation_service: TaskValidationService
        ):
            """Test valid estimated effort formats."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Valid description",
                status="todo",
                priority="medium"
            )
            
            valid_efforts = ["2 hours", "1 day", "3 weeks", "1 month", "5 minutes", "2 sprints", "3 story points"]
            
            for effort in valid_efforts:
                task.estimated_effort = effort
                errors = validation_service.validate_content_appropriateness(task)
                
                # Should not have effort-related errors
                effort_errors = [e for e in errors if "time units" in e]
                assert len(effort_errors) == 0

        def test_acceptable_brief_descriptions(
            self, validation_service: TaskValidationService
        ):
            """Test that certain brief descriptions are acceptable."""
            # Arrange
            task = Task(
                id=TaskId.generate(),
                title="Valid task title",
                description="Initial description",
                status="todo",
                priority="medium"
            )
            
            acceptable_brief_descriptions = ["", "n/a", "na", "none"]
            
            for desc in acceptable_brief_descriptions:
                task.description = desc
                errors = validation_service.validate_content_appropriateness(task)
                
                # Should not have description-related errors
                desc_errors = [e for e in errors if "too brief" in e]
                assert len(desc_errors) == 0

        def test_content_validation_exception(
            self, validation_service: TaskValidationService
        ):
            """Test exception handling in content validation."""
            # Arrange
            task = Mock()
            task.title = "Valid Title"
            task.id = TaskId.generate()
            # Make accessing description raise an exception
            type(task).description = Mock(side_effect=Exception("Test error"))

            # Act
            errors = validation_service.validate_content_appropriateness(task)

            # Assert
            assert len(errors) > 0
            assert any("Content validation error" in error for error in errors)


# Integration tests for realistic scenarios
class TestTaskValidationServiceIntegration:
    """Integration tests for TaskValidationService with realistic scenarios."""

    @pytest.fixture
    def integration_service(self):
        """Set up service with mocked dependencies for integration tests."""
        git_repo = Mock(spec=GitBranchRepositoryProtocol)
        project_repo = Mock(spec=ProjectRepositoryProtocol)
        service = TaskValidationService(git_repo, project_repo)
        return service, git_repo, project_repo

    def test_comprehensive_task_validation_workflow(self, integration_service):
        """Test a comprehensive task validation workflow."""
        service, git_repo, project_repo = integration_service
        
        # Setup repository responses
        git_repo.exists.return_value = True
        git_repo.get_branch_info.return_value = {"name": "feature/auth"}
        project_repo.exists.return_value = True
        
        # Create a realistic task for validation
        task = Task(
            id=TaskId.generate(),
            title="Implement JWT-based authentication system",
            description="Design and implement a comprehensive JWT authentication system with token refresh, role-based access control, and secure session management. Include unit tests and documentation.",
            status="todo",
            priority="high"
        )
        task.git_branch_id = "branch-uuid-123"
        task.project_id = "project-uuid-456"
        task.assignees = ["senior.developer@company.com", "security.engineer@company.com"]
        task.labels = ["feature", "authentication", "security", "high-priority"]
        task.dependencies = []
        task.estimated_effort = "2 weeks"
        task.due_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Test creation validation
        creation_errors = service.validate_task_creation(task)
        assert creation_errors == []
        
        # Test relationship validation
        is_valid, relationship_errors = service.validate_task_relationships(task)
        assert is_valid is True
        assert relationship_errors == []
        
        # Test business constraints
        business_errors = service.validate_business_constraints(task, 'create')
        assert business_errors == []
        
        # Test content appropriateness
        content_errors = service.validate_content_appropriateness(task)
        assert content_errors == []
        
        # Test task update scenario
        updated_task = Task(
            id=task.id,  # Same ID
            title=task.title + " - Updated",
            description=task.description + " Updated with additional requirements.",
            status="in_progress",  # Valid transition from 'todo'
            priority="urgent"  # Changed priority
        )
        updated_task.git_branch_id = task.git_branch_id
        updated_task.project_id = task.project_id
        updated_task.assignees = task.assignees + ["junior.developer@company.com"]
        updated_task.labels = task.labels
        updated_task.dependencies = task.dependencies
        updated_task.estimated_effort = "3 weeks"  # Updated estimate
        
        update_errors = service.validate_task_update(task, updated_task)
        assert update_errors == []

    def test_multiple_validation_failures(self, integration_service):
        """Test handling of multiple validation failures simultaneously."""
        service, git_repo, project_repo = integration_service
        
        # Setup repository responses for failures
        git_repo.exists.return_value = False  # Git branch doesn't exist
        project_repo.exists.return_value = False  # Project doesn't exist
        
        # Create a task with multiple validation issues
        task = Task(
            id=TaskId.generate(),
            title="Valid title",  # Create valid task first
            description="Valid description",
            status="todo",
            priority="medium"
        )
        # Modify after creation to create invalid state
        task.title = "TODO"  # Placeholder title
        task.description = "A" * 2001  # Too long description
        task.priority = "critical"  # Critical but in todo status
        task.git_branch_id = "non-existent-branch"
        task.project_id = "non-existent-project"
        task.assignees = [""] * 6  # Too many empty assignees
        task.labels = [""] * 11  # Too many empty labels
        task.dependencies = [str(task.id)]  # Self-dependency
        task.estimated_effort = "sometime"  # Invalid format
        task.due_date = datetime.now(timezone.utc) + timedelta(days=365 * 3)  # Too far in future
        
        # Test that all validation types catch their respective errors
        creation_errors = service.validate_task_creation(task)
        is_valid, relationship_errors = service.validate_task_relationships(task)
        business_errors = service.validate_business_constraints(task, 'create')
        content_errors = service.validate_content_appropriateness(task)
        
        # Should have multiple types of errors
        all_errors = creation_errors + relationship_errors + business_errors + content_errors
        
        # Verify specific error categories are present
        assert any("placeholder text" in error for error in all_errors)
        assert any("does not exist" in error for error in all_errors)
        assert any("cannot have more than" in error for error in all_errors)
        assert any("cannot depend on itself" in error for error in all_errors)
        assert any("should be started immediately" in error for error in all_errors)
        assert any("time units" in error for error in all_errors)
        assert any("2 years in the future" in error for error in all_errors)
        
        assert len(all_errors) >= 7  # At least 7 different types of errors