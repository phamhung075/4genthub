"""
Secure Health Check System with Information Filtering

This module provides a secure health check implementation that filters sensitive
information based on user access level and security context.

Security Features:
- Client-safe responses (minimal information)
- Admin-level responses (full details)
- Role-based access control
- Environment-based filtering
- No sensitive path exposure for clients

Author: Security Enhancement
Date: 2025-01-30
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Access levels for health check responses"""
    CLIENT = "client"           # Basic status only
    AUTHENTICATED = "authenticated"  # Limited details
    ADMIN = "admin"            # Full administrative details


@dataclass
class SecurityContext:
    """Security context for health check requests"""
    access_level: AccessLevel
    user_id: Optional[str] = None
    is_internal: bool = False
    environment: str = "production"  # production, development, testing
    
    @classmethod
    def from_request(cls, user_id: str = None, is_admin: bool = False, 
                    is_internal: bool = False, environment: str = None) -> 'SecurityContext':
        """Create security context from request parameters"""
        # Determine access level
        if is_admin and is_internal:
            access_level = AccessLevel.ADMIN
        elif user_id and (is_admin or is_internal):
            access_level = AccessLevel.AUTHENTICATED
        else:
            access_level = AccessLevel.CLIENT
            
        # Get environment from ENV if not provided
        env = environment or os.environ.get("ENVIRONMENT", "production")
        
        return cls(
            access_level=access_level,
            user_id=user_id,
            is_internal=is_internal,
            environment=env
        )


class SecureHealthChecker:
    """Secure health checker with information filtering"""
    
    def __init__(self):
        self.server_name = "DhafnckMCP Server"
        self.version = "2.1.0"
        
    async def check_health(self, security_context: SecurityContext) -> Dict[str, Any]:
        """
        Perform health check with security-filtered response
        
        Args:
            security_context: Security context determining response level
            
        Returns:
            Filtered health check response
        """
        try:
            # Get basic health status (always safe)
            basic_status = await self._get_basic_status()
            
            # Filter response based on access level
            if security_context.access_level == AccessLevel.CLIENT:
                return self._get_client_response(basic_status)
            elif security_context.access_level == AccessLevel.AUTHENTICATED:
                return self._get_authenticated_response(basic_status, security_context)
            else:  # ADMIN
                return self._get_admin_response(basic_status, security_context)
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return self._get_error_response(str(e), security_context)
    
    async def _get_basic_status(self) -> Dict[str, Any]:
        """Get basic server status (internal method)"""
        try:
            # Import here to avoid circular imports
            from .connection_manager import get_connection_manager
            from .connection_status_broadcaster import get_status_broadcaster
            
            # Get connection stats
            connection_manager = await get_connection_manager()
            connection_stats = await connection_manager.get_connection_stats()
            
            # Get broadcaster status
            status_broadcaster = await get_status_broadcaster()
            
            return {
                "server_healthy": True,
                "active_connections": connection_stats["connections"]["active_connections"],
                "uptime_seconds": connection_stats["server_info"]["uptime_seconds"],
                "restart_count": connection_stats["server_info"]["restart_count"],
                "broadcaster_active": True,
                "registered_clients": status_broadcaster.get_client_count(),
                "auth_enabled": os.environ.get("DHAFNCK_AUTH_ENABLED", "true").lower() == "true",
                "mvp_mode": os.environ.get("DHAFNCK_MVP_MODE", "false").lower() == "true"
            }
            
        except Exception as e:
            logger.warning(f"Could not get full status: {e}")
            return {
                "server_healthy": True,  # Assume healthy if we can't check
                "active_connections": 0,
                "uptime_seconds": 0,
                "restart_count": 0,
                "broadcaster_active": False,
                "registered_clients": 0,
                "auth_enabled": True,
                "mvp_mode": False,
                "partial_status": True,
                "status_error": str(e)
            }
    
    def _get_client_response(self, basic_status: Dict[str, Any]) -> Dict[str, Any]:
        """Get client-safe response (minimal information)"""
        return {
            "success": True,
            "status": "healthy" if basic_status["server_healthy"] else "unhealthy",
            "timestamp": time.time()
        }
    
    def _get_authenticated_response(self, basic_status: Dict[str, Any], 
                                  security_context: SecurityContext) -> Dict[str, Any]:
        """Get authenticated user response (limited details)"""
        response = {
            "success": True,
            "status": "healthy" if basic_status["server_healthy"] else "unhealthy",
            "server_name": self.server_name,
            "version": self.version,
            "uptime_seconds": basic_status["uptime_seconds"],
            "active_connections": basic_status["active_connections"],
            "timestamp": time.time()
        }
        
        # Add restart info if relevant
        if basic_status["restart_count"] > 0:
            response["restart_count"] = basic_status["restart_count"]
            response["restart_notice"] = "Server has been restarted"
        
        return response
    
    def _get_admin_response(self, basic_status: Dict[str, Any], 
                           security_context: SecurityContext) -> Dict[str, Any]:
        """Get full administrative response (all details)"""
        # Get full environment information (admin only)
        environment = self._get_environment_info()
        authentication = self._get_authentication_info()
        task_management = self._get_task_management_info()
        connections = self._get_connections_info(basic_status)
        
        return {
            "success": True,
            "status": "healthy" if basic_status["server_healthy"] else "unhealthy",
            "server_name": self.server_name,
            "version": self.version,
            "authentication": authentication,
            "task_management": task_management,
            "environment": environment,
            "connections": connections,
            "security_context": {
                "access_level": security_context.access_level.value,
                "user_id": security_context.user_id,
                "environment": security_context.environment
            },
            "timestamp": time.time()
        }
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information (admin only)"""
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
    
    def _get_authentication_info(self) -> Dict[str, Any]:
        """Get authentication information"""
        return {
            "enabled": os.environ.get("DHAFNCK_AUTH_ENABLED", "true").lower() == "true",
            "mvp_mode": os.environ.get("DHAFNCK_MVP_MODE", "false").lower() == "true"
        }
    
    def _get_task_management_info(self) -> Dict[str, Any]:
        """Get task management information"""
        return {
            "task_management_enabled": True,
            "enabled_tools_count": 0,
            "total_tools_count": 0,
            "enabled_tools": []
        }
    
    def _get_connections_info(self, basic_status: Dict[str, Any]) -> Dict[str, Any]:
        """Get connections information"""
        return {
            "active_connections": basic_status["active_connections"],
            "server_restart_count": basic_status["restart_count"],
            "uptime_seconds": basic_status["uptime_seconds"],
            "recommended_action": "no_action_needed" if basic_status["active_connections"] > 0 else "check_client_connection",
            "status_broadcasting": {
                "active": basic_status["broadcaster_active"],
                "registered_clients": basic_status["registered_clients"],
                "last_broadcast": None,
                "last_broadcast_time": None
            }
        }
    
    def _get_error_response(self, error: str, security_context: SecurityContext) -> Dict[str, Any]:
        """Get error response filtered by access level"""
        if security_context.access_level == AccessLevel.CLIENT:
            return {
                "success": False,
                "status": "error",
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "status": "error",
                "error": error if security_context.access_level == AccessLevel.ADMIN else "Service temporarily unavailable",
                "timestamp": time.time()
            }


# Global instance
_secure_health_checker = SecureHealthChecker()


async def secure_health_check(user_id: str = None, is_admin: bool = False, 
                             is_internal: bool = False, environment: str = None) -> Dict[str, Any]:
    """
    Perform secure health check with automatic access level determination
    
    Args:
        user_id: User identifier (None for anonymous)
        is_admin: Whether user has admin privileges
        is_internal: Whether request is from internal system
        environment: Environment context (production, development, etc.)
        
    Returns:
        Security-filtered health check response
    """
    security_context = SecurityContext.from_request(
        user_id=user_id,
        is_admin=is_admin,
        is_internal=is_internal,
        environment=environment
    )
    
    return await _secure_health_checker.check_health(security_context)


async def client_health_check() -> Dict[str, Any]:
    """Get client-safe health check (minimal information)"""
    return await secure_health_check()


async def admin_health_check(user_id: str = "admin") -> Dict[str, Any]:
    """Get full admin health check (all details)"""
    return await secure_health_check(
        user_id=user_id,
        is_admin=True,
        is_internal=True
    ) 