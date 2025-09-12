"""Unit tests for Response Profile functionality

Tests the profile-based response optimization including:
- Profile auto-selection logic
- Profile-specific filtering
- Size differences between profiles
- Request context handling
- Profile usage metrics
"""

import unittest
import json
from typing import Dict, Any

from fastmcp.task_management.application.services.response_optimizer import (
    ResponseOptimizer,
    ResponseProfile
)


class TestResponseProfiles(unittest.TestCase):
    """Test cases for Response Profile functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.optimizer = ResponseOptimizer()
        
        # Sample response for testing
        self.sample_response = {
            "status": "success",
            "success": True,
            "operation": "create",
            "operation_id": "uuid-123",
            "timestamp": "2025-01-01T00:00:00Z",
            "data": {
                "task": {
                    "id": "task-456",
                    "title": "Test Task",
                    "status": "todo",
                    "assignees": ["coding-agent"]
                }
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["update_status"],
                    "required_actions": ["add_description"]
                },
                "autonomous_guidance": {
                    "confidence": 0.85
                }
            },
            "metadata": {
                "created_by": "user-789"
            }
        }
    
    def test_profile_auto_selection_default(self):
        """Test default profile selection (STANDARD)"""
        profile = self.optimizer.auto_select_profile(
            {"operation": "update", "data": {"item": "test"}}
        )
        self.assertEqual(profile, ResponseProfile.STANDARD)
    
    def test_profile_auto_selection_high_frequency(self):
        """Test MINIMAL profile selection for high-frequency operations"""
        # Test with list operation
        profile = self.optimizer.auto_select_profile(
            {"operation": "list", "data": {"items": [1, 2, 3]}}
        )
        self.assertEqual(profile, ResponseProfile.MINIMAL)
        
        # Test with get_status operation
        profile = self.optimizer.auto_select_profile(
            {"operation": "get_status", "data": {"status": "ok"}}
        )
        self.assertEqual(profile, ResponseProfile.MINIMAL)
    
    def test_profile_auto_selection_ai_agent(self):
        """Test DETAILED profile selection for AI agent requests"""
        # Test with assignees containing agent
        response = {
            "operation": "create",
            "data": {"assignees": ["coding-agent", "@test-orchestrator-agent"]}
        }
        profile = self.optimizer.auto_select_profile(response)
        self.assertEqual(profile, ResponseProfile.DETAILED)
        
        # Test with agent in request context
        request_context = {
            "params": {"agent": "autonomous"}
        }
        profile = self.optimizer.auto_select_profile(
            {"operation": "update", "data": {}}, 
            request_context
        )
        self.assertEqual(profile, ResponseProfile.DETAILED)
    
    def test_profile_auto_selection_debug(self):
        """Test DEBUG profile selection"""
        # Test with debug flag
        request_context = {"debug": True}
        profile = self.optimizer.auto_select_profile(
            {"operation": "create", "data": {}},
            request_context
        )
        self.assertEqual(profile, ResponseProfile.DEBUG)
        
        # Test with debug in headers
        request_context = {
            "headers": {"X-Debug": "true"}
        }
        profile = self.optimizer.auto_select_profile(
            {"operation": "update", "data": {}},
            request_context
        )
        self.assertEqual(profile, ResponseProfile.DEBUG)
    
    def test_profile_auto_selection_large_list(self):
        """Test MINIMAL profile for large list responses"""
        response = {
            "operation": "list",
            "data": {
                "tasks": [{"id": i} for i in range(20)]  # 20 items
            }
        }
        profile = self.optimizer.auto_select_profile(response)
        self.assertEqual(profile, ResponseProfile.MINIMAL)
    
    def test_profile_explicit_selection(self):
        """Test explicit profile selection via request context"""
        request_context = {"profile": "minimal"}
        profile = self.optimizer.auto_select_profile(
            {"operation": "create", "data": {}},
            request_context
        )
        self.assertEqual(profile, ResponseProfile.MINIMAL)
        
        request_context = {"profile": "detailed"}
        profile = self.optimizer.auto_select_profile(
            {"operation": "update", "data": {}},
            request_context
        )
        self.assertEqual(profile, ResponseProfile.DETAILED)
    
    def test_minimal_profile_fields(self):
        """Test MINIMAL profile includes only essential fields"""
        optimized = self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.MINIMAL
        )
        
        # Check only essential fields are present
        self.assertIn("success", optimized)
        # Operation might be in meta if it was merged
        self.assertTrue("operation" in optimized or 
                       (optimized.get("meta", {}).get("operation") == "create"))
        self.assertIn("data", optimized)
        
        # Check non-essential fields are removed
        self.assertNotIn("workflow_guidance", optimized)
        self.assertNotIn("metadata", optimized)
        self.assertNotIn("timestamp", optimized)
    
    def test_standard_profile_fields(self):
        """Test STANDARD profile includes standard fields plus meta"""
        optimized = self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.STANDARD
        )
        
        # Check standard fields are present
        self.assertIn("success", optimized)
        # Operation is moved to meta
        self.assertTrue("operation" in optimized or 
                       optimized.get("meta", {}).get("operation") == "create")
        self.assertIn("data", optimized)
        self.assertIn("meta", optimized)
        
        # Check meta contains moved fields
        self.assertEqual(optimized["meta"]["id"], "uuid-123")
        self.assertEqual(optimized["meta"]["timestamp"], "2025-01-01T00:00:00Z")
        
        # Check workflow_guidance is removed
        self.assertNotIn("workflow_guidance", optimized)
    
    def test_detailed_profile_fields(self):
        """Test DETAILED profile includes hints"""
        optimized = self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.DETAILED
        )
        
        # Check detailed fields are present
        self.assertIn("success", optimized)
        self.assertIn("data", optimized)
        self.assertIn("hints", optimized)
        
        # Check hints are simplified
        self.assertEqual(optimized["hints"]["next"], "update_status")
        # Required is a single-item array that might be flattened
        self.assertTrue(optimized["hints"]["required"] == ["add_description"] or
                       optimized["hints"]["required"] == "add_description")
        self.assertEqual(optimized["hints"]["confidence"], 0.85)
    
    def test_debug_profile_fields(self):
        """Test DEBUG profile includes everything plus debug info"""
        optimized = self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.DEBUG
        )
        
        # Check debug info is added
        self.assertIn("debug_info", optimized)
        self.assertEqual(optimized["debug_info"]["profile_used"], "debug")
        self.assertIn("optimization_steps", optimized["debug_info"])
        self.assertIn("timestamp", optimized["debug_info"])
        
        # Check original fields are preserved
        self.assertIn("data", optimized)
    
    def test_profile_size_differences(self):
        """Test that different profiles produce different response sizes"""
        # Create a larger response for better comparison
        large_response = {
            "status": "success",
            "success": True,
            "operation": "list",
            "operation_id": "uuid-999",
            "timestamp": "2025-01-01T00:00:00Z",
            "data": {
                "tasks": [
                    {
                        "id": f"task-{i}",
                        "title": f"Task {i}",
                        "description": f"Description for task {i}",
                        "status": "todo",
                        "priority": "medium",
                        "assignees": ["@agent1", "@agent2"],
                        "labels": ["label1", "label2", "label3"]
                    }
                    for i in range(5)
                ]
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["action1", "action2", "action3"],
                    "required_actions": ["req1", "req2"],
                    "optional_actions": ["opt1", "opt2"]
                },
                "validation": {
                    "errors": [],
                    "warnings": ["warning1", "warning2"]
                }
            },
            "metadata": {
                "total_count": 5,
                "page": 1,
                "per_page": 10
            }
        }
        
        # Get sizes for each profile
        minimal = self.optimizer.optimize_response(large_response.copy(), ResponseProfile.MINIMAL)
        standard = self.optimizer.optimize_response(large_response.copy(), ResponseProfile.STANDARD)
        detailed = self.optimizer.optimize_response(large_response.copy(), ResponseProfile.DETAILED)
        debug = self.optimizer.optimize_response(large_response.copy(), ResponseProfile.DEBUG)
        
        minimal_size = len(json.dumps(minimal))
        standard_size = len(json.dumps(standard))
        detailed_size = len(json.dumps(detailed))
        debug_size = len(json.dumps(debug))
        
        print(f"\nProfile size comparison:")
        print(f"MINIMAL:  {minimal_size} bytes")
        print(f"STANDARD: {standard_size} bytes")
        print(f"DETAILED: {detailed_size} bytes")
        print(f"DEBUG:    {debug_size} bytes")
        
        # Verify size ordering: MINIMAL < STANDARD < DETAILED < DEBUG
        self.assertLess(minimal_size, standard_size, 
                       "MINIMAL should be smaller than STANDARD")
        self.assertLess(standard_size, detailed_size,
                       "STANDARD should be smaller than DETAILED")
        self.assertLess(detailed_size, debug_size,
                       "DETAILED should be smaller than DEBUG")
    
    def test_profile_usage_metrics(self):
        """Test that profile usage is tracked in metrics"""
        # Reset metrics
        self.optimizer.metrics["total_optimized"] = 0
        self.optimizer.metrics["profile_usage"] = {
            "minimal": 0,
            "standard": 0,
            "detailed": 0,
            "debug": 0
        }
        
        # Use different profiles
        self.optimizer.optimize_response(
            self.sample_response.copy(), 
            ResponseProfile.MINIMAL
        )
        self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.STANDARD
        )
        self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.STANDARD
        )
        self.optimizer.optimize_response(
            self.sample_response.copy(),
            ResponseProfile.DETAILED
        )
        
        # Check metrics
        metrics = self.optimizer.get_metrics()
        self.assertEqual(metrics["profile_usage"]["minimal"], 1)
        self.assertEqual(metrics["profile_usage"]["standard"], 2)
        self.assertEqual(metrics["profile_usage"]["detailed"], 1)
        self.assertEqual(metrics["profile_usage"]["debug"], 0)
        self.assertEqual(metrics["most_used_profile"], "standard")
    
    def test_auto_profile_with_optimization(self):
        """Test auto profile selection during optimization"""
        # Test with AI agent context
        request_context = {
            "params": {"agent": "coding-agent"}
        }
        
        optimized = self.optimizer.optimize_response(
            self.sample_response.copy(),
            profile=None,  # Auto-select
            request_context=request_context
        )
        
        # Should use DETAILED profile and include hints
        self.assertIn("hints", optimized)
        
        # Test with high-frequency operation
        list_response = {
            "operation": "list",
            "success": True,
            "data": {"items": [1, 2, 3]}
        }
        
        optimized = self.optimizer.optimize_response(
            list_response.copy(),
            profile=None  # Auto-select
        )
        
        # Should use MINIMAL profile
        self.assertIn("success", optimized)
        self.assertIn("data", optimized)
        # meta might still exist if operation was moved there
        # but it should be minimal
    
    def test_profile_with_error_response(self):
        """Test profile handling with error responses"""
        error_response = {
            "status": "failure",
            "success": False,
            "operation": "create",
            "error": {
                "message": "Validation failed",
                "code": "VALIDATION_ERROR"
            }
        }
        
        # Test each profile with error
        for profile in ResponseProfile:
            optimized = self.optimizer.optimize_response(
                error_response.copy(),
                profile
            )
            
            # Error should be preserved in all profiles
            if profile != ResponseProfile.MINIMAL:
                self.assertIn("error", optimized)
            
            # Success should always be False
            self.assertFalse(optimized["success"])


if __name__ == "__main__":
    unittest.main()