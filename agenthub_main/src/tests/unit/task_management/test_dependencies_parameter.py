#!/usr/bin/env python3
"""
Test script to verify dependencies parameter handling in manage_task create action.
Tests all three formats: array, string, and comma-separated string.
"""

import json
import asyncio
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import pytest

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

def create_mock_facade():
    """Create a mock facade that simulates successful task creation."""
    mock_facade = MagicMock(spec=TaskApplicationFacade)
    mock_facade.create_task = MagicMock(return_value={
        "success": True,
        "task": {
            "id": "test-task-123",
            "title": "Test Task",
            "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
            "dependencies": []
        }
    })
    return mock_facade

@pytest.mark.asyncio
async def test_dependencies_formats():
    """Test all three dependency formats."""

    # Mock the FacadeService
    mock_facade_service = MagicMock(spec=FacadeService)
    mock_facade = create_mock_facade()
    mock_facade_service.get_task_facade = MagicMock(return_value=mock_facade)

    # Create controller with mock
    controller = TaskMCPController(facade_service_or_factory=mock_facade_service)

    # Mock authentication
    with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id',
               return_value="test-user-123"):

        print("Testing dependencies parameter formats...")
        print("-" * 50)

        # Test 1: Array format
        print("\n1. Testing array format: ['id1', 'id2']")
        try:
            result = await controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test with array dependencies",
                assignees=["coding-agent"],
                dependencies=["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002"]
            )
            if result.get("success"):
                print("   ✅ Array format works!")
            else:
                print(f"   ❌ Array format failed: {result.get('error', result)}")
        except Exception as e:
            print(f"   ❌ Array format exception: {e}")

        # Test 2: Single string format
        print("\n2. Testing single string format: 'id1'")
        try:
            result = await controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test with string dependency",
                assignees=["coding-agent"],
                dependencies="550e8400-e29b-41d4-a716-446655440001"
            )
            if result.get("success"):
                print("   ✅ Single string format works!")
            else:
                print(f"   ❌ Single string format failed: {result.get('error', result)}")
        except Exception as e:
            print(f"   ❌ Single string format exception: {e}")

        # Test 3: Comma-separated string format
        print("\n3. Testing comma-separated format: 'id1,id2'")
        try:
            result = await controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test with comma-separated dependencies",
                assignees=["coding-agent"],
                dependencies="550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002"
            )
            if result.get("success"):
                print("   ✅ Comma-separated format works!")
            else:
                print(f"   ❌ Comma-separated format failed: {result.get('error', result)}")
        except Exception as e:
            print(f"   ❌ Comma-separated format exception: {e}")

        # Test 4: Comma-separated with spaces
        print("\n4. Testing comma-separated with spaces: 'id1, id2'")
        try:
            result = await controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test with spaced comma-separated dependencies",
                assignees=["coding-agent"],
                dependencies="550e8400-e29b-41d4-a716-446655440001, 550e8400-e29b-41d4-a716-446655440002"
            )
            if result.get("success"):
                print("   ✅ Comma-separated with spaces format works!")
            else:
                print(f"   ❌ Comma-separated with spaces format failed: {result.get('error', result)}")
        except Exception as e:
            print(f"   ❌ Comma-separated with spaces format exception: {e}")

        print("\n" + "=" * 50)
        print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_dependencies_formats())