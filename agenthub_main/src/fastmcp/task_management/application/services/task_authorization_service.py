"""
Task Authorization Service

This service provides authorization checking for task operations,
extracting permission logic from controllers to the application layer.
Integrates with the existing PermissionChecker system.
"""

from __future__ import annotations

import logging
from typing import Any

from ....auth.domain.permissions import (
    PermissionAction,
    PermissionChecker,
    ResourceType,
)

logger = logging.getLogger(__name__)


class TaskAuthorizationService:
    """
    Service for handling task-related authorization checks.

    This service extracts authorization logic from controllers, providing
    a clean separation between interface and application layers.
    """

    # Action to permission mapping for task operations
    ACTION_PERMISSION_MAP = {
        "create": PermissionAction.CREATE,
        "get": PermissionAction.READ,
        "list": PermissionAction.READ,
        "search": PermissionAction.READ,
        "update": PermissionAction.UPDATE,
        "complete": PermissionAction.UPDATE,  # Completing is an update operation
        "delete": PermissionAction.DELETE,
        "next": PermissionAction.READ,  # Getting next task is read access
        "add_dependency": PermissionAction.UPDATE,  # Adding dependency is update
        "remove_dependency": PermissionAction.UPDATE,  # Removing dependency is update
    }

    def __init__(self, response_formatter: Any | None = None):
        """
        Initialize the authorization service.

        Args:
            response_formatter: Optional response formatter for creating error responses
        """
        self._response_formatter = response_formatter

    def check_task_permission(
        self,
        action: str,
        user_id: str,
        token_payload: dict[str, Any],
        task_id: str | None = None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Check if user has required permissions for task operations.

        Args:
            action: The action being performed (create, read, update, delete, etc.)
            user_id: The authenticated user ID
            token_payload: The JWT token payload containing permissions
            task_id: Optional task ID for task-specific operations

        Returns:
            Tuple of (success: bool, error_response: Dict | None)
            - If authorized: (True, None)
            - If denied: (False, error_response_dict)
        """
        try:
            # Map action to permission
            required_permission = self.ACTION_PERMISSION_MAP.get(action)

            if not required_permission:
                # Unknown action - allow by default (backwards compatibility)
                logger.warning(f"Unknown task action '{action}' - allowing by default")
                return True, None

            # Validate token payload
            if not token_payload:
                logger.error(f"No token payload found for user {user_id}")
                if self._response_formatter:
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error="No token payload found for permission validation",
                        error_code="AUTHENTICATION_ERROR",
                    )
                return False, {
                    "error": "No token payload found",
                    "code": "AUTHENTICATION_ERROR",
                }

            # Check permissions using PermissionChecker
            checker = PermissionChecker(token_payload)
            has_permission = checker.has_permission(
                ResourceType.TASKS, required_permission
            )

            if not has_permission:
                logger.warning(
                    f"User {user_id} lacks permission for tasks:{required_permission.value}"
                )
                if self._response_formatter:
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error=f"Permission denied: requires tasks:{required_permission.value}",
                        error_code="PERMISSION_DENIED",
                    )
                return False, {
                    "error": f"Permission denied: requires tasks:{required_permission.value}",
                    "code": "PERMISSION_DENIED",
                }

            logger.debug(
                f"User {user_id} has permission for tasks:{required_permission.value}"
            )
            return True, None

        except Exception as e:
            logger.error(
                f"Error checking task permissions for user {user_id}, action {action}: {e}"
            )
            # On error, allow the operation to proceed (fail-open for now)
            # In production, you might want to fail-closed (deny access on errors)
            return True, None

    def get_permission_for_action(self, action: str) -> PermissionAction | None:
        """
        Get the required permission for a given action.

        Args:
            action: The action being performed

        Returns:
            The required PermissionAction, or None if action is unknown
        """
        return self.ACTION_PERMISSION_MAP.get(action)

    def is_valid_action(self, action: str) -> bool:
        """
        Check if an action is valid and recognized.

        Args:
            action: The action to validate

        Returns:
            True if action is recognized, False otherwise
        """
        return action in self.ACTION_PERMISSION_MAP

    @staticmethod
    def extract_token_from_context() -> dict[str, Any] | None:
        """
        Extract token payload from current request context.

        This is a helper method that retrieves the token from the request context
        when available. Falls back gracefully when context is not available.

        Returns:
            Token payload dictionary if available, None otherwise
        """
        try:
            # Import here to avoid circular imports
            from .....auth.middleware.request_context_middleware import (
                get_current_request_context,
            )

            request_context = get_current_request_context()

            if (
                not request_context
                or not hasattr(request_context, "user")
                or not request_context.user
            ):
                # No context available (test environment or missing middleware)
                logger.debug("No user context found for token extraction")
                return None

            # Get token payload from user context
            user = request_context.user
            token_payload = getattr(user, "token", {})

            if not token_payload:
                logger.warning("User context exists but no token payload found")
                return None

            return token_payload

        except ImportError:
            # Middleware not available - likely in test environment
            logger.debug("Request context middleware not available")
            return None
        except Exception as e:
            logger.error(f"Error extracting token from context: {e}")
            return None

    def check_task_permission_from_context(
        self,
        action: str,
        user_id: str,
        task_id: str | None = None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Check task permission using token from current request context.

        This is a convenience method that automatically extracts the token
        from the request context and checks permissions.

        Args:
            action: The action being performed
            user_id: The authenticated user ID
            task_id: Optional task ID for task-specific operations

        Returns:
            Tuple of (success: bool, error_response: Dict | None)
        """
        token_payload = self.extract_token_from_context()

        if not token_payload:
            # Fallback for test environments or when authentication context is not available
            logger.warning(
                f"No user context found for permission check - user_id: {user_id}, "
                f"falling back to allow for backwards compatibility"
            )
            return True, None

        return self.check_task_permission(action, user_id, token_payload, task_id)
