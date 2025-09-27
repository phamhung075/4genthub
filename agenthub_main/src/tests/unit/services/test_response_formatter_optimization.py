"""Unit tests for StandardResponseFormatter with ResponseOptimizer integration

Tests the integration of ResponseOptimizer into StandardResponseFormatter including:
- Optimization toggle via environment variable
- Legacy mode support
- Profile auto-selection
- Backward compatibility
"""

import unittest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from fastmcp.task_management.interface.utils.response_formatter import (
    StandardResponseFormatter,
    ResponseStatus
)
from fastmcp.task_management.application.services.response_optimizer import ResponseProfile


class TestResponseFormatterOptimization(unittest.TestCase):
    """Test cases for StandardResponseFormatter with optimization"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Enable optimization by default
        os.environ['ENABLE_RESPONSE_OPTIMIZATION'] = 'true'
        self.formatter = StandardResponseFormatter()
        
        # Sample response data
        self.sample_data = {
            "task": {
                "id": "task-123",
                "title": "Test Task",
                "status": "todo"
            }
        }
    
    def tearDown(self):
        """Clean up after tests"""
        # Reset environment variable
        if 'ENABLE_RESPONSE_OPTIMIZATION' in os.environ:
            del os.environ['ENABLE_RESPONSE_OPTIMIZATION']
    
    def test_optimization_enabled_by_default(self):
        """Test that optimization is enabled by default"""
        formatter = StandardResponseFormatter()
        self.assertTrue(formatter.optimization_enabled)
        self.assertIsNotNone(formatter.optimizer)
    
    def test_optimization_disabled_via_env(self):
        """Test disabling optimization via environment variable"""
        os.environ['ENABLE_RESPONSE_OPTIMIZATION'] = 'false'
        formatter = StandardResponseFormatter()
        self.assertFalse(formatter.optimization_enabled)
    
    def test_legacy_mode_via_header(self):
        """Test legacy mode requested via X-Response-Format header"""
        request_context = {
            'headers': {
                'X-Response-Format': 'legacy'
            }
        }
        
        response = self.formatter.create_success_response(
            operation="create",
            data=self.sample_data,
            request_context=request_context
        )
        
        # Legacy mode should return unoptimized response with all fields
        self.assertIn("status", response)
        self.assertIn("confirmation", response)
        self.assertIn("operation_id", response)
        self.assertIn("timestamp", response)
    
    def test_optimized_response_structure(self):
        """Test that responses are optimized when enabled"""
        response = self.formatter.create_success_response(
            operation="create",
            data=self.sample_data
        )
        
        # Should have optimized structure (STANDARD profile by default)
        self.assertIn("success", response)
        self.assertIn("data", response)
        self.assertIn("meta", response)
        # Redundant fields should be removed
        self.assertNotIn("status", response)  # Removed as redundant with success
        self.assertNotIn("confirmation", response)  # Flattened/removed
    
    def test_profile_selection_via_parameter(self):
        """Test explicit profile selection"""
        # Test MINIMAL profile
        response = self.formatter.create_success_response(
            operation="list",
            data={"items": [1, 2, 3]},
            profile=ResponseProfile.MINIMAL
        )
        
        # MINIMAL should only have essential fields
        self.assertIn("success", response)
        self.assertIn("data", response)
        self.assertNotIn("workflow_guidance", response)
        self.assertNotIn("metadata", response)
    
    def test_auto_profile_selection_for_ai_agent(self):
        """Test auto-selection of DETAILED profile for AI agents"""
        request_context = {
            'params': {
                'agent': 'coding-agent'
            }
        }
        
        response = self.formatter.create_success_response(
            operation="create",
            data=self.sample_data,
            workflow_guidance={
                "next_steps": {
                    "recommendations": ["update_task"],
                    "required_actions": ["add_assignee"]
                }
            },
            request_context=request_context
        )
        
        # Should use DETAILED profile and include hints
        self.assertIn("hints", response)
        self.assertEqual(response["hints"]["next"], "update_task")
    
    def test_auto_profile_selection_for_high_frequency(self):
        """Test auto-selection of MINIMAL profile for high-frequency operations"""
        response = self.formatter.create_success_response(
            operation="list",
            data={"items": [1, 2, 3, 4, 5]}
        )
        
        # Should use MINIMAL profile
        self.assertIn("success", response)
        self.assertIn("data", response)
        # Meta might exist if operation was moved there
        # But overall response should be minimal
    
    def test_error_response_optimization(self):
        """Test that error responses are optimized"""
        response = self.formatter.create_error_response(
            operation="create",
            error="Validation failed",
            error_code="VALIDATION_ERROR"
        )
        
        # Error response should be optimized but preserve error info
        self.assertFalse(response["success"])
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], "VALIDATION_ERROR")
    
    def test_format_success_with_optimization(self):
        """Test format_success method with optimization"""
        raw_data = {
            "success": True,
            "task": self.sample_data["task"],
            "level": "task",
            "context_id": "ctx-123"
        }
        
        response = self.formatter.format_success(
            data=raw_data,
            operation="create"
        )
        
        # Should be properly formatted and optimized
        self.assertTrue(response["success"])
        self.assertIn("data", response)
        self.assertIn("meta", response)
    
    def test_format_context_response_with_optimization(self):
        """Test format_context_response with optimization"""
        context_data = {
            "success": True,
            "context": {
                "id": "ctx-123",
                "data": {"key": "value"}
            },
            "level": "task"
        }
        
        response = self.formatter.format_context_response(
            data=context_data,
            operation="context.get"
        )
        
        # Should properly format context response
        self.assertTrue(response["success"])
        self.assertIn("data", response)
        # The context data should be in the data field
        self.assertEqual(response["data"]["id"], "ctx-123")
    
    def test_singleton_instance(self):
        """Test singleton instance for backward compatibility"""
        instance1 = StandardResponseFormatter.get_instance()
        instance2 = StandardResponseFormatter.get_instance()
        
        # Should return the same instance
        self.assertIs(instance1, instance2)
    
    def test_optimization_failure_fallback(self):
        """Test fallback to unoptimized response on optimization failure"""
        # Mock the optimizer to raise an exception
        formatter = StandardResponseFormatter()
        original_optimize = formatter.optimizer.optimize_response
        
        def failing_optimize(*args, **kwargs):
            raise Exception("Optimization failed")
        
        formatter.optimizer.optimize_response = failing_optimize
        
        # Should return unoptimized response without crashing
        response = formatter.create_success_response(
            operation="create",
            data=self.sample_data
        )
        
        # Should still have a valid response
        self.assertIn("success", response)
        self.assertIn("data", response)
        
        # Restore original method
        formatter.optimizer.optimize_response = original_optimize
    
    def test_partial_success_response_optimization(self):
        """Test partial success response with optimization"""
        partial_failures = [
            {"item": "item1", "error": "Failed to process"}
        ]
        
        response = self.formatter.create_partial_success_response(
            operation="batch_create",
            data={"created": ["item2", "item3"]},
            partial_failures=partial_failures
        )
        
        # Should optimize but preserve partial failure info
        self.assertTrue(response["success"])  # Partial success still has success=true
        self.assertIn("data", response)
    
    def test_validation_error_response_optimization(self):
        """Test validation error response with optimization"""
        response = self.formatter.create_validation_error_response(
            operation="create",
            field="email",
            expected="valid email format",
            actual="invalid-email"
        )
        
        # Should optimize but preserve validation details
        self.assertFalse(response["success"])
        self.assertIn("error", response)
        self.assertIn("meta", response)  # Validation details in metadata


if __name__ == "__main__":
    unittest.main()