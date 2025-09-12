"""
Tests for Context Field Selector Service
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Set, Any

from fastmcp.task_management.application.services.context_field_selector import (
    ContextFieldSelector,
    FieldSelectionConfig,
    SelectionProfile
)


class TestContextFieldSelector:
    """Test Context Field Selector functionality"""

    @pytest.fixture
    def selector(self):
        """Create field selector instance"""
        return ContextFieldSelector()

    @pytest.fixture
    def sample_task_context(self):
        """Sample task context with all fields"""
        return {
            "id": "task-123",
            "title": "Implement authentication",
            "description": "Implement JWT authentication with refresh tokens",
            "status": "in_progress",
            "priority": "high",
            "assignees": ["coding-agent", "@security-auditor-agent"],
            "labels": ["backend", "security", "auth"],
            "details": "Detailed implementation plan with multiple steps...",
            "created_at": "2025-09-12T10:00:00Z",
            "updated_at": "2025-09-12T14:30:00Z",
            "due_date": "2025-09-15T00:00:00Z",
            "estimated_effort": "3 days",
            "actual_effort": "1.5 days",
            "completion_percentage": 60,
            "blockers": ["Waiting for API design approval"],
            "dependencies": ["task-111", "task-112"],
            "subtasks": [
                {"id": "sub-1", "title": "Design schema", "status": "done"},
                {"id": "sub-2", "title": "Implement endpoints", "status": "in_progress"}
            ],
            "comments": [
                {"author": "user1", "text": "Please prioritize this", "timestamp": "2025-09-12T11:00:00Z"},
                {"author": "user2", "text": "Working on it", "timestamp": "2025-09-12T12:00:00Z"}
            ],
            "attachments": [
                {"name": "design.pdf", "size": 1024000, "url": "https://example.com/design.pdf"}
            ],
            "metadata": {
                "version": "1.0",
                "tags": ["critical", "customer-facing"],
                "custom_field_1": "value1",
                "custom_field_2": "value2"
            }
        }

    def test_minimal_profile_selection(self, selector, sample_task_context):
        """Test minimal profile field selection"""
        result = selector.select_fields(
            sample_task_context,
            profile=SelectionProfile.MINIMAL
        )
        
        # Should only include essential fields
        assert "id" in result
        assert "title" in result
        assert "status" in result
        assert "priority" in result
        
        # Should exclude detailed fields
        assert "description" not in result
        assert "details" not in result
        assert "comments" not in result
        assert "attachments" not in result

    def test_standard_profile_selection(self, selector, sample_task_context):
        """Test standard profile field selection"""
        result = selector.select_fields(
            sample_task_context,
            profile=SelectionProfile.STANDARD
        )
        
        # Should include standard fields
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "status" in result
        assert "priority" in result
        assert "assignees" in result
        assert "labels" in result
        
        # Should exclude verbose fields
        assert "comments" not in result
        assert "attachments" not in result
        assert "metadata" not in result

    def test_detailed_profile_selection(self, selector, sample_task_context):
        """Test detailed profile field selection"""
        result = selector.select_fields(
            sample_task_context,
            profile=SelectionProfile.DETAILED
        )
        
        # Should include most fields
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "details" in result
        assert "assignees" in result
        assert "dependencies" in result
        assert "subtasks" in result
        
        # Might still exclude some fields
        assert len(result) > len(selector.select_fields(sample_task_context, SelectionProfile.STANDARD))

    def test_complete_profile_selection(self, selector, sample_task_context):
        """Test complete profile returns all fields"""
        result = selector.select_fields(
            sample_task_context,
            profile=SelectionProfile.COMPLETE
        )
        
        # Should include all fields
        assert result == sample_task_context
        assert "comments" in result
        assert "attachments" in result
        assert "metadata" in result

    def test_custom_field_selection(self, selector, sample_task_context):
        """Test custom field selection"""
        custom_fields = ["id", "title", "assignees", "blockers"]
        
        result = selector.select_fields(
            sample_task_context,
            custom_fields=custom_fields
        )
        
        # Should only include specified fields
        assert set(result.keys()) == set(custom_fields)
        assert result["id"] == "task-123"
        assert result["title"] == "Implement authentication"
        assert result["assignees"] == ["coding-agent", "@security-auditor-agent"]
        assert result["blockers"] == ["Waiting for API design approval"]

    def test_exclude_fields(self, selector, sample_task_context):
        """Test field exclusion"""
        result = selector.select_fields(
            sample_task_context,
            profile=SelectionProfile.STANDARD,
            exclude_fields=["assignees", "labels", "created_at", "updated_at"]
        )
        
        # Should not include excluded fields
        assert "assignees" not in result
        assert "labels" not in result
        assert "created_at" not in result
        assert "updated_at" not in result
        
        # Should still include other standard fields
        assert "id" in result
        assert "title" in result
        assert "status" in result

    def test_action_based_selection(self, selector, sample_task_context):
        """Test action-based field selection"""
        # List action should use minimal fields
        result = selector.select_fields_for_action(
            sample_task_context,
            action="list"
        )
        assert "id" in result
        assert "title" in result
        assert "details" not in result
        
        # Get action should use standard fields
        result = selector.select_fields_for_action(
            sample_task_context,
            action="get"
        )
        assert "description" in result
        assert "assignees" in result
        
        # Update action might need more fields
        result = selector.select_fields_for_action(
            sample_task_context,
            action="update"
        )
        assert len(result) >= len(selector.select_fields(sample_task_context, SelectionProfile.STANDARD))

    def test_nested_field_selection(self, selector):
        """Test selection of nested fields"""
        context = {
            "id": "123",
            "user": {
                "id": "user-1",
                "name": "John Doe",
                "email": "john@example.com",
                "profile": {
                    "avatar": "https://example.com/avatar.jpg",
                    "bio": "Software developer",
                    "preferences": {
                        "theme": "dark",
                        "notifications": True
                    }
                }
            }
        }
        
        # Select specific nested fields
        custom_fields = ["id", "user.name", "user.profile.bio"]
        result = selector.select_fields(context, custom_fields=custom_fields)
        
        assert result["id"] == "123"
        assert result["user"]["name"] == "John Doe"
        assert result["user"]["profile"]["bio"] == "Software developer"
        assert "email" not in result["user"]
        assert "preferences" not in result["user"]["profile"]

    def test_array_field_handling(self, selector, sample_task_context):
        """Test handling of array fields"""
        # Select fields including arrays
        result = selector.select_fields(
            sample_task_context,
            custom_fields=["id", "subtasks", "assignees"]
        )
        
        assert isinstance(result["subtasks"], list)
        assert len(result["subtasks"]) == 2
        assert isinstance(result["assignees"], list)
        assert len(result["assignees"]) == 2

    def test_field_size_limits(self, selector):
        """Test field size limiting"""
        large_context = {
            "id": "123",
            "title": "Task",
            "description": "x" * 10000,  # Very large description
            "details": "y" * 50000,  # Extremely large details
            "small_field": "small value"
        }
        
        # Apply size limits
        result = selector.select_fields(
            large_context,
            profile=SelectionProfile.STANDARD,
            max_field_size=1000
        )
        
        # Large fields should be truncated
        assert len(result["description"]) <= 1000
        if "details" in result:
            assert len(result["details"]) <= 1000
        assert result["small_field"] == "small value"

    def test_profile_configuration(self, selector):
        """Test custom profile configuration"""
        # Configure custom profile
        custom_config = FieldSelectionConfig(
            include_fields=["id", "title", "status", "custom_importance"],
            exclude_patterns=["*_at", "metadata.*"],
            max_depth=2
        )
        
        selector.configure_profile("custom", custom_config)
        
        context = {
            "id": "123",
            "title": "Task",
            "status": "open",
            "custom_importance": "high",
            "created_at": "2025-09-12",
            "updated_at": "2025-09-12",
            "metadata": {"key": "value"}
        }
        
        result = selector.select_fields(context, profile="custom")
        
        assert "custom_importance" in result
        assert "created_at" not in result  # Excluded by pattern
        assert "metadata" not in result  # Excluded by pattern

    def test_dynamic_field_discovery(self, selector):
        """Test dynamic field discovery from context"""
        contexts = [
            {"id": "1", "title": "Task 1", "special_field": "value1"},
            {"id": "2", "title": "Task 2", "another_field": "value2"},
            {"id": "3", "title": "Task 3", "special_field": "value3", "another_field": "value4"}
        ]
        
        # Discover common fields
        common_fields = selector.discover_common_fields(contexts)
        assert "id" in common_fields
        assert "title" in common_fields
        
        # Discover all fields
        all_fields = selector.discover_all_fields(contexts)
        assert "special_field" in all_fields
        assert "another_field" in all_fields

    def test_field_importance_scoring(self, selector, sample_task_context):
        """Test field importance scoring"""
        # Score fields by importance
        scores = selector.score_field_importance(sample_task_context)
        
        # Essential fields should have high scores
        assert scores.get("id", 0) > scores.get("metadata", 0)
        assert scores.get("title", 0) > scores.get("attachments", 0)
        assert scores.get("status", 0) > scores.get("comments", 0)

    def test_conditional_field_inclusion(self, selector):
        """Test conditional field inclusion based on values"""
        context = {
            "id": "123",
            "title": "Task",
            "status": "completed",
            "completion_date": "2025-09-12",
            "failure_reason": None,
            "success_metrics": {"accuracy": 0.95}
        }
        
        # Include completion fields only if status is completed
        result = selector.select_fields(
            context,
            conditional_rules={
                "completion_date": lambda ctx: ctx.get("status") == "completed",
                "failure_reason": lambda ctx: ctx.get("status") == "failed",
                "success_metrics": lambda ctx: ctx.get("status") == "completed"
            }
        )
        
        assert "completion_date" in result
        assert "success_metrics" in result
        assert "failure_reason" not in result  # None value and condition not met

    def test_field_transformation(self, selector):
        """Test field transformation during selection"""
        context = {
            "id": "123",
            "title": "  Task Title  ",  # Extra whitespace
            "assignees": "agent1,agent2,agent3",  # String instead of array
            "priority": 1  # Number instead of string
        }
        
        # Apply transformations
        transformations = {
            "title": lambda x: x.strip(),
            "assignees": lambda x: x.split(",") if isinstance(x, str) else x,
            "priority": lambda x: ["low", "medium", "high"][x-1] if isinstance(x, int) else x
        }
        
        result = selector.select_fields(
            context,
            transformations=transformations
        )
        
        assert result["title"] == "Task Title"
        assert result["assignees"] == ["agent1", "agent2", "agent3"]
        assert result["priority"] == "low"

    def test_performance_optimization(self, selector):
        """Test performance with large contexts"""
        import time
        
        # Create large context
        large_context = {
            f"field_{i}": f"value_{i}" * 100
            for i in range(1000)
        }
        large_context["id"] = "123"
        large_context["title"] = "Large Task"
        
        # Measure selection time
        start = time.time()
        result = selector.select_fields(
            large_context,
            profile=SelectionProfile.MINIMAL
        )
        elapsed = time.time() - start
        
        # Should be fast even with large context
        assert elapsed < 0.1  # Less than 100ms
        assert len(result) < len(large_context)  # Should filter fields

    def test_caching_field_configurations(self, selector):
        """Test caching of field configurations"""
        # First call should compute configuration
        config1 = selector.get_profile_config(SelectionProfile.STANDARD)
        
        # Second call should use cache
        config2 = selector.get_profile_config(SelectionProfile.STANDARD)
        
        # Should be the same object (cached)
        assert config1 is config2

    def test_merge_field_selections(self, selector):
        """Test merging multiple field selections"""
        context = {
            "id": "123",
            "title": "Task",
            "description": "Description",
            "status": "open",
            "priority": "high",
            "assignees": ["agent1"],
            "details": "Detailed info"
        }
        
        # Select different field sets
        minimal = selector.select_fields(context, profile=SelectionProfile.MINIMAL)
        custom = selector.select_fields(context, custom_fields=["description", "assignees", "details"])
        
        # Merge selections
        merged = selector.merge_selections([minimal, custom])
        
        # Should include fields from both selections
        assert "id" in merged  # From minimal
        assert "title" in merged  # From minimal
        assert "description" in merged  # From custom
        assert "details" in merged  # From custom