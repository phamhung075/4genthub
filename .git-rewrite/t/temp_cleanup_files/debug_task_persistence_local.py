#!/usr/bin/env python3
"""
Debug script to investigate task persistence issue using local SQLite database.
This script will temporarily override database configuration for testing.
"""

import sys
import os
import uuid
import logging
from datetime import datetime

# Override environment variables for local SQLite testing
os.environ['DATABASE_TYPE'] = 'sqlite'
os.environ['PYTEST_CURRENT_TEST'] = 'true'  # Enable test mode to allow SQLite

# Add project root to Python path
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_task_persistence_local():
    """Debug the task persistence issue using local SQLite database"""
    print("=" * 60)
    print("DEBUGGING TASK PERSISTENCE ISSUE (LOCAL SQLITE)")
    print("=" * 60)
    
    try:
        # Import necessary components
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Task, ProjectGitBranch, Project
        from fastmcp.task_management.domain.entities.task import Task as TaskEntity
        from fastmcp.task_management.domain.value_objects.task_id import TaskId
        from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
        from fastmcp.task_management.domain.value_objects.priority import Priority
        
        print("✅ Successfully imported all required components")
        
        # Create test data
        test_project_id = str(uuid.uuid4())
        test_git_branch_id = str(uuid.uuid4())
        test_user_id = "test_user_12345"
        
        print(f"🔧 Test Parameters:")
        print(f"   - project_id: {test_project_id}")
        print(f"   - git_branch_id: {test_git_branch_id}")
        print(f"   - user_id: {test_user_id}")
        
        # First, create the project and git branch in database
        print("\n" + "="*50)
        print("STEP 1: CREATING TEST PROJECT AND BRANCH")
        print("="*50)
        
        with get_session() as session:
            # Create project
            project = Project(
                id=test_project_id,
                name="Debug Test Project",
                description="Test project for debugging task persistence",
                user_id=test_user_id
            )
            session.add(project)
            session.flush()
            
            # Create git branch
            git_branch = ProjectGitBranch(
                id=test_git_branch_id,
                project_id=test_project_id,
                name="debug-test-branch",
                description="Test branch for debugging task persistence",
                user_id=test_user_id
            )
            session.add(git_branch)
            session.commit()
            
            print("✅ Project and Git Branch created successfully")
        
        # Initialize repository with test parameters
        repository = ORMTaskRepository(
            git_branch_id=test_git_branch_id,
            user_id=test_user_id
        )
        
        print("✅ Repository initialized successfully")
        
        # Step 2: Check initial database state
        print("\n" + "="*50)
        print("STEP 2: INITIAL DATABASE STATE")
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
        
        # Step 3: Create a task using repository create_task method
        print("\n" + "="*50)
        print("STEP 3: CREATING TASK WITH REPOSITORY")
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
        
        # Step 4: Verify task exists in database immediately
        print("\n" + "="*50)
        print("STEP 4: IMMEDIATE DATABASE VERIFICATION")
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
            for task in branch_tasks:
                print(f"   - {task.id}: {task.title}")
            
            user_tasks = session.query(Task).filter(
                Task.user_id == test_user_id
            ).all()
            print(f"📊 Tasks for user after creation: {len(user_tasks)}")
        
        # Step 5: Test repository get_task method
        print("\n" + "="*50)
        print("STEP 5: TESTING REPOSITORY GET_TASK")
        print("="*50)
        
        try:
            retrieved_task = repository.get_task(created_task_id)
            
            if retrieved_task:
                print(f"✅ Task retrieved successfully!")
                print(f"   - Task ID: {retrieved_task.id}")
                print(f"   - Title: {retrieved_task.title}")
                print(f"   - Status: {retrieved_task.status}")
                print(f"   - Git Branch ID: {retrieved_task.git_branch_id}")
            else:
                print(f"❌ Task NOT retrieved by repository.get_task()")
                print(f"   - Repository user_id: {repository.user_id}")
                print(f"   - Repository git_branch_id: {repository.git_branch_id}")
        except Exception as e:
            print(f"❌ Error retrieving task: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 6: Test repository list_tasks method
        print("\n" + "="*50)
        print("STEP 6: TESTING REPOSITORY LIST_TASKS")
        print("="*50)
        
        try:
            listed_tasks = repository.list_tasks(limit=100)
            print(f"📊 Repository list_tasks returned: {len(listed_tasks)} tasks")
            
            # Check if our created task is in the list
            our_task_in_list = None
            for task in listed_tasks:
                print(f"   - {task.id}: {task.title} (branch: {task.git_branch_id})")
                if str(task.id) == created_task_id:
                    our_task_in_list = task
            
            if our_task_in_list:
                print(f"✅ Our task found in list!")
            else:
                print(f"❌ Our task NOT found in list")
        
        except Exception as e:
            print(f"❌ Error listing tasks: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 7: Test with different user_id (should not find tasks)
        print("\n" + "="*50)
        print("STEP 7: TESTING USER ISOLATION")
        print("="*50)
        
        different_user_repo = ORMTaskRepository(
            git_branch_id=test_git_branch_id,
            user_id="different_user_123"
        )
        
        different_user_tasks = different_user_repo.list_tasks()
        print(f"📊 Tasks with different user_id: {len(different_user_tasks)}")
        
        # Step 8: Test find_by_criteria method
        print("\n" + "="*50)
        print("STEP 8: TESTING FIND_BY_CRITERIA METHOD")
        print("="*50)
        
        try:
            print(f"   - Repository git_branch_id: {repository.git_branch_id}")
            print(f"   - Test git_branch_id: {test_git_branch_id}")
            
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
    debug_task_persistence_local()