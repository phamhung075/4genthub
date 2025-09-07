"""
MCP Authentication Configuration Helper

This module provides utilities to configure MCP server with JWT Bearer authentication,
making it easy to integrate with the token management system.
"""

import os
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.auth.providers.jwt_bearer import JWTBearerAuthProvider


def create_mcp_auth_provider(
    auth_type: str = "jwt",
    secret_key: Optional[str] = None,
    required_scopes: Optional[List[str]] = None,
    check_database: bool = True,
):
    """
    Create an MCP authentication provider based on configuration.
    
    Args:
        auth_type: Type of authentication ("jwt", "env", or "none")
        secret_key: JWT secret key (defaults to JWT_SECRET_KEY env var)
        required_scopes: Required scopes for MCP access
        check_database: Whether to validate tokens in database
        
    Returns:
        Authentication provider or None if auth_type is "none"
    """
    if auth_type == "none":
        return None
    
    if auth_type == "env":
        # Environment bearer auth no longer supported - use JWT instead
        return None
    
    if auth_type == "jwt":
        # Use JWT Bearer authentication with token management system
        from fastmcp.server.auth.providers.jwt_bearer import JWTBearerAuthProvider
        return JWTBearerAuthProvider(
            secret_key=secret_key,
            required_scopes=required_scopes or ["mcp:access"],
            check_database=check_database,
        )
    
    raise ValueError(f"Unknown auth_type: {auth_type}")


def get_default_auth_provider():
    """
    Get the default authentication provider based on environment configuration.
    
    Checks MCP_AUTH_TYPE environment variable:
    - "jwt": Use JWT Bearer authentication (default if JWT_SECRET_KEY is set)
    - "env": Use environment variable Bearer token
    - "none": No authentication
    
    Returns:
        Default authentication provider
    """
    # Check if authentication is explicitly disabled
    if os.getenv("DHAFNCK_AUTH_ENABLED", "true").lower() == "false":
        return None
    
    auth_type = os.getenv("MCP_AUTH_TYPE")
    
    # Auto-detect based on available configuration
    if not auth_type:
        if os.getenv("JWT_SECRET_KEY"):
            auth_type = "jwt"
        elif os.getenv("MCP_BEARER_TOKEN"):
            auth_type = "env"
        else:
            auth_type = "none"
    
    return create_mcp_auth_provider(auth_type=auth_type)


def configure_mcp_server_auth(server_instance):
    """
    Configure authentication for an MCP server instance.
    
    Args:
        server_instance: FastMCP server instance to configure
        
    Returns:
        The configured server instance
    """
    if not server_instance.auth:
        # No auth configured, use default
        server_instance.auth = get_default_auth_provider()
        
        if server_instance.auth:
            from fastmcp.utilities.logging import get_logger
            logger = get_logger(__name__)
            
            auth_type = type(server_instance.auth).__name__
            logger.info(f"MCP server configured with {auth_type} authentication")
    
    return server_instance