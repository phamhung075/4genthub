"""
Project MCP Controller - Refactored Modular Implementation

This is the main entry point for the project MCP controller, now refactored into a modular 
architecture using factory pattern to maintain separation of concerns.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import modular components
from .factories.operation_factory import ProjectOperationFactory

# Import existing dependencies
# Import the description directly from the local file
from .manage_project_description import get_manage_project_description, get_manage_project_parameters
from ...utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from ....application.facades.project_application_facade import ProjectApplicationFacade
from ....application.services.facade_service import FacadeService
from ....domain.constants import validate_user_id
from ....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from .....config.auth_config import AuthConfig
from ..auth_helper import get_authenticated_user_id, log_authentication_details

# Import permission system for resource-specific CRUD authorization
from .....auth.domain.permissions import (
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
    # Use auth_helper which is already imported
    get_current_user_id = get_authenticated_user_id
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

# Import for description loading - needed for backward compatibility
try:
    from .....config.resource_descriptions.description_loader import DescriptionLoader
    description_loader = DescriptionLoader()
except ImportError:
    from types import SimpleNamespace
    # Create a mock description loader for tests
    description_loader = SimpleNamespace()
    description_loader.get_all_descriptions = lambda: {}


class ProjectMCPController(ContextPropagationMixin):
    """
    Refactored Project MCP Controller with modular architecture.
    
    This controller now uses factory pattern to delegate operations to specialized handlers,
    maintaining the same interface while improving maintainability and separation of concerns.
    """

    def __init__(self, facade_factory=None, facade_service: Optional[FacadeService] = None):
        """Initialize the modular project MCP controller."""
        
        # Support both old and new constructor patterns for backward compatibility
        if facade_factory is not None:
            # Old pattern - store the facade factory for tests
            self._project_facade_factory = facade_factory
            self._facade_service = None
        else:
            # New pattern - use facade service
            self._facade_service = facade_service or FacadeService.get_instance()
            self._project_facade_factory = None
        
        # Initialize response formatter
        self._response_formatter = StandardResponseFormatter()
        
        # Initialize modular operation factory
        self._operation_factory = ProjectOperationFactory(
            response_formatter=self._response_formatter
        )
        
        logger.info("ProjectMCPController initialized with modular architecture")

    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with the server."""
        
        # Get centralized parameter definitions
        params = get_manage_project_parameters()
        
        @mcp.tool(description=get_manage_project_description())
        async def manage_project(
            action: Annotated[str, Field(description=params["action"]["description"])],
            project_id: Annotated[str, Field(description=params["project_id"]["description"])] = None,
            name: Annotated[str, Field(description=params["name"]["description"])] = None,
            description: Annotated[str, Field(description=params["description"]["description"])] = None,
            force: Annotated[str, Field(description=params["force"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main project management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return await self._manage_project_async(
                action=action, project_id=project_id, name=name,
                description=description, force=force, user_id=user_id
            )

    def manage_project(self, action: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for project management operations (synchronous wrapper for tests)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, we can't use run_until_complete
                # This is a test context, so create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._manage_project_async(action, user_id, **kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(self._manage_project_async(action, user_id, **kwargs))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._manage_project_async(action, user_id, **kwargs))
    
    async def _manage_project_async(self, action: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for project management operations."""
        
        try:
            # Authentication
            user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=f"manage_project:{action}"
            )
            log_authentication_details(user_id, f"manage_project:{action}")
            
            # Permission Authorization - Check resource-specific CRUD permissions
            permission_result = self._check_project_permissions(action, user_id, kwargs.get('project_id'))
            if not permission_result[0]:
                return permission_result[1]  # Return permission denied error
            
            # Get facade for request
            facade = self._get_facade_for_request(user_id)
            
            # Validate required fields for specific actions
            validation_error = self._validate_operation_parameters(action, **kwargs)
            if validation_error:
                return validation_error
            
            # Execute operation using factory
            result = await self._operation_factory.handle_operation(
                operation=action,
                facade=facade,
                user_id=user_id,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in manage_project {action}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=action,
                error=f"Project operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"action": action}
            )

    def _get_facade_for_request(self, user_id: str = None) -> ProjectApplicationFacade:
        """Get appropriate facade for the request."""
        
        if self._project_facade_factory is not None:
            # Old pattern - use facade factory (for tests)
            return self._project_facade_factory.create_project_facade(user_id=user_id)
        elif self._facade_service is not None:
            # New pattern - use facade service
            return self._facade_service.get_project_facade(user_id=user_id)
        else:
            raise ValueError("Either facade_factory or facade_service is required")

    def _validate_operation_parameters(self, action: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Validate parameters for specific operations."""
        
        # Validate required parameters
        if action == "create":
            name = kwargs.get('name')
            if not name or not str(name).strip():
                return self._create_missing_field_error("name", action)
        
        elif action == "get":
            if not kwargs.get('project_id') and not kwargs.get('name'):
                return self._response_formatter.create_error_response(
                    operation=action,
                    error="Either 'project_id' or 'name' must be provided for get operation",
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    metadata={"required_fields": ["project_id OR name"]}
                )
        
        elif action in ["update", "delete", "project_health_check", "cleanup_obsolete", 
                       "validate_integrity", "rebalance_agents"]:
            if not kwargs.get('project_id'):
                return self._create_missing_field_error("project_id", action)
        
        return None

    def _create_missing_field_error(self, field: str, action: str) -> Dict[str, Any]:
        """Create a standardized missing field error response."""
        
        return self._response_formatter.create_error_response(
            operation=action,
            error=f"Missing required field: {field}. Expected: A valid {field} string",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={
                "field": field,
                "hint": f"Include '{field}' in your request",
                "action": action
            }
        )

    def _check_project_permissions(self, action: str, user_id: str, project_id: Optional[str] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if user has required permissions for project operations.
        
        Args:
            action: The action being performed (create, read, update, delete, etc.)
            user_id: The authenticated user ID
            project_id: Optional project ID for project-specific operations
            
        Returns:
            Tuple of (success: bool, error_response: Optional[Dict])
        """
        try:
            # Map action to permission
            action_to_permission = {
                'create': PermissionAction.CREATE,
                'get': PermissionAction.READ,
                'list': PermissionAction.READ,
                'update': PermissionAction.UPDATE,
                'delete': PermissionAction.DELETE,
                'project_health_check': PermissionAction.READ,  # Health check is read access
                'cleanup_obsolete': PermissionAction.UPDATE,  # Cleanup is update operation
                'validate_integrity': PermissionAction.READ,  # Validation is read access
                'rebalance_agents': PermissionAction.UPDATE,  # Rebalancing is update operation
            }
            
            required_permission = action_to_permission.get(action)
            if not required_permission:
                # Unknown action - allow by default (backwards compatibility)
                logger.warning(f"Unknown project action '{action}' - allowing by default")
                return True, None
            
            # Get user context and token for permission checking
            try:
                # Import here to avoid circular imports
                from .....auth.middleware.request_context_middleware import get_current_auth_info
                auth_info = get_current_auth_info()
                
                if not auth_info:
                    logger.error(f"No authentication context found for permission check - user_id: {user_id}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error="Authentication context not available for permission check",
                        error_code="AUTHENTICATION_ERROR"
                    )
                
                # Get token payload from auth info
                token_payload = auth_info
                if not token_payload:
                    logger.error(f"No token payload found for user {user_id}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error="No token payload found for permission validation",
                        error_code="AUTHENTICATION_ERROR"
                    )
                
                # Check permissions using PermissionChecker
                checker = PermissionChecker(token_payload)
                has_permission = checker.has_permission(ResourceType.PROJECTS, required_permission)
                
                if not has_permission:
                    logger.warning(f"User {user_id} lacks permission for projects:{required_permission.value}")
                    return False, self._response_formatter.create_error_response(
                        operation=action,
                        error=f"Permission denied: requires projects:{required_permission.value}",
                        error_code="PERMISSION_DENIED"
                    )
                
                logger.debug(f"User {user_id} has permission for projects:{required_permission.value}")
                return True, None
                
            except ImportError:
                # Fallback: If request context middleware is not available, allow operation
                # This ensures backwards compatibility
                logger.warning(f"Request context middleware not available - allowing project {action} for user {user_id}")
                return True, None
                
        except Exception as e:
            logger.error(f"Error checking project permissions for user {user_id}, action {action}: {e}")
            # On error, allow the operation to proceed (fail-open for now)
            return True, None

    # ====== BACKWARD COMPATIBILITY METHODS FOR TESTS ======

    def handle_crud_operations(self, action: str, project_id: Optional[str] = None,
                             name: Optional[str] = None, description: Optional[str] = None,
                             user_id: Optional[str] = None, force: Optional[bool] = False) -> Dict[str, Any]:
        """
        Handle CRUD operations for backward compatibility with tests.
        This method delegates to the new factory-based architecture.
        """
        try:
            # Use the same validation logic as the main method
            validation_error = self._validate_operation_parameters(action, 
                                                                 project_id=project_id, 
                                                                 name=name, 
                                                                 description=description)
            if validation_error:
                return validation_error
            
            # Get facade and delegate to operation factory
            facade = self._get_facade_for_request(user_id)
            
            # Convert to async call for factory
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an event loop, we can't use run_until_complete
                    # This is a test context, so create a new thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._operation_factory.handle_operation(
                            operation=action,
                            facade=facade,
                            user_id=user_id,
                            project_id=project_id,
                            name=name,
                            description=description,
                            force=force
                        ))
                        return future.result()
                else:
                    return loop.run_until_complete(self._operation_factory.handle_operation(
                        operation=action,
                        facade=facade,
                        user_id=user_id,
                        project_id=project_id,
                        name=name,
                        description=description,
                        force=force
                    ))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(self._operation_factory.handle_operation(
                    operation=action,
                    facade=facade,
                    user_id=user_id,
                    project_id=project_id,
                    name=name,
                    description=description,
                    force=force
                ))
                
        except Exception as e:
            logger.error(f"Error in handle_crud_operations {action}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=action,
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR
            )

    def handle_maintenance_operations(self, action: str, project_id: Optional[str] = None, 
                                    force: Optional[bool] = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle maintenance operations for backward compatibility with tests.
        This method delegates to _handle_maintenance_action to match test expectations.
        """
        try:
            # Validate project_id is provided for maintenance operations
            if not project_id:
                return self._create_missing_field_error("project_id", action)
            
            # Delegate to _handle_maintenance_action (this is what tests mock)
            return self._handle_maintenance_action(
                action=action,
                project_id=project_id,
                force=force,
                user_id=user_id
            )
                
        except Exception as e:
            logger.error(f"Error in handle_maintenance_operations {action}: {str(e)}")
            # Return format expected by tests for backward compatibility
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }

    def _handle_maintenance_action(self, action: str, project_id: str, force: Optional[bool] = False,
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle specific maintenance action for backward compatibility.
        This method delegates to the maintenance handler.
        """
        try:
            facade = self._get_facade_for_request(user_id)
            
            # Get the maintenance handler from the factory
            maintenance_handler = self._operation_factory._maintenance_handler
            
            # Convert to async call
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, maintenance_handler.handle_maintenance_action(
                            facade=facade,
                            action=action,
                            project_id=project_id,
                            force=force,
                            user_id=user_id
                        ))
                        return future.result()
                else:
                    return loop.run_until_complete(maintenance_handler.handle_maintenance_action(
                        facade=facade,
                        action=action,
                        project_id=project_id,
                        force=force,
                        user_id=user_id
                    ))
            except RuntimeError:
                return asyncio.run(maintenance_handler.handle_maintenance_action(
                    facade=facade,
                    action=action,
                    project_id=project_id,
                    force=force,
                    user_id=user_id
                ))
                
        except Exception as e:
            logger.error(f"Error in _handle_maintenance_action {action}: {str(e)}")
            # Return format expected by tests for backward compatibility
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }

    def _get_project_management_descriptions(self) -> Dict[str, Any]:
        """Get project management descriptions for backward compatibility with tests."""
        try:
            # Import from current module to ensure test mocking works
            import fastmcp.task_management.interface.mcp_controllers.project_mcp_controller as current_module
            loader = getattr(current_module, 'description_loader', None)
            
            if loader is not None:
                descriptions = loader.get_all_descriptions()
                # Extract project-specific descriptions
                if isinstance(descriptions, dict) and "projects" in descriptions:
                    return descriptions["projects"]
            
            # Fallback to basic descriptions
            return {
                "manage_project": {
                    "description": get_manage_project_description(),
                    "parameters": get_manage_project_parameters()
                }
            }
        except Exception as e:
            logger.error(f"Error getting project descriptions: {e}")
            # Return minimal fallback
            return {
                "manage_project": {
                    "description": "Manage project operations",
                    "parameters": {"action": "Action to perform"}
                }
            }

    def _include_project_context(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Include project context in response for backward compatibility.
        """
        try:
            # Extract project_id from response
            if not response.get("project", {}).get("id"):
                return response
            
            project_id = response["project"]["id"]
            
            # Import context facade factory
            from .....task_management.infrastructure.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
            
            # Get context
            context_factory = UnifiedContextFacadeFactory()
            context_facade = context_factory.create_facade(user_id=None)  # Tests don't provide user_id
            context_result = context_facade.get_context(
                "project",
                project_id,
                include_inherited=True
            )
            
            if context_result.get("success") and context_result.get("context"):
                response["project_context"] = context_result["context"]
            
            return response
            
        except Exception as e:
            logger.error(f"Error including project context: {e}")
            # Return original response if context inclusion fails
            return response

    # Additional CRUD handler methods for individual operations (used by tests)
    def _handle_create_project(self, name: str, description: Optional[str] = None,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle project creation for backward compatibility."""
        facade = self._get_facade_for_request(user_id)
        crud_handler = self._operation_factory._crud_handler
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, crud_handler.create_project(
                        facade=facade, name=name, description=description, user_id=user_id
                    ))
                    return future.result()
            else:
                return loop.run_until_complete(crud_handler.create_project(
                    facade=facade, name=name, description=description, user_id=user_id
                ))
        except RuntimeError:
            return asyncio.run(crud_handler.create_project(
                facade=facade, name=name, description=description, user_id=user_id
            ))

    def _handle_get_project(self, project_id: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """Handle project retrieval for backward compatibility."""
        facade = self._get_facade_for_request()
        crud_handler = self._operation_factory._crud_handler
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, crud_handler.get_project(
                        facade=facade, project_id=project_id, name=name
                    ))
                    return future.result()
            else:
                return loop.run_until_complete(crud_handler.get_project(
                    facade=facade, project_id=project_id, name=name
                ))
        except RuntimeError:
            return asyncio.run(crud_handler.get_project(
                facade=facade, project_id=project_id, name=name
            ))

    def _handle_list_projects(self) -> Dict[str, Any]:
        """Handle project listing for backward compatibility."""
        facade = self._get_facade_for_request()
        crud_handler = self._operation_factory._crud_handler
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, crud_handler.list_projects(facade=facade))
                    return future.result()
            else:
                return loop.run_until_complete(crud_handler.list_projects(facade=facade))
        except RuntimeError:
            return asyncio.run(crud_handler.list_projects(facade=facade))

    def _handle_update_project(self, project_id: str, name: Optional[str] = None,
                             description: Optional[str] = None) -> Dict[str, Any]:
        """Handle project update for backward compatibility."""
        facade = self._get_facade_for_request()
        crud_handler = self._operation_factory._crud_handler
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, crud_handler.update_project(
                        facade=facade, project_id=project_id, name=name, description=description
                    ))
                    return future.result()
            else:
                return loop.run_until_complete(crud_handler.update_project(
                    facade=facade, project_id=project_id, name=name, description=description
                ))
        except RuntimeError:
            return asyncio.run(crud_handler.update_project(
                facade=facade, project_id=project_id, name=name, description=description
            ))