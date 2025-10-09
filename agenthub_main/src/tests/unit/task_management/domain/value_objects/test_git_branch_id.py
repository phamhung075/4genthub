"""Tests for GitBranchId value object"""

import pytest
import uuid
from fastmcp.task_management.domain.value_objects.git_branch_id import GitBranchId


class TestGitBranchIdCreation:
    """Test GitBranchId creation and validation"""

    def test_create_from_valid_uuid_string(self):
        """Should create GitBranchId from valid UUID string"""
        valid_uuid = str(uuid.uuid4())
        git_branch_id = GitBranchId(valid_uuid)
        assert git_branch_id.value == valid_uuid

    def test_create_from_uuid_with_uppercase(self):
        """Should normalize uppercase UUIDs to lowercase"""
        uuid_upper = str(uuid.uuid4()).upper()
        git_branch_id = GitBranchId(uuid_upper)
        assert git_branch_id.value == uuid_upper.lower()

    def test_create_from_uuid_without_hyphens(self):
        """Should accept UUID without hyphens and add them"""
        uuid_obj = uuid.uuid4()
        uuid_no_hyphens = str(uuid_obj).replace('-', '')
        git_branch_id = GitBranchId(uuid_no_hyphens)
        assert git_branch_id.value == str(uuid_obj)
        assert '-' in git_branch_id.value

    def test_reject_none_value(self):
        """Should raise ValueError when value is None"""
        with pytest.raises(ValueError, match="GitBranchId cannot be None"):
            GitBranchId(None)

    def test_reject_empty_string(self):
        """Should raise ValueError when value is empty string"""
        with pytest.raises(ValueError, match="GitBranchId cannot be empty or whitespace"):
            GitBranchId("")

    def test_reject_whitespace_only(self):
        """Should raise ValueError when value is whitespace only"""
        with pytest.raises(ValueError, match="GitBranchId cannot be empty or whitespace"):
            GitBranchId("   ")

    def test_reject_non_string_value(self):
        """Should raise TypeError when value is not a string"""
        with pytest.raises(TypeError, match="GitBranchId value must be a string"):
            GitBranchId(12345)

    def test_reject_invalid_uuid_format(self):
        """Should raise ValueError for invalid UUID format"""
        with pytest.raises(ValueError, match="Invalid GitBranchId format"):
            GitBranchId("not-a-valid-uuid")

    def test_reject_malformed_uuid(self):
        """Should raise ValueError for malformed UUID"""
        with pytest.raises(ValueError, match="Invalid GitBranchId format"):
            GitBranchId("123e4567-e89b-12d3-a456-42661417400")  # Missing last digit


class TestGitBranchIdFactoryMethods:
    """Test GitBranchId factory methods"""

    def test_from_string_creates_valid_git_branch_id(self):
        """Should create GitBranchId using from_string factory method"""
        valid_uuid = str(uuid.uuid4())
        git_branch_id = GitBranchId.from_string(valid_uuid)
        assert isinstance(git_branch_id, GitBranchId)
        assert git_branch_id.value == valid_uuid

    def test_generate_new_creates_unique_ids(self):
        """Should generate unique GitBranchIds"""
        id1 = GitBranchId.generate_new()
        id2 = GitBranchId.generate_new()
        assert isinstance(id1, GitBranchId)
        assert isinstance(id2, GitBranchId)
        assert id1 != id2
        assert id1.value != id2.value

    def test_generate_new_creates_valid_uuid(self):
        """Should generate valid UUID format"""
        git_branch_id = GitBranchId.generate_new()
        # Verify it can be parsed as UUID
        uuid_obj = uuid.UUID(git_branch_id.value)
        assert str(uuid_obj) == git_branch_id.value


class TestGitBranchIdEquality:
    """Test GitBranchId equality and hashing"""

    def test_equal_git_branch_ids_are_equal(self):
        """Should be equal when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = GitBranchId(uuid_str)
        id2 = GitBranchId(uuid_str)
        assert id1 == id2

    def test_different_git_branch_ids_are_not_equal(self):
        """Should not be equal when values differ"""
        id1 = GitBranchId.generate_new()
        id2 = GitBranchId.generate_new()
        assert id1 != id2

    def test_git_branch_id_not_equal_to_other_types(self):
        """Should not be equal to other types"""
        git_branch_id = GitBranchId.generate_new()
        assert git_branch_id != git_branch_id.value
        assert git_branch_id != 12345
        assert git_branch_id != None

    def test_equal_git_branch_ids_have_same_hash(self):
        """Should have same hash when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = GitBranchId(uuid_str)
        id2 = GitBranchId(uuid_str)
        assert hash(id1) == hash(id2)

    def test_can_be_used_in_sets(self):
        """Should work correctly in sets"""
        id1 = GitBranchId.generate_new()
        id2 = GitBranchId.generate_new()
        id3 = GitBranchId(id1.value)  # Same as id1

        git_branch_set = {id1, id2, id3}
        assert len(git_branch_set) == 2  # id1 and id3 are same
        assert id1 in git_branch_set
        assert id2 in git_branch_set

    def test_can_be_used_as_dict_keys(self):
        """Should work correctly as dictionary keys"""
        id1 = GitBranchId.generate_new()
        id2 = GitBranchId.generate_new()

        git_branch_dict = {id1: "value1", id2: "value2"}
        assert git_branch_dict[id1] == "value1"
        assert git_branch_dict[id2] == "value2"


class TestGitBranchIdStringRepresentation:
    """Test GitBranchId string representations"""

    def test_str_returns_value(self):
        """Should return value when converted to string"""
        uuid_str = str(uuid.uuid4())
        git_branch_id = GitBranchId(uuid_str)
        assert str(git_branch_id) == uuid_str

    def test_to_canonical_format(self):
        """Should return canonical format with hyphens"""
        git_branch_id = GitBranchId.generate_new()
        canonical = git_branch_id.to_canonical_format()
        assert canonical == git_branch_id.value
        assert '-' in canonical
        assert len(canonical) == 36

    def test_to_hex_format(self):
        """Should return hex format without hyphens"""
        git_branch_id = GitBranchId.generate_new()
        hex_format = git_branch_id.to_hex_format()
        assert '-' not in hex_format
        assert len(hex_format) == 32
        # Verify it's the same UUID
        assert hex_format == git_branch_id.value.replace('-', '')


class TestGitBranchIdImmutability:
    """Test GitBranchId immutability"""

    def test_cannot_modify_value_after_creation(self):
        """Should not allow modification of value after creation"""
        git_branch_id = GitBranchId.generate_new()
        with pytest.raises(AttributeError):
            git_branch_id.value = "new-value"

    def test_frozen_dataclass(self):
        """Should be a frozen dataclass"""
        git_branch_id = GitBranchId.generate_new()
        assert git_branch_id.__dataclass_fields__['value'].metadata.get('frozen', False) or \
               getattr(git_branch_id.__class__, '__dataclass_params__').frozen
