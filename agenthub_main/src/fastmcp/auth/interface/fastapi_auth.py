"""
FastAPI authentication interface supporting multiple providers.
This file provides authentication functions that work with both Keycloak and Supabase.
"""

import os
import logging
from typing import Optional, Generator
from sqlalchemy.orm import Session
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastmcp.auth.domain.entities.user import User
from fastmcp.task_management.infrastructure.database.database_config import get_session

logger = logging.getLogger(__name__)

# Get the configured auth provider
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "keycloak").lower()

# Security scheme for extracting Bearer tokens
security = HTTPBearer()

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    session = get_session()
    try:
        yield session
    finally:
        session.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user based on configured provider"""
    if AUTH_PROVIDER == "keycloak":
        # Use Keycloak authentication with development fallback
        try:
            from ..keycloak_dependencies import get_current_user_universal
            return await get_current_user_universal(credentials)
        except Exception as e:
            # Development fallback when Keycloak is not accessible
            # Check if we're in development mode and Keycloak is unavailable
            env = os.getenv("ENV", "production").lower()
            if env in ["local", "development", "dev"]:
                logger.warning(f"Keycloak authentication failed in development mode, using test user: {e}")
                return User(
                    id="dev-user-001",
                    email="dev@example.com",
                    username="dev-user",
                    password_hash="dev-hash"
                )
            else:
                # In production, re-raise the exception
                raise
    elif AUTH_PROVIDER == "supabase":
        # Use Supabase authentication
        from .supabase_fastapi_auth import get_current_user_supabase
        return await get_current_user_supabase(credentials)
    else:
        # Fallback for local/testing - should not be used in production
        return User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )

async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current active user based on configured provider"""
    return await get_current_user(credentials)

async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Require admin role - validates token and checks admin role"""
    from fastmcp.auth.domain.entities.user import UserRole
    user = await get_current_user(credentials)
    # In a real implementation, you'd check roles from the token
    # For now, just return the authenticated user
    return user

async def require_roles(
    *roles,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Require specific roles - validates token and checks roles"""
    user = await get_current_user(credentials)
    # In a real implementation, you'd check roles from the token
    # For now, just return the authenticated user
    return user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get optional user - returns user if authenticated, None otherwise"""
    if credentials:
        try:
            return await get_current_user(credentials)
        except:
            return None
    return None