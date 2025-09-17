"""Integration tests for agent assignment and inheritance flow"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.handlers.crud_handler import CRUDHandler
from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.handlers.crud_handler import SubtaskCRUDHandler
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId


class TestAgentAssignmentAtCreation:
    """Test agent assignment during task and subtask creation"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_task_repo = Mock()
        self.mock_subtask_repo = Mock()
        self.mock_context_service = Mock()
        
        # Create facade with mocked dependencies
        self.task_facade = TaskApplicationFacade(
            task_repository=self.mock_task_repo,
            subtask_repository=self.mock_subtask_repo,
            context_service=self.mock_context_service
        )
        
        self.subtask_facade = SubtaskApplicationFacade(
            task_repository=self.mock_task_repo,
            subtask_repository=self.mock_subtask_repo
        )
        
        # Create handlers
        self.response_formatter = StandardResponseFormatter()
        self.task_handler = CRUDHandler(self.response_formatter)
        self.subtask_handler = SubtaskCRUDHandler(self.response_formatter)

    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    @patch('fastmcp.task_management.application.facades.task_application_facade.TaskApplicationFacade._await_if_coroutine')
    def test_create_task_with_multiple_assignees_success(self, mock_await, mock_validate_user):
        """Test successful task creation with multiple valid assignees"""
        # Setup mocks
        mock_validate_user.return_value = "test-user"
        # Mock _await_if_coroutine to handle the async context derivation
        def await_side_effect(coro):
            # Check if this is the context derivation call
            if hasattr(coro, '__name__') and '_derive_context' in str(coro):
                return {"project_id": "test-project", "git_branch_name": "main"}
            # For other coroutines, return a default dict
            return {"project_id": "test-project", "git_branch_name": "main"}
        mock_await.side_effect = await_side_effect
        
        # Mock successful task creation
        created_task = Task(
            id=TaskId("550e8400-e29b-41d4-a716-446655440000"),
            title="Test Task",
            description="Test Description",
            assignees=["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
        )
        
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = created_task

        with patch.object(self.task_facade._create_task_use_case, 'execute', return_value=mock_task_response):
            result = self.task_handler.create_task(
                facade=self.task_facade,
                git_branch_id="test-branch",
                title="Test Task",
                description="Test Description",
                assignees=["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
            )
        
        assert result["success"] is True
        assert result["action"] == "create"
        assert "task" in result

    def test_create_task_with_invalid_assignees(self):
        """Test task creation with invalid assignees returns error"""
        result = self.task_handler.create_task(
            facade=self.task_facade,
            git_branch_id="test-branch",
            title="Test Task",
            description="Test Description",
            assignees=["invalid-agent", "another-invalid"]
        )

        assert result["success"] is False
        # The error message will contain information about invalid assignees
        # Check for the actual error format returned by _create_standardized_error
        # With response optimization, error is structured as {"message": "...", "code": "..."}
        error_message = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else result.get("error", "")
        assert "assignees" in error_message or (result.get("metadata") and result["metadata"].get("hint") and "Invalid assignees" in result["metadata"]["hint"])

    def test_create_task_empty_assignees(self):
        """Test task creation with empty assignees list - should fail as at least one assignee is required"""
        result = self.task_handler.create_task(
            facade=self.task_facade,
            git_branch_id="test-branch",
            title="Test Task",
            assignees=[]  # Empty list
        )

        # Empty assignees list should fail validation
        assert result["success"] is False
        # With response optimization, error is structured as {"message": "...", "code": "..."}
        error_message = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else result.get("error", "")
        assert "assignees" in error_message or (result.get("metadata") and result["metadata"].get("field") == "assignees")


class TestAgentInheritanceFlow:
    """Test agent inheritance from parent tasks to subtasks"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_task_repo = Mock()
        self.mock_subtask_repo = Mock()
        
        # Create parent task with assignees
        self.parent_task = Task(
            id=TaskId("parent-task-123"),
            title="Parent Task",
            description="Parent Description",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        # Setup repository mocks
        self.mock_task_repo.find_by_id.return_value = self.parent_task
        
        self.subtask_facade = SubtaskApplicationFacade(
            task_repository=self.mock_task_repo,
            subtask_repository=self.mock_subtask_repo
        )
        
        self.response_formatter = StandardResponseFormatter()
        self.subtask_handler = SubtaskCRUDHandler(self.response_formatter)

    def test_create_subtask_inherits_parent_assignees(self):
        """Test subtask creation inherits assignees from parent when none provided"""
        # Mock the handle_manage_subtask method to simulate inheritance
        with patch.object(self.subtask_facade, 'handle_manage_subtask') as mock_handle:
            mock_response = {
                "success": True,
                "action": "create",
                "message": "Subtask created",
                "subtask": {
                    "id": "subtask-456",
                    "title": "Test Subtask",
                    "assignees": ["coding-agent", "@test-orchestrator-agent"]
                },
                "task_id": "parent-task-123",
                "progress": {},
                "agent_inheritance_applied": True,
                "inherited_assignees": ["coding-agent", "@test-orchestrator-agent"]
            }
            mock_handle.return_value = mock_response
            
            result = self.subtask_handler.create_subtask(
                facade=self.subtask_facade,
                task_id="parent-task-123",
                title="Test Subtask",
                assignees=None  # No assignees provided
            )
        
        assert result["success"] is True
        assert result.get("agent_inheritance_applied") is True
        assert result.get("inherited_assignees") == ["coding-agent", "@test-orchestrator-agent"]
        assert "inheritance_info" in result
        assert result["inheritance_info"]["applied"] is True

    def test_create_subtask_with_explicit_assignees_no_inheritance(self):
        """Test subtask creation with explicit assignees does not inherit"""
        with patch.object(self.subtask_facade, 'handle_manage_subtask') as mock_handle:
            mock_response = {
                "success": True,
                "action": "create",
                "message": "Subtask created",
                "subtask": {
                    "id": "subtask-456",
                    "title": "Test Subtask",
                    "assignees": ["security-auditor-agent"]
                },
                "task_id": "parent-task-123",
                "progress": {},
                "agent_inheritance_applied": False
            }
            mock_handle.return_value = mock_response

            result = self.subtask_handler.create_subtask(
                facade=self.subtask_facade,
                task_id="parent-task-123",
                title="Test Subtask",
                assignees=["security-auditor-agent"]  # Explicit assignees - no @ prefix needed
            )

        assert result["success"] is True
        # When explicit assignees are provided, inheritance is not applied
        if "agent_inheritance_applied" in result:
            assert result.get("agent_inheritance_applied") is False
        # inheritance_info may or may not be present based on implementation

    def test_create_subtask_invalid_assignees(self):
        """Test subtask creation with invalid assignees returns error"""
        result = self.subtask_handler.create_subtask(
            facade=self.subtask_facade,
            task_id="parent-task-123",
            title="Test Subtask",
            assignees=["invalid-agent"]
        )

        assert result["success"] is False
        # Check for assignees validation error in multiple possible locations
        # With response optimization, error is structured as {"message": "...", "code": "..."}
        error_message = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else result.get("error", "")
        assert "assignees" in error_message.lower() or \
               (result.get("metadata") and "assignees" in str(result.get("metadata", {})))


class TestEndToEndAgentFlow:
    """End-to-end tests for complete agent assignment and inheritance flow"""

    def setup_method(self):
        """Setup complete test environment"""
        self.mock_task_repo = Mock()
        self.mock_subtask_repo = Mock()
        self.mock_context_service = Mock()
        
        self.task_facade = TaskApplicationFacade(
            task_repository=self.mock_task_repo,
            subtask_repository=self.mock_subtask_repo,
            context_service=self.mock_context_service
        )
        
        self.subtask_facade = SubtaskApplicationFacade(
            task_repository=self.mock_task_repo,
            subtask_repository=self.mock_subtask_repo
        )
        
        self.response_formatter = StandardResponseFormatter()
        self.task_handler = CRUDHandler(self.response_formatter)
        self.subtask_handler = SubtaskCRUDHandler(self.response_formatter)

    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_complete_task_to_subtask_flow(self, mock_validate_user):
        """Test complete flow: create task with agents, then create subtask that inherits"""
        mock_validate_user.return_value = "test-user"
        
        # Step 1: Create parent task with multiple assignees
        created_task = Task(
            id=TaskId("parent-task-123"),
            title="Parent Task",
            description="Parent Description",
            assignees=["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
        )
        
        # Mock task creation
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = created_task
        
        with patch.object(self.task_facade._create_task_use_case, 'execute', return_value=mock_task_response):
            with patch.object(self.task_facade, '_await_if_coroutine') as mock_await:
                mock_await.side_effect = [
                    {"project_id": "test-project", "git_branch_name": "main"},  # Context derivation
                    None  # Context sync
                ]
                
                task_result = self.task_handler.create_task(
                    facade=self.task_facade,
                    git_branch_id="test-branch",
                    title="Parent Task",
                    description="Parent Description",
                    assignees=["coding-agent", "test-orchestrator-agent", "documentation-agent"]
                )
        
        assert task_result["success"] is True
        
        # Step 2: Create subtask without assignees (should inherit)
        self.mock_task_repo.find_by_id.return_value = created_task
        
        with patch.object(self.subtask_facade, 'handle_manage_subtask') as mock_handle:
            mock_subtask_response = {
                "success": True,
                "action": "create",
                "message": "Subtask created with 3 inherited assignees",
                "subtask": {
                    "id": "subtask-456",
                    "title": "Child Subtask",
                    "assignees": ["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
                },
                "task_id": "parent-task-123",
                "progress": {},
                "agent_inheritance_applied": True,
                "inherited_assignees": ["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
            }
            mock_handle.return_value = mock_subtask_response
            
            subtask_result = self.subtask_handler.create_subtask(
                facade=self.subtask_facade,
                task_id="parent-task-123",
                title="Child Subtask",
                assignees=None  # Should inherit from parent
            )
        
        assert subtask_result["success"] is True
        assert subtask_result["agent_inheritance_applied"] is True
        assert len(subtask_result["inherited_assignees"]) == 3
        assert subtask_result["inheritance_info"]["applied"] is True

    def test_multiple_subtasks_inheritance_scenarios(self):
        """Test multiple subtasks with different inheritance scenarios"""
        # Parent task with assignees
        parent_task = Task(
            id=TaskId("parent-task-123"),
            title="Parent Task",
            description="Parent Description",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        self.mock_task_repo.find_by_id.return_value = parent_task
        
        # Scenario 1: Subtask with no assignees (should inherit)
        with patch.object(self.subtask_facade, 'handle_manage_subtask') as mock_handle:
            mock_handle.return_value = {
                "success": True,
                "agent_inheritance_applied": True,
                "inherited_assignees": ["coding-agent", "@test-orchestrator-agent"]
            }
            
            result1 = self.subtask_handler.create_subtask(
                facade=self.subtask_facade,
                task_id="parent-task-123",
                title="Subtask 1",
                assignees=None
            )
            
            assert result1.get("agent_inheritance_applied") is True

        # Scenario 2: Subtask with explicit assignees (should not inherit)
        with patch.object(self.subtask_facade, 'handle_manage_subtask') as mock_handle:
            mock_handle.return_value = {
                "success": True,
                "agent_inheritance_applied": False
            }

            result2 = self.subtask_handler.create_subtask(
                facade=self.subtask_facade,
                task_id="parent-task-123",
                title="Subtask 2",
                assignees=["security-auditor-agent"]  # No @ prefix needed
            )

            # When explicit assignees are provided, inheritance should not be applied
            if "agent_inheritance_applied" in result2:
                assert result2.get("agent_inheritance_applied") is False


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error scenarios"""

    def setup_method(self):
        """Setup test environment"""
        self.response_formatter = StandardResponseFormatter()
        self.task_handler = CRUDHandler(self.response_formatter)
        self.subtask_handler = SubtaskCRUDHandler(self.response_formatter)

    def test_create_task_with_mixed_valid_invalid_assignees(self):
        """Test task creation with mix of valid and invalid assignees"""
        mock_facade = Mock()

        result = self.task_handler.create_task(
            facade=mock_facade,
            git_branch_id="test-branch",
            title="Test Task",
            assignees=["coding-agent", "invalid-agent", "test-orchestrator-agent"]
        )

        assert result["success"] is False
        # Check that the error mentions assignees validation
        # With response optimization, error is structured as {"message": "...", "code": "..."}
        error_message = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else result.get("error", "")
        assert "assignees" in error_message or \
               (result.get("metadata") and result["metadata"].get("hint") and "invalid-agent" in result["metadata"]["hint"])

    def test_create_subtask_parent_task_not_found(self):
        """Test subtask creation when parent task is not found"""
        mock_facade = Mock()
        mock_facade.handle_manage_subtask.side_effect = ValueError("Task parent-task-123 not found")

        result = self.subtask_handler.create_subtask(
            facade=mock_facade,
            task_id="nonexistent-task",
            title="Test Subtask"
        )

        assert result["success"] is False
        # Error message will be about the task not being found or a generic failure
        # With response optimization, error is structured as {"message": "...", "code": "..."}
        error_message = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else result.get("error", "")
        assert "failed" in error_message.lower() or "not found" in error_message.lower()

    def test_create_subtask_inheritance_service_failure(self):
        """Test subtask creation when inheritance service fails"""
        mock_facade = Mock()
        mock_facade.handle_manage_subtask.return_value = {
            "success": True,
            "agent_inheritance_applied": False,
            "warning": "Inheritance service failed"
        }
        
        result = self.subtask_handler.create_subtask(
            facade=mock_facade,
            task_id="parent-task-123",
            title="Test Subtask"
        )
        
        assert result["success"] is True
        assert result.get("agent_inheritance_applied") is False

    def test_validate_large_assignee_list(self):
        """Test validation with large number of assignees"""
        # Create list of 10 valid assignees - note: ui-designer-agent may not be valid
        large_assignee_list = [
            "coding-agent", "test-orchestrator-agent", "documentation-agent",
            "security-auditor-agent", "devops-agent", "ui-specialist-agent",  # Fixed agent name
            "system-architect-agent", "performance-load-tester-agent",
            "code-reviewer-agent", "debugger-agent"
        ]

        mock_facade = Mock()
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Task(
            id=TaskId("test-task"),
            title="Test Task",
            description="Test",
            assignees=large_assignee_list  # No @ prefix needed in list
        )

        # Mock the _create_task_use_case attribute
        mock_facade._create_task_use_case = Mock()
        mock_facade._create_task_use_case.execute = Mock(return_value=mock_task_response)
        mock_facade._await_if_coroutine = Mock(return_value={"project_id": "test", "git_branch_name": "main"})
        mock_facade.create_task = Mock(return_value={"success": True, "task": mock_task_response.task})

        with patch('fastmcp.task_management.domain.constants.validate_user_id', return_value="test-user"):
            result = self.task_handler.create_task(
                facade=mock_facade,
                git_branch_id="test-branch",
                title="Test Task",
                assignees=large_assignee_list
            )

        assert result["success"] is True
        # The test validates that a large list of assignees is accepted
        assert "task" in result or result.get("action") == "create"


if __name__ == "__main__":
    pytest.main([__file__])