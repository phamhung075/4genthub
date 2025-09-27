#!/usr/bin/env python3
"""Test cascade deletion functionality"""

import os
import sys
import asyncio
from datetime import datetime

# Add the source directory to path
sys.path.insert(0, './agenthub_main/src')

# Set environment variables
os.environ['DATABASE_HOST'] = 'localhost'
os.environ['DATABASE_USER'] = 'postgres'
os.environ['DATABASE_PASSWORD'] = 'P02tqbj016p9'
os.environ['DATABASE_NAME'] = 'postgresdb'
os.environ['DATABASE_TYPE'] = 'postgresql'
os.environ['DATABASE_SSL_MODE'] = 'disable'
os.environ['ENV'] = 'development'
os.environ['CONTAINER_ENV'] = 'local'

async def test_cascade_deletion():
    """Test the enhanced cascade deletion"""
    print("=" * 60)
    print("Testing Enhanced Cascade Deletion")
    print(f"Time: {datetime.now()}")
    print("=" * 60)

    try:
        # Import and initialize the task repository
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.database.database_config import get_db_session

        # Create repository with user ID
        user_id = 'f0de4c5d-2a97-4324-abcd-9dae3922761e'
        task_repo = ORMTaskRepository(user_id=user_id)

        test_task_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

        print(f"\n[TEST] Deleting task {test_task_id} with enhanced cascade deletion...")

        # Test the enhanced delete_task method
        result = task_repo.delete_task(test_task_id)

        if result:
            print("✅ Task deletion successful!")

            # Verify that related task_contexts were also deleted
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                database='postgresdb',
                user='postgres',
                password='P02tqbj016p9'
            )
            cursor = conn.cursor()

            # Check if task still exists (should not)
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = %s", (test_task_id,))
            task_count = cursor.fetchone()[0]

            # Check if task_contexts still exist (should not)
            cursor.execute("SELECT COUNT(*) FROM task_contexts WHERE task_id = %s", (test_task_id,))
            context_count = cursor.fetchone()[0]

            print(f"   Tasks remaining: {task_count} (should be 0)")
            print(f"   Task contexts remaining: {context_count} (should be 0)")

            if task_count == 0 and context_count == 0:
                print("✅ CASCADE DELETION SUCCESSFUL - All related data cleaned up!")
            else:
                print("❌ CASCADE DELETION FAILED - Some related data still exists")

            conn.close()
        else:
            print("❌ Task deletion failed")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cascade_deletion())