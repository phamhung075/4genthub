"""
MCP Authentication Middleware with Keycloak Integration

This module provides authentication middleware for MCP tools using Keycloak tokens.
It validates tokens from Keycloak and manages MCP tool access.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from .keycloak_integration import KeycloakAuthProvider

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer()

class MCPKeycloakAuth:
    """MCP Authentication handler using Keycloak tokens"""

    def __init__(self):
        """Initialize MCP Keycloak authentication"""
        self.keycloak_provider = KeycloakAuthProvider()
        self.mcp_auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
        self.required_roles = ["mcp-user", "mcp-tools"]  # Required roles for MCP access
        self.jwks_cache = None
        self.jwks_cache_time = None

        logger.info(f"MCP Keycloak Auth initialized (enabled: {self.mcp_auth_enabled})")

    async def validate_mcp_token(self, token: str) -> Dict[str, Any]:
        """
        Validate MCP token from Keycloak

        Args:
            token: Bearer token from request

        Returns:
            Validated token data with user info and permissions

        Raises:
            HTTPException: If token is invalid or user lacks permissions
        """
        if not self.mcp_auth_enabled:
            # Auth disabled, return mock user for development
            return {
                "active": True,
                "sub": "dev-user",
                "email": "dev@localhost",
                "roles": ["mcp-user", "mcp-tools", "admin"],
                "permissions": ["*"]
            }

        try:
            # Validate token with Keycloak
            token_data = await self.keycloak_provider.validate_token(token)

            if not token_data:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token"
                )

            # Extract user roles from Keycloak token payload
            realm_access = token_data.get("realm_access", {})
            roles = realm_access.get("roles", [])
            
            # Also check resource access for client-specific roles
            resource_access = token_data.get("resource_access", {})
            client_access = resource_access.get(self.keycloak_provider.client_id, {})
            if client_access:
                roles.extend(client_access.get("roles", []))

            # Check if user has required MCP roles
            has_mcp_access = any(role in roles for role in self.required_roles)

            if not has_mcp_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required roles: {self.required_roles}"
                )

            # Build MCP permissions based on roles
            permissions = self._build_mcp_permissions(roles)

            # Build response data with MCP-specific information
            mcp_token_data = {
                "active": True,
                "sub": token_data.get("sub"),
                "email": token_data.get("email"),
                "preferred_username": token_data.get("preferred_username"),
                "roles": roles,
                "mcp_access": True,
                "mcp_permissions": permissions,
                "mcp_tools": self._get_allowed_tools(roles),
                "exp": token_data.get("exp"),
                "iat": token_data.get("iat")
            }

            return mcp_token_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Authentication service error"
            )

    def _build_mcp_permissions(self, roles: List[str]) -> List[str]:
        """
        Build MCP permissions based on user roles

        Args:
            roles: List of user roles from Keycloak

        Returns:
            List of MCP permissions
        """
        permissions = []

        # Map roles to permissions
        role_permissions = {
            "mcp-admin": ["*"],  # Full access
            "mcp-tools": [
                "tools:execute",
                "tools:list",
                "tools:describe",
                "context:read",
                "context:write"
            ],
            "mcp-user": [
                "tools:list",
                "tools:describe",
                "context:read"
            ],
            "mcp-developer": [
                "tools:*",
                "context:*",
                "agents:*",
                "projects:*"
            ]
        }

        for role in roles:
            if role in role_permissions:
                permissions.extend(role_permissions[role])

        # Remove duplicates
        return list(set(permissions))

    def _get_allowed_tools(self, roles: List[str]) -> Dict[str, List[str]]:
        """
        Get list of allowed MCP tools based on roles

        Args:
            roles: List of user roles

        Returns:
            Dictionary of tool categories and allowed tools
        """
        # Define tool access by role
        if "mcp-admin" in roles or "admin" in roles:
            # Admin has access to all tools
            return {"all": ["*"]}

        allowed_tools = {}

        if "mcp-developer" in roles:
            allowed_tools.update({
                "project": ["manage_project", "manage_git_branch"],
                "task": ["manage_task", "manage_subtask"],
                "context": ["manage_context"],
                "agent": ["call_agent", "manage_agent"],
                "development": ["*"]
            })

        if "mcp-tools" in roles:
            allowed_tools.update({
                "task": ["manage_task", "search_task"],
                "context": ["manage_context"],
                "agent": ["call_agent"]
            })

        if "mcp-user" in roles:
            allowed_tools.update({
                "task": ["search_task"],
                "context": ["get_context"]
            })

        return allowed_tools

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        FastAPI dependency to get current authenticated user

        Args:
            credentials: HTTP Bearer credentials

        Returns:
            Validated user data
        """
        token = credentials.credentials
        return await self.validate_mcp_token(token)

    def require_mcp_permission(self, permission: str):
        """
        Decorator to require specific MCP permission

        Args:
            permission: Required permission string

        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get user from kwargs (injected by FastAPI)
                user = kwargs.get("current_user")

                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required"
                    )

                permissions = user.get("mcp_permissions", [])

                # Check for wildcard or specific permission
                if "*" not in permissions and permission not in permissions:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied. Required: {permission}"
                    )

                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def require_tool_access(self, tool_name: str):
        """
        Decorator to require access to specific MCP tool

        Args:
            tool_name: Name of the MCP tool

        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get user from kwargs
                user = kwargs.get("current_user")

                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required"
                    )

                allowed_tools = user.get("mcp_tools", {})

                # Check if user has access to all tools
                if allowed_tools.get("all") == ["*"]:
                    return await func(*args, **kwargs)

                # Check specific tool access
                tool_allowed = False
                for category, tools in allowed_tools.items():
                    if "*" in tools or tool_name in tools:
                        tool_allowed = True
                        break

                if not tool_allowed:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied to tool: {tool_name}"
                    )

                return await func(*args, **kwargs)

            return wrapper
        return decorator

    async def create_mcp_session(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create MCP session for authenticated user

        Args:
            user_data: Validated user data from Keycloak

        Returns:
            MCP session data
        """
        session_id = f"mcp-{user_data['sub']}-{datetime.utcnow().timestamp()}"

        session = {
            "session_id": session_id,
            "user_id": user_data["sub"],
            "email": user_data.get("email"),
            "roles": user_data.get("roles", []),
            "permissions": user_data.get("mcp_permissions", []),
            "tools": user_data.get("mcp_tools", {}),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }

        # Store session in cache/database if needed
        # For now, return the session data
        return session

    async def validate_tool_request(
        self,
        tool_name: str,
        user_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate if user can execute specific tool with parameters

        Args:
            tool_name: Name of the MCP tool
            user_data: User data from token
            parameters: Tool parameters to validate

        Returns:
            True if request is valid, False otherwise
        """
        # Check basic tool access
        allowed_tools = user_data.get("mcp_tools", {})

        if allowed_tools.get("all") == ["*"]:
            return True

        # Check specific tool
        tool_allowed = False
        for category, tools in allowed_tools.items():
            if "*" in tools or tool_name in tools:
                tool_allowed = True
                break

        if not tool_allowed:
            return False

        # Additional parameter validation if needed
        if parameters:
            # Add custom validation logic for specific tools
            if tool_name == "manage_project" and parameters.get("action") == "delete":
                # Only admins can delete projects
                if "mcp-admin" not in user_data.get("roles", []):
                    return False

        return True

# Global instance
mcp_auth = MCPKeycloakAuth()

# FastAPI dependencies
async def get_mcp_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency for MCP authentication

    Args:
        credentials: Bearer token from request

    Returns:
        Validated user data with MCP permissions
    """
    return await mcp_auth.validate_mcp_token(credentials.credentials)

def require_mcp_auth(func):
    """
    Decorator for functions requiring MCP authentication

    Usage:
        @require_mcp_auth
        async def my_mcp_tool(current_user: Dict = Depends(get_mcp_user)):
            # Tool implementation
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if auth is enabled
        if not mcp_auth.mcp_auth_enabled:
            # Auth disabled, proceed without validation
            return await func(*args, **kwargs)

        # Auth is handled by FastAPI dependency injection
        return await func(*args, **kwargs)

    return wrapper