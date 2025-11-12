"""Unit tests for PaginationService domain service.

Tests the pagination logic extracted from BaseRepository to ensure:
- Correct pagination calculation
- Edge case handling (empty results, single page, exact boundaries)
- Feature flag behavior
- Request validation
- Offset calculation
"""

from dataclasses import dataclass

import pytest

from fastmcp.task_management.domain.repositories.base_repository import (
    PaginationRequest,
    PaginationResult,
)
from fastmcp.task_management.domain.services.pagination_service import PaginationService


# Test entity for generic type testing
@dataclass
class _MockPaginationEntity:
    """Simple mock entity for pagination testing (underscore prefix prevents pytest collection)."""

    id: int
    name: str


class TestPaginationServiceBasicOperations:
    """Test basic pagination operations."""

    def test_create_pagination_result_first_page(self):
        """Test creating pagination result for first page."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        total_count = 25
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert isinstance(result, PaginationResult)
        assert result.items == items
        assert result.total_count == 25
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 3  # (25 + 10 - 1) // 10 = 3
        assert result.has_next is True  # Page 1 < 3
        assert result.has_previous is False  # Page 1 > 1 = False

    def test_create_pagination_result_middle_page(self):
        """Test creating pagination result for middle page."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10, 20)]
        total_count = 25
        pagination = PaginationRequest(page=2, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_count == 25
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_next is True  # Page 2 < 3
        assert result.has_previous is True  # Page 2 > 1

    def test_create_pagination_result_last_page(self):
        """Test creating pagination result for last page."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(20, 25)]  # 5 items
        total_count = 25
        pagination = PaginationRequest(page=3, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_count == 25
        assert result.page == 3
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_next is False  # Page 3 < 3 = False
        assert result.has_previous is True  # Page 3 > 1

    def test_create_pagination_result_single_page(self):
        """Test creating pagination result when all items fit on one page."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(5)]
        total_count = 5
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_count == 5
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 1  # (5 + 10 - 1) // 10 = 1
        assert result.has_next is False
        assert result.has_previous is False


class TestPaginationServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_pagination_result_empty_results(self):
        """Test creating pagination result with no items."""
        # Arrange
        items = []
        total_count = 0
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.items == []
        assert result.total_count == 0
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 0  # (0 + 10 - 1) // 10 = 0
        assert result.has_next is False  # Page 1 < 0 = False
        assert result.has_previous is False

    def test_create_pagination_result_exact_page_boundary(self):
        """Test when total_count is exactly divisible by page_size."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        total_count = 30  # Exactly 3 pages
        pagination = PaginationRequest(page=2, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_count == 30
        assert result.total_pages == 3  # (30 + 10 - 1) // 10 = 3
        assert result.has_next is True
        assert result.has_previous is True

    def test_create_pagination_result_last_page_exact_boundary(self):
        """Test last page when total_count is exactly divisible."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        total_count = 30
        pagination = PaginationRequest(page=3, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_pages == 3
        assert result.has_next is False  # Last page
        assert result.has_previous is True

    def test_create_pagination_result_one_item_per_page(self):
        """Test pagination with page_size=1."""
        # Arrange
        items = [_MockPaginationEntity(5, "item5")]
        total_count = 10
        pagination = PaginationRequest(page=5, page_size=1)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_count == 10
        assert result.total_pages == 10  # (10 + 1 - 1) // 1 = 10
        assert result.page == 5
        assert result.page_size == 1
        assert result.has_next is True  # Page 5 < 10
        assert result.has_previous is True  # Page 5 > 1

    def test_create_pagination_result_large_page_size(self):
        """Test pagination with page_size larger than total count."""
        # Arrange
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        total_count = 10
        pagination = PaginationRequest(page=1, page_size=100)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=total_count, pagination=pagination
        )

        # Assert
        assert result.total_pages == 1  # (10 + 100 - 1) // 100 = 1
        assert result.has_next is False
        assert result.has_previous is False


class TestPaginationServiceValidation:
    """Test validation methods."""

    def test_validate_pagination_request_valid(self):
        """Test validation succeeds with valid parameters."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=10)

        # Act & Assert - Should not raise
        PaginationService.validate_pagination_request(pagination)

    def test_validate_pagination_request_page_zero(self):
        """Test validation fails when page is 0."""
        # Arrange
        pagination = PaginationRequest(page=0, page_size=10)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PaginationService.validate_pagination_request(pagination)
        assert "Page must be >= 1" in str(exc_info.value)

    def test_validate_pagination_request_page_negative(self):
        """Test validation fails when page is negative."""
        # Arrange
        pagination = PaginationRequest(page=-1, page_size=10)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PaginationService.validate_pagination_request(pagination)
        assert "Page must be >= 1" in str(exc_info.value)

    def test_validate_pagination_request_page_size_zero(self):
        """Test validation fails when page_size is 0."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=0)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PaginationService.validate_pagination_request(pagination)
        assert "Page size must be > 0" in str(exc_info.value)

    def test_validate_pagination_request_page_size_negative(self):
        """Test validation fails when page_size is negative."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=-10)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PaginationService.validate_pagination_request(pagination)
        assert "Page size must be > 0" in str(exc_info.value)

    def test_validate_pagination_request_page_size_too_large(self):
        """Test validation fails when page_size exceeds maximum."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=101)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            PaginationService.validate_pagination_request(pagination)
        assert "Page size must be <= 100" in str(exc_info.value)

    def test_validate_pagination_request_page_size_at_limit(self):
        """Test validation succeeds when page_size is at maximum limit."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=100)

        # Act & Assert - Should not raise
        PaginationService.validate_pagination_request(pagination)


class TestPaginationServiceOffsetCalculation:
    """Test offset calculation for database queries."""

    def test_calculate_offset_first_page(self):
        """Test offset calculation for first page."""
        # Arrange
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        offset = PaginationService.calculate_offset(pagination)

        # Assert
        assert offset == 0  # (1 - 1) * 10 = 0

    def test_calculate_offset_second_page(self):
        """Test offset calculation for second page."""
        # Arrange
        pagination = PaginationRequest(page=2, page_size=10)

        # Act
        offset = PaginationService.calculate_offset(pagination)

        # Assert
        assert offset == 10  # (2 - 1) * 10 = 10

    def test_calculate_offset_third_page(self):
        """Test offset calculation for third page."""
        # Arrange
        pagination = PaginationRequest(page=3, page_size=10)

        # Act
        offset = PaginationService.calculate_offset(pagination)

        # Assert
        assert offset == 20  # (3 - 1) * 10 = 20

    def test_calculate_offset_different_page_size(self):
        """Test offset calculation with different page size."""
        # Arrange
        pagination = PaginationRequest(page=5, page_size=25)

        # Act
        offset = PaginationService.calculate_offset(pagination)

        # Assert
        assert offset == 100  # (5 - 1) * 25 = 100

    def test_calculate_offset_page_size_one(self):
        """Test offset calculation with page_size=1."""
        # Arrange
        pagination = PaginationRequest(page=50, page_size=1)

        # Act
        offset = PaginationService.calculate_offset(pagination)

        # Assert
        assert offset == 49  # (50 - 1) * 1 = 49


class TestPaginationServiceFeatureFlag:
    """Test feature flag behavior."""

    def test_feature_flag_default_value(self):
        """Test that FEATURE_CLEAN_REPOSITORIES defaults to False."""
        assert PaginationService.FEATURE_CLEAN_REPOSITORIES is False

    def test_service_works_with_flag_disabled(self):
        """Test service functions correctly when feature flag is False."""
        # Arrange
        PaginationService.FEATURE_CLEAN_REPOSITORIES = False
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=25, pagination=pagination
        )

        # Assert - Service should work normally
        assert result.total_pages == 3
        assert result.has_next is True

    def test_service_works_with_flag_enabled(self):
        """Test service functions correctly when feature flag is True."""
        # Arrange
        PaginationService.FEATURE_CLEAN_REPOSITORIES = True
        items = [_MockPaginationEntity(i, f"item{i}") for i in range(10)]
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=25, pagination=pagination
        )

        # Assert - Service should work normally
        assert result.total_pages == 3
        assert result.has_next is True

        # Cleanup
        PaginationService.FEATURE_CLEAN_REPOSITORIES = False


class TestPaginationServiceTypeCompatibility:
    """Test generic type compatibility."""

    def test_works_with_string_type(self):
        """Test pagination service works with string items."""
        # Arrange
        items = ["item1", "item2", "item3"]
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[str].create_pagination_result(
            items=items, total_count=3, pagination=pagination
        )

        # Assert
        assert result.items == items
        assert len(result.items) == 3

    def test_works_with_dict_type(self):
        """Test pagination service works with dict items."""
        # Arrange
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[dict].create_pagination_result(
            items=items, total_count=3, pagination=pagination
        )

        # Assert
        assert result.items == items
        assert len(result.items) == 3

    def test_works_with_custom_entity(self):
        """Test pagination service works with custom entity type."""
        # Arrange
        items = [_MockPaginationEntity(i, f"test{i}") for i in range(5)]
        pagination = PaginationRequest(page=1, page_size=10)

        # Act
        result = PaginationService[_MockPaginationEntity].create_pagination_result(
            items=items, total_count=5, pagination=pagination
        )

        # Assert
        assert all(isinstance(item, _MockPaginationEntity) for item in result.items)
        assert len(result.items) == 5


class TestPaginationServiceBusinessRules:
    """Test business rule compliance."""

    def test_ceiling_division_formula(self):
        """Test that total_pages uses ceiling division correctly."""
        test_cases = [
            (25, 10, 3),  # (25 + 10 - 1) // 10 = 34 // 10 = 3
            (30, 10, 3),  # (30 + 10 - 1) // 10 = 39 // 10 = 3
            (31, 10, 4),  # (31 + 10 - 1) // 10 = 40 // 10 = 4
            (1, 10, 1),  # (1 + 10 - 1) // 10 = 10 // 10 = 1
            (10, 10, 1),  # (10 + 10 - 1) // 10 = 19 // 10 = 1
            (11, 10, 2),  # (11 + 10 - 1) // 10 = 20 // 10 = 2
        ]

        for total_count, page_size, expected_pages in test_cases:
            # Arrange
            pagination = PaginationRequest(page=1, page_size=page_size)

            # Act
            result = PaginationService[_MockPaginationEntity].create_pagination_result(
                items=[], total_count=total_count, pagination=pagination
            )

            # Assert
            assert (
                result.total_pages == expected_pages
            ), f"Failed for total_count={total_count}, page_size={page_size}"

    def test_has_next_logic(self):
        """Test has_next flag is set correctly."""
        # Test cases: (page, total_pages, expected_has_next)
        test_cases = [
            (1, 3, True),  # First page, has next
            (2, 3, True),  # Middle page, has next
            (3, 3, False),  # Last page, no next
            (1, 1, False),  # Single page, no next
            (1, 0, False),  # Empty results, no next
        ]

        for page, total_pages, expected_has_next in test_cases:
            # Arrange
            # Calculate total_count from total_pages and page_size
            page_size = 10
            total_count = (total_pages * page_size) if total_pages > 0 else 0
            pagination = PaginationRequest(page=page, page_size=page_size)

            # Act
            result = PaginationService[_MockPaginationEntity].create_pagination_result(
                items=[], total_count=total_count, pagination=pagination
            )

            # Assert
            assert (
                result.has_next == expected_has_next
            ), f"Failed for page={page}, total_pages={total_pages}"

    def test_has_previous_logic(self):
        """Test has_previous flag is set correctly."""
        # Test cases: (page, expected_has_previous)
        test_cases = [
            (1, False),  # First page, no previous
            (2, True),  # Second page, has previous
            (3, True),  # Third page, has previous
            (10, True),  # Any page > 1, has previous
        ]

        for page, expected_has_previous in test_cases:
            # Arrange
            pagination = PaginationRequest(page=page, page_size=10)

            # Act
            result = PaginationService[_MockPaginationEntity].create_pagination_result(
                items=[],
                total_count=100,  # Arbitrary large count
                pagination=pagination,
            )

            # Assert
            assert (
                result.has_previous == expected_has_previous
            ), f"Failed for page={page}"
