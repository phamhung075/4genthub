"""
Authentication Utilities (DEPRECATED - Middleware removed)

This module provides utility functions for authentication.
The AuthenticationMiddleware class has been removed in favor of OAuth2PasswordBearer.

For protected endpoints, use dependencies from fastapi_auth.py:
- get_current_user
- get_current_active_user  
- require_roles
- require_admin
"""

import logging
from typing import Optional
from fastapi import Request
from ..domain.entities.user import UserRole

logger = logging.getLogger(__name__)


# Legacy utility functions - kept for backward compatibility
# These functions rely on request.state which was set by the old middleware
# Consider migrating to OAuth2PasswordBearer dependencies instead

def get_current_user_id(request: Request) -> Optional[str]:
    """
    Get current user ID from request state (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using get_current_user from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        
    Returns:
        User ID if authenticated, None otherwise
    """
    return getattr(request.state, "user_id", None)


def get_current_user_email(request: Request) -> Optional[str]:
    """
    Get current user email from request state (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using get_current_user from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        
    Returns:
        User email if authenticated, None otherwise
    """
    return getattr(request.state, "user_email", None)


def get_current_user_roles(request: Request) -> list[str]:
    """
    Get current user roles from request state (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using get_current_user from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        
    Returns:
        User roles if authenticated, empty list otherwise
    """
    return getattr(request.state, "user_roles", [])


def is_authenticated(request: Request) -> bool:
    """
    Check if request is authenticated (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using get_current_user from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        
    Returns:
        True if authenticated, False otherwise
    """
    return hasattr(request.state, "user_id")


def has_role(request: Request, role: str) -> bool:
    """
    Check if authenticated user has specific role (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using require_roles from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        role: Role to check
        
    Returns:
        True if user has role, False otherwise
    """
    roles = get_current_user_roles(request)
    return role in roles


def is_admin(request: Request) -> bool:
    """
    Check if authenticated user is admin (DEPRECATED)
    
    This function relies on request.state set by the old middleware.
    Consider using require_admin from fastapi_auth.py instead.
    
    Args:
        request: FastAPI request
        
    Returns:
        True if user is admin, False otherwise
    """
    return has_role(request, UserRole.ADMIN.value)


# Re-export functions from fastapi_auth for backward compatibility
from .fastapi_auth import require_roles, require_admin

# For backward compatibility - these were exported from the old middleware
require_auth = None  # Removed - use get_current_user from fastapi_auth.py instead
AuthenticationMiddleware = None  # Removed - use OAuth2PasswordBearer dependencies instead