"""Unit tests for ProjectApplicationService."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, call
from datetime import datetime, timezone

from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.agent import Agent, AgentCapability, AgentStatus
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestProjectApplicationServiceInit:
    """Test ProjectApplicationService initialization."""
    
    def test_service_initialization(self):
        """Test service initializes with required dependencies."""
        # Arrange
        mock_repo = Mock()
        
        # Act
        service = ProjectApplicationService(project_repository=mock_repo)
        
        # Assert
        assert service._project_repository == mock_repo
        assert service._create_project_use_case is not None
        assert service._get_project_use_case is not None
        assert service._list_projects_use_case is not None
        assert service._update_project_use_case is not None
        assert service._create_git_branch_use_case is not None
        assert service._project_health_check_use_case is not None


class TestCreateProject:
    """Test create project functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._create_project_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case,
            "mock_repo": mock_repo
        }
    
    @pytest.mark.asyncio
    async def test_create_project_success(self, setup):
        """Test successful project creation."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        # Mock successful response
        mock_response = {
            "success": True,
            "project": {
                "id": "test-project",
                "name": "Test Project",
                "description": "Test Description"
            }
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.create_project(
            project_id="test-project",
            name="Test Project",
            description="Test Description"
        )
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(
            "test-project", "Test Project", "Test Description"
        )
    
    @pytest.mark.asyncio
    async def test_create_project_minimal(self, setup):
        """Test project creation with minimal parameters."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {"success": True}
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.create_project(
            project_id="test-project",
            name="Test Project"
        )
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(
            "test-project", "Test Project", ""
        )


class TestGetProject:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test get project functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._get_project_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case
        }
    
    @pytest.mark.asyncio
    async def test_get_project_success(self, setup):
        """Test successful project retrieval."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {
            "success": True,
            "project": {
                "id": "test-project",
                "name": "Test Project"
            }
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.get_project("test-project")
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("test-project")


class TestListProjects:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test list projects functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._list_projects_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case
        }
    
    @pytest.mark.asyncio
    async def test_list_projects(self, setup):
        """Test listing all projects."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {
            "success": True,
            "projects": [
                {"id": "project-1", "name": "Project 1"},
                {"id": "project-2", "name": "Project 2"}
            ]
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.list_projects()
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once()


class TestUpdateProject:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test update project functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._update_project_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case
        }
    
    @pytest.mark.asyncio
    async def test_update_project_full(self, setup):
        """Test updating project with all fields."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {"success": True}
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.update_project(
            project_id="test-project",
            name="Updated Name",
            description="Updated Description"
        )
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(
            "test-project", "Updated Name", "Updated Description"
        )
    
    @pytest.mark.asyncio
    async def test_update_project_partial(self, setup):
        """Test updating project with partial fields."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {"success": True}
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.update_project(
            project_id="test-project",
            name="Updated Name"
        )
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(
            "test-project", "Updated Name", None
        )


class TestCreateGitBranch:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test create task tree functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._create_git_branch_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case
        }
    
    @pytest.mark.asyncio
    async def test_create_git_branch(self, setup):
        """Test creating task tree in project."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {
            "success": True,
            "git_branch": {
                "name": "feature-branch",
                "description": "Feature branch tree"
            }
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.create_git_branch(
            project_id="test-project",
            git_branch_name="feature-branch",
            tree_name="Feature Branch",
            tree_description="Feature branch tree"
        )
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(
            "test-project", "feature-branch", "Feature Branch", "Feature branch tree"
        )


class TestProjectHealthCheck:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test project health check functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock the use case
        mock_use_case = AsyncMock()
        service._project_health_check_use_case = mock_use_case
        
        return {
            "service": service,
            "mock_use_case": mock_use_case
        }
    
    @pytest.mark.asyncio
    async def test_health_check_specific_project(self, setup):
        """Test health check for specific project."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {
            "success": True,
            "health_status": "healthy"
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.project_health_check("test-project")
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("test-project")
    
    @pytest.mark.asyncio
    async def test_health_check_all_projects(self, setup):
        """Test health check for all projects."""
        # Arrange
        service = setup["service"]
        mock_use_case = setup["mock_use_case"]
        
        mock_response = {
            "success": True,
            "projects_checked": 5
        }
        mock_use_case.execute.return_value = mock_response
        
        # Act
        result = await service.project_health_check()
        
        # Assert
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(None)


class TestRegisterAgent:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test register agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        return {
            "service": service,
            "mock_repo": mock_repo
        }
    
    @pytest.mark.asyncio
    async def test_register_agent_success(self, setup):
        """Test successful agent registration."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.registered_agents = {}
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.register_agent(
            project_id="test-project",
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["coding", "testing"]
        )
        
        # Assert
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-1"
        assert result["agent"]["name"] == "Test Agent"
        mock_project.register_agent.assert_called_once()
        mock_repo.update.assert_called_once_with(mock_project)
    
    @pytest.mark.asyncio
    async def test_register_agent_project_not_found(self, setup):
        """Test agent registration when project not found."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        mock_repo.find_by_id.return_value = None
        
        # Act
        result = await service.register_agent(
            project_id="non-existent",
            agent_id="agent-1",
            name="Test Agent"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_register_agent_duplicate(self, setup):
        """Test registering duplicate agent."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.register_agent.side_effect = ValueError("Agent already exists")
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.register_agent(
            project_id="test-project",
            agent_id="agent-1",
            name="Test Agent"
        )
        
        # Assert
        assert result["success"] is False
        assert "already exists" in result["error"]


class TestAssignAgentToTree:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test assign agent to tree functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        return {
            "service": service,
            "mock_repo": mock_repo
        }
    
    @pytest.mark.asyncio
    async def test_assign_agent_success(self, setup):
        """Test successful agent assignment to tree."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.assign_agent_to_tree(
            project_id="test-project",
            agent_id="agent-1",
            git_branch_name="feature-branch"
        )
        
        # Assert
        assert result["success"] is True
        mock_project.assign_agent_to_tree.assert_called_once_with(
            "agent-1", "feature-branch"
        )
        mock_repo.update.assert_called_once_with(mock_project)
    
    @pytest.mark.asyncio
    async def test_assign_agent_project_not_found(self, setup):
        """Test agent assignment when project not found."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        mock_repo.find_by_id.return_value = None
        
        # Act
        result = await service.assign_agent_to_tree(
            project_id="non-existent",
            agent_id="agent-1",
            git_branch_name="feature"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_assign_agent_invalid_tree(self, setup):
        """Test agent assignment to invalid tree."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.assign_agent_to_tree.side_effect = ValueError("Tree not found")
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.assign_agent_to_tree(
            project_id="test-project",
            agent_id="agent-1",
            git_branch_name="non-existent"
        )
        
        # Assert
        assert result["success"] is False
        assert "Tree not found" in result["error"]


class TestUnregisterAgent:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test unregister agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        return {
            "service": service,
            "mock_repo": mock_repo
        }
    
    @pytest.mark.asyncio
    async def test_unregister_agent_success(self, setup):
        """Test successful agent unregistration."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock agent
        mock_agent = Mock()
        mock_agent.id = "agent-1"
        mock_agent.name = "Test Agent"
        mock_agent.capabilities = []
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.registered_agents = {"agent-1": mock_agent}
        mock_project.agent_assignments = {"feature": "agent-1"}
        mock_project.active_work_sessions = {}
        mock_project.resource_locks = {}
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.unregister_agent(
            project_id="test-project",
            agent_id="agent-1"
        )
        
        # Assert
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-1"
        assert "agent-1" not in mock_project.registered_agents
        mock_repo.update.assert_called_once_with(mock_project)
    
    @pytest.mark.asyncio
    async def test_unregister_agent_not_found(self, setup):
        """Test unregistering non-existent agent."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.registered_agents = {}
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.unregister_agent(
            project_id="test-project",
            agent_id="non-existent"
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]


class TestCleanupObsolete:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test cleanup obsolete functionality."""
    
    @pytest_asyncio.fixture
    async def setup(self):
        """Set up test dependencies."""
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        return {
            "service": service,
            "mock_repo": mock_repo
        }
    
    @pytest.mark.asyncio
    async def test_cleanup_specific_project(self, setup):
        """Test cleanup for specific project."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock project with obsolete data
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project"
        mock_project.git_branchs = {"main": Mock()}
        mock_project.registered_agents = {}
        mock_project.agent_assignments = {"feature": "agent-1"}  # Obsolete
        mock_project.active_work_sessions = {}
        mock_project.resource_locks = {}
        mock_repo.find_by_id.return_value = mock_project
        
        # Act
        result = await service.cleanup_obsolete("test-project")
        
        # Assert
        assert result["success"] is True
        assert len(result["cleaned_items"]) > 0
        assert "feature" not in mock_project.agent_assignments
        mock_repo.update.assert_called_once_with(mock_project)
    
    @pytest.mark.asyncio
    async def test_cleanup_project_not_found(self, setup):
        """Test cleanup when project not found."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        mock_repo.find_by_id.return_value = None
        
        # Act
        result = await service.cleanup_obsolete("non-existent")
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_cleanup_all_projects(self, setup):
        """Test cleanup for all projects."""
        # Arrange
        service = setup["service"]
        mock_repo = setup["mock_repo"]
        
        # Mock multiple projects
        mock_project1 = Mock(spec=Project)
        mock_project1.id = "project-1"
        mock_project1.git_branchs = {}
        mock_project1.registered_agents = {}
        mock_project1.agent_assignments = {}
        mock_project1.active_work_sessions = {}
        mock_project1.resource_locks = {}
        
        mock_project2 = Mock(spec=Project)
        mock_project2.id = "project-2"
        mock_project2.git_branchs = {}
        mock_project2.registered_agents = {}
        mock_project2.agent_assignments = {"obsolete": "agent-x"}
        mock_project2.active_work_sessions = {}
        mock_project2.resource_locks = {}
        
        mock_repo.find_all.return_value = [mock_project1, mock_project2]
        
        # Act
        result = await service.cleanup_obsolete()
        
        # Assert
        assert result["success"] is True
        assert result["total_cleaned"] >= 1
        assert "project-1" in result["cleanup_results"]
        assert "project-2" in result["cleanup_results"]


class TestCleanupProjectData:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test internal cleanup project data method."""
    
    def test_cleanup_orphaned_assignments(self):
        """Test cleaning up orphaned assignments."""
        # Arrange
        mock_repo = Mock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock project
        mock_project = Mock()
        mock_project.git_branchs = {"main": Mock()}
        mock_project.registered_agents = {"agent-1": Mock()}
        mock_project.agent_assignments = {
            "main": "agent-1",  # Valid
            "feature": "agent-2"  # Orphaned - agent not registered
        }
        mock_project.active_work_sessions = {}
        mock_project.resource_locks = {}
        
        # Act
        cleaned_items = service._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned_items) > 0
        assert "feature" not in mock_project.agent_assignments
        assert "main" in mock_project.agent_assignments
    
    def test_cleanup_orphaned_sessions(self):
        """Test cleaning up orphaned work sessions."""
        # Arrange
        mock_repo = Mock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock session
        mock_session = Mock()
        mock_session.agent_id = "agent-2"
        
        # Mock project
        mock_project = Mock()
        mock_project.git_branchs = {}
        mock_project.registered_agents = {"agent-1": Mock()}
        mock_project.agent_assignments = {}
        mock_project.active_work_sessions = {
            "session-1": mock_session  # Orphaned
        }
        mock_project.resource_locks = {}
        
        # Act
        cleaned_items = service._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned_items) > 0
        assert "session-1" not in mock_project.active_work_sessions
    
    def test_cleanup_orphaned_locks(self):
        """Test cleaning up orphaned resource locks."""
        # Arrange
        mock_repo = Mock()
        service = ProjectApplicationService(mock_repo)
        
        # Mock project
        mock_project = Mock()
        mock_project.git_branchs = {}
        mock_project.registered_agents = {"agent-1": Mock()}
        mock_project.agent_assignments = {}
        mock_project.active_work_sessions = {}
        mock_project.resource_locks = {
            "resource-1": "agent-1",  # Valid
            "resource-2": "agent-2"   # Orphaned
        }
        
        # Act
        cleaned_items = service._cleanup_project_data(mock_project)
        
        # Assert
        assert len(cleaned_items) > 0
        assert "resource-2" not in mock_project.resource_locks
        assert "resource-1" in mock_project.resource_locks


class TestProjectApplicationServiceIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test integration scenarios for ProjectApplicationService."""
    
    @pytest.mark.asyncio
    async def test_full_project_lifecycle(self):
        """Test complete project lifecycle with agents and trees."""
        # Arrange
        mock_repo = AsyncMock()
        service = ProjectApplicationService(mock_repo)
        
        # Create project
        service._create_project_use_case = AsyncMock()
        service._create_project_use_case.execute.return_value = {
            "success": True,
            "project": {"id": "test-project"}
        }
        
        result = await service.create_project("test-project", "Test Project")
        assert result["success"] is True
        
        # Create task tree
        service._create_git_branch_use_case = AsyncMock()
        service._create_git_branch_use_case.execute.return_value = {
            "success": True
        }
        
        result = await service.create_git_branch(
            "test-project", "feature", "Feature", "Feature branch"
        )
        assert result["success"] is True
        
        # Register agent
        mock_project = Mock(spec=Project)
        mock_project.registered_agents = {}
        mock_repo.find_by_id.return_value = mock_project
        
        result = await service.register_agent(
            "test-project", "agent-1", "Test Agent", ["coding"]
        )
        assert result["success"] is True
        
        # Assign agent to tree
        result = await service.assign_agent_to_tree(
            "test-project", "agent-1", "feature"
        )
        assert result["success"] is True
        
        # Health check
        service._project_health_check_use_case = AsyncMock()
        service._project_health_check_use_case.execute.return_value = {
            "success": True,
            "health_status": "healthy"
        }
        
        result = await service.project_health_check("test-project")
        assert result["success"] is True