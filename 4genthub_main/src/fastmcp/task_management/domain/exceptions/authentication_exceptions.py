"""Authentication-related exceptions for 4genthub.

This module defines exceptions for authentication requirements and validation.
Authentication is handled by Keycloak.
"""

class AuthenticationError(Exception):
    """Base exception for authentication-related errors"""
    pass

class UserAuthenticationRequiredError(AuthenticationError):
    """Raised when an operation requires user authentication but none was provided.
    
    This exception ensures that all operations have proper user context.
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
    """Raised when a default user ID is used instead of proper authentication.
    
    This ensures that operations are performed with authenticated user credentials
    and prevents the use of default or system-generated user IDs.
    """
    def __init__(self):
        super().__init__(
            "Use of default user ID is prohibited. All operations must be performed "
            "with authenticated user credentials."
        )