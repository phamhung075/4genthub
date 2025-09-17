"""
Tests for Unified Context Module
"""

import pytest

from fastmcp.task_management.domain.models.unified_context import ContextLevel


class TestUnifiedContextModule:
    """Test unified context module imports and compatibility"""
    
    def test_context_level_import(self):
        """Test that ContextLevel can be imported from unified_context"""
        from fastmcp.task_management.domain.models.unified_context import ContextLevel
        
        assert ContextLevel is not None
        assert hasattr(ContextLevel, 'GLOBAL')
        assert hasattr(ContextLevel, 'PROJECT')
        assert hasattr(ContextLevel, 'BRANCH')
        assert hasattr(ContextLevel, 'TASK')
    
    def test_context_level_functionality(self):
        """Test that imported ContextLevel has expected functionality"""
        # Test enum values
        assert ContextLevel.GLOBAL.value == "global"
        assert ContextLevel.PROJECT.value == "project"
        assert ContextLevel.BRANCH.value == "branch"
        assert ContextLevel.TASK.value == "task"
    
    def test_context_level_hierarchy_methods(self):
        """Test ContextLevel hierarchy methods work through import"""
        # Test parent level method
        assert ContextLevel.TASK.get_parent_level() == ContextLevel.BRANCH
        assert ContextLevel.BRANCH.get_parent_level() == ContextLevel.PROJECT
        assert ContextLevel.PROJECT.get_parent_level() == ContextLevel.GLOBAL
        assert ContextLevel.GLOBAL.get_parent_level() is None
    
    def test_context_level_from_string(self):
        """Test from_string method works through import"""
        assert ContextLevel.from_string("global") == ContextLevel.GLOBAL
        assert ContextLevel.from_string("project") == ContextLevel.PROJECT
        assert ContextLevel.from_string("branch") == ContextLevel.BRANCH
        assert ContextLevel.from_string("task") == ContextLevel.TASK
        
        # Test case insensitive
        assert ContextLevel.from_string("GLOBAL") == ContextLevel.GLOBAL
        assert ContextLevel.from_string("Project") == ContextLevel.PROJECT
    
    def test_context_level_from_string_invalid(self):
        """Test from_string with invalid value"""
        with pytest.raises(ValueError) as exc_info:
            ContextLevel.from_string("invalid")
        
        assert "Invalid context level: invalid" in str(exc_info.value)
        assert "global, project, branch, task" in str(exc_info.value)
    
    def test_context_level_string_representation(self):
        """Test string representation through import"""
        assert str(ContextLevel.GLOBAL) == "global"
        assert str(ContextLevel.PROJECT) == "project" 
        assert str(ContextLevel.BRANCH) == "branch"
        assert str(ContextLevel.TASK) == "task"
    
    def test_module_all_exports(self):
        """Test that __all__ exports are correct"""
        from fastmcp.task_management.domain.models import unified_context
        
        assert hasattr(unified_context, '__all__')
        assert 'ContextLevel' in unified_context.__all__
    
    def test_compatibility_import_patterns(self):
        """Test various import patterns work correctly"""
        # Direct import
        from fastmcp.task_management.domain.models.unified_context import ContextLevel as DirectContextLevel
        
        # Module import
        from fastmcp.task_management.domain.models import unified_context
        ModuleContextLevel = unified_context.ContextLevel
        
        # Test they're the same class
        assert DirectContextLevel is ModuleContextLevel
        assert DirectContextLevel.GLOBAL is ModuleContextLevel.GLOBAL


class TestContextLevelThroughUnifiedContext:
    """Test ContextLevel functionality specifically through unified_context import"""
    
    def test_enum_membership(self):
        """Test that ContextLevel values are proper enum members"""
        levels = list(ContextLevel)
        
        assert len(levels) == 4
        assert ContextLevel.GLOBAL in levels
        assert ContextLevel.PROJECT in levels
        assert ContextLevel.BRANCH in levels
        assert ContextLevel.TASK in levels
    
    def test_enum_iteration_order(self):
        """Test that enum iteration follows expected order"""
        levels = list(ContextLevel)
        
        # Should be in the order they're defined
        expected_order = [
            ContextLevel.GLOBAL,
            ContextLevel.PROJECT,
            ContextLevel.BRANCH,
            ContextLevel.TASK
        ]
        
        assert levels == expected_order
    
    def test_enum_comparison(self):
        """Test enum comparison operations"""
        # Equality
        assert ContextLevel.GLOBAL == ContextLevel.GLOBAL
        assert ContextLevel.GLOBAL != ContextLevel.PROJECT
        
        # String comparison
        assert ContextLevel.GLOBAL == "global"
        assert ContextLevel.PROJECT == "project"
        assert ContextLevel.BRANCH == "branch"
        assert ContextLevel.TASK == "task"
    
    def test_enum_in_collections(self):
        """Test using ContextLevel in collections"""
        # In lists
        level_list = [ContextLevel.GLOBAL, ContextLevel.PROJECT]
        assert ContextLevel.GLOBAL in level_list
        assert ContextLevel.TASK not in level_list
        
        # In sets
        level_set = {ContextLevel.BRANCH, ContextLevel.TASK}
        assert ContextLevel.BRANCH in level_set
        assert ContextLevel.GLOBAL not in level_set
        
        # As dictionary keys
        level_dict = {
            ContextLevel.GLOBAL: "global_data",
            ContextLevel.PROJECT: "project_data"
        }
        assert level_dict[ContextLevel.GLOBAL] == "global_data"
        assert level_dict[ContextLevel.PROJECT] == "project_data"
    
    def test_hierarchy_traversal(self):
        """Test traversing the context hierarchy"""
        # Start from task level and traverse up
        current = ContextLevel.TASK
        hierarchy = []
        
        while current is not None:
            hierarchy.append(current)
            current = current.get_parent_level()
        
        expected_hierarchy = [
            ContextLevel.TASK,
            ContextLevel.BRANCH,
            ContextLevel.PROJECT,
            ContextLevel.GLOBAL
        ]
        
        assert hierarchy == expected_hierarchy
    
    def test_from_string_edge_cases(self):
        """Test from_string with various edge cases"""
        # Whitespace handling
        assert ContextLevel.from_string("  global  ".strip()) == ContextLevel.GLOBAL
        
        # Case variations
        test_cases = [
            ("global", ContextLevel.GLOBAL),
            ("GLOBAL", ContextLevel.GLOBAL),
            ("Global", ContextLevel.GLOBAL),
            ("gLoBaL", ContextLevel.GLOBAL),
            ("project", ContextLevel.PROJECT),
            ("PROJECT", ContextLevel.PROJECT),
            ("branch", ContextLevel.BRANCH),
            ("BRANCH", ContextLevel.BRANCH),
            ("task", ContextLevel.TASK),
            ("TASK", ContextLevel.TASK)
        ]
        
        for input_value, expected_level in test_cases:
            assert ContextLevel.from_string(input_value) == expected_level
    
    def test_from_string_error_message_quality(self):
        """Test that from_string error messages are helpful"""
        with pytest.raises(ValueError) as exc_info:
            ContextLevel.from_string("unknown")
        
        error_message = str(exc_info.value)
        
        # Should contain the invalid value
        assert "unknown" in error_message
        
        # Should contain all valid options
        assert "global" in error_message
        assert "project" in error_message
        assert "branch" in error_message
        assert "task" in error_message
    
    def test_level_parent_relationships(self):
        """Test all parent-child relationships in detail"""
        # Test specific relationships
        assert ContextLevel.TASK.get_parent_level() == ContextLevel.BRANCH
        assert ContextLevel.BRANCH.get_parent_level() == ContextLevel.PROJECT
        assert ContextLevel.PROJECT.get_parent_level() == ContextLevel.GLOBAL
        assert ContextLevel.GLOBAL.get_parent_level() is None
        
        # Test that relationships are consistent
        for level in ContextLevel:
            parent = level.get_parent_level()
            if parent is not None:
                # Parent should be a valid ContextLevel
                assert isinstance(parent, ContextLevel)
                # Parent should not be the same as child
                assert parent != level


class TestContextLevelEdgeCases:
    """Test edge cases and error conditions for ContextLevel through unified_context"""
    
    def test_invalid_from_string_inputs(self):
        """Test from_string with various invalid inputs"""
        invalid_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "invalid",  # Non-existent level
            "context",  # Close but not valid
            "tasks",  # Plural form
            "projects",  # Plural form
            "123",  # Numeric
            "global project",  # Multiple words
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                ContextLevel.from_string(invalid_input)
    
    def test_context_level_type_safety(self):
        """Test type safety of ContextLevel operations"""
        # Should be both str and Enum
        assert isinstance(ContextLevel.GLOBAL, str)
        assert isinstance(ContextLevel.GLOBAL, ContextLevel)
        
        # String operations should work
        assert ContextLevel.GLOBAL.upper() == "GLOBAL"
        assert ContextLevel.GLOBAL.capitalize() == "Global"
        
        # Enum operations should work
        assert ContextLevel.GLOBAL.name == "GLOBAL"
        assert ContextLevel.GLOBAL.value == "global"
    
    def test_serialization_compatibility(self):
        """Test that ContextLevel works well with serialization"""
        import json
        
        # Should be JSON serializable as string
        data = {"level": ContextLevel.GLOBAL}
        
        # This should work because ContextLevel inherits from str
        json_str = json.dumps(data, default=str)
        assert "global" in json_str
        
        # Deserialization
        loaded_data = json.loads(json_str)
        assert loaded_data["level"] == "global"
        
        # Can reconstruct the enum
        reconstructed = ContextLevel.from_string(loaded_data["level"])
        assert reconstructed == ContextLevel.GLOBAL