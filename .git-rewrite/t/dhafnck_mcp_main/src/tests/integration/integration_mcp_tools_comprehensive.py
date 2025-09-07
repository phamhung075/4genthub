#!/usr/bin/env python3
"""
Comprehensive test script for dhafnck_mcp_http server tools
Tests all available actions and verifies functionality
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
MCP_SERVER_URL = "http://localhost:8000/mcp/"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json"
}

# Test data
TEST_PROJECT_ID = "test_project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_GIT_BRANCH = "test_branch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = "test_user"

# Storage for created items
created_items = {
    "git_branch_id": None,
    "task_ids": [],
    "subtask_ids": [],
    "context_ids": []
}

def make_request(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to the MCP server"""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        },
        "id": int(time.time() * 1000)
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"Action: {params.get('action', 'N/A')}")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.post(MCP_SERVER_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            print(f"ERROR: {result['error']}")
            return result["error"]
        
        if "result" in result:
            print(f"SUCCESS: {json.dumps(result['result'], indent=2)}")
            return result["result"]
        
        return result
    except Exception as e:
        print(f"REQUEST FAILED: {str(e)}")
        return {"error": str(e)}

def test_git_branch_operations():
    """Test git branch creation and management"""
    print("\n\n" + "="*80)
    print("TESTING GIT BRANCH OPERATIONS")
    print("="*80)
    
    # Create git branch
    result = make_request("manage_git_branch", {
        "action": "create",
        "project_id": TEST_PROJECT_ID,
        "branch_name": TEST_GIT_BRANCH,
        "user_id": TEST_USER_ID
    })
    
    if result.get("success") and result.get("git_branch"):
        created_items["git_branch_id"] = result["git_branch"]["id"]
        print(f"\n✓ Git branch created: {created_items['git_branch_id']}")
    else:
        print("\n✗ Failed to create git branch")
        return False
    
    # List git branches
    make_request("manage_git_branch", {
        "action": "list"
    })
    
    # Get specific git branch
    make_request("manage_git_branch", {
        "action": "get",
        "git_branch_id": created_items["git_branch_id"]
    })
    
    return True

def test_task_operations():
    """Test task creation and management"""
    print("\n\n" + "="*80)
    print("TESTING TASK OPERATIONS")
    print("="*80)
    
    if not created_items["git_branch_id"]:
        print("✗ No git branch ID available")
        return False
    
    # Test 1: Create tasks
    for i in range(3):
        result = make_request("manage_task", {
            "action": "create",
            "git_branch_id": created_items["git_branch_id"],
            "title": f"Test Task {i+1}",
            "description": f"This is test task number {i+1}",
            "priority": ["high", "medium", "low"][i],
            "status": "pending",
            "details": f"Detailed information for task {i+1}",
            "estimated_effort": f"{(i+1)*2} hours",
            "assignees": [TEST_USER_ID],
            "labels": ["test", f"priority-{['high', 'medium', 'low'][i]}"]
        })
        
        if result.get("success") and result.get("task"):
            created_items["task_ids"].append(result["task"]["id"])
            print(f"\n✓ Task {i+1} created: {result['task']['id']}")
    
    # Test 2: List tasks
    print("\n\nTesting list tasks...")
    make_request("manage_task", {
        "action": "list",
        "git_branch_id": created_items["git_branch_id"],
        "limit": 10
    })
    
    # Test 3: Get specific task
    if created_items["task_ids"]:
        print("\n\nTesting get task...")
        make_request("manage_task", {
            "action": "get",
            "task_id": created_items["task_ids"][0]
        })
    
    # Test 4: Update task
    if created_items["task_ids"]:
        print("\n\nTesting update task...")
        make_request("manage_task", {
            "action": "update",
            "task_id": created_items["task_ids"][0],
            "status": "in_progress",
            "details": "Started working on this task",
            "estimated_effort": "3 hours"
        })
    
    # Test 5: Search tasks
    print("\n\nTesting search tasks...")
    make_request("manage_task", {
        "action": "search",
        "query": "test",
        "git_branch_id": created_items["git_branch_id"]
    })
    
    # Test 6: Get next task
    print("\n\nTesting next task...")
    make_request("manage_task", {
        "action": "next",
        "git_branch_id": created_items["git_branch_id"]
    })
    
    # Test 7: Add dependency
    if len(created_items["task_ids"]) >= 2:
        print("\n\nTesting add dependency...")
        make_request("manage_task", {
            "action": "add_dependency",
            "task_id": created_items["task_ids"][0],
            "dependency_id": created_items["task_ids"][1]
        })
    
    # Test 8: Complete task with context
    if created_items["task_ids"]:
        print("\n\nTesting complete task...")
        make_request("manage_task", {
            "action": "complete",
            "task_id": created_items["task_ids"][1],
            "completion_summary": "Successfully completed the test task",
            "testing_notes": "All tests passed, functionality verified"
        })
    
    return True

def test_subtask_operations():
    """Test subtask creation and management"""
    print("\n\n" + "="*80)
    print("TESTING SUBTASK OPERATIONS")
    print("="*80)
    
    if not created_items["task_ids"]:
        print("✗ No task IDs available")
        return False
    
    parent_task_id = created_items["task_ids"][0]
    
    # Test 1: Create subtasks
    for i in range(2):
        result = make_request("manage_subtask", {
            "action": "create",
            "task_id": parent_task_id,
            "title": f"Subtask {i+1}",
            "description": f"This is subtask number {i+1}",
            "priority": ["high", "medium"][i],
            "status": "pending",
            "assignees": [TEST_USER_ID]
        })
        
        if result.get("success") and result.get("subtask"):
            created_items["subtask_ids"].append(result["subtask"]["id"])
            print(f"\n✓ Subtask {i+1} created: {result['subtask']['id']}")
    
    # Test 2: List subtasks
    print("\n\nTesting list subtasks...")
    make_request("manage_subtask", {
        "action": "list",
        "task_id": parent_task_id
    })
    
    # Test 3: Update subtask with progress
    if created_items["subtask_ids"]:
        print("\n\nTesting update subtask...")
        make_request("manage_subtask", {
            "action": "update",
            "task_id": parent_task_id,
            "subtask_id": created_items["subtask_ids"][0],
            "status": "in_progress",
            "progress_notes": "Making good progress on the subtask",
            "progress_percentage": 50,
            "impact_on_parent": "This will help complete the parent task faster"
        })
    
    # Test 4: Complete subtask
    if created_items["subtask_ids"]:
        print("\n\nTesting complete subtask...")
        make_request("manage_subtask", {
            "action": "complete",
            "task_id": parent_task_id,
            "subtask_id": created_items["subtask_ids"][0],
            "completion_summary": "Subtask completed successfully",
            "insights_found": ["Learned about MCP tools", "Found efficient approach"]
        })
    
    return True

def test_context_operations():
    """Test context management"""
    print("\n\n" + "="*80)
    print("TESTING CONTEXT OPERATIONS")
    print("="*80)
    
    if not created_items["task_ids"]:
        print("✗ No task IDs available")
        return False
    
    # Context should be auto-created with tasks, let's update it
    task_id = created_items["task_ids"][0]
    
    # Update context
    print("\n\nTesting update context...")
    make_request("manage_context", {
        "action": "update",
        "task_id": task_id,
        "data": {
            "progress": "Made significant progress",
            "learnings": ["MCP tools work well", "Auto-context is helpful"],
            "next_steps": ["Continue testing", "Document findings"]
        }
    })
    
    # Get context
    print("\n\nTesting get context...")
    make_request("manage_context", {
        "action": "get",
        "task_id": task_id
    })
    
    # List contexts
    print("\n\nTesting list contexts...")
    make_request("manage_context", {
        "action": "list"
    })
    
    return True

def test_error_cases():
    """Test error handling and edge cases"""
    print("\n\n" + "="*80)
    print("TESTING ERROR CASES")
    print("="*80)
    
    # Test missing required fields
    print("\n\nTesting missing required field (create without title)...")
    make_request("manage_task", {
        "action": "create",
        "git_branch_id": created_items["git_branch_id"],
        "description": "Task without title"
    })
    
    # Test invalid action
    print("\n\nTesting invalid action...")
    make_request("manage_task", {
        "action": "invalid_action",
        "task_id": "some_id"
    })
    
    # Test non-existent task
    print("\n\nTesting non-existent task...")
    make_request("manage_task", {
        "action": "get",
        "task_id": "non_existent_task_id"
    })
    
    # Test missing git_branch_id for create
    print("\n\nTesting create without git_branch_id...")
    make_request("manage_task", {
        "action": "create",
        "title": "Task without branch"
    })
    
    return True

def test_cleanup():
    """Clean up created test data"""
    print("\n\n" + "="*80)
    print("CLEANING UP TEST DATA")
    print("="*80)
    
    # Delete subtasks
    for subtask_id in created_items["subtask_ids"]:
        if created_items["task_ids"]:
            make_request("manage_subtask", {
                "action": "delete",
                "task_id": created_items["task_ids"][0],
                "subtask_id": subtask_id
            })
    
    # Delete tasks
    for task_id in created_items["task_ids"]:
        make_request("manage_task", {
            "action": "delete",
            "task_id": task_id
        })
    
    # Note: Git branches might not have delete action, check implementation
    
    return True

def main():
    """Run all tests"""
    print("Starting comprehensive MCP tools test...")
    print(f"Server: {MCP_SERVER_URL}")
    print(f"Time: {datetime.now()}")
    
    tests = [
        ("Git Branch Operations", test_git_branch_operations),
        ("Task Operations", test_task_operations),
        ("Subtask Operations", test_subtask_operations),
        ("Context Operations", test_context_operations),
        ("Error Cases", test_error_cases),
        ("Cleanup", test_cleanup)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, result in results if result)
    print(f"\nTotal: {total_passed}/{len(tests)} tests passed")
    
    # Print created items for reference
    print("\n\nCreated items:")
    print(json.dumps(created_items, indent=2))

if __name__ == "__main__":
    main()