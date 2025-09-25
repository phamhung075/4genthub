"""Delete Branch Use Case"""

from typing import Optional, Dict, Any
import logging
import asyncio

from ...domain.services.cascade_deletion_service import CascadeDeletionService
from ...domain.interfaces.database_session import IDatabaseSessionFactory
from ...domain.interfaces.logging_service import ILoggingService


class DeleteBranchUseCase:
    """Use case for deleting a branch with cascade deletion"""

    def __init__(self,
                 task_repository,
                 subtask_repository,
                 branch_repository,
                 project_repository,
                 context_repository=None,
                 db_session_factory: Optional[IDatabaseSessionFactory] = None,
                 logging_service: Optional[ILoggingService] = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._branch_repository = branch_repository
        self._project_repository = project_repository
        self._context_repository = context_repository
        self._db_session_factory = db_session_factory
        self._logger = logging.getLogger(__name__) if not logging_service else logging_service.get_logger(__name__)

        # Initialize cascade deletion service
        self._cascade_service = CascadeDeletionService(
            task_repository=task_repository,
            subtask_repository=subtask_repository,
            branch_repository=branch_repository,
            project_repository=project_repository,
            context_repository=context_repository
        )

    def execute(self, branch_id: str) -> Dict[str, Any]:
        """
        Execute the delete branch use case with cascade deletion.

        Args:
            branch_id: ID of the branch to delete

        Returns:
            Dictionary with deletion statistics and success status
        """
        # Find the branch to get info for WebSocket notification
        branch = self._branch_repository.find_by_id(branch_id)
        if not branch:
            return {
                "success": False,
                "branch_deleted": False,
                "message": f"Branch {branch_id} not found"
            }

        # Store branch info for WebSocket notification
        project_id = branch.project_id if hasattr(branch, 'project_id') else None
        branch_name = branch.name if hasattr(branch, 'name') else "Unknown"

        # Use cascade deletion service
        stats = self._cascade_service.delete_branch_cascade(branch_id)

        # Send WebSocket notification for frontend
        if stats["branch_deleted"]:
            self._send_websocket_notification(
                branch_id=branch_id,
                project_id=project_id,
                name=branch_name,
                stats=stats
            )

            self._logger.info(
                f"Successfully deleted branch {branch_id} with cascade: "
                f"{stats['tasks_deleted']} tasks, "
                f"{stats['subtasks_deleted']} subtasks, "
                f"{stats['contexts_deleted']} contexts"
            )

        # Update project statistics after branch deletion
        if stats["branch_deleted"] and project_id:
            self._update_project_statistics(project_id)

        return {
            "success": stats["branch_deleted"],
            **stats
        }

    def _send_websocket_notification(self, branch_id: str, project_id: Optional[str],
                                    name: str, stats: Dict[str, Any]) -> None:
        """Send WebSocket notification for branch deletion."""
        try:
            # Import WebSocket service
            from ...infrastructure.websocket.websocket_service import WebSocketService

            # Create deletion notification
            notification = {
                "type": "branch_deleted",
                "branch_id": branch_id,
                "project_id": project_id,
                "name": name,
                "cascade_stats": {
                    "tasks_deleted": stats.get("tasks_deleted", 0),
                    "subtasks_deleted": stats.get("subtasks_deleted", 0),
                    "contexts_deleted": stats.get("contexts_deleted", 0)
                }
            }

            # Send via WebSocket
            websocket_service = WebSocketService()
            asyncio.create_task(websocket_service.broadcast(notification))

            self._logger.info(f"Sent WebSocket notification for branch {branch_id} deletion")

        except Exception as e:
            self._logger.warning(f"Failed to send WebSocket notification: {e}")

    def _update_project_statistics(self, project_id: str) -> None:
        """Update project statistics after branch deletion."""
        try:
            from ...domain.services.event_dispatcher import dispatch_domain_event
            from ...domain.events.project_lifecycle_events import ProjectStatisticsUpdatedEvent

            # Calculate new project statistics
            branches = self._branch_repository.find_by_project_id(project_id)
            branch_count = len(branches)

            total_tasks = 0
            completed_tasks = 0
            for branch in branches:
                branch_id = str(branch.id) if hasattr(branch, 'id') else str(branch)
                tasks = self._task_repository.find_by_git_branch_id(branch_id)
                total_tasks += len(tasks)
                completed_tasks += sum(1 for t in tasks if str(t.status) == 'done')

            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Dispatch event
            event = ProjectStatisticsUpdatedEvent.create(
                project_id=project_id,
                branch_count=branch_count,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                in_progress_tasks=total_tasks - completed_tasks,
                todo_tasks=0,
                overall_progress_percentage=progress_percentage
            )

            dispatch_domain_event("project_statistics_updated", event)
            self._logger.info(f"Updated statistics for project {project_id}")

        except Exception as e:
            self._logger.warning(f"Failed to update project statistics: {e}")