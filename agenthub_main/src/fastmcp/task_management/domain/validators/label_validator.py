"""Label Validator - Domain Layer Validation for Label Entities.

This module provides comprehensive validation for label data before database operations,
ensuring all business rules and constraints are met. Following DDD principles, this
validator operates at the domain layer and prevents invalid data from reaching the
infrastructure layer.

Key Validation Rules:
- Timestamp awareness (UTC timezone required)
- Label name format and constraints
- Color format validation (hex colors)
- Description length limits
- Business rule enforcement

NO LEGACY COMPATIBILITY - Clean validation implementation only.
"""

import re
from datetime import datetime, timezone, timezone
from typing import Optional, Tuple


class LabelValidationError(ValueError):
    """Custom exception for label validation errors with detailed context."""

    def __init__(self, field: str, message: str, hint: Optional[str] = None):
        """Initialize validation error with field context.

        Args:
            field: The field that failed validation
            message: Human-readable error message
            hint: Optional hint for fixing the error
        """
        self.field = field
        self.message = message
        self.hint = hint

        error_msg = f"Label validation error ({field}): {message}"
        if hint:
            error_msg += f"\nHint: {hint}"

        super().__init__(error_msg)


class LabelValidator:
    """Domain validator for Label entities following DDD principles.

    This validator enforces business rules and constraints at the domain layer,
    ensuring data integrity before it reaches the database. All validation
    methods return clear, actionable error messages to aid debugging.

    Validation Categories:
    1. Timestamp Validation - UTC awareness and consistency
    2. Name Validation - Format, length, and character constraints
    3. Color Validation - Hex color format validation
    4. Description Validation - Length and content constraints
    5. Complete Entity Validation - All rules applied together

    Usage:
        validator = LabelValidator()
        validator.validate_label_creation("backend", "#ff0000", "Backend tasks")
    """

    # Validation constraints (single source of truth)
    MAX_NAME_LENGTH = 50
    MIN_NAME_LENGTH = 1
    MAX_DESCRIPTION_LENGTH = 2000
    HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$')
    ALLOWED_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]+$')

    @staticmethod
    def validate_timestamp(
        timestamp: Optional[datetime],
        field_name: str = "timestamp"
    ) -> None:
        """Validate timestamp is not None and is timezone.utc-aware.

        Args:
            timestamp: The datetime to validate
            field_name: Name of the field being validated (for error messages)

        Raises:
            LabelValidationError: If timestamp is None or not UTC-aware

        Examples:
            >>> validator = LabelValidator()
            >>> validator.validate_timestamp(datetime.now(timezone.utc), "created_at")
            >>> validator.validate_timestamp(datetime.now(), "created_at")  # Raises error
            LabelValidationError: Label validation error (created_at): Timestamp must be timezone-aware
        """
        if timestamp is None:
            raise LabelValidationError(
                field=field_name,
                message=f"{field_name} cannot be None",
                hint="Use datetime.now(timezone.utc) to create UTC timestamps"
            )

        if timestamp.tzinfo is None:
            raise LabelValidationError(
                field=field_name,
                message="Timestamp must be timezone-aware",
                hint="Use datetime.now(timezone.utc) instead of datetime.now()"
            )

        if timestamp.tzinfo != timezone.utc:
            raise LabelValidationError(
                field=field_name,
                message="Timestamp must be in UTC timezone",
                hint=f"Convert to UTC using: {field_name}.astimezone(UTC)"
            )

    @classmethod
    def validate_name(cls, name: str) -> None:
        """Validate label name format and constraints.

        Business Rules:
        - Name cannot be empty or whitespace-only
        - Name length must be between MIN_NAME_LENGTH and MAX_NAME_LENGTH
        - Name can only contain alphanumeric characters, spaces, hyphens, and underscores

        Args:
            name: The label name to validate

        Raises:
            LabelValidationError: If name violates any validation rule

        Examples:
            >>> validator = LabelValidator()
            >>> validator.validate_name("backend")  # Valid
            >>> validator.validate_name("api-integration")  # Valid
            >>> validator.validate_name("frontend_ui")  # Valid
            >>> validator.validate_name("")  # Raises error
            >>> validator.validate_name("x" * 100)  # Raises error (too long)
        """
        if not name or not name.strip():
            raise LabelValidationError(
                field="name",
                message="Label name cannot be empty or whitespace",
                hint="Provide a meaningful label name (e.g., 'backend', 'frontend', 'api')"
            )

        if len(name) < cls.MIN_NAME_LENGTH:
            raise LabelValidationError(
                field="name",
                message=f"Label name must be at least {cls.MIN_NAME_LENGTH} character(s)",
                hint=f"Current length: {len(name)}"
            )

        if len(name) > cls.MAX_NAME_LENGTH:
            raise LabelValidationError(
                field="name",
                message=f"Label name cannot exceed {cls.MAX_NAME_LENGTH} characters",
                hint=f"Current length: {len(name)}. Consider abbreviating the name."
            )

        if not cls.ALLOWED_NAME_PATTERN.match(name):
            raise LabelValidationError(
                field="name",
                message="Label name contains invalid characters",
                hint="Only alphanumeric characters, spaces, hyphens (-), and underscores (_) are allowed"
            )

    @classmethod
    def validate_color(cls, color: Optional[str]) -> None:
        """Validate label color format (hex color).

        Business Rules:
        - Color must be a valid hex color format (#RGB or #RRGGBB)
        - Color is optional (None is allowed)

        Args:
            color: The hex color string to validate (e.g., "#ff0000" or "#f00")

        Raises:
            LabelValidationError: If color format is invalid

        Examples:
            >>> validator = LabelValidator()
            >>> validator.validate_color("#ff0000")  # Valid
            >>> validator.validate_color("#f00")  # Valid
            >>> validator.validate_color(None)  # Valid (optional)
            >>> validator.validate_color("red")  # Raises error
            >>> validator.validate_color("#gg0000")  # Raises error
        """
        if color is None:
            return  # Color is optional

        if not isinstance(color, str):
            raise LabelValidationError(
                field="color",
                message="Color must be a string",
                hint="Use hex color format (e.g., '#ff0000' or '#f00')"
            )

        if not color.startswith("#"):
            raise LabelValidationError(
                field="color",
                message="Color must start with '#'",
                hint=f"Did you mean '#{color}'? Use hex color format (e.g., '#ff0000')"
            )

        if not cls.HEX_COLOR_PATTERN.match(color):
            raise LabelValidationError(
                field="color",
                message=f"Invalid hex color format: {color}",
                hint="Use format #RGB (e.g., '#f00') or #RRGGBB (e.g., '#ff0000')"
            )

    @classmethod
    def validate_description(cls, description: Optional[str]) -> None:
        """Validate label description constraints.

        Business Rules:
        - Description is optional (None or empty string allowed)
        - Description length cannot exceed MAX_DESCRIPTION_LENGTH

        Args:
            description: The description text to validate

        Raises:
            LabelValidationError: If description violates length constraint

        Examples:
            >>> validator = LabelValidator()
            >>> validator.validate_description("Backend API tasks")  # Valid
            >>> validator.validate_description(None)  # Valid (optional)
            >>> validator.validate_description("")  # Valid (optional)
            >>> validator.validate_description("x" * 3000)  # Raises error
        """
        if description is None or description == "":
            return  # Description is optional

        if not isinstance(description, str):
            raise LabelValidationError(
                field="description",
                message="Description must be a string",
                hint="Provide a text description or leave empty"
            )

        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            raise LabelValidationError(
                field="description",
                message=f"Description cannot exceed {cls.MAX_DESCRIPTION_LENGTH} characters",
                hint=f"Current length: {len(description)}. Consider shortening the description."
            )

    @classmethod
    def validate_label_creation(
        cls,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate all requirements for label creation.

        This method performs comprehensive validation of all label fields
        required for creation. It's the main entry point for label validation.

        Args:
            name: Label name (required)
            color: Label color in hex format (optional)
            description: Label description (optional)
            created_at: Creation timestamp (optional, will be set if None)
            updated_at: Update timestamp (optional, will be set if None)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            - (True, None) if validation passes
            - (False, error_message) if validation fails

        Examples:
            >>> validator = LabelValidator()
            >>> success, error = validator.validate_label_creation(
            ...     name="backend",
            ...     color="#ff0000",
            ...     description="Backend tasks",
            ...     created_at=datetime.now(timezone.utc),
            ...     updated_at=datetime.now(timezone.utc)
            ... )
            >>> assert success is True
            >>> assert error is None
        """
        try:
            # Validate name (required)
            cls.validate_name(name)

            # Validate color (optional)
            if color is not None:
                cls.validate_color(color)

            # Validate description (optional)
            if description is not None:
                cls.validate_description(description)

            # Validate timestamps if provided
            if created_at is not None:
                cls.validate_timestamp(created_at, "created_at")

            if updated_at is not None:
                cls.validate_timestamp(updated_at, "updated_at")

            # Validate timestamp consistency if both provided
            if created_at is not None and updated_at is not None:
                if updated_at < created_at:
                    raise LabelValidationError(
                        field="updated_at",
                        message="updated_at cannot be earlier than created_at",
                        hint="Ensure updated_at >= created_at"
                    )

            return True, None

        except LabelValidationError as e:
            return False, str(e)

    @classmethod
    def validate_label_update(
        cls,
        name: Optional[str] = None,
        color: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate requirements for label update.

        Update validation is more permissive than creation validation since
        only the fields being updated need to be validated.

        Args:
            name: New label name (optional)
            color: New label color (optional)
            description: New label description (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])

        Examples:
            >>> validator = LabelValidator()
            >>> success, error = validator.validate_label_update(name="updated-name")
            >>> assert success is True
        """
        try:
            # Validate only fields that are being updated
            if name is not None:
                cls.validate_name(name)

            if color is not None:
                cls.validate_color(color)

            if description is not None:
                cls.validate_description(description)

            return True, None

        except LabelValidationError as e:
            return False, str(e)

    @staticmethod
    def validate_timestamps_consistency(
        created_at: datetime,
        updated_at: datetime
    ) -> None:
        """Validate that timestamps are consistent and logical.

        Business Rules:
        - Both timestamps must be timezone-aware
        - Both timestamps must be in UTC
        - updated_at must not be earlier than created_at

        Args:
            created_at: Creation timestamp
            updated_at: Update timestamp

        Raises:
            LabelValidationError: If timestamps are inconsistent

        Examples:
            >>> validator = LabelValidator()
            >>> created = datetime.now(timezone.utc)
            >>> updated = created + timedelta(seconds=1)
            >>> validator.validate_timestamps_consistency(created, updated)  # Valid
        """
        # Validate individual timestamps
        LabelValidator.validate_timestamp(created_at, "created_at")
        LabelValidator.validate_timestamp(updated_at, "updated_at")

        # Validate consistency
        if updated_at < created_at:
            raise LabelValidationError(
                field="updated_at",
                message="updated_at cannot be earlier than created_at",
                hint=f"created_at: {created_at.isoformat()}, updated_at: {updated_at.isoformat()}"
            )
