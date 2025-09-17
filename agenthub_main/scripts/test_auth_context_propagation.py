#!/usr/bin/env python3
"""
Test script to verify authentication context propagation in MCP operations.

This script tests that JWT-authenticated users have their user_id properly
propagated through thread boundaries in MCP controllers.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.auth.mcp_integration.jwt_auth_backend import create_jwt_auth_backend
from fastmcp.auth.mcp_integration.user_context_middleware import current_user_context, MCPUserContext
from fastmcp.auth.mcp_integration.thread_context_manager import ThreadContextManager, verify_context_propagation
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_direct_context_propagation():
    """Test that ThreadContextManager properly propagates context."""
    print("\n=== Testing Direct Context Propagation ===")
    
    # Create a test user context
    test_user = MCPUserContext(
        user_id="test-user-123",
        email="test@example.com",
        username="testuser",
        roles=["user", "developer"],
        scopes=["mcp:read", "mcp:write"]
    )
    
    # Set the context
    current_user_context.set(test_user)
    print(f"✅ Set user context: {test_user.user_id}")
    
    # Verify it's set
    verification = verify_context_propagation()
    print(f"✅ Context verification before threading: {verification}")
    
    # Create ThreadContextManager
    context_manager = ThreadContextManager()
    
    # Define an async function that checks context
    async def check_context_in_thread():
        verification = verify_context_propagation()
        logger.debug(f"Context in thread: {verification}")
        return verification
    
    # Run with context propagation
    result = context_manager.run_async_with_context(check_context_in_thread)
    
    print(f"✅ Context verification after threading: {result}")
    
    if result["user_id"] == "test-user-123":
        print("✅ SUCCESS: User context properly propagated through thread boundary!")
        return True
    else:
        print(f"❌ FAILURE: Expected user_id 'test-user-123', got '{result['user_id']}'")
        return False


async def test_controller_context_propagation():
    """Test that MCP controllers properly propagate context."""
    print("\n=== Testing Controller Context Propagation ===")
    
    # Create a test user context
    test_user = MCPUserContext(
        user_id="controller-test-user-456",
        email="controller@example.com",
        username="controlleruser",
        roles=["user", "admin"],
        scopes=["mcp:read", "mcp:write", "mcp:admin"]
    )
    
    # Set the context
    current_user_context.set(test_user)
    print(f"✅ Set user context: {test_user.user_id}")
    
    # Create a project controller
    facade_factory = ProjectFacadeFactory()
    controller = ProjectMCPController(facade_factory)
    
    # Test project creation
    print("\n📋 Testing project creation with authenticated user...")
    try:
        result = controller.manage_project(
            action="create",
            name="test-auth-project",
            description="Project to test authentication context"
        )
        
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        if result.get("success"):
            project = result.get("project", {})
            created_by = project.get("user_id") or project.get("created_by")
            
            if created_by == "controller-test-user-456":
                print(f"✅ SUCCESS: Project created with correct user_id: {created_by}")
                return True
            else:
                print(f"❌ FAILURE: Project created with wrong user_id: {created_by} (expected: controller-test-user-456)")
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


async def test_jwt_authentication_flow():
    """Test the full JWT authentication flow."""
    print("\n=== Testing JWT Authentication Flow ===")
    
    # Create JWT backend
    jwt_backend = create_jwt_auth_backend()
    
    # Create a test user
    test_user = MCPUserContext(
        user_id="jwt-test-user-789",
        email="jwt@example.com",
        username="jwtuser",
        roles=["user"],
        scopes=["mcp:read", "mcp:write"]
    )
    
    # Generate a token for the user
    print("🔑 Generating JWT token...")
    token_response = await jwt_backend.create_access_token(
        client_id=test_user.user_id,
        scopes=["mcp:read", "mcp:write"],
        metadata={
            "email": test_user.email,
            "username": test_user.username,
            "roles": test_user.roles
        }
    )
    
    if not token_response:
        print("❌ FAILURE: Could not generate JWT token")
        return False
    
    token = token_response.token
    print(f"✅ Generated JWT token: {token[:20]}...")
    
    # Simulate middleware setting context from token
    print("\n🔐 Simulating middleware authentication...")
    access_token = await jwt_backend.load_access_token(token)
    
    if not access_token:
        print("❌ FAILURE: Could not validate JWT token")
        return False
    
    print(f"✅ Token validated for user: {access_token.client_id}")
    
    # Get user context from token
    user_context = await jwt_backend._get_user_context(access_token.client_id)
    
    if not user_context:
        print("❌ FAILURE: Could not get user context from token")
        return False
    
    # Set the context as middleware would
    current_user_context.set(user_context)
    print(f"✅ User context set from JWT: {user_context.user_id}")
    
    # Verify context propagation
    verification = verify_context_propagation()
    
    if verification["user_id"] == "jwt-test-user-789":
        print("✅ SUCCESS: JWT authentication properly sets user context!")
        return True
    else:
        print(f"❌ FAILURE: Expected user_id 'jwt-test-user-789', got '{verification['user_id']}'")
        return False


async def main():
    """Run all authentication context tests."""
    print("=" * 60)
    print("AUTHENTICATION CONTEXT PROPAGATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Direct context propagation
    results.append(await test_direct_context_propagation())
    
    # Test 2: Controller context propagation
    results.append(await test_controller_context_propagation())
    
    # Test 3: JWT authentication flow
    results.append(await test_jwt_authentication_flow())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Authentication context propagation is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Authentication context propagation needs fixes.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)