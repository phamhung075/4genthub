"""
MCP Authentication Middleware for HTTP Transport

This middleware extracts JWT tokens from HTTP Authorization headers
and sets the user context for MCP operations when using HTTP transport.
"""

import logging
from typing import Optional
from contextvars import ContextVar

from .jwt_auth_backend import JWTAuthBackend, MCPUserContext, create_jwt_auth_backend
from ..middleware.request_context_middleware import current_user_context

logger = logging.getLogger(__name__)


class MCPAuthMiddleware:
    """
    ASGI Middleware that extracts user context from JWT tokens for MCP HTTP requests.
    
    This middleware is specifically designed for the FastMCP server's HTTP transport
    and integrates with the existing user context system.
    """
    
    def __init__(self, app, jwt_backend: Optional[JWTAuthBackend] = None):
        """
        Initialize the middleware.
        
        Args:
            app: The ASGI application
            jwt_backend: JWT authentication backend
        """
        self.app = app
        self.jwt_backend = jwt_backend or create_jwt_auth_backend()
        logger.info("MCPAuthMiddleware initialized for HTTP transport")
    
    async def __call__(self, scope, receive, send):
        """
        ASGI middleware handler that extracts user context from JWT.
        
        This processes the Authorization header and sets the user context
        before passing the request to the MCP server.
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Reset context for this request
        token_value = current_user_context.set(None)
        
        try:
            # Extract Authorization header from scope
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                
                try:
                    # Validate token and get user context
                    access_token = await self.jwt_backend.load_access_token(token)
                    if access_token:
                        # Get user context from token
                        user_id = access_token.client_id
                        user_context = await self.jwt_backend._get_user_context(user_id)
                        
                        if user_context:
                            # Store in context variable for MCP tools to access
                            current_user_context.set(user_context)
                            logger.debug(f"MCP user context set for user {user_context.user_id}")
                            
                            # Also add to scope for other middlewares
                            if "state" not in scope:
                                scope["state"] = {}
                            scope["state"]["user_id"] = user_context.user_id
                            scope["state"]["user_email"] = user_context.email
                            scope["state"]["user_roles"] = user_context.roles
                            scope["state"]["user_scopes"] = access_token.scopes
                        else:
                            logger.warning(f"Could not get user context for user_id: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to validate JWT token: {e}")
                    # Continue without user context on error
            else:
                logger.debug("No Bearer token found in Authorization header")
            
            # Process the request with context set
            await self.app(scope, receive, send)
            
        except Exception as e:
            logger.error(f"Error in MCPAuthMiddleware: {e}")
            # Continue without user context on error
            await self.app(scope, receive, send)
        finally:
            # Reset context after request
            current_user_context.reset(token_value)


def get_mcp_auth_middleware(app, jwt_backend: Optional[JWTAuthBackend] = None):
    """
    Factory function to create MCPAuthMiddleware.
    
    Args:
        app: The ASGI application
        jwt_backend: Optional JWT backend, will create default if not provided
        
    Returns:
        MCPAuthMiddleware instance
    """
    return MCPAuthMiddleware(app, jwt_backend)