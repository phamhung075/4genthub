"""Domain Constants for Task Management

This module defines domain-level constants and validation functions for the task management system.

Authentication is required for all operations. The system uses Keycloak for authentication.

ENHANCED: Now includes UUID normalization for flexible user ID handling while maintaining
the ORM model as the source of truth.
"""

from typing import Optional

def validate_user_id(user_id: Optional[str], operation: str = "This operation") -> str:
    """
    Validate and normalize user ID to UUID format.
    
    ENHANCED: Now normalizes user IDs to UUID format for database compatibility
    while accepting flexible input formats like 'test-user-123'.
    
    Ensures that a user ID is provided (not None or empty) and converts it to
    a valid UUID format using deterministic conversion if needed.
    Authentication and authorization are handled by Keycloak.
    
    Args:
        user_id: The user ID to validate (can be UUID format or any string)
        operation: Description of the operation requiring authentication
        
    Returns:
        The validated and normalized user ID in UUID format
        
    Raises:
        ValueError: If user_id is None or empty
    """
    # Check if user_id is provided
    if user_id is None:
        raise ValueError(f"{operation} requires user authentication. No user ID was provided.")
    
    # Convert to string and strip whitespace
    user_id_str = str(user_id).strip()
    
    # Check if empty after stripping
    if not user_id_str:
        raise ValueError(f"{operation} requires user authentication. No user ID was provided.")
    
    # Normalize to UUID format using the same logic as UnifiedUUID
    try:
        from ..infrastructure.database.uuid_column_type import normalize_user_id_to_uuid
        normalized_user_id = normalize_user_id_to_uuid(user_id_str)
        return normalized_user_id
    except Exception as e:
        # Fallback to original string if UUID normalization fails
        import logging
        logging.warning(f"UUID normalization failed for user_id '{user_id_str}': {e}. Using original value.")
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
        ValueError: If user_id is None or empty
    """
    return validate_user_id(user_id, operation)

# Authentication is required for all operations
# Keycloak handles authentication and authorization