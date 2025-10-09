"""Base Repository Interface for DDD Standardization"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic

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

    Feature Flag: FEATURE_CLEAN_REPOSITORIES
    - False (default): Provides create_pagination_result() helper method
    - True: Removes helper - use PaginationService instead (clean interface)
    """

    @property
    def FEATURE_CLEAN_REPOSITORIES(self) -> bool:
        """
        Feature flag for clean repository pattern (Strangler Fig Pattern).
        Reads from environment variable dynamically for testability.
        """
        return os.getenv("FEATURE_CLEAN_REPOSITORIES", "false").lower() == "true"
    
    @abstractmethod
    def find_by_criteria(
        self, 
        filters: Dict[str, Any], 
        pagination: Optional[PaginationRequest] = None
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
    def find_all(self, pagination: Optional[PaginationRequest] = None) -> PaginationResult[T]:
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
    def count_by_criteria(self, filters: Dict[str, Any]) -> int:
        """Get count of entities matching the given criteria"""
        pass
    
    @abstractmethod
    def exists(self, entity_id: Any) -> bool:
        """Check if an entity exists by its identifier"""
        pass
    
    @abstractmethod
    def bulk_save(self, entities: List[T]) -> List[T]:
        """
        Save multiple entities in a single operation.
        
        Args:
            entities: List of entities to save
            
        Returns:
            List of saved entities (may include generated IDs)
        """
        pass
    
    @abstractmethod
    def bulk_delete(self, entity_ids: List[Any]) -> int:
        """
        Delete multiple entities by their identifiers.
        
        Args:
            entity_ids: List of entity identifiers to delete
            
        Returns:
            Number of entities actually deleted
        """
        pass
    
    def create_pagination_result(
        self,
        items: List[T],
        total_count: int,
        pagination: PaginationRequest
    ) -> PaginationResult[T]:
        """
        DEPRECATED: Use PaginationService.create_pagination_result() instead.

        This method will raise NotImplementedError when FEATURE_CLEAN_REPOSITORIES=True.
        For clean repository pattern, use the dedicated PaginationService.

        Migration Guide:
            Old: result = repository.create_pagination_result(items, count, pagination)
            New: from ..services.pagination_service import PaginationService
                 result = PaginationService.create_pagination_result(items, count, pagination)

        Args:
            items: List of entities for current page
            total_count: Total number of entities across all pages
            pagination: Pagination request parameters

        Returns:
            Properly formatted pagination result

        Raises:
            NotImplementedError: When FEATURE_CLEAN_REPOSITORIES=True
        """
        if self.FEATURE_CLEAN_REPOSITORIES:
            raise NotImplementedError(
                "Pagination logic has been moved to PaginationService for clean separation of concerns. "
                "Please use: PaginationService.create_pagination_result(items, total_count, pagination). "
                "This maintains DDD principle of keeping repositories focused on data access only. "
                "Set FEATURE_CLEAN_REPOSITORIES=false to temporarily re-enable this method during migration."
            )

        # Legacy implementation - backward compatibility when flag=False
        total_pages = (total_count + pagination.page_size - 1) // pagination.page_size
        has_next = pagination.page < total_pages
        has_previous = pagination.page > 1

        return PaginationResult(
            items=items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )