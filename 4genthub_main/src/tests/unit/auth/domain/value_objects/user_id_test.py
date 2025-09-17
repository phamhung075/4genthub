"""Unit tests for UserId value object"""

import pytest
import uuid
from fastmcp.auth.domain.value_objects.user_id import UserId


class TestUserId:
    """Tests for UserId value object"""
    
    def test_create_valid_user_id(self):
        """Test creating a UserId with a valid UUID"""
        valid_uuid = str(uuid.uuid4())
        user_id = UserId(valid_uuid)
        assert user_id.value == valid_uuid
    
    def test_from_string_factory(self):
        """Test creating UserId using from_string factory method"""
        valid_uuid = str(uuid.uuid4())
        user_id = UserId.from_string(valid_uuid)
        assert user_id.value == valid_uuid
    
    def test_generate_new_user_id(self):
        """Test generating a new UserId"""
        user_id1 = UserId.generate()
        user_id2 = UserId.generate()
        
        # Should generate valid UUIDs
        assert uuid.UUID(user_id1.value)
        assert uuid.UUID(user_id2.value)
        
        # Should generate unique IDs
        assert user_id1 != user_id2
    
    def test_string_representation(self):
        """Test string representation of UserId"""
        valid_uuid = str(uuid.uuid4())
        user_id = UserId(valid_uuid)
        assert str(user_id) == valid_uuid
    
    def test_equality(self):
        """Test UserId equality comparison"""
        uuid_str = str(uuid.uuid4())
        user_id1 = UserId(uuid_str)
        user_id2 = UserId(uuid_str)
        user_id3 = UserId(str(uuid.uuid4()))
        
        assert user_id1 == user_id2
        assert user_id1 != user_id3
        assert user_id1 != uuid_str  # Not equal to string
    
    def test_hashable(self):
        """Test that UserId can be used in sets and as dict keys"""
        uuid_str1 = str(uuid.uuid4())
        uuid_str2 = str(uuid.uuid4())
        
        user_id1 = UserId(uuid_str1)
        user_id2 = UserId(uuid_str1)  # Same UUID
        user_id3 = UserId(uuid_str2)  # Different UUID
        
        # Test in set
        user_id_set = {user_id1, user_id2, user_id3}
        assert len(user_id_set) == 2  # user_id1 and user_id2 are the same
        
        # Test as dict key
        user_id_dict = {user_id1: "value1", user_id3: "value2"}
        assert user_id_dict[user_id2] == "value1"  # user_id2 should map to same as user_id1
    
    def test_invalid_user_id_empty(self):
        """Test that empty user ID raises ValueError"""
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            UserId("")
        
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            UserId(None)
    
    def test_invalid_user_id_format(self):
        """Test that invalid UUID formats raise ValueError"""
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "12345678-1234-1234-1234-12345678901g",  # Invalid character
            "12345678-1234-1234-1234-1234567890",     # Too short
            "12345678-1234-1234-1234-1234567890123",   # Too long
        ]
        
        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid user ID format"):
                UserId(invalid_uuid)
    
    def test_different_uuid_versions(self):
        """Test that different UUID versions are accepted"""
        # Test UUID v1
        uuid1 = str(uuid.uuid1())
        user_id1 = UserId(uuid1)
        assert user_id1.value == uuid1
        
        # Test UUID v4
        uuid4 = str(uuid.uuid4())
        user_id4 = UserId(uuid4)
        assert user_id4.value == uuid4
        
        # Test UUID v5
        uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "example.com"))
        user_id5 = UserId(uuid5)
        assert user_id5.value == uuid5
    
    def test_case_sensitivity(self):
        """Test that UUIDs with different cases are handled correctly"""
        uuid_lower = str(uuid.uuid4()).lower()
        uuid_upper = uuid_lower.upper()
        
        user_id_lower = UserId(uuid_lower)
        user_id_upper = UserId(uuid_upper)
        
        # Both should be valid
        assert user_id_lower.value == uuid_lower
        assert user_id_upper.value == uuid_upper
    
    def test_immutability(self):
        """Test that UserId value object is immutable"""
        user_id = UserId.generate()
        
        # Should not be able to modify the value
        with pytest.raises(AttributeError):
            user_id.value = str(uuid.uuid4())