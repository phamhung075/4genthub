#!/usr/bin/env python3
"""
Test WebSocket notification flow end-to-end
This script will test the complete WebSocket notification chain
"""
import sys
import asyncio
import logging
sys.path.insert(0, '/home/daihungpham/__projects__/4genthub/agenthub_main/src')

from fastmcp.task_management.application.services.websocket_notification_service import WebSocketNotificationService

# Set up logging to see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_notification():
    """Test the complete WebSocket notification flow"""

    print("🧪 Testing WebSocket Notification Flow")
    print("=" * 50)

    # Test parameters
    test_task_id = "test-task-123"
    test_user_id = "test-user-456"
    test_branch_id = "test-branch-789"

    test_task_data = {
        "id": test_task_id,
        "title": "Test Task",
        "status": "created",
        "priority": "high"
    }

    try:
        print("🔍 Step 1: Testing sync_broadcast_task_event...")

        # Call the sync method that the use cases are calling
        result = WebSocketNotificationService.sync_broadcast_task_event(
            event_type="created",
            task_id=test_task_id,
            user_id=test_user_id,
            task_data=test_task_data,
            git_branch_id=test_branch_id
        )

        print(f"✅ sync_broadcast_task_event completed")
        print(f"   Result: {result}")

    except Exception as e:
        print(f"❌ sync_broadcast_task_event failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

    try:
        print("\n🔍 Step 2: Testing async broadcast_task_event...")

        # Test the async version
        await WebSocketNotificationService.broadcast_task_event(
            event_type="updated",
            task_id=test_task_id,
            user_id=test_user_id,
            task_data=test_task_data,
            git_branch_id=test_branch_id
        )

        print(f"✅ broadcast_task_event completed")

    except Exception as e:
        print(f"❌ broadcast_task_event failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

    try:
        print("\n🔍 Step 3: Testing direct broadcast_data_change...")

        # Test the direct broadcast function
        from fastmcp.server.routes.websocket_routes import broadcast_data_change

        await broadcast_data_change(
            event_type="deleted",
            entity_type="task",
            entity_id=test_task_id,
            user_id=test_user_id,
            data=test_task_data,
            metadata={"git_branch_id": test_branch_id}
        )

        print(f"✅ broadcast_data_change completed")

    except Exception as e:
        print(f"❌ broadcast_data_change failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('/home/daihungpham/__projects__/4genthub/.env')

    asyncio.run(test_websocket_notification())