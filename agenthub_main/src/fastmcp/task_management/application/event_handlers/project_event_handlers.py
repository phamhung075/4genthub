"""
Event handlers for project lifecycle events.

This module processes project-related domain events, maintains project health,
tracks statistics, and triggers project-level workflows.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ...domain.events.base import BaseDomainEvent
from ...domain.events.project_lifecycle_events import (
    ProjectArchived,
    ProjectCreatedEvent,
    ProjectDeletedEvent,
    ProjectHealthChanged,
    ProjectStatisticsUpdatedEvent,
    ProjectUpdatedEvent,
)
from ...infrastructure.event_store import EventStore

logger = logging.getLogger(__name__)


class ProjectEventHandlers:
    """
    Handles project-related domain events.

    Processes events to maintain project health, track statistics,
    manage lifecycle, and trigger project-level workflows.
    """

    def __init__(
        self,
        event_store: EventStore,
        project_repository: Any | None = None,
        notification_service: Any | None = None,
        analytics_service: Any | None = None,
    ):
        self.event_store = event_store
        self.project_repository = project_repository
        self.notification_service = notification_service
        self.analytics_service = analytics_service

        # Project statistics tracking
        self.project_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "created_at": None,
                "total_tasks": 0,
                "completed_tasks": 0,
                "active_tasks": 0,
                "total_branches": 0,
                "total_agents": 0,
                "updates": 0,
                "health_changes": 0,
            }
        )

        # Health tracking
        self.health_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Archive tracking
        self.archived_projects: dict[str, dict[str, Any]] = {}

    async def handle_project_created(self, event: ProjectCreatedEvent) -> None:
        """
        Handle project created event.

        Initializes project tracking and notifies stakeholders.
        """
        logger.info(
            f"Project created: {event.project_id} - '{event.project_name}' "
            f"by {event.created_by}"
        )

        # Initialize statistics
        project_key = str(event.project_id)
        self.project_stats[project_key].update(
            {
                "created_at": event.occurred_at,
                "name": event.project_name,
                "created_by": event.created_by,
                "description": getattr(event, "description", ""),
            }
        )

        # Initialize health tracking
        self.health_history[project_key].append(
            {
                "status": "healthy",
                "score": 100.0,
                "timestamp": event.occurred_at.isoformat(),
                "reason": "Project initialized",
            }
        )

        # Send notifications
        if self.notification_service:
            await self.notification_service.notify_project_created(
                project_id=event.project_id,
                project_name=event.project_name,
                created_by=event.created_by,
            )

        # Initialize analytics tracking
        if self.analytics_service:
            await self.analytics_service.start_project_tracking(
                project_id=event.project_id,
                metadata={
                    "name": event.project_name,
                    "created_at": event.occurred_at.isoformat(),
                    "created_by": event.created_by,
                },
            )

    async def handle_project_updated(self, event: ProjectUpdatedEvent) -> None:
        """
        Handle project updated event.

        Tracks changes and triggers relevant workflows.
        """
        logger.info(
            f"Project updated: {event.project_id} - "
            f"Changed fields: {', '.join(event.changed_fields)}"
        )

        # Update statistics
        project_key = str(event.project_id)
        self.project_stats[project_key]["updates"] += 1
        self.project_stats[project_key]["last_updated"] = event.occurred_at

        # Track significant changes
        significant_fields = ["name", "status", "owner", "due_date"]
        significant_changes = [
            f for f in event.changed_fields if f in significant_fields
        ]

        if significant_changes and self.notification_service:
            await self.notification_service.notify_project_updated(
                project_id=event.project_id,
                changed_fields=significant_changes,
                previous_values=event.previous_values,
                new_values=event.new_values,
                updated_by=event.updated_by,
            )

        # Update analytics
        if self.analytics_service:
            await self.analytics_service.track_project_update(
                project_id=event.project_id, changes=event.changed_fields
            )

    async def handle_project_deleted(self, event: ProjectDeletedEvent) -> None:
        """
        Handle project deleted event.

        Archives project data and notifies stakeholders.
        """
        logger.info(f"Project deleted: {event.project_id} by {event.deleted_by}")

        project_key = str(event.project_id)

        # Archive project data
        if project_key in self.project_stats:
            archived_data = {
                **self.project_stats[project_key],
                "deleted_at": event.occurred_at,
                "deleted_by": event.deleted_by,
                "health_history": self.health_history.get(project_key, []),
            }
            self.archived_projects[project_key] = archived_data

            # Remove from active tracking
            del self.project_stats[project_key]
            if project_key in self.health_history:
                del self.health_history[project_key]

        # Notify stakeholders
        if self.notification_service:
            await self.notification_service.notify_project_deleted(
                project_id=event.project_id, deleted_by=event.deleted_by
            )

        # Finalize analytics
        if self.analytics_service:
            await self.analytics_service.finalize_project_tracking(
                project_id=event.project_id, deleted_at=event.occurred_at
            )

    async def handle_project_statistics_updated(
        self, event: ProjectStatisticsUpdatedEvent
    ) -> None:
        """
        Handle project statistics updated event.

        Updates metrics and triggers health checks.
        """
        logger.info(
            f"Project statistics updated: {event.project_id} - "
            f"Branches: {event.branch_count}, Tasks: {event.total_tasks} (completed: {event.completed_tasks})"
        )

        project_key = str(event.project_id)

        # Update statistics
        self.project_stats[project_key].update(
            {
                "branch_count": event.branch_count,
                "total_tasks": event.total_tasks,
                "completed_tasks": event.completed_tasks,
                "active_tasks": event.active_tasks,
                "completion_rate": event.overall_progress_percentage / 100.0,
                "stats_updated_at": event.occurred_at,
            }
        )

        # Persist updated statistics to database (not just in-memory)
        if self.project_repository:
            try:
                self.project_repository.update_statistics(
                    project_id=str(event.project_id),
                    branch_count=event.branch_count,
                    task_count=event.total_tasks,
                    completed_tasks=event.completed_tasks,
                    in_progress_tasks=event.in_progress_tasks,
                    todo_tasks=event.todo_tasks,
                    progress_percentage=event.overall_progress_percentage,
                )
                logger.info(
                    f"Persisted project {event.project_id} statistics to database"
                )
            except Exception as db_error:
                logger.warning(
                    f"Failed to persist project statistics to database: {db_error}"
                )

        # Send WebSocket notification to update frontend cache
        try:
            from ...application.services.websocket_notification_service import (
                WebSocketNotificationService,
            )

            await WebSocketNotificationService.broadcast_project_event(
                event_type="updated",
                project_id=str(event.project_id),
                user_id=event.user_id
                if hasattr(event, "user_id") and event.user_id
                else "system",
                project_data={
                    "id": str(event.project_id),
                    "branch_count": event.branch_count,
                    "task_count": event.total_tasks,
                    "completed_tasks": event.completed_tasks,
                    "in_progress_tasks": event.in_progress_tasks,
                    "todo_tasks": event.todo_tasks,
                    "progress_percentage": event.overall_progress_percentage,
                },
            )
            logger.info(
                f"✅ Sent WebSocket notification for project {event.project_id} statistics update"
            )
        except Exception as ws_error:
            logger.warning(
                f"Failed to send WebSocket notification for project statistics: {ws_error}"
            )

        # Check if health assessment is needed
        await self._assess_project_health(event.project_id, event)

        # Update analytics dashboard
        if self.analytics_service:
            await self.analytics_service.update_project_metrics(
                project_id=event.project_id,
                metrics={
                    "total_tasks": event.total_tasks,
                    "completed_tasks": event.completed_tasks,
                    "active_tasks": event.active_tasks,
                    "completion_percentage": event.overall_progress_percentage,
                },
            )

    async def handle_project_health_changed(self, event: ProjectHealthChanged) -> None:
        """
        Handle project health changed event.

        Tracks health trends and triggers interventions.
        """
        logger.info(
            f"Project health changed: {event.project_id} - "
            f"{event.previous_health_status} → {event.new_health_status} "
            f"(score: {event.health_score:.2f})"
        )

        project_key = str(event.project_id)
        self.project_stats[project_key]["health_changes"] += 1

        # Record health history
        health_record = {
            "status": event.new_health_status,
            "score": event.health_score,
            "previous_status": event.previous_health_status,
            "timestamp": event.occurred_at.isoformat(),
            "indicators": event.health_indicators,
            "issues": event.identified_issues,
        }
        self.health_history[project_key].append(health_record)

        # Keep only last 50 health records
        if len(self.health_history[project_key]) > 50:
            self.health_history[project_key] = self.health_history[project_key][-50:]

        # Trigger interventions based on health degradation
        if event.new_health_status in ["at_risk", "critical"]:
            await self._trigger_health_intervention(event)

        # Notify stakeholders of significant changes
        if event.previous_health_status != event.new_health_status:
            if self.notification_service:
                await self.notification_service.notify_project_health_changed(
                    project_id=event.project_id,
                    previous_status=event.previous_health_status,
                    new_status=event.new_health_status,
                    health_score=event.health_score,
                    issues=event.identified_issues,
                )

    async def handle_project_archived(self, event: ProjectArchived) -> None:
        """
        Handle project archived event.

        Preserves project data and updates access permissions.
        """
        logger.info(
            f"Project archived: {event.project_id} by {event.archived_by} "
            f"(reason: {event.archive_reason})"
        )

        project_key = str(event.project_id)

        # Archive project data
        if project_key in self.project_stats:
            archived_data = {
                **self.project_stats[project_key],
                "archived_at": event.occurred_at,
                "archived_by": event.archived_by,
                "archive_reason": event.archive_reason,
                "final_health_history": self.health_history.get(project_key, []),
            }
            self.archived_projects[project_key] = archived_data

            # Mark as archived in active stats
            self.project_stats[project_key]["archived"] = True
            self.project_stats[project_key]["archived_at"] = event.occurred_at

        # Notify stakeholders
        if self.notification_service:
            await self.notification_service.notify_project_archived(
                project_id=event.project_id,
                archived_by=event.archived_by,
                reason=event.archive_reason,
            )

        # Archive analytics data
        if self.analytics_service:
            await self.analytics_service.archive_project_data(
                project_id=event.project_id, archived_at=event.occurred_at
            )

    async def _assess_project_health(
        self, project_id: UUID, stats_event: ProjectStatisticsUpdatedEvent
    ) -> None:
        """
        Assess project health based on current statistics.

        Args:
            project_id: The project ID
            stats_event: The statistics update event
        """
        project_key = str(project_id)
        current_health = (
            self.health_history[project_key][-1]
            if self.health_history[project_key]
            else None
        )

        # Calculate health score based on multiple factors
        health_score = 100.0
        indicators = []
        issues = []

        # Factor 1: Completion rate
        completion_rate = stats_event.completion_percentage / 100.0
        if completion_rate < 0.2:
            health_score -= 20
            issues.append("Low completion rate")
        indicators.append(f"Completion: {stats_event.completion_percentage:.1f}%")

        # Factor 2: Active tasks ratio
        if stats_event.total_tasks > 0:
            active_ratio = stats_event.active_tasks / stats_event.total_tasks
            if active_ratio > 0.8:
                health_score -= 15
                issues.append("Too many active tasks")
            indicators.append(f"Active ratio: {active_ratio:.1%}")

        # Factor 3: Task velocity (if we have history)
        if current_health and "score" in current_health:
            # Check if health is declining
            if health_score < current_health["score"] - 10:
                issues.append("Health declining")

        # Determine health status
        if health_score >= 80:
            health_status = "healthy"
        elif health_score >= 60:
            health_status = "stable"
        elif health_score >= 40:
            health_status = "at_risk"
        else:
            health_status = "critical"

        # If health changed, create event
        if not current_health or current_health["status"] != health_status:
            health_event = ProjectHealthChanged(
                aggregate_id=project_id,
                occurred_at=datetime.now(UTC),
                user_id="system_health_check",
                project_id=project_id,
                previous_health_status=current_health["status"]
                if current_health
                else "unknown",
                new_health_status=health_status,
                health_score=health_score,
                health_indicators=indicators,
                identified_issues=issues,
            )

            await self.event_store.append(health_event)
            await self.handle_project_health_changed(health_event)

    async def _trigger_health_intervention(self, event: ProjectHealthChanged) -> None:
        """
        Trigger intervention workflows for unhealthy projects.

        Args:
            event: The health changed event
        """
        logger.warning(
            f"Triggering health intervention for project {event.project_id} "
            f"(status: {event.new_health_status}, issues: {', '.join(event.identified_issues)})"
        )

        # Notify project owner/admin
        if self.notification_service:
            await self.notification_service.send_health_alert(
                project_id=event.project_id,
                health_status=event.new_health_status,
                health_score=event.health_score,
                issues=event.identified_issues,
                urgency="high" if event.new_health_status == "critical" else "medium",
            )

        # Suggest corrective actions based on issues
        suggestions = []
        for issue in event.identified_issues:
            if "completion rate" in issue.lower():
                suggestions.append(
                    "Consider reviewing task priorities and removing blockers"
                )
            elif "active tasks" in issue.lower():
                suggestions.append(
                    "Consider completing or postponing some active tasks"
                )
            elif "declining" in issue.lower():
                suggestions.append("Review recent changes and identify root causes")

        if suggestions and self.notification_service:
            await self.notification_service.send_health_suggestions(
                project_id=event.project_id, suggestions=suggestions
            )

    async def get_project_statistics(
        self, project_id: UUID | None = None
    ) -> dict[str, Any]:
        """
        Get project statistics for a specific project or all projects.

        Args:
            project_id: Optional project ID to filter statistics

        Returns:
            Dictionary containing project statistics
        """
        if project_id:
            project_key = str(project_id)
            stats = self.project_stats.get(project_key, {})
            health = self.health_history.get(project_key, [])

            return {
                "project_id": project_key,
                "statistics": dict(stats),
                "current_health": health[-1] if health else None,
                "health_history": health[-10:] if health else [],
            }

        # Aggregate across all projects
        active_projects = {
            k: v for k, v in self.project_stats.items() if not v.get("archived", False)
        }

        return {
            "total_projects": len(self.project_stats),
            "active_projects": len(active_projects),
            "archived_projects": len(self.archived_projects),
            "summary": {
                "total_tasks": sum(
                    p.get("total_tasks", 0) for p in active_projects.values()
                ),
                "completed_tasks": sum(
                    p.get("completed_tasks", 0) for p in active_projects.values()
                ),
                "average_completion_rate": (
                    sum(p.get("completion_rate", 0) for p in active_projects.values())
                    / max(len(active_projects), 1)
                )
                if active_projects
                else 0.0,
                "projects_at_risk": len(
                    [
                        p
                        for p in self.health_history.values()
                        if p and p[-1].get("status") in ["at_risk", "critical"]
                    ]
                ),
            },
            "by_project": {k: dict(v) for k, v in active_projects.items()},
        }

    async def get_archived_projects(self) -> dict[str, Any]:
        """Get all archived projects."""
        return {
            "total_archived": len(self.archived_projects),
            "projects": self.archived_projects,
        }

    async def process_event(self, event: BaseDomainEvent) -> None:
        """
        Process a domain event.

        Routes events to appropriate handlers.
        """
        handlers = {
            "project_created": self.handle_project_created,
            "project_updated": self.handle_project_updated,
            "project_deleted": self.handle_project_deleted,
            "project_statistics_updated": self.handle_project_statistics_updated,
            "project_health_changed": self.handle_project_health_changed,
            "project_archived": self.handle_project_archived,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"No handler for event type: {event.event_type}")
