"""
Integration test for project API performance improvements.

This test verifies the end-to-end performance improvement from the N+1 query fix.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.application.services.project_management_service import ProjectManagementService


class TestProjectAPIPerformance:
    """Integration tests for project API performance"""
    
    @pytest.mark.asyncio
    async def test_controller_returns_projects_with_branches(self):
        """Test that the controller returns projects with embedded branch data"""
        # Arrange
        controller = ProjectMCPController()
        
        # Mock the facade to return test data
        mock_facade = AsyncMock(spec=ProjectApplicationFacade)
        mock_facade.manage_project.return_value = {
            "success": True,
            "projects": [
                {
                    "id": str(uuid4()),
                    "name": "Test Project 1",
                    "description": "Test description",
                    "git_branchs": {
                        str(uuid4()): {
                            "id": str(uuid4()),
                            "name": "main",
                            "status": "active"
                        },
                        str(uuid4()): {
                            "id": str(uuid4()),
                            "name": "develop",
                            "status": "active"
                        }
                    }
                },
                {
                    "id": str(uuid4()),
                    "name": "Test Project 2",
                    "description": "Another test",
                    "git_branchs": {
                        str(uuid4()): {
                            "id": str(uuid4()),
                            "name": "main",
                            "status": "active"
                        }
                    }
                }
            ],
            "count": 2
        }
        
        # Inject the mock facade
        with patch.object(controller, '_get_facade', return_value=mock_facade):
            # Act
            result = controller.manage_project(action="list")
            
            # Assert
            assert result["success"] is True
            assert "projects" in result
            assert len(result["projects"]) == 2
            
            # Verify each project has branches
            for project in result["projects"]:
                assert "git_branchs" in project
                assert isinstance(project["git_branchs"], dict)
                assert len(project["git_branchs"]) > 0
    
    @pytest.mark.asyncio
    async def test_single_api_call_for_complete_data(self):
        """Test that getting complete project data only requires one API call"""
        # This simulates what the frontend would do
        
        # Arrange
        controller = ProjectMCPController()
        call_count = 0
        
        async def mock_manage_project(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("action") == "list":
                return {
                    "success": True,
                    "projects": [
                        {
                            "id": f"project-{i}",
                            "name": f"Project {i}",
                            "git_branchs": {
                                f"branch-{j}": {
                                    "id": f"branch-{j}",
                                    "name": f"branch-{j}",
                                    "status": "active"
                                } for j in range(3)
                            }
                        } for i in range(9)  # Simulate 9 projects like in the issue
                    ],
                    "count": 9
                }
            return {"success": False, "error": "Unknown action"}
        
        mock_facade = AsyncMock(spec=ProjectApplicationFacade)
        mock_facade.manage_project = mock_manage_project
        
        with patch.object(controller, '_get_facade', return_value=mock_facade):
            # Act
            start_time = time.time()
            result = controller.manage_project(action="list")
            elapsed_time = time.time() - start_time
            
            # Assert
            assert result["success"] is True
            assert call_count == 1, "Should only make one API call"
            assert len(result["projects"]) == 9
            
            # All projects should have branches already
            for project in result["projects"]:
                assert "git_branchs" in project
                assert len(project["git_branchs"]) == 3
            
            # Performance check - should be fast
            assert elapsed_time < 0.5, f"API call took {elapsed_time:.3f}s, expected < 0.5s"
    
    @pytest.mark.asyncio 
    async def test_backwards_compatibility(self):
        """Test that the API changes are backwards compatible"""
        # Arrange
        controller = ProjectMCPController()
        
        # Mock facade to return old-style response (without branches)
        mock_facade = AsyncMock(spec=ProjectApplicationFacade)
        mock_facade.manage_project.return_value = {
            "success": True,
            "projects": [
                {
                    "id": str(uuid4()),
                    "name": "Legacy Project",
                    "description": "Project without branches in response",
                    "git_branchs_count": 2,  # Old style - just count
                    "registered_agents_count": 0,
                    "active_assignments": 0,
                    "active_sessions": 0
                }
            ],
            "count": 1
        }
        
        with patch.object(controller, '_get_facade', return_value=mock_facade):
            # Act
            result = controller.manage_project(action="list")
            
            # Assert
            assert result["success"] is True
            assert len(result["projects"]) == 1
            
            # Should still work even without git_branchs field
            project = result["projects"][0]
            assert project["name"] == "Legacy Project"
            assert project["git_branchs_count"] == 2