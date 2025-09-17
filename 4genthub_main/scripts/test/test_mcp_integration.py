#!/usr/bin/env python3
"""Test MCP server integration and find issues."""

import os
import sys
import json
import requests
from datetime import datetime

# Add the source directory to path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/4genthub_main/src')

def test_mcp_server():
    """Test MCP server endpoints and functionality."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("MCP Server Integration Test")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n[TEST 1] Health Check")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Server: {health_data.get('server', 'Unknown')}")
            print(f"   Version: {health_data.get('version', 'Unknown')}")
            print(f"   Auth Enabled: {health_data.get('auth_enabled', False)}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: MCP Tools
    print("\n[TEST 2] Testing MCP Tools Import")
    tools = None
    try:
        # Try the new import method using the backward compatibility alias
        from fastmcp.task_management.interface import ConsolidatedMCPTools
        tools = ConsolidatedMCPTools()
        print("✅ ConsolidatedMCPTools imported successfully (using DDDCompliantMCPTools)")
    except ImportError as e:
        print(f"⚠️ Import warning (expected during refactoring): {e}")
        print("   Trying direct import...")
        try:
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            tools = DDDCompliantMCPTools()
            print("✅ DDDCompliantMCPTools imported directly")
        except ImportError as e2:
            print(f"❌ Direct import also failed: {e2}")
            return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test manage_connection
    if tools:
        print("\n[TEST 3] Testing manage_connection")
        try:
            result = tools.manage_connection(action="health_check")
            if result.get("success"):
                print("✅ manage_connection health_check passed")
            else:
                print(f"❌ manage_connection failed: {result}")
        except Exception as e:
            print(f"⚠️ manage_connection not available or error: {e}")
    
    # Test 4: Project Management
    print("\n[TEST 4] Testing Project Management")
    try:
        # List projects
        result = tools.manage_project(action="list")
        if "projects" in result:
            print(f"✅ Listed {len(result['projects'])} projects")
            if result['projects']:
                for project in result['projects'][:3]:
                    print(f"   - {project.get('name', 'Unknown')}")
        else:
            print(f"⚠️ No projects found or error: {result}")
            
        # Create test project
        print("\n[TEST 5] Creating Test Project")
        test_project = tools.manage_project(
            action="create",
            name=f"test-project-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            description="Automated test project"
        )
        if test_project.get("success"):
            print(f"✅ Created test project: {test_project.get('project', {}).get('name')}")
            project_id = test_project.get('project', {}).get('id')
            
            # Create branch
            print("\n[TEST 6] Creating Git Branch")
            branch_result = tools.manage_git_branch(
                action="create",
                project_id=project_id,
                git_branch_name="test/automated-testing"
            )
            if branch_result.get("success"):
                print(f"✅ Created branch: {branch_result.get('git_branch', {}).get('name')}")
                branch_id = branch_result.get('git_branch', {}).get('id')
                
                # Create task
                print("\n[TEST 7] Creating Task")
                task_result = tools.manage_task(
                    action="create",
                    git_branch_id=branch_id,
                    title="Test MCP Integration",
                    description="Automated test task",
                    priority="high"
                )
                if task_result.get("success"):
                    print(f"✅ Created task: {task_result.get('task', {}).get('title')}")
                    task_id = task_result.get('task', {}).get('id')
                    
                    # Update task
                    print("\n[TEST 8] Updating Task")
                    update_result = tools.manage_task(
                        action="update",
                        task_id=task_id,
                        status="in_progress",
                        details="Testing task update functionality"
                    )
                    if update_result.get("success"):
                        print("✅ Task updated successfully")
                    else:
                        print(f"❌ Task update failed: {update_result}")
                        
                    # Complete task
                    print("\n[TEST 9] Completing Task")
                    complete_result = tools.manage_task(
                        action="complete",
                        task_id=task_id,
                        completion_summary="Task completed successfully",
                        testing_notes="All tests passed"
                    )
                    if complete_result.get("success"):
                        print("✅ Task completed successfully")
                    else:
                        print(f"❌ Task completion failed: {complete_result}")
                else:
                    print(f"❌ Task creation failed: {task_result}")
            else:
                print(f"❌ Branch creation failed: {branch_result}")
        else:
            print(f"❌ Project creation failed: {test_project}")
            
    except Exception as e:
        print(f"❌ Project management test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 10: Context Management
    print("\n[TEST 10] Testing Context Management")
    try:
        # Get global context
        context_result = tools.manage_context(
            action="get",
            level="global",
            context_id="global"
        )
        if context_result.get("success") or "context" in context_result:
            print("✅ Context management working")
        else:
            print(f"⚠️ Context management issue: {context_result}")
    except Exception as e:
        print(f"❌ Context management test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("- Check the results above for any ❌ failures")
    print("- These indicate issues that need to be fixed")
    print("=" * 60)

if __name__ == "__main__":
    test_mcp_server()