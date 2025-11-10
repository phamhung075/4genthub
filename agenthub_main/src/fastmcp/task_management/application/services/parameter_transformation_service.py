"""
Parameter Transformation Service

This service handles all parameter transformations that were previously in MCP controllers.
Following DDD principles, this business logic belongs in the application layer, not the interface layer.

Responsibilities:
- String-to-list conversions (assignees, labels, dependencies)
- Integer type coercion with default values
- Progress percentage transformation (delegates validation to domain ProgressPercentage value object)
- Boolean default handling
"""

from __future__ import annotations

import logging
from typing import Any

from ...domain.value_objects import ProgressPercentage

logger = logging.getLogger(__name__)


class ParameterTransformationService:
    """Service for transforming and validating MCP controller parameters."""

    @staticmethod
    def transform_string_to_list(
        value: str | list | None, field_name: str = "parameter"
    ) -> list | None:
        """
        Transform string parameter to list, handling comma-separated values.

        Supports three input formats:
        1. None - returns None
        2. List - returns as-is
        3. String - splits by comma or returns single-element list

        Args:
            value: The value to transform (str, list, or None)
            field_name: Name of the field for logging purposes

        Returns:
            List of strings or None
        """
        if value is None:
            return None

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            # Check for comma-separated values
            if "," in value:
                # Split by comma and strip whitespace
                result = [item.strip() for item in value.split(",") if item.strip()]
                logger.debug(f"Transformed {field_name} from CSV to list: {result}")
                return result
            else:
                # Single value - convert to list
                result = [value]
                logger.debug(
                    f"Transformed {field_name} from single value to list: {result}"
                )
                return result

        logger.warning(
            f"Unexpected type for {field_name}: {type(value)}. Returning None."
        )
        return None

    @staticmethod
    def transform_to_integer(
        value: Any, default: int, field_name: str = "parameter"
    ) -> int:
        """
        Transform value to integer with fallback to default.

        Args:
            value: The value to transform
            default: Default value if transformation fails
            field_name: Name of the field for logging purposes

        Returns:
            Integer value or default
        """
        if value is None:
            return default

        if isinstance(value, int):
            return value

        try:
            result = int(value)
            logger.debug(f"Transformed {field_name} to integer: {result}")
            return result
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Failed to convert {field_name}={value} to integer: {e}. Using default={default}"
            )
            return default

    @staticmethod
    def validate_progress_percentage(value: Any) -> tuple[int | None, str | None]:
        """
        Validate and transform progress percentage (0-100 range).

        This method now delegates validation to the domain ProgressPercentage value object,
        following DDD principles where business rules belong in the domain layer.

        Args:
            value: The value to validate and transform

        Returns:
            Tuple of (transformed_value, error_message)
            - If valid: (int_value, None)
            - If invalid: (None, error_message)
        """
        if value is None:
            return None, None

        try:
            # Delegate validation to domain value object
            progress = ProgressPercentage.from_any(value)
            logger.debug(f"Validated progress_percentage: {progress.to_int()}")
            return progress.to_int(), None
        except (ValueError, TypeError) as e:
            error_msg = f"progress_percentage must be an integer between 0 and 100: {str(e)}"
            logger.warning(f"Invalid progress_percentage: {value} - {error_msg}")
            return None, error_msg

    @staticmethod
    def transform_boolean_default(value: bool | None, default: bool) -> bool:
        """
        Handle boolean parameters with default values.

        Args:
            value: The boolean value or None
            default: Default value if None

        Returns:
            Boolean value or default
        """
        if value is None:
            logger.debug(f"Boolean parameter is None, using default: {default}")
            return default
        return value

    @staticmethod
    def transform_multiple_fields(
        kwargs: dict[str, Any], field_configs: dict[str, dict]
    ) -> dict[str, Any]:
        """
        Transform multiple fields at once based on configuration.

        Args:
            kwargs: Dictionary of parameters to transform
            field_configs: Configuration for each field
                Format: {
                    'field_name': {
                        'type': 'list'|'integer'|'percentage'|'boolean',
                        'default': value (for integer/boolean),
                    }
                }

        Returns:
            Transformed kwargs dictionary
        """
        result = kwargs.copy()

        for field_name, config in field_configs.items():
            if field_name not in result:
                continue

            field_type = config.get("type")
            field_value = result[field_name]

            if field_type == "list":
                result[field_name] = ParameterTransformationService.transform_string_to_list(
                    field_value, field_name
                )
            elif field_type == "integer":
                default = config.get("default", 0)
                result[field_name] = ParameterTransformationService.transform_to_integer(
                    field_value, default, field_name
                )
            elif field_type == "percentage":
                transformed, error = (
                    ParameterTransformationService.validate_progress_percentage(
                        field_value
                    )
                )
                if error:
                    # Return error information
                    result[field_name] = None
                    result[f"{field_name}_error"] = error
                else:
                    result[field_name] = transformed
            elif field_type == "boolean":
                default = config.get("default", False)
                result[field_name] = ParameterTransformationService.transform_boolean_default(
                    field_value, default
                )

        return result
