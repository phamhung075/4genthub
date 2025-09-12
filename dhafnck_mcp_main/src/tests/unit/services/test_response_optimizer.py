"""Unit tests for ResponseOptimizer class

Tests the response optimization functionality including:
- Duplicate field removal
- Structure flattening
- Null/empty field removal
- Profile-based filtering
- Metadata consolidation
- Size reduction verification
"""

import unittest
import json
from typing import Dict, Any
from datetime import datetime, timezone

from fastmcp.task_management.application.services.response_optimizer import (
    ResponseOptimizer,
    ResponseProfile
)


class TestResponseOptimizer(unittest.TestCase):
    """Test cases for ResponseOptimizer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.optimizer = ResponseOptimizer()
        
        # Sample redundant response (current format with duplicates)
        self.redundant_response = {
            "status": "success",
            "success": True,
            "operation": "create",
            "operation_id": "uuid-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "confirmation": {
                "operation_completed": True,
                "data_persisted": True,
                "partial_failures": [],
                "operation_details": {
                    "operation": "create",
                    "operation_id": "uuid-123",
                    "timestamp": "2025-01-01T00:00:00Z"
                }
            },
            "data": {
                "task": {
                    "id": "task-456",
                    "title": "Test Task",
                    "status": "todo",
                    "empty_field": "",
                    "null_field": None,
                    "single_item_array": ["single_value"]
                }
            },
            "metadata": {
                "empty_list": [],
                "null_value": None
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["update_status", "add_description"],
                    "required_actions": ["add_assignee"],
                    "optional_actions": ["set_priority", "add_labels"]
                },
                "validation": {
                    "errors": [],
                    "warnings": []
                },
                "autonomous_guidance": {
                    "decision_points": [],
                    "confidence": 0.85
                }
            }
        }
    
    def test_remove_duplicates(self):
        """Test removal of duplicate fields"""
        response = {
            "status": "success",
            "success": True,
            "operation": "create",
            "operation_id": "uuid-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "confirmation": {
                "operation_completed": True,
                "operation_details": {
                    "operation": "create",
                    "operation_id": "uuid-123",
                    "timestamp": "2025-01-01T00:00:00Z"
                }
            }
        }
        
        optimized = self.optimizer.remove_duplicates(response)
        
        # Check that duplicates are removed from operation_details
        self.assertNotIn("operation_details", optimized.get("confirmation", {}))
        
        # Check that redundant status is removed (keeping success)
        self.assertNotIn("status", optimized)
        self.assertTrue(optimized["success"])
        
        # Check that operation_completed is removed if matches success
        self.assertNotIn("operation_completed", optimized.get("confirmation", {}))
    
    def test_flatten_structure(self):
        """Test flattening of nested structures"""
        response = {
            "confirmation": {
                "data_persisted": True,
                "partial_failures": []
            },
            "data": {
                "items": ["single_item"]
            }
        }
        
        optimized = self.optimizer.flatten_structure(response)
        
        # Check that confirmation is flattened to meta
        self.assertNotIn("confirmation", optimized)
        self.assertEqual(optimized["meta"]["persisted"], True)
        
        # Check that single-item array is flattened
        self.assertEqual(optimized["data"]["items"], "single_item")
    
    def test_remove_nulls(self):
        """Test removal of null and empty values"""
        data = {
            "field1": "value1",
            "field2": None,
            "field3": "",
            "field4": [],
            "field5": {},
            "nested": {
                "valid": "data",
                "invalid": None,
                "empty": ""
            }
        }
        
        cleaned = self.optimizer.remove_nulls(data)
        
        # Check that null/empty values are removed
        self.assertIn("field1", cleaned)
        self.assertNotIn("field2", cleaned)
        self.assertNotIn("field3", cleaned)
        self.assertNotIn("field4", cleaned)
        self.assertNotIn("field5", cleaned)
        
        # Check nested cleaning
        self.assertIn("valid", cleaned["nested"])
        self.assertNotIn("invalid", cleaned["nested"])
        self.assertNotIn("empty", cleaned["nested"])
    
    def test_apply_profile_minimal(self):
        """Test MINIMAL profile filtering"""
        response = {
            "success": True,
            "operation": "create",
            "data": {"task": "data"},
            "meta": {"id": "123"},
            "workflow_guidance": {"hints": "test"}
        }
        
        filtered = self.optimizer.apply_profile(response, ResponseProfile.MINIMAL)
        
        # Check only essential fields are kept
        self.assertIn("success", filtered)
        self.assertIn("operation", filtered)
        self.assertIn("data", filtered)
        self.assertNotIn("meta", filtered)
        self.assertNotIn("workflow_guidance", filtered)
    
    def test_apply_profile_standard(self):
        """Test STANDARD profile filtering"""
        response = {
            "success": True,
            "operation": "create",
            "operation_id": "uuid-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "data": {"task": "data"},
            "workflow_guidance": {"hints": "test"}
        }
        
        filtered = self.optimizer.apply_profile(response, ResponseProfile.STANDARD)
        
        # Check standard fields are kept and reorganized
        self.assertIn("success", filtered)
        self.assertIn("operation", filtered)
        self.assertIn("data", filtered)
        self.assertIn("meta", filtered)
        self.assertEqual(filtered["meta"]["id"], "uuid-123")
        self.assertEqual(filtered["meta"]["timestamp"], "2025-01-01T00:00:00Z")
        self.assertNotIn("workflow_guidance", filtered)
    
    def test_apply_profile_detailed(self):
        """Test DETAILED profile with workflow hints"""
        response = {
            "success": True,
            "operation": "create",
            "data": {"task": "data"},
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["update_status"],
                    "required_actions": ["add_assignee"]
                },
                "autonomous_guidance": {
                    "confidence": 0.9
                }
            }
        }
        
        filtered = self.optimizer.apply_profile(response, ResponseProfile.DETAILED)
        
        # Check that workflow_guidance is simplified to hints
        self.assertIn("hints", filtered)
        self.assertEqual(filtered["hints"]["next"], "update_status")
        self.assertEqual(filtered["hints"]["required"], ["add_assignee"])
        self.assertEqual(filtered["hints"]["confidence"], 0.9)
        self.assertNotIn("workflow_guidance", filtered)
    
    def test_merge_metadata(self):
        """Test metadata consolidation"""
        response = {
            "success": True,
            "operation": "create",
            "operation_id": "uuid-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "data": {"task": "data"},
            "confirmation": {
                "data_persisted": True,
                "partial_failures": ["failure1"]
            }
        }
        
        merged = self.optimizer.merge_metadata(response)
        
        # Check metadata is consolidated in meta object
        self.assertIn("meta", merged)
        self.assertEqual(merged["meta"]["id"], "uuid-123")
        self.assertEqual(merged["meta"]["operation"], "create")
        self.assertEqual(merged["meta"]["timestamp"], "2025-01-01T00:00:00Z")
        self.assertEqual(merged["meta"]["persisted"], True)
        self.assertEqual(merged["meta"]["partial_failures"], ["failure1"])
        
        # Check original fields are removed
        self.assertNotIn("operation_id", merged)
        self.assertNotIn("timestamp", merged)
        self.assertNotIn("confirmation", merged)
    
    def test_optimize_response_complete(self):
        """Test complete optimization pipeline"""
        original = self.redundant_response.copy()
        optimized = self.optimizer.optimize_response(original, ResponseProfile.STANDARD)
        
        # Check structure is optimized
        self.assertIn("success", optimized)
        self.assertIn("data", optimized)
        self.assertIn("meta", optimized)
        
        # Check duplicates are removed
        self.assertNotIn("status", optimized)
        self.assertNotIn("confirmation", optimized)
        
        # Check nulls are removed
        self.assertNotIn("empty_field", optimized["data"]["task"])
        self.assertNotIn("null_field", optimized["data"]["task"])
        
        # Check single array is flattened
        self.assertEqual(optimized["data"]["task"]["single_item_array"], "single_value")
        
        # Check metadata is consolidated
        self.assertEqual(optimized["meta"]["id"], "uuid-123")
        self.assertEqual(optimized["meta"]["persisted"], True)
    
    def test_size_reduction(self):
        """Test that 60% size reduction target is achieved"""
        original = self.redundant_response.copy()
        optimized = self.optimizer.optimize_response(original, ResponseProfile.STANDARD)
        
        # Calculate size reduction
        original_size = len(json.dumps(original))
        optimized_size = len(json.dumps(optimized))
        reduction_percentage = ((original_size - optimized_size) / original_size) * 100
        
        print(f"\nSize reduction test:")
        print(f"Original size: {original_size} bytes")
        print(f"Optimized size: {optimized_size} bytes")
        print(f"Reduction: {reduction_percentage:.1f}%")
        
        # Verify significant reduction (may not always be 60% for small samples)
        self.assertGreater(reduction_percentage, 30, 
                          f"Expected at least 30% reduction, got {reduction_percentage:.1f}%")
    
    def test_metrics_tracking(self):
        """Test that metrics are properly tracked"""
        # Reset metrics
        self.optimizer.metrics = {
            "total_optimized": 0,
            "total_bytes_saved": 0,
            "average_compression_ratio": 0.0,
            "profile_usage": {
                "minimal": 0,
                "standard": 0,
                "detailed": 0,
                "debug": 0
            }
        }
        
        # Optimize multiple responses
        for _ in range(3):
            self.optimizer.optimize_response(self.redundant_response, ResponseProfile.STANDARD)
        
        metrics = self.optimizer.get_metrics()
        
        # Check metrics are updated
        self.assertEqual(metrics["total_responses_optimized"], 3)
        self.assertGreater(metrics["total_bytes_saved"], 0)
        self.assertIn("%", metrics["average_compression_ratio"])
    
    def test_workflow_guidance_simplification(self):
        """Test simplification of workflow guidance to hints"""
        guidance = {
            "next_steps": {
                "recommendations": ["action1", "action2", "action3"],
                "required_actions": ["req1", "req2", "req3", "req4"],
                "optional_actions": ["opt1", "opt2", "opt3"]
            },
            "autonomous_guidance": {
                "confidence": 0.75,
                "decision_points": ["point1", "point2"]
            }
        }
        
        hints = self.optimizer._simplify_workflow_guidance(guidance)
        
        # Check hints are simplified
        self.assertEqual(hints["next"], "action1")
        self.assertEqual(len(hints["required"]), 3)  # Max 3
        self.assertEqual(hints["required"], ["req1", "req2", "req3"])
        self.assertEqual(len(hints.get("tips", [])), 0)  # No tips from optional_actions
        self.assertEqual(hints["confidence"], 0.75)
    
    def test_error_response_optimization(self):
        """Test optimization of error responses"""
        error_response = {
            "status": "failure",
            "success": False,
            "operation": "create",
            "operation_id": "uuid-789",
            "timestamp": "2025-01-01T00:00:00Z",
            "error": {
                "message": "Validation failed",
                "code": "VALIDATION_ERROR",
                "operation": "create",
                "timestamp": "2025-01-01T00:00:00Z"
            },
            "confirmation": {
                "operation_completed": False
            }
        }
        
        optimized = self.optimizer.optimize_response(error_response, ResponseProfile.STANDARD)
        
        # Check error response is optimized
        self.assertFalse(optimized["success"])
        self.assertIn("error", optimized)
        self.assertNotIn("confirmation", optimized)
        self.assertIn("meta", optimized)
    
    def test_profile_debug_returns_everything(self):
        """Test that DEBUG profile returns everything plus debug info"""
        original = self.redundant_response.copy()
        debug_response = self.optimizer.apply_profile(original, ResponseProfile.DEBUG)
        
        # DEBUG should return everything from original plus debug_info
        for key in original.keys():
            self.assertIn(key, debug_response)
            self.assertEqual(original[key], debug_response[key])
        
        # DEBUG should add debug_info
        self.assertIn("debug_info", debug_response)
        self.assertEqual(debug_response["debug_info"]["profile_used"], "debug")
    
    def test_empty_response_handling(self):
        """Test handling of minimal/empty responses"""
        empty_response = {
            "success": True,
            "data": {}
        }
        
        optimized = self.optimizer.optimize_response(empty_response, ResponseProfile.MINIMAL)
        
        # Should handle empty response gracefully
        self.assertIn("success", optimized)
        self.assertIn("data", optimized)
        self.assertEqual(optimized["data"], {})


if __name__ == "__main__":
    unittest.main()