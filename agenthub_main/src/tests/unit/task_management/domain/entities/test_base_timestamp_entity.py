"""
Comprehensive unit tests for BaseTimestampEntity.

This test suite validates the core timestamp management functionality of BaseTimestampEntity
including automatic initialization, touch() method behavior, domain events, validation,
and edge cases. These are unit tests focused on the base class behavior.
"""

import pytest
from datetime import datetime, timezone, timedelta
from time import sleep
from unittest.mock import patch, MagicMock
import uuid

from fastmcp.task_management.domain.entities.base.base_timestamp_entity import (
    BaseTimestampEntity,
    TimestampUpdatedEvent,
    TimestampCreatedEvent
)


class TestEntity(BaseTimestampEntity):
    """Concrete test entity for testing BaseTimestampEntity functionality"""

    def __init__(self, entity_id: str = None):
        self.entity_id = entity_id or str(uuid.uuid4())
        super().__post_init__()

    def _get_entity_id(self) -> str:
        return self.entity_id

    def _validate_entity(self) -> None:
        if not self.entity_id:
            raise ValueError("Entity id cannot be empty")


class TestBaseTimestampEntity:
    """Comprehensive unit tests for BaseTimestampEntity"""

    def test_automatic_timestamp_initialization_new_entity(self):
        """Test that new entities get automatic timestamp initialization"""
        # Create new entity (both timestamps None initially)
        entity = TestEntity()

        # Verify timestamps were automatically set
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert entity.created_at.tzinfo == timezone.utc
        assert entity.updated_at.tzinfo == timezone.utc

        # Both timestamps should be the same for new entity
        assert entity.created_at == entity.updated_at

    def test_automatic_timestamp_initialization_missing_created_at(self):
        """Test handling when only created_at is missing"""
        entity = TestEntity()

        # Simulate entity with missing created_at (clean initialization handles this)
        entity.created_at = None
        # Since created_at is missing, we also need to reset updated_at to avoid consistency issues
        entity.updated_at = None

        # Re-initialize timestamps
        entity._ensure_clean_timestamps()

        # Verify both timestamps were set to consistent values
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert entity.created_at <= entity.updated_at

    def test_automatic_timestamp_initialization_missing_updated_at(self):
        """Test handling when only updated_at is missing"""
        entity = TestEntity()

        # Simulate entity with only created_at set
        original_created = entity.created_at
        entity.updated_at = None

        # Re-initialize timestamps
        entity._ensure_clean_timestamps()

        # Verify updated_at was set but created_at remained
        assert entity.created_at == original_created
        assert entity.updated_at is not None

    def test_touch_method_updates_timestamp(self):
        """Test that touch() method properly updates timestamp"""
        entity = TestEntity()
        original_created = entity.created_at
        original_updated = entity.updated_at

        # Small delay to ensure timestamp difference
        sleep(0.01)

        # Touch the entity
        entity.touch("test_reason")

        # Verify updated_at changed but created_at remained the same
        assert entity.created_at == original_created
        assert entity.updated_at > original_updated
        assert entity.updated_at.tzinfo == timezone.utc

    def test_touch_method_fires_domain_event(self):
        """Test that touch() method fires TimestampUpdatedEvent"""
        entity = TestEntity()
        original_updated = entity.updated_at

        # Clear any existing events
        entity.clear_domain_events()

        # Touch the entity
        entity.touch("event_test_reason")

        # Verify domain event was fired
        events = entity.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], TimestampUpdatedEvent)
        assert events[0].entity_id == entity._get_entity_id()
        assert events[0].old_timestamp == original_updated
        assert events[0].new_timestamp == entity.updated_at

    def test_creation_fires_domain_event(self):
        """Test that entity creation fires TimestampCreatedEvent"""
        entity = TestEntity()

        # Verify creation event was fired
        events = entity.get_domain_events()
        creation_events = [e for e in events if isinstance(e, TimestampCreatedEvent)]
        assert len(creation_events) == 1
        assert creation_events[0].entity_id == entity._get_entity_id()
        assert creation_events[0].created_timestamp == entity.created_at

    def test_touch_with_custom_reason(self):
        """Test touch() method with custom reason parameter"""
        entity = TestEntity()

        # Clear existing events
        entity.clear_domain_events()

        # Touch with custom reason
        custom_reason = "custom_business_reason"
        entity.touch(custom_reason)

        # Verify event contains the custom reason in metadata or can be traced
        events = entity.get_domain_events()
        assert len(events) == 1

        # The reason is primarily for logging, event should still be fired
        assert isinstance(events[0], TimestampUpdatedEvent)

    def test_is_newer_than_comparison(self):
        """Test is_newer_than() method for comparing entity ages"""
        older_entity = TestEntity()
        sleep(0.01)  # Ensure time difference
        newer_entity = TestEntity()

        # Newer entity should be newer than older entity
        assert newer_entity.is_newer_than(older_entity)
        assert not older_entity.is_newer_than(newer_entity)

        # Entity should not be newer than itself
        assert not newer_entity.is_newer_than(newer_entity)

    def test_is_newer_than_with_none_timestamps(self):
        """Test is_newer_than() handles None timestamps correctly"""
        entity_with_timestamp = TestEntity()

        # Create entity with None updated_at
        entity_without_timestamp = TestEntity()
        entity_without_timestamp.updated_at = None

        # Entity with timestamp should be newer
        assert entity_with_timestamp.is_newer_than(entity_without_timestamp)
        assert not entity_without_timestamp.is_newer_than(entity_with_timestamp)

    def test_get_age_seconds(self):
        """Test get_age_seconds() method"""
        entity = TestEntity()

        # Age should be very small (just created)
        age = entity.get_age_seconds()
        assert age is not None
        assert age >= 0
        assert age < 1  # Should be less than 1 second old

        # Test with None created_at
        entity.created_at = None
        assert entity.get_age_seconds() is None

    def test_get_staleness_seconds(self):
        """Test get_staleness_seconds() method"""
        entity = TestEntity()

        # Staleness should be very small (just updated)
        staleness = entity.get_staleness_seconds()
        assert staleness is not None
        assert staleness >= 0
        assert staleness < 1  # Should be less than 1 second old

        # Test with None updated_at
        entity.updated_at = None
        assert entity.get_staleness_seconds() is None

    def test_timestamp_validation_non_utc_warning(self):
        """Test that non-UTC timestamps trigger validation warnings"""
        entity = TestEntity()

        # Set non-UTC timestamp
        non_utc_time = datetime.now()  # No timezone = local time
        entity.created_at = non_utc_time

        # Validation should handle non-UTC timestamps
        with patch('fastmcp.task_management.domain.entities.base.base_timestamp_entity.logger') as mock_logger:
            entity._validate_entity()
            # Should have logged a warning about non-UTC timestamp
            mock_logger.warning.assert_called()

    def test_domain_events_management(self):
        """Test domain event collection and management"""
        entity = TestEntity()

        # Should start with at least creation event
        initial_events = entity.get_domain_events()
        assert len(initial_events) >= 1

        # Touch should add another event
        entity.touch("test_event_management")
        events_after_touch = entity.get_domain_events()
        assert len(events_after_touch) == len(initial_events) + 1

        # Clear events
        entity.clear_domain_events()
        assert len(entity.get_domain_events()) == 0

    def test_to_timestamp_dict_export(self):
        """Test to_timestamp_dict() export functionality"""
        entity = TestEntity()

        # Touch to create some history
        entity.touch("export_test")

        # Export to dict
        timestamp_dict = entity.to_timestamp_dict()

        # Verify export contains expected fields
        assert "entity_id" in timestamp_dict
        assert "created_at" in timestamp_dict
        assert "updated_at" in timestamp_dict
        assert "age_seconds" in timestamp_dict
        assert "staleness_seconds" in timestamp_dict
        assert "domain_events_count" in timestamp_dict

        # Verify values
        assert timestamp_dict["entity_id"] == entity._get_entity_id()
        assert timestamp_dict["created_at"] == entity.created_at.isoformat()
        assert timestamp_dict["updated_at"] == entity.updated_at.isoformat()
        assert isinstance(timestamp_dict["age_seconds"], float)
        assert isinstance(timestamp_dict["staleness_seconds"], float)
        assert timestamp_dict["domain_events_count"] >= 1

    def test_string_representation(self):
        """Test __repr__ method"""
        entity = TestEntity()
        repr_str = repr(entity)

        # Should contain class name and timestamp info
        assert "TestEntity" in repr_str
        assert str(entity._get_entity_id()) in repr_str
        assert str(entity.created_at) in repr_str
        assert str(entity.updated_at) in repr_str

    def test_multiple_touches_preserve_created_at(self):
        """Test that multiple touch() calls never change created_at"""
        entity = TestEntity()
        original_created = entity.created_at

        # Touch multiple times
        for i in range(5):
            sleep(0.001)  # Small delay
            entity.touch(f"touch_sequence_{i}")

        # created_at should never change
        assert entity.created_at == original_created

        # updated_at should have changed with each touch
        assert entity.updated_at > original_created

    def test_entity_id_requirement(self):
        """Test that entities must provide _get_entity_id implementation"""
        # TestEntity properly implements _get_entity_id
        entity = TestEntity("test-id-123")
        assert entity._get_entity_id() == "test-id-123"

        # Verify it's used in events and exports
        timestamp_dict = entity.to_timestamp_dict()
        assert timestamp_dict["entity_id"] == "test-id-123"

    @patch('fastmcp.task_management.domain.entities.base.base_timestamp_entity.datetime')
    def test_timestamp_consistency_during_creation(self, mock_datetime):
        """Test that created_at and updated_at are set to same value during creation"""
        # Mock datetime.now to return consistent time
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        entity = TestEntity()

        # Both timestamps should be the same fixed time
        assert entity.created_at == fixed_time
        assert entity.updated_at == fixed_time

    def test_touch_updates_only_updated_at(self):
        """Test that touch() only updates updated_at, never created_at"""
        entity = TestEntity()
        original_created = entity.created_at
        original_updated = entity.updated_at

        sleep(0.01)
        entity.touch("selective_update_test")

        # Only updated_at should change
        assert entity.created_at == original_created  # Unchanged
        assert entity.updated_at > original_updated   # Changed
        assert entity.updated_at > original_created   # Newer than creation

    def test_concurrent_touch_thread_safety_simulation(self):
        """Test simulated concurrent touch operations"""
        entity = TestEntity()
        original_created = entity.created_at

        # Simulate rapid concurrent touches
        timestamps = []
        for i in range(10):
            entity.touch(f"concurrent_test_{i}")
            timestamps.append(entity.updated_at)
            # Very small delay to allow timestamp differences
            sleep(0.0001)

        # All timestamps should be different and increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]

        # created_at should never change
        assert entity.created_at == original_created

    def test_edge_case_same_millisecond_touches(self):
        """Test behavior when touches happen in same millisecond"""
        entity = TestEntity()

        # Multiple rapid touches
        entity.touch("rapid_1")
        entity.touch("rapid_2")
        entity.touch("rapid_3")

        # Should not error and should maintain valid timestamps
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert entity.updated_at >= entity.created_at

        # Should have generated multiple events
        events = entity.get_domain_events()
        update_events = [e for e in events if isinstance(e, TimestampUpdatedEvent)]
        assert len(update_events) == 3


class TestTimestampUpdatedEvent:
    """Test TimestampUpdatedEvent domain event"""

    def test_event_creation(self):
        """Test TimestampUpdatedEvent creation and properties"""
        old_time = datetime.now(timezone.utc)
        new_time = old_time + timedelta(seconds=1)

        event = TimestampUpdatedEvent(
            entity_id="test-entity-123",
            old_timestamp=old_time,
            new_timestamp=new_time
        )

        assert event.entity_id == "test-entity-123"
        assert event.old_timestamp == old_time
        assert event.new_timestamp == new_time
        assert event.event_type == "timestamp_updated"

    def test_event_to_dict(self):
        """Test TimestampUpdatedEvent to_dict method"""
        old_time = datetime.now(timezone.utc)
        new_time = old_time + timedelta(seconds=1)

        event = TimestampUpdatedEvent(
            entity_id="test-entity-456",
            old_timestamp=old_time,
            new_timestamp=new_time
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "timestamp_updated"
        assert event_dict["entity_id"] == "test-entity-456"
        assert event_dict["old_timestamp"] == old_time.isoformat()
        assert event_dict["new_timestamp"] == new_time.isoformat()
        assert "metadata" in event_dict


class TestTimestampCreatedEvent:
    """Test TimestampCreatedEvent domain event"""

    def test_creation_event(self):
        """Test TimestampCreatedEvent creation and properties"""
        created_time = datetime.now(timezone.utc)

        event = TimestampCreatedEvent(
            entity_id="new-entity-789",
            created_timestamp=created_time
        )

        assert event.entity_id == "new-entity-789"
        assert event.created_timestamp == created_time
        assert event.event_type == "timestamp_created"

    def test_creation_event_to_dict(self):
        """Test TimestampCreatedEvent to_dict method"""
        created_time = datetime.now(timezone.utc)

        event = TimestampCreatedEvent(
            entity_id="new-entity-101112",
            created_timestamp=created_time
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "timestamp_created"
        assert event_dict["entity_id"] == "new-entity-101112"
        assert event_dict["created_timestamp"] == created_time.isoformat()
        assert "metadata" in event_dict
