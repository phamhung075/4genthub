"""
WebSocket Connection Manager v2.0

Manages WebSocket connections with dual-track message processing:
- User updates (immediate processing)
- AI updates (500ms batching)

NO backward compatibility - clean v2.0 implementation only.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..task_management.domain.services.cascade_calculator import (
    CascadeCalculator,
    EntityType as CascadeEntityType
)
from .protocol import (
    validate_message,
    create_user_update,
    create_ai_batch,
    create_error,
    create_heartbeat,
    create_sync,
    ProtocolError,
    InvalidVersionError,
    MessageSizeError
)
from .models import WSMessage, UserUpdateMessage, AIBatchMessage
from .types import EntityType, ActionType, SourceType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket Connection Manager with dual-track processing.

    Handles both immediate user updates and batched AI updates with
    full cascade support and v2.0 protocol enforcement.
    """

    def __init__(self, session_factory):
        """
        Initialize connection manager.

        Args:
            session_factory: Factory function for creating database sessions
        """
        self.connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_users: Dict[str, str] = {}  # session_id -> user_id

        # AI batching queue and processor
        self.ai_batch_queue: asyncio.Queue = asyncio.Queue()
        self.batch_processor = None

        # Message sequence counter
        self.sequence_counter = 0

        # Database and cascade calculator
        self.session_factory = session_factory
        self.cascade_calculator: Optional[CascadeCalculator] = None

        # Connection tracking
        self.active_users: Set[str] = set()
        self.heartbeat_intervals: Dict[str, float] = {}

        logger.info("ConnectionManager initialized for WebSocket v2.0 protocol")

    async def connect(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Accept a new WebSocket connection and perform initial sync.

        Args:
            websocket: WebSocket connection
            user_id: Authenticated user ID
            session_id: Optional session ID (auto-generated if None)

        Returns:
            Session ID for this connection
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        await websocket.accept()

        # Store connection
        self.connections[user_id] = websocket
        self.user_sessions[user_id] = session_id
        self.session_users[session_id] = user_id
        self.active_users.add(user_id)

        logger.info(f"WebSocket connected: user_id={user_id}, session_id={session_id}")

        # Initialize cascade calculator with new session
        async with self.session_factory() as db_session:
            self.cascade_calculator = CascadeCalculator(db_session)

            # Send initial sync data
            await self.send_initial_sync(user_id, session_id)

        return session_id

    async def disconnect(self, user_id: str) -> None:
        """
        Disconnect a WebSocket connection and cleanup.

        Args:
            user_id: User ID to disconnect
        """
        if user_id in self.connections:
            websocket = self.connections[user_id]
            session_id = self.user_sessions.get(user_id)

            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for {user_id}: {e}")

            # Cleanup tracking
            del self.connections[user_id]
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            if session_id and session_id in self.session_users:
                del self.session_users[session_id]
            if user_id in self.active_users:
                self.active_users.remove(user_id)
            if user_id in self.heartbeat_intervals:
                del self.heartbeat_intervals[user_id]

            logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def process_message(self, user_id: str, raw_message: str) -> None:
        """
        Process incoming WebSocket message with v2.0 validation.

        Args:
            user_id: User ID that sent the message
            raw_message: Raw JSON message string
        """
        try:
            # Parse JSON
            message_dict = json.loads(raw_message)

            # Validate v2.0 protocol (NO backward compatibility)
            validated_message = validate_message(message_dict)

            logger.debug(f"Processing v2.0 message from {user_id}: {validated_message.type}")

            # Route message based on source
            if validated_message.metadata.source == "user":
                await self._process_user_message(user_id, validated_message)
            elif validated_message.metadata.source == "mcp-ai":
                await self._queue_ai_message(validated_message)
            else:
                logger.warning(f"Unknown message source: {validated_message.metadata.source}")

        except json.JSONDecodeError as e:
            await self.send_error(user_id, f"Invalid JSON: {e}")
        except InvalidVersionError as e:
            await self.send_error(user_id, f"Protocol error: {e}")
        except MessageSizeError as e:
            await self.send_error(user_id, f"Message too large: {e}")
        except ProtocolError as e:
            await self.send_error(user_id, f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing message from {user_id}: {e}")
            await self.send_error(user_id, "Internal server error")

    async def _process_user_message(self, user_id: str, message: WSMessage) -> None:
        """
        Process user-initiated message with immediate broadcast.

        Args:
            user_id: User ID that sent the message
            message: Validated WSMessage
        """
        session_id = self.user_sessions.get(user_id)

        # Extract entity data for cascade calculation
        entity_type = message.payload.entity
        action = message.payload.action
        primary_data = message.payload.data.primary

        # Get entity ID from primary data for cascade calculation
        entity_id = None
        if isinstance(primary_data, dict):
            entity_id = primary_data.get("id")
        elif isinstance(primary_data, list) and primary_data:
            entity_id = primary_data[0].get("id") if isinstance(primary_data[0], dict) else None

        async with self.session_factory() as db_session:
            cascade_calculator = CascadeCalculator(db_session)

            # Create user update message with cascade data
            user_update = await create_user_update(
                entity_type=entity_type,
                action=action,
                primary_data=primary_data,
                cascade_calculator=cascade_calculator,
                entity_id=entity_id,
                user_id=user_id,
                session_id=session_id,
                correlation_id=message.metadata.correlation_id,
                sequence=self._next_sequence()
            )

            # Broadcast immediately to all connected users
            await self.broadcast_immediate(user_update)

    async def _queue_ai_message(self, message: WSMessage) -> None:
        """
        Queue AI message for batched processing.

        Args:
            message: Validated WSMessage from AI
        """
        await self.ai_batch_queue.put(message)
        logger.debug("AI message queued for batch processing")

    async def broadcast_immediate(self, message: Union[WSMessage, UserUpdateMessage]) -> None:
        """
        Broadcast message immediately to all connected users.

        Args:
            message: Message to broadcast
        """
        if not self.connections:
            logger.debug("No connections available for broadcast")
            return

        message_json = message.model_dump_json()
        disconnected_users = []

        for user_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message_json)
                logger.debug(f"Message broadcast to {user_id}")
            except WebSocketDisconnect:
                disconnected_users.append(user_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")
                disconnected_users.append(user_id)

        # Cleanup disconnected users
        for user_id in disconnected_users:
            await self.disconnect(user_id)

    async def broadcast_batch(self, batch_message: AIBatchMessage) -> None:
        """
        Broadcast AI batch message to all connected users.

        Args:
            batch_message: Combined AI batch message
        """
        await self.broadcast_immediate(batch_message)

    async def send_to_user(self, user_id: str, message: WSMessage) -> bool:
        """
        Send message to specific user.

        Args:
            user_id: Target user ID
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if user_id not in self.connections:
            logger.warning(f"User {user_id} not connected")
            return False

        try:
            websocket = self.connections[user_id]
            message_json = message.model_dump_json()
            await websocket.send_text(message_json)
            return True
        except WebSocketDisconnect:
            await self.disconnect(user_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return False

    async def send_error(self, user_id: str, error_message: str, error_code: Optional[str] = None) -> None:
        """
        Send error message to specific user.

        Args:
            user_id: Target user ID
            error_message: Human-readable error message
            error_code: Optional error code
        """
        session_id = self.user_sessions.get(user_id)

        error_msg = create_error(
            error_message=error_message,
            error_code=error_code,
            session_id=session_id,
            sequence=self._next_sequence()
        )

        await self.send_to_user(user_id, error_msg)

    async def send_initial_sync(self, user_id: str, session_id: str) -> None:
        """
        Send initial synchronization data when user connects.

        Uses the bulk API endpoint to get all user's project/branch summaries.

        Args:
            user_id: User ID for data context
            session_id: Session ID for tracking
        """
        try:
            # TODO: Integration with bulk API endpoint for initial sync
            # For now, send a basic sync message
            sync_data = {
                "type": "initial_sync",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket v2.0 connection established"
            }

            sync_message = create_sync(
                sync_data=sync_data,
                session_id=session_id,
                user_id=user_id,
                sequence=self._next_sequence()
            )

            await self.send_to_user(user_id, sync_message)
            logger.info(f"Initial sync sent to {user_id}")

        except Exception as e:
            logger.error(f"Error sending initial sync to {user_id}: {e}")
            await self.send_error(user_id, "Failed to load initial data")

    async def send_heartbeat(self, user_id: str) -> None:
        """
        Send heartbeat message to specific user.

        Args:
            user_id: Target user ID
        """
        session_id = self.user_sessions.get(user_id)

        heartbeat = create_heartbeat(
            session_id=session_id,
            sequence=self._next_sequence()
        )

        await self.send_to_user(user_id, heartbeat)

    def _next_sequence(self) -> int:
        """
        Get next message sequence number.

        Returns:
            Incremented sequence number
        """
        self.sequence_counter += 1
        return self.sequence_counter

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics for monitoring.

        Returns:
            Dictionary with connection stats
        """
        return {
            "total_connections": len(self.connections),
            "active_users": list(self.active_users),
            "queue_size": self.ai_batch_queue.qsize(),
            "sequence_counter": self.sequence_counter,
            "sessions": {
                "user_sessions": dict(self.user_sessions),
                "session_users": dict(self.session_users)
            }
        }

    async def cleanup(self) -> None:
        """
        Cleanup all connections and resources.
        """
        logger.info("Starting ConnectionManager cleanup")

        # Disconnect all users
        user_ids = list(self.connections.keys())
        for user_id in user_ids:
            await self.disconnect(user_id)

        # Clear queues
        while not self.ai_batch_queue.empty():
            try:
                self.ai_batch_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("ConnectionManager cleanup completed")

    def is_user_connected(self, user_id: str) -> bool:
        """
        Check if user is currently connected.

        Args:
            user_id: User ID to check

        Returns:
            True if user is connected
        """
        return user_id in self.connections and user_id in self.active_users