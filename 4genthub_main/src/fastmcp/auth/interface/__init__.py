"""Authentication Interface Layer"""

# Import OAuth2PasswordBearer dependencies from fastapi_auth
# These work with both Keycloak and Supabase based on AUTH_PROVIDER env var
from .fastapi_auth import (
    get_current_user,
    get_current_active_user,
    require_roles,
    require_admin,
    get_optional_user,
    get_db
)


__all__ = [
    # OAuth2PasswordBearer dependencies (recommended)
    "get_current_user",
    "get_current_active_user",
    "require_roles",
    "require_admin",
    "get_optional_user",
    "get_db",
]

# Note: unified_auth_endpoints and auth_endpoints have been removed.
# Authentication is handled through middleware and fastapi_auth.py
# which automatically selects Keycloak or Supabase based on AUTH_PROVIDER.