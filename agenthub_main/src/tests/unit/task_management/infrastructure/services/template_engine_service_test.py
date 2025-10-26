"""Unit tests for template engine infrastructure service"""

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timezone
import json
import hashlib
import time

from fastmcp.task_management.infrastructure.services.template_engine_service import TemplateEngineService
from fastmcp.task_management.domain.entities.template import TemplateResult, TemplateRenderRequest
from fastmcp.task_management.domain.value_objects.template_id import TemplateId
from fastmcp.task_management.domain.exceptions.template_exceptions import (
    TemplateRenderError, 
    TemplateCompilationError
)


class TestTemplateEngineService(unittest.IsolatedAsyncioTestCase):
    """Test suite for TemplateEngineService"""
    
    async def asyncSetUp(self):
        """Set up test dependencies"""
        # Mock registry service
        self.mock_registry_service = Mock()
        self.mock_registry_service.get_template = AsyncMock()
        self.mock_registry_service.suggest_templates = AsyncMock()
        
        # Mock Redis client
        self.mock_redis_client = Mock()
        self.mock_redis_client.get = Mock(return_value=None)
        self.mock_redis_client.setex = Mock()
        self.mock_redis_client.keys = Mock(return_value=[])
        self.mock_redis_client.delete = Mock()
        
        # Mock pybars compiler
        with patch('fastmcp.task_management.infrastructure.services.template_engine_service.pybars'):
            self.service = TemplateEngineService(
                registry_service=self.mock_registry_service,
                redis_client=self.mock_redis_client
            )
            
        # Mock handlebars compiler
        self.mock_compiled_template = Mock(return_value="Rendered content")
        self.service.handlebars = Mock()
        self.service.handlebars.compile = Mock(return_value=self.mock_compiled_template)
    
    @patch('fastmcp.task_management.infrastructure.services.template_engine_service.time')
    async def test_render_template_success(self, mock_time):
        """Test successful template rendering without cache"""
        # Arrange
        mock_time.time.side_effect = [1000.0, 1000.1]  # 100ms difference
        
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={"name": "Test", "value": 123},
            task_context={"project": "TestProject"},
            output_path="/output/test.md",
            force_regenerate=False
        )
        
        self.mock_registry_service.get_template.return_value = {
            'content': 'Hello {{name}}, value is {{value}}!'
        }
        
        # Act
        result = await self.service.render_template(request)
        
        # Assert
        self.assertIsInstance(result, TemplateResult)
        self.assertEqual(result.content, "Rendered content")
        self.assertEqual(result.template_id, template_id)
        self.assertIn("name", result.variables_used)
        self.assertIn("value", result.variables_used)
        self.assertIn("timestamp", result.variables_used)
        self.assertFalse(result.cache_hit)
        self.assertEqual(result.output_path, "/output/test.md")
        self.assertEqual(result.generation_time_ms, 100)  # (1000.1 - 1000.0) * 1000
        
        # Verify metrics updated
        self.assertEqual(self.service.render_count, 1)
        self.assertEqual(self.service.cache_hits, 0)
        self.assertEqual(self.service.total_render_time, 100)
        
    async def test_render_template_cache_hit(self):
        """Test template rendering with cache hit"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={"test": "value"},
            force_regenerate=False
        )
        
        # Mock cached result
        cached_data = {
            'content': 'Cached content',
            'template_id': str(template_id.value),
            'variables_used': {'test': 'value'},
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'generation_time_ms': 50,
            'cache_hit': True,
            'output_path': None
        }
        self.mock_redis_client.get.return_value = json.dumps(cached_data)
        
        # Act
        result = await self.service.render_template(request)
        
        # Assert
        self.assertEqual(result.content, 'Cached content')
        self.assertTrue(result.cache_hit)
        self.assertEqual(self.service.render_count, 1)
        self.assertEqual(self.service.cache_hits, 1)
        
        # Verify registry not called for cached result
        self.mock_registry_service.get_template.assert_not_called()
        
    async def test_render_template_force_regenerate(self):
        """Test template rendering with force regenerate ignores cache"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={"force": True},
            force_regenerate=True
        )
        
        # Mock cached result that should be ignored
        self.mock_redis_client.get.return_value = json.dumps({'content': 'Cached'})
        
        self.mock_registry_service.get_template.return_value = {
            'content': 'Template {{force}}'
        }
        
        # Act
        result = await self.service.render_template(request)
        
        # Assert
        self.assertEqual(result.content, "Rendered content")
        self.assertFalse(result.cache_hit)
        self.assertEqual(self.service.cache_hits, 0)
        
        # Verify cache was not checked
        self.mock_redis_client.get.assert_not_called()
        
    async def test_render_template_not_found(self):
        """Test template rendering when template not found"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={}
        )
        
        self.mock_registry_service.get_template.return_value = None
        
        # Act & Assert
        with self.assertRaises(TemplateRenderError) as context:
            await self.service.render_template(request)
        
        self.assertIn("Template not found", str(context.exception))
        
    async def test_render_template_compilation_error(self):
        """Test template rendering with compilation error"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={}
        )
        
        self.mock_registry_service.get_template.return_value = {
            'content': '{{#invalid}}{{/invalid'
        }
        
        self.service.handlebars.compile.side_effect = Exception("Invalid syntax")
        
        # Act & Assert
        with self.assertRaises(TemplateCompilationError) as context:
            await self.service.render_template(request)
        
        self.assertIn("Template compilation failed", str(context.exception))
        
    async def test_render_template_render_error(self):
        """Test template rendering with render error"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={"test": "value"}
        )
        
        self.mock_registry_service.get_template.return_value = {
            'content': '{{test}}'
        }
        
        # Mock compiled template that throws error
        self.mock_compiled_template.side_effect = Exception("Render error")
        
        # Act & Assert
        with self.assertRaises(TemplateRenderError) as context:
            await self.service.render_template(request)
        
        self.assertIn("Template rendering failed", str(context.exception))
        
    async def test_resolve_variables_hierarchy(self):
        """Test variable resolution with hierarchy"""
        # Arrange
        template_id = "test"
        variables = {"name": "User", "priority": "high"}
        task_context = {"name": "Default", "project": "TestProject", "priority": "low"}
        
        # Act
        resolved = await self.service._resolve_variables(template_id, variables, task_context)
        
        # Assert
        # Request variables should override task context
        self.assertEqual(resolved["name"], "User")
        self.assertEqual(resolved["priority"], "high")
        # Task context variables not overridden
        self.assertEqual(resolved["project"], "TestProject")
        # System variables added
        self.assertIn("timestamp", resolved)
        self.assertIn("template_id", resolved)
        self.assertIn("render_time", resolved)
        
    async def test_compiled_template_caching(self):
        """Test that compiled templates are cached"""
        # Arrange
        template_id = "cached-compilation"
        content = "Template content"
        
        # Act
        compiled1 = await self.service._get_compiled_template(template_id, content)
        compiled2 = await self.service._get_compiled_template(template_id, content)
        
        # Assert
        # Should only compile once
        self.service.handlebars.compile.assert_called_once_with(content)
        # Should return same compiled template
        self.assertIs(compiled1, compiled2)
        self.assertIs(compiled1, self.mock_compiled_template)
        
    async def test_cache_key_generation(self):
        """Test cache key generation is deterministic"""
        # Arrange
        template_id = "test-key"
        variables1 = {"b": 2, "a": 1}
        variables2 = {"a": 1, "b": 2}  # Same vars, different order
        variables3 = {"a": 1, "b": 3}  # Different value
        
        # Act
        key1 = self.service._generate_cache_key(template_id, variables1)
        key2 = self.service._generate_cache_key(template_id, variables2)
        key3 = self.service._generate_cache_key(template_id, variables3)
        
        # Assert
        # Same variables should produce same key regardless of order
        self.assertEqual(key1, key2)
        # Different variables should produce different key
        self.assertNotEqual(key1, key3)
        # Key format check
        self.assertTrue(key1.startswith(f"template:{template_id}:"))
        
    async def test_get_performance_metrics(self):
        """Test performance metrics retrieval"""
        # Arrange - set some metrics
        self.service.render_count = 10
        self.service.cache_hits = 7
        self.service.total_render_time = 500.0
        self.service._compiled_templates = {"t1": Mock(), "t2": Mock()}
        
        # Act
        metrics = await self.service.get_performance_metrics()
        
        # Assert
        self.assertEqual(metrics['render_count'], 10)
        self.assertEqual(metrics['cache_hits'], 7)
        self.assertEqual(metrics['cache_hit_rate'], 0.7)
        self.assertEqual(metrics['total_render_time'], 500.0)
        self.assertEqual(metrics['avg_render_time'], 50.0)
        self.assertEqual(metrics['compiled_templates_count'], 2)
        
    async def test_get_performance_metrics_zero_renders(self):
        """Test performance metrics with zero renders"""
        # Act
        metrics = await self.service.get_performance_metrics()
        
        # Assert
        self.assertEqual(metrics['render_count'], 0)
        self.assertEqual(metrics['cache_hits'], 0)
        self.assertEqual(metrics['cache_hit_rate'], 0.0)
        self.assertEqual(metrics['total_render_time'], 0.0)
        self.assertEqual(metrics['avg_render_time'], 0.0)
        self.assertEqual(metrics['compiled_templates_count'], 0)
        
    async def test_clear_cache_specific_template(self):
        """Test clearing cache for specific template"""
        # Arrange
        template_id = "template-to-clear"
        self.service._compiled_templates = {
            template_id: Mock(),
            "other-template": Mock()
        }
        
        # Act
        await self.service.clear_cache(template_id)
        
        # Assert
        # Specific template removed
        self.assertNotIn(template_id, self.service._compiled_templates)
        # Other template remains
        self.assertIn("other-template", self.service._compiled_templates)
        
        # Redis cache cleared for specific template
        self.mock_redis_client.keys.assert_called_with(f"template:{template_id}:*")
        
    async def test_clear_cache_all(self):
        """Test clearing all cache"""
        # Arrange
        self.service._compiled_templates = {
            "template1": Mock(),
            "template2": Mock()
        }
        
        # Act
        await self.service.clear_cache()
        
        # Assert
        # All compiled templates cleared
        self.assertEqual(len(self.service._compiled_templates), 0)
        
        # Redis cache cleared for all templates
        self.mock_redis_client.keys.assert_called_with("template:*")
        
    async def test_suggest_templates(self):
        """Test template suggestions delegation"""
        # Arrange
        task_context = {"type": "feature"}
        agent_type = "coding-agent"
        file_patterns = ["*.py", "*.js"]
        
        expected_suggestions = [
            {"template_id": "t1", "score": 90},
            {"template_id": "t2", "score": 80}
        ]
        self.mock_registry_service.suggest_templates.return_value = expected_suggestions
        
        # Act
        result = await self.service.suggest_templates(
            task_context=task_context,
            agent_type=agent_type,
            file_patterns=file_patterns
        )
        
        # Assert
        self.assertEqual(result, expected_suggestions)
        self.mock_registry_service.suggest_templates.assert_called_once_with(
            task_context=task_context,
            agent_type=agent_type,
            file_patterns=file_patterns
        )
        
    async def test_suggest_templates_error_handling(self):
        """Test template suggestions with error"""
        # Arrange
        self.mock_registry_service.suggest_templates.side_effect = Exception("DB error")
        
        # Act
        result = await self.service.suggest_templates(
            task_context={},
            agent_type="test"
        )
        
        # Assert
        self.assertEqual(result, [])  # Returns empty list on error
        
    async def test_cache_result_redis_error_handling(self):
        """Test cache result handles Redis errors gracefully"""
        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={}
        )
        result = TemplateResult(
            content="Test",
            template_id=template_id,
            variables_used={},
            generated_at=datetime.now(timezone.utc),
            generation_time_ms=10,
            cache_hit=False,
            output_path=None
        )
        
        # Mock Redis error
        self.mock_redis_client.setex.side_effect = Exception("Redis down")
        
        # Act - should not raise exception
        await self.service._cache_result(request, result)
        
        # Assert
        self.mock_redis_client.setex.assert_called_once()
        
    async def test_check_cache_redis_error_handling(self):
        """Test check cache handles Redis errors gracefully"""
        # Arrange
        request = TemplateRenderRequest(
            template_id=TemplateId.generate_new(),
            variables={}
        )
        
        # Mock Redis error
        self.mock_redis_client.get.side_effect = Exception("Redis down")
        
        # Act
        result = await self.service._check_cache(request)
        
        # Assert
        self.assertIsNone(result)  # Returns None on error
        
    async def test_clear_cache_redis_error_handling(self):
        """Test clear cache handles Redis errors gracefully"""
        # Arrange
        self.mock_redis_client.keys.side_effect = Exception("Redis down")
        
        # Act - should not raise exception
        await self.service.clear_cache()
        
        # Assert
        # Compiled templates still cleared even if Redis fails
        self.assertEqual(len(self.service._compiled_templates), 0)
        
    @patch('fastmcp.task_management.infrastructure.services.template_engine_service.pybars', None)
    async def test_init_without_pybars(self):
        """Test initialization fails without pybars"""
        # Act & Assert
        with self.assertRaises(ImportError) as context:
            TemplateEngineService(
                registry_service=self.mock_registry_service
            )

        self.assertIn("pybars package required", str(context.exception))

    async def test_check_cache_without_redis(self):
        """Test branch 127->144: check cache when redis_client is None"""
        # Create service without Redis client
        with patch('fastmcp.task_management.infrastructure.services.template_engine_service.pybars'):
            service_no_redis = TemplateEngineService(
                registry_service=self.mock_registry_service,
                redis_client=None
            )

        # Arrange
        request = TemplateRenderRequest(
            template_id=TemplateId.generate_new(),
            variables={"test": "value"}
        )

        # Act - branch 127->144: if self.redis_client (False, skips)
        result = await service_no_redis._check_cache(request)

        # Assert
        self.assertIsNone(result)  # Should return None without Redis

    async def test_cache_result_without_redis(self):
        """Test branch 151->exit: cache result when redis_client is None"""
        # Create service without Redis client
        with patch('fastmcp.task_management.infrastructure.services.template_engine_service.pybars'):
            service_no_redis = TemplateEngineService(
                registry_service=self.mock_registry_service,
                redis_client=None
            )

        # Arrange
        template_id = TemplateId.generate_new()
        request = TemplateRenderRequest(
            template_id=template_id,
            variables={"test": "value"}
        )
        result = TemplateResult(
            content="Test content",
            template_id=template_id,
            variables_used={"test": "value"},
            generated_at=datetime.now(timezone.utc),
            generation_time_ms=10,
            cache_hit=False,
            output_path=None
        )

        # Act - branch 151->exit: if self.redis_client (False, exits early)
        await service_no_redis._cache_result(request, result)

        # Assert - should complete without error

    async def test_clear_cache_specific_template_not_in_compiled(self):
        """Test branch 236->240: clear cache when template not in compiled cache"""
        # Arrange
        template_id = "non-existent-template"
        self.service._compiled_templates = {
            "other-template": Mock()
        }

        # Mock Redis with keys to delete
        redis_keys = [b"template:non-existent-template:hash1", b"template:non-existent-template:hash2"]
        self.mock_redis_client.keys.return_value = redis_keys

        # Act - branch 236->240: if template_id in self._compiled_templates (False, skips to line 240)
        await self.service.clear_cache(template_id)

        # Assert
        # Lines 245-247: Redis keys fetched and deleted
        self.mock_redis_client.keys.assert_called_with(f"template:{template_id}:*")
        self.mock_redis_client.delete.assert_called_once_with(*redis_keys)
        # Other templates remain
        self.assertIn("other-template", self.service._compiled_templates)

    async def test_clear_cache_specific_template_no_redis_keys(self):
        """Test branch 240->exit: clear cache when no Redis keys found"""
        # Arrange
        template_id = "template-no-keys"
        self.service._compiled_templates = {template_id: Mock()}

        # Mock Redis with no keys
        self.mock_redis_client.keys.return_value = []  # No keys found

        # Act - branch 240->exit: if keys (False, exits without delete)
        await self.service.clear_cache(template_id)

        # Assert
        # Template removed from compiled cache
        self.assertNotIn(template_id, self.service._compiled_templates)
        # Redis keys checked
        self.mock_redis_client.keys.assert_called_with(f"template:{template_id}:*")
        # Delete not called because no keys found (line 245 condition false)
        self.mock_redis_client.delete.assert_not_called()

    async def test_clear_cache_all_without_redis(self):
        """Test branch 252->exit: clear all cache when redis_client is None"""
        # Create service without Redis client
        with patch('fastmcp.task_management.infrastructure.services.template_engine_service.pybars'):
            service_no_redis = TemplateEngineService(
                registry_service=self.mock_registry_service,
                redis_client=None
            )

        # Arrange
        service_no_redis._compiled_templates = {
            "template1": Mock(),
            "template2": Mock()
        }

        # Act - branch 252->exit: if self.redis_client (False, exits)
        await service_no_redis.clear_cache()  # No template_id = clear all

        # Assert
        # Compiled templates cleared (line 250)
        self.assertEqual(len(service_no_redis._compiled_templates), 0)

    async def test_clear_cache_all_no_redis_keys(self):
        """Test line 257: clear all cache when no Redis keys found"""
        # Arrange
        self.service._compiled_templates = {
            "template1": Mock(),
            "template2": Mock()
        }

        # Mock Redis with no keys
        self.mock_redis_client.keys.return_value = []  # No keys found

        # Act
        await self.service.clear_cache()  # No template_id = clear all

        # Assert
        # Compiled templates cleared (line 250)
        self.assertEqual(len(self.service._compiled_templates), 0)
        # Redis keys checked (line 255)
        self.mock_redis_client.keys.assert_called_with("template:*")
        # Line 257: Delete not called because no keys found (line 256 condition false)
        self.mock_redis_client.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()