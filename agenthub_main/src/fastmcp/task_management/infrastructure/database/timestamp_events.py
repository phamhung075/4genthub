"""SQLAlchemy Event Handlers for Automatic Timestamp Management

This module provides clean, automatic timestamp handling through SQLAlchemy events.
It integrates with BaseTimestampEntity to provide seamless timestamp management
without manual intervention.

Key Features:
- Automatic created_at/updated_at handling
- UTC timezone enforcement
- Integration with BaseTimestampEntity
- Clean architecture compliance
- NO manual timestamp code paths

NO LEGACY SUPPORT:
- No fallback mechanisms
- No dual handling systems
- Clean implementation only
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.state import InstanceState

logger = logging.getLogger(__name__)


def setup_timestamp_events() -> None:
    """Set up SQLAlchemy event listeners for automatic timestamp management.

    This function registers all necessary event handlers for BaseTimestampEntity
    subclasses. Call this once during application initialization.

    Events handled:
    - before_insert: Set created_at and updated_at for new entities
    - before_update: Update updated_at for existing entities
    """
    logger.info("Setting up timestamp event handlers")

    # Register event handlers for individual operations
    try:
        event.remove(Mapper, 'before_insert', _before_insert_handler)
    except InvalidRequestError:
        logger.debug("No existing before_insert handler to remove")
    except Exception as exc:
        logger.debug("Skipping before_insert removal: %s", exc)

    try:
        event.remove(Mapper, 'before_update', _before_update_handler)
    except InvalidRequestError:
        logger.debug("No existing before_update handler to remove")
    except Exception as exc:
        logger.debug("Skipping before_update removal: %s", exc)

    event.listen(Mapper, 'before_insert', _before_insert_handler)
    event.listen(Mapper, 'before_update', _before_update_handler)

    logger.info("Timestamp event handlers registered successfully")


def _before_insert_handler(mapper: Mapper, connection: Any, target: Any) -> None:
    """Handle before_insert events for timestamp management.

    Automatically sets created_at and updated_at for new entities that inherit
    from BaseTimestampEntity.

    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: The entity being inserted
    """
    # Check if target has timestamp attributes (BaseTimestampEntity subclass)
    if not _is_timestamp_entity(target):
        return

    now = datetime.now(timezone.utc)
    entity_class = target.__class__.__name__

    # Set created_at if not already set
    if not hasattr(target, 'created_at') or target.created_at is None:
        target.created_at = now
        logger.debug(f"Set created_at for new {entity_class}: {now}")

    # Set updated_at if not already set
    if not hasattr(target, 'updated_at') or target.updated_at is None:
        target.updated_at = now
        logger.debug(f"Set updated_at for new {entity_class}: {now}")

    # Ensure timestamps are in UTC
    _ensure_utc_timezone(target)

    logger.debug(f"Processed before_insert for {entity_class} with timestamps")


def _before_update_handler(mapper: Mapper, connection: Any, target: Any) -> None:
    """Handle before_update events for timestamp management.

    Automatically updates updated_at for existing entities that inherit
    from BaseTimestampEntity. Preserves created_at (immutable).

    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: The entity being updated
    """
    # Check if target has timestamp attributes (BaseTimestampEntity subclass)
    if not _is_timestamp_entity(target):
        return

    now = datetime.now(timezone.utc)
    entity_class = target.__class__.__name__

    # Always update updated_at for existing entities
    old_updated_at = getattr(target, 'updated_at', None)
    target.updated_at = now

    # Ensure created_at is preserved and in UTC
    if hasattr(target, 'created_at') and target.created_at:
        _ensure_created_at_utc(target)

    # Ensure updated_at is in UTC
    _ensure_updated_at_utc(target)

    logger.debug(
        f"Updated timestamp for {entity_class}: "
        f"old={old_updated_at}, new={target.updated_at}"
    )



def _is_timestamp_entity(target: Any) -> bool:
    """Check if target is a BaseTimestampEntity subclass.

    Args:
        target: Entity instance to check

    Returns:
        bool: True if target has timestamp management capabilities
    """
    return (
        hasattr(target, 'created_at') and
        hasattr(target, 'updated_at') and
        hasattr(target, 'touch')  # BaseTimestampEntity method
    )


def _mapper_handles_timestamps(mapper: Mapper) -> bool:
    """Check if mapper is for a BaseTimestampEntity subclass.

    Args:
        mapper: SQLAlchemy mapper to check

    Returns:
        bool: True if mapper handles timestamp entities
    """
    return (
        hasattr(mapper.class_, 'created_at') and
        hasattr(mapper.class_, 'updated_at') and
        hasattr(mapper.class_, 'touch')  # BaseTimestampEntity method
    )


def _ensure_utc_timezone(target: Any) -> None:
    """Ensure both timestamps are in UTC timezone.

    Args:
        target: Entity instance to check and fix
    """
    _ensure_created_at_utc(target)
    _ensure_updated_at_utc(target)


def _ensure_created_at_utc(target: Any) -> None:
    """Ensure created_at is in UTC timezone.

    Args:
        target: Entity instance to check and fix
    """
    if hasattr(target, 'created_at') and target.created_at:
        if target.created_at.tzinfo is None:
            # Assume naive datetime is UTC
            target.created_at = target.created_at.replace(tzinfo=timezone.utc)
            logger.debug(f"Added UTC timezone to created_at for {target.__class__.__name__}")
        elif target.created_at.tzinfo != timezone.utc:
            # Convert to UTC
            target.created_at = target.created_at.astimezone(timezone.utc)
            logger.debug(f"Converted created_at to UTC for {target.__class__.__name__}")


def _ensure_updated_at_utc(target: Any) -> None:
    """Ensure updated_at is in UTC timezone.

    Args:
        target: Entity instance to check and fix
    """
    if hasattr(target, 'updated_at') and target.updated_at:
        if target.updated_at.tzinfo is None:
            # Assume naive datetime is UTC
            target.updated_at = target.updated_at.replace(tzinfo=timezone.utc)
            logger.debug(f"Added UTC timezone to updated_at for {target.__class__.__name__}")
        elif target.updated_at.tzinfo != timezone.utc:
            # Convert to UTC
            target.updated_at = target.updated_at.astimezone(timezone.utc)
            logger.debug(f"Converted updated_at to UTC for {target.__class__.__name__}")


def cleanup_timestamp_events() -> None:
    """Remove all timestamp event handlers.

    Useful for testing or when reinitializing the system.
    """
    logger.info("Cleaning up timestamp event handlers")

    try:
        # Remove event handlers
        event.remove(Mapper, 'before_insert', _before_insert_handler)
        event.remove(Mapper, 'before_update', _before_update_handler)

        logger.info("Timestamp event handlers removed successfully")
    except Exception as e:
        logger.warning(f"Some event handlers may not have been registered: {e}")


