"""Unit tests for TaskId value object."""

from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.value_objects.task_id import TaskId

pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

class TestTaskIdCreation:
    """Test TaskId creation and validation."""
    
    def test_create_subtask_id_with_hex_string(self):
        """Test creating TaskId with 32-character hex string."""
        hex_id = "550e8400e29b41d4a716446655440001"
        subtask_id = TaskId(hex_id)
        
        # Should be stored in canonical format
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
        assert str(subtask_id) == expected
    
    def test_create_subtask_id_with_canonical_uuid(self):
        """Test creating TaskId with canonical UUID format."""
        canonical = "550e8400-e29b-41d4-a716-446655440001"
        subtask_id = TaskId(canonical)
        
        # Should store in canonical format
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_converts_to_lowercase(self):
        """Test that TaskId converts uppercase to lowercase."""
        upper_id = "550E8400E29B41D4A716446655440001"
        subtask_id = TaskId(upper_id)
        
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_mixed_case_with_hyphens(self):
        """Test creating TaskId with mixed case and hyphens."""
        mixed = "550E8400-e29B-41d4-A716-446655440001"
        subtask_id = TaskId(mixed)
        
        expected = "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id.value == expected
    
    def test_create_subtask_id_strips_whitespace(self):
        """Test that TaskId strips leading/trailing whitespace."""
        padded = "  550e8400-e29b-41d4-a716-446655440001  "
        subtask_id = TaskId(padded)
        
        assert subtask_id.value == padded.strip()


class TestTaskIdValidation:
    
    """Test TaskId validation rules."""
    
    def test_subtask_id_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="TaskId cannot be empty"):
            TaskId("")

    def test_subtask_id_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="TaskId cannot be empty"):
            TaskId("   ")

    def test_subtask_id_non_string_raises_error(self):
        """Test that non-string value raises TypeError."""
        with pytest.raises(TypeError, match="TaskId value must be a string"):
            TaskId(12345)

        # None raises ValueError (checked first before type check)
        with pytest.raises(ValueError, match="TaskId cannot be None"):
            TaskId(None)

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
            with pytest.raises(ValueError, match="Invalid TaskId format"):
                TaskId(invalid)
    
    def test_subtask_id_valid_uuid_formats(self):
        """Test various valid UUID formats."""
        test_cases = [
            ("550e8400e29b41d4a716446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Hex to canonical
            ("550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Canonical stays canonical
            ("550E8400E29B41D4A716446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Uppercase hex to canonical
            ("550e8400-E29B-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440001"),  # Mixed case to canonical
        ]
        
        for input_format, expected_canonical in test_cases:
            subtask_id = TaskId(input_format)
            assert subtask_id.value == expected_canonical


class TestTaskIdGeneration:

    """Test TaskId generation."""
    
    def test_generate_new_subtask_id(self):
        """Test generating new TaskId."""
        subtask_id1 = TaskId.generate_new()
        subtask_id2 = TaskId.generate_new()
        
        # Should generate valid UUIDs
        assert len(subtask_id1.value) == 36
        assert len(subtask_id2.value) == 36
        
        # Should be unique
        assert subtask_id1 != subtask_id2
        assert subtask_id1.value != subtask_id2.value
    
    def test_generated_subtask_id_format(self):
        """Test that generated TaskId has correct format."""
        subtask_id = TaskId.generate_new()
        
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
        
        subtask_id = TaskId.generate_new()
        
        assert subtask_id.value == "550e8400-e29b-41d4-a716-446655440001"  # Stored in canonical format
        mock_uuid4.assert_called_once()


class TestTaskIdEquality:

    """Test TaskId equality and hashing."""
    
    def test_subtask_id_equality(self):
        """Test TaskId equality comparison."""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id3 = TaskId("550e8400e29b41d4a716446655440002")
        
        assert id1 == id2
        assert id1 != id3
        assert id2 != id3
    
    def test_subtask_id_equality_with_different_formats(self):
        """Test equality with different input formats."""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id3 = TaskId("550E8400E29B41D4A716446655440001")
        
        # All should be equal after normalization
        assert id1 == id2
        assert id1 == id3
        assert id2 == id3
    
    def test_subtask_id_not_equal_to_other_types(self):
        """Test that TaskId is not equal to other types."""
        subtask_id = TaskId("550e8400-e29b-41d4-a716-446655440001")
        
        assert subtask_id != "550e8400-e29b-41d4-a716-446655440001"
        assert subtask_id != 123
        assert subtask_id is not None
        assert subtask_id != []
    
    def test_subtask_id_hashing(self):
        """Test TaskId hashing for use in sets and dicts."""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId("550e8400-e29b-41d4-a716-446655440001")  # Same ID, different format
        id3 = TaskId("550e8400e29b41d4a716446655440002")
        
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


class TestTaskIdStringRepresentation:

    """Test TaskId string representations."""
    
    def test_str_representation(self):
        """Test __str__ method."""
        subtask_id = TaskId("550e8400-e29b-41d4-a716-446655440001")
        assert str(subtask_id) == "550e8400-e29b-41d4-a716-446655440001"
    
    def test_repr_representation(self):
        """Test __repr__ method."""
        subtask_id = TaskId("550e8400-e29b-41d4-a716-446655440001")
        # Dataclass repr includes field name
        assert repr(subtask_id) == "TaskId(value='550e8400-e29b-41d4-a716-446655440001')"
    
    def test_repr_eval_roundtrip(self):
        """Test that repr can be used to recreate the object."""
        original = TaskId("550e8400-e29b-41d4-a716-446655440001")
        repr_str = repr(original)
        
        # Should be able to eval the repr (in a safe context)
        recreated = eval(repr_str, {"TaskId": TaskId})
        assert recreated == original


class TestTaskIdImmutability:

    """Test TaskId immutability."""
    
    def test_subtask_id_is_frozen(self):
        """Test that TaskId is immutable (frozen dataclass)."""
        subtask_id = TaskId("550e8400-e29b-41d4-a716-446655440001")
        
        # Should not be able to modify value
        with pytest.raises(AttributeError):
            subtask_id.value = "550e8400e29b41d4a716446655440002"
    
    def test_subtask_id_value_cannot_be_deleted(self):
        """Test that TaskId value cannot be deleted."""
        subtask_id = TaskId("550e8400-e29b-41d4-a716-446655440001")
        
        with pytest.raises(AttributeError):
            del subtask_id.value


class TestTaskIdUsageScenarios:

    """Test TaskId in typical usage scenarios."""
    
    def test_subtask_id_in_collections(self):
        """Test using TaskId in various collections."""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        id2 = TaskId("550e8400e29b41d4a716446655440002")
        id3 = TaskId("550e8400-e29b-41d4-a716-446655440001")  # Duplicate of id1
        
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
        """Test that TaskIds can be sorted."""
        ids = [
            TaskId("550e8400e29b41d4a716446655440003"),
            TaskId("550e8400-e29b-41d4-a716-446655440001"),
            TaskId("550e8400e29b41d4a716446655440002"),
        ]
        
        sorted_ids = sorted(ids, key=lambda x: x.value)
        
        assert sorted_ids[0].value == "550e8400-e29b-41d4-a716-446655440001"
        assert sorted_ids[1].value == "550e8400-e29b-41d4-a716-446655440002"
        assert sorted_ids[2].value == "550e8400-e29b-41d4-a716-446655440003"
    
    def test_subtask_id_as_function_parameter(self):
        """Test passing TaskId as function parameter."""
        def process_subtask(subtask_id: TaskId) -> str:
            return f"Processing subtask: {subtask_id}"
        
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        result = process_subtask(id1)
        
        assert result == "Processing subtask: 550e8400-e29b-41d4-a716-446655440001"