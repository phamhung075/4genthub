"""Unit tests for Project entity."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.agent import Agent, AgentCapability, AgentStatus
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestProjectCreation:
    
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

    """Test Project creation and initialization."""
    
    def test_create_project_with_factory_method(self):
        """Test creating project with factory method."""
        project = Project.create(
            name="Test Project",
            description="A test project description"
        )
        
        assert len(project.id) == 36  # UUID format
        assert project.name == "Test Project"
        assert project.description == "A test project description"
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)
        assert project.created_at.tzinfo == timezone.utc
        assert project.updated_at.tzinfo == timezone.utc
        assert project.created_at == project.updated_at
        assert len(project.git_branchs) == 0
        assert len(project.registered_agents) == 0
        assert len(project.agent_assignments) == 0
        assert len(project.cross_tree_dependencies) == 0
        assert len(project.active_work_sessions) == 0
        assert len(project.resource_locks) == 0
    
    def test_create_project_minimal(self):
        """Test creating project with minimal data."""
        project = Project.create(name="Minimal Project")
        
        assert project.name == "Minimal Project"
        assert project.description == ""
        assert isinstance(project.id, str)
        assert len(project.id) == 36
    
    def test_project_post_init_timezone_handling(self):
        """Test that __post_init__ ensures timestamps are timezone-aware."""
        # Create project with naive timestamps
        naive_time = datetime(2024, 1, 1, 12, 0, 0)
        project = Project(
            id="test-id",
            name="Test Project",
            description="Test",
            created_at=naive_time,
            updated_at=naive_time
        )
        
        # Timestamps should be made timezone-aware
        assert project.created_at.tzinfo == timezone.utc
        assert project.updated_at.tzinfo == timezone.utc
    
    def test_project_hashable(self):
        """Test that projects are hashable based on ID."""
        project1 = Project.create(name="Project 1")
        project2 = Project.create(name="Project 2")
        
        # Should be able to use in sets
        project_set = {project1, project2}
        assert len(project_set) == 2
        assert project1 in project_set
        assert project2 in project_set
        
        # Should be able to use as dict keys
        project_dict = {project1: "First", project2: "Second"}
        assert project_dict[project1] == "First"
        assert project_dict[project2] == "Second"


class TestGitBranchManagement:
    
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

    """Test Project task tree management functionality."""
    
    def test_create_git_branch_legacy_method(self):
        """Test creating task tree with legacy method."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature-auth",
            name="Authentication Feature",
            description="Implement user authentication"
        )
        
        assert isinstance(git_branch, GitBranch)
        assert len(git_branch.id) == 36  # UUID format
        assert git_branch.name == "Authentication Feature"
        assert git_branch.description == "Implement user authentication"
        assert git_branch.project_id == project.id
        assert git_branch.id in project.git_branchs
        assert project.git_branchs[git_branch.id] == git_branch
        assert project.updated_at > project.created_at
    
    def test_create_git_branch_duplicate_name_raises_error(self):
        """Test that creating task tree with duplicate name raises error."""
        project = Project.create(name="Test Project")
        
        # Create first tree
        tree1 = project.create_git_branch("feature-auth", "Auth Feature")
        
        # The implementation checks if any existing tree's name matches the git_branch_name parameter
        # So we need to create a tree whose name matches the git_branch_name we're trying to use
        project.create_git_branch("another-branch", "feature-auth")  # name="feature-auth"
        
        # Now try to create with git_branch_name matching an existing tree's name
        with pytest.raises(ValueError, match="already exists"):
            project.create_git_branch("feature-auth", "New Feature")
    
    @pytest.mark.asyncio
    async def test_create_git_branch_with_repository(self):
        """Test creating git branch using repository."""
        project = Project.create(name="Test Project")
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.find_by_name = AsyncMock(return_value=None)
        
        # Create mock task tree
        mock_tree = GitBranch(
            id="tree-123",
            name="Feature Branch",
            description="Test branch",
            project_id=project.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.create_branch = AsyncMock(return_value=mock_tree)
        
        # Create branch
        git_branch = await project.create_git_branch_async(
            mock_repo,
            "feature-branch",
            "Test branch"
        )
        
        assert git_branch == mock_tree
        assert git_branch.id in project.git_branchs
        assert project.git_branchs[git_branch.id] == git_branch
        
        # Verify repository calls
        mock_repo.find_by_name.assert_called_once_with(project.id, "feature-branch")
        mock_repo.create_branch.assert_called_once_with(
            project_id=project.id,
            branch_name="feature-branch",
            description="Test branch"
        )
    
    @pytest.mark.asyncio
    async def test_create_git_branch_already_exists(self):
        """Test that creating existing branch raises error."""
        project = Project.create(name="Test Project")
        
        # Mock repository to return existing branch
        mock_repo = Mock()
        mock_repo.find_by_name = AsyncMock(return_value=Mock())
        
        with pytest.raises(ValueError, match="already exists"):
            await project.create_git_branch_async(
                mock_repo,
                "existing-branch"
            )
    
    def test_add_git_branch(self):
        """Test adding an existing task tree to project."""
        project = Project.create(name="Test Project")
        
        # Create task tree externally
        git_branch = GitBranch(
            id="external-tree",
            name="External Tree",
            description="Created externally",
            project_id=project.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        original_updated = project.updated_at
        import time
        time.sleep(0.01)
        
        project.add_git_branch(git_branch)
        
        assert git_branch.id in project.git_branchs
        assert project.git_branchs[git_branch.id] == git_branch
        assert project.updated_at > original_updated
    
    def test_get_git_branch_by_name(self):
        """Test getting task tree by name."""
        project = Project.create(name="Test Project")
        
        # Create multiple trees
        tree1 = project.create_git_branch("main", "Main Branch", "Main development")
        tree2 = project.create_git_branch("feature", "Feature Branch", "New feature")
        
        # Get by name
        found_tree = project.get_git_branch("Main Branch")
        assert found_tree == tree1
        
        found_tree = project.get_git_branch("Feature Branch")
        assert found_tree == tree2
        
        # Non-existent tree
        assert project.get_git_branch("Non-existent") is None


class TestAgentManagement:
    
    def setup_method(self, method):
        """Clean up before each test"""
        # For unit tests of domain entities, we don't need database access
        # Domain entities should be tested in isolation
        pass

    """Test Project agent management functionality."""
    
    def test_register_agent(self):
        """Test registering an agent to the project."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        
        # Store original timestamp and ensure sufficient time difference
        original_updated = project.updated_at
        import time
        time.sleep(0.1)  # Increased sleep time to avoid race condition
        
        project.register_agent(agent)
        
        assert agent.id in project.registered_agents
        assert project.registered_agents[agent.id] == agent
        assert project.updated_at > original_updated
    
    def test_assign_agent_to_tree(self):
        """Test assigning agent to a task tree."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree = project.create_git_branch("main", "Main Branch")
        
        # Register agent first
        project.register_agent(agent)
        
        # Assign to tree
        project.assign_agent_to_tree(agent.id, tree.id)
        
        assert project.agent_assignments[tree.id] == agent.id
    
    def test_assign_unregistered_agent_raises_error(self):
        """Test that assigning unregistered agent raises error."""
        project = Project.create(name="Test Project")
        tree = project.create_git_branch("main", "Main Branch")
        
        with pytest.raises(ValueError, match="not registered"):
            project.assign_agent_to_tree("unregistered-agent", tree.id)
    
    def test_assign_agent_to_nonexistent_tree_raises_error(self):
        """Test that assigning to non-existent tree raises error."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)
        
        with pytest.raises(ValueError, match="not found"):
            project.assign_agent_to_tree(agent.id, "non-existent-tree")
    
    def test_reassign_tree_to_different_agent_raises_error(self):
        """Test that reassigning tree to different agent raises error."""
        project = Project.create(name="Test Project")
        agent1 = Agent(id="agent-1", name="Agent 1")
        agent2 = Agent(id="agent-2", name="Agent 2")
        tree = project.create_git_branch("main", "Main Branch")
        
        # Register both agents
        project.register_agent(agent1)
        project.register_agent(agent2)
        
        # Assign first agent
        project.assign_agent_to_tree(agent1.id, tree.id)
        
        # Try to assign second agent
        with pytest.raises(ValueError, match="already assigned"):
            project.assign_agent_to_tree(agent2.id, tree.id)
    
    def test_reassign_same_agent_succeeds(self):
        """Test that reassigning same agent to tree succeeds."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree = project.create_git_branch("main", "Main Branch")
        
        project.register_agent(agent)
        project.assign_agent_to_tree(agent.id, tree.id)
        
        # Reassign same agent (should not raise error)
        project.assign_agent_to_tree(agent.id, tree.id)
        
        assert project.agent_assignments[tree.id] == agent.id


class TestCrossTreeDependencies:
    
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

    """Test cross-tree dependency management."""
    
    def test_add_cross_tree_dependency(self):
        """Test adding dependency between tasks in different trees."""
        project = Project.create(name="Test Project")
        
        # Create two trees with tasks
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        
        # Add tasks to trees
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440001"),
            title="Task 1",
            description="In tree 1"
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440002"),
            title="Task 2",
            description="In tree 2"
        )
        
        tree1.add_root_task(task1)
        tree2.add_root_task(task2)
        
        # Add cross-tree dependency
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440002", "550e8400e29b41d4a716446655440001")
        
        # After normalization, task IDs should be in canonical format
        canonical_task2 = "550e8400-e29b-41d4-a716-446655440002"
        canonical_task1 = "550e8400-e29b-41d4-a716-446655440001"
        
        assert canonical_task2 in project.cross_tree_dependencies
        assert canonical_task1 in project.cross_tree_dependencies[canonical_task2]
    
    def test_add_same_tree_dependency_raises_error(self):
        """Test that adding dependency within same tree raises error."""
        project = Project.create(name="Test Project")
        tree = project.create_git_branch("tree1", "Tree 1")
        
        # Add two tasks to same tree
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440001"),
            title="Task 1",
            description="Task 1"
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440002"),
            title="Task 2",
            description="Task 2"
        )
        
        tree.add_root_task(task1)
        tree.add_root_task(task2)
        
        with pytest.raises(ValueError, match="Use regular task dependencies"):
            project.add_cross_tree_dependency("550e8400e29b41d4a716446655440002", "550e8400e29b41d4a716446655440001")
    
    def test_add_dependency_task_not_found(self):
        """Test that adding dependency for non-existent task raises error."""
        project = Project.create(name="Test Project")
        
        with pytest.raises(ValueError, match="not found"):
            project.add_cross_tree_dependency("550e8400e29b41d4a716446655440001", "550e8400e29b41d4a716446655440002")
    
    def test_find_git_branch(self):
        """Test finding which tree contains a task."""
        project = Project.create(name="Test Project")
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440001"),
            title="Task 1",
            description="In tree 1"
        )
        tree1.add_root_task(task1)
        
        # Find tree containing task
        found_tree = project._find_git_branch("550e8400e29b41d4a716446655440001")
        assert found_tree == tree1
        
        # Task not found
        assert project._find_git_branch("non-existent") is None


class TestWorkCoordination:
    
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

    """Test work coordination and session management."""
    
    def test_get_available_work_for_agent(self):
        """Test getting available work for a specific agent."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree = project.create_git_branch("main", "Main Branch")
        
        # Setup: register agent, assign to tree, add tasks
        project.register_agent(agent)
        project.assign_agent_to_tree(agent.id, tree.id)
        
        # Add available tasks
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440001"),
            title="Available Task 1",
            description="Ready to work on",
            status=TaskStatus.todo()
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440002"),
            title="Available Task 2",
            description="Also ready",
            status=TaskStatus.todo()
        )
        task3 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440003"),
            title="Completed Task",
            description="Already done",
            status=TaskStatus.done()
        )
        
        tree.add_root_task(task1)
        tree.add_root_task(task2)
        tree.add_root_task(task3)
        
        # Get available work
        available_tasks = project.get_available_work_for_agent(agent.id)
        
        assert len(available_tasks) == 2
        assert task1 in available_tasks
        assert task2 in available_tasks
        assert task3 not in available_tasks
    
    def test_get_available_work_with_cross_tree_dependencies(self):
        """Test that cross-tree dependencies block tasks."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        
        # Register agent and assign to tree2
        project.register_agent(agent)
        project.assign_agent_to_tree(agent.id, tree2.id)
        
        # Add tasks
        prerequisite = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440004"),
            title="Prerequisite",
            description="Must be done first",
            status=TaskStatus.todo()  # Not completed
        )
        dependent = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440005"),
            title="Dependent",
            description="Depends on prerequisite",
            status=TaskStatus.todo()
        )
        
        tree1.add_root_task(prerequisite)
        tree2.add_root_task(dependent)
        
        # Add cross-tree dependency
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440005", "550e8400e29b41d4a716446655440004")
        
        # Get available work - dependent should be blocked
        available_tasks = project.get_available_work_for_agent(agent.id)
        
        assert len(available_tasks) == 0  # Dependent is blocked
        
        # Complete prerequisite
        prerequisite.status = TaskStatus.done()
        
        # Now dependent should be available
        available_tasks = project.get_available_work_for_agent(agent.id)
        assert len(available_tasks) == 1
        assert dependent in available_tasks
    
    def test_get_available_work_unregistered_agent(self):
        """Test that getting work for unregistered agent raises error."""
        project = Project.create(name="Test Project")
        
        with pytest.raises(ValueError, match="not registered"):
            project.get_available_work_for_agent("unregistered-agent")
    
    def test_start_work_session(self):
        """Test starting a work session."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree = project.create_git_branch("main", "Main Branch")
        
        # Setup
        project.register_agent(agent)
        project.assign_agent_to_tree(agent.id, tree.id)
        
        task = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440006"),
            title="Task to work on",
            description="Test task"
        )
        tree.add_root_task(task)
        
        # Start work session
        session = project.start_work_session(
            agent_id=agent.id,
            task_id="550e8400e29b41d4a716446655440006",
            max_duration_hours=2.0
        )
        
        assert isinstance(session, WorkSession)
        assert session.agent_id == agent.id
        assert session.task_id == "550e8400e29b41d4a716446655440006"
        assert session.git_branch_name == tree.id
        assert session.max_duration == timedelta(hours=2.0)
        assert session.id in project.active_work_sessions
        assert project.active_work_sessions[session.id] == session
    
    def test_start_work_session_unregistered_agent(self):
        """Test that starting session with unregistered agent raises error."""
        project = Project.create(name="Test Project")
        
        with pytest.raises(ValueError, match="not registered"):
            project.start_work_session("unregistered", "task-1")
    
    def test_start_work_session_task_not_found(self):
        """Test that starting session for non-existent task raises error."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        project.register_agent(agent)
        
        with pytest.raises(ValueError, match="not found"):
            project.start_work_session(agent.id, "non-existent-task")
    
    def test_start_work_session_agent_not_assigned_to_tree(self):
        """Test that agent must be assigned to tree containing task."""
        project = Project.create(name="Test Project")
        agent = Agent(id="agent-1", name="Test Agent")
        tree = project.create_git_branch("main", "Main Branch")
        
        project.register_agent(agent)
        # Don't assign agent to tree
        
        task = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440007"),
            title="Task",
            description="Test"
        )
        tree.add_root_task(task)
        
        with pytest.raises(ValueError, match="not assigned to tree"):
            project.start_work_session(agent.id, "550e8400e29b41d4a716446655440007")


class TestOrchestrationStatus:
    
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

    """Test orchestration status and reporting."""
    
    def test_get_orchestration_status_empty_project(self):
        """Test getting status for empty project."""
        project = Project.create(name="Empty Project")
        
        status = project.get_orchestration_status()
        
        assert status["project_id"] == project.id
        assert status["project_name"] == "Empty Project"
        assert status["total_branches"] == 0
        assert status["registered_agents"] == 0
        assert status["active_assignments"] == 0
        assert status["active_sessions"] == 0
        assert status["cross_tree_dependencies"] == 0
        assert status["resource_locks"] == 0
        assert status["branches"] == {}
        assert status["agents"] == {}
    
    def test_get_orchestration_status_with_data(self):
        """Test getting comprehensive orchestration status."""
        project = Project.create(name="Test Project")
        
        # Create agents
        agent1 = Agent(
            id="agent-1",
            name="Agent 1",
            capabilities={AgentCapability.BACKEND_DEVELOPMENT}
        )
        agent2 = Agent(
            id="agent-2",
            name="Agent 2",
            capabilities={AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.TESTING}
        )
        
        # Create trees
        tree1 = project.create_git_branch("backend", "Backend Work")
        tree2 = project.create_git_branch("frontend", "Frontend Work")
        
        # Add tasks
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440008"),
            title="API Implementation",
            description="Build REST API"
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440009"),
            title="UI Components",
            description="Build UI",
            status=TaskStatus.done()
        )
        
        tree1.add_root_task(task1)
        tree2.add_root_task(task2)
        
        # Register agents and assign to trees
        project.register_agent(agent1)
        project.register_agent(agent2)
        project.assign_agent_to_tree(agent1.id, tree1.id)
        project.assign_agent_to_tree(agent2.id, tree2.id)
        
        # Add cross-tree dependency
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440009", "550e8400e29b41d4a716446655440008")
        
        # Start a work session
        session = project.start_work_session(agent1.id, "550e8400e29b41d4a716446655440008")
        
        # Add resource lock
        project.resource_locks["database"] = agent1.id
        
        # Get status
        status = project.get_orchestration_status()
        
        assert status["project_id"] == project.id
        assert status["project_name"] == "Test Project"
        assert status["total_branches"] == 2
        assert status["registered_agents"] == 2
        assert status["active_assignments"] == 2
        assert status["active_sessions"] == 1
        assert status["cross_tree_dependencies"] == 1
        assert status["resource_locks"] == 1
        
        # Check trees info
        assert len(status["branches"]) == 2
        assert tree1.id in status["branches"]
        assert status["branches"][tree1.id]["name"] == "Backend Work"
        assert status["branches"][tree1.id]["assigned_agent"] == agent1.id
        assert status["branches"][tree1.id]["total_tasks"] == 1
        assert status["branches"][tree1.id]["completed_tasks"] == 0
        assert status["branches"][tree1.id]["progress"] == 0.0
        
        assert status["branches"][tree2.id]["completed_tasks"] == 1
        assert status["branches"][tree2.id]["progress"] == 100.0
        
        # Check agents info
        assert len(status["agents"]) == 2
        assert agent1.id in status["agents"]
        assert status["agents"][agent1.id]["name"] == "Agent 1"
        assert "backend_development" in status["agents"][agent1.id]["capabilities"]
        assert tree1.id in status["agents"][agent1.id]["assigned_trees"]
        assert session.id in status["agents"][agent1.id]["active_sessions"]
        
        assert len(status["agents"][agent2.id]["capabilities"]) == 2


class TestDependencyCoordination:
    
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

    """Test cross-tree dependency coordination."""
    
    def test_coordinate_cross_tree_dependencies_empty(self):
        """Test coordinating when no dependencies exist."""
        project = Project.create(name="Test Project")
        
        result = project.coordinate_cross_tree_dependencies()
        
        assert result["total_dependencies"] == 0
        assert result["validated_dependencies"] == 0
        assert result["blocked_tasks"] == []
        assert result["ready_tasks"] == []
        assert result["missing_prerequisites"] == []
    
    def test_coordinate_dependencies_all_satisfied(self):
        """Test coordination when all dependencies are satisfied."""
        project = Project.create(name="Test Project")
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        
        # Create tasks
        prereq = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000a"),
            title="Prerequisite",
            description="Must be done first",
            status=TaskStatus.done()  # Completed
        )
        dependent = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000b"),
            title="Dependent",
            description="Depends on prereq",
            status=TaskStatus.todo()
        )
        
        tree1.add_root_task(prereq)
        tree2.add_root_task(dependent)
        
        project.add_cross_tree_dependency("550e8400e29b41d4a71644665544000b", "550e8400e29b41d4a71644665544000a")
        
        result = project.coordinate_cross_tree_dependencies()
        
        assert result["total_dependencies"] == 1
        assert result["validated_dependencies"] == 1
        assert len(result["ready_tasks"]) == 1
        assert "550e8400-e29b-41d4-a716-44665544000b" in result["ready_tasks"]
        assert len(result["blocked_tasks"]) == 0
        assert len(result["missing_prerequisites"]) == 0
    
    def test_coordinate_dependencies_blocked(self):
        """Test coordination when dependencies are not satisfied."""
        project = Project.create(name="Test Project")
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        
        # Create tasks
        prereq = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000c"),
            title="Prerequisite",
            description="Must be done first",
            status=TaskStatus.todo()  # Not completed
        )
        dependent = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000d"),
            title="Dependent",
            description="Depends on prereq",
            status=TaskStatus.todo()
        )
        
        tree1.add_root_task(prereq)
        tree2.add_root_task(dependent)
        
        project.add_cross_tree_dependency("550e8400e29b41d4a71644665544000d", "550e8400e29b41d4a71644665544000c")
        
        result = project.coordinate_cross_tree_dependencies()
        
        assert result["total_dependencies"] == 1
        assert result["validated_dependencies"] == 1
        assert len(result["blocked_tasks"]) == 1
        assert "550e8400-e29b-41d4-a716-44665544000d" in result["blocked_tasks"]
        assert len(result["ready_tasks"]) == 0
    
    def test_coordinate_dependencies_missing_tasks(self):
        """Test coordination when tasks are missing."""
        project = Project.create(name="Test Project")
        
        # Add dependency for non-existent tasks
        project.cross_tree_dependencies["missing-dependent"] = {"missing-prereq"}
        
        result = project.coordinate_cross_tree_dependencies()
        
        assert result["total_dependencies"] == 1
        assert result["validated_dependencies"] == 0
        assert len(result["missing_prerequisites"]) == 1
        assert result["missing_prerequisites"][0]["task_id"] == "missing-dependent"
        assert "not found" in result["missing_prerequisites"][0]["issue"]
    
    def test_coordinate_dependencies_mixed_scenarios(self):
        """Test coordination with mixed scenarios."""
        project = Project.create(name="Test Project")
        tree1 = project.create_git_branch("tree1", "Tree 1")
        tree2 = project.create_git_branch("tree2", "Tree 2")
        tree3 = project.create_git_branch("tree3", "Tree 3")
        
        # Create tasks with various states
        task1 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000e"),
            title="Task 1",
            description="Completed prerequisite",
            status=TaskStatus.done()
        )
        task2 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a71644665544000f"),
            title="Task 2",
            description="Incomplete prerequisite",
            status=TaskStatus.in_progress()
        )
        task3 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440010"),
            title="Task 3",
            description="Depends on task-1 (ready)",
            status=TaskStatus.todo()
        )
        task4 = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440011"),
            title="Task 4",
            description="Depends on task-2 (blocked)",
            status=TaskStatus.todo()
        )
        
        tree1.add_root_task(task1)
        tree1.add_root_task(task2)
        tree2.add_root_task(task3)
        tree3.add_root_task(task4)
        
        # Add dependencies
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440010", "550e8400e29b41d4a71644665544000e")  # Ready
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440011", "550e8400e29b41d4a71644665544000f")  # Blocked
        # Manually add a dependency for non-existent task to test missing dependency scenario
        project.cross_tree_dependencies["550e8400e29b41d4a716446655440012"] = {"550e8400e29b41d4a71644665544000e"}
        
        result = project.coordinate_cross_tree_dependencies()
        
        assert result["total_dependencies"] == 3
        assert result["validated_dependencies"] == 2  # task-3 and task-4
        assert len(result["ready_tasks"]) == 1
        assert "550e8400-e29b-41d4-a716-446655440010" in result["ready_tasks"]
        assert len(result["blocked_tasks"]) == 1
        assert "550e8400-e29b-41d4-a716-446655440011" in result["blocked_tasks"]
        assert len(result["missing_prerequisites"]) == 1


class TestProjectIntegration:
    
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

    """Integration tests for Project functionality."""
    
    @pytest.mark.asyncio
    async def test_full_project_workflow(self):
        """Test complete project workflow from creation to task completion."""
        # Create project
        project = Project.create(
            name="E-commerce Platform",
            description="Build a modern e-commerce platform"
        )
        
        # Create agents with different capabilities
        backend_agent = Agent(
            id="backend-agent",
            name="Backend Developer",
            capabilities={AgentCapability.BACKEND_DEVELOPMENT, AgentCapability.ARCHITECTURE}
        )
        frontend_agent = Agent(
            id="frontend-agent",
            name="Frontend Developer",
            capabilities={AgentCapability.FRONTEND_DEVELOPMENT}
        )
        test_agent = Agent(
            id="test-agent",
            name="QA Engineer",
            capabilities={AgentCapability.TESTING}
        )
        
        # Register agents
        project.register_agent(backend_agent)
        project.register_agent(frontend_agent)
        project.register_agent(test_agent)
        
        # Create task trees for different components
        api_tree = project.create_git_branch("api", "API Development")
        ui_tree = project.create_git_branch("ui", "UI Development")
        test_tree = project.create_git_branch("tests", "Testing")
        
        # Assign agents to trees
        project.assign_agent_to_tree(backend_agent.id, api_tree.id)
        project.assign_agent_to_tree(frontend_agent.id, ui_tree.id)
        project.assign_agent_to_tree(test_agent.id, test_tree.id)
        
        # Create tasks
        api_task = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440013"),
            title="Create REST API endpoints",
            description="Implement product and order endpoints",
            priority=Priority.high()
        )
        ui_task = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440014"),
            title="Build UI components",
            description="Create product listing and cart components",
            priority=Priority.high()
        )
        test_task = Task.create(
            id=TaskId.from_string("550e8400e29b41d4a716446655440015"),
            title="Write integration tests",
            description="Test API and UI integration",
            priority=Priority.medium()
        )
        
        # Add tasks to trees
        api_tree.add_root_task(api_task)
        ui_tree.add_root_task(ui_task)
        test_tree.add_root_task(test_task)
        
        # Add cross-tree dependencies (UI depends on API, tests depend on both)
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440014", "550e8400e29b41d4a716446655440013")
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440015", "550e8400e29b41d4a716446655440013")
        project.add_cross_tree_dependency("550e8400e29b41d4a716446655440015", "550e8400e29b41d4a716446655440014")
        
        # Check initial available work
        backend_work = project.get_available_work_for_agent(backend_agent.id)
        assert len(backend_work) == 1
        assert api_task in backend_work
        
        frontend_work = project.get_available_work_for_agent(frontend_agent.id)
        assert len(frontend_work) == 0  # Blocked by API
        
        test_work = project.get_available_work_for_agent(test_agent.id)
        assert len(test_work) == 0  # Blocked by both
        
        # Backend agent starts work
        backend_session = project.start_work_session(
            backend_agent.id,
            "550e8400e29b41d4a716446655440013",
            max_duration_hours=4
        )
        assert backend_session.is_active()
        
        # Complete API task (need to go through in_progress first)
        api_task.update_status(TaskStatus.in_progress())
        api_task.update_status(TaskStatus.done())
        backend_session.complete_session(success=True, notes="All endpoints implemented")
        
        # Now UI work should be available
        frontend_work = project.get_available_work_for_agent(frontend_agent.id)
        assert len(frontend_work) == 1
        assert ui_task in frontend_work
        
        # Frontend agent works on UI
        frontend_session = project.start_work_session(
            frontend_agent.id,
            "550e8400e29b41d4a716446655440014",
            max_duration_hours=3
        )
        ui_task.update_status(TaskStatus.in_progress())
        ui_task.update_status(TaskStatus.done())
        frontend_session.complete_session(success=True)
        
        # Now test work should be available
        test_work = project.get_available_work_for_agent(test_agent.id)
        assert len(test_work) == 1
        assert test_task in test_work
        
        # Get final orchestration status
        final_status = project.get_orchestration_status()
        assert final_status["total_branches"] == 3
        assert final_status["registered_agents"] == 3
        assert final_status["active_assignments"] == 3
        assert final_status["cross_tree_dependencies"] == 3
        
        # Check coordination result
        coord_result = project.coordinate_cross_tree_dependencies()
        # Both UI and test tasks should be ready (UI is done, test dependencies are satisfied)
        assert len(coord_result["ready_tasks"]) == 2
        assert "550e8400-e29b-41d4-a716-446655440014" in coord_result["ready_tasks"]  # UI task (done but still in ready list)
        assert "550e8400-e29b-41d4-a716-446655440015" in coord_result["ready_tasks"]  # Test task
        assert len(coord_result["blocked_tasks"]) == 0