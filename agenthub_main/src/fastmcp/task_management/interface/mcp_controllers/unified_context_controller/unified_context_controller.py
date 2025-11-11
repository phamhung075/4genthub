"""Unified Context MCP Controller - Updated Implementation

This controller handles MCP tool registration for unified context management operations,
following the new standardized MCP parameter pattern for consistent parameter type display.
"""

import json
import logging
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import permission system for resource-specific CRUD authorization
from .....auth.domain.permissions import (
    PermissionAction,
    PermissionChecker,
    ResourceType,
)
from ....application.services.facade_service import FacadeService
from ...utils.response_formatter import ErrorCodes, StandardResponseFormatter
from ..auth_helper import get_authenticated_user_id
from .factories.operation_factory import ContextOperationFactory
from .manage_unified_context_description import (
    get_manage_unified_context_description,
    get_manage_unified_context_parameters,
)

logger = logging.getLogger(__name__)

# Get centralized parameter definitions at module level
# This must be at module level so Pydantic can access it when evaluating type annotations
params = get_manage_unified_context_parameters()


# Pre-compute Field descriptors to avoid annotation evaluation issues
ActionField = Field(description="[OPTIONAL] " + params["action"]["description"])
LevelField = Field(description="[REQUIRED for all actions except 'list'] " + params["level"]["description"])
ContextIdField = Field(description="[REQUIRED for all actions except 'list'] " + params["context_id"]["description"])
DataField = Field(description="[OPTIONAL] " + params["data"]["description"])
UserIdField = Field(description="[OPTIONAL] " + params["user_id"]["description"])
ProjectIdField = Field(description="[OPTIONAL] " + params["project_id"]["description"])
GitBranchIdField = Field(description="[OPTIONAL] " + params["git_branch_id"]["description"])
ForceRefreshField = Field(description="[OPTIONAL] " + params["force_refresh"]["description"])
IncludeInheritedField = Field(description="[OPTIONAL] " + params["include_inherited"]["description"])
PropagateChangesField = Field(description="[OPTIONAL] " + params["propagate_changes"]["description"])
DelegateToField = Field(description="[REQUIRED for 'delegate' action] " + params["delegate_to"]["description"])
DelegateDataField = Field(description="[OPTIONAL] " + params["delegate_data"]["description"])
DelegationReasonField = Field(description="[OPTIONAL] " + params["delegation_reason"]["description"])
ContentField = Field(description="[REQUIRED for 'add_insight' and 'add_progress' actions] " + params["content"]["description"])
CategoryField = Field(description="[OPTIONAL] " + params["category"]["description"])
ImportanceField = Field(description="[OPTIONAL] " + params["importance"]["description"])
AgentField = Field(description="[OPTIONAL] " + params["agent"]["description"])
FiltersField = Field(description="[OPTIONAL] " + params["filters"]["description"])


class UnifiedContextMCPController:
    """
    MCP Controller for unified context management operations.

    Handles only MCP protocol concerns and delegates business operations
    to specialized handlers following proper DDD layer separation.
    """

    def __init__(self, facade_service: FacadeService | None = None):
        """
        Initialize controller with facade service.

        Args:
            facade_service: Service for obtaining application facades (optional)
        """
        self._facade_service = facade_service or FacadeService.get_instance()
        self._response_formatter = StandardResponseFormatter()
        self._operation_factory = ContextOperationFactory(self._response_formatter)

        logger.info("UnifiedContextMCPController initialized with modular architecture")

    def register_tools(self, mcp: "FastMCP"):
        """Register unified context management tools with FastMCP."""

        @mcp.tool(description=get_manage_unified_context_description())
        def manage_context(
            action: Annotated[str, ActionField],
            level: Annotated[
                str, LevelField
            ] = None,
            context_id: Annotated[
                str, ContextIdField
            ] = None,
            data: Annotated[
                str, DataField
            ] = None,
            user_id: Annotated[
                str, UserIdField
            ] = None,
            project_id: Annotated[
                str, ProjectIdField
            ] = None,
            git_branch_id: Annotated[
                str, GitBranchIdField
            ] = None,
            force_refresh: Annotated[
                str, ForceRefreshField
            ] = None,
            include_inherited: Annotated[
                str, IncludeInheritedField
            ] = None,
            propagate_changes: Annotated[
                str, PropagateChangesField
            ] = None,
            delegate_to: Annotated[
                str, DelegateToField
            ] = None,
            delegate_data: Annotated[
                str, DelegateDataField
            ] = None,
            delegation_reason: Annotated[
                str, DelegationReasonField
            ] = None,
            content: Annotated[
                str, ContentField
            ] = None,
            category: Annotated[
                str, CategoryField
            ] = None,
            importance: Annotated[
                str, ImportanceField
            ] = None,
            agent: Annotated[
                str, AgentField
            ] = None,
            filters: Annotated[
                str, FiltersField
            ] = None,
        ) -> dict[str, Any]:
            """Main unified context management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.manage_unified_context(
                action=action,
                level=level,
                context_id=context_id,
                data=data,
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id,
                force_refresh=force_refresh,
                include_inherited=include_inherited,
                propagate_changes=propagate_changes,
                delegate_to=delegate_to,
                delegate_data=delegate_data,
                delegation_reason=delegation_reason,
                content=content,
                category=category,
                importance=importance,
                agent=agent,
                filters=filters,
            )

    def manage_unified_context(
        self,
        action: str,
        level: str | None = None,
        context_id: str | None = None,
        data: str | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        git_branch_id: str | None = None,
        force_refresh: str | None = None,
        include_inherited: str | None = None,
        propagate_changes: str | None = None,
        delegate_to: str | None = None,
        delegate_data: str | None = None,
        delegation_reason: str | None = None,
        content: str | None = None,
        category: str | None = None,
        importance: str | None = None,
        agent: str | None = None,
        filters: str | None = None,
    ) -> dict[str, Any]:
        """Main unified context management method with parameter coercion and validation."""
        try:
            # Import parameter coercion utility
            from ...utils.parameter_validation_fix import coerce_parameter_types

            # Coerce all parameters to proper types
            coerced_params = coerce_parameter_types(
                {
                    "level": level,
                    "context_id": context_id,
                    "data": data,
                    "user_id": user_id,
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "force_refresh": force_refresh,
                    "include_inherited": include_inherited,
                    "propagate_changes": propagate_changes,
                    "delegate_to": delegate_to,
                    "delegate_data": delegate_data,
                    "delegation_reason": delegation_reason,
                    "content": content,
                    "category": category,
                    "importance": importance,
                    "agent": agent,
                    "filters": filters,
                }
            )

            # Apply coerced values with defaults
            level = coerced_params.get("level", level) or "task"
            context_id = coerced_params.get("context_id", context_id)
            user_id = coerced_params.get("user_id", user_id)
            project_id = coerced_params.get("project_id", project_id)
            git_branch_id = coerced_params.get("git_branch_id", git_branch_id)
            force_refresh = coerced_params.get("force_refresh", force_refresh)
            include_inherited = coerced_params.get(
                "include_inherited", include_inherited
            )
            propagate_changes = coerced_params.get(
                "propagate_changes", propagate_changes
            )

            # Parse JSON string parameters
            if data and isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    return self._response_formatter.create_error_response(
                        operation="manage_context.create",
                        error=f"Invalid JSON string in data parameter: {str(e)}",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        metadata={
                            "field": "data",
                            "suggestions": "Ensure data parameter contains valid JSON",
                        },
                    )

            if delegate_data and isinstance(delegate_data, str):
                try:
                    delegate_data = json.loads(delegate_data)
                except json.JSONDecodeError as e:
                    return self._response_formatter.create_error_response(
                        operation="manage_context.delegate",
                        error=f"Invalid JSON string in delegate_data parameter: {str(e)}",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        metadata={
                            "field": "delegate_data",
                            "suggestions": "Ensure delegate_data parameter contains valid JSON",
                        },
                    )

            if filters and isinstance(filters, str):
                try:
                    filters = json.loads(filters)
                except json.JSONDecodeError as e:
                    return self._response_formatter.create_error_response(
                        operation="manage_context.list",
                        error=f"Invalid JSON string in filters parameter: {str(e)}",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        metadata={
                            "field": "filters",
                            "suggestions": "Ensure filters parameter contains valid JSON",
                        },
                    )

            # Get authenticated user
            authenticated_user_id = get_authenticated_user_id(
                user_id, f"manage_context.{action}"
            )

            # Permission Authorization - Check resource-specific CRUD permissions
            permission_result = self._check_context_permissions(
                action, authenticated_user_id, context_id
            )
            if not permission_result[0]:
                return permission_result[1]  # Return permission denied error

            # For global context, automatically use authenticated user's ID
            # No context_id needed for global - it's always user-scoped
            if level == "global":
                context_id = authenticated_user_id

            # Get facade from service with proper scoping
            facade = self._facade_service.get_context_facade(
                user_id=authenticated_user_id,
                project_id=project_id,
                git_branch_id=git_branch_id,
            )

            return self._operation_factory.handle_operation(
                facade=facade,
                action=action,
                level=level,
                context_id=context_id,
                data=data,
                user_id=authenticated_user_id,
                project_id=project_id,
                git_branch_id=git_branch_id,
                force_refresh=force_refresh,
                include_inherited=include_inherited,
                propagate_changes=propagate_changes,
                delegate_to=delegate_to,
                delegate_data=delegate_data,
                delegation_reason=delegation_reason,
                content=content,
                category=category,
                importance=importance,
                agent=agent,
                filters=filters,
            )

        except Exception as e:
            logger.error(f"Error in unified context management '{action}': {e}")
            return {
                "success": False,
                "error": f"Context operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
            }

    def _check_context_permissions(
        self, action: str, user_id: str, context_id: str | None = None
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Check if user has required permissions for context operations.

        Args:
            action: The action being performed (create, read, update, delete, etc.)
            user_id: The authenticated user ID
            context_id: Optional context ID for context-specific operations

        Returns:
            Tuple of (success: bool, error_response: Dict | None)
        """
        try:
            # Map action to permission
            action_to_permission = {
                "create": PermissionAction.CREATE,
                "get": PermissionAction.READ,
                "update": PermissionAction.UPDATE,
                "delete": PermissionAction.DELETE,
                "resolve": PermissionAction.READ,  # Resolve is read with inheritance
                "delegate": PermissionAction.DELEGATE,  # Delegate is special permission
                "add_insight": PermissionAction.UPDATE,  # Adding insight is update operation
                "add_progress": PermissionAction.UPDATE,  # Adding progress is update operation
                "list": PermissionAction.READ,  # List contexts is read access
            }

            required_permission = action_to_permission.get(action)
            if not required_permission:
                # Unknown action - allow by default (backwards compatibility)
                logger.warning(
                    f"Unknown context action '{action}' - allowing by default"
                )
                return True, None

            # Get user context and token for permission checking
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
                    logger.error(
                        f"No user context found for permission check - user_id: {user_id}"
                    )
                    return False, {
                        "success": False,
                        "error": "Authentication context not available for permission check",
                        "error_code": "AUTHENTICATION_ERROR",
                    }

                # Get token payload from user context
                user = request_context.user
                token_payload = getattr(user, "token", {})
                if not token_payload:
                    logger.error(f"No token payload found for user {user_id}")
                    return False, {
                        "success": False,
                        "error": "No token payload found for permission validation",
                        "error_code": "AUTHENTICATION_ERROR",
                    }

                # Check permissions using PermissionChecker
                checker = PermissionChecker(token_payload)
                has_permission = checker.has_permission(
                    ResourceType.CONTEXTS, required_permission
                )

                if not has_permission:
                    logger.warning(
                        f"User {user_id} lacks permission for contexts:{required_permission.value}"
                    )
                    return False, {
                        "success": False,
                        "error": f"Permission denied: requires contexts:{required_permission.value}",
                        "error_code": "PERMISSION_DENIED",
                    }

                logger.debug(
                    f"User {user_id} has permission for contexts:{required_permission.value}"
                )
                return True, None

            except ImportError:
                # Fallback: If request context middleware is not available, allow operation
                # This ensures backwards compatibility
                logger.warning(
                    f"Request context middleware not available - allowing context {action} for user {user_id}"
                )
                return True, None

        except Exception as e:
            logger.error(
                f"Error checking context permissions for user {user_id}, action {action}: {e}"
            )
            # On error, allow the operation to proceed (fail-open for now)
            return True, None

    def manage_context(self, **kwargs) -> dict[str, Any]:
        """Backward compatibility method that delegates to manage_unified_context"""
        return self.manage_unified_context(**kwargs)
