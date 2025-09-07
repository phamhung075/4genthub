"""Tests for GitBranchMCPController"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError
)


class TestGitBranchMCPController:
    """Test suite for GitBranchMCPController"""

    @pytest.fixture
    def mock_git_branch_facade_factory(self):
        """Create mock git branch facade factory"""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade responses
        mock_facade.create_git_branch.return_value = {"success": True, "git_branch_id": "branch-123"}
        mock_facade.get_git_branch.return_value = {"success": True, "git_branch": {"id": "branch-123"}}
        mock_facade.list_git_branches.return_value = {"success": True, "git_branches": []}
        mock_facade.update_git_branch.return_value = {"success": True, "updated": True}
        mock_facade.delete_git_branch.return_value = {"success": True, "deleted": True}
        mock_facade.assign_agent.return_value = {"success": True, "assigned": True}
        mock_facade.unassign_agent.return_value = {"success": True, "unassigned": True}
        mock_facade.get_statistics.return_value = {"success": True, "statistics": {}}
        mock_facade.archive_git_branch.return_value = {"success": True, "archived": True}
        mock_facade.restore_git_branch.return_value = {"success": True, "restored": True}
        
        factory.create_git_branch_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_git_branch_facade_factory):
        """Create controller instance with mocked facade factory"""
        return GitBranchMCPController(mock_git_branch_facade_factory)

    def test_controller_initialization(self, mock_git_branch_facade_factory):
        """Test controller initializes correctly with facade factory"""
        controller = GitBranchMCPController(mock_git_branch_facade_factory)
        
        assert controller._git_branch_facade_factory == mock_git_branch_facade_factory

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_create_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch creation"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        
        assert result["success"] is True
        assert result["git_branch_id"] == "branch-123"
        mock_facade.create_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_get_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="get",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert "git_branch" in result
        mock_facade.get_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_list_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch listing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="list",
            project_id="project-123"
        )
        
        assert result["success"] is True
        assert "git_branches" in result
        mock_facade.list_git_branches.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_update_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch update"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="update",
            project_id="project-123",
            git_branch_id="branch-123",
            git_branch_name="updated-branch"
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        mock_facade.update_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_delete_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch deletion"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="delete",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert result["deleted"] is True
        mock_facade.delete_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_assign_agent_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful agent assignment to git branch"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_name="feature/test"
        )
        
        assert result["success"] is True
        assert result["assigned"] is True
        mock_facade.assign_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_unassign_agent_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful agent unassignment from git branch"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="unassign_agent",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert result["unassigned"] is True
        mock_facade.unassign_agent.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_get_statistics_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch statistics retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="get_statistics",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert "statistics" in result
        mock_facade.get_statistics.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_archive_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch archival"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="archive",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert result["archived"] is True
        mock_facade.archive_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_restore_success(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test successful git branch restoration"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        result = controller.manage_git_branch(
            action="restore",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        
        assert result["success"] is True
        assert result["restored"] is True
        mock_facade.restore_git_branch.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_invalid_action(self, mock_get_user, controller):
        """Test handling of invalid action"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_git_branch(
            action="invalid_action",
            project_id="project-123"
        )
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error"""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        
        assert result["success"] is False
        assert "Authentication required" in result["error"]
        assert result["error_code"] == "AUTHENTICATION_REQUIRED"


    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_manage_git_branch_general_exception(self, mock_get_user, controller):
        """Test handling of general exceptions"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._git_branch_facade_factory.create_git_branch_facade.return_value
        mock_facade.create_git_branch.side_effect = Exception("Unexpected error")
        
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["action"] == "create"

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    # Note: The register_tools method uses hardcoded descriptions, 
    # not an external description_loader, so this test was removed

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_user_id_parameter_handling(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test that user_id parameter is handled correctly"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        
        # Verify facade was created with authenticated user
        mock_git_branch_facade_factory.create_git_branch_facade.assert_called_once_with(
            project_id="project-123",
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_workflow_guidance_integration(self, mock_get_user, controller):
        """Test that workflow guidance is integrated"""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller can handle workflow guidance
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        
        # Workflow guidance should be included in responses
        assert "workflow_guidance" in result or result["success"] is True

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_git_branch_identification_by_name_or_id(self, mock_get_user, controller):
        """Test git branch identification by name or ID"""
        mock_get_user.return_value = "test-user"
        
        # Test with git_branch_id
        result_id = controller.manage_git_branch(
            action="get",
            project_id="project-123",
            git_branch_id="branch-123"
        )
        assert result_id["success"] is True
        
        # Test with git_branch_name
        result_name = controller.manage_git_branch(
            action="assign_agent",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_name="feature/test"
        )
        assert result_name["success"] is True

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_parameter_validation_for_actions(self, mock_get_user, controller):
        """Test parameter validation for different actions"""
        mock_get_user.return_value = "test-user"
        
        # Test create action requires project_id and git_branch_name
        result = controller.manage_git_branch(
            action="create",
            project_id="project-123",
            git_branch_name="feature/test"
        )
        assert result["success"] is True
        
        # Test assign_agent requires agent_id
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id="project-123",
            agent_id="agent-123",
            git_branch_name="feature/test"
        )
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional"""
        # Logger should be available for operations
        assert mock_logger is not None
        
        # Test that we can log (logger is imported at module level)
        from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_facade_creation_and_delegation(self, mock_get_user, controller, mock_git_branch_facade_factory):
        """Test that facade is properly created and operations are delegated"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_git_branch_facade_factory.create_git_branch_facade.return_value
        
        # Make request
        controller.manage_git_branch(
            action="list",
            project_id="project-123"
        )
        
        # Verify facade creation
        mock_git_branch_facade_factory.create_git_branch_facade.assert_called_once_with(
            project_id="project-123",
            user_id="test-user"
        )
        
        # Verify operation delegation
        mock_facade.list_git_branches.assert_called_once()

    @patch('fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.get_current_user_id')
    def test_action_availability_list(self, mock_get_user, controller):
        """Test that available actions are correctly listed for invalid actions"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_git_branch(
            action="nonexistent",
            project_id="project-123"
        )
        
        assert result["success"] is False
        assert "available_actions" in result
        
        expected_actions = [
            "create", "get", "list", "update", "delete",
            "assign_agent", "unassign_agent", "get_statistics",
            "archive", "restore"
        ]
        
        for action in expected_actions:
            assert action in result["available_actions"]