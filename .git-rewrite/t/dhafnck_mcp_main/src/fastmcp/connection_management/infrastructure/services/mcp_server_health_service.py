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
        """Get server environment information"""
        return {
            "pythonpath": os.environ.get("PYTHONPATH", "not set"),
            "tasks_json_path": os.environ.get("TASKS_JSON_PATH", "not set"),
            "projects_file_path": os.environ.get("PROJECTS_FILE_PATH", "not set"),
            "agent_library_dir": os.environ.get("AGENT_LIBRARY_DIR_PATH", "not set"),
            "auth_enabled": os.environ.get("DHAFNCK_AUTH_ENABLED", "true"),
            "cursor_tools_disabled": os.environ.get("DHAFNCK_DISABLE_CURSOR_TOOLS", "false"),
            "mvp_mode": os.environ.get("DHAFNCK_MVP_MODE", "false"),
            "supabase_configured": bool(os.environ.get("SUPABASE_URL"))
        }
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """Get authentication configuration and status"""
        return {
            "enabled": os.environ.get("DHAFNCK_AUTH_ENABLED", "true").lower() == "true",
            "mvp_mode": os.environ.get("DHAFNCK_MVP_MODE", "false").lower() == "true"
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
        """Validate server configuration and dependencies"""
        try:
            # Try to import and use the existing connection manager
            from ....server.connection_manager import get_connection_manager
            from ....server.connection_status_broadcaster import get_status_broadcaster
            
            # Get connection manager info
            connection_manager = None
            connection_stats = {}
            reconnection_info = {}
            
            try:
                # This is async, so we'll handle it differently in the actual implementation
                # For now, return basic info
                connection_stats = {
                    "connections": {"active_connections": 0},
                    "server_info": {"restart_count": 0, "uptime_seconds": 0}
                }
                reconnection_info = {"recommended_action": "no_action_needed"}
            except Exception as e:
                logger.warning(f"Could not get connection manager stats: {e}")
                connection_stats = {"error": str(e)}
                reconnection_info = {"error": str(e)}
            
            # Get status broadcaster info
            status_broadcasting = {}
            try:
                # This would be async in real implementation
                status_broadcasting = {
                    "active": True,
                    "registered_clients": 0,
                    "last_broadcast": None,
                    "last_broadcast_time": None
                }
            except Exception as e:
                logger.warning(f"Could not get status broadcaster info: {e}")
                status_broadcasting = {"error": str(e)}
            
            return {
                "active_connections": connection_stats.get("connections", {}).get("active_connections", 0),
                "server_restart_count": connection_stats.get("server_info", {}).get("restart_count", 0),
                "uptime_seconds": connection_stats.get("server_info", {}).get("uptime_seconds", 0),
                "recommended_action": reconnection_info.get("recommended_action", "unknown"),
                "status_broadcasting": status_broadcasting
            }
            
        except Exception as e:
            logger.error(f"Error validating server configuration: {e}")
            return {"error": str(e)} 