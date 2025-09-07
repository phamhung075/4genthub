"""Test suite for Project domain entity.

Tests the Project entity including:
- Creation and initialization
- Git branch management
- Agent registration and assignment
- Cross-tree dependencies
- Work session management
- Orchestration status
- Multi-agent coordination
- Validation and business rules
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid

from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.agent import Agent, AgentCapability
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


class TestProjectCreation:
    """Test cases for Project creation and initialization."""
    
    def test_create_project_with_factory_method(self):
        """Test creating a project using the factory method."""
        project = Project.create(
            name="Test Project",
            description="A test project"
        )
        
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.created_at is not None
        assert project.updated_at is not None
        assert project.created_at.tzinfo == timezone.utc
        assert project.updated_at.tzinfo == timezone.utc
        assert project.git_branchs == {}
        assert project.registered_agents == {}
        assert project.agent_assignments == {}
        assert project.cross_tree_dependencies == {}
        assert project.active_work_sessions == {}
        assert project.resource_locks == {}
    
    def test_create_project_minimal_data(self):
        """Test creating a project with minimal data."""
        project = Project.create(name="Minimal Project")
        
        assert project.name == "Minimal Project"
        assert project.description == ""
        assert isinstance(project.id, str)
        assert len(project.id) == 36  # UUID4 format
    
    def test_create_project_uuid_generation(self):
        """Test that each project gets a unique UUID."""
        project1 = Project.create(name="Project 1")
        project2 = Project.create(name="Project 2")
        
        assert project1.id != project2.id
        # Verify UUID format
        uuid.UUID(project1.id)  # Should not raise exception
        uuid.UUID(project2.id)  # Should not raise exception
    
    def test_project_direct_instantiation(self):
        """Test creating a project with direct instantiation."""
        project_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        project = Project(
            id=project_id,
            name="Direct Project",
            description="Created directly",
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert project.id == project_id
        assert project.name == "Direct Project"
        assert project.description == "Created directly"
        assert project.created_at == created_at
        assert project.updated_at == updated_at
    
    def test_timezone_handling(self):
        """Test timezone handling for timestamps."""
        # Test with naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        project = Project(
            id=str(uuid.uuid4()),
            name="Test",
            description="Test",
            created_at=naive_dt,
            updated_at=naive_dt
        )
        
        # Should be converted to UTC
        assert project.created_at.tzinfo == timezone.utc
        assert project.updated_at.tzinfo == timezone.utc
    
    def test_project_hashable(self):
        """Test project can be hashed for use in sets/dicts."""
        project = Project.create(name="Test")
        
        # Should be hashable
        project_set = {project}
        assert project in project_set
        
        # Hash should be based on ID
        assert hash(project) == hash(project.id)


class TestGitBranchManagement:
    """Test cases for git branch management."""
    
    def test_create_git_branch_legacy_method(self):
        """Test creating a git branch using the legacy method."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/auth",
            name="Authentication Feature",
            description="Implement user authentication"
        )
        
        assert isinstance(git_branch, GitBranch)
        assert git_branch.name == "Authentication Feature"
        assert git_branch.description == "Implement user authentication"
        assert git_branch.project_id == project.id
        assert git_branch.id in project.git_branchs
        assert project.git_branchs[git_branch.id] == git_branch
    
    def test_create_git_branch_duplicate_name(self):
        """Test creating a git branch with duplicate name fails."""
        project = Project.create(name="Test Project")
        
        # Create first branch
        project.create_git_branch(
            git_branch_name="feature/auth",
            name="Auth Branch",
            description="First auth branch"
        )
        
        # Attempt to create duplicate
        with pytest.raises(ValueError, match="Git branch feature/auth already exists"):
            project.create_git_branch(
                git_branch_name="feature/auth",
                name="Another Auth Branch",
                description="Second auth branch"
            )
    
    def test_add_git_branch(self):
        """Test adding an existing git branch to the project."""
        project = Project.create(name="Test Project")
        
        git_branch = GitBranch(
            id=str(uuid.uuid4()),
            name="External Branch",
            description="Created externally",
            project_id=project.id,
            created_at=datetime.now(timezone.utc)
        )
        
        original_updated = project.updated_at
        project.add_git_branch(git_branch)
        
        assert git_branch.id in project.git_branchs
        assert project.git_branchs[git_branch.id] == git_branch
        assert project.updated_at > original_updated
    
    def test_get_git_branch_by_name(self):
        """Test getting git branch by name."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/search",
            name="Search Feature",
            description="Implement search"
        )
        
        found_branch = project.get_git_branch("Search Feature")
        assert found_branch == git_branch
        
        # Non-existent branch
        not_found = project.get_git_branch("Non Existent")
        assert not_found is None
    
    @pytest.mark.asyncio
    async def test_create_git_branch_async(self):
        """Test creating git branch using async repository method."""
        project = Project.create(name="Test Project")
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.find_by_name = AsyncMock(return_value=None)
        mock_repo.create_branch = AsyncMock(return_value=GitBranch(
            id=str(uuid.uuid4()),
            name="Async Branch",
            description="Created async",
            project_id=project.id,
            created_at=datetime.now(timezone.utc)
        ))
        
        git_branch = await project.create_git_branch_async(
            git_branch_repository=mock_repo,
            branch_name="feature/async",
            description="Async branch"
        )
        
        assert git_branch.id in project.git_branchs
        mock_repo.find_by_name.assert_called_once_with(project.id, "feature/async")
        mock_repo.create_branch.assert_called_once_with(
            project_id=project.id,
            branch_name="feature/async",
            description="Async branch"
        )
    
    @pytest.mark.asyncio
    async def test_create_git_branch_async_duplicate(self):
        """Test async git branch creation fails for duplicates."""
        project = Project.create(name="Test Project")
        
        # Mock repository returning existing branch
        existing_branch = GitBranch(
            id=str(uuid.uuid4()),
            name="Existing",
            description="Already exists",
            project_id=project.id,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_repo = Mock()
        mock_repo.find_by_name = AsyncMock(return_value=existing_branch)
        
        with pytest.raises(ValueError, match="Git branch feature/existing already exists"):
            await project.create_git_branch_async(
                git_branch_repository=mock_repo,
                branch_name="feature/existing",
                description="Duplicate"
            )


class TestAgentManagement:
    """Test cases for agent registration and assignment."""
    
    def test_register_agent(self):
        """Test registering an agent to the project."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        
        original_updated = project.updated_at
        project.register_agent(agent)
        
        assert agent.id in project.registered_agents
        assert project.registered_agents[agent.id] == agent
        assert project.updated_at > original_updated
    
    def test_assign_agent_to_tree(self):
        """Test assigning an agent to a git branch."""
        project = Project.create(name="Test Project")
        
        # Create agent and git branch
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        # Assign agent to tree
        project.assign_agent_to_tree(agent.id, git_branch.id)
        
        assert project.agent_assignments[git_branch.id] == agent.id
    
    def test_assign_unregistered_agent(self):
        """Test assigning unregistered agent fails."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        with pytest.raises(ValueError, match="Agent unregistered-agent not registered"):
            project.assign_agent_to_tree("unregistered-agent", git_branch.id)
    
    def test_assign_agent_to_nonexistent_tree(self):
        """Test assigning agent to non-existent tree fails."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        with pytest.raises(ValueError, match="Task tree nonexistent-tree not found"):
            project.assign_agent_to_tree(agent.id, "nonexistent-tree")
    
    def test_reassign_agent_to_same_tree(self):
        """Test reassigning same agent to same tree succeeds."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        # First assignment
        project.assign_agent_to_tree(agent.id, git_branch.id)
        
        # Second assignment (same agent) should succeed
        project.assign_agent_to_tree(agent.id, git_branch.id)
        assert project.agent_assignments[git_branch.id] == agent.id
    
    def test_assign_different_agent_to_assigned_tree(self):
        """Test assigning different agent to already assigned tree fails."""
        project = Project.create(name="Test Project")
        
        # Create two agents
        agent1 = Agent(
            id="agent-1",
            name="Agent 1",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        agent2 = Agent(
            id="agent-2",
            name="Agent 2",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        
        project.register_agent(agent1)
        project.register_agent(agent2)
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        # Assign first agent
        project.assign_agent_to_tree(agent1.id, git_branch.id)
        
        # Assign second agent should fail
        with pytest.raises(ValueError, match="already assigned to agent agent-1"):
            project.assign_agent_to_tree(agent2.id, git_branch.id)


class TestCrossTreeDependencies:
    """Test cases for cross-tree dependency management."""
    
    def test_add_cross_tree_dependency(self):
        """Test adding cross-tree dependency between tasks."""
        project = Project.create(name="Test Project")
        
        # Create two git branches with tasks
        branch1 = project.create_git_branch(
            git_branch_name="feature/auth",
            name="Auth Branch",
            description="Auth"
        )
        branch2 = project.create_git_branch(
            git_branch_name="feature/ui",
            name="UI Branch",
            description="UI"
        )
        
        # Mock tasks in branches
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        with patch.object(project, '_find_git_branch') as mock_find:
            mock_find.side_effect = lambda task_id: branch1 if task_id == project._normalize_task_id(task1_id) else branch2
            
            project.add_cross_tree_dependency(task2_id, task1_id)
            
            normalized_task2 = project._normalize_task_id(task2_id)
            normalized_task1 = project._normalize_task_id(task1_id)
            
            assert normalized_task2 in project.cross_tree_dependencies
            assert normalized_task1 in project.cross_tree_dependencies[normalized_task2]
    
    def test_add_cross_tree_dependency_same_tree_fails(self):
        """Test adding dependency between tasks in same tree fails."""
        project = Project.create(name="Test Project")
        
        branch = project.create_git_branch(
            git_branch_name="feature/auth",
            name="Auth Branch",
            description="Auth"
        )
        
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        with patch.object(project, '_find_git_branch') as mock_find:
            # Both tasks in same branch
            mock_find.return_value = branch
            
            with pytest.raises(ValueError, match="Use regular task dependencies for tasks within the same tree"):
                project.add_cross_tree_dependency(task2_id, task1_id)
    
    def test_add_cross_tree_dependency_nonexistent_task(self):
        """Test adding dependency with non-existent task fails."""
        project = Project.create(name="Test Project")
        
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        with patch.object(project, '_find_git_branch') as mock_find:
            # One task not found
            mock_find.side_effect = lambda task_id: None
            
            with pytest.raises(ValueError, match="One or both tasks not found in project"):
                project.add_cross_tree_dependency(task2_id, task1_id)
    
    def test_coordinate_cross_tree_dependencies(self):
        """Test coordinating cross-tree dependencies."""
        project = Project.create(name="Test Project")
        
        # Set up mock dependencies
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        project.cross_tree_dependencies = {
            task2_id: {task1_id}
        }
        
        # Mock task lookup
        mock_task1 = Mock()
        mock_task1.status.is_done.return_value = True
        
        mock_branch1 = Mock()
        mock_branch1.get_task.return_value = mock_task1
        
        mock_branch2 = Mock()
        
        with patch.object(project, '_find_git_branch') as mock_find:
            mock_find.side_effect = lambda task_id: mock_branch1 if task_id == task1_id else mock_branch2
            
            result = project.coordinate_cross_tree_dependencies()
            
            assert result["total_dependencies"] == 1
            assert result["validated_dependencies"] == 1
            assert task2_id in result["ready_tasks"]
            assert task2_id not in result["blocked_tasks"]


class TestWorkSessionManagement:
    """Test cases for work session management."""
    
    def test_start_work_session(self):
        """Test starting a work session."""
        project = Project.create(name="Test Project")
        
        # Create and register agent
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        # Create git branch and assign agent
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        project.assign_agent_to_tree(agent.id, git_branch.id)
        
        task_id = str(uuid.uuid4())
        
        with patch.object(project, '_find_git_branch') as mock_find:
            mock_find.return_value = git_branch
            
            with patch('fastmcp.task_management.domain.entities.work_session.WorkSession.create_session') as mock_create:
                mock_session = Mock()
                mock_session.id = "session-123"
                mock_session.agent_id = agent.id
                mock_create.return_value = mock_session
                
                session = project.start_work_session(agent.id, task_id)
                
                assert session == mock_session
                assert session.id in project.active_work_sessions
                mock_create.assert_called_once_with(
                    agent_id=agent.id,
                    task_id=task_id,
                    git_branch_name=git_branch.id,
                    max_duration_hours=None
                )
    
    def test_start_work_session_unregistered_agent(self):
        """Test starting work session with unregistered agent fails."""
        project = Project.create(name="Test Project")
        
        with pytest.raises(ValueError, match="Agent unregistered-agent not registered"):
            project.start_work_session("unregistered-agent", "task-123")
    
    def test_start_work_session_task_not_found(self):
        """Test starting work session with non-existent task fails."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        with patch.object(project, '_find_git_branch', return_value=None):
            with pytest.raises(ValueError, match="Task nonexistent-task not found"):
                project.start_work_session(agent.id, "nonexistent-task")
    
    def test_start_work_session_agent_not_assigned(self):
        """Test starting work session when agent not assigned to tree fails."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        # Not assigning agent to branch
        
        task_id = str(uuid.uuid4())
        
        with patch.object(project, '_find_git_branch', return_value=git_branch):
            with pytest.raises(ValueError, match=f"Agent {agent.id} not assigned to tree {git_branch.id}"):
                project.start_work_session(agent.id, task_id)


class TestUtilityMethods:
    """Test cases for utility methods."""
    
    def test_normalize_task_id_hex_format(self):
        """Test normalizing hex format task ID to canonical UUID."""
        project = Project.create(name="Test Project")
        
        hex_id = "550e8400e29b41d4a716446655440000"
        canonical_id = "550e8400-e29b-41d4-a716-446655440000"
        
        normalized = project._normalize_task_id(hex_id)
        assert normalized == canonical_id
    
    def test_normalize_task_id_already_canonical(self):
        """Test normalizing already canonical UUID."""
        project = Project.create(name="Test Project")
        
        canonical_id = "550e8400-e29b-41d4-a716-446655440000"
        normalized = project._normalize_task_id(canonical_id)
        assert normalized == canonical_id
    
    def test_find_git_branch_task_exists(self):
        """Test finding git branch containing a specific task."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        task_id = str(uuid.uuid4())
        
        with patch.object(git_branch, 'has_task', return_value=True):
            found_branch = project._find_git_branch(task_id)
            assert found_branch == git_branch
    
    def test_find_git_branch_task_not_found(self):
        """Test finding git branch when task doesn't exist."""
        project = Project.create(name="Test Project")
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        
        task_id = str(uuid.uuid4())
        
        with patch.object(git_branch, 'has_task', return_value=False):
            found_branch = project._find_git_branch(task_id)
            assert found_branch is None
    
    def test_is_task_ready_for_work_no_dependencies(self):
        """Test task readiness with no cross-tree dependencies."""
        project = Project.create(name="Test Project")
        
        task_id = str(uuid.uuid4())
        assert project._is_task_ready_for_work(task_id) is True
    
    def test_is_task_ready_for_work_with_completed_dependencies(self):
        """Test task readiness with completed dependencies."""
        project = Project.create(name="Test Project")
        
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        # Set up dependency
        project.cross_tree_dependencies = {
            task2_id: {task1_id}
        }
        
        # Mock completed prerequisite task
        mock_task = Mock()
        mock_task.status.is_done.return_value = True
        
        mock_branch = Mock()
        mock_branch.get_task.return_value = mock_task
        
        with patch.object(project, '_find_git_branch', return_value=mock_branch):
            assert project._is_task_ready_for_work(task2_id) is True
    
    def test_is_task_ready_for_work_with_incomplete_dependencies(self):
        """Test task readiness with incomplete dependencies."""
        project = Project.create(name="Test Project")
        
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        # Set up dependency
        project.cross_tree_dependencies = {
            task2_id: {task1_id}
        }
        
        # Mock incomplete prerequisite task
        mock_task = Mock()
        mock_task.status.is_done.return_value = False
        
        mock_branch = Mock()
        mock_branch.get_task.return_value = mock_task
        
        with patch.object(project, '_find_git_branch', return_value=mock_branch):
            assert project._is_task_ready_for_work(task2_id) is False


class TestOrchestrationStatus:
    """Test cases for orchestration status reporting."""
    
    def test_get_orchestration_status_empty_project(self):
        """Test orchestration status for empty project."""
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
        """Test orchestration status with project data."""
        project = Project.create(name="Active Project")
        
        # Add agent
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        # Add git branch
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        project.assign_agent_to_tree(agent.id, git_branch.id)
        
        # Mock git branch methods
        with patch.object(git_branch, 'get_task_count', return_value=5):
            with patch.object(git_branch, 'get_completed_task_count', return_value=2):
                with patch.object(git_branch, 'get_progress_percentage', return_value=40.0):
                    
                    status = project.get_orchestration_status()
                    
                    assert status["total_branches"] == 1
                    assert status["registered_agents"] == 1
                    assert status["active_assignments"] == 1
                    assert status["cross_tree_dependencies"] == 0
                    
                    # Check branch info
                    assert git_branch.id in status["branches"]
                    branch_info = status["branches"][git_branch.id]
                    assert branch_info["name"] == "Test Branch"
                    assert branch_info["assigned_agent"] == agent.id
                    assert branch_info["total_tasks"] == 5
                    assert branch_info["completed_tasks"] == 2
                    assert branch_info["progress"] == 40.0
                    
                    # Check agent info
                    assert agent.id in status["agents"]
                    agent_info = status["agents"][agent.id]
                    assert agent_info["name"] == "Test Agent"
                    assert AgentCapability.PROJECT_MANAGEMENT.value in agent_info["capabilities"]
                    assert git_branch.id in agent_info["assigned_trees"]


class TestGetAvailableWork:
    """Test cases for getting available work for agents."""
    
    def test_get_available_work_unregistered_agent(self):
        """Test getting work for unregistered agent fails."""
        project = Project.create(name="Test Project")
        
        with pytest.raises(ValueError, match="Agent unregistered-agent not registered"):
            project.get_available_work_for_agent("unregistered-agent")
    
    def test_get_available_work_no_assignments(self):
        """Test getting work when agent has no assignments."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        available_tasks = project.get_available_work_for_agent(agent.id)
        assert available_tasks == []
    
    def test_get_available_work_with_assignments(self):
        """Test getting available work with assignments."""
        project = Project.create(name="Test Project")
        
        agent = Agent(
            id="agent-123",
            name="Test Agent",
            capabilities={AgentCapability.PROJECT_MANAGEMENT},
            project_id=project.id
        )
        project.register_agent(agent)
        
        git_branch = project.create_git_branch(
            git_branch_name="feature/test",
            name="Test Branch",
            description="Test"
        )
        project.assign_agent_to_tree(agent.id, git_branch.id)
        
        # Mock available tasks
        mock_task1 = Mock()
        mock_task1.id.value = "task-1"
        mock_task2 = Mock()
        mock_task2.id.value = "task-2"
        
        available_branch_tasks = [mock_task1, mock_task2]
        
        with patch.object(git_branch, 'get_available_tasks', return_value=available_branch_tasks):
            with patch.object(project, '_is_task_ready_for_work', return_value=True):
                
                available_tasks = project.get_available_work_for_agent(agent.id)
                
                assert len(available_tasks) == 2
                assert mock_task1 in available_tasks
                assert mock_task2 in available_tasks


if __name__ == "__main__":
    pytest.main([__file__])