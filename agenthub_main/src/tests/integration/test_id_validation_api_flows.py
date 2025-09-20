"""
Integration tests for ID validation in real API flows.
Tests how ID validation integrates with actual API endpoints and controllers
to prevent MCP ID vs Application ID confusion in production scenarios.
"""

import pytest
import json
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    IDValidationError,
    prevent_id_confusion
)


class TestSubtaskAPIIntegrationWithValidation:
    """Integration tests for subtask API with ID validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

        # Create realistic test IDs
        self.project_id = str(uuid4())
        self.git_branch_id = str(uuid4())
        self.user_id = str(uuid4())
        self.task_id = str(uuid4())
        self.subtask_id = str(uuid4())

        # Mock task data
        self.mock_task = {
            "id": self.task_id,
            "git_branch_id": self.git_branch_id,
            "project_id": self.project_id,
            "title": "Test Parent Task",
            "status": "todo"
        }

        self.mock_subtask = {
            "id": self.subtask_id,
            "parent_task_id": self.task_id,
            "title": "Test Subtask",
            "status": "todo"
        }

    def test_subtask_controller_integration_with_validation(self):
        """Test subtask controller with integrated ID validation."""

        class ValidatedSubtaskController:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self._facade_service = Mock()

            def _validate_request_parameters(self, **params) -> None:
                """Validate request parameters before processing."""
                try:
                    prevent_id_confusion(**params)
                except IDValidationError as e:
                    raise ValueError(f"Parameter validation failed: {e}")

            def _get_facade_for_request(self, task_id: str, user_id: str):
                """Get facade with proper ID validation (FIXED VERSION)."""
                # Validate input parameters
                self._validate_request_parameters(task_id=task_id, user_id=user_id)

                # Get task facade to look up git_branch_id
                task_facade = self._facade_service.get_task_facade(user_id=user_id)
                task_response = task_facade.get_task(task_id=task_id)

                if not task_response.get("success"):
                    raise ValueError(f"Task {task_id} not found")

                task_data = task_response["data"]["task"]
                git_branch_id = task_data.get("git_branch_id")

                if not git_branch_id:
                    raise ValueError(f"Task {task_id} missing git_branch_id")

                # Validate task context
                context_result = self.validator.validate_task_context(
                    task_id=task_id,
                    expected_git_branch_id=git_branch_id
                )

                if not context_result.is_valid:
                    raise ValueError(f"Task context validation failed: {context_result.error_message}")

                # Get subtask facade with CORRECT git_branch_id
                return self._facade_service.get_subtask_facade(
                    user_id=user_id,
                    git_branch_id=git_branch_id  # FIXED: Use actual git_branch_id
                )

            def create_subtask(self, task_id: str, title: str, user_id: str, **kwargs) -> Dict:
                """Create subtask with validation."""
                # Get validated facade
                facade = self._get_facade_for_request(task_id=task_id, user_id=user_id)

                # Create subtask
                result = facade.create_subtask(
                    task_id=task_id,  # Use as parent_task_id
                    title=title,
                    **kwargs
                )

                return result

            def get_subtask(self, task_id: str, subtask_id: str, user_id: str) -> Dict:
                """Get subtask with validation."""
                # Validate all parameters
                self._validate_request_parameters(
                    task_id=task_id,
                    user_id=user_id
                )

                # Validate subtask ID format
                subtask_result = self.validator.validate_uuid_format(subtask_id)
                if not subtask_result.is_valid:
                    raise ValueError(f"Invalid subtask ID: {subtask_result.error_message}")

                # Get validated facade
                facade = self._get_facade_for_request(task_id=task_id, user_id=user_id)

                # Get subtask
                result = facade.get_subtask(subtask_id=subtask_id)
                return result

        # Set up mocks
        controller = ValidatedSubtaskController(self.validator)

        # Mock task facade
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {"task": self.mock_task}
        }

        # Mock subtask facade
        mock_subtask_facade = Mock()
        mock_subtask_facade.create_subtask.return_value = {
            "success": True,
            "subtask": self.mock_subtask
        }
        mock_subtask_facade.get_subtask.return_value = {
            "success": True,
            "subtask": self.mock_subtask
        }

        controller._facade_service.get_task_facade.return_value = mock_task_facade
        controller._facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # Test successful subtask creation
        result = controller.create_subtask(
            task_id=self.task_id,
            title="Test Subtask",
            user_id=self.user_id
        )

        assert result["success"] is True
        assert result["subtask"]["parent_task_id"] == self.task_id

        # Verify facade was called with correct git_branch_id
        controller._facade_service.get_subtask_facade.assert_called_with(
            user_id=self.user_id,
            git_branch_id=self.git_branch_id  # Should use git_branch_id from task
        )

        # Test successful subtask retrieval
        get_result = controller.get_subtask(
            task_id=self.task_id,
            subtask_id=self.subtask_id,
            user_id=self.user_id
        )

        assert get_result["success"] is True

        # Test validation failures
        with pytest.raises(ValueError, match="Parameter validation failed"):
            controller.create_subtask(
                task_id="invalid-uuid",
                title="Test",
                user_id=self.user_id
            )

    def test_api_endpoint_integration_with_validation(self):
        """Test API endpoint integration with ID validation."""

        class ValidatedAPIHandler:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.controller = Mock()

            def handle_create_subtask(self, request_data: Dict) -> Dict:
                """Handle POST /api/v2/tasks/{task_id}/subtasks with validation."""
                task_id = request_data.get("task_id")
                user_id = request_data.get("user_id")
                subtask_data = request_data.get("subtask_data", {})

                # API-level validation
                if not task_id or not user_id:
                    return {
                        "success": False,
                        "error": "Missing required parameters: task_id, user_id"
                    }

                try:
                    # Validate request parameters
                    prevent_id_confusion(task_id=task_id, user_id=user_id)

                    # Validate subtask data if ID provided
                    subtask_id = subtask_data.get("id")
                    if subtask_id:
                        subtask_result = self.validator.validate_uuid_format(subtask_id)
                        if not subtask_result.is_valid:
                            return {
                                "success": False,
                                "error": f"Invalid subtask ID: {subtask_result.error_message}"
                            }

                    # Call controller
                    result = self.controller.create_subtask(
                        task_id=task_id,
                        user_id=user_id,
                        **subtask_data
                    )

                    return {
                        "success": True,
                        "data": result
                    }

                except IDValidationError as e:
                    return {
                        "success": False,
                        "error": f"Validation error: {str(e)}"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Internal error: {str(e)}"
                    }

            def handle_get_subtask(self, request_data: Dict) -> Dict:
                """Handle GET /api/v2/tasks/{task_id}/subtasks/{subtask_id} with validation."""
                task_id = request_data.get("task_id")
                subtask_id = request_data.get("subtask_id")
                user_id = request_data.get("user_id")

                # API-level validation
                if not all([task_id, subtask_id, user_id]):
                    return {
                        "success": False,
                        "error": "Missing required parameters"
                    }

                try:
                    # Validate all IDs
                    result = self.validator.validate_parameter_mapping(
                        task_id=task_id,
                        user_id=user_id
                    )

                    if not result.is_valid:
                        return {
                            "success": False,
                            "error": f"Parameter validation failed: {result.error_message}"
                        }

                    subtask_result = self.validator.validate_uuid_format(subtask_id)
                    if not subtask_result.is_valid:
                        return {
                            "success": False,
                            "error": f"Invalid subtask ID: {subtask_result.error_message}"
                        }

                    # Call controller
                    controller_result = self.controller.get_subtask(
                        task_id=task_id,
                        subtask_id=subtask_id,
                        user_id=user_id
                    )

                    return {
                        "success": True,
                        "data": controller_result
                    }

                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e)
                    }

        # Set up API handler
        api_handler = ValidatedAPIHandler(self.validator)
        api_handler.controller.create_subtask.return_value = self.mock_subtask
        api_handler.controller.get_subtask.return_value = self.mock_subtask

        # Test successful create request
        create_request = {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "subtask_data": {
                "title": "New Subtask",
                "description": "Test description"
            }
        }

        create_response = api_handler.handle_create_subtask(create_request)
        assert create_response["success"] is True
        assert create_response["data"]["parent_task_id"] == self.task_id

        # Test successful get request
        get_request = {
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "user_id": self.user_id
        }

        get_response = api_handler.handle_get_subtask(get_request)
        assert get_response["success"] is True

        # Test validation failure cases
        invalid_create_request = {
            "task_id": "invalid-uuid",
            "user_id": self.user_id,
            "subtask_data": {"title": "Test"}
        }

        invalid_response = api_handler.handle_create_subtask(invalid_create_request)
        assert invalid_response["success"] is False
        assert "Validation error" in invalid_response["error"]

    def test_database_integration_with_validation(self):
        """Test database operations with ID validation."""

        class ValidatedDatabaseService:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.tasks = {}
                self.subtasks = {}

            def create_task(self, task_data: Dict) -> str:
                """Create task with validation."""
                task_id = task_data.get("id") or str(uuid4())
                git_branch_id = task_data["git_branch_id"]
                user_id = task_data["user_id"]

                # Validate before database operation
                try:
                    prevent_id_confusion(
                        task_id=task_id,
                        git_branch_id=git_branch_id,
                        user_id=user_id
                    )
                except IDValidationError as e:
                    raise ValueError(f"Task creation validation failed: {e}")

                # Store in "database"
                self.tasks[task_id] = {
                    "id": task_id,
                    "git_branch_id": git_branch_id,
                    "user_id": user_id,
                    "title": task_data["title"],
                    "created_at": "2025-09-20T21:00:00Z"
                }

                return task_id

            def create_subtask(self, subtask_data: Dict) -> str:
                """Create subtask with validation."""
                subtask_id = subtask_data.get("id") or str(uuid4())
                parent_task_id = subtask_data["parent_task_id"]
                user_id = subtask_data["user_id"]

                # Validate parent task exists
                if parent_task_id not in self.tasks:
                    raise ValueError(f"Parent task {parent_task_id} not found")

                parent_task = self.tasks[parent_task_id]

                # Validate user access
                if parent_task["user_id"] != user_id:
                    raise ValueError("User not authorized to create subtask for this task")

                # Validate task context
                context_result = self.validator.validate_task_context(
                    task_id=parent_task_id,
                    expected_git_branch_id=parent_task["git_branch_id"]
                )

                if not context_result.is_valid:
                    raise ValueError(f"Task context validation failed: {context_result.error_message}")

                # Validate subtask parameters
                try:
                    prevent_id_confusion(
                        task_id=parent_task_id,
                        user_id=user_id
                    )
                except IDValidationError as e:
                    raise ValueError(f"Subtask creation validation failed: {e}")

                # Store in "database"
                self.subtasks[subtask_id] = {
                    "id": subtask_id,
                    "parent_task_id": parent_task_id,
                    "user_id": user_id,
                    "title": subtask_data["title"],
                    "status": "todo",
                    "created_at": "2025-09-20T21:00:00Z"
                }

                return subtask_id

            def get_subtasks_for_task(self, task_id: str, user_id: str) -> List[Dict]:
                """Get subtasks with validation."""
                # Validate task exists and user has access
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")

                task = self.tasks[task_id]
                if task["user_id"] != user_id:
                    raise ValueError("User not authorized to access this task")

                # Validate parameters
                try:
                    prevent_id_confusion(task_id=task_id, user_id=user_id)
                except IDValidationError as e:
                    raise ValueError(f"Subtask query validation failed: {e}")

                # Return subtasks
                return [
                    subtask for subtask in self.subtasks.values()
                    if subtask["parent_task_id"] == task_id and subtask["user_id"] == user_id
                ]

            def update_subtask(self, subtask_id: str, update_data: Dict, user_id: str) -> Dict:
                """Update subtask with validation."""
                # Validate subtask exists
                if subtask_id not in self.subtasks:
                    raise ValueError(f"Subtask {subtask_id} not found")

                subtask = self.subtasks[subtask_id]

                # Validate user access
                if subtask["user_id"] != user_id:
                    raise ValueError("User not authorized to update this subtask")

                # Validate parameters
                parent_task_id = subtask["parent_task_id"]
                try:
                    prevent_id_confusion(
                        task_id=parent_task_id,
                        user_id=user_id
                    )
                except IDValidationError as e:
                    raise ValueError(f"Subtask update validation failed: {e}")

                # Update subtask
                for key, value in update_data.items():
                    if key not in ["id", "parent_task_id", "user_id"]:  # Protect key fields
                        subtask[key] = value

                subtask["updated_at"] = "2025-09-20T21:00:00Z"
                return subtask

        # Test database service
        db_service = ValidatedDatabaseService(self.validator)

        # Create parent task
        task_id = db_service.create_task({
            "git_branch_id": self.git_branch_id,
            "user_id": self.user_id,
            "title": "Parent Task"
        })

        assert task_id in db_service.tasks

        # Create subtasks
        subtask1_id = db_service.create_subtask({
            "parent_task_id": task_id,
            "user_id": self.user_id,
            "title": "Subtask 1"
        })

        subtask2_id = db_service.create_subtask({
            "parent_task_id": task_id,
            "user_id": self.user_id,
            "title": "Subtask 2"
        })

        assert subtask1_id in db_service.subtasks
        assert subtask2_id in db_service.subtasks

        # Verify parent relationships
        assert db_service.subtasks[subtask1_id]["parent_task_id"] == task_id
        assert db_service.subtasks[subtask2_id]["parent_task_id"] == task_id

        # Get subtasks for task
        subtasks = db_service.get_subtasks_for_task(task_id, self.user_id)
        assert len(subtasks) == 2
        assert all(s["parent_task_id"] == task_id for s in subtasks)

        # Update subtask
        updated = db_service.update_subtask(
            subtask1_id,
            {"title": "Updated Subtask 1", "status": "in_progress"},
            self.user_id
        )
        assert updated["title"] == "Updated Subtask 1"
        assert updated["status"] == "in_progress"

        # Test validation failures
        with pytest.raises(ValueError, match="validation failed"):
            db_service.create_task({
                "git_branch_id": "invalid-uuid",
                "user_id": self.user_id,
                "title": "Invalid Task"
            })

        with pytest.raises(ValueError, match="not found"):
            db_service.create_subtask({
                "parent_task_id": str(uuid4()),  # Non-existent
                "user_id": self.user_id,
                "title": "Orphan Subtask"
            })

    def test_full_stack_integration_scenario(self):
        """Test full stack integration scenario from API to database."""

        class FullStackService:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.db = {}  # Simple in-memory database

            def api_create_subtask(self, api_request: Dict) -> Dict:
                """Full API endpoint simulation."""
                try:
                    # 1. API Layer Validation
                    task_id = api_request["path_params"]["task_id"]
                    user_id = api_request["auth"]["user_id"]
                    body = api_request["body"]

                    # Validate API parameters
                    api_result = self.validator.validate_parameter_mapping(
                        task_id=task_id,
                        user_id=user_id
                    )

                    if not api_result.is_valid:
                        return {
                            "status": 400,
                            "error": f"Invalid parameters: {api_result.error_message}"
                        }

                    # 2. Controller Layer
                    controller_result = self._controller_create_subtask(
                        task_id=task_id,
                        user_id=user_id,
                        subtask_data=body
                    )

                    if not controller_result["success"]:
                        return {
                            "status": 400,
                            "error": controller_result["error"]
                        }

                    # 3. Return success response
                    return {
                        "status": 201,
                        "data": controller_result["data"]
                    }

                except Exception as e:
                    return {
                        "status": 500,
                        "error": f"Internal server error: {str(e)}"
                    }

            def _controller_create_subtask(self, task_id: str, user_id: str, subtask_data: Dict) -> Dict:
                """Controller layer with business logic."""
                try:
                    # Validate task exists
                    task = self._get_task(task_id, user_id)
                    if not task:
                        return {"success": False, "error": "Task not found"}

                    # Validate task context
                    context_result = self.validator.validate_task_context(
                        task_id=task_id,
                        expected_git_branch_id=task["git_branch_id"]
                    )

                    if not context_result.is_valid:
                        return {
                            "success": False,
                            "error": f"Task context validation failed: {context_result.error_message}"
                        }

                    # Create subtask via service layer
                    subtask = self._service_create_subtask(
                        parent_task_id=task_id,
                        user_id=user_id,
                        subtask_data=subtask_data
                    )

                    return {"success": True, "data": subtask}

                except Exception as e:
                    return {"success": False, "error": str(e)}

            def _service_create_subtask(self, parent_task_id: str, user_id: str, subtask_data: Dict) -> Dict:
                """Service layer with database operations."""
                # Validate service parameters
                try:
                    prevent_id_confusion(task_id=parent_task_id, user_id=user_id)
                except IDValidationError as e:
                    raise ValueError(f"Service validation failed: {e}")

                # Generate subtask ID
                subtask_id = str(uuid4())

                # Validate subtask ID
                subtask_result = self.validator.validate_uuid_format(subtask_id)
                if not subtask_result.is_valid:
                    raise ValueError(f"Generated invalid subtask ID: {subtask_result.error_message}")

                # Store in database
                subtask = {
                    "id": subtask_id,
                    "parent_task_id": parent_task_id,
                    "user_id": user_id,
                    "title": subtask_data["title"],
                    "description": subtask_data.get("description", ""),
                    "status": "todo",
                    "created_at": "2025-09-20T21:00:00Z"
                }

                self.db[f"subtask:{subtask_id}"] = subtask
                return subtask

            def _get_task(self, task_id: str, user_id: str) -> Dict:
                """Get task from database."""
                # Simulate task lookup
                return {
                    "id": task_id,
                    "git_branch_id": str(uuid4()),
                    "user_id": user_id,
                    "title": "Test Task"
                }

        # Test full stack service
        full_stack = FullStackService(self.validator)

        # Successful request
        api_request = {
            "path_params": {"task_id": self.task_id},
            "auth": {"user_id": self.user_id},
            "body": {
                "title": "New Subtask",
                "description": "Test subtask description"
            }
        }

        response = full_stack.api_create_subtask(api_request)
        assert response["status"] == 201
        assert response["data"]["parent_task_id"] == self.task_id
        assert response["data"]["title"] == "New Subtask"

        # Verify subtask was stored
        subtask_id = response["data"]["id"]
        assert f"subtask:{subtask_id}" in full_stack.db

        # Invalid request (bad UUID)
        invalid_request = {
            "path_params": {"task_id": "invalid-uuid"},
            "auth": {"user_id": self.user_id},
            "body": {"title": "Invalid Subtask"}
        }

        invalid_response = full_stack.api_create_subtask(invalid_request)
        assert invalid_response["status"] == 400
        assert "Invalid parameters" in invalid_response["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])