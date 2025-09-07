#!/usr/bin/env python3
"""
Test Parameter Validation Issues
Reproduces the specific validation errors mentioned in the task.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.interface.controllers.subtask_mcp_controller import SubtaskMCPController
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.factories.subtask_facade_factory import SubtaskFacadeFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory

def test_labels_array_validation():
    """Test labels parameter with array format"""
    print("🧪 Testing Labels Array Validation...")
    
    # Create factories and controller
    task_repository_factory = TaskRepositoryFactory()
    subtask_repository_factory = SubtaskRepositoryFactory()
    task_facade_factory = TaskFacadeFactory(task_repository_factory, subtask_repository_factory)
    controller = TaskMCPController(task_facade_factory)
    
    try:
        # Test 1: Labels as list (the documented format that fails)
        print("\n1. Testing labels=[\"test\", \"mcp\", \"validation\"]...")
        result = controller.manage_task_tool(
            action="create",
            git_branch_id="test-branch-123",
            title="Test Task with Labels Array",
            labels=["test", "mcp", "validation"]
        )
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    try:
        # Test 2: Labels as comma-separated string
        print("\n2. Testing labels as comma-separated string...")
        result = controller.manage_task_tool(
            action="create", 
            git_branch_id="test-branch-124",
            title="Test Task with Labels String",
            labels="test,mcp,validation"
        )
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_progress_percentage_validation():
    """Test progress_percentage parameter with integer format"""
    print("\n🧪 Testing Progress Percentage Validation...")
    
    # Create factories and controller
    task_repository_factory = TaskRepositoryFactory()
    subtask_repository_factory = SubtaskRepositoryFactory()
    subtask_facade_factory = SubtaskFacadeFactory(task_repository_factory, subtask_repository_factory)
    controller = SubtaskMCPController(subtask_facade_factory)
    
    try:
        # Test 1: progress_percentage as integer (the documented format that fails)
        print("\n1. Testing progress_percentage=50...")
        result = controller.manage_subtask_tool(
            action="update",
            task_id="test-task-123",
            subtask_id="test-subtask-123", 
            progress_percentage=50
        )
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    try:
        # Test 2: progress_percentage as string
        print("\n2. Testing progress_percentage=\"50\"...")
        result = controller.manage_subtask_tool(
            action="update",
            task_id="test-task-123", 
            subtask_id="test-subtask-123",
            progress_percentage="50"
        )
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🔍 Parameter Validation Issue Reproduction Test")
    print("=" * 50)
    
    await test_labels_array_validation()
    await test_progress_percentage_validation()
    
    print("\n🎯 Test Complete!")

if __name__ == "__main__":
    asyncio.run(main())