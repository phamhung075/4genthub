"""Connection MCP Controller

This controller handles only MCP protocol concerns and delegates business operations
to the ConnectionApplicationFacade following proper DDD layer separation.
Uses external description files for clean documentation separation.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING, Annotated, Union
from pydantic import Field

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from ...application.facades.connection_application_facade import ConnectionApplicationFacade
from ....task_management.interface.utils.json_parameter_parser import JSONParameterParser

logger = logging.getLogger(__name__)


class ConnectionMCPController:
    """
    MCP Controller for connection management operations.
    
    Handles only MCP protocol concerns and delegates business operations
    to the ConnectionApplicationFacade following proper DDD layer separation.
    """
    
    def __init__(self, connection_facade: ConnectionApplicationFacade):
        """
        Initialize controller with connection application facade.
        
        Args:
            connection_facade: Application facade for connection operations
        """
        self._connection_facade = connection_facade
        logger.info("ConnectionMCPController initialized")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register connection management MCP tools with the FastMCP server using external descriptions"""
        
        # Use hardcoded description for now since the description file structure is different
        manage_connection_desc = {
            "description": "🔗 UNIFIED CONNECTION MANAGEMENT ENGINE - Complete connection, health, and monitoring operations",
            "parameters": {
                "action": "Connection management action to perform. Valid actions: 'health_check', 'server_capabilities', 'connection_health', 'status', 'register_updates'",
                "include_details": "Whether to include detailed information in responses. Default: true",
                "session_id": "Client session identifier for update registration",
                "connection_id": "Specific connection identifier for targeted diagnostics",
                "client_info": "Optional client metadata for registration customization",
                "user_id": "User identifier for authentication and audit trails"
            }
        }
        
        @mcp.tool(description=manage_connection_desc["description"])
        def manage_connection(
            action: Annotated[str, Field(description=manage_connection_desc.get("parameters", {}).get("action", "Connection management action to perform"))],
            include_details: Annotated[bool, Field(description=manage_connection_desc.get("parameters", {}).get("include_details", "Whether to include detailed information"))] = True,
            connection_id: Annotated[Optional[str], Field(description=manage_connection_desc.get("parameters", {}).get("connection_id", "Specific connection identifier"))] = None,
            session_id: Annotated[Optional[str], Field(description=manage_connection_desc.get("parameters", {}).get("session_id", "Client session identifier"))] = None,
            client_info: Annotated[Optional[Union[str, Dict[str, Any]]], Field(description=manage_connection_desc.get("parameters", {}).get("client_info", "Optional client metadata (dictionary or JSON string)"))] = None,
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:
            return self.manage_connection(
                action=action,
                include_details=include_details,
                connection_id=connection_id,
                session_id=session_id,
                client_info=client_info,
                user_id=user_id
            )
    
    def manage_connection(self, action: str, include_details: bool = True, 
                         connection_id: Optional[str] = None, 
                         session_id: Optional[str] = None,
                         client_info: Optional[Union[str, Dict[str, Any]]] = None,
                         user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Unified connection management method that routes to appropriate handlers.
        
        Args:
            action: Action to perform (health_check, server_capabilities, connection_health, status, register_updates)
            include_details: Whether to include detailed information in responses
            connection_id: Specific connection identifier for targeted diagnostics
            session_id: Client session identifier for update registration
            client_info: Optional client metadata for registration customization
            user_id: User identifier for authentication and audit trails
            
        Returns:
            Formatted response dictionary for the requested action
        """
        try:
            # Parse JSON strings for dictionary parameters
            if client_info is not None:
                try:
                    client_info = JSONParameterParser.parse_dict_parameter(
                        client_info, "client_info"
                    )
                except ValueError as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_code": "INVALID_PARAMETER_FORMAT",
                        "action": action,
                        **JSONParameterParser.create_error_response(
                            "client_info", str(e), "manage_connection"
                        )
                    }
            
            # Route to appropriate handler method based on action
            if action == "health_check":
                return self.handle_health_check(include_details, user_id)
            
            elif action == "server_capabilities":
                return self.handle_server_capabilities(include_details, user_id)
            
            elif action == "connection_health":
                return self.handle_connection_health(connection_id, include_details, user_id)
            
            elif action == "status":
                return self.handle_server_status(include_details, user_id)
            
            elif action == "register_updates":
                # Require session_id for registration
                if not session_id:
                    raise ValueError("session_id is required for register_updates action")
                return self.handle_register_updates(session_id, client_info, user_id)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "available_actions": [
                        "health_check", "server_capabilities", "connection_health",
                        "status", "register_updates"
                    ],
                    "action": action
                }
                
        except Exception as e:
            logger.error(f"Error in manage_connection action {action}: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    def handle_health_check(self, include_details: bool = True, user_id: str = None) -> Dict[str, Any]:
        """Handle health check request"""
        try:
            response = self._connection_facade.check_server_health(include_details, user_id)
            return self._format_health_check_response(response)
        except Exception as e:
            logger.error(f"Error in handle_health_check: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "health_check"
            }
    
    def handle_server_capabilities(self, include_details: bool = True, user_id: str = None) -> Dict[str, Any]:
        """Handle server capabilities request"""
        try:
            response = self._connection_facade.get_server_capabilities(include_details, user_id)
            return self._format_server_capabilities_response(response)
        except Exception as e:
            logger.error(f"Error in handle_server_capabilities: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "server_capabilities"
            }
    
    def handle_connection_health(self, connection_id: Optional[str] = None, 
                                include_details: bool = True, user_id: str = None) -> Dict[str, Any]:
        """Handle connection health check request"""
        try:
            response = self._connection_facade.check_connection_health(connection_id, include_details, user_id)
            return self._format_connection_health_response(response)
        except Exception as e:
            logger.error(f"Error in handle_connection_health: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "connection_health"
            }
    
    def handle_server_status(self, include_details: bool = True, user_id: str = None) -> Dict[str, Any]:
        """Handle server status request"""
        try:
            response = self._connection_facade.get_server_status(include_details, user_id)
            return self._format_server_status_response(response)
        except Exception as e:
            logger.error(f"Error in handle_server_status: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "status"
            }
    
    def handle_register_updates(self, session_id: str, 
                               client_info: Optional[Dict[str, Any]] = None,
                               user_id: str = None) -> Dict[str, Any]:
        """Handle register status updates request"""
        try:
            response = self._connection_facade.register_for_status_updates(session_id, client_info, user_id)
            return self._format_register_updates_response(response)
        except Exception as e:
            logger.error(f"Error in handle_register_updates: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "register_updates"
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
    
    def _format_server_capabilities_response(self, response) -> Dict[str, Any]:
        """Format server capabilities response for MCP protocol"""
        if response.success:
            return {
                "success": True,
                "core_features": response.core_features,
                "available_actions": response.available_actions,
                "authentication_enabled": response.authentication_enabled,
                "mvp_mode": response.mvp_mode,
                "version": response.version,
                "total_actions": response.total_actions
            }
        else:
            return {
                "success": False,
                "error": response.error
            }
    
    def _format_connection_health_response(self, response) -> Dict[str, Any]:
        """Format connection health response for MCP protocol"""
        if response.success:
            return {
                "success": True,
                "status": response.status,
                "connection_info": response.connection_info,
                "diagnostics": response.diagnostics,
                "recommendations": response.recommendations
            }
        else:
            return {
                "success": False,
                "status": "error",
                "error": response.error
            }
    
    def _format_server_status_response(self, response) -> Dict[str, Any]:
        """Format server status response for MCP protocol"""
        if response.success:
            return {
                "success": True,
                "server_info": response.server_info,
                "connection_stats": response.connection_stats,
                "health_status": response.health_status,
                "capabilities_summary": response.capabilities_summary
            }
        else:
            return {
                "success": False,
                "error": response.error
            }
    
    def _format_register_updates_response(self, response) -> Dict[str, Any]:
        """Format register updates response for MCP protocol"""
        if response.success:
            return {
                "success": True,
                "session_id": response.session_id,
                "registered": response.registered,
                "update_info": response.update_info
            }
        else:
            return {
                "success": False,
                "session_id": response.session_id,
                "registered": False,
                "error": response.error
            } 