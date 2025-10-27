"""
Test suite for Context domain entity

Tests the context entity behavior and validation.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
import json

from fastmcp.task_management.domain.entities.context import Context
from fastmcp.task_management.domain.value_objects import ContextID, UserID
from fastmcp.task_management.domain.exceptions import ValidationError


class TestContextEntity:
    """Test suite for Context domain entity"""

    def test_create_minimal_context(self):
        """Test creating context with minimal required fields"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="project",
            entity_id=str(uuid4()),
            user_id=UserID("user123")
        )
        
        assert context.id is not None
        assert context.level == "project"
        assert context.entity_id is not None
        assert context.user_id.value == "user123"
        assert context.data == {}  # Default empty dict

    def test_create_context_with_data(self):
        """Test creating context with data"""
        context_data = {
            "theme": "dark",
            "preferences": {
                "notifications": True,
                "language": "en"
            },
            "settings": {
                "autosave": True
            }
        }
        
        context = Context(
            id=ContextID(str(uuid4())),
            level="user",
            entity_id="user123",
            user_id=UserID("user123"),
            data=context_data
        )
        
        assert context.data == context_data
        assert context.data["theme"] == "dark"
        assert context.data["preferences"]["notifications"] is True

    def test_context_hierarchy_levels(self):
        """Test all valid hierarchy levels"""
        levels = ["global", "project", "branch", "task"]
        entity_id = str(uuid4())
        
        for level in levels:
            context = Context(
                id=ContextID(str(uuid4())),
                level=level,
                entity_id=entity_id,
                user_id=UserID("user123")
            )
            assert context.level == level

    def test_invalid_context_level(self):
        """Test creating context with invalid level"""
        with pytest.raises(ValidationError, match="Invalid context level"):
            Context(
                id=ContextID(str(uuid4())),
                level="invalid_level",
                entity_id=str(uuid4()),
                user_id=UserID("user123")
            )

    def test_update_context_data(self):
        """Test updating context data"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="project",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data={"original": "value"}
        )
        
        # Update data
        context.update_data({"new": "data", "another": "field"})
        
        assert context.data == {"new": "data", "another": "field"}
        assert "original" not in context.data

    def test_merge_context_data(self):
        """Test merging context data"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="branch",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data={
                "existing": "value",
                "nested": {
                    "field1": "value1"
                }
            }
        )
        
        # Merge new data
        context.merge_data({
            "new": "field",
            "nested": {
                "field2": "value2"
            }
        })
        
        assert context.data["existing"] == "value"
        assert context.data["new"] == "field"
        assert context.data["nested"]["field1"] == "value1"
        assert context.data["nested"]["field2"] == "value2"

    def test_clear_context_data(self):
        """Test clearing context data"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="task",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data={"some": "data", "more": "fields"}
        )
        
        context.clear_data()
        
        assert context.data == {}

    def test_context_data_immutability(self):
        """Test that context data maintains proper encapsulation"""
        original_data = {"key": "value"}
        context = Context(
            id=ContextID(str(uuid4())),
            level="project",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data=original_data
        )
        
        # Modifying original dict shouldn't affect context
        original_data["new_key"] = "new_value"
        assert "new_key" not in context.data
        
        # Getting data and modifying shouldn't affect internal state
        retrieved_data = context.data
        retrieved_data["another_key"] = "another_value"
        # Note: This test depends on implementation - may need deep copy

    def test_context_insights(self):
        """Test adding and managing insights"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="task",
            entity_id=str(uuid4()),
            user_id=UserID("user123")
        )
        
        # Add insights
        context.add_insight("Performance can be improved with caching", "performance")
        context.add_insight("Consider using async operations", "performance")
        context.add_insight("Add input validation", "security")
        
        assert len(context.insights) == 3
        assert context.insights[0]["content"] == "Performance can be improved with caching"
        assert context.insights[0]["category"] == "performance"
        assert context.insights[2]["category"] == "security"

    def test_context_progress_tracking(self):
        """Test progress updates"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="task",
            entity_id=str(uuid4()),
            user_id=UserID("user123")
        )
        
        # Add progress updates
        context.add_progress("Started implementation", "coding-agent")
        context.add_progress("Completed 50% of features", "coding-agent")
        context.add_progress("Added unit tests", "test-agent")
        
        assert len(context.progress_updates) == 3
        assert context.progress_updates[0]["content"] == "Started implementation"
        assert context.progress_updates[0]["agent"] == "coding-agent"
        assert context.progress_updates[2]["agent"] == "test-agent"

    def test_context_serialization(self):
        """Test context can be serialized to dict"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="branch",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data={
                "config": {
                    "feature_flags": ["flag1", "flag2"],
                    "environment": "development"
                }
            }
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["id"] == context.id.value
        assert context_dict["level"] == "branch"
        assert context_dict["entity_id"] == context.entity_id
        assert context_dict["user_id"] == "user123"
        assert context_dict["data"] == context.data
        assert "created_at" in context_dict
        assert "updated_at" in context_dict

    def test_context_timestamp_updates(self):
        """Test timestamp behavior"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="project",
            entity_id=str(uuid4()),
            user_id=UserID("user123")
        )
        
        original_updated_at = context.updated_at
        
        # Any data update should update timestamp
        context.update_data({"new": "data"})
        
        assert context.updated_at > original_updated_at
        assert context.created_at < context.updated_at

    def test_global_context_user_scoped(self):
        """Test global context is properly user-scoped"""
        user1_context = Context(
            id=ContextID(str(uuid4())),
            level="global",
            entity_id="user123",  # For global, entity_id should be user_id
            user_id=UserID("user123"),
            data={"preference": "user1"}
        )
        
        user2_context = Context(
            id=ContextID(str(uuid4())),
            level="global",
            entity_id="user456",  # Different user
            user_id=UserID("user456"),
            data={"preference": "user2"}
        )
        
        assert user1_context.entity_id != user2_context.entity_id
        assert user1_context.data != user2_context.data

    def test_context_metadata(self):
        """Test context metadata fields"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="task",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            metadata={
                "source": "api",
                "version": "1.0",
                "tags": ["important", "phase1"]
            }
        )
        
        assert context.metadata["source"] == "api"
        assert "important" in context.metadata["tags"]

    def test_context_data_size_limits(self):
        """Test context handles large data appropriately"""
        # Create large nested structure
        large_data = {}
        for i in range(100):
            large_data[f"key_{i}"] = {
                "nested": {
                    "data": f"value_{i}" * 100  # Long strings
                }
            }
        
        context = Context(
            id=ContextID(str(uuid4())),
            level="project",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data=large_data
        )
        
        # Should handle large data without issues
        assert len(context.data) == 100
        
        # Serialization should work
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)

    def test_context_inheritance_metadata(self):
        """Test context tracks inheritance information"""
        parent_id = ContextID(str(uuid4()))
        context = Context(
            id=ContextID(str(uuid4())),
            level="branch",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            parent_context_id=parent_id,
            inheritance_enabled=True
        )
        
        assert context.parent_context_id == parent_id
        assert context.inheritance_enabled is True

    def test_context_empty_data_handling(self):
        """Test context handles empty and null data correctly"""
        context = Context(
            id=ContextID(str(uuid4())),
            level="task",
            entity_id=str(uuid4()),
            user_id=UserID("user123"),
            data=None  # Should default to empty dict
        )
        
        assert context.data == {}
        
        # Should be able to add data
        context.update_data({"new": "value"})
        assert context.data["new"] == "value"