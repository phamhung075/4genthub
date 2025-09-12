"""Integration tests for complete MCP optimization system

Tests the full optimization pipeline including:
- Response optimization with profiles
- Context field selection
- Template management
- Cache optimization
- Performance benchmarking
- Metrics collection
"""

import unittest
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path

from fastmcp.task_management.application.services.response_optimizer import (
    ResponseOptimizer, ResponseProfile
)
from fastmcp.task_management.application.services.context_field_selector import (
    ContextFieldSelector, FieldSet
)
from fastmcp.task_management.application.services.context_template_manager import (
    ContextTemplateManager, OperationType
)
from fastmcp.task_management.application.services.context_cache_optimizer import (
    ContextCacheOptimizer, CacheStrategy
)
from fastmcp.task_management.application.services.workflow_hints_simplifier import (
    WorkflowHintsSimplifier
)
from fastmcp.task_management.application.services.performance_benchmarker import (
    PerformanceBenchmarker, BenchmarkCategory
)
from fastmcp.task_management.application.services.metrics_dashboard import (
    MetricsDashboard, MetricType
)


class TestOptimizationIntegration(unittest.TestCase):
    """Integration tests for optimization system"""
    
    def setUp(self):
        """Set up test components"""
        self.response_optimizer = ResponseOptimizer()
        self.field_selector = ContextFieldSelector()
        self.template_manager = ContextTemplateManager()
        self.cache_optimizer = ContextCacheOptimizer(max_size_mb=10)
        self.hints_simplifier = WorkflowHintsSimplifier()
        self.benchmarker = PerformanceBenchmarker()
        self.metrics_dashboard = MetricsDashboard()
        
        # Sample data for testing
        self.sample_response = {
            "status": "success",
            "success": True,
            "operation": "task.create",
            "operation_id": "test-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "data": {
                "task": {
                    "id": "task-456",
                    "title": "Integration Test Task",
                    "status": "todo",
                    "priority": "high",
                    "assignees": ["user1"],
                    "dependencies": [],
                    "progress_percentage": 0
                }
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["Add task description", "Set assignees"],
                    "required_actions": ["Validate task data"]
                },
                "autonomous_guidance": {
                    "confidence": 0.85
                }
            },
            "metadata": {
                "created_by": "user1",
                "context_type": "task"
            }
        }
        
        self.sample_context = {
            "task": {
                "id": "task-456",
                "title": "Test Task",
                "description": "A test task",
                "status": "todo",
                "priority": "high",
                "assignees": ["user1", "user2"],
                "labels": ["test", "integration"],
                "dependencies": ["task-123"],
                "progress_percentage": 25,
                "created_at": "2025-01-01",
                "updated_at": "2025-01-02",
                "metadata": {"category": "test"}
            },
            "project": {
                "id": "proj-789",
                "name": "Test Project",
                "description": "A test project",
                "owner": "user1",
                "status": "active"
            },
            "user": {
                "id": "user1",
                "name": "Test User",
                "preferences": {"theme": "dark"},
                "permissions": ["read", "write"]
            }
        }
    
    def test_complete_optimization_pipeline(self):
        """Test complete optimization pipeline end-to-end"""
        # Step 1: Start benchmark
        suite = self.benchmarker.start_suite("integration_test")
        
        # Step 2: Get template for operation
        template = self.template_manager.get_template(OperationType.TASK_CREATE)
        self.assertIsInstance(template, dict)
        self.assertIn("project", template)
        
        # Step 3: Extract minimal context using template
        minimal_context = self.template_manager.get_minimal_context(
            OperationType.TASK_CREATE,
            self.sample_context
        )
        
        # Should have reduced context
        self.assertIn("project", minimal_context)
        self.assertLess(len(str(minimal_context)), len(str(self.sample_context)))
        
        # Step 4: Optimize response structure
        optimized_response = self.response_optimizer.optimize_response(
            self.sample_response.copy(),
            profile=ResponseProfile.STANDARD
        )
        
        # Should be optimized
        self.assertIn("success", optimized_response)
        self.assertIn("meta", optimized_response)
        self.assertLess(len(str(optimized_response)), len(str(self.sample_response)))
        
        # Step 5: Simplify workflow hints
        if "workflow_guidance" in self.sample_response:
            simplified_hints = self.hints_simplifier.simplify_workflow_guidance(
                self.sample_response["workflow_guidance"]
            )
            self.assertIsInstance(simplified_hints, dict)
        
        # Step 6: Record metrics
        self.metrics_dashboard.record_histogram(
            "response_compression_ratio",
            75.0,  # Example compression ratio
            {"operation": "task.create"}
        )
        
        # Step 7: Complete benchmark
        completed_suite = self.benchmarker.complete_suite()
        self.assertIsNotNone(completed_suite)
        
        # Verify integration
        metrics = self.response_optimizer.get_metrics()
        self.assertGreater(metrics["responses_optimized"], 0)
    
    def test_field_selector_with_templates(self):
        """Test field selector integration with templates"""
        # Get task fields with MINIMAL profile
        task_spec = self.field_selector.get_task_fields("task-123", FieldSet.MINIMAL)
        
        # Get template for the same operation
        template = self.template_manager.get_template(OperationType.TASK_GET)
        
        # Both should work together for optimization
        self.assertIsInstance(task_spec, dict)
        self.assertIsInstance(template, dict)
        
        # Template should specify what contexts are needed
        # Field selector should specify which fields from those contexts
        self.assertEqual(task_spec["entity_type"], "task")
        self.assertTrue(task_spec["optimized"])
    
    def test_cache_integration(self):
        """Test cache integration with other components"""
        # Cache a template result
        template_key = "template_task.create"
        template = self.template_manager.get_template(OperationType.TASK_CREATE)
        
        cached = self.cache_optimizer.put(
            template_key,
            template,
            "template",
            "get_template"
        )
        self.assertTrue(cached)
        
        # Retrieve from cache
        cached_template = self.cache_optimizer.get(template_key, "template")
        self.assertEqual(cached_template, template)
        
        # Cache field selector results
        field_spec_key = "field_spec_task_minimal"
        field_spec = self.field_selector.get_task_fields("task-123", FieldSet.MINIMAL)
        
        cached = self.cache_optimizer.put(
            field_spec_key,
            field_spec,
            "field_spec",
            "get_task_fields"
        )
        self.assertTrue(cached)
        
        # Verify cache stats
        stats = self.cache_optimizer.get_cache_stats()
        self.assertGreater(stats["performance"]["cache_hits"], 0)
        self.assertEqual(stats["storage"]["entries_count"], 2)
    
    def test_performance_benchmarking_integration(self):
        """Test performance benchmarking with all components"""
        suite = self.benchmarker.start_suite("performance_integration_test")
        
        # Benchmark response optimization
        test_responses = [self.sample_response.copy() for _ in range(5)]
        self.benchmarker.benchmark_response_optimization(
            self.response_optimizer,
            test_responses
        )
        
        # Benchmark context selection
        test_contexts = [self.sample_context.copy() for _ in range(3)]
        self.benchmarker.benchmark_context_selection(
            self.field_selector,
            self.template_manager,
            test_contexts
        )
        
        # Benchmark cache performance
        test_cache_data = [(f"key_{i}", {"data": f"value_{i}"}) for i in range(10)]
        self.benchmarker.benchmark_cache_performance(
            self.cache_optimizer,
            test_cache_data
        )
        
        # Complete suite and get report
        completed_suite = self.benchmarker.complete_suite()
        report = self.benchmarker.generate_report(completed_suite)
        
        # Verify report structure
        self.assertIn("summary", report)
        self.assertIn("category_summaries", report)
        self.assertIn("recommendations", report)
        
        # Should have results for each category
        categories = report["category_summaries"]
        self.assertIn("response_optimization", categories)
        self.assertIn("context_selection", categories)
        self.assertIn("cache_performance", categories)
    
    def test_metrics_dashboard_integration(self):
        """Test metrics dashboard with all components"""
        # Record various metrics from different components
        
        # Response optimization metrics
        self.metrics_dashboard.record_histogram(
            "response_compression_ratio", 72.5,
            {"profile": "standard", "operation": "task.create"}
        )
        
        self.metrics_dashboard.record_timer(
            "response_processing_time", 45.2,
            {"profile": "standard"}
        )
        
        # Context optimization metrics  
        self.metrics_dashboard.record_histogram(
            "context_field_reduction", 85.0,
            {"field_set": "minimal", "entity": "task"}
        )
        
        # Cache metrics
        self.metrics_dashboard.set_gauge("cache_hit_rate", 78.5)
        self.metrics_dashboard.set_gauge("cache_size", 1024000)  # 1MB
        self.metrics_dashboard.increment_counter("cache_evictions", 2)
        
        # System metrics
        self.metrics_dashboard.record_timer("api_response_time", 125.0)
        self.metrics_dashboard.set_gauge("memory_usage", 45.2)
        
        # Get dashboard data
        dashboard = self.metrics_dashboard.get_dashboard_data(duration_minutes=60)
        
        # Verify structure
        self.assertIn("metrics", dashboard)
        self.assertIn("summary", dashboard)
        self.assertIn("health_status", dashboard)
        
        # Verify metrics are present
        metrics = dashboard["metrics"]
        self.assertIn("response_compression_ratio", metrics)
        self.assertIn("context_field_reduction", metrics)
        self.assertIn("cache_hit_rate", metrics)
        
        # Verify health status
        health = dashboard["health_status"]
        self.assertIn("status", health)
        self.assertIn("score", health)
    
    def test_workflow_hints_integration(self):
        """Test workflow hints simplifier integration"""
        # Create complex workflow guidance
        complex_guidance = {
            "next_steps": {
                "recommendations": [
                    "You should consider adding a detailed description to this task",
                    "Please make sure to assign the task to appropriate team members",
                    "It would be good to set realistic deadlines for completion"
                ],
                "required_actions": [
                    "Validate all required fields are present",
                    "Check dependencies are resolved"
                ]
            },
            "autonomous_guidance": {
                "confidence": 0.85,
                "recommendations": [
                    "This task appears to be well-structured",
                    "Consider adding labels for better categorization"
                ]
            },
            "validation": {
                "rules": [
                    "Task title must be between 10 and 200 characters",
                    "At least one assignee must be specified",
                    "Priority must be set to high, medium, or low"
                ]
            }
        }
        
        # Simplify the guidance
        simplified = self.hints_simplifier.simplify_workflow_guidance(complex_guidance)
        
        # Should be more concise
        self.assertIn("next", simplified)
        self.assertIn("confidence", simplified)
        
        # Verify simplification metrics
        metrics = self.hints_simplifier.get_metrics()
        self.assertGreater(metrics["hints_processed"], 0)
        self.assertGreater(metrics["words_saved"], 0)
        
        # Create structured hints
        structured_hints = self.hints_simplifier.create_structured_hints(complex_guidance)
        self.assertIsInstance(structured_hints, list)
        self.assertGreater(len(structured_hints), 0)
        
        # Each hint should have proper structure
        for hint in structured_hints:
            self.assertTrue(hasattr(hint, 'type'))
            self.assertTrue(hasattr(hint, 'action'))
            self.assertTrue(hasattr(hint, 'priority'))
    
    def test_optimization_with_different_profiles(self):
        """Test optimization with different response profiles"""
        profiles = [
            ResponseProfile.MINIMAL,
            ResponseProfile.STANDARD, 
            ResponseProfile.DETAILED,
            ResponseProfile.DEBUG
        ]
        
        original_size = len(str(self.sample_response))
        results = {}
        
        for profile in profiles:
            optimized = self.response_optimizer.optimize_response(
                self.sample_response.copy(),
                profile=profile
            )
            
            optimized_size = len(str(optimized))
            compression_ratio = (1 - optimized_size / original_size) * 100
            
            results[profile.value] = {
                "optimized_size": optimized_size,
                "compression_ratio": compression_ratio,
                "has_hints": "hints" in optimized
            }
        
        # Verify profile differences
        self.assertLess(results["minimal"]["optimized_size"], results["standard"]["optimized_size"])
        self.assertLess(results["standard"]["optimized_size"], results["detailed"]["optimized_size"])
        self.assertLess(results["detailed"]["optimized_size"], results["debug"]["optimized_size"])
        
        # DETAILED and DEBUG should have hints
        self.assertTrue(results["detailed"]["has_hints"])
        self.assertTrue(results["debug"]["has_hints"])
    
    def test_error_handling_integration(self):
        """Test error handling across components"""
        # Test with invalid data
        invalid_response = {"invalid": "response"}
        
        # Response optimizer should handle gracefully
        try:
            optimized = self.response_optimizer.optimize_response(invalid_response)
            # Should return something, even if minimal optimization
            self.assertIsInstance(optimized, dict)
        except Exception as e:
            # Or raise a specific error that we can handle
            self.assertIsInstance(e, (ValueError, KeyError))
        
        # Template manager with invalid operation
        try:
            from fastmcp.task_management.application.services.context_template_manager import OperationType
            template = self.template_manager.get_template(OperationType.TASK_CREATE)
            # Should work
            self.assertIsInstance(template, dict)
        except Exception as e:
            self.fail(f"Template manager failed: {e}")
        
        # Cache with oversized data
        large_data = {"data": "x" * 1000000}  # 1MB+ of data
        cached = self.cache_optimizer.put("large_key", large_data, "test")
        # Should handle gracefully (likely reject)
        self.assertIsInstance(cached, bool)
    
    def test_memory_usage_optimization(self):
        """Test memory usage during optimization"""
        import sys
        
        # Measure memory before
        initial_size = sys.getsizeof(self.sample_response)
        
        # Run optimization
        optimized = self.response_optimizer.optimize_response(
            self.sample_response.copy(),
            profile=ResponseProfile.MINIMAL
        )
        
        optimized_size = sys.getsizeof(optimized)
        
        # Should use less memory
        self.assertLess(optimized_size, initial_size)
        
        # Test with context optimization
        minimal_context = self.template_manager.get_minimal_context(
            OperationType.TASK_CREATE,
            self.sample_context
        )
        
        context_size = sys.getsizeof(minimal_context)
        original_context_size = sys.getsizeof(self.sample_context)
        
        self.assertLess(context_size, original_context_size)


if __name__ == "__main__":
    unittest.main()