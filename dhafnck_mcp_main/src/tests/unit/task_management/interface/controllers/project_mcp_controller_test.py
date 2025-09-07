"""Test suite for ProjectMCPController.

Tests the project MCP controller including:
- Tool registration and MCP integration
- CRUD operations for projects
- Health checks and maintenance
- Authentication and user context
- Error handling and validation
- Workflow guidance integration
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestProjectMCPController:
    """Test cases for ProjectMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=ProjectFacadeFactory)
        self.mock_facade = Mock(spec=ProjectApplicationFacade)
        self.mock_facade_factory.create_project_facade.return_value = self.mock_facade
        
        # Create controller directly - no need to patch non-existent factory
        self.controller = ProjectMCPController(self.mock_facade_factory)
    
    def test_init(self):
        """Test controller initialization."""
        controller = ProjectMCPController(self.mock_facade_factory)
        
        assert controller._project_facade_factory == self.mock_facade_factory
    
    def test_register_tools(self):
        """Test MCP tool registration."""
        mock_mcp = Mock()
        mock_mcp.tool = Mock()
        
        with patch.object(self.controller, '_get_project_management_descriptions') as mock_get_desc:
            mock_get_desc.return_value = {
                "manage_project": {
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
            assert call_kwargs["name"] == "manage_project"
            assert call_kwargs["description"] == "Test description"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_get_facade_for_request_with_user_context(self, mock_get_auth_user_id):
        """Test getting facade with user context from JWT."""
        mock_get_auth_user_id.return_value = "jwt-user-123"
        
        result = self.controller._get_facade_for_request()
        
        assert result == self.mock_facade
        mock_get_auth_user_id.assert_called_once_with(None, "Project facade creation")
        self.mock_facade_factory.create_project_facade.assert_called_once_with(
            user_id="jwt-user-123"
        )
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_get_facade_for_request_no_auth_raises_error(self, mock_get_auth_user_id):
        """Test getting facade without authentication raises error."""
        mock_get_auth_user_id.side_effect = UserAuthenticationRequiredError("Project facade creation")
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            self.controller._get_facade_for_request()
        
        assert "Project facade creation" in str(exc_info.value)
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.validate_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_manage_project_create_action(self, mock_get_auth_user_id, mock_get_current_user_id, mock_validate_user_id):
        """Test manage_project with create action."""
        mock_get_auth_user_id.return_value = "test-user-123"
        mock_get_current_user_id.return_value = "test-user-123"
        mock_validate_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, 'handle_crud_operations') as mock_crud:
            mock_crud.return_value = {"success": True}
            
            result = self.controller.manage_project(
                action="create",
                name="test-project",
                description="Test project description"
            )
            
            assert result == {"success": True}
            mock_crud.assert_called_once_with(
                "create", None, "test-project", "Test project description", "test-user-123", False
            )
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.validate_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_manage_project_health_check_action(self, mock_get_auth_user_id, mock_get_current_user_id, mock_validate_user_id):
        """Test manage_project with project_health_check action."""
        mock_get_auth_user_id.return_value = "test-user-123"
        mock_get_current_user_id.return_value = "test-user-123"
        mock_validate_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, 'handle_maintenance_operations') as mock_maintenance:
            mock_maintenance.return_value = {"success": True}
            
            result = self.controller.manage_project(
                action="project_health_check",
                project_id="test-project"
            )
            
            assert result == {"success": True}
            mock_maintenance.assert_called_once_with(
                "project_health_check", "test-project", False, "test-user-123"
            )
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.validate_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_manage_project_unknown_action(self, mock_get_auth_user_id, mock_get_current_user_id, mock_validate_user_id):
        """Test manage_project with unknown action."""
        mock_get_auth_user_id.return_value = "test-user-123"
        mock_get_current_user_id.return_value = "test-user-123"
        mock_validate_user_id.return_value = "test-user-123"
        
        result = self.controller.manage_project(
            action="invalid_action",
            name="test-project"
        )
        
        assert result["success"] is False
        assert result["error"] == "Unknown action: invalid_action"
        assert result["error_code"] == "UNKNOWN_ACTION"
        assert "valid_actions" in result
    
    def test_handle_crud_operations_create_success(self):
        """Test handling create operation successfully."""
        with patch.object(self.controller, '_handle_create_project') as mock_create:
            mock_create.return_value = {"success": True, "project": {"id": "project-123"}}
                
            result = self.controller.handle_crud_operations(
                "create", None, "test-project", "Test description", "test-user-123", False
            )
            
            assert result == {"success": True, "project": {"id": "project-123"}}
            mock_create.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_handle_crud_operations_create_missing_name(self, mock_get_auth_user_id):
        """Test create operation with missing name."""
        mock_get_auth_user_id.return_value = "test-user-123"
        
        result = self.controller.handle_crud_operations(
            "create", None, None, "Test description"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: name"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_crud_operations_get_success(self):
        """Test handling get operation successfully."""
        with patch.object(self.controller, '_handle_get_project') as mock_get:
            mock_get.return_value = {"success": True, "project": {"id": "project-123"}}
                
            result = self.controller.handle_crud_operations(
                "get", "project-123", "test-project", None, "test-user-123", False
            )
            
            assert result == {"success": True, "project": {"id": "project-123"}}
            mock_get.assert_called_once()
    
    def test_handle_crud_operations_get_by_name(self):
        """Test get operation using name when project_id not provided."""
        with patch.object(self.controller, '_handle_get_project') as mock_get:
            mock_get.return_value = {"success": True, "project": {"id": "project-123"}}
                
            result = self.controller.handle_crud_operations(
                "get", None, "test-project", None, "test-user-123", False
            )
            
            assert result == {"success": True, "project": {"id": "project-123"}}
            mock_get.assert_called_once()
    
    def test_handle_crud_operations_get_missing_identifier(self):
        """Test get operation with missing project identifier."""
        result = self.controller.handle_crud_operations(
            "get", None, None, None, "test-user-123", False
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: either project_id or name is required"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_crud_operations_list_success(self):
        """Test handling list operation successfully."""
        with patch.object(self.controller, '_handle_list_projects') as mock_list:
            mock_list.return_value = {"success": True, "projects": [{"id": "project-1"}]}
                
            result = self.controller.handle_crud_operations("list", None, None, None, "test-user-123", False)
            
            assert result == {"success": True, "projects": [{"id": "project-1"}]}
            mock_list.assert_called_once()
    
    def test_handle_crud_operations_update_success(self):
        """Test handling update operation successfully."""
        with patch.object(self.controller, '_handle_update_project') as mock_update:
            mock_update.return_value = {"success": True}
                
            result = self.controller.handle_crud_operations(
                "update", "project-123", "new-name", "new-description", "test-user-123", False
            )
            
            assert result == {"success": True}
            mock_update.assert_called_once()
    
    def test_handle_crud_operations_update_missing_project_id(self):
        """Test update operation with missing project_id."""
        result = self.controller.handle_crud_operations(
            "update", None, "new-name", "new-description", "test-user-123", False
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: project_id"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_crud_operations_exception(self):
        """Test handling exception in CRUD operations."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_crud_operations(
                "create", None, "test-project", "description", "test-user-123", False
            )
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"
    
    def test_handle_maintenance_operations_health_check_success(self):
        """Test handling health check operation successfully."""
        with patch.object(self.controller, '_handle_maintenance_action') as mock_maintenance:
            mock_maintenance.return_value = {"success": True, "health_score": 85}
                
            result = self.controller.handle_maintenance_operations(
                "project_health_check", "project-123", False, "test-user-123"
            )
            
            assert result == {"success": True, "health_score": 85}
            mock_maintenance.assert_called_once()
    
    def test_handle_maintenance_operations_cleanup_obsolete_success(self):
        """Test handling cleanup obsolete operation successfully."""
        with patch.object(self.controller, '_handle_maintenance_action') as mock_maintenance:
            mock_maintenance.return_value = {"success": True}
                
            result = self.controller.handle_maintenance_operations(
                "cleanup_obsolete", "project-123", True, "test-user-123"
            )
            
            assert result == {"success": True}
            mock_maintenance.assert_called_once()
    
    def test_handle_maintenance_operations_validate_integrity_success(self):
        """Test handling validate integrity operation successfully."""
        with patch.object(self.controller, '_handle_maintenance_action') as mock_maintenance:
            mock_maintenance.return_value = {"success": True}
                
            result = self.controller.handle_maintenance_operations(
                "validate_integrity", "project-123", False, "test-user-123"
            )
            
            assert result == {"success": True}
            mock_maintenance.assert_called_once()
    
    def test_handle_maintenance_operations_rebalance_agents_success(self):
        """Test handling rebalance agents operation successfully."""
        with patch.object(self.controller, '_handle_maintenance_action') as mock_maintenance:
            mock_maintenance.return_value = {"success": True}
                
            result = self.controller.handle_maintenance_operations(
                "rebalance_agents", "project-123", False, "test-user-123"
            )
            
            assert result == {"success": True}
            mock_maintenance.assert_called_once()
    
    def test_handle_maintenance_operations_missing_project_id(self):
        """Test maintenance operation with missing project_id."""
        result = self.controller.handle_maintenance_operations(
            "project_health_check", None, False, "test-user-123"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: project_id"
        assert result["error_code"] == "MISSING_FIELD"
    
    def test_handle_maintenance_operations_exception(self):
        """Test handling exception in maintenance operations."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_maintenance_operations(
                "project_health_check", "project-123", False, "test-user-123"
            )
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"
    
    def test_get_project_management_descriptions(self):
        """Test getting project management descriptions."""
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.description_loader') as mock_loader:
            mock_loader.get_all_descriptions.return_value = {
                "projects": {
                    "manage_project": {
                        "description": "Test description",
                        "parameters": {"action": "Action param"}
                    }
                }
            }
            
            result = self.controller._get_project_management_descriptions()
            
            expected = {
                "manage_project": {
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
    
    def test_create_invalid_action_error(self):
        """Test creating invalid action error response."""
        result = self.controller._create_invalid_action_error("invalid_action")
        
        assert result["success"] is False
        assert result["error"] == "Invalid action: invalid_action"
        assert result["error_code"] == "INVALID_ACTION"
        assert "valid_actions" in result
    
    def test_include_project_context(self):
        """Test including project context in response."""
        response = {"success": True, "project": {"id": "project-123"}}
        
        with patch('fastmcp.task_management.infrastructure.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            mock_context_facade = Mock()
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            mock_context_facade.get_context.return_value = {
                "success": True,
                "context": {"test": "context"}
            }
            
            result = self.controller._include_project_context(response)
            
            assert result["success"] is True
            assert result["project_context"] == {"test": "context"}
            mock_context_facade.get_context.assert_called_once_with("project", "project-123", include_inherited=True)
    
    def test_include_project_context_missing_project_id(self):
        """Test including project context with missing project ID."""
        response = {"success": True, "project": {}}
        
        result = self.controller._include_project_context(response)
        
        # Should return unchanged response when project_id is missing
        assert result == response
    
    def test_include_project_context_exception(self):
        """Test handling exception when including project context."""
        response = {"success": True, "project": {"id": "project-123"}}
        
        with patch('fastmcp.task_management.infrastructure.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            mock_factory.side_effect = Exception("Context error")
            
            result = self.controller._include_project_context(response)
            
            # Should return original response when context inclusion fails
            assert result == response
            assert "project_context" not in result


class TestProjectMCPControllerIntegration:
    """Integration tests for ProjectMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=ProjectFacadeFactory)
        self.mock_facade = Mock(spec=ProjectApplicationFacade)
        self.mock_facade_factory.create_project_facade.return_value = self.mock_facade
        
        # Create controller directly - no need to patch non-existent factory
        self.controller = ProjectMCPController(self.mock_facade_factory)
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.validate_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_complete_create_workflow(self, mock_get_auth_user_id, mock_get_current_user_id, mock_validate_user_id):
        """Test complete project creation workflow."""
        mock_get_auth_user_id.return_value = "test-user"
        mock_get_current_user_id.return_value = "test-user"
        mock_validate_user_id.return_value = "test-user"
        
        with patch.object(self.controller, '_handle_create_project') as mock_create:
            mock_create.return_value = {
                "success": True,
                "project": {"id": "project-123", "name": "test-project"}
            }
            
            result = self.controller.manage_project(
                action="create",
                name="test-project",
                description="Test project description"
            )
            
            # Verify successful creation
            assert result["success"] is True
            assert result["project"]["id"] == "project-123"
            mock_create.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.validate_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_complete_health_check_workflow(self, mock_get_auth_user_id, mock_get_current_user_id, mock_validate_user_id):
        """Test complete project health check workflow."""
        mock_get_auth_user_id.return_value = "test-user"
        mock_get_current_user_id.return_value = "test-user"
        mock_validate_user_id.return_value = "test-user"
        
        with patch.object(self.controller, '_handle_maintenance_action') as mock_maintenance:
            mock_maintenance.return_value = {
                "success": True,
                "health_score": 75,
                "issues": ["Low task completion rate"]
            }
            
            result = self.controller.manage_project(
                action="project_health_check",
                project_id="project-123"
            )
            
            # Verify successful health check
            assert result["success"] is True
            assert result["health_score"] == 75
            mock_maintenance.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])