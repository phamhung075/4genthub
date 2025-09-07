"""MCP Integration Module for Authentication"""

from .jwt_auth_backend import (
    JWTAuthBackend,
    MCPUserContext,
    create_jwt_auth_backend
)
# UserContextMiddleware has been replaced with RequestContextMiddleware
# Import from the new location for backward compatibility
try:
    from ..middleware.request_context_middleware import RequestContextMiddleware
    UserContextMiddleware = RequestContextMiddleware  # Alias for backward compatibility
except ImportError:
    RequestContextMiddleware = None  # type: ignore
    UserContextMiddleware = None  # type: ignore

from .repository_filter import UserFilteredRepository

__all__ = [
    "JWTAuthBackend",
    "MCPUserContext", 
    "create_jwt_auth_backend",
    "UserFilteredRepository"
]

# Only export middleware classes if they're available
if RequestContextMiddleware is not None:
    __all__.extend(["RequestContextMiddleware", "UserContextMiddleware"])