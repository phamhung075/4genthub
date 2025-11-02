"""
Connection Management Routes

This module provides connection health check and status endpoints.
Health checks are typically unauthenticated to allow system monitoring.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from ...connection_management.application.facades.connection_application_facade import ConnectionApplicationFacade
from ...connection_management.infrastructure.repositories.in_memory_server_repository import InMemoryServerRepository
from ...connection_management.infrastructure.repositories.in_memory_connection_repository import InMemoryConnectionRepository
from ...connection_management.infrastructure.services.mcp_server_health_service import MCPServerHealthService
from ...connection_management.infrastructure.services.mcp_connection_diagnostics_service import MCPConnectionDiagnosticsService
from ...connection_management.infrastructure.services.mcp_status_broadcasting_service import MCPStatusBroadcastingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/connections", tags=["Connection Management"])

# Initialize connection facade with dependencies
_server_repository = InMemoryServerRepository()
_connection_repository = InMemoryConnectionRepository()
_health_service = MCPServerHealthService()
_diagnostics_service = MCPConnectionDiagnosticsService()
_broadcasting_service = MCPStatusBroadcastingService()

connection_facade = ConnectionApplicationFacade(
    server_repository=_server_repository,
    connection_repository=_connection_repository,
    health_service=_health_service,
    diagnostics_service=_diagnostics_service,
    broadcasting_service=_broadcasting_service
)


@router.get("/health")
async def health_check(include_details: bool = True):
    """
    Check connection and server health status.

    This endpoint is used for session keep-alive and system monitoring.
    It does not require authentication to allow external health checks.

    Args:
        include_details: Whether to include detailed health information

    Returns:
        Health status response with server information
    """
    try:
        logger.debug("Health check endpoint called")

        # Get health status from facade
        health_response = connection_facade.check_server_health(
            include_details=include_details,
            user_id=None  # Health checks don't require user context
        )

        # Convert HealthCheckResponse to dict for JSON response
        response_data = {
            "success": health_response.success,
            "status": health_response.status,
            "server_name": health_response.server_name,
            "version": health_response.version,
            "uptime_seconds": health_response.uptime_seconds,
            "timestamp": health_response.timestamp,
        }

        # Add optional details if requested and available
        if include_details:
            if health_response.authentication:
                response_data["authentication"] = health_response.authentication
            if health_response.task_management:
                response_data["task_management"] = health_response.task_management
            if health_response.environment:
                response_data["environment"] = health_response.environment
            if health_response.connections:
                response_data["connections"] = health_response.connections

        # Add error if present
        if hasattr(health_response, 'error') and health_response.error:
            response_data["error"] = health_response.error

        logger.info(f"Health check completed: {health_response.status}")
        return response_data

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        # Return a basic healthy status even on error to prevent client-side issues
        # The session keep-alive should not fail due to health check errors
        return {
            "success": True,
            "status": "healthy",
            "server_name": "AgentHub MCP Server",
            "version": "unknown",
            "uptime_seconds": 0,
            "timestamp": 0,
            "error": str(e)
        }


@router.get("/status")
async def connection_status():
    """
    Get detailed connection status and diagnostics.

    This endpoint provides more comprehensive connection information
    compared to the basic health check.

    Returns:
        Detailed connection status and diagnostics
    """
    try:
        logger.debug("Connection status endpoint called")

        # Get server capabilities which includes connection information
        capabilities_response = connection_facade.get_server_capabilities(
            include_details=True,
            user_id=None
        )

        return {
            "success": True,
            "status": "connected",
            "capabilities": {
                "version": capabilities_response.version,
                "features": capabilities_response.features if hasattr(capabilities_response, 'features') else [],
                "limits": capabilities_response.limits if hasattr(capabilities_response, 'limits') else {}
            }
        }

    except Exception as e:
        logger.error(f"Connection status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection status: {str(e)}"
        )
