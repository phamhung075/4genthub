"""Tests for AgentId value object"""

import pytest
import uuid
from fastmcp.task_management.domain.value_objects.agent_id import AgentId


class TestAgentIdCreation:
    """Test AgentId creation and validation"""

    def test_create_from_valid_uuid_string(self):
        """Should create AgentId from valid UUID string"""
        valid_uuid = str(uuid.uuid4())
        agent_id = AgentId(valid_uuid)
        assert agent_id.value == valid_uuid

    def test_create_from_uuid_with_uppercase(self):
        """Should normalize uppercase UUIDs to lowercase"""
        uuid_upper = str(uuid.uuid4()).upper()
        agent_id = AgentId(uuid_upper)
        assert agent_id.value == uuid_upper.lower()

    def test_create_from_uuid_without_hyphens(self):
        """Should accept UUID without hyphens and add them"""
        uuid_obj = uuid.uuid4()
        uuid_no_hyphens = str(uuid_obj).replace('-', '')
        agent_id = AgentId(uuid_no_hyphens)
        assert agent_id.value == str(uuid_obj)
        assert '-' in agent_id.value

    def test_reject_none_value(self):
        """Should raise ValueError when value is None"""
        with pytest.raises(ValueError, match="AgentId cannot be None"):
            AgentId(None)

    def test_reject_empty_string(self):
        """Should raise ValueError when value is empty string"""
        with pytest.raises(ValueError, match="AgentId cannot be empty or whitespace"):
            AgentId("")

    def test_reject_whitespace_only(self):
        """Should raise ValueError when value is whitespace only"""
        with pytest.raises(ValueError, match="AgentId cannot be empty or whitespace"):
            AgentId("   ")

    def test_reject_non_string_value(self):
        """Should raise TypeError when value is not a string"""
        with pytest.raises(TypeError, match="AgentId value must be a string"):
            AgentId(12345)

    def test_reject_invalid_uuid_format(self):
        """Should raise ValueError for invalid UUID format"""
        with pytest.raises(ValueError, match="Invalid AgentId format"):
            AgentId("not-a-valid-uuid")

    def test_reject_malformed_uuid(self):
        """Should raise ValueError for malformed UUID"""
        with pytest.raises(ValueError, match="Invalid AgentId format"):
            AgentId("123e4567-e89b-12d3-a456-42661417400")  # Missing last digit


class TestAgentIdFactoryMethods:
    """Test AgentId factory methods"""

    def test_from_string_creates_valid_agent_id(self):
        """Should create AgentId using from_string factory method"""
        valid_uuid = str(uuid.uuid4())
        agent_id = AgentId.from_string(valid_uuid)
        assert isinstance(agent_id, AgentId)
        assert agent_id.value == valid_uuid

    def test_generate_new_creates_unique_ids(self):
        """Should generate unique AgentIds"""
        id1 = AgentId.generate_new()
        id2 = AgentId.generate_new()
        assert isinstance(id1, AgentId)
        assert isinstance(id2, AgentId)
        assert id1 != id2
        assert id1.value != id2.value

    def test_generate_new_creates_valid_uuid(self):
        """Should generate valid UUID format"""
        agent_id = AgentId.generate_new()
        # Verify it can be parsed as UUID
        uuid_obj = uuid.UUID(agent_id.value)
        assert str(uuid_obj) == agent_id.value


class TestAgentIdEquality:
    """Test AgentId equality and hashing"""

    def test_equal_agent_ids_are_equal(self):
        """Should be equal when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = AgentId(uuid_str)
        id2 = AgentId(uuid_str)
        assert id1 == id2

    def test_different_agent_ids_are_not_equal(self):
        """Should not be equal when values differ"""
        id1 = AgentId.generate_new()
        id2 = AgentId.generate_new()
        assert id1 != id2

    def test_agent_id_not_equal_to_other_types(self):
        """Should not be equal to other types"""
        agent_id = AgentId.generate_new()
        assert agent_id != agent_id.value
        assert agent_id != 12345
        assert agent_id != None

    def test_equal_agent_ids_have_same_hash(self):
        """Should have same hash when values are equal"""
        uuid_str = str(uuid.uuid4())
        id1 = AgentId(uuid_str)
        id2 = AgentId(uuid_str)
        assert hash(id1) == hash(id2)

    def test_can_be_used_in_sets(self):
        """Should work correctly in sets"""
        id1 = AgentId.generate_new()
        id2 = AgentId.generate_new()
        id3 = AgentId(id1.value)  # Same as id1

        agent_set = {id1, id2, id3}
        assert len(agent_set) == 2  # id1 and id3 are same
        assert id1 in agent_set
        assert id2 in agent_set

    def test_can_be_used_as_dict_keys(self):
        """Should work correctly as dictionary keys"""
        id1 = AgentId.generate_new()
        id2 = AgentId.generate_new()

        agent_dict = {id1: "value1", id2: "value2"}
        assert agent_dict[id1] == "value1"
        assert agent_dict[id2] == "value2"


class TestAgentIdStringRepresentation:
    """Test AgentId string representations"""

    def test_str_returns_value(self):
        """Should return value when converted to string"""
        uuid_str = str(uuid.uuid4())
        agent_id = AgentId(uuid_str)
        assert str(agent_id) == uuid_str

    def test_to_canonical_format(self):
        """Should return canonical format with hyphens"""
        agent_id = AgentId.generate_new()
        canonical = agent_id.to_canonical_format()
        assert canonical == agent_id.value
        assert '-' in canonical
        assert len(canonical) == 36

    def test_to_hex_format(self):
        """Should return hex format without hyphens"""
        agent_id = AgentId.generate_new()
        hex_format = agent_id.to_hex_format()
        assert '-' not in hex_format
        assert len(hex_format) == 32
        # Verify it's the same UUID
        assert hex_format == agent_id.value.replace('-', '')


class TestAgentIdImmutability:
    """Test AgentId immutability"""

    def test_cannot_modify_value_after_creation(self):
        """Should not allow modification of value after creation"""
        agent_id = AgentId.generate_new()
        with pytest.raises(AttributeError):
            agent_id.value = "new-value"

    def test_frozen_dataclass(self):
        """Should be a frozen dataclass"""
        agent_id = AgentId.generate_new()
        assert agent_id.__dataclass_fields__['value'].metadata.get('frozen', False) or \
               getattr(agent_id.__class__, '__dataclass_params__').frozen
