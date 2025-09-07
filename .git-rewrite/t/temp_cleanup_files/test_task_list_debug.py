#!/usr/bin/env python3
"""
Debug script to test task list filtering with detailed logging
"""

import sys
import os
import logging

# Set up logging to see ALL debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the src directory to Python path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

def test_task_list_filtering():
    """Test task list filtering with extensive debug logging"""
    print("\n" + "="*80)
    print("TESTING TASK LIST FILTERING WITH DEBUG LOGGING")
    print("="*80 + "\n")
    
    try:
        # Import after path is set
        from fastmcp.task_management.application.dtos.task import ListTasksRequest
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        
        # Test parameters
        git_branch_id = "143e93f7-d6ce-4d7a-a56d-c5ec69e0853f"
        
        print(f"Test Parameters:")
        print(f"  git_branch_id: {git_branch_id}")
        print()
        
        # Create repository and facade
        print("Creating task repository...")
        task_repo = ORMTaskRepository(user_id='system')
        
        print("Creating task facade...")
        facade = TaskApplicationFacade(task_repo)
        print()
        
        # Create request with git_branch_id
        print("Creating ListTasksRequest with git_branch_id...")
        request = ListTasksRequest(
            git_branch_id=git_branch_id,
            limit=20
        )
        print(f"Request created: git_branch_id={request.git_branch_id}")
        print()
        
        # Call list_tasks
        print("Calling facade.list_tasks()...")
        print("Watch the debug logs to trace the flow!\n")
        
        result = facade.list_tasks(request, minimal=True)
        
        print(f"\nResult:")
        print(f"  Success: {result.get('success')}")
        print(f"  Task count: {result.get('count', 0)}")
        
        if result.get('tasks'):
            print(f"\n  Tasks returned:")
            for task in result['tasks']:
                print(f"    - {task.get('id')}: {task.get('title')}")
                
    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_task_list_filtering()