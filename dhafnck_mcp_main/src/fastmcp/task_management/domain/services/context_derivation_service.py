"""Context Derivation Service - Domain service for deriving context from domain entities

This service encapsulates the business logic for deriving context information
from tasks, git branches, and other domain entities. This logic was previously
scattered across application facades.
"""

import logging
from typing import Dict, Optional, Any
from ..entities.task import Task
from ..value_objects.task_id import TaskId
from ..repositories.task_repository import TaskRepository
from ..repositories.git_branch_repository import GitBranchRepository

logger = logging.getLogger(__name__)


class ContextDerivationService:
    """
    Domain service responsible for deriving context information from domain entities.
    
    This service encapsulates the business rules for:
    - Deriving context from tasks
    - Deriving context from git branches
    - Resolving context hierarchies
    - Determining default contexts
    """
    
    def __init__(
        self,
        task_repository: Optional[TaskRepository] = None,
        git_branch_repository: Optional[GitBranchRepository] = None
    ):
        """Initialize the context derivation service with repositories"""
        self._task_repository = task_repository
        self._git_branch_repository = git_branch_repository
    
    def derive_context_from_task(
        self,
        task_id: str,
        default_user_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Derive context parameters from a task.
        
        Business Rules:
        - Tasks inherit context from their git branch
        - If task has no git branch, use default context
        - User authentication is required for context derivation
        
        Args:
            task_id: The task identifier
            default_user_id: Default user ID for authentication
            
        Returns:
            Dictionary containing project_id, git_branch_name, and user_id
        """
        try:
            if self._task_repository:
                # Find the task using repository
                task = self._task_repository.find_by_id(TaskId.from_string(task_id))
                
                if task and task.git_branch_id:
                    logger.debug(f"Task {task_id} found with git_branch_id: {task.git_branch_id}")
                    # Delegate to git branch context derivation
                    return self.derive_context_from_git_branch(
                        task.git_branch_id,
                        default_user_id
                    )
                elif task:
                    logger.debug(f"Task {task_id} found but no git_branch_id")
                else:
                    logger.debug(f"Task {task_id} not found")
                    
        except Exception as e:
            logger.warning(f"Failed to derive context from task {task_id}: {e}")
        
        # Return default context if derivation fails
        return self._get_default_context(default_user_id)
    
    def derive_context_from_git_branch(
        self,
        git_branch_id: str,
        default_user_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Derive context parameters from a git branch.
        
        Business Rules:
        - Git branches belong to projects
        - Projects have owners (users)
        - Context includes project, branch name, and user
        
        Args:
            git_branch_id: The git branch identifier
            default_user_id: Default user ID for authentication
            
        Returns:
            Dictionary containing project_id, git_branch_name, and user_id
        """
        try:
            if self._git_branch_repository:
                # Find the git branch using repository
                git_branch = self._git_branch_repository.find_by_id(git_branch_id)
                
                if git_branch:
                    logger.debug(
                        f"Git branch {git_branch_id} found: "
                        f"project_id={git_branch.project_id}, name={git_branch.name}"
                    )
                    
                    # Derive context from git branch entity
                    context = {
                        "project_id": git_branch.project_id,
                        "git_branch_name": git_branch.name,
                        "user_id": default_user_id  # Will be resolved below
                    }
                    
                    # Try to get user from project if available
                    if hasattr(git_branch, 'project') and git_branch.project:
                        if hasattr(git_branch.project, 'user_id'):
                            context["user_id"] = git_branch.project.user_id
                    
                    # Ensure user_id is set
                    if not context.get("user_id"):
                        context["user_id"] = self._resolve_user_id(default_user_id)
                    
                    return context
                    
        except Exception as e:
            logger.warning(f"Failed to derive context from git_branch {git_branch_id}: {e}")
        
        # Return default context if derivation fails
        return self._get_default_context(default_user_id)
    
    def derive_context_hierarchy(
        self,
        task_id: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Derive complete context hierarchy from available identifiers.
        
        Business Rules:
        - Context flows from Global -> Project -> Branch -> Task
        - Higher levels provide defaults for lower levels
        - Each level can override inherited values
        
        Args:
            task_id: Optional task identifier
            git_branch_id: Optional git branch identifier
            project_id: Optional project identifier
            user_id: Optional user identifier
            
        Returns:
            Dictionary containing complete context hierarchy
        """
        context_hierarchy = {
            "global": {},
            "project": {},
            "branch": {},
            "task": {}
        }
        
        # Start with user context (global level)
        if user_id:
            context_hierarchy["global"]["user_id"] = user_id
        
        # Add project context
        if project_id:
            context_hierarchy["project"]["project_id"] = project_id
        
        # Derive branch context
        if git_branch_id:
            branch_context = self.derive_context_from_git_branch(git_branch_id, user_id)
            context_hierarchy["branch"] = branch_context
            
            # Propagate to project if not set
            if not context_hierarchy["project"].get("project_id"):
                context_hierarchy["project"]["project_id"] = branch_context.get("project_id")
        
        # Derive task context
        if task_id:
            task_context = self.derive_context_from_task(task_id, user_id)
            context_hierarchy["task"] = task_context
            
            # Propagate upwards if not set
            if not context_hierarchy["branch"]:
                context_hierarchy["branch"] = {
                    "git_branch_name": task_context.get("git_branch_name"),
                    "project_id": task_context.get("project_id")
                }
            if not context_hierarchy["project"].get("project_id"):
                context_hierarchy["project"]["project_id"] = task_context.get("project_id")
        
        return context_hierarchy
    
    def _get_default_context(self, default_user_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get default context when derivation fails.
        
        Business Rules:
        - Project ID must be provided (no defaults)
        - Default branch is "main"
        - User authentication is required
        
        Args:
            default_user_id: Default user ID for authentication
            
        Returns:
            Dictionary with default context values
            
        Raises:
            ValueError: If context cannot be derived without project ID
        """
        # DDD Compliance: No hardcoded project IDs - require explicit values
        raise ValueError("Cannot derive context: Project ID is required. No fallback to default project allowed per DDD principles.")
    
    def _resolve_user_id(self, default_user_id: Optional[str] = None) -> str:
        """
        Resolve user ID with authentication requirements.
        
        Business Rules:
        - User authentication is required for all operations
        - System user is used as fallback for background operations
        
        Args:
            default_user_id: Default user ID to use
            
        Returns:
            Resolved user ID
            
        Raises:
            ValueError: If user authentication cannot be resolved
        """
        if default_user_id:
            return default_user_id
        
        # In a domain service, we don't directly access authentication
        # This would typically be passed from the application layer
        logger.warning("No user ID provided, using system user")
        return "system"
    
    def determine_context_level(
        self,
        task_id: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> str:
        """
        Determine the appropriate context level based on available identifiers.
        
        Business Rules:
        - Task level if task_id is provided
        - Branch level if only git_branch_id is provided
        - Project level if only project_id is provided
        - Global level if no identifiers provided
        
        Args:
            task_id: Optional task identifier
            git_branch_id: Optional git branch identifier
            project_id: Optional project identifier
            
        Returns:
            Context level string: "task", "branch", "project", or "global"
        """
        if task_id:
            return "task"
        elif git_branch_id:
            return "branch"
        elif project_id:
            return "project"
        else:
            return "global"