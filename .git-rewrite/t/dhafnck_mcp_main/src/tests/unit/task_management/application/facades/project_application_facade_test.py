"""
Tests for Project Application Facade

This module tests the ProjectApplicationFacade functionality including:
- Project management action routing
- CRUD operations (create, read, update, delete)
- Health check and maintenance operations
- Error handling and validation
- Integration with ProjectManagementService
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade


class TestProjectApplicationFacade:
    """Test suite for ProjectApplicationFacade"""
    
    @pytest.fixture
    def mock_project_service(self):
        """Create a mock project management service"""
        service = Mock()
        service.create_project = AsyncMock()
        service.get_project = AsyncMock()
        service.get_project_by_name = AsyncMock()
        service.list_projects = AsyncMock()
        service.update_project = AsyncMock()
        service.project_health_check = AsyncMock()
        service.cleanup_obsolete = AsyncMock()
        service.validate_integrity = AsyncMock()
        service.rebalance_agents = AsyncMock()
        service.delete_project = AsyncMock()
        service.with_user = Mock(return_value=service)  # Return self for with_user
        return service
    
    @pytest.fixture
    def facade(self, mock_project_service):
        """Create facade instance with mocked dependencies"""
        return ProjectApplicationFacade(mock_project_service)
    
    @pytest.mark.asyncio
    async def test_manage_project_create_success(self, facade, mock_project_service):
        """Test successful project creation via manage_project"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        mock_project_service.create_project.return_value = expected_response
        
        result = await facade.manage_project(
            action="create",
            name="Test Project",
            description="Test Description",
            user_id="user-123"
        )
        
        # Verify the service was scoped to user and create_project was called
        mock_project_service.with_user.assert_called_once_with("user-123")
        mock_project_service.create_project.assert_called_once_with(
            "Test Project", "Test Description"
        )
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_create_missing_name(self, facade, mock_project_service):
        """Test project creation with missing name"""
        result = await facade.manage_project(action="create")
        
        mock_project_service.create_project.assert_not_called()
        assert result["success"] is False
        assert "name" in result["error"]
    
    @pytest.mark.asyncio
    async def test_manage_project_get_by_id(self, facade, mock_project_service):
        """Test getting project by ID"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        mock_project_service.get_project.return_value = expected_response
        
        result = await facade.manage_project(
            action="get",
            project_id="project-123"
        )
        
        mock_project_service.get_project.assert_called_once_with("project-123")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_get_by_name(self, facade, mock_project_service):
        """Test getting project by name"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        mock_project_service.get_project_by_name.return_value = expected_response
        
        result = await facade.manage_project(
            action="get",
            name="Test Project"
        )
        
        mock_project_service.get_project_by_name.assert_called_once_with("Test Project")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_get_missing_identifier(self, facade, mock_project_service):
        """Test getting project without ID or name"""
        result = await facade.manage_project(action="get")
        
        mock_project_service.get_project.assert_not_called()
        mock_project_service.get_project_by_name.assert_not_called()
        assert result["success"] is False
        assert "project_id or name" in result["error"]
    
    @pytest.mark.asyncio
    async def test_manage_project_list(self, facade, mock_project_service):
        """Test listing projects"""
        expected_response = {
            "success": True,
            "projects": [
                {"id": "project-1", "name": "Project 1"},
                {"id": "project-2", "name": "Project 2"}
            ]
        }
        mock_project_service.list_projects.return_value = expected_response
        
        result = await facade.manage_project(action="list")
        
        # Should always include branches for frontend optimization
        mock_project_service.list_projects.assert_called_once_with(include_branches=True)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_update_success(self, facade, mock_project_service):
        """Test successful project update"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Updated Project"}
        }
        mock_project_service.update_project.return_value = expected_response
        
        result = await facade.manage_project(
            action="update",
            project_id="project-123",
            name="Updated Project",
            description="Updated Description"
        )
        
        mock_project_service.update_project.assert_called_once_with(
            "project-123", "Updated Project", "Updated Description"
        )
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_update_missing_id(self, facade, mock_project_service):
        """Test project update with missing project_id"""
        result = await facade.manage_project(action="update", name="Updated")
        
        mock_project_service.update_project.assert_not_called()
        assert result["success"] is False
        assert "project_id" in result["error"]
    
    @pytest.mark.asyncio
    async def test_manage_project_health_check(self, facade, mock_project_service):
        """Test project health check"""
        expected_response = {
            "success": True,
            "health_score": 85,
            "metrics": {"tasks": 10, "completed": 8}
        }
        mock_project_service.project_health_check.return_value = expected_response
        
        result = await facade.manage_project(
            action="project_health_check",
            project_id="project-123"
        )
        
        mock_project_service.project_health_check.assert_called_once_with("project-123")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_cleanup_obsolete(self, facade, mock_project_service):
        """Test cleanup obsolete operation"""
        expected_response = {
            "success": True,
            "cleaned_items": ["task-1", "task-2"]
        }
        mock_project_service.cleanup_obsolete.return_value = expected_response
        
        result = await facade.manage_project(
            action="cleanup_obsolete",
            project_id="project-123"
        )
        
        mock_project_service.cleanup_obsolete.assert_called_once_with("project-123")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_validate_integrity(self, facade, mock_project_service):
        """Test validate integrity operation"""
        expected_response = {
            "success": True,
            "validation_results": {"errors": 0, "warnings": 2}
        }
        mock_project_service.validate_integrity.return_value = expected_response
        
        result = await facade.manage_project(
            action="validate_integrity",
            project_id="project-123"
        )
        
        mock_project_service.validate_integrity.assert_called_once_with("project-123")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_rebalance_agents(self, facade, mock_project_service):
        """Test rebalance agents operation"""
        expected_response = {
            "success": True,
            "rebalanced_agents": ["@coding_agent", "@test_agent"]
        }
        mock_project_service.rebalance_agents.return_value = expected_response
        
        result = await facade.manage_project(
            action="rebalance_agents",
            project_id="project-123"
        )
        
        mock_project_service.rebalance_agents.assert_called_once_with("project-123")
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_delete_success(self, facade, mock_project_service):
        """Test successful project deletion"""
        expected_response = {"success": True, "deleted": True}
        mock_project_service.delete_project.return_value = expected_response
        
        result = await facade.manage_project(
            action="delete",
            project_id="project-123",
            force=True
        )
        
        mock_project_service.delete_project.assert_called_once_with("project-123", True)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_manage_project_delete_missing_id(self, facade, mock_project_service):
        """Test project deletion with missing project_id"""
        result = await facade.manage_project(action="delete")
        
        mock_project_service.delete_project.assert_not_called()
        assert result["success"] is False
        assert "project_id" in result["error"]
    
    @pytest.mark.asyncio
    async def test_manage_project_invalid_action(self, facade, mock_project_service):
        """Test invalid action handling"""
        result = await facade.manage_project(action="invalid_action")
        
        assert result["success"] is False
        assert "Invalid action" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_project_convenience_method(self, facade, mock_project_service):
        """Test create_project convenience method"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        mock_project_service.create_project.return_value = expected_response
        
        result = await facade.create_project("Test Project", "Test Description")
        
        # The convenience method should call manage_project with no user_id
        # so no with_user should be called, just the direct create_project call
        mock_project_service.create_project.assert_called_once_with(
            "Test Project", "Test Description"
        )
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_get_project_convenience_method(self, facade, mock_project_service):
        """Test get_project convenience method"""
        expected_response = {
            "success": True,
            "project": {"id": "project-123", "name": "Test Project"}
        }
        mock_project_service.get_project.return_value = expected_response
        
        result = await facade.get_project("project-123")
        
        mock_project_service.get_project.assert_called_once_with("project-123")
        assert result == expected_response
    
    @patch('fastmcp.task_management.application.facades.project_application_facade.GlobalRepositoryManager')
    def test_facade_initialization_default_service(self, mock_global_repo_manager):
        """Test facade initialization with default service"""
        mock_repo = Mock()
        mock_global_repo_manager.get_default.return_value = mock_repo
        
        with patch('fastmcp.task_management.application.facades.project_application_facade.ProjectManagementService') as MockService:
            mock_service_instance = Mock()
            MockService.return_value = mock_service_instance
            
            facade = ProjectApplicationFacade()
            
            MockService.assert_called_once_with(mock_repo, None)
            assert facade._project_service == mock_service_instance
    
    def test_facade_initialization_with_service(self, mock_project_service):
        """Test facade initialization with provided service"""
        facade = ProjectApplicationFacade(mock_project_service)
        
        assert facade._project_service == mock_project_service


class TestProjectApplicationFacadeErrorHandling:
    """Test suite for error handling in ProjectApplicationFacade"""
    
    @pytest.fixture
    def mock_project_service(self):
        """Create a mock project management service"""
        service = Mock()
        service.create_project = AsyncMock()
        service.get_project = AsyncMock()
        service.list_projects = AsyncMock()
        return service
    
    @pytest.fixture
    def facade(self, mock_project_service):
        """Create facade instance with mocked dependencies"""
        return ProjectApplicationFacade(mock_project_service)
    
    @pytest.mark.asyncio
    async def test_service_exception_propagation(self, facade, mock_project_service):
        """Test that service exceptions are properly propagated"""
        mock_project_service.create_project.side_effect = Exception("Service error")
        
        with pytest.raises(Exception, match="Service error"):
            await facade.manage_project(action="create", name="Test Project")
    
    @pytest.mark.asyncio
    async def test_service_error_response_returned(self, facade, mock_project_service):
        """Test that service error responses are returned properly"""
        error_response = {"success": False, "error": "Project already exists"}
        mock_project_service.create_project.return_value = error_response
        
        result = await facade.manage_project(action="create", name="Existing Project")
        
        assert result == error_response
        assert result["success"] is False


class TestProjectApplicationFacadeParameterHandling:
    """Test suite for parameter handling in ProjectApplicationFacade"""
    
    @pytest.fixture
    def mock_project_service(self):
        """Create a mock project management service"""
        service = Mock()
        service.create_project = AsyncMock()
        service.update_project = AsyncMock()
        service.delete_project = AsyncMock()
        return service
    
    @pytest.fixture
    def facade(self, mock_project_service):
        """Create facade instance with mocked dependencies"""
        return ProjectApplicationFacade(mock_project_service)
    
    @pytest.mark.asyncio
    async def test_optional_parameters_handling(self, facade, mock_project_service):
        """Test handling of optional parameters"""
        expected_response = {"success": True}
        mock_project_service.create_project.return_value = expected_response
        
        # Test with minimal parameters
        result = await facade.manage_project(action="create", name="Test Project")
        
        # Since no user_id provided, should use the facade's service directly
        mock_project_service.create_project.assert_called_once_with(
            "Test Project", ""
        )
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_force_parameter_default(self, facade, mock_project_service):
        """Test that force parameter defaults to False"""
        expected_response = {"success": True}
        mock_project_service.delete_project.return_value = expected_response
        
        result = await facade.manage_project(action="delete", project_id="project-123")
        
        mock_project_service.delete_project.assert_called_once_with("project-123", False)
        assert result == expected_response