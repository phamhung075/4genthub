#!/usr/bin/env python3
"""
Verify the fix is working
"""

import sys
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Import the function directly and test it
from fastmcp.task_management.application.dtos.task.create_task_request import resolve_legacy_role

print("=== Testing Fixed Legacy Role Resolution ===")

test_inputs = [
    "coding_agent",
    "senior_developer", 
    "qa_engineer",
    "test_orchestrator_agent"
]

for input_role in test_inputs:
    resolved = resolve_legacy_role(input_role)
    print(f"resolve_legacy_role('{input_role}') = '{resolved}'")

# Now test the full DTO
print("\n=== Testing Full DTO ===")
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest

request = CreateTaskRequest(
    title="Test",
    description="Test",
    git_branch_id="test-id",
    assignees=["coding_agent"]
)

print(f"DTO assignees result: {request.assignees}")