"""Authentication Helper for MCP Controllers

This module provides authentication functionality for MCP controllers
to extract user_id from JWT tokens. No legacy code, no hardcoded IDs.
"""

import logging
from typing import Optional

from .services.authentication_service import AuthenticationService

logger = logging.getLogger(__name__)

# Create singleton instance
_auth_service = None

def _get_auth_service():
    """Get or create authentication service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthenticationService()
    return _auth_service

def get_authenticated_user_id(provided_user_id: Optional[str] = None, operation_name: str = "Operation") -> str:
    """
    Get authenticated user ID from JWT token or provided parameter.
    
    This function extracts user_id from:
    1. Provided user_id parameter (if given)
    2. JWT token from Authorization header
    
    NO hardcoded IDs, NO legacy fallbacks.
    
    Args:
        provided_user_id: User ID provided explicitly (optional)
        operation_name: Name of the operation for error messages
        
    Returns:
        Validated user ID string
        
    Raises:
        UserAuthenticationRequiredError: If no valid authentication is found
    """
    return _get_auth_service().get_authenticated_user_id(provided_user_id, operation_name)

def log_authentication_details(user_id=None, operation=None):
    """
    Log current authentication state for debugging purposes.
    
    Args:
        user_id: Optional user ID for context
        operation: Optional operation name for context
    """
    if user_id:
        logger.info(f"🔐 Authenticated user: {user_id} for operation: {operation}")
    else:
        logger.warning(f"⚠️ No authentication for operation: {operation}")