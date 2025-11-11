"""
Unit tests for GlobalContextNestedData - Domain Entity

Tests the global context schema entity that provides structured data storage
for user-scoped global context across the application.
"""

import pytest

from fastmcp.task_management.domain.entities.global_context_schema import (
    GlobalContextNestedData,
)


class TestGlobalContextNestedData:
    """Test cases for GlobalContextNestedData entity."""

    @pytest.fixture
    def schema(self):
        """Create a GlobalContextNestedData instance for testing."""
        return GlobalContextNestedData()

    def test_set_nested_value_two_parts(self, schema):
        """Test setting nested value with 2-part path (line 182)."""
        # Test line 182: if hasattr(self, category)
        # For 2-part path, it sets the whole subcategory dict
        schema.set_nested_value("preferences.user_interface", {"theme": "dark"})
        assert schema.preferences["user_interface"] == {"theme": "dark"}

    def test_set_nested_value_three_parts_new_subcategory(self, schema):
        """Test setting nested value with 3 parts creating new subcategory (lines 184, 186, 188)."""
        # Test line 184: elif len(parts) == 3
        # Test line 186: if hasattr(self, category)
        # Test line 188: if subcategory not in category_data (creates new subcategory)
        # Use "customsettings" which doesn't exist in defaults
        schema.development["customsettings"] = {}  # Will trigger line 188
        schema.set_nested_value("development.newsub.enabled", "true")
        assert schema.development["newsub"]["enabled"] == "true"

    def test_set_nested_value_three_parts_existing_subcategory(self, schema):
        """Test setting nested value with 3 parts on existing subcategory (lines 184, 186)."""
        # Use existing subcategory
        # Test line 184: elif len(parts) == 3
        # Test line 186: if hasattr(self, category)
        # Line 188 should be False since "patterns" subcategory exists
        schema.set_nested_value("development.patterns.mvc", "enabled")

        assert schema.development["patterns"]["mvc"] == "enabled"

    def test_get_nested_value_two_parts(self, schema):
        """Test getting nested value with 2-part path."""
        schema.preferences["user_interface"] = {"theme": "dark"}
        value = schema.get_nested_value("preferences.user_interface")
        assert value == {"theme": "dark"}

    def test_get_nested_value_three_parts(self, schema):
        """Test getting nested value with 3-part path (lines 199, 201)."""
        # Setup data
        schema.development["patterns"] = {"mvc": "enabled"}

        # Test line 199: elif len(parts) == 3
        # Test line 201: if hasattr(self, category)
        value = schema.get_nested_value("development.patterns.mvc")
        assert value == "enabled"

    def test_get_nested_value_missing_returns_default(self, schema):
        """Test getting nested value returns default when not found."""
        value = schema.get_nested_value(
            "preferences.nonexistent", default="default_value"
        )
        assert value == "default_value"

    def test_get_nested_value_three_parts_missing(self, schema):
        """Test getting 3-part nested value returns default when not found."""
        value = schema.get_nested_value(
            "development.patterns.nonexistent", default="default"
        )
        assert value == "default"

    def test_set_get_roundtrip(self, schema):
        """Test setting and getting values roundtrip."""
        # Two-part path
        schema.set_nested_value("preferences.user_interface", {"language": "en"})
        assert schema.get_nested_value("preferences.user_interface") == {
            "language": "en"
        }

        # Three-part path
        schema.set_nested_value("development.tools.github", "connected")
        assert schema.get_nested_value("development.tools.github") == "connected"

    def test_nested_value_invalid_category(self, schema):
        """Test handling invalid category gracefully."""
        # This should not raise an error, just not set anything
        schema.set_nested_value("invalid_category.field", "value")

        # Verify nothing was set
        assert not hasattr(schema, "invalid_category")

    def test_get_nested_value_invalid_category(self, schema):
        """Test getting value with invalid category returns default."""
        value = schema.get_nested_value("invalid_category.field", default="default")
        assert value == "default"
