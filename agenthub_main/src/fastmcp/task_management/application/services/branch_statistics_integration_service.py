"""Branch Statistics Integration Service - Wires domain events to statistics updates"""

import logging
from typing import Optional

from ...domain.services.branch_statistics_service import BranchStatisticsService
from ...domain.services.event_dispatcher import get_event_dispatcher
from ...domain.events.task_lifecycle_events import (
    TaskCreatedEvent,
    TaskUpdatedEvent,
    TaskDeletedEvent,
    TaskStatusChangedEvent,
    TaskMovedToBranchEvent
)

logger = logging.getLogger(__name__)


class BranchStatisticsIntegrationService:
    """
    Application service that integrates branch statistics with domain events.
    This service registers event handlers and ensures branch statistics
    are updated whenever tasks change.
    """

    def __init__(self, task_repository, git_branch_repository):
        """
        Initialize the integration service.

        Args:
            task_repository: Repository for accessing tasks
            git_branch_repository: Repository for accessing branches
        """
        self._branch_statistics_service = BranchStatisticsService(
            task_repository,
            git_branch_repository
        )
        self._event_dispatcher = get_event_dispatcher()
        self._handlers_registered = False

    def register_event_handlers(self) -> None:
        """Register all event handlers for branch statistics updates."""
        if self._handlers_registered:
            logger.debug("Event handlers already registered")
            return

        dispatcher = self._event_dispatcher

        # Register handler for task creation
        dispatcher.register_handler(
            "task_created",
            self._handle_task_created
        )

        # Register handler for task updates
        dispatcher.register_handler(
            "task_updated",
            self._handle_task_updated
        )

        # Register handler for task deletion
        dispatcher.register_handler(
            "task_deleted",
            self._handle_task_deleted
        )

        # Register handler for status changes
        dispatcher.register_handler(
            "task_status_changed",
            self._handle_task_status_changed
        )

        # Register handler for branch moves
        dispatcher.register_handler(
            "task_moved_to_branch",
            self._handle_task_moved_to_branch
        )

        self._handlers_registered = True
        logger.info("Registered all branch statistics event handlers")

    def _handle_task_created(self, event: TaskCreatedEvent) -> None:
        """Handle task creation event."""
        try:
            logger.info(f"Handling task created event for task {event.task_id}")
            self._branch_statistics_service.on_task_created(
                task_id=event.task_id,
                branch_id=event.branch_id,
                status=event.status
            )
        except Exception as e:
            logger.error(f"Failed to handle task created event: {e}")

    def _handle_task_updated(self, event: TaskUpdatedEvent) -> None:
        """Handle task update event."""
        try:
            logger.info(f"Handling task updated event for task {event.task_id}")
            self._branch_statistics_service.on_task_updated(
                task_id=event.task_id,
                old_branch_id=event.old_branch_id,
                new_branch_id=event.new_branch_id or event.branch_id,
                old_status=event.old_status,
                new_status=event.new_status
            )
        except Exception as e:
            logger.error(f"Failed to handle task updated event: {e}")

    def _handle_task_deleted(self, event: TaskDeletedEvent) -> None:
        """Handle task deletion event."""
        try:
            logger.info(f"Handling task deleted event for task {event.task_id}")
            self._branch_statistics_service.on_task_deleted(
                task_id=event.task_id,
                branch_id=event.branch_id,
                status=event.status
            )
        except Exception as e:
            logger.error(f"Failed to handle task deleted event: {e}")

    def _handle_task_status_changed(self, event: TaskStatusChangedEvent) -> None:
        """Handle task status change event."""
        try:
            logger.info(
                f"Handling task status change for task {event.task_id}: "
                f"{event.old_status} -> {event.new_status}"
            )
            self._branch_statistics_service.on_task_updated(
                task_id=event.task_id,
                old_branch_id=event.branch_id,
                new_branch_id=event.branch_id,
                old_status=event.old_status,
                new_status=event.new_status
            )
        except Exception as e:
            logger.error(f"Failed to handle task status change event: {e}")

    def _handle_task_moved_to_branch(self, event: TaskMovedToBranchEvent) -> None:
        """Handle task moved to branch event."""
        try:
            logger.info(
                f"Handling task {event.task_id} moved from branch "
                f"{event.old_branch_id} to {event.new_branch_id}"
            )
            self._branch_statistics_service.on_task_updated(
                task_id=event.task_id,
                old_branch_id=event.old_branch_id,
                new_branch_id=event.new_branch_id,
                old_status=None,
                new_status=None
            )
        except Exception as e:
            logger.error(f"Failed to handle task moved to branch event: {e}")

    def recalculate_all_branches(self, project_id: Optional[str] = None) -> dict:
        """
        Recalculate statistics for all branches.

        Args:
            project_id: Optional project ID to limit recalculation

        Returns:
            Dictionary of branch statistics
        """
        return self._branch_statistics_service.recalculate_all_branches(project_id)


# Singleton instance
_integration_service = None


def get_branch_statistics_integration_service(task_repository, git_branch_repository):
    """
    Get the singleton instance of the integration service.

    Args:
        task_repository: Task repository
        git_branch_repository: Git branch repository

    Returns:
        BranchStatisticsIntegrationService instance
    """
    global _integration_service
    if _integration_service is None:
        _integration_service = BranchStatisticsIntegrationService(
            task_repository,
            git_branch_repository
        )
        _integration_service.register_event_handlers()
        logger.info("Created and initialized branch statistics integration service")
    return _integration_service