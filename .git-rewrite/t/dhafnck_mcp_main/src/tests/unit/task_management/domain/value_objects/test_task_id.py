"""Unit tests for TaskId value object."""

import pytest
import uuid
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestTaskIdCreation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId creation with valid and invalid inputs."""
    
    def test_create_taskid_with_valid_uuid_hex(self):
        """Test creating TaskId with valid 32-char hex UUID."""
        # Using a valid UUID v4 in hex format
        valid_hex = "550e8400e29b41d4a716446655440000"
        task_id = TaskId(valid_hex)
        # Should be stored in canonical format
        expected_canonical = "550e8400-e29b-41d4-a716-446655440000"
        assert task_id.value == expected_canonical
        assert str(task_id) == expected_canonical
        # But we can get the hex format if needed
        assert task_id.to_hex_format() == valid_hex
    
    def test_create_taskid_with_canonical_uuid(self):
        """Test creating TaskId with canonical UUID format (with dashes)."""
        # Using a valid UUID v4 in canonical format
        canonical_uuid = "550e8400-e29b-41d4-a716-446655440000"
        task_id = TaskId(canonical_uuid)
        # Should store in canonical format, lowercase
        expected = "550e8400-e29b-41d4-a716-446655440000"
        assert task_id.value == expected
    
    def test_create_taskid_with_uppercase_uuid(self):
        """Test that uppercase UUIDs are converted to lowercase."""
        uppercase_uuid = "550E8400E29B41D4A716446655440000"
        task_id = TaskId(uppercase_uuid)
        expected = "550e8400-e29b-41d4-a716-446655440000"
        assert task_id.value == expected
    
    def test_create_taskid_with_mixed_case_canonical(self):
        """Test mixed case canonical UUID is normalized."""
        mixed_case = "550E8400-e29b-41d4-A716-446655440000"
        task_id = TaskId(mixed_case)
        expected = "550e8400-e29b-41d4-a716-446655440000"
        assert task_id.value == expected
    
    def test_create_taskid_with_whitespace(self):
        """Test that whitespace is stripped from input."""
        uuid_with_space = "  550e8400-e29b-41d4-a716-446655440000  "
        task_id = TaskId(uuid_with_space)
        assert task_id.value == "550e8400-e29b-41d4-a716-446655440000"


class TestTaskIdValidation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId validation and error handling."""
    
    def test_taskid_with_none_raises_error(self):
        """Test that None value raises ValueError."""
        with pytest.raises(ValueError, match="Task ID cannot be None"):
            TaskId(None)
    
    def test_taskid_with_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Task ID cannot be empty or whitespace"):
            TaskId("")
    
    def test_taskid_with_only_whitespace_raises_error(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Task ID cannot be empty or whitespace"):
            TaskId("   ")
    
    def test_taskid_with_invalid_type_raises_error(self):
        """Test that non-string types raise TypeError."""
        with pytest.raises(TypeError, match="Task ID value must be a string"):
            TaskId(12345)
        
        with pytest.raises(TypeError, match="Task ID value must be a string"):
            TaskId(['a', 'b', 'c'])
    
    def test_taskid_with_invalid_format_raises_error(self):
        """Test that invalid UUID formats raise ValueError."""
        invalid_formats = [
            "not-a-uuid",
            # "12345",  # Now valid as integer ID
            "g50e8400e29b41d4a716446655440000",  # 'g' is not hex
            "550e8400e29b41d4a71644665544000",   # Too short (31 chars)
            "550e8400-e29b-41d4-a716-4466554400000",  # Too long (33 chars)
            "550e8400-e29b-41d4-a716-44665544000", # Wrong length with dashes
            "123.abc",  # Invalid hierarchical ID
        ]
        
        for invalid in invalid_formats:
            with pytest.raises(ValueError, match="Invalid Task ID format"):
                TaskId(invalid)


class TestTaskIdEquality:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId equality comparison."""
    
    def test_equal_taskids(self):
        """Test that TaskIds with same value are equal."""
        uuid_value = "550e8400-e29b-41d4-a716-446655440000"
        task_id1 = TaskId(uuid_value)
        task_id2 = TaskId(uuid_value)
        assert task_id1 == task_id2
    
    def test_equal_taskids_different_input_formats(self):
        """Test TaskIds are equal when created from different formats of same UUID."""
        hex_format = "550e8400e29b41d4a716446655440000"
        canonical_format = "550e8400-e29b-41d4-a716-446655440000"
        uppercase_format = "550E8400E29B41D4A716446655440000"
        
        task_id1 = TaskId(hex_format)
        task_id2 = TaskId(canonical_format)
        task_id3 = TaskId(uppercase_format)
        
        assert task_id1 == task_id2
        assert task_id2 == task_id3
        assert task_id1 == task_id3
    
    def test_not_equal_taskids(self):
        """Test that TaskIds with different values are not equal."""
        task_id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        task_id2 = TaskId("660e8400e29b41d4a716446655440000")
        assert task_id1 != task_id2
    
    def test_equality_with_non_taskid(self):
        """Test that TaskId returns NotImplemented when compared to non-TaskId."""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        assert task_id.__eq__("550e8400-e29b-41d4-a716-446655440000") == NotImplemented
        assert task_id.__eq__(123) == NotImplemented
        assert task_id.__eq__(None) == NotImplemented


class TestTaskIdImmutability:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId immutability."""
    
    def test_taskid_is_immutable(self):
        """Test that TaskId value cannot be changed after creation."""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        
        with pytest.raises(AttributeError):
            task_id.value = "660e8400e29b41d4a716446655440000"


class TestTaskIdHashing:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId hashing behavior."""
    
    def test_taskid_is_hashable(self):
        """Test that TaskId can be used as dict key or in sets."""
        task_id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        task_id2 = TaskId("660e8400e29b41d4a716446655440000")
        
        # Test as dict keys
        task_dict = {task_id1: "Task 1", task_id2: "Task 2"}
        assert task_dict[task_id1] == "Task 1"
        assert task_dict[task_id2] == "Task 2"
        
        # Test in sets
        task_set = {task_id1, task_id2, task_id1}  # Duplicate should be ignored
        assert len(task_set) == 2
        assert task_id1 in task_set
        assert task_id2 in task_set
    
    def test_equal_taskids_have_same_hash(self):
        """Test that equal TaskIds have the same hash."""
        hex_format = "550e8400e29b41d4a716446655440000"
        canonical_format = "550e8400-e29b-41d4-a716-446655440000"
        
        task_id1 = TaskId(hex_format)
        task_id2 = TaskId(canonical_format)
        
        assert hash(task_id1) == hash(task_id2)


class TestTaskIdFactoryMethods:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId factory methods."""
    
    def test_from_string(self):
        """Test creating TaskId from string using factory method."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        task_id = TaskId.from_string(uuid_str)
        assert task_id.value == uuid_str
    
    def test_from_int(self):
        """Test creating TaskId from integer."""
        # from_int now creates valid integer-based TaskIds for backward compatibility
        task_id = TaskId.from_int(12345)
        assert str(task_id) == "12345"
        assert isinstance(task_id, TaskId)
    
    def test_generate_new(self):
        """Test generating new TaskId."""
        task_id1 = TaskId.generate_new()
        task_id2 = TaskId.generate_new()
        
        # Should create valid TaskIds
        assert isinstance(task_id1, TaskId)
        assert isinstance(task_id2, TaskId)
        
        # Should be unique
        assert task_id1 != task_id2
        
        # Should be valid 36-char canonical UUID strings
        assert len(task_id1.value) == 36
        assert len(task_id2.value) == 36
        assert all(c in '0123456789abcdef-' for c in task_id1.value)
        assert all(c in '0123456789abcdef-' for c in task_id2.value)
    
    def test_generate_subtask(self):
        """Test generating hierarchical subtask IDs."""
        # Create parent task ID
        parent_id = TaskId.generate_new()
        
        # Generate first subtask
        existing_ids = []
        subtask1 = TaskId.generate_subtask(parent_id, existing_ids)
        assert str(subtask1) == f"{parent_id}.001"
        
        # Generate second subtask
        existing_ids.append(str(subtask1))
        subtask2 = TaskId.generate_subtask(parent_id, existing_ids)
        assert str(subtask2) == f"{parent_id}.002"
        
        # Generate third subtask with non-subtask ID in list
        existing_ids.append(str(subtask2))
        existing_ids.append("unrelated-id")  # Should be ignored
        subtask3 = TaskId.generate_subtask(parent_id, existing_ids)
        assert str(subtask3) == f"{parent_id}.003"
        
        # All subtasks should be unique
        assert subtask1 != subtask2
        assert subtask2 != subtask3
        assert subtask1 != subtask3


class TestTaskIdSerialization:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId serialization/deserialization."""
    
    def test_string_representation(self):
        """Test string representation of TaskId."""
        uuid_value = "550e8400-e29b-41d4-a716-446655440000"
        task_id = TaskId(uuid_value)
        assert str(task_id) == uuid_value
    
    def test_to_canonical_format(self):
        """Test converting TaskId to canonical UUID format."""
        hex_value = "550e8400e29b41d4a716446655440000"
        task_id = TaskId(hex_value)
        
        canonical = task_id.to_canonical_format()
        expected = "550e8400-e29b-41d4-a716-446655440000"
        assert canonical == expected
    
    def test_round_trip_conversion(self):
        """Test converting between hex and canonical formats."""
        original_hex = "550e8400e29b41d4a716446655440000"
        task_id1 = TaskId(original_hex)
        
        # Convert to canonical
        canonical = task_id1.to_canonical_format()
        
        # Create new TaskId from canonical
        task_id2 = TaskId(canonical)
        
        # Should be equal
        assert task_id1 == task_id2
        assert task_id1.value == task_id2.value


class TestTaskIdEdgeCases:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test edge cases and error handling."""
    
    def test_uuid_with_invalid_hex_chars(self):
        """Test that non-hex characters in UUID are rejected."""
        invalid_uuids = [
            "g50e8400e29b41d4a716446655440000",  # 'g' is not hex
            "z50e8400-e29b-41d4-a716-446655440000",  # 'z' is not hex
        ]
        
        for invalid in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid Task ID format"):
                TaskId(invalid)
    
    def test_real_uuid_compatibility(self):
        """Test compatibility with Python's uuid module."""
        # Generate a real UUID
        real_uuid = uuid.uuid4()
        
        # Create TaskId from hex
        task_id1 = TaskId(real_uuid.hex)
        assert task_id1.value == str(real_uuid)  # Should be canonical format
        
        # Create TaskId from string representation
        task_id2 = TaskId(str(real_uuid))
        assert task_id2.value == str(real_uuid)  # Should be canonical format
        
        # Both should be equal
        assert task_id1 == task_id2
    
    def test_zero_uuid(self):
        """Test handling of zero UUID (all zeros)."""
        zero_uuid = "00000000000000000000000000000000"
        task_id = TaskId(zero_uuid)
        assert task_id.value == "00000000-0000-0000-0000-000000000000"
    
    def test_max_uuid(self):
        """Test handling of max UUID (all f's)."""
        max_uuid = "ffffffffffffffffffffffffffffffff"
        task_id = TaskId(max_uuid)
        assert task_id.value == "ffffffff-ffff-ffff-ffff-ffffffffffff"


class TestTaskIdOrdering:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskId ordering and comparison (if applicable)."""
    
    def test_taskid_not_orderable(self):
        """Test that TaskIds don't support ordering operations."""
        task_id1 = TaskId("550e8400-e29b-41d4-a716-446655440000")
        task_id2 = TaskId("660e8400e29b41d4a716446655440000")
        
        # TaskIds should not be orderable
        with pytest.raises(TypeError):
            _ = task_id1 < task_id2
        
        with pytest.raises(TypeError):
            _ = task_id1 > task_id2
        
        with pytest.raises(TypeError):
            _ = task_id1 <= task_id2
        
        with pytest.raises(TypeError):
            _ = task_id1 >= task_id2


class TestTaskIdIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Integration tests with real use cases."""
    
    def test_taskid_in_collections(self):
        """Test TaskId behavior in various collections."""
        # Create some TaskIds
        ids = [TaskId.generate_new() for _ in range(5)]
        
        # Test in list
        task_list = list(ids)
        assert len(task_list) == 5
        assert all(isinstance(tid, TaskId) for tid in task_list)
        
        # Test in set (uniqueness)
        task_set = set(ids)
        assert len(task_set) == 5  # All should be unique
        
        # Test duplicate handling in set
        duplicate_set = set(ids + [ids[0], ids[1]])  # Add duplicates
        assert len(duplicate_set) == 5  # Duplicates should be ignored
        
        # Test in dict as keys
        task_dict = {tid: f"Task {i}" for i, tid in enumerate(ids)}
        assert len(task_dict) == 5
        assert all(task_dict[tid] == f"Task {i}" for i, tid in enumerate(ids))
    
    def test_taskid_json_serialization(self):
        """Test that TaskId can be serialized for JSON."""
        task_id = TaskId("550e8400-e29b-41d4-a716-446655440000")
        
        # Should be able to convert to string for JSON
        json_value = str(task_id)
        assert json_value == "550e8400-e29b-41d4-a716-446655440000"
        
        # Should be able to recreate from JSON value
        restored_id = TaskId(json_value)
        assert restored_id == task_id