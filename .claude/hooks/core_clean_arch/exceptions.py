"""
Custom exceptions for the hook system.
"""
from typing import Any


class HookException(Exception):
    """Base exception for hook system."""
    pass


class ValidationError(HookException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


class ConfigurationError(HookException):
    """Raised when configuration is invalid."""
    pass


class ProcessingError(HookException):
    """Raised when processing fails."""
    pass


class HintGenerationError(HookException):
    """Raised when hint generation fails."""
    pass


class MCPAuthenticationError(HookException):
    """Raised when MCP authentication fails."""
    pass