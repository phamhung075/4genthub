"""Test suite for Agent Domain Entity"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.entities.agent import (
    Agent,
    AgentStatus,
    AgentCapability
)


class TestAgentStatus:
    """Test suite for AgentStatus enum"""

    def test_agent_status_values(self):
        """Test AgentStatus enum values"""
        assert AgentStatus.AVAILABLE.value == "available"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.PAUSED.value == "paused"

    def test_agent_status_enumeration(self):
        """Test AgentStatus enumeration"""
        statuses = list(AgentStatus)
        assert len(statuses) == 4
        assert AgentStatus.AVAILABLE in statuses
        assert AgentStatus.BUSY in statuses
        assert AgentStatus.OFFLINE in statuses
        assert AgentStatus.PAUSED in statuses


class TestAgentCapability:
    """Test suite for AgentCapability enum"""

    def test_agent_capability_values(self):
        """Test AgentCapability enum values"""
        assert AgentCapability.FRONTEND_DEVELOPMENT.value == "frontend_development"
        assert AgentCapability.BACKEND_DEVELOPMENT.value == "backend_development"
        assert AgentCapability.DEVOPS.value == "devops"
        assert AgentCapability.TESTING.value == "testing"
        assert AgentCapability.SECURITY.value == "security"
        assert AgentCapability.DOCUMENTATION.value == "documentation"
        assert AgentCapability.ARCHITECTURE.value == "architecture"
        assert AgentCapability.CODE_REVIEW.value == "code_review"
        assert AgentCapability.PROJECT_MANAGEMENT.value == "project_management"
        assert AgentCapability.DATA_ANALYSIS.value == "data_analysis"

    def test_agent_capability_enumeration(self):
        """Test AgentCapability enumeration completeness"""
        capabilities = list(AgentCapability)
        assert len(capabilities) == 10
        
        expected_capabilities = {
            AgentCapability.FRONTEND_DEVELOPMENT,
            AgentCapability.BACKEND_DEVELOPMENT,
            AgentCapability.DEVOPS,
            AgentCapability.TESTING,
            AgentCapability.SECURITY,
            AgentCapability.DOCUMENTATION,
            AgentCapability.ARCHITECTURE,
            AgentCapability.CODE_REVIEW,
            AgentCapability.PROJECT_MANAGEMENT,
            AgentCapability.DATA_ANALYSIS
        }
        
        assert set(capabilities) == expected_capabilities


class TestAgentInitialization:
    """Test suite for Agent initialization"""

    def test_minimal_agent_creation(self):
        """Test creating agent with minimal required parameters"""
        agent_id = "agent_123"
        name = "Test Agent"
        
        agent = Agent(id=agent_id, name=name)
        
        assert agent.id == agent_id
        assert agent.name == name
        assert agent.description == ""
        assert agent.created_at is not None
        assert agent.updated_at is not None
        assert isinstance(agent.capabilities, set)
        assert len(agent.capabilities) == 0
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_workload == 0
        assert agent.max_concurrent_tasks == 1

    def test_agent_creation_with_all_parameters(self):
        """Test creating agent with all parameters"""
        agent_id = "agent_456"
        name = "Full Agent"
        description = "Comprehensive test agent"
        created_at = datetime.now(timezone.utc)
        capabilities = {AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.TESTING}
        specializations = ["React", "Jest"]
        preferred_languages = ["JavaScript", "TypeScript"]
        preferred_frameworks = ["React", "Next.js"]
        
        agent = Agent(
            id=agent_id,
            name=name,
            description=description,
            created_at=created_at,
            capabilities=capabilities,
            specializations=specializations,
            preferred_languages=preferred_languages,
            preferred_frameworks=preferred_frameworks,
            max_concurrent_tasks=3,
            timezone="America/New_York",
            priority_preference="high"
        )
        
        assert agent.id == agent_id
        assert agent.name == name
        assert agent.description == description
        assert agent.created_at == created_at
        assert agent.capabilities == capabilities
        assert agent.specializations == specializations
        assert agent.preferred_languages == preferred_languages
        assert agent.preferred_frameworks == preferred_frameworks
        assert agent.max_concurrent_tasks == 3
        assert agent.timezone == "America/New_York"
        assert agent.priority_preference == "high"

    def test_agent_post_init_sets_timestamps(self):
        """Test that __post_init__ sets default timestamps"""
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            agent = Agent(id="test", name="Test Agent")
            
            assert agent.created_at == mock_now
            assert agent.updated_at == mock_now
            assert mock_datetime.now.call_count == 2

    def test_agent_post_init_preserves_existing_timestamps(self):
        """Test that __post_init__ preserves existing timestamps"""
        created_at = datetime(2023, 12, 1, 10, 0, 0)
        updated_at = datetime(2023, 12, 2, 11, 0, 0)
        
        agent = Agent(
            id="test",
            name="Test Agent",
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert agent.created_at == created_at
        assert agent.updated_at == updated_at


class TestAgentCapabilityManagement:
    """Test suite for agent capability management"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="test_agent", name="Test Agent")

    def test_add_capability(self):
        """Test adding capability to agent"""
        capability = AgentCapability.FRONTEND_DEVELOPMENT
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.add_capability(capability)
            
            assert capability in self.agent.capabilities
            assert self.agent.updated_at == mock_now

    def test_add_duplicate_capability(self):
        """Test adding duplicate capability (should not duplicate)"""
        capability = AgentCapability.TESTING
        
        self.agent.add_capability(capability)
        initial_count = len(self.agent.capabilities)
        
        self.agent.add_capability(capability)  # Add again
        
        assert len(self.agent.capabilities) == initial_count
        assert capability in self.agent.capabilities

    def test_remove_capability(self):
        """Test removing capability from agent"""
        capability = AgentCapability.BACKEND_DEVELOPMENT
        
        # Add capability first
        self.agent.add_capability(capability)
        assert capability in self.agent.capabilities
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.remove_capability(capability)
            
            assert capability not in self.agent.capabilities
            assert self.agent.updated_at == mock_now

    def test_remove_nonexistent_capability(self):
        """Test removing capability that agent doesn't have"""
        capability = AgentCapability.DEVOPS
        
        # Ensure capability is not present
        assert capability not in self.agent.capabilities
        
        # Remove should not raise error
        self.agent.remove_capability(capability)
        
        assert capability not in self.agent.capabilities

    def test_has_capability(self):
        """Test checking if agent has capability"""
        capability = AgentCapability.SECURITY
        
        # Initially should not have capability
        assert not self.agent.has_capability(capability)
        
        # Add capability
        self.agent.add_capability(capability)
        
        # Now should have capability
        assert self.agent.has_capability(capability)


class TestAgentTaskHandling:
    """Test suite for agent task handling capabilities"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(
            id="task_agent",
            name="Task Handler",
            capabilities={AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.TESTING},
            preferred_languages=["JavaScript", "Python"],
            preferred_frameworks=["React", "Django"]
        )

    def test_can_handle_task_with_matching_capabilities(self):
        """Test can_handle_task with matching capabilities"""
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "languages": ["JavaScript"],
            "frameworks": ["React"]
        }
        
        assert self.agent.can_handle_task(task_requirements) is True

    def test_can_handle_task_with_missing_capability(self):
        """Test can_handle_task with missing capability"""
        task_requirements = {
            "capabilities": [AgentCapability.DEVOPS],
            "languages": ["JavaScript"],
            "frameworks": ["React"]
        }
        
        assert self.agent.can_handle_task(task_requirements) is False

    def test_can_handle_task_with_missing_language(self):
        """Test can_handle_task with missing language"""
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "languages": ["Go"],
            "frameworks": ["React"]
        }
        
        assert self.agent.can_handle_task(task_requirements) is False

    def test_can_handle_task_with_missing_framework(self):
        """Test can_handle_task with missing framework"""
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "languages": ["JavaScript"],
            "frameworks": ["Vue.js"]
        }
        
        assert self.agent.can_handle_task(task_requirements) is False

    def test_can_handle_task_with_string_capabilities(self):
        """Test can_handle_task with string capability values"""
        task_requirements = {
            "capabilities": ["frontend_development", "unknown_capability"],
            "languages": ["JavaScript"],
            "frameworks": ["React"]
        }
        
        assert self.agent.can_handle_task(task_requirements) is True

    def test_can_handle_task_with_no_requirements(self):
        """Test can_handle_task with empty requirements"""
        task_requirements = {}
        
        assert self.agent.can_handle_task(task_requirements) is True

    def test_can_handle_task_with_partial_language_match(self):
        """Test can_handle_task with partial language match"""
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "languages": ["Python", "Go"],  # Agent has Python but not Go
        }
        
        assert self.agent.can_handle_task(task_requirements) is True  # Any match is sufficient

    def test_can_handle_task_with_partial_framework_match(self):
        """Test can_handle_task with partial framework match"""
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "frameworks": ["Django", "Flask"],  # Agent has Django but not Flask
        }
        
        assert self.agent.can_handle_task(task_requirements) is True  # Any match is sufficient


class TestAgentAvailability:
    """Test suite for agent availability management"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="availability_agent", name="Availability Test", max_concurrent_tasks=2)

    def test_is_available_when_under_capacity(self):
        """Test is_available returns True when under capacity"""
        assert self.agent.current_workload == 0
        assert self.agent.max_concurrent_tasks == 2
        assert self.agent.status == AgentStatus.AVAILABLE
        
        assert self.agent.is_available() is True

    def test_is_available_when_at_capacity(self):
        """Test is_available returns False when at capacity"""
        self.agent.current_workload = 2
        self.agent.status = AgentStatus.BUSY
        
        assert self.agent.is_available() is False

    def test_is_available_when_paused(self):
        """Test is_available returns False when paused"""
        self.agent.status = AgentStatus.PAUSED
        
        assert self.agent.is_available() is False

    def test_is_available_when_offline(self):
        """Test is_available returns False when offline"""
        self.agent.status = AgentStatus.OFFLINE
        
        assert self.agent.is_available() is False


class TestAgentTaskAssignment:
    """Test suite for agent task assignment and management"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="task_mgmt_agent", name="Task Management Test", max_concurrent_tasks=2)

    def test_start_task_when_available(self):
        """Test starting task when agent is available"""
        task_id = "task_123"
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.start_task(task_id)
            
            assert task_id in self.agent.active_tasks
            assert self.agent.current_workload == 1
            assert self.agent.status == AgentStatus.AVAILABLE  # Still under capacity
            assert self.agent.updated_at == mock_now

    def test_start_task_reaches_capacity(self):
        """Test starting task that reaches capacity"""
        task_id1 = "task_1"
        task_id2 = "task_2"
        
        # Start first task
        self.agent.start_task(task_id1)
        assert self.agent.status == AgentStatus.AVAILABLE
        
        # Start second task (reaches capacity)
        self.agent.start_task(task_id2)
        assert self.agent.current_workload == 2
        assert self.agent.status == AgentStatus.BUSY

    def test_start_task_when_unavailable(self):
        """Test starting task when agent is unavailable"""
        self.agent.status = AgentStatus.OFFLINE
        
        with pytest.raises(ValueError, match="Agent .* is not available for new tasks"):
            self.agent.start_task("task_123")

    def test_start_task_when_at_capacity(self):
        """Test starting task when agent is at capacity"""
        # Fill capacity
        self.agent.start_task("task_1")
        self.agent.start_task("task_2")
        assert self.agent.current_workload == 2
        
        with pytest.raises(ValueError, match="Agent .* is not available for new tasks"):
            self.agent.start_task("task_3")

    def test_complete_task_success(self):
        """Test completing task successfully"""
        task_id = "task_success"
        
        # Start task
        self.agent.start_task(task_id)
        initial_completed = self.agent.completed_tasks
        initial_success_rate = self.agent.success_rate
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.complete_task(task_id, success=True)
            
            assert task_id not in self.agent.active_tasks
            assert self.agent.current_workload == 0
            assert self.agent.completed_tasks == initial_completed + 1
            assert self.agent.success_rate >= initial_success_rate  # Should maintain/improve
            assert self.agent.status == AgentStatus.AVAILABLE
            assert self.agent.updated_at == mock_now

    def test_complete_task_failure(self):
        """Test completing task with failure"""
        task_id = "task_failure"
        
        # Start task
        self.agent.start_task(task_id)
        initial_success_rate = self.agent.success_rate
        
        self.agent.complete_task(task_id, success=False)
        
        assert task_id not in self.agent.active_tasks
        assert self.agent.current_workload == 0
        assert self.agent.success_rate < initial_success_rate  # Should decrease

    def test_complete_task_not_assigned(self):
        """Test completing task that wasn't assigned to agent"""
        task_id = "unassigned_task"
        
        with pytest.raises(ValueError, match="Task .* not assigned to agent"):
            self.agent.complete_task(task_id)

    def test_complete_task_status_change_from_busy(self):
        """Test status change from busy to available when completing task"""
        # Fill capacity
        self.agent.start_task("task_1")
        self.agent.start_task("task_2")
        assert self.agent.status == AgentStatus.BUSY
        
        # Complete one task
        self.agent.complete_task("task_1")
        
        assert self.agent.current_workload == 1
        assert self.agent.status == AgentStatus.AVAILABLE


class TestAgentProjectAndTreeAssignment:
    """Test suite for agent project and tree assignment"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="assignment_agent", name="Assignment Test")

    def test_assign_to_project(self):
        """Test assigning agent to project"""
        project_id = "project_123"
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.assign_to_project(project_id)
            
            assert project_id in self.agent.assigned_projects
            assert self.agent.updated_at == mock_now

    def test_assign_to_multiple_projects(self):
        """Test assigning agent to multiple projects"""
        projects = ["project_1", "project_2", "project_3"]
        
        for project_id in projects:
            self.agent.assign_to_project(project_id)
        
        assert len(self.agent.assigned_projects) == 3
        for project_id in projects:
            assert project_id in self.agent.assigned_projects

    def test_assign_to_tree(self):
        """Test assigning agent to task tree"""
        git_branch_name = "feature/auth-system"
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.assign_to_tree(git_branch_name)
            
            assert git_branch_name in self.agent.assigned_trees
            assert self.agent.updated_at == mock_now

    def test_assign_to_multiple_trees(self):
        """Test assigning agent to multiple trees"""
        trees = ["feature/auth", "bugfix/login", "feature/dashboard"]
        
        for tree in trees:
            self.agent.assign_to_tree(tree)
        
        assert len(self.agent.assigned_trees) == 3
        for tree in trees:
            assert tree in self.agent.assigned_trees


class TestAgentStatusManagement:
    """Test suite for agent status management"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="status_agent", name="Status Test")

    def test_pause_work(self):
        """Test pausing agent work"""
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.pause_work()
            
            assert self.agent.status == AgentStatus.PAUSED
            assert self.agent.updated_at == mock_now

    def test_resume_work_under_capacity(self):
        """Test resuming work when under capacity"""
        self.agent.pause_work()
        assert self.agent.status == AgentStatus.PAUSED
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.resume_work()
            
            assert self.agent.status == AgentStatus.AVAILABLE
            assert self.agent.updated_at == mock_now

    def test_resume_work_at_capacity(self):
        """Test resuming work when at capacity"""
        self.agent.max_concurrent_tasks = 1
        self.agent.current_workload = 1
        self.agent.pause_work()
        
        self.agent.resume_work()
        
        assert self.agent.status == AgentStatus.BUSY

    def test_go_offline(self):
        """Test setting agent offline"""
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.go_offline()
            
            assert self.agent.status == AgentStatus.OFFLINE
            assert self.agent.updated_at == mock_now

    def test_go_online(self):
        """Test setting agent online"""
        self.agent.go_offline()
        assert self.agent.status == AgentStatus.OFFLINE
        
        with patch('fastmcp.task_management.domain.entities.agent.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            
            self.agent.go_online()
            
            assert self.agent.status == AgentStatus.AVAILABLE
            assert self.agent.updated_at == mock_now


class TestAgentMetrics:
    """Test suite for agent metrics and calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="metrics_agent", name="Metrics Test", max_concurrent_tasks=4)

    def test_get_workload_percentage_empty(self):
        """Test workload percentage when no tasks"""
        assert self.agent.current_workload == 0
        assert self.agent.get_workload_percentage() == 0.0

    def test_get_workload_percentage_partial(self):
        """Test workload percentage with partial load"""
        self.agent.current_workload = 2
        assert self.agent.get_workload_percentage() == 50.0

    def test_get_workload_percentage_full(self):
        """Test workload percentage at full capacity"""
        self.agent.current_workload = 4
        assert self.agent.get_workload_percentage() == 100.0

    def test_get_workload_percentage_zero_capacity(self):
        """Test workload percentage with zero capacity"""
        self.agent.max_concurrent_tasks = 0
        assert self.agent.get_workload_percentage() == 100.0

    def test_calculate_task_suitability_score_cannot_handle(self):
        """Test suitability score for task agent cannot handle"""
        task_requirements = {
            "capabilities": [AgentCapability.DEVOPS],
            "languages": ["Go"],
        }
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        assert score == 0.0

    def test_calculate_task_suitability_score_basic_match(self):
        """Test suitability score for basic task match"""
        self.agent.add_capability(AgentCapability.FRONTEND_DEVELOPMENT)
        self.agent.preferred_languages = ["JavaScript"]
        
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT],
            "languages": ["JavaScript"],
        }
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        assert score > 50.0  # Base score plus bonuses

    def test_calculate_task_suitability_score_high_workload(self):
        """Test suitability score with high workload"""
        self.agent.add_capability(AgentCapability.TESTING)
        self.agent.current_workload = 3  # 75% capacity
        
        task_requirements = {"capabilities": [AgentCapability.TESTING]}
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        
        # Should have lower workload bonus
        assert 50.0 <= score < 100.0

    def test_calculate_task_suitability_score_matching_priority(self):
        """Test suitability score with matching priority preference"""
        self.agent.add_capability(AgentCapability.ARCHITECTURE)
        self.agent.priority_preference = "high"
        
        task_requirements = {
            "capabilities": [AgentCapability.ARCHITECTURE],
            "priority": "high"
        }
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        
        # Should get priority bonus
        assert score > 70.0

    def test_calculate_task_suitability_score_low_success_rate(self):
        """Test suitability score with low success rate"""
        self.agent.add_capability(AgentCapability.CODE_REVIEW)
        self.agent.success_rate = 60.0
        
        task_requirements = {"capabilities": [AgentCapability.CODE_REVIEW]}
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        
        # Should have reduced success bonus
        assert score < 100.0

    def test_calculate_task_suitability_score_max_capped(self):
        """Test that suitability score is capped at 100.0"""
        self.agent.add_capability(AgentCapability.PROJECT_MANAGEMENT)
        self.agent.success_rate = 100.0
        self.agent.current_workload = 0
        self.agent.priority_preference = "high"
        
        task_requirements = {
            "capabilities": [AgentCapability.PROJECT_MANAGEMENT],
            "priority": "high"
        }
        
        score = self.agent.calculate_task_suitability_score(task_requirements)
        assert score <= 100.0


class TestAgentProfile:
    """Test suite for agent profile generation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(
            id="profile_agent",
            name="Profile Test",
            description="Test agent for profile",
            capabilities={AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.TESTING},
            specializations=["React Testing"],
            preferred_languages=["JavaScript", "TypeScript"],
            preferred_frameworks=["React", "Jest"],
            max_concurrent_tasks=3,
            current_workload=1,
            completed_tasks=10,
            success_rate=95.5,
            average_task_duration=4.5,
            timezone="America/Los_Angeles",
            priority_preference="medium"
        )
        self.agent.assign_to_project("project_1")
        self.agent.assign_to_tree("feature/branch")
        self.agent.active_tasks.add("active_task_1")

    def test_get_agent_profile_structure(self):
        """Test agent profile has correct structure"""
        profile = self.agent.get_agent_profile()
        
        expected_keys = {
            "id", "name", "description", "status", "capabilities",
            "specializations", "preferred_languages", "preferred_frameworks",
            "workload", "performance", "assignments", "preferences",
            "created_at", "updated_at"
        }
        
        assert set(profile.keys()) == expected_keys

    def test_get_agent_profile_workload_section(self):
        """Test agent profile workload section"""
        profile = self.agent.get_agent_profile()
        workload = profile["workload"]
        
        assert workload["current"] == 1
        assert workload["max"] == 3
        assert workload["percentage"] == (1/3) * 100
        assert workload["available"] == True

    def test_get_agent_profile_performance_section(self):
        """Test agent profile performance section"""
        profile = self.agent.get_agent_profile()
        performance = profile["performance"]
        
        assert performance["completed_tasks"] == 10
        assert performance["success_rate"] == 95.5
        assert performance["average_duration"] == 4.5

    def test_get_agent_profile_assignments_section(self):
        """Test agent profile assignments section"""
        profile = self.agent.get_agent_profile()
        assignments = profile["assignments"]
        
        assert "project_1" in assignments["projects"]
        assert "feature/branch" in assignments["trees"]
        assert "active_task_1" in assignments["active_tasks"]

    def test_get_agent_profile_capabilities_serialization(self):
        """Test that capabilities are serialized as strings"""
        profile = self.agent.get_agent_profile()
        capabilities = profile["capabilities"]
        
        assert "frontend_development" in capabilities
        assert "testing" in capabilities
        assert all(isinstance(cap, str) for cap in capabilities)

    def test_get_agent_profile_timestamps_serialization(self):
        """Test that timestamps are serialized as ISO format"""
        profile = self.agent.get_agent_profile()
        
        # Should be ISO format strings
        assert isinstance(profile["created_at"], str)
        assert isinstance(profile["updated_at"], str)
        
        # Should be parseable as datetime
        datetime.fromisoformat(profile["created_at"])
        datetime.fromisoformat(profile["updated_at"])


class TestAgentFactoryMethod:
    """Test suite for Agent factory method"""

    def test_create_agent_minimal(self):
        """Test creating agent with minimal parameters"""
        agent_id = "factory_agent"
        name = "Factory Test"
        description = "Factory created agent"
        
        agent = Agent.create_agent(agent_id, name, description)
        
        assert agent.id == agent_id
        assert agent.name == name
        assert agent.description == description
        assert isinstance(agent.capabilities, set)
        assert len(agent.capabilities) == 0
        assert agent.specializations == []
        assert agent.preferred_languages == []

    def test_create_agent_with_capabilities(self):
        """Test creating agent with capabilities"""
        capabilities = [AgentCapability.BACKEND_DEVELOPMENT, AgentCapability.SECURITY]
        specializations = ["Django", "OAuth"]
        preferred_languages = ["Python", "Go"]
        
        agent = Agent.create_agent(
            "full_factory_agent",
            "Full Factory Test",
            "Factory with all options",
            capabilities=capabilities,
            specializations=specializations,
            preferred_languages=preferred_languages
        )
        
        assert agent.capabilities == set(capabilities)
        assert agent.specializations == specializations
        assert agent.preferred_languages == preferred_languages

    def test_create_agent_with_none_parameters(self):
        """Test creating agent with None optional parameters"""
        agent = Agent.create_agent(
            "none_params_agent",
            "None Params Test",
            "Testing None parameters",
            capabilities=None,
            specializations=None,
            preferred_languages=None
        )
        
        assert agent.capabilities == set()
        assert agent.specializations == []
        assert agent.preferred_languages == []


class TestAgentEdgeCases:
    """Test suite for edge cases and error conditions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.agent = Agent(id="edge_case_agent", name="Edge Case Test")

    def test_success_rate_calculation_with_failures(self):
        """Test success rate calculation with multiple failures"""
        initial_rate = 100.0
        
        # Start and complete task with failure
        self.agent.start_task("task_1")
        self.agent.complete_task("task_1", success=False)
        
        # Success rate should decrease but be weighted
        assert self.agent.success_rate < initial_rate
        assert self.agent.success_rate > 0.0  # Should not be zero due to weighting

    def test_current_workload_never_goes_negative(self):
        """Test that current workload never goes below zero"""
        self.agent.current_workload = 1
        
        # Complete task that would make workload negative
        self.agent.start_task("task_1")
        self.agent.complete_task("task_1")
        
        # Try to decrement below zero manually
        self.agent.current_workload = 0
        task = Mock()
        task.id = "fake_task"
        self.agent.active_tasks.add("fake_task")
        self.agent.complete_task("fake_task")
        
        assert self.agent.current_workload >= 0

    def test_agent_with_zero_max_concurrent_tasks(self):
        """Test agent with zero max concurrent tasks"""
        self.agent.max_concurrent_tasks = 0
        
        assert not self.agent.is_available()
        assert self.agent.get_workload_percentage() == 100.0

    def test_very_long_agent_name_and_description(self):
        """Test agent with very long name and description"""
        long_text = "x" * 1000
        
        agent = Agent(
            id="long_text_agent",
            name=long_text,
            description=long_text
        )
        
        assert agent.name == long_text
        assert agent.description == long_text
        
        # Profile should still work
        profile = agent.get_agent_profile()
        assert len(profile["name"]) == 1000
        assert len(profile["description"]) == 1000

    def test_agent_with_many_capabilities(self):
        """Test agent with all available capabilities"""
        all_capabilities = set(AgentCapability)
        
        agent = Agent(
            id="all_cap_agent",
            name="All Capabilities",
            capabilities=all_capabilities
        )
        
        assert len(agent.capabilities) == len(all_capabilities)
        
        for capability in all_capabilities:
            assert agent.has_capability(capability)
        
        # Should handle any task requirements
        task_requirements = {
            "capabilities": [AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.SECURITY]
        }
        assert agent.can_handle_task(task_requirements)

    def test_concurrent_task_management_edge_cases(self):
        """Test edge cases in concurrent task management"""
        self.agent.max_concurrent_tasks = 1
        
        # Start task to reach capacity
        self.agent.start_task("task_1")
        assert self.agent.status == AgentStatus.BUSY
        
        # Complete task
        self.agent.complete_task("task_1")
        assert self.agent.status == AgentStatus.AVAILABLE
        
        # Start new task immediately
        self.agent.start_task("task_2")
        assert self.agent.status == AgentStatus.BUSY