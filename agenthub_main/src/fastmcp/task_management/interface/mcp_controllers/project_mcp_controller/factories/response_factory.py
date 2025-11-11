"""
Response Factory for Project MCP Controller

Provides centralized error response generation for project operations.
"""

import logging
from typing import Any

from .....utils.response_formatter import (
    ErrorCodes,
    StandardResponseFormatter,
)

logger = logging.getLogger(__name__)


class ProjectResponseFactory:
    """Factory for creating standardized project operation responses."""

    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        logger.info("ProjectResponseFactory initialized")

    def create_missing_field_error(self, field: str, action: str) -> dict[str, Any]:
        """Create standardized missing field error response.

        Args:
            field: The missing field name
            action: The action being performed

        Returns:
            Standardized error response for missing field
        """
        return self._response_formatter.create_error_response(
            operation=action,
            error=f"Missing required field: {field}. Expected: A valid {field} string",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={
                "field": field,
                "hint": f"Include '{field}' in your request",
                "action": action,
            },
        )

    def create_invalid_action_error(
        self, invalid_action: str, valid_actions: list[str] | None = None
    ) -> dict[str, Any]:
        """Create standardized invalid action error response.

        Args:
            invalid_action: The invalid action provided
            valid_actions: Optional list of valid actions (uses default if not provided)

        Returns:
            Standardized error response for invalid action
        """
        if valid_actions is None:
            valid_actions = [
                "create",
                "get",
                "list",
                "update",
                "delete",
                "project_health_check",
                "cleanup_obsolete",
                "validate_integrity",
                "rebalance_agents",
            ]

        return self._response_formatter.create_error_response(
            operation="unknown_action",
            error="Invalid action",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={
                "field": "action",
                "expected": f"One of: {', '.join(valid_actions)}",
                "hint": f"Invalid action: {invalid_action}. Use one of the supported actions.",
            },
        )
