"""
Event handlers for task lifecycle events.

This module processes task-related domain events, maintains statistics,
updates metrics, and triggers follow-up actions.
"""

import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from ...domain.events.base import BaseDomainEvent
from ...domain.events.task_lifecycle_events import (
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskMovedToBranchEvent,
    TaskRetrievedEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from ...infrastructure.event_store import EventStore

logger = logging.getLogger(__name__)


class TaskEventHandlers:
    """
    Handles task-related domain events.

    Processes events to maintain statistics, update metrics,
    track task lifecycle, and trigger workflow actions.
    """

    def __init__(
        self,
        event_store: EventStore,
        task_repository: Any | None = None,
        notification_service: Any | None = None
    ):
        self.event_store = event_store
        self.task_repository = task_repository
        self.notification_service = notification_service

        # Statistics tracking
        self.task_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "created": 0,
                "updated": 0,
                "completed": 0,
                "deleted": 0,
                "status_changes": 0,
                "moved": 0
            }
        )

        # Status transition tracking
        self.status_transitions: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Completion time tracking
        self.completion_times: list[float] = []

    async def handle_task_created(self, event: TaskCreatedEvent) -> None:
        """
        Handle task created event.

        Updates statistics, notifies stakeholders, and initializes tracking.
        """
        logger.info(
            f"Task created: {event.task_id} - '{event.title}' "
            f"(priority: {event.priority}, status: {event.status})"
        )

        # Update statistics by project
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["created"] += 1

        # Send notifications to assignees
        if self.notification_service and hasattr(event, 'assignees'):
            for assignee in event.assignees:
                await self.notification_service.notify_task_assignment(
                    assignee=assignee,
                    task_id=event.task_id,
                    title=event.title,
                    priority=event.priority
                )

        # Initialize task tracking
        if self.task_repository:
            await self.task_repository.track_task_creation(event)

    async def handle_task_updated(self, event: TaskUpdatedEvent) -> None:
        """
        Handle task updated event.

        Tracks changes, updates metrics, and triggers notifications.
        """
        logger.info(
            f"Task updated: {event.task_id} - "
            f"Changed fields: {', '.join(event.changed_fields)}"
        )

        # Update statistics
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["updated"] += 1

        # Track significant changes
        significant_fields = ['status', 'priority', 'assignees', 'due_date']
        significant_changes = [f for f in event.changed_fields if f in significant_fields]

        if significant_changes and self.notification_service:
            await self.notification_service.notify_task_updated(
                task_id=event.task_id,
                changed_fields=significant_changes,
                previous_values=event.previous_values,
                new_values=event.new_values
            )

    async def handle_task_deleted(self, event: TaskDeletedEvent) -> None:
        """
        Handle task deleted event.

        Updates statistics, archives data, and notifies stakeholders.
        """
        logger.info(
            f"Task deleted: {event.task_id} "
            f"(reason: {event.reason if hasattr(event, 'reason') else 'not specified'})"
        )

        # Update statistics
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["deleted"] += 1

        # Archive task data
        if self.task_repository:
            await self.task_repository.archive_task(event.task_id, event.occurred_at)

        # Notify stakeholders
        if self.notification_service:
            await self.notification_service.notify_task_deleted(
                task_id=event.task_id,
                deleted_by=event.user_id
            )

    async def handle_task_status_changed(self, event: TaskStatusChangedEvent) -> None:
        """
        Handle task status changed event.

        Tracks status transitions, calculates metrics, and triggers workflows.
        """
        logger.info(
            f"Task status changed: {event.task_id} - "
            f"{event.previous_status} → {event.new_status}"
        )

        # Update statistics
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["status_changes"] += 1

        # Track status transition
        transition = {
            "task_id": str(event.task_id),
            "from": event.previous_status,
            "to": event.new_status,
            "timestamp": event.occurred_at.isoformat(),
            "user": event.user_id
        }
        self.status_transitions[str(event.task_id)].append(transition)

        # Trigger workflow actions based on new status
        if event.new_status == "in_progress":
            await self._handle_task_started(event)
        elif event.new_status == "blocked":
            await self._handle_task_blocked(event)
        elif event.new_status == "review":
            await self._handle_task_needs_review(event)

    async def handle_task_completed(self, event: TaskCompletedEvent) -> None:
        """
        Handle task completed event.

        Calculates completion time, updates metrics, and triggers celebrations.
        """
        logger.info(
            f"Task completed: {event.task_id} - '{event.title}' "
            f"(completion time: {event.completion_time_seconds}s)"
        )

        # Update statistics
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["completed"] += 1

        # Track completion time
        if event.completion_time_seconds:
            self.completion_times.append(event.completion_time_seconds)

        # Calculate completion metrics
        if len(self.completion_times) >= 5:
            avg_completion = sum(self.completion_times[-10:]) / min(len(self.completion_times), 10)
            logger.info(f"Average completion time (last 10): {avg_completion:.2f}s")

        # Notify stakeholders
        if self.notification_service:
            await self.notification_service.notify_task_completed(
                task_id=event.task_id,
                title=event.title,
                completed_by=event.user_id,
                completion_time=event.completion_time_seconds
            )

        # Check for dependent tasks that can now start
        if self.task_repository:
            dependent_tasks = await self.task_repository.get_dependent_tasks(event.task_id)
            for dep_task in dependent_tasks:
                await self._check_dependencies_and_notify(dep_task)

    async def handle_task_retrieved(self, event: TaskRetrievedEvent) -> None:
        """
        Handle task retrieved event.

        Tracks access patterns for analytics.
        """
        logger.debug(
            f"Task retrieved: {event.task_id} by {event.user_id}"
        )

        # Track access patterns (for analytics)
        if self.task_repository:
            await self.task_repository.track_task_access(
                task_id=event.task_id,
                user_id=event.user_id,
                accessed_at=event.occurred_at
            )

    async def handle_task_moved_to_branch(self, event: TaskMovedToBranchEvent) -> None:
        """
        Handle task moved to branch event.

        Updates branch metrics and notifies relevant parties.
        """
        logger.info(
            f"Task moved: {event.task_id} from branch {event.previous_branch_id} "
            f"to {event.new_branch_id}"
        )

        # Update statistics
        project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
        self.task_stats[project_key]["moved"] += 1

        # Notify affected branch members
        if self.notification_service:
            await self.notification_service.notify_task_moved(
                task_id=event.task_id,
                previous_branch=event.previous_branch_id,
                new_branch=event.new_branch_id,
                moved_by=event.user_id
            )

    async def _handle_task_started(self, event: TaskStatusChangedEvent) -> None:
        """Handle workflow when task is started."""
        logger.info(f"Task started workflow triggered for {event.task_id}")

        if self.notification_service:
            await self.notification_service.notify_task_started(
                task_id=event.task_id,
                started_by=event.user_id
            )

    async def _handle_task_blocked(self, event: TaskStatusChangedEvent) -> None:
        """Handle workflow when task is blocked."""
        logger.warning(f"Task blocked workflow triggered for {event.task_id}")

        if self.notification_service:
            await self.notification_service.notify_task_blocked(
                task_id=event.task_id,
                blocked_by=event.user_id,
                urgent=True
            )

    async def _handle_task_needs_review(self, event: TaskStatusChangedEvent) -> None:
        """Handle workflow when task needs review."""
        logger.info(f"Task review workflow triggered for {event.task_id}")

        if self.notification_service:
            await self.notification_service.notify_task_needs_review(
                task_id=event.task_id,
                submitted_by=event.user_id
            )

    async def _check_dependencies_and_notify(self, task_id: UUID) -> None:
        """Check if all dependencies are complete and notify if ready."""
        if not self.task_repository:
            return

        dependencies = await self.task_repository.get_task_dependencies(task_id)
        all_complete = all(dep.status == "done" for dep in dependencies)

        if all_complete and self.notification_service:
            await self.notification_service.notify_task_ready(
                task_id=task_id,
                message="All dependencies completed, task is ready to start"
            )

    async def get_task_statistics(self, project_id: UUID | None = None) -> dict[str, Any]:
        """
        Get task statistics for a project or all projects.

        Args:
            project_id: Optional project ID to filter statistics

        Returns:
            Dictionary containing task statistics
        """
        if project_id:
            project_key = str(project_id)
            stats = self.task_stats.get(project_key, {})
            return {
                "project_id": project_key,
                "statistics": dict(stats)
            }

        # Aggregate across all projects
        total_stats = {
            "created": sum(s.get("created", 0) for s in self.task_stats.values()),
            "updated": sum(s.get("updated", 0) for s in self.task_stats.values()),
            "completed": sum(s.get("completed", 0) for s in self.task_stats.values()),
            "deleted": sum(s.get("deleted", 0) for s in self.task_stats.values()),
            "status_changes": sum(s.get("status_changes", 0) for s in self.task_stats.values()),
            "moved": sum(s.get("moved", 0) for s in self.task_stats.values()),
        }

        # Calculate completion rate
        if total_stats["created"] > 0:
            total_stats["completion_rate"] = (
                total_stats["completed"] / total_stats["created"]
            )
        else:
            total_stats["completion_rate"] = 0.0

        # Add average completion time
        if self.completion_times:
            total_stats["avg_completion_time_seconds"] = (
                sum(self.completion_times) / len(self.completion_times)
            )

        return {
            "summary": total_stats,
            "by_project": {k: dict(v) for k, v in self.task_stats.items()}
        }

    async def process_event(self, event: BaseDomainEvent) -> None:
        """
        Process a domain event.

        Routes events to appropriate handlers.
        """
        handlers = {
            "task_created": self.handle_task_created,
            "task_updated": self.handle_task_updated,
            "task_deleted": self.handle_task_deleted,
            "task_status_changed": self.handle_task_status_changed,
            "task_completed": self.handle_task_completed,
            "task_retrieved": self.handle_task_retrieved,
            "task_moved_to_branch": self.handle_task_moved_to_branch,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"No handler for event type: {event.event_type}")
