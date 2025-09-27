"""
Task Management Utils Module

This module provides commonly used utilities for the task management system.
It acts as a centralized location for shared functionality and re-exports
utilities from the interface layer for easier access.
"""

# Re-export commonly used utilities from interface.utils
from ..interface.utils.response_formatter import (
    StandardResponseFormatter, 
    ResponseStatus, 
    ErrorCodes
)
from ..interface.utils.error_handler import UserFriendlyErrorHandler
from ..interface.utils.json_parameter_parser import JSONParameterParser
from ..interface.utils.mcp_parameter_validator import MCPParameterValidator

# Database utilities
from ..infrastructure.database.uuid_column_type import (
    UnifiedUUID,
    create_uuid_column, 
    generate_uuid_string
)

# Export for easier importing
__all__ = [
    'StandardResponseFormatter',
    'ResponseStatus', 
    'ErrorCodes',
    'UserFriendlyErrorHandler',
    'JSONParameterParser',
    'MCPParameterValidator',
    'UnifiedUUID',
    'create_uuid_column',
    'generate_uuid_string'
]