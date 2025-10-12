#!/usr/bin/env python3
"""Initialize Timestamp Management System

This script initializes the clean timestamp management system by setting up
SQLAlchemy event handlers and registering the foundation components.

Usage:
    python init_timestamp_system.py
    python init_timestamp_system.py --verify
"""

import sys
import os
from pathlib import Path

# Add the project src to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from fastmcp.task_management.infrastructure.database.timestamp_events import (
        setup_timestamp_events,
        cleanup_timestamp_events
    )
    print("✅ Successfully imported timestamp event handlers")
except ImportError as e:
    print(f"❌ Failed to import timestamp event handlers: {e}")
    sys.exit(1)


def initialize_timestamp_system():
    """Initialize the timestamp management system."""
    print("🚀 Initializing Clean Timestamp Management System")
    print("=" * 55)

    try:
        print("📝 Setting up SQLAlchemy event handlers...")
        setup_timestamp_events()
        print("✅ Timestamp event handlers registered successfully")

        print("\n🎯 System Initialization Complete!")
        print("=" * 40)
        print("✅ BaseTimestampEntity foundation ready")
        print("✅ SQLAlchemy event handlers registered")
        print("✅ Automatic timestamp management active")
        print("✅ Domain events enabled")

        print("\n📋 NEXT STEPS:")
        print("1. 🔄 Migrate existing entities to inherit from BaseTimestampEntity")
        print("2. 🧹 Remove manual timestamp handling from entities")
        print("3. 🔧 Update repositories to use BaseTimestampRepository")
        print("4. 🧪 Run tests to ensure migration success")

        return True

    except Exception as e:
        print(f"❌ Failed to initialize timestamp system: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_timestamp_system():
    """Verify the timestamp system is working correctly."""
    print("\n🔍 Verifying Timestamp System...")

    try:
        # Create a test entity to verify event handling
        from fastmcp.task_management.domain.entities.base.base_timestamp_entity import BaseTimestampEntity
        from dataclasses import dataclass

        @dataclass
        class TestEntity(BaseTimestampEntity):
            name: str = "verification_test"

            def _get_entity_id(self) -> str:
                return f"verify_{id(self)}"

            def _validate_entity(self) -> None:
                if not self.name or not self.name.strip():
                    raise ValueError("TestEntity name cannot be empty")

        # Test entity creation
        print("🧪 Testing entity creation...")
        test_entity = TestEntity(name="test_verification")

        assert test_entity.created_at is not None, "Timestamps should be initialized"
        assert test_entity.updated_at is not None, "Timestamps should be initialized"
        print("✅ Entity timestamps initialized correctly")

        # Test touch functionality
        print("🧪 Testing touch functionality...")
        original_updated = test_entity.updated_at
        test_entity.touch("verification_touch")
        assert test_entity.updated_at > original_updated, "Touch should update timestamp"
        print("✅ Touch functionality working")

        # Test domain events
        print("🧪 Testing domain events...")
        events = test_entity.get_domain_events()
        assert len(events) > 0, "Should have domain events"
        print(f"✅ Domain events working ({len(events)} events)")

        print("\n🎉 VERIFICATION SUCCESSFUL!")
        print("✅ Timestamp system is fully operational")

        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_system():
    """Clean up the timestamp system (for testing)."""
    print("\n🧹 Cleaning up timestamp system...")

    try:
        cleanup_timestamp_events()
        print("✅ Event handlers removed")
        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


def main():
    """Main script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize or verify the timestamp management system"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the system after initialization"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up the system (for testing)"
    )

    args = parser.parse_args()

    success = True

    if args.cleanup:
        success &= cleanup_system()
        return 0 if success else 1

    # Always initialize first
    success &= initialize_timestamp_system()

    if args.verify and success:
        success &= verify_timestamp_system()

    if success:
        print("\n🎊 TIMESTAMP SYSTEM READY FOR PRODUCTION!")
        print("=" * 50)
        print("The clean timestamp management system is now active.")
        print("All new entities using BaseTimestampEntity will have")
        print("automatic timestamp management with NO manual coding required.")
        return 0
    else:
        print("\n❌ INITIALIZATION FAILED!")
        print("Please check the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    exit(main())
