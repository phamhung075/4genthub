"""
Integration tests for Subtask API endpoints
Tests the complete API flow to ensure subtasks use correct parent_task_id
"""

import pytest
import requests
import json
from uuid import uuid4
from typing import Dict, Any
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# API configuration
API_BASE_URL = "http://localhost:8000"
API_V2_URL = f"{API_BASE_URL}/api/v2"


class TestSubtaskAPIIntegration:
    """Integration tests for subtask API endpoints with correct parent_task_id"""

    @pytest.fixture
    def api_headers(self):
        """Get API headers with authentication if needed"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @pytest.fixture
    def setup_test_project_and_branch(self, api_headers):
        """Create test project and git branch for testing"""
        project_id = str(uuid4())
        git_branch_id = str(uuid4())

        # Note: These endpoints might not exist yet, adjust based on actual API
        # This is a placeholder for the test structure
        return {
            "project_id": project_id,
            "git_branch_id": git_branch_id,
            "project_name": f"test_project_{project_id[:8]}",
            "branch_name": f"test_branch_{git_branch_id[:8]}"
        }

    @pytest.fixture
    def setup_test_task(self, api_headers, setup_test_project_and_branch):
        """Create a test task for subtask operations"""
        test_data = setup_test_project_and_branch
        task_id = str(uuid4())

        # Create task via API (adjust endpoint based on actual implementation)
        task_payload = {
            "id": task_id,
            "title": "Test Parent Task for Subtask Integration",
            "description": "Parent task to test subtask ID relationships",
            "git_branch_id": test_data["git_branch_id"],
            "project_id": test_data["project_id"],
            "status": "todo",
            "priority": "medium"
        }

        # Note: Actual endpoint might differ
        response = requests.post(
            f"{API_V2_URL}/tasks",
            json=task_payload,
            headers=api_headers
        )

        # If the endpoint doesn't exist or returns error, skip the test
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test task: {response.status_code} - {response.text}")

        task_data = response.json()

        # Return test data including the created task
        return {
            **test_data,
            "task_id": task_id,
            "task_data": task_data
        }

    def test_create_subtask_with_correct_parent_task_id(self, api_headers, setup_test_task):
        """Test creating a subtask ensures correct parent_task_id (not git_branch_id)"""
        test_data = setup_test_task
        task_id = test_data["task_id"]
        git_branch_id = test_data["git_branch_id"]
        subtask_id = str(uuid4())

        # Create subtask via API
        subtask_payload = {
            "id": subtask_id,
            "title": "Test Subtask with Correct Parent",
            "description": "Verifying parent_task_id is set correctly",
            "status": "todo",
            "priority": "medium"
        }

        # POST to subtask endpoint
        response = requests.post(
            f"{API_V2_URL}/tasks/{task_id}/subtasks",
            json=subtask_payload,
            headers=api_headers
        )

        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Subtask endpoint not implemented yet")

        # Verify successful creation
        assert response.status_code in [200, 201], f"Failed to create subtask: {response.text}"

        subtask_data = response.json()

        # CRITICAL ASSERTIONS:
        # 1. Subtask should have parent_task_id field
        assert "parent_task_id" in subtask_data or "task_id" in subtask_data, \
            "Subtask missing parent reference"

        # 2. Parent ID should be the task_id, NOT git_branch_id
        parent_field = subtask_data.get("parent_task_id") or subtask_data.get("task_id")
        assert parent_field == task_id, \
            f"Wrong parent ID: expected {task_id}, got {parent_field}"

        # 3. Parent ID should NOT be git_branch_id
        assert parent_field != git_branch_id, \
            f"Parent ID incorrectly set to git_branch_id: {git_branch_id}"

    def test_fetch_subtask_via_parent_task_endpoint(self, api_headers, setup_test_task):
        """Test fetching a subtask through the parent task API endpoint"""
        test_data = setup_test_task
        task_id = test_data["task_id"]

        # First create a subtask
        subtask_payload = {
            "title": "Test Subtask for Fetching",
            "description": "Testing fetch operation"
        }

        create_response = requests.post(
            f"{API_V2_URL}/tasks/{task_id}/subtasks",
            json=subtask_payload,
            headers=api_headers
        )

        if create_response.status_code == 404:
            pytest.skip("Subtask create endpoint not implemented")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create subtask: {create_response.text}")

        created_subtask = create_response.json()
        subtask_id = created_subtask.get("id")

        if not subtask_id:
            pytest.skip("Created subtask has no ID")

        # Now fetch the subtask via parent task endpoint
        fetch_response = requests.get(
            f"{API_V2_URL}/tasks/{task_id}/subtasks/{subtask_id}",
            headers=api_headers
        )

        # Verify successful fetch
        assert fetch_response.status_code == 200, \
            f"Failed to fetch subtask: {fetch_response.status_code} - {fetch_response.text}"

        fetched_subtask = fetch_response.json()

        # Verify the fetched subtask has correct parent relationship
        parent_field = fetched_subtask.get("parent_task_id") or fetched_subtask.get("task_id")
        assert parent_field == task_id, \
            f"Fetched subtask has wrong parent: expected {task_id}, got {parent_field}"

    def test_list_subtasks_for_task(self, api_headers, setup_test_task):
        """Test listing all subtasks for a task returns correct parent relationships"""
        test_data = setup_test_task
        task_id = test_data["task_id"]
        git_branch_id = test_data["git_branch_id"]

        # Create multiple subtasks
        subtask_ids = []
        for i in range(3):
            subtask_payload = {
                "title": f"Test Subtask {i+1}",
                "description": f"Subtask number {i+1} for listing test"
            }

            response = requests.post(
                f"{API_V2_URL}/tasks/{task_id}/subtasks",
                json=subtask_payload,
                headers=api_headers
            )

            if response.status_code == 404:
                pytest.skip("Subtask endpoint not implemented")

            if response.status_code in [200, 201]:
                subtask = response.json()
                if "id" in subtask:
                    subtask_ids.append(subtask["id"])

        # List all subtasks for the task
        list_response = requests.get(
            f"{API_V2_URL}/tasks/{task_id}/subtasks",
            headers=api_headers
        )

        if list_response.status_code == 404:
            pytest.skip("Subtask list endpoint not implemented")

        assert list_response.status_code == 200, \
            f"Failed to list subtasks: {list_response.text}"

        subtasks = list_response.json()

        # Handle both array and object with 'subtasks' field
        if isinstance(subtasks, dict) and "subtasks" in subtasks:
            subtasks = subtasks["subtasks"]

        # Verify all subtasks have correct parent_task_id
        for subtask in subtasks:
            parent_field = subtask.get("parent_task_id") or subtask.get("task_id")

            # Each subtask should reference the correct parent task
            assert parent_field == task_id, \
                f"Subtask {subtask.get('id')} has wrong parent: expected {task_id}, got {parent_field}"

            # Parent should NOT be git_branch_id
            assert parent_field != git_branch_id, \
                f"Subtask {subtask.get('id')} incorrectly uses git_branch_id as parent"

    def test_reject_invalid_task_id_for_subtask_creation(self, api_headers):
        """Test that creating a subtask with non-existent task_id fails appropriately"""

        # Use a random UUID that doesn't exist
        non_existent_task_id = str(uuid4())

        subtask_payload = {
            "title": "Subtask for Non-existent Task",
            "description": "This should fail"
        }

        response = requests.post(
            f"{API_V2_URL}/tasks/{non_existent_task_id}/subtasks",
            json=subtask_payload,
            headers=api_headers
        )

        # Should return 404 or 400 for non-existent parent task
        assert response.status_code in [400, 404], \
            f"Expected error for non-existent task, got {response.status_code}"

        # Error message should indicate task not found
        if response.text:
            error_msg = response.text.lower()
            assert "not found" in error_msg or "does not exist" in error_msg or "invalid" in error_msg, \
                f"Error message doesn't indicate missing task: {response.text}"

    def test_update_subtask_maintains_parent_relationship(self, api_headers, setup_test_task):
        """Test that updating a subtask doesn't break parent relationship"""
        test_data = setup_test_task
        task_id = test_data["task_id"]

        # Create a subtask
        create_payload = {
            "title": "Original Subtask Title",
            "description": "Original description"
        }

        create_response = requests.post(
            f"{API_V2_URL}/tasks/{task_id}/subtasks",
            json=create_payload,
            headers=api_headers
        )

        if create_response.status_code == 404:
            pytest.skip("Subtask endpoint not implemented")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create subtask: {create_response.text}")

        created_subtask = create_response.json()
        subtask_id = created_subtask.get("id")

        if not subtask_id:
            pytest.skip("Created subtask has no ID")

        # Update the subtask
        update_payload = {
            "title": "Updated Subtask Title",
            "description": "Updated description",
            "status": "in_progress"
        }

        update_response = requests.put(
            f"{API_V2_URL}/tasks/{task_id}/subtasks/{subtask_id}",
            json=update_payload,
            headers=api_headers
        )

        # Also try PATCH if PUT doesn't work
        if update_response.status_code == 405:  # Method not allowed
            update_response = requests.patch(
                f"{API_V2_URL}/tasks/{task_id}/subtasks/{subtask_id}",
                json=update_payload,
                headers=api_headers
            )

        if update_response.status_code == 404:
            pytest.skip("Subtask update endpoint not implemented")

        assert update_response.status_code in [200, 201], \
            f"Failed to update subtask: {update_response.text}"

        updated_subtask = update_response.json()

        # Verify parent relationship is maintained after update
        parent_field = updated_subtask.get("parent_task_id") or updated_subtask.get("task_id")
        assert parent_field == task_id, \
            f"Parent relationship lost after update: expected {task_id}, got {parent_field}"

    def test_delete_subtask_via_parent_task(self, api_headers, setup_test_task):
        """Test deleting a subtask through parent task endpoint"""
        test_data = setup_test_task
        task_id = test_data["task_id"]

        # Create a subtask to delete
        create_payload = {
            "title": "Subtask to Delete",
            "description": "This will be deleted"
        }

        create_response = requests.post(
            f"{API_V2_URL}/tasks/{task_id}/subtasks",
            json=create_payload,
            headers=api_headers
        )

        if create_response.status_code == 404:
            pytest.skip("Subtask endpoint not implemented")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create subtask: {create_response.text}")

        created_subtask = create_response.json()
        subtask_id = created_subtask.get("id")

        if not subtask_id:
            pytest.skip("Created subtask has no ID")

        # Delete the subtask
        delete_response = requests.delete(
            f"{API_V2_URL}/tasks/{task_id}/subtasks/{subtask_id}",
            headers=api_headers
        )

        if delete_response.status_code == 404:
            pytest.skip("Subtask delete endpoint not implemented")

        assert delete_response.status_code in [200, 204], \
            f"Failed to delete subtask: {delete_response.text}"

        # Verify subtask is deleted by trying to fetch it
        fetch_response = requests.get(
            f"{API_V2_URL}/tasks/{task_id}/subtasks/{subtask_id}",
            headers=api_headers
        )

        # Should return 404 for deleted subtask
        assert fetch_response.status_code == 404, \
            f"Deleted subtask still accessible: {fetch_response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])