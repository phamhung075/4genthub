#!/usr/bin/env python3
"""
Test manual task creation with direct calls
"""

import sys
import asyncio
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

async def test_manual_task_creation():
    """Test task creation manually"""
    
    # Simulate exactly what the MCP controller should do
    print("=== Testing Manual Task Creation ===")
    
    # Step 1: Test string to list conversion (same as task controller)
    assignees = "coding-agent"
    print(f"Input assignees: {assignees}")
    
    if assignees is not None and isinstance(assignees, str):
        if ',' in assignees:
            assignees = [a.strip() for a in assignees.split(',') if a.strip()]
        else:
            assignees = [assignees.strip()] if assignees.strip() else []
    
    print(f"Converted assignees: {assignees}")
    
    # Step 2: Test CreateTaskRequest DTO  
    from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
    
    request = CreateTaskRequest(
        title="Manual test task",
        description="Testing manual creation",
        git_branch_id="052e2006-2252-419b-95f8-5b5d72707bf5",
        assignees=assignees,
        priority="high",
        estimated_effort="2 hours"
    )
    
    print(f"DTO assignees after processing: {pytest_request.assignees}")
    
    # Step 3: Test Task entity creation
    from fastmcp.task_management.domain.entities.task import Task
    
    try:
        task = Task(
            title=pytest_request.title,
            description=pytest_request.description,
            assignees=pytest_request.assignees,
            git_branch_id=pytest_request.git_branch_id
        )
        print(f"Task created successfully!")
        print(f"Task assignees: {task.assignees}")
        
        # Step 4: Test the validation that fails in CRUD handler
        validation_passes = not (not pytest_request.assignees or len(pytest_request.assignees) == 0)
        print(f"CRUD handler validation passes: {validation_passes}")
        
    except Exception as e:
        print(f"Task creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_manual_task_creation())