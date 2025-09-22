"""
FastAPI WebSocket Integration for v2.0 Protocol

Integrates WebSocket server with existing FastMCP server infrastructure.
Provides startup/shutdown hooks and database session management.

NO backward compatibility - clean v2.0 implementation only.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from ..task_management.infrastructure.database.database_config import get_db_config
from .server import WebSocketServer, initialize_websocket_server

logger = logging.getLogger(__name__)


async def get_database_session_factory():
    """
    Get database session factory for WebSocket server.

    Returns:
        Database session factory function
    """
    db_config = get_db_config()
    if not db_config or not db_config.get_async_session:
        raise RuntimeError("Database configuration not available")

    return db_config.get_async_session


def setup_websocket_integration(app: FastAPI) -> WebSocketServer:
    """
    Set up WebSocket v2.0 integration with FastAPI application.

    Args:
        app: FastAPI application instance

    Returns:
        Configured WebSocketServer instance

    Raises:
        RuntimeError: If database configuration is not available
    """
    logger.info("Setting up WebSocket v2.0 integration...")

    # Get database session factory
    try:
        db_config = get_db_config()
        if not db_config or not db_config.get_async_session:
            raise RuntimeError("Database configuration not available")

        session_factory = db_config.get_async_session
        logger.info("Database session factory configured for WebSocket server")

    except Exception as e:
        logger.error(f"Failed to configure database for WebSocket server: {e}")
        raise RuntimeError(f"WebSocket database setup failed: {e}")

    # Initialize WebSocket server
    try:
        websocket_server = initialize_websocket_server(app, session_factory)
        logger.info("WebSocket server initialized successfully")

        # Add startup and shutdown event handlers
        @app.on_event("startup")
        async def start_websocket_server():
            """Start WebSocket server on FastAPI startup."""
            try:
                await websocket_server.start()
                logger.info("WebSocket server started on FastAPI startup")
            except Exception as e:
                logger.error(f"Failed to start WebSocket server: {e}")
                # Don't raise - let the main server continue

        @app.on_event("shutdown")
        async def stop_websocket_server():
            """Stop WebSocket server on FastAPI shutdown."""
            try:
                await websocket_server.stop()
                logger.info("WebSocket server stopped on FastAPI shutdown")
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")

        logger.info("WebSocket v2.0 integration completed successfully")
        return websocket_server

    except Exception as e:
        logger.error(f"Failed to initialize WebSocket server: {e}")
        raise RuntimeError(f"WebSocket server initialization failed: {e}")


def get_websocket_endpoints_info() -> dict:
    """
    Get information about WebSocket endpoints for documentation.

    Returns:
        Dictionary with endpoint information
    """
    return {
        "websocket_endpoint": "/ws/{user_id}",
        "health_endpoint": "/ws/health",
        "stats_endpoint": "/ws/stats",
        "protocol_version": "2.0",
        "authentication": "JWT token required (query parameter)",
        "supported_message_types": ["update", "bulk", "sync", "heartbeat", "error"],
        "features": [
            "Real-time user updates (immediate processing)",
            "AI message batching (500ms intervals)",
            "Cascade data integration",
            "JWT authentication",
            "Connection management",
            "Health monitoring"
        ]
    }


def add_websocket_routes_to_existing_app(app: FastAPI) -> None:
    """
    Add WebSocket routes to an existing FastAPI app without full integration.

    Use this if you only want to add the routes without startup/shutdown hooks.

    Args:
        app: Existing FastAPI application
    """
    try:
        # Get database session factory
        db_config = get_db_config()
        if not db_config or not db_config.get_async_session:
            logger.warning("Database not configured - WebSocket routes will not work properly")
            return

        session_factory = db_config.get_async_session

        # Create WebSocket server instance without global initialization
        websocket_server = WebSocketServer(app, session_factory)

        logger.info("WebSocket routes added to existing FastAPI app")

    except Exception as e:
        logger.error(f"Failed to add WebSocket routes: {e}")


# Convenience function for FastMCP server integration
def integrate_websocket_with_fastmcp(fastmcp_server) -> Optional[WebSocketServer]:
    """
    Integrate WebSocket v2.0 server with FastMCP server.

    This function provides easy integration with the existing FastMCP
    server infrastructure used by agenthub.

    Args:
        fastmcp_server: FastMCP server instance

    Returns:
        WebSocketServer instance if successful, None otherwise
    """
    try:
        # Get the FastAPI app from FastMCP server
        if hasattr(fastmcp_server, 'app'):
            app = fastmcp_server.app
        elif hasattr(fastmcp_server, '_app'):
            app = fastmcp_server._app
        else:
            logger.error("Cannot find FastAPI app in FastMCP server")
            return None

        # Set up WebSocket integration
        websocket_server = setup_websocket_integration(app)

        logger.info("WebSocket v2.0 successfully integrated with FastMCP server")
        return websocket_server

    except Exception as e:
        logger.error(f"Failed to integrate WebSocket with FastMCP: {e}")
        return None


# Health check integration
def add_websocket_health_to_main_health(main_health_response: dict, websocket_server: Optional[WebSocketServer]) -> dict:
    """
    Add WebSocket health information to main server health response.

    Args:
        main_health_response: Main server health response dictionary
        websocket_server: WebSocket server instance (optional)

    Returns:
        Updated health response with WebSocket information
    """
    if websocket_server:
        try:
            # Get WebSocket health status
            import asyncio
            ws_health = asyncio.run(websocket_server.get_health_status())

            main_health_response["websocket"] = {
                "status": ws_health["status"],
                "version": ws_health["version"],
                "connections": ws_health["connections"]["total"],
                "active_users": ws_health["connections"]["active_users"],
                "batch_processing": ws_health["batch_processing"]["is_running"]
            }

        except Exception as e:
            main_health_response["websocket"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        main_health_response["websocket"] = {
            "status": "not_configured"
        }

    return main_health_response