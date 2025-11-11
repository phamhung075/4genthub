"""Tests for TemplateId value object"""

import uuid

import pytest

from fastmcp.task_management.domain.value_objects.template_id import TemplateId


class TestTemplateIdCreation:
    """Test TemplateId creation and validation"""

    def test_create_from_valid_uuid_string(self):
        """Should create TemplateId from valid UUID string"""
        valid_uuid = str(uuid.uuid4())
        template_id = TemplateId(valid_uuid)
        assert template_id.value == valid_uuid

    def test_create_from_uuid_with_uppercase(self):
        """Should normalize uppercase UUIDs to lowercase"""
        uuid_upper = str(uuid.uuid4()).upper()
        template_id = TemplateId(uuid_upper)
        assert template_id.value == uuid_upper.lower()

    def test_create_from_uuid_without_hyphens(self):
        """Should accept UUID without hyphens and add them"""
        uuid_obj = uuid.uuid4()
        uuid_no_hyphens = str(uuid_obj).replace("-", "")
        template_id = TemplateId(uuid_no_hyphens)
        assert template_id.value == str(uuid_obj)
        assert "-" in template_id.value

    def test_reject_none_value(self):
        """Should raise ValueError when value is None"""
        with pytest.raises(ValueError, match="TemplateId cannot be None"):
            TemplateId(None)

    def test_reject_empty_string(self):
        """Should raise ValueError when value is empty string"""
        with pytest.raises(
            ValueError, match="TemplateId cannot be empty or whitespace"
        ):
            TemplateId("")

    def test_reject_whitespace_only(self):
        """Should raise ValueError when value is whitespace only"""
        with pytest.raises(
            ValueError, match="TemplateId cannot be empty or whitespace"
        ):
            TemplateId("   ")

    def test_reject_non_string_value(self):
        """Should raise TypeError when value is not a string"""
        with pytest.raises(TypeError, match="TemplateId value must be a string"):
            TemplateId(12345)

    def test_reject_invalid_uuid_format(self):
        """Should raise ValueError for invalid UUID format"""
        with pytest.raises(ValueError, match="Invalid TemplateId format"):
            TemplateId("not-a-valid-uuid")

    def test_reject_malformed_uuid(self):
        """Should raise ValueError for malformed UUID"""
        with pytest.raises(ValueError, match="Invalid TemplateId format"):
            TemplateId("123e4567-e89b-12d3-a456-42661417400")  # Missing last digit


class TestTemplateIdFactoryMethods:
    """Test TemplateId factory methods"""

    def test_from_string_creates_valid_template_id(self):
        """Should create TemplateId using from_string factory method"""
        valid_uuid = str(uuid.uuid4())
        template_id = TemplateId.from_string(valid_uuid)
        assert isinstance(template_id, TemplateId)
        assert template_id.value == valid_uuid

    def test_generate_new_creates_unique_ids(self):
        """Should generate unique TemplateIds"""
        id1 = TemplateId.generate_new()
        id2 = TemplateId.generate_new()
        assert isinstance(id1, TemplateId)
        assert isinstance(id2, TemplateId)
        assert id1 != id2
        assert id1.value != id2.value

    def test_generate_new_creates_valid_uuid(self):
        """Should generate valid UUID format"""
        template_id = TemplateId.generate_new()
        # Verify it can be parsed as UUID
        uuid_obj = uuid.UUID(template_id.value)
        assert str(uuid_obj) == template_id.value


class TestTemplateIdEquality:
    """Test TemplateId equality and hashing"""

    def test_equal_template_ids_are_equal(self):
        """Should be equal when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = TemplateId(uuid_str)
        id2 = TemplateId(uuid_str)
        assert id1 == id2

    def test_different_template_ids_are_not_equal(self):
        """Should not be equal when values differ"""
        id1 = TemplateId.generate_new()
        id2 = TemplateId.generate_new()
        assert id1 != id2

    def test_template_id_not_equal_to_other_types(self):
        """Should not be equal to other types"""
        template_id = TemplateId.generate_new()
        assert template_id != template_id.value
        assert template_id != 12345
        assert template_id is not None

    def test_equal_template_ids_have_same_hash(self):
        """Should have same hash when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = TemplateId(uuid_str)
        id2 = TemplateId(uuid_str)
        assert hash(id1) == hash(id2)

    def test_can_be_used_in_sets(self):
        """Should work correctly in sets"""
        id1 = TemplateId.generate_new()
        id2 = TemplateId.generate_new()
        id3 = TemplateId(id1.value)  # Same as id1

        template_set = {id1, id2, id3}
        assert len(template_set) == 2  # id1 and id3 are same
        assert id1 in template_set
        assert id2 in template_set

    def test_can_be_used_as_dict_keys(self):
        """Should work correctly as dictionary keys"""
        id1 = TemplateId.generate_new()
        id2 = TemplateId.generate_new()

        template_dict = {id1: "value1", id2: "value2"}
        assert template_dict[id1] == "value1"
        assert template_dict[id2] == "value2"


class TestTemplateIdStringRepresentation:
    """Test TemplateId string representations"""

    def test_str_returns_value(self):
        """Should return value when converted to string"""
        uuid_str = str(uuid.uuid4())
        template_id = TemplateId(uuid_str)
        assert str(template_id) == uuid_str

    def test_to_canonical_format(self):
        """Should return canonical format with hyphens"""
        template_id = TemplateId.generate_new()
        canonical = template_id.to_canonical_format()
        assert canonical == template_id.value
        assert "-" in canonical
        assert len(canonical) == 36

    def test_to_hex_format(self):
        """Should return hex format without hyphens"""
        template_id = TemplateId.generate_new()
        hex_format = template_id.to_hex_format()
        assert "-" not in hex_format
        assert len(hex_format) == 32
        # Verify it's the same UUID
        assert hex_format == template_id.value.replace("-", "")


class TestTemplateIdImmutability:
    """Test TemplateId immutability"""

    def test_cannot_modify_value_after_creation(self):
        """Should not allow modification of value after creation"""
        template_id = TemplateId.generate_new()
        with pytest.raises(AttributeError):
            template_id.value = "new-value"

    def test_frozen_dataclass(self):
        """Should be a frozen dataclass"""
        template_id = TemplateId.generate_new()
        assert (
            template_id.__dataclass_fields__["value"].metadata.get("frozen", False)
            or getattr(template_id.__class__, "__dataclass_params__").frozen
        )
