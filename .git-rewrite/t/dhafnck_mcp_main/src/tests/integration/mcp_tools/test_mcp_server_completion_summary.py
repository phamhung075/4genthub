#!/usr/bin/env python3
"""
Test completion_summary functionality through the MCP server
"""

import requests
import json
import uuid

def test_mcp_completion_summary():
    """Test completion_summary through MCP server API"""
    print("🧪 Testing completion_summary through MCP server...")
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. Health check
        health = requests.get(f"{base_url}/health")
        print(f"✅ Server health: {health.json()['status']}")
        
        # 2. Create a project
        project_data = {
            "name": "MCP Completion Summary Test",
            "description": "Testing completion_summary through MCP server"
        }
        
        project_response = requests.post(f"{base_url}/mcp/manage_project", json={
            "action": "create",
            **project_data
        })
        
        if project_response.status_code != 200:
            print(f"❌ Failed to create project: {project_response.text}")
            return False
            
        project_result = project_response.json()
        print(f"📋 Project creation result: {project_result}")
        
        if not project_result.get("success"):
            print(f"❌ Project creation failed: {project_result}")
            return False
            
        project_id = project_result["project"]["id"]
        print(f"✅ Created project: {project_id}")
        
        # 3. Create a branch
        branch_response = requests.post(f"{base_url}/mcp/manage_git_branch", json={
            "action": "create",
            "project_id": project_id,
            "git_branch_name": "completion-test",
            "git_branch_description": "Branch for testing completion summary"
        })
        
        if branch_response.status_code != 200:
            print(f"❌ Failed to create branch: {branch_response.text}")
            return False
            
        branch_result = branch_response.json()
        print(f"📋 Branch creation result: {branch_result}")
        
        if not branch_result.get("success"):
            print(f"❌ Branch creation failed: {branch_result}")
            return False
            
        branch_id = branch_result["git_branch"]["id"]
        print(f"✅ Created branch: {branch_id}")
        
        # 4. Create a task
        task_response = requests.post(f"{base_url}/mcp/manage_task", json={
            "action": "create",
            "git_branch_id": branch_id,
            "title": "MCP Completion Summary Test Task",
            "description": "Testing completion_summary storage through MCP server",
            "priority": "medium"
        })
        
        if task_response.status_code != 200:
            print(f"❌ Failed to create task: {task_response.text}")
            return False
            
        task_result = task_response.json()
        print(f"📋 Task creation result: {task_result}")
        
        if not task_result.get("success"):
            print(f"❌ Task creation failed: {task_result}")
            return False
            
        task_id = task_result["task"]["id"]
        print(f"✅ Created task: {task_id}")
        
        # 5. Complete the task with completion_summary
        completion_summary = "Task completed successfully through MCP server with completion summary validation"
        testing_notes = "Verified that MCP server correctly handles completion_summary context storage"
        
        complete_response = requests.post(f"{base_url}/mcp/manage_task", json={
            "action": "complete",
            "task_id": task_id,
            "completion_summary": completion_summary,
            "testing_notes": testing_notes
        })
        
        if complete_response.status_code != 200:
            print(f"❌ Failed to complete task: {complete_response.text}")
            return False
            
        complete_result = complete_response.json()
        print(f"📋 Task completion result: {complete_result}")
        
        if not complete_result.get("success"):
            print(f"❌ Task completion failed: {complete_result}")
            return False
            
        print(f"✅ Task completed successfully")
        
        # 6. Get the context to verify completion_summary was stored
        context_response = requests.post(f"{base_url}/mcp/manage_context", json={
            "action": "get",
            "level": "task",
            "context_id": task_id
        })
        
        if context_response.status_code != 200:
            print(f"❌ Failed to get context: {context_response.text}")
            return False
            
        context_result = context_response.json()
        print(f"📋 Context result: {json.dumps(context_result, indent=2)}")
        
        if not context_result.get("success"):
            print(f"❌ Context retrieval failed: {context_result}")
            return False
            
        context = context_result.get("context", {})
        
        # Check for completion_summary in progress section
        progress = context.get('progress', {})
        if isinstance(progress, dict):
            current_session = progress.get('current_session_summary')
            if current_session == completion_summary:
                print(f"✅ completion_summary correctly stored in context: {current_session}")
                
                # Check testing notes in next_steps
                next_steps = progress.get('next_steps', [])
                expected_testing_note = f"Testing completed: {testing_notes}"
                if isinstance(next_steps, list) and expected_testing_note in next_steps:
                    print(f"✅ testing_notes correctly stored in next_steps: {expected_testing_note}")
                    print(f"\n🎉 SUCCESS: MCP server completion_summary functionality is working!")
                    return True
                else:
                    print(f"⚠️  testing_notes not found in next_steps: {next_steps}")
            else:
                print(f"❌ completion_summary not found. Expected: {completion_summary}, Found: {current_session}")
        else:
            print(f"❌ Progress is not a dict: {progress}")
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 MCP Server Completion Summary Test")
    print("=" * 60)
    
    success = test_mcp_completion_summary()
    
    if success:
        print("\n🎉 SUCCESS: MCP server completion_summary functionality is working correctly!")
        exit(0)
    else:
        print("\n💥 FAILURE: MCP server completion_summary needs investigation")
        exit(1)