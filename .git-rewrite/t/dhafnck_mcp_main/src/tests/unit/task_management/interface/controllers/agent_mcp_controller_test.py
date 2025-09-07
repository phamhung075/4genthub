"""Test suite for AgentMCPController.

Tests the agent MCP controller including:
- Tool registration and MCP integration
- CRUD operations routing
- Assignment operations handling
- Authentication and user context
- Error handling and validation
- Workflow guidance integration
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.task_management.interface.controllers.agent_mcp_controller import AgentMCPController
from fastmcp.task_management.application.factories.agent_facade_factory import AgentFacadeFactory
from fastmcp.task_management.application.facades.agent_application_facade import AgentApplicationFacade
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestAgentMCPController:
    """Test cases for AgentMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=AgentFacadeFactory)
        self.mock_facade = Mock(spec=AgentApplicationFacade)
        self.mock_facade_factory.create_agent_facade.return_value = self.mock_facade
        
        # Mock workflow guidance
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.AgentWorkflowFactory'):
            self.controller = AgentMCPController(self.mock_facade_factory)
    
    def test_init(self):
        """Test controller initialization."""
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.AgentWorkflowFactory') as mock_workflow_factory:
            mock_workflow = Mock()
            mock_workflow_factory.create.return_value = mock_workflow
            
            controller = AgentMCPController(self.mock_facade_factory)
            
            assert controller._agent_facade_factory == self.mock_facade_factory
            assert controller._workflow_guidance == mock_workflow
            mock_workflow_factory.create.assert_called_once()
    
    def test_register_tools(self):
        """Test MCP tool registration."""
        mock_mcp = Mock()
        mock_mcp.tool = Mock()
        
        with patch.object(self.controller, '_get_agent_management_descriptions') as mock_get_desc:
            mock_get_desc.return_value = {
                "manage_agent": {
                    "description": "Test description",
                    "parameters": {
                        "action": "Action parameter",
                        "project_id": "Project ID parameter"
                    }
                }
            }
            
            self.controller.register_tools(mock_mcp)
            
            # Verify tool was registered
            mock_mcp.tool.assert_called_once()
            call_kwargs = mock_mcp.tool.call_args[1]
            assert call_kwargs["name"] == "manage_agent"
            assert call_kwargs["description"] == "Test description"
    
    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_get_facade_for_request_with_user_context(self, mock_get_user_id):
        """Test getting facade with user context from JWT."""
        mock_get_user_id.return_value = "jwt-user-123"
        project_id = "test-project"
        
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.validate_user_id') as mock_validate:
            mock_validate.return_value = "jwt-user-123"
            
            result = self.controller._get_facade_for_request(project_id)
            
            assert result == self.mock_facade
            mock_validate.assert_called_once_with("jwt-user-123", "Agent facade creation")
            self.mock_facade_factory.create_agent_facade.assert_called_once_with(
                project_id=project_id,
                user_id="jwt-user-123"
            )
    
    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_get_facade_for_request_no_auth_raises_error(self, mock_get_user_id):
        """Test getting facade without authentication raises error."""
        mock_get_user_id.return_value = None
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            self.controller._get_facade_for_request("test-project")
        
        assert "Agent facade creation" in str(exc_info.value)
    
    def test_manage_agent_register_action(self):
        """Test manage_agent with register action."""
        with patch.object(self.controller, 'handle_crud_operations') as mock_crud:
            mock_crud.return_value = {"success": True}
            
            result = self.controller.manage_agent(
                action="register",
                project_id="test-project",
                name="test-agent"
            )
            
            assert result == {"success": True}
            mock_crud.assert_called_once_with(
                "register", "test-project", None, "test-agent", None, None
            )
    
    def test_manage_agent_assign_action(self):
        """Test manage_agent with assign action."""
        with patch.object(self.controller, 'handle_assignment_operations') as mock_assign:
            mock_assign.return_value = {"success": True}
            
            result = self.controller.manage_agent(
                action="assign",
                project_id="test-project",
                agent_id="agent-123",
                git_branch_id="branch-456"
            )
            
            assert result == {"success": True}
            mock_assign.assert_called_once_with(
                "assign", "test-project", "agent-123", "branch-456", None
            )
    
    def test_manage_agent_rebalance_action(self):
        """Test manage_agent with rebalance action."""
        with patch.object(self.controller, 'handle_rebalance_operation') as mock_rebalance:
            mock_rebalance.return_value = {"success": True}
            
            result = self.controller.manage_agent(
                action="rebalance",
                project_id="test-project"
            )
            
            assert result == {"success": True}
            mock_rebalance.assert_called_once_with("test-project", None)
    
    def test_manage_agent_unknown_action(self):
        """Test manage_agent with unknown action."""
        result = self.controller.manage_agent(
            action="invalid_action",
            project_id="test-project"
        )
        
        assert result["success"] is False
        assert result["error"] == "Unknown action: invalid_action"
        assert result["error_code"] == "UNKNOWN_ACTION"
        assert "valid_actions" in result
        assert "hint" in result
    
    def test_handle_crud_operations_register_success(self):
        """Test handling register operation successfully."""
        self.mock_facade.register_agent.return_value = {
            "success": True,
            "agent": {"id": "agent-123", "name": "test-agent"}
        }
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_crud_operations(
                    "register", "test-project", "agent-123", "test-agent", "call-config"
                )
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.register_agent.assert_called_once_with(
                    "test-project", "agent-123", "test-agent", "call-config"
                )
                mock_enhance.assert_called_once()
    
    def test_handle_crud_operations_register_auto_generate_id(self):
        """Test register operation auto-generates agent ID."""
        self.mock_facade.register_agent.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True}
                with patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value.hex = "auto-generated-id"
                    
                    result = self.controller.handle_crud_operations(
                        "register", "test-project", None, "test-agent", None
                    )
                    
                    # Should have auto-generated an ID
                    self.mock_facade.register_agent.assert_called_once()
                    call_args = self.mock_facade.register_agent.call_args[0]
                    assert call_args[1] is not None  # agent_id should not be None
    
    def test_handle_crud_operations_register_missing_name(self):
        """Test register operation with missing name."""
        result = self.controller.handle_crud_operations(
            "register", "test-project", "agent-123", None, None, user_id="test-user"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: name"
        assert result["error_code"] == "MISSING_FIELD"
        assert result["field"] == "name"
        assert result["action"] == "register"
    
    def test_handle_crud_operations_get_success(self):
        """Test handling get operation successfully."""
        self.mock_facade.get_agent.return_value = {
            "success": True,
            "agent": {"id": "agent-123", "name": "test-agent"}
        }
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_crud_operations(
                    "get", "test-project", "agent-123"
                )
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.get_agent.assert_called_once_with("test-project", "agent-123")
    
    def test_handle_crud_operations_get_missing_agent_id(self):
        """Test get operation with missing agent_id."""
        result = self.controller.handle_crud_operations(
            "get", "test-project", None, user_id="test-user"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: agent_id"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_crud_operations_list_success(self):
        """Test handling list operation successfully."""
        self.mock_facade.list_agents.return_value = {
            "success": True,
            "agents": [{"id": "agent-1"}, {"id": "agent-2"}]
        }
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_crud_operations(
                    "list", "test-project"
                )
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.list_agents.assert_called_once_with("test-project")
    
    def test_handle_crud_operations_exception(self):
        """Test handling exception in CRUD operations."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_crud_operations(
                "register", "test-project", "agent-123", "test-agent"
            )
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"
            assert "Test exception" in result["details"]
    
    def test_handle_assignment_operations_assign_success(self):
        """Test handling assign operation successfully."""
        self.mock_facade.assign_agent.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_assignment_operations(
                    "assign", "test-project", "agent-123", "branch-456"
                )
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.assign_agent.assert_called_once_with(
                    "test-project", "agent-123", "branch-456"
                )
    
    def test_handle_assignment_operations_missing_agent_id(self):
        """Test assignment operation with missing agent_id."""
        result = self.controller.handle_assignment_operations(
            "assign", "test-project", None, "branch-456", user_id="test-user"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: agent_id"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_assignment_operations_missing_git_branch_id(self):
        """Test assignment operation with missing git_branch_id."""
        result = self.controller.handle_assignment_operations(
            "assign", "test-project", "agent-123", None, user_id="test-user"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: git_branch_id"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_assignment_operations_unassign_success(self):
        """Test handling unassign operation successfully."""
        self.mock_facade.unassign_agent.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_assignment_operations(
                    "unassign", "test-project", "agent-123", "branch-456"
                )
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.unassign_agent.assert_called_once_with(
                    "test-project", "agent-123", "branch-456"
                )
    
    def test_handle_assignment_operations_exception(self):
        """Test handling exception in assignment operations."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_assignment_operations(
                "assign", "test-project", "agent-123", "branch-456"
            )
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"
    
    def test_handle_rebalance_operation_success(self):
        """Test handling rebalance operation successfully."""
        self.mock_facade.rebalance_agents.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            with patch.object(self.controller, '_enhance_response_with_workflow_guidance') as mock_enhance:
                mock_enhance.return_value = {"success": True, "enhanced": True}
                
                result = self.controller.handle_rebalance_operation("test-project")
                
                assert result == {"success": True, "enhanced": True}
                self.mock_facade.rebalance_agents.assert_called_once_with("test-project")
    
    def test_handle_rebalance_operation_exception(self):
        """Test handling exception in rebalance operation."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_rebalance_operation("test-project")
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"
    
    def test_get_agent_management_descriptions(self):
        """Test getting agent management descriptions."""
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.description_loader') as mock_loader:
            mock_loader.get_all_descriptions.return_value = {
                "agents": {
                    "manage_agent": {
                        "description": "Test description",
                        "parameters": {"action": "Action param"}
                    }
                }
            }
            
            result = self.controller._get_agent_management_descriptions()
            
            expected = {
                "manage_agent": {
                    "description": "Test description",
                    "parameters": {"action": "Action param"}
                }
            }
            assert result == expected
    
    def test_create_missing_field_error(self):
        """Test creating missing field error response."""
        result = self.controller._create_missing_field_error("test_field", "test_action")
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: test_field"
        assert result["error_code"] == "MISSING_FIELD"
        assert result["field"] == "test_field"
        assert result["action"] == "test_action"
        assert "expected" in result
        assert "hint" in result
    
    def test_create_invalid_action_error(self):
        """Test creating invalid action error response."""
        result = self.controller._create_invalid_action_error("invalid_action")
        
        assert result["success"] is False
        assert result["error"] == "Invalid action: invalid_action"
        assert result["error_code"] == "INVALID_ACTION"
        assert result["field"] == "action"
        assert "valid_actions" in result
        assert "hint" in result
    
    def test_enhance_response_with_workflow_guidance_success(self):
        """Test enhancing successful response with workflow guidance."""
        response = {"success": True, "agent": {"id": "agent-123"}}
        
        mock_guidance = {"next_steps": ["Test step"], "hints": ["Test hint"]}
        self.controller._workflow_guidance.generate_guidance.return_value = mock_guidance
        
        result = self.controller._enhance_response_with_workflow_guidance(
            response, "register", "test-project", "agent-123"
        )
        
        assert result["success"] is True
        assert result["workflow_guidance"] == mock_guidance
        self.controller._workflow_guidance.generate_guidance.assert_called_once_with(
            "register", {"project_id": "test-project", "agent_id": "agent-123"}
        )
    
    def test_enhance_response_with_workflow_guidance_failure(self):
        """Test enhancing failed response (no guidance added)."""
        response = {"success": False, "error": "Test error"}
        
        result = self.controller._enhance_response_with_workflow_guidance(
            response, "register", "test-project"
        )
        
        assert result == response  # Should be unchanged
        assert "workflow_guidance" not in result
        # Should not call guidance generation for failed responses
        self.controller._workflow_guidance.generate_guidance.assert_not_called()
    
    def test_enhance_response_extract_agent_id_from_register(self):
        """Test extracting agent ID from register response for guidance."""
        response = {
            "success": True,
            "agent": {"id": "new-agent-123", "name": "test-agent"}
        }
        
        mock_guidance = {"next_steps": ["Test step"]}
        self.controller._workflow_guidance.generate_guidance.return_value = mock_guidance
        
        result = self.controller._enhance_response_with_workflow_guidance(
            response, "register", "test-project"
        )
        
        # Should extract agent ID from response
        expected_context = {
            "project_id": "test-project",
            "agent_id": "new-agent-123"
        }
        self.controller._workflow_guidance.generate_guidance.assert_called_once_with(
            "register", expected_context
        )


class TestAgentMCPControllerIntegration:
    """Integration tests for AgentMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=AgentFacadeFactory)
        self.mock_facade = Mock(spec=AgentApplicationFacade)
        self.mock_facade_factory.create_agent_facade.return_value = self.mock_facade
        
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.AgentWorkflowFactory'):
            self.controller = AgentMCPController(self.mock_facade_factory)
    
    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_complete_register_workflow(self, mock_get_user_id):
        """Test complete agent registration workflow."""
        mock_get_user_id.return_value = "test-user"
        
        # Mock facade response
        self.mock_facade.register_agent.return_value = {
            "success": True,
            "agent": {"id": "agent-123", "name": "test-agent"}
        }
        
        # Mock workflow guidance
        mock_guidance = {"next_steps": ["Assign agent to branch"]}
        self.controller._workflow_guidance.generate_guidance.return_value = mock_guidance
        
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.validate_user_id') as mock_validate:
            mock_validate.return_value = "test-user"
            
            result = self.controller.manage_agent(
                action="register",
                project_id="test-project",
                name="test-agent",
                call_agent="test-config"
            )
            
            # Verify successful registration
            assert result["success"] is True
            assert result["agent"]["id"] == "agent-123"
            assert result["workflow_guidance"] == mock_guidance
            
            # Verify facade was called correctly
            self.mock_facade_factory.create_agent_facade.assert_called_once_with(
                project_id="test-project",
                user_id="test-user"
            )
            
            # Verify register was called with auto-generated ID
            self.mock_facade.register_agent.assert_called_once()
            call_args = self.mock_facade.register_agent.call_args[0]
            assert call_args[0] == "test-project"  # project_id
            assert call_args[1] is not None       # agent_id (auto-generated)
            assert call_args[2] == "test-agent"   # name
            assert call_args[3] == "test-config"  # call_agent
    
    @patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.get_current_user_id')
    def test_complete_assign_workflow(self, mock_get_user_id):
        """Test complete agent assignment workflow."""
        mock_get_user_id.return_value = "test-user"
        
        # Mock facade response
        self.mock_facade.assign_agent.return_value = {"success": True}
        
        # Mock workflow guidance
        mock_guidance = {"next_steps": ["Start working on tasks"]}
        self.controller._workflow_guidance.generate_guidance.return_value = mock_guidance
        
        with patch('fastmcp.task_management.interface.controllers.agent_mcp_controller.validate_user_id') as mock_validate:
            mock_validate.return_value = "test-user"
            
            result = self.controller.manage_agent(
                action="assign",
                project_id="test-project",
                agent_id="agent-123",
                git_branch_id="branch-456"
            )
            
            # Verify successful assignment
            assert result["success"] is True
            assert result["workflow_guidance"] == mock_guidance
            
            # Verify facade was called correctly
            self.mock_facade.assign_agent.assert_called_once_with(
                "test-project", "agent-123", "branch-456"
            )


if __name__ == "__main__":
    pytest.main([__file__])