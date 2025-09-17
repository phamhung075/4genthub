"""Unit tests for SubtaskId value object."""

import pytest
import uuid
from unittest.mock import patch, Mock

from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId

pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

class TestSubtaskIdCreation:
    """Test SubtaskId creation and validation."""
    
    def test_create_subtask_id_with_hex_string(self):
        """Test creating SubtaskId with 32-character hex string."""
        hex_id = "550e8400e29b41d4a716446655440001"
        subtask_id = SubtaskId(hex_id)
        
        # Should be stored in canonical format
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
        assert str(subtask_id) == expected
    
    def test_create_subtask_id_with_canonical_uuid(self):
        """Test creating SubtaskId with canonical UUID format."""
        canonical = "550e8400-e29b-41d4-a716-446655440001"
        subtask_id = SubtaskId(canonical)
        
        # Should store in canonical format
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_converts_to_lowercase(self):
        """Test that SubtaskId converts uppercase to lowercase."""
        upper_id = "550E8400E29B41D4A716446655440001"
        subtask_id = SubtaskId(upper_id)
        
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_mixed_case_with_hyphens(self):
        """Test creating SubtaskId with mixed case and hyphens."""
        mixed = "550E8400-e29B-41d4-A716-446655440001"
        subtask_id = SubtaskId(mixed)
        
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_strips_whitespace(self):
        """Test that SubtaskId strips leading/trailing whitespace."""
        padded = "  550e8400-e29b-41d4-a716-446655440001  "
        subtask_id = SubtaskId(padded)
        
        assert subtask_id.value == padded.strip()


class TestSubtaskIdValidation:
    
    """Test SubtaskId validation rules."""
    
    def test_subtask_id_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Subtask ID cannot be empty"):
            SubtaskId("")
    
    def test_subtask_id_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Subtask ID cannot be empty"):
            SubtaskId("   ")
    
    def test_subtask_id_non_string_raises_error(self):
        """Test that non-string value raises TypeError."""
        with pytest.raises(TypeError, match="Subtask ID value must be a string"):
            SubtaskId(12345)
        
        with pytest.raises(TypeError, match="Subtask ID value must be a string"):
            SubtaskId(None)
    
    def test_subtask_id_invalid_format_raises_error(self):
        """Test that truly invalid formats raise ValueError."""
        invalid_formats = [
            "@@invalid@@",  # Special characters not allowed
            "550e8400-e29b-41d4-a716-446655440001z",  # Invalid character 'z' in UUID
            "550e8400.999",  # Invalid hierarchical format (not full UUID)
            "g50e8400e29b41d4a716446655440001",  # Invalid hex character 'g'
            "test-@-123",  # Invalid character '@' in test ID
        ]

        for invalid in invalid_formats:
            with pytest.raises(ValueError, match="Invalid Subtask ID format"):
                SubtaskId(invalid)
    
    def test_subtask_id_valid_uuid_formats(self):
        """Test various valid UUID formats."""
        test_cases = [
            ("550e8400e29b41d4a716446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Hex to canonical
            ("550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Canonical stays canonical
            ("550E8400E29B41D4A716446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Uppercase hex to canonical
            ("550e8400-E29B-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Mixed case to canonical
        ]
        
        for input_format, expected_canonical in test_cases:
            subtask_id = SubtaskId(input_format)
            assert subtask_id.value == expected_canonical


class TestSubtaskIdGeneration:

    """Test SubtaskId generation."""
    
    def test_generate_new_subtask_id(self):
        """Test generating new SubtaskId."""
        subtask_id1 = SubtaskId.generate_new()
        subtask_id2 = SubtaskId.generate_new()
        
        # Should generate valid UUIDs
        assert len(subtask_id1.value) == 36
        assert len(subtask_id2.value) == 36
        
        # Should be unique
        assert subtask_id1 != subtask_id2
        assert subtask_id1.value != subtask_id2.value
    
    def test_generated_subtask_id_format(self):
        """Test that generated SubtaskId has correct format."""
        subtask_id = SubtaskId.generate_new()
        
        # Should be lowercase canonical format with hyphens
        assert subtask_id.value.islower()
        assert len(subtask_id.value) == 36  # Canonical format
        assert subtask_id.value.count('-') == 4  # Four hyphens
        # Check format pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = subtask_id.value.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
    
    @patch('uuid.uuid4')
    def test_generate_uses_uuid4(self, mock_uuid4):
        """Test that generate_new uses uuid4."""
        mock_uuid = Mock()
        mock_uuid.hex = "550e8400e29b41d4a716446655440001"  # Hex format for .hex property
        mock_uuid.__str__ = Mock(return_value="550e8400-e29b-41d4-a716-446655440001")  # Canonical format for str()
        mock_uuid4.return_value = mock_uuid
        
        subtask_id = SubtaskId.generate_new()
        
        assert subtask_id.value == "550e8400-e29b-41d4-a716-446655440001"  # Stored in canonical format
        mock_uuid4.assert_called_once()


class TestSubtaskIdEquality:

    """Test SubtaskId equality and hashing."""
    
    def test_subtask_id_equality(self):
        """Test SubtaskId equality comparison."""
        id1 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id3 = SubtaskId("550e8400e29b41d4a716446655440002")
        
        assert id1 == id2
        assert id1 != id3
        assert id2 != id3
    
    def test_subtask_id_equality_with_different_formats(self):
        """Test equality with different input formats."""
        id1 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id3 = SubtaskId("550E8400E29B41D4A716446655440001")
        
        # All should be equal after normalization
        assert id1 == id2
        assert id1 == id3
        assert id2 == id3
    
    def test_subtask_id_not_equal_to_other_types(self):
        """Test that SubtaskId is not equal to other types."""
        subtask_id = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        
        assert subtask_id != "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id != 123
        assert subtask_id != None
        assert subtask_id != []
    
    def test_subtask_id_hashing(self):
        """Test SubtaskId hashing for use in sets and dicts."""
        id1 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")  # Same ID, different format
        id3 = SubtaskId("550e8400e29b41d4a716446655440002")
        
        # Same IDs should have same hash
        assert hash(id1) == hash(id2)
        
        # Can be used in sets
        id_set = {id1, id2, id3}
        assert len(id_set) == 2  # id1 and id2 are the same
        
        # Can be used as dict keys
        id_dict = {id1: "value1", id3: "value3"}
        id_dict[id2] = "value2"  # Should overwrite id1's value
        assert len(id_dict) == 2
        assert id_dict[id1] == "value2"


class TestSubtaskIdStringRepresentation:

    """Test SubtaskId string representations."""
    
    def test_str_representation(self):
        """Test __str__ method."""
        subtask_id = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        assert str(subtask_id) == "550e8400-e29b-41d4-a716-446655440001"
    
    def test_repr_representation(self):
        """Test __repr__ method."""
        subtask_id = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        assert repr(subtask_id) == "SubtaskId('550e8400-e29b-41d4-a716-446655440001')"
    
    def test_repr_eval_roundtrip(self):
        """Test that repr can be used to recreate the object."""
        original = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        repr_str = repr(original)
        
        # Should be able to eval the repr (in a safe context)
        recreated = eval(repr_str, {"SubtaskId": SubtaskId})
        assert recreated == original


class TestSubtaskIdImmutability:

    """Test SubtaskId immutability."""
    
    def test_subtask_id_is_frozen(self):
        """Test that SubtaskId is immutable (frozen dataclass)."""
        subtask_id = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        
        # Should not be able to modify value
        with pytest.raises(AttributeError):
            subtask_id.value = "550e8400e29b41d4a716446655440002"
    
    def test_subtask_id_value_cannot_be_deleted(self):
        """Test that SubtaskId value cannot be deleted."""
        subtask_id = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        
        with pytest.raises(AttributeError):
            del subtask_id.value


class TestSubtaskIdUsageScenarios:

    """Test SubtaskId in typical usage scenarios."""
    
    def test_subtask_id_in_collections(self):
        """Test using SubtaskId in various collections."""
        id1 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = SubtaskId("550e8400e29b41d4a716446655440002")
        id3 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")  # Duplicate of id1
        
        # List usage
        id_list = [id1, id2, id3]
        assert len(id_list) == 3
        assert id_list.count(id1) == 2
        
        # Set usage (deduplication)
        id_set = set(id_list)
        assert len(id_set) == 2
        assert id1 in id_set
        assert id2 in id_set
        
        # Dict usage
        id_dict = {
            id1: "First subtask",
            id2: "Second subtask"
        }
        assert id_dict[id3] == "First subtask"  # id3 equals id1
    
    def test_subtask_id_sorting(self):
        """Test that SubtaskIds can be sorted."""
        ids = [
            SubtaskId("550e8400e29b41d4a716446655440003"),
            SubtaskId("550e8400-e29b-41d4-a716-446655440001"),
            SubtaskId("550e8400e29b41d4a716446655440002"),
        ]
        
        sorted_ids = sorted(ids, key=lambda x: x.value)
        
        assert sorted_ids[0].value == "550e8400-e29b-41d4-a716-446655440001"
        assert sorted_ids[1].value == "550e8400-e29b-41d4-a716-446655440002"
        assert sorted_ids[2].value == "550e8400-e29b-41d4-a716-446655440003"
    
    def test_subtask_id_as_function_parameter(self):
        """Test passing SubtaskId as function parameter."""
        def process_subtask(subtask_id: SubtaskId) -> str:
            return f"Processing subtask: {subtask_id}"
        
        id1 = SubtaskId("550e8400-e29b-41d4-a716-446655440001")
        result = process_subtask(id1)
        
        assert result == "Processing subtask: 550e8400-e29b-41d4-a716-446655440001"