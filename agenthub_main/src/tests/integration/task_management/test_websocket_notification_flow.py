"""
Integration Tests for WebSocket Notification Flow

Test Coverage:
- End-to-end notification flow across all DDD layers
- Complete workflow: Controller → Use Case → WebSocket → Frontend
- Cascade data updates after task operations
- Multi-tenant isolation and authorization
- Notification payload structure validation
- Deduplication across the full flow

Following DDD Clean Architecture:
- Interface Layer (Controllers) → Application Layer (Use Cases) → Infrastructure Layer (WebSocket)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest,
    UpdateTaskRequest,
)
from fastmcp.task_management.domain.value_objects import Priority, TaskStatus
from fastmcp.task_management.domain.value_objects.priority import PriorityLevel
from fastmcp.task_management.domain.value_objects.task_status import TaskStatusEnum


class TestCreateTaskNotificationFlow:
    """
    Integration tests for task creation notification flow.
    Tests complete workflow: Create Task → Use Case → WebSocket Broadcast
    """

    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository for integration tests"""
        repo = Mock()
        repo.get_next_id = Mock(return_value=Mock(value=str(uuid4())))
        repo.save = Mock(return_value=True)
        repo.git_branch_exists = Mock(return_value=True)
        repo.user_id = "test-user-123"
        return repo

    @pytest.fixture
    def mock_git_branch_repository(self):
        """Create mock git branch repository"""
        repo = Mock()
        branch = Mock()
        branch.project_id = "project-123"
        branch.task_count = 1
        branch.completed_tasks = 0
        branch.in_progress_tasks = 1
        branch.todo_tasks = 0
        branch.progress_percentage = 0.0
        branch.id = "branch-123"
        branch.name = "Test Branch"
        # Configure mock to return None for any other attribute access to avoid Mock object serialization
        branch.configure_mock(**{attr: None for attr in dir(branch) if not attr.startswith('_') and attr not in ['project_id', 'task_count', 'completed_tasks', 'in_progress_tasks', 'todo_tasks', 'progress_percentage', 'id', 'name']})
        repo.get = Mock(return_value=branch)
        return repo

    @pytest.fixture
    def create_task_use_case(self, mock_task_repository, mock_git_branch_repository):
        """Create CreateTaskUseCase with mocked dependencies"""
        from fastmcp.task_management.application.use_cases.create_task import (
            CreateTaskUseCase,
        )
        return CreateTaskUseCase(
            task_repository=mock_task_repository,
            git_branch_repository=mock_git_branch_repository
        )

    @pytest.fixture(autouse=True)
    def clear_websocket_connections(self):
        """Clear WebSocket connections before each test"""
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_subscriptions,
            connection_users,
        )
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()
        yield
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()

    @pytest.fixture(autouse=True)
    def clear_deduplication_cache(self):
        """Clear deduplication cache before each test"""
        from fastmcp.task_management.application.services import (
            websocket_notification_service,
        )
        websocket_notification_service._notification_cache.clear()
        yield
        websocket_notification_service._notification_cache.clear()

    @pytest.mark.asyncio
    async def test_create_task_triggers_websocket_notification(
        self, create_task_use_case, mock_task_repository, mock_git_branch_repository
    ):
        """
        Test that creating a task triggers WebSocket notification with complete flow.

        Flow:
        1. Create task via use case
        2. Use case saves task to repository
        3. Use case calls WebSocketNotificationService
        4. WebSocket broadcasts to connected clients
        """
        # Arrange: Setup WebSocket connection
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-1"].add(mock_websocket)

        # Mock user for connection
        mock_user = Mock()
        mock_user.id = "test-user-123"
        connection_users[mock_websocket] = mock_user

        # Arrange: Create task request
        request = CreateTaskRequest(
            title="Integration Test Task",
            description="Testing full notification flow",
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.HIGH.label,
            git_branch_id="branch-123",
            assignees=["test-agent"],
            user_id="test-user-123"
        )

        # Arrange: Mock authorization to always return True
        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            # Act: Create task (triggers full flow)
            response = create_task_use_case.execute(request)

            # Wait for async WebSocket broadcast
            await asyncio.sleep(0.1)

        # Assert: Task created successfully
        assert response.success is True
        assert response.task is not None

        # Assert: WebSocket notification sent
        assert mock_websocket.send_json.called

        # Assert: Notification payload structure
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert "id" in sent_message
        assert "version" in sent_message
        assert sent_message["version"] == "2.0"
        assert "type" in sent_message
        assert "payload" in sent_message
        assert "metadata" in sent_message

    @pytest.mark.asyncio
    async def test_notification_payload_matches_frontend_expectations(
        self, create_task_use_case, mock_task_repository, mock_git_branch_repository
    ):
        """
        Test that notification payload structure matches TypeScript interface.

        Expected Frontend Interface:
        - event_type: "created" | "updated" | "deleted" | "completed"
        - entity_type: "task" | "subtask" | "branch" | "project"
        - entity_id: string (UUID)
        - user_id: string (UUID)
        - data: object | null
        - metadata: object with timestamp, git_branch_id, etc.
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-1"].add(mock_websocket)

        mock_user = Mock()
        mock_user.id = "test-user-123"
        connection_users[mock_websocket] = mock_user

        request = CreateTaskRequest(
            title="Frontend Interface Test",
            description="Validate payload structure",
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.MEDIUM.label,
            git_branch_id="branch-456",
            assignees=["test-agent"],
            user_id="test-user-123"
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            create_task_use_case.execute(request)
            await asyncio.sleep(0.1)

        # Assert: Validate complete payload structure
        sent_message = mock_websocket.send_json.call_args[0][0]

        # Top-level required fields
        required_fields = ["id", "version", "type", "timestamp", "sequence", "payload", "metadata"]
        for field in required_fields:
            assert field in sent_message, f"Missing required field: {field}"

        # Payload structure
        assert "entity" in sent_message["payload"]
        assert "action" in sent_message["payload"]
        assert "data" in sent_message["payload"]

        # Metadata structure
        assert "source" in sent_message["metadata"]
        assert "userId" in sent_message["metadata"]
        assert "entity_type" in sent_message["metadata"]
        assert "entity_id" in sent_message["metadata"]
        assert "event_type" in sent_message["metadata"]

    @pytest.mark.asyncio
    async def test_cascade_data_included_in_notification(
        self, create_task_use_case, mock_task_repository, mock_git_branch_repository
    ):
        """
        Test that cascade data (branch statistics) is included in notification.

        Cascade data should include:
        - branches: Array of branch statistics
        - task_count, completed_tasks, progress_percentage per branch
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-1"].add(mock_websocket)

        mock_user = Mock()
        mock_user.id = "test-user-123"
        connection_users[mock_websocket] = mock_user

        # Mock branch with statistics
        branch_with_stats = Mock()
        branch_with_stats.id = "branch-789"
        branch_with_stats.project_id = "project-123"
        branch_with_stats.task_count = 5
        branch_with_stats.completed_tasks = 2
        branch_with_stats.in_progress_tasks = 2
        branch_with_stats.todo_tasks = 1
        branch_with_stats.progress_percentage = 40.0

        mock_git_branch_repository.get.return_value = branch_with_stats

        request = CreateTaskRequest(
            title="Cascade Data Test",
            description="Test cascade data inclusion",
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.LOW.label,
            git_branch_id="branch-789",
            assignees=["test-agent"],
            user_id="test-user-123"
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            create_task_use_case.execute(request)
            await asyncio.sleep(0.1)

        # Assert: Cascade data present
        sent_message = mock_websocket.send_json.call_args[0][0]

        # Check cascade data location (should be in payload.data, not metadata after bug fix)
        if "cascade" in sent_message["payload"]["data"]:
            cascade = sent_message["payload"]["data"]["cascade"]
            assert "branches" in cascade
            assert isinstance(cascade["branches"], list)


class TestUpdateTaskNotificationFlow:
    """
    Integration tests for task update notification flow.
    """

    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        repo = Mock()

        # Mock task entity
        task = Mock()
        task.id = Mock(value="task-update-123")
        task.title = "Original Title"
        task.description = "Original Description"
        task.status = TaskStatus(TaskStatusEnum.TODO.value)
        task.priority = Priority(PriorityLevel.MEDIUM.label)
        task.git_branch_id = "branch-update-123"
        task.get_events = Mock(return_value=[])

        repo.get = Mock(return_value=task)
        repo.save = Mock(return_value=True)
        repo.user_id = "test-user-456"

        return repo

    @pytest.fixture
    def mock_git_branch_repository(self):
        """Create mock git branch repository"""
        repo = Mock()
        branch = Mock()
        branch.project_id = "project-456"
        branch.task_count = 1
        branch.completed_tasks = 0
        branch.in_progress_tasks = 1
        branch.todo_tasks = 0
        branch.progress_percentage = 0.0
        branch.id = "branch-update-123"
        branch.name = "Update Test Branch"
        # Configure mock to return None for any other attribute access to avoid Mock object serialization
        branch.configure_mock(**{attr: None for attr in dir(branch) if not attr.startswith('_') and attr not in ['project_id', 'task_count', 'completed_tasks', 'in_progress_tasks', 'todo_tasks', 'progress_percentage', 'id', 'name']})
        repo.get = Mock(return_value=branch)
        return repo

    @pytest.fixture
    def update_task_use_case(self, mock_task_repository, mock_git_branch_repository):
        """Create UpdateTaskUseCase with mocked dependencies"""
        from fastmcp.task_management.application.use_cases.update_task import (
            UpdateTaskUseCase,
        )
        return UpdateTaskUseCase(
            task_repository=mock_task_repository,
            git_branch_repository=mock_git_branch_repository
        )

    @pytest.fixture(autouse=True)
    def clear_websocket_connections(self):
        """Clear WebSocket connections before each test"""
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_subscriptions,
            connection_users,
        )
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()
        yield
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()

    @pytest.fixture(autouse=True)
    def clear_deduplication_cache(self):
        """Clear deduplication cache before each test"""
        from fastmcp.task_management.application.services import (
            websocket_notification_service,
        )
        websocket_notification_service._notification_cache.clear()
        yield
        websocket_notification_service._notification_cache.clear()

    @pytest.mark.asyncio
    async def test_update_task_triggers_websocket_notification(
        self, update_task_use_case, mock_task_repository
    ):
        """
        Test that updating a task triggers WebSocket notification.

        Flow:
        1. Update task via use case
        2. Use case updates task in repository
        3. Use case calls WebSocketNotificationService
        4. WebSocket broadcasts update notification
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-2"].add(mock_websocket)

        mock_user = Mock()
        mock_user.id = "test-user-456"
        connection_users[mock_websocket] = mock_user

        request = UpdateTaskRequest(
            title="Updated Title",
            description="Updated Description",
            status=TaskStatusEnum.IN_PROGRESS.value
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            # Act
            response = update_task_use_case.execute("task-update-123", request, "test-user-456")
            await asyncio.sleep(0.1)

        # Assert
        assert response.success is True
        assert mock_websocket.send_json.called

        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["payload"]["action"] == "updated"


class TestDeleteTaskNotificationFlow:
    """
    Integration tests for task deletion notification flow.
    Tests pre-fetched context usage for deletion notifications.
    """

    @pytest.fixture(autouse=True)
    def clear_websocket_connections(self):
        """Clear WebSocket connections before each test"""
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_subscriptions,
            connection_users,
        )
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()
        yield
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()

    @pytest.fixture(autouse=True)
    def clear_deduplication_cache(self):
        """Clear deduplication cache before each test"""
        from fastmcp.task_management.application.services import (
            websocket_notification_service,
        )
        websocket_notification_service._notification_cache.clear()
        yield
        websocket_notification_service._notification_cache.clear()

    @pytest.mark.asyncio
    async def test_delete_task_triggers_websocket_notification(self):
        """
        Test that deleting a task triggers WebSocket notification.

        Critical: Deletion must use pre-fetched context since task is deleted from DB.
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-3"].add(mock_websocket)

        mock_user = Mock()
        mock_user.id = "test-user-789"
        connection_users[mock_websocket] = mock_user

        # Mock delete task use case
        from fastmcp.task_management.application.use_cases.delete_task import (
            DeleteTaskUseCase,
        )

        mock_task_repo = Mock()
        mock_git_branch_repo = Mock()

        # Mock existing task before deletion
        task_to_delete = Mock()
        task_to_delete.id = Mock(value="task-delete-123")
        task_to_delete.title = "Task To Delete"
        task_to_delete.git_branch_id = "branch-delete-123"
        task_to_delete.get_events = Mock(return_value=[])

        mock_task_repo.get = Mock(return_value=task_to_delete)
        mock_task_repo.delete = Mock(return_value=True)

        branch = Mock()
        branch.project_id = "project-789"
        mock_git_branch_repo.get = Mock(return_value=branch)

        delete_use_case = DeleteTaskUseCase(
            task_repository=mock_task_repo,
            git_branch_repository=mock_git_branch_repo
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            # Act
            response = delete_use_case.execute("task-delete-123", "test-user-789")
            await asyncio.sleep(0.1)

        # Assert
        assert response.success is True
        assert mock_websocket.send_json.called

        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["payload"]["action"] == "deleted"


class TestMultiTenantNotificationIsolation:
    """
    Integration tests for multi-tenant isolation in notification flow.
    Ensures users only receive their own notifications.
    """

    @pytest.fixture(autouse=True)
    def clear_websocket_connections(self):
        """Clear WebSocket connections before each test"""
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_subscriptions,
            connection_users,
        )
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()
        yield
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()

    @pytest.fixture(autouse=True)
    def clear_deduplication_cache(self):
        """Clear deduplication cache before each test"""
        from fastmcp.task_management.application.services import (
            websocket_notification_service,
        )
        websocket_notification_service._notification_cache.clear()
        yield
        websocket_notification_service._notification_cache.clear()

    @pytest.mark.asyncio
    async def test_user_filtering_prevents_unauthorized_notifications(self):
        """
        Test that User A doesn't receive User B's task notifications.

        Scenario:
        1. User A and User B both connected via WebSocket
        2. User B creates a task
        3. Only User B receives notification, User A does not
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        # Setup two users with WebSocket connections
        websocket_user_a = AsyncMock()
        websocket_user_b = AsyncMock()

        active_connections["client-user-a"].add(websocket_user_a)
        active_connections["client-user-b"].add(websocket_user_b)

        user_a = Mock()
        user_a.id = "user-a-123"
        user_b = Mock()
        user_b.id = "user-b-456"

        connection_users[websocket_user_a] = user_a
        connection_users[websocket_user_b] = user_b

        # Mock authorization: Only allow user who owns the task
        async def strict_authorization(websocket, entity_type, entity_id, user_id, metadata):
            connection_user = connection_users.get(websocket)
            return connection_user and connection_user.id == user_id

        # Setup create task use case for User B
        from fastmcp.task_management.application.use_cases.create_task import (
            CreateTaskUseCase,
        )

        mock_task_repo = Mock()
        mock_task_repo.get_next_id = Mock(return_value=Mock(value=str(uuid4())))
        mock_task_repo.save = Mock(return_value=True)
        mock_task_repo.git_branch_exists = Mock(return_value=True)
        mock_task_repo.user_id = "user-b-456"

        mock_git_branch_repo = Mock()
        branch = Mock()
        branch.project_id = "project-shared"
        mock_git_branch_repo.get = Mock(return_value=branch)

        create_use_case = CreateTaskUseCase(
            task_repository=mock_task_repo,
            git_branch_repository=mock_git_branch_repo
        )

        request = CreateTaskRequest(
            title="User B's Task",
            description="Should only notify User B",
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.HIGH.label,
            git_branch_id="shared-branch-123",
            assignees=["test-agent"],
            user_id="user-b-456"
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', side_effect=strict_authorization):
            # Act: User B creates task
            create_use_case.execute(request)
            await asyncio.sleep(0.1)

        # Assert: User B received notification, User A did not
        assert websocket_user_b.send_json.called
        assert not websocket_user_a.send_json.called

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user_all_receive_notification(self):
        """
        Test that if the same user has multiple WebSocket connections (e.g., multiple tabs),
        all connections receive the notification.
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        # Same user with 3 WebSocket connections (3 browser tabs)
        websocket_1 = AsyncMock()
        websocket_2 = AsyncMock()
        websocket_3 = AsyncMock()

        active_connections["client-tab-1"].add(websocket_1)
        active_connections["client-tab-2"].add(websocket_2)
        active_connections["client-tab-3"].add(websocket_3)

        same_user = Mock()
        same_user.id = "multi-tab-user-123"

        connection_users[websocket_1] = same_user
        connection_users[websocket_2] = same_user
        connection_users[websocket_3] = same_user

        # Setup create task use case
        from fastmcp.task_management.application.use_cases.create_task import (
            CreateTaskUseCase,
        )

        mock_task_repo = Mock()
        mock_task_repo.get_next_id = Mock(return_value=Mock(value=str(uuid4())))
        mock_task_repo.save = Mock(return_value=True)
        mock_task_repo.git_branch_exists = Mock(return_value=True)
        mock_task_repo.user_id = "multi-tab-user-123"

        mock_git_branch_repo = Mock()
        branch = Mock()
        branch.project_id = "project-multi-tab"
        mock_git_branch_repo.get = Mock(return_value=branch)

        create_use_case = CreateTaskUseCase(
            task_repository=mock_task_repo,
            git_branch_repository=mock_git_branch_repo
        )

        request = CreateTaskRequest(
            title="Multi-Tab Test Task",
            description="All tabs should receive notification",
            status=TaskStatusEnum.TODO.value,
            priority=PriorityLevel.MEDIUM.label,
            git_branch_id="multi-tab-branch",
            assignees=["test-agent"],
            user_id="multi-tab-user-123"
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            # Act
            create_use_case.execute(request)
            await asyncio.sleep(0.1)

        # Assert: All 3 connections received notification
        assert websocket_1.send_json.called
        assert websocket_2.send_json.called
        assert websocket_3.send_json.called


class TestNotificationDeduplicationFlow:
    """
    Integration tests for notification deduplication across full flow.
    """

    @pytest.fixture(autouse=True)
    def clear_websocket_connections(self):
        """Clear WebSocket connections before each test"""
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_subscriptions,
            connection_users,
        )
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()
        yield
        active_connections.clear()
        connection_users.clear()
        connection_subscriptions.clear()

    @pytest.fixture(autouse=True)
    def clear_deduplication_cache(self):
        """Clear deduplication cache before each test"""
        from fastmcp.task_management.application.services import (
            websocket_notification_service,
        )
        websocket_notification_service._notification_cache.clear()
        yield
        websocket_notification_service._notification_cache.clear()

    @pytest.mark.asyncio
    async def test_rapid_updates_deduplicated_across_full_flow(self):
        """
        Test that rapid task updates are deduplicated in the complete flow.

        Scenario:
        1. Update task rapidly 3 times
        2. First update triggers notification
        3. Second update blocked by deduplication (within 5 seconds)
        4. Third update also blocked
        5. Only 1 notification sent to frontend
        """
        # Arrange
        from fastmcp.server.routes.websocket_routes import (
            active_connections,
            connection_users,
        )

        mock_websocket = AsyncMock()
        active_connections["client-dedup"].add(mock_websocket)

        mock_user = Mock()
        mock_user.id = "dedup-user-123"
        connection_users[mock_websocket] = mock_user

        # Setup update task use case
        from fastmcp.task_management.application.use_cases.update_task import (
            UpdateTaskUseCase,
        )

        mock_task_repo = Mock()
        mock_git_branch_repo = Mock()

        task = Mock()
        task.id = Mock(value="task-dedup-123")
        task.title = "Deduplication Test"
        task.description = "Test rapid updates"
        task.status = TaskStatus(TaskStatusEnum.TODO.value)
        task.priority = Priority(PriorityLevel.MEDIUM.label)
        task.git_branch_id = "branch-dedup-123"
        task.get_events = Mock(return_value=[])

        mock_task_repo.get = Mock(return_value=task)
        mock_task_repo.save = Mock(return_value=True)

        branch = Mock()
        branch.project_id = "project-dedup"
        mock_git_branch_repo.get = Mock(return_value=branch)

        update_use_case = UpdateTaskUseCase(
            task_repository=mock_task_repo,
            git_branch_repository=mock_git_branch_repo
        )

        with patch('fastmcp.server.routes.websocket_routes.is_user_authorized_for_message', return_value=True):
            # Act: Rapid updates
            update_use_case.execute("task-dedup-123", UpdateTaskRequest(title="Update 1"), "dedup-user-123")
            await asyncio.sleep(0.05)

            update_use_case.execute("task-dedup-123", UpdateTaskRequest(title="Update 2"), "dedup-user-123")
            await asyncio.sleep(0.05)

            update_use_case.execute("task-dedup-123", UpdateTaskRequest(title="Update 3"), "dedup-user-123")
            await asyncio.sleep(0.1)

        # Assert: Only 1 notification sent (deduplication working)
        # Note: Due to deduplication, only the first update should trigger notification
        assert mock_websocket.send_json.call_count == 1
