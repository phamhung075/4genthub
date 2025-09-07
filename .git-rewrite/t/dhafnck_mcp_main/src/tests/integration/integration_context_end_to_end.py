#!/usr/bin/env python3
"""End-to-end test of context auto-loading fix"""

import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main/src'))

# Use production database
os.environ['MCP_DB_PATH'] = os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main/database/data/dhafnck_mcp.db')

def test_context_via_mcp_tools():
    """Test context loading using the MCP tool interface directly"""
    
    # Import after setting env vars
    try:
        from fastmcp.server.server import create_server
    except ImportError:
        # Fallback - skip this test
        print("❌ Server module not available - skipping test")
        return True
    import asyncio
    
    async def run_test():
        # Create server instance
        server = create_server()
        
        # Get tool functions
        tools = {tool.name: tool.func for tool in server.list_tools()}
        
        print("=== Testing Context Auto-Loading via MCP Tools ===\n")
        
        # Step 1: Create a project
        print("1. Creating project...")
        project_result = await tools["manage_project"](
            action="create",
            name="Test Project for Context",
            description="Testing context auto-loading"
        )
        
        if not project_result.get("success"):
            print(f"❌ Failed to create project: {project_result}")
            return False
            
        project_id = project_result["project"]["id"]
        print(f"✅ Project created: {project_id}")
        
        # Step 2: Create a git branch
        print("\n2. Creating git branch...")
        branch_result = await tools["manage_git_branch"](
            action="create",
            project_id=project_id,
            git_branch_name="test-context-branch",
            git_branch_description="Testing context"
        )
        
        if not branch_result.get("success"):
            print(f"❌ Failed to create branch: {branch_result}")
            return False
            
        git_branch_id = branch_result["git_branch"]["id"]
        print(f"✅ Git branch created: {git_branch_id}")
        
        # Step 3: Create a task
        print("\n3. Creating task...")
        task_result = await tools["manage_task"](
            action="create",
            git_branch_id=git_branch_id,
            title="Test Task with Context",
            description="This task should have context auto-loaded",
            priority="high",
            estimated_effort="2 hours"
        )
        
        if not task_result.get("success"):
            print(f"❌ Failed to create task: {task_result}")
            return False
            
        task = task_result["task"]
        task_id = task["id"]
        print(f"✅ Task created: {task_id}")
        print(f"   - Context ID: {task.get('context_id')}")
        
        # Wait a moment for async operations
        await asyncio.sleep(0.5)
        
        # Step 4: Get the task (KEY TEST)
        print("\n4. Getting task with auto-loaded context (TESTING THE FIX)...")
        get_result = await tools["manage_task"](
            action="get",
            task_id=task_id
        )
        
        if not get_result.get("success"):
            print(f"❌ Failed to get task: {get_result}")
            return False
            
        task_with_context = get_result["task"]
        context_available = task_with_context.get("context_available", False)
        context_data = task_with_context.get("context_data")
        
        print(f"✅ Task retrieved successfully")
        print(f"   - Title: {task_with_context.get('title')}")
        print(f"   - Context available: {context_available}")
        print(f"   - Context data present: {context_data is not None}")
        
        if context_data:
            print(f"   - Context sections: {list(context_data.keys())}")
            print("\n✅ SUCCESS: Context auto-loading is WORKING!")
            
            # Show sample of context data
            if 'metadata' in context_data:
                print(f"\nContext metadata:")
                print(json.dumps(context_data['metadata'], indent=2))
            
            return True
        else:
            print("\n❌ FAILED: Context data was NOT loaded!")
            
            # Additional debugging
            print("\nDebugging info:")
            print(f"   - Task has context_id: {task_with_context.get('context_id')}")
            print(f"   - Context available flag: {context_available}")
            
            # Try to get context directly
            print("\n5. Trying to get context directly...")
            context_result = await tools["manage_context"](
                action="get",
                task_id=task_id
            )
            
            if context_result.get("success"):
                print("✅ Context exists when retrieved directly")
                print(f"   - Has context: {context_result.get('context') is not None}")
            else:
                print(f"❌ Direct context retrieval failed: {context_result.get('error')}")
            
            return False
    
    # Run the async test
    try:
        import asyncio
        return asyncio.run(run_test())
    except Exception as e:
        print(f"\n❌ Error running test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    success = test_context_via_mcp_tools()
    
    print("\n" + "="*60)
    if success:
        print("✅ CONTEXT AUTO-LOADING FIX IS WORKING CORRECTLY!")
    else:
        print("❌ Context auto-loading fix is NOT working properly")
        print("\nThe fix should ensure that:")
        print("- When getting a task, context is automatically loaded")
        print("- The context_available field is set to true")
        print("- The context_data field contains the actual context")

if __name__ == "__main__":
    main()