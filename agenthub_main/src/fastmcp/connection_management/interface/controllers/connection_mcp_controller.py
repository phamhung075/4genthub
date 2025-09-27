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
            # Don't expose internal error details to users
            return {
                "success": False,
                "status": "error",
                "message": "Health check temporarily unavailable",
                "action": "health_check"
            }
    
    
    def _format_health_check_response(self, response) -> Dict[str, Any]:
        """Format health check response for MCP protocol (sanitized for security)"""
        if response.success:
            # Sanitize the response to ensure no sensitive data is exposed
            sanitized_response = {
                "success": True,
                "status": response.status,
                "server_name": response.server_name,
                "version": response.version,
                "timestamp": response.timestamp
            }
            
            # Only include authentication status (not details)
            if hasattr(response, 'authentication') and response.authentication:
                sanitized_response["authentication"] = {
                    "enabled": response.authentication.get("enabled", False),
                    "mvp_mode": response.authentication.get("mvp_mode", False)
                }
            
            # Only include task management status (not internal details)
            if hasattr(response, 'task_management') and response.task_management:
                sanitized_response["task_management"] = {
                    "enabled": response.task_management.get("task_management_enabled", True)
                }
            
            # Sanitize environment info (already filtered in service layer, but double-check)
            if hasattr(response, 'environment') and response.environment:
                # Only include non-sensitive flags
                sanitized_env = {}
                allowed_keys = ["auth_enabled", "cursor_tools_disabled", "mvp_mode", 
                               "database_configured", "services_configured"]
                for key in allowed_keys:
                    if key in response.environment:
                        sanitized_env[key] = response.environment[key]
                if sanitized_env:
                    sanitized_response["environment"] = sanitized_env
            
            # Sanitize connection info
            if hasattr(response, 'connections') and response.connections:
                # Only include non-sensitive connection stats
                sanitized_connections = {}
                allowed_conn_keys = ["active_connections", "server_restart_count", 
                                    "uptime_seconds", "status", "broadcasting_enabled"]
                for key in allowed_conn_keys:
                    if key in response.connections:
                        sanitized_connections[key] = response.connections[key]
                if sanitized_connections:
                    sanitized_response["connections"] = sanitized_connections
            
            return sanitized_response
        else:
            # For errors, provide minimal information
            return {
                "success": False,
                "status": "error",
                "message": "Health check failed",  # Generic message instead of detailed error
                "timestamp": response.timestamp
            } 