"""Dependency Operation Handler"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DependencyOperationHandler:
    """Handler for all dependency operations"""
    
    def __init__(self, task_facade):
        self._task_facade = task_facade
        logger.info("DependencyOperationHandler initialized")
    
    def handle_operation(self, action: str, task_id: str, 
                        project_id: Optional[str] = None, 
                        git_branch_name: str = "main", 
                        user_id: Optional[str] = None, 
                        dependency_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle dependency operations based on action type.
        
        Args:
            action: The dependency action to perform
            task_id: The task ID
            project_id: The project ID
            git_branch_name: The git branch name
            user_id: The user ID
            dependency_data: Additional dependency data
            
        Returns:
            Operation result dictionary
        """
        try:
            if not task_id:
                return self._missing_field_error("task_id", "A valid task_id string")
            
            # Note: project_id is optional here as task already has project context
            # The facade will determine project context from the task itself
            
            if action == "add_dependency":
                return self._handle_add_dependency(task_id, dependency_data)
            elif action == "remove_dependency":
                return self._handle_remove_dependency(task_id, dependency_data)
            elif action == "get_dependencies":
                return self._task_facade.get_dependencies(task_id)
            elif action == "clear_dependencies":
                return self._task_facade.clear_dependencies(task_id)
            elif action == "get_blocking_tasks":
                return self._task_facade.get_blocking_tasks(task_id)
            else:
                return self._unknown_action_error(action)
                
        except Exception as e:
            logger.error(f"Error in dependency operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Dependency operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def _handle_add_dependency(self, task_id: str, dependency_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle add dependency operation"""
        if not dependency_data or "dependency_id" not in dependency_data:
            return self._missing_dependency_id_error()
        return self._task_facade.add_dependency(task_id, dependency_data["dependency_id"])
    
    def _handle_remove_dependency(self, task_id: str, dependency_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle remove dependency operation"""
        if not dependency_data or "dependency_id" not in dependency_data:
            return self._missing_dependency_id_error()
        return self._task_facade.remove_dependency(task_id, dependency_data["dependency_id"])
    
    def _missing_field_error(self, field: str, expected: str) -> Dict[str, Any]:
        """Generate missing field error response"""
        return {
            "success": False,
            "error": f"Missing required field: {field}",
            "error_code": "MISSING_FIELD",
            "field": field,
            "expected": expected,
            "hint": f"Include '{field}' in your request body"
        }
    
    def _missing_dependency_id_error(self) -> Dict[str, Any]:
        """Generate missing dependency_id error response"""
        return {
            "success": False,
            "error": "Missing required field: dependency_id in dependency_data",
            "error_code": "MISSING_FIELD",
            "field": "dependency_data.dependency_id",
            "expected": "A valid dependency_id string inside dependency_data",
            "hint": "Include 'dependency_data': {'dependency_id': ...} in your request body"
        }
    
    def _unknown_action_error(self, action: str) -> Dict[str, Any]:
        """Generate unknown action error response"""
        return {
            "success": False,
            "error": f"Unknown dependency action: {action}",
            "error_code": "UNKNOWN_ACTION",
            "field": "action",
            "expected": "One of: add_dependency, remove_dependency, get_dependencies, clear_dependencies, get_blocking_tasks",
            "hint": "Check the 'action' parameter for typos"
        }