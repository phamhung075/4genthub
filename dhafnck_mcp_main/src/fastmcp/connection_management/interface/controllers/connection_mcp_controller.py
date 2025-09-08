"""Simplified Connection MCP Controller

This controller provides a basic health check endpoint for system monitoring.
Simplified from the original complex controller to focus only on essential health monitoring.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING, Annotated
from pydantic import Field

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from ...application.facades.connection_application_facade import ConnectionApplicationFacade

logger = logging.getLogger(__name__)


class ConnectionMCPController:
    """
    Simplified MCP Controller for basic health monitoring.
    
    Provides only a health check endpoint for system monitoring.
    Removed complex features that were not being used by the frontend.
    """
    
    def __init__(self, connection_facade: ConnectionApplicationFacade):
        """
        Initialize controller with connection application facade.
        
        Args:
            connection_facade: Application facade for connection operations
        """
        self._connection_facade = connection_facade
        logger.info("Simplified ConnectionMCPController initialized with health check only")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register simplified health check tool with the FastMCP server"""
        
        @mcp.tool(description="Basic health check endpoint for system monitoring")
        def manage_connection(
            include_details: Annotated[bool, Field(description="Whether to include detailed information in health response")] = True,
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:
            return self.health_check(
                include_details=include_details,
                user_id=user_id
            )
    
    def health_check(self, include_details: bool = True, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Simplified health check method - the only function this controller provides.
        
        Args:
            include_details: Whether to include detailed information in responses
            user_id: User identifier for authentication and audit trails
            
        Returns:
            Formatted health check response dictionary
        """
        try:
            response = self._connection_facade.check_server_health(include_details, user_id)
            return self._format_health_check_response(response)
        except Exception as e:
            logger.error(f"Error in health_check: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "health_check"
            }
    
    
    def _format_health_check_response(self, response) -> Dict[str, Any]:
        """Format health check response for MCP protocol"""
        if response.success:
            return {
                "success": True,
                "status": response.status,
                "server_name": response.server_name,
                "version": response.version,
                "authentication": response.authentication,
                "task_management": response.task_management,
                "environment": response.environment,
                "connections": response.connections,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "status": "error",
                "error": response.error,
                "timestamp": response.timestamp
            } 