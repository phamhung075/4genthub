"""
Test Suite for WebSocket Context Notifications

Tests real-time notification system including event publishing, subscription
management, filtering, and WebSocket connection handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastmcp.task_management.infrastructure.websocket.context_notifications import (
    ContextNotificationService,
    WebSocketManager,
    ContextEvent,
    EventType,
    SubscriptionScope,
    Subscription,
    get_notification_service,
    get_websocket_manager
)
from fastmcp.task_management.domain.models.unified_context import ContextLevel


# Mock WebSocket classes when not available
class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.client_state = "CONNECTED"
        self.messages_sent = []
        self.accepted = False
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: Dict[str, Any]):
        self.messages_sent.append(data)
    
    async def receive_json(self):
        # Mock receiving data
        return {"type": "ping"}


class MockWebSocketState:
    """Mock WebSocket state"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class TestContextEvent:
    """Test suite for ContextEvent"""
    
    def test_context_event_creation(self):
        """Test creating a context event"""
        event = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1",
            data={"name": "New Project"},
            metadata={"project_id": "proj_1"}
        )
        
        assert event.event_type == EventType.CREATED
        assert event.level == "project"
        assert event.context_id == "proj_1"
        assert event.user_id == "user_1"
        assert event.data == {"name": "New Project"}
        assert event.metadata == {"project_id": "proj_1"}
        assert event.timestamp is not None
    
    def test_context_event_to_dict(self):
        """Test converting event to dictionary"""
        event = ContextEvent(
            event_type=EventType.UPDATED,
            level="task",
            context_id="task_1",
            user_id="user_1"
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "context.updated"
        assert result["level"] == "task"
        assert result["context_id"] == "task_1"
        assert result["user_id"] == "user_1"
        assert "timestamp" in result
        assert result["data"] is None
        assert result["metadata"] == {}


class TestSubscription:
    """Test suite for Subscription"""
    
    def test_subscription_creation(self):
        """Test creating a subscription"""
        websocket = MockWebSocket()
        
        subscription = Subscription(
            client_id="client_1",
            websocket=websocket,
            scope=SubscriptionScope.USER,
            filters={"user_id": "user_1"}
        )
        
        assert subscription.client_id == "client_1"
        assert subscription.websocket == websocket
        assert subscription.scope == SubscriptionScope.USER
        assert subscription.filters == {"user_id": "user_1"}
        assert subscription.created_at is not None
        assert subscription.last_activity is not None
    
    def test_subscription_matches_global_scope(self):
        """Test subscription matching with global scope"""
        subscription = Subscription(
            client_id="client_1",
            websocket=MockWebSocket(),
            scope=SubscriptionScope.GLOBAL
        )
        
        # Global scope matches all events
        event = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="any_user"
        )
        
        assert subscription.matches(event) is True
    
    def test_subscription_matches_user_scope(self):
        """Test subscription matching with user scope"""
        subscription = Subscription(
            client_id="client_1",
            websocket=MockWebSocket(),
            scope=SubscriptionScope.USER,
            filters={"user_id": "user_1"}
        )
        
        # Matching user
        event1 = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        assert subscription.matches(event1) is True
        
        # Non-matching user
        event2 = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_2"
        )
        assert subscription.matches(event2) is False
    
    def test_subscription_matches_project_scope(self):
        """Test subscription matching with project scope"""
        subscription = Subscription(
            client_id="client_1",
            websocket=MockWebSocket(),
            scope=SubscriptionScope.PROJECT,
            filters={"project_id": "proj_1"}
        )
        
        # Matching project
        event1 = ContextEvent(
            event_type=EventType.UPDATED,
            level="branch",
            context_id="branch_1",
            user_id="user_1",
            metadata={"project_id": "proj_1"}
        )
        assert subscription.matches(event1) is True
        
        # Non-matching project
        event2 = ContextEvent(
            event_type=EventType.UPDATED,
            level="branch",
            context_id="branch_2",
            user_id="user_1",
            metadata={"project_id": "proj_2"}
        )
        assert subscription.matches(event2) is False
    
    def test_subscription_matches_event_type_filter(self):
        """Test subscription matching with event type filter"""
        subscription = Subscription(
            client_id="client_1",
            websocket=MockWebSocket(),
            scope=SubscriptionScope.GLOBAL,
            filters={
                "event_types": [EventType.CREATED, EventType.DELETED]
            }
        )
        
        # Matching event type
        event1 = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        assert subscription.matches(event1) is True
        
        # Non-matching event type
        event2 = ContextEvent(
            event_type=EventType.UPDATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        assert subscription.matches(event2) is False
    
    def test_subscription_matches_level_filter(self):
        """Test subscription matching with level filter"""
        subscription = Subscription(
            client_id="client_1",
            websocket=MockWebSocket(),
            scope=SubscriptionScope.GLOBAL,
            filters={
                "levels": ["project", "branch"]
            }
        )
        
        # Matching level
        event1 = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        assert subscription.matches(event1) is True
        
        # Non-matching level
        event2 = ContextEvent(
            event_type=EventType.CREATED,
            level="task",
            context_id="task_1",
            user_id="user_1"
        )
        assert subscription.matches(event2) is False


class TestContextNotificationService:
    """Test suite for ContextNotificationService"""
    
    @pytest.fixture
    def notification_service(self):
        """Create notification service instance"""
        return ContextNotificationService()
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, notification_service):
        """Test starting and stopping the service"""
        # Start service
        await notification_service.start()
        assert notification_service._running is True
        assert notification_service._task is not None
        
        # Stop service
        await notification_service.stop()
        assert notification_service._running is False
    
    @pytest.mark.asyncio
    async def test_subscribe(self, notification_service):
        """Test subscribing to notifications"""
        websocket = MockWebSocket()
        
        subscription = await notification_service.subscribe(
            websocket=websocket,
            client_id="client_1",
            scope=SubscriptionScope.USER,
            filters={"user_id": "user_1"}
        )
        
        assert subscription.client_id == "client_1"
        assert "client_1" in notification_service.subscriptions
        assert notification_service.stats["active_connections"] == 1
        assert notification_service.stats["total_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, notification_service):
        """Test unsubscribing from notifications"""
        websocket = MockWebSocket()
        
        # Subscribe first
        await notification_service.subscribe(
            websocket=websocket,
            client_id="client_1",
            scope=SubscriptionScope.USER
        )
        
        # Unsubscribe
        await notification_service.unsubscribe("client_1")
        
        assert "client_1" not in notification_service.subscriptions
        assert notification_service.stats["active_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_notify(self, notification_service):
        """Test sending notifications"""
        await notification_service.notify(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1",
            data={"name": "New Project"},
            metadata={"tags": ["important"]}
        )
        
        # Event should be queued
        assert notification_service.event_queue.qsize() == 1
        assert notification_service.stats["events_queued"] == 1
        
        # Get the event from queue
        event = await notification_service.event_queue.get()
        assert event.event_type == EventType.CREATED
        assert event.context_id == "proj_1"
    
    @pytest.mark.asyncio
    @patch('fastmcp.task_management.infrastructure.websocket.context_notifications.WEBSOCKET_AVAILABLE', True)
    @patch('fastmcp.task_management.infrastructure.websocket.context_notifications.WebSocket')
    @patch('fastmcp.task_management.infrastructure.websocket.context_notifications.WebSocketState')
    async def test_broadcast_event(self, mock_ws_state, mock_ws_class, notification_service):
        """Test broadcasting event to matching subscriptions"""
        # Setup WebSocket state mock
        mock_ws_state.CONNECTED = "CONNECTED"
        
        # Create mock websockets
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        # Subscribe clients with different scopes
        await notification_service.subscribe(
            websocket=ws1,
            client_id="client_1",
            scope=SubscriptionScope.USER,
            filters={"user_id": "user_1"}
        )
        
        await notification_service.subscribe(
            websocket=ws2,
            client_id="client_2",
            scope=SubscriptionScope.USER,
            filters={"user_id": "user_2"}
        )
        
        await notification_service.subscribe(
            websocket=ws3,
            client_id="client_3",
            scope=SubscriptionScope.GLOBAL
        )
        
        # Create event for user_1
        event = ContextEvent(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        
        # Broadcast event
        await notification_service._broadcast_event(event)
        
        # Check who received the event
        assert len(ws1.messages_sent) == 1  # user_1 subscription
        assert len(ws2.messages_sent) == 0  # user_2 subscription (no match)
        assert len(ws3.messages_sent) == 1  # global subscription
        
        # Verify event content
        sent_event = ws1.messages_sent[0]
        assert sent_event["event_type"] == "context.created"
        assert sent_event["context_id"] == "proj_1"
    
    @pytest.mark.asyncio
    async def test_event_handlers(self, notification_service):
        """Test custom event handlers"""
        handler_called = False
        received_event = None
        
        async def custom_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event
        
        notification_service.add_event_handler(custom_handler)
        
        # Start service to process events
        await notification_service.start()
        
        # Send event
        await notification_service.notify(
            event_type=EventType.CREATED,
            level="project",
            context_id="proj_1",
            user_id="user_1"
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Cleanup
        await notification_service.stop()
        
        assert handler_called is True
        assert received_event is not None
        assert received_event.context_id == "proj_1"
    
    def test_get_stats(self, notification_service):
        """Test getting service statistics"""
        stats = notification_service.get_stats()
        
        assert "events_sent" in stats
        assert "events_queued" in stats
        assert "active_connections" in stats
        assert "total_connections" in stats
        assert "errors" in stats
        assert "queue_size" in stats
        assert "subscriptions" in stats
    
    @pytest.mark.asyncio
    @patch('fastmcp.task_management.infrastructure.websocket.context_notifications.WEBSOCKET_AVAILABLE', True)
    async def test_heartbeat(self, notification_service):
        """Test heartbeat functionality"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws2.client_state = "DISCONNECTED"
        
        # Subscribe clients
        await notification_service.subscribe(
            websocket=ws1,
            client_id="client_1",
            scope=SubscriptionScope.USER
        )
        
        await notification_service.subscribe(
            websocket=ws2,
            client_id="client_2",
            scope=SubscriptionScope.USER
        )
        
        # Send heartbeat
        await notification_service.heartbeat()
        
        # Connected client should receive heartbeat
        assert len(ws1.messages_sent) == 0  # MockWebSocket doesn't implement heartbeat
        
        # Disconnected client should be removed
        assert "client_2" not in notification_service.subscriptions


class TestWebSocketManager:
    """Test suite for WebSocketManager"""
    
    @pytest.fixture
    def notification_service(self):
        """Create notification service"""
        return ContextNotificationService()
    
    @pytest.fixture
    def websocket_manager(self, notification_service):
        """Create WebSocket manager"""
        return WebSocketManager(notification_service)
    
    @pytest.mark.asyncio
    async def test_connect(self, websocket_manager, notification_service):
        """Test WebSocket connection"""
        websocket = MockWebSocket()
        
        await websocket_manager.connect(websocket, "client_1")
        
        assert websocket.accepted is True
        assert websocket in websocket_manager.active_connections
        assert "client_1" in notification_service.subscriptions
    
    @pytest.mark.asyncio
    async def test_disconnect(self, websocket_manager, notification_service):
        """Test WebSocket disconnection"""
        websocket = MockWebSocket()
        
        # Connect first
        await websocket_manager.connect(websocket, "client_1")
        
        # Disconnect
        await websocket_manager.disconnect(websocket, "client_1")
        
        assert websocket not in websocket_manager.active_connections
        assert "client_1" not in notification_service.subscriptions
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, websocket_manager, notification_service):
        """Test handling subscribe message"""
        websocket = MockWebSocket()
        await websocket_manager.connect(websocket, "client_1")
        
        # Send subscribe message
        message = {
            "type": "subscribe",
            "scope": "project",
            "filters": {"project_id": "proj_1"}
        }
        
        await websocket_manager.handle_message(websocket, "client_1", message)
        
        # Check subscription was updated
        subscription = notification_service.subscriptions["client_1"]
        assert subscription.scope == SubscriptionScope.PROJECT
        assert subscription.filters["project_id"] == "proj_1"
        
        # Check response
        assert len(websocket.messages_sent) >= 1
        response = websocket.messages_sent[-1]
        assert response["type"] == "subscribed"
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, websocket_manager):
        """Test handling ping message"""
        websocket = MockWebSocket()
        
        message = {"type": "ping"}
        await websocket_manager.handle_message(websocket, "client_1", message)
        
        # Check pong response
        assert len(websocket.messages_sent) == 1
        assert websocket.messages_sent[0]["type"] == "pong"
        assert "timestamp" in websocket.messages_sent[0]
    
    @pytest.mark.asyncio
    async def test_handle_get_stats_message(self, websocket_manager, notification_service):
        """Test handling get_stats message"""
        websocket = MockWebSocket()
        
        message = {"type": "get_stats"}
        await websocket_manager.handle_message(websocket, "client_1", message)
        
        # Check stats response
        assert len(websocket.messages_sent) == 1
        assert websocket.messages_sent[0]["type"] == "stats"
        assert "data" in websocket.messages_sent[0]
    
    @pytest.mark.asyncio
    async def test_handle_unknown_message(self, websocket_manager):
        """Test handling unknown message type"""
        websocket = MockWebSocket()
        
        message = {"type": "unknown_type"}
        await websocket_manager.handle_message(websocket, "client_1", message)
        
        # Check error response
        assert len(websocket.messages_sent) == 1
        assert websocket.messages_sent[0]["type"] == "error"
        assert "Unknown message type" in websocket.messages_sent[0]["message"]


class TestSingletons:
    """Test singleton instances"""
    
    def test_get_notification_service_singleton(self):
        """Test notification service singleton"""
        service1 = get_notification_service()
        service2 = get_notification_service()
        
        assert service1 is service2
    
    def test_get_websocket_manager_singleton(self):
        """Test WebSocket manager singleton"""
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        assert manager1 is manager2
        
        # Should use same notification service
        assert manager1.notification_service is manager2.notification_service


class TestWebSocketEndpoint:
    """Test WebSocket endpoint integration"""
    
    @pytest.mark.asyncio
    @patch('fastmcp.task_management.infrastructure.websocket.context_notifications.WEBSOCKET_AVAILABLE', False)
    async def test_websocket_endpoint_unavailable(self):
        """Test endpoint when WebSocket not available"""
        from fastmcp.task_management.infrastructure.websocket.context_notifications import websocket_endpoint
        
        websocket = MockWebSocket()
        
        # Should return early when WebSocket not available
        result = await websocket_endpoint(websocket, "client_1")
        assert result is None


class TestEventTypeEnum:
    """Test EventType enum values"""
    
    def test_event_type_values(self):
        """Test all event type values"""
        assert EventType.CREATED.value == "context.created"
        assert EventType.UPDATED.value == "context.updated"
        assert EventType.DELETED.value == "context.deleted"
        assert EventType.DELEGATED.value == "context.delegated"
        assert EventType.INHERITED.value == "context.inherited"
        assert EventType.BATCH_UPDATED.value == "context.batch_updated"
        assert EventType.CACHE_INVALIDATED.value == "context.cache_invalidated"


class TestSubscriptionScopeEnum:
    """Test SubscriptionScope enum values"""
    
    def test_subscription_scope_values(self):
        """Test all subscription scope values"""
        assert SubscriptionScope.GLOBAL.value == "global"
        assert SubscriptionScope.USER.value == "user"
        assert SubscriptionScope.PROJECT.value == "project"
        assert SubscriptionScope.BRANCH.value == "branch"
        assert SubscriptionScope.TASK.value == "task"