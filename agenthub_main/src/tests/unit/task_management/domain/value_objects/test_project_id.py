"""Tests for ProjectId value object"""

import uuid

import pytest

from fastmcp.task_management.domain.value_objects.project_id import ProjectId


class TestProjectIdCreation:
    """Test ProjectId creation and validation"""

    def test_create_from_valid_uuid_string(self):
        """Should create ProjectId from valid UUID string"""
        valid_uuid = str(uuid.uuid4())
        project_id = ProjectId(valid_uuid)
        assert project_id.value == valid_uuid

    def test_create_from_uuid_with_uppercase(self):
        """Should normalize uppercase UUIDs to lowercase"""
        uuid_upper = str(uuid.uuid4()).upper()
        project_id = ProjectId(uuid_upper)
        assert project_id.value == uuid_upper.lower()

    def test_create_from_uuid_without_hyphens(self):
        """Should accept UUID without hyphens and add them"""
        uuid_obj = uuid.uuid4()
        uuid_no_hyphens = str(uuid_obj).replace('-', '')
        project_id = ProjectId(uuid_no_hyphens)
        assert project_id.value == str(uuid_obj)
        assert '-' in project_id.value

    def test_reject_none_value(self):
        """Should raise ValueError when value is None"""
        with pytest.raises(ValueError, match="ProjectId cannot be None"):
            ProjectId(None)

    def test_reject_empty_string(self):
        """Should raise ValueError when value is empty string"""
        with pytest.raises(ValueError, match="ProjectId cannot be empty or whitespace"):
            ProjectId("")

    def test_reject_whitespace_only(self):
        """Should raise ValueError when value is whitespace only"""
        with pytest.raises(ValueError, match="ProjectId cannot be empty or whitespace"):
            ProjectId("   ")

    def test_reject_non_string_value(self):
        """Should raise TypeError when value is not a string"""
        with pytest.raises(TypeError, match="ProjectId value must be a string"):
            ProjectId(12345)

    def test_reject_invalid_uuid_format(self):
        """Should raise ValueError for invalid UUID format"""
        with pytest.raises(ValueError, match="Invalid ProjectId format"):
            ProjectId("not-a-valid-uuid")

    def test_reject_malformed_uuid(self):
        """Should raise ValueError for malformed UUID"""
        with pytest.raises(ValueError, match="Invalid ProjectId format"):
            ProjectId("123e4567-e89b-12d3-a456-42661417400")  # Missing last digit


class TestProjectIdFactoryMethods:
    """Test ProjectId factory methods"""

    def test_from_string_creates_valid_project_id(self):
        """Should create ProjectId using from_string factory method"""
        valid_uuid = str(uuid.uuid4())
        project_id = ProjectId.from_string(valid_uuid)
        assert isinstance(project_id, ProjectId)
        assert project_id.value == valid_uuid

    def test_generate_new_creates_unique_ids(self):
        """Should generate unique ProjectIds"""
        id1 = ProjectId.generate_new()
        id2 = ProjectId.generate_new()
        assert isinstance(id1, ProjectId)
        assert isinstance(id2, ProjectId)
        assert id1 != id2
        assert id1.value != id2.value

    def test_generate_new_creates_valid_uuid(self):
        """Should generate valid UUID format"""
        project_id = ProjectId.generate_new()
        # Verify it can be parsed as UUID
        uuid_obj = uuid.UUID(project_id.value)
        assert str(uuid_obj) == project_id.value


class TestProjectIdEquality:
    """Test ProjectId equality and hashing"""

    def test_equal_project_ids_are_equal(self):
        """Should be equal when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = ProjectId(uuid_str)
        id2 = ProjectId(uuid_str)
        assert id1 == id2

    def test_different_project_ids_are_not_equal(self):
        """Should not be equal when values differ"""
        id1 = ProjectId.generate_new()
        id2 = ProjectId.generate_new()
        assert id1 != id2

    def test_project_id_not_equal_to_other_types(self):
        """Should not be equal to other types"""
        project_id = ProjectId.generate_new()
        assert project_id != project_id.value
        assert project_id != 12345
        assert project_id is not None

    def test_equal_project_ids_have_same_hash(self):
        """Should have same hash when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = ProjectId(uuid_str)
        id2 = ProjectId(uuid_str)
        assert hash(id1) == hash(id2)

    def test_can_be_used_in_sets(self):
        """Should work correctly in sets"""
        id1 = ProjectId.generate_new()
        id2 = ProjectId.generate_new()
        id3 = ProjectId(id1.value)  # Same as id1

        project_set = {id1, id2, id3}
        assert len(project_set) == 2  # id1 and id3 are same
        assert id1 in project_set
        assert id2 in project_set

    def test_can_be_used_as_dict_keys(self):
        """Should work correctly as dictionary keys"""
        id1 = ProjectId.generate_new()
        id2 = ProjectId.generate_new()

        project_dict = {id1: "value1", id2: "value2"}
        assert project_dict[id1] == "value1"
        assert project_dict[id2] == "value2"


class TestProjectIdStringRepresentation:
    """Test ProjectId string representations"""

    def test_str_returns_value(self):
        """Should return value when converted to string"""
        uuid_str = str(uuid.uuid4())
        project_id = ProjectId(uuid_str)
        assert str(project_id) == uuid_str

    def test_to_canonical_format(self):
        """Should return canonical format with hyphens"""
        project_id = ProjectId.generate_new()
        canonical = project_id.to_canonical_format()
        assert canonical == project_id.value
        assert '-' in canonical
        assert len(canonical) == 36

    def test_to_hex_format(self):
        """Should return hex format without hyphens"""
        project_id = ProjectId.generate_new()
        hex_format = project_id.to_hex_format()
        assert '-' not in hex_format
        assert len(hex_format) == 32
        # Verify it's the same UUID
        assert hex_format == project_id.value.replace('-', '')


class TestProjectIdImmutability:
    """Test ProjectId immutability"""

    def test_cannot_modify_value_after_creation(self):
        """Should not allow modification of value after creation"""
        project_id = ProjectId.generate_new()
        with pytest.raises(AttributeError):
            project_id.value = "new-value"

    def test_frozen_dataclass(self):
        """Should be a frozen dataclass"""
        project_id = ProjectId.generate_new()
        assert project_id.__dataclass_fields__['value'].metadata.get('frozen', False) or \
               getattr(project_id.__class__, '__dataclass_params__').frozen
