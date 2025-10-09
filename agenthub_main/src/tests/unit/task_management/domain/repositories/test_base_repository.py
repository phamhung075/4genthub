"""
Unit tests for BaseRepository Interface - Feature Flag Testing

Tests verify that BaseRepository.create_pagination_result() behaves correctly
based on FEATURE_CLEAN_REPOSITORIES flag:
- flag=False: Legacy behavior (backward compatibility)
- flag=True: Raises NotImplementedError directing to PaginationService
"""

import os
import pytest
from typing import List
from unittest.mock import patch

from fastmcp.task_management.domain.repositories.base_repository import (
    BaseRepository,
    PaginationRequest,
    PaginationResult
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


class TestBaseRepositoryPaginationMethod:
    """Test suite for BaseRepository.create_pagination_result() feature flag behavior"""

    def test_pagination_with_flag_false_legacy_behavior(self):
        """
        Test: create_pagination_result() works normally when flag=False
        Expected: Returns PaginationResult with correct calculations
        """
        with patch.dict(os.environ, {"FEATURE_CLEAN_REPOSITORIES": "false"}):
            # Reload class to pick up new environment variable
            from fastmcp.task_management.domain.repositories.base_repository import BaseRepository

            class TestRepo(BaseRepository[str]):
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

            repo = TestRepo()

            # Test data
            items = ["item1", "item2", "item3"]
            total_count = 10
            pagination = PaginationRequest(page=2, page_size=3)

            # Should work without error
            result = repo.create_pagination_result(items, total_count, pagination)

            # Verify result structure
            assert isinstance(result, PaginationResult)
            assert result.items == items
            assert result.total_count == 10
            assert result.page == 2
            assert result.page_size == 3
            assert result.total_pages == 4  # ceil(10/3)
            assert result.has_next is True  # page 2 < 4
            assert result.has_previous is True  # page 2 > 1

    def test_pagination_with_flag_true_raises_error(self):
        """
        Test: create_pagination_result() raises NotImplementedError when flag=True
        Expected: Clear error message directing to PaginationService
        """
        with patch.dict(os.environ, {"FEATURE_CLEAN_REPOSITORIES": "true"}):
            # Reload class to pick up new environment variable
            from fastmcp.task_management.domain.repositories.base_repository import BaseRepository

            class TestRepo(BaseRepository[str]):
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

            repo = TestRepo()

            # Test data
            items = ["item1", "item2"]
            total_count = 5
            pagination = PaginationRequest(page=1, page_size=2)

            # Should raise NotImplementedError
            with pytest.raises(NotImplementedError) as exc_info:
                repo.create_pagination_result(items, total_count, pagination)

            # Verify error message directs to PaginationService
            error_message = str(exc_info.value)
            assert "PaginationService" in error_message
            assert "clean separation of concerns" in error_message
            assert "create_pagination_result" in error_message

    def test_pagination_calculations_accuracy(self):
        """
        Test: Verify pagination calculations are accurate (flag=False)
        Expected: All edge cases handled correctly
        """
        with patch.dict(os.environ, {"FEATURE_CLEAN_REPOSITORIES": "false"}):
            from fastmcp.task_management.domain.repositories.base_repository import BaseRepository

            class TestRepo(BaseRepository[str]):
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

            repo = TestRepo()

            # Test Case 1: First page
            result = repo.create_pagination_result(
                items=["a", "b"],
                total_count=10,
                pagination=PaginationRequest(page=1, page_size=2)
            )
            assert result.page == 1
            assert result.total_pages == 5
            assert result.has_previous is False  # First page
            assert result.has_next is True  # More pages

            # Test Case 2: Last page
            result = repo.create_pagination_result(
                items=["i", "j"],
                total_count=10,
                pagination=PaginationRequest(page=5, page_size=2)
            )
            assert result.page == 5
            assert result.total_pages == 5
            assert result.has_previous is True  # Not first page
            assert result.has_next is False  # Last page

            # Test Case 3: Uneven division
            result = repo.create_pagination_result(
                items=["a", "b", "c"],
                total_count=7,
                pagination=PaginationRequest(page=1, page_size=3)
            )
            assert result.total_pages == 3  # ceil(7/3)

            # Test Case 4: Single page
            result = repo.create_pagination_result(
                items=["a", "b"],
                total_count=2,
                pagination=PaginationRequest(page=1, page_size=10)
            )
            assert result.total_pages == 1
            assert result.has_previous is False
            assert result.has_next is False

    def test_flag_default_value_is_false(self):
        """
        Test: Verify default flag value is False (backward compatibility)
        Expected: Flag defaults to False when not set
        """
        with patch.dict(os.environ, {}, clear=True):
            # Remove FEATURE_CLEAN_REPOSITORIES from environment
            if "FEATURE_CLEAN_REPOSITORIES" in os.environ:
                del os.environ["FEATURE_CLEAN_REPOSITORIES"]

            from fastmcp.task_management.domain.repositories.base_repository import BaseRepository

            class TestRepo(BaseRepository[str]):
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

            repo = TestRepo()

            # Should work (flag defaults to False)
            items = ["test"]
            result = repo.create_pagination_result(
                items=items,
                total_count=1,
                pagination=PaginationRequest(page=1, page_size=10)
            )

            assert isinstance(result, PaginationResult)
            assert result.items == items


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
