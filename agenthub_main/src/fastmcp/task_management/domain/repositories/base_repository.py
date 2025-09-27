"""Base Repository Interface for DDD Standardization"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from dataclasses import dataclass

# Generic type for entities
T = TypeVar('T')


@dataclass(frozen=True)
class PaginationRequest:
    """Standard pagination request parameters"""
    page: int = 1
    page_size: int = 20
    offset: Optional[int] = None
    
    def __post_init__(self):
        if self.offset is None:
            object.__setattr__(self, 'offset', (self.page - 1) * self.page_size)


@dataclass(frozen=True)
class PaginationResult(Generic[T]):
    """Standard pagination result wrapper"""
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class BaseRepository(ABC, Generic[T]):
    """
    Base repository interface providing standardized operations.
    
    All domain repositories should inherit from this to ensure consistency
    in interface design and DDD compliance.
    """
    
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
        Helper method to create standardized pagination results.
        
        Args:
            items: List of entities for current page
            total_count: Total number of entities across all pages
            pagination: Pagination request parameters
            
        Returns:
            Properly formatted pagination result
        """
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