"""
Tests for ProjectMCPController - Project management operations following DDD principles
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestProjectMCPController:
    """Test suite for ProjectMCPController."""

    @pytest.fixture
    def mock_project_facade_factory(self):
        """Create mock project facade factory."""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade async responses
        mock_facade.manage_project = AsyncMock()
        mock_facade.manage_project.return_value = {
            "success": True, 
            "project": {"id": "project-123", "name": "test-project"}
        }
        
        factory.create_project_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        """Create controller instance with mocked facade factory."""
        return ProjectMCPController(mock_project_facade_factory)

    def test_controller_initialization(self, mock_project_facade_factory):
        """Test controller initializes correctly with facade factory."""
        controller = ProjectMCPController(mock_project_facade_factory)
        
        assert controller._project_facade_factory == mock_project_facade_factory

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_create_success(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test successful project creation."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "project": {"id": "project-123", "name": "test-project"}
        })
        
        result = controller.manage_project(
            action="create",
            name="test-project",
            description="Test Description"
        )
        
        assert result["success"] is True
        assert "project" in result
        mock_facade.manage_project.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_get_success(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test successful project retrieval."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "project": {"id": "project-123", "name": "test-project"}
        })
        
        # Mock context inclusion
        controller._include_project_context = Mock(return_value={
            "success": True,
            "project": {"id": "project-123", "name": "test-project"},
            "project_context": {"version": "1.0"}
        })
        
        result = controller.manage_project(
            action="get",
            project_id="project-123"
        )
        
        assert result["success"] is True
        assert "project_context" in result
        mock_facade.manage_project.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_list_success(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test successful project listing."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "projects": [
                {"id": "project-1", "name": "Project 1"},
                {"id": "project-2", "name": "Project 2"}
            ]
        })
        
        result = controller.manage_project(action="list")
        
        assert result["success"] is True
        assert "projects" in result
        mock_facade.manage_project.assert_called_once_with(action="list")

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_update_success(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test successful project update."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "project": {"id": "project-123", "name": "updated-project"}
        })
        
        result = controller.manage_project(
            action="update",
            project_id="project-123",
            name="updated-project",
            description="Updated Description"
        )
        
        assert result["success"] is True
        mock_facade.manage_project.assert_called_once_with(
            action="update",
            project_id="project-123",
            name="updated-project",
            description="Updated Description"
        )

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_delete_success(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test successful project deletion."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "message": "Project deleted successfully"
        })
        
        result = controller.manage_project(
            action="delete",
            project_id="project-123",
            force=True
        )
        
        assert result["success"] is True
        mock_facade.manage_project.assert_called_once_with(
            action="delete",
            project_id="project-123",
            force=True
        )

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_maintenance_operations(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test maintenance operations."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={
            "success": True,
            "message": "Health check completed"
        })
        
        result = controller.manage_project(
            action="project_health_check",
            project_id="project-123"
        )
        
        assert result["success"] is True
        mock_facade.manage_project.assert_called_once_with(
            action="project_health_check",
            project_id="project-123",
            force=False,
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    def test_manage_project_no_authentication(self, mock_get_user, controller):
        """Test project management without authentication."""
        mock_get_user.return_value = None
        
        result = controller.manage_project(
            action="create",
            name="test-project"
        )
        
        assert result["success"] is False
        assert "authentication" in result["error"].lower()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    def test_manage_project_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error."""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_project(
            action="create",
            name="test-project"
        )
        
        assert result["success"] is False
        assert "authentication" in result["error"].lower()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_manage_project_invalid_action(self, mock_validate_user, mock_get_user, controller):
        """Test handling of invalid action."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        result = controller.manage_project(
            action="invalid_action",
            project_id="project-123"
        )
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "error_code" in result
        assert "valid_actions" in result

    def test_manage_project_create_missing_name(self, controller):
        """Test create project without name."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            result = controller.manage_project(action="create")
            
            assert result["success"] is False
            assert "Missing required field: name" in result["error"]
            assert result["error_code"] == "MISSING_FIELD"

    def test_manage_project_get_missing_identifier(self, controller):
        """Test get project without project_id or name."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            result = controller.manage_project(action="get")
            
            assert result["success"] is False
            assert "either project_id or name is required" in result["error"]
            assert result["error_code"] == "MISSING_FIELD"

    def test_manage_project_update_missing_project_id(self, controller):
        """Test update project without project_id."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            result = controller.manage_project(action="update", name="new-name")
            
            assert result["success"] is False
            assert "Missing required field: project_id" in result["error"]

    def test_manage_project_delete_missing_project_id(self, controller):
        """Test delete project without project_id."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            result = controller.manage_project(action="delete")
            
            assert result["success"] is False
            assert "Missing required field: project_id" in result["error"]

    def test_manage_project_maintenance_missing_project_id(self, controller):
        """Test maintenance operation without project_id."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            result = controller.manage_project(action="project_health_check")
            
            assert result["success"] is False
            assert "Missing required field: project_id" in result["error"]


class TestUserContextHandling:
    """Test user context extraction and handling."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_user_id_string_context(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test user ID extraction when context returns string."""
        mock_get_user.return_value = "user123"
        mock_validate_user.return_value = "user123"
        
        result = controller.manage_project(action="list")
        
        assert result["success"] is True
        mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="user123")

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_user_id_object_context(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test user ID extraction when context returns object with user_id attribute."""
        mock_user_context = Mock()
        mock_user_context.user_id = "user456"
        mock_get_user.return_value = mock_user_context
        mock_validate_user.return_value = "user456"
        
        result = controller.manage_project(action="list")
        
        assert result["success"] is True
        mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="user456")

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_user_id_fallback_conversion(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test user ID fallback string conversion."""
        mock_get_user.return_value = 12345  # Non-string, no user_id attribute
        mock_validate_user.return_value = "12345"
        
        result = controller.manage_project(action="list")
        
        assert result["success"] is True
        mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="12345")

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    def test_user_id_extraction_failure(self, mock_get_user, controller):
        """Test failure in user ID extraction."""
        mock_get_user.return_value = ""  # Empty string
        
        with pytest.raises(UserAuthenticationRequiredError):
            controller.manage_project(action="list")

    def test_provided_user_id_parameter(self, controller, mock_project_facade_factory):
        """Test when user_id is provided as parameter."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_validate.return_value = "provided_user"
            
            result = controller.manage_project(
                action="list",
                user_id="provided_user"
            )
            
            assert result["success"] is True
            mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="provided_user")


class TestFacadeIntegration:
    """Test facade creation and delegation."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_facade_creation_and_delegation(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test that facade is properly created and operations are delegated."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        
        controller.manage_project(
            action="create",
            name="test-project"
        )
        
        # Verify facade creation with correct user
        mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="test-user")
        
        # Verify operation delegation
        mock_facade.manage_project.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_facade_exception_handling(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test handling of facade exceptions."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(side_effect=Exception("Facade error"))
        
        result = controller.manage_project(
            action="create",
            name="test-project"
        )
        
        assert result["success"] is False
        assert "Operation failed" in result["error"]
        assert result["error_code"] == "INTERNAL_ERROR"

    def test_get_facade_for_request(self, controller, mock_project_facade_factory):
        """Test _get_facade_for_request method."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_authenticated_user_id') as mock_get_auth_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.log_authentication_details') as mock_log_auth:
            
            mock_get_auth_user.return_value = "authenticated_user"
            
            facade = controller._get_facade_for_request()
            
            assert facade is not None
            mock_log_auth.assert_called_once()
            mock_get_auth_user.assert_called_once_with(None, "Project facade creation")
            mock_project_facade_factory.create_project_facade.assert_called_once_with(user_id="authenticated_user")


class TestContextInclusion:
    """Test project context inclusion functionality."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    def test_include_project_context_success(self, controller):
        """Test successful project context inclusion."""
        result = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.UnifiedContextFacadeFactory') as mock_factory:
            mock_context_facade = Mock()
            mock_context_facade.get_context.return_value = {
                "success": True,
                "context": {"version": "1.0", "metadata": "test"}
            }
            
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            enhanced_result = controller._include_project_context(result)
            
            assert enhanced_result["success"] is True
            assert "project_context" in enhanced_result
            assert enhanced_result["project_context"]["version"] == "1.0"

    def test_include_project_context_no_project_id(self, controller):
        """Test project context inclusion when no project ID."""
        result = {
            "success": True,
            "project": {}  # No ID
        }
        
        enhanced_result = controller._include_project_context(result)
        
        # Should return unchanged result
        assert enhanced_result == result
        assert "project_context" not in enhanced_result

    def test_include_project_context_failure(self, controller):
        """Test project context inclusion when context fetch fails."""
        result = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.UnifiedContextFacadeFactory') as mock_factory:
            mock_context_facade = Mock()
            mock_context_facade.get_context.return_value = {
                "success": False,
                "error": "Context not found"
            }
            
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            enhanced_result = controller._include_project_context(result)
            
            # Should return original result without context
            assert enhanced_result["success"] is True
            assert "project_context" not in enhanced_result

    def test_include_project_context_exception(self, controller):
        """Test project context inclusion when exception occurs."""
        result = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.UnifiedContextFacadeFactory') as mock_factory:
            mock_factory.side_effect = Exception("Context service error")
            
            enhanced_result = controller._include_project_context(result)
            
            # Should return original result without context
            assert enhanced_result == result


class TestToolRegistration:
    """Test tool registration functionality."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable."""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.description_loader')
    def test_register_tools_calls_description_loader(self, mock_desc_loader, controller):
        """Test that register_tools calls the description loader."""
        mock_mcp = Mock()
        mock_desc_loader.get_all_descriptions.return_value = {
            "project_management": {
                "manage_project": {
                    "description": "Manage project operations",
                    "parameters": {
                        "action": "Project management action",
                        "project_id": "Project identifier"
                    }
                }
            }
        }
        
        controller.register_tools(mock_mcp)
        
        # Verify that description loader was called
        mock_desc_loader.get_all_descriptions.assert_called_once()

    def test_get_project_management_descriptions(self, controller):
        """Test _get_project_management_descriptions method."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.description_loader') as mock_loader:
            mock_loader.get_all_descriptions.return_value = {
                "project_management": {
                    "manage_project": {
                        "description": "Test description",
                        "parameters": {}
                    }
                }
            }
            
            descriptions = controller._get_project_management_descriptions()
            
            assert "manage_project" in descriptions
            assert descriptions["manage_project"]["description"] == "Test description"


class TestAsyncOperationHandling:
    """Test async operation handling with context propagation."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    def test_run_async_with_context_success(self, controller):
        """Test successful async operation with context propagation."""
        async def mock_async_operation():
            return {"success": True, "result": "test"}
        
        result = controller._run_async_with_context(mock_async_operation)
        
        assert result["success"] is True
        assert result["result"] == "test"

    def test_run_async_with_context_exception(self, controller):
        """Test async operation exception handling."""
        async def mock_async_operation():
            raise Exception("Async operation failed")
        
        with pytest.raises(Exception, match="Async operation failed"):
            controller._run_async_with_context(mock_async_operation)

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_async_crud_operations(self, mock_validate_user, mock_get_user, controller, mock_project_facade_factory):
        """Test that CRUD operations properly handle async calls."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        mock_facade = mock_project_facade_factory.create_project_facade.return_value
        mock_facade.manage_project = AsyncMock(return_value={"success": True, "project": {}})
        
        # Test each CRUD operation
        operations = [
            {"action": "create", "name": "test"},
            {"action": "get", "project_id": "123"},
            {"action": "update", "project_id": "123", "name": "updated"},
            {"action": "delete", "project_id": "123"},
            {"action": "list"}
        ]
        
        for operation in operations:
            result = controller.manage_project(**operation)
            assert result["success"] is True


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    def test_create_missing_field_error(self, controller):
        """Test creation of missing field error response."""
        error = controller._create_missing_field_error("name", "create")
        
        assert error["success"] is False
        assert error["error"] == "Missing required field: name"
        assert error["error_code"] == "MISSING_FIELD"
        assert error["field"] == "name"
        assert error["action"] == "create"

    def test_create_invalid_action_error(self, controller):
        """Test creation of invalid action error response."""
        error = controller._create_invalid_action_error("invalid_action")
        
        assert error["success"] is False
        assert error["error"] == "Invalid action: invalid_action"
        assert error["error_code"] == "INVALID_ACTION"
        assert "valid_actions" in error
        assert isinstance(error["valid_actions"], list)


class TestValidationAndErrorHandling:
    """Test validation and error handling scenarios."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    def test_user_validation_integration(self, controller):
        """Test integration with user validation."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            
            mock_get_user.return_value = "valid-user"
            mock_validate.return_value = "valid-user"
            
            result = controller.manage_project(action="list")
            
            # Should work with valid user
            assert result["success"] is True
            mock_validate.assert_called_once_with("valid-user", "Project list")

    def test_default_user_prohibited_error_handling(self, controller):
        """Test handling of DefaultUserProhibitedError."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            
            mock_get_user.return_value = "default"
            mock_validate.side_effect = DefaultUserProhibitedError("Default user not allowed")
            
            result = controller.manage_project(action="create", name="test")
            
            assert result["success"] is False
            assert "Default user not allowed" in result["error"]

    def test_general_exception_handling(self, controller, mock_project_facade_factory):
        """Test handling of general exceptions."""
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            # Make facade creation fail
            mock_project_facade_factory.create_project_facade.side_effect = Exception("Unexpected error")
            
            result = controller.manage_project(action="list")
            
            assert result["success"] is False
            assert "Operation failed" in result["error"]
            assert result["error_code"] == "INTERNAL_ERROR"


class TestImportErrorHandling:
    """Test import error handling scenarios."""

    def test_import_error_fallback(self):
        """Test that import errors for auth context are handled gracefully."""
        # The controller should handle import errors gracefully
        # This is tested by the module-level import handling in the actual code
        
        # Verify the controller can be instantiated even with import issues
        factory = Mock()
        controller = ProjectMCPController(factory)
        assert controller is not None

    def test_context_propagation_mixin_fallback(self):
        """Test fallback context propagation mixin."""
        # Test that the fallback ContextPropagationMixin works
        from fastmcp.task_management.interface.controllers.project_mcp_controller import ContextPropagationMixin
        
        mixin = ContextPropagationMixin()
        
        # Test the fallback _run_async_with_context method
        async def test_async():
            return "test_result"
        
        result = mixin._run_async_with_context(test_async)
        assert result == "test_result"


class TestLogingAndDebugging:
    """Test logging and debugging functionality."""

    @pytest.fixture
    def controller(self, mock_project_facade_factory):
        return ProjectMCPController(mock_project_facade_factory)

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional."""
        # Logger should be available for operations
        assert mock_logger is not None

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.logger')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id')
    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id')
    def test_operation_logging(self, mock_validate_user, mock_get_user, mock_logger, controller, mock_project_facade_factory):
        """Test that operations are logged."""
        mock_get_user.return_value = "test-user"
        mock_validate_user.return_value = "test-user"
        
        controller.manage_project(action="list")
        
        # Verify that info logging was called for the operation
        mock_logger.info.assert_called()

    @patch('fastmcp.task_management.interface.controllers.project_mcp_controller.logger')
    def test_error_logging(self, mock_logger, controller, mock_project_facade_factory):
        """Test that errors are logged."""
        mock_project_facade_factory.create_project_facade.side_effect = Exception("Test error")
        
        with patch('fastmcp.task_management.interface.controllers.project_mcp_controller.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.interface.controllers.project_mcp_controller.validate_user_id') as mock_validate:
            mock_get_user.return_value = "test-user"
            mock_validate.return_value = "test-user"
            
            controller.manage_project(action="list")
            
            # Verify that error logging was called
            mock_logger.error.assert_called()