#!/usr/bin/env python3
"""
Test script to verify the WebSocket system message authorization fix.

This script tests that:
1. System messages reach only the resource owner
2. System messages are blocked for non-owners
3. Regular user messages still work as before
"""

import asyncio
import uuid
from unittest.mock import Mock, MagicMock
import sys
import os

async def test_system_message_authorization():
    """Test the WebSocket system message authorization logic."""

    # Import the function we're testing
    from fastmcp.server.routes.websocket_routes import is_user_authorized_for_message, _check_resource_ownership
    from fastmcp.auth.domain.entities.user import User

    print("🧪 Testing WebSocket System Message Authorization Fix")
    print("=" * 60)

    # Create mock users
    user1 = User(id="user123", email="user1@example.com")
    user2 = User(id="user456", email="user2@example.com")

    # Create mock WebSocket connections
    websocket1 = Mock()
    websocket2 = Mock()

    # Mock the connection_users dictionary
    from fastmcp.server.routes import websocket_routes
    websocket_routes.connection_users = {
        websocket1: user1,
        websocket2: user2
    }

    # Test 1: User receives their own messages (existing behavior)
    print("Test 1: User receives their own messages")
    result = await is_user_authorized_for_message(
        websocket=websocket1,
        entity_type="task",
        entity_id="task123",
        triggering_user_id="user123"  # Same as websocket1 user
    )
    print(f"  Result: {result} (Expected: True)")
    assert result == True, "User should receive their own messages"
    print("  ✅ PASSED")

    # Test 2: User does NOT receive other user's messages (existing behavior)
    print("\nTest 2: User does NOT receive other user's messages")
    result = await is_user_authorized_for_message(
        websocket=websocket1,
        entity_type="task",
        entity_id="task123",
        triggering_user_id="user456"  # Different from websocket1 user
    )
    print(f"  Result: {result} (Expected: False)")
    assert result == False, "User should NOT receive other user's messages"
    print("  ✅ PASSED")

    # Test 3: System message authorization - this is our new functionality
    print("\nTest 3: System message calls resource ownership check")

    # Mock the database session to simulate task ownership
    from unittest.mock import patch

    with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:
        # Create mock database objects
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None

        # Create mock task that belongs to user1
        mock_task = Mock()
        mock_task.user_id = "user123"  # Owned by user1
        mock_session.query().filter().first.return_value = mock_task

        # Test: User1 should receive system message about their own task
        print("  Subtest 3a: User receives system message about their own task")
        result = await is_user_authorized_for_message(
            websocket=websocket1,  # user123's connection
            entity_type="task",
            entity_id="task123",
            triggering_user_id="system"  # System message
        )
        print(f"    Result: {result} (Expected: True)")
        assert result == True, "User should receive system messages about their own tasks"
        print("    ✅ PASSED")

        # Test: User2 should NOT receive system message about user1's task
        print("  Subtest 3b: User does NOT receive system message about other's task")
        mock_session.query().filter().first.return_value = None  # No task found for user2
        result = await is_user_authorized_for_message(
            websocket=websocket2,  # user456's connection
            entity_type="task",
            entity_id="task123",
            triggering_user_id="system"  # System message
        )
        print(f"    Result: {result} (Expected: False)")
        assert result == False, "User should NOT receive system messages about other's tasks"
        print("    ✅ PASSED")

    print("\n🎉 All tests passed! System message authorization works correctly.")
    print("\nSummary:")
    print("- ✅ Users still receive their own messages")
    print("- ✅ Users still blocked from other user's messages")
    print("- ✅ System messages reach only resource owners")
    print("- ✅ System messages blocked for non-owners")
    print("- ✅ Proper data isolation maintained")

if __name__ == "__main__":
    asyncio.run(test_system_message_authorization())