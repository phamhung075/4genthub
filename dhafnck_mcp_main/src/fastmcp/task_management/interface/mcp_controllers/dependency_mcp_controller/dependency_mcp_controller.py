"""Dependency MCP Controller

This controller handles MCP protocol concerns for dependency operations.
It converts between MCP request formats and application DTOs, then
delegates all business logic to the TaskApplicationFacade.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP
    from ....application.facades.task_application_facade import TaskApplicationFacade

from .handlers import DependencyOperationHandler
from .services import DescriptionService
from .manage_dependency_description import get_manage_dependency_description, get_manage_dependency_parameters

logger = logging.getLogger(__name__)


class DependencyMCPController:
    """
    MCP controller for dependency operations.
    Handles MCP protocol concerns for dependencies:
    - Converting MCP parameters to application DTOs
    - Delegating to application facade
    - Converting responses back to MCP format
    - Handling protocol-specific errors
    """
    def __init__(self, task_facade: "TaskApplicationFacade"):
        self._handler = DependencyOperationHandler(task_facade)
        self._description_service = DescriptionService()
        logger.info("DependencyMCPController initialized")

    def register_tools(self, mcp: "FastMCP"):
        
        # Get centralized parameter definitions
        params = get_manage_dependency_parameters()

        @mcp.tool(description=get_manage_dependency_description())
        def manage_dependency(
            action: Annotated[str, Field(description=params["action"]["description"])],
            task_id: Annotated[str, Field(description=params["task_id"]["description"])] = None,
            project_id: Annotated[str, Field(description=params["project_id"]["description"])] = None,
            git_branch_name: Annotated[str, Field(description=params["git_branch_name"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None,
            dependency_data: Annotated[str, Field(description=params["dependency_data"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main dependency management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.handle_dependency_operations(
                action=action,
                task_id=task_id,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id,
                dependency_data=dependency_data
            )

    def handle_dependency_operations(self, action: str, task_id: Optional[str] = None, 
                                     project_id: Optional[str] = None, 
                                     git_branch_name: Optional[str] = None, 
                                     user_id: Optional[str] = None, 
                                     dependency_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle dependency operations with parameter coercion and validation.
        
        Args:
            action: The dependency action to perform
            task_id: The task ID (optional, but required for most actions)
            project_id: The project ID (optional, defaults to 'default_project')
            git_branch_name: The git branch name (optional, defaults to 'main')
            user_id: The user ID (required for multi-tenancy)
            dependency_data: Additional dependency data as JSON string (optional)
            
        Returns:
            Operation result dictionary
        """
        try:
            # Import parameter coercion utility
            from ...utils.parameter_validation_fix import coerce_parameter_types
            
            # Coerce string parameters to proper types
            coerced_params = coerce_parameter_types({
                "task_id": task_id,
                "project_id": project_id,
                "git_branch_name": git_branch_name,
                "user_id": user_id,
                "dependency_data": dependency_data
            })
            
            # Apply coerced values with defaults
            task_id = coerced_params.get("task_id", task_id)
            project_id = coerced_params.get("project_id", project_id)
            if not project_id:
                raise ValueError("project_id is required but was not provided")
            git_branch_name = coerced_params.get("git_branch_name", git_branch_name) or "main"
            user_id = coerced_params.get("user_id", user_id)
            dependency_data = coerced_params.get("dependency_data", dependency_data)
            
            # Parse dependency_data if it's a JSON string
            if isinstance(dependency_data, str) and dependency_data.strip():
                try:
                    import json
                    dependency_data = json.loads(dependency_data)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Invalid JSON in dependency_data parameter: {str(e)}",
                        "error_code": "INVALID_JSON",
                        "field": "dependency_data",
                        "hint": "Ensure dependency_data parameter contains valid JSON"
                    }
            
            return self._handler.handle_operation(
                action=action,
                task_id=task_id,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id,
                dependency_data=dependency_data
            )
            
        except Exception as e:
            logger.error(f"Error in dependency operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Dependency operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }