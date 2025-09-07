"""Authentication-related exceptions for DhafnckMCP.

This module defines exceptions for authentication requirements and validation,
enforcing that all operations must have proper user authentication with no
fallback to default_id.
"""

class AuthenticationError(Exception):
    """Base exception for authentication-related errors"""
    pass

class UserAuthenticationRequiredError(AuthenticationError):
    """Raised when an operation requires user authentication but none was provided.
    
    This exception replaces the previous pattern of falling back to default_id,
    ensuring that all operations have proper user context.
    """
    def __init__(self, operation: str = "This operation"):
        self.operation = operation
        super().__init__(f"{operation} requires user authentication. No user ID was provided.")

class InvalidUserIdError(AuthenticationError):
    """Raised when an invalid user ID is provided.
    
    This includes malformed UUIDs, empty strings, or any other invalid format.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"Invalid user ID provided: {user_id}. User authentication is required.")

class DefaultUserProhibitedError(AuthenticationError):
    """Raised when default_id usage is attempted but prohibited.
    
    This exception specifically catches attempts to use:
    - 'default_id'
    - '00000000-0000-0000-0000-000000000000'
    - 'default'
    - Any other form of default user identifier
    """
    def __init__(self):
        super().__init__(
            "Use of default user ID is prohibited. "
            "All operations must be performed with authenticated user credentials."
        )