"""Event Handler Initializer

This module initializes and registers all domain event handlers with the event bus on application startup.

DDD Pattern:
- Event handlers are registered once during application initialization
- Handlers listen for specific event types and react accordingly
- Loose coupling between domain entities and cross-cutting concerns
"""

import logging

from ...application.event_handlers.agent_event_handlers import AgentEventHandlers
from ...application.event_handlers.project_event_handlers import ProjectEventHandlers
from ...application.event_handlers.task_event_handlers import TaskEventHandlers
from ...domain.events.agent_events import (
    AgentAssigned,
    AgentPerformanceEvaluated,
    AgentUnassigned,
    AgentWorkloadChanged,
    ConflictDetected,
    ConflictResolved,
    WorkHandoffAccepted,
    WorkHandoffRequested,
)
from ...domain.events.project_lifecycle_events import (
    ProjectArchived,
    ProjectCreatedEvent,
    ProjectDeletedEvent,
    ProjectHealthChanged,
    ProjectStatisticsUpdatedEvent,
    ProjectUpdatedEvent,
)
from ...domain.events.task_lifecycle_events import (
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskMovedToBranchEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)

logger = logging.getLogger(__name__)


class EventHandlerInitializer:
    """
    Initializes and registers all domain event handlers with the event bus.

    This class follows the DDD pattern of separating event registration
    from event handling logic, ensuring clean architecture boundaries.
    """

    _initialized = False
    _event_handlers_registered = 0

    @classmethod
    def initialize(cls) -> bool:
        """
        Initialize all event handlers and register them with the event bus.

        This method should be called once during application startup.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if cls._initialized:
            logger.info("Event handlers already initialized, skipping")
            return True

        try:
            logger.info("Initializing domain event handlers...")

            # Get event bus instance
            from ..event_bus import get_event_bus

            event_bus = get_event_bus()

            # Get event store instance
            from ..event_store import get_event_store

            event_store = get_event_store()

            # Initialize handler instances with required dependencies
            task_handlers = TaskEventHandlers(event_store=event_store)
            agent_handlers = AgentEventHandlers(event_store=event_store)
            project_handlers = ProjectEventHandlers(event_store=event_store)

            # Register task event handlers
            cls._register_task_handlers(event_bus, task_handlers)

            # Register agent event handlers
            cls._register_agent_handlers(event_bus, agent_handlers)

            # Register project event handlers
            cls._register_project_handlers(event_bus, project_handlers)

            cls._initialized = True
            logger.info(
                f"✅ Event handler initialization complete: {cls._event_handlers_registered} handlers registered"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize event handlers: {e}", exc_info=True)
            return False

    @classmethod
    def _register_task_handlers(cls, event_bus, handlers: TaskEventHandlers) -> None:
        """Register all task event handlers."""
        logger.debug("Registering task event handlers...")

        # Task lifecycle events
        event_bus.subscribe(TaskCreatedEvent, handlers.handle_task_created, priority=10)
        cls._event_handlers_registered += 1

        event_bus.subscribe(TaskUpdatedEvent, handlers.handle_task_updated, priority=10)
        cls._event_handlers_registered += 1

        event_bus.subscribe(TaskDeletedEvent, handlers.handle_task_deleted, priority=10)
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            TaskStatusChangedEvent, handlers.handle_task_status_changed, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            TaskCompletedEvent, handlers.handle_task_completed, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            TaskMovedToBranchEvent, handlers.handle_task_moved_to_branch, priority=10
        )
        cls._event_handlers_registered += 1

        logger.debug("Registered 6 task event handlers")

    @classmethod
    def _register_agent_handlers(cls, event_bus, handlers: AgentEventHandlers) -> None:
        """Register all agent event handlers."""
        logger.debug("Registering agent event handlers...")

        # Agent assignment events
        event_bus.subscribe(AgentAssigned, handlers.handle_agent_assigned, priority=10)
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            AgentUnassigned, handlers.handle_agent_unassigned, priority=10
        )
        cls._event_handlers_registered += 1

        # Agent workload events
        event_bus.subscribe(
            AgentWorkloadChanged, handlers.handle_agent_workload_changed, priority=10
        )
        cls._event_handlers_registered += 1

        # Agent collaboration/handoff events
        event_bus.subscribe(
            WorkHandoffRequested, handlers.handle_work_handoff_requested, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            WorkHandoffAccepted, handlers.handle_work_handoff_accepted, priority=10
        )
        cls._event_handlers_registered += 1

        # Agent conflict events
        event_bus.subscribe(
            ConflictDetected, handlers.handle_conflict_detected, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ConflictResolved, handlers.handle_conflict_resolved, priority=10
        )
        cls._event_handlers_registered += 1

        # Agent performance events
        event_bus.subscribe(
            AgentPerformanceEvaluated,
            handlers.handle_agent_performance_evaluated,
            priority=10,
        )
        cls._event_handlers_registered += 1

        logger.debug("Registered 8 agent event handlers")

    @classmethod
    def _register_project_handlers(
        cls, event_bus, handlers: ProjectEventHandlers
    ) -> None:
        """Register all project event handlers."""
        logger.debug("Registering project event handlers...")

        # Project lifecycle events
        event_bus.subscribe(
            ProjectCreatedEvent, handlers.handle_project_created, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ProjectUpdatedEvent, handlers.handle_project_updated, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ProjectDeletedEvent, handlers.handle_project_deleted, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ProjectArchived, handlers.handle_project_archived, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ProjectHealthChanged, handlers.handle_project_health_changed, priority=10
        )
        cls._event_handlers_registered += 1

        event_bus.subscribe(
            ProjectStatisticsUpdatedEvent,
            handlers.handle_project_statistics_updated,
            priority=10,
        )
        cls._event_handlers_registered += 1

        logger.debug("Registered 6 project event handlers")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if event handlers have been initialized."""
        return cls._initialized

    @classmethod
    def get_handler_count(cls) -> int:
        """Get the number of registered event handlers."""
        return cls._event_handlers_registered

    @classmethod
    def reset(cls) -> None:
        """Reset initialization state (mainly for testing)."""
        cls._initialized = False
        cls._event_handlers_registered = 0
        logger.debug("Event handler initializer reset")


def initialize_event_handlers() -> bool:
    """
    Convenience function to initialize event handlers.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    return EventHandlerInitializer.initialize()
