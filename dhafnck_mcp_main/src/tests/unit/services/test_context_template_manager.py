"""Unit tests for ContextTemplateManager

Tests the context template system including:
- Template retrieval and caching
- Template inheritance
- Custom template loading
- Minimal context extraction
- Performance metrics
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any

from fastmcp.task_management.application.services.context_template_manager import (
    ContextTemplateManager,
    OperationType
)


class TestContextTemplateManager(unittest.TestCase):
    """Test cases for ContextTemplateManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ContextTemplateManager()
        
        # Sample context data for testing
        self.sample_data = {
            "task": {
                "id": "task-123",
                "title": "Test Task",
                "description": "A test task",
                "status": "todo",
                "priority": "high",
                "assignees": ["user1", "user2"],
                "labels": ["bug", "urgent"],
                "dependencies": ["task-456"],
                "progress_percentage": 50,
                "created_at": "2025-01-01",
                "updated_at": "2025-01-02"
            },
            "project": {
                "id": "proj-789",
                "name": "Test Project",
                "description": "A test project",
                "workflow_rules": {"auto_assign": True},
                "completion_rules": {"require_review": True},
                "default_priority": "medium"
            },
            "user": {
                "id": "user-999",
                "preferences": {"theme": "dark"},
                "permissions": ["read", "write"],
                "search_history": ["bug", "feature"],
                "saved_filters": {"my_tasks": {"assignee": "user-999"}}
            }
        }
    
    def test_get_default_template(self):
        """Test retrieving default templates"""
        template = self.manager.get_template(OperationType.TASK_CREATE)
        
        self.assertIn("project", template)
        self.assertIn("git_branch", template)
        self.assertIn("user", template)
        
        # Check specific fields
        self.assertIn("id", template["project"])
        self.assertIn("name", template["project"])
        self.assertIn("default_priority", template["project"])
    
    def test_template_override(self):
        """Test template field override"""
        override = {
            "project": ["id"],  # Only need project ID
            "user": ["*"]  # Need all user fields
        }
        
        template = self.manager.get_template(OperationType.TASK_CREATE, override)
        
        self.assertEqual(template["project"], ["id"])
        self.assertEqual(template["user"], ["*"])
        # Other fields should remain from default
        self.assertIn("git_branch", template)
    
    def test_template_inheritance(self):
        """Test template inheritance for similar operations"""
        # Subtask operations should inherit from task operations
        subtask_template = self.manager.get_template(OperationType.SUBTASK_CREATE)
        task_template = self.manager.get_template(OperationType.TASK_CREATE)
        
        # Should have parent_task specific field
        self.assertIn("parent_task", subtask_template)
        
        # Should also inherit some task fields
        if "project" in task_template:
            self.assertIn("project", subtask_template)
    
    def test_get_minimal_context(self):
        """Test extracting minimal context based on template"""
        minimal = self.manager.get_minimal_context(
            OperationType.TASK_LIST,
            self.sample_data
        )
        
        # Should only include fields specified in template
        template = self.manager.get_template(OperationType.TASK_LIST)
        
        if "user" in minimal and "user" in template:
            user_fields = template["user"]
            for field in minimal["user"]:
                self.assertIn(field, user_fields)
        
        # Should not include all available fields
        if "task" in self.sample_data and "task" not in template:
            self.assertNotIn("task", minimal)
    
    def test_all_fields_wildcard(self):
        """Test handling of '*' wildcard for all fields"""
        template = self.manager.get_template(OperationType.TASK_GET)
        
        # TASK_GET should include all task fields
        self.assertEqual(template["task"], ["*"])
        
        # When extracting minimal context with wildcard
        minimal = self.manager.get_minimal_context(
            OperationType.TASK_GET,
            self.sample_data
        )
        
        if "task" in minimal:
            # Should include all fields from source
            self.assertEqual(minimal["task"], self.sample_data["task"])
    
    def test_custom_template_loading(self):
        """Test loading custom templates from YAML"""
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            custom_templates = {
                "version": "2.0.0",
                "templates": {
                    "task.create": {
                        "custom_context": ["field1", "field2"]
                    }
                }
            }
            yaml.dump(custom_templates, f)
            temp_path = f.name
        
        try:
            # Load custom templates
            manager = ContextTemplateManager(temp_path)
            
            # Check version updated
            self.assertEqual(manager.template_version, "2.0.0")
            
            # Check custom template loaded
            template = manager.get_template(OperationType.TASK_CREATE)
            self.assertIn("custom_context", template)
            self.assertEqual(template["custom_context"], ["field1", "field2"])
        finally:
            # Clean up
            Path(temp_path).unlink()
    
    def test_template_validation(self):
        """Test template validation"""
        # Should be valid if all required contexts present
        valid = self.manager.validate_template(
            OperationType.TASK_CREATE,
            ["project", "user"]
        )
        self.assertTrue(valid)
        
        # Should be invalid if required context missing
        invalid = self.manager.validate_template(
            OperationType.TASK_CREATE,
            ["nonexistent_context"]
        )
        self.assertFalse(invalid)
    
    def test_suggest_improvements(self):
        """Test template improvement suggestions"""
        actual_usage = {
            "project": ["id"],  # Only using ID
            "user": ["id", "unknown_field"],  # Using unknown field
            "git_branch": ["id", "name", "status"]  # Using all fields
        }
        
        suggestions = self.manager.suggest_template_improvements(
            OperationType.TASK_CREATE,
            actual_usage
        )
        
        # Should identify unused fields
        if "project" in suggestions["unused_fields"]:
            unused_project = suggestions["unused_fields"]["project"]
            self.assertIn("name", unused_project)  # name is in template but not used
        
        # Should identify missing fields
        if "user" in suggestions["missing_fields"]:
            missing_user = suggestions["missing_fields"]["user"]
            self.assertIn("unknown_field", missing_user)
        
        # Should calculate optimization potential
        self.assertGreater(suggestions["optimization_potential"], 0)
    
    def test_caching(self):
        """Test template caching"""
        # First call should miss cache
        template1 = self.manager.get_template(OperationType.TASK_CREATE)
        initial_hits = self.manager.get_metrics()["cache_hits"]
        
        # Second call should hit cache
        template2 = self.manager.get_template(OperationType.TASK_CREATE)
        after_hits = self.manager.get_metrics()["cache_hits"]
        
        self.assertEqual(template1, template2)
        self.assertEqual(after_hits, initial_hits + 1)
        
        # Different operation should miss cache
        template3 = self.manager.get_template(OperationType.TASK_UPDATE)
        self.assertNotEqual(template1, template3)
    
    def test_metrics_tracking(self):
        """Test metrics tracking"""
        self.manager.reset_metrics()
        
        # Perform some operations
        self.manager.get_template(OperationType.TASK_CREATE)
        self.manager.get_minimal_context(OperationType.TASK_LIST, self.sample_data)
        
        metrics = self.manager.get_metrics()
        self.assertGreater(metrics["templates_used"], 0)
        self.assertGreater(metrics["fields_requested"], 0)
    
    def test_estimate_savings(self):
        """Test savings estimation"""
        self.manager.reset_metrics()
        
        # Perform operations that save fields
        self.manager.get_minimal_context(OperationType.TASK_LIST, self.sample_data)
        
        savings = self.manager.estimate_savings()
        
        # Should have some savings
        self.assertIn("field_reduction_percent", savings)
        self.assertIn("estimated_time_savings_ms", savings)
        self.assertIn("estimated_bandwidth_savings_kb", savings)
        
        # With minimal template, should have high reduction
        if self.manager._metrics["fields_saved"] > 0:
            self.assertGreater(savings["field_reduction_percent"], 0)
    
    def test_all_operations_have_templates(self):
        """Test that all operations have defined templates"""
        for op in OperationType:
            template = self.manager.get_template(op)
            self.assertIsNotNone(template, f"No template for {op.value}")
            self.assertIsInstance(template, dict)
    
    def test_save_templates(self):
        """Test saving templates to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "templates.yaml"
            
            self.manager.save_templates(str(output_path))
            
            # Check file created
            self.assertTrue(output_path.exists())
            
            # Load and verify
            with open(output_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            self.assertIn("version", saved_data)
            self.assertIn("templates", saved_data)
            self.assertEqual(saved_data["version"], self.manager.template_version)
    
    def test_get_all_operations(self):
        """Test getting list of all operations"""
        operations = self.manager.get_all_operations()
        
        self.assertIsInstance(operations, list)
        self.assertGreater(len(operations), 30)  # Should have 30+ operations
        self.assertIn("task.create", operations)
        self.assertIn("task.update", operations)
        self.assertIn("project.create", operations)


if __name__ == "__main__":
    unittest.main()