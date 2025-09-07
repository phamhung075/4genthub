"""
Authentication Server Integration

This module provides integration of authentication with the FastMCP server.
NOTE: AuthenticationMiddleware has been removed in favor of OAuth2PasswordBearer.
"""

import os
from typing import Optional, List
from starlette.routing import BaseRoute
from starlette.applications import Starlette

from ..interface.auth_endpoints import router as auth_router


def get_auth_routes() -> List[BaseRoute]:
    """
    Get authentication routes for mounting
    
    Returns:
        List of authentication routes
    """
    # Convert FastAPI router to Starlette routes
    # This would need proper conversion from FastAPI to Starlette
    # For now, return empty list - routes should be mounted differently
    return []


def create_auth_app() -> Starlette:
    """
    Create a standalone authentication Starlette app
    
    This can be mounted as a sub-application
    
    Returns:
        Starlette app with authentication endpoints
    """
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    
    async def register(request):
        """Register endpoint stub"""
        return JSONResponse({"message": "Registration endpoint"})
    
    async def login(request):
        """Login endpoint stub"""
        return JSONResponse({"message": "Login endpoint"})
    
    async def health(request):
        """Health check endpoint"""
        return JSONResponse({"status": "healthy"})
    
    routes = [
        Route("/register", register, methods=["POST"]),
        Route("/login", login, methods=["POST"]),
        Route("/health", health, methods=["GET"]),
    ]
    
    app = Starlette(routes=routes)
    return app


# DEPRECATED FUNCTIONS - Removed in OAuth2PasswordBearer migration
# setup_authentication() - No longer needed, use OAuth2PasswordBearer dependencies
# get_auth_middleware() - No longer needed, authentication handled by dependencies