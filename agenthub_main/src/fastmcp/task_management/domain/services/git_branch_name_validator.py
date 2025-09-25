"""
Git Branch Name Validation Domain Service

This domain service validates git branch names according to business rules,
including checking for duplicates within the project's scope.
"""

import logging
from typing import Optional

from ..repositories.git_branch_repository import GitBranchRepository
from ..exceptions.base_exceptions import ValidationException

logger = logging.getLogger(__name__)


class GitBranchNameValidator:
    """
    Domain service for validating git branch names.

    This service encapsulates business rules for git branch name validation,
    including duplicate checks and format validation.
    """

    def __init__(self, git_branch_repository: GitBranchRepository):
        """
        Initialize the validator with required dependencies.

        Args:
            git_branch_repository: Repository for checking existing branches
        """
        self._git_branch_repository = git_branch_repository

    async def validate_unique_name(self, name: str, project_id: str, exclude_branch_id: Optional[str] = None) -> None:
        """
        Validate that a git branch name is unique within the project's scope.

        Args:
            name: The branch name to validate
            project_id: The project ID to scope the validation to
            exclude_branch_id: Optional branch ID to exclude from validation (for updates)

        Raises:
            ValidationException: If the name is not unique or invalid
        """
        # Validate input parameters
        if not name or not name.strip():
            raise ValidationException("Branch name cannot be empty")

        if not project_id or not project_id.strip():
            raise ValidationException("Project ID is required for validation")

        # Trim whitespace for consistency
        name = name.strip()

        # Validate name format and length
        if len(name) < 1:
            raise ValidationException("Branch name must be at least 1 character long")

        if len(name) > 100:
            raise ValidationException("Branch name cannot exceed 100 characters")

        # Check for duplicate names within project scope
        existing_branches = await self._git_branch_repository.find_all_by_project(project_id)

        if existing_branches:
            for branch in existing_branches:
                if branch.name == name:
                    # If we're excluding a specific branch ID (for updates), check if it's the same
                    if exclude_branch_id and branch.id == exclude_branch_id:
                        # This is the same branch being updated, allow the name
                        continue

                    # Another branch with this name exists - not allowed
                    raise ValidationException(
                        f"A branch with the name '{name}' already exists in this project. Please choose a different name."
                    )

        logger.debug(f"Branch name '{name}' validated successfully for project {project_id}")

    async def validate_name_format(self, name: str) -> None:
        """
        Validate git branch name format according to business rules and git conventions.

        Args:
            name: The branch name to validate

        Raises:
            ValidationException: If the name format is invalid
        """
        if not name or not name.strip():
            raise ValidationException("Branch name cannot be empty")

        # Trim whitespace for validation
        name = name.strip()

        # Length constraints
        if len(name) < 1:
            raise ValidationException("Branch name must be at least 1 character long")

        if len(name) > 100:
            raise ValidationException("Branch name cannot exceed 100 characters")

        # Git branch name rules (simplified version of git's rules)
        forbidden_chars = [' ', '~', '^', ':', '\\', '*', '?', '[', '.', '@{']
        for char in forbidden_chars:
            if char in name:
                if char == ' ':
                    raise ValidationException("Branch name cannot contain spaces. Use hyphens or underscores instead.")
                else:
                    raise ValidationException(f"Branch name cannot contain the character '{char}'")

        # Cannot start with slash, dot, or hyphen
        if name.startswith('/') or name.startswith('.') or name.startswith('-'):
            raise ValidationException("Branch name cannot start with '/', '.', or '-'")

        # Cannot end with slash or dot
        if name.endswith('/') or name.endswith('.'):
            raise ValidationException("Branch name cannot end with '/' or '.'")

        # Cannot contain consecutive dots
        if '..' in name:
            raise ValidationException("Branch name cannot contain consecutive dots (..)")

        # Cannot contain slash at beginning or end
        if name.startswith('/') or name.endswith('/'):
            raise ValidationException("Branch name cannot start or end with '/'")

        logger.debug(f"Branch name format '{name}' validated successfully")

    async def validate_branch_name(self, name: str, project_id: str, exclude_branch_id: Optional[str] = None) -> None:
        """
        Comprehensive git branch name validation including format and uniqueness.

        Args:
            name: The branch name to validate
            project_id: The project ID to scope the validation to
            exclude_branch_id: Optional branch ID to exclude from validation (for updates)

        Raises:
            ValidationException: If validation fails
        """
        # First validate format
        await self.validate_name_format(name)

        # Then validate uniqueness
        await self.validate_unique_name(name, project_id, exclude_branch_id)

        logger.info(f"Branch name '{name}' passed comprehensive validation for project {project_id}")