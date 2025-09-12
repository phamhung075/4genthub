"""
Tests for Response Optimizer Service
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any
import json

from fastmcp.task_management.application.services.response_optimizer import (
    ResponseOptimizer,
    OptimizationStrategy,
    ResponseProfile,
    OptimizationResult
)


class TestResponseOptimizer:
    """Test Response Optimizer functionality"""

    @pytest.fixture
    def optimizer(self):
        """Create response optimizer instance"""
        return ResponseOptimizer()

    @pytest.fixture
    def large_response(self):
        """Create a large response for testing"""
        return {
            "tasks": [
                {
                    "id": f"task-{i}",
                    "title": f"Task {i}",
                    "description": f"This is a detailed description for task {i} " * 10,
                    "details": f"Implementation details for task {i} " * 20,
                    "metadata": {
                        "created_at": "2025-09-12T10:00:00Z",
                        "updated_at": "2025-09-12T10:00:00Z",
                        "version": "1.0",
                        "tags": [f"tag{j}" for j in range(20)]
                    },
                    "history": [
                        {
                            "timestamp": f"2025-09-{10+j}T10:00:00Z",
                            "action": "update",
                            "changes": {"field": "value"} 
                        } for j in range(50)
                    ]
                } for i in range(100)
            ],
            "metadata": {
                "total_count": 100,
                "page": 1,
                "per_page": 100,
                "debug_info": {
                    "query_time": 0.123,
                    "db_queries": 15,
                    "cache_hits": 3
                }
            }
        }

    def test_optimizer_initialization(self):
        """Test optimizer initialization with custom settings"""
        optimizer = ResponseOptimizer(
            max_response_size_kb=500,
            enable_compression=True,
            remove_nulls=True
        )
        assert optimizer.max_response_size_kb == 500
        assert optimizer.enable_compression is True
        assert optimizer.remove_nulls is True

    def test_optimize_minimal_profile(self, optimizer, large_response):
        """Test optimization with minimal profile"""
        result = optimizer.optimize(
            response=large_response,
            profile=ResponseProfile.MINIMAL
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.size_reduction_percentage > 50
        assert result.optimized_size_kb < result.original_size_kb
        
        # Check that detailed fields are removed
        optimized_data = result.optimized_response
        if "tasks" in optimized_data and len(optimized_data["tasks"]) > 0:
            task = optimized_data["tasks"][0]
            assert "description" not in task or len(task.get("description", "")) < 100
            assert "details" not in task
            assert "history" not in task

    def test_optimize_standard_profile(self, optimizer, large_response):
        """Test optimization with standard profile"""
        result = optimizer.optimize(
            response=large_response,
            profile=ResponseProfile.STANDARD
        )
        
        optimized_data = result.optimized_response
        assert "tasks" in optimized_data
        
        # Standard profile should keep important fields but trim large ones
        if len(optimized_data["tasks"]) > 0:
            task = optimized_data["tasks"][0]
            assert "id" in task
            assert "title" in task
            assert "description" in task
            # History might be truncated
            if "history" in task:
                assert len(task["history"]) <= 10

    def test_optimize_detailed_profile(self, optimizer, large_response):
        """Test optimization with detailed profile"""
        result = optimizer.optimize(
            response=large_response,
            profile=ResponseProfile.DETAILED
        )
        
        # Detailed profile should keep most data but still optimize
        assert result.size_reduction_percentage > 0
        optimized_data = result.optimized_response
        assert "tasks" in optimized_data
        assert "metadata" in optimized_data

    def test_field_truncation(self, optimizer):
        """Test field truncation strategy"""
        response = {
            "short_field": "Short value",
            "long_field": "x" * 10000,
            "nested": {
                "description": "y" * 5000
            }
        }
        
        result = optimizer.optimize(
            response=response,
            strategy=OptimizationStrategy.TRUNCATE_FIELDS,
            max_field_length=1000
        )
        
        optimized = result.optimized_response
        assert len(optimized["long_field"]) <= 1000
        assert optimized["long_field"].endswith("...")
        assert len(optimized["nested"]["description"]) <= 1000

    def test_remove_null_empty_fields(self, optimizer):
        """Test removal of null and empty fields"""
        response = {
            "id": "123",
            "title": "Test",
            "description": None,
            "tags": [],
            "metadata": {},
            "empty_string": "",
            "zero": 0,
            "false_value": False,
            "nested": {
                "null_field": None,
                "empty_list": [],
                "valid": "data"
            }
        }
        
        optimizer.remove_nulls = True
        optimizer.remove_empty = True
        
        result = optimizer.optimize(response)
        optimized = result.optimized_response
        
        assert "description" not in optimized
        assert "tags" not in optimized
        assert "metadata" not in optimized
        assert "empty_string" not in optimized
        assert "zero" in optimized  # Keep zero values
        assert "false_value" in optimized  # Keep false values
        assert "null_field" not in optimized["nested"]
        assert "valid" in optimized["nested"]

    def test_pagination_optimization(self, optimizer):
        """Test optimization of paginated responses"""
        response = {
            "data": [{"id": i, "name": f"Item {i}"} for i in range(1000)],
            "pagination": {
                "page": 1,
                "per_page": 1000,
                "total": 10000
            }
        }
        
        result = optimizer.optimize(
            response=response,
            strategy=OptimizationStrategy.PAGINATE,
            page_size=50
        )
        
        optimized = result.optimized_response
        assert len(optimized["data"]) == 50
        assert optimized["pagination"]["per_page"] == 50
        assert "next_page" in optimized["pagination"]

    def test_compression_strategy(self, optimizer):
        """Test response compression"""
        large_text = "This is a repeating pattern. " * 1000
        response = {
            "content": large_text,
            "metadata": {"size": "large"}
        }
        
        result = optimizer.optimize(
            response=response,
            strategy=OptimizationStrategy.COMPRESS
        )
        
        # Compressed response should be significantly smaller
        assert result.compression_ratio > 5  # At least 5x compression
        assert result.is_compressed is True
        
        # Should be able to decompress
        decompressed = optimizer.decompress(result.optimized_response)
        assert decompressed["content"] == large_text

    def test_field_filtering(self, optimizer):
        """Test selective field filtering"""
        response = {
            "id": "123",
            "public_data": "visible",
            "private_data": "sensitive",
            "internal_metadata": {"debug": "info"},
            "user": {
                "name": "John",
                "email": "john@example.com",
                "password_hash": "xxxxx"
            }
        }
        
        result = optimizer.optimize(
            response=response,
            exclude_fields=["private_data", "internal_metadata", "user.password_hash"]
        )
        
        optimized = result.optimized_response
        assert "public_data" in optimized
        assert "private_data" not in optimized
        assert "internal_metadata" not in optimized
        assert "password_hash" not in optimized["user"]
        assert "name" in optimized["user"]

    def test_deduplication(self, optimizer):
        """Test deduplication of repeated data"""
        response = {
            "items": [
                {
                    "id": i,
                    "category": {"id": 1, "name": "Category A", "description": "Long description" * 10},
                    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
                } for i in range(100)
            ]
        }
        
        result = optimizer.optimize(
            response=response,
            strategy=OptimizationStrategy.DEDUPLICATE
        )
        
        optimized = result.optimized_response
        # Should extract common data
        assert "common_data" in optimized or "references" in optimized
        assert result.size_reduction_percentage > 50

    def test_adaptive_optimization(self, optimizer, large_response):
        """Test adaptive optimization based on response size"""
        # Small response - minimal optimization
        small_response = {"id": "123", "name": "Test"}
        result_small = optimizer.optimize_adaptive(small_response)
        assert result_small.optimization_level == "none"
        
        # Large response - aggressive optimization
        result_large = optimizer.optimize_adaptive(large_response)
        assert result_large.optimization_level in ["high", "maximum"]
        assert result_large.size_reduction_percentage > 60

    def test_streaming_optimization(self, optimizer):
        """Test optimization for streaming responses"""
        def response_generator():
            for i in range(100):
                yield {
                    "id": i,
                    "data": "x" * 1000,
                    "metadata": {"index": i}
                }
        
        optimized_stream = optimizer.optimize_stream(
            response_generator(),
            chunk_size=10,
            profile=ResponseProfile.MINIMAL
        )
        
        chunks = list(optimized_stream)
        assert len(chunks) == 10  # 100 items / 10 per chunk
        
        # Each chunk should be optimized
        first_chunk = chunks[0]
        assert len(first_chunk) == 10
        assert len(first_chunk[0].get("data", "")) < 1000

    def test_caching_optimization(self, optimizer):
        """Test caching of optimization strategies"""
        response_template = {
            "type": "task_list",
            "data": [{"id": i} for i in range(50)]
        }
        
        # First optimization
        result1 = optimizer.optimize(response_template)
        
        # Second optimization of similar structure should use cached strategy
        similar_response = {
            "type": "task_list",
            "data": [{"id": i} for i in range(100, 150)]
        }
        
        with patch.object(optimizer, '_analyze_response') as mock_analyze:
            result2 = optimizer.optimize(similar_response)
            # Analysis should not be called due to caching
            assert mock_analyze.call_count == 0

    def test_custom_optimization_rules(self, optimizer):
        """Test custom optimization rules"""
        # Add custom rule
        optimizer.add_rule(
            name="remove_debug_info",
            condition=lambda resp: "debug" in resp,
            action=lambda resp: {k: v for k, v in resp.items() if k != "debug"}
        )
        
        response = {
            "data": "important",
            "debug": {"queries": 10, "time": 0.5},
            "metadata": {"version": "1.0"}
        }
        
        result = optimizer.optimize(response)
        assert "data" in result.optimized_response
        assert "debug" not in result.optimized_response

    def test_format_specific_optimization(self, optimizer):
        """Test optimization for specific response formats"""
        # JSON API format
        json_api_response = {
            "data": [
                {
                    "type": "tasks",
                    "id": "1",
                    "attributes": {"title": "Task 1"},
                    "relationships": {
                        "author": {"data": {"type": "users", "id": "10"}}
                    }
                }
            ],
            "included": [
                {"type": "users", "id": "10", "attributes": {"name": "John"}}
            ]
        }
        
        result = optimizer.optimize(
            json_api_response,
            format="json_api"
        )
        
        # Should maintain JSON API structure while optimizing
        assert "data" in result.optimized_response
        assert "type" in result.optimized_response["data"][0]

    def test_performance_metrics(self, optimizer, large_response):
        """Test optimization performance metrics"""
        import time
        
        start_time = time.time()
        result = optimizer.optimize(large_response)
        optimization_time = time.time() - start_time
        
        assert result.optimization_time_ms > 0
        assert result.optimization_time_ms < 1000  # Should be fast
        
        # Check other metrics
        assert result.fields_removed >= 0
        assert result.bytes_saved > 0
        assert hasattr(result, 'optimization_strategies_used')

    def test_error_handling(self, optimizer):
        """Test error handling during optimization"""
        # Circular reference
        circular_response = {"a": {}}
        circular_response["a"]["b"] = circular_response
        
        # Should handle circular references gracefully
        result = optimizer.optimize(circular_response)
        assert result.errors == [] or "circular reference" in str(result.errors)
        
        # Invalid input
        with pytest.raises(ValueError):
            optimizer.optimize(None)

    def test_response_validation(self, optimizer):
        """Test response validation after optimization"""
        response = {
            "required_field": "value",
            "optional_field": "can be removed",
            "data": [1, 2, 3]
        }
        
        schema = {
            "required": ["required_field", "data"],
            "properties": {
                "required_field": {"type": "string"},
                "data": {"type": "array"}
            }
        }
        
        result = optimizer.optimize(
            response=response,
            validate_schema=schema
        )
        
        # Optimization should maintain schema validity
        assert "required_field" in result.optimized_response
        assert "data" in result.optimized_response
        assert result.is_valid is True