"""Authentication configuration for DhafnckMCP.

This module provides configuration options for authentication behavior.
All operations require proper user authentication - no fallbacks allowed.
"""

import os
import logging
from typing import Optional
from ..task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError
)

logger = logging.getLogger(__name__)

class AuthConfig:
    """Authentication configuration for DhafnckMCP.
    
    This class enforces strict authentication requirements.
    All operations must have valid user authentication - no fallbacks or compatibility modes.
    """
    
    @staticmethod
    def should_enforce_authentication() -> bool:
        """
        Check if authentication should be strictly enforced.
        
        Always returns True - authentication is always required.
        
        Returns:
            True - authentication is always enforced
        """
        return True
    
    @staticmethod
    def validate_security_requirements() -> dict:
        """
        Validate that all security requirements are met.
        
        Returns:
            Dict with security status and configuration
        """
        env = os.getenv('ENVIRONMENT', '').lower()
        
        # Check for any legacy configuration that might bypass authentication
        legacy_config_issues = []
        
        # Check for old environment variables that might bypass security
        if os.getenv('ALLOW_DEFAULT_USER', '').lower() in ('true', '1', 'yes', 'on'):
            legacy_config_issues.append("ALLOW_DEFAULT_USER environment variable is set")
        
        return {
            'authentication_required': True,
            'legacy_config_issues': legacy_config_issues,
            'environment': env or 'unknown',
            'secure': len(legacy_config_issues) == 0
        }