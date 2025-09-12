#!/usr/bin/env python3
"""
Test direct task creation through the facade
"""

import sys
import asyncio
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

async def test_direct_task_creation():
    """Test task creation directly through the facade"""
    
    from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
    
    # Test the DTO creation first
    print("=== Testing CreateTaskRequest DTO ===")
    
    request = CreateTaskRequest(
        title="Test task direct creation",
        description="Testing direct task creation", 
        git_branch_id="052e2006-2252-419b-95f8-5b5d72707bf5",
        assignees=["coding-agent"],  # Pass as list directly
        priority="high",
        estimated_effort="2 hours"
    )
    
    print(f"Request created successfully!")
    print(f"Title: {pytest_request.title}")
    print(f"Assignees: {pytest_request.assignees}")
    print(f"Assignees type: {type(pytest_request.assignees)}")
    print(f"Assignees length: {len(pytest_request.assignees)}")
    
    # Test task entity creation
    print("\n=== Testing Task Entity Creation ===")
    
    from fastmcp.task_management.domain.entities.task import Task
    
    try:
        task = Task(
            title=pytest_request.title,
            description=pytest_request.description,
            assignees=pytest_request.assignees  # Use the processed assignees from DTO
        )
        print(f"Task created successfully!")
        print(f"Task assignees: {task.assignees}")
    except Exception as e:
        print(f"Task creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_task_creation())