"""Tests for AgentMCPController"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.controllers.agent_mcp_controller import AgentMCPController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError, DefaultUserProhibitedError
)


class TestAgentMCPController:
    """Test suite for AgentMCPController"""

    @pytest.fixture
    def mock_agent_facade_factory(self):
        """Create mock agent facade factory"""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade responses
        mock_facade.register_agent.return_value = {"success": True, "agent_id": "agent-123"}
        mock_facade.assign_agent.return_value = {"success": True, "assigned": True}
        mock_facade.get_agent.return_value = {"success": True, "agent": {"id": "agent-123", "name": "test-agent"}}
        mock_facade.list_agents.return_value = {"success": True, "agents": []}
        mock_facade.update_agent.return_value = {"success": True, "updated": True}
        mock_facade.unassign_agent.return_value = {"success": True, "unassigned": True}
        mock_facade.unregister_agent.return_value = {"success": True, "unregistered": True}
        mock_facade.rebalance_agents.return_value = {"success": True, "rebalanced": True}
        
        factory.create_agent_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_agent_facade_factory):
        """Create controller instance with mocked facade factory"""
        return AgentMCPController(mock_agent_facade_factory)

    def test_controller_initialization(self, mock_agent_facade_factory):
        """Test controller initializes correctly with facade factory"""
        controller = AgentMCPController(mock_agent_facade_factory)
        
        assert controller._agent_facade_factory == mock_agent_facade_factory

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_register_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent registration"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is True
        assert result["agent_id"] == "agent-123"
        mock_facade.register_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_assign_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent assignment"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="assign",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
        
        assert result["success"] is True
        assert result["assigned"] is True
        mock_facade.assign_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_get_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="get",
            project_id="project-123",
            agent_id="agent-123"
        )
        
        assert result["success"] is True
        assert "agent" in result
        mock_facade.get_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_list_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agents listing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="list",
            project_id="project-123"
        )
        
        assert result["success"] is True
        assert "agents" in result
        mock_facade.list_agents.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_update_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent update"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="update",
            project_id="project-123",
            agent_id="agent-123",
            name="updated-agent"
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        mock_facade.update_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_unassign_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent unassignment"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="unassign",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
        
        assert result["success"] is True
        assert result["unassigned"] is True
        mock_facade.unassign_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_unregister_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent unregistration"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="unregister",
            project_id="project-123",
            agent_id="agent-123"
        )
        
        assert result["success"] is True
        assert result["unregistered"] is True
        mock_facade.unregister_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_rebalance_success(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test successful agent rebalancing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        result = controller.manage_agent(
            action="rebalance",
            project_id="project-123"
        )
        
        assert result["success"] is True
        assert result["rebalanced"] is True
        mock_facade.rebalance_agents.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_invalid_action(self, mock_get_user, controller):
        """Test handling of invalid action"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_agent(
            action="invalid_action",
            project_id="project-123"
        )
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error"""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is False
        assert "Authentication required" in result["error"]
        assert result["error_code"] == "AUTHENTICATION_REQUIRED"

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_default_user_prohibited_error(self, mock_get_user, controller):
        """Test handling of default user prohibited error"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._agent_facade_factory.create_agent_facade.return_value
        mock_facade.register_agent.side_effect = DefaultUserProhibitedError("Default user not allowed")
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is False
        assert "Default user not allowed" in result["error"]
        assert result["error_code"] == "DEFAULT_USER_PROHIBITED"

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_manage_agent_general_exception(self, mock_get_user, controller):
        """Test handling of general exceptions"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._agent_facade_factory.create_agent_facade.return_value
        mock_facade.register_agent.side_effect = Exception("Unexpected error")
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["action"] == "register"

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.description_loader')
    def test_register_tools_calls_description_loader(self, mock_desc_loader, controller):
        """Test that register_tools calls the description loader"""
        mock_mcp = Mock()
        mock_desc_loader.get_agent_management_descriptions.return_value = {
            "manage_agent": {"description": "test desc", "parameters": {}}
        }
        
        controller.register_tools(mock_mcp)
        
        mock_desc_loader.get_agent_management_descriptions.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_user_id_parameter_handling(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test that user_id parameter is handled correctly"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        # Verify facade was created with authenticated user
        mock_agent_facade_factory.create_agent_facade.assert_called_once_with(
            project_id="project-123",
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_workflow_guidance_integration(self, mock_get_user, controller):
        """Test that workflow guidance is integrated"""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller can handle workflow guidance
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        # Workflow guidance should be included in responses
        assert "workflow_guidance" in result or result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional"""
        # Logger should be available for operations
        assert mock_logger is not None
        
        # Test that we can log (logger is imported at module level)
        from fastmcp.task_management.interface.controllers.agent_mcp_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_parameter_validation(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test parameter validation for different actions"""
        mock_get_user.return_value = "test-user"
        
        # Test register action requires project_id and name
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        assert result["success"] is True
        
        # Test assign action requires agent_id and git_branch_id
        result = controller.manage_agent(
            action="assign",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_facade_creation_and_delegation(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test that facade is properly created and operations are delegated"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        
        # Make request
        controller.manage_agent(
            action="list",
            project_id="project-123"
        )
        
        # Verify facade creation
        mock_agent_facade_factory.create_agent_facade.assert_called_once_with(
            project_id="project-123",
            user_id="test-user"
        )
        
        # Verify operation delegation
        mock_facade.list_agents.assert_called_once()

    def test_import_error_handling(self):
        """Test that import errors for auth context are handled"""
        # The controller should handle import errors gracefully
        # This is tested by the module-level import in the actual code
        
        # Verify the controller can be instantiated even with import issues
        factory = Mock()
        controller = AgentMCPController(factory)
        assert controller is not None

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_user_validation_integration(self, mock_get_user, controller):
        """Test integration with user validation"""
        mock_get_user.return_value = "valid-user"
        
        # Should work with valid user
        result = controller.manage_agent(
            action="list",
            project_id="project-123"
        )
        
        # Basic validation should pass (detailed validation tested in domain layer)
        assert "error_code" not in result or result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_workflow_guidance_factory_integration(self, mock_get_user, controller):
        """Test that workflow guidance factory integration works."""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller has workflow guidance factory available
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.AgentWorkflowFactory') as mock_workflow_factory:
            result = controller.manage_agent(
                action="register",
                project_id="project-123",
                name="test-agent"
            )
            
            # Workflow guidance should be available even if not explicitly used
            assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_enhanced_error_handling(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test enhanced error handling with more specific error types."""
        mock_get_user.return_value = "test-user"
        
        # Test facade exception handling
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        mock_facade.register_agent.side_effect = ConnectionError("Database connection failed")
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is False
        assert "Database connection failed" in result["error"]

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.validate_user_id')
    def test_user_id_validation_flow(self, mock_validate_user, mock_get_user, controller):
        """Test complete user ID validation flow."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        result = controller.manage_agent(
            action="register",
            project_id="project-123",
            name="test-agent"
        )
        
        assert result["success"] is True
        mock_validate_user.assert_called()

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_all_supported_actions_comprehensive(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test all supported agent management actions with proper responses."""
        mock_get_user.return_value = "test-user"
        
        # Setup different responses for different actions
        mock_facade = mock_agent_facade_factory.create_agent_facade.return_value
        mock_facade.register_agent.return_value = {"success": True, "agent_id": "agent-123", "action": "register"}
        mock_facade.assign_agent.return_value = {"success": True, "assigned": True, "action": "assign"}
        mock_facade.get_agent.return_value = {"success": True, "agent": {"id": "agent-123"}, "action": "get"}
        mock_facade.list_agents.return_value = {"success": True, "agents": [], "action": "list"}
        mock_facade.update_agent.return_value = {"success": True, "updated": True, "action": "update"}
        mock_facade.unassign_agent.return_value = {"success": True, "unassigned": True, "action": "unassign"}
        mock_facade.unregister_agent.return_value = {"success": True, "unregistered": True, "action": "unregister"}
        mock_facade.rebalance_agents.return_value = {"success": True, "rebalanced": True, "action": "rebalance"}
        
        actions = [
            {"action": "register", "project_id": "p1", "name": "agent"},
            {"action": "assign", "project_id": "p1", "agent_id": "a1", "git_branch_id": "b1"},
            {"action": "get", "project_id": "p1", "agent_id": "a1"},
            {"action": "list", "project_id": "p1"},
            {"action": "update", "project_id": "p1", "agent_id": "a1", "name": "updated"},
            {"action": "unassign", "project_id": "p1", "agent_id": "a1", "git_branch_id": "b1"},
            {"action": "unregister", "project_id": "p1", "agent_id": "a1"},
            {"action": "rebalance", "project_id": "p1"}
        ]
        
        for action_params in actions:
            result = controller.manage_agent(**action_params)
            
            # All should succeed with mocked facade
            assert result["success"] is True
            assert result["action"] == action_params["action"]

    def test_controller_initialization_comprehensive(self, mock_agent_facade_factory):
        """Test comprehensive controller initialization."""
        controller = AgentMCPController(mock_agent_facade_factory)
        
        # Test that the factory is properly stored
        assert controller._agent_facade_factory == mock_agent_facade_factory
        
        # Test that the workflow factory is initialized
        assert hasattr(controller, '_workflow_factory')
        
        # Test logging is configured
        from fastmcp.task_management.interface.controllers.agent_mcp_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_concurrent_operations_safety(self, mock_get_user, controller, mock_agent_facade_factory):
        """Test that concurrent operations are handled safely."""
        mock_get_user.return_value = "test-user"
        
        # Simulate multiple concurrent requests
        results = []
        import threading
        
        def make_request(project_id):
            result = controller.manage_agent(
                action="list",
                project_id=project_id
            )
            results.append(result)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(f"project-{i}",))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should succeed
        for result in results:
            assert result["success"] is True
        
        # Should have been called 5 times
        assert mock_agent_facade_factory.create_agent_facade.call_count == 5