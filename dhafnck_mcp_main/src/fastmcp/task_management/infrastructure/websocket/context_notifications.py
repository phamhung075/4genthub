"""
Real-time Context Change Notifications via WebSocket

Provides real-time notifications for context changes across the hierarchy,
enabling immediate updates to connected clients and agents.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.websockets import WebSocketState
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("FastAPI WebSocket support not available")

    # Create mock classes for testing when FastAPI is not available
    class WebSocket:
        pass

    class WebSocketDisconnect(Exception):
        pass

    class WebSocketState:
        CONNECTED = "CONNECTED"
        DISCONNECTED = "DISCONNECTED"


class EventType(Enum):
    """Types of context events"""
    CREATED = "context.created"
    UPDATED = "context.updated"
    DELETED = "context.deleted"
    DELEGATED = "context.delegated"
    INHERITED = "context.inherited"
    BATCH_UPDATED = "context.batch_updated"
    CACHE_INVALIDATED = "context.cache_invalidated"


class SubscriptionScope(Enum):
    """Subscription scope levels"""
    GLOBAL = "global"           # All context changes
    USER = "user"               # User-specific changes
    PROJECT = "project"         # Project-specific changes
    BRANCH = "branch"           # Branch-specific changes
    TASK = "task"              # Task-specific changes


@dataclass
class ContextEvent:
    """Context change event"""
    event_type: EventType
    level: str
    context_id: str
    user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_type': self.event_type.value,
            'level': self.level,
            'context_id': self.context_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }


@dataclass
class Subscription:
    """WebSocket subscription"""
    client_id: str
    websocket: Any  # WebSocket connection
    scope: SubscriptionScope
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def matches(self, event: ContextEvent) -> bool:
        """Check if event matches subscription filters"""
        
        # Check scope
        if self.scope == SubscriptionScope.GLOBAL:
            # Global scope receives all events
            pass
        elif self.scope == SubscriptionScope.USER:
            if event.user_id != self.filters.get('user_id'):
                return False
        elif self.scope == SubscriptionScope.PROJECT:
            if event.metadata.get('project_id') != self.filters.get('project_id'):
                return False
        elif self.scope == SubscriptionScope.BRANCH:
            if event.metadata.get('git_branch_id') != self.filters.get('git_branch_id'):
                return False
        elif self.scope == SubscriptionScope.TASK:
            if event.context_id != self.filters.get('task_id'):
                return False
        
        # Check additional filters
        if 'event_types' in self.filters:
            if event.event_type not in self.filters['event_types']:
                return False
        
        if 'levels' in self.filters:
            if event.level not in self.filters['levels']:
                return False
        
        return True


class ContextNotificationService:
    """
    Service for managing real-time context change notifications.
    """
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_handlers: List[Callable] = []
        self._running = False
        self._task = None
        
        # Statistics
        self.stats = {
            'events_sent': 0,
            'events_queued': 0,
            'active_connections': 0,
            'total_connections': 0,
            'errors': 0
        }
    
    async def start(self):
        """Start the notification service"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("Context notification service started")
    
    async def stop(self):
        """Stop the notification service"""
        self._running = False
        if self._task:
            await self._task
        logger.info("Context notification service stopped")
    
    async def _process_events(self):
        """Process event queue and send notifications"""
        while self._running:
            try:
                # Get event from queue (with timeout)
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Send to matching subscriptions
                await self._broadcast_event(event)
                
                # Call event handlers
                for handler in self.event_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")
                
            except asyncio.TimeoutError:
                # No events, continue
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self.stats['errors'] += 1
    
    async def _broadcast_event(self, event: ContextEvent):
        """Broadcast event to matching subscriptions"""
        
        disconnected = []
        
        for client_id, subscription in self.subscriptions.items():
            try:
                # Check if subscription matches
                if not subscription.matches(event):
                    continue
                
                # Send event
                if WEBSOCKET_AVAILABLE:
                    websocket = subscription.websocket
                    # Check if we have a real WebSocket with proper methods
                    if hasattr(websocket, 'client_state') and hasattr(websocket, 'send_json'):
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(event.to_dict())
                            subscription.last_activity = datetime.now(timezone.utc)
                            self.stats['events_sent'] += 1
                        else:
                            disconnected.append(client_id)
                else:
                    # Fallback for testing without WebSocket
                    logger.info(f"Would send event to {client_id}: {event.event_type}")
                    
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                disconnected.append(client_id)
                self.stats['errors'] += 1
        
        # Remove disconnected clients
        for client_id in disconnected:
            await self.unsubscribe(client_id)
    
    async def subscribe(
        self,
        websocket: Any,
        client_id: str,
        scope: SubscriptionScope,
        filters: Optional[Dict[str, Any]] = None
    ) -> Subscription:
        """
        Subscribe to context notifications.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            scope: Subscription scope
            filters: Additional filters
        
        Returns:
            Subscription object
        """
        
        subscription = Subscription(
            client_id=client_id,
            websocket=websocket,
            scope=scope,
            filters=filters or {}
        )
        
        self.subscriptions[client_id] = subscription
        self.stats['active_connections'] = len(self.subscriptions)
        self.stats['total_connections'] += 1
        
        logger.info(f"Client {client_id} subscribed with scope {scope}")
        
        # Send welcome message
        if WEBSOCKET_AVAILABLE:
            # Only send welcome message if we have real FastAPI WebSocket
            if hasattr(websocket, 'send_json'):
                await websocket.send_json({
                    'type': 'welcome',
                    'client_id': client_id,
                    'scope': scope.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        return subscription
    
    async def unsubscribe(self, client_id: str):
        """Unsubscribe from notifications"""
        
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
            self.stats['active_connections'] = len(self.subscriptions)
            logger.info(f"Client {client_id} unsubscribed")
    
    async def notify(
        self,
        event_type: EventType,
        level: str,
        context_id: str,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Send notification for context change.
        
        Args:
            event_type: Type of event
            level: Context level
            context_id: Context identifier
            user_id: User who triggered change
            data: Event data
            metadata: Additional metadata
        """
        
        event = ContextEvent(
            event_type=event_type,
            level=level,
            context_id=context_id,
            user_id=user_id,
            data=data,
            metadata=metadata or {}
        )
        
        await self.event_queue.put(event)
        self.stats['events_queued'] += 1
    
    def add_event_handler(self, handler: Callable):
        """Add custom event handler"""
        self.event_handlers.append(handler)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'subscriptions': [
                {
                    'client_id': sub.client_id,
                    'scope': sub.scope.value,
                    'created_at': sub.created_at.isoformat(),
                    'last_activity': sub.last_activity.isoformat()
                }
                for sub in self.subscriptions.values()
            ]
        }
    
    async def heartbeat(self):
        """Send heartbeat to all connections"""
        
        disconnected = []
        
        for client_id, subscription in self.subscriptions.items():
            try:
                if WEBSOCKET_AVAILABLE:
                    websocket = subscription.websocket
                    # Check if we have a real WebSocket with proper methods
                    if hasattr(websocket, 'client_state') and hasattr(websocket, 'send_json'):
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json({
                                'type': 'heartbeat',
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
                        else:
                            disconnected.append(client_id)
            except:
                disconnected.append(client_id)
        
        for client_id in disconnected:
            await self.unsubscribe(client_id)


class WebSocketManager:
    """
    Manager for WebSocket connections and routing.
    """
    
    def __init__(self, notification_service: ContextNotificationService):
        self.notification_service = notification_service
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Default subscription to user scope
        await self.notification_service.subscribe(
            websocket=websocket,
            client_id=client_id,
            scope=SubscriptionScope.USER,
            filters={'user_id': client_id}
        )
    
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """Handle WebSocket disconnection"""
        self.active_connections.discard(websocket)
        await self.notification_service.unsubscribe(client_id)
    
    async def handle_message(
        self,
        websocket: WebSocket,
        client_id: str,
        message: Dict[str, Any]
    ):
        """Handle incoming WebSocket message"""
        
        msg_type = message.get('type')
        
        if msg_type == 'subscribe':
            # Update subscription
            scope = SubscriptionScope(message.get('scope', 'user'))
            filters = message.get('filters', {})
            
            await self.notification_service.subscribe(
                websocket=websocket,
                client_id=client_id,
                scope=scope,
                filters=filters
            )
            
            await websocket.send_json({
                'type': 'subscribed',
                'scope': scope.value,
                'filters': filters
            })
        
        elif msg_type == 'ping':
            # Respond to ping
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        elif msg_type == 'get_stats':
            # Send statistics
            stats = self.notification_service.get_stats()
            await websocket.send_json({
                'type': 'stats',
                'data': stats
            })
        
        else:
            # Unknown message type
            await websocket.send_json({
                'type': 'error',
                'message': f'Unknown message type: {msg_type}'
            })


# Global instance
_notification_service = None
_websocket_manager = None


def get_notification_service() -> ContextNotificationService:
    """Get or create notification service singleton"""
    global _notification_service
    if _notification_service is None:
        _notification_service = ContextNotificationService()
    return _notification_service


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager singleton"""
    global _websocket_manager
    if _websocket_manager is None:
        service = get_notification_service()
        _websocket_manager = WebSocketManager(service)
    return _websocket_manager


# FastAPI WebSocket endpoint example
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Example WebSocket endpoint for FastAPI.
    
    Usage in FastAPI:
    ```python
    from fastapi import FastAPI, WebSocket
    
    app = FastAPI()
    
    @app.websocket("/ws/context/{client_id}")
    async def websocket_route(websocket: WebSocket, client_id: str):
        await websocket_endpoint(websocket, client_id)
    ```
    """
    
    if not WEBSOCKET_AVAILABLE:
        logger.error("WebSocket support not available")
        return
    
    manager = get_websocket_manager()
    
    try:
        await manager.connect(websocket, client_id)
        
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                await manager.handle_message(websocket, client_id, data)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        await manager.disconnect(websocket, client_id)