"""
Tests for Context Template Manager - Operation-Specific Context Injection
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import json
from typing import Dict, List, Any, Optional

from fastmcp.task_management.application.services.context_template_manager import (
    ContextTemplateManager,
    OperationType,
    TemplateValidationError
)


class TestOperationType:
    """Test suite for OperationType enum"""
    
    def test_operation_type_values(self):
        """Test that operation types have expected values"""
        assert OperationType.TASK_CREATE.value == "task.create"
        assert OperationType.TASK_UPDATE.value == "task.update"
        assert OperationType.CONTEXT_RESOLVE.value == "context.resolve"
        assert OperationType.AGENT_CALL.value == "agent.call"
    
    def test_all_operation_types_defined(self):
        """Test that all expected operation types exist"""
        expected_operations = [
            "TASK_CREATE", "TASK_UPDATE", "TASK_GET", "TASK_LIST", "TASK_DELETE",
            "TASK_COMPLETE", "TASK_SEARCH", "TASK_NEXT",
            "SUBTASK_CREATE", "SUBTASK_UPDATE", "SUBTASK_DELETE", "SUBTASK_LIST",
            "SUBTASK_COMPLETE",
            "CONTEXT_CREATE", "CONTEXT_GET", "CONTEXT_UPDATE", "CONTEXT_DELETE",
            "CONTEXT_RESOLVE", "CONTEXT_DELEGATE",
            "PROJECT_CREATE", "PROJECT_GET", "PROJECT_UPDATE", "PROJECT_LIST",
            "PROJECT_HEALTH_CHECK",
            "GIT_BRANCH_CREATE", "GIT_BRANCH_GET", "GIT_BRANCH_LIST",
            "GIT_BRANCH_UPDATE", "GIT_BRANCH_DELETE",
            "AGENT_REGISTER", "AGENT_ASSIGN", "AGENT_LIST", "AGENT_CALL"
        ]
        
        for op_name in expected_operations:
            assert hasattr(OperationType, op_name)


class TestContextTemplateManager:
    """Test Context Template Manager functionality"""

    @pytest.fixture
    def manager(self):
        """Create template manager instance"""
        return ContextTemplateManager()

    @pytest.fixture
    def sample_yaml_content(self):
        """Sample YAML template content"""
        return """
version: "2.0.0"
templates:
  task.create:
    project: ["id", "name", "settings"]
    git_branch: ["id", "name"]
    user: ["id", "preferences"]
  task.custom:
    task: ["id", "title", "status"]
    custom_field: ["data"]
"""

    def test_manager_initialization(self, manager):
        """Test manager initialization with default templates"""
        assert manager.template_version == "1.0.0"
        assert len(manager.templates) > 0
        assert OperationType.TASK_CREATE in manager.templates
        assert OperationType.TASK_UPDATE in manager.templates
        assert manager._metrics["templates_used"] == 0

    def test_get_template_basic(self, manager):
        """Test getting a basic template"""
        template = manager.get_template(OperationType.TASK_CREATE)
        
        assert isinstance(template, dict)
        assert "project" in template
        assert "git_branch" in template
        assert "user" in template
        assert manager._metrics["templates_used"] == 1

    def test_get_template_with_overrides(self, manager):
        """Test getting template with field overrides"""
        override_fields = {
            "project": ["id", "name"],
            "custom": ["new_field"]
        }
        
        template = manager.get_template(OperationType.TASK_CREATE, override_fields)
        
        assert template["project"] == ["id", "name"]
        assert template["custom"] == ["new_field"]

    def test_get_template_with_wildcard(self, manager):
        """Test getting template with wildcard fields"""
        override_fields = {
            "task": ["*"]
        }
        
        template = manager.get_template(OperationType.TASK_GET, override_fields)
        
        assert template["task"] == ["*"]

    def test_template_caching(self, manager):
        """Test that templates are cached"""
        # First call
        template1 = manager.get_template(OperationType.TASK_CREATE)
        
        # Second call should use cache
        template2 = manager.get_template(OperationType.TASK_CREATE)
        
        assert template1 == template2
        assert manager._metrics["cache_hits"] == 1
        # Templates_used tracks unique templates, not individual calls
        assert manager._metrics["templates_used"] == 1

    def test_inheritance_map(self, manager):
        """Test that inheritance map is built correctly"""
        inheritance_map = manager._inheritance_map
        
        assert OperationType.SUBTASK_CREATE in inheritance_map
        assert OperationType.TASK_CREATE in inheritance_map[OperationType.SUBTASK_CREATE]
        assert OperationType.TASK_SEARCH in inheritance_map
        assert OperationType.TASK_LIST in inheritance_map[OperationType.TASK_SEARCH]

    def test_apply_inheritance(self, manager):
        """Test template inheritance application"""
        # Test subtask create inherits from task create
        subtask_template = manager.get_template(OperationType.SUBTASK_CREATE)
        task_template = manager.get_template(OperationType.TASK_CREATE)
        
        # Should have inherited some fields from parent
        assert "project" in subtask_template
        assert "parent_task" in subtask_template  # Own fields

    def test_load_custom_templates(self, manager, sample_yaml_content):
        """Test loading custom templates from YAML"""
        with patch("builtins.open", mock_open(read_data=sample_yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                manager.load_custom_templates("test_templates.yaml")
        
        # Should have updated version
        assert manager.template_version == "2.0.0"
        
        # Should have custom template
        assert OperationType.TASK_CREATE in manager.custom_templates
        
        # Should be able to get custom template
        custom_template = manager.get_template(OperationType.TASK_CREATE)
        assert "project" in custom_template

    def test_load_custom_templates_file_not_exists(self, manager):
        """Test loading custom templates when file doesn't exist"""
        with patch.object(Path, "exists", return_value=False):
            manager.load_custom_templates("nonexistent.yaml")
        
        # Should still have default templates
        assert len(manager.templates) > 0

    def test_load_custom_templates_invalid_operation(self, manager):
        """Test loading custom templates with invalid operation type"""
        invalid_yaml = """
templates:
  invalid.operation:
    field: ["value"]
"""
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch.object(Path, "exists", return_value=True):
                manager.load_custom_templates("test_templates.yaml")
        
        # Should not have added invalid operation
        assert len(manager.custom_templates) == 0

    def test_save_templates(self, manager):
        """Test saving templates to YAML file"""
        output_path = "/tmp/test_templates.yaml"
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch.object(Path, "mkdir"):
                manager.save_templates(output_path)
        
        mock_file.assert_called_once_with(Path(output_path), 'w')

    def test_validate_template_valid(self, manager):
        """Test template validation with required contexts"""
        required_contexts = ["project", "git_branch"]
        
        is_valid = manager.validate_template(OperationType.TASK_CREATE, required_contexts)
        
        assert is_valid

    def test_validate_template_invalid(self, manager):
        """Test template validation with missing contexts"""
        required_contexts = ["project", "nonexistent_context"]
        
        is_valid = manager.validate_template(OperationType.TASK_CREATE, required_contexts)
        
        assert not is_valid

    def test_get_minimal_context_basic(self, manager):
        """Test extracting minimal context from available data"""
        available_data = {
            "project": {
                "id": "proj-123",
                "name": "Test Project",
                "description": "Long description",
                "settings": {"key": "value"},
                "extra_field": "not needed"
            },
            "git_branch": {
                "id": "branch-456",
                "name": "feature/test",
                "status": "active",
                "commits": ["commit1", "commit2"]
            }
        }
        
        minimal = manager.get_minimal_context(OperationType.TASK_CREATE, available_data)
        
        # Should only have required fields from template
        assert "project" in minimal
        assert "id" in minimal["project"]
        assert "name" in minimal["project"]
        # Settings not included in current TASK_CREATE template
        assert "extra_field" not in minimal["project"]

    def test_get_minimal_context_wildcard(self, manager):
        """Test extracting minimal context with wildcard fields"""
        available_data = {
            "task": {
                "id": "task-123",
                "title": "Test Task",
                "description": "Description",
                "status": "active"
            }
        }
        
        minimal = manager.get_minimal_context(OperationType.TASK_GET, available_data)
        
        # Wildcard should include all fields
        assert minimal["task"] == available_data["task"]

    def test_get_minimal_context_missing_data(self, manager):
        """Test extracting minimal context when some data is missing"""
        available_data = {
            "project": {
                "id": "proj-123",
                "name": "Test Project"
                # Missing 'settings' field
            }
        }
        
        minimal = manager.get_minimal_context(OperationType.TASK_CREATE, available_data)
        
        assert "project" in minimal
        assert minimal["project"]["id"] == "proj-123"
        assert minimal["project"]["name"] == "Test Project"

    def test_suggest_template_improvements(self, manager):
        """Test suggesting template improvements based on usage"""
        actual_usage = {
            "project": ["id", "name"],  # Missing 'default_priority' from template
            "git_branch": ["id", "name", "status", "extra_field"],  # Has extra field
            "user": ["id"]  # Missing 'preferences'
        }
        
        suggestions = manager.suggest_template_improvements(
            OperationType.TASK_CREATE, actual_usage
        )
        
        assert suggestions["operation"] == "task.create"
        assert "unused_fields" in suggestions
        assert "missing_fields" in suggestions
        assert suggestions["optimization_potential"] >= 0

    def test_get_metrics(self, manager):
        """Test getting usage metrics"""
        # Use some templates to generate metrics
        manager.get_template(OperationType.TASK_CREATE)
        manager.get_template(OperationType.TASK_UPDATE)
        manager.get_template(OperationType.TASK_CREATE)  # Should hit cache
        
        metrics = manager.get_metrics()
        
        # Templates_used tracks unique templates, not total calls
        assert metrics["templates_used"] == 2
        assert metrics["cache_hits"] == 1
        assert metrics["fields_requested"] > 0

    def test_reset_metrics(self, manager):
        """Test resetting usage metrics"""
        # Generate some metrics
        manager.get_template(OperationType.TASK_CREATE)
        assert manager._metrics["templates_used"] == 1
        
        # Reset
        manager.reset_metrics()
        
        assert manager._metrics["templates_used"] == 0
        assert manager._metrics["cache_hits"] == 0

    def test_get_all_operations(self, manager):
        """Test getting all supported operations"""
        operations = manager.get_all_operations()
        
        assert isinstance(operations, list)
        assert "task.create" in operations
        assert "context.resolve" in operations
        assert "agent.call" in operations

    def test_estimate_savings_no_usage(self, manager):
        """Test estimating savings with no usage"""
        savings = manager.estimate_savings()
        
        assert savings["field_reduction_percent"] == 0
        assert savings["estimated_time_savings_ms"] == 0
        assert savings["estimated_bandwidth_savings_kb"] == 0

    def test_estimate_savings_with_usage(self, manager):
        """Test estimating savings with usage"""
        # Simulate some field savings
        manager._metrics["fields_requested"] = 100
        manager._metrics["fields_saved"] = 50
        manager._metrics["templates_used"] = 10
        manager._metrics["cache_hits"] = 3
        
        savings = manager.estimate_savings()
        
        assert savings["field_reduction_percent"] > 0
        assert savings["estimated_time_savings_ms"] == 50  # 1ms per field
        assert savings["estimated_bandwidth_savings_kb"] > 0
        assert savings["cache_hit_rate"] == 30.0  # 3/10 * 100

    def test_default_templates_structure(self, manager):
        """Test that default templates have expected structure"""
        # Task operations
        task_create = manager.get_template(OperationType.TASK_CREATE)
        assert "project" in task_create
        assert "git_branch" in task_create
        assert "user" in task_create
        
        # Context operations
        context_resolve = manager.get_template(OperationType.CONTEXT_RESOLVE)
        assert "context" in context_resolve
        assert "hierarchy" in context_resolve
        
        # Agent operations
        agent_call = manager.get_template(OperationType.AGENT_CALL)
        assert "agent" in agent_call
        assert "context" in agent_call

    def test_template_with_custom_path(self):
        """Test creating manager with custom templates path"""
        yaml_content = """
version: "1.5.0"
templates:
  task.create:
    custom: ["field"]
"""
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                manager = ContextTemplateManager(templates_path="custom.yaml")
        
        assert manager.template_version == "1.5.0"
        assert len(manager.custom_templates) > 0


class TestTemplateValidationError:
    """Test TemplateValidationError exception"""
    
    def test_template_validation_error(self):
        """Test that TemplateValidationError can be raised and caught"""
        with pytest.raises(TemplateValidationError):
            raise TemplateValidationError("Test validation error")


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def manager(self):
        return ContextTemplateManager()
    
    def test_get_template_unknown_operation(self, manager):
        """Test getting template for unknown operation type"""
        # Create a mock operation type that doesn't exist in DEFAULT_TEMPLATES
        unknown_op = Mock()
        unknown_op.value = "unknown.operation"
        
        template = manager.get_template(unknown_op)
        
        # Should return empty template
        assert template == {}
    
    def test_load_templates_yaml_error(self, manager):
        """Test loading templates with YAML parsing error"""
        invalid_yaml = "invalid: yaml: content: ["
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch.object(Path, "exists", return_value=True):
                # Should not raise exception, just log error
                manager.load_custom_templates("invalid.yaml")
        
        # Should still have default templates
        assert len(manager.templates) > 0
    
    def test_save_templates_permission_error(self, manager):
        """Test saving templates with permission error"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Should not raise exception, just log error
            manager.save_templates("/root/test.yaml")
    
    def test_get_minimal_context_empty_available(self, manager):
        """Test getting minimal context with empty available data"""
        minimal = manager.get_minimal_context(OperationType.TASK_CREATE, {})
        
        # Should return empty dict
        assert minimal == {}
    
    def test_inheritance_circular_protection(self, manager):
        """Test that circular inheritance is protected against"""
        # The inheritance map should not contain circular references
        inheritance_map = manager._inheritance_map
        
        for child, parents in inheritance_map.items():
            # Parents should not contain the child itself
            assert child not in parents
            
            # Check one level deeper to avoid simple circular references
            for parent in parents:
                if parent in inheritance_map:
                    assert child not in inheritance_map[parent]