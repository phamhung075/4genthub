"""Test suite for Label Domain Entity"""

import pytest
from datetime import datetime, timezone

from fastmcp.task_management.domain.entities.label import Label


class TestLabelInitialization:
    """Test suite for Label initialization"""

    def test_minimal_label_creation(self):
        """Test creating label with minimal required parameters"""
        label_id = 1
        name = "Bug"
        
        label = Label(id=label_id, name=name)
        
        assert label.id == label_id
        assert label.name == name
        assert label.color == "#0066cc"  # Default color
        assert label.description == ""
        assert label.created_at is None

    def test_label_creation_with_all_parameters(self):
        """Test creating label with all parameters"""
        label_id = 2
        name = "Feature"
        color = "#00ff00"
        description = "New feature implementation"
        created_at = datetime.now(timezone.utc)
        
        label = Label(
            id=label_id,
            name=name,
            color=color,
            description=description,
            created_at=created_at
        )
        
        assert label.id == label_id
        assert label.name == name
        assert label.color == color
        assert label.description == description
        assert label.created_at == created_at

    def test_label_creation_with_custom_color(self):
        """Test creating label with custom color"""
        colors = [
            "#ff0000",  # Red
            "#00ff00",  # Green
            "#0000ff",  # Blue
            "#ffffff",  # White
            "#000000",  # Black
            "#abc",     # Short form
            "#123456"   # Full form
        ]
        
        for color in colors:
            label = Label(id=1, name="Test", color=color)
            assert label.color == color

    def test_label_creation_without_color(self):
        """Test creating label without specifying color uses default"""
        label = Label(id=1, name="Default Color Test")
        assert label.color == "#0066cc"


class TestLabelValidation:
    """Test suite for Label validation"""

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError"""
        with pytest.raises(ValueError, match="Label name cannot be empty"):
            Label(id=1, name="")

    def test_none_name_raises_error(self):
        """Test that None name raises ValueError"""
        with pytest.raises(ValueError, match="Label name cannot be empty"):
            Label(id=1, name=None)

    def test_whitespace_only_name_raises_error(self):
        """Test that whitespace-only name raises ValueError"""
        with pytest.raises(ValueError, match="Label name cannot be empty"):
            Label(id=1, name="   ")

    def test_invalid_color_format_raises_error(self):
        """Test that invalid color format raises ValueError"""
        invalid_colors = [
            "red",          # Named color
            "rgb(255,0,0)", # RGB format
            "#zzzzzz",      # Invalid hex characters
            "#12345",       # Invalid length (5 characters)
            "#1234567",     # Invalid length (7 characters)
            "123456",       # Missing #
            "#",            # Just #
            "",             # Empty string
        ]
        
        for invalid_color in invalid_colors:
            with pytest.raises(ValueError, match="Invalid color format"):
                Label(id=1, name="Test", color=invalid_color)

    def test_valid_hex_color_accepted(self):
        """Test that valid hex colors are accepted"""
        valid_colors = [
            "#000000",  # Black
            "#ffffff",  # White
            "#ff0000",  # Red
            "#00ff00",  # Green
            "#0000ff",  # Blue
            "#abc",     # Short form (3 chars)
            "#123",     # Short form numbers
            "#AbC",     # Mixed case
            "#FFFFFF",  # Uppercase
        ]
        
        for valid_color in valid_colors:
            label = Label(id=1, name="Test", color=valid_color)
            assert label.color == valid_color


class TestLabelColorValidation:
    """Test suite for Label color validation method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.label = Label(id=1, name="Test")

    def test_is_valid_hex_color_valid_formats(self):
        """Test _is_valid_hex_color with valid formats"""
        valid_colors = [
            "#000",
            "#fff",
            "#123",
            "#abc",
            "#000000",
            "#ffffff",
            "#123456",
            "#abcdef",
            "#ABCDEF",
            "#123ABC"
        ]
        
        for color in valid_colors:
            assert self.label._is_valid_hex_color(color) is True

    def test_is_valid_hex_color_invalid_formats(self):
        """Test _is_valid_hex_color with invalid formats"""
        invalid_colors = [
            "000",          # Missing #
            "#",            # Just #
            "#12",          # Too short
            "#12345",       # Invalid length
            "#1234567",     # Too long
            "#gggggg",      # Invalid hex characters
            "#xyz",         # Invalid hex characters
            "red",          # Named color
            "",             # Empty
            None,           # None
        ]
        
        for color in invalid_colors:
            assert self.label._is_valid_hex_color(color) is False

    def test_is_valid_hex_color_edge_cases(self):
        """Test _is_valid_hex_color with edge cases"""
        edge_cases = [
            ("#000", True),    # Minimum valid 3-char
            ("#FFF", True),    # Maximum valid 3-char
            ("#000000", True), # Minimum valid 6-char
            ("#FFFFFF", True), # Maximum valid 6-char
            ("#aA1", True),    # Mixed case 3-char
            ("#aA1bB2", True), # Mixed case 6-char
        ]
        
        for color, expected in edge_cases:
            assert self.label._is_valid_hex_color(color) is expected


class TestLabelStringRepresentation:
    """Test suite for Label string representations"""

    def test_str_representation(self):
        """Test __str__ method"""
        label = Label(id=1, name="Bug Fix")
        
        str_repr = str(label)
        assert str_repr == "Label(Bug Fix)"

    def test_str_representation_with_special_characters(self):
        """Test __str__ with special characters in name"""
        label = Label(id=1, name="Feature/Enhancement #1")
        
        str_repr = str(label)
        assert str_repr == "Label(Feature/Enhancement #1)"

    def test_repr_representation(self):
        """Test __repr__ method"""
        label = Label(id=42, name="Documentation", color="#ffaa00")
        
        repr_str = repr(label)
        assert repr_str == "Label(id=42, name='Documentation', color='#ffaa00')"

    def test_repr_representation_with_quotes_in_name(self):
        """Test __repr__ with quotes in name"""
        label = Label(id=1, name="Test's Label", color="#123456")
        
        repr_str = repr(label)
        assert repr_str == "Label(id=1, name='Test's Label', color='#123456')"


class TestLabelEquality:
    """Test suite for Label equality and comparison"""

    def test_labels_with_same_data_are_equal(self):
        """Test that labels with same data are considered equal"""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        label1 = Label(
            id=1,
            name="Feature",
            color="#ff0000",
            description="Feature label",
            created_at=created_at
        )
        
        label2 = Label(
            id=1,
            name="Feature",
            color="#ff0000",
            description="Feature label",
            created_at=created_at
        )
        
        assert label1 == label2

    def test_labels_with_different_ids_are_not_equal(self):
        """Test that labels with different IDs are not equal"""
        label1 = Label(id=1, name="Test")
        label2 = Label(id=2, name="Test")
        
        assert label1 != label2

    def test_labels_with_different_names_are_not_equal(self):
        """Test that labels with different names are not equal"""
        label1 = Label(id=1, name="Bug")
        label2 = Label(id=1, name="Feature")
        
        assert label1 != label2

    def test_labels_with_different_colors_are_not_equal(self):
        """Test that labels with different colors are not equal"""
        label1 = Label(id=1, name="Test", color="#ff0000")
        label2 = Label(id=1, name="Test", color="#00ff00")
        
        assert label1 != label2


class TestLabelBusinessLogic:
    """Test suite for Label business logic"""

    def test_label_represents_category(self):
        """Test that label can represent different categories"""
        categories = [
            ("bug", "#ff0000", "Bug reports and fixes"),
            ("feature", "#00ff00", "New feature implementation"),
            ("documentation", "#0066cc", "Documentation updates"),
            ("testing", "#ffaa00", "Testing and QA"),
            ("security", "#800080", "Security-related issues")
        ]
        
        labels = []
        for i, (name, color, description) in enumerate(categories, 1):
            label = Label(
                id=i,
                name=name.title(),
                color=color,
                description=description
            )
            labels.append(label)
            
            assert label.name == name.title()
            assert label.color == color
            assert label.description == description

    def test_label_can_have_long_description(self):
        """Test that label can have long description"""
        long_description = (
            "This is a very long description that might be used to provide "
            "detailed information about what this label represents and how "
            "it should be used in the context of task management and organization."
        )
        
        label = Label(
            id=1,
            name="Detailed Label",
            description=long_description
        )
        
        assert label.description == long_description

    def test_label_id_can_be_large_number(self):
        """Test that label can have large ID numbers"""
        large_id = 999999999
        
        label = Label(id=large_id, name="Large ID Test")
        
        assert label.id == large_id

    def test_label_name_can_contain_unicode(self):
        """Test that label name can contain unicode characters"""
        unicode_names = [
            "优先级",       # Chinese
            "Priorité",     # French
            "Приоритет",    # Russian
            "🐛 Bug",       # Emoji
            "Feature ⭐",   # Emoji
        ]
        
        for i, name in enumerate(unicode_names, 1):
            label = Label(id=i, name=name)
            assert label.name == name


class TestLabelEdgeCases:
    """Test suite for Label edge cases"""

    def test_label_with_minimum_values(self):
        """Test label with minimum possible values"""
        label = Label(id=0, name="a")  # Minimum valid name
        
        assert label.id == 0
        assert label.name == "a"
        assert label.color == "#0066cc"

    def test_label_with_negative_id(self):
        """Test label with negative ID (should be allowed)"""
        label = Label(id=-1, name="Negative ID")
        
        assert label.id == -1
        assert label.name == "Negative ID"

    def test_label_color_case_insensitive_validation(self):
        """Test that color validation is case insensitive"""
        colors = [
            "#abc",
            "#ABC",
            "#aBc",
            "#123def",
            "#123DEF",
            "#123dEf"
        ]
        
        for color in colors:
            label = Label(id=1, name="Case Test", color=color)
            assert label.color == color

    def test_label_with_very_long_name(self):
        """Test label with very long name"""
        long_name = "x" * 1000
        
        label = Label(id=1, name=long_name)
        
        assert label.name == long_name
        assert len(label.name) == 1000

    def test_label_name_with_leading_trailing_spaces(self):
        """Test that label name preserves leading/trailing spaces"""
        name_with_spaces = "  Label Name  "
        
        # Note: Current implementation doesn't trim spaces in validation
        # This test documents the current behavior
        label = Label(id=1, name=name_with_spaces)
        
        assert label.name == name_with_spaces

    def test_label_description_can_be_empty(self):
        """Test that empty description is allowed"""
        label = Label(id=1, name="Test", description="")
        
        assert label.description == ""

    def test_label_created_at_can_be_none(self):
        """Test that created_at can be None"""
        label = Label(id=1, name="Test", created_at=None)
        
        assert label.created_at is None

    def test_label_created_at_with_future_date(self):
        """Test label with future created_at date"""
        future_date = datetime(2030, 12, 31, 23, 59, 59)
        
        label = Label(id=1, name="Future", created_at=future_date)
        
        assert label.created_at == future_date

    def test_multiple_labels_with_same_name_different_ids(self):
        """Test creating multiple labels with same name but different IDs"""
        name = "Duplicate Name"
        
        label1 = Label(id=1, name=name, color="#ff0000")
        label2 = Label(id=2, name=name, color="#00ff00")
        
        assert label1.name == label2.name
        assert label1.id != label2.id
        assert label1.color != label2.color
        assert label1 != label2  # Should not be equal due to different IDs


class TestLabelSerializationScenarios:
    """Test suite for scenarios involving label serialization/deserialization"""

    def test_label_attributes_are_accessible(self):
        """Test that all label attributes are accessible"""
        created_at = datetime.now(timezone.utc)
        
        label = Label(
            id=123,
            name="Serialization Test",
            color="#abcdef",
            description="Test description",
            created_at=created_at
        )
        
        # All attributes should be accessible
        assert hasattr(label, 'id')
        assert hasattr(label, 'name')
        assert hasattr(label, 'color')
        assert hasattr(label, 'description')
        assert hasattr(label, 'created_at')
        
        # Values should match
        assert label.id == 123
        assert label.name == "Serialization Test"
        assert label.color == "#abcdef"
        assert label.description == "Test description"
        assert label.created_at == created_at

    def test_label_can_be_converted_to_dict_manually(self):
        """Test that label can be manually converted to dictionary"""
        label = Label(
            id=456,
            name="Dict Test",
            color="#123456",
            description="Dictionary conversion test"
        )
        
        # Manual dict conversion
        label_dict = {
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'description': label.description,
            'created_at': label.created_at
        }
        
        assert label_dict['id'] == 456
        assert label_dict['name'] == "Dict Test"
        assert label_dict['color'] == "#123456"
        assert label_dict['description'] == "Dictionary conversion test"
        assert label_dict['created_at'] is None

    def test_label_fields_are_mutable(self):
        """Test that label fields can be modified after creation"""
        label = Label(id=1, name="Mutable Test")
        
        # Modify fields
        label.name = "Updated Name"
        label.color = "#ff00ff"
        label.description = "Updated description"
        label.created_at = datetime.now(timezone.utc)
        
        assert label.name == "Updated Name"
        assert label.color == "#ff00ff"
        assert label.description == "Updated description"
        assert label.created_at is not None

    def test_label_modification_preserves_other_fields(self):
        """Test that modifying one field doesn't affect others"""
        original_created_at = datetime(2024, 1, 1)
        
        label = Label(
            id=789,
            name="Preservation Test",
            color="#fedcba",
            description="Original description",
            created_at=original_created_at
        )
        
        # Modify only the name
        label.name = "Modified Name"
        
        # Other fields should remain unchanged
        assert label.id == 789
        assert label.color == "#fedcba"
        assert label.description == "Original description"
        assert label.created_at == original_created_at