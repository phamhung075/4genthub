"""
Test cases for Unified Context MCP Controller.

This module tests the UnifiedContextMCPController which handles MCP tool
registration for unified context management operations across the 4-tier hierarchy.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.unified_context_controller import UnifiedContextMCPController
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestUnifiedContextMCPController:
    """Test cases for UnifiedContextMCPController class."""
    
    @pytest.fixture
    def mock_facade_service(self):
        """Create mock facade service."""
        service = Mock(spec=FacadeService)
        return service
    
    @pytest.fixture
    def mock_facade(self):
        """Create mock unified context facade."""
        facade = Mock(spec=UnifiedContextFacade)
        return facade
    
    @pytest.fixture
    def controller(self, mock_facade_service, mock_facade):
        """Create controller instance with mocked dependencies."""
        mock_facade_service.get_context_facade.return_value = mock_facade
        return UnifiedContextMCPController(mock_facade_service)
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock FastMCP server."""
        server = MagicMock()
        
        # Store registered tools - no name parameter is passed to @mcp.tool decorator
        registered_tools = {}
        
        def tool_decorator(description=None):
            def decorator(func):
                # The function name becomes the tool name
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        server.tool = tool_decorator
        server.registered_tools = registered_tools
        return server
    
    def test_controller_initialization(self, mock_facade_service):
        """Test controller initialization."""
        controller = UnifiedContextMCPController(mock_facade_service)
        assert controller._facade_service == mock_facade_service
    
    def test_register_tools(self, controller, mock_mcp_server):
        """Test tool registration with MCP server."""
        controller.register_tools(mock_mcp_server)
        
        # Check that manage_context tool was registered
        assert "manage_context" in mock_mcp_server.registered_tools
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_create_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade_service, mock_facade):
        """Test manage_context tool with create action."""
        mock_get_user_id.return_value = "authenticated-user"
        mock_facade.create_context.return_value = {
            "success": True,
            "context": {"id": "task-123", "level": "task", "data": {"title": "Test Task"}}
        }
        
        # Register tools and get the manage_context function
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        # Test create action
        result = manage_context(
            action="create",
            level="task",
            context_id="task-123",
            data={"title": "Test Task", "description": "Test Description"}
        )
        
        # Verify authenticated user was retrieved
        mock_get_user_id.assert_called_once_with(None, "manage_context.create")
        
        # Verify facade was created with authenticated user
        mock_facade_service.get_context_facade.assert_called_once_with(
            user_id="authenticated-user",
            project_id=None,
            git_branch_id=None
        )
        
        # Verify facade method was called
        mock_facade.create_context.assert_called_once_with(
            level="task",
            context_id="task-123",
            data={"title": "Test Task", "description": "Test Description"},
            user_id="authenticated-user"
        )
        
        # Verify response structure (now uses StandardResponseFormatter)
        assert result["success"] is True
        assert result["status"] == "success"
        assert "data" in result
        # The data field contains the context directly
        assert result["data"]["id"] == "task-123"
        assert result["data"]["level"] == "task"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_get_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with get action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.get_context.return_value = {
            "success": True,
            "context": {"id": "project-456", "level": "project", "data": {"name": "Test Project"}}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="get",
            level="project",
            context_id="project-456",
            include_inherited=True,
            force_refresh=False
        )
        
        mock_facade.get_context.assert_called_once_with(
            level="project",
            context_id="project-456",
            include_inherited=True,
            force_refresh=False,
            user_id="test-user"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_update_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with update action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.update_context.return_value = {
            "success": True,
            "context": {"id": "branch-789", "level": "branch", "data": {"status": "active"}}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="update",
            level="branch",
            context_id="branch-789",
            data={"status": "active", "progress": 75},
            propagate_changes=True
        )
        
        mock_facade.update_context.assert_called_once_with(
            level="branch",
            context_id="branch-789",
            data={"status": "active", "progress": 75},
            propagate_changes=True
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_delete_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with delete action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.delete_context.return_value = {"success": True}
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="delete",
            level="task",
            context_id="task-999"
        )
        
        mock_facade.delete_context.assert_called_once_with(
            level="task",
            context_id="task-999"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_resolve_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with resolve action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.resolve_context.return_value = {
            "success": True,
            "resolved_context": {"id": "task-111", "inherited_data": {}}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="resolve",
            level="task",
            context_id="task-111",
            force_refresh=True
        )
        
        mock_facade.resolve_context.assert_called_once_with(
            level="task",
            context_id="task-111",
            force_refresh=True
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_delegate_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with delegate action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.delegate_context.return_value = {
            "success": True,
            "delegation": {"id": "del-123", "status": "pending"}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="delegate",
            level="task",
            context_id="task-222",
            delegate_to="project",
            delegate_data={"pattern": "auth_flow", "reusable": True},
            delegation_reason="Reusable authentication pattern"
        )
        
        mock_facade.delegate_context.assert_called_once_with(
            level="task",
            context_id="task-222",
            delegate_to="project",
            data={"pattern": "auth_flow", "reusable": True},
            delegation_reason="Reusable authentication pattern"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_add_insight_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with add_insight action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.add_insight.return_value = {
            "success": True,
            "insight": {"id": "ins-123", "content": "Performance improved"}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="add_insight",
            level="branch",
            context_id="branch-333",
            content="Performance improved by 50%",
            category="performance",
            importance="high",
            agent="@optimization_agent"
        )
        
        mock_facade.add_insight.assert_called_once_with(
            level="branch",
            context_id="branch-333",
            content="Performance improved by 50%",
            category="performance",
            importance="high",
            agent="@optimization_agent"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_add_progress_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with add_progress action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.add_progress.return_value = {
            "success": True,
            "progress": {"id": "prog-123", "content": "Completed phase 1"}
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="add_progress",
            level="task",
            context_id="task-444",
            content="Completed phase 1 of implementation",
            agent="@development_agent"
        )
        
        mock_facade.add_progress.assert_called_once_with(
            level="task",
            context_id="task-444",
            content="Completed phase 1 of implementation",
            agent="@development_agent"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_list_action(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context tool with list action."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.list_contexts.return_value = {
            "success": True,
            "contexts": [
                {"id": "ctx-1", "level": "project"},
                {"id": "ctx-2", "level": "project"}
            ]
        }
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="list",
            level="project",
            filters={"status": "active"}
        )
        
        mock_facade.list_contexts.assert_called_once_with(
            level="project",
            filters={"status": "active"}
        )
        
        assert result["success"] is True
        assert result["status"] == "success"
        assert "data" in result
        assert "contexts" in result["data"]
        assert len(result["data"]["contexts"]) == 2
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_invalid_action(self, mock_get_user_id, controller, mock_mcp_server):
        """Test manage_context tool with invalid action."""
        mock_get_user_id.return_value = "test-user"
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="invalid_action",
            level="task",
            context_id="task-555"
        )
        
        assert result["success"] is False
        assert result["status"] == "failure"
        assert "error" in result
        assert "Unknown action: invalid_action" in result["error"]["message"]
        assert "Valid actions:" in result["error"]["message"]
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_json_string_data(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test manage_context with JSON string data parameter."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.create_context.return_value = {"success": True}
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        # Test with JSON string
        json_data = '{"title": "Test Task", "priority": "high"}'
        result = manage_context(
            action="create",
            level="task",
            context_id="task-666",
            data=json_data
        )
        
        # Verify data was parsed correctly
        mock_facade.create_context.assert_called_once_with(
            level="task",
            context_id="task-666",
            data={"title": "Test Task", "priority": "high"},
            user_id="test-user"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_invalid_json_data(self, mock_get_user_id, controller, mock_mcp_server):
        """Test manage_context with invalid JSON string data."""
        mock_get_user_id.return_value = "test-user"
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        # Test with invalid JSON
        result = manage_context(
            action="create",
            level="task",
            context_id="task-777",
            data='{"invalid json}'
        )
        
        assert result["success"] is False
        assert result["status"] == "failure"
        assert "error" in result
        assert "Invalid JSON string" in result["error"]["message"]
        assert "metadata" in result
        assert "suggestions" in result["metadata"]
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_boolean_parameter_coercion(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test boolean parameter coercion from string values."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.get_context.return_value = {"success": True}
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        # Test with string boolean values
        result = manage_context(
            action="get",
            level="task",
            context_id="task-888",
            include_inherited="true",
            force_refresh="false"
        )
        
        # Verify boolean values were converted
        mock_facade.get_context.assert_called_once_with(
            level="task",
            context_id="task-888",
            include_inherited=True,
            force_refresh=False,
            user_id="test-user"
        )
        
        assert result["success"] is True
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_authentication_error(self, mock_get_user_id, controller, mock_mcp_server):
        """Test authentication error handling."""
        mock_get_user_id.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="create",
            level="task",
            context_id="task-999"
        )
        
        assert result["success"] is False
        assert "error" in result
        # The UserFriendlyErrorHandler wraps UserAuthenticationRequiredError
        # Check for error message content from the handler
        error_content = str(result.get("error", ""))
        assert ("could not be completed" in error_content or 
                "Authentication required" in error_content or
                "USER_AUTHENTICATION_REQUIRED" in str(result.get("error_code", "")))
    
    @patch('fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller.get_authenticated_user_id')
    def test_manage_context_facade_error(self, mock_get_user_id, controller, mock_mcp_server, mock_facade):
        """Test facade error handling."""
        mock_get_user_id.return_value = "test-user"
        mock_facade.create_context.side_effect = ValueError("Invalid context data")
        
        controller.register_tools(mock_mcp_server)
        manage_context = mock_mcp_server.registered_tools["manage_context"]
        
        result = manage_context(
            action="create",
            level="task",
            context_id="task-1000",
            data={"invalid": "data"}
        )
        
        assert result["success"] is False
        assert result["status"] == "failure"
        assert "error" in result
        assert "Invalid context data" in result["error"]["message"]
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    # def test_get_context_management_descriptions(self, controller):
    #     """Test loading context management descriptions."""
    #     # NOTE: This method no longer exists in the controller
    #     descriptions = controller._get_context_management_descriptions()
    #     
    #     assert "description" in descriptions
    #     assert "parameters" in descriptions
    #     assert "Unified context management" in descriptions["description"]
    #     assert "action" in descriptions["parameters"]
    
    # def test_get_param_description_flat_format(self, controller):
    #     """Test getting parameter description from flat format."""
    #     # NOTE: This method no longer exists in the controller
    #     desc = {
    #         "parameters": {
    #             "action": "Action to perform"
    #         }
    #     }
    #     
    #     result = controller._get_param_description(desc, "action", "default")
    #     assert result == "Action to perform"
    
    # def test_get_param_description_nested_format(self, controller):
    #     """Test getting parameter description from nested format."""
    #     # NOTE: This method no longer exists in the controller
    #     desc = {
    #         "parameters": {
    #             "action": {
    #                 "description": "Action to perform",
    #                 "type": "string"
    #             }
    #         }
    #     }
    #     
    #     result = controller._get_param_description(desc, "action", "default")
    #     assert result == "Action to perform"
    
    # def test_get_param_description_missing(self, controller):
    #     """Test getting parameter description when missing."""
    #     # NOTE: This method no longer exists in the controller
    #     desc = {"parameters": {}}
    #     
    #     result = controller._get_param_description(desc, "missing_param", "default value")
    #     assert result == "default value"
    
    # NOTE: Tests for private methods _normalize_context_data, _standardize_facade_response, 
    # and _get_context_management_descriptions have been removed as these methods 
    # no longer exist in the current implementation of UnifiedContextMCPController.
    # The controller now uses ContextOperationFactory for operation handling.


class TestParameterParsing:
    """Test cases for parameter parsing and validation."""
    
    @pytest.fixture
    def controller(self):
        """Create controller for parameter testing."""
        service = Mock(spec=FacadeService)
        return UnifiedContextMCPController(service)
    
    # NOTE: Tests for JSONParameterParser and coerce_parameter_types have been removed
    # as these are no longer used in the current implementation.
    # The controller now uses ContextOperationFactory for all operations.


if __name__ == "__main__":
    pytest.main([__file__])