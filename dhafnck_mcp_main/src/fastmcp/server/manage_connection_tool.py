"""
Unified Connection Management Tool for MCP Server (LEGACY)

⚠️  DEPRECATION WARNING: This module is being replaced by a DDD-compliant implementation.
    Please migrate to the new connection management system at:
    fastmcp.connection_management.interface.ddd_compliant_connection_tools

This module consolidates all connection-related functionality into a single
manage_connection tool with different actions for different operations.

Combines functionality from:
- health_check
- get_server_capabilities  
- connection_health_check
- get_mcp_status
- register_for_status_updates

Author: DevOps Agent
Date: 2025-01-27
Purpose: Consolidate connection management tools for better organization

⚠️  MIGRATION NOTICE: This implementation violates DDD principles by having
    business logic in the interface layer. The new DDD-compliant version
    provides proper layer separation and improved maintainability.
"""

import asyncio
import json
import logging
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .context import Context
from .connection_manager import get_connection_manager
from .connection_status_broadcaster import get_status_broadcaster

logger = logging.getLogger(__name__)


async def manage_connection(ctx: Context, action: str, **kwargs) -> Dict[str, Any]:
    """
    Unified connection management function
    
    Args:
        ctx: MCP context with session information
        action: Action to perform - health_check, server_capabilities, connection_health, 
                status, register_updates
        **kwargs: Additional parameters for specific actions
    
    Returns:
        Action-specific response data
    """
    try:
        if action == "health_check":
            return await _health_check(ctx, **kwargs)
        elif action == "server_capabilities":
            return await _get_server_capabilities(ctx, **kwargs)
        elif action == "connection_health":
            return await _connection_health_check(ctx, **kwargs)
        elif action == "status":
            return await _get_mcp_status(ctx, **kwargs)
        elif action == "register_updates":
            return await _register_for_status_updates(ctx, **kwargs)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": [
                    "health_check", "server_capabilities", "connection_health", 
                    "status", "register_updates"
                ]
            }
    except Exception as e:
        logger.error(f"Error in manage_connection action {action}: {e}")
        return {
            "success": False,
            "error": str(e),
            "action": action
        }


async def _health_check(ctx: Context, **kwargs) -> Dict[str, Any]:
    """Secure health check functionality with information filtering"""
    try:
        # Import the secure health check system
        from .secure_health_check import secure_health_check
        
        # Determine access level based on context
        # For now, we'll assume internal/admin access for backward compatibility
        # but this should be enhanced with proper authentication
        user_id = getattr(ctx, 'user_id', None) if ctx else None
        is_admin = kwargs.get('admin_access', True)  # Default to admin for backward compatibility
        is_internal = kwargs.get('internal_access', True)  # Default to internal for backward compatibility
        
        # Check if client requested minimal information
        include_details = kwargs.get('include_details', True)
        if not include_details:
            # Client requested minimal info - use client-safe response
            is_admin = False
            is_internal = False
        
        # Perform secure health check
        result = await secure_health_check(
            user_id=user_id,
            is_admin=is_admin,
            is_internal=is_internal,
            environment=os.environ.get("ENVIRONMENT", "production")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


async def _get_server_capabilities(ctx: Context, **kwargs) -> Dict[str, Any]:
    """Get detailed server capabilities information"""
    try:
        # Authentication is always enabled now
        auth_enabled = True
        mvp_mode = os.environ.get("PRODUCTION", "false").lower() == "true"
        
        capabilities = {
            "core_features": [
                "Task Management",
                "Project Management", 
                "Agent Orchestration",
                "Cursor Rules Integration",
                "Multi-Agent Coordination",
                "Token-based Authentication",
                "Rate Limiting",
                "Security Logging",
                "Connection Management",
                "Real-time Status Updates"
            ],
            "available_actions": {
                "connection_management": [
                    "health_check", "server_capabilities", "connection_health",
                    "status", "register_updates"
                ],
                "authentication": [
                    "validate_token", "get_rate_limit_status", "revoke_token",
                    "get_auth_status", "generate_token"
                ],
                "project_management": [
                    "create", "get", "list", "create_tree", "get_tree_status", 
                    "orchestrate", "get_dashboard"
                ],
                "task_management": [
                    "create", "update", "complete", "list", "search", "get_next",
                    "add_dependency", "remove_dependency", "list_dependencies"
                ],
                "subtask_management": [
                    "add", "update", "remove", "list"
                ],
                "agent_management": [
                    "register", "assign", "get", "list", "get_assignments", 
                    "update", "unregister", "rebalance"
                ],
                "cursor_integration": [
                    "update_auto_rule", "validate_rules", "manage_rule",
                    "regenerate_auto_rule", "validate_tasks_json"
                ]
            },
            "security_features": {
                "authentication_enabled": auth_enabled,
                "mvp_mode": mvp_mode,
                "rate_limiting": auth_enabled,
                "token_caching": auth_enabled,
                "security_logging": auth_enabled,
                "supabase_integration": bool(os.environ.get("SUPABASE_URL"))
            },
            "transport_info": {
                "is_docker": os.path.exists("/.dockerenv"),
                "transport": os.environ.get("FASTMCP_TRANSPORT", "stdio"),
                "host": os.environ.get("FASTMCP_HOST", "localhost"),
                "port": os.environ.get("FASTMCP_PORT", "8000")
            }
        }
        
        return {
            "success": True,
            "capabilities": capabilities,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Get server capabilities failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }


async def _connection_health_check(ctx: Context, **kwargs) -> Dict[str, Any]:
    """Detailed connection health check with troubleshooting guidance"""
    try:
        connection_manager = await get_connection_manager()
        
        # Update activity for current session
        if ctx and ctx.session_id:
            await connection_manager.update_connection_activity(ctx.session_id)
        
        # Get comprehensive connection stats
        connection_stats = await connection_manager.get_connection_stats()
        reconnection_info = await connection_manager.get_reconnection_info()
        
        # Build health response
        health_info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "current_session_id": ctx.session_id if ctx else None,
            "server_status": "healthy",
            "connection_manager": connection_stats,
            "reconnection_info": reconnection_info
        }
        
        # Determine overall health status
        active_connections = connection_stats["connections"]["active_connections"]
        restart_count = connection_stats["server_info"]["restart_count"]
        
        if restart_count > 0 and active_connections == 0:
            health_info["server_status"] = "restarted_no_clients"
            health_info["recommendation"] = "Server was restarted. MCP clients should reconnect."
        elif restart_count > 0:
            health_info["server_status"] = "restarted_with_clients"
            health_info["recommendation"] = "Server was restarted but has active connections."
        elif active_connections == 0:
            health_info["server_status"] = "no_clients"
            health_info["recommendation"] = "No active MCP clients connected."
        else:
            health_info["recommendation"] = "All connections healthy."
        
        # Add warnings for common issues
        warnings = []
        
        if restart_count > 0:
            warnings.append(f"Server has been restarted {restart_count} time(s). MCP clients may need to reconnect.")
        
        if connection_stats["connections"]["stale_connections"] > 0:
            warnings.append(f"{connection_stats['connections']['stale_connections']} stale connections detected.")
        
        if active_connections == 0 and ctx and ctx.session_id:
            warnings.append("No active connections detected, but current session exists. Connection state may be inconsistent.")
        
        if warnings:
            health_info["warnings"] = warnings
        
        # Add troubleshooting steps
        health_info["troubleshooting"] = {
            "cursor_reconnection": [
                "1. Toggle MCP server off in Cursor settings",
                "2. Wait 2-3 seconds", 
                "3. Toggle MCP server back on",
                "4. Check if tools are available again"
            ],
            "docker_rebuild": [
                "1. After rebuilding Docker containers",
                "2. The MCP server gets a new container ID",
                "3. Cursor's HTTP connection becomes stale",
                "4. Use the toggle method above to reconnect"
            ],
            "alternative_methods": [
                "1. Restart Cursor completely (slower but reliable)",
                "2. Use Cursor Developer Tools to check MCP connection status",
                "3. Check Docker container status: docker ps",
                "4. Verify server health: curl your_backend_service_url/health"
            ]
        }
        
        logger.info(f"Connection health check completed for session {ctx.session_id if ctx else 'unknown'}")
        return health_info
        
    except Exception as e:
        logger.error(f"Connection health check failed: {e}")
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "server_status": "error",
            "error": str(e),
            "recommendation": "Connection health check failed. Check server logs for details.",
            "troubleshooting": {
                "immediate_steps": [
                    "1. Check if Docker container is running: docker ps",
                    "2. Check server logs: docker logs dhafnck-mcp-server",
                    "3. Verify server health: curl your_backend_service_url/health",
                    "4. Restart MCP server if needed"
                ]
            }
        }


async def _get_mcp_status(ctx: Context, include_details: bool = True, **kwargs) -> Dict[str, Any]:
    """Get comprehensive MCP server status information"""
    try:
        # Get current timestamp
        now = time.time()
        
        # Initialize status response
        status = {
            "success": True,
            "timestamp": now,
            "iso_timestamp": datetime.now().isoformat(),
            "session_id": ctx.session_id if ctx else "unknown",
            "server_info": {
                "name": "DhafnckMCP - Task Management & Agent Orchestration",
                "version": "2.1.0",
                "status": "healthy"
            }
        }
        
        # Get connection manager information
        try:
            connection_manager = await get_connection_manager()
            connection_stats = await connection_manager.get_connection_stats()
            reconnection_info = await connection_manager.get_reconnection_info()
            
            status["connection_info"] = {
                "active_connections": connection_stats["connections"]["active_connections"],
                "total_registered": connection_stats["connections"]["total_registered"],
                "stale_connections": connection_stats["connections"]["stale_connections"],
                "server_restart_count": connection_stats["server_info"]["restart_count"],
                "uptime_seconds": connection_stats["server_info"]["uptime_seconds"],
                "recommended_action": reconnection_info["recommended_action"]
            }
            
            # Determine overall server status
            restart_count = connection_stats["server_info"]["restart_count"]
            uptime = connection_stats["server_info"]["uptime_seconds"]
            active_connections = connection_stats["connections"]["active_connections"]
            
            if restart_count > 0 and active_connections == 0:
                status["server_info"]["status"] = "restarted"
                status["server_info"]["message"] = "Server restarted, no active clients"
            elif restart_count > 0:
                status["server_info"]["status"] = "restarted"
                status["server_info"]["message"] = f"Server restarted with {active_connections} active connections"
            elif active_connections == 0:
                status["server_info"]["status"] = "no_clients"
                status["server_info"]["message"] = "Server healthy but no active clients"
            elif uptime < 60:  # Less than 1 minute uptime
                status["server_info"]["status"] = "restarted"
                status["server_info"]["message"] = "Server recently started"
            
            # Include active clients if requested
            if include_details:
                status["active_clients"] = connection_stats.get("active_clients", [])
                
        except Exception as e:
            status["connection_info"] = {"error": str(e)}
            status["server_info"]["status"] = "degraded"
            status["server_info"]["message"] = f"Connection manager error: {str(e)}"
        
        # Get broadcasting information
        try:
            status_broadcaster = await get_status_broadcaster()
            last_status = status_broadcaster.get_last_status()
            
            status["broadcast_info"] = {
                "broadcasting_active": True,
                "registered_clients": status_broadcaster.get_client_count(),
                "last_broadcast": last_status
            }
            
        except Exception as e:
            status["broadcast_info"] = {
                "broadcasting_active": False,
                "error": str(e)
            }
        
        # Add authentication status - always enabled now
        try:
            status["auth_info"] = {
                "enabled": True,
                "mvp_mode": os.environ.get("PRODUCTION", "false").lower() == "true"
            }
        except Exception:
            status["auth_info"] = {"enabled": True, "mvp_mode": False}
        
        # Add Docker/container information
        try:
            status["container_info"] = {
                "is_docker": os.path.exists("/.dockerenv"),
                "transport": os.environ.get("FASTMCP_TRANSPORT", "stdio"),
                "host": os.environ.get("FASTMCP_HOST", "localhost"),
                "port": os.environ.get("FASTMCP_PORT", "8000")
            }
        except Exception:
            status["container_info"] = {"error": "Could not determine container info"}
        
        # Add tools availability check
        status["tools_info"] = {
            "available": True,  # If this tool is running, tools are available
            "last_check": now,
            "tool_count": "unknown"  # Could be enhanced to count actual tools
        }
        
        # Add recommendations based on status
        recommendations = []
        
        if status["server_info"]["status"] == "restarted":
            recommendations.append("Use Cursor MCP toggle: Settings → Extensions → MCP → Toggle dhafnck_mcp_http OFF/ON")
            recommendations.append("Alternative: Restart Cursor completely")
            
        elif status["server_info"]["status"] == "no_clients":
            recommendations.append("Check Cursor MCP configuration in .cursor/mcp.json")
            recommendations.append("Verify MCP server URL: Check your backend service URL at /mcp/")
            
        elif status["connection_info"].get("stale_connections", 0) > 0:
            recommendations.append("Some connections are stale, consider reconnecting")
        
        if recommendations:
            status["recommendations"] = recommendations
        
        return status
        
    except Exception as e:
        logger.error(f"Error in get_mcp_status: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "server_info": {"status": "error", "message": str(e)}
        }


async def _register_for_status_updates(ctx: Context, **kwargs) -> Dict[str, Any]:
    """Register the current session for real-time status updates"""
    try:
        if not ctx or not ctx.session_id:
            return {
                "success": False,
                "error": "No valid session ID for registration"
            }
        
        # Register with status broadcaster
        status_broadcaster = await get_status_broadcaster()
        await status_broadcaster.register_client(ctx.session_id)
        
        # Register with connection manager
        connection_manager = await get_connection_manager()
        await connection_manager.register_connection(
            ctx.session_id,
            {"name": "cursor", "version": "unknown", "type": "mcp_client"}
        )
        
        logger.info(f"Session {ctx.session_id} registered for status updates")
        
        return {
            "success": True,
            "session_id": ctx.session_id,
            "message": "Successfully registered for status updates",
            "update_interval": 30,  # seconds
            "immediate_events": ["server_restart", "tools_unavailable"]
        }
        
    except Exception as e:
        logger.error(f"Error registering for status updates: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def register_manage_connection_tool(server):
    """Register the unified connection management tool with the FastMCP server"""
    
    @server.tool(
        name="manage_connection",
        description="🔗 UNIFIED CONNECTION MANAGEMENT - Complete connection, health, and status operations"
    )
    async def manage_connection_tool(ctx: Context, action: str, include_details: bool = True) -> str:
        """
        🔗 UNIFIED CONNECTION MANAGEMENT SYSTEM - Complete connection lifecycle operations

        ⭐ WHAT IT DOES: Comprehensive connection management with health checks, status monitoring, and troubleshooting
        📋 WHEN TO USE: All connection-related operations including health checks, status monitoring, and diagnostics  
        🎯 CRITICAL FOR: Server health monitoring, connection troubleshooting, and status updates

        🔧 FUNCTIONALITY:
        • Health Check: Basic server health and availability status
        • Server Capabilities: Detailed server features and configuration information
        • Connection Health: Comprehensive connection diagnostics with troubleshooting guidance
        • Status: Real-time server status with connection statistics and recommendations
        • Register Updates: Register session for real-time status update notifications

        💡 ACTION TYPES:
        • 'health_check': Basic server health status and environment information
        • 'server_capabilities': Detailed server capabilities and feature information
        • 'connection_health': Connection diagnostics with troubleshooting guidance
        • 'status': Comprehensive server status with connection statistics
        • 'register_updates': Register for real-time status update notifications

        📋 PARAMETER REQUIREMENTS BY ACTION:
        • health_check: action ✓ (no additional parameters)
        • server_capabilities: action ✓ (no additional parameters)
        • connection_health: action ✓ (no additional parameters)
        • status: action ✓, optional: include_details (boolean, default: true)
        • register_updates: action ✓ (no additional parameters)

        ⚠️ USAGE GUIDELINES:
        • Always specify the action parameter for the desired operation
        • Use 'health_check' for basic server availability verification
        • Use 'connection_health' for detailed connection troubleshooting
        • Use 'status' for comprehensive server and connection monitoring
        • Use 'register_updates' to enable real-time status notifications

        🎯 USE CASES:
        • Server Health Monitoring: Check basic server availability and environment
        • Connection Troubleshooting: Diagnose connection issues with guided solutions
        • Status Monitoring: Monitor server status, connections, and performance
        • Real-time Updates: Register for automatic status change notifications
        • Capability Discovery: Learn about available server features and actions
        
        Args:
            action: Connection management action to perform
            include_details: Include detailed information (for status action)
        
        Returns:
            Formatted response with action-specific information and guidance
        """
        result = await manage_connection(ctx, action, include_details=include_details)
        
        if not result.get("success", True):
            return f"❌ **Connection Management Error**\n\n**Action:** {action}\n**Error:** {result.get('error', 'Unknown error')}\n\n**Available Actions:** {', '.join(result.get('available_actions', []))}"
        
        # Format response based on action
        if action == "health_check":
            return _format_health_check_response(result)
        elif action == "server_capabilities":
            return _format_server_capabilities_response(result)
        elif action == "connection_health":
            return _format_connection_health_response(result)
        elif action == "status":
            return _format_status_response(result)
        elif action == "register_updates":
            return _format_register_updates_response(result)
        else:
            return f"❓ **Unknown Action:** {action}\n\n**Available Actions:** health_check, server_capabilities, connection_health, status, register_updates"
    
    logger.info("Unified connection management tool registered successfully")
    return manage_connection_tool


def _format_health_check_response(result: Dict[str, Any]) -> str:
    """Format health check response for display"""
    status_emoji = "✅" if result.get("status") == "healthy" else "🚨"
    
    response = f"{status_emoji} **Server Health Check**\n\n"
    response += f"**Server Information:**\n"
    response += f"- Name: {result.get('server_name', 'Unknown')}\n"
    response += f"- Version: {result.get('version', 'Unknown')}\n"
    response += f"- Status: {result.get('status', 'Unknown')}\n"
    response += f"- Timestamp: {datetime.fromtimestamp(result.get('timestamp', 0)).isoformat()}\n\n"
    
    # Authentication info
    auth = result.get("authentication", {})
    response += f"**Authentication:**\n"
    response += f"- Enabled: {'Yes' if auth.get('enabled') else 'No'}\n"
    response += f"- MVP Mode: {'Yes' if auth.get('mvp_mode') else 'No'}\n\n"
    
    # Task management info
    task_mgmt = result.get("task_management", {})
    response += f"**Task Management:**\n"
    response += f"- Enabled: {'Yes' if task_mgmt.get('task_management_enabled') else 'No'}\n"
    response += f"- Tools Count: {task_mgmt.get('enabled_tools_count', 0)}\n\n"
    
    # Connection info
    connections = result.get("connections", {})
    if "error" not in connections:
        response += f"**Connections:**\n"
        response += f"- Active: {connections.get('active_connections', 0)}\n"
        response += f"- Restarts: {connections.get('server_restart_count', 0)}\n"
        response += f"- Uptime: {connections.get('uptime_seconds', 0):.1f}s\n"
        response += f"- Action: {connections.get('recommended_action', 'continue')}\n"
    else:
        response += f"**Connections:** Error - {connections['error']}\n"
    
    return response


def _format_server_capabilities_response(result: Dict[str, Any]) -> str:
    """Format server capabilities response for display"""
    capabilities = result.get("capabilities", {})
    
    response = "🔧 **Server Capabilities**\n\n"
    
    # Core features
    core_features = capabilities.get("core_features", [])
    response += f"**Core Features ({len(core_features)}):**\n"
    for feature in core_features:
        response += f"- {feature}\n"
    response += "\n"
    
    # Available actions by category
    actions = capabilities.get("available_actions", {})
    response += "**Available Actions:**\n"
    for category, action_list in actions.items():
        response += f"- **{category.replace('_', ' ').title()}:** {', '.join(action_list)}\n"
    response += "\n"
    
    # Security features
    security = capabilities.get("security_features", {})
    response += "**Security Features:**\n"
    response += f"- Authentication: {'Enabled' if security.get('authentication_enabled') else 'Disabled'}\n"
    response += f"- MVP Mode: {'Yes' if security.get('mvp_mode') else 'No'}\n"
    response += f"- Rate Limiting: {'Yes' if security.get('rate_limiting') else 'No'}\n"
    response += f"- Supabase Integration: {'Yes' if security.get('supabase_integration') else 'No'}\n\n"
    
    # Transport info
    transport = capabilities.get("transport_info", {})
    response += "**Transport Configuration:**\n"
    response += f"- Environment: {'Docker' if transport.get('is_docker') else 'Local'}\n"
    response += f"- Transport: {transport.get('transport', 'unknown')}\n"
    response += f"- Endpoint: {transport.get('host', 'localhost')}:{transport.get('port', '8000')}\n"
    
    return response


def _format_connection_health_response(result: Dict[str, Any]) -> str:
    """Format connection health response for display"""
    status_emoji = {
        "healthy": "✅",
        "restarted_no_clients": "🔄",
        "restarted_with_clients": "⚠️",
        "no_clients": "📡",
        "error": "🚨"
    }
    
    server_status = result.get("server_status", "unknown")
    emoji = status_emoji.get(server_status, "❓")
    status = server_status.replace("_", " ").title()
    
    response = f"{emoji} **Connection Health Status: {status}**\n\n"
    
    # Current session info
    response += "**Current Session:**\n"
    response += f"- Session ID: {result.get('current_session_id', 'none')}\n"
    response += f"- Timestamp: {result.get('timestamp', 'unknown')}\n\n"
    
    # Server information
    server_info = result.get("connection_manager", {}).get("server_info", {})
    response += "**Server Information:**\n"
    response += f"- Uptime: {server_info.get('uptime_seconds', 0):.1f} seconds\n"
    response += f"- Restart Count: {server_info.get('restart_count', 0)}\n"
    response += f"- Start Time: {server_info.get('start_time', 'unknown')}\n\n"
    
    # Connection statistics
    conn_info = result.get("connection_manager", {}).get("connections", {})
    response += "**Connection Statistics:**\n"
    response += f"- Active Connections: {conn_info.get('active_connections', 0)}\n"
    response += f"- Total Registered: {conn_info.get('total_registered', 0)}\n"
    response += f"- Stale Connections: {conn_info.get('stale_connections', 0)}\n\n"
    
    # Active clients
    active_clients = result.get("connection_manager", {}).get("active_clients", [])
    if active_clients:
        response += "**Active Clients:**\n"
        for client in active_clients:
            response += f"- {client.get('client_name', 'unknown')} (v{client.get('client_version', '?')})\n"
            response += f"  Connected: {client.get('connection_age_seconds', 0):.1f}s ago\n"
            response += f"  Health Checks: {client.get('health_checks', 0)}\n"
        response += "\n"
    
    # Recommendation
    if result.get("recommendation"):
        response += f"**💡 Recommendation:**\n{result['recommendation']}\n\n"
    
    # Warnings
    if result.get("warnings"):
        response += "**⚠️ Warnings:**\n"
        for warning in result["warnings"]:
            response += f"- {warning}\n"
        response += "\n"
    
    # Troubleshooting steps
    troubleshooting = result.get("troubleshooting", {})
    
    if "cursor_reconnection" in troubleshooting:
        response += "**🔄 Quick Cursor Reconnection (Recommended):**\n"
        for step in troubleshooting["cursor_reconnection"]:
            response += f"{step}\n"
        response += "\n"
    
    if "docker_rebuild" in troubleshooting:
        response += "**🐳 After Docker Rebuild:**\n"
        for step in troubleshooting["docker_rebuild"]:
            response += f"{step}\n"
        response += "\n"
    
    if "alternative_methods" in troubleshooting:
        response += "**🛠️ Alternative Methods:**\n"
        for step in troubleshooting["alternative_methods"]:
            response += f"{step}\n"
        response += "\n"
    
    if "immediate_steps" in troubleshooting:
        response += "**🚨 Immediate Troubleshooting:**\n"
        for step in troubleshooting["immediate_steps"]:
            response += f"{step}\n"
        response += "\n"
    
    # Reconnection info
    reconnection_info = result.get("reconnection_info", {})
    if reconnection_info.get("recommended_action") == "reconnect":
        response += "**🔗 Reconnection Required:**\n"
        response += f"Server was restarted. Please use the quick reconnection steps above.\n\n"
    
    # Error details
    if result.get("error"):
        response += f"**🚨 Error Details:**\n{result['error']}\n\n"
    
    return response


def _format_status_response(result: Dict[str, Any]) -> str:
    """Format status response for display"""
    server_status = result.get("server_info", {}).get("status", "unknown")
    status_emoji = {
        "healthy": "✅",
        "restarted": "🔄",
        "no_clients": "📡",
        "degraded": "⚠️",
        "error": "🚨"
    }
    
    emoji = status_emoji.get(server_status, "❓")
    response = f"{emoji} **MCP Server Status: {server_status.title()}**\n\n"
    
    # Server information
    server_info = result.get("server_info", {})
    response += "**Server Information:**\n"
    response += f"- Name: {server_info.get('name', 'Unknown')}\n"
    response += f"- Version: {server_info.get('version', 'Unknown')}\n"
    response += f"- Status: {server_info.get('status', 'Unknown')}\n"
    if server_info.get("message"):
        response += f"- Message: {server_info['message']}\n"
    response += f"- Timestamp: {result.get('iso_timestamp', 'Unknown')}\n\n"
    
    # Connection information
    conn_info = result.get("connection_info", {})
    if "error" not in conn_info:
        response += "**Connection Information:**\n"
        response += f"- Active Connections: {conn_info.get('active_connections', 0)}\n"
        response += f"- Total Registered: {conn_info.get('total_registered', 0)}\n"
        response += f"- Stale Connections: {conn_info.get('stale_connections', 0)}\n"
        response += f"- Server Restarts: {conn_info.get('server_restart_count', 0)}\n"
        response += f"- Uptime: {conn_info.get('uptime_seconds', 0):.1f} seconds\n"
        response += f"- Recommended Action: {conn_info.get('recommended_action', 'continue')}\n\n"
    else:
        response += f"**Connection Error:** {conn_info['error']}\n\n"
    
    # Broadcasting information
    broadcast_info = result.get("broadcast_info", {})
    if broadcast_info.get("broadcasting_active"):
        response += "**Real-time Updates:**\n"
        response += f"- Broadcasting Active: ✅\n"
        response += f"- Registered Clients: {broadcast_info.get('registered_clients', 0)}\n"
        if broadcast_info.get("last_broadcast"):
            last_broadcast = broadcast_info["last_broadcast"]
            response += f"- Last Broadcast: {last_broadcast.get('event_type', 'unknown')} "
            response += f"({last_broadcast.get('server_status', 'unknown')})\n"
        response += "\n"
    
    # Authentication and container info
    auth_info = result.get("auth_info", {})
    container_info = result.get("container_info", {})
    response += "**Configuration:**\n"
    response += f"- Authentication: {'Enabled' if auth_info.get('enabled') else 'Disabled'}\n"
    response += f"- MVP Mode: {'Yes' if auth_info.get('mvp_mode') else 'No'}\n"
    response += f"- Container: {'Docker' if container_info.get('is_docker') else 'Local'}\n"
    response += f"- Transport: {container_info.get('transport', 'unknown')}\n"
    response += f"- Endpoint: {container_info.get('host', 'localhost')}:{container_info.get('port', '8000')}\n\n"
    
    # Active clients details
    if result.get("active_clients"):
        response += "**Active Clients:**\n"
        for client in result["active_clients"]:
            response += f"- {client.get('client_name', 'unknown')} "
            response += f"(v{client.get('client_version', '?')})\n"
            response += f"  Session: {client.get('session_id', 'unknown')}\n"
            response += f"  Connected: {client.get('connection_age_seconds', 0):.1f}s ago\n"
            response += f"  Health Checks: {client.get('health_checks', 0)}\n"
        response += "\n"
    
    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        response += "**💡 Recommendations:**\n"
        for rec in recommendations:
            response += f"- {rec}\n"
        response += "\n"
    
    # Quick actions
    response += "**🔧 Quick Actions:**\n"
    response += "- Check connection: Call `manage_connection` with action='connection_health'\n"
    response += "- Register for updates: Call `manage_connection` with action='register_updates'\n"
    response += "- Server health: Visit your backend service URL at /health\n"
    
    return response


def _format_register_updates_response(result: Dict[str, Any]) -> str:
    """Format register updates response for display"""
    if result.get("success"):
        response = "✅ **Successfully Registered for Status Updates**\n\n"
        response += f"**Session Information:**\n"
        response += f"- Session ID: {result.get('session_id', 'unknown')}\n"
        response += f"- Update Interval: {result.get('update_interval', 30)} seconds\n"
        response += f"- Immediate Events: {', '.join(result.get('immediate_events', []))}\n\n"
        response += "**What This Means:**\n"
        response += "- Your MCP tools status icon will update automatically\n"
        response += "- You'll receive immediate notifications on server restarts\n"
        response += "- Connection issues will be detected and reported\n"
        response += "- Tools availability changes will be broadcasted\n\n"
        response += "**Next Steps:**\n"
        response += "- Your session is now monitored for connection health\n"
        response += "- If the server restarts, you'll be notified to reconnect\n"
        response += "- Use `manage_connection` with action='status' to check current status anytime\n"
    else:
        response = "❌ **Registration Failed**\n\n"
        response += f"**Error:** {result.get('error', 'Unknown error')}\n\n"
        response += "**Troubleshooting:**\n"
        response += "- Ensure you have a valid MCP session\n"
        response += "- Check server logs for connection issues\n"
        response += "- Try `manage_connection` with action='connection_health' for diagnostics\n"
    
    return response