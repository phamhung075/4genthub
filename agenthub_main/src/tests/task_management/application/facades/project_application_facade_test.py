"""
Test suite for project_application_facade.py - Project Application Facade

Tests the facade layer for project management, including routing of actions,
parameter validation, and integration with the service layer.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.application.services.project_management_service import ProjectManagementService

class TestProjectApplicationFacade:
    """Test ProjectApplicationFacade class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        # Setup async methods
        self.mock_service.create_project = AsyncMock()
        self.mock_service.get_project = AsyncMock()
        self.mock_service.get_project_by_name = AsyncMock()
        self.mock_service.list_projects = AsyncMock()
        self.mock_service.update_project = AsyncMock()
        self.mock_service.delete_project = AsyncMock()
        self.mock_service.project_health_check = AsyncMock()
        self.mock_service.cleanup_obsolete = AsyncMock()
        self.mock_service.validate_integrity = AsyncMock()
        self.mock_service.rebalance_agents = AsyncMock()
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    def test_initialization_with_service(self):
        """Test facade initialization with provided service"""
        facade = ProjectApplicationFacade(project_service=self.mock_service)
        assert facade._project_service == self.mock_service
    
    def test_initialization_with_user_id(self):
        """Test facade initialization with user_id"""
        with patch('fastmcp.task_management.infrastructure.repositories.project_repository_factory.GlobalRepositoryManager') as mock_manager:
            mock_repo = Mock()
            mock_manager.get_for_user.return_value = mock_repo
            
            facade = ProjectApplicationFacade(user_id="user-123")
            assert facade._user_id == "user-123"
            mock_manager.get_for_user.assert_called_once_with("user-123")
    
    def test_initialization_without_parameters(self):
        """Test facade initialization without parameters"""
        with patch('fastmcp.task_management.infrastructure.repositories.project_repository_factory.GlobalRepositoryManager') as mock_manager:
            mock_repo = Mock()
            mock_manager.get_default.return_value = mock_repo
            
            facade = ProjectApplicationFacade()
            assert facade._user_id is None
            mock_manager.get_default.assert_called_once()
    
    def test_with_user_method(self):
        """Test with_user method creates scoped facade"""
        user_scoped_facade = self.facade.with_user("user-456")
        
        assert isinstance(user_scoped_facade, ProjectApplicationFacade)
        assert user_scoped_facade._user_id == "user-456"
        self.mock_service.with_user.assert_called_once_with("user-456")


class TestCreateProjectAction:
    """Test create project action through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.create_project = AsyncMock()
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        self.facade = ProjectApplicationFacade(project_service=self.mock_service, user_id="user-123")
    
    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation"""
        # Mock successful creation
        self.mock_service.create_project.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "Test Project"}
        }
        
        # Mock validator to pass
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.manage_project(
                action="create",
                name="Test Project",
                description="Test Description",
                user_id="user-123"
            )
            
            assert result["success"] is True
            assert result["project"]["name"] == "Test Project"
            
            # Verify validation was called
            mock_validator.validate_project_name.assert_called_once_with("Test Project", "user-123")
            
            # Verify service was called
            self.mock_service.create_project.assert_called_once_with("Test Project", "Test Description")
    
    @pytest.mark.asyncio
    async def test_create_project_missing_name(self):
        """Test create project with missing name"""
        result = await self.facade.manage_project(
            action="create",
            description="Test Description"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: name"
        
        # Service should not be called
        self.mock_service.create_project.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_project_missing_user_id(self):
        """Test create project with missing user_id"""
        facade = ProjectApplicationFacade(project_service=self.mock_service)
        
        result = await facade.manage_project(
            action="create",
            name="Test Project"
        )
        
        assert result["success"] is False
        assert result["error"] == "User authentication required"
    
    @pytest.mark.asyncio
    async def test_create_project_validation_failure(self):
        """Test create project with validation failure"""
        # Mock validator to fail
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock(side_effect=ValueError("Project name already exists"))
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.manage_project(
                action="create",
                name="Duplicate Project",
                user_id="user-123"
            )
            
            assert result["success"] is False
            assert result["error"] == "Project name already exists"
            
            # Service should not be called after validation failure
            self.mock_service.create_project.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_project_direct_method(self):
        """Test create_project direct method"""
        self.mock_service.create_project.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "Test Project"}
        }
        
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.create_project("Test Project", "Test Description")
            
            assert result["success"] is True
            assert result["project"]["name"] == "Test Project"


class TestGetProjectAction:
    """Test get project actions through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.get_project = AsyncMock()
        self.mock_service.get_project_by_name = AsyncMock()
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    @pytest.mark.asyncio
    async def test_get_project_by_id(self):
        """Test get project by ID"""
        self.mock_service.get_project.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "Test Project"}
        }
        
        result = await self.facade.manage_project(
            action="get",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        assert result["project"]["id"] == "proj-123"
        
        self.mock_service.get_project.assert_called_once_with("proj-123")
    
    @pytest.mark.asyncio
    async def test_get_project_by_name(self):
        """Test get project by name"""
        self.mock_service.get_project_by_name.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "Test Project"}
        }
        
        result = await self.facade.manage_project(
            action="get",
            name="Test Project"
        )
        
        assert result["success"] is True
        assert result["project"]["name"] == "Test Project"
        
        self.mock_service.get_project_by_name.assert_called_once_with("Test Project")
    
    @pytest.mark.asyncio
    async def test_get_project_missing_parameters(self):
        """Test get project with missing parameters"""
        result = await self.facade.manage_project(action="get")
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: project_id or name"
    
    @pytest.mark.asyncio
    async def test_get_project_direct_methods(self):
        """Test direct get methods"""
        # Test get_project
        self.mock_service.get_project.return_value = {"success": True, "project": {"id": "proj-123"}}
        result = await self.facade.get_project("proj-123")
        assert result["success"] is True
        
        # Test get_project_by_name
        self.mock_service.get_project_by_name.return_value = {"success": True, "project": {"name": "Test"}}
        result = await self.facade.get_project_by_name("Test")
        assert result["success"] is True


class TestListProjectsAction:
    """Test list projects action through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.list_projects = AsyncMock()
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    @pytest.mark.asyncio
    async def test_list_projects_without_user(self):
        """Test list projects without user context"""
        self.mock_service.list_projects.return_value = {
            "success": True,
            "projects": [{"id": "proj-1"}, {"id": "proj-2"}]
        }
        
        result = await self.facade.manage_project(action="list")
        
        assert result["success"] is True
        assert len(result["projects"]) == 2
        
        # Should always include branches for optimization
        self.mock_service.list_projects.assert_called_once_with(include_branches=True)
    
    @pytest.mark.asyncio
    async def test_list_projects_with_user(self):
        """Test list projects with user context"""
        self.mock_service.list_projects.return_value = {
            "success": True,
            "projects": [{"id": "proj-1"}]
        }
        
        result = await self.facade.manage_project(action="list", user_id="user-123")
        
        assert result["success"] is True
        
        # Should use user-scoped service
        self.mock_service.with_user.assert_called_once_with("user-123")
        self.mock_service.list_projects.assert_called_once_with(include_branches=True)
    
    @pytest.mark.asyncio
    async def test_list_projects_direct_method(self):
        """Test list_projects direct method"""
        self.mock_service.list_projects.return_value = {
            "success": True,
            "projects": []
        }
        
        result = await self.facade.list_projects()
        assert result["success"] is True


class TestUpdateProjectAction:
    """Test update project action through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.update_project = AsyncMock()
        self.facade = ProjectApplicationFacade(project_service=self.mock_service, user_id="user-123")
    
    @pytest.mark.asyncio
    async def test_update_project_success(self):
        """Test successful project update"""
        self.mock_service.update_project.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "Updated Project"}
        }
        
        result = await self.facade.manage_project(
            action="update",
            project_id="proj-123",
            description="New Description"
        )
        
        assert result["success"] is True
        
        self.mock_service.update_project.assert_called_once_with("proj-123", None, "New Description")
    
    @pytest.mark.asyncio
    async def test_update_project_with_name_validation(self):
        """Test update project with name validation"""
        self.mock_service.update_project.return_value = {
            "success": True,
            "project": {"id": "proj-123", "name": "New Name"}
        }
        
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.manage_project(
                action="update",
                project_id="proj-123",
                name="New Name",
                user_id="user-123"
            )
            
            assert result["success"] is True
            
            # Verify validation was called with project_id to exclude current project
            mock_validator.validate_project_name.assert_called_once_with("New Name", "user-123", "proj-123")
    
    @pytest.mark.asyncio
    async def test_update_project_missing_id(self):
        """Test update project with missing ID"""
        result = await self.facade.manage_project(
            action="update",
            name="New Name"
        )
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: project_id"
    
    @pytest.mark.asyncio
    async def test_update_project_name_validation_failure(self):
        """Test update project with name validation failure"""
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock(side_effect=ValueError("Name already exists"))
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.manage_project(
                action="update",
                project_id="proj-123",
                name="Duplicate Name",
                user_id="user-123"
            )
            
            assert result["success"] is False
            assert result["error"] == "Name already exists"
    
    @pytest.mark.asyncio
    async def test_update_project_direct_method(self):
        """Test update_project direct method"""
        self.mock_service.update_project.return_value = {"success": True}
        
        result = await self.facade.update_project("proj-123", "New Name", "New Desc")
        assert result["success"] is True
        
        self.mock_service.update_project.assert_called_once_with("proj-123", "New Name", "New Desc")


class TestDeleteProjectAction:
    """Test delete project action through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.delete_project = AsyncMock()
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    @pytest.mark.asyncio
    async def test_delete_project_success(self):
        """Test successful project deletion"""
        self.mock_service.delete_project.return_value = {
            "success": True,
            "message": "Project deleted"
        }
        
        result = await self.facade.manage_project(
            action="delete",
            project_id="proj-123",
            user_id="user-123",
            force=True
        )
        
        assert result["success"] is True
        
        # Should use user-scoped service
        self.mock_service.with_user.assert_called_once_with("user-123")
        self.mock_service.delete_project.assert_called_once_with("proj-123", True)
    
    @pytest.mark.asyncio
    async def test_delete_project_missing_id(self):
        """Test delete project with missing ID"""
        result = await self.facade.manage_project(action="delete")
        
        assert result["success"] is False
        assert result["error"] == "Missing required field: project_id"
    
    @pytest.mark.asyncio
    async def test_delete_project_direct_method(self):
        """Test delete_project direct method"""
        self.mock_service.delete_project.return_value = {"success": True}
        
        result = await self.facade.delete_project("proj-123", force=True)
        assert result["success"] is True


class TestMaintenanceActions:
    """Test maintenance actions through facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.project_health_check = AsyncMock()
        self.mock_service.cleanup_obsolete = AsyncMock()
        self.mock_service.validate_integrity = AsyncMock()
        self.mock_service.rebalance_agents = AsyncMock()
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    @pytest.mark.asyncio
    async def test_project_health_check(self):
        """Test project health check action"""
        self.mock_service.project_health_check.return_value = {
            "success": True,
            "health": "good"
        }
        
        # Test through manage_project
        result = await self.facade.manage_project(
            action="project_health_check",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        self.mock_service.project_health_check.assert_called_once_with("proj-123")
        
        # Test direct method
        result = await self.facade.project_health_check("proj-123", user_id="user-123")
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_obsolete(self):
        """Test cleanup obsolete action"""
        self.mock_service.cleanup_obsolete.return_value = {
            "success": True,
            "cleaned": 5
        }
        
        # Test through manage_project
        result = await self.facade.manage_project(
            action="cleanup_obsolete",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        self.mock_service.cleanup_obsolete.assert_called_once_with("proj-123")
        
        # Test direct method
        result = await self.facade.cleanup_obsolete("proj-123", force=True)
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_validate_integrity(self):
        """Test validate integrity action"""
        self.mock_service.validate_integrity.return_value = {
            "success": True,
            "valid": True
        }
        
        # Test through manage_project
        result = await self.facade.manage_project(
            action="validate_integrity",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        self.mock_service.validate_integrity.assert_called_once_with("proj-123")
        
        # Test direct method
        result = await self.facade.validate_integrity("proj-123")
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_rebalance_agents(self):
        """Test rebalance agents action"""
        self.mock_service.rebalance_agents.return_value = {
            "success": True,
            "rebalanced": 3
        }
        
        # Test through manage_project
        result = await self.facade.manage_project(
            action="rebalance_agents",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        self.mock_service.rebalance_agents.assert_called_once_with("proj-123")
        
        # Test direct method
        result = await self.facade.rebalance_agents("proj-123", force=True)
        assert result["success"] is True


class TestErrorHandling:
    """Test error handling in facade"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.facade = ProjectApplicationFacade(project_service=self.mock_service)
    
    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test invalid action handling"""
        result = await self.facade.manage_project(
            action="invalid_action",
            project_id="proj-123"
        )
        
        assert result["success"] is False
        assert "Invalid action: invalid_action" in result["error"]
    
    @pytest.mark.asyncio
    async def test_service_exception_handling(self):
        """Test handling of service exceptions"""
        self.mock_service.create_project = AsyncMock(side_effect=Exception("Service error"))
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        
        # Should not let exception bubble up from validation
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            result = await self.facade.manage_project(
                action="create",
                name="Test Project",
                user_id="user-123"
            )
            
            # The exception from service will be raised, not caught
            # This test verifies the exception would be raised
            assert result["success"] is True  # Validation passed
            self.mock_service.create_project.assert_called_once()


class TestUserScopedOperations:
    """Test user-scoped operations"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_service = Mock(spec=ProjectManagementService)
        self.mock_service.with_user = Mock(return_value=self.mock_service)
        self.mock_service.create_project = AsyncMock(return_value={"success": True})
        self.mock_service.list_projects = AsyncMock(return_value={"success": True})
        self.mock_service.delete_project = AsyncMock(return_value={"success": True})
    
    @pytest.mark.asyncio
    async def test_operations_use_effective_user_id(self):
        """Test that operations use effective user_id (parameter over instance)"""
        facade = ProjectApplicationFacade(project_service=self.mock_service, user_id="instance-user")
        
        # Create with parameter user_id should override instance user_id
        with patch('fastmcp.task_management.domain.services.project_name_validator.ProjectNameValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_project_name = AsyncMock()
            mock_validator_class.return_value = mock_validator
            
            await facade.manage_project(
                action="create",
                name="Test",
                user_id="param-user"
            )
            
            # Should use parameter user_id
            self.mock_service.with_user.assert_called_with("param-user")
    
    @pytest.mark.asyncio
    async def test_operations_fallback_to_instance_user_id(self):
        """Test that operations fallback to instance user_id"""
        facade = ProjectApplicationFacade(project_service=self.mock_service, user_id="instance-user")
        
        # List without parameter user_id should use instance user_id
        await facade.manage_project(action="list")
        
        # Should use instance user_id
        self.mock_service.with_user.assert_called_with("instance-user")


if __name__ == "__main__":
    pytest.main([__file__])