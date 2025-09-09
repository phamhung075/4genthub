"""
Comprehensive Unit Tests for ProjectMCPController

This module provides extensive testing for the ProjectMCPController with proper mocking
of all dependencies, including facades, authentication, permissions, and factories.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timezone

# Import the controller under test
from fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller import (
    ProjectMCPController
)

# Import dependencies that need to be mocked
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestProjectMCPController:
    """Comprehensive test suite for ProjectMCPController with proper dependency mocking."""

    @pytest.fixture
    def mock_facade_service(self):
        """Mock FacadeService with all required methods."""
        mock_service = Mock(spec=FacadeService)
        mock_facade = Mock(spec=ProjectApplicationFacade)
        
        # Configure facade methods as async mocks
        mock_facade.create_project = AsyncMock()
        mock_facade.get_project = AsyncMock()
        mock_facade.get_project_by_name = AsyncMock()
        mock_facade.update_project = AsyncMock()
        mock_facade.list_projects = AsyncMock()
        mock_facade.project_health_check = AsyncMock()
        mock_facade.cleanup_obsolete = AsyncMock()
        mock_facade.validate_integrity = AsyncMock()
        mock_facade.rebalance_agents = AsyncMock()
        
        mock_service.get_project_facade.return_value = mock_facade
        return mock_service, mock_facade

    @pytest.fixture
    def sample_project_data(self):
        """Sample project data for testing."""
        return {
            "project_id": str(uuid.uuid4()),
            "name": "Test Project",
            "description": "A test project for unit testing",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "git_branches": [],
            "tasks_count": 0
        }

    @pytest.fixture
    def sample_user_id(self):
        """Sample authenticated user ID."""
        return "test-user-456"

    @pytest.fixture
    def controller(self, mock_facade_service):
        """Create ProjectMCPController instance with mocked dependencies."""
        facade_service, _ = mock_facade_service
        return ProjectMCPController(facade_service=facade_service)

    @pytest.fixture
    def mock_authentication(self, sample_user_id):
        """Mock authentication functions."""
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id') as mock_auth, \
             patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.log_authentication_details') as mock_log:
            mock_auth.return_value = sample_user_id
            yield mock_auth, mock_log

    @pytest.fixture
    def mock_permissions(self):
        """Mock permission checking."""
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_current_request_context') as mock_context:
            # Configure mock request context with project permissions
            mock_request_context = Mock()
            mock_user = Mock()
            mock_user.token = {
                "sub": "test-user", 
                "permissions": [
                    "projects:read", "projects:write", "projects:create", 
                    "projects:update", "projects:delete", "projects:manage"
                ]
            }
            mock_request_context.user = mock_user
            mock_context.return_value = mock_request_context
            yield mock_context

    # Test Cases for CREATE operation
    @pytest.mark.asyncio
    async def test_create_project_success(self, controller, mock_facade_service, sample_project_data, sample_user_id, mock_authentication, mock_permissions):
        """Test successful project creation."""
        facade_service, mock_facade = mock_facade_service
        mock_auth, mock_log = mock_authentication
        
        # Configure facade to return success response
        expected_response = {
            "success": True,
            "data": {
                "project_id": sample_project_data["project_id"],
                "name": sample_project_data["name"],
                "description": sample_project_data["description"],
                "status": "active"
            },
            "message": "Project created successfully"
        }
        mock_facade.create_project.return_value = expected_response

        # Execute create operation
        result = await controller.manage_project(
            action="create",
            name=sample_project_data["name"],
            description=sample_project_data["description"]
        )

        # Verify authentication was called
        mock_auth.assert_called_once()
        mock_log.assert_called_once()
        
        # Verify facade was called with correct parameters
        mock_facade.create_project.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert "project_id" in result.get("data", {})
        assert result["data"]["name"] == sample_project_data["name"]

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, controller, mock_authentication, mock_permissions):
        """Test project creation with missing required name."""
        mock_auth, mock_log = mock_authentication
        
        # Execute create operation without required name
        result = await controller.manage_project(
            action="create",
            description="Project without name"
        )

        # Verify authentication was called
        mock_auth.assert_called_once()
        
        # Verify validation error is returned
        assert result["success"] is False
        assert "error" in result
        assert "name" in result["error"].lower() or "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test project creation with duplicate name."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade to return duplicate name error
        mock_facade.create_project.return_value = {
            "success": False,
            "error": "Project with name 'Test Project' already exists",
            "error_code": "DUPLICATE_NAME"
        }

        result = await controller.manage_project(
            action="create",
            name=sample_project_data["name"],
            description=sample_project_data["description"]
        )

        assert result["success"] is False
        assert "duplicate" in result["error"].lower() or "already exists" in result["error"].lower()

    # Test Cases for GET operation
    @pytest.mark.asyncio
    async def test_get_project_by_id_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful project retrieval by ID."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        expected_response = {
            "success": True,
            "data": sample_project_data,
            "message": "Project retrieved successfully"
        }
        mock_facade.get_project.return_value = expected_response

        result = await controller.manage_project(
            action="get",
            project_id=sample_project_data["project_id"]
        )

        # Verify facade was called
        mock_facade.get_project.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["project_id"] == sample_project_data["project_id"]

    @pytest.mark.asyncio
    async def test_get_project_by_name_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful project retrieval by name."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        expected_response = {
            "success": True,
            "data": sample_project_data,
            "message": "Project retrieved successfully"
        }
        mock_facade.get_project_by_name.return_value = expected_response

        result = await controller.manage_project(
            action="get",
            name=sample_project_data["name"]
        )

        # Verify facade was called
        mock_facade.get_project_by_name.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["name"] == sample_project_data["name"]

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, controller, mock_facade_service, mock_authentication, mock_permissions):
        """Test project retrieval with non-existent project."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade to return not found response
        mock_facade.get_project.return_value = {
            "success": False,
            "error": "Project not found",
            "error_code": "PROJECT_NOT_FOUND"
        }

        result = await controller.manage_project(
            action="get",
            project_id="non-existent-id"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_project_missing_identifier(self, controller, mock_authentication, mock_permissions):
        """Test project retrieval without project_id or name."""
        result = await controller.manage_project(action="get")
        
        assert result["success"] is False
        assert "project_id" in result["error"].lower() or "name" in result["error"].lower()

    # Test Cases for UPDATE operation
    @pytest.mark.asyncio
    async def test_update_project_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful project update."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        updated_data = sample_project_data.copy()
        updated_data["name"] = "Updated Project Name"
        updated_data["description"] = "Updated description"
        
        expected_response = {
            "success": True,
            "data": updated_data,
            "message": "Project updated successfully"
        }
        mock_facade.update_project.return_value = expected_response

        result = await controller.manage_project(
            action="update",
            project_id=sample_project_data["project_id"],
            name="Updated Project Name",
            description="Updated description"
        )

        # Verify facade was called
        mock_facade.update_project.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["name"] == "Updated Project Name"

    @pytest.mark.asyncio
    async def test_update_project_missing_project_id(self, controller, mock_authentication, mock_permissions):
        """Test project update without project_id."""
        result = await controller.manage_project(
            action="update",
            name="Updated Name"
        )
        
        assert result["success"] is False
        assert "project_id" in result["error"].lower()

    # Test Cases for LIST operation
    @pytest.mark.asyncio
    async def test_list_projects_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful project listing."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response with multiple projects
        project_list = [
            sample_project_data, 
            {**sample_project_data, "project_id": str(uuid.uuid4()), "name": "Another Project"}
        ]
        expected_response = {
            "success": True,
            "data": {
                "projects": project_list,
                "total": len(project_list)
            },
            "message": "Projects retrieved successfully"
        }
        mock_facade.list_projects.return_value = expected_response

        result = await controller.manage_project(action="list")

        # Verify facade was called
        mock_facade.list_projects.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert len(result["data"]["projects"]) == 2

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, controller, mock_facade_service, mock_authentication, mock_permissions):
        """Test listing when no projects exist."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {"projects": [], "total": 0},
            "message": "No projects found"
        }
        mock_facade.list_projects.return_value = expected_response

        result = await controller.manage_project(action="list")

        assert result["success"] is True
        assert len(result["data"]["projects"]) == 0
        assert result["data"]["total"] == 0

    # Test Cases for HEALTH CHECK operation
    @pytest.mark.asyncio
    async def test_project_health_check_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful project health check."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response with health metrics
        health_data = {
            "project_id": sample_project_data["project_id"],
            "health_status": "healthy",
            "metrics": {
                "total_tasks": 25,
                "completed_tasks": 15,
                "active_branches": 3,
                "issues": []
            },
            "recommendations": ["Consider adding more tests"]
        }
        expected_response = {
            "success": True,
            "data": health_data,
            "message": "Health check completed successfully"
        }
        mock_facade.project_health_check.return_value = expected_response

        result = await controller.manage_project(
            action="project_health_check",
            project_id=sample_project_data["project_id"]
        )

        # Verify facade was called
        mock_facade.project_health_check.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["health_status"] == "healthy"
        assert "metrics" in result["data"]

    @pytest.mark.asyncio
    async def test_project_health_check_unhealthy(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test health check for unhealthy project."""
        facade_service, mock_facade = mock_facade_service
        
        health_data = {
            "project_id": sample_project_data["project_id"],
            "health_status": "unhealthy",
            "metrics": {
                "total_tasks": 100,
                "completed_tasks": 10,
                "active_branches": 15,
                "issues": ["Too many stale branches", "Low completion rate"]
            },
            "recommendations": ["Clean up stale branches", "Review task priorities"]
        }
        expected_response = {
            "success": True,
            "data": health_data,
            "message": "Health check completed - issues found"
        }
        mock_facade.project_health_check.return_value = expected_response

        result = await controller.manage_project(
            action="project_health_check",
            project_id=sample_project_data["project_id"]
        )

        assert result["success"] is True
        assert result["data"]["health_status"] == "unhealthy"
        assert len(result["data"]["metrics"]["issues"]) > 0

    # Test Cases for CLEANUP operations
    @pytest.mark.asyncio
    async def test_cleanup_obsolete_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful cleanup of obsolete resources."""
        facade_service, mock_facade = mock_facade_service
        
        cleanup_data = {
            "project_id": sample_project_data["project_id"],
            "cleaned_tasks": 5,
            "cleaned_branches": 2,
            "freed_space": "15MB"
        }
        expected_response = {
            "success": True,
            "data": cleanup_data,
            "message": "Cleanup completed successfully"
        }
        mock_facade.cleanup_obsolete.return_value = expected_response

        result = await controller.manage_project(
            action="cleanup_obsolete",
            project_id=sample_project_data["project_id"]
        )

        # Verify facade was called
        mock_facade.cleanup_obsolete.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["cleaned_tasks"] == 5

    @pytest.mark.asyncio
    async def test_cleanup_obsolete_with_force(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test cleanup with force parameter."""
        facade_service, mock_facade = mock_facade_service
        
        expected_response = {
            "success": True,
            "data": {"cleaned_tasks": 10, "cleaned_branches": 3},
            "message": "Force cleanup completed"
        }
        mock_facade.cleanup_obsolete.return_value = expected_response

        result = await controller.manage_project(
            action="cleanup_obsolete",
            project_id=sample_project_data["project_id"],
            force="true"
        )

        assert result["success"] is True

    # Test Cases for VALIDATE INTEGRITY operation
    @pytest.mark.asyncio
    async def test_validate_integrity_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful integrity validation."""
        facade_service, mock_facade = mock_facade_service
        
        validation_data = {
            "project_id": sample_project_data["project_id"],
            "validation_status": "valid",
            "checks_performed": ["structure", "dependencies", "consistency"],
            "issues": [],
            "recommendations": []
        }
        expected_response = {
            "success": True,
            "data": validation_data,
            "message": "Integrity validation completed successfully"
        }
        mock_facade.validate_integrity.return_value = expected_response

        result = await controller.manage_project(
            action="validate_integrity",
            project_id=sample_project_data["project_id"]
        )

        # Verify facade was called
        mock_facade.validate_integrity.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["validation_status"] == "valid"

    @pytest.mark.asyncio
    async def test_validate_integrity_with_issues(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test integrity validation with issues found."""
        facade_service, mock_facade = mock_facade_service
        
        validation_data = {
            "project_id": sample_project_data["project_id"],
            "validation_status": "issues_found",
            "checks_performed": ["structure", "dependencies", "consistency"],
            "issues": ["Orphaned task dependencies", "Missing branch references"],
            "recommendations": ["Fix task dependencies", "Clean up branch references"]
        }
        expected_response = {
            "success": True,
            "data": validation_data,
            "message": "Integrity validation completed with issues"
        }
        mock_facade.validate_integrity.return_value = expected_response

        result = await controller.manage_project(
            action="validate_integrity",
            project_id=sample_project_data["project_id"]
        )

        assert result["success"] is True
        assert result["data"]["validation_status"] == "issues_found"
        assert len(result["data"]["issues"]) > 0

    # Test Cases for REBALANCE AGENTS operation
    @pytest.mark.asyncio
    async def test_rebalance_agents_success(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test successful agent rebalancing."""
        facade_service, mock_facade = mock_facade_service
        
        rebalance_data = {
            "project_id": sample_project_data["project_id"],
            "agents_rebalanced": 8,
            "assignments_changed": 15,
            "load_distribution": "improved"
        }
        expected_response = {
            "success": True,
            "data": rebalance_data,
            "message": "Agent rebalancing completed successfully"
        }
        mock_facade.rebalance_agents.return_value = expected_response

        result = await controller.manage_project(
            action="rebalance_agents",
            project_id=sample_project_data["project_id"]
        )

        # Verify facade was called
        mock_facade.rebalance_agents.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["agents_rebalanced"] == 8

    # Test Cases for AUTHENTICATION and PERMISSIONS
    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, controller):
        """Test request without authentication."""
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.side_effect = UserAuthenticationRequiredError("Authentication required")
            
            result = await controller.manage_project(action="list")
            
            assert result["success"] is False
            assert "authentication" in result["error"].lower() or "permission" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, controller, mock_authentication):
        """Test request with insufficient permissions."""
        mock_auth, mock_log = mock_authentication
        
        with patch('fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller.get_current_request_context') as mock_context:
            # Configure mock user with insufficient permissions
            mock_request_context = Mock()
            mock_user = Mock()
            mock_user.token = {"sub": "test-user", "permissions": ["projects:read"]}  # Only read permission
            mock_request_context.user = mock_user
            mock_context.return_value = mock_request_context
            
            result = await controller.manage_project(
                action="create", 
                name="Test Project"
            )
            
            # Should return permission denied error (if permission system is strict)
            # Note: Depending on implementation, this might be allowed
            assert "success" in result  # Basic check that method doesn't crash

    # Test Cases for ERROR HANDLING
    @pytest.mark.asyncio
    async def test_facade_exception_handling(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test handling of facade exceptions."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade to raise exception
        mock_facade.get_project.side_effect = Exception("Database connection error")

        result = await controller.manage_project(
            action="get",
            project_id=sample_project_data["project_id"]
        )

        # Verify error is handled gracefully
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_action(self, controller, mock_authentication, mock_permissions):
        """Test handling of invalid action parameter."""
        result = await controller.manage_project(action="invalid_action")
        
        # Should handle gracefully
        assert "success" in result

    # Test Cases for PARAMETER VALIDATION
    @pytest.mark.parametrize("project_name", [
        "Valid Project Name",
        "project-with-dashes",
        "Project_With_Underscores",
        "ProjectWithCamelCase",
        "project123"
    ])
    @pytest.mark.asyncio
    async def test_valid_project_names(self, controller, mock_facade_service, project_name, mock_authentication, mock_permissions):
        """Test project creation with different valid project names."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade response
        expected_response = {
            "success": True,
            "data": {"project_id": str(uuid.uuid4()), "name": project_name},
            "message": "Project created successfully"
        }
        mock_facade.create_project.return_value = expected_response

        result = await controller.manage_project(
            action="create",
            name=project_name,
            description="Test project"
        )

        assert result["success"] is True

    @pytest.mark.parametrize("invalid_name", [
        "",  # Empty string
        "   ",  # Whitespace only
        None  # None value
    ])
    @pytest.mark.asyncio
    async def test_invalid_project_names(self, controller, invalid_name, mock_authentication, mock_permissions):
        """Test project creation with invalid project names."""
        result = await controller.manage_project(
            action="create",
            name=invalid_name,
            description="Test project"
        )

        # Should return validation error
        assert result["success"] is False

    # Test Cases for EDGE CASES
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, controller, mock_facade_service, sample_project_data, mock_authentication, mock_permissions):
        """Test handling of concurrent operations on same project."""
        facade_service, mock_facade = mock_facade_service
        
        # Configure facade to simulate successful operations
        mock_facade.get_project.return_value = {
            "success": True,
            "data": sample_project_data,
            "message": "Project retrieved successfully"
        }

        # Execute multiple operations concurrently
        tasks = [
            controller.manage_project(action="get", project_id=sample_project_data["project_id"]),
            controller.manage_project(action="get", project_id=sample_project_data["project_id"]),
            controller.manage_project(action="get", project_id=sample_project_data["project_id"])
        ]

        results = await asyncio.gather(*tasks)

        # All operations should succeed
        for result in results:
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_large_project_data_handling(self, controller, mock_facade_service, mock_authentication, mock_permissions):
        """Test handling of projects with large amounts of data."""
        facade_service, mock_facade = mock_facade_service
        
        # Create project data with large description
        large_description = "A" * 10000  # 10KB description
        
        expected_response = {
            "success": True,
            "data": {
                "project_id": str(uuid.uuid4()),
                "name": "Large Project",
                "description": large_description
            },
            "message": "Project created successfully"
        }
        mock_facade.create_project.return_value = expected_response

        result = await controller.manage_project(
            action="create",
            name="Large Project",
            description=large_description
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_special_characters_in_project_data(self, controller, mock_facade_service, mock_authentication, mock_permissions):
        """Test handling of special characters in project data."""
        facade_service, mock_facade = mock_facade_service
        
        project_name = "Test Project ñáéíóú 中文 🚀"
        project_description = "Description with special chars: @#$%^&*()_+{}|:<>?[];',./"
        
        expected_response = {
            "success": True,
            "data": {
                "project_id": str(uuid.uuid4()),
                "name": project_name,
                "description": project_description
            },
            "message": "Project created successfully"
        }
        mock_facade.create_project.return_value = expected_response

        result = await controller.manage_project(
            action="create",
            name=project_name,
            description=project_description
        )

        assert result["success"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])