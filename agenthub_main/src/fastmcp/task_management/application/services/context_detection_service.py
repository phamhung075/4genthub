"""Context Detection Service

This service provides utilities to detect whether a given ID is a project ID, 
git branch ID, or task ID by checking through the proper application layer.
"""

import logging
from typing import Tuple, Optional

from ...infrastructure.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class ContextDetectionService:
    """Service for detecting the type of a given ID through proper repository access"""
    
    def __init__(self):
        """Initialize the service with repository factories"""
        self.project_repository = RepositoryFactory.get_project_repository()
        self.git_branch_repository = RepositoryFactory.get_git_branch_repository()
        self.task_repository = RepositoryFactory.get_task_repository()
    
    def detect_id_type(self, context_id: str) -> Tuple[str, Optional[str]]:
        """
        Detect whether the given ID is a project, git branch, or task ID.
        
        Args:
            context_id: The ID to check
            
        Returns:
            Tuple of (id_type, project_id) where:
            - id_type is one of: "project", "git_branch", "task", "unknown"
            - project_id is the associated project ID (None for unknown)
        """
        if not context_id:
            logger.warning("Empty context_id provided")
            return ("unknown", None)
            
        try:
            # Check if it's a project ID
            try:
                project = self.project_repository.get_by_id(context_id)
                if project:
                    logger.debug(f"ID {context_id} identified as project ID")
                    return ("project", context_id)
            except Exception:
                pass  # Not a project ID
            
            # Check if it's a git branch ID
            try:
                branch = self.git_branch_repository.get_by_id(context_id)
                if branch:
                    logger.debug(f"ID {context_id} identified as git branch ID with project {branch.project_id}")
                    return ("git_branch", branch.project_id)
            except Exception:
                pass  # Not a git branch ID
            
            # Check if it's a task ID
            try:
                task = self.task_repository.get_by_id(context_id)
                if task:
                    # Get the project ID via the git branch
                    branch = self.git_branch_repository.get_by_id(task.git_branch_id)
                    if branch:
                        logger.debug(f"ID {context_id} identified as task ID with project {branch.project_id}")
                        return ("task", branch.project_id)
            except Exception:
                pass  # Not a task ID
            
            # ID not found in any repository
            logger.warning(f"ID {context_id} not found in any repository")
            return ("unknown", None)
                
        except Exception as e:
            logger.error(f"Error detecting ID type for {context_id}: {e}")
            return ("unknown", None)
    
    def get_context_level_for_id(self, context_id: str) -> str:
        """
        Get the appropriate context level for a given ID.
        
        Args:
            context_id: The ID to check
            
        Returns:
            The context level: "project", "task", or "task" (default)
        """
        id_type, _ = self.detect_id_type(context_id)
        
        # Map ID types to context levels
        if id_type == "project":
            return "project"
        elif id_type in ["git_branch", "task"]:
            return "task"  # Both git branches and tasks use task-level contexts
        else:
            # Default to task level for unknown IDs
            logger.warning(f"Unknown ID type for {context_id}, defaulting to task level")
            return "task"