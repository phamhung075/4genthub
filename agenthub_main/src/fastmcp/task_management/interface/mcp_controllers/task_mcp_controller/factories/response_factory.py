"""
Response Factory for Task MCP Controller

Coordinates response formatting and enrichment for task operations.
"""

from __future__ import annotations

import logging
from typing import Any

from ....utils.response_formatter import (
    ErrorCodes,
    StandardResponseFormatter,
)

logger = logging.getLogger(__name__)


class ResponseFactory:
    """Factory for creating and formatting task operation responses."""

    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        logger.info("ResponseFactory initialized")

    def create_success_response(
        self,
        operation: str,
        data: dict[str, Any],
        workflow_guidance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create standardized success response."""
        return self._response_formatter.create_success_response(
            operation=operation, data=data, workflow_guidance=workflow_guidance
        )

    def create_error_response(
        self,
        operation: str,
        error: str,
        error_code: str = ErrorCodes.OPERATION_FAILED,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create standardized error response."""
        return self._response_formatter.create_error_response(
            operation=operation, error=error, error_code=error_code, metadata=metadata
        )

    def standardize_facade_response(
        self, facade_response: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """
        Convert facade response to standardized format.

        Args:
            facade_response: Response from facade method
            operation: Operation name for tracking

        Returns:
            Standardized response using StandardResponseFormatter
        """
        if facade_response.get("success", False):
            # Extract data from facade response
            data = {}
            for key, value in facade_response.items():
                if key not in ["success", "action", "error", "error_code"]:
                    data[key] = value

            # Extract workflow guidance if present
            workflow_guidance = None
            if "workflow_guidance" in data:
                workflow_guidance = data.pop("workflow_guidance")

            return self.create_success_response(
                operation=operation, data=data, workflow_guidance=workflow_guidance
            )
        else:
            # Handle error response
            error_message = facade_response.get("error", "Unknown error occurred")
            error_code = facade_response.get("error_code", ErrorCodes.OPERATION_FAILED)

            # Extract metadata
            metadata = {}
            for key, value in facade_response.items():
                if key not in ["success", "action", "error", "error_code"]:
                    metadata[key] = value

            return self.create_error_response(
                operation=operation,
                error=error_message,
                error_code=error_code,
                metadata=metadata if metadata else None,
            )

    def enrich_response_with_metadata(
        self, response: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Add metadata to existing response."""
        enriched_response = response.copy()

        if "metadata" in enriched_response:
            enriched_response["metadata"].update(metadata)
        else:
            enriched_response["metadata"] = metadata

        return enriched_response

    def add_pagination_metadata(
        self, response: dict[str, Any], total: int, limit: int, offset: int
    ) -> dict[str, Any]:
        """Add pagination metadata to list responses."""
        pagination_metadata = {
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": total > (offset + limit),
            }
        }

        return self.enrich_response_with_metadata(response, pagination_metadata)

    def add_operation_metadata(
        self, response: dict[str, Any], operation: str, timestamp: str | None = None
    ) -> dict[str, Any]:
        """Add operation metadata to response."""
        operation_metadata = {
            "operation_info": {
                "operation": operation,
                "timestamp": timestamp or self._response_formatter._get_timestamp(),
            }
        }

        return self.enrich_response_with_metadata(response, operation_metadata)

    def create_validation_error_response(
        self, field: str, expected: str, hint: str, operation: str = "validation"
    ) -> dict[str, Any]:
        """Create standardized validation error response."""
        return self.create_error_response(
            operation=operation,
            error=f"Invalid field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint},
        )

    def create_business_rule_error_response(
        self,
        rule_name: str,
        message: str,
        hint: str,
        operation: str = "business_validation",
    ) -> dict[str, Any]:
        """Create standardized business rule error response."""
        return self.create_error_response(
            operation=operation,
            error=f"Business rule violation ({rule_name}): {message}",
            error_code=ErrorCodes.BUSINESS_RULE_VIOLATION,
            metadata={"rule": rule_name, "hint": hint},
        )

    def create_missing_field_error(self, field: str, action: str) -> dict[str, Any]:
        """Create standardized missing field error response.

        Args:
            field: The missing field name
            action: The action being performed

        Returns:
            Standardized error response for missing field
        """
        return {
            "status": "failure",
            "error": {
                "message": f"Validation failed for field: {field}",
                "code": "VALIDATION_ERROR",
            },
            "operation": action,
            "metadata": {
                "validation_details": {
                    "field": field,
                    "expected": f"A valid {field} value",
                    "hint": f"Include '{field}' in your request for action '{action}'",
                }
            },
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
                "create",
                "update",
                "get",
                "delete",
                "complete",
                "list",
                "search",
                "next",
                "add_dependency",
                "remove_dependency",
                "ai_plan",
                "ai_create",
                "ai_enhance",
                "ai_analyze",
                "ai_suggest_agents",
            ]

        return {
            "status": "failure",
            "error": {
                "message": "Validation failed for field: action",
                "code": "VALIDATION_ERROR",
            },
            "operation": "unknown_action",
            "metadata": {
                "validation_details": {
                    "field": "action",
                    "expected": f"One of: {', '.join(valid_actions)}",
                    "hint": f"Invalid action: {invalid_action}. Use one of the supported actions.",
                }
            },
        }
