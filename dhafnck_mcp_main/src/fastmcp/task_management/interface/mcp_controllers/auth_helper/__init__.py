"""Authentication Helper Module

Clean authentication module for MCP controllers.
Only token-based authentication, no legacy code.
"""

from .auth_helper import (
    get_authenticated_user_id,
    log_authentication_details
)

__all__ = [
    'get_authenticated_user_id',
    'log_authentication_details'
]