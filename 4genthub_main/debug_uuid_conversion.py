#!/usr/bin/env python3
"""
Debug UUID conversion issue in TaskId and Task entity
"""

import sys
import os
sys.path.insert(0, 'src')

import uuid
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority

def test_uuid_conversion():
    print("🧪 Testing UUID conversion in TaskId and Task entity...")
    
    # 1. Test TaskId with canonical UUID
    canonical_uuid = str(uuid.uuid4())
    print(f"1. Original canonical UUID: '{canonical_uuid}' (length: {len(canonical_uuid)})")
    
    task_id = TaskId(canonical_uuid)
    print(f"   TaskId.value: '{task_id.value}' (length: {len(task_id.value)})")
    print(f"   str(task_id): '{str(task_id)}' (length: {len(str(task_id))})")
    print(f"   Match: {canonical_uuid == str(task_id)}")
    
    # 2. Test git_branch_id handling in Task entity
    git_branch_id = str(uuid.uuid4())
    print(f"\n2. git_branch_id input: '{git_branch_id}' (length: {len(git_branch_id)})")
    
    task = Task.create(
        id=task_id,
        title="Test task",
        description="Test description", 
        git_branch_id=git_branch_id
    )
    
    print(f"   Task.git_branch_id: '{task.git_branch_id}' (length: {len(task.git_branch_id)})")
    print(f"   Match: {git_branch_id == task.git_branch_id}")
    
    # 3. Test if there's any implicit conversion
    print(f"\n3. Task.id: '{task.id}' (type: {type(task.id)})")
    print(f"   str(task.id): '{str(task.id)}' (length: {len(str(task.id))})")

if __name__ == "__main__":
    test_uuid_conversion()