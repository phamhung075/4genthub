"""
Comprehensive Tests for WebSocket Routes (Infrastructure Layer)

Test Coverage:
- broadcast_data_change sends messages to connected clients
- Message format matches frontend v2.0 specification
- User authorization filters messages correctly
- Cascade data moved to payload.data for frontend
- WebSocket connection tracking
- Disconnected client cleanup
- Multi-tenant isolation (user_id filtering)

Infrastructure Layer focuses on:
- WebSocket connection management
- Message broadcasting mechanics
- Authorization enforcement
- Message formatting
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from fastmcp.auth.domain.entities.user import User

# Import the functions and data structures we're testing
from fastmcp.server.routes.websocket_routes import (
    WebSocketConnection,  # Updated: connection state dataclass
    broadcast_data_change,
    connections,  # Updated: unified connections dictionary
)


class TestBroadcastDataChange:
    """
    Test suite for broadcast_data_change function.
    Validates that broadcasts reach connected clients with correct format.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear global connection state before each test
        connections.clear()  # Updated: single unified connections dictionary
        yield
        # Cleanup after test
        connections.clear()  # Updated: single unified connections dictionary

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_connected_clients(self):
        """Test that broadcast_data_change sends messages to connected WebSocket clients"""
        # Arrange: Setup mock WebSocket clients
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        # Setup mock users for authorization
        user1 = Mock(spec=User)
        user1.id = "user-123"
        user1.email = "user1@test.com"

        # Add clients to unified connections dictionary (updated architecture)
        connections[mock_websocket1] = WebSocketConnection(
            websocket=mock_websocket1,
            user=user1,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[mock_websocket2] = WebSocketConnection(
            websocket=mock_websocket2,
            user=user1,
            client_id="client-2",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        # Mock authorization to always return True for this test
        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act: Broadcast a task creation event
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"title": "Test Task"},
                metadata={"git_branch_id": "branch-123"},
            )

        # Assert: Both clients received the message
        assert mock_websocket1.send_json.called, "WebSocket 1 should receive message"
        assert mock_websocket2.send_json.called, "WebSocket 2 should receive message"

        # Verify message was sent to both clients
        assert mock_websocket1.send_json.call_count == 1
        assert mock_websocket2.send_json.call_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_message_format_matches_v2_spec(self):
        """Test that broadcast message follows v2.0 format specification"""
        # Arrange
        mock_websocket = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add client to unified connections dictionary (updated architecture)
        connections[mock_websocket] = WebSocketConnection(
            websocket=mock_websocket,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"title": "Test Task", "status": "todo"},
                metadata={"git_branch_id": "branch-123", "project_id": "project-123"},
            )

        # Assert: Message structure matches v2.0 spec
        assert mock_websocket.send_json.called
        sent_message = mock_websocket.send_json.call_args[0][0]

        # Validate v2.0 structure
        assert "id" in sent_message, "Message should have unique ID"
        assert "version" in sent_message, "Message should have version"
        assert sent_message["version"] == "2.0", "Version should be 2.0"
        assert "type" in sent_message, "Message should have type"
        assert sent_message["type"] == "update", "Type should be 'update'"
        assert "timestamp" in sent_message, "Message should have timestamp"
        assert "sequence" in sent_message, "Message should have sequence number"

        # Validate payload structure
        assert "payload" in sent_message
        payload = sent_message["payload"]
        assert "entity" in payload
        assert payload["entity"] == "task"
        assert "action" in payload
        assert payload["action"] == "created"
        assert "data" in payload
        assert "primary" in payload["data"]

        # Validate metadata
        assert "metadata" in sent_message
        metadata = sent_message["metadata"]
        assert metadata["source"] == "user"  # Source is 'user' when userId is present
        assert metadata["userId"] == "user-123"
        assert metadata["entity_type"] == "task"
        assert metadata["entity_id"] == "task-123"
        assert metadata["event_type"] == "created"

    @pytest.mark.asyncio
    async def test_broadcast_moves_cascade_data_to_payload(self):
        """Test that cascade data is moved from metadata to payload.data for frontend"""
        # Arrange
        mock_websocket = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add client to unified connections dictionary (updated architecture)
        connections[mock_websocket] = WebSocketConnection(
            websocket=mock_websocket,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        cascade_data = {
            "branches": [
                {
                    "id": "branch-123",
                    "task_count": 5,
                    "completed_tasks": 2,
                    "progress_percentage": 40.0,
                }
            ]
        }

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act: Send notification with cascade data in metadata
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"title": "Test Task"},
                metadata={"git_branch_id": "branch-123", "cascade": cascade_data},
            )

        # Assert: Cascade data moved to payload.data
        sent_message = mock_websocket.send_json.call_args[0][0]

        # Cascade data should be in payload.data (for frontend consumption)
        assert "cascade" in sent_message["payload"]["data"], (
            "Cascade data should be in payload.data for frontend"
        )
        assert sent_message["payload"]["data"]["cascade"] == cascade_data

        # Cascade data should NOT be in metadata (to avoid duplication)
        assert "cascade" not in sent_message["metadata"], (
            "Cascade data should be removed from metadata to avoid duplication"
        )

    @pytest.mark.asyncio
    async def test_broadcast_respects_authorization(self):
        """Test that only authorized users receive messages"""
        # Arrange: Setup two clients with different users
        mock_websocket_authorized = AsyncMock()
        mock_websocket_unauthorized = AsyncMock()

        # User who owns the task
        authorized_user = Mock(spec=User)
        authorized_user.id = "user-123"

        # Different user who doesn't own the task
        unauthorized_user = Mock(spec=User)
        unauthorized_user.id = "user-456"

        # Add clients to unified connections dictionary (updated architecture)
        connections[mock_websocket_authorized] = WebSocketConnection(
            websocket=mock_websocket_authorized,
            user=authorized_user,
            client_id="client-authorized",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[mock_websocket_unauthorized] = WebSocketConnection(
            websocket=mock_websocket_unauthorized,
            user=unauthorized_user,
            client_id="client-unauthorized",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        # Mock authorization to return True only for authorized user
        async def mock_authorization(
            websocket, entity_type, entity_id, user_id, metadata
        ):
            connection = connections.get(
                websocket
            )  # Updated: use unified connections dict
            return connection and connection.user.id == user_id

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            side_effect=mock_authorization,
        ):
            # Act: Broadcast task event for user-123
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",  # Owner is user-123
                data={"title": "Test Task"},
                metadata={"git_branch_id": "branch-123"},
            )

        # Assert: Only authorized user received the data message
        assert mock_websocket_authorized.send_json.called, (
            "Authorized user should receive message"
        )

        # Unauthorized user receives error message, not data message (updated expectation)
        assert mock_websocket_unauthorized.send_json.called, (
            "Unauthorized user should receive error notification"
        )

        # Verify unauthorized user got error message, not data
        unauthorized_message = mock_websocket_unauthorized.send_json.call_args[0][0]
        assert unauthorized_message["type"] == "error", (
            "Unauthorized user should receive error type message"
        )
        assert (
            "authorization" in unauthorized_message["payload"]["entity"]
            or unauthorized_message["payload"]["entity"] == "system"
        ), "Unauthorized message should be system/authorization error"

    @pytest.mark.asyncio
    async def test_broadcast_cleans_up_disconnected_clients(self):
        """Test that disconnected clients are removed from active connections"""
        # Arrange: Setup client that will fail to receive message
        mock_websocket_disconnected = AsyncMock()
        mock_websocket_disconnected.send_json.side_effect = Exception("Connection lost")

        mock_websocket_active = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add clients to unified connections dictionary (updated architecture)
        connections[mock_websocket_disconnected] = WebSocketConnection(
            websocket=mock_websocket_disconnected,
            user=user,
            client_id="client-disconnected",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[mock_websocket_active] = WebSocketConnection(
            websocket=mock_websocket_active,
            user=user,
            client_id="client-active",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act: Broadcast message
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"title": "Test Task"},
            )

        # Assert: Disconnected client removed from tracking (updated architecture)
        assert mock_websocket_disconnected not in connections, (
            "Disconnected client should be removed from connections dictionary"
        )

        # Active client should still be tracked (updated architecture)
        assert mock_websocket_active in connections, (
            "Active client should still be in connections dictionary"
        )

    @pytest.mark.asyncio
    async def test_broadcast_handles_empty_connections(self):
        """Test that broadcast works gracefully with no connected clients"""
        # Arrange: No clients connected (updated architecture)
        assert len(connections) == 0

        # Act: Broadcast message (should not raise error)
        try:
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"title": "Test Task"},
            )
            success = True
        except Exception:
            success = False

        # Assert: No error raised
        assert success, "Broadcast should handle empty connections gracefully"


class TestMessageFormatting:
    """
    Test suite for message formatting.
    Validates that messages match frontend expectations exactly.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        connections.clear()  # Updated: single unified connections dictionary
        yield
        connections.clear()  # Updated: single unified connections dictionary

    @pytest.mark.asyncio
    async def test_message_includes_all_required_fields(self):
        """Test that every broadcast message includes all required fields"""
        # Arrange
        mock_websocket = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add client to unified connections dictionary (updated architecture)
        connections[mock_websocket] = WebSocketConnection(
            websocket=mock_websocket,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act
            await broadcast_data_change(
                event_type="updated",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"status": "in_progress"},
                metadata={"git_branch_id": "branch-123"},
            )

        # Assert: All required fields present
        sent_message = mock_websocket.send_json.call_args[0][0]

        required_top_level_fields = [
            "id",
            "version",
            "type",
            "timestamp",
            "sequence",
            "payload",
            "metadata",
        ]
        for field in required_top_level_fields:
            assert field in sent_message, f"Message must include '{field}' field"

        required_payload_fields = ["entity", "action", "data"]
        for field in required_payload_fields:
            assert field in sent_message["payload"], (
                f"Payload must include '{field}' field"
            )

        required_metadata_fields = [
            "source",
            "userId",
            "entity_type",
            "entity_id",
            "event_type",
        ]
        for field in required_metadata_fields:
            assert field in sent_message["metadata"], (
                f"Metadata must include '{field}' field"
            )

    @pytest.mark.asyncio
    async def test_message_timestamp_is_iso_8601_format(self):
        """Test that timestamp is in ISO 8601 format"""
        # Arrange
        mock_websocket = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add client to unified connections dictionary (updated architecture)
        connections[mock_websocket] = WebSocketConnection(
            websocket=mock_websocket,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act
            await broadcast_data_change(
                event_type="deleted",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
            )

        # Assert: Timestamp is ISO 8601
        sent_message = mock_websocket.send_json.call_args[0][0]
        timestamp = sent_message["timestamp"]

        # Should be parseable as ISO 8601
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            is_valid_iso = True
        except ValueError:
            is_valid_iso = False

        assert is_valid_iso, "Timestamp must be valid ISO 8601 format"

    @pytest.mark.asyncio
    async def test_message_includes_entity_and_event_info(self):
        """Test that message includes entity and event type information"""
        # Arrange
        mock_websocket = AsyncMock()

        user = Mock(spec=User)
        user.id = "user-123"

        # Add client to unified connections dictionary (updated architecture)
        connections[mock_websocket] = WebSocketConnection(
            websocket=mock_websocket,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act
            await broadcast_data_change(
                event_type="completed",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"completion_summary": "Done"},
            )

        # Assert: Entity and event info present
        sent_message = mock_websocket.send_json.call_args[0][0]

        assert sent_message["payload"]["entity"] == "task"
        assert sent_message["payload"]["action"] == "completed"
        assert sent_message["metadata"]["entity_type"] == "task"
        assert sent_message["metadata"]["entity_id"] == "task-123"
        assert sent_message["metadata"]["event_type"] == "completed"


class TestMultiTenantIsolation:
    """
    Test suite for multi-tenant isolation.
    Validates that users only receive notifications for their own data.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        connections.clear()  # Updated: single unified connections dictionary
        yield
        connections.clear()  # Updated: single unified connections dictionary

    @pytest.mark.asyncio
    async def test_users_only_receive_their_own_notifications(self):
        """Test that User A doesn't receive User B's notifications"""
        # Arrange: Setup two users with separate WebSocket connections
        websocket_user_a = AsyncMock()
        websocket_user_b = AsyncMock()

        user_a = Mock(spec=User)
        user_a.id = "user-a"
        user_b = Mock(spec=User)
        user_b.id = "user-b"

        # Add clients to unified connections dictionary (updated architecture)
        connections[websocket_user_a] = WebSocketConnection(
            websocket=websocket_user_a,
            user=user_a,
            client_id="client-a",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[websocket_user_b] = WebSocketConnection(
            websocket=websocket_user_b,
            user=user_b,
            client_id="client-b",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        # Mock authorization to only allow matching user IDs
        async def strict_authorization(
            websocket, entity_type, entity_id, user_id, metadata
        ):
            connection = connections.get(
                websocket
            )  # Updated: use unified connections dict
            return connection and connection.user.id == user_id

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            side_effect=strict_authorization,
        ):
            # Act: Broadcast User A's task creation
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-a",
                user_id="user-a",  # This is User A's task
                data={"title": "User A's Task"},
            )

        # Assert: User A received data, User B received error (updated expectation)
        assert websocket_user_a.send_json.called, (
            "User A should receive their own notification"
        )
        assert websocket_user_b.send_json.called, (
            "User B should receive error notification"
        )

        # Verify User B got error message, not data
        user_b_message = websocket_user_b.send_json.call_args[0][0]
        assert user_b_message["type"] == "error", (
            "User B should receive error type message"
        )

        # Reset mocks for next test
        websocket_user_a.send_json.reset_mock()
        websocket_user_b.send_json.reset_mock()

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            side_effect=strict_authorization,
        ):
            # Act: Broadcast User B's task creation
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id="task-b",
                user_id="user-b",  # This is User B's task
                data={"title": "User B's Task"},
            )

        # Assert: User B received data, User A received error (updated expectation)
        assert websocket_user_a.send_json.called, (
            "User A should receive error notification"
        )
        assert websocket_user_b.send_json.called, (
            "User B should receive their own notification"
        )

        # Verify User A got error message, not data
        user_a_message = websocket_user_a.send_json.call_args[0][0]
        assert user_a_message["type"] == "error", (
            "User A should receive error type message"
        )

    @pytest.mark.asyncio
    async def test_same_user_multiple_connections_all_receive_notification(self):
        """Test that same user with multiple connections receives notification on all"""
        # Arrange: Same user with 3 different WebSocket connections
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        websocket3 = AsyncMock()

        # Same user for all connections
        user = Mock(spec=User)
        user.id = "user-123"

        # Add clients to unified connections dictionary (updated architecture)
        connections[websocket1] = WebSocketConnection(
            websocket=websocket1,
            user=user,
            client_id="client-1",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[websocket2] = WebSocketConnection(
            websocket=websocket2,
            user=user,
            client_id="client-2",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )
        connections[websocket3] = WebSocketConnection(
            websocket=websocket3,
            user=user,
            client_id="client-3",
            subscription={"scope": "all"},
            connected_at=datetime.now(),
            last_activity=datetime.now(),
        )

        with patch(
            "fastmcp.server.routes.websocket_routes.is_user_authorized_for_message",
            return_value=True,
        ):
            # Act: Broadcast notification for this user
            await broadcast_data_change(
                event_type="updated",
                entity_type="task",
                entity_id="task-123",
                user_id="user-123",
                data={"status": "in_progress"},
            )

        # Assert: All 3 connections received the notification
        assert websocket1.send_json.called, "Connection 1 should receive notification"
        assert websocket2.send_json.called, "Connection 2 should receive notification"
        assert websocket3.send_json.called, "Connection 3 should receive notification"
