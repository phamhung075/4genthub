"""Subtask Application Facade

Handles subtask-related application boundary concerns, orchestrating subtask use cases and response formatting.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from ..dtos.task import TaskResponse
from ..use_cases.get_task import GetTaskUseCase
from ...domain.repositories.task_repository import TaskRepository
from ...domain.exceptions import TaskNotFoundError
from ...domain.value_objects.task_id import TaskId
from ...domain.repositories.subtask_repository import SubtaskRepository
from ..use_cases.add_subtask import AddSubtaskUseCase, AddSubtaskRequest
from ..use_cases.update_subtask import UpdateSubtaskUseCase, UpdateSubtaskRequest
from ..use_cases.remove_subtask import RemoveSubtaskUseCase
from ..use_cases.get_subtask import GetSubtaskUseCase
from ..use_cases.get_subtasks import GetSubtasksUseCase
from ..use_cases.complete_subtask import CompleteSubtaskUseCase
from ...infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from ...infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory

logger = logging.getLogger(__name__)

class SubtaskApplicationFacade:
    """Facade for subtask-related operations"""
    
    def __init__(self, task_repository: TaskRepository = None, subtask_repository: SubtaskRepository = None, 
                 task_repository_factory: TaskRepositoryFactory = None, 
                 subtask_repository_factory: SubtaskRepositoryFactory = None):
        # For backward compatibility, keep the old constructor signature
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        
        # New factory-based approach
        self._task_repository_factory = task_repository_factory
        self._subtask_repository_factory = subtask_repository_factory
        
        # Initialize use cases only if static repositories are provided (backward compatibility)
        if task_repository:
            self._add_subtask_use_case = AddSubtaskUseCase(task_repository, subtask_repository)
            self._update_subtask_use_case = UpdateSubtaskUseCase(task_repository, subtask_repository)
            self._remove_subtask_use_case = RemoveSubtaskUseCase(task_repository, subtask_repository)
            self._get_subtask_use_case = GetSubtaskUseCase(task_repository, subtask_repository)
            self._get_subtasks_use_case = GetSubtasksUseCase(task_repository, subtask_repository)
            self._complete_subtask_use_case = CompleteSubtaskUseCase(task_repository, subtask_repository)
        else:
            # Use cases will be created dynamically with context-specific repositories
            self._add_subtask_use_case = None
            self._update_subtask_use_case = None
            self._remove_subtask_use_case = None
            self._get_subtask_use_case = None
            self._get_subtasks_use_case = None
            self._complete_subtask_use_case = None
    
    def _derive_context_from_task(self, task_id: str, subtask_id: str = None) -> Dict[str, str]:
        """Derive context parameters from the parent task by using system-level repository access"""
        try:
            # Use system-level repository access (no context restrictions) to find the task
            system_task_repository = self._task_repository_factory.create_system_repository() if self._task_repository_factory else None
            
            if system_task_repository:
                # Find the task without context restrictions
                logger.debug(f"Looking for task {task_id} with system repository")
                task = system_task_repository.find_by_id(TaskId.from_string(task_id))
                logger.debug(f"System repository found task: {task is not None}")
                if task and task.git_branch_id:
                    logger.debug(f"Task found with git_branch_id: {task.git_branch_id}")
                    # Derive context from task's git_branch_id by looking up the git branch and project
                    return self._derive_context_from_git_branch_id(task.git_branch_id)
                elif task:
                    logger.debug(f"Task found but no git_branch_id: {task}")
                else:
                    logger.debug("Task not found by system repository")
                    
        except Exception as e:
            logger.debug(f"Failed to find task {task_id} with system repository: {e}")
        
        # If task not found, return defaults
        logger.warning(f"Task {task_id} not found, using default context")
        # Validate user authentication
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        # Use auth_helper to get authenticated user ID (same as controllers)
        try:
            from ...interface.controllers.auth_helper import get_authenticated_user_id
            user_id = get_authenticated_user_id(None, "Subtask context derivation")
        except Exception as e:
            logger.error(f"Authentication failed for subtask context derivation: {e}")
            # No fallback allowed - authentication is required
            logger.error(f"Authentication required for subtask context derivation: {e}")
            raise e
        
        return {
            "project_id": "default_project",
            "git_branch_name": "main", 
            "user_id": user_id
        }
    
    def _derive_context_from_git_branch_id(self, git_branch_id: str) -> Dict[str, str]:
        """Derive context parameters from git_branch_id by looking up the project_git_branchs table"""
        try:
            # Use system-level database access to look up git branch and project
            from ...infrastructure.database.database_source_manager import get_database_path
            import sqlite3
            
            db_path = get_database_path()
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Look up the git branch in project_git_branchs to get project_id and git_branch_name
                branch_row = conn.execute(
                    'SELECT project_id, name FROM project_git_branchs WHERE id = ?',
                    (git_branch_id,)
                ).fetchone()
                
                if branch_row:
                    project_id = branch_row['project_id']
                    git_branch_name = branch_row['name']
                    
                    # Look up the project to get user_id
                    project_row = conn.execute(
                        'SELECT user_id FROM projects WHERE id = ?',
                        (project_id,)
                    ).fetchone()
                    
                    if project_row:
                        user_id = project_row['user_id']
                        logger.debug(f"Derived context from git_branch_id {git_branch_id}: {project_id}/{git_branch_name}/{user_id}")
                        return {
                            "project_id": project_id,
                            "git_branch_name": git_branch_name,
                            "user_id": user_id
                        }
                        
        except Exception as e:
            logger.debug(f"Failed to derive context from git_branch_id {git_branch_id}: {e}")
        
        # Fallback to defaults
        logger.warning(f"Could not derive context from git_branch_id {git_branch_id}, using defaults")
        # Validate user authentication
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        # Use auth_helper to get authenticated user ID (same as controllers)
        try:
            from ...interface.controllers.auth_helper import get_authenticated_user_id
            user_id = get_authenticated_user_id(None, "Subtask context derivation")
        except Exception as e:
            logger.error(f"Authentication failed for subtask context derivation: {e}")
            # No fallback allowed - authentication is required
            logger.error(f"Authentication required for subtask context derivation: {e}")
            raise e
        
        return {
            "project_id": "default_project",
            "git_branch_name": "main", 
            "user_id": user_id
        }

    def _get_context_repositories(self, project_id: str = None, git_branch_name: str = None, user_id: str = None) -> tuple[TaskRepository, SubtaskRepository]:
        """Get repositories with correct context parameters"""
        if self._task_repository_factory and self._subtask_repository_factory and all([project_id, git_branch_name, user_id]):
            # Use factory-based approach with context parameters
            task_repository = self._task_repository_factory.create_repository(project_id, git_branch_name, user_id)
            subtask_repository = self._subtask_repository_factory.create_subtask_repository(project_id, git_branch_name, user_id)
            return task_repository, subtask_repository
        else:
            # Fall back to static repositories for backward compatibility
            return self._task_repository, self._subtask_repository

    def handle_manage_subtask(
        self,
        action: str,
        task_id: str,
        subtask_data: Dict[str, Any] | None = None,
        # Legacy compatibility parameters (will be ignored following clean relationship chain)
        project_id: str | None = None,
        git_branch_name: str | None = None,
        user_id: str | None = None,
    ) -> Dict[str, Any]:
        """Handle subtask operations.

        The historical signature placed *subtask_data* as the **third** positional
        argument (after ``task_id``) whereas the modern signature accepts it as a
        keyword-only parameter.  To remain compatible with both call styles we
        detect when *project_id* is in fact a ``dict`` (i.e., looks like
        subtask_data) and shuffle parameters accordingly.
        """

        # ----- Back-compat argument shuffle ---------------------------------
        if isinstance(project_id, dict) and subtask_data is None:
            # Caller used legacy positional style: (action, task_id, subtask_data)
            subtask_data = project_id  # type: ignore[assignment]
            project_id = None
        # --------------------------------------------------------------------

        if not task_id:
            raise ValueError("Task ID is required")
        
        # Following clean relationship chain: derive context from task_id for factory-based repositories
        if self._task_repository_factory and self._subtask_repository_factory:
            # For factory-based repositories, derive context from task_id
            context = self._derive_context_from_task(task_id)
            task_repository, subtask_repository = self._get_context_repositories(
                project_id=context.get("project_id"),
                git_branch_name=context.get("git_branch_name"), 
                user_id=context.get("user_id")
            )
        else:
            # For static repositories (backward compatibility), use them directly
            task_repository, subtask_repository = self._get_context_repositories()
        
        # Normalize action: allow 'add' as alias for 'create'
        action = action.lower()
        if action == "add":
            action = "create"
        if action == "create":
            return self._handle_create_subtask(task_id, subtask_data, task_repository, subtask_repository)
        elif action == "update":
            return self._handle_update_subtask(task_id, subtask_data, task_repository, subtask_repository)
        elif action == "delete":
            return self._handle_delete_subtask(task_id, subtask_data, task_repository, subtask_repository)
        elif action == "list":
            return self._handle_list_subtasks(task_id, task_repository, subtask_repository)
        elif action == "get":
            return self._handle_get_subtask(task_id, subtask_data, task_repository, subtask_repository)
        elif action == "complete":
            return self._handle_complete_subtask(task_id, subtask_data, task_repository, subtask_repository)
        else:
            raise ValueError(f"Unsupported subtask action: {action}")
    
    def _handle_create_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle subtask creation"""
        if not subtask_data or "title" not in subtask_data:
            raise ValueError("subtask_data with title is required")
        
        # Create use case with context-specific repositories
        add_subtask_use_case = self._add_subtask_use_case or AddSubtaskUseCase(task_repository, subtask_repository)
        
        request = AddSubtaskRequest(
            task_id=task_id,
            title=subtask_data["title"],
            description=subtask_data.get("description", ""),
            assignees=subtask_data.get("assignees", []),
            priority=subtask_data.get("priority")
        )
        response = add_subtask_use_case.execute(request)
        return {
            "success": True,
            "action": "create",
            "message": f"Subtask '{subtask_data['title']}' created for task {task_id}",
            "subtask": response.subtask,  # Direct access to subtask data, not wrapped response
            "task_id": response.task_id,
            "progress": response.progress
        }
    
    def _handle_update_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle subtask update"""
        if not subtask_data or "subtask_id" not in subtask_data:
            raise ValueError("subtask_data with subtask_id is required")
        
        # Create use case with context-specific repositories
        update_subtask_use_case = self._update_subtask_use_case or UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        request = UpdateSubtaskRequest(
            task_id=task_id,
            id=subtask_data["subtask_id"],
            title=subtask_data.get("title"),
            description=subtask_data.get("description"),
            status=subtask_data.get("status"),
            priority=subtask_data.get("priority"),
            assignees=subtask_data.get("assignees"),
            progress_percentage=subtask_data.get("progress_percentage")
        )
        response = update_subtask_use_case.execute(request)
        return {
            "success": True,
            "action": "update",
            "message": f"Subtask {subtask_data['subtask_id']} updated",
            "subtask": response.to_dict()
        }
    
    def _handle_delete_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle subtask deletion"""
        if not subtask_data or "subtask_id" not in subtask_data:
            raise ValueError("subtask_data with subtask_id is required")
        
        # Create use case with context-specific repositories
        remove_subtask_use_case = self._remove_subtask_use_case or RemoveSubtaskUseCase(task_repository, subtask_repository)
        
        result = remove_subtask_use_case.execute(task_id, subtask_data["subtask_id"])
        return {
            "success": result["success"],
            "action": "delete",
            "message": f"Subtask {subtask_data['subtask_id']} deleted from task {task_id}",
            "progress": result.get("progress", {})
        }
    
    def _handle_list_subtasks(self, task_id: str, task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle listing subtasks for a task"""
        # Create use case with context-specific repositories
        get_subtasks_use_case = self._get_subtasks_use_case or GetSubtasksUseCase(task_repository, subtask_repository)
        
        result = get_subtasks_use_case.execute(task_id)
        return {
            "success": True,
            "action": "list",
            "message": f"Subtasks retrieved for task {task_id}",
            "subtasks": result["subtasks"],
            "progress": result["progress"]
        }
    
    def _handle_get_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle getting a specific subtask"""
        if not subtask_data or "subtask_id" not in subtask_data:
            raise ValueError("subtask_data with subtask_id is required")
        
        # Create use case with context-specific repositories
        get_subtask_use_case = self._get_subtask_use_case or GetSubtaskUseCase(task_repository, subtask_repository)
        
        result = get_subtask_use_case.execute(task_id, subtask_data["subtask_id"])
        return {
            "success": True,
            "action": "get",
            "message": f"Subtask {subtask_data['subtask_id']} retrieved",
            "subtask": result["subtask"],
            "progress": result["progress"]
        }
    
    def _handle_complete_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle completing a subtask"""
        if not subtask_data or "subtask_id" not in subtask_data:
            raise ValueError("subtask_data with subtask_id is required")
        
        # Create use case with context-specific repositories
        complete_subtask_use_case = self._complete_subtask_use_case or CompleteSubtaskUseCase(task_repository, subtask_repository)
        
        result = complete_subtask_use_case.execute(task_id, subtask_data["subtask_id"])
        return {
            "success": result["success"],
            "action": "complete",
            "message": f"Subtask {subtask_data['subtask_id']} completed",
            "subtask": {"id": subtask_data['subtask_id'], "completed": True},
            "progress": result["progress"]
        }
