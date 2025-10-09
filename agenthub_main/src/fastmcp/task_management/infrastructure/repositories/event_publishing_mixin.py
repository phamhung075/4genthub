"""Event Publishing Mixin for Repositories

This mixin provides event publishing capabilities to repositories,
automatically publishing domain events when entities are persisted.

DDD Pattern:
- Repositories are responsible for persistence AND event publishing
- Domain events are raised by entities during business operations
- Infrastructure layer (repositories) publishes events to the event bus
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class EventPublishingMixin:
    """
    Mixin to add event publishing capabilities to repositories.

    This mixin integrates with the event bus to publish domain events
    that have been raised by entities during business operations.

    Usage:
        class TaskRepository(EventPublishingMixin, BaseRepository):
            def save(self, entity):
                # Save entity
                result = super().save(entity)
                # Publish events
                self.publish_entity_events(entity)
                return result
    """

    def __init__(self, *args, **kwargs):
        """Initialize event publishing mixin."""
        super().__init__(*args, **kwargs)
        self._event_bus = None
        self._event_publishing_enabled = True

    def enable_event_publishing(self) -> None:
        """Enable automatic event publishing after save operations."""
        self._event_publishing_enabled = True
        logger.debug("Event publishing enabled")

    def disable_event_publishing(self) -> None:
        """Disable automatic event publishing (useful for testing/migration)."""
        self._event_publishing_enabled = False
        logger.debug("Event publishing disabled")

    def is_event_publishing_enabled(self) -> bool:
        """Check if event publishing is enabled."""
        return self._event_publishing_enabled

    def get_event_bus(self):
        """
        Get the event bus instance (lazy loading).

        Returns:
            EventBus instance
        """
        if self._event_bus is None:
            from ...infrastructure.event_bus import get_event_bus
            self._event_bus = get_event_bus()
        return self._event_bus

    def set_event_bus(self, event_bus) -> None:
        """
        Set a custom event bus (useful for testing).

        Args:
            event_bus: Custom EventBus instance
        """
        self._event_bus = event_bus
        logger.debug(f"Custom event bus configured: {event_bus}")

    async def publish_entity_events_async(self, entity: Any) -> int:
        """
        Publish all domain events raised by an entity (async version).

        This method extracts events from the entity and publishes them
        to the event bus for async processing by event handlers.

        Args:
            entity: Domain entity with events to publish

        Returns:
            Number of events published
        """
        if not self._event_publishing_enabled:
            logger.debug("Event publishing is disabled, skipping")
            return 0

        # Check if entity has events
        if not hasattr(entity, 'get_events'):
            logger.debug(f"Entity {type(entity).__name__} does not support events")
            return 0

        # Get events from entity
        events = entity.get_events()
        if not events:
            logger.debug(f"No events to publish for entity {type(entity).__name__}")
            return 0

        # Get event bus
        event_bus = self.get_event_bus()

        # Publish each event
        published_count = 0
        for event in events:
            try:
                await event_bus.publish(event)
                logger.debug(
                    f"Published event {type(event).__name__} for "
                    f"entity {type(entity).__name__}"
                )
                published_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to publish event {type(event).__name__}: {e}",
                    exc_info=True
                )
                # Continue publishing other events even if one fails

        return published_count

    def publish_entity_events(self, entity: Any) -> int:
        """
        Publish all domain events raised by an entity (sync version).

        This is a synchronous wrapper around async publish for compatibility
        with existing synchronous repository methods.

        Args:
            entity: Domain entity with events to publish

        Returns:
            Number of events published
        """
        if not self._event_publishing_enabled:
            logger.debug("Event publishing is disabled, skipping")
            return 0

        # Check if entity has events
        if not hasattr(entity, 'get_events'):
            logger.debug(f"Entity {type(entity).__name__} does not support events")
            return 0

        # Get events from entity (this also clears them)
        events = entity.get_events()
        if not events:
            logger.debug(f"No events to publish for entity {type(entity).__name__}")
            return 0

        # Get event bus
        event_bus = self.get_event_bus()

        # Publish each event synchronously
        published_count = 0
        for event in events:
            try:
                event_bus.publish_sync(event)
                logger.debug(
                    f"Published event {type(event).__name__} for "
                    f"entity {type(entity).__name__}"
                )
                published_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to publish event {type(event).__name__}: {e}",
                    exc_info=True
                )
                # Continue publishing other events even if one fails

        return published_count

    def publish_events_batch(self, entities: List[Any]) -> int:
        """
        Publish events from multiple entities in batch.

        Args:
            entities: List of domain entities with events

        Returns:
            Total number of events published
        """
        if not self._event_publishing_enabled:
            logger.debug("Event publishing is disabled, skipping batch")
            return 0

        total_published = 0
        for entity in entities:
            total_published += self.publish_entity_events(entity)

        logger.info(f"Published {total_published} events from {len(entities)} entities")
        return total_published
