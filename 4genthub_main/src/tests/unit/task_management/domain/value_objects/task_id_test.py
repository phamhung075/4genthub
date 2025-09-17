"""Unit tests for TaskId value object."""
import pytest
import uuid
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestTaskId:
    """Test cases for TaskId value object"""
    
    def test_create_task_id_with_valid_uuid(self):
        """Test creating TaskId with valid UUID string"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        task_id = TaskId(uuid_str)
        
        assert task_id.value == uuid_str
        assert str(task_id) == uuid_str
    
    def test_create_task_id_with_hex_format(self):
        """Test creating TaskId with hex format UUID (no dashes)"""
        hex_uuid = "550e8400e29b41d4a716446655440000"
        task_id = TaskId(hex_uuid)
        
        # Should be converted to canonical format
        assert task_id.value == "550e8400-e29b-41d4-a716-446655440000"
    
    def test_create_task_id_with_uppercase_uuid(self):
        """Test that UUIDs are normalized to lowercase"""
        uppercase_uuid = "550E8400-E29B-41D4-A716-446655440000"
        task_id = TaskId(uppercase_uuid)
        
        assert task_id.value == "550e8400-e29b-41d4-a716-446655440000"
    
    def test_create_task_id_with_integer_string(self):
        """Test creating TaskId with integer string (legacy support)"""
        task_id = TaskId("123")
        assert task_id.value == "123"
    
    def test_create_task_id_with_test_pattern(self):
        """Test creating TaskId with test pattern (e.g., task-123)"""
        task_id = TaskId("task-123")
        assert task_id.value == "task-123"
    
    def test_create_task_id_with_hierarchical_format(self):
        """Test creating TaskId with hierarchical format (parent.001)"""
        hierarchical_id = "550e8400-e29b-41d4-a716-446655440000.001"
        task_id = TaskId(hierarchical_id)
        
        assert task_id.value == hierarchical_id
    
    def test_task_id_is_immutable(self):
        """Test that TaskId is immutable (frozen dataclass)"""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(AttributeError):
            task_id.value = "new-value"
    
    def test_task_id_with_none_value(self):
        """Test that None value raises ValueError"""
        with pytest.raises(ValueError, match="Task ID cannot be None"):
            TaskId(None)
    
    def test_task_id_with_empty_string(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="Task ID cannot be empty or whitespace"):
            TaskId("")
        
        with pytest.raises(ValueError, match="Task ID cannot be empty or whitespace"):
            TaskId("   ")
    
    def test_task_id_with_non_string_value(self):
        """Test that non-string value raises TypeError"""
        with pytest.raises(TypeError, match="Task ID value must be a string"):
            TaskId(123)
        
        with pytest.raises(TypeError, match="Task ID value must be a string"):
            TaskId(['not', 'a', 'string'])
    
    def test_task_id_with_invalid_format(self):
        """Test that invalid format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid Task ID format"):
            TaskId("not-a-valid-uuid")
        
        with pytest.raises(ValueError, match="Invalid Task ID format"):
            TaskId("12345-678")
    
    def test_task_id_equality(self):
        """Test TaskId equality comparison"""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        id2 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        id3 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        
        assert id1 == id2
        assert id1 != id3
        assert id1 != "550e8400-e29b-41d4-a716-446655440000"  # Not equal to string
    
    def test_task_id_hash(self):
        """Test TaskId hashing for use in sets/dicts"""
        id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        id2 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        id3 = TaskId("550e8400-e29b-41d4-a716-446655440001")
        
        assert hash(id1) == hash(id2)
        assert hash(id1) != hash(id3)
        
        # Can be used in sets
        task_ids = {id1, id2, id3}
        assert len(task_ids) == 2  # id1 and id2 are equal
    
    def test_from_string_class_method(self):
        """Test creating TaskId using from_string class method"""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440000")
        assert task_id.value == "550e8400-e29b-41d4-a716-446655440000"
    
    def test_from_int_class_method(self):
        """Test creating TaskId using from_int class method"""
        task_id = TaskId.from_int(123)
        assert task_id.value == "123"
    
    def test_generate_new_class_method(self):
        """Test generating new TaskId using generate_new"""
        task_id1 = TaskId.generate_new()
        task_id2 = TaskId.generate_new()
        
        # Should be valid UUIDs
        assert len(task_id1.value) == 36
        assert task_id1 != task_id2
        
        # Should be valid UUID format
        uuid.UUID(task_id1.value)  # This will raise if invalid
        uuid.UUID(task_id2.value)
    
    def test_generate_subtask_method(self):
        """Test generating hierarchical subtask IDs"""
        parent_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        
        # No existing subtasks
        subtask1 = TaskId.generate_subtask(parent_id, [])
        assert subtask1.value == "550e8400-e29b-41d4-a716-446655440000.001"
        
        # With existing subtasks
        existing_ids = [
            TaskId("550e8400-e29b-41d4-a716-446655440000.001"),
            TaskId("550e8400-e29b-41d4-a716-446655440000.002"),
            TaskId("550e8400-e29b-41d4-a716-446655440000.005"),
        ]
        subtask2 = TaskId.generate_subtask(parent_id, existing_ids)
        assert subtask2.value == "550e8400-e29b-41d4-a716-446655440000.006"
    
    def test_to_canonical_format(self):
        """Test converting to canonical UUID format"""
        # Already canonical
        task_id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        assert task_id1.to_canonical_format() == "550e8400-e29b-41d4-a716-446655440000"
        
        # From hex format
        task_id2 = TaskId("550e8400e29b41d4a716446655440000")
        assert task_id2.to_canonical_format() == "550e8400-e29b-41d4-a716-446655440000"
    
    def test_to_hex_format(self):
        """Test converting to hex UUID format"""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        assert task_id.to_hex_format() == "550e8400e29b41d4a716446655440000"
    
    def test_str_representation(self):
        """Test string representation of TaskId"""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        assert str(task_id) == "550e8400-e29b-41d4-a716-446655440000"
    
    def test_edge_cases_for_generate_subtask(self):
        """Test edge cases for generate_subtask method"""
        parent_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        
        # Mixed existing IDs (some not related to parent)
        existing_ids = [
            TaskId("550e8400-e29b-41d4-a716-446655440000.001"),
            TaskId("999e8400-e29b-41d4-a716-446655440000.001"),  # Different parent
            TaskId("task-123"),  # Legacy format
        ]
        subtask = TaskId.generate_subtask(parent_id, existing_ids)
        assert subtask.value == "550e8400-e29b-41d4-a716-446655440000.002"
        
        # Test with non-sequential subtask numbers
        existing_ids_non_sequential = [
            TaskId("550e8400-e29b-41d4-a716-446655440000.001"),
            TaskId("550e8400-e29b-41d4-a716-446655440000.005"),  # Gap in sequence
            TaskId("550e8400-e29b-41d4-a716-446655440000.003"),
        ]
        subtask = TaskId.generate_subtask(parent_id, existing_ids_non_sequential)
        assert subtask.value == "550e8400-e29b-41d4-a716-446655440000.006"  # Should use max + 1