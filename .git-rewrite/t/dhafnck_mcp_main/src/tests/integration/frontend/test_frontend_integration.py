#!/usr/bin/env python3
"""
Test frontend integration for completion summary context storage
"""

import requests
import json
import uuid

def test_frontend_api_integration():
    """Test that the frontend API correctly handles completion_summary context storage"""
    print("🌐 Testing Frontend API Integration...")
    
    backend_url = "http://localhost:8000"
    
    try:
        # 1. Check health
        health_response = requests.get(f"{backend_url}/health")
        print(f"✅ Backend health: {health_response.json()['status']}")
        
        # 2. List projects to see if API is working
        print("📋 Testing project listing...")
        projects_response = requests.get(f"{backend_url}/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json()
            print(f"✅ Found {len(projects)} projects")
            
            if projects:
                project_id = projects[0]['id']
                print(f"✅ Using project: {project_id}")
                
                # 3. List branches for this project
                branches_response = requests.get(f"{backend_url}/projects/{project_id}/branches")
                if branches_response.status_code == 200:
                    branches = branches_response.json()
                    print(f"✅ Found {len(branches)} branches")
                    
                    if branches:
                        branch_id = branches[0]['id']
                        print(f"✅ Using branch: {branch_id}")
                        
                        # 4. Create a test task
                        task_data = {
                            "title": "Frontend Integration Test Task",
                            "description": "Testing completion_summary context storage via frontend API",
                            "priority": "medium",
                            "git_branch_id": branch_id
                        }
                        
                        task_response = requests.post(f"{backend_url}/tasks", json=task_data)
                        if task_response.status_code == 201:
                            task = task_response.json()
                            task_id = task['id']
                            print(f"✅ Created task: {task_id}")
                            
                            # 5. Complete the task with completion summary
                            completion_data = {
                                "completion_summary": "Task completed successfully through frontend API integration test",
                                "testing_notes": "Verified that completion_summary context storage works through REST API"
                            }
                            
                            complete_response = requests.patch(f"{backend_url}/tasks/{task_id}/complete", json=completion_data)
                            if complete_response.status_code == 200:
                                completed_task = complete_response.json()
                                print(f"✅ Task completed successfully")
                                
                                # 6. Check if context was created with completion_summary
                                if 'context' in completed_task and completed_task['context']:
                                    context = completed_task['context']
                                    print(f"✅ Context found in response")
                                    
                                    # Parse context if it's a string
                                    if isinstance(context, str):
                                        try:
                                            context = json.loads(context)
                                        except:
                                            pass
                                    
                                    # Check for completion_summary in progress section
                                    if isinstance(context, dict):
                                        progress = context.get('progress', {})
                                        if isinstance(progress, dict):
                                            current_session = progress.get('current_session_summary')
                                            if current_session == completion_data['completion_summary']:
                                                print("✅ completion_summary correctly stored in context.progress.current_session_summary")
                                                print(f"   Value: {current_session}")
                                                
                                                # Check testing notes
                                                next_steps = progress.get('next_steps', [])
                                                if isinstance(next_steps, list) and completion_data['testing_notes'] in next_steps:
                                                    print("✅ testing_notes correctly stored in context.progress.next_steps")
                                                    print(f"   Value: {completion_data['testing_notes']}")
                                                    return True
                                                else:
                                                    print(f"⚠️  testing_notes not found in next_steps: {next_steps}")
                                            else:
                                                print(f"❌ completion_summary not found in expected location")
                                                print(f"   Expected: {completion_data['completion_summary']}")
                                                print(f"   Found: {current_session}")
                                        else:
                                            print(f"❌ Context.progress is not a dict: {progress}")
                                    else:
                                        print(f"❌ Context is not a dict: {type(context)}")
                                else:
                                    print(f"❌ No context found in completed task response")
                                    print(f"   Response keys: {list(completed_task.keys())}")
                            else:
                                print(f"❌ Failed to complete task: {complete_response.status_code}")
                                print(f"   Response: {complete_response.text}")
                        else:
                            print(f"❌ Failed to create task: {task_response.status_code}")
                            print(f"   Response: {task_response.text}")
                    else:
                        print("❌ No branches found")
                else:
                    print(f"❌ Failed to list branches: {branches_response.status_code}")
            else:
                print("❌ No projects found")
        else:
            print(f"❌ Failed to list projects: {projects_response.status_code}")
            
        return False
        
    except Exception as e:
        print(f"❌ Frontend API integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Frontend API Integration Test")
    print("=" * 50)
    
    success = test_frontend_api_integration()
    
    if success:
        print("\n🎉 SUCCESS: Frontend API correctly handles completion_summary context storage!")
        exit(0)
    else:
        print("\n💥 FAILURE: Frontend API integration needs investigation")
        exit(1)