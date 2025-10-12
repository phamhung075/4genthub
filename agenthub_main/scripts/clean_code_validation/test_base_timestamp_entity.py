#!/usr/bin/env python3
"""Test Script for BaseTimestampEntity Foundation

This script tests the basic functionality of the BaseTimestampEntity
foundation to ensure it works correctly before proceeding with the
full migration.

Usage:
    python test_base_timestamp_entity.py
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add the project src to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from fastmcp.task_management.domain.entities.base.base_timestamp_entity import (
        BaseTimestampEntity,
        TimestampCreatedEvent,
        TimestampUpdatedEvent
    )
    from dataclasses import dataclass

    print("✅ Successfully imported BaseTimestampEntity")
except ImportError as e:
    print(f"❌ Failed to import BaseTimestampEntity: {e}")
    sys.exit(1)


@dataclass
class TestEntity(BaseTimestampEntity):
    """Simple test entity for testing BaseTimestampEntity."""

    name: str = "test"

    def _get_entity_id(self) -> str:
        return f"test_{id(self)}"

    def _validate_entity(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("TestEntity name cannot be empty")


def test_basic_functionality():
    """Test basic BaseTimestampEntity functionality."""
    print("\n🧪 Testing basic functionality...")

    # Create a new entity
    entity = TestEntity(name="test_entity")

    # Check that timestamps were set
    assert entity.created_at is not None, "created_at should be set automatically"
    assert entity.updated_at is not None, "updated_at should be set automatically"
    assert entity.created_at.tzinfo == timezone.utc, "created_at should be in UTC"
    assert entity.updated_at.tzinfo == timezone.utc, "updated_at should be in UTC"

    print("✅ Timestamps initialized correctly")

    # Check initial timestamps are the same
    assert entity.created_at == entity.updated_at, "Initial timestamps should be equal"
    print("✅ Initial timestamps are equal")

    # Test domain events
    events = entity.get_domain_events()
    assert len(events) == 1, "Should have one creation event"
    assert isinstance(events[0], TimestampCreatedEvent), "Should be TimestampCreatedEvent"

    print("✅ Domain events working correctly")


def test_touch_functionality():
    """Test the touch() method."""
    print("\n🧪 Testing touch() functionality...")

    entity = TestEntity(name="touch_test")
    original_created_at = entity.created_at
    original_updated_at = entity.updated_at

    # Clear initial events
    entity.clear_domain_events()

    # Wait a moment to ensure timestamp difference
    import time
    time.sleep(0.001)

    # Touch the entity
    entity.touch("test_touch")

    # Check that updated_at changed but created_at didn't
    assert entity.created_at == original_created_at, "created_at should remain unchanged"
    assert entity.updated_at > original_updated_at, "updated_at should be newer"

    print("✅ Touch updates timestamps correctly")

    # Check domain event
    events = entity.get_domain_events()
    assert len(events) == 1, "Should have one update event"
    assert isinstance(events[0], TimestampUpdatedEvent), "Should be TimestampUpdatedEvent"

    print("✅ Touch generates correct domain events")


def test_comparison_methods():
    """Test entity comparison methods."""
    print("\n🧪 Testing comparison methods...")

    entity1 = TestEntity(name="entity1")

    # Wait to ensure timestamp difference
    import time
    time.sleep(0.001)

    entity2 = TestEntity(name="entity2")

    # Test is_newer_than
    assert entity2.is_newer_than(entity1), "entity2 should be newer than entity1"
    assert not entity1.is_newer_than(entity2), "entity1 should not be newer than entity2"

    print("✅ Comparison methods working correctly")


def test_utility_methods():
    """Test utility methods."""
    print("\n🧪 Testing utility methods...")

    entity = TestEntity(name="utility_test")

    # Test age calculation
    age = entity.get_age_seconds()
    assert age is not None, "Age should be calculated"
    assert age >= 0, "Age should be non-negative"

    # Test staleness calculation
    staleness = entity.get_staleness_seconds()
    assert staleness is not None, "Staleness should be calculated"
    assert staleness >= 0, "Staleness should be non-negative"

    # Test timestamp dict export
    timestamp_dict = entity.to_timestamp_dict()
    assert "entity_id" in timestamp_dict, "Should include entity_id"
    assert "created_at" in timestamp_dict, "Should include created_at"
    assert "updated_at" in timestamp_dict, "Should include updated_at"
    assert "age_seconds" in timestamp_dict, "Should include age_seconds"

    print("✅ Utility methods working correctly")


def test_domain_events():
    """Test domain event handling."""
    print("\n🧪 Testing domain event handling...")

    entity = TestEntity(name="events_test")

    # Get initial events
    initial_events = entity.get_domain_events()
    assert len(initial_events) >= 1, "Should have at least creation event"

    # Touch entity multiple times
    entity.touch("first_touch")
    entity.touch("second_touch")

    # Check event accumulation
    all_events = entity.get_domain_events()
    assert len(all_events) >= 3, "Should accumulate events"

    # Clear events
    entity.clear_domain_events()
    cleared_events = entity.get_domain_events()
    assert len(cleared_events) == 0, "Events should be cleared"

    print("✅ Domain event handling working correctly")


def main():
    """Run all tests."""
    print("🚀 Testing BaseTimestampEntity Foundation")
    print("=" * 50)

    try:
        test_basic_functionality()
        test_touch_functionality()
        test_comparison_methods()
        test_utility_methods()
        test_domain_events()

        print("\n🎉 ALL TESTS PASSED!")
        print("✅ BaseTimestampEntity foundation is working correctly")
        print("✅ Ready for Phase 2: Entity Migration")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
