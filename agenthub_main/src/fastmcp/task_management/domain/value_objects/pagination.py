"""Pagination Value Objects for Query Results

This module contains value objects for pagination parameters and results.
Moved from base_repository.py in Phase 5.1 for proper DDD layer separation.

Business Rules:
- Page numbering starts at 1 (not 0)
- Offset is automatically calculated from page and page_size
- PaginationResult includes metadata for API responses
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass(frozen=True)
class PaginationRequest:
    """Value object for pagination parameters.

    Represents a request for paginated data with page number and size.
    Automatically calculates offset for database queries.

    Attributes:
        page: Page number (1-based indexing)
        page_size: Number of items per page
        offset: Database offset (auto-calculated if not provided)

    Example:
        >>> req = PaginationRequest(page=2, page_size=10)
        >>> req.offset
        10
    """
    page: int = 1
    page_size: int = 20
    offset: int | None = None

    def __post_init__(self):
        """Calculate offset if not provided."""
        if self.offset is None:
            object.__setattr__(self, 'offset', (self.page - 1) * self.page_size)


@dataclass(frozen=True)
class PaginationResult(Generic[T]):
    """Value object for paginated query results.

    Wraps a list of items with pagination metadata for API responses.

    Attributes:
        items: List of items for current page
        total_count: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there are more pages after this one
        has_previous: Whether there are pages before this one

    Example:
        >>> result = PaginationResult(
        ...     items=[1, 2, 3],
        ...     total_count=30,
        ...     page=2,
        ...     page_size=10,
        ...     total_pages=3,
        ...     has_next=True,
        ...     has_previous=True
        ... )
    """
    items: list[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
