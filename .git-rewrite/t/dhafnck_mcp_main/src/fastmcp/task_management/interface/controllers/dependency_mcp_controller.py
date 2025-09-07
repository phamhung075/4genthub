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

from .desc import description_loader
from ...application.facades.task_application_facade import TaskApplicationFacade

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
    def __init__(self, task_facade: TaskApplicationFacade):
        self._task_facade = task_facade
        logger.info("DependencyMCPController initialized")

    def register_tools(self, mcp: "FastMCP"):
        descriptions = self._get_dependency_management_descriptions()
        manage_dependency_desc = descriptions["manage_dependency"]

        @mcp.tool(description=manage_dependency_desc["description"])
        def manage_dependency(
            action: Annotated[str, Field(description=manage_dependency_desc["parameters"].get("action", "Dependency management action"))],
            task_id: Annotated[str, Field(description=manage_dependency_desc["parameters"].get("task_id", "Task identifier"))],
            project_id: Annotated[str, Field(description=manage_dependency_desc["parameters"].get("project_id", "Project identifier"))] = "default_project",
            git_branch_name: Annotated[str, Field(description=manage_dependency_desc["parameters"].get("git_branch_name", "Task tree identifier"))] = "main",
            user_id: Annotated[Optional[str], Field(description=manage_dependency_desc["parameters"].get("user_id", "User identifier"))] = None,
            dependency_data: Annotated[Optional[Dict[str, Any]], Field(description=manage_dependency_desc["parameters"].get("dependency_data", "Dependency data"))] = None
        ) -> Dict[str, Any]:
            return self.handle_dependency_operations(
                action=action,
                task_id=task_id,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id,
                dependency_data=dependency_data
            )

    def _get_dependency_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten dependency descriptions for robust access, similar to other controllers.
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for 'manage_dependency' in any subdict (e.g., all_desc['task']['manage_dependency'])
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_dependency" in sub:
                flat["manage_dependency"] = sub["manage_dependency"]
        return flat

    def handle_dependency_operations(self, action: str, task_id: str, 
                                     project_id: str = "default_project", 
                                     git_branch_name: str = "main", 
                                     user_id: Optional[str] = None, 
                                     dependency_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if not task_id:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "error_code": "MISSING_FIELD",
                    "field": "task_id",
                    "expected": "A valid task_id string",
                    "hint": "Include 'task_id' in your request body"
                }
            if action == "add_dependency":
                if not dependency_data or "dependency_id" not in dependency_data:
                    return {
                        "success": False,
                        "error": "Missing required field: dependency_id in dependency_data",
                        "error_code": "MISSING_FIELD",
                        "field": "dependency_data.dependency_id",
                        "expected": "A valid dependency_id string inside dependency_data",
                        "hint": "Include 'dependency_data': {'dependency_id': ...} in your request body"
                    }
                return self._task_facade.add_dependency(task_id, dependency_data["dependency_id"])
            elif action == "remove_dependency":
                if not dependency_data or "dependency_id" not in dependency_data:
                    return {
                        "success": False,
                        "error": "Missing required field: dependency_id in dependency_data",
                        "error_code": "MISSING_FIELD",
                        "field": "dependency_data.dependency_id",
                        "expected": "A valid dependency_id string inside dependency_data",
                        "hint": "Include 'dependency_data': {'dependency_id': ...} in your request body"
                    }
                return self._task_facade.remove_dependency(task_id, dependency_data["dependency_id"])
            elif action == "get_dependencies":
                return self._task_facade.get_dependencies(task_id)
            elif action == "clear_dependencies":
                return self._task_facade.clear_dependencies(task_id)
            elif action == "get_blocking_tasks":
                return self._task_facade.get_blocking_tasks(task_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown dependency action: {action}",
                    "error_code": "UNKNOWN_ACTION",
                    "field": "action",
                    "expected": "One of: add_dependency, remove_dependency, get_dependencies, clear_dependencies, get_blocking_tasks",
                    "hint": "Check the 'action' parameter for typos"
                }
        except Exception as e:
            logger.error(f"Error in dependency operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Dependency operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            } 