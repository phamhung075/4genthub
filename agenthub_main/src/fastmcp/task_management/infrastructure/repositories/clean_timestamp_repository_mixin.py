"""Clean timestamp repository mixin.

Provides helper methods that ensure domain entities inheriting from
``BaseTimestampEntity`` maintain consistent timestamp semantics when persisted
through repository implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Generic, Iterable, List, Sequence, TypeVar

from ...domain.entities.base.base_timestamp_entity import BaseTimestampEntity


T = TypeVar("T", bound=BaseTimestampEntity)


class CleanTimestampRepository(ABC, Generic[T]):
    """Mixin that encapsulates clean timestamp persistence patterns."""

    def save_with_clean_timestamp(self, entity: T, *, reason: str = "repository_save") -> T:
        """Persist a single entity with automatic timestamp management."""
        entity.touch(reason)
        return self._perform_save(entity)

    def save_bulk_with_consistent_timestamp(
        self,
        entities: Sequence[T],
        *,
        reason: str = "repository_bulk_save"
    ) -> List[T]:
        """Persist multiple entities with a consistent timestamp."""
        if not entities:
            return []

        consistent_timestamp = datetime.now(timezone.utc)
        for entity in entities:
            # Use touch to capture domain events, then override with consistent timestamp
            entity.touch(reason)
            entity.updated_at = consistent_timestamp

        return self._perform_bulk_save(entities)

    @abstractmethod
    def _perform_save(self, entity: T) -> T:
        """Concrete persistence logic implemented by repositories."""

    @abstractmethod
    def _perform_bulk_save(self, entities: Iterable[T]) -> List[T]:
        """Concrete bulk persistence logic implemented by repositories."""

