"""Unit tests for ContextFieldSelector

Tests the selective field query optimization system including:
- Field set selection
- Field dependency expansion
- Caching behavior
- Performance metrics
- Savings estimation
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from fastmcp.task_management.application.services.context_field_selector import (
    ContextFieldSelector,
    FieldSet
)


class TestContextFieldSelector(unittest.TestCase):
    """Test cases for ContextFieldSelector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.selector = ContextFieldSelector()
    
    def test_task_minimal_fields(self):
        """Test minimal field set for tasks"""
        result = self.selector.get_task_fields("task-123", FieldSet.MINIMAL)

        self.assertEqual(result["entity_type"], "task")
        self.assertEqual(result["entity_id"], "task-123")
        self.assertEqual(set(result["fields"]), {"id", "title", "status", "priority"})
        self.assertTrue(result["optimized"])
    
    def test_task_summary_fields(self):
        """Test summary field set for tasks"""
        result = self.selector.get_task_fields("task-456", FieldSet.SUMMARY)
        
        self.assertEqual(result["entity_type"], "task")
        self.assertEqual(result["entity_id"], "task-456")
        self.assertIn("id", result["fields"])
        self.assertIn("title", result["fields"])
        self.assertIn("status", result["fields"])
        self.assertIn("priority", result["fields"])
        # Check field dependencies are expanded
        self.assertIn("assignee_ids", result["fields"])  # Dependency of assignees
        self.assertTrue(result["optimized"])
    
    def test_task_detail_fields(self):
        """Test detail field set for tasks"""
        result = self.selector.get_task_fields("task-789", FieldSet.DETAIL)
        
        self.assertEqual(result["entity_type"], "task")
        self.assertIn("description", result["fields"])
        self.assertIn("estimated_effort", result["fields"])
        self.assertIn("label_ids", result["fields"])  # Dependency of labels
        self.assertTrue(result["optimized"])
    
    def test_task_full_fields(self):
        """Test full field set for tasks"""
        result = self.selector.get_task_fields("task-999", FieldSet.FULL)
        
        self.assertEqual(result["entity_type"], "task")
        self.assertIsNone(result["fields"])  # Full means all fields
        self.assertFalse(result["optimized"])
    
    def test_task_custom_fields(self):
        """Test custom field list for tasks"""
        custom_fields = ["id", "title", "custom_field"]
        result = self.selector.get_task_fields("task-custom", custom_fields)
        
        self.assertEqual(result["entity_type"], "task")
        self.assertEqual(set(result["fields"]), set(custom_fields))
        self.assertTrue(result["optimized"])
    
    def test_project_field_sets(self):
        """Test all field sets for projects"""
        # Minimal
        result = self.selector.get_project_fields("proj-123", FieldSet.MINIMAL)
        self.assertEqual(set(result["fields"]), {"id", "name", "status"})
        
        # Summary
        result = self.selector.get_project_fields("proj-456", FieldSet.SUMMARY)
        self.assertIn("description", result["fields"])
        self.assertIn("created_at", result["fields"])
        
        # Detail
        result = self.selector.get_project_fields("proj-789", FieldSet.DETAIL)
        self.assertIn("owner", result["fields"])
        self.assertIn("team_member_ids", result["fields"])  # Dependency
    
    def test_context_field_sets(self):
        """Test all field sets for contexts"""
        # Minimal
        result = self.selector.get_context_fields("ctx-123", "task", FieldSet.MINIMAL)
        self.assertEqual(result["entity_type"], "context")
        self.assertEqual(result["level"], "task")
        self.assertEqual(set(result["fields"]), {"id", "level", "data"})
        
        # Detail
        result = self.selector.get_context_fields("ctx-456", "project", FieldSet.DETAIL)
        self.assertIn("metadata", result["fields"])
        self.assertIn("parent_id", result["fields"])
    
    def test_field_dependency_expansion(self):
        """Test that field dependencies are properly expanded"""
        fields = ["assignees", "labels"]
        expanded = self.selector._expand_field_dependencies(fields)
        
        # Original fields should be present
        self.assertIn("assignees", expanded)
        self.assertIn("labels", expanded)
        
        # Dependencies should be added
        self.assertIn("assignee_ids", expanded)
        self.assertIn("label_ids", expanded)
    
    def test_optimal_field_set_selection(self):
        """Test automatic field set selection based on operation"""
        # High-frequency operations
        self.assertEqual(
            self.selector.get_optimal_field_set("list", "task"),
            FieldSet.MINIMAL
        )
        self.assertEqual(
            self.selector.get_optimal_field_set("status", "project"),
            FieldSet.MINIMAL
        )
        
        # Summary operations
        self.assertEqual(
            self.selector.get_optimal_field_set("get", "task"),
            FieldSet.SUMMARY
        )
        self.assertEqual(
            self.selector.get_optimal_field_set("search", "context"),
            FieldSet.SUMMARY
        )
        
        # Detail operations
        self.assertEqual(
            self.selector.get_optimal_field_set("update", "task"),
            FieldSet.DETAIL
        )
        self.assertEqual(
            self.selector.get_optimal_field_set("workflow", "project"),
            FieldSet.DETAIL
        )
        
        # Debug operations
        self.assertEqual(
            self.selector.get_optimal_field_set("debug", "task"),
            FieldSet.FULL
        )
    
    def test_caching_behavior(self):
        """Test field mapping cache"""
        # Cache some data
        self.selector.cache_field_mapping(
            "task-cache",
            ["id", "title", "status"],
            {"id": "task-cache", "title": "Test", "status": "todo"}
        )
        
        # Retrieve cached data
        cached = self.selector.get_cached_fields("task-cache", ["id", "title", "status"])
        self.assertIsNotNone(cached)
        self.assertEqual(cached["id"], "task-cache")
        self.assertEqual(cached["title"], "Test")
        
        # Cache miss for different fields
        cached = self.selector.get_cached_fields("task-cache", ["id", "description"])
        self.assertIsNone(cached)
        
        # Check metrics
        metrics = self.selector.get_metrics()
        self.assertEqual(metrics["cache_hits"], 1)
        self.assertEqual(metrics["cache_misses"], 1)
    
    def test_metrics_tracking(self):
        """Test performance metrics tracking"""
        # Reset metrics
        self.selector.reset_metrics()
        
        # Perform some operations
        self.selector.get_task_fields("task-1", FieldSet.MINIMAL)
        self.selector.get_task_fields("task-2", FieldSet.SUMMARY)
        self.selector.get_project_fields("proj-1", FieldSet.DETAIL)
        
        # Check metrics
        metrics = self.selector.get_metrics()
        self.assertEqual(metrics["queries_optimized"], 3)
        self.assertGreater(metrics["fields_reduced"], 0)
        
        # Reset and verify
        self.selector.reset_metrics()
        metrics = self.selector.get_metrics()
        self.assertEqual(metrics["queries_optimized"], 0)
    
    def test_savings_estimation(self):
        """Test performance savings estimation"""
        # Task minimal savings
        savings = self.selector.estimate_savings("task", FieldSet.MINIMAL)
        self.assertEqual(savings["selected_fields"], 4)
        self.assertEqual(savings["full_fields"], 50)
        self.assertGreater(savings["field_reduction_percent"], 90)
        self.assertGreater(savings["bandwidth_savings_percent"], 80)
        
        # Project summary savings
        savings = self.selector.estimate_savings("project", FieldSet.SUMMARY)
        self.assertEqual(savings["selected_fields"], 5)
        self.assertEqual(savings["full_fields"], 30)
        self.assertGreater(savings["field_reduction_percent"], 80)
        
        # Context full (no savings)
        savings = self.selector.estimate_savings("context", FieldSet.FULL)
        self.assertEqual(savings["field_reduction_percent"], 0)
        self.assertEqual(savings["query_time_savings_percent"], 0)
    
    def test_default_field_set(self):
        """Test default field set when none specified"""
        # Should default to summary
        result = self.selector.get_task_fields("task-default")
        self.assertEqual(len(result["fields"]), len(self.selector.TASK_FIELD_SETS[FieldSet.SUMMARY]) + 2)  # +2 for dependencies (assignee_ids, label_ids)
        
        result = self.selector.get_project_fields("proj-default")
        self.assertEqual(len(result["fields"]), 5)
    
    def test_build_optimized_query(self):
        """Test SQLAlchemy query building"""
        # Mock entity class
        class MockTask:
            id = "id_column"
            title = "title_column"
            status = "status_column"
            unknown = None
        
        # Test with fields
        fields = ["id", "title", "status", "unknown_field"]
        attrs = self.selector.build_optimized_query(MockTask, fields)
        
        # Should return list of attributes (excluding unknown)
        self.assertEqual(len(attrs), 3)
        self.assertEqual(attrs[0], "id_column")
        self.assertEqual(attrs[1], "title_column")
        self.assertEqual(attrs[2], "status_column")
        
        # Test with None (full query)
        result = self.selector.build_optimized_query(MockTask, None)
        self.assertEqual(result, MockTask)


if __name__ == "__main__":
    unittest.main()