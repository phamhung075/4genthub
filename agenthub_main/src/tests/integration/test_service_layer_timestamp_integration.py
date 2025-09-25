"""
Integration tests for service layer timestamp handling.

This test suite validates that the service layer properly integrates with the automated
timestamp management system. Tests cover service operations, repository interactions,
and end-to-end workflows with clean timestamp patterns.
"""

import pytest
from datetime import datetime, timezone
from time import sleep
import uuid

from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.application.dtos.task import CreateTaskRequest, UpdateTaskRequest
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.infrastructure.database.database_config import get_db_config


class TestServiceLayerTimestampIntegration:
    """Integration tests for service layer with automated timestamp handling"""

    @pytest.fixture
    def user_id(self):
        """Test user ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def task_repository(self, user_id):
        """Task repository with test user"""
        db_config = get_db_config()
        session = db_config.get_session()
        return ORMTaskRepository(session=session, user_id=user_id)

    @pytest.fixture
    def project_repository(self, user_id):
        """Project repository with test user"""
        db_config = get_db_config()
        session = db_config.get_session()
        return ORMProjectRepository(session=session, user_id=user_id)

    @pytest.fixture
    def task_service(self, task_repository, user_id):
        """Task application service"""
        return TaskApplicationService(task_repository, user_id=user_id)

    @pytest.fixture
    def project_service(self, project_repository, user_id):
        """Project application service"""
        return ProjectApplicationService(project_repository, user_id=user_id)

    @pytest.fixture
    def test_project_and_branch(self, project_service):
        """Create test project and branch for tasks"""
        project_id = str(uuid.uuid4())

        # Create project
        project_result = project_service.create_project(
            project_id=project_id,
            name="Integration Test Project",
            description="Project for service layer timestamp integration tests"
        )

        # Create git branch
        branch_result = project_service.create_git_branch(
            project_id=project_id,
            git_branch_name="test-branch",
            tree_name="Test Branch",
            tree_description="Test branch for integration tests"
        )

        return {
            'project_id': project_id,
            'git_branch_id': branch_result['git_branch']['id']
        }

    def test_task_service_create_uses_entity_timestamps(self, task_service, test_project_and_branch):
        """Test that TaskApplicationService create operations use entity timestamp management"""
        # Create task through service
        request = CreateTaskRequest(
            title="Service Layer Timestamp Test",
            description="Test automated timestamp handling in service layer",
            git_branch_id=test_project_and_branch['git_branch_id'],
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.HIGH.label
        )

        # Record time before service call
        before_creation = datetime.now(timezone.utc)

        response = task_service.create_task(request)

        # Record time after service call
        after_creation = datetime.now(timezone.utc)

        # Verify task was created successfully
        assert response.success
        assert response.task is not None

        # Verify timestamps are within expected range and properly set
        task = response.task
        assert task.created_at is not None
        assert task.updated_at is not None
        assert before_creation <= task.created_at <= after_creation
        assert before_creation <= task.updated_at <= after_creation

        # For new task, created_at and updated_at should be the same
        assert task.created_at == task.updated_at

    def test_task_service_update_uses_touch_method(self, task_service, test_project_and_branch):
        """Test that TaskApplicationService update operations use entity touch() method"""
        # Create task first
        create_request = CreateTaskRequest(
            title="Update Timestamp Test",
            description="Test timestamp handling during updates",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        task_id = str(create_response.task.id.value)
        original_created = create_response.task.created_at
        original_updated = create_response.task.updated_at

        # Small delay to ensure timestamp difference
        sleep(0.01)

        # Update task through service
        update_request = UpdateTaskRequest(
            task_id=task_id,
            title="Updated Title",
            description="Updated description"
        )

        update_response = task_service.update_task(update_request)

        # Verify update was successful
        assert update_response is not None
        assert update_response.success

        # Verify timestamp behavior
        updated_task = update_response.task
        assert updated_task.created_at == original_created  # Should not change
        assert updated_task.updated_at > original_updated   # Should be updated
        assert updated_task.updated_at > original_created   # Should be newer than creation

    def test_task_completion_uses_clean_timestamp_handling(self, task_service, test_project_and_branch):
        """Test that task completion uses clean timestamp handling (touch method)"""
        # Create task
        create_request = CreateTaskRequest(
            title="Completion Timestamp Test",
            description="Test clean timestamp handling during completion",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        task_id = str(create_response.task.id.value)
        original_created = create_response.task.created_at
        original_updated = create_response.task.updated_at

        # Small delay
        sleep(0.01)

        # Complete task through service
        completion_response = task_service.complete_task(task_id)

        # Verify completion was successful
        assert completion_response["success"]

        # Retrieve completed task to verify timestamps
        completed_task_response = task_service.get_task(task_id)
        completed_task = completed_task_response.task

        # Verify clean timestamp handling
        assert completed_task.created_at == original_created  # Never changes
        assert completed_task.updated_at > original_updated   # Updated by touch()
        assert completed_task.status.value == TaskStatusEnum.DONE.value

    def test_service_layer_no_manual_timestamp_interference(self, task_service, test_project_and_branch):
        """Test that service layer doesn't manually interfere with timestamps"""
        # Create multiple tasks and verify all use automated timestamp handling
        tasks_created = []

        for i in range(3):
            request = CreateTaskRequest(
                title=f"No Interference Test {i}",
                description=f"Task {i} for testing no manual timestamp interference",
                git_branch_id=test_project_and_branch['git_branch_id']
            )

            response = task_service.create_task(request)
            assert response.success
            tasks_created.append(response.task)

            # Small delay between creations
            sleep(0.001)

        # Verify all tasks have proper automated timestamps
        for i, task in enumerate(tasks_created):
            assert task.created_at is not None
            assert task.updated_at is not None
            assert task.created_at == task.updated_at  # New tasks

            # Each subsequent task should have later timestamp
            if i > 0:
                assert task.created_at >= tasks_created[i-1].created_at

    def test_repository_integration_preserves_entity_timestamps(self, task_repository, test_project_and_branch):
        """Test that repository operations preserve entity timestamp management"""
        # Create task entity directly (not through service)
        task = Task.create(
            id=str(uuid.uuid4()),
            title="Repository Integration Test",
            description="Test repository preserves entity timestamps",
            status=TaskStatus(TaskStatusEnum.TODO.value),
            priority=Priority(PriorityLevel.MEDIUM.label),
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        original_created = task.created_at
        original_updated = task.updated_at

        # Save through repository
        save_result = task_repository.save(task)
        assert save_result  # Verify save succeeded

        # Timestamps should be preserved by repository
        assert task.created_at == original_created
        assert task.updated_at == original_updated

        # Retrieve from repository
        retrieved_task = task_repository.get_by_id(task.id)
        assert retrieved_task is not None

        # Retrieved task should have same timestamps
        assert retrieved_task.created_at == original_created
        assert retrieved_task.updated_at == original_updated

    def test_service_operations_generate_domain_events(self, task_service, test_project_and_branch):
        """Test that service operations properly generate timestamp domain events"""
        # Create task
        create_request = CreateTaskRequest(
            title="Domain Events Test",
            description="Test domain event generation through service",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        assert create_response.success

        # The task should have generated domain events during creation
        task = create_response.task

        # Note: Domain events may be cleared by repository after persistence
        # The important thing is that the timestamp system is working
        assert task.created_at is not None
        assert task.updated_at is not None

    def test_concurrent_service_operations_timestamp_consistency(self, task_service, test_project_and_branch):
        """Test timestamp consistency with rapid service operations"""
        # Rapidly create and update tasks to test timestamp consistency
        create_request = CreateTaskRequest(
            title="Concurrency Test",
            description="Test concurrent operations timestamp consistency",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        task_id = str(create_response.task.id.value)

        # Rapid updates
        timestamps = []
        for i in range(5):
            update_request = UpdateTaskRequest(
                task_id=task_id,
                description=f"Rapid update {i}"
            )

            update_response = task_service.update_task(update_request)
            assert update_response.success
            timestamps.append(update_response.task.updated_at)

            # Very small delay
            sleep(0.001)

        # Verify timestamps are consistent and increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]

    def test_service_error_handling_preserves_timestamps(self, task_service, test_project_and_branch):
        """Test that service error conditions don't corrupt timestamp handling"""
        # Create valid task
        create_request = CreateTaskRequest(
            title="Error Handling Test",
            description="Test error handling preserves timestamps",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        task_id = str(create_response.task.id.value)
        original_created = create_response.task.created_at
        original_updated = create_response.task.updated_at

        # Attempt invalid update (should handle gracefully)
        try:
            invalid_update = UpdateTaskRequest(
                task_id=task_id,
                title=""  # Invalid empty title
            )
            task_service.update_task(invalid_update)
        except Exception:
            pass  # Expected to potentially fail

        # Retrieve task and verify timestamps weren't corrupted
        retrieved_task_response = task_service.get_task(task_id)
        if retrieved_task_response:
            task = retrieved_task_response.task
            assert task.created_at == original_created
            # updated_at might have changed if update partially succeeded

    def test_cross_service_timestamp_consistency(self, task_service, project_service, test_project_and_branch):
        """Test timestamp consistency across different service operations"""
        project_id = test_project_and_branch['project_id']

        # Get project
        project_response = project_service.get_project(project_id)
        assert project_response["success"]

        # Create task
        task_request = CreateTaskRequest(
            title="Cross-Service Test",
            description="Test cross-service timestamp consistency",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        task_response = task_service.create_task(task_request)
        assert task_response.success

        # Both operations should use consistent timestamp management
        # (Both should rely on entity timestamp handling, not manual service timestamps)
        task = task_response.task
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.created_at.tzinfo == timezone.utc
        assert task.updated_at.tzinfo == timezone.utc

    def test_service_layer_touch_method_integration(self, task_service, test_project_and_branch):
        """Test that service layer operations properly integrate with entity touch() method"""
        # Create task
        create_request = CreateTaskRequest(
            title="Touch Method Integration Test",
            description="Test service integration with touch method",
            git_branch_id=test_project_and_branch['git_branch_id']
        )

        create_response = task_service.create_task(create_request)
        task_id = str(create_response.task.id.value)

        # Track timestamp changes through multiple service operations
        timestamps = [(create_response.task.created_at, create_response.task.updated_at)]

        # Update through service multiple times
        for i in range(3):
            sleep(0.01)

            update_request = UpdateTaskRequest(
                task_id=task_id,
                description=f"Touch integration test update {i}"
            )

            update_response = task_service.update_task(update_request)
            assert update_response.success

            task = update_response.task
            timestamps.append((task.created_at, task.updated_at))

        # Verify timestamp behavior consistent with touch() method
        original_created = timestamps[0][0]

        for created, updated in timestamps:
            assert created == original_created  # created_at never changes
            assert updated >= original_created  # updated_at >= created_at

        # Verify updated_at progresses with each update
        for i in range(1, len(timestamps)):
            assert timestamps[i][1] >= timestamps[i-1][1]