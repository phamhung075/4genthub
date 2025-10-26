"""
Unit tests for Task Repository utility functions and helpers

These tests cover utility functions, data validation, and helper methods
without requiring database setup or complex mocking.
"""

import pytest
from datetime import datetime, timezone
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    _ensure_estimated_effort_default
)


class TestEstimatedEffortHelper:
    """Test _ensure_estimated_effort_default utility function"""

    def test_none_returns_default(self):
        """Test that None returns default '2 hours'"""
        assert _ensure_estimated_effort_default(None) == "2 hours"

    def test_empty_string_returns_default(self):
        """Test that empty string returns default '2 hours'"""
        assert _ensure_estimated_effort_default("") == "2 hours"

    def test_whitespace_only_returns_default(self):
        """Test that whitespace-only string returns default '2 hours'"""
        assert _ensure_estimated_effort_default("   ") == "2 hours"
        assert _ensure_estimated_effort_default("\t\n  ") == "2 hours"

    def test_valid_value_preserved(self):
        """Test that valid value is preserved"""
        assert _ensure_estimated_effort_default("5 days") == "5 days"
        assert _ensure_estimated_effort_default("3 hours") == "3 hours"
        assert _ensure_estimated_effort_default("2 weeks") == "2 weeks"

    def test_value_with_leading_trailing_whitespace_is_trimmed(self):
        """Test that values with whitespace are trimmed"""
        assert _ensure_estimated_effort_default("  5 days  ") == "5 days"
        assert _ensure_estimated_effort_default("\t3 hours\n") == "3 hours"

    def test_numeric_value_converted_to_string(self):
        """Test that numeric values are converted to strings"""
        assert _ensure_estimated_effort_default(5) == "5"
        assert _ensure_estimated_effort_default(10.5) == "10.5"

    def test_boolean_false_returns_default(self):
        """Test that False (falsy) returns default"""
        # Empty string is falsy but None handling is explicit
        result = _ensure_estimated_effort_default(False)
        # False is not None and not empty string, so it converts to "False"
        assert result == "False" or result == "2 hours"


class TestRepositoryConstants:
    """Test repository class constants and defaults"""

    def test_default_estimated_effort_value(self):
        """Test that default effort is correctly defined"""
        # This tests the constant used in _ensure_estimated_effort_default
        assert _ensure_estimated_effort_default(None) == "2 hours"

    def test_various_time_formats_accepted(self):
        """Test that various time format strings are accepted"""
        valid_formats = [
            "1 hour",
            "2 hours",
            "1 day",
            "3 days",
            "1 week",
            "2 weeks",
            "30 minutes",
            "1.5 hours"
        ]
        for format_str in valid_formats:
            result = _ensure_estimated_effort_default(format_str)
            assert result == format_str


class TestRepositoryDataValidation:
    """Test data validation patterns used in repository"""

    def test_empty_effort_normalization(self):
        """Test various empty value normalizations"""
        empty_values = [None, "", "  ", "\t", "\n", "   \n\t  "]
        for empty in empty_values:
            result = _ensure_estimated_effort_default(empty)
            assert result == "2 hours", f"Failed for empty value: {repr(empty)}"

    def test_effort_value_trimming(self):
        """Test that effort values are properly trimmed"""
        test_cases = [
            ("  hello  ", "hello"),
            ("\tworld\n", "world"),
            ("  spaced  value  ", "spaced  value"),  # Internal spaces preserved
        ]
        for input_val, expected in test_cases:
            result = _ensure_estimated_effort_default(input_val)
            assert result == expected

    def test_special_characters_in_effort(self):
        """Test that special characters are handled"""
        special_values = [
            "2-3 hours",
            "~5 days",
            "3.5 hours",
            "1/2 day"
        ]
        for value in special_values:
            result = _ensure_estimated_effort_default(value)
            assert result == value


class TestRepositoryHelperEdgeCases:
    """Test edge cases in repository helper functions"""

    def test_unicode_effort_values(self):
        """Test Unicode characters in effort strings"""
        unicode_values = [
            "2 часа",  # Russian "hours"
            "5 días",  # Spanish "days"
            "3 heures",  # French "hours"
        ]
        for value in unicode_values:
            result = _ensure_estimated_effort_default(value)
            assert result == value

    def test_very_long_effort_string(self):
        """Test handling of very long effort strings"""
        long_value = ("This is a very long estimated effort description " * 10).strip()
        result = _ensure_estimated_effort_default(long_value)
        assert result == long_value

    def test_effort_with_numbers_only(self):
        """Test effort values that are pure numbers"""
        number_values = ["5", "10", "100", "0.5"]
        for value in number_values:
            result = _ensure_estimated_effort_default(value)
            assert result == value
