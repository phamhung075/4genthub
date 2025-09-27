"""Authentication middleware package."""
from .jwt_auth_middleware import JWTAuthMiddleware, UserContextManager
from .dual_auth_middleware import DualAuthMiddleware, create_dual_auth_middleware
from .request_context_middleware import (
    RequestContextMiddleware, 
    create_request_context_middleware,
    get_current_user_id,
    get_current_user_email,
    get_current_auth_method,
    is_request_authenticated,
    get_authentication_context
)

__all__ = [
    "JWTAuthMiddleware", 
    "UserContextManager",
    "DualAuthMiddleware",
    "create_dual_auth_middleware",
    "RequestContextMiddleware",
    "create_request_context_middleware",
    "get_current_user_id",
    "get_current_user_email", 
    "get_current_auth_method",
    "is_request_authenticated",
    "get_authentication_context"
]