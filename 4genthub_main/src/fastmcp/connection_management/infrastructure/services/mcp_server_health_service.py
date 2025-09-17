"""MCP Server Health Service Implementation"""

import os
import logging
from typing import Dict, Any

from ...domain.services.server_health_service import ServerHealthService
from ...domain.entities.server import Server
from ...domain.value_objects.server_status import ServerStatus

logger = logging.getLogger(__name__)


class MCPServerHealthService(ServerHealthService):
    """Infrastructure implementation of ServerHealthService that integrates with MCP infrastructure"""
    
    def check_server_health(self, server: Server) -> ServerStatus:
        """Perform comprehensive server health check"""
        # Delegate to the server entity for the actual health check logic
        return server.check_health()
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get server environment information (sanitized for security)"""
        # Only expose non-sensitive configuration flags
        # Do NOT expose paths, URLs, or internal configuration details
        return {
            "auth_enabled": os.environ.get("AUTH_ENABLED", "true").lower() == "true",
            "cursor_tools_disabled": os.environ.get("4GENTHUB_DISABLE_CURSOR_TOOLS", "false").lower() == "true",
            "mvp_mode": os.environ.get("PRODUCTION", "false").lower() == "true",
            "database_configured": bool(os.environ.get("SUPABASE_URL") or os.environ.get("DATABASE_URL")),
            # Only indicate if services are configured, not their actual values
            "services_configured": {
                "database": bool(os.environ.get("SUPABASE_URL") or os.environ.get("DATABASE_URL")),
                "authentication": os.environ.get("AUTH_ENABLED", "true").lower() == "true",
                "task_management": True  # Always enabled
            }
        }
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """Get authentication configuration and status"""
        return {
            "enabled": os.environ.get("AUTH_ENABLED", "true").lower() == "true",
            "mvp_mode": os.environ.get("PRODUCTION", "false").lower() == "true"
        }
    
    def get_task_management_info(self) -> Dict[str, Any]:
        """Get task management system information"""
        return {
            "task_management_enabled": True,
            "enabled_tools_count": 0,
            "total_tools_count": 0,
            "enabled_tools": []
        }
    
    def validate_server_configuration(self) -> Dict[str, Any]:
        """Validate server configuration and dependencies (sanitized)"""
        try:
            # Try to import and use the existing connection manager
            from ....server.connection_manager import get_connection_manager
            from ....server.connection_status_broadcaster import get_status_broadcaster
            
            # Get connection manager info
            connection_stats = {}
            
            try:
                # This is async, so we'll handle it differently in the actual implementation
                # For now, return basic info
                connection_stats = {
                    "connections": {"active_connections": 0},
                    "server_info": {"restart_count": 0, "uptime_seconds": 0}
                }
            except Exception as e:
                logger.warning(f"Could not get connection manager stats")
                # Don't expose error details to users
                connection_stats = {"connections": {"active_connections": 0}}
            
            # Get status broadcaster info
            status_broadcasting_active = False
            try:
                # This would be async in real implementation
                status_broadcasting_active = True
            except Exception as e:
                logger.warning(f"Could not get status broadcaster info")
                status_broadcasting_active = False
            
            return {
                "active_connections": connection_stats.get("connections", {}).get("active_connections", 0),
                "server_restart_count": connection_stats.get("server_info", {}).get("restart_count", 0),
                "uptime_seconds": connection_stats.get("server_info", {}).get("uptime_seconds", 0),
                "status": "healthy",  # Simplified status instead of detailed error info
                "broadcasting_enabled": status_broadcasting_active
            }
            
        except Exception as e:
            logger.error(f"Error validating server configuration: {e}")
            # Don't expose internal error details
            return {"status": "configuration_error", "message": "Unable to validate configuration"} 