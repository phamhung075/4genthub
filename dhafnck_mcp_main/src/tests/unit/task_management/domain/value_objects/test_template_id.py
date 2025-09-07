"""Unit tests for TemplateId value object"""

import pytest
import uuid
import re
from unittest.mock import patch, Mock

from fastmcp.task_management.domain.value_objects.template_id import TemplateId


class TestTemplateIdCreation:
    """Test TemplateId creation with various valid inputs"""

    def test_create_with_uuid_string(self):
        """Test creating TemplateId with UUID string"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        template_id = TemplateId(uuid_str)
        assert template_id.value == uuid_str
        assert str(template_id) == uuid_str

    def test_create_with_simple_string(self):
        """Test creating TemplateId with simple string"""
        simple_str = "my-template"
        template_id = TemplateId(simple_str)
        assert template_id.value == simple_str
        assert str(template_id) == simple_str

    def test_create_with_alphanumeric_string(self):
        """Test creating TemplateId with alphanumeric string"""
        alphanumeric = "template123"
        template_id = TemplateId(alphanumeric)
        assert template_id.value == alphanumeric
        assert str(template_id) == alphanumeric

    def test_create_with_special_characters(self):
        """Test creating TemplateId with special characters"""
        special_str = "template_2024-v1.0"
        template_id = TemplateId(special_str)
        assert template_id.value == special_str
        assert str(template_id) == special_str

    def test_create_with_whitespace_preserved(self):
        """Test creating TemplateId preserves whitespace (does not strip)"""
        padded_str = "  template-name  "
        template_id = TemplateId(padded_str)
        assert template_id.value == padded_str
        assert str(template_id) == padded_str


class TestTemplateIdValidation:
    """Test TemplateId validation and error handling"""

    def test_create_with_empty_string_raises_error(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="Template ID cannot be empty"):
            TemplateId("")

    def test_create_with_none_raises_error(self):
        """Test that None raises ValueError"""
        with pytest.raises(ValueError, match="Template ID cannot be empty"):
            TemplateId(None)

    def test_create_with_non_string_raises_error(self):
        """Test that non-string value raises ValueError"""
        with pytest.raises(ValueError, match="Template ID must be a string"):
            TemplateId(123)
        
        with pytest.raises(ValueError, match="Template ID must be a string"):
            TemplateId(['template-id'])
        
        with pytest.raises(ValueError, match="Template ID must be a string"):
            TemplateId({'id': 'template'})

    def test_create_with_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValueError"""
        with pytest.raises(ValueError, match="Template ID cannot be whitespace only"):
            TemplateId("   ")
        
        with pytest.raises(ValueError, match="Template ID cannot be whitespace only"):
            TemplateId("\t\n")
        
        with pytest.raises(ValueError, match="Template ID cannot be whitespace only"):
            TemplateId("  \r  ")


class TestTemplateIdImmutability:
    """Test TemplateId immutability (frozen dataclass)"""

    def test_template_id_is_immutable(self):
        """Test that TemplateId instances cannot be modified after creation"""
        template_id = TemplateId("my-template")
        
        with pytest.raises(AttributeError):
            template_id.value = "different-template"

    def test_template_id_hashable(self):
        """Test that TemplateId instances can be used as dictionary keys"""
        id1 = TemplateId("template-1")
        id2 = TemplateId("template-2")
        
        template_dict = {id1: "First template", id2: "Second template"}
        
        assert template_dict[id1] == "First template"
        assert template_dict[id2] == "Second template"


class TestTemplateIdEquality:
    """Test TemplateId equality comparison"""

    def test_equal_template_ids(self):
        """Test that TemplateIds with same value are equal"""
        id1 = TemplateId("my-template")
        id2 = TemplateId("my-template")
        
        assert id1 == id2
        assert hash(id1) == hash(id2)

    def test_different_template_ids_with_whitespace(self):
        """Test that TemplateIds with different whitespace are not equal"""
        id1 = TemplateId("my-template")
        id2 = TemplateId("  my-template  ")
        
        assert id1 != id2  # Different because whitespace is preserved
        assert hash(id1) != hash(id2)

    def test_different_template_ids_not_equal(self):
        """Test that TemplateIds with different values are not equal"""
        id1 = TemplateId("template-1")
        id2 = TemplateId("template-2")
        
        assert id1 != id2
        assert hash(id1) != hash(id2)

    def test_equality_with_string(self):
        """Test equality comparison with string values"""
        template_id = TemplateId("my-template")
        
        # Should equal string with same value
        assert template_id == "my-template"
        
        # Should not equal string with different value
        assert template_id != "different-template"
        assert template_id != "my_template"

    def test_equality_with_non_string_non_template_id(self):
        """Test equality with non-string, non-TemplateId objects"""
        template_id = TemplateId("my-template")
        
        assert template_id != 123
        assert template_id != None
        assert template_id != ['my-template']
        assert template_id != {'id': 'my-template'}


class TestTemplateIdClassMethods:
    """Test TemplateId class methods"""

    def test_generate_class_method(self):
        """Test TemplateId.generate() class method"""
        template_id = TemplateId.generate()
        
        assert isinstance(template_id, TemplateId)
        assert isinstance(template_id.value, str)
        assert len(template_id.value) == 36  # UUID v4 string length
        
        # Should be a valid UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, template_id.value)

    def test_generate_creates_unique_ids(self):
        """Test that generate() creates unique IDs"""
        id1 = TemplateId.generate()
        id2 = TemplateId.generate()
        
        assert id1 != id2
        assert id1.value != id2.value

    @patch('uuid.uuid4')
    def test_generate_uses_uuid4(self, mock_uuid4):
        """Test that generate() uses uuid.uuid4()"""
        mock_uuid = Mock()
        mock_uuid.__str__ = Mock(return_value="550e8400-e29b-41d4-a716-446655440000")
        mock_uuid4.return_value = mock_uuid
        
        template_id = TemplateId.generate()
        
        assert template_id.value == "550e8400-e29b-41d4-a716-446655440000"
        mock_uuid4.assert_called_once()

    def test_from_string_class_method(self):
        """Test TemplateId.from_string() class method"""
        template_str = "my-custom-template"
        template_id = TemplateId.from_string(template_str)
        
        assert isinstance(template_id, TemplateId)
        assert template_id.value == template_str

    def test_from_string_strips_whitespace(self):
        """Test that from_string() strips whitespace"""
        template_str = "  my-template  "
        template_id = TemplateId.from_string(template_str)
        
        assert template_id.value == "my-template"

    def test_from_string_with_empty_string_raises_error(self):
        """Test that from_string() with empty string raises error"""
        with pytest.raises(ValueError, match="Template ID cannot be empty"):
            TemplateId.from_string("")

    def test_from_string_with_whitespace_only_raises_error(self):
        """Test that from_string() with whitespace only raises error"""
        with pytest.raises(ValueError, match="Template ID cannot be empty"):
            TemplateId.from_string("   ")  # This gets stripped to empty string


class TestTemplateIdStringRepresentation:
    """Test TemplateId string representation"""

    def test_str_method(self):
        """Test __str__ method returns the value"""
        template_id = TemplateId("my-template")
        assert str(template_id) == "my-template"

    def test_repr_method(self):
        """Test __repr__ method provides meaningful representation"""
        template_id = TemplateId("my-template")
        
        repr_str = repr(template_id)
        expected = "TemplateId('my-template')"
        assert repr_str == expected

    def test_repr_with_special_characters(self):
        """Test __repr__ with special characters"""
        template_id = TemplateId("template_2024-v1.0")
        
        repr_str = repr(template_id)
        expected = "TemplateId('template_2024-v1.0')"
        assert repr_str == expected

    def test_repr_eval_roundtrip(self):
        """Test that repr can be used to recreate the object"""
        original = TemplateId("my-template")
        repr_str = repr(original)
        
        # Should be able to eval the repr (in a safe context)
        recreated = eval(repr_str, {"TemplateId": TemplateId})
        assert recreated == original


class TestTemplateIdHashing:
    """Test TemplateId hashing behavior"""

    def test_template_id_hash_consistency(self):
        """Test that TemplateId hash is consistent"""
        template_id = TemplateId("my-template")
        
        # Hash should be consistent across multiple calls
        hash1 = hash(template_id)
        hash2 = hash(template_id)
        assert hash1 == hash2

    def test_equal_template_ids_have_same_hash(self):
        """Test that equal TemplateIds have the same hash"""
        id1 = TemplateId("my-template")
        id2 = TemplateId("my-template")
        
        assert id1 == id2
        assert hash(id1) == hash(id2)

    def test_different_template_ids_have_different_hash(self):
        """Test that different TemplateIds have different hashes"""
        id1 = TemplateId("template-1")
        id2 = TemplateId("template-2")
        
        assert id1 != id2
        assert hash(id1) != hash(id2)

    def test_template_id_in_set(self):
        """Test that TemplateId works correctly in sets"""
        id1 = TemplateId("template-1")
        id2 = TemplateId("template-2")
        id3 = TemplateId("template-1")  # Duplicate
        
        template_set = {id1, id2, id3}
        
        # Should only have 2 unique templates
        assert len(template_set) == 2
        assert id1 in template_set
        assert id2 in template_set


class TestTemplateIdEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_template_id_with_long_string(self):
        """Test TemplateId with very long string"""
        long_string = "a" * 1000
        template_id = TemplateId(long_string)
        assert template_id.value == long_string

    def test_template_id_with_unicode_characters(self):
        """Test TemplateId with Unicode characters"""
        unicode_string = "template-🚀-2024"
        template_id = TemplateId(unicode_string)
        assert template_id.value == unicode_string

    def test_template_id_with_newlines_and_tabs(self):
        """Test TemplateId with newlines and tabs in middle"""
        string_with_newlines = "template\nwith\nnewlines"
        template_id = TemplateId(string_with_newlines)
        assert template_id.value == string_with_newlines

    def test_template_id_with_only_numbers(self):
        """Test TemplateId with numeric string"""
        numeric_string = "123456789"
        template_id = TemplateId(numeric_string)
        assert template_id.value == numeric_string

    def test_template_id_case_sensitivity(self):
        """Test that TemplateId is case-sensitive"""
        id1 = TemplateId("Template")
        id2 = TemplateId("template")
        id3 = TemplateId("TEMPLATE")
        
        # All should be different
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3
        
        # Should have different hashes
        assert hash(id1) != hash(id2)
        assert hash(id2) != hash(id3)
        assert hash(id1) != hash(id3)


class TestTemplateIdIntegration:
    """Integration tests combining multiple TemplateId features"""

    def test_template_id_in_collections(self):
        """Test using TemplateId in various collections"""
        template_ids = [
            TemplateId.generate(),
            TemplateId("custom-template"),
            TemplateId("another-template"),
            TemplateId.generate(),
        ]
        
        # Test in list
        assert len(template_ids) == 4
        assert all(isinstance(tid, TemplateId) for tid in template_ids)
        
        # Test in set (should maintain uniqueness)
        template_set = set(template_ids)
        assert len(template_set) == len(template_ids)  # All should be unique
        
        # Test as dictionary keys
        template_data = {tid: f"template_{i}" for i, tid in enumerate(template_ids)}
        assert len(template_data) == len(template_ids)
        
        # Verify we can retrieve data by TemplateId
        for i, template_id in enumerate(template_ids):
            assert template_data[template_id] == f"template_{i}"

    def test_template_id_sorting(self):
        """Test sorting TemplateIds"""
        template_ids = [
            TemplateId("zebra-template"),
            TemplateId("alpha-template"), 
            TemplateId("beta-template"),
            TemplateId("charlie-template"),
        ]
        
        # Sort by string value
        sorted_ids = sorted(template_ids, key=lambda x: x.value)
        
        expected_order = [
            "alpha-template",
            "beta-template", 
            "charlie-template",
            "zebra-template"
        ]
        
        for i, expected in enumerate(expected_order):
            assert sorted_ids[i].value == expected

    def test_template_id_json_serialization_workflow(self):
        """Test workflow for JSON serialization/deserialization"""
        original_id = TemplateId("my-json-template")
        
        # Serialize to string for JSON
        json_value = str(original_id)
        assert isinstance(json_value, str)
        assert json_value == "my-json-template"
        
        # Deserialize from JSON string
        restored_id = TemplateId(json_value)
        
        # Should be equal to original
        assert restored_id == original_id
        assert str(restored_id) == str(original_id)

    def test_template_business_logic_scenarios(self):
        """Test common business logic scenarios"""
        # Scenario 1: Template creation and management
        template_registry = {}
        
        # Create various templates
        default_template = TemplateId("default-task-template")
        bug_template = TemplateId("bug-report-template")
        feature_template = TemplateId("feature-request-template")
        
        template_registry[default_template] = {
            'name': 'Default Task Template',
            'fields': ['title', 'description', 'priority']
        }
        template_registry[bug_template] = {
            'name': 'Bug Report Template',
            'fields': ['title', 'description', 'steps_to_reproduce', 'expected_behavior']
        }
        template_registry[feature_template] = {
            'name': 'Feature Request Template', 
            'fields': ['title', 'description', 'user_story', 'acceptance_criteria']
        }
        
        # Test template lookup
        assert len(template_registry) == 3
        assert default_template in template_registry
        assert template_registry[bug_template]['name'] == 'Bug Report Template'
        
        # Scenario 2: Template duplication detection
        duplicate_default = TemplateId("default-task-template")
        assert duplicate_default == default_template
        assert duplicate_default in template_registry
        
        # Scenario 3: Generated template IDs for dynamic templates
        dynamic_template1 = TemplateId.generate()
        dynamic_template2 = TemplateId.generate() 
        
        assert dynamic_template1 != dynamic_template2
        assert dynamic_template1 not in template_registry
        assert dynamic_template2 not in template_registry

    def test_template_id_with_mixed_creation_methods(self):
        """Test mixing different TemplateId creation methods"""
        # Create using different methods
        generated_id = TemplateId.generate()
        string_id = TemplateId("custom-string-template")
        from_string_id = TemplateId.from_string("  from-string-template  ")
        
        # All should be valid TemplateId instances
        assert isinstance(generated_id, TemplateId)
        assert isinstance(string_id, TemplateId)
        assert isinstance(from_string_id, TemplateId)
        
        # All should be unique (different values)
        all_ids = [generated_id, string_id, from_string_id]
        assert len(set(all_ids)) == 3
        
        # from_string should have whitespace stripped
        assert from_string_id.value == "from-string-template"
        
        # Should work in collections together
        template_collection = {
            generated_id: "Generated Template",
            string_id: "Custom Template", 
            from_string_id: "From String Template"
        }
        
        assert len(template_collection) == 3
        assert all(isinstance(key, TemplateId) for key in template_collection.keys())


class TestTemplateIdTypeAnnotations:
    """Test TemplateId with type annotations and type checking scenarios"""

    def test_template_id_type_checking(self):
        """Test TemplateId behaves correctly with type checking"""
        template_id = TemplateId("test-template")
        
        # Should pass isinstance checks
        assert isinstance(template_id, TemplateId)
        assert not isinstance(template_id, str)
        assert not isinstance(template_id, int)
        
    def test_template_id_as_function_parameter(self):
        """Test using TemplateId as a function parameter"""
        def process_template(template_id: TemplateId) -> str:
            return f"Processing template: {template_id.value}"
        
        test_id = TemplateId("my-test-template")
        result = process_template(test_id)
        
        assert result == "Processing template: my-test-template"

    def test_template_id_return_type(self):
        """Test returning TemplateId from functions"""
        def create_template_id(name: str) -> TemplateId:
            return TemplateId.from_string(name)
        
        result = create_template_id("function-created-template")
        
        assert isinstance(result, TemplateId)
        assert result.value == "function-created-template"