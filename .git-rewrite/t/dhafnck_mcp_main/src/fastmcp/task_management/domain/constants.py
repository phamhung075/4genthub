"""Domain Constants for Task Management

This module defines domain-level constants and validation functions for the task management system.

CRITICAL CHANGE: This module no longer supports default_id. All operations must provide
proper user authentication. The previous DEFAULT_USER_UUID and related functions have been
permanently removed to enforce authentication requirements.
"""

from typing import Optional
from .exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError,
    InvalidUserIdError
)

# List of prohibited default user identifiers that should never be used
PROHIBITED_DEFAULT_IDS = {
    'default_id',
    '00000000-0000-0000-0000-000000000000',
    'default',
    'default_user',
    'system',
    'anonymous',
    'unauthenticated'
}

def validate_user_id(user_id: Optional[str], operation: str = "This operation") -> str:
    """
    Validate that a user ID is provided and valid.
    
    This function enforces authentication requirements by ensuring:
    1. A user ID is provided (not None or empty)
    2. The user ID is not a prohibited default value
    3. The user ID is a valid non-empty string
    
    Args:
        user_id: The user ID to validate
        operation: Description of the operation requiring authentication
        
    Returns:
        The validated user ID
        
    Raises:
        UserAuthenticationRequiredError: If user_id is None or empty
        DefaultUserProhibitedError: If user_id is a prohibited default value
        InvalidUserIdError: If user_id is invalid format
    """
    # Check if user_id is provided
    if user_id is None:
        raise UserAuthenticationRequiredError(operation)
    
    # Convert to string and strip whitespace
    user_id_str = str(user_id).strip()
    
    # Check if empty after stripping
    if not user_id_str:
        raise UserAuthenticationRequiredError(operation)
    
    # Check for prohibited default IDs (case-insensitive)
    if user_id_str.lower() in PROHIBITED_DEFAULT_IDS:
        raise DefaultUserProhibitedError()
    
    # Additional validation for UUID format if it looks like a UUID
    if len(user_id_str) == 36 and user_id_str.count('-') == 4:
        # Check if it's the zero UUID
        if user_id_str == '00000000-0000-0000-0000-000000000000':
            raise DefaultUserProhibitedError()
    
    return user_id_str

def require_authenticated_user(user_id: Optional[str], operation: str = "This operation") -> str:
    """
    Alias for validate_user_id for clearer intent in code.
    
    Use this when you want to explicitly show that authentication is required.
    
    Args:
        user_id: The user ID to validate
        operation: Description of the operation requiring authentication
        
    Returns:
        The validated user ID
        
    Raises:
        UserAuthenticationRequiredError: If user_id is None or empty
        DefaultUserProhibitedError: If user_id is a prohibited default value
        InvalidUserIdError: If user_id is invalid format
    """
    return validate_user_id(user_id, operation)

# REMOVED FUNCTIONS (for documentation purposes):
# - get_default_user_id(): No longer supported - authentication is required
# - is_default_user(): No longer needed - default users are prohibited
# - normalize_user_id(): No longer needed - no normalization to defaults
# - DEFAULT_USER_UUID: Removed - no default user concept
# - DEFAULT_USER_UUID_STR: Removed - no default user concept
# - LEGACY_DEFAULT_USER_ID: Removed - no legacy support for defaults