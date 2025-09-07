#!/usr/bin/env python
"""Test script to debug context creation issue"""

import os
import sys
import uuid

# Add src to path
sys.path.insert(0, '/home/daihungpham/agentic-project/dhafnck_mcp_main/src')

from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory

def test_context_creation():
    """Test that context can be created directly"""
    
    # Create factory
    factory = UnifiedContextFacadeFactory()
    
    # Create facade with a test branch ID
    branch_id = str(uuid.uuid4())
    context_facade = factory.create_facade(
        user_id="test_user",
        git_branch_id=branch_id
    )
    
    # Create a task context
    task_id = str(uuid.uuid4())
    context_data = {
        "branch_id": branch_id,
        "task_data": {
            "title": "Test Task",
            "status": "todo",
            "description": "Test Description",
            "priority": "medium"
        }
    }
    
    print(f"Creating context for task: {task_id}")
    try:
        response = context_facade.create_context(
            level="task",
            context_id=task_id,
            data=context_data
        )
        print(f"Context creation response: {response}")
        
        if response.get("success"):
            print("✅ Context created successfully!")
        else:
            print(f"❌ Context creation failed: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ Exception during context creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_context_creation()