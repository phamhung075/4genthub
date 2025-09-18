"""
WebSocket routes for real-time data synchronization
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional, Dict, Any, Set
import json
import asyncio
from datetime import datetime, timezone
from collections import defaultdict
import random

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

# Store active connections and subscriptions
active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
connection_subscriptions: Dict[WebSocket, Dict[str, Any]] = {}

@router.websocket("/realtime")
async def realtime_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data updates.
    Clients connect here to receive notifications when data changes.
    """
    client_id = None

    try:
        # Accept connection first
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        # Generate a unique client ID
        # Try to get token from query params for authentication
        token = websocket.query_params.get("token")
        if token:
            # For now, just use the token as part of the client ID
            # In production, validate the token properly
            client_id = f"user_{hash(token) % 1000000}"
        else:
            # Anonymous connection
            client_id = f"anonymous_{random.randint(100000, 999999)}"

        logger.info(f"Client connected: {client_id}")

        # Store the connection
        active_connections[client_id].add(websocket)
        connection_subscriptions[websocket] = {
            "client_id": client_id,
            "scope": "branch",  # Default scope
            "filters": {}
        }

        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "client_id": client_id,
            "scope": "branch",
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
        # Clean up
        if client_id and websocket in connection_subscriptions:
            active_connections[client_id].discard(websocket)
            if not active_connections[client_id]:
                del active_connections[client_id]
            del connection_subscriptions[websocket]
            logger.info(f"Client {client_id} disconnected")


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
    logger.info(f"Broadcasting {entity_type} {event_type} event from {user_id}")

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

    # Send to all connected clients
    disconnected = []
    for websocket_set in active_connections.values():
        for websocket in websocket_set:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(websocket)

    # Clean up disconnected clients
    for websocket in disconnected:
        for client_id, ws_set in active_connections.items():
            ws_set.discard(websocket)
        connection_subscriptions.pop(websocket, None)