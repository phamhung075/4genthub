"""Test suite for MCP Keycloak Authentication

Comprehensive test coverage for MCP Keycloak authentication including:
- Token validation with Keycloak integration
- Role-based permissions and tool access
- Session management
- Decorator functionality
- Error handling and edge cases
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from functools import wraps

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from fastmcp.auth.mcp_keycloak_auth import (
    MCPKeycloakAuth,
    mcp_auth,
    get_mcp_user,
    require_mcp_auth
)


class TestMCPKeycloakAuth:
    """Test MCPKeycloakAuth class"""
    
    @pytest.fixture
    def auth_instance(self):
        """Create MCPKeycloakAuth instance"""
        with patch('fastmcp.auth.mcp_keycloak_auth.KeycloakAuthProvider') as mock_provider:
            auth = MCPKeycloakAuth()
            # Replace with mock provider
            auth.keycloak_provider = AsyncMock()
            return auth
    
    def test_initialization_enabled(self):
        """Test initialization with auth enabled"""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true"}):
            with patch('fastmcp.auth.mcp_keycloak_auth.KeycloakAuthProvider'):
                auth = MCPKeycloakAuth()
                assert auth.mcp_auth_enabled is True
                assert auth.required_roles == ["mcp-user", "mcp-tools"]
    
    def test_initialization_disabled(self):
        """Test initialization with auth disabled"""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            with patch('fastmcp.auth.mcp_keycloak_auth.KeycloakAuthProvider'):
                auth = MCPKeycloakAuth()
                assert auth.mcp_auth_enabled is False
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_auth_disabled(self, auth_instance):
        """Test token validation when auth is disabled"""
        auth_instance.mcp_auth_enabled = False
        
        result = await auth_instance.validate_mcp_token("any.token")
        
        assert result["active"] is True
        assert result["sub"] == "dev-user"
        assert result["email"] == "dev@localhost"
        assert "mcp-user" in result["roles"]
        assert "mcp-tools" in result["roles"]
        assert "admin" in result["roles"]
        assert result["permissions"] == ["*"]
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_valid(self, auth_instance):
        """Test validation of valid MCP token"""
        auth_instance.mcp_auth_enabled = True
        
        # Mock Keycloak token data
        mock_token_data = {
            "sub": "user-123",
            "email": "user@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["mcp-user", "mcp-tools"]},
            "resource_access": {},
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        auth_instance.keycloak_provider.validate_token.return_value = mock_token_data
        
        result = await auth_instance.validate_mcp_token("valid.token")
        
        assert result["active"] is True
        assert result["sub"] == "user-123"
        assert result["email"] == "user@example.com"
        assert result["mcp_access"] is True
        assert "mcp-user" in result["roles"]
        assert "mcp-tools" in result["roles"]
        assert "tools:execute" in result["mcp_permissions"]
        assert result["mcp_tools"] is not None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_invalid(self, auth_instance):
        """Test validation of invalid token"""
        auth_instance.mcp_auth_enabled = True
        auth_instance.keycloak_provider.validate_token.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_instance.validate_mcp_token("invalid.token")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_insufficient_roles(self, auth_instance):
        """Test validation with insufficient roles"""
        auth_instance.mcp_auth_enabled = True
        
        mock_token_data = {
            "sub": "user-456",
            "realm_access": {"roles": ["regular-user"]},  # Missing required MCP roles
            "resource_access": {}
        }
        
        auth_instance.keycloak_provider.validate_token.return_value = mock_token_data
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_instance.validate_mcp_token("limited.token")
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
        assert "mcp-user" in exc_info.value.detail or "mcp-tools" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_client_specific_roles(self, auth_instance):
        """Test validation with client-specific roles"""
        auth_instance.mcp_auth_enabled = True
        auth_instance.keycloak_provider.client_id = "mcp-client"
        
        mock_token_data = {
            "sub": "user-789",
            "realm_access": {"roles": []},
            "resource_access": {
                "mcp-client": {
                    "roles": ["mcp-tools"]  # Client-specific role
                }
            }
        }
        
        auth_instance.keycloak_provider.validate_token.return_value = mock_token_data
        
        result = await auth_instance.validate_mcp_token("client.token")
        
        assert result["mcp_access"] is True
        assert "mcp-tools" in result["roles"]
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_exception_handling(self, auth_instance):
        """Test exception handling during validation"""
        auth_instance.mcp_auth_enabled = True
        auth_instance.keycloak_provider.validate_token.side_effect = Exception("Service error")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_instance.validate_mcp_token("error.token")
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Authentication service error"
    
    def test_build_mcp_permissions_admin(self, auth_instance):
        """Test permission building for admin role"""
        permissions = auth_instance._build_mcp_permissions(["mcp-admin"])
        assert permissions == ["*"]
    
    def test_build_mcp_permissions_developer(self, auth_instance):
        """Test permission building for developer role"""
        permissions = auth_instance._build_mcp_permissions(["mcp-developer"])
        
        expected = ["tools:*", "context:*", "agents:*", "projects:*"]
        assert all(perm in permissions for perm in expected)
    
    def test_build_mcp_permissions_user(self, auth_instance):
        """Test permission building for user role"""
        permissions = auth_instance._build_mcp_permissions(["mcp-user"])
        
        expected = ["tools:list", "tools:describe", "context:read"]
        assert all(perm in permissions for perm in expected)
    
    def test_build_mcp_permissions_multiple_roles(self, auth_instance):
        """Test permission building with multiple roles"""
        permissions = auth_instance._build_mcp_permissions(["mcp-user", "mcp-tools"])
        
        # Should combine permissions from both roles
        assert "tools:execute" in permissions  # From mcp-tools
        assert "tools:list" in permissions     # From mcp-user
        assert "context:read" in permissions   # From both
        
        # Should have no duplicates
        assert len(permissions) == len(set(permissions))
    
    def test_get_allowed_tools_admin(self, auth_instance):
        """Test allowed tools for admin"""
        tools = auth_instance._get_allowed_tools(["mcp-admin"])
        assert tools == {"all": ["*"]}
        
        tools = auth_instance._get_allowed_tools(["admin"])
        assert tools == {"all": ["*"]}
    
    def test_get_allowed_tools_developer(self, auth_instance):
        """Test allowed tools for developer"""
        tools = auth_instance._get_allowed_tools(["mcp-developer"])
        
        assert "manage_project" in tools["project"]
        assert "manage_git_branch" in tools["project"]
        assert "manage_task" in tools["task"]
        assert "call_agent" in tools["agent"]
        assert tools["development"] == ["*"]
    
    def test_get_allowed_tools_regular_user(self, auth_instance):
        """Test allowed tools for regular user"""
        tools = auth_instance._get_allowed_tools(["mcp-user"])
        
        assert tools["task"] == ["search_task"]
        assert tools["context"] == ["get_context"]
        assert "manage_task" not in tools.get("task", [])
    
    def test_get_allowed_tools_combined_roles(self, auth_instance):
        """Test allowed tools with combined roles"""
        tools = auth_instance._get_allowed_tools(["mcp-user", "mcp-tools"])
        
        # Should have combined access
        assert "manage_task" in tools["task"]  # From mcp-tools
        assert "search_task" in tools["task"]  # From mcp-user
        assert "call_agent" in tools["agent"]  # From mcp-tools
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, auth_instance):
        """Test get_current_user dependency"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test.token"
        )
        
        expected_user = {
            "active": True,
            "sub": "user-123",
            "mcp_access": True
        }
        
        with patch.object(auth_instance, 'validate_mcp_token') as mock_validate:
            mock_validate.return_value = expected_user
            
            result = await auth_instance.get_current_user(credentials)
            
            assert result == expected_user
            mock_validate.assert_called_once_with("test.token")
    
    @pytest.mark.asyncio
    async def test_require_mcp_permission_decorator_success(self, auth_instance):
        """Test permission decorator with valid permission"""
        @auth_instance.require_mcp_permission("tools:execute")
        async def test_function(current_user=None):
            return "success"
        
        user = {
            "mcp_permissions": ["tools:execute", "context:read"]
        }
        
        result = await test_function(current_user=user)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_mcp_permission_decorator_wildcard(self, auth_instance):
        """Test permission decorator with wildcard permission"""
        @auth_instance.require_mcp_permission("tools:execute")
        async def test_function(current_user=None):
            return "success"
        
        user = {
            "mcp_permissions": ["*"]  # Wildcard permission
        }
        
        result = await test_function(current_user=user)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_mcp_permission_decorator_denied(self, auth_instance):
        """Test permission decorator with missing permission"""
        @auth_instance.require_mcp_permission("tools:execute")
        async def test_function(current_user=None):
            return "success"
        
        user = {
            "mcp_permissions": ["tools:list", "context:read"]  # Missing tools:execute
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await test_function(current_user=user)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail
        assert "tools:execute" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_mcp_permission_decorator_no_user(self, auth_instance):
        """Test permission decorator without user"""
        @auth_instance.require_mcp_permission("tools:execute")
        async def test_function(current_user=None):
            return "success"
        
        with pytest.raises(HTTPException) as exc_info:
            await test_function(current_user=None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
    
    @pytest.mark.asyncio
    async def test_require_tool_access_decorator_success(self, auth_instance):
        """Test tool access decorator with valid access"""
        @auth_instance.require_tool_access("manage_task")
        async def test_function(current_user=None):
            return "success"
        
        user = {
            "mcp_tools": {
                "task": ["manage_task", "search_task"]
            }
        }
        
        result = await test_function(current_user=user)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_tool_access_decorator_wildcard(self, auth_instance):
        """Test tool access decorator with wildcard"""
        @auth_instance.require_tool_access("manage_task")
        async def test_function(current_user=None):
            return "success"
        
        # Test with all tools wildcard
        user = {"mcp_tools": {"all": ["*"]}}
        result = await test_function(current_user=user)
        assert result == "success"
        
        # Test with category wildcard
        user = {"mcp_tools": {"task": ["*"]}}
        result = await test_function(current_user=user)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_tool_access_decorator_denied(self, auth_instance):
        """Test tool access decorator with denied access"""
        @auth_instance.require_tool_access("manage_task")
        async def test_function(current_user=None):
            return "success"
        
        user = {
            "mcp_tools": {
                "task": ["search_task"]  # Only search, not manage
            }
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await test_function(current_user=user)
        
        assert exc_info.value.status_code == 403
        assert "Access denied to tool: manage_task" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_create_mcp_session(self, auth_instance):
        """Test MCP session creation"""
        user_data = {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": ["mcp-user", "mcp-tools"],
            "mcp_permissions": ["tools:execute", "context:read"],
            "mcp_tools": {"task": ["manage_task"]}
        }
        
        session = await auth_instance.create_mcp_session(user_data)
        
        assert session["user_id"] == "user-123"
        assert session["email"] == "user@example.com"
        assert session["roles"] == ["mcp-user", "mcp-tools"]
        assert session["permissions"] == ["tools:execute", "context:read"]
        assert session["tools"] == {"task": ["manage_task"]}
        assert "session_id" in session
        assert "created_at" in session
        assert "expires_at" in session
        
        # Check session expiry is 24 hours
        created = datetime.fromisoformat(session["created_at"])
        expires = datetime.fromisoformat(session["expires_at"])
        duration = expires - created
        assert 23 <= duration.total_seconds() / 3600 <= 25  # Allow some variance
    
    @pytest.mark.asyncio
    async def test_validate_tool_request_allowed(self, auth_instance):
        """Test tool request validation - allowed"""
        user_data = {
            "mcp_tools": {"task": ["manage_task"]},
            "roles": ["mcp-user"]
        }
        
        result = await auth_instance.validate_tool_request(
            "manage_task",
            user_data,
            {"action": "create"}
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_tool_request_admin_wildcard(self, auth_instance):
        """Test tool request validation - admin wildcard"""
        user_data = {
            "mcp_tools": {"all": ["*"]},
            "roles": ["mcp-admin"]
        }
        
        result = await auth_instance.validate_tool_request(
            "any_tool",
            user_data
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_tool_request_denied(self, auth_instance):
        """Test tool request validation - denied"""
        user_data = {
            "mcp_tools": {"task": ["search_task"]},
            "roles": ["mcp-user"]
        }
        
        result = await auth_instance.validate_tool_request(
            "manage_task",
            user_data
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_tool_request_parameter_validation(self, auth_instance):
        """Test tool request validation with parameter checks"""
        # Non-admin trying to delete project
        user_data = {
            "mcp_tools": {"project": ["manage_project"]},
            "roles": ["mcp-developer"]
        }
        
        result = await auth_instance.validate_tool_request(
            "manage_project",
            user_data,
            {"action": "delete"}
        )
        
        assert result is False
        
        # Admin can delete
        user_data["roles"] = ["mcp-admin"]
        result = await auth_instance.validate_tool_request(
            "manage_project",
            user_data,
            {"action": "delete"}
        )
        
        assert result is True


class TestGlobalFunctions:
    """Test global functions and dependencies"""
    
    @pytest.mark.asyncio
    async def test_get_mcp_user_dependency(self):
        """Test get_mcp_user FastAPI dependency"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test.token"
        )
        
        expected_user = {
            "active": True,
            "sub": "user-123"
        }
        
        with patch.object(mcp_auth, 'validate_mcp_token') as mock_validate:
            mock_validate.return_value = expected_user
            
            result = await get_mcp_user(credentials)
            
            assert result == expected_user
            mock_validate.assert_called_once_with("test.token")
    
    @pytest.mark.asyncio
    async def test_require_mcp_auth_decorator_enabled(self):
        """Test require_mcp_auth decorator with auth enabled"""
        @require_mcp_auth
        async def protected_function():
            return "protected"
        
        with patch.object(mcp_auth, 'mcp_auth_enabled', True):
            result = await protected_function()
            assert result == "protected"
    
    @pytest.mark.asyncio
    async def test_require_mcp_auth_decorator_disabled(self):
        """Test require_mcp_auth decorator with auth disabled"""
        @require_mcp_auth
        async def protected_function():
            return "protected"
        
        with patch.object(mcp_auth, 'mcp_auth_enabled', False):
            result = await protected_function()
            assert result == "protected"


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow"""
        with patch('fastmcp.auth.mcp_keycloak_auth.KeycloakAuthProvider') as mock_provider_class:
            # Create auth instance
            auth = MCPKeycloakAuth()
            auth.keycloak_provider = AsyncMock()
            
            # Mock Keycloak response
            keycloak_token_data = {
                "sub": "integration-user",
                "email": "integration@example.com",
                "preferred_username": "integrationuser",
                "realm_access": {"roles": ["mcp-developer"]},
                "resource_access": {},
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            }
            
            auth.keycloak_provider.validate_token.return_value = keycloak_token_data
            
            # Validate token
            mcp_user = await auth.validate_mcp_token("integration.token")
            
            # Check user data
            assert mcp_user["sub"] == "integration-user"
            assert mcp_user["mcp_access"] is True
            assert "mcp-developer" in mcp_user["roles"]
            assert "tools:*" in mcp_user["mcp_permissions"]
            
            # Create session
            session = await auth.create_mcp_session(mcp_user)
            assert session["user_id"] == "integration-user"
            
            # Validate tool request
            can_manage_project = await auth.validate_tool_request(
                "manage_project",
                mcp_user
            )
            assert can_manage_project is True
            
            # Cannot delete without admin role
            can_delete = await auth.validate_tool_request(
                "manage_project",
                mcp_user,
                {"action": "delete"}
            )
            assert can_delete is False
    
    @pytest.mark.asyncio
    async def test_decorator_integration(self):
        """Test decorator integration"""
        auth = MCPKeycloakAuth()
        
        # Define protected function
        @auth.require_tool_access("manage_task")
        @auth.require_mcp_permission("tools:execute")
        async def protected_tool(current_user=None):
            return f"User {current_user['sub']} executed tool"
        
        # Test with valid user
        user = {
            "sub": "test-user",
            "mcp_permissions": ["tools:execute"],
            "mcp_tools": {"task": ["manage_task"]}
        }
        
        result = await protected_tool(current_user=user)
        assert result == "User test-user executed tool"
        
        # Test with missing permission
        user_no_perm = {
            "sub": "limited-user",
            "mcp_permissions": ["tools:list"],
            "mcp_tools": {"task": ["manage_task"]}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await protected_tool(current_user=user_no_perm)
        
        assert exc_info.value.status_code == 403
        assert "tools:execute" in exc_info.value.detail