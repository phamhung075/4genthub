"""
Delete Project Use Case with Cascade Deletion

This module provides comprehensive project deletion with cascade deletion of all related data:
- Git branches
- Tasks and subtasks  
- Contexts (project, branch, task levels)
- Agent assignments
- Dependencies
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...domain.entities.project import Project
from ...domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)

logger = logging.getLogger(__name__)


class DeleteProjectUseCase:
    """
    Use case for deleting a project with cascade deletion of all related data.
    
    This includes:
    - All git branches in the project
    - All tasks in those branches
    - All subtasks of those tasks
    - All contexts (project, branch, task levels)
    - All agent assignments
    - All task dependencies
    """
    
    def __init__(self, project_repo=None, git_branch_repo=None, task_repo=None, context_repo=None):
        """Initialize the delete project use case with required repositories."""
        # Use provided repositories or get defaults
        if project_repo is None or git_branch_repo is None or task_repo is None:
            from ...domain.interfaces.repository_factory import IProjectRepositoryFactory
            from ...domain.interfaces.repository_factory import IGitBranchRepositoryFactory
            from ...domain.interfaces.repository_factory import ITaskRepositoryFactory
            
            self.project_repo = project_repo or GlobalRepositoryManager.get_default()
            self.git_branch_repo = git_branch_repo or GitBranchRepositoryFactory.create()
            self.task_repo = task_repo or TaskRepositoryFactory.create()
        else:
            self.project_repo = project_repo
            self.git_branch_repo = git_branch_repo
            self.task_repo = task_repo
        
        # Context repo can be None - it's optional
        self.context_repo = context_repo
        
        # Initialize unified context repositories for hierarchical deletion
        try:
            from ..services.unified_context_facade_factory import UnifiedContextFacadeFactory
            factory = UnifiedContextFacadeFactory()
            self.unified_context_repo = factory.create_hierarchical_context_repository()
        except Exception as e:
            logger.warning(f"Could not initialize unified context repository: {e}")
            self.unified_context_repo = None
    
    async def execute(self, project_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Execute project deletion with cascade deletion.
        
        Args:
            project_id: The ID of the project to delete
            force: If True, skip confirmation checks and force deletion
            
        Returns:
            Dictionary with deletion results and statistics
            
        Raises:
            ResourceNotFoundException: If project not found
            ValidationException: If deletion cannot proceed (unless force=True)
            DatabaseException: If database operation fails
        """
        logger.info(f"Starting cascade deletion for project: {project_id}")
        
        # Track deletion statistics
        stats = {
            "project_id": project_id,
            "git_branches_deleted": 0,
            "tasks_deleted": 0,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "agent_assignments_removed": 0,
            "dependencies_removed": 0,
            "errors": []
        }
        
        try:
            # 1. Verify project exists
            project = await self.project_repo.find_by_id(project_id)
            if not project:
                raise ResourceNotFoundException(
                    resource_type="Project",
                    resource_id=project_id,
                    message=f"Project {project_id} not found"
                )
            
            stats["project_name"] = project.name
            logger.info(f"Found project: {project.name}")
            
            # 2. Check if safe to delete (unless forced)
            if not force:
                await self._validate_deletion_safety(project)
            
            # 3. Delete all contexts (hierarchical: task -> branch -> project)
            await self._delete_contexts(project_id, stats)
            
            # 4. Delete all tasks and subtasks
            await self._delete_tasks(project_id, stats)
            
            # 5. Delete all git branches
            await self._delete_git_branches(project_id, stats)
            
            # 6. Delete the project itself
            success = await self.project_repo.delete(project_id)
            if not success:
                raise DatabaseException(
                    message=f"Failed to delete project {project_id}",
                    operation="delete",
                    table="projects"
                )
            
            logger.info(f"Successfully deleted project {project_id} with all related data")
            
            return {
                "success": True,
                "message": f"Project '{project.name}' and all related data deleted successfully",
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error during project deletion: {e}")
            stats["errors"].append(str(e))
            
            if isinstance(e, (ResourceNotFoundException, ValidationException, DatabaseException)):
                raise
            
            raise DatabaseException(
                message=f"Failed to delete project: {str(e)}",
                operation="delete",
                table="projects"
            )
    
    async def _validate_deletion_safety(self, project: Project) -> None:
        """
        Validate if it's safe to delete the project.
        Only allow deletion if project has only 'main' branch with 0 tasks.
        
        Args:
            project: The project to validate
            
        Raises:
            ValidationException: If deletion is not safe
        """
        try:
            branches = await self.git_branch_repo.find_by_project(project.id)
            
            # Check if project has only one branch and it's 'main'
            if len(branches) > 1:
                branch_names = [b.name for b in branches]
                raise ValidationException(
                    field="project",
                    value=project.id,
                    message=f"Cannot delete project with multiple branches ({len(branches)} branches: {', '.join(branch_names)}). "
                            f"Delete other branches first, or use force=True"
                )
            
            if len(branches) == 1:
                main_branch = branches[0]
                if main_branch.name != "main":
                    raise ValidationException(
                        field="project",
                        value=project.id,
                        message=f"Cannot delete project with non-main branch '{main_branch.name}'. "
                                f"Project must have only 'main' branch, or use force=True"
                    )
                
                # Check if main branch has any tasks
                tasks = await self.task_repo.find_by_git_branch(main_branch.id)
                if tasks and len(tasks) > 0:
                    raise ValidationException(
                        field="project",
                        value=project.id,
                        message=f"Cannot delete project with {len(tasks)} tasks in main branch. "
                                f"Delete all tasks first, or use force=True"
                    )
            
            # If no branches at all, it's safe to delete
            logger.info(f"Project {project.id} is safe to delete (only main branch with 0 tasks)")
            
        except Exception as e:
            if isinstance(e, ValidationException):
                raise
            logger.warning(f"Error checking deletion safety: {e}")
    
    async def _delete_contexts(self, project_id: str, stats: Dict[str, Any]) -> None:
        """
        Delete all contexts related to the project (hierarchical).
        
        Args:
            project_id: The project ID
            stats: Statistics dictionary to update
        """
        try:
            # Delete task-level contexts first
            branches = await self.git_branch_repo.find_by_project(project_id)
            for branch in branches:
                tasks = await self.task_repo.find_by_git_branch(branch.id)
                for task in tasks:
                    # Delete task context
                    try:
                        if self.unified_context_repo:
                            # Use unified context system
                            deleted = await self.unified_context_repo.delete_context(
                                level="task",
                                context_id=task.id
                            )
                            if deleted:
                                stats["contexts_deleted"] += 1
                        elif self.context_repo:
                            # Fallback to basic context if available
                            deleted = await self.context_repo.delete(task.id)
                            if deleted:
                                stats["contexts_deleted"] += 1
                    except Exception as e:
                        logger.warning(f"Error deleting task context {task.id}: {e}")
                        stats["errors"].append(f"Task context {task.id}: {str(e)}")
                
                # Delete branch context
                try:
                    if self.unified_context_repo:
                        deleted = await self.unified_context_repo.delete_context(
                            level="branch",
                            context_id=branch.id
                        )
                        if deleted:
                            stats["contexts_deleted"] += 1
                except Exception as e:
                    logger.warning(f"Error deleting branch context {branch.id}: {e}")
                    stats["errors"].append(f"Branch context {branch.id}: {str(e)}")
            
            # Delete project context
            try:
                if self.unified_context_repo:
                    deleted = await self.unified_context_repo.delete_context(
                        level="project",
                        context_id=project_id
                    )
                    if deleted:
                        stats["contexts_deleted"] += 1
                elif self.context_repo:
                    # Fallback to basic context if available
                    deleted = await self.context_repo.delete(project_id)
                    if deleted:
                        stats["contexts_deleted"] += 1
            except Exception as e:
                logger.warning(f"Error deleting project context: {e}")
                stats["errors"].append(f"Project context: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during context deletion: {e}")
            stats["errors"].append(f"Context deletion: {str(e)}")
    
    async def _delete_tasks(self, project_id: str, stats: Dict[str, Any]) -> None:
        """
        Delete all tasks and subtasks in the project.
        
        Args:
            project_id: The project ID
            stats: Statistics dictionary to update
        """
        try:
            branches = await self.git_branch_repo.find_by_project(project_id)
            
            for branch in branches:
                tasks = await self.task_repo.find_by_git_branch(branch.id)
                
                for task in tasks:
                    # Count subtasks before deletion
                    if hasattr(task, 'subtasks') and task.subtasks:
                        stats["subtasks_deleted"] += len(task.subtasks)
                    
                    # Delete the task (subtasks cascade automatically)
                    try:
                        deleted = await self.task_repo.delete(task.id)
                        if deleted:
                            stats["tasks_deleted"] += 1
                    except Exception as e:
                        logger.warning(f"Error deleting task {task.id}: {e}")
                        stats["errors"].append(f"Task {task.id}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error during task deletion: {e}")
            stats["errors"].append(f"Task deletion: {str(e)}")
    
    async def _delete_git_branches(self, project_id: str, stats: Dict[str, Any]) -> None:
        """
        Delete all git branches in the project.
        
        Args:
            project_id: The project ID
            stats: Statistics dictionary to update
        """
        try:
            branches = await self.git_branch_repo.find_by_project(project_id)
            
            for branch in branches:
                # Count agent assignments before deletion
                if hasattr(branch, 'assigned_agent_id') and branch.assigned_agent_id:
                    stats["agent_assignments_removed"] += 1
                
                # Delete the branch
                try:
                    deleted = await self.git_branch_repo.delete(branch.id)
                    if deleted:
                        stats["git_branches_deleted"] += 1
                except Exception as e:
                    logger.warning(f"Error deleting git branch {branch.id}: {e}")
                    stats["errors"].append(f"Git branch {branch.id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error during git branch deletion: {e}")
            stats["errors"].append(f"Git branch deletion: {str(e)}")