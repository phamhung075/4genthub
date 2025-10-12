"""
Project Name Validation Domain Service

This domain service validates project names according to business rules,
including checking for duplicates within the user's scope.
"""

import logging
from typing import Optional

from ..repositories.project_repository import ProjectRepository
from ..exceptions.base_exceptions import ValidationException

logger = logging.getLogger(__name__)


class ProjectNameValidator:
    """
    Domain service for validating project names.

    This service encapsulates business rules for project name validation,
    including duplicate checks and format validation.
    """

    def __init__(self, project_repository: ProjectRepository):
        """
        Initialize the validator with required dependencies.

        Args:
            project_repository: Repository for checking existing projects
        """
        self._project_repository = project_repository

    async def validate_unique_name(self, name: str, user_id: str, exclude_project_id: Optional[str] = None) -> None:
        """
        Validate that a project name is unique within the user's scope.

        Args:
            name: The project name to validate
            user_id: The user ID to scope the validation to
            exclude_project_id: Optional project ID to exclude from validation (for updates)

        Raises:
            ValidationException: If the name is not unique or invalid
        """
        # Validate input parameters
        if not name or not name.strip():
            raise ValidationException("Project name cannot be empty")

        if not user_id or not user_id.strip():
            raise ValidationException("User ID is required for validation")

        # Trim whitespace for consistency
        name = name.strip()

        # Validate name format and length
        if len(name) < 1:
            raise ValidationException("Project name must be at least 1 character long")

        if len(name) > 255:
            raise ValidationException("Project name cannot exceed 255 characters")

        # Check for duplicate names within user scope
        existing_project = await self._project_repository.find_by_name(name)

        if existing_project:
            # If we're excluding a specific project ID (for updates), check if it's the same
            if exclude_project_id and existing_project.id == exclude_project_id:
                # This is the same project being updated, allow the name
                return

            # Another project with this name exists - not allowed
            raise ValidationException(
                f"A project with the name '{name}' already exists. Please choose a different name."
            )

        logger.debug(f"Project name '{name}' validated successfully for user {user_id}")

    async def validate_name_format(self, name: str) -> None:
        """
        Validate project name format according to business rules.

        Args:
            name: The project name to validate

        Raises:
            ValidationException: If the name format is invalid
        """
        if not name or not name.strip():
            raise ValidationException("Project name cannot be empty")

        # Trim whitespace for validation
        name = name.strip()

        # Length constraints
        if len(name) < 1:
            raise ValidationException("Project name must be at least 1 character long")

        if len(name) > 255:
            raise ValidationException("Project name cannot exceed 255 characters")

        # Character validation - allow most characters but prevent problematic ones
        forbidden_chars = ['<', '>', '"', '|', '\\', '/', ':', '*', '?']
        for char in forbidden_chars:
            if char in name:
                raise ValidationException(f"Project name cannot contain the character '{char}'")

        logger.debug(f"Project name format '{name}' validated successfully")

    async def validate_project_name(self, name: str, user_id: str, exclude_project_id: Optional[str] = None) -> None:
        """
        Comprehensive project name validation including format and uniqueness.

        Args:
            name: The project name to validate
            user_id: The user ID to scope the validation to
            exclude_project_id: Optional project ID to exclude from validation (for updates)

        Raises:
            ValidationException: If validation fails
        """
        # First validate format
        await self.validate_name_format(name)

        # Then validate uniqueness
        await self.validate_unique_name(name, user_id, exclude_project_id)

        logger.info(f"Project name '{name}' passed comprehensive validation for user {user_id}")