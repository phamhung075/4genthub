"""
End-to-End Tests for WebSocket Notification Reliability

Critical tests addressing user's reliability issues:
"need test data is correct update on task create, update, delete because some time i no see it not trigger"
"need TDD correct model data websocket send to frontend, notification is trigger only by websocket, not by API"

Tests complete flow:
1. Backend operation (task create/update/delete)
2. WebSocket notification triggered
3. Frontend receives notification
4. Data model correct (TypeScript interface)

Following DDD Architecture - Layer by Layer
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastmcp.auth.domain.entities.user import User

# Import WebSocket infrastructure
from fastmcp.server.routes.websocket_routes import active_connections, connection_users
from fastmcp.task_management.application.dtos.task.create_task_request import (
    CreateTaskRequest,
)
from fastmcp.task_management.application.dtos.task.update_task_request import (
    UpdateTaskRequest,
)

# Import application layer
from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade,
)

logger = logging.getLogger(__name__)


class MockWebSocketConnection:
    """Mock WebSocket connection that mimics frontend behavior"""

    def __init__(self, user_id: str, user_email: str):
        self.user_id = user_id
        self.user_email = user_email
        self.received_messages: list[dict[str, Any]] = []
        self.connected = True

    async def send_json(self, message: dict[str, Any]):
        """Mock sending JSON message - just store it"""
        if self.connected:
            self.received_messages.append(message)
            logger.info(
                f"✅ Mock WebSocket received message: {message['type']} - {message['payload']['action']}"
            )
        else:
            raise Exception("WebSocket not connected")

    def get_messages_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get messages filtered by event type"""
        return [
            msg
            for msg in self.received_messages
            if msg["payload"]["action"] == event_type
        ]

    def clear_messages(self):
        """Clear received messages"""
        self.received_messages.clear()


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def user_id():
    """Generate test user ID"""
    return str(uuid4())


@pytest.fixture
def mock_auth(user_id):
    """Mock authentication context"""
    mock_auth_info = {
        "user_id": user_id,
        "email": "test@example.com",
        "sub": user_id,
        "realm_roles": ["admin", "user"],
        "resource_access": {},
    }

    with (
        patch(
            "fastmcp.auth.middleware.request_context_middleware.get_current_auth_info",
            return_value=mock_auth_info,
        ),
        patch(
            "fastmcp.auth.middleware.request_context_middleware.is_authenticated",
            return_value=True,
        ),
    ):
        yield mock_auth_info


@pytest.fixture
def user(user_id):
    """Create test user"""
    return User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        password_hash="test_hash",
    )


@pytest.fixture
def task_facade(user_id, mock_auth):
    """Create Task Application Facade"""
    return TaskApplicationFacade(user_id=user_id)


@pytest.fixture
def mock_websocket(user_id, user):
    """Create mock WebSocket connection and register it in global state"""
    # Create mock WebSocket connection (mimics frontend)
    mock_ws = MockWebSocketConnection(user_id, user.email)

    # Register mock WebSocket in global state (simulates connected frontend)
    client_id = f"user_{user_id}_test"
    active_connections[client_id].add(mock_ws)
    connection_users[mock_ws] = user

    logger.info(f"🔧 E2E Test Setup: Mock WebSocket registered for user {user_id}")

    yield mock_ws

    # Cleanup: Remove mock WebSocket from global state
    active_connections[client_id].discard(mock_ws)
    if not active_connections[client_id]:
        del active_connections[client_id]

    if mock_ws in connection_users:
        del connection_users[mock_ws]

    logger.info("🧹 E2E Test Teardown: Cleaned up mock WebSocket")


# ============================================================================
# E2E TESTS - Critical Reliability Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_task_create_notification_reaches_frontend(
    task_facade, mock_websocket, user_id
):
    """
    E2E Test 1: Verify task creation notification reaches frontend reliably.

    User Issue: "some time i no see it not trigger"

    Success Criteria:
    ✅ Notification sent by backend
    ✅ Notification received by mock WebSocket (frontend)
    ✅ Data model matches TypeScript interface
    ✅ All required fields present
    """
    # Arrange: Create task request
    git_branch_id = str(uuid4())
    request = CreateTaskRequest(
        title="E2E Reliability Test - Create",
        description="Testing notification reliability",
        git_branch_id=git_branch_id,
        assignees=["agent-1"],
        status="todo",
        priority="high",
        user_id=user_id,
    )

    mock_websocket.clear_messages()

    # Act: Create task via Facade (simulates API call)
    logger.info("🎬 E2E TEST 1: Creating task to test notification...")
    response = task_facade.create_task(request, user_id, session=None)

    # Allow async event loop to process notification
    await asyncio.sleep(0.2)

    # Assert 1: Task created successfully
    assert response.success, f"Task creation failed: {response.error}"

    # Assert 2: Notification received by frontend
    create_notifications = mock_websocket.get_messages_by_type("created")

    assert len(create_notifications) > 0, (
        f"❌ RELIABILITY ISSUE: NO NOTIFICATION RECEIVED! "
        f"This is the 'some time i no see it not trigger' problem. "
        f"Messages received: {[msg['payload']['action'] for msg in mock_websocket.received_messages]}"
    )

    notification = create_notifications[0]

    # Assert 3: WebSocket v2.0 message format (TypeScript interface)
    assert notification["version"] == "2.0", f"Wrong version: {notification['version']}"
    assert notification["type"] == "update", f"Wrong type: {notification['type']}"
    assert "timestamp" in notification, "Missing timestamp"

    # Verify timestamp is valid ISO 8601
    try:
        datetime.fromisoformat(notification["timestamp"].replace("Z", "+00:00"))
    except ValueError as e:
        pytest.fail(
            f"Invalid timestamp format: {notification['timestamp']}, error: {e}"
        )

    # Assert 4: Payload structure (TypeScript interface)
    payload = notification["payload"]
    assert payload["entity"] == "task", f"Wrong entity: {payload['entity']}"
    assert payload["action"] == "created", f"Wrong action: {payload['action']}"
    assert "data" in payload, "Missing data in payload"
    assert "primary" in payload["data"], "Missing primary in payload.data"

    # Assert 5: Task data complete
    task_data = payload["data"]["primary"]
    assert "id" in task_data, "Missing task ID"
    assert "title" in task_data, "Missing title"
    assert (
        task_data["title"] == request.title
    ), f"Title mismatch: expected '{request.title}', got '{task_data['title']}'"
    assert "status" in task_data, "Missing status"
    assert "priority" in task_data, "Missing priority"

    logger.info(
        "✅ E2E TEST 1 PASSED: Task create notification reached frontend reliably"
    )


@pytest.mark.asyncio
async def test_task_update_notification_reaches_frontend(
    task_facade, mock_websocket, user_id
):
    """
    E2E Test 2: Verify task update notification reaches frontend reliably.

    User Issue: "need test data is correct update on task create, update, delete"

    Success Criteria:
    ✅ Update notification sent and received
    ✅ Updated data correct in notification
    ✅ No stale data sent to frontend
    """
    # Arrange: Create task first
    git_branch_id = str(uuid4())
    create_request = CreateTaskRequest(
        title="E2E Update Test Task",
        description="Testing update notifications",
        git_branch_id=git_branch_id,
        assignees=["agent-1"],
        user_id=user_id,
    )

    create_response = task_facade.create_task(create_request, user_id, session=None)
    assert create_response.success, "Task creation failed"
    task_id = create_response.task.id

    await asyncio.sleep(0.2)
    mock_websocket.clear_messages()  # Clear create notification

    # Act: Update task
    logger.info("🎬 E2E TEST 2: Updating task to test notification...")
    update_request = UpdateTaskRequest(
        title="UPDATED - E2E Test Task", status="in_progress"
    )

    update_response = task_facade.update_task(
        task_id, update_request, user_id, session=None
    )

    await asyncio.sleep(0.2)

    # Assert 1: Update successful
    assert update_response.success, f"Task update failed: {update_response.error}"

    # Assert 2: Update notification received
    update_notifications = mock_websocket.get_messages_by_type("updated")

    assert len(update_notifications) > 0, (
        f"❌ RELIABILITY ISSUE: NO UPDATE NOTIFICATION! "
        f"Messages: {[msg['payload']['action'] for msg in mock_websocket.received_messages]}"
    )

    notification = update_notifications[0]

    # Assert 3: Updated data correct (no stale data)
    task_data = notification["payload"]["data"]["primary"]
    assert (
        task_data["title"] == "UPDATED - E2E Test Task"
    ), f"❌ STALE DATA: Title not updated! Expected 'UPDATED - E2E Test Task', got '{task_data['title']}'"

    # Status can be in different formats depending on serialization
    status_str = str(task_data.get("status", ""))
    assert (
        "in_progress" in status_str.lower() or "in progress" in status_str.lower()
    ), f"❌ STALE DATA: Status not updated! Got: {task_data.get('status')}"

    logger.info(
        "✅ E2E TEST 2 PASSED: Task update notification with correct data reached frontend"
    )


@pytest.mark.asyncio
async def test_task_delete_notification_reaches_frontend(
    task_facade, mock_websocket, user_id
):
    """
    E2E Test 3: Verify task delete notification reaches frontend reliably.

    User Issue: "need test data is correct update on task create, update, delete"

    Success Criteria:
    ✅ Delete notification sent and received
    ✅ Task ID included for frontend to remove from UI
    ✅ Notification triggered only by WebSocket, not API
    """
    # Arrange: Create task first
    git_branch_id = str(uuid4())
    create_request = CreateTaskRequest(
        title="E2E Delete Test Task",
        description="Testing delete notifications",
        git_branch_id=git_branch_id,
        assignees=["agent-1"],
        user_id=user_id,
    )

    create_response = task_facade.create_task(create_request, user_id, session=None)
    assert create_response.success, "Task creation failed"
    task_id = create_response.task.id

    await asyncio.sleep(0.2)
    mock_websocket.clear_messages()  # Clear create notification

    # Act: Delete task
    logger.info("🎬 E2E TEST 3: Deleting task to test notification...")
    delete_response = task_facade.delete_task(task_id, user_id, session=None)

    await asyncio.sleep(0.2)

    # Assert 1: Delete successful
    assert delete_response.success, f"Task deletion failed: {delete_response.error}"

    # Assert 2: API response does NOT contain notification data (WebSocket only requirement)
    response_dict = (
        delete_response.__dict__ if hasattr(delete_response, "__dict__") else {}
    )
    assert (
        "notification_sent" not in response_dict
    ), "❌ VIOLATION: API response contains notification metadata! Should be WebSocket only"
    assert (
        "websocket_message" not in response_dict
    ), "❌ VIOLATION: API response contains WebSocket data! Should be separate"

    # Assert 3: Delete notification received via WebSocket (separate from API)
    delete_notifications = mock_websocket.get_messages_by_type("deleted")

    assert len(delete_notifications) > 0, (
        f"❌ RELIABILITY ISSUE: NO DELETE NOTIFICATION! "
        f"Messages: {[msg['payload']['action'] for msg in mock_websocket.received_messages]}"
    )

    notification = delete_notifications[0]

    # Assert 4: Deleted task ID included (for frontend to remove from UI)
    task_data = notification["payload"]["data"]["primary"]
    assert "id" in task_data, "Missing task ID in delete notification"
    assert (
        task_data["id"] == task_id
    ), f"Task ID mismatch: expected '{task_id}', got '{task_data['id']}'"

    logger.info(
        "✅ E2E TEST 3 PASSED: Task delete notification via WebSocket only, API response clean"
    )


# ============================================================================
# TEST EXECUTION SUMMARY
# ============================================================================
"""
Test Coverage Summary:

1. ✅ Task Create Notification - Verifies create triggers notification reliably
2. ✅ Task Update Notification - Verifies update triggers notification with correct data
3. ✅ Task Delete Notification - Verifies delete triggers notification, WebSocket only

User Requirements Met:
✅ "need test data is correct update on task create, update, delete" - Verified
✅ "because some time i no see it not trigger" - Reliability issues will be caught
✅ "notification is trigger only by websocket, not by API" - Verified delete response clean
✅ "need TDD correct model data websocket send to frontend" - TypeScript interface validated

Running Tests:
cd /home/daihu/__projects__/4genthub/agenthub_main
python -m pytest src/tests/e2e/test_websocket_notification_reliability.py -v -s

Expected Result:
All 3 tests pass, confirming WebSocket notifications reliably reach frontend.

If Tests Fail:
- Check WEBSOCKET_RELIABILITY_ANALYSIS.md for root causes
- Review websocket_routes.py:459 for authorization issues
- Check websocket_routes.py:454-456 for database error handling
- Verify message queuing and retry mechanism implemented

Next Steps if Tests Fail:
1. Implement message queuing with retry (HIGH PRIORITY)
2. Improve authorization error logging (HIGH PRIORITY)
3. Add connection state synchronization (MEDIUM PRIORITY)
4. Implement message persistence for missed notifications (MEDIUM PRIORITY)
"""
