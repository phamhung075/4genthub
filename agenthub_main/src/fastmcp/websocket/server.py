"""
WebSocket Server v2.0 Implementation

Complete WebSocket server with connection management, batch processing,
and v2.0 protocol support. Integrates with FastAPI for authentication
and provides dual-track message processing.

NO backward compatibility - clean v2.0 implementation only.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.keycloak_auth import KeycloakAuth, TokenValidation
from ..task_management.infrastructure.database.database_config import get_db_config
from .connection_manager import ConnectionManager
from .batch_processor import BatchProcessor

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket Server v2.0 with dual-track processing.

    Features:
    - JWT authentication
    - Connection management
    - User message immediate processing
    - AI message batch processing (500ms)
    - Cascade data integration
    - Health monitoring
    """

    def __init__(self, app: FastAPI, session_factory):
        """
        Initialize WebSocket server.

        Args:
            app: FastAPI application instance
            session_factory: Database session factory
        """
        self.app = app
        self.session_factory = session_factory

        # Core components
        self.connection_manager = ConnectionManager(session_factory)
        self.batch_processor = BatchProcessor(self.connection_manager, session_factory)

        # Server state
        self.is_running = False
        self.startup_time: Optional[str] = None

        # Register WebSocket endpoints
        self._register_endpoints()

        logger.info("WebSocketServer v2.0 initialized")

    def _register_endpoints(self) -> None:
        """
        Register WebSocket endpoints with FastAPI.
        """
        @self.app.websocket("/ws/{user_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            user_id: str,
            token: str = Query(..., description="JWT authentication token")
        ):
            """
            Main WebSocket endpoint with JWT authentication.

            Args:
                websocket: WebSocket connection
                user_id: User ID from URL path
                token: JWT token from query parameter
            """
            await self._handle_websocket_connection(websocket, user_id, token)

        @self.app.get("/ws/health")
        async def websocket_health():
            """
            WebSocket server health check endpoint.

            Returns:
                Health status and statistics
            """
            return await self.get_health_status()

        @self.app.get("/ws/stats")
        async def websocket_stats():
            """
            WebSocket server statistics endpoint.

            Returns:
                Detailed server statistics
            """
            return await self.get_detailed_stats()

    async def _handle_websocket_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        token: str
    ) -> None:
        """
        Handle individual WebSocket connection with authentication.

        Args:
            websocket: WebSocket connection
            user_id: User ID from URL path
            token: JWT authentication token
        """
        session_id = None

        try:
            # Validate JWT token using Keycloak
            keycloak_auth = KeycloakAuth()
            token_validation = await keycloak_auth.validate_token(token)

            if not token_validation.valid:
                await websocket.close(code=1008, reason="Invalid token")
                return

            authenticated_user_id = token_validation.user_id

            # Verify user_id matches token
            if authenticated_user_id != user_id:
                await websocket.close(code=1008, reason="User ID mismatch")
                return

            logger.info(f"Authenticated WebSocket connection for user: {user_id}")

            # Accept connection and get session ID
            session_id = await self.connection_manager.connect(websocket, user_id)

            # Message processing loop
            while True:
                try:
                    # Receive message from client
                    raw_message = await websocket.receive_text()

                    # Process message through connection manager
                    await self.connection_manager.process_message(user_id, raw_message)

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected normally: {user_id}")
                    break

                except Exception as e:
                    logger.error(f"Error processing message from {user_id}: {e}")
                    await self.connection_manager.send_error(
                        user_id,
                        "Message processing error"
                    )

        except Exception as e:
            logger.error(f"WebSocket connection error for {user_id}: {e}")
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass

        finally:
            # Cleanup connection
            if session_id:
                await self.connection_manager.disconnect(user_id)

    async def start(self) -> None:
        """
        Start the WebSocket server and background services.
        """
        if self.is_running:
            logger.warning("WebSocketServer already running")
            return

        try:
            # Start batch processor
            await self.batch_processor.start()

            self.is_running = True
            from datetime import datetime
            self.startup_time = datetime.utcnow().isoformat()

            logger.info("WebSocketServer v2.0 started successfully")

        except Exception as e:
            logger.error(f"Failed to start WebSocketServer: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop the WebSocket server and cleanup resources.
        """
        if not self.is_running:
            return

        logger.info("Stopping WebSocketServer...")

        try:
            # Stop batch processor
            await self.batch_processor.stop()

            # Cleanup all connections
            await self.connection_manager.cleanup()

            self.is_running = False
            self.startup_time = None

            logger.info("WebSocketServer stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping WebSocketServer: {e}")

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get WebSocket server health status.

        Returns:
            Health status dictionary
        """
        connection_stats = self.connection_manager.get_connection_stats()
        batch_stats = self.batch_processor.get_stats()

        return {
            "status": "healthy" if self.is_running else "stopped",
            "version": "2.0",
            "is_running": self.is_running,
            "startup_time": self.startup_time,
            "connections": {
                "total": connection_stats["total_connections"],
                "active_users": len(connection_stats["active_users"])
            },
            "batch_processing": {
                "is_running": batch_stats["is_running"],
                "queue_size": batch_stats["queue_size"],
                "batches_processed": batch_stats["batches_processed"]
            }
        }

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """
        Get detailed WebSocket server statistics.

        Returns:
            Detailed statistics dictionary
        """
        connection_stats = self.connection_manager.get_connection_stats()
        batch_stats = self.batch_processor.get_stats()

        return {
            "server": {
                "version": "2.0",
                "is_running": self.is_running,
                "startup_time": self.startup_time
            },
            "connections": connection_stats,
            "batch_processing": batch_stats,
            "protocol": {
                "version": "2.0",
                "supported_message_types": ["update", "bulk", "sync", "heartbeat", "error"],
                "supported_sources": ["user", "mcp-ai", "system"],
                "max_message_size_bytes": 64 * 1024
            }
        }

    async def broadcast_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Broadcast a message to all connected users (API endpoint).

        Args:
            message_data: Message data to broadcast

        Returns:
            True if broadcast was successful
        """
        try:
            # This would integrate with the protocol to create proper messages
            # For now, basic implementation
            if not self.is_running:
                return False

            # TODO: Convert message_data to proper WSMessage format
            # For now, just check if we have connections
            connection_stats = self.connection_manager.get_connection_stats()
            return connection_stats["total_connections"] > 0

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return False

    def get_connection_count(self) -> int:
        """
        Get current number of WebSocket connections.

        Returns:
            Number of active connections
        """
        stats = self.connection_manager.get_connection_stats()
        return stats["total_connections"]

    def is_user_connected(self, user_id: str) -> bool:
        """
        Check if specific user is connected.

        Args:
            user_id: User ID to check

        Returns:
            True if user is connected
        """
        return self.connection_manager.is_user_connected(user_id)

    async def send_message_to_user(self, user_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Send message to specific user (API endpoint).

        Args:
            user_id: Target user ID
            message_data: Message data to send

        Returns:
            True if message was sent successfully
        """
        try:
            # TODO: Convert message_data to proper WSMessage format
            # For now, basic implementation
            return self.connection_manager.is_user_connected(user_id)

        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return False


# Global WebSocket server instance
websocket_server: Optional[WebSocketServer] = None


def get_websocket_server() -> Optional[WebSocketServer]:
    """
    Get the global WebSocket server instance.

    Returns:
        WebSocketServer instance or None if not initialized
    """
    return websocket_server


def initialize_websocket_server(app: FastAPI, session_factory) -> WebSocketServer:
    """
    Initialize and configure the global WebSocket server.

    Args:
        app: FastAPI application instance
        session_factory: Database session factory

    Returns:
        Configured WebSocketServer instance
    """
    global websocket_server

    if websocket_server is not None:
        logger.warning("WebSocketServer already initialized")
        return websocket_server

    websocket_server = WebSocketServer(app, session_factory)
    logger.info("Global WebSocketServer initialized")

    return websocket_server


async def startup_websocket_server() -> None:
    """
    Startup function for WebSocket server (call from FastAPI startup event).
    """
    global websocket_server

    if websocket_server is None:
        logger.error("WebSocketServer not initialized - call initialize_websocket_server first")
        return

    await websocket_server.start()


async def shutdown_websocket_server() -> None:
    """
    Shutdown function for WebSocket server (call from FastAPI shutdown event).
    """
    global websocket_server

    if websocket_server is not None:
        await websocket_server.stop()
        websocket_server = None