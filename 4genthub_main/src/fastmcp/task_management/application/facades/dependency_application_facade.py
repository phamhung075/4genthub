"""Dependency Application Facade

Handles dependency-related application boundary concerns, orchestrating dependency use cases and response formatting.
"""

import logging
from typing import Dict, Any

from ..dtos.dependency.add_dependency_request import AddDependencyRequest
from ..services.dependencie_application_service import DependencieApplicationService
from ...domain.repositories.task_repository import TaskRepository
from ...domain.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)

class DependencyApplicationFacade:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
        self._dependency_app_service = DependencieApplicationService(task_repository)

    def manage_dependencies(self, action: str, task_id: str, dependency_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Manage task dependencies"""
        try:
            if not task_id or not task_id.strip():
                raise ValueError("Task ID is required for dependency operations")
            if action == "add_dependency":
                if not dependency_data or "dependency_id" not in dependency_data:
                    raise ValueError("dependency_data with dependency_id is required")
                request = AddDependencyRequest(task_id=task_id, depends_on_task_id=dependency_data["dependency_id"])
                response = self._dependency_app_service.add_dependency(request)
                return {
                    "success": response.success,
                    "action": "add_dependency",
                    "task_id": response.task_id,
                    "dependencies": response.dependencies,
                    "message": response.message
                }
            elif action == "remove_dependency":
                if not dependency_data or "dependency_id" not in dependency_data:
                    raise ValueError("dependency_data with dependency_id is required")
                response = self._dependency_app_service.remove_dependency(task_id, dependency_data["dependency_id"])
                return {
                    "success": response.success,
                    "action": "remove_dependency",
                    "task_id": response.task_id,
                    "dependencies": response.dependencies,
                    "message": response.message
                }
            elif action == "get_dependencies":
                response = self._dependency_app_service.get_dependencies(task_id)
                return {"success": True, "action": "get_dependencies", **response}
            elif action == "clear_dependencies":
                response = self._dependency_app_service.clear_dependencies(task_id)
                return {
                    "success": response.success,
                    "action": "clear_dependencies",
                    "task_id": response.task_id,
                    "dependencies": response.dependencies,
                    "message": response.message
                }
            elif action == "get_blocking_tasks":
                response = self._dependency_app_service.get_blocking_tasks(task_id)
                return {"success": True, "action": "get_blocking_tasks", **response}
            else:
                return {"success": False, "error": f"Unknown dependency action: {action}"}
        except TaskNotFoundError as e:
            return {"success": False, "error": str(e)}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in manage_dependencies: {e}")
            return {"success": False, "error": f"Dependency operation failed: {str(e)}"} 