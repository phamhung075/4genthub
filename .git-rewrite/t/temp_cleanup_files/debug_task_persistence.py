#!/usr/bin/env python3
"""
Debug script to investigate task persistence issue.
This script will create tasks and attempt to retrieve them to identify the root cause.
"""

import sys
import os
import uuid
import logging
from datetime import datetime

# Add project root to Python path
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_task_persistence():
    """Debug the task persistence issue step by step"""
    print("=" * 60)
    print("DEBUGGING TASK PERSISTENCE ISSUE")
    print("=" * 60)
    
    try:
        # Import necessary components
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Task
        from fastmcp.task_management.domain.entities.task import Task as TaskEntity
        from fastmcp.task_management.domain.value_objects.task_id import TaskId
        from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
        from fastmcp.task_management.domain.value_objects.priority import Priority
        
        print("✅ Successfully imported all required components")
        
        # Create a test git_branch_id and user_id
        test_git_branch_id = str(uuid.uuid4())
        test_user_id = "test_user_12345"
        
        print(f"🔧 Test Parameters:")
        print(f"   - git_branch_id: {test_git_branch_id}")
        print(f"   - user_id: {test_user_id}")
        
        # Initialize repository with test parameters
        repository = ORMTaskRepository(
            git_branch_id=test_git_branch_id,
            user_id=test_user_id
        )
        
        print("✅ Repository initialized successfully")
        
        # Step 1: Check direct database access
        print("\n" + "="*50)
        print("STEP 1: TESTING DIRECT DATABASE ACCESS")
        print("="*50)
        
        with get_session() as session:
            # Count existing tasks in database
            all_tasks_count = session.query(Task).count()
            print(f"📊 Total tasks in database: {all_tasks_count}")
            
            # Count tasks for our test branch
            branch_tasks_count = session.query(Task).filter(
                Task.git_branch_id == test_git_branch_id
            ).count()
            print(f"📊 Tasks for test branch: {branch_tasks_count}")
            
            # Count tasks for our test user
            user_tasks_count = session.query(Task).filter(
                Task.user_id == test_user_id
            ).count()
            print(f"📊 Tasks for test user: {user_tasks_count}")
        
        # Step 2: Create a task using repository create_task method
        print("\n" + "="*50)
        print("STEP 2: CREATING TASK WITH REPOSITORY")
        print("="*50)
        
        task_title = "Debug Test Task - Persistence Check"
        task_description = "This task is created to debug the persistence issue"
        
        try:
            created_task = repository.create_task(
                title=task_title,
                description=task_description,
                priority="high"
            )
            
            print(f"✅ Task created successfully!")
            print(f"   - Task ID: {created_task.id}")
            print(f"   - Title: {created_task.title}")
            print(f"   - Status: {created_task.status}")
            print(f"   - Git Branch ID: {created_task.git_branch_id}")
            
            created_task_id = str(created_task.id)
            
        except Exception as e:
            print(f"❌ Task creation failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 3: Verify task exists in database immediately
        print("\n" + "="*50)
        print("STEP 3: IMMEDIATE DATABASE VERIFICATION")
        print("="*50)
        
        with get_session() as session:
            # Check if task exists in database
            db_task = session.query(Task).filter(Task.id == created_task_id).first()
            
            if db_task:
                print(f"✅ Task found in database!")
                print(f"   - ID: {db_task.id}")
                print(f"   - Title: {db_task.title}")
                print(f"   - Git Branch ID: {db_task.git_branch_id}")
                print(f"   - User ID: {db_task.user_id}")
                print(f"   - Status: {db_task.status}")
            else:
                print(f"❌ Task NOT found in database with ID: {created_task_id}")
                
            # Check if task exists with different filters
            branch_tasks = session.query(Task).filter(
                Task.git_branch_id == test_git_branch_id
            ).all()
            print(f"📊 Tasks in branch after creation: {len(branch_tasks)}")
            
            user_tasks = session.query(Task).filter(
                Task.user_id == test_user_id
            ).all()
            print(f"📊 Tasks for user after creation: {len(user_tasks)}")
        
        # Step 4: Test repository get_task method
        print("\n" + "="*50)
        print("STEP 4: TESTING REPOSITORY GET_TASK")
        print("="*50)
        
        try:
            retrieved_task = repository.get_task(created_task_id)
            
            if retrieved_task:
                print(f"✅ Task retrieved successfully!")
                print(f"   - Task ID: {retrieved_task.id}")
                print(f"   - Title: {retrieved_task.title}")
                print(f"   - Status: {retrieved_task.status}")
            else:
                print(f"❌ Task NOT retrieved by repository.get_task()")
        except Exception as e:
            print(f"❌ Error retrieving task: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 5: Test repository list_tasks method
        print("\n" + "="*50)
        print("STEP 5: TESTING REPOSITORY LIST_TASKS")
        print("="*50)
        
        try:
            listed_tasks = repository.list_tasks(limit=100)
            print(f"📊 Repository list_tasks returned: {len(listed_tasks)} tasks")
            
            # Check if our created task is in the list
            our_task_in_list = None
            for task in listed_tasks:
                if str(task.id) == created_task_id:
                    our_task_in_list = task
                    break
            
            if our_task_in_list:
                print(f"✅ Our task found in list!")
            else:
                print(f"❌ Our task NOT found in list")
                if listed_tasks:
                    print(f"   Sample tasks in list:")
                    for i, task in enumerate(listed_tasks[:3]):
                        print(f"   {i+1}. {task.id} - {task.title}")
        
        except Exception as e:
            print(f"❌ Error listing tasks: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 6: Check user filtering in repository
        print("\n" + "="*50)
        print("STEP 6: TESTING USER FILTERING")
        print("="*50)
        
        print(f"Repository user_id: {repository.user_id}")
        print(f"Repository git_branch_id: {repository.git_branch_id}")
        
        # Test with different user_id
        different_user_repo = ORMTaskRepository(
            git_branch_id=test_git_branch_id,
            user_id="different_user_123"
        )
        
        different_user_tasks = different_user_repo.list_tasks()
        print(f"📊 Tasks with different user_id: {len(different_user_tasks)}")
        
        # Step 7: Test find_by_id method
        print("\n" + "="*50)
        print("STEP 7: TESTING FIND_BY_ID METHOD")
        print("="*50)
        
        try:
            domain_task_id = TaskId(created_task_id)
            found_task = repository.find_by_id(domain_task_id)
            
            if found_task:
                print(f"✅ Task found by find_by_id!")
                print(f"   - Task ID: {found_task.id}")
                print(f"   - Title: {found_task.title}")
            else:
                print(f"❌ Task NOT found by find_by_id")
        
        except Exception as e:
            print(f"❌ Error with find_by_id: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 8: Test find_by_criteria method
        print("\n" + "="*50)
        print("STEP 8: TESTING FIND_BY_CRITERIA METHOD")
        print("="*50)
        
        try:
            criteria_tasks = repository.find_by_criteria({
                'git_branch_id': test_git_branch_id
            })
            print(f"📊 Tasks found by criteria: {len(criteria_tasks)}")
            
            if criteria_tasks:
                for task in criteria_tasks:
                    print(f"   - {task.id} - {task.title}")
            
        except Exception as e:
            print(f"❌ Error with find_by_criteria: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 9: Final summary
        print("\n" + "="*60)
        print("DEBUG SUMMARY")
        print("="*60)
        
        with get_session() as session:
            final_all_tasks = session.query(Task).count()
            final_branch_tasks = session.query(Task).filter(
                Task.git_branch_id == test_git_branch_id
            ).count()
            final_user_tasks = session.query(Task).filter(
                Task.user_id == test_user_id
            ).count()
            
            print(f"📊 Final counts:")
            print(f"   - All tasks in DB: {final_all_tasks}")
            print(f"   - Tasks in test branch: {final_branch_tasks}")
            print(f"   - Tasks for test user: {final_user_tasks}")
    
    except Exception as e:
        print(f"❌ Critical error in debug script: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_task_persistence()