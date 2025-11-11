"""
Response Factory for Agent MCP Controller

Provides centralized error response generation for agent operations.
"""

import logging
from typing import Any

from .....utils.response_formatter import (
    StandardResponseFormatter,
)

logger = logging.getLogger(__name__)


class AgentResponseFactory:
    """Factory for creating standardized agent operation responses."""

    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        logger.info("AgentResponseFactory initialized")

    def create_missing_field_error(self, field: str, action: str) -> dict[str, Any]:
        """Create standardized missing field error response.

        Args:
            field: The missing field name
            action: The action being performed

        Returns:
            Standardized error response for missing field
        """
        return {
            "success": False,
            "error": f"Missing required field: {field}",
            "error_code": "MISSING_FIELD",
            "field": field,
            "action": action,
            "expected": f"A valid {field} value",
            "hint": f"Include '{field}' in your request for action '{action}'",
        }

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
                "register",
                "assign",
                "get",
                "list",
                "update",
                "unassign",
                "unregister",
                "rebalance",
            ]

        return {
            "success": False,
            "error": "Invalid action",
            "error_code": "INVALID_ACTION",
            "field": "action",
            "expected": f"One of: {', '.join(valid_actions)}",
            "hint": f"Invalid action: {invalid_action}. Use one of the supported actions.",
        }
