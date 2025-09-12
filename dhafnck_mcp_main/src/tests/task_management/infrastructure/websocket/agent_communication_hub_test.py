"""Test agent communication hub"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from fastmcp.task_management.infrastructure.websocket.agent_communication_hub import (
    AgentCommunicationHub,
    WebSocketMessage,
    MessageType,
    AgentConnection
)
from fastmcp.task_management.application.services.real_time_status_tracker import (
    RealTimeStatusTracker
)


class TestWebSocketMessage:
    """Test WebSocket message value object"""

    def test_message_creation(self):
        """Test creating WebSocket message"""
        msg = WebSocketMessage(
            id="msg-123",
            type=MessageType.STATUS_UPDATE,
            from_agent="agent-1",
            to_agents=["agent-2", "agent-3"],
            timestamp=datetime.now(timezone.utc),
            payload={"status": "busy"},
            requires_ack=True,
            correlation_id="corr-456"
        )
        
        assert msg.id == "msg-123"
        assert msg.type == MessageType.STATUS_UPDATE
        assert msg.from_agent == "agent-1"
        assert len(msg.to_agents) == 2
        assert msg.payload["status"] == "busy"
        assert msg.requires_ack
        assert msg.correlation_id == "corr-456"

    def test_to_json(self):
        """Test converting message to JSON"""
        timestamp = datetime.now(timezone.utc)
        msg = WebSocketMessage(
            id="msg-123",
            type=MessageType.DIRECT_MESSAGE,
            from_agent="agent-1",
            to_agents=["agent-2"],
            timestamp=timestamp,
            payload={"content": "Hello"}
        )
        
        json_str = msg.to_json()
        data = json.loads(json_str)
        
        assert data["id"] == "msg-123"
        assert data["type"] == "direct_message"
        assert data["from_agent"] == "agent-1"
        assert data["to_agents"] == ["agent-2"]
        assert data["timestamp"] == timestamp.isoformat()
        assert data["payload"]["content"] == "Hello"
        assert data["requires_ack"] is False

    def test_from_json(self):
        """Test creating message from JSON"""
        timestamp = datetime.now(timezone.utc)
        json_data = {
            "id": "msg-123",
            "type": "broadcast_message",
            "from_agent": "agent-1",
            "to_agents": [],
            "timestamp": timestamp.isoformat(),
            "payload": {"announcement": "System update"},
            "requires_ack": False,
            "correlation_id": None
        }
        
        json_str = json.dumps(json_data)
        msg = WebSocketMessage.from_json(json_str)
        
        assert msg.id == "msg-123"
        assert msg.type == MessageType.BROADCAST_MESSAGE
        assert msg.from_agent == "agent-1"
        assert msg.to_agents == []
        assert msg.payload["announcement"] == "System update"


class TestAgentConnection:
    """Test agent connection"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        ws.send_text = AsyncMock()
        return ws

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create test connection"""
        return AgentConnection(
            agent_id="agent-123",
            session_id="session-456",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc)
        )

    @pytest.mark.asyncio
    async def test_send_message(self, connection):
        """Test sending message through connection"""
        msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.STATUS_UPDATE,
            from_agent="hub",
            to_agents=["agent-123"],
            timestamp=datetime.now(timezone.utc),
            payload={"status": "active"}
        )
        
        result = await connection.send_message(msg)
        
        assert result is True
        connection.websocket.send_text.assert_called_once()
        call_args = connection.websocket.send_text.call_args[0][0]
        assert "status_update" in call_args

    @pytest.mark.asyncio
    async def test_send_message_disconnected(self, connection):
        """Test sending message when disconnected"""
        connection.websocket.client_state = WebSocketState.DISCONNECTED
        
        msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.HEARTBEAT,
            from_agent="hub",
            to_agents=["agent-123"],
            timestamp=datetime.now(timezone.utc),
            payload={}
        )
        
        result = await connection.send_message(msg)
        assert result is False

    def test_is_alive(self, connection):
        """Test checking if connection is alive"""
        assert connection.is_alive()
        
        # Old heartbeat
        connection.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=70)
        assert not connection.is_alive()
        
        # Custom timeout
        assert connection.is_alive(timeout_seconds=120)


class TestAgentCommunicationHub:
    """Test agent communication hub"""

    @pytest.fixture
    def status_tracker(self):
        """Create mock status tracker"""
        return AsyncMock(spec=RealTimeStatusTracker)

    @pytest.fixture
    async def hub(self, status_tracker):
        """Create communication hub"""
        hub = AgentCommunicationHub(
            status_tracker=status_tracker,
            heartbeat_interval=5,
            message_timeout=10
        )
        await hub.start()
        yield hub
        await hub.stop()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_hub_initialization(self, status_tracker):
        """Test hub initialization"""
        hub = AgentCommunicationHub(
            status_tracker=status_tracker,
            heartbeat_interval=30,
            message_timeout=30
        )
        
        assert hub.heartbeat_interval == 30
        assert hub.message_timeout == 30
        assert not hub._is_running
        assert len(hub.connections) == 0
        assert "global" in hub.channels

    @pytest.mark.asyncio
    async def test_start_stop(self, status_tracker):
        """Test starting and stopping hub"""
        hub = AgentCommunicationHub(status_tracker=status_tracker)
        
        # Start
        await hub.start()
        assert hub._is_running
        assert hub._heartbeat_task is not None
        assert hub._cleanup_task is not None
        
        # Start again (idempotent)
        await hub.start()
        assert hub._is_running
        
        # Stop
        await hub.stop()
        assert not hub._is_running

    @pytest.mark.asyncio
    async def test_connect_agent(self, hub, mock_websocket):
        """Test connecting an agent"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        # Verify connection created
        assert "agent-123" in hub.connections
        connection = hub.connections["agent-123"]
        assert connection.session_id == "session-456"
        assert connection.websocket == mock_websocket
        
        # Verify added to global channel
        assert "agent-123" in hub.channels["global"]
        
        # Verify welcome message sent
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_agent(self, hub, mock_websocket):
        """Test disconnecting an agent"""
        # Connect first
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        # Disconnect
        await hub.disconnect_agent("agent-123")
        
        # Verify disconnection
        assert "agent-123" not in hub.connections
        assert "agent-123" not in hub.channels["global"]
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, hub, mock_websocket):
        """Test sending message to agent"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        result = await hub.send_message(
            "agent-123",
            MessageType.STATUS_UPDATE,
            {"status": "ready"},
            requires_ack=True
        )
        
        assert result is True
        assert hub.metrics["messages_sent"] == 1
        
        # Verify message sent through WebSocket
        calls = mock_websocket.send_text.call_args_list
        assert len(calls) >= 2  # Welcome + actual message

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, hub):
        """Test sending message to disconnected agent"""
        result = await hub.send_message(
            "agent-999",
            MessageType.NOTIFICATION,
            {"note": "test"}
        )
        
        assert result is False
        assert hub.metrics["messages_sent"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_message(self, hub, mock_websocket):
        """Test broadcasting message"""
        # Connect multiple agents
        ws1 = Mock(spec=WebSocket)
        ws1.client_state = WebSocketState.CONNECTED
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        
        ws2 = Mock(spec=WebSocket)
        ws2.client_state = WebSocketState.CONNECTED
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()
        
        await hub.connect_agent("agent-1", "session-1", ws1)
        await hub.connect_agent("agent-2", "session-2", ws2)
        
        # Broadcast
        count = await hub.broadcast_message(
            MessageType.NOTIFICATION,
            {"announcement": "System update"},
            exclude=["agent-1"]
        )
        
        assert count == 1  # Only agent-2
        ws1.send_text.assert_called_once()  # Only welcome message
        assert ws2.send_text.call_count >= 2  # Welcome + broadcast

    @pytest.mark.asyncio
    async def test_channel_subscription(self, hub, mock_websocket):
        """Test channel subscription"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        # Subscribe to channel
        result = await hub.subscribe_to_channel("agent-123", "status")
        assert result is True
        assert "agent-123" in hub.channels["status"]
        assert "status" in hub.connections["agent-123"].subscriptions
        
        # Unsubscribe
        result = await hub.unsubscribe_from_channel("agent-123", "status")
        assert result is True
        assert "agent-123" not in hub.channels["status"]
        assert "status" not in hub.connections["agent-123"].subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, hub):
        """Test broadcasting to channel"""
        # Connect and subscribe agents
        ws1 = Mock(spec=WebSocket)
        ws1.client_state = WebSocketState.CONNECTED
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        
        ws2 = Mock(spec=WebSocket)
        ws2.client_state = WebSocketState.CONNECTED
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()
        
        await hub.connect_agent("agent-1", "session-1", ws1)
        await hub.connect_agent("agent-2", "session-2", ws2)
        
        await hub.subscribe_to_channel("agent-1", "coordination")
        await hub.subscribe_to_channel("agent-2", "coordination")
        
        # Broadcast to channel
        count = await hub.broadcast_to_channel(
            "coordination",
            MessageType.GROUP_MESSAGE,
            {"message": "Coordination update"},
            exclude=["agent-1"]
        )
        
        assert count == 1  # Only agent-2

    @pytest.mark.asyncio
    async def test_process_message(self, hub, mock_websocket):
        """Test processing incoming message"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        # Create message
        msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.STATUS_UPDATE,
            from_agent="agent-123",
            to_agents=[],
            timestamp=datetime.now(timezone.utc),
            payload={"status": "busy", "task": "processing"},
            requires_ack=True
        )
        
        # Process
        await hub.process_message("agent-123", msg.to_json())
        
        # Verify metrics updated
        assert hub.metrics["messages_received"] == 1
        
        # Verify heartbeat updated
        assert hub.connections["agent-123"].last_heartbeat > datetime.now(timezone.utc) - timedelta(seconds=1)

    @pytest.mark.asyncio
    async def test_handle_status_update(self, hub, status_tracker):
        """Test handling status update"""
        msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.STATUS_UPDATE,
            from_agent="agent-123",
            to_agents=[],
            timestamp=datetime.now(timezone.utc),
            payload={
                "status": "active",
                "current_task_id": "task-456",
                "current_activity": "Processing",
                "metadata": {"custom": "data"}
            }
        )
        
        await hub.handle_status_update("agent-123", msg)
        
        # Verify status tracker called
        status_tracker.update_agent_status.assert_called_once_with(
            "agent-123",
            "active",
            "task-456",
            "Processing",
            {"custom": "data"}
        )

    @pytest.mark.asyncio
    async def test_handle_acknowledgment(self, hub):
        """Test handling acknowledgment"""
        # Add pending ack
        original_msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.HEARTBEAT,
            from_agent="hub",
            to_agents=["agent-123"],
            timestamp=datetime.now(timezone.utc),
            payload={}
        )
        hub.pending_acks["msg-1"] = original_msg
        
        # Handle ack
        ack_msg = WebSocketMessage(
            id="ack-1",
            type=MessageType.ACK,
            from_agent="agent-123",
            to_agents=["hub"],
            timestamp=datetime.now(timezone.utc),
            payload={"ack_message_id": "msg-1"}
        )
        
        await hub.handle_acknowledgment(ack_msg)
        
        assert "msg-1" not in hub.pending_acks

    @pytest.mark.asyncio
    async def test_register_message_handler(self, hub):
        """Test registering custom message handler"""
        handler_called = False
        
        async def custom_handler(message):
            nonlocal handler_called
            handler_called = True
        
        hub.register_message_handler(MessageType.ALERT, custom_handler)
        
        # Call handlers
        msg = WebSocketMessage(
            id="msg-1",
            type=MessageType.ALERT,
            from_agent="agent-123",
            to_agents=[],
            timestamp=datetime.now(timezone.utc),
            payload={"alert": "test"}
        )
        
        await hub.call_message_handlers(MessageType.ALERT, msg)
        
        assert handler_called

    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, hub, mock_websocket):
        """Test heartbeat loop"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        # Wait for heartbeat
        await asyncio.sleep(0.1)
        
        # Should have sent heartbeats
        calls = mock_websocket.send_text.call_args_list
        heartbeat_sent = any("heartbeat" in str(call) for call in calls)
        assert heartbeat_sent

    @pytest.mark.asyncio
    async def test_cleanup_dead_connections(self, hub):
        """Test cleanup of dead connections"""
        # Create connection with old heartbeat
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        
        await hub.connect_agent("agent-123", "session-456", ws)
        
        # Make connection appear dead
        hub.connections["agent-123"].last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        # Run cleanup
        await hub._cleanup_loop()
        
        # Connection should be removed
        assert "agent-123" not in hub.connections

    @pytest.mark.asyncio
    async def test_handle_agent_connection_lifecycle(self, hub, mock_websocket):
        """Test full connection lifecycle"""
        # Mock receive messages
        messages = [
            WebSocketMessage(
                id="msg-1",
                type=MessageType.STATUS_UPDATE,
                from_agent="agent-123",
                to_agents=[],
                timestamp=datetime.now(timezone.utc),
                payload={"status": "ready"}
            ).to_json(),
            WebSocketMessage(
                id="msg-2",
                type=MessageType.HEARTBEAT,
                from_agent="agent-123",
                to_agents=[],
                timestamp=datetime.now(timezone.utc),
                payload={}
            ).to_json()
        ]
        
        mock_websocket.receive_text.side_effect = [
            messages[0],
            messages[1],
            asyncio.TimeoutError(),  # Trigger heartbeat
            Exception("WebSocket disconnected")  # End connection
        ]
        
        # Handle connection
        await hub.handle_agent_connection(mock_websocket, "agent-123", "session-456")
        
        # Verify connection was handled
        assert mock_websocket.accept.called
        assert hub.metrics["messages_received"] >= 2
        assert "agent-123" not in hub.connections  # Cleaned up

    def test_get_connection_status(self, hub):
        """Test getting connection status"""
        status = hub.get_connection_status()
        
        assert status["active_connections"] == 0
        assert status["agents"] == []
        assert "global" in status["channels"]
        assert status["pending_acks"] == 0
        assert "metrics" in status

    @pytest.mark.asyncio
    async def test_get_agent_info(self, hub, mock_websocket):
        """Test getting agent info"""
        await hub.connect_agent("agent-123", "session-456", mock_websocket)
        
        info = hub.get_agent_info("agent-123")
        
        assert info is not None
        assert info["agent_id"] == "agent-123"
        assert info["session_id"] == "session-456"
        assert info["is_alive"] is True
        assert "connected_at" in info
        assert "subscriptions" in info
        
        # Non-existent agent
        assert hub.get_agent_info("agent-999") is None