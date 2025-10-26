"""Test suite for Project Domain Entity"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import uuid
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.agent import Agent
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.value_objects.agent_roles import AgentRole
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository


@pytest.fixture
def project():
    """Create a test project"""
    return Project(
        id="test-project-id",
        name="Test Project",
        description="Test Description"
    )


@pytest.fixture
def mock_git_branch():
    """Create a mock git branch"""
    branch = Mock(spec=GitBranch)
    branch.id = "branch-123"
    branch.name = "feature/test"
    branch.git_branch_name = "feature/test"
    branch.project_id = "test-project-id"
    branch.has_task = Mock(return_value=True)
    branch.get_task = Mock()
    branch.get_available_tasks = Mock(return_value=[])
    branch.get_task_count = Mock(return_value=5)
    branch.get_completed_task_count = Mock(return_value=2)
    branch.get_progress_percentage = Mock(return_value=40.0)
    return branch


@pytest.fixture
def mock_agent():
    """Create a mock agent"""
    agent = Mock(spec=Agent)
    agent.id = "agent-123"
    agent.name = "Test Agent"
    agent.capabilities = {AgentRole.TASK_PLANNING}
    agent.created_at = datetime.now(timezone.utc)
    return agent


@pytest.fixture
def mock_git_branch_repository():
    """Create a mock git branch repository"""
    repo = Mock(spec=GitBranchRepository)
    repo.find_by_name = AsyncMock()
    repo.create_branch = AsyncMock()
    return repo


class TestProjectEntity:
    """Test cases for Project entity"""
    
    def test_init_with_required_fields(self):
        """Test project initialization with required fields"""
        # Act
        project = Project(
            id="proj-123",
            name="My Project",
            description="My Description"
        )
        
        # Assert
        assert project.id == "proj-123"
        assert project.name == "My Project"
        assert project.description == "My Description"
        assert project.git_branchs == {}
        assert project.registered_agents == {}
        assert project.agent_assignments == {}
    
    def test_get_entity_id(self, project):
        """Test _get_entity_id returns project id"""
        # Act
        entity_id = project._get_entity_id()
        
        # Assert
        assert entity_id == "test-project-id"
    
    def test_get_entity_id_when_empty(self):
        """Test _get_entity_id returns unknown when id is empty"""
        # Arrange - Must provide valid name due to __post_init__ validation
        project = Project(name="Test Project")

        # Act
        entity_id = project._get_entity_id()

        # Assert
        assert entity_id == "unknown"
    
    def test_create_class_method(self):
        """Test create class method generates UUID"""
        # Act
        with patch('fastmcp.task_management.domain.value_objects.base_entity_id.uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            project = Project.create(
                name="New Project",
                description="New Description"
            )

        # Assert
        assert str(project.id) == "12345678-1234-5678-1234-567812345678"
        assert project.name == "New Project"
        assert project.description == "New Description"
    
    def test_hash(self, project):
        """Test project is hashable"""
        # Act
        hash_value = hash(project)
        
        # Assert
        assert isinstance(hash_value, int)
        assert hash(project) == hash(project.id)
    
    def test_validate_entity_empty_name_raises_error(self):
        """Test validation fails with empty name during construction"""
        # Act & Assert - Validation happens in __post_init__
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            project = Project(id="123", name="", description="desc")
    
    def test_validate_entity_whitespace_name_raises_error(self):
        """Test validation fails with whitespace-only name during construction"""
        # Act & Assert - Validation happens in __post_init__
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            project = Project(id="123", name="   ", description="desc")
    
    @pytest.mark.asyncio
    async def test_create_git_branch_async_success(self, project, mock_git_branch_repository):
        """Test async git branch creation"""
        # Arrange
        new_branch = Mock(spec=GitBranch)
        new_branch.id = "new-branch-id"
        new_branch.name = "feature/new"
        mock_git_branch_repository.find_by_name.return_value = None
        mock_git_branch_repository.create_branch.return_value = new_branch
        
        # Act
        result = await project.create_git_branch_async(
            mock_git_branch_repository,
            "feature/new",
            "New feature branch"
        )
        
        # Assert
        assert result == new_branch
        assert project.git_branchs["new-branch-id"] == new_branch
        mock_git_branch_repository.find_by_name.assert_called_once_with(str(project.id), "feature/new")
        mock_git_branch_repository.create_branch.assert_called_once_with(
            project_id=str(project.id),
            branch_name="feature/new",
            description="New feature branch"
        )
    
    @pytest.mark.asyncio
    async def test_create_git_branch_async_already_exists(self, project, mock_git_branch_repository):
        """Test async git branch creation when branch already exists"""
        # Arrange
        existing_branch = Mock()
        mock_git_branch_repository.find_by_name.return_value = existing_branch
        
        # Act & Assert
        with pytest.raises(ValueError, match="Git branch feature/existing already exists"):
            await project.create_git_branch_async(
                mock_git_branch_repository,
                "feature/existing",
                "Description"
            )
    
    def test_create_git_branch_legacy_success(self, project):
        """Test legacy git branch creation"""
        # Act
        with patch('fastmcp.task_management.domain.value_objects.base_entity_id.uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            branch = project.create_git_branch(
                git_branch_name="feature/test",
                name="Test Feature",
                description="Feature description"
            )

        # Assert
        assert str(branch.id) == "12345678-1234-5678-1234-567812345678"
        assert branch.name == "Test Feature"
        assert branch.git_branch_name == "feature/test"
        assert str(branch.project_id) == str(project.id)
        assert project.git_branchs[str(branch.id)] == branch
    
    def test_create_git_branch_legacy_duplicate_name(self, project, mock_git_branch):
        """Test legacy git branch creation with duplicate name"""
        # Arrange
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        
        # Act & Assert
        with pytest.raises(ValueError, match="Git branch feature/test already exists"):
            project.create_git_branch(
                git_branch_name="feature/test",
                name="Another Test",
                description="Another description"
            )
    
    def test_add_git_branch(self, project, mock_git_branch):
        """Test adding a git branch"""
        # Act
        project.add_git_branch(mock_git_branch)
        
        # Assert
        assert project.git_branchs[mock_git_branch.id] == mock_git_branch
    
    def test_get_git_branch_by_name(self, project, mock_git_branch):
        """Test getting git branch by name"""
        # Arrange
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        
        # Act
        result = project.get_git_branch("feature/test")
        
        # Assert
        assert result == mock_git_branch
    
    def test_get_git_branch_not_found(self, project):
        """Test getting non-existent git branch"""
        # Act
        result = project.get_git_branch("non-existent")
        
        # Assert
        assert result is None
    
    def test_register_agent(self, project, mock_agent):
        """Test registering an agent"""
        # Act
        project.register_agent(mock_agent)
        
        # Assert
        assert project.registered_agents[mock_agent.id] == mock_agent
    
    def test_assign_agent_to_tree_success(self, project, mock_agent, mock_git_branch):
        """Test successful agent assignment to tree"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        
        # Act
        project.assign_agent_to_tree(mock_agent.id, mock_git_branch.id)
        
        # Assert
        assert project.agent_assignments[mock_git_branch.id] == mock_agent.id
    
    def test_assign_agent_to_tree_agent_not_registered(self, project, mock_git_branch):
        """Test agent assignment when agent not registered"""
        # Arrange
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        
        # Act & Assert
        with pytest.raises(ValueError, match="Agent unregistered-agent not registered"):
            project.assign_agent_to_tree("unregistered-agent", mock_git_branch.id)
    
    def test_assign_agent_to_tree_tree_not_found(self, project, mock_agent):
        """Test agent assignment when tree not found"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        
        # Act & Assert
        with pytest.raises(ValueError, match="Task tree non-existent not found"):
            project.assign_agent_to_tree(mock_agent.id, "non-existent")
    
    def test_assign_agent_to_tree_already_assigned(self, project, mock_agent, mock_git_branch):
        """Test agent assignment when tree already assigned to different agent"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.registered_agents["other-agent"] = Mock()
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project.agent_assignments[mock_git_branch.id] = "other-agent"
        
        # Act & Assert
        with pytest.raises(ValueError, match="already assigned to agent other-agent"):
            project.assign_agent_to_tree(mock_agent.id, mock_git_branch.id)
    
    def test_assign_agent_to_tree_same_agent(self, project, mock_agent, mock_git_branch):
        """Test reassigning same agent to tree succeeds"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project.agent_assignments[mock_git_branch.id] = mock_agent.id
        
        # Act - should not raise
        project.assign_agent_to_tree(mock_agent.id, mock_git_branch.id)
        
        # Assert
        assert project.agent_assignments[mock_git_branch.id] == mock_agent.id
    
    def test_add_cross_tree_dependency_success(self, project):
        """Test adding cross-tree dependency"""
        # Arrange
        branch1 = Mock(spec=GitBranch)
        branch1.id = "branch-1"
        branch1.has_task = Mock(return_value=True)
        
        branch2 = Mock(spec=GitBranch)
        branch2.id = "branch-2"
        branch2.has_task = Mock(return_value=True)
        
        project.git_branchs = {"branch-1": branch1, "branch-2": branch2}
        
        # Mock _find_git_branch to return different branches
        project._find_git_branch = Mock(side_effect=lambda task_id: branch1 if task_id == "task-1" else branch2)
        
        # Act
        project.add_cross_tree_dependency("task-1", "task-2")
        
        # Assert
        assert "task-1" in project.cross_tree_dependencies
        assert "task-2" in project.cross_tree_dependencies["task-1"]
    
    def test_add_cross_tree_dependency_same_tree_error(self, project):
        """Test adding dependency within same tree raises error"""
        # Arrange
        branch = Mock(spec=GitBranch)
        branch.id = "branch-1"
        branch.has_task = Mock(return_value=True)
        
        project.git_branchs = {"branch-1": branch}
        project._find_git_branch = Mock(return_value=branch)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Use regular task dependencies"):
            project.add_cross_tree_dependency("task-1", "task-2")
    
    def test_add_cross_tree_dependency_task_not_found(self, project):
        """Test adding dependency when task not found"""
        # Arrange
        project._find_git_branch = Mock(return_value=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="One or both tasks not found"):
            project.add_cross_tree_dependency("task-1", "task-2")
    
    def test_normalize_task_id_hex_format(self, project):
        """Test normalizing hex format task ID to canonical UUID"""
        # Arrange
        hex_id = "12345678123456781234567812345678"
        
        # Act
        result = project._normalize_task_id(hex_id)
        
        # Assert
        assert result == "12345678-1234-5678-1234-567812345678"
    
    def test_normalize_task_id_already_canonical(self, project):
        """Test normalizing already canonical task ID"""
        # Arrange
        canonical_id = "12345678-1234-5678-1234-567812345678"
        
        # Act
        result = project._normalize_task_id(canonical_id)
        
        # Assert
        assert result == canonical_id
    
    def test_find_git_branch_found(self, project, mock_git_branch):
        """Test finding git branch containing a task"""
        # Arrange
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        mock_git_branch.has_task.return_value = True
        
        # Act
        result = project._find_git_branch("task-123")
        
        # Assert
        assert result == mock_git_branch
    
    def test_find_git_branch_not_found(self, project, mock_git_branch):
        """Test finding git branch when task not found"""
        # Arrange
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        mock_git_branch.has_task.return_value = False
        
        # Act
        result = project._find_git_branch("task-123")
        
        # Assert
        assert result is None
    
    def test_is_task_ready_for_work_no_dependencies(self, project):
        """Test task readiness when no cross-tree dependencies"""
        # Act
        result = project._is_task_ready_for_work("task-123")
        
        # Assert
        assert result is True
    
    def test_is_task_ready_for_work_dependencies_met(self, project):
        """Test task readiness when dependencies are met"""
        # Arrange
        project.cross_tree_dependencies["task-123"] = {"prereq-task"}
        
        # Mock prerequisite task as done
        prereq_task = Mock()
        prereq_task.status = Mock()
        prereq_task.status.is_done = Mock(return_value=True)
        
        branch = Mock()
        branch.get_task = Mock(return_value=prereq_task)
        
        project._find_git_branch = Mock(return_value=branch)
        
        # Act
        result = project._is_task_ready_for_work("task-123")
        
        # Assert
        assert result is True
    
    def test_is_task_ready_for_work_dependencies_not_met(self, project):
        """Test task readiness when dependencies are not met"""
        # Arrange
        project.cross_tree_dependencies["task-123"] = {"prereq-task"}
        
        # Mock prerequisite task as not done
        prereq_task = Mock()
        prereq_task.status = Mock()
        prereq_task.status.is_done = Mock(return_value=False)
        
        branch = Mock()
        branch.get_task = Mock(return_value=prereq_task)
        
        project._find_git_branch = Mock(return_value=branch)
        
        # Act
        result = project._is_task_ready_for_work("task-123")
        
        # Assert
        assert result is False
    
    def test_is_task_ready_for_work_dict_task_done(self, project):
        """Test task readiness with dict task representation (done)"""
        # Arrange
        project.cross_tree_dependencies["task-123"] = {"prereq-task"}
        
        # Mock prerequisite task as dict
        prereq_task = {"status": "done"}
        
        branch = Mock()
        branch.get_task = Mock(return_value=prereq_task)
        
        project._find_git_branch = Mock(return_value=branch)
        
        # Act
        result = project._is_task_ready_for_work("task-123")
        
        # Assert
        assert result is True
    
    def test_is_task_ready_for_work_dict_task_not_done(self, project):
        """Test task readiness with dict task representation (not done)"""
        # Arrange
        project.cross_tree_dependencies["task-123"] = {"prereq-task"}
        
        # Mock prerequisite task as dict
        prereq_task = {"status": "in_progress"}
        
        branch = Mock()
        branch.get_task = Mock(return_value=prereq_task)
        
        project._find_git_branch = Mock(return_value=branch)
        
        # Act
        result = project._is_task_ready_for_work("task-123")
        
        # Assert
        assert result is False
    
    def test_get_available_work_for_agent(self, project, mock_agent, mock_git_branch):
        """Test getting available work for agent"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project.agent_assignments[mock_git_branch.id] = mock_agent.id
        
        task1 = Mock()
        task1.id = Mock()
        task1.id.value = "task-1"
        
        task2 = Mock()
        task2.id = Mock()
        task2.id.value = "task-2"
        
        mock_git_branch.get_available_tasks.return_value = [task1, task2]
        project._is_task_ready_for_work = Mock(return_value=True)
        
        # Act
        result = project.get_available_work_for_agent(mock_agent.id)
        
        # Assert
        assert len(result) == 2
        assert task1 in result
        assert task2 in result
    
    def test_get_available_work_for_agent_unregistered(self, project):
        """Test getting work for unregistered agent"""
        # Act & Assert
        with pytest.raises(ValueError, match="Agent unknown not registered"):
            project.get_available_work_for_agent("unknown")
    
    def test_start_work_session_success(self, project, mock_agent, mock_git_branch):
        """Test starting work session"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project.agent_assignments[mock_git_branch.id] = mock_agent.id
        project._find_git_branch = Mock(return_value=mock_git_branch)
        
        # Act
        with patch('fastmcp.task_management.domain.entities.work_session.WorkSession.create_session') as mock_create:
            mock_session = Mock(spec=WorkSession)
            mock_session.id = "session-123"
            mock_create.return_value = mock_session
            
            result = project.start_work_session(mock_agent.id, "task-123", max_duration_hours=2.0)
        
        # Assert
        assert result == mock_session
        assert project.active_work_sessions["session-123"] == mock_session
        mock_create.assert_called_once_with(
            agent_id=mock_agent.id,
            task_id="task-123",
            git_branch_name=mock_git_branch.id,
            max_duration_hours=2.0
        )
    
    def test_start_work_session_agent_not_registered(self, project):
        """Test starting work session with unregistered agent"""
        # Act & Assert
        with pytest.raises(ValueError, match="Agent unknown not registered"):
            project.start_work_session("unknown", "task-123")
    
    def test_start_work_session_task_not_found(self, project, mock_agent):
        """Test starting work session with non-existent task"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project._find_git_branch = Mock(return_value=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Task unknown-task not found"):
            project.start_work_session(mock_agent.id, "unknown-task")
    
    def test_start_work_session_agent_not_assigned(self, project, mock_agent, mock_git_branch):
        """Test starting work session when agent not assigned to tree"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project._find_git_branch = Mock(return_value=mock_git_branch)
        # No assignment
        
        # Act & Assert
        with pytest.raises(ValueError, match=f"Agent {mock_agent.id} not assigned to tree"):
            project.start_work_session(mock_agent.id, "task-123")
    
    def test_get_orchestration_status(self, project, mock_agent, mock_git_branch):
        """Test getting orchestration status"""
        # Arrange
        project.registered_agents[mock_agent.id] = mock_agent
        project.git_branchs[mock_git_branch.id] = mock_git_branch
        project.agent_assignments[mock_git_branch.id] = mock_agent.id
        
        session = Mock(spec=WorkSession)
        session.id = "session-123"
        session.agent_id = mock_agent.id
        project.active_work_sessions["session-123"] = session
        
        project.cross_tree_dependencies["task-1"] = {"task-2", "task-3"}
        project.resource_locks["resource-1"] = mock_agent.id
        
        # Act
        status = project.get_orchestration_status()
        
        # Assert
        assert status["project_id"] == project.id
        assert status["project_name"] == project.name
        assert status["total_branches"] == 1
        assert status["registered_agents"] == 1
        assert status["active_assignments"] == 1
        assert status["active_sessions"] == 1
        assert status["cross_tree_dependencies"] == 2
        assert status["resource_locks"] == 1
        
        # Check branch details
        assert mock_git_branch.id in status["branches"]
        branch_status = status["branches"][mock_git_branch.id]
        assert branch_status["name"] == mock_git_branch.name
        assert branch_status["assigned_agent"] == mock_agent.id
        
        # Check agent details
        assert mock_agent.id in status["agents"]
        agent_status = status["agents"][mock_agent.id]
        assert agent_status["name"] == mock_agent.name
        assert mock_git_branch.id in agent_status["assigned_trees"]
        assert "session-123" in agent_status["active_sessions"]
    
    def test_coordinate_cross_tree_dependencies(self, project):
        """Test coordinating cross-tree dependencies"""
        # Arrange
        # Setup prerequisite task (done)
        prereq_task = Mock()
        prereq_task.status = Mock()
        prereq_task.status.is_done = Mock(return_value=True)
        
        prereq_branch = Mock()
        prereq_branch.get_task = Mock(return_value=prereq_task)
        
        # Setup dependent task
        dependent_branch = Mock()
        
        # Setup cross-tree dependencies
        project.cross_tree_dependencies["task-1"] = {"prereq-task"}
        
        # Mock _find_git_branch
        def find_branch(task_id):
            if task_id == "task-1":
                return dependent_branch
            elif task_id == "prereq-task":
                return prereq_branch
            return None
        
        project._find_git_branch = Mock(side_effect=find_branch)
        
        # Act
        result = project.coordinate_cross_tree_dependencies()
        
        # Assert
        assert result["total_dependencies"] == 1
        assert result["validated_dependencies"] == 1
        assert "task-1" in result["ready_tasks"]
        assert len(result["blocked_tasks"]) == 0
    
    def test_coordinate_cross_tree_dependencies_blocked(self, project):
        """Test coordinating dependencies with blocked task"""
        # Arrange
        # Setup prerequisite task (not done)
        prereq_task = {"status": "in_progress"}
        
        prereq_branch = Mock()
        prereq_branch.get_task = Mock(return_value=prereq_task)
        
        # Setup dependent task
        dependent_branch = Mock()
        
        # Setup cross-tree dependencies
        project.cross_tree_dependencies["task-1"] = {"prereq-task"}
        
        # Mock _find_git_branch
        def find_branch(task_id):
            if task_id == "task-1":
                return dependent_branch
            elif task_id == "prereq-task":
                return prereq_branch
            return None
        
        project._find_git_branch = Mock(side_effect=find_branch)
        
        # Act
        result = project.coordinate_cross_tree_dependencies()
        
        # Assert
        assert result["total_dependencies"] == 1
        assert result["validated_dependencies"] == 1
        assert "task-1" in result["blocked_tasks"]
        assert len(result["ready_tasks"]) == 0
    
    def test_coordinate_cross_tree_dependencies_missing_task(self, project):
        """Test coordinating dependencies with missing task"""
        # Arrange
        project.cross_tree_dependencies["missing-task"] = {"prereq-task"}
        project._find_git_branch = Mock(return_value=None)
        
        # Act
        result = project.coordinate_cross_tree_dependencies()
        
        # Assert
        assert result["total_dependencies"] == 1
        assert len(result["missing_prerequisites"]) == 1
        assert result["missing_prerequisites"][0]["task_id"] == "missing-task"
        assert "not found" in result["missing_prerequisites"][0]["issue"]