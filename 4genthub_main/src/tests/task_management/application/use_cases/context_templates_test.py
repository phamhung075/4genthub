"""
Test Suite for Context Templates System

Tests template management, variable substitution, template application,
and the built-in template registry.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.context_templates import (
    ContextTemplateService,
    TemplateRegistry,
    ContextTemplate,
    TemplateVariable,
    TemplateCategory
)
from fastmcp.task_management.domain.models.unified_context import ContextLevel


class TestTemplateRegistry:
    """Test suite for TemplateRegistry"""
    
    @pytest.fixture
    def registry(self):
        """Create a template registry instance"""
        return TemplateRegistry()
    
    def test_init_loads_builtin_templates(self, registry):
        """Test that built-in templates are loaded on initialization"""
        assert len(registry.templates) > 0
        
        # Check for specific built-in templates
        assert "web_app_react" in registry.templates
        assert "api_fastapi" in registry.templates
        assert "ml_model_training" in registry.templates
        assert "task_feature_impl" in registry.templates
    
    def test_register_template(self, registry):
        """Test registering a new template"""
        template = ContextTemplate(
            id="custom_test",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.PROJECT,
            data_template={"test": "data"},
            author="test_user"
        )
        
        registry.register(template)
        
        assert "custom_test" in registry.templates
        assert registry.templates["custom_test"] == template
    
    def test_get_template(self, registry):
        """Test getting a template by ID"""
        # Get built-in template
        template = registry.get("web_app_react")
        assert template is not None
        assert template.name == "React Web Application"
        
        # Get non-existent template
        assert registry.get("non_existent") is None
    
    def test_list_by_category(self, registry):
        """Test listing templates by category"""
        web_templates = registry.list_by_category(TemplateCategory.WEB_APP)
        assert len(web_templates) > 0
        assert all(t.category == TemplateCategory.WEB_APP for t in web_templates)
        
        api_templates = registry.list_by_category(TemplateCategory.API_SERVICE)
        assert len(api_templates) > 0
        assert all(t.category == TemplateCategory.API_SERVICE for t in api_templates)
    
    def test_list_by_level(self, registry):
        """Test listing templates by context level"""
        project_templates = registry.list_by_level(ContextLevel.PROJECT)
        assert len(project_templates) > 0
        assert all(t.level == ContextLevel.PROJECT for t in project_templates)
        
        task_templates = registry.list_by_level(ContextLevel.TASK)
        assert len(task_templates) > 0
        assert all(t.level == ContextLevel.TASK for t in task_templates)
    
    def test_search_by_tags(self, registry):
        """Test searching templates by tags"""
        react_templates = registry.search_by_tags(["react"])
        assert len(react_templates) > 0
        assert all("react" in t.tags for t in react_templates)
        
        python_templates = registry.search_by_tags(["python"])
        assert len(python_templates) > 0
        assert all("python" in t.tags for t in python_templates)
    
    def test_builtin_template_structure(self, registry):
        """Test structure of built-in templates"""
        react_template = registry.get("web_app_react")
        
        assert react_template is not None
        assert react_template.category == TemplateCategory.WEB_APP
        assert react_template.level == ContextLevel.PROJECT
        assert len(react_template.variables) > 0
        assert "project_type" in react_template.data_template
        assert "framework" in react_template.data_template
        
        # Check variables
        var_names = [v.name for v in react_template.variables]
        assert "coverage_threshold" in var_names
        assert "ui_library" in var_names
        assert "state_management" in var_names


class TestContextTemplateService:
    """Test suite for ContextTemplateService"""
    
    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service"""
        service = Mock()
        service.create_context = AsyncMock()
        service.update_context = AsyncMock()
        service.get_context = AsyncMock()
        return service
    
    @pytest.fixture
    def template_service(self, mock_context_service):
        """Create template service instance"""
        return ContextTemplateService(mock_context_service)
    
    def test_list_templates_all(self, template_service):
        """Test listing all templates"""
        templates = template_service.list_templates()
        assert len(templates) > 0
        
        # Check template format
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "level" in template
            assert "tags" in template
            assert "variables" in template
    
    def test_list_templates_filtered(self, template_service):
        """Test listing templates with filters"""
        # Filter by category
        web_templates = template_service.list_templates(
            category=TemplateCategory.WEB_APP
        )
        assert all(t["category"] == "web_app" for t in web_templates)
        
        # Filter by level
        project_templates = template_service.list_templates(
            level=ContextLevel.PROJECT
        )
        assert all(t["level"] == "project" for t in project_templates)
        
        # Filter by tags
        react_templates = template_service.list_templates(
            tags=["react"]
        )
        assert all("react" in t["tags"] for t in react_templates)
    
    def test_template_to_dict(self, template_service):
        """Test template to dictionary conversion"""
        template = ContextTemplate(
            id="test",
            name="Test",
            description="Test template",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.PROJECT,
            data_template={"key": "value"},
            author="author",
            variables=[
                TemplateVariable(
                    name="var1",
                    description="Variable 1",
                    default_value="default",
                    required=True
                )
            ],
            tags=["test"],
            usage_count=5,
            version="1.0.0"
        )
        
        result = template_service._template_to_dict(template)
        
        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert result["category"] == "custom"
        assert result["level"] == "project"
        assert len(result["variables"]) == 1
        assert result["variables"][0]["name"] == "var1"
        assert result["usage_count"] == 5
        assert result["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_apply_template_success(self, template_service, mock_context_service):
        """Test successful template application"""
        mock_context_service.create_context.return_value = {
            "id": "new_project",
            "success": True
        }
        
        result = await template_service.apply_template(
            template_id="web_app_react",
            context_id="new_project",
            user_id="user1",
            variables={
                "coverage_threshold": 90,
                "ui_library": "Material-UI",
                "state_management": "Redux"
            },
            project_id="proj_123"
        )
        
        assert result["success"] is True
        
        # Verify context was created with substituted variables
        create_call = mock_context_service.create_context.call_args
        assert create_call.kwargs["context_level"] == ContextLevel.PROJECT
        assert create_call.kwargs["context_id"] == "new_project"
        
        # Check variable substitution
        created_data = create_call.kwargs["data"]
        assert created_data["testing"]["coverage_threshold"] == 90
        assert created_data["dependencies"]["ui_library"] == "Material-UI"
        assert created_data["dependencies"]["state_management"] == "Redux"
    
    @pytest.mark.asyncio
    async def test_apply_template_not_found(self, template_service):
        """Test applying non-existent template"""
        with pytest.raises(ValueError, match="Template not found"):
            await template_service.apply_template(
                template_id="non_existent",
                context_id="test",
                user_id="user1"
            )
    
    @pytest.mark.asyncio
    async def test_apply_template_missing_required_variable(self, template_service):
        """Test applying template without required variables"""
        # Create template with required variable
        template = ContextTemplate(
            id="test_required",
            name="Test Required",
            description="Test",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.PROJECT,
            data_template={"db": "{{database_type}}"},
            author="test",
            variables=[
                TemplateVariable(
                    name="database_type",
                    description="Database type",
                    default_value=None,
                    required=True
                )
            ]
        )
        
        template_service.registry.register(template)
        
        with pytest.raises(ValueError, match="Required variable not provided"):
            await template_service.apply_template(
                template_id="test_required",
                context_id="test",
                user_id="user1",
                variables={}  # Missing required variable
            )
    
    def test_apply_variables(self, template_service):
        """Test variable substitution logic"""
        template = ContextTemplate(
            id="test",
            name="Test",
            description="Test",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.PROJECT,
            data_template={
                "string_var": "{{string_var}}",
                "number_var": "{{number_var}}",
                "bool_var": "{{bool_var}}",
                "nested": {
                    "value": "{{nested_var}}"
                }
            },
            author="test",
            variables=[
                TemplateVariable("string_var", "String", "default_string"),
                TemplateVariable("number_var", "Number", 42),
                TemplateVariable("bool_var", "Boolean", True),
                TemplateVariable("nested_var", "Nested", "nested_value")
            ]
        )
        
        variables = {
            "string_var": "custom_string",
            "number_var": 100,
            "bool_var": False
            # nested_var will use default
        }
        
        result = template_service._apply_variables(template, variables)
        
        assert result["string_var"] == "custom_string"
        assert result["number_var"] == 100
        assert result["bool_var"] is False
        assert result["nested"]["value"] == "nested_value"  # Used default
    
    @pytest.mark.asyncio
    async def test_apply_template_with_metadata(self, template_service, mock_context_service):
        """Test that template metadata is added to context"""
        mock_context_service.create_context.return_value = {"success": True}
        
        result = await template_service.apply_template(
            template_id="api_fastapi",
            context_id="new_api",
            user_id="user1"
        )
        
        # Check that template metadata was added
        create_call = mock_context_service.create_context.call_args
        created_data = create_call.kwargs["data"]
        
        assert "_template" in created_data
        assert created_data["_template"]["id"] == "api_fastapi"
        assert created_data["_template"]["name"] == "FastAPI Service"
        assert "applied_at" in created_data["_template"]
    
    @pytest.mark.asyncio
    async def test_apply_template_updates_usage_stats(self, template_service, mock_context_service):
        """Test that template usage statistics are updated"""
        mock_context_service.create_context.return_value = {"success": True}
        
        template = template_service.registry.get("web_app_react")
        initial_count = template.usage_count
        initial_last_used = template.last_used_at
        
        await template_service.apply_template(
            template_id="web_app_react",
            context_id="test",
            user_id="user1"
        )
        
        assert template.usage_count == initial_count + 1
        assert template.last_used_at is not None
        if initial_last_used:
            assert template.last_used_at > initial_last_used
    
    def test_create_custom_template(self, template_service):
        """Test creating a custom template"""
        template = template_service.create_custom_template(
            name="Custom API",
            description="Custom API template",
            level=ContextLevel.PROJECT,
            data_template={
                "type": "api",
                "port": "{{port}}",
                "features": ["auth", "logging"]
            },
            variables=[
                TemplateVariable(
                    name="port",
                    description="API port",
                    default_value=8080
                )
            ],
            tags=["api", "custom"]
        )
        
        assert template.id.startswith("custom_")
        assert template.name == "Custom API"
        assert template.category == TemplateCategory.CUSTOM
        assert template.level == ContextLevel.PROJECT
        assert len(template.variables) == 1
        assert template.tags == ["api", "custom"]
        
        # Verify it was registered
        assert template_service.registry.get(template.id) == template
    
    def test_export_template(self, template_service):
        """Test exporting template as JSON"""
        json_str = template_service.export_template("web_app_react")
        
        data = json.loads(json_str)
        assert data["id"] == "web_app_react"
        assert data["name"] == "React Web Application"
        assert "data_template" in data
        assert "variables" in data
        assert len(data["variables"]) > 0
    
    def test_export_template_not_found(self, template_service):
        """Test exporting non-existent template"""
        with pytest.raises(ValueError, match="Template not found"):
            template_service.export_template("non_existent")
    
    def test_import_template(self, template_service):
        """Test importing template from JSON"""
        export_data = {
            "id": "imported_template",
            "name": "Imported Template",
            "description": "An imported template",
            "category": "custom",
            "level": "project",
            "data_template": {
                "key": "{{value}}"
            },
            "variables": [
                {
                    "name": "value",
                    "description": "A value",
                    "default_value": "default",
                    "required": False
                }
            ],
            "tags": ["imported"],
            "version": "1.0.0",
            "author": "importer"
        }
        
        json_str = json.dumps(export_data)
        template = template_service.import_template(json_str)
        
        assert template.id == "imported_template"
        assert template.name == "Imported Template"
        assert template.category == TemplateCategory.CUSTOM
        assert len(template.variables) == 1
        assert template.variables[0].name == "value"
        
        # Verify it was registered
        assert template_service.registry.get("imported_template") == template
    
    def test_import_template_invalid_json(self, template_service):
        """Test importing invalid JSON"""
        with pytest.raises(json.JSONDecodeError):
            template_service.import_template("invalid json")
    
    @pytest.mark.asyncio
    async def test_template_variable_validation(self, template_service):
        """Test template variable validation"""
        template = ContextTemplate(
            id="test_validation",
            name="Test Validation",
            description="Test",
            category=TemplateCategory.CUSTOM,
            level=ContextLevel.PROJECT,
            data_template={"email": "{{email}}"},
            author="test",
            variables=[
                TemplateVariable(
                    name="email",
                    description="Email address",
                    default_value=None,
                    required=True,
                    validation_regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                )
            ]
        )
        
        template_service.registry.register(template)
        
        # For now, regex validation is stored but not enforced
        # This test documents the expected structure
        assert template.variables[0].validation_regex is not None
    
    def test_ml_template_structure(self, template_service):
        """Test ML model template has proper structure"""
        ml_template = template_service.registry.get("ml_model_training")
        
        assert ml_template is not None
        assert ml_template.category == TemplateCategory.ML_MODEL
        assert "model_type" in ml_template.data_template
        assert "training" in ml_template.data_template
        assert "experiment_tracking" in ml_template.data_template
        
        # Check ML-specific variables
        var_names = [v.name for v in ml_template.variables]
        assert "ml_framework" in var_names
        assert "optimizer" in var_names
        assert "loss_function" in var_names


class TestTemplateVariables:
    """Test suite for TemplateVariable functionality"""
    
    def test_template_variable_creation(self):
        """Test creating template variables"""
        var = TemplateVariable(
            name="test_var",
            description="A test variable",
            default_value="default",
            required=True,
            validation_regex=r"^\w+$"
        )
        
        assert var.name == "test_var"
        assert var.description == "A test variable"
        assert var.default_value == "default"
        assert var.required is True
        assert var.validation_regex == r"^\w+$"
    
    def test_template_variable_optional(self):
        """Test optional template variables"""
        var = TemplateVariable(
            name="optional_var",
            description="Optional",
            default_value=None
        )
        
        assert var.required is False
        assert var.validation_regex is None