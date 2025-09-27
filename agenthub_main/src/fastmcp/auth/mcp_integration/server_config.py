"""
MCP Server Configuration with JWT Authentication

This module provides configuration helpers to integrate JWT authentication
with the MCP server.
"""

import os
from typing import Optional, List
from starlette.middleware import Middleware

from fastmcp.server.auth.auth import OAuthProvider
from .jwt_auth_backend import JWTAuthBackend, create_jwt_auth_backend
# UserContextMiddleware has been replaced with RequestContextMiddleware
try:
    from ..middleware.request_context_middleware import RequestContextMiddleware as UserContextMiddleware
except ImportError:
    # Fallback if middleware not available
    UserContextMiddleware = None


def configure_jwt_auth_for_mcp(
    required_scopes: Optional[List[str]] = None,
    database_session_factory=None
) -> JWTAuthBackend:
    """
    Configure JWT authentication for MCP server.
    
    Args:
        required_scopes: List of required scopes for MCP access
        database_session_factory: Database session factory for user lookups
        
    Returns:
        Configured JWT auth backend
    """
    # Set default required scopes if not provided
    if required_scopes is None:
        required_scopes = ["mcp:access"]
    
    # Create JWT auth backend
    auth_backend = create_jwt_auth_backend(
        database_session_factory=database_session_factory,
        required_scopes=required_scopes
    )
    
    return auth_backend


def get_jwt_middleware(
    jwt_backend: Optional[JWTAuthBackend] = None
) -> List[Middleware]:
    """
    Get middleware list for JWT authentication.
    
    Args:
        jwt_backend: JWT auth backend (will create default if not provided)
        
    Returns:
        List of middleware for JWT authentication
    """
    if jwt_backend is None:
        jwt_backend = configure_jwt_auth_for_mcp()
    
    middleware_list = []
    if UserContextMiddleware is not None:
        middleware_list.append(
            Middleware(UserContextMiddleware, jwt_backend=jwt_backend)
        )
    
    return middleware_list


def setup_mcp_with_jwt_auth(
    mcp_server,
    required_scopes: Optional[List[str]] = None,
    database_session_factory=None
) -> None:
    """
    Setup MCP server with JWT authentication.
    
    This function configures the MCP server to use JWT authentication
    for all operations.
    
    Args:
        mcp_server: The MCP server instance
        required_scopes: List of required scopes
        database_session_factory: Database session factory
    """
    # Create JWT auth backend
    auth_backend = configure_jwt_auth_for_mcp(
        required_scopes=required_scopes,
        database_session_factory=database_session_factory
    )
    
    # Set as the auth provider for the MCP server
    mcp_server.auth = auth_backend
    
    # Add user context middleware
    middleware = get_jwt_middleware(auth_backend)
    if hasattr(mcp_server, 'middleware'):
        mcp_server.middleware.extend(middleware)
    else:
        mcp_server.middleware = middleware


def integrate_jwt_with_http_server(
    http_server_factory_kwargs: dict,
    database_session_factory=None
) -> dict:
    """
    Integrate JWT authentication with HTTP server factory kwargs.
    
    This function modifies the kwargs passed to create_sse_app or
    create_streamable_http_app to include JWT authentication.
    
    Args:
        http_server_factory_kwargs: Kwargs for HTTP server creation
        database_session_factory: Database session factory
        
    Returns:
        Modified kwargs with JWT auth integrated
    """
    # Create JWT auth backend
    auth_backend = configure_jwt_auth_for_mcp(
        database_session_factory=database_session_factory
    )
    
    # Add auth to kwargs
    http_server_factory_kwargs['auth'] = auth_backend
    
    # Add middleware
    middleware = http_server_factory_kwargs.get('middleware', [])
    middleware.extend(get_jwt_middleware(auth_backend))
    http_server_factory_kwargs['middleware'] = middleware
    
    return http_server_factory_kwargs


# Environment variable helpers
def configure_jwt_from_env() -> dict:
    """
    Configure JWT settings from environment variables.
    
    Returns:
        Dictionary of JWT configuration
    """
    config = {
        'secret_key': os.getenv('JWT_SECRET_KEY'),
        'issuer': os.getenv('JWT_ISSUER', 'agenthub'),
        'audience': 'mcp-server',  # Default audience, not configured via environment
        'algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
        'access_token_expire_minutes': int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '15')),
        'refresh_token_expire_days': int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '30')),
    }
    
    # Validate required settings
    if not config['secret_key']:
        raise ValueError("JWT_SECRET_KEY environment variable must be set")
    
    return config


def validate_jwt_configuration() -> bool:
    """
    Validate that JWT is properly configured.
    
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        config = configure_jwt_from_env()
        
        # Check secret key strength
        if len(config['secret_key']) < 32:
            raise ValueError("JWT_SECRET_KEY should be at least 32 characters for security")
        
        # Validate token expiration times
        if config['access_token_expire_minutes'] < 5:
            raise ValueError("Access token expiration should be at least 5 minutes")
        
        if config['refresh_token_expire_days'] < 1:
            raise ValueError("Refresh token expiration should be at least 1 day")
        
        return True
        
    except Exception as e:
        raise ValueError(f"JWT configuration validation failed: {e}")