"""
Authentication Tools for Conditional Registration

This module contains all authentication-related MCP tools that can be
conditionally registered based on configuration.
"""

import logging
from typing import Dict, Any
from fastmcp.auth import AuthMiddleware, TokenValidationError, RateLimitError


logger = logging.getLogger(__name__)


class AuthenticationTools:
    """Container for authentication-related MCP tools."""

    def __init__(self, auth_middleware: AuthMiddleware):
        """
        Initialize authentication tools.

        Args:
            auth_middleware: Authentication middleware instance
        """
        self.auth_middleware = auth_middleware

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate an authentication token.

        Args:
            token: The authentication token to validate

        Returns:
            Token validation result with user information
        """
        try:
            token_info = await self.auth_middleware.authenticate_request(token)

            if not token_info:
                return {
                    "valid": True,
                    "message": "Authentication disabled or MVP mode",
                    "user_id": "mvp_user",
                    "auth_enabled": self.auth_middleware.enabled
                }

            return {
                "valid": True,
                "user_id": token_info.user_id,
                "created_at": token_info.created_at.isoformat(),
                "expires_at": token_info.expires_at.isoformat() if token_info.expires_at else None,
                "usage_count": token_info.usage_count,
                "last_used": token_info.last_used.isoformat() if token_info.last_used else None,
                "auth_enabled": self.auth_middleware.enabled
            }

        except TokenValidationError as e:
            return {
                "valid": False,
                "error": str(e),
                "error_type": "validation_error",
                "auth_enabled": self.auth_middleware.enabled
            }
        except RateLimitError as e:
            return {
                "valid": False,
                "error": str(e),
                "error_type": "rate_limit_error",
                "auth_enabled": self.auth_middleware.enabled
            }
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {
                "valid": False,
                "error": "Internal validation error",
                "error_type": "internal_error",
                "auth_enabled": self.auth_middleware.enabled
            }

    async def get_rate_limit_status(self, token: str) -> Dict[str, Any]:
        """
        Get rate limit status for a token.

        Args:
            token: The authentication token

        Returns:
            Current rate limit status
        """
        try:
            status = await self.auth_middleware.get_rate_limit_status(token)
            return {
                "success": True,
                "rate_limits": status
            }
        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def revoke_token(self, token: str) -> Dict[str, Any]:
        """
        Revoke an authentication token.

        Args:
            token: The token to revoke

        Returns:
            Revocation result
        """
        try:
            success = await self.auth_middleware.revoke_token(token)
            return {
                "success": success,
                "message": "Token revoked successfully" if success else "Failed to revoke token"
            }
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get authentication system status.

        Returns:
            Authentication system status and configuration
        """
        return self.auth_middleware.get_auth_status()

    def generate_token(self) -> Dict[str, Any]:
        """
        Generate a new secure authentication token.

        NOTE: Token generation is now handled through the API at /api/v2/tokens
        This MCP tool is deprecated and will return an informative message.

        Returns:
            Information about how to generate tokens
        """
        return {
            "success": False,
            "error": "Token generation via MCP tool is deprecated",
            "message": (
                "Please use the API endpoint POST /api/v2/tokens to generate tokens. "
                "This provides better security and integration with the authentication system."
            ),
            "api_endpoint": "/api/v2/tokens",
            "method": "POST",
            "example": {
                "name": "my-token",
                "expires_in_days": 30,
                "scopes": ["read", "write"]
            }
        }

    def get_tool_functions(self) -> Dict[str, callable]:
        """
        Get dictionary of tool functions for registration.

        Returns:
            Dictionary mapping tool names to their implementation functions
        """
        return {
            "validate_token": self.validate_token,
            "get_rate_limit_status": self.get_rate_limit_status,
            "revoke_token": self.revoke_token,
            "get_auth_status": self.get_auth_status,
            "generate_token": self.generate_token
        }


def create_authentication_tools(auth_middleware: AuthMiddleware) -> Dict[str, callable]:
    """
    Create authentication tools for conditional registration.

    Args:
        auth_middleware: Authentication middleware instance

    Returns:
        Dictionary mapping tool names to their implementation functions
    """
    auth_tools = AuthenticationTools(auth_middleware)
    return auth_tools.get_tool_functions()