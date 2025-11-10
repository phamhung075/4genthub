"""Base Repository Interface for DDD Standardization"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# Import pagination types from value_objects (moved in Phase 5.1)
# Previously defined here, now properly located in value_objects layer
from ..value_objects.pagination import PaginationRequest, PaginationResult

# Generic type for entities
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Base repository interface providing standardized operations.

    All domain repositories should inherit from this to ensure consistency
    in interface design and DDD compliance.

    Note: For pagination, use PaginationService.create_pagination_result()
    """
    
    @abstractmethod
    def find_by_criteria(
        self, 
        filters: dict[str, Any], 
        pagination: PaginationRequest | None = None
    ) -> PaginationResult[T]:
        """
        Find entities by multiple criteria with optional pagination.
        
        Args:
            filters: Dictionary of filter criteria
            pagination: Optional pagination parameters
            
        Returns:
            PaginationResult containing matching entities and pagination info
        """
        pass
    
    @abstractmethod
    def find_all(self, pagination: PaginationRequest | None = None) -> PaginationResult[T]:
        """
        Find all entities with optional pagination.
        
        Args:
            pagination: Optional pagination parameters
            
        Returns:
            PaginationResult containing all entities and pagination info
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total count of entities in the repository"""
        pass
    
    @abstractmethod
    def count_by_criteria(self, filters: dict[str, Any]) -> int:
        """Get count of entities matching the given criteria"""
        pass
    
    @abstractmethod
    def exists(self, entity_id: Any) -> bool:
        """Check if an entity exists by its identifier"""
        pass
    
    @abstractmethod
    def bulk_save(self, entities: list[T]) -> list[T]:
        """
        Save multiple entities in a single operation.
        
        Args:
            entities: List of entities to save
            
        Returns:
            List of saved entities (may include generated IDs)
        """
        pass
    
    @abstractmethod
    def bulk_delete(self, entity_ids: list[Any]) -> int:
        """
        Delete multiple entities by their identifiers.

        Args:
            entity_ids: List of entity identifiers to delete

        Returns:
            Number of entities actually deleted
        """
        pass