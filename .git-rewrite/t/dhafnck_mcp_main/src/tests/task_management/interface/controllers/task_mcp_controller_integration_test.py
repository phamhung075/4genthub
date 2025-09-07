"""Integration Test Suite for TaskMCPController

This integration test suite focuses on comprehensive testing of TaskMCPController
with real integrations and edge cases that complement the existing unit tests.

Created by: Test Orchestrator Agent  
Date: 2025-08-26
Purpose: Provide comprehensive integration test coverage for task_mcp_controller.py
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestTaskMCPControllerIntegration:
    """Integration tests for TaskMCPController with comprehensive coverage."""

    @pytest.fixture
    def mock_task_facade_factory(self):
        """Create mock task facade factory for testing."""
        factory = Mock(spec=TaskFacadeFactory)
        mock_facade = Mock(spec=TaskApplicationFacade)
        
        # Setup successful responses
        mock_facade.create_task.return_value = {
            "success": True,
            "task": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Test Task",
                "status": "todo"
            }
        }
        mock_facade.get_task.return_value = {
            "success": True, 
            "task": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Test Task"
            }
        }
        mock_facade.update_task.return_value = {"success": True, "updated": True}
        mock_facade.delete_task.return_value = {"success": True, "deleted": True}
        mock_facade.complete_task.return_value = {"success": True, "completed": True}
        mock_facade.list_tasks.return_value = {"success": True, "tasks": []}
        mock_facade.search_tasks.return_value = {"success": True, "tasks": []}
        mock_facade.get_next_task.return_value = {"success": True, "next_task": {"id": "next-123"}}
        
        factory.create_task_facade.return_value = mock_facade
        return factory, mock_facade

    @pytest.fixture
    def controller(self, mock_task_facade_factory):
        """Create TaskMCPController instance for testing."""
        factory, _ = mock_task_facade_factory
        return TaskMCPController(factory)

    def test_controller_initialization_with_services(self, mock_task_facade_factory):
        """Test controller initializes correctly with all services."""
        factory, _ = mock_task_facade_factory
        
        controller = TaskMCPController(
            task_facade_factory=factory,
            progress_service=Mock(),
            hint_service=Mock(),
            workflow_service=Mock(),
            coordination_service=Mock()
        )
        
        # Verify initialization
        assert controller._task_facade_factory == factory
        assert controller._progress_service is not None
        assert controller._hint_service is not None 
        assert controller._workflow_service is not None
        assert controller._coordination_service is not None
        assert controller._enforcement_service is not None
        assert controller._progressive_enforcement is not None
        assert controller._response_enrichment is not None

    def test_uuid_validation_comprehensive(self, controller):
        """Test comprehensive UUID validation scenarios."""
        # Valid UUIDs
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            str(uuid.uuid4())
        ]
        
        for valid_uuid in valid_uuids:
            assert controller._is_valid_uuid(valid_uuid) is True
        
        # Invalid UUIDs 
        invalid_uuids = [
            "invalid-uuid",
            "550e8400-e29b-41d4",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "",
            None,
            "not-a-uuid-at-all"
        ]
        
        for invalid_uuid in invalid_uuids:
            if invalid_uuid is not None:
                assert controller._is_valid_uuid(invalid_uuid) is False

    def test_boolean_coercion_edge_cases(self, controller):
        """Test boolean parameter coercion handles edge cases."""
        # True values
        true_values = [True, "true", "True", "TRUE", "yes", "YES", "1", 1, "on", "enabled"]
        for val in true_values:
            assert controller._coerce_to_bool(val, "test") is True
        
        # False values
        false_values = [False, "false", "False", "FALSE", "no", "NO", "0", 0, "off", "disabled"] 
        for val in false_values:
            assert controller._coerce_to_bool(val, "test") is False

    def test_string_list_parsing_scenarios(self, controller):
        """Test string list parsing handles various input formats."""
        # Test cases: (input, expected_output)
        test_cases = [
            (["a", "b", "c"], ["a", "b", "c"]),  # Already a list
            ("a,b,c", ["a", "b", "c"]),  # Comma-separated
            ('["a", "b", "c"]', ["a", "b", "c"]),  # JSON string
            ("single", ["single"]),  # Single string
            ("", None),  # Empty string
            (None, None),  # None input
            ("a, b, c", ["a", "b", "c"]),  # With spaces
        ]
        
        for input_val, expected in test_cases:
            result = controller._parse_string_list(input_val)
            assert result == expected, f"Failed for input {input_val}"

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_authenticated_user_id')
    def test_authentication_flow_integration(self, mock_get_auth_user_id, controller, mock_task_facade_factory):
        """Test complete authentication flow integration."""
        factory, mock_facade = mock_task_facade_factory
        mock_get_auth_user_id.return_value = "test-user-123"
        
        git_branch_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock database query
        with patch('fastmcp.task_management.infrastructure.database.session_manager.get_session_manager') as mock_session_mgr:
            mock_session = MagicMock()
            mock_session_mgr.return_value.get_session.return_value.__enter__.return_value = mock_session
            
            mock_result = MagicMock()
            mock_result.fetchone.return_value = ("test-project-id", "feature/test")
            mock_session.execute.return_value = mock_result
            
            with patch('fastmcp.task_management.interface.controllers.task_mcp_controller.validate_user_id') as mock_validate:
                mock_validate.return_value = "test-user-123"
                
                facade = controller._get_facade_for_request(git_branch_id)
                
                assert facade == mock_facade
                mock_validate.assert_called_once_with("test-user-123", "Task facade creation")

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_authenticated_user_id')
    def test_authentication_error_scenarios(self, mock_get_auth_user_id, controller):
        """Test various authentication error scenarios."""
        git_branch_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Test authentication required error
        mock_get_auth_user_id.side_effect = UserAuthenticationRequiredError("No auth")
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            controller._get_facade_for_request(git_branch_id)
        assert "Task facade creation" in str(exc_info.value)
        
        # Test default user prohibited error  
        mock_get_auth_user_id.side_effect = None
        mock_get_auth_user_id.return_value = "default_user"
        
        with patch('fastmcp.task_management.interface.controllers.task_mcp_controller.validate_user_id') as mock_validate:
            mock_validate.side_effect = DefaultUserProhibitedError("Default user not allowed")
            with pytest.raises(DefaultUserProhibitedError):
                controller._get_facade_for_request(git_branch_id)

    def test_response_standardization(self, controller):
        """Test response standardization functionality."""
        # Test successful facade response
        facade_response = {
            "success": True,
            "action": "create", 
            "task": {"id": "test-123", "title": "Test"},
            "workflow_guidance": {"hints": ["Test hint"]}
        }
        
        result = controller._standardize_facade_response(facade_response, "create_task")
        
        assert result["success"] is True
        assert result["operation"] == "create_task"
        assert "task" in result["data"]
        assert "workflow_guidance" in result
        
        # Test error facade response
        error_response = {
            "success": False,
            "error": "Task not found",
            "error_code": "NOT_FOUND"
        }
        
        result = controller._standardize_facade_response(error_response, "get_task")
        
        assert result["success"] is False
        assert result["operation"] == "get_task"
        assert result["error"] == "Task not found"
        assert result["error_code"] == "NOT_FOUND"

    def test_task_response_enrichment_integration(self, controller):
        """Test task response enrichment with mocked services."""
        task_data = {
            "id": "enrich-task-123",
            "title": "Test Task",
            "status": "in_progress",
            "progress": 50
        }
        
        response = {
            "success": True,
            "action": "update",
            "data": {"task": task_data}
        }
        
        # Mock enrichment service
        with patch.object(controller._response_enrichment, 'enrich_task_response') as mock_enrich:
            mock_enrichment = Mock()
            mock_enrichment.visual_indicators = ["🎯 50% Complete"]
            mock_enrichment.context_hints = ["Consider adding tests"]
            mock_enrichment.actionable_suggestions = ["Break into subtasks"]
            mock_enrichment.template_examples = []
            mock_enrichment.warnings = []
            mock_enrichment.metadata = {"version": "2.1.0"}
            mock_enrich.return_value = mock_enrichment
            
            enriched = controller._enrich_task_response(response, "update", task_data)
            
            assert "workflow_guidance" in enriched
            guidance = enriched["workflow_guidance"]
            assert "visual_indicators" in guidance
            assert "🎯 50% Complete" in guidance["visual_indicators"]

    def test_error_handling_resilience(self, controller, mock_task_facade_factory):
        """Test error handling and resilience patterns."""
        factory, mock_facade = mock_task_facade_factory
        
        # Test enrichment service failure
        task_data = {"id": "error-test", "title": "Error Test"}
        response = {"success": True, "action": "create", "data": {"task": task_data}}
        
        with patch.object(controller._response_enrichment, 'enrich_task_response') as mock_enrich:
            mock_enrich.side_effect = Exception("Enrichment failed")
            
            # Should not raise exception
            result = controller._enrich_task_response(response, "create", task_data)
            
            # Should return original response
            assert result["success"] is True
            assert result["action"] == "create"

    @patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id')
    def test_manage_task_workflow_integration(self, mock_get_user_id, controller, mock_task_facade_factory):
        """Test complete manage_task workflow integration."""
        factory, mock_facade = mock_task_facade_factory
        mock_get_user_id.return_value = "workflow-user-123"
        
        # Test create action workflow
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
             patch.object(controller, 'handle_crud_operations') as mock_crud:
            
            mock_get_facade.return_value = mock_facade
            mock_crud.return_value = {
                "success": True,
                "action": "create",
                "task": {"id": "workflow-123", "title": "Workflow Test"}
            }
            
            result = controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Workflow Test Task"
            )
            
            assert result["success"] is True
            assert result["action"] == "create"
            mock_crud.assert_called_once()

    def test_parameter_enforcement_integration(self, controller):
        """Test parameter enforcement service integration."""
        # Mock enforcement to return warnings
        with patch.object(controller._enforcement_service, 'check_parameter_conformity') as mock_enforce:
            mock_result = Mock()
            mock_result.conformity_score = 0.7
            mock_result.has_violations = True
            mock_result.violations = ["Missing optional field"]
            mock_result.suggestions = ["Add field for better tracking"]
            mock_enforce.return_value = mock_result
            
            # Test that enforcement is checked
            with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
                 patch.object(controller, 'handle_crud_operations') as mock_crud, \
                 patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id') as mock_user:
                
                mock_facade = Mock()
                mock_get_facade.return_value = mock_facade
                mock_crud.return_value = {"success": True, "action": "create"}
                mock_user.return_value = "enforce-user-123"
                
                result = controller.manage_task(
                    action="create",
                    git_branch_id="550e8400-e29b-41d4-a716-446655440000"
                )
                
                # Should succeed with warnings
                assert result["success"] is True

    def test_context_propagation_mixin_functionality(self, controller):
        """Test ContextPropagationMixin functionality."""
        # Test async context propagation
        import asyncio
        
        async def test_async_func(value):
            await asyncio.sleep(0.01)  # Minimal async work
            return f"async_result_{value}"
        
        result = controller._run_async_with_context(test_async_func, "test")
        assert result == "async_result_test"

    def test_mcp_tool_registration_integration(self, controller):
        """Test MCP tool registration integration."""
        mock_mcp = Mock()
        mock_mcp.tool = Mock()
        
        # Mock description loader
        with patch.object(controller, '_get_task_management_descriptions') as mock_desc:
            mock_desc.return_value = {
                "manage_task": {
                    "description": "Test task management",
                    "parameters": {"action": {"description": "Action param"}}
                }
            }
            
            controller.register_tools(mock_mcp)
            
            # Verify tool registration
            mock_mcp.tool.assert_called_once()
            call_kwargs = mock_mcp.tool.call_args[1]
            assert call_kwargs["name"] == "manage_task"
            assert "Test task management" in call_kwargs["description"]

    def test_workflow_hints_integration(self, controller):
        """Test workflow hints functionality."""
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
             patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id') as mock_user:
            
            mock_facade = Mock()
            mock_facade.get_workflow_hints.return_value = {
                "success": True,
                "workflow_hints": [
                    {"type": "next_action", "content": "Add unit tests"},
                    {"type": "optimization", "content": "Consider refactoring"}
                ]
            }
            
            mock_get_facade.return_value = mock_facade
            mock_user.return_value = "hints-user-123"
            
            result = controller.get_workflow_hints("test-task-123")
            
            assert result["success"] is True
            assert "workflow_hints" in result
            assert len(result["workflow_hints"]) == 2

    def test_progress_reporting_integration(self, controller):
        """Test progress reporting functionality."""
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
             patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id') as mock_user:
            
            mock_facade = Mock()
            mock_facade.report_progress.return_value = {
                "success": True,
                "progress_recorded": True,
                "progress_percentage": 75
            }
            
            mock_get_facade.return_value = mock_facade
            mock_user.return_value = "progress-user-123"
            
            result = controller.report_progress(
                task_id="progress-test-123",
                progress_percentage=75,
                notes="Making good progress"
            )
            
            assert result["success"] is True
            assert result["progress_recorded"] is True
            assert result["progress_percentage"] == 75

    def test_vision_alignment_integration(self, controller):
        """Test vision alignment functionality.""" 
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
             patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id') as mock_user:
            
            mock_facade = Mock()
            mock_facade.get_vision_alignment.return_value = {
                "success": True,
                "alignment_score": 0.85,
                "alignment_factors": {
                    "priority_alignment": 0.9,
                    "timeline_feasibility": 0.8
                }
            }
            
            mock_get_facade.return_value = mock_facade
            mock_user.return_value = "vision-user-123"
            
            result = controller.get_vision_alignment("vision-test-123")
            
            assert result["success"] is True
            assert result["alignment_score"] == 0.85
            assert "alignment_factors" in result

    def test_complete_task_with_context_integration(self, controller):
        """Test complete task with context functionality."""
        with patch.object(controller, '_get_facade_for_request') as mock_get_facade, \
             patch.object(controller._context_facade_factory, 'create') as mock_create_context, \
             patch('fastmcp.task_management.interface.controllers.task_mcp_controller.get_current_user_id') as mock_user:
            
            mock_facade = Mock()
            mock_context_facade = Mock()
            
            mock_facade.complete_task.return_value = {
                "success": True,
                "task": {"id": "context-complete-123", "status": "done"}
            }
            mock_context_facade.update_context.return_value = {"success": True}
            
            mock_get_facade.return_value = mock_facade
            mock_create_context.return_value = mock_context_facade
            mock_user.return_value = "context-user-123"
            
            result = controller.complete_task_with_context(
                task_id="context-complete-123",
                completion_summary="Task completed successfully",
                context_data={"completion_notes": "All tests passed"}
            )
            
            assert result["success"] is True
            assert result["task"]["status"] == "done"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])