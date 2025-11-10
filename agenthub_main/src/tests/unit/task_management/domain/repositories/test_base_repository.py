"""
Unit tests for BaseRepository Interface

Tests verify that BaseRepository provides a proper abstract interface
for domain repositories following DDD principles.
"""

import pytest

from fastmcp.task_management.domain.repositories.base_repository import (
    BaseRepository,
    PaginationRequest,
)


# Mock implementation for testing
class MockRepository(BaseRepository[str]):
    """Mock repository for testing BaseRepository interface"""

    def find_by_criteria(self, filters, pagination=None):
        pass

    def find_all(self, pagination=None):
        pass

    def count(self):
        pass

    def count_by_criteria(self, filters):
        pass

    def exists(self, entity_id):
        pass

    def bulk_save(self, entities):
        pass

    def bulk_delete(self, entity_ids):
        pass


class TestBaseRepositoryInterface:
    """Test suite for BaseRepository abstract interface"""

    def test_cannot_instantiate_abstract_repository(self):
        """
        Test: BaseRepository is abstract and cannot be instantiated directly
        Expected: Raises TypeError
        """
        with pytest.raises(TypeError):
            BaseRepository()  # Should fail - abstract class

    def test_mock_repository_implements_interface(self):
        """
        Test: Mock repository properly implements BaseRepository interface
        Expected: Can instantiate without errors
        """
        repo = MockRepository()
        assert isinstance(repo, BaseRepository)

    def test_pagination_request_offset_auto_calculation(self):
        """
        Test: PaginationRequest automatically calculates offset
        Expected: offset = (page - 1) * page_size
        """
        # Page 1
        pagination = PaginationRequest(page=1, page_size=20)
        assert pagination.offset == 0

        # Page 2
        pagination = PaginationRequest(page=2, page_size=20)
        assert pagination.offset == 20

        # Page 3, custom page_size
        pagination = PaginationRequest(page=3, page_size=10)
        assert pagination.offset == 20

    def test_pagination_request_manual_offset(self):
        """
        Test: PaginationRequest respects manually provided offset
        Expected: Uses provided offset instead of calculating
        """
        pagination = PaginationRequest(page=2, page_size=20, offset=50)
        assert pagination.offset == 50  # Manual offset preserved
