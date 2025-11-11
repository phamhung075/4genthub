"""Integration tests for PaginationService usage in repository implementations

This test suite demonstrates the CORRECT pattern for repositories to use PaginationService
instead of the deprecated BaseRepository.create_pagination_result() method.

Purpose:
- Serve as reference implementation for future repository pagination
- Verify PaginationService works correctly in repository context
- Demonstrate best practices for pagination in DDD repositories

Test Coverage:
1. Correct import and usage of PaginationService
2. Pagination with different page sizes and page numbers
3. Edge cases (empty results, single page, last page)
4. Feature flag compatibility (works with both flag states)
"""

from uuid import uuid4

import pytest

from fastmcp.task_management.domain.repositories.base_repository import (
    BaseRepository,
    PaginationRequest,
    PaginationResult,
)
from fastmcp.task_management.domain.services.pagination_service import PaginationService


# Test entity for demonstration
class PaginationEntity:
    """Simple entity for testing pagination"""

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class ExampleRepositoryWithPagination(BaseRepository[PaginationEntity]):
    """
    REFERENCE IMPLEMENTATION: How repositories SHOULD implement pagination

    This example shows the correct pattern:
    1. Import PaginationService from domain.services
    2. Use PaginationService.create_pagination_result() instead of self.create_pagination_result()
    3. No dependency on BaseRepository's deprecated pagination method

    Pattern works with both feature flag states:
    - FEATURE_CLEAN_REPOSITORIES=False: PaginationService available as alternative
    - FEATURE_CLEAN_REPOSITORIES=True: PaginationService is the only option
    """

    def __init__(self):
        """Initialize with in-memory storage for testing"""
        self._storage: list[PaginationEntity] = []

    def add(self, entity: PaginationEntity) -> PaginationEntity:
        """Add entity to storage"""
        self._storage.append(entity)
        return entity

    def get_by_id(self, entity_id: str) -> PaginationEntity | None:
        """Get entity by ID"""
        for entity in self._storage:
            if entity.id == entity_id:
                return entity
        return None

    def get_all(self) -> list[PaginationEntity]:
        """Get all entities"""
        return self._storage.copy()

    def update(self, entity: PaginationEntity) -> PaginationEntity:
        """Update entity"""
        for i, stored_entity in enumerate(self._storage):
            if stored_entity.id == entity.id:
                self._storage[i] = entity
                return entity
        raise ValueError(f"Entity {entity.id} not found")

    def delete(self, entity_id: str) -> None:
        """Delete entity by ID"""
        self._storage = [e for e in self._storage if e.id != entity_id]

    # Implement abstract methods from BaseRepository
    def find_all(self) -> list[PaginationEntity]:
        """Find all entities"""
        return self.get_all()

    def find_by_criteria(self, **criteria) -> list[PaginationEntity]:
        """Find entities by criteria"""
        return self.get_all()

    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        return self.get_by_id(entity_id) is not None

    def count(self) -> int:
        """Count all entities"""
        return len(self._storage)

    def count_by_criteria(self, **criteria) -> int:
        """Count entities by criteria"""
        return len(self._storage)

    def bulk_save(self, entities: list[PaginationEntity]) -> list[PaginationEntity]:
        """Bulk save entities"""
        for entity in entities:
            self.add(entity)
        return entities

    def bulk_delete(self, entity_ids: list[str]) -> None:
        """Bulk delete entities"""
        for entity_id in entity_ids:
            self.delete(entity_id)

    def list_with_pagination(
        self, pagination: PaginationRequest
    ) -> PaginationResult[PaginationEntity]:
        """
        ✅ CORRECT PATTERN: Using PaginationService for pagination

        This is how ALL repository implementations should handle pagination:
        1. Calculate offset using PaginationService.calculate_offset()
        2. Slice items for current page
        3. Use PaginationService.create_pagination_result() for result

        Benefits:
        - Clean separation of concerns (service handles pagination logic)
        - Works with both feature flag states
        - Easy to test and maintain
        - Follows DDD principles (domain service for domain logic)
        """
        # Calculate offset for current page
        offset = PaginationService.calculate_offset(pagination)

        # Get total count and current page items
        all_items = self.get_all()
        total_count = len(all_items)

        # Slice items for current page
        end = offset + pagination.page_size
        page_items = all_items[offset:end]

        # ✅ CORRECT: Use PaginationService.create_pagination_result()
        # NOT: self.create_pagination_result() (deprecated)
        return PaginationService[PaginationEntity].create_pagination_result(
            items=page_items, total_count=total_count, pagination=pagination
        )

    def search_with_pagination(
        self, name_filter: str, pagination: PaginationRequest
    ) -> PaginationResult[PaginationEntity]:
        """
        ✅ CORRECT PATTERN: Pagination with filtering

        Demonstrates pagination with search/filter functionality:
        1. Apply filters first
        2. Calculate total count of filtered results
        3. Apply pagination to filtered results
        4. Use PaginationService for result creation
        """
        # Apply filter
        filtered_items = [
            entity
            for entity in self._storage
            if name_filter.lower() in entity.name.lower()
        ]

        # Calculate offset and slice
        offset = PaginationService.calculate_offset(pagination)
        total_count = len(filtered_items)
        end = offset + pagination.page_size
        page_items = filtered_items[offset:end]

        # ✅ CORRECT: Use PaginationService
        return PaginationService[PaginationEntity].create_pagination_result(
            items=page_items, total_count=total_count, pagination=pagination
        )


class TestPaginationServiceIntegration:
    """
    Integration tests demonstrating correct PaginationService usage in repositories
    """

    @pytest.fixture
    def repository(self) -> ExampleRepositoryWithPagination:
        """Create repository with test data"""
        repo = ExampleRepositoryWithPagination()

        # Add 25 test entities
        for i in range(25):
            repo.add(PaginationEntity(id=str(uuid4()), name=f"Entity {i + 1}"))

        return repo

    def test_repository_pagination_first_page(self, repository):
        """Test: Repository pagination works correctly for first page"""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = repository.list_with_pagination(pagination)

        # Assert
        assert len(result.items) == 10
        assert result.total_count == 25
        assert result.total_pages == 3
        assert result.page == 1
        assert result.page_size == 10
        assert result.has_next is True
        assert result.has_previous is False

    def test_repository_pagination_middle_page(self, repository):
        """Test: Repository pagination works correctly for middle page"""
        # Arrange
        pagination = PaginationRequest(page=2, page_size=10)

        # Act
        result = repository.list_with_pagination(pagination)

        # Assert
        assert len(result.items) == 10
        assert result.total_count == 25
        assert result.total_pages == 3
        assert result.page == 2
        assert result.has_next is True
        assert result.has_previous is True

    def test_repository_pagination_last_page(self, repository):
        """Test: Repository pagination works correctly for last page (partial)"""
        # Arrange
        pagination = PaginationRequest(page=3, page_size=10)

        # Act
        result = repository.list_with_pagination(pagination)

        # Assert
        assert len(result.items) == 5  # Only 5 items on last page
        assert result.total_count == 25
        assert result.total_pages == 3
        assert result.page == 3
        assert result.has_next is False
        assert result.has_previous is True

    def test_repository_pagination_empty_results(self):
        """Test: Repository pagination handles empty results correctly"""
        # Arrange
        empty_repo = ExampleRepositoryWithPagination()
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = empty_repo.list_with_pagination(pagination)

        # Assert
        assert len(result.items) == 0
        assert result.total_count == 0
        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False

    def test_repository_pagination_single_page(self):
        """Test: Repository pagination works with results fitting in single page"""
        # Arrange
        small_repo = ExampleRepositoryWithPagination()
        for i in range(5):
            small_repo.add(PaginationEntity(id=str(uuid4()), name=f"Entity {i + 1}"))

        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = small_repo.list_with_pagination(pagination)

        # Assert
        assert len(result.items) == 5
        assert result.total_count == 5
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_previous is False

    def test_repository_search_with_pagination(self, repository):
        """Test: Repository pagination works with filtering/search"""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=5)

        # Act - search for entities containing "1" in name
        result = repository.search_with_pagination("1", pagination)

        # Assert - Should find entities: Entity 1, Entity 10-19, Entity 21
        # That's 12 entities total, first page should have 5
        assert len(result.items) == 5
        assert result.total_count == 12
        assert result.total_pages == 3
        assert result.has_next is True

    def test_pagination_service_calculate_offset(self):
        """Test: PaginationService.calculate_offset() helper works correctly"""
        # Test different pages
        assert (
            PaginationService.calculate_offset(PaginationRequest(page=1, page_size=10))
            == 0
        )
        assert (
            PaginationService.calculate_offset(PaginationRequest(page=2, page_size=10))
            == 10
        )
        assert (
            PaginationService.calculate_offset(PaginationRequest(page=3, page_size=10))
            == 20
        )
        assert (
            PaginationService.calculate_offset(PaginationRequest(page=5, page_size=20))
            == 80
        )

    def test_pagination_service_validation(self):
        """Test: PaginationService validates pagination requests"""
        # Valid requests should not raise
        PaginationService.validate_pagination_request(
            PaginationRequest(page=1, page_size=10)
        )
        PaginationService.validate_pagination_request(
            PaginationRequest(page=5, page_size=50)
        )

        # Invalid page number
        with pytest.raises(ValueError, match="Page must be >= 1"):
            PaginationService.validate_pagination_request(
                PaginationRequest(page=0, page_size=10)
            )

        # Invalid page size (zero)
        with pytest.raises(ValueError, match="Page size must be > 0"):
            PaginationService.validate_pagination_request(
                PaginationRequest(page=1, page_size=0)
            )

        # Invalid page size (too large)
        with pytest.raises(ValueError, match="Page size must be <= 100"):
            PaginationService.validate_pagination_request(
                PaginationRequest(page=1, page_size=200)
            )

    def test_feature_flag_compatibility(self, repository):
        """
        Test: Verify PaginationService works with both feature flag states

        This ensures zero-downtime migration regardless of FEATURE_CLEAN_REPOSITORIES setting
        """
        pagination = PaginationRequest(page=1, page_size=10)

        # Test with flag=False (legacy mode)
        PaginationService.FEATURE_CLEAN_REPOSITORIES = False
        result_legacy = repository.list_with_pagination(pagination)

        # Test with flag=True (clean mode)
        PaginationService.FEATURE_CLEAN_REPOSITORIES = True
        result_clean = repository.list_with_pagination(pagination)

        # Results should be identical
        assert result_legacy.items == result_clean.items
        assert result_legacy.total_count == result_clean.total_count
        assert result_legacy.total_pages == result_clean.total_pages
        assert result_legacy.has_next == result_clean.has_next
        assert result_legacy.has_previous == result_clean.has_previous

        # Reset flag
        PaginationService.FEATURE_CLEAN_REPOSITORIES = False


class TestRepositoryPaginationDocumentation:
    """
    Documentation tests that show the migration path for existing repositories
    """

    def test_migration_example_before_after(self):
        """
        DOCUMENTATION: Shows before/after pattern for repository migration

        This test demonstrates how to migrate existing repository code
        from using BaseRepository.create_pagination_result() to PaginationService
        """

        # ❌ OLD PATTERN (DEPRECATED):
        # class OldRepository(BaseRepository[Entity]):
        #     def list_paginated(self, pagination: PaginationRequest):
        #         items = self.get_all()
        #         return self.create_pagination_result(items, len(items), pagination)

        # ✅ NEW PATTERN (CORRECT):
        # class NewRepository(BaseRepository[Entity]):
        #     def list_paginated(self, pagination: PaginationRequest):
        #         items = self.get_all()
        #         return PaginationService[Entity].create_pagination_result(
        #             items, len(items), pagination
        #         )

        # Verify the example compiles and works
        repo = ExampleRepositoryWithPagination()
        for i in range(5):
            repo.add(PaginationEntity(id=str(uuid4()), name=f"Entity {i + 1}"))

        pagination = PaginationRequest(page=1, page_size=10)
        result = repo.list_with_pagination(pagination)

        assert result.total_count == 5
        assert len(result.items) == 5

    def test_import_pattern_documentation(self):
        """
        DOCUMENTATION: Shows correct import pattern for repositories
        """

        # ✅ CORRECT IMPORTS:
        # from fastmcp.task_management.domain.repositories.base_repository import (
        #     BaseRepository,
        #     PaginationRequest,
        #     PaginationResult
        # )
        # from fastmcp.task_management.domain.services.pagination_service import PaginationService

        # Verify imports work
        assert PaginationService is not None
        assert PaginationRequest is not None
        assert PaginationResult is not None
        assert BaseRepository is not None
