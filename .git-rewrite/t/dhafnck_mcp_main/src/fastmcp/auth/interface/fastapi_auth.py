"""
Minimal FastAPI auth interface for compatibility
This file provides minimal functions for import compatibility only.
"""

from typing import Optional, Generator
from sqlalchemy.orm import Session
from fastmcp.auth.domain.entities.user import User
from fastmcp.task_management.infrastructure.database.database_config import get_session

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    session = get_session()
    try:
        yield session
    finally:
        session.close()

def get_current_user() -> User:
    """Get current authenticated user - stub for compatibility"""
    # Return a default user for compatibility
    # Real authentication happens in middleware
    return User(
        id="default-user",
        email="user@example.com",
        username="user",
        password_hash="stub-password-hash"
    )

def get_current_active_user() -> User:
    """Get current active user - stub for compatibility"""
    return get_current_user()

def require_admin() -> User:
    """Require admin role - stub for compatibility"""
    # Return a default admin user for compatibility
    # Real authorization happens in middleware
    from fastmcp.auth.domain.entities.user import UserRole
    user = get_current_user()
    user.role = UserRole.ADMIN
    return user

def require_roles(*roles) -> User:
    """Require specific roles - stub for compatibility"""
    # Return user with first requested role for compatibility
    # Real authorization happens in middleware
    from fastmcp.auth.domain.entities.user import UserRole
    user = get_current_user()
    if roles:
        # Set the first role from the requested roles
        user.role = roles[0] if isinstance(roles[0], UserRole) else UserRole.USER
    return user

def get_optional_user() -> Optional[User]:
    """Get optional user - stub for compatibility"""
    # Return None for anonymous requests
    # Real authentication happens in middleware
    try:
        return get_current_user()
    except:
        return None