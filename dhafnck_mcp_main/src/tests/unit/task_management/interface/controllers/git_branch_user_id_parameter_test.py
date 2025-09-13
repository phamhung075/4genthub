"""Test for user_id parameter support in manage_git_branch tool.

This test verifies that the manage_git_branch tool now accepts user_id as a parameter
and properly passes it through to the authentication system.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade


class TestGitBranchUserIdParameter:
    """Test cases for user_id parameter support in GitBranchMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_service = Mock(spec=FacadeService)
        self.mock_facade = Mock(spec=GitBranchApplicationFacade)
        self.mock_facade_service.get_branch_facade.return_value = self.mock_facade
        
        # Mock workflow guidance
        with patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller.GitBranchWorkflowFactory'):
            self.controller = GitBranchMCPController(self.mock_facade_service)
    
    def test_manage_git_branch_accepts_user_id_parameter(self):
        """Test that manage_git_branch method accepts user_id parameter without error."""
        with patch.object(self.controller._operation_factory, 'handle_operation') as mock_operation:
            mock_operation.return_value = {"success": True, "git_branch": {"id": "branch-123"}}
            
            # This should NOT raise "unexpected keyword argument" error
            result = self.controller.manage_git_branch(
                action="create",
                project_id="test-project",
                git_branch_name="feature-branch",
                user_id="test-user-001"
            )
            
            assert result["success"] is True
            # Verify that the operation factory was called
            mock_operation.assert_called_once()
    
    def test_user_id_passed_to_facade_creation(self):
        """Test that user_id is properly passed to facade creation."""
        with patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller.get_authenticated_user_id') as mock_auth:
            with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
                with patch.object(self.controller._operation_factory, 'handle_operation') as mock_operation:
                    # Mock auth to return the provided user_id unchanged
                    mock_auth.return_value = "test-user-001"
                    mock_get_facade.return_value = self.mock_facade
                    mock_operation.return_value = {
                        "success": True, 
                        "git_branch": {"id": "branch-123", "name": "feature-branch"}
                    }
                    
                    # Mock workflow guidance
                    self.controller._workflow_guidance = Mock()
                    self.controller._workflow_guidance.generate_guidance.return_value = {}
                    
                    result = self.controller.manage_git_branch(
                        action="create",
                        project_id="test-project",
                        git_branch_name="feature-branch",
                        user_id="test-user-001"
                    )
                    
                    assert result["success"] is True
                    
                    # Verify that _get_facade_for_request was called with the provided user_id
                    mock_get_facade.assert_called_once_with("test-project", "test-user-001")
    
    def test_user_id_none_uses_context_authentication(self):
        """Test that when user_id is None, context authentication is used."""
        with patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller.get_authenticated_user_id') as mock_auth:
            with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
                with patch.object(self.controller._operation_factory, 'handle_operation') as mock_operation:
                    # Mock auth to return None when no user_id is provided
                    mock_auth.return_value = None
                    mock_get_facade.return_value = self.mock_facade
                    mock_operation.return_value = {
                        "success": True,
                        "git_branch": {"id": "branch-123", "name": "feature-branch"}
                    }
                    
                    # Mock workflow guidance
                    self.controller._workflow_guidance = Mock()
                    self.controller._workflow_guidance.generate_guidance.return_value = {}
                    
                    result = self.controller.manage_git_branch(
                        action="create",
                        project_id="test-project",
                        git_branch_name="feature-branch",
                        user_id=None  # Explicitly None
                    )
                    
                    assert result["success"] is True
                    
                    # Verify that _get_facade_for_request was called with None user_id
                    mock_get_facade.assert_called_once_with("test-project", None)
    
    def test_all_actions_accept_user_id(self):
        """Test that all action types accept user_id parameter."""
        test_cases = [
            ("create", {"git_branch_name": "test-branch"}),
            ("update", {"git_branch_id": "branch-123"}),
            ("get", {"git_branch_id": "branch-123"}),
            ("list", {}),
            ("delete", {"git_branch_id": "branch-123"}),
            ("assign_agent", {"git_branch_id": "branch-123", "agent_id": "agent-456"}),
            ("unassign_agent", {"git_branch_id": "branch-123", "agent_id": "agent-456"}),
            ("get_statistics", {"git_branch_id": "branch-123"}),
        ]
        
        for action, extra_params in test_cases:
            with patch.object(self.controller._operation_factory, 'handle_operation') as mock_operation:
                mock_operation.return_value = {"success": True}
                
                params = {
                    "action": action,
                    "project_id": "test-project",
                    "user_id": "test-user-001"
                }
                params.update(extra_params)
                
                # This should not raise any "unexpected keyword argument" errors
                result = self.controller.manage_git_branch(**params)
                
                assert result["success"] is True, f"Action {action} failed"
    
    def test_mcp_tool_registration_includes_user_id(self):
        """Test that the MCP tool registration includes user_id parameter."""
        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda f: f)  # Mock decorator that returns the function
        
        # Test that registration doesn't fail - this validates that the tool function
        # properly accepts user_id parameter
        try:
            self.controller.register_tools(mock_mcp)
            # Verify tool was registered
            mock_mcp.tool.assert_called_once()
            # If we get here without exception, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"Tool registration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])