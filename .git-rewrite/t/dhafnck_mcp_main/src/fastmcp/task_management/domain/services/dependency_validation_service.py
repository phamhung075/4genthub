"""Dependency Chain Validation Service"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone

from ..entities.task import Task
from ..value_objects.task_id import TaskId
from ..repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class DependencyValidationService:
    """Service for validating dependency chains and detecting issues"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
    
    def validate_dependency_chain(self, task_id: TaskId) -> Dict[str, Any]:
        """
        Validate the entire dependency chain for a task.
        
        Args:
            task_id: The task to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            task = self._task_repository.find_by_id(task_id)
            if not task:
                return {
                    "valid": False,
                    "errors": [f"Task {task_id} not found"],
                    "issues": []
                }
            
            # Get all tasks for dependency resolution
            all_tasks = self._task_repository.find_all()
            task_map = {str(t.id): t for t in all_tasks}
            
            issues = []
            errors = []
            
            # Check if task has dependencies
            dependency_ids = []
            if hasattr(task, 'get_dependency_ids'):
                dependency_ids = task.get_dependency_ids()
            
            if not dependency_ids:
                return {
                    "valid": True,
                    "message": "Task has no dependencies",
                    "issues": [],
                    "errors": []
                }
            
            # Validate each dependency
            for dep_id in dependency_ids:
                dep_issues = self._validate_single_dependency(task, dep_id, task_map)
                issues.extend(dep_issues)
            
            # Check for circular dependencies
            circular_deps = self._check_circular_dependencies(task, all_tasks)
            if circular_deps:
                errors.append(f"Circular dependency detected: {' -> '.join(circular_deps)}")
            
            # Check for orphaned dependencies
            orphaned_deps = self._check_orphaned_dependencies(task, task_map)
            if orphaned_deps:
                errors.extend([f"Dependency {dep_id} no longer exists" for dep_id in orphaned_deps])
            
            # Overall validation result
            is_valid = len(errors) == 0
            
            return {
                "valid": is_valid,
                "task_id": str(task_id),
                "dependency_count": len(dependency_ids),
                "issues": issues,
                "errors": errors,
                "can_proceed": self._can_task_proceed(task, task_map),
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating dependency chain for {task_id}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "issues": []
            }
    
    def _validate_single_dependency(self, task: Task, dependency_id: str, task_map: Dict[str, Task]) -> List[Dict[str, Any]]:
        """
        Validate a single dependency relationship.
        
        Args:
            task: The dependent task
            dependency_id: ID of the dependency task
            task_map: Map of task ID to task objects
            
        Returns:
            List of issues found with this dependency
        """
        issues = []
        
        # Check if dependency task exists
        dep_task = task_map.get(dependency_id)
        if not dep_task:
            # Try enhanced lookup for completed/archived tasks
            dep_task = self._find_dependency_across_states(dependency_id)
            
        if not dep_task:
            issues.append({
                "type": "missing_dependency",
                "dependency_id": dependency_id,
                "severity": "error",
                "message": f"Dependency task {dependency_id} not found in any state",
                "suggestion": "Remove this dependency or check if the task ID is correct"
            })
            return issues
        
        # Check dependency status
        dep_status = dep_task.status.value if hasattr(dep_task.status, 'value') else str(dep_task.status)
        
        if dep_status == 'cancelled':
            issues.append({
                "type": "cancelled_dependency",
                "dependency_id": dependency_id,
                "dependency_title": dep_task.title,
                "severity": "warning",
                "message": f"Dependency '{dep_task.title}' was cancelled",
                "suggestion": "Consider removing this dependency or finding an alternative"
            })
        elif dep_status == 'blocked':
            issues.append({
                "type": "blocked_dependency",
                "dependency_id": dependency_id,
                "dependency_title": dep_task.title,
                "severity": "warning",
                "message": f"Dependency '{dep_task.title}' is currently blocked",
                "suggestion": "Resolve blockers in the dependency task first"
            })
        elif dep_status == 'done':
            issues.append({
                "type": "satisfied_dependency",
                "dependency_id": dependency_id,
                "dependency_title": dep_task.title,
                "severity": "info",
                "message": f"Dependency '{dep_task.title}' is completed",
                "suggestion": "Task can proceed with this dependency satisfied"
            })
        
        return issues
    
    def _find_dependency_across_states(self, dependency_id: str) -> Optional[Task]:
        """
        Find a dependency task across all states (active, completed, archived).
        
        Args:
            dependency_id: ID of the dependency task
            
        Returns:
            Task if found, None otherwise
        """
        # Try across contexts if the repository supports it
        if hasattr(self._task_repository, 'find_by_id_across_contexts'):
            try:
                task_id = TaskId.from_string(dependency_id)
                return self._task_repository.find_by_id_across_contexts(task_id)
            except Exception as e:
                logger.debug(f"Could not find task {dependency_id} across contexts: {e}")
        
        return None
    
    def _check_circular_dependencies(self, task: Task, all_tasks: List[Task]) -> Optional[List[str]]:
        """
        Check for circular dependencies in the task chain.
        
        Args:
            task: The task to check
            all_tasks: All tasks in the system
            
        Returns:
            List representing circular dependency path if found, None otherwise
        """
        try:
            visited = set()
            path = []
            task_map = {str(t.id): t for t in all_tasks}
            
            def dfs(current_task_id: str) -> Optional[List[str]]:
                if current_task_id in visited:
                    # Found a cycle - return the cycle path
                    cycle_start = path.index(current_task_id)
                    return path[cycle_start:] + [current_task_id]
                
                visited.add(current_task_id)
                path.append(current_task_id)
                
                # Get dependencies of current task
                current_task = task_map.get(current_task_id)
                if current_task and hasattr(current_task, 'get_dependency_ids'):
                    for dep_id in current_task.get_dependency_ids():
                        cycle = dfs(dep_id)
                        if cycle:
                            return cycle
                
                path.pop()
                return None
            
            return dfs(str(task.id))
            
        except Exception as e:
            logger.error(f"Error checking circular dependencies: {e}")
            return None
    
    def _check_orphaned_dependencies(self, task: Task, task_map: Dict[str, Task]) -> List[str]:
        """
        Check for dependencies that no longer exist.
        
        Args:
            task: The task to check
            task_map: Map of existing tasks
            
        Returns:
            List of orphaned dependency IDs
        """
        orphaned = []
        
        if hasattr(task, 'get_dependency_ids'):
            for dep_id in task.get_dependency_ids():
                if dep_id not in task_map:
                    # Check if it exists in completed/archived tasks
                    if not self._find_dependency_across_states(dep_id):
                        orphaned.append(dep_id)
        
        return orphaned
    
    def _can_task_proceed(self, task: Task, task_map: Dict[str, Task]) -> bool:
        """
        Check if a task can proceed based on its dependencies.
        
        Args:
            task: The task to check
            task_map: Map of existing tasks
            
        Returns:
            True if task can proceed, False otherwise
        """
        if not hasattr(task, 'get_dependency_ids'):
            return True
        
        dependency_ids = task.get_dependency_ids()
        if not dependency_ids:
            return True
        
        # Check each dependency
        for dep_id in dependency_ids:
            dep_task = task_map.get(dep_id)
            if not dep_task:
                # Try to find in completed/archived
                dep_task = self._find_dependency_across_states(dep_id)
            
            if not dep_task:
                return False  # Missing dependency blocks progress
            
            # Check if dependency is completed
            if hasattr(dep_task.status, 'is_done'):
                if not dep_task.status.is_done():
                    return False
            else:
                dep_status = dep_task.status.value if hasattr(dep_task.status, 'value') else str(dep_task.status)
                if dep_status != 'done':
                    return False
        
        return True
    
    def get_dependency_chain_status(self, task_id: TaskId) -> Dict[str, Any]:
        """
        Get detailed status of the entire dependency chain for a task.
        
        Args:
            task_id: The task to analyze
            
        Returns:
            Detailed dependency chain status
        """
        try:
            task = self._task_repository.find_by_id(task_id)
            if not task:
                return {"error": f"Task {task_id} not found"}
            
            all_tasks = self._task_repository.find_all()
            task_map = {str(t.id): t for t in all_tasks}
            
            dependency_chain = []
            if hasattr(task, 'get_dependency_ids'):
                for dep_id in task.get_dependency_ids():
                    dep_info = self._get_dependency_info(dep_id, task_map)
                    dependency_chain.append(dep_info)
            
            # Calculate chain statistics
            total_deps = len(dependency_chain)
            completed_deps = sum(1 for dep in dependency_chain if dep.get('status') == 'done')
            blocked_deps = sum(1 for dep in dependency_chain if dep.get('status') == 'blocked')
            
            return {
                "task_id": str(task_id),
                "task_title": task.title,
                "task_status": str(task.status),
                "dependency_chain": dependency_chain,
                "chain_statistics": {
                    "total_dependencies": total_deps,
                    "completed_dependencies": completed_deps,
                    "blocked_dependencies": blocked_deps,
                    "completion_percentage": (completed_deps / total_deps * 100) if total_deps > 0 else 100
                },
                "can_proceed": self._can_task_proceed(task, task_map),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dependency chain status for {task_id}: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def _get_dependency_info(self, dependency_id: str, task_map: Dict[str, Task]) -> Dict[str, Any]:
        """
        Get detailed information about a single dependency.
        
        Args:
            dependency_id: ID of the dependency
            task_map: Map of existing tasks
            
        Returns:
            Dictionary with dependency information
        """
        dep_task = task_map.get(dependency_id)
        if not dep_task:
            dep_task = self._find_dependency_across_states(dependency_id)
        
        if not dep_task:
            return {
                "dependency_id": dependency_id,
                "status": "missing",
                "title": "Unknown",
                "found": False,
                "message": "Dependency task not found"
            }
        
        dep_status = dep_task.status.value if hasattr(dep_task.status, 'value') else str(dep_task.status)
        
        return {
            "dependency_id": dependency_id,
            "title": dep_task.title,
            "status": dep_status,
            "found": True,
            "is_completed": dep_task.status.is_done() if hasattr(dep_task.status, 'is_done') else dep_status == 'done',
            "priority": str(dep_task.priority) if hasattr(dep_task, 'priority') else "unknown"
        }