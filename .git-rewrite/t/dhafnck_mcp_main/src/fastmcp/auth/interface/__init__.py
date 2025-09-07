"""Authentication Interface Layer"""

from .auth_endpoints import router as auth_router

# Import OAuth2PasswordBearer dependencies from fastapi_auth
from .fastapi_auth import (
    get_current_user,
    get_current_active_user,
    require_roles,
    require_admin,
    get_optional_user
)

# Import legacy utility functions (DEPRECATED - for backward compatibility only)
from .auth_middleware import (
    get_current_user_id,
    get_current_user_email,
    get_current_user_roles,
    is_authenticated,
    has_role,
    is_admin
)

__all__ = [
    "auth_router",
    # OAuth2PasswordBearer dependencies (recommended)
    "get_current_user",
    "get_current_active_user",
    "require_roles",
    "require_admin",
    "get_optional_user",
    # Legacy functions (deprecated)
    "get_current_user_id",
    "get_current_user_email", 
    "get_current_user_roles",
    "is_authenticated",
    "has_role",
    "is_admin"
]

# Note: AuthenticationMiddleware and require_auth have been removed.
# Use OAuth2PasswordBearer dependencies from fastapi_auth instead.