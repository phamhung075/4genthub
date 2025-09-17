"""Authentication Integration Module"""

from .server_integration import (
    setup_authentication,
    get_auth_routes,
    get_auth_middleware,
    create_auth_app
)

__all__ = [
    "setup_authentication",
    "get_auth_routes",
    "get_auth_middleware",
    "create_auth_app"
]