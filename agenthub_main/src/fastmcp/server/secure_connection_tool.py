"""
Secure Connection Management Tool

This module provides secure health check endpoints with proper information filtering
based on access levels. It demonstrates the secure implementation that should be
used for client-facing health checks.

Security Features:
- Client-safe health check (minimal info)
- Authenticated health check (limited details)
- Admin health check (full details)
- Proper access control
- No sensitive information exposure

Author: Security Enhancement
Date: 2025-01-30
"""

import logging
from typing import Any

from .context import Context
from .secure_health_check import (
    admin_health_check,
    client_health_check,
    secure_health_check,
)

logger = logging.getLogger(__name__)


async def secure_connection_check(ctx: Context, access_level: str = "client", **kwargs) -> dict[str, Any]:
    """
    Secure connection health check with access level control
    
    Args:
        ctx: MCP context with session information
        access_level: Access level - "client", "authenticated", or "admin"
        **kwargs: Additional parameters
    
    Returns:
        Security-filtered health check response
    """
    try:
        if access_level == "client":
            # Client-safe response (minimal information)
            return await client_health_check()
            
        elif access_level == "authenticated":
            # Authenticated user response (limited details)
            user_id = getattr(ctx, 'user_id', 'authenticated_user') if ctx else 'authenticated_user'
            return await secure_health_check(
                user_id=user_id,
                is_admin=False,
                is_internal=False
            )
            
        elif access_level == "admin":
            # Admin response (full details)
            user_id = getattr(ctx, 'user_id', 'admin_user') if ctx else 'admin_user'
            return await admin_health_check(user_id=user_id)
            
        else:
            return {
                "success": False,
                "error": f"Invalid access level: {access_level}",
                "valid_levels": ["client", "authenticated", "admin"],
                "timestamp": 0
            }
            
    except Exception as e:
        logger.error(f"Secure connection check failed: {e}")
        return {
            "success": False,
            "status": "error",
            "error": "Service temporarily unavailable",
            "timestamp": 0
        }


def register_secure_connection_tool(server):
    """Register the secure connection tool with the MCP server"""
    
    @server.tool(
        name="secure_health_check",
        description="""🔒 SECURE HEALTH CHECK - Security-filtered server health information

This tool provides server health information with appropriate security filtering
based on access level. Different access levels return different amounts of information:

• CLIENT: Basic status only (healthy/unhealthy, timestamp)
• AUTHENTICATED: Limited details (server name, version, uptime, connections)  
• ADMIN: Full details (all system information, paths, configuration)

Parameters:
- access_level: "client" (default), "authenticated", or "admin"

Security Features:
- No sensitive paths exposed to clients
- Role-based information filtering
- Minimal information disclosure
- Production-safe defaults

Example Usage:
- Client: secure_health_check(access_level="client")
- Auth: secure_health_check(access_level="authenticated") 
- Admin: secure_health_check(access_level="admin")"""
    )
    async def secure_health_check_tool(ctx: Context, access_level: str = "client") -> str:
        """Secure health check tool with access level control"""
        try:
            result = await secure_connection_check(ctx, access_level)
            
            if result["success"]:
                return _format_secure_health_response(result, access_level)
            else:
                return f"❌ Health Check Failed\n\nError: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Secure health check tool error: {e}")
            return "❌ Health Check Error\n\nService temporarily unavailable"


def _format_secure_health_response(result: dict[str, Any], access_level: str) -> str:
    """Format secure health check response for display"""
    
    if access_level == "client":
        # Client-safe formatting (minimal info)
        status_emoji = "🟢" if result["status"] == "healthy" else "🔴"
        return f"""{status_emoji} Server Status: {result["status"].upper()}

Timestamp: {result["timestamp"]}

This is a client-safe health check with minimal information disclosure."""

    elif access_level == "authenticated":
        # Authenticated user formatting (limited details)
        status_emoji = "🟢" if result["status"] == "healthy" else "🔴"
        uptime_hours = result.get("uptime_seconds", 0) / 3600
        
        response = f"""{status_emoji} Server Health Check - Authenticated View

**Server Information:**
• Name: {result.get("server_name", "Unknown")}
• Version: {result.get("version", "Unknown")}
• Status: {result["status"].upper()}
• Uptime: {uptime_hours:.1f} hours
• Active Connections: {result.get("active_connections", 0)}"""

        if result.get("restart_count", 0) > 0:
            response += f"\n• Restart Count: {result['restart_count']}"
            response += f"\n• Notice: {result.get('restart_notice', '')}"

        response += f"\n\nTimestamp: {result['timestamp']}"
        return response

    else:  # admin
        # Admin formatting (full details)
        status_emoji = "🟢" if result["status"] == "healthy" else "🔴"
        uptime_hours = result.get("uptime_seconds", 0) / 3600
        
        response = f"""{status_emoji} Server Health Check - Administrative View

**Server Information:**
• Name: {result.get("server_name", "Unknown")}
• Version: {result.get("version", "Unknown")}
• Status: {result["status"].upper()}
• Uptime: {uptime_hours:.1f} hours"""

        # Authentication info
        auth = result.get("authentication", {})
        response += f"""

**Authentication:**
• Enabled: {auth.get("enabled", False)}
• MVP Mode: {auth.get("mvp_mode", False)}"""

        # Task management info
        task_mgmt = result.get("task_management", {})
        response += f"""

**Task Management:**
• Enabled: {task_mgmt.get("task_management_enabled", False)}
• Tools Count: {task_mgmt.get("enabled_tools_count", 0)}/{task_mgmt.get("total_tools_count", 0)}"""

        # Connection info
        connections = result.get("connections", {})
        response += f"""

**Connections:**
• Active: {connections.get("active_connections", 0)}
• Restart Count: {connections.get("server_restart_count", 0)}
• Recommended Action: {connections.get("recommended_action", "unknown")}"""

        # Broadcasting info
        broadcasting = connections.get("status_broadcasting", {})
        response += f"""
• Broadcasting Active: {broadcasting.get("active", False)}
• Registered Clients: {broadcasting.get("registered_clients", 0)}"""

        # Environment info (admin only)
        env = result.get("environment", {})
        if env:
            response += f"""

**Environment Configuration:**
• Python Path: {env.get("pythonpath", "not set")}
• Tasks JSON Path: {env.get("tasks_json_path", "not set")}
• Projects File Path: {env.get("projects_file_path", "not set")}
• Agent Library Dir: {env.get("agent_library_dir", "not set")}
• Cursor Tools Disabled: {env.get("cursor_tools_disabled", "false")}
• Supabase Configured: {env.get("supabase_configured", False)}"""

        # Security context
        security_ctx = result.get("security_context", {})
        response += f"""

**Security Context:**
• Access Level: {security_ctx.get("access_level", "unknown")}
• User ID: {security_ctx.get("user_id", "unknown")}
• Environment: {security_ctx.get("environment", "unknown")}"""

        response += f"\n\nTimestamp: {result['timestamp']}"
        return response 