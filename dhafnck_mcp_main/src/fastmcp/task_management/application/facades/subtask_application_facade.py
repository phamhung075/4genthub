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
from ...domain.interfaces.repository_factory import ITaskRepositoryFactory
from ...infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from ...infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory

logger = logging.getLogger(__name__)

class SubtaskApplicationFacade:
    """Facade for subtask-related operations"""
    
    def __init__(self, task_repository: TaskRepository = None, subtask_repository: SubtaskRepository = None, 
                 task_repository_factory: TaskRepositoryFactory = None, 
                 subtask_repository_factory: SubtaskRepositoryFactory = None,
                 user_id: str = None):
        # For backward compatibility, keep the old constructor signature
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        
        # New factory-based approach
        self._task_repository_factory = task_repository_factory
        self._subtask_repository_factory = subtask_repository_factory
        
        # Store user_id for repository creation
        self._user_id = user_id
        
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
        """Derive context parameters from the parent task by looking it up in database"""
        # First, ensure we have a user_id for authentication filtering
        lookup_user_id = None
        if self._user_id:
            lookup_user_id = self._user_id
        else:
            # Get authenticated user ID for proper multi-tenant filtering
            try:
                from ...interface.mcp_controllers.auth_helper.auth_helper import get_authenticated_user_id
                lookup_user_id = get_authenticated_user_id(None, "Task lookup for subtask context")
                logger.info(f"🔍 Using authenticated user_id for task lookup: {lookup_user_id}")
            except Exception as e:
                logger.error(f"Authentication failed for task lookup: {e}")
                raise ValueError("User authentication required for task lookup") from e
        
        try:
            # Use proper database connection (PostgreSQL/Supabase)
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Task
            
            with get_session() as session:
                # CRITICAL FIX: Look up the task with user_id filter for proper multi-tenant isolation
                task = session.query(Task).filter(
                    Task.id == task_id,
                    Task.user_id == lookup_user_id  # Multi-tenant filtering - REQUIRED
                ).first()
                
                if task:
                    logger.info(f"✅ Task {task_id} found with git_branch_id: {task.git_branch_id}, user_id: {task.user_id}")
                    
                    # If task has a user_id, use it directly for consistency
                    if task.user_id:
                        # DDD Compliance: No hardcoded project IDs - require explicit values
                        if not task.git_branch_id:
                            raise ValueError(f"Task {task_id} missing git_branch_id required for context derivation")
                        context = None
                        
                        # If task has git_branch_id, derive full context
                        if task.git_branch_id:
                            branch_context = self._derive_context_from_git_branch_id(task.git_branch_id)
                            # But preserve the task's user_id
                            branch_context["user_id"] = str(task.user_id)
                            context = branch_context
                        
                        logger.info(f"✅ Derived context for subtask with task's user_id: {context}")
                        return context
                    elif task.git_branch_id:
                        # Derive context from task's git_branch_id
                        context = self._derive_context_from_git_branch_id(task.git_branch_id)
                        logger.info(f"✅ Derived context for subtask from branch: {context}")
                        return context
                else:
                    logger.error(f"❌ Task {task_id} not found for user {lookup_user_id}")
                    # CRITICAL: Task not found for this user - raise error instead of fallback
                    from ...domain.exceptions import TaskNotFoundError
                    raise TaskNotFoundError(f"Task {task_id} not found")
                    
        except Exception as e:
            if isinstance(e, ValueError) and "authentication required" in str(e).lower():
                # Re-raise authentication errors
                raise e
            logger.error(f"Failed to find task {task_id} in database: {e}")
            # CRITICAL: If task lookup fails, we should fail rather than create defaults
            from ...domain.exceptions import TaskNotFoundError
            raise TaskNotFoundError(f"Task {task_id} not found") from e
    
    def _derive_context_from_git_branch_id(self, git_branch_id: str) -> Dict[str, str]:
        """Derive context parameters from git_branch_id by looking up the project_git_branchs table"""
        try:
            # Use proper database connection (PostgreSQL/Supabase)
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import ProjectGitBranch, Project
            
            with get_session() as session:
                # Look up the git branch to get project_id and git_branch_name
                branch = session.query(ProjectGitBranch).filter(ProjectGitBranch.id == git_branch_id).first()
                
                if branch:
                    project_id = branch.project_id
                    git_branch_name = branch.name
                    
                    # Look up the project to get user_id
                    project = session.query(Project).filter(Project.id == project_id).first()
                    
                    if project:
                        user_id = project.user_id
                        # If user_id is still None (e.g., in MVP mode), get authenticated user
                        if not user_id:
                            try:
                                from ...interface.mcp_controllers.auth_helper.auth_helper import get_authenticated_user_id
                                user_id = get_authenticated_user_id(None, "Subtask context derivation from git_branch")
                                logger.info(f"✅ Using authenticated user for context: {user_id}")
                            except Exception as e:
                                logger.error(f"Failed to get authenticated user: {e}")
                                # Authentication is required - no fallbacks
                                raise ValueError("User authentication required. No user ID provided.") from e
                        
                        logger.info(f"✅ Derived context from git_branch_id {git_branch_id}: project={project_id}, branch={git_branch_name}, user={user_id}")
                        return {
                            "project_id": str(project_id) if project_id else None,  # Convert UUID to string
                            "git_branch_name": git_branch_name,
                            "user_id": str(user_id) if user_id else None  # Convert to string
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
            from ...interface.mcp_controllers.auth_helper.auth_helper import get_authenticated_user_id
            user_id = get_authenticated_user_id(None, "Subtask context derivation")
        except Exception as e:
            logger.error(f"Authentication failed for subtask context derivation: {e}")
            # Authentication is required - no fallbacks
            raise ValueError("User authentication required. No user ID provided.")
        
        # DDD Compliance: No hardcoded project IDs - require explicit values
        raise ValueError("Cannot derive subtask context: git_branch_id is required. No fallback to default project allowed per DDD principles.")

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
        subtask_id: str | None = None,  # Add subtask_id as separate parameter
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
            return self._handle_update_subtask(task_id, subtask_data, task_repository, subtask_repository, subtask_id)
        elif action == "delete":
            return self._handle_delete_subtask(task_id, subtask_data, task_repository, subtask_repository, subtask_id)
        elif action == "list":
            return self._handle_list_subtasks(task_id, task_repository, subtask_repository)
        elif action == "get":
            return self._handle_get_subtask(task_id, subtask_data, task_repository, subtask_repository, subtask_id)
        elif action == "complete":
            return self._handle_complete_subtask(task_id, subtask_data, task_repository, subtask_repository, subtask_id)
        else:
            raise ValueError(f"Unsupported subtask action: {action}")
    
    def _handle_create_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository) -> Dict[str, Any]:
        """Handle subtask creation"""
        if not subtask_data or "title" not in subtask_data:
            raise ValueError("subtask_data with title is required")
        
        # Create use case with context-specific repositories
        add_subtask_use_case = self._add_subtask_use_case or AddSubtaskUseCase(task_repository, subtask_repository)
        
        # Extract user_id and ensure it's passed through
        # When using factory-based repositories, the user_id should already be set in the repository
        # But we need to ensure it's properly configured
        if hasattr(subtask_repository, '_user_id') and not subtask_repository._user_id:
            # If repository doesn't have user_id, derive it from context
            context = self._derive_context_from_task(task_id)
            if context.get('user_id'):
                # Create a new repository instance with the proper user_id
                if self._subtask_repository_factory:
                    subtask_repository = self._subtask_repository_factory.create_subtask_repository(
                        project_id=context.get("project_id"),
                        git_branch_name=context.get("git_branch_name"),
                        user_id=context.get("user_id")
                    )
                    # Recreate the use case with the properly scoped repository
                    add_subtask_use_case = AddSubtaskUseCase(task_repository, subtask_repository)
        
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
    
    def _handle_update_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository, subtask_id: str = None) -> Dict[str, Any]:
        """Handle subtask update"""
        # Use subtask_id parameter if provided, otherwise extract from subtask_data (backward compatibility)
        actual_subtask_id = subtask_id or (subtask_data and subtask_data.get("subtask_id"))
        if not actual_subtask_id:
            raise ValueError("subtask_id is required (either as parameter or in subtask_data)")
        
        # Create use case with context-specific repositories
        update_subtask_use_case = self._update_subtask_use_case or UpdateSubtaskUseCase(task_repository, subtask_repository)
        
        request = UpdateSubtaskRequest(
            task_id=task_id,
            id=actual_subtask_id,
            title=subtask_data.get("title") if subtask_data else None,
            description=subtask_data.get("description") if subtask_data else None,
            status=subtask_data.get("status") if subtask_data else None,
            priority=subtask_data.get("priority") if subtask_data else None,
            assignees=subtask_data.get("assignees") if subtask_data else None,
            progress_percentage=subtask_data.get("progress_percentage") if subtask_data else None
        )
        response = update_subtask_use_case.execute(request)
        return {
            "success": True,
            "action": "update",
            "message": f"Subtask {actual_subtask_id} updated",
            "subtask": response.to_dict()
        }
    
    def _handle_delete_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository, subtask_id: str = None) -> Dict[str, Any]:
        """Handle subtask deletion"""
        # Use subtask_id parameter if provided, otherwise extract from subtask_data (backward compatibility)
        actual_subtask_id = subtask_id or (subtask_data and subtask_data.get("subtask_id"))
        if not actual_subtask_id:
            raise ValueError("subtask_id is required (either as parameter or in subtask_data)")
        
        # Create use case with context-specific repositories
        remove_subtask_use_case = self._remove_subtask_use_case or RemoveSubtaskUseCase(task_repository, subtask_repository)
        
        result = remove_subtask_use_case.execute(task_id, actual_subtask_id)
        return {
            "success": result["success"],
            "action": "delete",
            "message": f"Subtask {actual_subtask_id} deleted from task {task_id}",
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
    
    def _handle_get_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository, subtask_id: str = None) -> Dict[str, Any]:
        """Handle getting a specific subtask"""
        # Use subtask_id parameter if provided, otherwise extract from subtask_data (backward compatibility)
        actual_subtask_id = subtask_id or (subtask_data and subtask_data.get("subtask_id"))
        if not actual_subtask_id:
            raise ValueError("subtask_id is required (either as parameter or in subtask_data)")
        
        # Create use case with context-specific repositories
        get_subtask_use_case = self._get_subtask_use_case or GetSubtaskUseCase(task_repository, subtask_repository)
        
        result = get_subtask_use_case.execute(task_id, actual_subtask_id)
        return {
            "success": True,
            "action": "get",
            "message": f"Subtask {actual_subtask_id} retrieved",
            "subtask": result["subtask"],
            "progress": result["progress"]
        }
    
    def _handle_complete_subtask(self, task_id: str, subtask_data: Dict[str, Any], task_repository: TaskRepository, subtask_repository: SubtaskRepository, subtask_id: str = None) -> Dict[str, Any]:
        """Handle completing a subtask"""
        # Use subtask_id parameter if provided, otherwise extract from subtask_data (backward compatibility)
        actual_subtask_id = subtask_id or (subtask_data and subtask_data.get("subtask_id"))
        if not actual_subtask_id:
            raise ValueError("subtask_id is required (either as parameter or in subtask_data)")
        
        # Create use case with context-specific repositories
        complete_subtask_use_case = self._complete_subtask_use_case or CompleteSubtaskUseCase(task_repository, subtask_repository)
        
        result = complete_subtask_use_case.execute(task_id, actual_subtask_id)
        return {
            "success": result["success"],
            "action": "complete",
            "message": f"Subtask {actual_subtask_id} completed",
            "subtask": {"id": actual_subtask_id, "completed": True},
            "progress": result["progress"]
        }
