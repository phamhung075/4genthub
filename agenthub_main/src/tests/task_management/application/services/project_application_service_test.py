"""Test suite for ProjectApplicationService following DDD patterns"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.agent import Agent
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.value_objects.agent_roles import AgentRole


@pytest.fixture
def mock_repository():
    """Create a mock project repository"""
    repository = Mock(spec=ProjectRepository)
    repository.find_by_id = AsyncMock()
    repository.find_all = AsyncMock()
    repository.update = AsyncMock()
    repository.save = AsyncMock()
    return repository


@pytest.fixture
def mock_project():
    """Create a mock project with necessary attributes"""
    project = Mock(spec=Project)
    project.id = "test-project-id"
    project.name = "Test Project"
    project.description = "Test Description"
    project.registered_agents = {}
    project.agent_assignments = {}
    project.active_work_sessions = {}
    project.resource_locks = {}
    project.git_branchs = {}
    project.register_agent = Mock()
    project.assign_agent_to_tree = Mock()
    return project


@pytest.fixture
def service_with_user(mock_repository):
    """Create service instance with user context"""
    return ProjectApplicationService(mock_repository, user_id="test-user-123")


@pytest.fixture
def service_without_user(mock_repository):
    """Create service instance without user context"""
    return ProjectApplicationService(mock_repository)


class TestProjectApplicationService:
    """Test cases for ProjectApplicationService"""
    
    async def test_init_with_user_scoped_repository(self):
        """Test service initialization with user-scoped repository"""
        # Arrange
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.with_user = Mock(return_value=mock_repo)
        
        # Act
        service = ProjectApplicationService(mock_repo, user_id="test-user-123")
        
        # Assert
        assert service._user_id == "test-user-123"
        mock_repo.with_user.assert_called_with("test-user-123")
    
    async def test_init_with_repository_user_id_property(self):
        """Test service initialization when repository has user_id property"""
        # Arrange
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.user_id = "old-user"
        mock_repo.session = Mock()
        
        # Act
        service = ProjectApplicationService(mock_repo, user_id="new-user")
        
        # Assert
        assert service._user_id == "new-user"
    
    async def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository when with_user method exists"""
        # Arrange
        mock_repo = Mock(spec=ProjectRepository)
        scoped_repo = Mock(spec=ProjectRepository)
        mock_repo.with_user = Mock(return_value=scoped_repo)
        service = ProjectApplicationService(mock_repo, user_id="test-user")
        
        # Act
        result = service._get_user_scoped_repository()
        
        # Assert
        assert result == scoped_repo
        mock_repo.with_user.assert_called_with("test-user")
    
    async def test_get_user_scoped_repository_without_user_id(self):
        """Test getting repository when no user_id is set"""
        # Arrange
        mock_repo = Mock(spec=ProjectRepository)
        service = ProjectApplicationService(mock_repo)
        
        # Act
        result = service._get_user_scoped_repository()
        
        # Assert
        assert result == mock_repo
    
    async def test_with_user_creates_new_instance(self):
        """Test with_user method creates new service instance"""
        # Arrange
        mock_repo = Mock(spec=ProjectRepository)
        service = ProjectApplicationService(mock_repo)
        
        # Act
        new_service = service.with_user("new-user-id")
        
        # Assert
        assert isinstance(new_service, ProjectApplicationService)
        assert new_service._user_id == "new-user-id"
        assert new_service != service
    
    async def test_create_project(self, service_with_user):
        """Test create_project delegates to use case"""
        # Arrange
        expected_result = {"success": True, "project": {"id": "proj-123"}}
        service_with_user._create_project_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.create_project("proj-123", "Test Project", "Description")
        
        # Assert
        service_with_user._create_project_use_case.execute.assert_called_once_with(
            "proj-123", "Test Project", "Description"
        )
        assert result == expected_result
    
    async def test_get_project(self, service_with_user):
        """Test get_project delegates to use case"""
        # Arrange
        expected_result = {"success": True, "project": {"id": "proj-123"}}
        service_with_user._get_project_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.get_project("proj-123")
        
        # Assert
        service_with_user._get_project_use_case.execute.assert_called_once_with("proj-123")
        assert result == expected_result
    
    async def test_list_projects(self, service_with_user):
        """Test list_projects delegates to use case"""
        # Arrange
        expected_result = {"success": True, "projects": []}
        service_with_user._list_projects_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.list_projects()
        
        # Assert
        service_with_user._list_projects_use_case.execute.assert_called_once()
        assert result == expected_result
    
    async def test_update_project(self, service_with_user):
        """Test update_project delegates to use case"""
        # Arrange
        expected_result = {"success": True}
        service_with_user._update_project_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.update_project("proj-123", "New Name", "New Description")
        
        # Assert
        service_with_user._update_project_use_case.execute.assert_called_once_with(
            "proj-123", "New Name", "New Description"
        )
        assert result == expected_result
    
    async def test_create_git_branch(self, service_with_user):
        """Test create_git_branch delegates to use case"""
        # Arrange
        expected_result = {"success": True, "git_branch": {"id": "branch-123"}}
        service_with_user._create_git_branch_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.create_git_branch(
            "proj-123", "feature/test", "Test Branch", "Branch description"
        )
        
        # Assert
        service_with_user._create_git_branch_use_case.execute.assert_called_once_with(
            "proj-123", "feature/test", "Test Branch", "Branch description"
        )
        assert result == expected_result
    
    async def test_project_health_check(self, service_with_user):
        """Test project_health_check delegates to use case"""
        # Arrange
        expected_result = {"success": True, "health": "good"}
        service_with_user._project_health_check_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service_with_user.project_health_check("proj-123")
        
        # Assert
        service_with_user._project_health_check_use_case.execute.assert_called_once_with("proj-123")
        assert result == expected_result
    
    async def test_register_agent_success(self, service_with_user, mock_repository, mock_project):
        """Test successful agent registration"""
        # Arrange
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.register_agent(
            "proj-123", "agent-123", "Test Agent", ["task_planning", "code_review"]
        )
        
        # Assert
        mock_repository.find_by_id.assert_called_once_with("proj-123")
        mock_project.register_agent.assert_called_once()
        mock_repository.update.assert_called_once_with(mock_project)
        
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert result["agent"]["name"] == "Test Agent"
        assert "message" in result
    
    async def test_register_agent_project_not_found(self, service_with_user, mock_repository):
        """Test agent registration when project not found"""
        # Arrange
        mock_repository.find_by_id.return_value = None
        
        # Act
        result = await service_with_user.register_agent(
            "proj-123", "agent-123", "Test Agent"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    async def test_register_agent_with_invalid_capabilities(self, service_with_user, mock_repository, mock_project):
        """Test agent registration with invalid capabilities"""
        # Arrange
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.register_agent(
            "proj-123", "agent-123", "Test Agent", ["invalid_capability"]
        )
        
        # Assert
        # Should still succeed but skip invalid capabilities
        assert result["success"] is True
        mock_project.register_agent.assert_called_once()
    
    async def test_register_agent_value_error(self, service_with_user, mock_repository, mock_project):
        """Test agent registration when ValueError is raised"""
        # Arrange
        mock_repository.find_by_id.return_value = mock_project
        mock_project.register_agent.side_effect = ValueError("Agent already exists")
        
        # Act
        result = await service_with_user.register_agent(
            "proj-123", "agent-123", "Test Agent"
        )
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "Agent already exists"
    
    async def test_assign_agent_to_tree_success(self, service_with_user, mock_repository, mock_project):
        """Test successful agent assignment to tree"""
        # Arrange
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.assign_agent_to_tree(
            "proj-123", "agent-123", "branch-123"
        )
        
        # Assert
        mock_repository.find_by_id.assert_called_once_with("proj-123")
        mock_project.assign_agent_to_tree.assert_called_once_with("agent-123", "branch-123")
        mock_repository.update.assert_called_once_with(mock_project)
        
        assert result["success"] is True
        assert "message" in result
    
    async def test_assign_agent_to_tree_project_not_found(self, service_with_user, mock_repository):
        """Test agent assignment when project not found"""
        # Arrange
        mock_repository.find_by_id.return_value = None
        
        # Act
        result = await service_with_user.assign_agent_to_tree(
            "proj-123", "agent-123", "branch-123"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    async def test_assign_agent_to_tree_value_error(self, service_with_user, mock_repository, mock_project):
        """Test agent assignment when ValueError is raised"""
        # Arrange
        mock_repository.find_by_id.return_value = mock_project
        mock_project.assign_agent_to_tree.side_effect = ValueError("Agent not registered")
        
        # Act
        result = await service_with_user.assign_agent_to_tree(
            "proj-123", "agent-123", "branch-123"
        )
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "Agent not registered"
    
    async def test_unregister_agent_success(self, service_with_user, mock_repository, mock_project):
        """Test successful agent unregistration"""
        # Arrange
        mock_agent = Mock(spec=Agent)
        mock_agent.id = "agent-123"
        mock_agent.name = "Test Agent"
        mock_agent.capabilities = {AgentRole.TASK_PLANNING}
        
        mock_project.registered_agents = {"agent-123": mock_agent}
        mock_project.agent_assignments = {"branch-123": "agent-123", "branch-456": "other-agent"}
        
        mock_session = Mock(spec=WorkSession)
        mock_session.agent_id = "agent-123"
        mock_project.active_work_sessions = {"session-123": mock_session}
        
        mock_project.resource_locks = {"resource-123": "agent-123"}
        
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.unregister_agent("proj-123", "agent-123")
        
        # Assert
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert result["removed_sessions"] == 1
        assert result["unlocked_resources"] == 1
        assert "agent-123" not in mock_project.registered_agents
        assert "branch-123" not in mock_project.agent_assignments
        assert "session-123" not in mock_project.active_work_sessions
        assert "resource-123" not in mock_project.resource_locks
    
    async def test_unregister_agent_not_found(self, service_with_user, mock_repository, mock_project):
        """Test agent unregistration when agent not found"""
        # Arrange
        mock_project.registered_agents = {}
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.unregister_agent("proj-123", "agent-123")
        
        # Assert
        assert result["success"] is False
        assert "not found in project" in result["error"]
    
    async def test_cleanup_obsolete_single_project(self, service_with_user, mock_repository, mock_project):
        """Test cleanup obsolete data for single project"""
        # Arrange
        mock_project.git_branchs = {"branch-123": Mock()}
        mock_project.registered_agents = {"agent-123": Mock()}
        mock_project.agent_assignments = {"non-existent-branch": "agent-123"}
        
        mock_repository.find_by_id.return_value = mock_project
        
        # Act
        result = await service_with_user.cleanup_obsolete("proj-123")
        
        # Assert
        assert result["success"] is True
        assert result["project_id"] == "proj-123"
        assert len(result["cleaned_items"]) > 0
        mock_repository.update.assert_called_once()
    
    async def test_cleanup_obsolete_all_projects(self, service_with_user, mock_repository):
        """Test cleanup obsolete data for all projects"""
        # Arrange
        mock_project1 = Mock(spec=Project)
        mock_project1.id = "proj-1"
        mock_project1.git_branchs = {}
        mock_project1.registered_agents = {}
        mock_project1.agent_assignments = {"branch-123": "non-existent-agent"}
        mock_project1.active_work_sessions = {}
        mock_project1.resource_locks = {}
        
        mock_project2 = Mock(spec=Project)
        mock_project2.id = "proj-2"
        mock_project2.git_branchs = {}
        mock_project2.registered_agents = {"agent-123": Mock()}
        mock_project2.agent_assignments = {}
        mock_project2.active_work_sessions = {}
        mock_project2.resource_locks = {"resource-123": "non-existent-agent"}
        
        mock_repository.find_all.return_value = [mock_project1, mock_project2]
        
        # Act
        result = await service_with_user.cleanup_obsolete()
        
        # Assert
        assert result["success"] is True
        assert result["total_cleaned"] > 0
        assert "proj-1" in result["cleanup_results"]
        assert "proj-2" in result["cleanup_results"]
    
    async def test_cleanup_obsolete_project_not_found(self, service_with_user, mock_repository):
        """Test cleanup obsolete when project not found"""
        # Arrange
        mock_repository.find_by_id.return_value = None
        
        # Act
        result = await service_with_user.cleanup_obsolete("proj-123")
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_cleanup_project_data_removes_orphaned_assignments(self, service_with_user, mock_project):
        """Test cleanup removes assignments to non-existent trees"""
        # Arrange
        mock_project.git_branchs = {"branch-123": Mock()}
        mock_project.registered_agents = {"agent-123": Mock()}
        mock_project.agent_assignments = {
            "branch-123": "agent-123",
            "non-existent-branch": "agent-123"
        }
        
        # Act
        cleaned = service_with_user._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned) == 1
        assert "non-existent-branch" in cleaned[0]
        assert "non-existent-branch" not in mock_project.agent_assignments
    
    def test_cleanup_project_data_removes_orphaned_sessions(self, service_with_user, mock_project):
        """Test cleanup removes sessions for unregistered agents"""
        # Arrange
        mock_session = Mock()
        mock_session.agent_id = "non-existent-agent"
        mock_project.active_work_sessions = {"session-123": mock_session}
        mock_project.registered_agents = {}
        
        # Act
        cleaned = service_with_user._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned) == 1
        assert "session-123" in cleaned[0]
        assert "session-123" not in mock_project.active_work_sessions
    
    def test_cleanup_project_data_removes_orphaned_locks(self, service_with_user, mock_project):
        """Test cleanup removes resource locks for unregistered agents"""
        # Arrange
        mock_project.resource_locks = {"resource-123": "non-existent-agent"}
        mock_project.registered_agents = {}
        
        # Act
        cleaned = service_with_user._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned) == 1
        assert "resource-123" in cleaned[0]
        assert "resource-123" not in mock_project.resource_locks
    
    def test_cleanup_project_data_no_cleanup_needed(self, service_with_user, mock_project):
        """Test cleanup when no data needs cleaning"""
        # Arrange
        mock_project.git_branchs = {"branch-123": Mock()}
        mock_project.registered_agents = {"agent-123": Mock()}
        mock_project.agent_assignments = {"branch-123": "agent-123"}
        mock_project.active_work_sessions = {}
        mock_project.resource_locks = {}
        
        # Act
        cleaned = service_with_user._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned) == 0