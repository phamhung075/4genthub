#!/usr/bin/env python3
"""Test script to verify MCP task operations fix"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8000"

async def test_task_operations():
    """Test task create and retrieve operations"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("Testing MCP Task Operations")
        print("=" * 60)
        
        # Test 1: Create Project
        print("\n1. Creating test project...")
        project_response = await client.post(
            f"{BASE_URL}/tools/manage_project",
            json={
                "action": "create",
                "name": f"test-fix-project",
                "description": "Testing task fixes"
            }
        )
        
        if project_response.status_code == 200:
            project_data = project_response.json()
            project_id = project_data.get("project", {}).get("id")
            print(f"✅ Project created: {project_id}")
        else:
            print(f"❌ Failed to create project: {project_response.text}")
            return
        
        # Test 2: Create Git Branch
        print("\n2. Creating git branch...")
        branch_response = await client.post(
            f"{BASE_URL}/tools/manage_git_branch",
            json={
                "action": "create",
                "project_id": project_id,
                "git_branch_name": "test-fix-branch",
                "git_branch_description": "Testing branch"
            }
        )
        
        if branch_response.status_code == 200:
            branch_data = branch_response.json()
            branch_id = branch_data.get("git_branch", {}).get("id")
            print(f"✅ Branch created: {branch_id}")
        else:
            print(f"❌ Failed to create branch: {branch_response.text}")
            return
        
        # Test 3: Create Task
        print("\n3. Creating task...")
        task_response = await client.post(
            f"{BASE_URL}/tools/manage_task",
            json={
                "action": "create",
                "git_branch_id": branch_id,
                "title": "Test Task for Fix",
                "description": "Verifying task operations"
            }
        )
        
        if task_response.status_code == 200:
            task_data = task_response.json()
            task_id = task_data.get("task", {}).get("id")
            print(f"✅ Task created: {task_id}")
        else:
            print(f"❌ Failed to create task: {task_response.text}")
            return
        
        # Test 4: Get Task (This was failing before)
        print("\n4. Getting task by ID...")
        get_task_response = await client.post(
            f"{BASE_URL}/tools/manage_task",
            json={
                "action": "get",
                "task_id": task_id
            }
        )
        
        if get_task_response.status_code == 200:
            retrieved_task = get_task_response.json()
            print(f"✅ Task retrieved successfully")
            print(f"   Title: {retrieved_task.get('task', {}).get('title')}")
        else:
            print(f"❌ Failed to get task: {get_task_response.text}")
        
        # Test 5: List Tasks
        print("\n5. Listing tasks...")
        list_task_response = await client.post(
            f"{BASE_URL}/tools/manage_task",
            json={
                "action": "list",
                "git_branch_id": branch_id
            }
        )
        
        if list_task_response.status_code == 200:
            tasks = list_task_response.json().get("tasks", [])
            print(f"✅ Found {len(tasks)} tasks")
            for task in tasks:
                print(f"   - {task.get('title')}")
        else:
            print(f"❌ Failed to list tasks: {list_task_response.text}")
        
        print("\n" + "=" * 60)
        print("Test Summary:")
        print("- Project creation: ✅")
        print("- Branch creation: ✅")
        print("- Task creation: ✅")
        print(f"- Task retrieval: {'✅' if get_task_response.status_code == 200 else '❌'}")
        print(f"- Task listing: {'✅' if list_task_response.status_code == 200 else '❌'}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_task_operations())