"""Base Timestamp Repository with Clean Architecture Integration

This module provides the base repository pattern for entities that inherit from
BaseTimestampEntity. It integrates automatic timestamp handling with the existing
ORM repository infrastructure.

Key Features:
- Automatic timestamp management through BaseTimestampEntity integration
- Domain event publishing for timestamp changes
- Clean architecture compliance
- Extends existing BaseORMRepository patterns
- NO manual timestamp handling required

NO LEGACY SUPPORT:
- No manual timestamp methods
- No fallback mechanisms
- Clean implementation only
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base_orm_repository import BaseORMRepository
from ...domain.entities.base.base_timestamp_entity import BaseTimestampEntity
from ...domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)

logger = logging.getLogger(__name__)

# Type variable for BaseTimestampEntity subclasses
TimestampEntityType = TypeVar("TimestampEntityType", bound=BaseTimestampEntity)


class BaseTimestampRepository(BaseORMRepository[TimestampEntityType]):
    """Base repository for entities that inherit from BaseTimestampEntity.

    This repository extends BaseORMRepository with automatic timestamp management
    and domain event publishing. All timestamp entities should use this as their
    repository base class.

    Features:
    - Automatic timestamp handling through BaseTimestampEntity
    - Domain event collection and publishing
    - Integration with existing ORM patterns
    - Clean save/update methods with timestamp awareness
    - Proper transaction handling with event publishing

    Usage:
        class TaskRepository(BaseTimestampRepository[Task]):
            def __init__(self):
                super().__init__(TaskModel)  # SQLAlchemy model
    """

    def __init__(self, model_class: Type[TimestampEntityType]):
        """Initialize timestamp repository.

        Args:
            model_class: SQLAlchemy model class that represents a BaseTimestampEntity
        """
        super().__init__(model_class)
        logger.debug(f"Initialized BaseTimestampRepository for {model_class.__name__}")

    def save(self, entity: TimestampEntityType, flush: bool = True) -> TimestampEntityType:
        """Save entity with automatic timestamp management.

        This method handles both new entities (INSERT) and existing entities (UPDATE).
        Timestamps are managed automatically through BaseTimestampEntity and SQLAlchemy events.

        Args:
            entity: BaseTimestampEntity to save
            flush: Whether to flush changes immediately

        Returns:
            TimestampEntityType: The saved entity with updated timestamps

        Raises:
            ValidationException: If entity validation fails
            DatabaseException: If database operation fails
        """
        try:
            with self.get_db_session() as session:
                # Check if this is a new entity or an update
                is_new_entity = not hasattr(entity, 'id') or entity.id is None

                if is_new_entity:
                    logger.debug(f"Saving new {entity.__class__.__name__}")
                    # Entity timestamps will be set by SQLAlchemy events
                    session.add(entity)
                else:
                    logger.debug(f"Updating existing {entity.__class__.__name__} with id {entity.id}")
                    # Touch the entity to update timestamp and fire events
                    entity.touch(f"repository_save_{entity.__class__.__name__.lower()}")
                    # Merge the entity with the session
                    entity = session.merge(entity)

                if flush:
                    session.flush()

                # Publish domain events after successful save
                self._publish_domain_events(entity, session)

                # Log timestamp information
                self._log_timestamp_info(entity, is_new_entity)

                return entity

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error(f"Database error saving {entity.__class__.__name__}: {e}")
            raise DatabaseException(f"Failed to save {entity.__class__.__name__}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving {entity.__class__.__name__}: {e}")
            raise DatabaseException(f"Unexpected error saving entity: {str(e)}")

    def update(self, entity: TimestampEntityType, **kwargs) -> TimestampEntityType:
        """Update entity with automatic timestamp management.

        Updates the entity with provided changes and automatically manages timestamps.
        This is a convenience method that wraps the save method.

        Args:
            entity: BaseTimestampEntity to update
            **kwargs: Additional attributes to update

        Returns:
            TimestampEntityType: Updated entity

        Raises:
            ValidationException: If entity validation fails
            DatabaseException: If database operation fails
        """
        logger.debug(f"Updating {entity.__class__.__name__} with {len(kwargs)} changes")

        # Apply updates to entity
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            else:
                logger.warning(f"Attribute {key} not found on {entity.__class__.__name__}")

        # Touch entity to update timestamp (this will fire domain events)
        entity.touch(f"repository_update_{entity.__class__.__name__.lower()}")

        # Save the updated entity
        return self.save(entity)

    def delete(self, entity: TimestampEntityType) -> None:
        """Delete entity and publish domain events.

        Args:
            entity: BaseTimestampEntity to delete

        Raises:
            ResourceNotFoundException: If entity doesn't exist
            DatabaseException: If database operation fails
        """
        try:
            with self.get_db_session() as session:
                logger.debug(f"Deleting {entity.__class__.__name__} with id {getattr(entity, 'id', 'unknown')}")

                # Collect domain events before deletion
                events = entity.get_domain_events()

                # Delete the entity
                session.delete(entity)
                session.flush()

                # Publish events after successful deletion
                for event in events:
                    logger.debug(f"Publishing domain event after deletion: {event}")

                logger.info(f"Deleted {entity.__class__.__name__} successfully")

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error(f"Database error deleting {entity.__class__.__name__}: {e}")
            raise DatabaseException(f"Failed to delete {entity.__class__.__name__}: {str(e)}")

    def find_by_timestamp_range(
        self,
        start_time: datetime,
        end_time: datetime,
        timestamp_field: str = "updated_at"
    ) -> List[TimestampEntityType]:
        """Find entities within a timestamp range.

        Args:
            start_time: Start of timestamp range (inclusive)
            end_time: End of timestamp range (inclusive)
            timestamp_field: Timestamp field to filter on ("created_at" or "updated_at")

        Returns:
            List[TimestampEntityType]: Entities within the timestamp range

        Raises:
            ValidationException: If timestamp field is invalid
            DatabaseException: If database operation fails
        """
        if timestamp_field not in ("created_at", "updated_at"):
            raise ValidationException(f"Invalid timestamp field: {timestamp_field}")

        try:
            with self.get_db_session() as session:
                logger.debug(
                    f"Finding {self.model_class.__name__} entities by {timestamp_field} "
                    f"between {start_time} and {end_time}"
                )

                query = session.query(self.model_class)
                field_attr = getattr(self.model_class, timestamp_field)
                query = query.filter(field_attr.between(start_time, end_time))
                entities = query.all()

                logger.debug(f"Found {len(entities)} entities in timestamp range")
                return entities

        except SQLAlchemyError as e:
            logger.error(f"Database error finding entities by timestamp: {e}")
            raise DatabaseException(f"Failed to find entities by timestamp: {str(e)}")

    def find_stale_entities(self, max_staleness_hours: int = 24) -> List[TimestampEntityType]:
        """Find entities that haven't been updated recently.

        Args:
            max_staleness_hours: Maximum hours since last update

        Returns:
            List[TimestampEntityType]: Stale entities

        Raises:
            DatabaseException: If database operation fails
        """
        from datetime import timedelta, timezone

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_staleness_hours)

        try:
            with self.get_db_session() as session:
                logger.debug(f"Finding stale {self.model_class.__name__} entities older than {cutoff_time}")

                query = session.query(self.model_class)
                query = query.filter(self.model_class.updated_at < cutoff_time)
                entities = query.all()

                logger.debug(f"Found {len(entities)} stale entities")
                return entities

        except SQLAlchemyError as e:
            logger.error(f"Database error finding stale entities: {e}")
            raise DatabaseException(f"Failed to find stale entities: {str(e)}")

    def touch_entity(self, entity_id: str, reason: str = "repository_touch") -> TimestampEntityType:
        """Touch an entity to update its timestamp.

        Args:
            entity_id: ID of entity to touch
            reason: Reason for the touch (for logging and events)

        Returns:
            TimestampEntityType: The touched entity

        Raises:
            ResourceNotFoundException: If entity doesn't exist
            DatabaseException: If database operation fails
        """
        entity = self.get_by_id(entity_id)
        if not entity:
            raise ResourceNotFoundException(f"{self.model_class.__name__} with id {entity_id} not found")

        entity.touch(reason)
        return self.save(entity)

    def _publish_domain_events(self, entity: TimestampEntityType, session: Session) -> None:
        """Publish domain events for the entity.

        Args:
            entity: Entity with domain events to publish
            session: Database session for event persistence (if needed)
        """
        events = entity.get_domain_events()

        for event in events:
            logger.debug(f"Publishing domain event: {event}")
            # TODO: Integrate with domain event publisher when available
            # For now, just log the events

        # Clear events after publishing
        entity.clear_domain_events()
        logger.debug(f"Published and cleared {len(events)} domain events")

    def _log_timestamp_info(self, entity: TimestampEntityType, is_new_entity: bool) -> None:
        """Log timestamp information for debugging.

        Args:
            entity: Entity to log timestamp info for
            is_new_entity: Whether this was a new entity creation
        """
        operation = "created" if is_new_entity else "updated"
        timestamp_info = entity.to_timestamp_dict()

        logger.debug(f"Entity {operation}: {timestamp_info}")

    def get_timestamp_stats(self) -> Dict[str, Any]:
        """Get timestamp statistics for all entities in this repository.

        Returns:
            Dict[str, Any]: Statistics including count, oldest, newest, etc.

        Raises:
            DatabaseException: If database operation fails
        """
        try:
            with self.get_db_session() as session:
                from sqlalchemy import func

                query = session.query(
                    func.count(self.model_class.id).label('total_count'),
                    func.min(self.model_class.created_at).label('oldest_created'),
                    func.max(self.model_class.created_at).label('newest_created'),
                    func.min(self.model_class.updated_at).label('oldest_updated'),
                    func.max(self.model_class.updated_at).label('newest_updated'),
                )

                result = query.one()

                stats = {
                    "entity_type": self.model_class.__name__,
                    "total_count": result.total_count or 0,
                    "oldest_created": result.oldest_created.isoformat() if result.oldest_created else None,
                    "newest_created": result.newest_created.isoformat() if result.newest_created else None,
                    "oldest_updated": result.oldest_updated.isoformat() if result.oldest_updated else None,
                    "newest_updated": result.newest_updated.isoformat() if result.newest_updated else None,
                }

                logger.debug(f"Timestamp stats for {self.model_class.__name__}: {stats}")
                return stats

        except SQLAlchemyError as e:
            logger.error(f"Database error getting timestamp stats: {e}")
            raise DatabaseException(f"Failed to get timestamp stats: {str(e)}")