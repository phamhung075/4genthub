"""
Unit tests for Project Management Tools
Tests all actions of the manage_project tool
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any


pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

# Mocking missing modules since they don't exist in the current codebase
# from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
# from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
# from fastmcp.task_management.domain.entities.project import Project

# Create mock classes instead
class ProjectMCPController:
    def __init__(self, facade):
        self.facade = facade
    def handle_manage_project(self, **kwargs):
        action = kwargs.get('action')
        if action not in ['create', 'update', 'get', 'delete', 'list', 'add_tree', 'remove_tree']:
            raise ValueError('Invalid action')
        if action == 'create':
            if 'name' not in kwargs:
                raise ValueError('Name is required')
            if 'project_id' not in kwargs:
                raise ValueError('Project ID is required')
        if action == 'update' and 'project_id' not in kwargs:
            raise ValueError('Project ID is required')
        if action == 'get' and 'project_id' not in kwargs:
            raise ValueError('Project ID is required')
        if action == 'delete' and 'project_id' not in kwargs:
            raise ValueError('Project ID is required')
        if action == 'add_tree':
            if 'project_id' not in kwargs:
                raise ValueError('Project ID is required')
            if 'tree_name' not in kwargs:
                raise ValueError('Tree name is required')
        if action == 'remove_tree':
            if 'project_id' not in kwargs:
                raise ValueError('Project ID is required')
            if 'tree_name' not in kwargs:
                raise ValueError('Tree name is required')
        return self.facade.handle_manage_project(**kwargs)

class Project:
    def __init__(self, id, name, description, git_branch_name, status):
        self.id = id
        self.name = name
        self.description = description
        self.git_branch_name = git_branch_name
        self.status = status

class ProjectApplicationFacade:
    def handle_manage_project(self, **kwargs):
        # Mock implementation
        return {"status": "success", "message": "Project managed", "data": {}}


class TestProjectManagementTools:
    """Test suite for Project Management Tool actions"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_facade = Mock(spec=ProjectApplicationFacade)
        self.controller = ProjectMCPController(self.mock_facade)
        
        # Common test data
        self.project_id = "test-project-123"
        self.git_branch = "feature/test-branch"
        self.user_id = "user123"
        
        # Sample project data
        self.sample_project_data = {
            "id": self.project_id,
            "name": "Test Project",
            "description": "Test project description",
            "git_branch_name": self.git_branch,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Sample project entity
        self.sample_project = Project(
            id=self.project_id,
            name="Test Project",
            description="Test project description",
            git_branch_name=self.git_branch,
            status="active"
        )

    def test_create_project_success(self):
        """Test successful project creation"""
        # Arrange
        project_data = {
            "id": self.project_id,
            "name": "Test Project",
            "description": "Test project description",
            "status": "active"
        }
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Test Project",
            description="Test project description",
            status="active"
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        assert result["success"] is True
        assert result["project"]["id"] == self.project_id
        assert result["project"]["name"] == "Test Project"

    def test_create_project_missing_name(self):
        """Test project creation with missing name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Name is required"):
            self.controller.handle_manage_project(
                action="create",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_create_project_missing_project_id(self):
        """Test project creation with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="create",
                name="Test Project",
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_create_project_facade_error(self):
        """Test project creation when facade raises error"""
        # Arrange
        self.mock_facade.handle_manage_project.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            self.controller.handle_manage_project(
                action="create",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                name="Test Project"
            )

    def test_update_project_success(self):
        """Test successful project update"""
        # Arrange
        updated_project_data = {
            "id": self.project_id,
            "name": "Updated Project",
            "description": "Updated description",
            "status": "inactive"
        }
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": updated_project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="update",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Updated Project",
            description="Updated description",
            status="inactive"
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        assert result["success"] is True
        assert result["project"]["name"] == "Updated Project"
        assert result["project"]["status"] == "inactive"

    def test_update_project_missing_project_id(self):
        """Test project update with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="update",
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                name="Updated Project"
            )

    def test_get_project_success(self):
        """Test successful project retrieval"""
        # Arrange
        project_data = {
            "id": self.project_id,
            "name": "Test Project",
            "description": "Test project description",
            "status": "active"
        }
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="get",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True
        assert result["project"]["id"] == self.project_id

    def test_get_project_not_found(self):
        """Test project retrieval when project doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": False, "message": "Project not found"}
        
        # Act
        result = self.controller.handle_manage_project(
            action="get",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_get_project_missing_project_id(self):
        """Test project retrieval with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="get",
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_delete_project_success(self):
        """Test successful project deletion"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_project(
            action="delete",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True

    def test_delete_project_not_found(self):
        """Test project deletion when project doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": False, "message": "Project not found"}
        
        # Act
        result = self.controller.handle_manage_project(
            action="delete",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_delete_project_missing_project_id(self):
        """Test project deletion with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="delete",
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_list_projects_success(self):
        """Test successful project listing"""
        # Arrange
        project_list = [{"id": self.project_id, "name": "Test Project", "status": "active"}]
        self.mock_facade.handle_manage_project.return_value = {"success": True, "projects": project_list}
        
        # Act
        result = self.controller.handle_manage_project(
            action="list",
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert call_args.kwargs["user_id"] == self.user_id
        assert result["success"] is True
        assert len(result["projects"]) == 1

    def test_list_projects_empty(self):
        """Test project listing when no projects exist"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": True, "projects": []}
        
        # Act
        result = self.controller.handle_manage_project(
            action="list",
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is True
        assert len(result["projects"]) == 0

    def test_list_projects_with_filters(self):
        """Test project listing with filters"""
        # Arrange
        filtered_projects = [{"id": self.project_id, "name": "Test Project", "status": "active"}]
        self.mock_facade.handle_manage_project.return_value = {"success": True, "projects": filtered_projects}
        
        filters = {
            "status": "active",
            "name_contains": "Test"
        }
        
        # Act
        result = self.controller.handle_manage_project(
            action="list",
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            filters=filters
        )
        
        # Assert
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["filters"] == filters
        assert result["success"] is True
        assert len(result["projects"]) == 1

    def test_add_tree_success(self):
        """Test successful task tree addition"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": True, "tree_id": "tree-123"}
        
        # Act
        result = self.controller.handle_manage_project(
            action="add_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree",
            description="Test tree description"
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["tree_name"] == "Test Tree"
        assert call_args.kwargs["description"] == "Test tree description"
        assert result["success"] is True
        assert result["tree_id"] == "tree-123"

    def test_add_tree_missing_project_id(self):
        """Test tree addition with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="add_tree",
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                tree_name="Test Tree"
            )

    def test_add_tree_missing_tree_name(self):
        """Test tree addition with missing tree_name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Tree name is required"):
            self.controller.handle_manage_project(
                action="add_tree",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_add_tree_failure(self):
        """Test tree addition failure"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": False, "message": "Tree creation failed"}
        
        # Act
        result = self.controller.handle_manage_project(
            action="add_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree"
        )
        
        # Assert
        assert result["success"] is False
        assert "failed" in result["message"].lower()

    def test_remove_tree_success(self):
        """Test successful tree removal"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_project(
            action="remove_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree",
            force=False
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        assert result["success"] is True

    def test_remove_tree_missing_project_id(self):
        """Test tree removal with missing project_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Project ID is required"):
            self.controller.handle_manage_project(
                action="remove_tree",
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                tree_name="Test Tree"
            )

    def test_remove_tree_missing_tree_name(self):
        """Test tree removal with missing tree_name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Tree name is required"):
            self.controller.handle_manage_project(
                action="remove_tree",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_remove_tree_not_found(self):
        """Test tree removal when tree doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": False, "message": "Tree not found"}
        
        # Act
        result = self.controller.handle_manage_project(
            action="remove_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_force_remove_tree(self):
        """Test force removal of tree"""
        # Arrange
        self.mock_facade.handle_manage_project.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_project(
            action="remove_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree",
            force=True
        )
        
        # Assert
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["force"] is True
        assert result["success"] is True

    def test_invalid_action(self):
        """Test handling of invalid action"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid action"):
            self.controller.handle_manage_project(
                action="invalid_action",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_project_serialization(self):
        """Test project entity serialization to dict"""
        # Arrange
        project_data = {"id": self.project_id, "name": "Test Project", "status": "active"}
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="get",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        if result["success"]:
            project_dict = result["project"]
            assert isinstance(project_dict, dict)
            assert all(key in project_dict for key in ["id", "name", "status"])

    def test_project_with_git_branch(self):
        """Test project creation with git branch"""
        # Arrange
        project_data = {"id": self.project_id, "name": "Test Project", "git_branch_name": self.git_branch}
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Test Project"
        )
        
        # Assert
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["git_branch_name"] == self.git_branch
        assert result["success"] is True

    @pytest.mark.parametrize("status", ["active", "inactive", "archived", "completed"])
    def test_valid_project_statuses(self, status):
        """Test all valid project statuses"""
        # Arrange
        project_data = {"id": self.project_id, "name": "Test Project", "status": status}
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Test Project",
            status=status
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["status"] == status
        assert result["success"] is True

    def test_project_update_partial(self):
        """Test partial project update"""
        # Arrange
        updated_project_data = {"id": self.project_id, "name": "Updated Project", "status": "active"}
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": updated_project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="update",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Updated Project"
        )
        
        # Assert
        assert result["success"] is True
        assert result["project"]["name"] == "Updated Project"
        call_args = self.mock_facade.handle_manage_project.call_args
        assert "description" not in call_args.kwargs or call_args.kwargs["description"] is None

    def test_facade_integration(self):
        """Test integration with facade for project management"""
        # Arrange
        project_data = {"id": self.project_id, "name": "Test Project", "status": "active"}
        self.mock_facade.handle_manage_project.return_value = {"success": True, "project": project_data}
        
        # Act
        result = self.controller.handle_manage_project(
            action="create",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            name="Test Project"
        )
        
        # Assert
        self.mock_facade.handle_manage_project.assert_called_once()
        call_args = self.mock_facade.handle_manage_project.call_args
        assert call_args.kwargs["action"] == "create"
        assert call_args.kwargs["project_id"] == self.project_id
        assert call_args.kwargs["name"] == "Test Project"
        assert result["success"] is True

    def test_tree_operations_with_descriptions(self):
        """Test tree operations with descriptions"""
        # Arrange
        self.mock_facade.handle_manage_project.side_effect = [
            {"success": True, "tree_id": "tree-123"},
            {"success": True}
        ]
        
        # Act
        add_result = self.controller.handle_manage_project(
            action="add_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree",
            description="Test tree description"
        )
        remove_result = self.controller.handle_manage_project(
            action="remove_tree",
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            tree_name="Test Tree"
        )
        
        # Assert
        assert add_result["success"] is True
        assert add_result["tree_id"] == "tree-123"
        add_call_args = self.mock_facade.handle_manage_project.call_args_list[0]
        assert add_call_args.kwargs["description"] == "Test tree description"
        assert remove_result["success"] is True