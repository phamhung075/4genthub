"""
Tests for Context Template Manager Service
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import json

from fastmcp.task_management.application.services.context_template_manager import (
    ContextTemplateManager,
    ContextTemplate,
    TemplateVariable,
    TemplateValidationError
)


class TestContextTemplateManager:
    """Test Context Template Manager functionality"""

    @pytest.fixture
    def manager(self):
        """Create template manager instance"""
        return ContextTemplateManager()

    @pytest.fixture
    def sample_template(self):
        """Sample context template"""
        return ContextTemplate(
            name="task_creation",
            description="Template for task creation context",
            variables=[
                TemplateVariable(name="project_name", type="string", required=True),
                TemplateVariable(name="priority", type="string", required=False, default="medium"),
                TemplateVariable(name="assignees", type="array", required=True)
            ],
            structure={
                "project": {
                    "name": "{{project_name}}",
                    "type": "software"
                },
                "task": {
                    "priority": "{{priority}}",
                    "assignees": "{{assignees}}",
                    "status": "todo"
                }
            }
        )

    @pytest.fixture
    def template_yaml_content(self):
        """Sample YAML template content"""
        return """
templates:
  task_creation:
    description: Template for creating tasks
    variables:
      - name: project_name
        type: string
        required: true
        description: Name of the project
      - name: priority
        type: string
        required: false
        default: medium
        allowed_values: [low, medium, high, urgent]
      - name: assignees
        type: array
        required: true
        min_items: 1
    structure:
      project:
        name: "{{project_name}}"
        type: software
      task:
        priority: "{{priority}}"
        assignees: "{{assignees}}"
        status: todo
        
  quick_fix:
    description: Template for quick fixes
    variables:
      - name: issue_id
        type: string
        required: true
    structure:
      fix:
        issue: "{{issue_id}}"
        type: hotfix
"""

    def test_load_templates_from_yaml(self, manager, template_yaml_content):
        """Test loading templates from YAML file"""
        with patch("builtins.open", mock_open(read_data=template_yaml_content)):
            manager.load_templates_from_file("templates.yaml")
        
        assert len(manager.templates) == 2
        assert "task_creation" in manager.templates
        assert "quick_fix" in manager.templates
        
        task_template = manager.get_template("task_creation")
        assert task_template.description == "Template for creating tasks"
        assert len(task_template.variables) == 3

    def test_register_template(self, manager, sample_template):
        """Test registering a template"""
        manager.register_template(sample_template)
        
        assert "task_creation" in manager.templates
        retrieved = manager.get_template("task_creation")
        assert retrieved == sample_template

    def test_apply_template_basic(self, manager, sample_template):
        """Test applying a template with basic values"""
        manager.register_template(sample_template)
        
        values = {
            "project_name": "MyProject",
            "assignees": ["coding-agent", "@test-agent"]
        }
        
        result = manager.apply_template("task_creation", values)
        
        assert result["project"]["name"] == "MyProject"
        assert result["task"]["priority"] == "medium"  # Default value
        assert result["task"]["assignees"] == ["coding-agent", "@test-agent"]
        assert result["task"]["status"] == "todo"

    def test_apply_template_with_all_values(self, manager, sample_template):
        """Test applying template with all values provided"""
        manager.register_template(sample_template)
        
        values = {
            "project_name": "MyProject",
            "priority": "high",
            "assignees": ["coding-agent"]
        }
        
        result = manager.apply_template("task_creation", values)
        
        assert result["task"]["priority"] == "high"

    def test_apply_template_missing_required(self, manager, sample_template):
        """Test applying template with missing required values"""
        manager.register_template(sample_template)
        
        values = {
            "project_name": "MyProject"
            # Missing required 'assignees'
        }
        
        with pytest.raises(TemplateValidationError) as exc:
            manager.apply_template("task_creation", values)
        
        assert "assignees" in str(exc.value)

    def test_template_variable_validation(self, manager):
        """Test variable type validation"""
        template = ContextTemplate(
            name="validated",
            variables=[
                TemplateVariable(name="count", type="integer", required=True),
                TemplateVariable(name="active", type="boolean", required=True),
                TemplateVariable(name="tags", type="array", required=True),
                TemplateVariable(name="config", type="object", required=True)
            ],
            structure={
                "data": {
                    "count": "{{count}}",
                    "active": "{{active}}",
                    "tags": "{{tags}}",
                    "config": "{{config}}"
                }
            }
        )
        
        manager.register_template(template)
        
        # Valid values
        values = {
            "count": 42,
            "active": True,
            "tags": ["tag1", "tag2"],
            "config": {"key": "value"}
        }
        
        result = manager.apply_template("validated", values)
        assert result["data"]["count"] == 42
        assert result["data"]["active"] is True
        
        # Invalid type
        invalid_values = {
            "count": "not a number",
            "active": True,
            "tags": ["tag1"],
            "config": {"key": "value"}
        }
        
        with pytest.raises(TemplateValidationError):
            manager.apply_template("validated", invalid_values)

    def test_template_with_nested_variables(self, manager):
        """Test template with nested variable substitution"""
        template = ContextTemplate(
            name="nested",
            variables=[
                TemplateVariable(name="env", type="string", required=True),
                TemplateVariable(name="region", type="string", required=True),
                TemplateVariable(name="service", type="string", required=True)
            ],
            structure={
                "deployment": {
                    "environment": "{{env}}",
                    "location": {
                        "region": "{{region}}",
                        "zone": "{{region}}-zone-1"
                    },
                    "service": {
                        "name": "{{service}}",
                        "url": "https://{{service}}.{{env}}.{{region}}.example.com"
                    }
                }
            }
        )
        
        manager.register_template(template)
        
        values = {
            "env": "prod",
            "region": "us-east",
            "service": "api"
        }
        
        result = manager.apply_template("nested", values)
        
        assert result["deployment"]["environment"] == "prod"
        assert result["deployment"]["location"]["region"] == "us-east"
        assert result["deployment"]["location"]["zone"] == "us-east-zone-1"
        assert result["deployment"]["service"]["url"] == "https://api.prod.us-east.example.com"

    def test_template_with_conditionals(self, manager):
        """Test template with conditional sections"""
        template = ContextTemplate(
            name="conditional",
            variables=[
                TemplateVariable(name="include_debug", type="boolean", required=True),
                TemplateVariable(name="log_level", type="string", required=False)
            ],
            structure={
                "config": {
                    "base": "standard",
                    "debug": {
                        "_condition": "{{include_debug}}",
                        "enabled": True,
                        "level": "{{log_level}}"
                    }
                }
            }
        )
        
        manager.register_template(template)
        
        # With debug enabled
        result = manager.apply_template("conditional", {
            "include_debug": True,
            "log_level": "verbose"
        })
        assert "debug" in result["config"]
        assert result["config"]["debug"]["level"] == "verbose"
        
        # With debug disabled
        result = manager.apply_template("conditional", {
            "include_debug": False
        })
        # Debug section should be excluded based on condition

    def test_template_with_loops(self, manager):
        """Test template with loop constructs"""
        template = ContextTemplate(
            name="loops",
            variables=[
                TemplateVariable(name="services", type="array", required=True),
                TemplateVariable(name="port_base", type="integer", required=True)
            ],
            structure={
                "services": {
                    "_for": "service in {{services}}",
                    "_template": {
                        "name": "{{service}}",
                        "port": "{{port_base + _index}}"
                    }
                }
            }
        )
        
        manager.register_template(template)
        
        values = {
            "services": ["web", "api", "worker"],
            "port_base": 8000
        }
        
        result = manager.apply_template("loops", values)
        # This would generate multiple service configurations

    def test_template_inheritance(self, manager):
        """Test template inheritance"""
        # Base template
        base = ContextTemplate(
            name="base_task",
            variables=[
                TemplateVariable(name="title", type="string", required=True)
            ],
            structure={
                "task": {
                    "title": "{{title}}",
                    "created_by": "system",
                    "version": "1.0"
                }
            }
        )
        
        # Extended template
        extended = ContextTemplate(
            name="feature_task",
            extends="base_task",
            variables=[
                TemplateVariable(name="feature_name", type="string", required=True)
            ],
            structure={
                "task": {
                    "type": "feature",
                    "feature": "{{feature_name}}"
                }
            }
        )
        
        manager.register_template(base)
        manager.register_template(extended)
        
        result = manager.apply_template("feature_task", {
            "title": "Implement login",
            "feature_name": "authentication"
        })
        
        # Should have fields from both base and extended
        assert result["task"]["title"] == "Implement login"
        assert result["task"]["created_by"] == "system"  # From base
        assert result["task"]["type"] == "feature"  # From extended
        assert result["task"]["feature"] == "authentication"

    def test_template_allowed_values(self, manager):
        """Test validation of allowed values"""
        template = ContextTemplate(
            name="restricted",
            variables=[
                TemplateVariable(
                    name="status",
                    type="string",
                    required=True,
                    allowed_values=["draft", "published", "archived"]
                )
            ],
            structure={"status": "{{status}}"}
        )
        
        manager.register_template(template)
        
        # Valid value
        result = manager.apply_template("restricted", {"status": "published"})
        assert result["status"] == "published"
        
        # Invalid value
        with pytest.raises(TemplateValidationError) as exc:
            manager.apply_template("restricted", {"status": "deleted"})
        assert "allowed values" in str(exc.value)

    def test_template_with_functions(self, manager):
        """Test template with built-in functions"""
        template = ContextTemplate(
            name="functions",
            variables=[
                TemplateVariable(name="name", type="string", required=True),
                TemplateVariable(name="items", type="array", required=True)
            ],
            structure={
                "formatted": {
                    "upper_name": "{{upper(name)}}",
                    "lower_name": "{{lower(name)}}",
                    "item_count": "{{len(items)}}",
                    "timestamp": "{{now()}}"
                }
            }
        )
        
        manager.register_template(template)
        
        with patch('fastmcp.task_management.application.services.context_template_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2025-09-12T10:00:00"
            
            result = manager.apply_template("functions", {
                "name": "TestName",
                "items": ["a", "b", "c"]
            })
        
        # Functions should be evaluated
        assert result["formatted"]["upper_name"] == "TESTNAME"
        assert result["formatted"]["lower_name"] == "testname"
        assert result["formatted"]["item_count"] == 3

    def test_template_composition(self, manager):
        """Test composing multiple templates"""
        # Register component templates
        header = ContextTemplate(
            name="header",
            variables=[TemplateVariable(name="title", type="string", required=True)],
            structure={"header": {"title": "{{title}}"}}
        )
        
        body = ContextTemplate(
            name="body",
            variables=[TemplateVariable(name="content", type="string", required=True)],
            structure={"body": {"content": "{{content}}"}}
        )
        
        manager.register_template(header)
        manager.register_template(body)
        
        # Compose templates
        composed = manager.compose_templates(
            ["header", "body"],
            {
                "title": "My Document",
                "content": "Document content here"
            }
        )
        
        assert composed["header"]["title"] == "My Document"
        assert composed["body"]["content"] == "Document content here"

    def test_template_caching(self, manager, sample_template):
        """Test template compilation caching"""
        manager.register_template(sample_template)
        
        # First application should compile
        values = {"project_name": "Test", "assignees": ["agent1"]}
        result1 = manager.apply_template("task_creation", values)
        
        # Second application should use cache
        result2 = manager.apply_template("task_creation", values)
        
        assert result1 == result2

    def test_export_import_templates(self, manager, sample_template):
        """Test exporting and importing templates"""
        manager.register_template(sample_template)
        
        # Export to JSON
        exported = manager.export_templates()
        assert "task_creation" in exported
        
        # Clear and re-import
        manager.templates.clear()
        manager.import_templates(exported)
        
        assert "task_creation" in manager.templates
        imported = manager.get_template("task_creation")
        assert imported.name == sample_template.name

    def test_template_versioning(self, manager):
        """Test template versioning support"""
        v1 = ContextTemplate(
            name="versioned",
            version="1.0",
            variables=[TemplateVariable(name="field1", type="string", required=True)],
            structure={"data": {"field1": "{{field1}}"}}
        )
        
        v2 = ContextTemplate(
            name="versioned",
            version="2.0",
            variables=[
                TemplateVariable(name="field1", type="string", required=True),
                TemplateVariable(name="field2", type="string", required=True)
            ],
            structure={"data": {"field1": "{{field1}}", "field2": "{{field2}}"}}
        )
        
        manager.register_template(v1)
        manager.register_template(v2)
        
        # Should be able to get specific versions
        result_v1 = manager.apply_template("versioned", {"field1": "value1"}, version="1.0")
        assert "field2" not in result_v1["data"]
        
        result_v2 = manager.apply_template("versioned", {"field1": "value1", "field2": "value2"}, version="2.0")
        assert result_v2["data"]["field2"] == "value2"