"""
Task MCP Controller - Refactored Modular Implementation

This is the main entry point for the task MCP controller, now refactored into a modular 
architecture using factory pattern to maintain separation of concerns.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Annotated, Union
from datetime import datetime, timezone
from pydantic import Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import modular components
from .factories.operation_factory import OperationFactory
from .factories.validation_factory import ValidationFactory
from .factories.response_factory import ResponseFactory

# Import existing dependencies
# Import the description and parameters directly from the local file
from .manage_task_description import MANAGE_TASK_DESCRIPTION, get_manage_task_description, get_manage_task_parameters
from ..workflow_hint_enhancer import WorkflowHintEnhancer
from ..workflow_guidance.task import TaskWorkflowFactory
from ...utils.error_handler import UserFriendlyErrorHandler
from ...utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

from ....application.dtos.task.create_task_request import CreateTaskRequest
from ....application.dtos.task.list_tasks_request import ListTasksRequest
from ....application.dtos.task.search_tasks_request import SearchTasksRequest
from ....application.dtos.task.update_task_request import UpdateTaskRequest
from ....application.services.facade_service import FacadeService

from ....application.facades.task_application_facade import TaskApplicationFacade
from ....application.facades.unified_context_facade import UnifiedContextFacade
# Services are created by factories with their required dependencies
from ....application.services.parameter_enforcement_service import (
    ParameterEnforcementService, 
    EnforcementLevel,
    EnforcementResult
)
from ....application.services.progressive_enforcement_service import ProgressiveEnforcementService
from ....application.services.response_enrichment_service import (
    ResponseEnrichmentService,
    ContextState,
    ContextStalnessLevel
)
from ....domain.constants import validate_user_id
from ....domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError
)
from .....config.auth_config import AuthConfig
from ..auth_helper import get_authenticated_user_id, log_authentication_details

# Import permission system for resource-specific CRUD authorization
from .....auth.domain.permissions import (
    require_permission, 
    ResourceType, 
    PermissionAction,
    PermissionChecker
)

logger = logging.getLogger(__name__)

# Import user context utilities - REQUIRED for authentication
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
    from fastmcp.auth.mcp_integration.thread_context_manager import ContextPropagationMixin
except ImportError:
    # Try alternative import path for RequestContextMiddleware
    try:
        from ..auth_helper import get_authenticated_user_id as get_current_user_id
    except ImportError:
        # Authentication is required - no fallbacks allowed
        from ....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        def get_current_user_id():
            raise UserAuthenticationRequiredError("User context middleware not available")
    
    # Fallback mixin if thread context manager is not available
    class ContextPropagationMixin:
        def _run_async_with_context(self, async_func, *args, **kwargs):
            import asyncio
            import threading
            result = None
            exception = None
            def run_in_new_loop():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(async_func(*args, **kwargs))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                except Exception as e:
                    exception = e
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()
            if exception:
                raise exception
            return result


class TaskMCPController(ContextPropagationMixin):
    """
    Refactored Task MCP Controller with modular architecture.
    
    This controller now uses factory pattern to delegate operations to specialized handlers,
    maintaining the same interface while improving maintainability and separation of concerns.
    """

    def __init__(self, 
                 facade_service: Optional[FacadeService] = None,
                 workflow_hint_enhancer: Optional[WorkflowHintEnhancer] = None):
        """Initialize the modular task MCP controller."""
        
        # Initialize core dependencies
        self._facade_service = facade_service or FacadeService.get_instance()
        self._workflow_hint_enhancer = workflow_hint_enhancer
        
        # Initialize response formatter and error handler
        self._response_formatter = StandardResponseFormatter()
        self._error_handler = UserFriendlyErrorHandler()
        
        # Initialize modular factories
        self._operation_factory = OperationFactory(
            response_formatter=self._response_formatter,
            context_facade_factory=None  # Will be obtained from facade_service
        )
        
        self._validation_factory = ValidationFactory(
            response_formatter=self._response_formatter
        )
        
        self._response_factory = ResponseFactory(
            response_formatter=self._response_formatter
        )
        
        # Initialize workflow components
        workflow_factory = TaskWorkflowFactory()
        self._workflow_guidance = workflow_factory.create()
        
        # Note: Orchestrator services are created by factories as needed
        # They require repositories and other dependencies that are not available here
        
        # Initialize enforcement services
        self._enforcement_service = ParameterEnforcementService(EnforcementLevel.WARNING)
        self._progressive_enforcement = ProgressiveEnforcementService(
            enforcement_service=self._enforcement_service,
            default_level=EnforcementLevel.WARNING
        )
        
        # Initialize response enrichment service
        self._response_enrichment = ResponseEnrichmentService()
        
        logger.info("TaskMCPController initialized with modular architecture")
        
        # Store last known git_branch_id for context operations
        self._last_git_branch_id = None

    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with the server."""
        
        # Load description and parameters
        tool_description = get_manage_task_description()
        tool_parameters = get_manage_task_parameters()
        
        # Extract parameter definitions
        params = tool_parameters["properties"]
        
        async def manage_task(
            action: Annotated[str, Field(description=params["action"]["description"])],
            task_id: Annotated[str, Field(description="[OPTIONAL] " + params["task_id"]["description"])] = None,
            git_branch_id: Annotated[str, Field(description="[OPTIONAL] " + params["git_branch_id"]["description"])] = None,
            title: Annotated[str, Field(description="[OPTIONAL] " + params["title"]["description"])] = None,
            description: Annotated[str, Field(description="[OPTIONAL] " + params["description"]["description"])] = None,
            status: Annotated[str, Field(description="[OPTIONAL] " + params["status"]["description"])] = None,
            priority: Annotated[str, Field(description="[OPTIONAL] " + params["priority"]["description"])] = None,
            details: Annotated[str, Field(description="[OPTIONAL] " + params["details"]["description"])] = None,
            estimated_effort: Annotated[str, Field(description="[OPTIONAL] " + params["estimated_effort"]["description"])] = None,
            assignees: Annotated[str, Field(description="[OPTIONAL] " + params["assignees"]["description"])] = None,
            labels: Annotated[str, Field(description="[OPTIONAL] " + params["labels"]["description"])] = None,
            due_date: Annotated[str, Field(description="[OPTIONAL] " + params["due_date"]["description"])] = None,
            dependencies: Annotated[str, Field(description="[OPTIONAL] " + params["dependencies"]["description"])] = None,
            dependency_id: Annotated[str, Field(description="[OPTIONAL] " + params["dependency_id"]["description"])] = None,
            context_id: Annotated[str, Field(description="[OPTIONAL] " + params["context_id"]["description"])] = None,
            completion_summary: Annotated[str, Field(description="[OPTIONAL] " + params["completion_summary"]["description"])] = None,
            testing_notes: Annotated[str, Field(description="[OPTIONAL] " + params["testing_notes"]["description"])] = None,
            query: Annotated[str, Field(description="[OPTIONAL] " + params["query"]["description"])] = None,
            limit: Annotated[int, Field(description="[OPTIONAL] " + params["limit"]["description"])] = None,
            offset: Annotated[int, Field(description="[OPTIONAL] " + params["offset"]["description"])] = None,
            sort_by: Annotated[str, Field(description="[OPTIONAL] " + params["sort_by"]["description"])] = None,
            sort_order: Annotated[str, Field(description="[OPTIONAL] " + params["sort_order"]["description"])] = None,
            include_context: Annotated[bool, Field(description="[OPTIONAL] " + params["include_context"]["description"])] = None,
            force_full_generation: Annotated[bool, Field(description="[OPTIONAL] " + params["force_full_generation"]["description"])] = None,
            assignee: Annotated[str, Field(description="[OPTIONAL] " + params["assignee"]["description"])] = None,
            tag: Annotated[str, Field(description="[OPTIONAL] " + params["tag"]["description"])] = None,
            user_id: Annotated[str, Field(description="[OPTIONAL] " + params["user_id"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main task management function with all parameters.
            
            TWO-STAGE VALIDATION PATTERN:
            1. Schema validation: Only 'action' is required at MCP level
            2. Business validation: Action-specific parameters are validated based on the action value
            
            This design allows flexible parameter requirements while maintaining a single entry point.
            Each action has its own required parameters validated by the ValidationFactory.
            """
            # Handle None defaults for boolean parameters
            if include_context is None:
                include_context = False
            if force_full_generation is None:
                force_full_generation = False
            
            # Handle flexible input types for parameters that can be string, list, or comma-separated
            if assignees is not None and isinstance(assignees, str):
                # Convert comma-separated string to list if needed
                if ',' in assignees:
                    assignees = [a.strip() for a in assignees.split(',')]
            
            if labels is not None and isinstance(labels, str):
                # Convert comma-separated string to list if needed
                if ',' in labels:
                    labels = [l.strip() for l in labels.split(',')]
            
            if dependencies is not None and isinstance(dependencies, str):
                # Convert comma-separated string to list if needed
                if ',' in dependencies:
                    dependencies = [d.strip() for d in dependencies.split(',')]
            
            # Convert string representations of integers to actual integers
            if limit is not None and not isinstance(limit, int):
                try:
                    limit = int(limit)
                except (ValueError, TypeError):
                    limit = 50  # Default value
            
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except (ValueError, TypeError):
                    offset = 0  # Default value
            
            return await self.manage_task(
                action=action, task_id=task_id, git_branch_id=git_branch_id,
                title=title, description=description, status=status, 
                priority=priority, details=details, estimated_effort=estimated_effort,
                assignees=assignees, labels=labels, due_date=due_date,
                dependencies=dependencies, dependency_id=dependency_id, context_id=context_id,
                completion_summary=completion_summary, testing_notes=testing_notes,
                query=query, limit=limit, offset=offset, sort_by=sort_by,
                sort_order=sort_order, include_context=include_context,
                force_full_generation=force_full_generation,
                assignee=assignee, tag=tag, user_id=user_id
            )
        
        # Register tool with description only (parameters is not supported by MCP tool decorator)
        mcp.tool(description=tool_description)(manage_task)

    async def manage_task(self, action: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for task management operations with modular architecture.
        
        Two-stage validation pattern:
        - Stage 1: MCP validates only 'action' is present (schema level)
        - Stage 2: This method validates action-specific requirements (business level)
        
        This allows different actions to have different required parameters while
        maintaining a single, flexible entry point for all task operations.
        """
        
        try:
            # Step 1: Authentication
            user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=f"manage_task:{action}"
            )
            log_authentication_details(user_id, f"manage_task:{action}")
            
            # Step 1.5: Permission Authorization - Check resource-specific CRUD permissions
            permission_result = self._check_task_permissions(action, user_id, kwargs.get('task_id'))
            if not permission_result[0]:
                return permission_result[1]  # Return permission denied error
            
            # Step 2: Extract task_id early and filter it from kwargs to prevent duplicates
            task_id = kwargs.get('task_id')
            git_branch_id = kwargs.get('git_branch_id')
            
            # Debug logging
            logger.info(f"manage_task - action: {action}")
            logger.info(f"manage_task - original kwargs keys: {list(kwargs.keys())}")
            logger.info(f"manage_task - task_id extracted: {task_id}")
            
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'task_id'}
            logger.info(f"manage_task - filtered_kwargs keys: {list(filtered_kwargs.keys())}")
            
            # Step 3: Get facade for request
            logger.debug(f"Getting facade for action={action}, task_id={task_id}, git_branch_id={git_branch_id}")
            facade = self._get_facade_for_request(
                task_id=task_id,
                git_branch_id=git_branch_id,
                user_id=user_id
            )
            
            # Step 4: Validation using factory (pass task_id explicitly)
            validation_result = self._validate_request(action, task_id=task_id, **filtered_kwargs)
            if not validation_result[0]:
                return validation_result[1]  # Return validation error
            
            # Step 5: Execute operation using factory (pass task_id explicitly)
            result = await self._operation_factory.handle_operation(
                operation=action,
                facade=facade,
                user_id=user_id,
                task_id=task_id,
                **filtered_kwargs
            )
            
            # Step 6: Standardize response using factory
            standardized_result = self._response_factory.standardize_facade_response(result, action)
            
            # Step 7: Apply workflow hints and enrichment (use original kwargs for context)
            if self._workflow_hint_enhancer and standardized_result.get("success"):
                try:
                    # Try without await first, as the method might not be async
                    enriched_result = self._workflow_hint_enhancer.enhance_response(
                        response=standardized_result,
                        action=action,
                        context=kwargs
                    )
                    return enriched_result
                except Exception as e:
                    logger.warning(f"Workflow hint enhancer failed: {e}")
                    # Return the result without enhancement if enhancement fails
                    return standardized_result
            
            return standardized_result
            
        except Exception as e:
            logger.error(f"Error in manage_task {action}: {str(e)}")
            return self._response_factory.create_error_response(
                operation=action,
                error=str(e),
                error_code=ErrorCodes.OPERATION_FAILED
            )

    def _get_facade_for_request(self, task_id: Optional[str] = None, 
                               git_branch_id: Optional[str] = None, 
                               user_id: Optional[str] = None) -> TaskApplicationFacade:
        """Get appropriate facade for the request."""
        
        if not self._facade_service:
            raise ValueError("FacadeService is required but not provided")
        
        logger.debug(f"_get_facade_for_request: task_id={task_id}, git_branch_id={git_branch_id}, user_id={user_id}")
        
        # Create facade with appropriate context
        if git_branch_id:
            # For operations with git_branch_id, use it (but project_id is None for now)
            logger.debug("Creating facade with git_branch_id")
            return self._facade_service.get_task_facade(project_id=None, git_branch_id=git_branch_id, user_id=user_id)
        elif task_id:
            # For task-specific operations, create facade without specific branch
            logger.debug("Creating facade for task-specific operation")
            return self._facade_service.get_task_facade(project_id=None, git_branch_id=None, user_id=user_id)
        else:
            # For general operations
            logger.debug("Creating facade for general operation")
            return self._facade_service.get_task_facade(project_id=None, git_branch_id=None, user_id=user_id)

    def _validate_request(self, action: str, task_id: Optional[str] = None, **kwargs):
        """Validate request using validation factory."""
        
        if action == "create":
            return self._validation_factory.validate_create_request(
                title=kwargs.get('title'),
                git_branch_id=kwargs.get('git_branch_id'),
                description=kwargs.get('description'),
                status=kwargs.get('status'),
                priority=kwargs.get('priority'),
                due_date=kwargs.get('due_date'),
                assignees=kwargs.get('assignees'),
                labels=kwargs.get('labels'),
                dependencies=kwargs.get('dependencies')
            )
        elif action in ["update", "complete"]:
            # Pass task_id explicitly to avoid duplicate parameter error
            # Debug: log what's in kwargs
            logger.info(f"_validate_request action: {action}")
            logger.info(f"_validate_request kwargs keys: {list(kwargs.keys())}")
            logger.info(f"_validate_request task_id param: {task_id}")
            logger.info(f"_validate_request 'task_id' in kwargs: {'task_id' in kwargs}")
            
            # Filter out task_id from kwargs if it somehow still exists
            filtered_validation_kwargs = {k: v for k, v in kwargs.items() if k != 'task_id'}
            logger.info(f"_validate_request filtered_validation_kwargs keys: {list(filtered_validation_kwargs.keys())}")
            
            return self._validation_factory.validate_update_request(
                task_id=task_id,
                **filtered_validation_kwargs
            )
        elif action in ["list", "search"]:
            return self._validation_factory.validate_search_request(
                operation=action,
                **kwargs
            )
        elif action == "delete":
            return self._validation_factory.validate_deletion_request(
                task_id=task_id
            )
        elif action == "get":
            # For get action, only task_id is required
            if not task_id:
                return False, self._response_formatter.create_error_response(
                    operation="get",
                    error="task_id is required",
                    error_code="VALIDATION_ERROR"
                )
            return True, None
        elif action in ["add_dependency", "remove_dependency"]:
            # For dependency actions, validate task_id and dependency_id
            if not task_id:
                return False, self._response_formatter.create_error_response(
                    operation=action,
                    error="task_id is required for dependency operations",
                    error_code="VALIDATION_ERROR"
                )
            if not kwargs.get('dependency_id'):
                return False, self._response_formatter.create_error_response(
                    operation=action,
                    error="dependency_id is required for dependency operations",
                    error_code="VALIDATION_ERROR"
                )
            return True, None
        else:
            # For other actions, basic validation
            return True, None

    def _check_task_permissions(self, action: str, user_id: str, task_id: Optional[str] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if user has required permissions for task operations.
        
        Args:
            action: The action being performed (create, read, update, delete, etc.)
            user_id: The authenticated user ID
            task_id: Optional task ID for task-specific operations
            
        Returns:
            Tuple of (success: bool, error_response: Optional[Dict])
        """
        try:
            # Map action to permission
            action_to_permission = {
                'create': PermissionAction.CREATE,
                'get': PermissionAction.READ,
                'list': PermissionAction.READ,
                'search': PermissionAction.READ,
                'update': PermissionAction.UPDATE,
                'complete': PermissionAction.UPDATE,  # Completing is an update operation
                'delete': PermissionAction.DELETE,
                'next': PermissionAction.READ,  # Getting next task is read access
                'add_dependency': PermissionAction.UPDATE,  # Adding dependency is update
                'remove_dependency': PermissionAction.UPDATE,  # Removing dependency is update
            }
            
            required_permission = action_to_permission.get(action)
            if not required_permission:
                # Unknown action - allow by default (backwards compatibility)
                logger.warning(f"Unknown task action '{action}' - allowing by default")
                return True, None
            
            # Get user context and token for permission checking
            try:
                # Import here to avoid circular imports
                from .....auth.middleware.request_context_middleware import get_current_request_context
                request_context = get_current_request_context()
                
                if not request_context or not hasattr(request_context, 'user') or not request_context.user:
                    logger.error(f"No user context found for permission check - user_id: {user_id}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error="Authentication context not available for permission check",
                        error_code="AUTHENTICATION_ERROR"
                    )
                
                # Get token payload from user context
                user = request_context.user
                token_payload = getattr(user, 'token', {})
                if not token_payload:
                    logger.error(f"No token payload found for user {user_id}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error="No token payload found for permission validation",
                        error_code="AUTHENTICATION_ERROR"
                    )
                
                # Check permissions using PermissionChecker
                checker = PermissionChecker(token_payload)
                has_permission = checker.has_permission(ResourceType.TASKS, required_permission)
                
                if not has_permission:
                    logger.warning(f"User {user_id} lacks permission for tasks:{required_permission.value}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error=f"Permission denied: requires tasks:{required_permission.value}",
                        error_code="PERMISSION_DENIED"
                    )
                
                logger.debug(f"User {user_id} has permission for tasks:{required_permission.value}")
                return True, None
                
            except ImportError:
                # Fallback: If request context middleware is not available, allow operation
                # This ensures backwards compatibility
                logger.warning(f"Request context middleware not available - allowing task {action} for user {user_id}")
                return True, None
                
        except Exception as e:
            logger.error(f"Error checking task permissions for user {user_id}, action {action}: {e}")
            # On error, allow the operation to proceed (fail-open for now)
            # In production, you might want to fail-closed (deny access on errors)
            return True, None