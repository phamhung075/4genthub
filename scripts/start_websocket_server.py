#!/usr/bin/env python3
"""
Standalone WebSocket server for real-time notifications.
Runs on port 8002 to avoid conflicts with MCP server (8000).
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active connections
clients: Set[WebSocketServerProtocol] = set()

async def handle_client(websocket: WebSocketServerProtocol, path: str):
    """Handle a WebSocket client connection."""
    clients.add(websocket)
    client_id = f"client_{id(websocket)}"

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "welcome",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        }))

        logger.info(f"Client {client_id} connected")

        # Handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(websocket)
        logger.info(f"Client {client_id} disconnected")

async def broadcast(message: Dict[str, Any]):
    """Broadcast a message to all connected clients."""
    if clients:
        message_json = json.dumps(message)
        await asyncio.gather(*[client.send(message_json) for client in clients])

async def main():
    """Start the WebSocket server."""
    logger.info("Starting WebSocket server on port 8002...")
    async with websockets.serve(handle_client, "localhost", 8002):
        logger.info("WebSocket server ready at ws://localhost:8002")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())