#!/usr/bin/env python3
"""
Verification script for enhanced duplicate project name error handling.
This script verifies the new error response structure with error_code, hint, and suggested_actions.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade


async def verify_duplicate_project_error():
    """Verify that duplicate project name returns enhanced error response."""
    print("=" * 60)
    print("Verifying Enhanced Duplicate Project Name Error Response")
    print("=" * 60)

    # Create facade with a test user
    facade = ProjectApplicationFacade(user_id="test-user-123")

    # First, create a project
    print("\n1. Creating initial project 'Test Project'...")
    result1 = await facade.manage_project(
        action="create",
        name="Test Project",
        description="Initial test project",
        user_id="test-user-123"
    )

    if result1.get("success"):
        print(f"   ✓ Project created successfully: {result1.get('project', {}).get('id')}")
    else:
        print(f"   ✗ Failed to create project: {result1.get('error')}")
        return False

    # Now try to create another project with the same name
    print("\n2. Attempting to create duplicate project 'Test Project'...")
    result2 = await facade.manage_project(
        action="create",
        name="Test Project",
        description="Duplicate test project",
        user_id="test-user-123"
    )

    print("\n3. Verifying enhanced error response...")

    # Check the response structure
    checks = {
        "success is False": result2.get("success") is False,
        "error message present": "error" in result2 and "already exists" in result2["error"].lower(),
        "error_code is DUPLICATE_PROJECT_NAME": result2.get("error_code") == "DUPLICATE_PROJECT_NAME",
        "hint present": "hint" in result2 and len(result2["hint"]) > 0,
        "suggested_actions present": "suggested_actions" in result2 and isinstance(result2["suggested_actions"], list),
        "suggested_actions has items": len(result2.get("suggested_actions", [])) > 0,
    }

    # Print detailed results
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False

    # Print the full response for verification
    print("\n4. Full error response structure:")
    print("-" * 60)
    import json
    print(json.dumps(result2, indent=2))
    print("-" * 60)

    # Cleanup
    print("\n5. Cleaning up test project...")
    if result1.get("success"):
        project_id = result1.get("project", {}).get('id')
        cleanup_result = await facade.manage_project(
            action="delete",
            project_id=project_id,
            user_id="test-user-123",
            force=True
        )
        if cleanup_result.get("success"):
            print("   ✓ Test project deleted successfully")
        else:
            print(f"   ✗ Failed to delete test project: {cleanup_result.get('error')}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Enhancement is working correctly!")
    else:
        print("✗ SOME CHECKS FAILED - Please review the implementation")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(verify_duplicate_project_error())
    sys.exit(0 if success else 1)
