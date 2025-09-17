#!/usr/bin/env python3
"""
Comprehensive test for dependencies parameter handling in manage_task create action.
Tests all possible input formats to ensure flexibility.
"""

import json
import asyncio
from typing import Dict, Any, List
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

def create_mock_facade():
    """Create a mock facade that simulates successful task creation."""
    mock_facade = MagicMock(spec=TaskApplicationFacade)

    def create_task_side_effect(request):
        # Capture the dependencies from the request to verify they were processed correctly
        return {
            "success": True,
            "task": {
                "id": "test-task-123",
                "title": request.title,
                "git_branch_id": request.git_branch_id,
                "dependencies": request.dependencies if hasattr(request, 'dependencies') else [],
                "assignees": request.assignees if hasattr(request, 'assignees') else []
            }
        }

    mock_facade.create_task = MagicMock(side_effect=create_task_side_effect)
    return mock_facade

async def test_all_dependency_formats():
    """Test all possible dependency input formats."""

    # Mock the FacadeService
    mock_facade_service = MagicMock(spec=FacadeService)
    mock_facade = create_mock_facade()
    mock_facade_service.get_task_facade = MagicMock(return_value=mock_facade)

    # Create controller with mock
    controller = TaskMCPController(facade_service_or_factory=mock_facade_service)

    # Mock authentication
    with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id',
               return_value="test-user-123"):

        print("Testing all dependency parameter formats...")
        print("=" * 60)

        test_cases = [
            {
                "name": "Python list format",
                "dependencies": ["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002"],
                "expected_count": 2
            },
            {
                "name": "Single string UUID",
                "dependencies": "550e8400-e29b-41d4-a716-446655440001",
                "expected_count": 1
            },
            {
                "name": "Comma-separated string",
                "dependencies": "550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002",
                "expected_count": 2
            },
            {
                "name": "Comma-separated with spaces",
                "dependencies": "550e8400-e29b-41d4-a716-446655440001, 550e8400-e29b-41d4-a716-446655440002",
                "expected_count": 2
            },
            {
                "name": "Empty list",
                "dependencies": [],
                "expected_count": 0
            },
            {
                "name": "Empty string",
                "dependencies": "",
                "expected_count": 0
            },
            {
                "name": "None (not provided)",
                "dependencies": None,
                "expected_count": 0
            },
            {
                "name": "Single item list",
                "dependencies": ["550e8400-e29b-41d4-a716-446655440001"],
                "expected_count": 1
            },
            {
                "name": "Three items comma-separated",
                "dependencies": "550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002,550e8400-e29b-41d4-a716-446655440003",
                "expected_count": 3
            }
        ]

        success_count = 0
        failure_count = 0

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. Testing {test_case['name']}: {test_case['dependencies']!r}")

            try:
                # Prepare kwargs
                kwargs = {
                    "action": "create",
                    "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": f"Test with {test_case['name']}",
                    "assignees": ["coding-agent"]
                }

                # Only add dependencies if not None
                if test_case['dependencies'] is not None:
                    kwargs['dependencies'] = test_case['dependencies']

                result = await controller.manage_task(**kwargs)

                if result.get("success"):
                    # Check if the task has the expected number of dependencies
                    task = result.get("task", {})
                    actual_deps = task.get("dependencies", [])
                    actual_count = len(actual_deps) if isinstance(actual_deps, list) else 0

                    if actual_count == test_case['expected_count']:
                        print(f"   ✅ PASS - {test_case['name']} works correctly!")
                        print(f"      Expected {test_case['expected_count']} dependencies, got {actual_count}")
                        success_count += 1
                    else:
                        print(f"   ⚠️  PARTIAL - Task created but dependency count mismatch")
                        print(f"      Expected {test_case['expected_count']} dependencies, got {actual_count}")
                        print(f"      Actual dependencies: {actual_deps}")
                        failure_count += 1
                else:
                    print(f"   ❌ FAIL - {test_case['name']}: {result.get('error', result)}")
                    failure_count += 1

            except Exception as e:
                print(f"   ❌ EXCEPTION - {test_case['name']}: {e}")
                failure_count += 1

        # Test edge case: Mixed assignees and dependencies formats
        print("\n" + "=" * 60)
        print("\nEdge Case: Mixed formats for assignees AND dependencies")
        print("-" * 60)

        edge_cases = [
            {
                "name": "Both as lists",
                "assignees": ["coding-agent", "test-orchestrator-agent"],
                "dependencies": ["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002"],
            },
            {
                "name": "Assignees as string, dependencies as list",
                "assignees": "coding-agent,test-orchestrator-agent",
                "dependencies": ["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002"],
            },
            {
                "name": "Assignees as list, dependencies as string",
                "assignees": ["coding-agent", "test-orchestrator-agent"],
                "dependencies": "550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002",
            },
            {
                "name": "Both as comma-separated strings",
                "assignees": "coding-agent, test-orchestrator-agent",
                "dependencies": "550e8400-e29b-41d4-a716-446655440001, 550e8400-e29b-41d4-a716-446655440002",
            }
        ]

        for test_case in edge_cases:
            print(f"\nTesting {test_case['name']}")
            try:
                result = await controller.manage_task(
                    action="create",
                    git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                    title=f"Edge case: {test_case['name']}",
                    assignees=test_case['assignees'],
                    dependencies=test_case['dependencies']
                )

                if result.get("success"):
                    task = result.get("task", {})
                    print(f"   ✅ PASS - Both parameters handled correctly")
                    print(f"      Assignees: {task.get('assignees', [])}")
                    print(f"      Dependencies: {task.get('dependencies', [])}")
                    success_count += 1
                else:
                    print(f"   ❌ FAIL - {result.get('error', result)}")
                    failure_count += 1

            except Exception as e:
                print(f"   ❌ EXCEPTION: {e}")
                failure_count += 1

        # Final summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {success_count}")
        print(f"❌ Failed: {failure_count}")
        print(f"Total tests: {success_count + failure_count}")

        if failure_count == 0:
            print("\n🎉 All tests passed! The dependencies parameter handling is working correctly.")
        else:
            print(f"\n⚠️  {failure_count} test(s) failed. Review the implementation.")

if __name__ == "__main__":
    asyncio.run(test_all_dependency_formats())