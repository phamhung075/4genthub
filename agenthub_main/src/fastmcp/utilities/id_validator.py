"""ID Validation Domain Service - Prevents MCP UUID vs Application ID Confusion

This domain service provides comprehensive validation for different types of IDs
used throughout the agenthub system, preventing the critical data integrity issues
where MCP task IDs are incorrectly stored as application task IDs.

Based on: ai_docs/troubleshooting-guides/subtask-wrong-task-id-api-calls.md
"""

import re
import logging
import html
from typing import Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IDType(Enum):
    """Enumeration of different ID types in the system."""

    UUID = "uuid"
    MCP_TASK_ID = "mcp_task_id"
    APPLICATION_TASK_ID = "application_task_id"
    GIT_BRANCH_ID = "git_branch_id"
    PROJECT_ID = "project_id"
    USER_ID = "user_id"
    CONTEXT_ID = "context_id"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Result of ID validation containing validation status and metadata."""

    is_valid: bool
    id_type: IDType
    original_value: str
    normalized_value: Optional[str] = None
    error_message: Optional[str] = None
    warnings: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None


class IDValidationError(Exception):
    """Exception raised when ID validation fails critically."""

    def __init__(self, message: str, id_value: str, expected_type: Optional[IDType] = None):
        self.id_value = id_value
        self.expected_type = expected_type
        super().__init__(message)


class IDValidator:
    """
    Domain service that validates ID formats and prevents ID type confusion.

    This service centralizes ID validation logic to prevent critical issues like:
    - MCP task IDs being stored as application task IDs
    - Invalid UUID formats causing database constraint violations
    - Parameter confusion between different ID types

    Key Features:
    - UUID format validation with strict regex
    - ID type detection and classification
    - Clear error messages for debugging
    - Prevention of parameter confusion
    - Support for different ID naming conventions
    """

    # UUID v4 format regex (strict validation)
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    # Relaxed UUID pattern for backwards compatibility
    UUID_RELAXED_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    def __init__(self, strict_uuid_validation: bool = True):
        """
        Initialize the ID validator.

        Args:
            strict_uuid_validation: If True, enforces UUID v4 format.
                                  If False, allows any valid UUID format.
        """
        self.strict_uuid_validation = strict_uuid_validation
        self._uuid_pattern = self.UUID_PATTERN if strict_uuid_validation else self.UUID_RELAXED_PATTERN

    def _sanitize_for_error_message(self, value: str, max_length: int = 50) -> str:
        """
        Sanitize user input to prevent XSS attacks and information disclosure in error messages.

        Args:
            value: The input value to sanitize
            max_length: Maximum length for the sanitized value

        Returns:
            Sanitized value safe for inclusion in error messages
        """
        if not value:
            return "[empty]"

        # First, handle Unicode normalization attacks and control characters
        # Remove/replace dangerous Unicode characters
        import unicodedata

        # Normalize Unicode to prevent normalization attacks
        try:
            sanitized = unicodedata.normalize('NFKC', value)
        except:
            sanitized = value

        # Remove control characters and format characters
        sanitized = ''.join(char for char in sanitized
                          if unicodedata.category(char) not in ['Cc', 'Cf', 'Cs', 'Co'])

        # HTML escape to prevent XSS
        sanitized = html.escape(sanitized)

        # Remove dangerous patterns that could still be problematic
        dangerous_patterns = [
            'javascript:',
            'vbscript:',
            'data:',
            'onload=',
            'onerror=',
            'onclick=',
            'onmouseover=',
            'onfocus=',
            'onblur=',
        ]

        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, '[removed]')
            sanitized = sanitized.replace(pattern.upper(), '[removed]')

        # Remove sensitive information patterns to prevent information disclosure
        sensitive_patterns = [
            '/etc/',
            '/root/',
            '/home/',
            '/var/',
            '/usr/',
            'c:\\',
            'windows\\',
            'system32\\',
            'delete from',
            'drop table',
            'insert into',
            'select *',
            'union select',
            'password',
            'passwd',
            'secret',
            'key',
            'token',
            'auth',
            'credential',
            'api_key',
            'database',
            'config',
            'admin',
        ]

        sanitized_lower = sanitized.lower()
        for pattern in sensitive_patterns:
            if pattern in sanitized_lower:
                # Replace sensitive content with generic placeholder
                sanitized = "[redacted-sensitive-content]"
                break

        # Truncate long values to prevent log flooding
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized

    def validate_uuid_format(self, value: str) -> ValidationResult:
        """
        Validate that a string is in proper UUID format.

        Args:
            value: The string to validate as UUID

        Returns:
            ValidationResult with validation status and details
        """
        if not value:
            return ValidationResult(
                is_valid=False,
                id_type=IDType.UNKNOWN,
                original_value=value or "",
                error_message="ID value cannot be empty or None"
            )

        # Security check: Reject if contains any non-ASCII characters
        # UUIDs should only contain ASCII hex digits and hyphens
        if not all(ord(char) < 128 for char in value):
            sanitized_value = self._sanitize_for_error_message(value)
            return ValidationResult(
                is_valid=False,
                id_type=IDType.UNKNOWN,
                original_value=value,
                error_message=f"Invalid UUID format: {sanitized_value}. Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        # Security check: Reject if contains any control characters
        if any(ord(char) < 32 for char in value):
            sanitized_value = self._sanitize_for_error_message(value)
            return ValidationResult(
                is_valid=False,
                id_type=IDType.UNKNOWN,
                original_value=value,
                error_message=f"Invalid UUID format: {sanitized_value}. Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        # Normalize the value
        normalized = value.strip().lower()

        # Check UUID format
        if self._uuid_pattern.match(normalized):
            return ValidationResult(
                is_valid=True,
                id_type=IDType.UUID,
                original_value=value,
                normalized_value=normalized,
                metadata={"uuid_version": "v4" if self.strict_uuid_validation else "any"}
            )
        else:
            sanitized_value = self._sanitize_for_error_message(value)
            return ValidationResult(
                is_valid=False,
                id_type=IDType.UNKNOWN,
                original_value=value,
                error_message=f"Invalid UUID format: {sanitized_value}. Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

    def detect_id_type(self, value: str, context_hint: Optional[str] = None) -> ValidationResult:
        """
        Detect the type of ID based on format and context hints.

        Args:
            value: The ID string to analyze
            context_hint: Optional hint about the expected ID type (e.g., "task_id", "git_branch_id")

        Returns:
            ValidationResult with detected ID type and validation status
        """
        # First validate basic UUID format
        uuid_result = self.validate_uuid_format(value)
        if not uuid_result.is_valid:
            return uuid_result

        # Determine specific ID type based on context hints
        detected_type = IDType.UUID  # Default for valid UUIDs
        warnings = []

        if context_hint:
            hint_lower = context_hint.lower()

            if "task" in hint_lower and "mcp" not in hint_lower:
                detected_type = IDType.APPLICATION_TASK_ID
            elif "task" in hint_lower and "mcp" in hint_lower:
                detected_type = IDType.MCP_TASK_ID
                warnings.append("MCP task ID detected - ensure not used as application task ID")
            elif "git_branch" in hint_lower or "branch" in hint_lower:
                detected_type = IDType.GIT_BRANCH_ID
            elif "project" in hint_lower:
                detected_type = IDType.PROJECT_ID
            elif "user" in hint_lower:
                detected_type = IDType.USER_ID
            elif "context" in hint_lower:
                detected_type = IDType.CONTEXT_ID

        return ValidationResult(
            is_valid=True,
            id_type=detected_type,
            original_value=value,
            normalized_value=uuid_result.normalized_value,
            warnings=warnings if warnings else None,
            metadata={
                "context_hint": context_hint,
                "uuid_version": "v4" if self.strict_uuid_validation else "any"
            }
        )

    def validate_parameter_mapping(self,
                                 task_id: Optional[str] = None,
                                 git_branch_id: Optional[str] = None,
                                 project_id: Optional[str] = None,
                                 user_id: Optional[str] = None) -> ValidationResult:
        """
        Validate that parameters are not confused with each other.

        This method specifically prevents the critical bug where task_id
        is incorrectly passed as git_branch_id to facade services.

        Args:
            task_id: Application task ID
            git_branch_id: Git branch ID
            project_id: Project ID
            user_id: User ID

        Returns:
            ValidationResult indicating if parameter mapping is correct
        """
        parameters = {
            "task_id": task_id,
            "git_branch_id": git_branch_id,
            "project_id": project_id,
            "user_id": user_id
        }

        # Filter out None values
        provided_params = {k: v for k, v in parameters.items() if v is not None}

        if not provided_params:
            return ValidationResult(
                is_valid=False,
                id_type=IDType.UNKNOWN,
                original_value="",
                error_message="At least one parameter must be provided"
            )

        validation_errors = []
        warnings = []
        all_valid = True

        # Validate each provided parameter
        for param_name, param_value in provided_params.items():
            param_result = self.detect_id_type(param_value, param_name)

            if not param_result.is_valid:
                all_valid = False
                validation_errors.append(f"{param_name}: {param_result.error_message}")

            # Check for potential confusion
            if param_name == "git_branch_id" and param_result.id_type == IDType.MCP_TASK_ID:
                all_valid = False
                sanitized_param_value = self._sanitize_for_error_message(param_value)
                validation_errors.append(
                    f"CRITICAL: MCP task ID {sanitized_param_value} incorrectly passed as git_branch_id. "
                    f"This causes data integrity issues."
                )

            if param_name == "task_id" and param_result.id_type == IDType.GIT_BRANCH_ID:
                sanitized_param_value = self._sanitize_for_error_message(param_value)
                warnings.append(
                    f"WARNING: Git branch ID {sanitized_param_value} passed as task_id. "
                    f"Verify this is intentional."
                )

            if param_result.warnings:
                warnings.extend(param_result.warnings)

        # Check for same ID used in multiple parameters (potential copy-paste error)
        unique_values = set(provided_params.values())
        if len(unique_values) < len(provided_params):
            warnings.append("Same ID value used for multiple parameters - verify this is intentional")

        return ValidationResult(
            is_valid=all_valid,
            id_type=IDType.UUID,  # All parameters should be UUIDs
            original_value=str(provided_params),
            error_message="; ".join(validation_errors) if validation_errors else None,
            warnings=warnings if warnings else None,
            metadata={
                "validated_parameters": list(provided_params.keys()),
                "parameter_count": len(provided_params)
            }
        )

    def validate_task_context(self, task_id: str, expected_git_branch_id: Optional[str] = None) -> ValidationResult:
        """
        Validate task context to ensure task_id corresponds to correct git_branch_id.

        This method helps prevent the critical issue where MCP task IDs
        are incorrectly used as git_branch_ids in facade service calls.

        Args:
            task_id: The task ID to validate
            expected_git_branch_id: The expected git_branch_id for validation

        Returns:
            ValidationResult with validation status and recommendations
        """
        # Validate task_id format
        task_result = self.detect_id_type(task_id, "task_id")
        if not task_result.is_valid:
            return task_result

        warnings = []
        metadata = {"validation_type": "task_context"}

        # Check if task_id looks like an MCP task ID
        if task_result.id_type == IDType.MCP_TASK_ID:
            warnings.append(
                "Task ID appears to be an MCP task ID. Ensure proper lookup "
                "is performed to get the corresponding application task ID."
            )

        # Validate git_branch_id if provided
        if expected_git_branch_id:
            branch_result = self.detect_id_type(expected_git_branch_id, "git_branch_id")
            if not branch_result.is_valid:
                sanitized_task_id = self._sanitize_for_error_message(task_id)
                sanitized_git_branch_id = self._sanitize_for_error_message(expected_git_branch_id)
                return ValidationResult(
                    is_valid=False,
                    id_type=IDType.UNKNOWN,
                    original_value=f"task_id: {sanitized_task_id}, git_branch_id: {sanitized_git_branch_id}",
                    error_message=f"Invalid git_branch_id: {branch_result.error_message}"
                )

            # Critical check: ensure task_id != git_branch_id
            if task_id == expected_git_branch_id:
                sanitized_task_id = self._sanitize_for_error_message(task_id)
                sanitized_git_branch_id = self._sanitize_for_error_message(expected_git_branch_id)
                return ValidationResult(
                    is_valid=False,
                    id_type=IDType.UNKNOWN,
                    original_value=f"task_id: {sanitized_task_id}, git_branch_id: {sanitized_git_branch_id}",
                    error_message=(
                        "CRITICAL: task_id and git_branch_id are identical. "
                        "This indicates parameter confusion that leads to data integrity issues."
                    )
                )

            metadata["git_branch_id_validated"] = True

        return ValidationResult(
            is_valid=True,
            id_type=task_result.id_type,
            original_value=task_id,
            normalized_value=task_result.normalized_value,
            warnings=warnings if warnings else None,
            metadata=metadata
        )

    def suggest_fix_for_confusion(self,
                                confused_task_id: str,
                                context: str = "unknown") -> Dict[str, str]:
        """
        Provide suggestions for fixing ID confusion issues.

        Args:
            confused_task_id: The ID that's being used incorrectly
            context: Context where the confusion occurred

        Returns:
            Dictionary with fix suggestions and code examples
        """
        suggestions = {
            "issue": f"ID confusion detected in {context}",
            "confused_id": confused_task_id,
            "root_cause": "MCP task ID being used as application task ID",
            "immediate_fix": (
                "Look up the correct git_branch_id from the task record before "
                "passing to facade service"
            ),
            "code_example": '''
# WRONG (causes data integrity issues):
facade = self._facade_service.get_subtask_facade(
    user_id=user_id,
    git_branch_id=task_id  # BUG: task_id ≠ git_branch_id
)

# CORRECT (proper ID resolution):
task_facade = self._facade_service.get_task_facade(user_id=user_id)
task_response = task_facade.get_task(task_id=task_id)
git_branch_id = task_response['data']['task']['git_branch_id']

facade = self._facade_service.get_subtask_facade(
    user_id=user_id,
    git_branch_id=git_branch_id  # FIXED: Use correct git_branch_id
)
            ''',
            "prevention": (
                "Use IDValidator.validate_parameter_mapping() before facade calls "
                "to catch parameter confusion early"
            )
        }

        return suggestions


# Convenience functions for common validation scenarios

def validate_uuid(value: str, strict: bool = True) -> bool:
    """
    Quick UUID validation function.

    Args:
        value: String to validate
        strict: If True, enforces UUID v4 format

    Returns:
        True if valid UUID, False otherwise
    """
    validator = IDValidator(strict_uuid_validation=strict)
    result = validator.validate_uuid_format(value)
    return result.is_valid


def prevent_id_confusion(task_id: Optional[str] = None,
                        git_branch_id: Optional[str] = None,
                        project_id: Optional[str] = None,
                        user_id: Optional[str] = None) -> None:
    """
    Validate parameters to prevent ID confusion (raises exception on failure).

    This function should be called before any facade service creation
    to prevent the critical MCP ID vs Application ID confusion.

    Args:
        task_id: Application task ID
        git_branch_id: Git branch ID
        project_id: Project ID
        user_id: User ID

    Raises:
        IDValidationError: If validation fails or confusion is detected
    """
    validator = IDValidator()
    result = validator.validate_parameter_mapping(
        task_id=task_id,
        git_branch_id=git_branch_id,
        project_id=project_id,
        user_id=user_id
    )

    if not result.is_valid:
        raise IDValidationError(
            message=result.error_message or "ID validation failed",
            id_value=result.original_value
        )

    # Log warnings for monitoring
    if result.warnings:
        for warning in result.warnings:
            logger.warning(f"ID Validation Warning: {warning}")


def is_mcp_task_id(value: str) -> bool:
    """
    Check if a value appears to be an MCP task ID.

    Note: Without additional context, this function can only validate UUID format.
    True MCP task ID detection requires context about the source or usage.

    Args:
        value: String to check

    Returns:
        True if appears to be MCP task ID, False otherwise
    """
    validator = IDValidator()
    result = validator.validate_uuid_format(value)
    # For now, just check if it's a valid UUID format
    # In real scenarios, additional context would be needed to distinguish
    # MCP task IDs from application task IDs
    return result.is_valid


# Global validator instance for module-level use
default_validator = IDValidator()