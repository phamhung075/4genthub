"""
Unit tests for TemplateRegistryService

Tests the template registry service's current behavior, which raises RuntimeError
indicating PostgreSQL refactoring is needed.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from fastmcp.task_management.infrastructure.services.template_registry_service import (
    TemplateRegistryService,
)


class TestTemplateRegistryService:
    """Test cases for TemplateRegistryService"""
    
    def test_init_raises_runtime_error(self):
        """Test that initialization raises RuntimeError for PostgreSQL refactoring"""
        with pytest.raises(RuntimeError) as exc_info:
            TemplateRegistryService()
        
        assert "Template Registry Service requires refactoring" in str(exc_info.value)
        assert "PostgreSQL implementation is in progress" in str(exc_info.value)
        assert "Use PostgreSQL with SQLAlchemy ORM" in str(exc_info.value)
    
    def test_init_with_db_path_raises_runtime_error(self):
        """Test that initialization with db_path still raises RuntimeError"""
        with pytest.raises(RuntimeError) as exc_info:
            TemplateRegistryService(db_path=Path("/some/path"))
        
        assert "Template Registry Service requires refactoring" in str(exc_info.value)
    
    def test_get_connection_raises_runtime_error(self):
        """Test that _get_connection raises RuntimeError"""
        # We need to create an instance without calling __init__
        service = object.__new__(TemplateRegistryService)
        
        with pytest.raises(RuntimeError) as exc_info:
            service._get_connection()
        
        assert "PostgreSQL connection implementation required" in str(exc_info.value)
        assert "Use PostgreSQL connection pool instead" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_template_requires_connection(self):
        """Test that get_template requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.get_template("template_id")
        assert result is None  # Should return None due to exception
    
    @pytest.mark.asyncio
    async def test_list_templates_requires_connection(self):
        """Test that list_templates requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.list_templates()
        assert result == []  # Should return empty list due to exception
    
    @pytest.mark.asyncio
    async def test_suggest_templates_handles_missing_connection(self):
        """Test that suggest_templates handles missing connection gracefully"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock list_templates to return empty list
        service.list_templates = Mock(return_value=[])
        
        result = await service.suggest_templates(
            task_context={"task_type": "test"},
            agent_type="test-agent",
            file_patterns=["*.py"]
        )
        
        assert result == []  # Should return empty list when no templates available
    
    @pytest.mark.asyncio
    async def test_track_usage_requires_connection(self):
        """Test that track_usage requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        # Should not raise exception, just log error
        await service.track_usage(
            template_id="test_template",
            task_id="task_123",
            project_id="proj_123",
            agent_name="test-agent",
            variables_used={"var1": "value1"},
            output_path="/path/to/output",
            generation_time_ms=100,
            cache_hit=True
        )
        
        # Verify _get_connection was called
        service._get_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_template_analytics_requires_connection(self):
        """Test that get_template_analytics requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.get_template_analytics()
        
        assert "error" in result  # Should return error dict
    
    @pytest.mark.asyncio
    async def test_register_template_requires_connection(self):
        """Test that register_template requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.register_template(
            template_id="test_id",
            name="Test Template",
            description="Test Description",
            content="Template content",
            template_type="test_type",
            agent_compatibility="all",
            file_patterns=["*.py"],
            variables=["var1", "var2"],
            priority="high"
        )
        
        assert result is False  # Should return False due to exception
    
    @pytest.mark.asyncio
    async def test_update_template_requires_connection(self):
        """Test that update_template requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.update_template(
            template_id="test_id",
            updates={
                "name": "Updated Template",
                "description": "Updated description"
            }
        )
        
        assert result is False  # Should return False due to exception
    
    @pytest.mark.asyncio
    async def test_delete_template_requires_connection(self):
        """Test that delete_template requires PostgreSQL connection"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_connection to raise the expected error
        service._get_connection = Mock(side_effect=RuntimeError("PostgreSQL connection implementation required"))
        
        result = await service.delete_template("test_id")
        
        assert result is False  # Should return False due to exception
    
    def test_patterns_match(self):
        """Test pattern matching logic"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Test exact match
        assert service._patterns_match("*.py", "*.py") is True
        
        # Test containment
        assert service._patterns_match("*.py", "**/*.py") is True
        assert service._patterns_match("**/*.py", "*.py") is True
        
        # Test no match - the method returns a set intersection, not boolean
        # An empty set is falsy but not False
        assert bool(service._patterns_match("*.js", "*.py")) is False
    
    def test_extract_pattern_components(self):
        """Test pattern component extraction"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Test extension extraction
        components = service._extract_pattern_components("*.py")
        assert "py" in components
        
        # Test directory extraction
        components = service._extract_pattern_components("src/test/*.js")
        assert "src" in components
        assert "test" in components
        assert "js" in components
        
        # Test wildcard patterns are excluded
        components = service._extract_pattern_components("**/test/*")
        assert "test" in components
        assert "**" not in components
        assert "*" not in components
    
    @pytest.mark.asyncio
    async def test_calculate_template_score(self):
        """Test template scoring calculation"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        # Mock _get_usage_score and _calculate_pattern_score to be async
        async def mock_usage_score(template_id):
            return 10.0
            
        async def mock_pattern_score(template_id, patterns):
            return 15.0
            
        service._get_usage_score = mock_usage_score
        service._calculate_pattern_score = mock_pattern_score
        
        template = {
            "id": "test_id",
            "agent_compatibility": "all",
            "template_type": "test_type",
            "priority": "high"
        }
        
        task_context = {
            "task_type": "test_type"
        }
        
        score = await service._calculate_template_score(
            template=template,
            task_context=task_context,
            agent_type="test-agent",
            file_patterns=["*.py"]
        )
        
        # Base score (10) + agent compat (20) + type match (40) + usage (10) + pattern (15) + priority (15) = 110
        assert score == 110.0
    
    @pytest.mark.asyncio
    async def test_get_suggestion_reason(self):
        """Test suggestion reason generation"""
        # Create instance without __init__
        service = object.__new__(TemplateRegistryService)
        
        template = {
            "template_type": "test_type",
            "agent_compatibility": "all"
        }
        
        task_context = {
            "task_type": "test_type"
        }
        
        # Test perfect match
        reason = await service._get_suggestion_reason(template, task_context, 60)
        assert "Perfect match for test_type tasks" in reason
        assert "Highly popular template" in reason
        
        # Test commonly used
        reason = await service._get_suggestion_reason(template, task_context, 35)
        assert "Commonly used template" in reason
        
        # Test default reason
        template["template_type"] = "other_type"
        del template["agent_compatibility"]  # Remove to trigger default case
        reason = await service._get_suggestion_reason(template, task_context, 20)
        assert "Good general-purpose template" in reason