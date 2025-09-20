#!/usr/bin/env python3
"""
Debug script to investigate task ID issue
This script will help identify where the wrong task IDs are coming from
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, '/home/daihungpham/__projects__/4genthub/agenthub_main/src')

import logging
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_task_ids():
    """Debug task IDs to identify the source of wrong IDs"""

    try:
        # Use SQLite database for debugging
        database_url = "sqlite:////data/agenthub.db"
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        print("🔍 DEBUGGING TASK IDS")
        print("=" * 80)

        # 1. Check what's in the actual database tables
        print("\n1. RAW DATABASE QUERY - Tasks table:")
        result = session.execute(text("""
            SELECT id, title, status, user_id, git_branch_id
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 5
        """))

        tasks = result.fetchall()
        for task in tasks:
            print(f"   ID: {task.id}")
            print(f"   Title: {task.title}")
            print(f"   Status: {task.status}")
            print(f"   User ID: {task.user_id}")
            print(f"   Git Branch ID: {task.git_branch_id}")
            print("   ---")

        # 2. Check if there are any other task-related tables
        print("\n2. CHECKING TABLE STRUCTURE:")
        result = session.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%task%'
        """))

        table_names = result.fetchall()
        print("   Task-related tables:")
        for table in table_names:
            print(f"   - {table.name}")

        # 3. Look for the specific problematic task ID
        problematic_id = "fee968a4-9cbc-4f75-9d5e-761f77959945"
        print(f"\n3. SEARCHING FOR PROBLEMATIC ID: {problematic_id}")

        # Check in tasks table
        result = session.execute(text("""
            SELECT * FROM tasks WHERE id = :task_id
        """), {"task_id": problematic_id})

        task = result.fetchone()
        if task:
            print("   Found in tasks table:")
            print(f"   ID: {task.id}")
            print(f"   Title: {task.title}")
            print(f"   User ID: {task.user_id}")
        else:
            print("   NOT found in tasks table")

        # 4. Look for the expected good task ID
        good_id = "f7f8f526-d1f2-4b9b-a2d3-96326c799cd6"
        print(f"\n4. SEARCHING FOR EXPECTED GOOD ID: {good_id}")

        result = session.execute(text("""
            SELECT * FROM tasks WHERE id = :task_id
        """), {"task_id": good_id})

        task = result.fetchone()
        if task:
            print("   Found in tasks table:")
            print(f"   ID: {task.id}")
            print(f"   Title: {task.title}")
            print(f"   User ID: {task.user_id}")
        else:
            print("   NOT found in tasks table")

        # 5. Check subtasks table for relationship
        print(f"\n5. CHECKING SUBTASKS:")
        result = session.execute(text("""
            SELECT id, parent_task_id, title
            FROM subtasks
            WHERE id = 'adf6c6ed-893b-4522-b938-c9a6b4a2bb50'
        """))

        subtask = result.fetchone()
        if subtask:
            print("   Found subtask:")
            print(f"   Subtask ID: {subtask.id}")
            print(f"   Parent Task ID: {subtask.parent_task_id}")
            print(f"   Title: {subtask.title}")
        else:
            print("   Subtask not found")

        session.close()

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_task_ids()