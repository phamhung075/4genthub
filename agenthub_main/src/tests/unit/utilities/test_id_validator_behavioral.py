"""
Behavioral tests for IDValidator domain service.
Tests complex ID confusion scenarios and behavioral patterns that prevent
the critical MCP ID vs Application ID confusion bug.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from typing import Dict, List, Any
from dataclasses import dataclass
from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    IDValidationError,
    validate_uuid,
    prevent_id_confusion,
)


@dataclass
class SimulatedTask:
    """Simulated task for testing scenarios."""
    id: str
    git_branch_id: str
    project_id: str
    title: str


@dataclass
class SimulatedSubtask:
    """Simulated subtask for testing scenarios."""
    id: str
    parent_task_id: str
    title: str


class TestIDConfusionScenarios:
    """Tests for complex ID confusion scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

        # Create realistic test data
        self.mcp_task_id = str(uuid4())
        self.app_task_id = str(uuid4())
        self.git_branch_id = str(uuid4())
        self.project_id = str(uuid4())
        self.user_id = str(uuid4())

        # Simulate the real-world objects
        self.simulated_task = SimulatedTask(
            id=self.app_task_id,
            git_branch_id=self.git_branch_id,
            project_id=self.project_id,
            title="Test Task"
        )

    def test_subtask_controller_line_270_bug_scenario(self):
        """
        Test the exact scenario that caused the bug in subtask_mcp_controller.py:270
        where task_id was incorrectly passed as git_branch_id to facade service.
        """
        # Simulate the bug scenario
        class BuggyControllerBehavior:
            def __init__(self, validator: IDValidator):
                self.validator = validator

            def get_facade_for_request_buggy(self, task_id: str, user_id: str):
                """Simulate the buggy behavior - passing task_id as git_branch_id."""
                # BUG: This is what the controller was doing incorrectly
                return self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    git_branch_id=task_id,  # BUG: Should be actual git_branch_id
                    user_id=user_id
                )

            def get_facade_for_request_fixed(self, task_id: str, user_id: str):
                """Simulate the fixed behavior - proper ID lookup."""
                # FIXED: Look up the correct git_branch_id from task
                # (In real code, this would be a database lookup)
                git_branch_id = self.lookup_git_branch_id_for_task(task_id)

                return self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    git_branch_id=git_branch_id,
                    user_id=user_id
                )

            def lookup_git_branch_id_for_task(self, task_id: str) -> str:
                """Simulate looking up git_branch_id from task."""
                # In real scenario, this would query the database
                if task_id == self.app_task_id:
                    return self.git_branch_id
                raise ValueError(f"Task {task_id} not found")

        controller = BuggyControllerBehavior(self.validator)

        # Test buggy behavior - should detect the critical error
        buggy_result = controller.get_facade_for_request_buggy(
            task_id=self.app_task_id,
            user_id=self.user_id
        )

        # The validator should detect this as a warning (same ID used for different purposes)
        assert buggy_result.warnings is not None
        assert any("Same ID value used for multiple parameters" in warning
                  for warning in buggy_result.warnings)

        # Test fixed behavior - should be valid
        fixed_result = controller.get_facade_for_request_fixed(
            task_id=self.app_task_id,
            user_id=self.user_id
        )

        assert fixed_result.is_valid is True
        assert fixed_result.warnings is None or len(fixed_result.warnings) == 0

    def test_mcp_task_management_workflow_confusion(self):
        """Test confusion between MCP task management and application tasks."""

        class MCPTaskWorkflow:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.mcp_tasks = {}  # Simulate MCP task storage
                self.app_tasks = {}  # Simulate application task storage

            def create_mcp_task(self, title: str) -> str:
                """Create an MCP task and return its ID."""
                mcp_id = str(uuid4())
                self.mcp_tasks[mcp_id] = {"title": title, "type": "mcp"}
                return mcp_id

            def create_app_task_from_mcp(self, mcp_task_id: str, git_branch_id: str) -> str:
                """Create an application task from MCP task (correct flow)."""
                # Validate that we're not confusing IDs
                result = self.validator.validate_parameter_mapping(
                    task_id=mcp_task_id,  # This is actually MCP ID at this point
                    git_branch_id=git_branch_id
                )

                if not result.is_valid:
                    raise IDValidationError(
                        message=f"MCP task ID validation failed: {result.error_message}",
                        id_value=mcp_task_id
                    )

                # Create proper application task
                app_task_id = str(uuid4())
                self.app_tasks[app_task_id] = {
                    "id": app_task_id,
                    "git_branch_id": git_branch_id,
                    "mcp_source": mcp_task_id,
                    "type": "application"
                }
                return app_task_id

            def get_app_task_incorrectly(self, mcp_task_id: str) -> Dict:
                """Simulate incorrect usage - treating MCP ID as app task ID."""
                # This is the BUG: trying to use MCP task ID as application task ID
                if mcp_task_id in self.app_tasks:
                    return self.app_tasks[mcp_task_id]
                else:
                    # This would fail in real scenario
                    raise ValueError(f"Application task {mcp_task_id} not found")

            def get_app_task_correctly(self, app_task_id: str) -> Dict:
                """Simulate correct usage - using proper application task ID."""
                if app_task_id in self.app_tasks:
                    return self.app_tasks[app_task_id]
                else:
                    raise ValueError(f"Application task {app_task_id} not found")

        workflow = MCPTaskWorkflow(self.validator)

        # Create MCP task
        mcp_id = workflow.create_mcp_task("Test MCP Task")

        # Create application task from MCP (correct flow)
        app_id = workflow.create_app_task_from_mcp(mcp_id, self.git_branch_id)

        # Test correct usage
        app_task = workflow.get_app_task_correctly(app_id)
        assert app_task["id"] == app_id
        assert app_task["git_branch_id"] == self.git_branch_id
        assert app_task["mcp_source"] == mcp_id

        # Test incorrect usage (this should fail)
        with pytest.raises(ValueError, match="not found"):
            workflow.get_app_task_incorrectly(mcp_id)

    def test_cascade_id_confusion_prevention(self):
        """Test prevention of cascade ID confusion across multiple levels."""

        class MultiLevelSystem:
            def __init__(self, validator: IDValidator):
                self.validator = validator

            def create_subtask_with_validation(self, parent_task_id: str, git_branch_id: str) -> str:
                """Create subtask with proper ID validation."""
                # Validate parent task context
                context_result = self.validator.validate_task_context(
                    task_id=parent_task_id,
                    expected_git_branch_id=git_branch_id
                )

                if not context_result.is_valid:
                    raise IDValidationError(
                        message=f"Task context validation failed: {context_result.error_message}",
                        id_value=parent_task_id
                    )

                # Validate parameter mapping for subtask creation
                subtask_id = str(uuid4())
                mapping_result = self.validator.validate_parameter_mapping(
                    task_id=parent_task_id,
                    git_branch_id=git_branch_id
                )

                if not mapping_result.is_valid:
                    raise IDValidationError(
                        message=f"Parameter mapping validation failed: {mapping_result.error_message}",
                        id_value=str({"task_id": parent_task_id, "git_branch_id": git_branch_id})
                    )

                return subtask_id

            def create_subtask_without_validation(self, parent_task_id: str) -> str:
                """Create subtask without validation (problematic)."""
                # This bypasses validation and could lead to confusion
                return str(uuid4())

        system = MultiLevelSystem(self.validator)

        # Test correct creation with validation
        subtask_id = system.create_subtask_with_validation(
            parent_task_id=self.app_task_id,
            git_branch_id=self.git_branch_id
        )
        assert subtask_id is not None

        # Test creation with invalid context (should fail)
        with pytest.raises(IDValidationError, match="identical"):
            system.create_subtask_with_validation(
                parent_task_id=self.app_task_id,
                git_branch_id=self.app_task_id  # BUG: Same ID used
            )

    def test_real_world_api_endpoint_behavior(self):
        """Test behavior patterns from real API endpoints."""

        class SubtaskAPIEndpoint:
            def __init__(self, validator: IDValidator):
                self.validator = validator

            def get_subtask(self, task_id: str, subtask_id: str, user_id: str) -> Dict:
                """Simulate GET /api/v2/tasks/{task_id}/subtasks/{subtask_id}"""
                # Validate all IDs before processing
                validation_result = self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    user_id=user_id
                )

                if not validation_result.is_valid:
                    raise IDValidationError(
                        message=f"API parameter validation failed: {validation_result.error_message}",
                        id_value=str({"task_id": task_id, "subtask_id": subtask_id})
                    )

                # Validate subtask ID format
                subtask_result = self.validator.validate_uuid_format(subtask_id)
                if not subtask_result.is_valid:
                    raise IDValidationError(
                        message=f"Invalid subtask ID: {subtask_result.error_message}",
                        id_value=subtask_id
                    )

                # Simulate successful retrieval
                return {
                    "id": subtask_id,
                    "parent_task_id": task_id,
                    "title": "Test Subtask"
                }

            def create_subtask(self, task_id: str, subtask_data: Dict, user_id: str) -> Dict:
                """Simulate POST /api/v2/tasks/{task_id}/subtasks"""
                # Validate parent task exists and user has access
                validation_result = self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    user_id=user_id
                )

                if not validation_result.is_valid:
                    raise IDValidationError(
                        message=f"Parent task validation failed: {validation_result.error_message}",
                        id_value=task_id
                    )

                # Create subtask with proper parent relationship
                subtask_id = str(uuid4())
                return {
                    "id": subtask_id,
                    "parent_task_id": task_id,  # CRITICAL: Correct parent reference
                    "title": subtask_data.get("title", "New Subtask"),
                    "status": "todo"
                }

        api = SubtaskAPIEndpoint(self.validator)

        # Test successful subtask creation
        subtask = api.create_subtask(
            task_id=self.app_task_id,
            subtask_data={"title": "Test Subtask"},
            user_id=self.user_id
        )

        assert subtask["parent_task_id"] == self.app_task_id
        assert subtask["id"] != self.app_task_id  # Should be different

        # Test successful subtask retrieval
        retrieved = api.get_subtask(
            task_id=self.app_task_id,
            subtask_id=subtask["id"],
            user_id=self.user_id
        )

        assert retrieved["parent_task_id"] == self.app_task_id

        # Test with invalid IDs
        with pytest.raises(IDValidationError):
            api.get_subtask(
                task_id="invalid-uuid",
                subtask_id=subtask["id"],
                user_id=self.user_id
            )

    def test_database_layer_id_consistency(self):
        """Test ID consistency at the database layer."""

        class DatabaseLayer:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.tasks = {}
                self.subtasks = {}

            def insert_task(self, task_data: Dict) -> str:
                """Insert task with ID validation."""
                task_id = task_data.get("id") or str(uuid4())
                git_branch_id = task_data["git_branch_id"]

                # Validate before database insertion
                result = self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    git_branch_id=git_branch_id
                )

                if not result.is_valid:
                    raise IDValidationError(
                        message=f"Database validation failed: {result.error_message}",
                        id_value=str(task_data)
                    )

                self.tasks[task_id] = {
                    "id": task_id,
                    "git_branch_id": git_branch_id,
                    "title": task_data["title"]
                }
                return task_id

            def insert_subtask(self, subtask_data: Dict) -> str:
                """Insert subtask with parent validation."""
                subtask_id = subtask_data.get("id") or str(uuid4())
                parent_task_id = subtask_data["parent_task_id"]

                # Validate parent task exists
                if parent_task_id not in self.tasks:
                    raise ValueError(f"Parent task {parent_task_id} not found")

                parent_task = self.tasks[parent_task_id]

                # Validate that subtask parent relationship is correct
                context_result = self.validator.validate_task_context(
                    task_id=parent_task_id,
                    expected_git_branch_id=parent_task["git_branch_id"]
                )

                if not context_result.is_valid:
                    raise IDValidationError(
                        message=f"Subtask parent validation failed: {context_result.error_message}",
                        id_value=parent_task_id
                    )

                self.subtasks[subtask_id] = {
                    "id": subtask_id,
                    "parent_task_id": parent_task_id,
                    "title": subtask_data["title"]
                }
                return subtask_id

            def get_subtasks_for_task(self, task_id: str) -> List[Dict]:
                """Get all subtasks for a task."""
                # Validate task exists
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")

                return [
                    subtask for subtask in self.subtasks.values()
                    if subtask["parent_task_id"] == task_id
                ]

        db = DatabaseLayer(self.validator)

        # Insert parent task
        task_id = db.insert_task({
            "git_branch_id": self.git_branch_id,
            "title": "Parent Task"
        })

        # Insert subtasks
        subtask1_id = db.insert_subtask({
            "parent_task_id": task_id,
            "title": "Subtask 1"
        })

        subtask2_id = db.insert_subtask({
            "parent_task_id": task_id,
            "title": "Subtask 2"
        })

        # Verify relationships
        subtasks = db.get_subtasks_for_task(task_id)
        assert len(subtasks) == 2
        assert all(s["parent_task_id"] == task_id for s in subtasks)

        # Test invalid parent reference (should fail)
        with pytest.raises(ValueError, match="not found"):
            db.insert_subtask({
                "parent_task_id": str(uuid4()),  # Non-existent parent
                "title": "Orphan Subtask"
            })

    def test_cross_session_id_consistency(self):
        """Test ID consistency across different user sessions."""

        class SessionManager:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.sessions = {}

            def create_session(self, user_id: str) -> str:
                """Create a new user session."""
                session_id = str(uuid4())
                self.sessions[session_id] = {
                    "user_id": user_id,
                    "created_tasks": [],
                    "accessed_tasks": []
                }
                return session_id

            def access_task_in_session(self, session_id: str, task_id: str) -> bool:
                """Access a task within a session."""
                if session_id not in self.sessions:
                    return False

                session = self.sessions[session_id]
                user_id = session["user_id"]

                # Validate session access
                result = self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    user_id=user_id
                )

                if result.is_valid:
                    session["accessed_tasks"].append(task_id)
                    return True
                return False

            def create_task_in_session(self, session_id: str, git_branch_id: str) -> str:
                """Create a task within a session."""
                session = self.sessions[session_id]
                user_id = session["user_id"]
                task_id = str(uuid4())

                # Validate task creation
                result = self.validator.validate_parameter_mapping(
                    task_id=task_id,
                    git_branch_id=git_branch_id,
                    user_id=user_id
                )

                if not result.is_valid:
                    raise IDValidationError(
                        message=f"Session task creation failed: {result.error_message}",
                        id_value=str({"session": session_id, "task": task_id})
                    )

                session["created_tasks"].append(task_id)
                return task_id

        session_mgr = SessionManager(self.validator)

        # Create sessions for different users
        user1_session = session_mgr.create_session(self.user_id)
        user2_session = session_mgr.create_session(str(uuid4()))

        # Create tasks in different sessions
        task1 = session_mgr.create_task_in_session(user1_session, self.git_branch_id)
        task2 = session_mgr.create_task_in_session(user2_session, str(uuid4()))

        # Test cross-session access
        assert session_mgr.access_task_in_session(user1_session, task1) is True
        assert session_mgr.access_task_in_session(user2_session, task2) is True

        # Verify session isolation
        session1 = session_mgr.sessions[user1_session]
        session2 = session_mgr.sessions[user2_session]

        assert task1 in session1["created_tasks"]
        assert task1 not in session2["created_tasks"]
        assert task2 in session2["created_tasks"]
        assert task2 not in session1["created_tasks"]


class TestComplexValidationFlows:
    """Tests for complex validation workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

    def test_multi_step_validation_pipeline(self):
        """Test a multi-step validation pipeline."""

        class ValidationPipeline:
            def __init__(self, validator: IDValidator):
                self.validator = validator
                self.validation_history = []

            def validate_step1_format(self, id_value: str, context: str) -> ValidationResult:
                """Step 1: Format validation."""
                result = self.validator.validate_uuid_format(id_value)
                self.validation_history.append(("format", context, result.is_valid))
                return result

            def validate_step2_type(self, id_value: str, context: str) -> ValidationResult:
                """Step 2: Type detection."""
                result = self.validator.detect_id_type(id_value, context)
                self.validation_history.append(("type", context, result.is_valid))
                return result

            def validate_step3_context(self, task_id: str, git_branch_id: str) -> ValidationResult:
                """Step 3: Context validation."""
                result = self.validator.validate_task_context(task_id, git_branch_id)
                self.validation_history.append(("context", f"{task_id}:{git_branch_id}", result.is_valid))
                return result

            def validate_step4_mapping(self, **params) -> ValidationResult:
                """Step 4: Parameter mapping validation."""
                result = self.validator.validate_parameter_mapping(**params)
                self.validation_history.append(("mapping", str(params), result.is_valid))
                return result

            def run_full_pipeline(self, task_id: str, git_branch_id: str, user_id: str) -> bool:
                """Run the complete validation pipeline."""
                # Step 1: Format validation
                if not self.validate_step1_format(task_id, "task_id").is_valid:
                    return False
                if not self.validate_step1_format(git_branch_id, "git_branch_id").is_valid:
                    return False
                if not self.validate_step1_format(user_id, "user_id").is_valid:
                    return False

                # Step 2: Type detection
                if not self.validate_step2_type(task_id, "task_id").is_valid:
                    return False
                if not self.validate_step2_type(git_branch_id, "git_branch_id").is_valid:
                    return False

                # Step 3: Context validation
                if not self.validate_step3_context(task_id, git_branch_id).is_valid:
                    return False

                # Step 4: Parameter mapping
                if not self.validate_step4_mapping(
                    task_id=task_id,
                    git_branch_id=git_branch_id,
                    user_id=user_id
                ).is_valid:
                    return False

                return True

        pipeline = ValidationPipeline(self.validator)

        # Test successful pipeline
        task_id = str(uuid4())
        git_branch_id = str(uuid4())
        user_id = str(uuid4())

        success = pipeline.run_full_pipeline(task_id, git_branch_id, user_id)
        assert success is True

        # Verify all steps were executed
        assert len(pipeline.validation_history) == 7  # 3 format + 2 type + 1 context + 1 mapping

        # Test failed pipeline (invalid UUID in step 1)
        pipeline_fail = ValidationPipeline(self.validator)
        fail_result = pipeline_fail.run_full_pipeline("invalid", git_branch_id, user_id)
        assert fail_result is False

        # Should stop at first failure
        assert len(pipeline_fail.validation_history) == 1

    def test_conditional_validation_based_on_context(self):
        """Test conditional validation logic based on context."""

        class ConditionalValidator:
            def __init__(self, validator: IDValidator):
                self.validator = validator

            def validate_based_on_operation(self, operation: str, **params) -> ValidationResult:
                """Validate based on operation type."""
                if operation == "create_task":
                    return self._validate_task_creation(**params)
                elif operation == "create_subtask":
                    return self._validate_subtask_creation(**params)
                elif operation == "update_task":
                    return self._validate_task_update(**params)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

            def _validate_task_creation(self, **params) -> ValidationResult:
                """Validation for task creation."""
                required_params = ["git_branch_id", "user_id"]
                for param in required_params:
                    if param not in params:
                        return ValidationResult(
                            is_valid=False,
                            id_type=IDType.UNKNOWN,
                            original_value=str(params),
                            error_message=f"Missing required parameter: {param}"
                        )

                return self.validator.validate_parameter_mapping(**params)

            def _validate_subtask_creation(self, **params) -> ValidationResult:
                """Validation for subtask creation."""
                required_params = ["task_id", "user_id"]
                for param in required_params:
                    if param not in params:
                        return ValidationResult(
                            is_valid=False,
                            id_type=IDType.UNKNOWN,
                            original_value=str(params),
                            error_message=f"Missing required parameter: {param}"
                        )

                # Additional validation for subtask
                task_id = params["task_id"]
                result = self.validator.validate_uuid_format(task_id)
                if not result.is_valid:
                    return result

                return self.validator.validate_parameter_mapping(**params)

            def _validate_task_update(self, **params) -> ValidationResult:
                """Validation for task update."""
                if "task_id" not in params:
                    return ValidationResult(
                        is_valid=False,
                        id_type=IDType.UNKNOWN,
                        original_value=str(params),
                        error_message="task_id required for update"
                    )

                return self.validator.validate_parameter_mapping(**params)

        conditional = ConditionalValidator(self.validator)

        # Test task creation
        task_create_result = conditional.validate_based_on_operation(
            "create_task",
            git_branch_id=str(uuid4()),
            user_id=str(uuid4())
        )
        assert task_create_result.is_valid is True

        # Test subtask creation
        subtask_create_result = conditional.validate_based_on_operation(
            "create_subtask",
            task_id=str(uuid4()),
            user_id=str(uuid4())
        )
        assert subtask_create_result.is_valid is True

        # Test task update
        task_update_result = conditional.validate_based_on_operation(
            "update_task",
            task_id=str(uuid4()),
            user_id=str(uuid4())
        )
        assert task_update_result.is_valid is True

        # Test missing parameters
        with pytest.raises(ValueError):
            conditional.validate_based_on_operation("unknown_operation")

        # Test validation failure
        fail_result = conditional.validate_based_on_operation(
            "create_task",
            git_branch_id="invalid",
            user_id=str(uuid4())
        )
        assert fail_result.is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])