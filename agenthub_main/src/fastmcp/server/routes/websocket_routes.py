"""
WebSocket routes for real-time data synchronization
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Optional, Dict, Any, Set
import json
import asyncio
from datetime import datetime, timezone
from collections import defaultdict
import random
import os

# Import authentication utilities for JWT validation
from fastmcp.auth.keycloak_dependencies import validate_keycloak_token, validate_local_token
from fastmcp.auth.domain.entities.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

# Store active connections and subscriptions
active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
connection_subscriptions: Dict[WebSocket, Dict[str, Any]] = {}
# Store user information for each WebSocket connection
connection_users: Dict[WebSocket, User] = {}


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
                logger.warning(f"Keycloak token validation failed: {e.detail}")
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
async def realtime_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data updates.
    Clients connect here to receive notifications when data changes.
    Now requires JWT authentication for security.
    """
    client_id = None
    authenticated_user = None

    try:
        # Get token from query params BEFORE accepting connection
        token = websocket.query_params.get("token")

        # Validate JWT token BEFORE accepting connection
        authenticated_user = await validate_websocket_token(token)
        if not authenticated_user:
            logger.warning("WebSocket connection rejected: Invalid or missing JWT token")
            await websocket.close(code=4001, reason="Authentication required")
            return

        # Accept connection only after successful authentication
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for authenticated user: {authenticated_user.id}")

        # Generate a unique client ID using authenticated user ID
        connection_id = random.randint(100000, 999999)  # Unique per connection
        client_id = f"user_{authenticated_user.id}_{connection_id}"

        logger.info(f"Authenticated client connected: {client_id}")

        # Store the connection with user authentication context
        active_connections[client_id].add(websocket)
        connection_subscriptions[websocket] = {
            "client_id": client_id,
            "user_id": authenticated_user.id,  # Store authenticated user ID
            "user_email": authenticated_user.email,
            "scope": "branch",  # Default scope
            "filters": {}
        }
        # Store user object for authorization checks
        connection_users[websocket] = authenticated_user

        # Send welcome message with authenticated user info
        await websocket.send_json({
            "type": "welcome",
            "client_id": client_id,
            "user_id": authenticated_user.id,
            "user_email": authenticated_user.email,
            "scope": "branch",
            "authenticated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe":
                    # Update subscription scope
                    scope = data.get("scope", "branch")
                    filters = data.get("filters", {})

                    connection_subscriptions[websocket].update({
                        "scope": scope,
                        "filters": filters
                    })

                    await websocket.send_json({
                        "type": "subscribed",
                        "scope": scope,
                        "filters": filters
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Clean up connection data
        if client_id and websocket in connection_subscriptions:
            active_connections[client_id].discard(websocket)
            if not active_connections[client_id]:
                del active_connections[client_id]
            del connection_subscriptions[websocket]

        # Clean up user authentication data
        if websocket in connection_users:
            del connection_users[websocket]

        if authenticated_user:
            logger.info(f"Authenticated client {client_id} (user: {authenticated_user.id}) disconnected")
        else:
            logger.info(f"Unauthenticated connection attempt terminated")


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
    if websocket not in connection_users:
        logger.warning("WebSocket connection has no associated user - denying access")
        return False

    connection_user = connection_users[websocket]
    connection_user_id = connection_user.id

    # Rule 1: Users always receive messages about their own actions
    if connection_user_id == triggering_user_id:
        logger.debug(f"User {connection_user_id} authorized to receive message about their own {entity_type}")
        return True

    # Rule 2: Check entity-specific authorization based on user ownership/access
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Task, ProjectGitBranch, TaskSubtask, Project

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
        logger.error(f"Error checking user authorization: {e}")
        # Fail closed - deny access on errors
        return False

    # Default: deny access if no authorization rules match
    logger.debug(f"User {connection_user_id} NOT authorized for {entity_type} {entity_id}")
    return False


async def broadcast_data_change(
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
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
    logger.info(f"Broadcasting {entity_type} {event_type} event from {user_id}, entity_id: {entity_id[:8]}")

    # Prepare the message
    message = {
        "type": "status_update",
        "event_type": event_type,
        "user_id": user_id,
        "data": data or {},
        "metadata": {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
    }

    # Send to authorized clients only - implement user-scoped authorization
    disconnected = []
    authorized_clients = 0
    total_connections = sum(len(ws_set) for ws_set in active_connections.values())
    logger.info(f"Filtering {total_connections} total WebSocket connections for authorization")

    for client_id, websocket_set in active_connections.items():
        for websocket in websocket_set:
            # Check if user is authorized to receive this message
            is_authorized = await is_user_authorized_for_message(websocket, entity_type, entity_id, user_id, metadata)

            if is_authorized:
                try:
                    await websocket.send_json(message)
                    authorized_clients += 1
                    logger.debug(f"Sent to authorized client {client_id}")
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")
                    disconnected.append(websocket)
            else:
                logger.debug(f"Skipped unauthorized client {client_id} for {entity_type} {entity_id}")

    logger.info(f"Message broadcast to {authorized_clients} authorized clients out of {total_connections} total connections")

    # Clean up disconnected clients
    for websocket in disconnected:
        for client_id, ws_set in active_connections.items():
            ws_set.discard(websocket)
        connection_subscriptions.pop(websocket, None)
        connection_users.pop(websocket, None)  # Clean up user authentication data