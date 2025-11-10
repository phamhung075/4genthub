"""Pagination domain service for managing paginated results

This service provides pagination logic as a domain service,
following DDD principles where interfaces should only contain abstract methods.
"""

from typing import Generic, TypeVar

# Import pagination types from value_objects (moved from base_repository in Phase 5.1)
from ..value_objects.pagination import PaginationRequest, PaginationResult

T = TypeVar('T')


class PaginationService(Generic[T]):
    """
    Domain service for creating paginated results.

    Business Rules:
    - Calculate total pages based on total_count and page_size
    - Determine if there are more pages (has_next)
    - Determine if there are previous pages (has_previous)
    - Include current page number in result
    - Handle edge cases (empty results, single page, etc.)
    """

    @classmethod
    def create_pagination_result(
        cls,
        items: list[T],
        total_count: int,
        pagination: PaginationRequest
    ) -> PaginationResult[T]:
        """
        Create a pagination result with metadata.

        This method extracts the exact logic from BaseRepository.create_pagination_result()
        to provide a domain service implementation that can be used independently.

        Args:
            items: List of entities for current page
            total_count: Total number of entities across all pages
            pagination: Pagination request parameters

        Returns:
            PaginationResult[T]: Properly formatted pagination result with metadata

        Business Rules:
        1. total_pages = (total_count + page_size - 1) // page_size
           - This ceiling division ensures we count partial pages
           - Example: 25 items with page_size=10 → 3 pages (10, 10, 5)

        2. has_next = current_page < total_pages
           - True if there are more pages after the current one
           - False if on the last page

        3. has_previous = current_page > 1
           - True if not on the first page
           - False if on the first page (page 1)

        Edge Cases:
        - Empty results (total_count=0): total_pages=0, has_next=False, has_previous depends on page
        - Single page (total_count <= page_size): total_pages=1, has_next=False
        - Exact page boundary (total_count % page_size == 0): Handled correctly by ceiling division

        Example:
            >>> service = PaginationService[str]()
            >>> pagination = PaginationRequest(page=2, page_size=10)
            >>> items = ["item1", "item2", ..., "item10"]
            >>> result = service.create_pagination_result(items, 25, pagination)
            >>> result.total_pages
            3
            >>> result.has_next
            True
            >>> result.has_previous
            True
        """
        # Calculate total pages using ceiling division
        # Formula: (total_count + page_size - 1) // page_size
        # This ensures partial pages are counted as full pages
        total_pages = (total_count + pagination.page_size - 1) // pagination.page_size

        # Determine if there are more pages after current page
        has_next = pagination.page < total_pages

        # Determine if there are pages before current page
        has_previous = pagination.page > 1

        # Create and return the pagination result
        return PaginationResult(
            items=items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )

    @classmethod
    def validate_pagination_request(cls, pagination: PaginationRequest) -> None:
        """
        Validate pagination request parameters.

        Args:
            pagination: Pagination request to validate

        Raises:
            ValueError: If pagination parameters are invalid

        Business Rules:
        - page must be >= 1 (first page is page 1, not 0)
        - page_size must be > 0 (at least one item per page)
        - page_size should have a reasonable upper limit (e.g., 100) to prevent abuse
        """
        if pagination.page < 1:
            raise ValueError(f"Page must be >= 1, got {pagination.page}")

        if pagination.page_size <= 0:
            raise ValueError(f"Page size must be > 0, got {pagination.page_size}")

        # Reasonable upper limit to prevent abuse
        MAX_PAGE_SIZE = 100
        if pagination.page_size > MAX_PAGE_SIZE:
            raise ValueError(
                f"Page size must be <= {MAX_PAGE_SIZE}, got {pagination.page_size}"
            )

    @classmethod
    def calculate_offset(cls, pagination: PaginationRequest) -> int:
        """
        Calculate database offset from pagination parameters.

        Args:
            pagination: Pagination request

        Returns:
            int: Database offset for the query

        Business Rule:
        - offset = (page - 1) * page_size
        - Page 1 → offset 0
        - Page 2 → offset page_size
        - Page N → offset (N-1) * page_size

        Example:
            >>> pagination = PaginationRequest(page=3, page_size=10)
            >>> PaginationService.calculate_offset(pagination)
            20
        """
        return (pagination.page - 1) * pagination.page_size
