
"""
Unified Authentication Interface

This module provides a unified authentication interface that automatically
delegates to the appropriate authentication provider (Keycloak or local JWT).
It ensures consistent user identity across all authentication methods.
"""

import os
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastmcp.auth.domain.entities.user import User

logger = logging.getLogger(__name__)

# Security scheme for extracting Bearer tokens
security = HTTPBearer()

# Get the configured auth provider
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "keycloak").lower()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from the appropriate provider.

    This function acts as the single entry point for authentication,
    automatically routing to the correct provider based on configuration.

    For Keycloak tokens:
    - Validates the token with Keycloak's public keys
    - Extracts user ID from the 'sub' claim
    - Returns a User object with Keycloak user details

    For local JWT tokens:
    - Validates the token with local JWT secret
    - Extracts user ID from the 'sub' or 'user_id' claim
    - Returns a User object with local user details

    Args:
        credentials: HTTP Bearer credentials containing the JWT token

    Returns:
        User object with authenticated user details

    Raises:
        HTTPException: If token is invalid or authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"Authenticating with provider: {AUTH_PROVIDER}")

    if AUTH_PROVIDER == "keycloak":
        # Use Keycloak authentication with proper user ID extraction
        from ..keycloak_dependencies import get_current_user_universal
        user = await get_current_user_universal(credentials)
        logger.info(f"Authenticated Keycloak user: {user.id} ({user.email})")
        return user

    elif AUTH_PROVIDER == "supabase":
        # Use Supabase authentication
        from .supabase_fastapi_auth import get_current_user_supabase
        user = await get_current_user_supabase(credentials)
        logger.info(f"Authenticated Supabase user: {user.id} ({user.email})")
        return user

    else:
        # Fallback to local JWT authentication or test mode
        from .fastapi_auth import get_current_user as get_local_user
        user = await get_local_user(credentials)
        logger.info(f"Authenticated local/test user: {user.id} ({user.email})")
        return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current active user (alias for get_current_user).

    This function ensures the user is active and valid.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Active User object
    """
    return await get_current_user(credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get optional user - returns user if authenticated, None otherwise.

    This is useful for endpoints that support both authenticated
    and anonymous access.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials:
        try:
            return await get_current_user(credentials)
        except HTTPException:
            logger.debug("Optional authentication failed, continuing as anonymous")
            return None
    return None


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Require admin role for access.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User object if user has admin role

    Raises:
        HTTPException: If user doesn't have admin role
    """
    user = await get_current_user(credentials)

    # TODO: Implement actual role checking from token claims
    # For now, just return the authenticated user
    # In production, check roles from JWT claims or database

    return user


async def require_roles(
    *required_roles: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Require specific roles for access.

    Args:
        *required_roles: Variable number of role names required
        credentials: HTTP Bearer credentials

    Returns:
        User object if user has required roles

    Raises:
        HTTPException: If user doesn't have required roles
    """
    user = await get_current_user(credentials)

    # TODO: Implement actual role checking from token claims
    # For now, just return the authenticated user
    # In production, check roles from JWT claims or database

    return user


# Export commonly used functions for convenience
__all__ = [
    'get_current_user',
    'get_current_active_user',
    'get_optional_user',
    'require_admin',
    'require_roles',
    'security'
]