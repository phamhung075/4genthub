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
        
        # Mock the get_manage_project_description function that's actually used
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_manage_project_description') as mock_get_desc, \
             patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_manage_project_parameters') as mock_get_params:
            
            mock_get_desc.return_value = "Test project management description"
            mock_get_params.return_value = {
                "action": {"description": "Action parameter"},
                "project_id": {"description": "Project ID parameter"},
                "name": {"description": "Name parameter"},
                "description": {"description": "Description parameter"},
                "force": {"description": "Force parameter"},
                "user_id": {"description": "User ID parameter"}
            }
            
            self.controller.register_tools(mock_mcp)
            
            # Verify tool decorator was called with description
            mock_mcp.tool.assert_called_once_with(description="Test project management description")
    
    def test_get_facade_for_request_with_user_context(self):
        """Test getting facade with user context from facade factory."""
        result = self.controller._get_facade_for_request(user_id="test-user-123")
        
        assert result == self.mock_facade
        self.mock_facade_factory.create_project_facade.assert_called_once_with(
            user_id="test-user-123"
        )
    
    def test_get_facade_for_request_no_facade_service_raises_error(self):
        """Test getting facade without facade service raises error."""
        # Set both facade factory and service to None to trigger the error
        self.controller._project_facade_factory = None
        self.controller._facade_service = None
        
        with pytest.raises(ValueError) as exc_info:
            self.controller._get_facade_for_request()
        
        assert "Either facade_factory or facade_service is required" in str(exc_info.value)
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_project_create_action(self, mock_get_auth_user_id):
        """Test manage_project with create action."""
        mock_get_auth_user_id.return_value = "test-user-123"
        
        # Mock permission check to always allow
        with patch.object(self.controller, '_check_project_permissions') as mock_permissions:
            mock_permissions.return_value = (True, None)
            
            # Mock the operation factory to return success
            with patch.object(self.controller._operation_factory, 'handle_operation', new_callable=AsyncMock) as mock_handle_operation:
                mock_handle_operation.return_value = {"success": True, "project": {"id": "test-project-id"}}
                
                result = await self.controller._manage_project_async(
                    action="create",
                    name="test-project",
                    description="Test project description"
                )
                
                assert result == {"success": True, "project": {"id": "test-project-id"}}
                mock_handle_operation.assert_called_once()
                mock_permissions.assert_called_once_with("create", "test-user-123", None)
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_project_health_check_action(self, mock_get_auth_user_id):
        """Test manage_project with project_health_check action."""
        mock_get_auth_user_id.return_value = "test-user-123"
        
        # Mock permission check to always allow
        with patch.object(self.controller, '_check_project_permissions') as mock_permissions:
            mock_permissions.return_value = (True, None)
            
            # Mock the operation factory to return success
            with patch.object(self.controller._operation_factory, 'handle_operation', new_callable=AsyncMock) as mock_handle_operation:
                mock_handle_operation.return_value = {"success": True, "health_score": 85}
                
                result = await self.controller._manage_project_async(
                    action="project_health_check",
                    project_id="test-project"
                )
                
                assert result == {"success": True, "health_score": 85}
                mock_handle_operation.assert_called_once()
                mock_permissions.assert_called_once_with("project_health_check", "test-user-123", "test-project")
    
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
        assert "error" in result
        assert "meta" in result
        # Note: This may return an internal error about INVALID_OPERATION missing from ErrorCodes
        assert "invalid_action" in result["error"]["message"].lower()
    
    def test_handle_crud_operations_create_success(self):
        """Test handling create operation successfully."""
        # Mock the facade to return success response
        self.mock_facade.create_project.return_value = {"success": True, "project": {"id": "project-123"}}
            
        result = self.controller.handle_crud_operations(
            "create", None, "test-project", "Test description", "test-user-123", False
        )
        
        assert result["success"] is True
        assert result["data"]["project"]["id"] == "project-123"
        assert "meta" in result
        self.mock_facade.create_project.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.get_authenticated_user_id')
    def test_handle_crud_operations_create_missing_name(self, mock_get_auth_user_id):
        """Test create operation with missing name."""
        mock_get_auth_user_id.return_value = "test-user-123"
        
        result = self.controller.handle_crud_operations(
            "create", None, None, "Test description"
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "meta" in result
        assert "Missing required field: name" in result["error"]["message"]
    
    def test_handle_crud_operations_get_success(self):
        """Test handling get operation successfully."""
        # Mock the facade to return success response
        self.mock_facade.get_project.return_value = {"success": True, "project": {"id": "project-123"}}
            
        result = self.controller.handle_crud_operations(
            "get", "project-123", "test-project", None, "test-user-123", False
        )
        
        assert result["success"] is True
        assert result["data"]["project"]["id"] == "project-123"
        assert "meta" in result
        self.mock_facade.get_project.assert_called_once()
    
    def test_handle_crud_operations_get_by_name(self):
        """Test get operation using name when project_id not provided."""
        # Mock the facade to return success response (when using name, it calls get_project_by_name)
        self.mock_facade.get_project_by_name.return_value = {"success": True, "project": {"id": "project-123"}}
            
        result = self.controller.handle_crud_operations(
            "get", None, "test-project", None, "test-user-123", False
        )
        
        assert result["success"] is True
        assert result["data"]["project"]["id"] == "project-123"
        assert "meta" in result
        self.mock_facade.get_project_by_name.assert_called_once()
    
    def test_handle_crud_operations_get_missing_identifier(self):
        """Test get operation with missing project identifier."""
        result = self.controller.handle_crud_operations(
            "get", None, None, None, "test-user-123", False
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "meta" in result
        assert "project_id" in result["error"]["message"] and "name" in result["error"]["message"]
    
    def test_handle_crud_operations_list_success(self):
        """Test handling list operation successfully."""
        # Mock the facade to return success response
        self.mock_facade.list_projects.return_value = {"success": True, "projects": [{"id": "project-1"}]}
            
        result = self.controller.handle_crud_operations("list", None, None, None, "test-user-123", False)
        
        assert result["success"] is True
        # The response formatter extracts the first element from arrays
        assert result["data"]["projects"]["id"] == "project-1"
        assert "meta" in result
        self.mock_facade.list_projects.assert_called_once()
    
    def test_handle_crud_operations_update_success(self):
        """Test handling update operation successfully."""
        # Mock the facade to return success response
        self.mock_facade.update_project.return_value = {"success": True, "project": {"id": "project-123"}}
            
        result = self.controller.handle_crud_operations(
            "update", "project-123", "new-name", "new-description", "test-user-123", False
        )
        
        assert result["success"] is True
        assert result["data"]["project"]["id"] == "project-123"
        assert "meta" in result
        self.mock_facade.update_project.assert_called_once()
    
    def test_handle_crud_operations_update_missing_project_id(self):
        """Test update operation with missing project_id."""
        result = self.controller.handle_crud_operations(
            "update", None, "new-name", "new-description", "test-user-123", False
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "meta" in result
        assert "Missing required field: project_id" in result["error"]["message"]
    
    def test_handle_crud_operations_exception(self):
        """Test handling exception in CRUD operations."""
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = self.controller.handle_crud_operations(
                "create", None, "test-project", "description", "test-user-123", False
            )
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]["message"]
            assert result["error"]["code"] == "INTERNAL_ERROR"
    
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
        assert "error" in result
        assert "meta" in result
        assert "Missing required field: project_id" in result["error"]["message"]
    
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
        assert "error" in result
        assert "meta" in result
        assert "Missing required field: test_field" in result["error"]["message"]
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    # NOTE: _create_invalid_action_error method no longer exists
    # Invalid action handling is now done by ProjectOperationFactory
    
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
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_complete_create_workflow(self, mock_get_auth_user_id):
        """Test complete project creation workflow."""
        mock_get_auth_user_id.return_value = "test-user"
        
        # Mock permission check to always allow
        with patch.object(self.controller, '_check_project_permissions') as mock_permissions:
            mock_permissions.return_value = (True, None)
            
            # Mock the operation factory to return success
            with patch.object(self.controller._operation_factory, 'handle_operation', new_callable=AsyncMock) as mock_handle_operation:
                mock_handle_operation.return_value = {
                    "success": True,
                    "project": {"id": "project-123", "name": "test-project"}
                }
                
                result = await self.controller._manage_project_async(
                    action="create",
                    name="test-project",
                    description="Test project description"
                )
                
                # Verify successful creation
                assert result["success"] is True
                assert result["project"]["id"] == "project-123"
                mock_handle_operation.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_complete_health_check_workflow(self, mock_get_auth_user_id):
        """Test complete project health check workflow."""
        mock_get_auth_user_id.return_value = "test-user"
        
        # Mock permission check to always allow
        with patch.object(self.controller, '_check_project_permissions') as mock_permissions:
            mock_permissions.return_value = (True, None)
            
            # Mock the operation factory to return success
            with patch.object(self.controller._operation_factory, 'handle_operation', new_callable=AsyncMock) as mock_handle_operation:
                mock_handle_operation.return_value = {
                    "success": True,
                    "health_score": 75,
                    "issues": ["Low task completion rate"]
                }
                
                result = await self.controller._manage_project_async(
                    action="project_health_check",
                    project_id="project-123"
                )
                
                # Verify successful health check
                assert result["success"] is True
                assert result["health_score"] == 75
                mock_handle_operation.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])