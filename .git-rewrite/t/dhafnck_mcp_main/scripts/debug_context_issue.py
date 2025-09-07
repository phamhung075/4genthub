#!/usr/bin/env python3
"""
Debug script to identify where user context is lost in MCP operations.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.auth.mcp_integration.user_context_middleware import current_user_context, MCPUserContext, get_current_user_id
from fastmcp.auth.mcp_integration.thread_context_manager import ThreadContextManager
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


def test_context_in_controller():
    """Test that context is properly available in controller methods."""
    print("\n=== Testing Context in Controller Method ===")
    
    # Create a test user context
    test_user = MCPUserContext(
        user_id="debug-user-789",
        email="debug@example.com",
        username="debuguser",
        roles=["user", "admin"],
        scopes=["mcp:read", "mcp:write", "mcp:admin"]
    )
    
    # Set the context
    current_user_context.set(test_user)
    print(f"✅ Set user context: {test_user.user_id}")
    
    # Check context is set
    user_id_before = get_current_user_id()
    print(f"✅ User ID before controller call: {user_id_before}")
    
    # Create a project controller
    facade_factory = ProjectFacadeFactory()
    
    # Monkey-patch the controller to add debug logging
    original_get_facade = ProjectMCPController._get_facade_for_request
    
    def debug_get_facade(self, user_id=None):
        print(f"\n🔍 DEBUG: _get_facade_for_request called with user_id={user_id}")
        
        # Check context in this method
        context_user_id = get_current_user_id()
        print(f"🔍 DEBUG: get_current_user_id() returned: {context_user_id}")
        
        # Check raw context
        raw_context = current_user_context.get()
        print(f"🔍 DEBUG: current_user_context.get() returned: {raw_context}")
        
        if raw_context:
            print(f"🔍 DEBUG: Context details: user_id={raw_context.user_id}, email={raw_context.email}")
        
        # Call original method
        result = original_get_facade(self, user_id)
        print(f"🔍 DEBUG: Facade created with user_id passed to factory")
        
        return result
    
    ProjectMCPController._get_facade_for_request = debug_get_facade
    
    # Also patch handle_crud_operations to see what's happening
    original_handle_crud = ProjectMCPController.handle_crud_operations
    
    def debug_handle_crud(self, action, project_id=None, name=None, description=None, user_id=None, force=False):
        print(f"\n🔍 DEBUG: handle_crud_operations called with:")
        print(f"  - action: {action}")
        print(f"  - user_id param: {user_id}")
        
        # Check context here
        context_user_id = get_current_user_id()
        print(f"🔍 DEBUG: Context user_id in handle_crud: {context_user_id}")
        
        return original_handle_crud(self, action, project_id, name, description, user_id, force)
    
    ProjectMCPController.handle_crud_operations = debug_handle_crud
    
    # Create controller
    controller = ProjectMCPController(facade_factory)
    
    # Test project creation
    print("\n📋 Testing project creation with authenticated user...")
    try:
        # Check context right before call
        user_id_before_call = get_current_user_id()
        print(f"✅ User ID right before manage_project call: {user_id_before_call}")
        
        result = controller.manage_project(
            action="create",
            name="debug-test-project",
            description="Project to debug authentication context"
        )
        
        print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
        
        if result.get("success"):
            project = result.get("project", {})
            created_by = project.get("user_id") or project.get("created_by")
            
            if created_by == "debug-user-789":
                print(f"✅ SUCCESS: Project created with correct user_id: {created_by}")
                return True
            else:
                print(f"❌ FAILURE: Project created with wrong user_id: {created_by} (expected: debug-user-789)")
                return False
        else:
            print(f"❌ FAILURE: Project creation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ FAILURE: Exception during project creation: {e}")
        logger.exception("Project creation failed")
        return False
    finally:
        # Clean up context
        current_user_context.set(None)


if __name__ == "__main__":
    success = test_context_in_controller()
    sys.exit(0 if success else 1)