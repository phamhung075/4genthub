"""
WebSocket routes for real-time data synchronization
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Response
from typing import Optional, Dict, Any, Set, List, DefaultDict, TypedDict, NotRequired
import json
import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import random
import os

# Additional exception types for better error handling
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError

# Import authentication utilities for JWT validation
from fastmcp.auth.keycloak_dependencies import validate_keycloak_token, validate_local_token
from fastmcp.auth.domain.entities.user import User

# Import Prometheus metrics for monitoring
from fastmcp.server.metrics import (
    update_connection_count,
    update_queue_size,
    clear_queue_metrics,
    record_retry_attempt,
    record_delivery_time,
    track_broadcast_duration,
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

# ============================================================================
# TYPE DEFINITIONS - Structured type hints for better type safety
# ============================================================================

class SubscriptionDict(TypedDict, total=False):
    """WebSocket subscription configuration"""
    scope: str
    entity_type: NotRequired[str]
    entity_id: NotRequired[str]
    user_id: NotRequired[str]

class MessagePayloadDataDict(TypedDict, total=False):
    """Payload data structure in broadcast messages"""
    primary: NotRequired[Optional[Dict[str, Any]]]
    cascade: NotRequired[Dict[str, Any]]

class MessagePayloadDict(TypedDict):
    """Payload structure in broadcast messages"""
    entity: str
    action: str
    data: MessagePayloadDataDict

class MessageMetadataDict(TypedDict, total=False):
    """Metadata structure in broadcast messages"""
    source: str
    userId: str
    entity_type: str
    entity_id: str
    event_type: str

class BroadcastMessageDict(TypedDict):
    """Complete WebSocket broadcast message structure"""
    id: str
    version: str
    type: str
    timestamp: str
    sequence: int
    payload: MessagePayloadDict
    metadata: MessageMetadataDict

# ============================================================================

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

# Track if retry queue processor is running
_retry_queue_task: Optional[asyncio.Task] = None

# Track if notification cleanup task is running
_cleanup_task: Optional[asyncio.Task] = None

# Concurrency protection locks for shared state
_message_queue_lock = asyncio.Lock()  # Protects user_message_queues access
_connections_lock = asyncio.Lock()     # Protects connections dict access

# ============================================================================
# CONFIGURATION CONSTANTS - Retry, Timing, and Cleanup Settings
# ============================================================================
# These constants centralize all timing and retry configuration for easy tuning.
# Consider moving to environment variables for production configurability.

# Retry mechanism configuration
RETRY_BASE_DELAY_SECONDS = 5  # Base delay for exponential backoff (5s, 10s, 20s)
RETRY_BACKOFF_MULTIPLIER = 2  # Multiplier for exponential backoff calculation
RETRY_MAX_ATTEMPTS = 3        # Maximum retry attempts before giving up

# Background task intervals
RETRY_QUEUE_CHECK_INTERVAL = 5    # How often to check retry queue (seconds)
NOTIFICATION_CLEANUP_INTERVAL = 3600  # How often to cleanup old notifications (1 hour)
NOTIFICATION_RETENTION_HOURS = 24     # How long to keep notifications before cleanup

# ============================================================================

# Store all WebSocket connections in single atomic data structure
# This replaces the previous three separate dictionaries (active_connections,
# connection_subscriptions, connection_users) which could get out of sync.
# Key: WebSocket object, Value: Complete connection state
connections: Dict[WebSocket, WebSocketConnection] = {}

# Message queue for retry mechanism - prevents notification loss
@dataclass
class QueuedMessage:
    """
    Represents a queued WebSocket message awaiting delivery or retry.

    Attributes:
        message_id: Unique identifier for this queued message
        message: The actual WebSocket message payload
        user_id: User ID this message is destined for
        timestamp: When the message was first queued
        retry_count: Number of delivery attempts made
        max_retries: Maximum retry attempts before giving up
        next_retry_time: When the next retry should be attempted
    """
    message_id: str
    message: Dict[str, Any]
    user_id: str
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    next_retry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

# Per-user message queues with failed messages awaiting retry
user_message_queues: DefaultDict[str, List[QueuedMessage]] = defaultdict(list)


@dataclass
class WebSocketConnection:
    """
    Represents a complete WebSocket connection state.

    This dataclass consolidates all connection-related data into a single atomic unit,
    preventing synchronization issues that occurred when tracking connection state
    across multiple separate dictionaries.

    Attributes:
        websocket: The WebSocket connection object
        user: Authenticated user associated with this connection
        client_id: Unique identifier for this client connection
        subscription: Subscription configuration (entity types, filters, etc.)
        connected_at: Timestamp when connection was established
        last_activity: Timestamp of last activity (for timeout detection)
    """
    websocket: WebSocket
    user: User
    client_id: str
    subscription: Dict[str, Any]
    connected_at: datetime
    last_activity: datetime

    def update_activity(self):
        """Update the last activity timestamp to current time."""
        self.last_activity = datetime.now(timezone.utc)


async def process_message_retry_queue() -> None:
    """
    Background task to process queued messages and retry failed deliveries.

    Runs every 5 seconds to:
    - Check all queued messages for users
    - Retry messages that are past their next_retry_time
    - Remove messages that exceeded max_retries
    - Apply exponential backoff (5s, 10s, 20s)

    This ensures notifications are eventually delivered even if the
    initial send fails due to temporary network issues or disconnections.
    """
    logger.info("🔄 Message retry queue processor started")

    while True:
        try:
            await asyncio.sleep(RETRY_QUEUE_CHECK_INTERVAL)

            current_time = datetime.now(timezone.utc)

            # Acquire lock to safely access user_message_queues
            async with _message_queue_lock:
                total_queued = sum(len(msgs) for msgs in user_message_queues.values())

                if total_queued > 0:
                    logger.debug(f"📬 Processing {total_queued} queued messages across {len(user_message_queues)} users")

                # Update queue size metrics for all users
                for user_id, message_queue in user_message_queues.items():
                    update_queue_size(user_id, len(message_queue))

                # Process each user's message queue
                    for user_id, message_queue in list(user_message_queues.items()):
                        messages_to_remove = []

                        for queued_msg in message_queue:
                            # Check if max retries exceeded
                            if queued_msg.retry_count >= queued_msg.max_retries:
                                logger.warning(
                                    f"❌ Dropping message {queued_msg.message_id} for user {user_id}: "
                                    f"max retries ({queued_msg.max_retries}) exceeded"
                                )
                                # Record failed delivery metrics
                                record_retry_attempt(success=False, attempt=queued_msg.retry_count)
                                record_delivery_time('failed', (current_time - queued_msg.queued_at).total_seconds())
                                messages_to_remove.append(queued_msg)
                                continue

                            # Check if it's time to retry
                            if current_time >= queued_msg.next_retry_time:
                                logger.info(
                                    f"🔄 Retrying message {queued_msg.message_id} for user {user_id} "
                                    f"(attempt {queued_msg.retry_count + 1}/{queued_msg.max_retries})"
                                )

                                # Find active websockets for this user
                                user_websockets = []
                                for connection in connections.values():
                                    if connection.user.id == user_id:
                                        user_websockets.append(connection.websocket)

                                if not user_websockets:
                                    # User not connected - will retry later
                                    logger.debug(f"⏳ User {user_id} not connected, will retry later")
                                    # Update next retry time
                                    queued_msg.retry_count += 1
                                    delay_seconds = RETRY_BASE_DELAY_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** (queued_msg.retry_count - 1))
                                    queued_msg.next_retry_time = current_time + timedelta(seconds=delay_seconds)
                                    continue

                                # Attempt delivery to all user's websockets
                                delivery_success = False
                                for websocket in user_websockets:
                                    try:
                                        await websocket.send_json(queued_msg.message)
                                        logger.info(f"✅ Successfully delivered queued message {queued_msg.message_id}")
                                        delivery_success = True
                                        break  # Success - no need to try other connections
                                    except Exception as e:
                                        logger.warning(f"⚠️ Retry failed for message {queued_msg.message_id}: {e}")
                                        continue

                                if delivery_success:
                                    # Remove from queue on successful delivery
                                    # Record successful retry metrics
                                    record_retry_attempt(success=True, attempt=queued_msg.retry_count + 1)
                                    record_delivery_time('retry', (current_time - queued_msg.queued_at).total_seconds())
                                    messages_to_remove.append(queued_msg)
                                else:
                                    # All attempts failed - update retry info
                                    queued_msg.retry_count += 1
                                    delay_seconds = RETRY_BASE_DELAY_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** (queued_msg.retry_count - 1))
                                    queued_msg.next_retry_time = current_time + timedelta(seconds=delay_seconds)
                                    logger.info(
                                        f"📬 Message {queued_msg.message_id} queued for retry #{queued_msg.retry_count} "
                                        f"in {delay_seconds}s"
                                    )

                        # Clean up processed messages
                        for msg in messages_to_remove:
                            message_queue.remove(msg)

                        # Clean up empty queues
                        if not message_queue:
                            del user_message_queues[user_id]
                            # Clear queue metrics for this user
                            clear_queue_metrics(user_id)

        except Exception as e:
            logger.error(f"❌ Error in message retry queue processor: {e}", exc_info=True)
            # Continue processing despite errors


def start_retry_queue_processor() -> None:
    """
    Start the background message retry queue processor.

    This should be called during application startup to ensure
    queued messages are processed and retried.
    """
    global _retry_queue_task

    if _retry_queue_task is None or _retry_queue_task.done():
        _retry_queue_task = asyncio.create_task(process_message_retry_queue())
        logger.info("✅ Message retry queue processor task started")
    else:
        logger.warning("⚠️ Message retry queue processor already running")


async def stop_retry_queue_processor() -> None:
    """
    Stop the background message retry queue processor.

    This should be called during application shutdown for graceful cleanup.
    """
    global _retry_queue_task

    if _retry_queue_task and not _retry_queue_task.done():
        _retry_queue_task.cancel()
        try:
            await _retry_queue_task
        except asyncio.CancelledError:
            logger.info("✅ Message retry queue processor stopped")
    _retry_queue_task = None


async def process_notification_cleanup() -> None:
    """
    Background task to periodically clean up expired missed notifications.

    Runs every hour and removes:
    - Undelivered notifications older than 24 hours
    - Delivered notifications older than 7 days

    This prevents the missed_notifications table from growing indefinitely.
    """
    while True:
        try:
            # Wait 1 hour between cleanup runs
            await asyncio.sleep(NOTIFICATION_CLEANUP_INTERVAL)

            # Clean up expired notifications
            deleted_count = cleanup_expired_notifications(older_than_hours=NOTIFICATION_RETENTION_HOURS)

            if deleted_count > 0:
                logger.info(
                    f"🗑️ Notification cleanup completed: Removed {deleted_count} expired notifications"
                )

        except asyncio.CancelledError:
            logger.info("✅ Notification cleanup task cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error in notification cleanup task: {e}")
            # Continue running despite errors - don't crash the cleanup task


def start_notification_cleanup_task() -> None:
    """
    Start the background notification cleanup task.

    This should be called during application startup to ensure
    old notifications are periodically removed from the database.
    """
    global _cleanup_task

    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(process_notification_cleanup())
        logger.info("✅ Notification cleanup task started (runs every 1 hour)")
    else:
        logger.warning("⚠️ Notification cleanup task already running")


async def stop_notification_cleanup_task() -> None:
    """
    Stop the background notification cleanup task.

    This should be called during application shutdown for graceful cleanup.
    """
    global _cleanup_task

    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            logger.info("✅ Notification cleanup task stopped")
    _cleanup_task = None


async def validate_websocket_token(token: str) -> Optional[User]:
    """
    Validate JWT token for WebSocket connections.

    Args:
        token: JWT token from query params or headers

    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        logger.warning("No token provided for WebSocket connection")
        return None

    try:
        # First, try to decode token structure to determine type
        import jwt
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss", "")

        # Check if this is a Keycloak token
        keycloak_url = os.getenv("KEYCLOAK_URL")
        auth_provider = os.getenv("AUTH_PROVIDER", "keycloak")

        if auth_provider == "keycloak" and keycloak_url and issuer.startswith(keycloak_url):
            logger.debug("Validating Keycloak token for WebSocket")
            try:
                user = await validate_keycloak_token(token)
                logger.info(f"WebSocket authenticated via Keycloak: {user.id}")
                return user
            except HTTPException as e:
                # Log detailed error for debugging
                logger.error(f"❌ Keycloak token validation failed: {e.detail}")
                logger.error(f"   Token issuer: {issuer}")
                logger.error(f"   Keycloak URL: {keycloak_url}")
                logger.error(f"   Auth provider: {auth_provider}")
                logger.error(f"   Troubleshooting: Verify KEYCLOAK_URL, KEYCLOAK_REALM, and token validity")

                # Return None - connection will be rejected with proper authentication failure
                return None
        else:
            logger.debug("Validating local JWT token for WebSocket")
            try:
                user = validate_local_token(token)
                logger.info(f"WebSocket authenticated via local JWT: {user.id}")
                return user
            except HTTPException as e:
                logger.warning(f"Local token validation failed: {e.detail}")
                return None

    except jwt.DecodeError:
        logger.warning("Failed to decode WebSocket token")
        return None
    except Exception as e:
        logger.error(f"WebSocket token validation error: {e}")
        return None

@router.websocket("/realtime")
async def realtime_updates(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time data updates.
    Clients connect here to receive notifications when data changes.
    Now requires JWT authentication for security.
    """
    client_id = None
    authenticated_user = None

    # 🔍 ENHANCED DEBUG: Log all connection attempts
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.warning(f"🔗 WEBSOCKET CONNECTION ATTEMPT from {client_ip}")
    logger.warning(f"🔗 Query params: {dict(websocket.query_params)}")
    logger.warning(f"🔗 Headers: {dict(websocket.headers)}")

    try:
        # Get token from query params BEFORE accepting connection
        token = websocket.query_params.get("token")
        logger.warning(f"🔗 Token provided: {'YES' if token else 'NO'}")
        if token:
            logger.warning(f"🔗 Token length: {len(token)} chars")

        # Validate JWT token BEFORE accepting connection
        authenticated_user = await validate_websocket_token(token)
        if not authenticated_user:
            logger.warning(f"🚫 WebSocket connection REJECTED: Invalid or missing JWT token from {client_ip}")
            await websocket.close(code=4001, reason="Authentication required")
            return

        logger.warning(f"✅ JWT token VALID for user: {authenticated_user.id} ({authenticated_user.email})")

        # Accept connection only after successful authentication
        await websocket.accept()
        logger.warning(f"🎉 WebSocket connection ACCEPTED for user: {authenticated_user.id} ({authenticated_user.email})")

        # Generate a unique client ID using authenticated user ID
        connection_id = random.randint(100000, 999999)  # Unique per connection
        client_id = f"user_{authenticated_user.id}_{connection_id}"

        logger.warning(f"🔗 Authenticated client CONNECTED: {client_id}")

        # Store the connection with complete state in single atomic operation
        # This prevents synchronization issues that occurred with three separate dictionaries
        current_time = datetime.now(timezone.utc)
        connection = WebSocketConnection(
            websocket=websocket,
            user=authenticated_user,
            client_id=client_id,
            subscription={
                "client_id": client_id,
                "user_id": authenticated_user.id,
                "user_email": authenticated_user.email,
                "scope": "branch",  # Default scope
                "filters": {}
            },
            connected_at=current_time,
            last_activity=current_time
        )

        # Acquire lock to safely add connection
        async with _connections_lock:
            connections[websocket] = connection

        # 🔍 ENHANCED DEBUG: Log connection state
        total_connections = len(connections)
        unique_clients = len(set(conn.client_id for conn in connections.values()))
        logger.warning(f"📊 WEBSOCKET STATS: {total_connections} total connections, {unique_clients} unique clients")

        # Update connection metrics
        authenticated_count = sum(1 for conn in connections.values() if conn.user.id)
        unauthenticated_count = total_connections - authenticated_count
        update_connection_count(total_connections, authenticated_count, unauthenticated_count)

        # Send welcome message with authenticated user info (v2.0 format)
        await websocket.send_json({
            "id": f"welcome-{connection_id}",
            "version": "2.0",
            "type": "sync",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": 0,
            "payload": {
                "entity": "connection",
                "action": "welcome",
                "data": {
                    "primary": {
                        "client_id": client_id,
                        "user_id": authenticated_user.id,
                        "user_email": authenticated_user.email,
                        "scope": "branch",
                        "authenticated": True
                    }
                }
            },
            "metadata": {
                "source": "system",
                "userId": authenticated_user.id,
                "sessionId": client_id
            }
        })

        # Replay missed notifications stored while user was offline
        try:
            missed_notifications = fetch_missed_notifications(
                user_id=authenticated_user.id,
                delivered=False,
                limit=100  # Replay up to 100 missed notifications
            )

            if missed_notifications:
                logger.info(
                    f"🔄 Replaying {len(missed_notifications)} missed notifications "
                    f"for user {authenticated_user.id[:8]} (client {client_id})"
                )

                replay_success_count = 0
                replay_failure_count = 0

                for notification in missed_notifications:
                    try:
                        # Send the stored notification to the client
                        await websocket.send_json(notification["message"])

                        # Mark as delivered
                        if mark_notification_delivered(notification["id"]):
                            replay_success_count += 1
                            logger.debug(
                                f"✅ Replayed notification {notification['id'][:8]} "
                                f"(created: {notification['created_at']})"
                            )
                        else:
                            replay_failure_count += 1
                            logger.warning(
                                f"⚠️ Sent notification {notification['id'][:8]} but failed to mark as delivered"
                            )

                    except Exception as e:
                        replay_failure_count += 1
                        logger.warning(
                            f"❌ Failed to replay notification {notification['id'][:8]}: {e}"
                        )
                        # Increment delivery attempt counter for failed replays
                        increment_delivery_attempts(notification["id"])

                logger.info(
                    f"🔄 Replay summary for user {authenticated_user.id[:8]}: "
                    f"{replay_success_count} succeeded, {replay_failure_count} failed"
                )

        except Exception as e:
            logger.error(
                f"❌ Error during notification replay for user {authenticated_user.id[:8]}: {e}"
            )
            # Don't disconnect user if replay fails - just log and continue

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type in ["ping", "heartbeat"]:
                    await websocket.send_json({
                        "id": f"pong-{random.randint(100000, 999999)}",
                        "version": "2.0",
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sequence": random.randint(1000, 9999),
                        "payload": {
                            "entity": "system",
                            "action": "pong",
                            "data": {
                                "primary": {"status": "alive"}
                            }
                        },
                        "metadata": {
                            "source": "system",
                            "userId": authenticated_user.id,
                            "sessionId": client_id
                        }
                    })

                elif message_type == "subscribe":
                    # Update subscription scope
                    scope = data.get("scope", "branch")
                    filters = data.get("filters", {})

                    # Update subscription in the connection object
                    if websocket in connections:
                        connections[websocket].subscription.update({
                            "scope": scope,
                            "filters": filters
                        })
                        connections[websocket].update_activity()

                    await websocket.send_json({
                        "id": f"subscribed-{random.randint(100000, 999999)}",
                        "version": "2.0",
                        "type": "sync",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sequence": random.randint(1000, 9999),
                        "payload": {
                            "entity": "subscription",
                            "action": "subscribed",
                            "data": {
                                "primary": {
                                    "scope": scope,
                                    "filters": filters
                                }
                            }
                        },
                        "metadata": {
                            "source": "system",
                            "userId": authenticated_user.id,
                            "sessionId": client_id
                        }
                    })

                else:
                    await websocket.send_json({
                        "id": f"error-{random.randint(100000, 999999)}",
                        "version": "2.0",
                        "type": "error",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sequence": random.randint(1000, 9999),
                        "payload": {
                            "entity": "system",
                            "action": "error",
                            "data": {
                                "primary": {
                                    "message": f"Unknown message type: {message_type}",
                                    "code": "UNKNOWN_MESSAGE_TYPE"
                                }
                            }
                        },
                        "metadata": {
                            "source": "system",
                            "userId": authenticated_user.id,
                            "sessionId": client_id
                        }
                    })

            except WebSocketDisconnect:
                logger.warning(f"🔌 WebSocket DISCONNECTED: {client_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "id": f"error-{random.randint(100000, 999999)}",
                    "version": "2.0",
                    "type": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence": random.randint(1000, 9999),
                    "payload": {
                        "entity": "system",
                        "action": "error",
                        "data": {
                            "primary": {
                                "message": "Invalid JSON",
                                "code": "INVALID_JSON"
                            }
                        }
                    },
                    "metadata": {
                        "source": "system",
                        "userId": authenticated_user.id if authenticated_user else None,
                        "sessionId": client_id
                    }
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send_json({
                    "id": f"error-{random.randint(100000, 999999)}",
                    "version": "2.0",
                    "type": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence": random.randint(1000, 9999),
                    "payload": {
                        "entity": "system",
                        "action": "error",
                        "data": {
                            "primary": {
                                "message": str(e),
                                "code": "GENERAL_ERROR"
                            }
                        }
                    },
                    "metadata": {
                        "source": "system",
                        "userId": authenticated_user.id if authenticated_user else None,
                        "sessionId": client_id
                    }
                })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Clean up connection data - single atomic deletion
        async with _connections_lock:
            if websocket in connections:
                del connections[websocket]
            remaining_connections = len(connections)

            # Update connection metrics after disconnect
            authenticated_count = sum(1 for conn in connections.values() if conn.user.id)
            unauthenticated_count = remaining_connections - authenticated_count
            update_connection_count(remaining_connections, authenticated_count, unauthenticated_count)

        # 🔍 ENHANCED DEBUG: Log final connection stats
        if authenticated_user:
            logger.warning(f"🔌 CLEANUP: Client {client_id} (user: {authenticated_user.id}) disconnected. Remaining: {remaining_connections}")
        else:
            logger.warning(f"🔌 CLEANUP: Unauthenticated connection terminated. Remaining: {remaining_connections}")


@router.websocket("/task-polling")
async def task_polling(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for task/subtask completion polling.

    Used by cclaude-wait and other tools to monitor specific task progress
    and receive completion data when tasks reach 'done' status.

    Authentication: JWT token required in query params (?token=<jwt>)

    Protocol:
      1. Client connects with valid JWT token
      2. Server authenticates and accepts connection
      3. Client sends subscription: {"type": "subscribe", "scope": "task|subtask", "entity_id": "uuid"}
      4. Server acknowledges subscription
      5. Server sends completion event when entity reaches 'done' status
      6. Connection can be kept alive for heartbeats or closed after delivery

    Example completion message format:
    {
        "version": "2.0",
        "type": "update",
        "payload": {
            "entity": "task",
            "action": "completed",
            "data": {"primary": {...task_data...}}
        },
        "metadata": {
            "status": "done",
            "entity_id": "task_uuid",
            "task_title": "...",
            "completion_summary": "...",
            "progress_percentage": 100,
            ...
        }
    }
    """
    authenticated_user = None
    subscription = {}
    client_id = None

    # Log connection attempt
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"🔗 TASK POLLING: Connection attempt from {client_ip}")

    try:
        # Get token from query params BEFORE accepting connection
        token = websocket.query_params.get("token")

        if not token:
            logger.warning(f"🚫 TASK POLLING: Connection rejected - no token provided from {client_ip}")
            await websocket.close(code=4001, reason="Authentication required: missing token")
            return

        # Validate JWT token BEFORE accepting connection (reuse existing validation)
        authenticated_user = await validate_websocket_token(token)

        if not authenticated_user:
            logger.warning(f"🚫 TASK POLLING: Connection rejected - invalid token from {client_ip}")
            await websocket.close(code=4001, reason="Authentication required: invalid token")
            return

        logger.info(f"✅ TASK POLLING: JWT token valid for user: {authenticated_user.id} ({authenticated_user.email})")

        # Accept connection after successful authentication
        await websocket.accept()
        logger.info(f"🎉 TASK POLLING: Connection accepted for user: {authenticated_user.id}")

        # Generate unique client ID
        connection_id = random.randint(100000, 999999)
        client_id = f"polling_{authenticated_user.id}_{connection_id}"

        # Wait for subscription message from client
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning(f"⏰ TASK POLLING: Timeout waiting for subscription from {client_id}")
            await websocket.close(code=4000, reason="Timeout: expected subscribe message within 10s")
            return

        # Validate subscription message
        if data.get("type") != "subscribe":
            logger.warning(f"🚫 TASK POLLING: Invalid message type from {client_id}: {data.get('type')}")
            await websocket.close(code=4000, reason="Expected subscribe message")
            return

        # Extract subscription details
        scope = data.get("scope")  # "task" or "subtask"
        entity_id = data.get("entity_id")

        if not entity_id:
            logger.warning(f"🚫 TASK POLLING: Missing entity_id from {client_id}")
            await websocket.close(code=4000, reason="Missing entity_id in subscription")
            return

        if scope not in ["task", "subtask"]:
            logger.warning(f"🚫 TASK POLLING: Invalid scope from {client_id}: {scope}")
            await websocket.close(code=4000, reason="Invalid scope: must be 'task' or 'subtask'")
            return

        # Store subscription details
        subscription = {
            "scope": scope,
            "entity_id": entity_id,
            "user_id": authenticated_user.id
        }

        logger.info(f"📡 TASK POLLING: Subscribed to {scope} {entity_id} for user {authenticated_user.id}")

        # Store connection in global connections dict for broadcast_data_change to find
        current_time = datetime.now(timezone.utc)
        connection = WebSocketConnection(
            websocket=websocket,
            user=authenticated_user,
            client_id=client_id,
            subscription=subscription,
            connected_at=current_time,
            last_activity=current_time
        )

        # Add to connections dict (thread-safe)
        async with _connections_lock:
            connections[websocket] = connection

        logger.info(f"✅ TASK POLLING: Connection registered for {scope} {entity_id}")

        # Send acknowledgment to client
        await websocket.send_json({
            "type": "subscribed",
            "scope": scope,
            "entity_id": entity_id,
            "client_id": client_id,
            "user_id": authenticated_user.id
        })

        # Keep connection alive - wait for completion event or disconnect
        # The broadcast_data_change function will send completion events when tasks complete
        while True:
            try:
                # Wait for messages with timeout
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=3600  # 1 hour timeout
                )

                # Handle heartbeat pings
                if message.get("type") in ["ping", "heartbeat"]:
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    connection.update_activity()
                    logger.debug(f"💓 TASK POLLING: Heartbeat from {client_id}")

            except asyncio.TimeoutError:
                logger.info(f"⏰ TASK POLLING: Timeout for {client_id} - closing connection")
                break
            except WebSocketDisconnect:
                logger.info(f"🔌 TASK POLLING: Client {client_id} disconnected")
                break
            except json.JSONDecodeError:
                logger.warning(f"⚠️ TASK POLLING: Invalid JSON from {client_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"❌ TASK POLLING: Error processing message from {client_id}: {e}")
                break

    except Exception as e:
        logger.error(f"❌ TASK POLLING: Unexpected error for {client_id}: {e}", exc_info=True)

    finally:
        # Cleanup connection
        async with _connections_lock:
            if websocket in connections:
                del connections[websocket]
                remaining = len(connections)
                logger.info(f"🧹 TASK POLLING: Cleaned up {client_id}. Remaining connections: {remaining}")

        # Update metrics
        if connections:
            authenticated_count = sum(1 for conn in connections.values() if conn.user.id)
            unauthenticated_count = len(connections) - authenticated_count
            update_connection_count(len(connections), authenticated_count, unauthenticated_count)


async def log_authorization_failure(
    websocket: WebSocket,
    user_id: str,
    entity_type: str,
    entity_id: str,
    error: Exception,
    failure_reason: str = "database_error"
) -> None:
    """
    Log authorization failures for security audit trail.

    Creates structured log entries for all authorization failures to help
    with debugging and security analysis. In production, these logs can be
    sent to SIEM systems for monitoring.

    Args:
        websocket: The WebSocket connection that failed authorization
        user_id: User ID that was denied access
        entity_type: Type of entity being accessed
        entity_id: ID of the entity
        error: The exception that caused the failure
        failure_reason: Categorized reason for the failure
    """
    # Structured logging for security audit trail
    audit_entry = {
        "event": "authorization_failure",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "failure_reason": failure_reason,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "connection_info": {
            "client_host": websocket.client.host if websocket.client else "unknown",
            "client_port": websocket.client.port if websocket.client else 0
        }
    }

    # Log as warning for visibility
    logger.warning(f"🔒 AUTHORIZATION FAILURE AUDIT: {audit_entry}")

    # In production, this could also write to a dedicated audit database table
    # or send to a SIEM system for security monitoring


# ==============================================================================
# MISSED NOTIFICATION PERSISTENCE - Database Helper Functions
# ==============================================================================

def store_missed_notification(user_id: str, message: Dict[str, Any]) -> Optional[str]:
    """
    Store a missed notification in the database for later replay.

    Args:
        user_id: User ID to store the notification for
        message: The WebSocket message to store (as dict)

    Returns:
        Notification ID if stored successfully, None if error
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import MissedNotification
        import uuid

        notification_id = str(uuid.uuid4())

        with get_session() as session:
            notification = MissedNotification(
                id=notification_id,
                user_id=user_id,
                message=message,
                created_at=datetime.now(timezone.utc),
                delivered=False,
                delivery_attempts=0
            )
            session.add(notification)
            session.commit()

            logger.info(f"💾 Stored missed notification {notification_id} for user {user_id}")
            return notification_id

    except Exception as e:
        logger.error(f"❌ Failed to store missed notification for user {user_id}: {e}")
        return None


def fetch_missed_notifications(user_id: str, delivered: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch missed notifications for a user from the database.

    Args:
        user_id: User ID to fetch notifications for
        delivered: Whether to fetch delivered or undelivered notifications
        limit: Maximum number of notifications to return

    Returns:
        List of notification dicts with id, message, created_at, etc.
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import MissedNotification

        with get_session() as session:
            notifications = session.query(MissedNotification).filter(
                MissedNotification.user_id == user_id,
                MissedNotification.delivered == delivered
            ).order_by(
                MissedNotification.created_at.asc()
            ).limit(limit).all()

            result = []
            for notif in notifications:
                result.append({
                    "id": notif.id,
                    "message": notif.message,
                    "created_at": notif.created_at,
                    "delivery_attempts": notif.delivery_attempts
                })

            return result

    except Exception as e:
        logger.error(f"❌ Failed to fetch missed notifications for user {user_id}: {e}")
        return []


def mark_notification_delivered(notification_id: str) -> bool:
    """
    Mark a notification as successfully delivered.

    Args:
        notification_id: ID of the notification to mark as delivered

    Returns:
        True if marked successfully, False if error
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import MissedNotification

        with get_session() as session:
            notification = session.query(MissedNotification).filter(
                MissedNotification.id == notification_id
            ).first()

            if notification:
                notification.delivered = True
                notification.last_attempt_at = datetime.now(timezone.utc)
                session.commit()
                return True
            else:
                logger.warning(f"⚠️ Notification {notification_id} not found for marking delivered")
                return False

    except Exception as e:
        logger.error(f"❌ Failed to mark notification {notification_id} as delivered: {e}")
        return False


def increment_delivery_attempts(notification_id: str) -> bool:
    """
    Increment the delivery attempt counter for a notification.

    Args:
        notification_id: ID of the notification to update

    Returns:
        True if updated successfully, False if error
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import MissedNotification

        with get_session() as session:
            notification = session.query(MissedNotification).filter(
                MissedNotification.id == notification_id
            ).first()

            if notification:
                notification.delivery_attempts += 1
                notification.last_attempt_at = datetime.now(timezone.utc)
                session.commit()
                return True
            else:
                logger.warning(f"⚠️ Notification {notification_id} not found for attempt increment")
                return False

    except Exception as e:
        logger.error(f"❌ Failed to increment delivery attempts for {notification_id}: {e}")
        return False


def cleanup_expired_notifications(older_than_hours: int = 24) -> int:
    """
    Clean up expired missed notifications from the database.

    Removes:
    - Undelivered notifications older than specified hours
    - Delivered notifications older than 7 days

    Args:
        older_than_hours: Remove undelivered notifications older than this many hours

    Returns:
        Number of notifications cleaned up
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import MissedNotification

        with get_session() as session:
            # Calculate cutoff times
            undelivered_cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            delivered_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

            # Delete undelivered notifications older than cutoff
            undelivered_deleted = session.query(MissedNotification).filter(
                MissedNotification.delivered == False,
                MissedNotification.created_at < undelivered_cutoff
            ).delete()

            # Delete delivered notifications older than 7 days
            delivered_deleted = session.query(MissedNotification).filter(
                MissedNotification.delivered == True,
                MissedNotification.created_at < delivered_cutoff
            ).delete()

            session.commit()

            total_deleted = undelivered_deleted + delivered_deleted
            logger.info(f"🗑️ Cleaned up {total_deleted} expired notifications ({undelivered_deleted} undelivered, {delivered_deleted} delivered)")
            return total_deleted

    except Exception as e:
        logger.error(f"❌ Failed to cleanup expired notifications: {e}")
        return 0


async def is_user_authorized_for_message(
    websocket: WebSocket,
    entity_type: str,
    entity_id: str,
    triggering_user_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check if a WebSocket connection's user is authorized to receive a specific message.

    Authorization rules:
    1. Users can receive messages about their own data
    2. Users can receive messages about shared data they have access to
    3. No unauthorized data exposure across user boundaries
    4. System messages are allowed only to the actual resource owner

    Args:
        websocket: The WebSocket connection to check
        entity_type: Type of entity (task, project, branch, subtask, etc.)
        entity_id: ID of the entity
        triggering_user_id: User who triggered the change
        metadata: Optional metadata containing additional context

    Returns:
        True if the user is authorized to receive the message, False otherwise
    """
    # Get user information for this connection
    if websocket not in connections:
        logger.warning(
            f"⚠️ AUTHORIZATION DENIED: NO_USER_CONTEXT - "
            f"WebSocket connection has no associated user for {entity_type} {entity_id}"
        )
        logger.warning(f"📊 Available authenticated connections: {len(connections)}")

        # Send error notification to frontend
        try:
            await websocket.send_json({
                "id": f"auth-error-{random.randint(100000, 999999)}",
                "version": "2.0",
                "type": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sequence": random.randint(1000, 9999),
                "payload": {
                    "entity": "system",
                    "action": "authorization_denied",
                    "data": {
                        "primary": {
                            "code": "NO_USER_CONTEXT",
                            "message": "WebSocket connection has no authenticated user",
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "reason": "Connection not properly authenticated"
                        }
                    }
                },
                "metadata": {
                    "source": "system",
                    "severity": "error"
                }
            })
        except Exception as send_error:
            logger.error(f"Failed to send NO_USER_CONTEXT error to client: {send_error}")

        return False

    connection_user = connections[websocket].user
    connection_user_id = connection_user.id

    logger.warning(f"🔍 🎯 AUTH DEBUG: Checking authorization for {entity_type} {entity_id}")
    logger.warning(f"🔍 🎯 AUTH DEBUG: Connection user: {connection_user_id}")
    logger.warning(f"🔍 🎯 AUTH DEBUG: Triggering user: {triggering_user_id}")

    # Rule 1: Users always receive messages about their own actions
    if connection_user_id == triggering_user_id:
        logger.warning(f"✅ 🎯 AUTH DEBUG: User {connection_user_id} authorized to receive message about their own {entity_type}")
        return True

    # Rule 2: Handle system messages with proper data isolation
    if triggering_user_id == "system":
        logger.debug(f"System message detected - checking resource ownership for user {connection_user_id}")
        return await _check_resource_ownership(connection_user_id, entity_type, entity_id, metadata)

    # Rule 3: Check entity-specific authorization based on user ownership/access
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Task, ProjectGitBranch, Subtask, Project

        with get_session() as session:
            # Check authorization based on entity type
            if entity_type == "task":
                # Check if user has access to this task
                task = session.query(Task).filter(
                    Task.id == entity_id,
                    Task.user_id == connection_user_id  # User owns this task
                ).first()
                if task:
                    logger.debug(f"User {connection_user_id} authorized for task {entity_id} (owner)")
                    return True

            elif entity_type == "subtask":
                # Check if user has access to the parent task
                parent_task_id = metadata.get("parent_task_id") if metadata else None
                if parent_task_id:
                    task = session.query(Task).filter(
                        Task.id == parent_task_id,
                        Task.user_id == connection_user_id
                    ).first()
                    if task:
                        logger.debug(f"User {connection_user_id} authorized for subtask {entity_id} (task owner)")
                        return True

            elif entity_type == "branch":
                # Check if user has access to this branch
                branch = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.id == entity_id,
                    ProjectGitBranch.user_id == connection_user_id
                ).first()
                if branch:
                    logger.debug(f"User {connection_user_id} authorized for branch {entity_id} (owner)")
                    return True

            elif entity_type == "project":
                # Check if user has access to this project
                project = session.query(Project).filter(
                    Project.id == entity_id,
                    Project.user_id == connection_user_id
                ).first()
                if project:
                    logger.debug(f"User {connection_user_id} authorized for project {entity_id} (owner)")
                    return True

    except Exception as e:
        logger.error(f"⚠️ AUTHORIZATION ERROR: Database error during authorization check: {e}")

        # Log for security audit trail
        await log_authorization_failure(
            websocket=websocket,
            user_id=connection_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            error=e,
            failure_reason="database_error"
        )

        # Send error notification to frontend
        try:
            await websocket.send_json({
                "id": f"auth-error-{random.randint(100000, 999999)}",
                "version": "2.0",
                "type": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sequence": random.randint(1000, 9999),
                "payload": {
                    "entity": "system",
                    "action": "authorization_error",
                    "data": {
                        "primary": {
                            "code": "AUTH_DB_ERROR",
                            "message": "Authorization check failed due to database issue",
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "retry_recommended": True,
                            "error_type": "temporary"
                        }
                    }
                },
                "metadata": {
                    "source": "system",
                    "userId": connection_user_id,
                    "severity": "warning"
                }
            })
        except Exception as send_error:
            logger.error(f"Failed to send auth error notification to client: {send_error}")

        # Environment-based failure mode
        environment = os.getenv("ENVIRONMENT", "production").lower()
        if environment == "development":
            logger.warning(f"⚠️ DEV MODE: Allowing message despite authorization error for user {connection_user_id}")
            return True  # Fail open in development
        else:
            logger.error(f"🔒 PROD MODE: Denying message due to authorization error for user {connection_user_id}")
            return False  # Fail closed in production

    # Default: deny access if no authorization rules match
    logger.warning(
        f"⚠️ AUTHORIZATION DENIED: NO_RULE_MATCHED - "
        f"User {connection_user_id} NOT authorized for {entity_type} {entity_id}"
    )
    logger.warning(
        f"📋 Authorization attempt: triggering_user={triggering_user_id}, "
        f"connection_user={connection_user_id}, entity={entity_type}:{entity_id}"
    )

    # Send error notification to frontend
    try:
        await websocket.send_json({
            "id": f"auth-error-{random.randint(100000, 999999)}",
            "version": "2.0",
            "type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": random.randint(1000, 9999),
            "payload": {
                "entity": "system",
                "action": "authorization_denied",
                "data": {
                    "primary": {
                        "code": "NOT_AUTHORIZED",
                        "message": f"You don't have access to this {entity_type}",
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "reason": "No authorization rules matched for this resource"
                    }
                }
            },
            "metadata": {
                "source": "system",
                "userId": connection_user_id,
                "severity": "warning"
            }
        })
    except Exception as send_error:
        logger.error(f"Failed to send NOT_AUTHORIZED error to client: {send_error}")

    return False


async def _check_resource_ownership(
    connection_user_id: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check if a user owns the resource being modified in a system message.

    This ensures that system messages (from MCP operations) only reach
    the authenticated user who owns the affected resource.

    Args:
        connection_user_id: ID of the WebSocket connection user
        entity_type: Type of entity (task, project, branch, subtask, etc.)
        entity_id: ID of the entity
        metadata: Optional metadata containing additional context

    Returns:
        True if the connection user owns the resource, False otherwise
    """
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Task, ProjectGitBranch, Subtask, Project

        with get_session() as session:
            if entity_type == "task":
                # Check if the connection user owns this task
                task = session.query(Task).filter(
                    Task.id == entity_id,
                    Task.user_id == connection_user_id
                ).first()
                if task:
                    logger.debug(f"System message authorized: User {connection_user_id} owns task {entity_id}")
                    return True
                else:
                    logger.debug(f"System message denied: User {connection_user_id} does not own task {entity_id}")
                    return False

            elif entity_type == "subtask":
                # For subtasks, check ownership via parent task
                parent_task_id = metadata.get("parent_task_id") if metadata else None
                if parent_task_id:
                    task = session.query(Task).filter(
                        Task.id == parent_task_id,
                        Task.user_id == connection_user_id
                    ).first()
                    if task:
                        logger.debug(f"System message authorized: User {connection_user_id} owns parent task {parent_task_id} for subtask {entity_id}")
                        return True
                    else:
                        logger.debug(f"System message denied: User {connection_user_id} does not own parent task {parent_task_id} for subtask {entity_id}")
                        return False
                else:
                    # Fallback: try to find parent task via subtask
                    subtask = session.query(Subtask).filter(Subtask.id == entity_id).first()
                    if subtask:
                        task = session.query(Task).filter(
                            Task.id == subtask.task_id,
                            Task.user_id == connection_user_id
                        ).first()
                        if task:
                            logger.debug(f"System message authorized: User {connection_user_id} owns parent task for subtask {entity_id}")
                            return True
                    logger.debug(f"System message denied: Could not verify ownership for subtask {entity_id}")
                    return False

            elif entity_type == "branch":
                # Check if the connection user owns this branch
                branch = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.id == entity_id,
                    ProjectGitBranch.user_id == connection_user_id
                ).first()
                if branch:
                    logger.debug(f"System message authorized: User {connection_user_id} owns branch {entity_id}")
                    return True
                else:
                    logger.debug(f"System message denied: User {connection_user_id} does not own branch {entity_id}")
                    return False

            elif entity_type == "project":
                # Check if the connection user owns this project
                project = session.query(Project).filter(
                    Project.id == entity_id,
                    Project.user_id == connection_user_id
                ).first()
                if project:
                    logger.debug(f"System message authorized: User {connection_user_id} owns project {entity_id}")
                    return True
                else:
                    logger.debug(f"System message denied: User {connection_user_id} does not own project {entity_id}")
                    return False

            else:
                logger.warning(f"Unknown entity type for system message: {entity_type}")
                return False

    except Exception as e:
        logger.error(f"⚠️ AUTHORIZATION ERROR: Database error checking resource ownership: {e}")

        # Log for security audit trail
        audit_entry = {
            "event": "resource_ownership_check_failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": connection_user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "failure_reason": "database_error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "context": "system_message_authorization"
        }
        logger.warning(f"🔒 RESOURCE OWNERSHIP CHECK FAILURE AUDIT: {audit_entry}")

        # Environment-based failure mode
        environment = os.getenv("ENVIRONMENT", "production").lower()
        if environment == "development":
            logger.warning(
                f"⚠️ DEV MODE: Allowing system message despite ownership check error "
                f"for user {connection_user_id}, {entity_type} {entity_id}"
            )
            return True  # Fail open in development
        else:
            logger.error(
                f"🔒 PROD MODE: Denying system message due to ownership check error "
                f"for user {connection_user_id}, {entity_type} {entity_id}"
            )
            return False  # Fail closed in production


async def broadcast_data_change(
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Broadcast data change to all connected clients.

    Args:
        event_type: Type of event (created, updated, deleted)
        entity_type: Type of entity (task, project, branch, etc.)
        entity_id: ID of the entity
        user_id: User who triggered the change
        data: Optional data about the change
        metadata: Optional metadata
    """
    logger.warning(f"📡 🎯 WEBSOCKET ROUTE: Broadcasting {entity_type} {event_type} event from {user_id}, entity_id: {entity_id[:8]}")

    # Enhanced logging for CREATE events
    if event_type.lower() == 'created':
        logger.warning(f"🎉 CREATE EVENT BROADCAST: {entity_type} creation detected")
        logger.warning(f"🎉 CREATE EVENT: Entity Type = {entity_type}")
        logger.warning(f"🎉 CREATE EVENT: Event Type = {event_type}")
        logger.warning(f"🎉 CREATE EVENT: Entity ID = {entity_id}")
        logger.warning(f"🎉 CREATE EVENT: User ID = {user_id}")
        logger.warning(f"🎉 CREATE EVENT: Data = {data}")
        logger.warning(f"🎉 CREATE EVENT: Metadata = {metadata}")

    logger.info(f"🚨 DELETE DEBUG: Broadcasting {entity_type} {event_type} event from {user_id}, entity_id: {entity_id[:8]}")

    # Special detailed logging for DELETE operations
    if event_type.lower() in ['delete', 'deleted']:
        logger.warning(f"🗑️ DELETE BROADCAST DETAILED LOG:")
        logger.warning(f"   Event Type: {event_type}")
        logger.warning(f"   Entity Type: {entity_type}")
        logger.warning(f"   Entity ID: {entity_id}")
        logger.warning(f"   User ID: {user_id}")
        logger.warning(f"   Data: {data}")
        logger.warning(f"   Metadata: {metadata}")
        logger.warning(f"   Active Connections Count: {len(connections)}")
        logger.warning(f"   Connection Client IDs: {[conn.client_id for conn in connections.values()]}")

    # Prepare the message in v2.0 format
    message = {
        "id": f"broadcast-{entity_type}-{random.randint(100000, 999999)}",
        "version": "2.0",
        "type": "update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": random.randint(1000, 9999),
        "payload": {
            "entity": entity_type,
            "action": event_type,
            "data": {
                "primary": data if data is not None else None
            }
        },
        "metadata": {
            "source": "system",
            "userId": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            **(metadata or {})
        }
    }

    # DEBUG: Log metadata structure for completion events
    if event_type == "completed" and entity_type == "subtask":
        logger.info(f"🔍 DEBUG WEBSOCKET: Subtask completion message being sent")
        logger.info(f"🔍 DEBUG WEBSOCKET: metadata keys = {list(metadata.keys()) if metadata else 'None'}")
        logger.info(f"🔍 DEBUG WEBSOCKET: message['metadata'] keys = {list(message['metadata'].keys())}")
        if metadata and 'progress_history' in metadata:
            logger.info(f"🔍 DEBUG WEBSOCKET: metadata['progress_history'] length = {len(metadata['progress_history'])}")
            logger.info(f"🔍 DEBUG WEBSOCKET: metadata['progress_history'] type = {type(metadata['progress_history'])}")
        if 'progress_history' in message['metadata']:
            logger.info(f"🔍 DEBUG WEBSOCKET: message['metadata']['progress_history'] length = {len(message['metadata']['progress_history'])}")
        else:
            logger.warning(f"⚠️ DEBUG WEBSOCKET: progress_history NOT IN message['metadata']!")

    # Move cascade data from metadata to payload.data for frontend compatibility
    if metadata and "cascade" in metadata:
        message["payload"]["data"]["cascade"] = metadata["cascade"]
        logger.info(f"✅ Moved cascade data to payload.data for frontend: {message['payload']['data']['cascade']}")
        # Remove from metadata to avoid duplication
        del message["metadata"]["cascade"]

    # Send to authorized clients only - implement user-scoped authorization
    disconnected = []
    authorized_clients = 0

    # Track broadcast duration with Prometheus metrics
    with track_broadcast_duration(event_type, entity_type):
        # Create snapshot of connections to prevent race conditions during iteration
        async with _connections_lock:
            connections_snapshot = list(connections.values())
            total_connections = len(connections_snapshot)

        logger.info(f"🔍 DELETE DEBUG: Filtering {total_connections} total WebSocket connections for authorization")

        # Special detailed client logging for DELETE operations
        if event_type.lower() in ['delete', 'deleted']:
            logger.warning(f"🗑️ DELETE CLIENT AUTHORIZATION LOG:")
            logger.warning(f"   Total connections: {total_connections}")
            logger.warning(f"   Client details:")
            for connection in connections_snapshot:
                logger.warning(f"     Client {connection.client_id}: User {connection.user.id}, Scope: {connection.subscription.get('scope', 'Unknown')}")
    
        for connection in connections_snapshot:
            websocket = connection.websocket
            client_id = connection.client_id
            connection_user = connection.user
    
            # Check if user is authorized to receive this message
            is_authorized = await is_user_authorized_for_message(websocket, entity_type, entity_id, user_id, metadata)
    
            if is_authorized:
                # Generate unique message ID for tracking
                message_id = f"{message['id']}-{connection_user.id}"
    
                # Queue message before attempting send (optimistic queuing)
                queued_msg = QueuedMessage(
                    message_id=message_id,
                    message=message.copy(),
                    user_id=connection_user.id,
                    timestamp=datetime.now(timezone.utc),
                    retry_count=0
                )
                # Acquire lock to safely append to message queue
                async with _message_queue_lock:
                    user_message_queues[connection_user.id].append(queued_msg)
    
                try:
                    await websocket.send_json(message)
                    authorized_clients += 1
    
                    # SUCCESS: Remove from queue since delivered successfully
                    # Acquire lock to safely modify message queue
                    async with _message_queue_lock:
                        user_message_queues[connection_user.id] = [
                            msg for msg in user_message_queues[connection_user.id]
                            if msg.message_id != message_id
                        ]
    
                    # Enhanced logging for DELETE operations
                    if event_type.lower() in ['delete', 'deleted']:
                        logger.warning(f"✅ DELETE SENT to authorized client {client_id}")
                    else:
                        logger.debug(f"Sent to authorized client {client_id}")
                except WebSocketDisconnect:
                    logger.info(f"Client {client_id} disconnected gracefully during send")
                    disconnected.append(websocket)
                    # No retry - client explicitly disconnected
                except (ConnectionClosed, ConnectionClosedError):
                    logger.warning(f"❌ Connection closed unexpectedly for client {client_id}")
                    disconnected.append(websocket)
                    # No retry - connection is dead
                except (RuntimeError, Exception) as e:
                    # WebSocket state errors or unexpected errors - queue for retry
                    error_type = "WebSocket state error" if isinstance(e, RuntimeError) else "Unexpected error"
                    logger.warning(f"❌ {error_type} sending to client {client_id}: {e}")
                    if not isinstance(e, RuntimeError):
                        logger.error(f"Full traceback:", exc_info=True)
    
                    # FAILED: Update queue entry with retry info (exponential backoff)
                    # Acquire lock to safely modify message queue
                    async with _message_queue_lock:
                        for msg in user_message_queues[connection_user.id]:
                            if msg.message_id == message_id:
                                msg.retry_count += 1
                                # Exponential backoff: 5s, 10s, 20s
                                delay_seconds = RETRY_BASE_DELAY_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** (msg.retry_count - 1))
                                msg.next_retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                                logger.info(f"📬 Queued message {message_id} for retry #{msg.retry_count} in {delay_seconds}s")
                            break
    
                    disconnected.append(websocket)
            else:
                # Authorization failed - log at WARNING level for visibility
                # connection_user is already available from the loop
                user_id_str = connection_user.id
    
                logger.warning(
                    f"⚠️ NOTIFICATION BLOCKED: Unauthorized client {client_id} (user: {user_id_str}) "
                    f"skipped for {entity_type} {entity_id} - {event_type} event"
                )
    
                # Send authorization error to frontend
                try:
                    await websocket.send_json({
                        "id": f"auth-blocked-{random.randint(100000, 999999)}",
                        "version": "2.0",
                        "type": "error",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sequence": random.randint(1000, 9999),
                        "payload": {
                            "entity": "system",
                            "action": "notification_blocked",
                            "data": {
                                "primary": {
                                    "code": "NOT_AUTHORIZED",
                                    "message": f"Notification blocked: You don't have access to this {entity_type}",
                                    "entity_type": entity_type,
                                    "entity_id": entity_id,
                                    "event_type": event_type,
                                    "reason": "Authorization check failed"
                                }
                            }
                        },
                        "metadata": {
                            "source": "system",
                            "userId": user_id_str,
                            "severity": "info"
                        }
                    })
                except Exception as e:
                    logger.debug(f"Could not send authorization error to client {client_id}: {e}")
    
        # Store missed notifications for offline users
        # Extract target users from metadata or use the event creator as fallback
        target_user_ids = set()
    
        # Add the event creator as a target recipient
        if user_id:
            target_user_ids.add(user_id)
    
        # Add explicit recipients from metadata
        if metadata:
            # Check for user_ids list in metadata
            if "user_ids" in metadata and isinstance(metadata["user_ids"], list):
                target_user_ids.update(metadata["user_ids"])
            # Check for single user_id in metadata
            elif "user_id" in metadata:
                target_user_ids.add(metadata["user_id"])
            # Check for branch members (all users in a branch should get notifications)
            elif "git_branch_id" in metadata or entity_type == "branch":
                # For branch-level events, we'll rely on authorization during replay
                # rather than trying to enumerate all branch members here
                pass
    
        # Find currently connected user IDs
        connected_user_ids = set(conn.user.id for conn in connections.values())
    
        # Store notifications for users who should receive it but aren't connected
        offline_user_ids = target_user_ids - connected_user_ids
    
        if offline_user_ids:
            for offline_user_id in offline_user_ids:
                stored_id = store_missed_notification(offline_user_id, message)
                if stored_id:
                    logger.info(
                        f"💾 Stored notification {stored_id[:8]} for offline user {offline_user_id[:8]} "
                        f"({entity_type} {event_type})"
                    )
                else:
                    logger.warning(
                        f"⚠️ Failed to store notification for offline user {offline_user_id[:8]} "
                        f"({entity_type} {event_type})"
                    )
    
        if event_type.lower() in ['delete', 'deleted']:
            logger.warning(f"🗑️ DELETE BROADCAST SUMMARY: Message sent to {authorized_clients} authorized clients out of {total_connections} total connections")
        else:
            logger.info(f"Message broadcast to {authorized_clients} authorized clients out of {total_connections} total connections")
    
        # Clean up disconnected clients - single atomic deletion per connection
        for websocket in disconnected:
            connections.pop(websocket, None)

# ============================================================================
# PROMETHEUS METRICS ENDPOINT
# ============================================================================

@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint for WebSocket monitoring.
    
    Exposes metrics in Prometheus text format including:
    - websocket_connections: Active WebSocket connections by status
    - websocket_message_queue_size: Queued messages per user
    - websocket_message_retries_total: Retry attempt counters
    - websocket_message_delivery_seconds: Message delivery latency histogram
    - websocket_broadcast_duration_seconds: Broadcast operation duration histogram
    
    Returns:
        Response with metrics in Prometheus text format
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
