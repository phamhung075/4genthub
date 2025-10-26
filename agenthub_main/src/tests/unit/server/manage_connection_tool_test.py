"""
Unit tests for manage_connection_tool module

This module tests the unified connection management functionality including:
- Main manage_connection dispatcher
- Health check operations
- Server capabilities
- Connection health diagnostics
- MCP status monitoring
- Registration for status updates
- Response formatting functions

Coverage Target: 55%+ (200+ lines out of 375 total)
"""

import pytest
import asyncio
import os
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any

# Import the module under test
from fastmcp.server.manage_connection_tool import (
    manage_connection,
    _health_check,
    _get_server_capabilities,
    _connection_health_check,
    _get_mcp_status,
    _register_for_status_updates,
    _format_health_check_response,
    _format_server_capabilities_response,
    _format_connection_health_response,
    _format_status_response,
    _format_register_updates_response,
    register_manage_connection_tool
)


# Fixtures for common test data
@pytest.fixture
def mock_context():
    """Create a mock Context object with session information"""
    ctx = MagicMock()
    ctx.session_id = "test-session-123"
    ctx.user_id = "test-user-456"
    return ctx


@pytest.fixture
def mock_connection_manager():
    """Create a mock connection manager with standard responses"""
    manager = AsyncMock()
    manager.update_connection_activity = AsyncMock()
    manager.get_connection_stats = AsyncMock(return_value={
        "connections": {
            "active_connections": 2,
            "total_registered": 5,
            "stale_connections": 1
        },
        "server_info": {
            "restart_count": 0,
            "uptime_seconds": 3600.0,
            "start_time": "2025-01-27T10:00:00"
        },
        "active_clients": []
    })
    manager.get_reconnection_info = AsyncMock(return_value={
        "recommended_action": "continue"
    })
    manager.register_connection = AsyncMock()
    return manager


@pytest.fixture
def mock_status_broadcaster():
    """Create a mock status broadcaster"""
    broadcaster = AsyncMock()
    broadcaster.register_client = AsyncMock()
    broadcaster.get_client_count = MagicMock(return_value=3)
    broadcaster.get_last_status = MagicMock(return_value={
        "event_type": "status_update",
        "server_status": "healthy"
    })
    return broadcaster


@pytest.fixture
def mock_secure_health_check():
    """Create a mock secure health check response"""
    return {
        "success": True,
        "status": "healthy",
        "server_name": "agenthub",
        "version": "2.1.0",
        "timestamp": time.time(),
        "authentication": {
            "enabled": True,
            "mvp_mode": False
        },
        "task_management": {
            "task_management_enabled": True,
            "enabled_tools_count": 15
        },
        "connections": {
            "active_connections": 2,
            "server_restart_count": 0,
            "uptime_seconds": 3600.0,
            "recommended_action": "continue"
        }
    }


# Tests for main manage_connection function
class TestManageConnection:
    """Test suite for the main manage_connection dispatcher"""

    @pytest.mark.asyncio
    async def test_health_check_action(self, mock_context, mock_secure_health_check):
        """Test manage_connection with health_check action"""
        with patch('fastmcp.server.secure_health_check.secure_health_check',
                   new_callable=AsyncMock, return_value=mock_secure_health_check):
            result = await manage_connection(mock_context, "health_check")

            assert result["success"] is True
            assert result["status"] == "healthy"
            assert "server_name" in result
            assert "version" in result

    @pytest.mark.asyncio
    async def test_server_capabilities_action(self, mock_context):
        """Test manage_connection with server_capabilities action"""
        result = await manage_connection(mock_context, "server_capabilities")

        assert result["success"] is True
        assert "capabilities" in result
        assert "core_features" in result["capabilities"]
        assert "available_actions" in result["capabilities"]
        assert "security_features" in result["capabilities"]

    @pytest.mark.asyncio
    async def test_connection_health_action(self, mock_context, mock_connection_manager):
        """Test manage_connection with connection_health action"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager):
            result = await manage_connection(mock_context, "connection_health")

            assert result["success"] is True
            assert "server_status" in result
            assert "connection_manager" in result
            assert "troubleshooting" in result

    @pytest.mark.asyncio
    async def test_status_action(self, mock_context, mock_connection_manager, mock_status_broadcaster):
        """Test manage_connection with status action"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await manage_connection(mock_context, "status")

            assert result["success"] is True
            assert "server_info" in result
            assert "connection_info" in result
            assert "broadcast_info" in result

    @pytest.mark.asyncio
    async def test_register_updates_action(self, mock_context, mock_connection_manager,
                                           mock_status_broadcaster):
        """Test manage_connection with register_updates action"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await manage_connection(mock_context, "register_updates")

            assert result["success"] is True
            assert result["session_id"] == "test-session-123"
            assert "message" in result
            assert "update_interval" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, mock_context):
        """Test manage_connection with unknown action returns error"""
        result = await manage_connection(mock_context, "invalid_action")

        assert result["success"] is False
        assert "error" in result
        assert "Unknown action" in result["error"]
        assert "available_actions" in result

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_context):
        """Test manage_connection handles exceptions gracefully"""
        with patch('fastmcp.server.manage_connection_tool._health_check',
                   side_effect=Exception("Test error")):
            result = await manage_connection(mock_context, "health_check")

            assert result["success"] is False
            assert "error" in result
            assert "Test error" in result["error"]


# Tests for _health_check function
class TestHealthCheck:
    """Test suite for _health_check function"""

    @pytest.mark.asyncio
    async def test_health_check_with_details(self, mock_context, mock_secure_health_check):
        """Test health check with include_details=True"""
        with patch('fastmcp.server.secure_health_check.secure_health_check',
                   new_callable=AsyncMock, return_value=mock_secure_health_check):
            result = await _health_check(mock_context, include_details=True)

            assert result["success"] is True
            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_minimal(self, mock_context, mock_secure_health_check):
        """Test health check with include_details=False for minimal info"""
        with patch('fastmcp.server.secure_health_check.secure_health_check',
                   new_callable=AsyncMock, return_value=mock_secure_health_check):
            result = await _health_check(mock_context, include_details=False)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_health_check_exception(self, mock_context):
        """Test health check handles exceptions"""
        with patch('fastmcp.server.secure_health_check.secure_health_check',
                   side_effect=Exception("Health check failed")):
            result = await _health_check(mock_context)

            assert result["success"] is False
            assert "error" in result
            assert result["status"] == "error"


# Tests for _get_server_capabilities function
class TestGetServerCapabilities:
    """Test suite for _get_server_capabilities function"""

    @pytest.mark.asyncio
    async def test_server_capabilities_structure(self, mock_context):
        """Test server capabilities returns proper structure"""
        result = await _get_server_capabilities(mock_context)

        assert result["success"] is True
        capabilities = result["capabilities"]
        assert "core_features" in capabilities
        assert "available_actions" in capabilities
        assert "security_features" in capabilities
        assert "transport_info" in capabilities

    @pytest.mark.asyncio
    async def test_server_capabilities_core_features(self, mock_context):
        """Test core features are listed correctly"""
        result = await _get_server_capabilities(mock_context)

        core_features = result["capabilities"]["core_features"]
        assert "Task Management" in core_features
        assert "Project Management" in core_features
        assert "Agent Orchestration" in core_features

    @pytest.mark.asyncio
    async def test_server_capabilities_security_features(self, mock_context):
        """Test security features configuration"""
        result = await _get_server_capabilities(mock_context)

        security = result["capabilities"]["security_features"]
        assert security["authentication_enabled"] is True
        assert "mvp_mode" in security
        assert "rate_limiting" in security

    @pytest.mark.asyncio
    async def test_server_capabilities_with_env_vars(self, mock_context):
        """Test server capabilities respects environment variables"""
        with patch.dict(os.environ, {'PRODUCTION': 'true', 'SUPABASE_URL': 'http://test.com'}):
            result = await _get_server_capabilities(mock_context)

            security = result["capabilities"]["security_features"]
            assert security["mvp_mode"] is True
            assert security["supabase_integration"] is True


# Tests for _connection_health_check function
class TestConnectionHealthCheck:
    """Test suite for _connection_health_check function"""

    @pytest.mark.asyncio
    async def test_connection_health_basic(self, mock_context, mock_connection_manager):
        """Test basic connection health check"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager):
            result = await _connection_health_check(mock_context)

            assert result["success"] is True
            assert result["server_status"] == "healthy"
            assert "troubleshooting" in result

    @pytest.mark.asyncio
    async def test_connection_health_restarted_no_clients(self, mock_context, mock_connection_manager):
        """Test connection health when server restarted with no clients"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 0, "total_registered": 0, "stale_connections": 0},
            "server_info": {"restart_count": 1, "uptime_seconds": 10.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager):
            result = await _connection_health_check(mock_context)

            assert result["server_status"] == "restarted_no_clients"
            assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_connection_health_with_warnings(self, mock_context, mock_connection_manager):
        """Test connection health includes warnings for issues"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 2, "total_registered": 5, "stale_connections": 3},
            "server_info": {"restart_count": 2, "uptime_seconds": 100.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager):
            result = await _connection_health_check(mock_context)

            assert "warnings" in result
            assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_connection_health_exception(self, mock_context):
        """Test connection health handles exceptions"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   side_effect=Exception("Connection manager error")):
            result = await _connection_health_check(mock_context)

            assert result["success"] is False
            assert result["server_status"] == "error"
            assert "error" in result


# Tests for _get_mcp_status function
class TestGetMcpStatus:
    """Test suite for _get_mcp_status function"""

    @pytest.mark.asyncio
    async def test_mcp_status_basic(self, mock_context, mock_connection_manager, mock_status_broadcaster):
        """Test basic MCP status retrieval"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context)

            assert result["success"] is True
            assert result["session_id"] == "test-session-123"
            assert "server_info" in result

    @pytest.mark.asyncio
    async def test_mcp_status_with_details(self, mock_context, mock_connection_manager,
                                          mock_status_broadcaster):
        """Test MCP status includes details when requested"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 2, "total_registered": 5, "stale_connections": 0},
            "server_info": {"restart_count": 0, "uptime_seconds": 3600.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": [{"client_name": "cursor", "session_id": "test-123"}]
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context, include_details=True)

            assert "active_clients" in result

    @pytest.mark.asyncio
    async def test_mcp_status_restarted_server(self, mock_context, mock_connection_manager,
                                               mock_status_broadcaster):
        """Test MCP status detects server restart"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 0, "total_registered": 1, "stale_connections": 0},
            "server_info": {"restart_count": 1, "uptime_seconds": 10.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context)

            assert result["server_info"]["status"] == "restarted"
            assert "recommendations" in result


# Tests for _register_for_status_updates function
class TestRegisterForStatusUpdates:
    """Test suite for _register_for_status_updates function"""

    @pytest.mark.asyncio
    async def test_register_success(self, mock_context, mock_connection_manager, mock_status_broadcaster):
        """Test successful registration for status updates"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _register_for_status_updates(mock_context)

            assert result["success"] is True
            assert result["session_id"] == "test-session-123"
            assert "update_interval" in result

    @pytest.mark.asyncio
    async def test_register_no_session(self):
        """Test registration fails without valid session"""
        ctx = MagicMock()
        ctx.session_id = None

        result = await _register_for_status_updates(ctx)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_register_exception(self, mock_context):
        """Test registration handles exceptions"""
        with patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   side_effect=Exception("Broadcaster error")):
            result = await _register_for_status_updates(mock_context)

            assert result["success"] is False
            assert "error" in result


# Tests for formatting functions
class TestFormattingFunctions:
    """Test suite for response formatting functions"""

    def test_format_health_check_response(self, mock_secure_health_check):
        """Test health check response formatting"""
        formatted = _format_health_check_response(mock_secure_health_check)

        assert "Server Health Check" in formatted
        assert "Server Information" in formatted
        assert "Authentication" in formatted
        assert "Task Management" in formatted

    def test_format_server_capabilities_response(self):
        """Test server capabilities response formatting"""
        capabilities_data = {
            "success": True,
            "capabilities": {
                "core_features": ["Task Management", "Project Management"],
                "available_actions": {
                    "connection_management": ["health_check", "status"]
                },
                "security_features": {
                    "authentication_enabled": True,
                    "mvp_mode": False
                },
                "transport_info": {
                    "is_docker": True,
                    "transport": "http"
                }
            }
        }

        formatted = _format_server_capabilities_response(capabilities_data)

        assert "Server Capabilities" in formatted
        assert "Core Features" in formatted
        assert "Available Actions" in formatted
        assert "Security Features" in formatted

    def test_format_connection_health_response(self):
        """Test connection health response formatting"""
        health_data = {
            "success": True,
            "server_status": "healthy",
            "current_session_id": "test-123",
            "timestamp": "2025-01-27T10:00:00",
            "connection_manager": {
                "server_info": {
                    "uptime_seconds": 3600.0,
                    "restart_count": 0,
                    "start_time": "2025-01-27T10:00:00"
                },
                "connections": {
                    "active_connections": 2,
                    "total_registered": 5,
                    "stale_connections": 0
                },
                "active_clients": []
            },
            "troubleshooting": {
                "cursor_reconnection": ["Step 1", "Step 2"]
            }
        }

        formatted = _format_connection_health_response(health_data)

        assert "Connection Health Status" in formatted
        assert "Current Session" in formatted
        assert "Server Information" in formatted
        assert "Connection Statistics" in formatted

    def test_format_status_response(self):
        """Test status response formatting"""
        status_data = {
            "success": True,
            "server_info": {
                "name": "agenthub",
                "version": "2.1.0",
                "status": "healthy"
            },
            "connection_info": {
                "active_connections": 2,
                "uptime_seconds": 3600.0
            },
            "auth_info": {
                "enabled": True,
                "mvp_mode": False
            },
            "container_info": {
                "is_docker": True
            }
        }

        formatted = _format_status_response(status_data)

        assert "MCP Server Status" in formatted
        assert "Server Information" in formatted
        assert "Connection Information" in formatted

    def test_format_register_updates_response_success(self):
        """Test register updates response formatting for success"""
        register_data = {
            "success": True,
            "session_id": "test-123",
            "update_interval": 30,
            "immediate_events": ["server_restart"]
        }

        formatted = _format_register_updates_response(register_data)

        assert "Successfully Registered" in formatted
        assert "Session Information" in formatted
        assert "What This Means" in formatted

    def test_format_register_updates_response_failure(self):
        """Test register updates response formatting for failure"""
        register_data = {
            "success": False,
            "error": "No valid session"
        }

        formatted = _format_register_updates_response(register_data)

        assert "Registration Failed" in formatted
        assert "Error" in formatted
        assert "Troubleshooting" in formatted


# Tests for register_manage_connection_tool function
class TestRegisterManageConnectionTool:
    """Test suite for tool registration"""

    @pytest.mark.asyncio
    async def test_register_tool(self):
        """Test tool registration with FastMCP server"""
        mock_server = MagicMock()
        tool_decorator = MagicMock(return_value=lambda f: f)
        mock_server.tool = tool_decorator

        result = register_manage_connection_tool(mock_server)

        # Verify tool decorator was called
        tool_decorator.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_function_health_check(self, mock_context, mock_secure_health_check):
        """Test the registered tool function with health_check action"""
        mock_server = MagicMock()

        # Store the tool function when tool() decorator is called
        tool_function = None
        def mock_tool_decorator(name, description):
            def decorator(func):
                nonlocal tool_function
                tool_function = func
                return func
            return decorator

        mock_server.tool = mock_tool_decorator

        # Register the tool
        register_manage_connection_tool(mock_server)

        # Test the tool function
        with patch('fastmcp.server.secure_health_check.secure_health_check',
                   new_callable=AsyncMock, return_value=mock_secure_health_check):
            result = await tool_function(mock_context, "health_check")

            assert "Server Health Check" in result

    @pytest.mark.asyncio
    async def test_tool_function_unknown_action(self, mock_context):
        """Test the registered tool function with unknown action"""
        mock_server = MagicMock()

        tool_function = None
        def mock_tool_decorator(name, description):
            def decorator(func):
                nonlocal tool_function
                tool_function = func
                return func
            return decorator

        mock_server.tool = mock_tool_decorator
        register_manage_connection_tool(mock_server)

        result = await tool_function(mock_context, "invalid_action")

        assert "Unknown Action" in result or "Error" in result


# Additional edge case tests for better coverage
class TestEdgeCasesAndErrorPaths:
    """Test suite for edge cases and error paths"""

    @pytest.mark.asyncio
    async def test_get_server_capabilities_exception(self, mock_context):
        """Test server capabilities handles exceptions gracefully"""
        with patch.dict(os.environ, {}, clear=True):
            result = await _get_server_capabilities(mock_context)

            # Should still succeed but with defaults
            assert result["success"] is True
            assert "capabilities" in result

    @pytest.mark.asyncio
    async def test_connection_health_no_context(self):
        """Test connection health with no context"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager') as mock_mgr:
            mock_mgr.return_value = AsyncMock()
            mock_mgr.return_value.get_connection_stats = AsyncMock(return_value={
                "connections": {"active_connections": 0, "total_registered": 0, "stale_connections": 0},
                "server_info": {"restart_count": 0, "uptime_seconds": 0.0, "start_time": ""},
                "active_clients": []
            })
            mock_mgr.return_value.get_reconnection_info = AsyncMock(return_value={
                "recommended_action": "continue"
            })

            result = await _connection_health_check(None)

            assert result["success"] is True
            assert result["current_session_id"] is None

    @pytest.mark.asyncio
    async def test_mcp_status_no_clients(self, mock_context, mock_connection_manager, mock_status_broadcaster):
        """Test MCP status with no active clients"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 0, "total_registered": 0, "stale_connections": 0},
            "server_info": {"restart_count": 0, "uptime_seconds": 3600.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context, include_details=False)

            assert result["success"] is True
            assert result["server_info"]["status"] == "no_clients"

    @pytest.mark.asyncio
    async def test_mcp_status_recently_started(self, mock_context, mock_connection_manager, mock_status_broadcaster):
        """Test MCP status detects recently started server"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 2, "total_registered": 2, "stale_connections": 0},
            "server_info": {"restart_count": 0, "uptime_seconds": 30.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context)

            assert result["success"] is True
            assert result["server_info"]["status"] == "restarted"

    @pytest.mark.asyncio
    async def test_mcp_status_connection_manager_error(self, mock_context, mock_status_broadcaster):
        """Test MCP status handles connection manager errors"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   side_effect=Exception("Connection manager unavailable")), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context)

            assert result["success"] is True
            assert result["server_info"]["status"] == "degraded"
            assert "error" in result["connection_info"]

    @pytest.mark.asyncio
    async def test_mcp_status_broadcaster_error(self, mock_context, mock_connection_manager):
        """Test MCP status handles broadcaster errors"""
        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   side_effect=Exception("Broadcaster unavailable")):
            result = await _get_mcp_status(mock_context)

            assert result["success"] is True
            assert result["broadcast_info"]["broadcasting_active"] is False

    @pytest.mark.asyncio
    async def test_mcp_status_with_stale_connections(self, mock_context, mock_connection_manager,
                                                     mock_status_broadcaster):
        """Test MCP status includes recommendations for stale connections"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 2, "total_registered": 5, "stale_connections": 3},
            "server_info": {"restart_count": 0, "uptime_seconds": 3600.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": []
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager), \
             patch('fastmcp.server.manage_connection_tool.get_status_broadcaster',
                   return_value=mock_status_broadcaster):
            result = await _get_mcp_status(mock_context)

            assert result["success"] is True
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_register_for_updates_none_context(self):
        """Test registration with None context"""
        result = await _register_for_status_updates(None)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_connection_health_with_active_clients(self, mock_context, mock_connection_manager):
        """Test connection health with active clients listed"""
        mock_connection_manager.get_connection_stats = AsyncMock(return_value={
            "connections": {"active_connections": 2, "total_registered": 2, "stale_connections": 0},
            "server_info": {"restart_count": 0, "uptime_seconds": 3600.0, "start_time": "2025-01-27T10:00:00"},
            "active_clients": [
                {
                    "client_name": "cursor",
                    "client_version": "0.1.0",
                    "connection_age_seconds": 1800.0,
                    "health_checks": 60
                }
            ]
        })

        with patch('fastmcp.server.manage_connection_tool.get_connection_manager',
                   return_value=mock_connection_manager):
            result = await _connection_health_check(mock_context)

            assert result["success"] is True
            assert len(result["connection_manager"]["active_clients"]) > 0

    def test_format_health_check_with_connection_error(self):
        """Test health check formatting with connection error"""
        health_data = {
            "success": True,
            "status": "healthy",
            "server_name": "agenthub",
            "version": "2.1.0",
            "timestamp": time.time(),
            "authentication": {"enabled": True, "mvp_mode": False},
            "task_management": {"task_management_enabled": True, "enabled_tools_count": 15},
            "connections": {"error": "Connection manager unavailable"}
        }

        formatted = _format_health_check_response(health_data)

        assert "Server Health Check" in formatted
        assert "Connections" in formatted
        assert "Error" in formatted

    def test_format_connection_health_with_error(self):
        """Test connection health formatting with error"""
        health_data = {
            "success": False,
            "server_status": "error",
            "error": "Connection failed",
            "troubleshooting": {
                "immediate_steps": ["Check Docker", "Restart server"]
            }
        }

        formatted = _format_connection_health_response(health_data)

        assert "Connection Health Status" in formatted
        assert "Error Details" in formatted
        assert "Immediate Troubleshooting" in formatted

    def test_format_connection_health_with_reconnection_required(self):
        """Test connection health formatting when reconnection required"""
        health_data = {
            "success": True,
            "server_status": "healthy",
            "current_session_id": "test-123",
            "timestamp": "2025-01-27T10:00:00",
            "connection_manager": {
                "server_info": {"uptime_seconds": 100.0, "restart_count": 1, "start_time": ""},
                "connections": {"active_connections": 0, "total_registered": 1, "stale_connections": 0},
                "active_clients": []
            },
            "reconnection_info": {"recommended_action": "reconnect"},
            "troubleshooting": {
                "cursor_reconnection": ["Step 1"],
                "docker_rebuild": ["Step 2"],
                "alternative_methods": ["Step 3"]
            }
        }

        formatted = _format_connection_health_response(health_data)

        assert "Reconnection Required" in formatted
        assert "Quick Cursor Reconnection" in formatted

    def test_format_status_with_active_clients(self):
        """Test status formatting with active clients"""
        status_data = {
            "success": True,
            "server_info": {"name": "agenthub", "version": "2.1.0", "status": "healthy"},
            "connection_info": {"active_connections": 2, "uptime_seconds": 3600.0},
            "auth_info": {"enabled": True, "mvp_mode": False},
            "container_info": {"is_docker": True, "transport": "http", "host": "localhost", "port": "8000"},
            "active_clients": [
                {
                    "client_name": "cursor",
                    "client_version": "0.1.0",
                    "session_id": "test-123",
                    "connection_age_seconds": 1800.0,
                    "health_checks": 60
                }
            ]
        }

        formatted = _format_status_response(status_data)

        assert "Active Clients" in formatted
        assert "cursor" in formatted

    def test_format_status_with_broadcast_info(self):
        """Test status formatting with broadcasting information"""
        status_data = {
            "success": True,
            "server_info": {"name": "agenthub", "version": "2.1.0", "status": "healthy"},
            "connection_info": {"active_connections": 2, "uptime_seconds": 3600.0},
            "auth_info": {"enabled": True, "mvp_mode": False},
            "container_info": {"is_docker": True},
            "broadcast_info": {
                "broadcasting_active": True,
                "registered_clients": 3,
                "last_broadcast": {
                    "event_type": "status_update",
                    "server_status": "healthy"
                }
            }
        }

        formatted = _format_status_response(status_data)

        assert "Real-time Updates" in formatted
        assert "Broadcasting Active" in formatted
