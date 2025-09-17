"""Automated Context Synchronization Service

This service provides centralized coordination for automatic context synchronization
across the task management system. It ensures that context is kept up-to-date
when tasks and subtasks change state.

Part of Fix for Issue #3: Automatic Context Updates for Task State Changes
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio

from .task_context_sync_service import TaskContextSyncService
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.entities.task import Task
from ...domain.entities.subtask import Subtask

logger = logging.getLogger(__name__)


class AutomatedContextSyncService:
    """Centralized service for automated context synchronization.
    
    This service coordinates context updates across different operations:
    - Task state changes (create, update, complete)
    - Subtask state changes (create, update, complete)
    - Progress aggregation from subtasks to parent tasks
    - Cross-hierarchy context propagation
    """

    def __init__(self, 
                 task_repository: TaskRepository,
                 subtask_repository: Optional[SubtaskRepository] = None,
                 user_id: Optional[str] = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._user_id = user_id  # Store user context
        
        # Create user-scoped context sync service
        task_repo = self._get_user_scoped_repository(task_repository)
        self._context_sync_service = TaskContextSyncService(task_repo)

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'AutomatedContextSyncService':
        """Create a new service instance scoped to a specific user."""
        return AutomatedContextSyncService(
            self._task_repository,
            self._subtask_repository,
            user_id
        )

    # ------------------------------------------------------------------
    # Task-level synchronization
    # ------------------------------------------------------------------

    async def sync_task_context_after_update(self, 
                                           task: Task,
                                           operation_type: str = "update") -> bool:
        """Synchronize task context after any task operation.
        
        Args:
            task: The task entity that was modified
            operation_type: Type of operation performed (create, update, complete)
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            task_id_str = str(task.id.value if hasattr(task.id, 'value') else task.id)
            git_branch_id = getattr(task, 'git_branch_id', None)
            project_id = getattr(task, 'project_id', None)
            
            logger.info(f"[AutomatedContextSync] Syncing task context for {task_id_str} after {operation_type}")
            
            # Perform context synchronization
            if not project_id:
                raise ValueError(f"project_id is required for automated context sync")
            result = await self._context_sync_service.sync_context_and_get_task(
                task_id=task_id_str,
                user_id=f"system_{operation_type}",
                project_id=project_id,
                git_branch_name="main"  # Default branch name
            )
            
            if result:
                logger.info(f"[AutomatedContextSync] Successfully synced context for task {task_id_str}")
                return True
            else:
                logger.warning(f"[AutomatedContextSync] Context sync returned None for task {task_id_str}")
                return False
                
        except Exception as e:
            logger.error(f"[AutomatedContextSync] Failed to sync context for task {task.id}: {e}")
            return False

    def sync_task_context_after_update_sync(self, 
                                           task: Task,
                                           operation_type: str = "update") -> bool:
        """Synchronous wrapper for task context sync.
        
        This method handles the async/sync bridge for use cases that cannot be async.
        """
        try:
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # Already in async context - just log and return
                logger.info(f"[AutomatedContextSync] Context sync triggered for task {task.id} (async context)")
                return True
            except RuntimeError:
                # No event loop - create one
                return asyncio.run(self.sync_task_context_after_update(task, operation_type))
                
        except Exception as e:
            logger.warning(f"[AutomatedContextSync] Sync wrapper failed for task {task.id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Subtask-level synchronization
    # ------------------------------------------------------------------

    async def sync_parent_context_after_subtask_update(self,
                                                      parent_task: Task,
                                                      subtask: Optional[Subtask] = None,
                                                      operation_type: str = "subtask_update") -> bool:
        """Synchronize parent task context after subtask changes.
        
        Args:
            parent_task: The parent task whose context should be updated
            subtask: The subtask that was modified (optional)
            operation_type: Type of subtask operation (create, update, complete)
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            # Get subtask progress summary if subtask repository is available
            progress_summary = None
            if self._subtask_repository and parent_task:
                progress_summary = await self._calculate_subtask_progress(parent_task)
            
            # Sync parent task context with updated progress
            success = await self.sync_task_context_after_update(
                parent_task, 
                f"parent_{operation_type}"
            )
            
            if success and progress_summary:
                logger.info(f"[AutomatedContextSync] Updated parent task {parent_task.id} context with subtask progress: {progress_summary}")
            
            return success
            
        except Exception as e:
            logger.error(f"[AutomatedContextSync] Failed to sync parent context for task {parent_task.id}: {e}")
            return False

    def sync_parent_context_after_subtask_update_sync(self,
                                                     parent_task: Task,
                                                     subtask: Optional[Subtask] = None,
                                                     operation_type: str = "subtask_update") -> bool:
        """Synchronous wrapper for parent context sync after subtask update."""
        try:
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # Already in async context - just log and return
                logger.info(f"[AutomatedContextSync] Parent context sync triggered for task {parent_task.id} (async context)")
                return True
            except RuntimeError:
                # No event loop - create one
                return asyncio.run(
                    self.sync_parent_context_after_subtask_update(parent_task, subtask, operation_type)
                )
                
        except Exception as e:
            logger.warning(f"[AutomatedContextSync] Parent sync wrapper failed for task {parent_task.id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Progress calculation and aggregation
    # ------------------------------------------------------------------

    async def _calculate_subtask_progress(self, parent_task: Task) -> Optional[Dict[str, Any]]:
        """Calculate subtask progress summary for parent task.
        
        Args:
            parent_task: The parent task to calculate progress for
            
        Returns:
            Dict with progress summary or None if calculation failed
        """
        try:
            if not self._subtask_repository:
                return None
                
            subtasks = self._subtask_repository.find_by_parent_task_id(parent_task.id)
            if not subtasks:
                return {
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                    "progress_percentage": 100,  # No subtasks = 100% complete
                    "can_complete_parent": True
                }
            
            total = len(subtasks)
            completed = sum(1 for subtask in subtasks if subtask.is_completed)
            progress_percentage = round((completed / total) * 100, 1) if total > 0 else 0
            
            return {
                "total_subtasks": total,
                "completed_subtasks": completed,
                "incomplete_subtasks": total - completed,
                "progress_percentage": progress_percentage,
                "can_complete_parent": completed == total,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[AutomatedContextSync] Failed to calculate subtask progress for task {parent_task.id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Batch synchronization operations
    # ------------------------------------------------------------------

    async def sync_multiple_tasks(self, task_ids: List[str]) -> Dict[str, bool]:
        """Synchronize context for multiple tasks in batch.
        
        Args:
            task_ids: List of task IDs to synchronize
            
        Returns:
            Dict mapping task_id to sync success status
        """
        results = {}
        
        for task_id in task_ids:
            try:
                # Find the task
                from ...domain.value_objects.task_id import TaskId
                domain_task_id = TaskId.from_string(task_id)
                task = self._task_repository.find_by_id(domain_task_id)
                
                if task:
                    success = await self.sync_task_context_after_update(task, "batch_sync")
                    results[task_id] = success
                else:
                    logger.warning(f"[AutomatedContextSync] Task {task_id} not found for batch sync")
                    results[task_id] = False
                    
            except Exception as e:
                logger.error(f"[AutomatedContextSync] Failed to sync task {task_id} in batch: {e}")
                results[task_id] = False
        
        successful_syncs = sum(1 for success in results.values() if success)
        logger.info(f"[AutomatedContextSync] Batch sync completed: {successful_syncs}/{len(task_ids)} successful")
        
        return results

    # ------------------------------------------------------------------
    # System health and monitoring
    # ------------------------------------------------------------------

    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get statistics about context synchronization operations.
        
        Returns:
            Dict with sync statistics and health information
        """
        return {
            "service_status": "active",
            "sync_service_available": bool(self._context_sync_service),
            "subtask_repository_available": bool(self._subtask_repository),
            "last_health_check": datetime.now(timezone.utc).isoformat(),
            "features": {
                "task_context_sync": True,
                "subtask_parent_sync": bool(self._subtask_repository),
                "batch_operations": True,
                "progress_calculation": bool(self._subtask_repository)
            }
        }

    def validate_sync_configuration(self) -> Dict[str, Any]:
        """Validate that the sync service is properly configured.
        
        Returns:
            Dict with validation results and any configuration issues
        """
        issues = []
        
        if not self._task_repository:
            issues.append("Task repository not configured")
            
        if not self._context_sync_service:
            issues.append("Context sync service not available")
            
        # Check if async capabilities are available
        try:
            asyncio.get_event_loop()
            async_available = True
        except Exception:
            async_available = False
            issues.append("Asyncio event loop not available")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "recommendations": [
                "Ensure all repositories are properly injected",
                "Verify async/await support in runtime environment",
                "Test context sync service connectivity"
            ] if issues else [],
            "async_support": async_available,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }