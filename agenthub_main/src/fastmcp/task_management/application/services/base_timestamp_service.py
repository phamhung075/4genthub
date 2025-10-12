"""Base Timestamp Service for Application Layer

This module provides the base application service for managing entities that inherit
from BaseTimestampEntity. It provides clean patterns for business operations while
maintaining automatic timestamp management.

Key Features:
- Application layer abstraction over timestamp repositories
- Business logic methods with automatic timestamp handling
- Transaction coordination with domain events
- Clean architecture compliance
- Integration with existing service patterns

NO LEGACY SUPPORT:
- No manual timestamp manipulation
- No backward compatibility methods
- Clean implementation only
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Callable
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod

from ...domain.entities.base.base_timestamp_entity import BaseTimestampEntity
from ...infrastructure.repositories.base_timestamp_repository import BaseTimestampRepository
from ...domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException
)

logger = logging.getLogger(__name__)

# Type variable for BaseTimestampEntity subclasses
TimestampEntityType = TypeVar("TimestampEntityType", bound=BaseTimestampEntity)


class BaseTimestampService(ABC, Generic[TimestampEntityType]):
    """Base application service for BaseTimestampEntity subclasses.

    This service provides common business operations for entities with automatic
    timestamp management. It abstracts repository operations and adds business
    logic coordination.

    Features:
    - Automatic timestamp management through repositories
    - Business transaction coordination
    - Domain event publishing
    - Validation and business rule enforcement
    - Clean separation of concerns

    Usage:
        class TaskService(BaseTimestampService[Task]):
            def __init__(self, task_repository: TaskRepository):
                super().__init__(task_repository)

            def _validate_business_rules(self, entity: Task) -> None:
                # Task-specific business validation
                pass
    """

    def __init__(self, repository: BaseTimestampRepository[TimestampEntityType]):
        """Initialize base timestamp service.

        Args:
            repository: Repository for the timestamp entity
        """
        self._repository = repository
        self._entity_type = self._get_entity_type_name()
        logger.debug(f"Initialized BaseTimestampService for {self._entity_type}")

    @abstractmethod
    def _validate_business_rules(self, entity: TimestampEntityType) -> None:
        """Validate business rules specific to the entity type.

        Override in concrete service classes to add entity-specific validation.

        Args:
            entity: Entity to validate

        Raises:
            BusinessLogicException: If business rules are violated
        """
        pass

    @abstractmethod
    def _get_entity_type_name(self) -> str:
        """Get the name of the entity type this service manages.

        Returns:
            str: Entity type name (e.g., "Task", "Project")
        """
        pass

    def create_entity(
        self,
        entity_data: Dict[str, Any],
        validation_callback: Optional[Callable[[TimestampEntityType], None]] = None
    ) -> TimestampEntityType:
        """Create a new entity with automatic timestamp management.

        Args:
            entity_data: Dictionary of entity attributes
            validation_callback: Optional additional validation function

        Returns:
            TimestampEntityType: Created entity with timestamps

        Raises:
            ValidationException: If validation fails
            BusinessLogicException: If business rules are violated
            DatabaseException: If database operation fails
        """
        logger.info(f"Creating new {self._entity_type} with data: {len(entity_data)} attributes")

        try:
            # Create entity instance (timestamps will be set automatically)
            entity = self._create_entity_from_data(entity_data)

            # Validate business rules
            self._validate_business_rules(entity)

            # Apply additional validation if provided
            if validation_callback:
                validation_callback(entity)

            # Save entity (repository will handle timestamps and events)
            saved_entity = self._repository.save(entity)

            logger.info(f"Successfully created {self._entity_type} with id {self._get_entity_id(saved_entity)}")
            return saved_entity

        except (ValidationException, BusinessLogicException):
            # Re-raise business exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating {self._entity_type}: {e}")
            raise DatabaseException(f"Failed to create {self._entity_type}: {str(e)}")

    def update_entity(
        self,
        entity_id: str,
        updates: Dict[str, Any],
        touch_reason: str = None
    ) -> TimestampEntityType:
        """Update entity with automatic timestamp management.

        Args:
            entity_id: ID of entity to update
            updates: Dictionary of attributes to update
            touch_reason: Reason for the update (for logging)

        Returns:
            TimestampEntityType: Updated entity

        Raises:
            ResourceNotFoundException: If entity doesn't exist
            ValidationException: If validation fails
            BusinessLogicException: If business rules are violated
            DatabaseException: If database operation fails
        """
        logger.info(f"Updating {self._entity_type} {entity_id} with {len(updates)} changes")

        # Get existing entity
        entity = self._repository.get_by_id(entity_id)
        if not entity:
            raise ResourceNotFoundException(f"{self._entity_type} with id {entity_id} not found")

        try:
            # Apply updates
            self._apply_updates_to_entity(entity, updates)

            # Validate business rules after updates
            self._validate_business_rules(entity)

            # Touch entity with reason
            reason = touch_reason or f"{self._entity_type.lower()}_updated"
            entity.touch(reason)

            # Save updated entity
            updated_entity = self._repository.save(entity)

            logger.info(f"Successfully updated {self._entity_type} {entity_id}")
            return updated_entity

        except (ValidationException, BusinessLogicException):
            # Re-raise business exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating {self._entity_type} {entity_id}: {e}")
            raise DatabaseException(f"Failed to update {self._entity_type}: {str(e)}")

    def get_entity(self, entity_id: str) -> Optional[TimestampEntityType]:
        """Get entity by ID.

        Args:
            entity_id: ID of entity to retrieve

        Returns:
            TimestampEntityType | None: Entity if found, None otherwise

        Raises:
            DatabaseException: If database operation fails
        """
        try:
            entity = self._repository.get_by_id(entity_id)
            if entity:
                logger.debug(f"Retrieved {self._entity_type} {entity_id}")
            else:
                logger.debug(f"{self._entity_type} {entity_id} not found")
            return entity

        except Exception as e:
            logger.error(f"Error retrieving {self._entity_type} {entity_id}: {e}")
            raise DatabaseException(f"Failed to retrieve {self._entity_type}: {str(e)}")

    def delete_entity(self, entity_id: str) -> None:
        """Delete entity by ID.

        Args:
            entity_id: ID of entity to delete

        Raises:
            ResourceNotFoundException: If entity doesn't exist
            BusinessLogicException: If deletion is not allowed
            DatabaseException: If database operation fails
        """
        logger.info(f"Deleting {self._entity_type} {entity_id}")

        # Get entity
        entity = self._repository.get_by_id(entity_id)
        if not entity:
            raise ResourceNotFoundException(f"{self._entity_type} with id {entity_id} not found")

        try:
            # Check if deletion is allowed (business rules)
            self._validate_deletion_allowed(entity)

            # Delete entity
            self._repository.delete(entity)

            logger.info(f"Successfully deleted {self._entity_type} {entity_id}")

        except BusinessLogicException:
            # Re-raise business exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting {self._entity_type} {entity_id}: {e}")
            raise DatabaseException(f"Failed to delete {self._entity_type}: {str(e)}")

    def touch_entity(self, entity_id: str, reason: str) -> TimestampEntityType:
        """Touch entity to update its timestamp.

        Args:
            entity_id: ID of entity to touch
            reason: Reason for the touch

        Returns:
            TimestampEntityType: Touched entity

        Raises:
            ResourceNotFoundException: If entity doesn't exist
            DatabaseException: If database operation fails
        """
        logger.debug(f"Touching {self._entity_type} {entity_id} with reason: {reason}")

        try:
            return self._repository.touch_entity(entity_id, reason)
        except Exception as e:
            logger.error(f"Error touching {self._entity_type} {entity_id}: {e}")
            raise

    def find_entities_by_timestamp_range(
        self,
        start_time: datetime,
        end_time: datetime,
        timestamp_field: str = "updated_at"
    ) -> List[TimestampEntityType]:
        """Find entities within a timestamp range.

        Args:
            start_time: Start of range (inclusive)
            end_time: End of range (inclusive)
            timestamp_field: Field to filter on ("created_at" or "updated_at")

        Returns:
            List[TimestampEntityType]: Entities in range

        Raises:
            ValidationException: If parameters are invalid
            DatabaseException: If database operation fails
        """
        logger.debug(f"Finding {self._entity_type} entities by {timestamp_field} range")

        # Validate timestamp range
        if start_time > end_time:
            raise ValidationException("Start time must be before end time")

        try:
            return self._repository.find_by_timestamp_range(start_time, end_time, timestamp_field)
        except Exception as e:
            logger.error(f"Error finding {self._entity_type} by timestamp range: {e}")
            raise

    def find_stale_entities(self, max_staleness_hours: int = 24) -> List[TimestampEntityType]:
        """Find entities that haven't been updated recently.

        Args:
            max_staleness_hours: Maximum hours since last update

        Returns:
            List[TimestampEntityType]: Stale entities

        Raises:
            ValidationException: If parameters are invalid
            DatabaseException: If database operation fails
        """
        if max_staleness_hours < 1:
            raise ValidationException("Max staleness must be at least 1 hour")

        logger.debug(f"Finding stale {self._entity_type} entities older than {max_staleness_hours} hours")

        try:
            return self._repository.find_stale_entities(max_staleness_hours)
        except Exception as e:
            logger.error(f"Error finding stale {self._entity_type} entities: {e}")
            raise

    def get_timestamp_statistics(self) -> Dict[str, Any]:
        """Get timestamp statistics for all entities.

        Returns:
            Dict[str, Any]: Statistics including counts, ranges, etc.

        Raises:
            DatabaseException: If database operation fails
        """
        logger.debug(f"Getting timestamp statistics for {self._entity_type}")

        try:
            return self._repository.get_timestamp_stats()
        except Exception as e:
            logger.error(f"Error getting timestamp stats for {self._entity_type}: {e}")
            raise

    def cleanup_stale_entities(
        self,
        max_staleness_days: int = 30,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up very stale entities.

        Args:
            max_staleness_days: Maximum days since last update
            dry_run: If True, only return what would be deleted

        Returns:
            Dict[str, Any]: Cleanup results

        Raises:
            ValidationException: If parameters are invalid
            DatabaseException: If database operation fails
        """
        if max_staleness_days < 1:
            raise ValidationException("Max staleness must be at least 1 day")

        logger.info(f"{'Dry-run' if dry_run else 'Executing'} cleanup of {self._entity_type} older than {max_staleness_days} days")

        try:
            stale_entities = self.find_stale_entities(max_staleness_days * 24)

            if dry_run:
                return {
                    "dry_run": True,
                    "entities_to_delete": len(stale_entities),
                    "entity_ids": [self._get_entity_id(e) for e in stale_entities]
                }

            # Actually delete stale entities
            deleted_count = 0
            errors = []

            for entity in stale_entities:
                try:
                    if self._can_cleanup_entity(entity):
                        self._repository.delete(entity)
                        deleted_count += 1
                except Exception as e:
                    error_msg = f"Failed to delete {self._get_entity_id(entity)}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            return {
                "dry_run": False,
                "entities_deleted": deleted_count,
                "entities_failed": len(errors),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error during cleanup of {self._entity_type}: {e}")
            raise DatabaseException(f"Cleanup failed: {str(e)}")

    # Abstract methods for subclasses to implement
    @abstractmethod
    def _create_entity_from_data(self, entity_data: Dict[str, Any]) -> TimestampEntityType:
        """Create entity instance from data dictionary.

        Args:
            entity_data: Dictionary of entity attributes

        Returns:
            TimestampEntityType: Created entity instance
        """
        pass

    def _apply_updates_to_entity(self, entity: TimestampEntityType, updates: Dict[str, Any]) -> None:
        """Apply updates to entity instance.

        Default implementation sets attributes directly.
        Override for custom update logic.

        Args:
            entity: Entity to update
            updates: Dictionary of updates to apply
        """
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            else:
                logger.warning(f"Attribute {key} not found on {self._entity_type}")

    def _validate_deletion_allowed(self, entity: TimestampEntityType) -> None:
        """Validate if entity deletion is allowed.

        Override in subclasses to add deletion constraints.

        Args:
            entity: Entity to validate for deletion

        Raises:
            BusinessLogicException: If deletion is not allowed
        """
        # Default implementation allows all deletions
        pass

    def _can_cleanup_entity(self, entity: TimestampEntityType) -> bool:
        """Check if entity can be cleaned up during maintenance.

        Override in subclasses to add cleanup constraints.

        Args:
            entity: Entity to check

        Returns:
            bool: True if entity can be cleaned up
        """
        # Default implementation allows cleanup of all stale entities
        return True

    def _get_entity_id(self, entity: TimestampEntityType) -> str:
        """Get entity ID for logging.

        Args:
            entity: Entity to get ID from

        Returns:
            str: Entity ID
        """
        return entity._get_entity_id()