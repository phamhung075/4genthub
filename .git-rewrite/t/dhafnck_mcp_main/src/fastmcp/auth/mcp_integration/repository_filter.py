"""
User-Filtered Repository Wrapper for MCP Operations

This module provides repository wrappers that automatically filter
all operations by the current user ID from JWT token context.
"""

import logging
from typing import Optional, List, Any, TypeVar, Generic
from abc import ABC, abstractmethod

from ..middleware.request_context_middleware import get_current_user_id, get_authentication_context as get_current_user_context

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for entities


class UserFilteredRepository(Generic[T], ABC):
    """
    Base class for user-filtered repositories.
    
    This wrapper automatically adds user_id filtering to all repository operations,
    ensuring users can only access their own data.
    """
    
    def __init__(self, base_repository: Any, user_id_field: str = "user_id"):
        """
        Initialize the filtered repository.
        
        Args:
            base_repository: The underlying repository to wrap
            user_id_field: The field name that contains user_id in entities
        """
        self._base_repository = base_repository
        self._user_id_field = user_id_field
    
    def _get_current_user_id(self) -> str:
        """
        Get the current user ID from context.
        
        Returns:
            Current user ID
            
        Raises:
            RuntimeError: If no user is authenticated
        """
        context_user_obj = get_current_user_id()
        
        # Extract user_id string from the context object (handles BackwardCompatUserContext objects)
        user_id = None
        if context_user_obj:
            if isinstance(context_user_obj, str):
                # Already a string
                user_id = context_user_obj
            elif hasattr(context_user_obj, 'user_id'):
                # Extract user_id attribute from BackwardCompatUserContext
                user_id = context_user_obj.user_id
            else:
                # Fallback: convert to string
                user_id = str(context_user_obj) if context_user_obj else None
        
        if not user_id:
            raise RuntimeError("No authenticated user in context")
        return user_id
    
    def _add_user_filter(self, filters: dict) -> dict:
        """
        Add user_id filter to existing filters.
        
        Args:
            filters: Existing filters
            
        Returns:
            Filters with user_id added
        """
        user_id = self._get_current_user_id()
        filters = filters or {}
        filters[self._user_id_field] = user_id
        return filters
    
    @abstractmethod
    def find_by_id(self, entity_id: Any) -> Optional[T]:
        """Find entity by ID, filtered by current user."""
        pass
    
    @abstractmethod
    def find_all(self, **filters) -> List[T]:
        """Find all entities matching filters, filtered by current user."""
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        """Save entity, ensuring it belongs to current user."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """Delete entity, ensuring it belongs to current user."""
        pass


class UserFilteredTaskRepository(UserFilteredRepository):
    """
    User-filtered wrapper for TaskRepository.
    
    Ensures all task operations are filtered by the current user's ID.
    """
    
    def find_by_id(self, task_id: Any) -> Optional[Any]:
        """
        Find task by ID, ensuring it belongs to current user.
        
        Args:
            task_id: Task ID to find
            
        Returns:
            Task if found and belongs to user, None otherwise
        """
        try:
            task = self._base_repository.find_by_id(task_id)
            if task:
                # Check if task belongs to current user
                user_id = self._get_current_user_id()
                task_user_id = getattr(task, self._user_id_field, None)
                
                if task_user_id == user_id:
                    return task
                else:
                    logger.warning(f"User {user_id} attempted to access task {task_id} belonging to {task_user_id}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error finding task {task_id}: {e}")
            return None
    
    def find_all(self, **filters) -> List[Any]:
        """
        Find all tasks matching filters, filtered by current user.
        
        Args:
            **filters: Additional filters
            
        Returns:
            List of tasks belonging to current user
        """
        try:
            # Add user filter
            filters = self._add_user_filter(filters)
            return self._base_repository.find_all(**filters)
        except Exception as e:
            logger.error(f"Error finding tasks: {e}")
            return []
    
    def find_by_git_branch_id(self, git_branch_id: str) -> List[Any]:
        """
        Find tasks by git branch ID, filtered by current user.
        
        Args:
            git_branch_id: Git branch ID
            
        Returns:
            List of tasks in branch belonging to current user
        """
        try:
            # Get all tasks in branch
            tasks = self._base_repository.find_by_git_branch_id(git_branch_id)
            
            # Filter by current user
            user_id = self._get_current_user_id()
            return [
                task for task in tasks 
                if getattr(task, self._user_id_field, None) == user_id
            ]
        except Exception as e:
            logger.error(f"Error finding tasks for branch {git_branch_id}: {e}")
            return []
    
    def save(self, task: Any) -> Any:
        """
        Save task, ensuring it belongs to current user.
        
        Args:
            task: Task to save
            
        Returns:
            Saved task
            
        Raises:
            RuntimeError: If task doesn't belong to current user
        """
        try:
            user_id = self._get_current_user_id()
            
            # For new tasks, set user_id
            if not hasattr(task, 'id') or task.id is None:
                setattr(task, self._user_id_field, user_id)
            else:
                # For existing tasks, verify user_id matches
                task_user_id = getattr(task, self._user_id_field, None)
                if task_user_id != user_id:
                    raise RuntimeError(f"Cannot save task belonging to another user")
            
            return self._base_repository.save(task)
        except Exception as e:
            logger.error(f"Error saving task: {e}")
            raise
    
    def delete(self, task_id: Any) -> bool:
        """
        Delete task, ensuring it belongs to current user.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # First check if task belongs to user
            task = self.find_by_id(task_id)
            if not task:
                return False
            
            return self._base_repository.delete(task_id)
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False


class UserFilteredProjectRepository(UserFilteredRepository):
    """
    User-filtered wrapper for ProjectRepository.
    
    Ensures all project operations are filtered by the current user's ID.
    """
    
    def find_by_id(self, project_id: Any) -> Optional[Any]:
        """Find project by ID, ensuring it belongs to current user."""
        try:
            project = self._base_repository.find_by_id(project_id)
            if project:
                user_id = self._get_current_user_id()
                project_user_id = getattr(project, self._user_id_field, None)
                
                if project_user_id == user_id:
                    return project
                else:
                    logger.warning(f"User {user_id} attempted to access project {project_id} belonging to {project_user_id}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error finding project {project_id}: {e}")
            return None
    
    def find_all(self, **filters) -> List[Any]:
        """Find all projects, filtered by current user."""
        try:
            filters = self._add_user_filter(filters)
            return self._base_repository.find_all(**filters)
        except Exception as e:
            logger.error(f"Error finding projects: {e}")
            return []
    
    def save(self, project: Any) -> Any:
        """Save project, ensuring it belongs to current user."""
        try:
            user_id = self._get_current_user_id()
            
            # For new projects, set user_id
            if not hasattr(project, 'id') or project.id is None:
                setattr(project, self._user_id_field, user_id)
            else:
                # For existing projects, verify user_id matches
                project_user_id = getattr(project, self._user_id_field, None)
                if project_user_id != user_id:
                    raise RuntimeError(f"Cannot save project belonging to another user")
            
            return self._base_repository.save(project)
        except Exception as e:
            logger.error(f"Error saving project: {e}")
            raise
    
    def delete(self, project_id: Any) -> bool:
        """Delete project, ensuring it belongs to current user."""
        try:
            # First check if project belongs to user
            project = self.find_by_id(project_id)
            if not project:
                return False
            
            return self._base_repository.delete(project_id)
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return False


class UserFilteredContextRepository(UserFilteredRepository):
    """
    User-filtered wrapper for ContextRepository.
    
    Ensures all context operations are filtered by the current user's ID.
    """
    
    def find_by_id(self, context_id: Any) -> Optional[Any]:
        """Find context by ID, ensuring it belongs to current user."""
        try:
            context = self._base_repository.find_by_id(context_id)
            if context:
                user_id = self._get_current_user_id()
                context_user_id = getattr(context, self._user_id_field, None)
                
                # CRITICAL FIX: All contexts (including global) must belong to user
                # Global contexts are user-scoped, not truly global
                if context_user_id == user_id:
                    return context
                else:
                    logger.warning(f"User {user_id} attempted to access context {context_id} belonging to {context_user_id}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error finding context {context_id}: {e}")
            return None
    
    def find_all(self, **filters) -> List[Any]:
        """Find all contexts, filtered by current user."""
        try:
            user_id = self._get_current_user_id()
            
            # Include both user's contexts and global contexts
            user_filters = filters.copy()
            user_filters[self._user_id_field] = user_id
            
            global_filters = filters.copy()
            global_filters[self._user_id_field] = None  # Global contexts have no user_id
            
            user_contexts = self._base_repository.find_all(**user_filters)
            global_contexts = self._base_repository.find_all(**global_filters)
            
            return user_contexts + global_contexts
        except Exception as e:
            logger.error(f"Error finding contexts: {e}")
            return []
    
    def save(self, context: Any) -> Any:
        """Save context, ensuring it belongs to current user."""
        try:
            user_id = self._get_current_user_id()
            
            # CRITICAL FIX: Global contexts now require user_id for user isolation
            # Each user has their own "global" context space
            context_level = getattr(context, 'level', None)
            if context_level == 'global':
                # Set user_id for global contexts (user-scoped globals)
                setattr(context, self._user_id_field, user_id)
                logger.debug(f"Setting user_id {user_id} for global context")
            else:
                # For new contexts, set user_id
                if not hasattr(context, 'id') or context.id is None:
                    setattr(context, self._user_id_field, user_id)
                else:
                    # For existing contexts, verify user_id matches
                    context_user_id = getattr(context, self._user_id_field, None)
                    if context_user_id is not None and context_user_id != user_id:
                        raise RuntimeError(f"Cannot save context belonging to another user")
            
            return self._base_repository.save(context)
        except Exception as e:
            logger.error(f"Error saving context: {e}")
            raise
    
    def delete(self, context_id: Any) -> bool:
        """Delete context, ensuring it belongs to current user."""
        try:
            # First check if context belongs to user
            context = self.find_by_id(context_id)
            if not context:
                return False
            
            # Don't allow deleting global contexts
            context_level = getattr(context, 'level', None)
            if context_level == 'global':
                logger.warning(f"User {self._get_current_user_id()} attempted to delete global context")
                return False
            
            return self._base_repository.delete(context_id)
        except Exception as e:
            logger.error(f"Error deleting context {context_id}: {e}")
            return False


def create_user_filtered_repository(
    repository_type: str,
    base_repository: Any,
    user_id_field: str = "user_id"
) -> UserFilteredRepository:
    """
    Factory function to create user-filtered repositories.
    
    Args:
        repository_type: Type of repository ('task', 'project', 'context')
        base_repository: The underlying repository to wrap
        user_id_field: The field name that contains user_id
        
    Returns:
        User-filtered repository wrapper
        
    Raises:
        ValueError: If repository type is unknown
    """
    repository_map = {
        'task': UserFilteredTaskRepository,
        'project': UserFilteredProjectRepository,
        'context': UserFilteredContextRepository,
    }
    
    repository_class = repository_map.get(repository_type)
    if not repository_class:
        raise ValueError(f"Unknown repository type: {repository_type}")
    
    return repository_class(base_repository, user_id_field)