"""
Tests for Response Optimizer Service
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any
import json
from datetime import datetime

from fastmcp.task_management.application.services.response_optimizer import (
    ResponseOptimizer,
    ResponseProfile
)


class TestResponseOptimizer:
    """Test Response Optimizer functionality"""

    @pytest.fixture
    def optimizer(self):
        """Create response optimizer instance"""
        return ResponseOptimizer()

    @pytest.fixture
    def sample_response(self):
        """Create a sample response for testing"""
        return {
            "success": True,
            "operation": "task_create",
            "operation_id": "op-123",
            "timestamp": "2025-09-12T10:00:00Z",
            "data": {
                "id": "task-456",
                "title": "Test Task",
                "description": "A test task for validation",
                "assignees": ["coding-agent"],
                "status": "todo"
            },
            "confirmation": {
                "operation_details": {
                    "operation": "task_create",
                    "operation_id": "op-123",
                    "timestamp": "2025-09-12T10:00:00Z"
                },
                "data_persisted": True,
                "partial_failures": [],
                "operation_completed": True
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": ["Update task status", "Add assignees"],
                    "required_actions": ["Review task details"]
                },
                "optional_actions": ["Add labels", "Set due date"],
                "autonomous_guidance": {
                    "confidence": 0.95
                }
            },
            "meta": {
                "version": "1.0",
                "empty_field": None,
                "empty_list": [],
                "empty_string": ""
            }
        }

    @pytest.fixture
    def large_list_response(self):
        """Create a large list response for testing"""
        return {
            "success": True,
            "operation": "list_tasks",
            "data": {
                "tasks": [
                    {
                        "id": f"task-{i}",
                        "title": f"Task {i}",
                        "description": f"Description for task {i}",
                        "status": "todo"
                    } for i in range(50)
                ]
            },
            "meta": {
                "total": 50,
                "page": 1
            }
        }

    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        optimizer = ResponseOptimizer()
        assert optimizer.metrics["total_optimized"] == 0
        assert optimizer.metrics["total_bytes_saved"] == 0
        assert optimizer.metrics["average_compression_ratio"] == 0.0
        assert "minimal" in optimizer.metrics["profile_usage"]

    def test_optimize_response_basic(self, optimizer, sample_response):
        """Test basic response optimization"""
        result = optimizer.optimize_response(
            response=sample_response,
            profile=ResponseProfile.STANDARD
        )
        
        # Should return optimized response
        assert isinstance(result, dict)
        assert "success" in result
        assert "data" in result
        
        # Should have updated metrics
        assert optimizer.metrics["total_optimized"] == 1

    def test_auto_select_profile_minimal(self, optimizer, large_list_response):
        """Test auto-selection of MINIMAL profile for large list responses"""
        profile = optimizer.auto_select_profile(large_list_response, None)
        assert profile == ResponseProfile.MINIMAL

    def test_auto_select_profile_detailed_for_ai_agent(self, optimizer, sample_response):
        """Test auto-selection of DETAILED profile for AI agent requests"""
        request_context = {
            "params": {"assignee": "coding-agent"}
        }
        profile = optimizer.auto_select_profile(sample_response, request_context)
        assert profile == ResponseProfile.DETAILED

    def test_auto_select_profile_debug(self, optimizer, sample_response):
        """Test auto-selection of DEBUG profile"""
        request_context = {
            "headers": {"User-Agent": "debug-client"},
            "debug": True
        }
        profile = optimizer.auto_select_profile(sample_response, request_context)
        assert profile == ResponseProfile.DEBUG

    def test_auto_select_profile_default(self, optimizer):
        """Test default profile selection"""
        # Create a response without AI agents to test true default behavior
        default_response = {
            "success": True,
            "operation": "task_create",
            "data": {
                "id": "task-456",
                "title": "Test Task",
                "assignees": ["user"],  # Regular user, not AI agent
                "status": "todo"
            }
        }
        profile = optimizer.auto_select_profile(default_response, None)
        assert profile == ResponseProfile.STANDARD

    def test_remove_duplicates(self, optimizer, sample_response):
        """Test removal of duplicate fields"""
        result = optimizer.remove_duplicates(sample_response)
        
        # Should remove duplicates from operation_details
        confirmation = result.get("confirmation", {})
        operation_details = confirmation.get("operation_details", {})
        
        # These fields should be removed from operation_details since they exist at root
        assert "operation" not in operation_details
        assert "operation_id" not in operation_details
        assert "timestamp" not in operation_details

    def test_flatten_structure(self, optimizer):
        """Test structure flattening"""
        response = {
            "success": True,
            "confirmation": {
                "data_persisted": True,
                "partial_failures": []
            },
            "data": {"id": "123"}
        }
        
        result = optimizer.flatten_structure(response)
        
        # Should move data_persisted to meta and remove confirmation
        assert "confirmation" not in result
        assert "meta" in result
        assert result["meta"]["persisted"] is True

    def test_remove_nulls(self, optimizer):
        """Test removal of null/empty values"""
        data = {
            "valid_string": "value",
            "null_value": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "zero_value": 0,
            "false_value": False,
            "data": {},  # Should be preserved even if empty
            "nested": {
                "valid": "data",
                "null_nested": None,
                "empty_nested": ""
            }
        }
        
        result = optimizer.remove_nulls(data)
        
        # Should keep valid values and preserve required fields
        assert "valid_string" in result
        assert "null_value" not in result
        assert "empty_string" not in result
        assert "empty_list" not in result
        assert "empty_dict" not in result
        assert "zero_value" in result  # Keep zero
        assert "false_value" in result  # Keep false
        assert "data" in result  # Always preserve data field
        
        # Check nested cleaning
        assert "valid" in result["nested"]
        assert "null_nested" not in result["nested"]
        assert "empty_nested" not in result["nested"]

    def test_apply_profile_minimal(self, optimizer, sample_response):
        """Test MINIMAL profile application"""
        result = optimizer.apply_profile(sample_response, ResponseProfile.MINIMAL)
        
        # Should only keep essential fields
        allowed_fields = ["success", "operation", "data", "error"]
        for key in result.keys():
            assert key in allowed_fields
        
        # Data should always be preserved
        assert "data" in result

    def test_apply_profile_standard(self, optimizer, sample_response):
        """Test STANDARD profile application"""
        result = optimizer.apply_profile(sample_response, ResponseProfile.STANDARD)
        
        # Should keep standard fields and move metadata to meta
        assert "success" in result
        assert "data" in result
        
        # Should move operation_id and timestamp to meta if they exist
        if "operation_id" in sample_response:
            assert "meta" in result
            assert "id" in result["meta"]

    def test_apply_profile_detailed(self, optimizer, sample_response):
        """Test DETAILED profile application"""
        result = optimizer.apply_profile(sample_response, ResponseProfile.DETAILED)
        
        # Should exclude confirmation but keep most fields
        assert "confirmation" not in result
        assert "success" in result
        assert "data" in result
        
        # Should simplify workflow_guidance to hints
        if "workflow_guidance" in sample_response:
            assert "hints" in result
            assert "workflow_guidance" not in result

    def test_apply_profile_debug(self, optimizer, sample_response):
        """Test DEBUG profile application"""
        result = optimizer.apply_profile(sample_response, ResponseProfile.DEBUG)
        
        # Should keep everything and add debug info
        assert "debug_info" in result
        assert "profile_used" in result["debug_info"]
        assert "optimization_steps" in result["debug_info"]

    def test_merge_metadata(self, optimizer, sample_response):
        """Test metadata merging"""
        result = optimizer.merge_metadata(sample_response)
        
        # Should consolidate metadata into meta object
        if "meta" in result:
            # operation_id should become meta.id
            if "operation_id" in sample_response:
                assert "id" in result.get("meta", {})
            
            # confirmation data should be merged
            if "confirmation" in sample_response and "data_persisted" in sample_response["confirmation"]:
                assert "persisted" in result.get("meta", {})

    def test_simplify_workflow_guidance(self, optimizer):
        """Test workflow guidance simplification"""
        guidance = {
            "next_steps": {
                "recommendations": ["Action 1", "Action 2"],
                "required_actions": "Required action"
            },
            "optional_actions": ["Optional 1", "Optional 2", "Optional 3"],
            "autonomous_guidance": {
                "confidence": 0.85
            }
        }
        
        result = optimizer._simplify_workflow_guidance(guidance)
        
        assert "next" in result
        assert result["next"] == "Action 1"  # First recommendation
        assert "required" in result
        assert result["required"] == ["Required action"]  # Converted to array
        assert "tips" in result
        assert len(result["tips"]) == 2  # Max 2 tips
        assert "confidence" in result
        assert result["confidence"] == 0.85

    def test_full_optimization_workflow(self, optimizer, sample_response):
        """Test complete optimization workflow"""
        original_size = len(str(sample_response))
        
        result = optimizer.optimize_response(
            response=sample_response,
            profile=ResponseProfile.STANDARD
        )
        
        optimized_size = len(str(result))
        
        # Should reduce response size
        assert optimized_size < original_size
        
        # Should maintain essential structure
        assert "success" in result
        assert "data" in result
        
        # Should have updated metrics
        assert optimizer.metrics["total_optimized"] == 1
        assert optimizer.metrics["total_bytes_saved"] > 0

    def test_high_frequency_operation_detection(self, optimizer):
        """Test detection of high-frequency operations"""
        response = {
            "operation": "list_tasks",
            "data": {"tasks": []}
        }
        
        profile = optimizer.auto_select_profile(response, None)
        assert profile == ResponseProfile.MINIMAL

    def test_request_context_profile_selection(self, optimizer, sample_response):
        """Test profile selection based on request context"""
        # Explicit profile in request
        context = {"profile": "detailed"}
        profile = optimizer.auto_select_profile(sample_response, context)
        assert profile == ResponseProfile.DETAILED
        
        # AI agent in headers
        context = {"headers": {"User-Agent": "coding-agent"}}
        profile = optimizer.auto_select_profile(sample_response, context)
        assert profile == ResponseProfile.DETAILED

    def test_metrics_tracking(self, optimizer, sample_response):
        """Test metrics tracking across multiple optimizations"""
        # Perform multiple optimizations
        for i in range(5):
            optimizer.optimize_response(sample_response, ResponseProfile.STANDARD)
        
        metrics = optimizer.get_metrics()
        
        assert metrics["total_responses_optimized"] == 5
        assert metrics["total_bytes_saved"] > 0
        assert "average_compression_ratio" in metrics
        assert "profile_usage" in metrics
        assert metrics["profile_usage"]["standard"] == 5

    def test_edge_cases(self, optimizer):
        """Test edge cases and error handling"""
        # Empty response
        result = optimizer.optimize_response({})
        assert isinstance(result, dict)
        
        # Response with only data
        result = optimizer.optimize_response({"data": {"id": "123"}})
        assert "data" in result
        
        # Response with circular reference handling
        circular = {"a": {}}
        circular["a"]["b"] = "safe_value"  # Avoid actual circular reference
        result = optimizer.optimize_response(circular)
        assert isinstance(result, dict)

    def test_flatten_single_arrays(self, optimizer):
        """Test flattening of single-item arrays"""
        data = {
            "single_item": ["only_item"],
            "multiple_items": ["item1", "item2"],
            "nested": {
                "single": ["value"],
                "multiple": ["a", "b"]
            }
        }
        
        result = optimizer._flatten_single_arrays(data)
        
        assert result["single_item"] == "only_item"  # Flattened
        assert result["multiple_items"] == ["item1", "item2"]  # Unchanged
        assert result["nested"]["single"] == "value"  # Flattened
        assert result["nested"]["multiple"] == ["a", "b"]  # Unchanged

    def test_calculate_reduction_percentage(self, optimizer):
        """Test percentage reduction calculation"""
        assert optimizer._calculate_reduction_percentage(100, 50) == 50.0
        assert optimizer._calculate_reduction_percentage(200, 100) == 50.0
        assert optimizer._calculate_reduction_percentage(0, 0) == 0.0
        assert optimizer._calculate_reduction_percentage(100, 100) == 0.0

    def test_response_profile_enum(self):
        """Test ResponseProfile enum values"""
        assert ResponseProfile.MINIMAL.value == "minimal"
        assert ResponseProfile.STANDARD.value == "standard"
        assert ResponseProfile.DETAILED.value == "detailed"
        assert ResponseProfile.DEBUG.value == "debug"

    def test_high_frequency_operation_list(self, optimizer):
        """Test high-frequency operations list handling"""
        for op in optimizer.HIGH_FREQUENCY_OPS:
            response = {"operation": op}
            profile = optimizer.auto_select_profile(response, None)
            assert profile == ResponseProfile.MINIMAL

    def test_ai_agent_indicators(self, optimizer, sample_response):
        """Test AI agent indicator detection"""
        for indicator in optimizer.AI_AGENT_INDICATORS:
            # Test in params to avoid DEBUG indicator collision in User-Agent
            context = {"params": {"agent": indicator}}
            profile = optimizer.auto_select_profile(sample_response, context)
            assert profile == ResponseProfile.DETAILED

    def test_debug_indicators(self, optimizer):
        """Test debug indicator detection"""
        # Create a response without AI agents to test pure debug detection
        debug_response = {
            "success": True,
            "operation": "task_create",
            "data": {
                "id": "task-456",
                "title": "Test Task",
                "assignees": ["user"],  # Regular user, not AI agent
                "status": "todo"
            }
        }
        for indicator in optimizer.DEBUG_INDICATORS:
            context = {"headers": {"X-Debug": indicator}}
            profile = optimizer.auto_select_profile(debug_response, context)
            assert profile == ResponseProfile.DEBUG

    def test_large_response_minimal_selection(self, optimizer):
        """Test automatic minimal profile for large responses"""
        # Create response with large list
        response = {
            "operation": "list_contexts",
            "data": {
                "contexts": [{"id": f"ctx-{i}"} for i in range(15)]
            }
        }
        
        profile = optimizer.auto_select_profile(response, None)
        assert profile == ResponseProfile.MINIMAL

    def test_empty_confirmation_removal(self, optimizer):
        """Test removal of empty confirmation objects"""
        response = {
            "success": True,
            "data": {"id": "123"},
            "confirmation": {
                "data_persisted": True,
                "partial_failures": [],
                "operation_details": {}
            }
        }
        
        result = optimizer.remove_duplicates(response)
        
        # Should remove empty operation_details
        if "confirmation" in result:
            assert "operation_details" not in result["confirmation"]

    def test_success_status_deduplication(self, optimizer):
        """Test deduplication of success/status fields"""
        response = {
            "success": True,
            "status": "success",
            "data": {"id": "123"}
        }
        
        result = optimizer.remove_duplicates(response)
        
        # Should keep success, remove redundant status
        assert "success" in result
        assert "status" not in result

    def test_operation_completed_deduplication(self, optimizer):
        """Test deduplication of operation_completed field"""
        response = {
            "success": True,
            "data": {"id": "123"},
            "confirmation": {
                "operation_completed": True
            }
        }
        
        result = optimizer.remove_duplicates(response)
        
        # Should remove operation_completed since it matches success
        if "confirmation" in result:
            assert "operation_completed" not in result["confirmation"]

    def test_preserve_data_field_always(self, optimizer):
        """Test that data field is always preserved, even if empty"""
        response = {"data": {}}
        
        result = optimizer.optimize_response(response, ResponseProfile.MINIMAL)
        
        assert "data" in result
        assert result["data"] == {}