"""
Unit tests for WorkDistributionService.

This module tests the work distribution, task assignment, strategy implementation,
and analytics functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any, Set
from collections import defaultdict

from fastmcp.task_management.application.services.work_distribution_service import (
    WorkDistributionService,
    DistributionStrategy,
    WorkDistributionException,
    TaskRequirements,
    DistributionPlan
)
from fastmcp.task_management.domain.entities.agent import Agent, AgentStatus, AgentCapability
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.value_objects.agents import (
    AgentRole, AgentExpertise, AgentProfile, AgentCapabilities
)
from fastmcp.task_management.domain.value_objects.coordination import WorkAssignment
from fastmcp.task_management.application.services.agent_coordination_service import AgentCoordinationService


class TestDistributionStrategy:
    """Test suite for DistributionStrategy enum"""
    
    def test_distribution_strategy_values(self):
        """Test DistributionStrategy enum values"""
        assert DistributionStrategy.ROUND_ROBIN.value == "round_robin"
        assert DistributionStrategy.LOAD_BALANCED.value == "load_balanced"
        assert DistributionStrategy.SKILL_MATCHED.value == "skill_matched"
        assert DistributionStrategy.PRIORITY_BASED.value == "priority_based"
        assert DistributionStrategy.HYBRID.value == "hybrid"
    
    def test_distribution_strategy_enumeration(self):
        """Test DistributionStrategy enumeration completeness"""
        strategies = list(DistributionStrategy)
        assert len(strategies) == 5
        
        expected_strategies = {
            DistributionStrategy.ROUND_ROBIN,
            DistributionStrategy.LOAD_BALANCED,
            DistributionStrategy.SKILL_MATCHED,
            DistributionStrategy.PRIORITY_BASED,
            DistributionStrategy.HYBRID
        }
        
        assert set(strategies) == expected_strategies


class TestTaskRequirements:
    """Test suite for TaskRequirements class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_id = str(uuid.uuid4())
        
    def test_task_requirements_initialization_minimal(self):
        """Test TaskRequirements initialization with minimal parameters"""
        requirements = TaskRequirements(task_id=self.task_id)
        
        assert requirements.task_id == self.task_id
        assert requirements.required_role is None
        assert requirements.required_expertise == set()
        assert requirements.required_skills == {}
        assert requirements.preferred_agents == []
        assert requirements.excluded_agents == []
        assert requirements.collaboration_needed is False
        assert requirements.estimated_hours == 0.0
        assert requirements.deadline is None
    
    def test_task_requirements_initialization_full(self):
        """Test TaskRequirements initialization with all parameters"""
        required_role = AgentRole.DEVELOPER
        required_expertise = {AgentExpertise.FRONTEND, AgentExpertise.TESTING}
        required_skills = {"python": 0.8, "react": 0.6}
        preferred_agents = ["agent1", "agent2"]
        excluded_agents = ["agent3"]
        collaboration_needed = True
        estimated_hours = 8.5
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        
        requirements = TaskRequirements(
            task_id=self.task_id,
            required_role=required_role,
            required_expertise=required_expertise,
            required_skills=required_skills,
            preferred_agents=preferred_agents,
            excluded_agents=excluded_agents,
            collaboration_needed=collaboration_needed,
            estimated_hours=estimated_hours,
            deadline=deadline
        )
        
        assert requirements.task_id == self.task_id
        assert requirements.required_role == required_role
        assert requirements.required_expertise == required_expertise
        assert requirements.required_skills == required_skills
        assert requirements.preferred_agents == preferred_agents
        assert requirements.excluded_agents == excluded_agents
        assert requirements.collaboration_needed == collaboration_needed
        assert requirements.estimated_hours == estimated_hours
        assert requirements.deadline == deadline
    
    def test_from_task_minimal_metadata(self):
        """Test creating TaskRequirements from task with minimal metadata"""
        task = Mock(spec=Task)
        task.id = Mock()
        task.id.value = self.task_id
        task.metadata = None
        task.due_date = None
        
        requirements = TaskRequirements.from_task(task)
        
        assert requirements.task_id == self.task_id
        assert requirements.required_role is None
        assert requirements.required_expertise == set()
        assert requirements.required_skills == {}
        assert requirements.deadline is None
    
    def test_from_task_with_metadata(self):
        """Test creating TaskRequirements from task with full metadata"""
        deadline = datetime.now(timezone.utc) + timedelta(days=3)
        task = Mock(spec=Task)
        task.id = Mock()
        task.id.value = self.task_id
        task.due_date = deadline
        task.metadata = {
            'required_role': 'developer',
            'required_expertise': ['frontend', 'testing'],
            'required_skills': {'javascript': 0.7, 'css': 0.5},
            'preferred_agents': ['agent_a', 'agent_b'],
            'excluded_agents': ['agent_c'],
            'collaboration_needed': True,
            'estimated_hours': 12.0
        }
        
        requirements = TaskRequirements.from_task(task)
        
        assert requirements.task_id == self.task_id
        assert requirements.required_role == AgentRole.DEVELOPER
        assert AgentExpertise.FRONTEND in requirements.required_expertise
        assert AgentExpertise.TESTING in requirements.required_expertise
        assert requirements.required_skills == {'javascript': 0.7, 'css': 0.5}
        assert requirements.preferred_agents == ['agent_a', 'agent_b']
        assert requirements.excluded_agents == ['agent_c']
        assert requirements.collaboration_needed is True
        assert requirements.estimated_hours == 12.0
        assert requirements.deadline == deadline
    
    def test_from_task_with_invalid_enum_values(self):
        """Test creating TaskRequirements from task with invalid enum values"""
        task = Mock(spec=Task)
        task.id = self.task_id
        task.metadata = {
            'required_role': 'invalid_role',
            'required_expertise': ['invalid_expertise', 'frontend']
        }
        task.due_date = None
        
        requirements = TaskRequirements.from_task(task)
        
        # Invalid role should be ignored
        assert requirements.required_role is None
        # Invalid expertise should be ignored, valid one should be included
        assert len(requirements.required_expertise) == 1
        assert AgentExpertise.FRONTEND in requirements.required_expertise
    
    def test_from_task_with_string_task_id(self):
        """Test creating TaskRequirements from task with string task_id"""
        task = Mock(spec=Task)
        task.id = self.task_id  # String ID without .value attribute
        task.metadata = {}
        task.due_date = None
        
        requirements = TaskRequirements.from_task(task)
        
        assert requirements.task_id == self.task_id


class TestDistributionPlan:
    """Test suite for DistributionPlan class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.plan = DistributionPlan()
        self.task_id = str(uuid.uuid4())
        self.agent_id = str(uuid.uuid4())
    
    def test_distribution_plan_initialization(self):
        """Test DistributionPlan initialization"""
        plan = DistributionPlan()
        
        assert plan.plan_id is not None
        assert len(plan.plan_id) > 0
        assert isinstance(plan.created_at, datetime)
        assert plan.assignments == []
        assert plan.unassignable_tasks == []
        assert plan.recommendations == {}
    
    def test_add_assignment(self):
        """Test adding assignment to plan"""
        self.plan.add_assignment(self.task_id, self.agent_id, "assignee")
        
        assert len(self.plan.assignments) == 1
        assignment = self.plan.assignments[0]
        assert assignment == (self.task_id, self.agent_id, "assignee")
    
    def test_add_assignment_with_default_role(self):
        """Test adding assignment with default role"""
        self.plan.add_assignment(self.task_id, self.agent_id)
        
        assert len(self.plan.assignments) == 1
        assignment = self.plan.assignments[0]
        assert assignment == (self.task_id, self.agent_id, "assignee")
    
    def test_mark_unassignable(self):
        """Test marking task as unassignable"""
        reason = "No available agents"
        self.plan.mark_unassignable(self.task_id, reason)
        
        assert self.task_id in self.plan.unassignable_tasks
        assert self.plan.recommendations[self.task_id] == reason
    
    def test_multiple_assignments_and_unassignables(self):
        """Test plan with multiple assignments and unassignables"""
        task_id_2 = str(uuid.uuid4())
        agent_id_2 = str(uuid.uuid4())
        
        self.plan.add_assignment(self.task_id, self.agent_id, "specialist")
        self.plan.add_assignment(task_id_2, agent_id_2, "reviewer")
        self.plan.mark_unassignable(str(uuid.uuid4()), "No suitable agent")
        
        assert len(self.plan.assignments) == 2
        assert len(self.plan.unassignable_tasks) == 1
        assert len(self.plan.recommendations) == 1


class TestWorkDistributionServiceInitialization:
    """Test suite for WorkDistributionService initialization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.agent_repository = AsyncMock()
        self.coordination_service = AsyncMock()
        self.event_bus = Mock()
    
    def test_initialization_minimal(self):
        """Test initialization with minimal required parameters"""
        service = WorkDistributionService(
            task_repository=self.task_repository
        )
        
        assert service.task_repository == self.task_repository
        assert service.agent_repository is None
        assert service.coordination_service is None
        assert service.event_bus is None
        assert service._user_id is None
        assert service.distribution_history == []
        assert service.agent_performance_cache == {}
    
    def test_initialization_full(self):
        """Test initialization with all parameters"""
        user_id = "test_user"
        service = WorkDistributionService(
            task_repository=self.task_repository,
            agent_repository=self.agent_repository,
            coordination_service=self.coordination_service,
            event_bus=self.event_bus,
            user_id=user_id
        )
        
        assert service.task_repository == self.task_repository
        assert service.agent_repository == self.agent_repository
        assert service.coordination_service == self.coordination_service
        assert service.event_bus == self.event_bus
        assert service._user_id == user_id
    
    def test_with_user_creates_new_instance(self):
        """Test that with_user creates a new service instance"""
        service = WorkDistributionService(self.task_repository)
        user_id = "new_user"
        
        user_service = service.with_user(user_id)
        
        assert user_service != service
        assert user_service._user_id == user_id
        assert user_service.task_repository == self.task_repository


class TestUserScopedRepository:
    """Test suite for user-scoped repository functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.service = WorkDistributionService(
            task_repository=self.task_repository,
            user_id="test_user"
        )
    
    def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository with with_user method"""
        mock_repo = Mock()
        user_scoped_repo = Mock()
        mock_repo.with_user.return_value = user_scoped_repo
        
        result = self.service._get_user_scoped_repository(mock_repo)
        
        assert result == user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")
    
    def test_get_user_scoped_repository_with_user_id_attribute(self):
        """Test getting user-scoped repository with user_id attribute and different user"""
        # Create a mock repository with user_id attribute set to different user
        mock_repo = Mock(spec=['user_id', 'session'])
        mock_repo.user_id = "different_user"
        mock_repo.session = Mock()

        # Mock the type() call to return a mock class that can be instantiated
        mock_repo_class = Mock(return_value=Mock())

        with patch('builtins.type', return_value=mock_repo_class):
            result = self.service._get_user_scoped_repository(mock_repo)

            # Should have attempted to create a new instance with the correct user_id
            mock_repo_class.assert_called_once_with(mock_repo.session, user_id="test_user")
            assert result == mock_repo_class.return_value
    
    def test_get_user_scoped_repository_no_user_context(self):
        """Test getting user-scoped repository with no user context"""
        service = WorkDistributionService(self.task_repository)
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        # Should return original repository
        assert result == mock_repo
    
    def test_get_user_scoped_repository_none(self):
        """Test getting user-scoped repository with None"""
        result = self.service._get_user_scoped_repository(None)
        
        assert result is None


class TestTaskDistribution:
    """Test suite for task distribution functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.agent_repository = AsyncMock()
        self.coordination_service = AsyncMock()
        
        self.service = WorkDistributionService(
            task_repository=self.task_repository,
            agent_repository=self.agent_repository,
            coordination_service=self.coordination_service
        )
        
        # Create mock tasks
        self.task1 = self._create_mock_task("task1", TaskStatusEnum.TODO)
        self.task2 = self._create_mock_task("task2", TaskStatusEnum.IN_PROGRESS)
        self.task3 = self._create_mock_task("task3", TaskStatusEnum.DONE)  # Should be filtered out
        
        # Create mock agents
        self.agent1 = self._create_mock_agent("agent1", available=True)
        self.agent2 = self._create_mock_agent("agent2", available=True)
        self.agent3 = self._create_mock_agent("agent3", available=False)  # Not available
    
    def _create_mock_task(self, task_id: str, status: TaskStatusEnum) -> Mock:
        """Create a mock task"""
        task = Mock(spec=Task)
        task.id = Mock()
        task.id.value = task_id
        task.status = Mock()
        task.status.value = status.value
        task.metadata = {}
        task.priority = Mock()
        task.priority.value = PriorityLevel.MEDIUM.label
        task.due_date = None
        return task
    
    def _create_mock_agent(self, agent_id: str, available: bool = True) -> Mock:
        """Create a mock agent"""
        agent = Mock(spec=Agent)
        agent.id = agent_id
        agent.is_available.return_value = available
        agent.current_workload = 0
        agent.max_concurrent_tasks = 3
        agent.get_workload_percentage.return_value = 0.0
        agent.success_rate = 85.0
        agent.average_task_duration = 6.0
        agent.capabilities = {AgentCapability.BACKEND_DEVELOPMENT}
        return agent
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_no_tasks_found(self):
        """Test task distribution when no distributable tasks are found"""
        self.task_repository.get.return_value = None
        
        plan = await self.service.distribute_tasks(["task1", "task2"])
        
        assert len(plan.assignments) == 0
        assert len(plan.unassignable_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_no_available_agents(self):
        """Test task distribution when no agents are available"""
        # Set up tasks
        self.task_repository.get.side_effect = [self.task1, self.task2]
        
        # All agents unavailable
        unavailable_agent = self._create_mock_agent("agent1", available=False)
        self.agent_repository.get_all.return_value = [unavailable_agent]
        
        plan = await self.service.distribute_tasks(["task1", "task2"])
        
        assert len(plan.assignments) == 0
        assert len(plan.unassignable_tasks) == 2
        assert "No available agents" in plan.recommendations.values()
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_round_robin_strategy(self):
        """Test task distribution with round-robin strategy"""
        # Set up tasks
        self.task_repository.get.side_effect = [self.task1, self.task2]
        self.agent_repository.get_all.return_value = [self.agent1, self.agent2]
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["task1", "task2"],
                strategy=DistributionStrategy.ROUND_ROBIN
            )
            
            assert len(plan.assignments) == 2
            # Should alternate between agents
            assert plan.assignments[0] == ("task1", "agent1", "assignee")
            assert plan.assignments[1] == ("task2", "agent2", "assignee")
            mock_execute.assert_called_once_with(plan)
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_load_balanced_strategy(self):
        """Test task distribution with load-balanced strategy"""
        # Set different workloads for agents
        self.agent1.get_workload_percentage.return_value = 20.0
        self.agent2.get_workload_percentage.return_value = 60.0
        
        self.task_repository.get.side_effect = [self.task1, self.task2]
        self.agent_repository.get_all.return_value = [self.agent1, self.agent2]
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["task1", "task2"],
                strategy=DistributionStrategy.LOAD_BALANCED
            )
            
            assert len(plan.assignments) == 2
            # Both tasks should go to agent1 (lower workload)
            assert all(assignment[1] == "agent1" for assignment in plan.assignments)
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_skill_matched_strategy(self):
        """Test task distribution with skill-matched strategy"""
        self.task_repository.get.side_effect = [self.task1]
        self.agent_repository.get_all.return_value = [self.agent1]
        
        # Mock coordination service to find best agent
        self.coordination_service.find_best_agent_for_task.return_value = self.agent1
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["task1"],
                strategy=DistributionStrategy.SKILL_MATCHED
            )
            
            assert len(plan.assignments) == 1
            assert plan.assignments[0] == ("task1", "agent1", "specialist")
            self.coordination_service.find_best_agent_for_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_priority_based_strategy(self):
        """Test task distribution with priority-based strategy"""
        # Create high and medium priority tasks
        high_priority_task = self._create_mock_task("high_task", TaskStatusEnum.TODO)
        high_priority_task.priority.value = PriorityLevel.HIGH.label
        
        medium_priority_task = self._create_mock_task("med_task", TaskStatusEnum.TODO)
        medium_priority_task.priority.value = PriorityLevel.MEDIUM.label
        
        # Set up different performance scores
        self.agent1.success_rate = 95.0
        self.agent2.success_rate = 80.0
        
        self.task_repository.get.side_effect = [high_priority_task, medium_priority_task]
        self.agent_repository.get_all.return_value = [self.agent1, self.agent2]
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["high_task", "med_task"],
                strategy=DistributionStrategy.PRIORITY_BASED
            )
            
            assert len(plan.assignments) == 2
            # High priority task should go to better agent first
            high_task_assignment = next(a for a in plan.assignments if a[0] == "high_task")
            assert high_task_assignment[1] == "agent1"  # Better performance
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_hybrid_strategy(self):
        """Test task distribution with hybrid strategy"""
        # Create tasks with different characteristics
        priority_task = self._create_mock_task("priority", TaskStatusEnum.TODO)
        priority_task.priority.value = PriorityLevel.CRITICAL.label
        
        skilled_task = self._create_mock_task("skilled", TaskStatusEnum.TODO)
        skilled_task.metadata = {'required_role': 'developer'}
        
        regular_task = self._create_mock_task("regular", TaskStatusEnum.TODO)
        
        self.task_repository.get.side_effect = [priority_task, skilled_task, regular_task]
        self.agent_repository.get_all.return_value = [self.agent1, self.agent2]
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["priority", "skilled", "regular"],
                strategy=DistributionStrategy.HYBRID
            )
            
            assert len(plan.assignments) == 3
            mock_execute.assert_called_once_with(plan)
    
    @pytest.mark.asyncio
    async def test_distribute_tasks_with_project_filter(self):
        """Test task distribution with project filter"""
        project_id = "test_project"
        
        self.task_repository.get.side_effect = [self.task1]
        self.agent_repository.get_by_project.return_value = [self.agent1]
        
        with patch.object(self.service, '_execute_distribution_plan') as mock_execute:
            plan = await self.service.distribute_tasks(
                ["task1"],
                project_id=project_id
            )
            
            self.agent_repository.get_by_project.assert_called_once_with(project_id)
            assert len(plan.assignments) == 1


class TestDistributionStrategies:
    """Test suite for individual distribution strategies"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkDistributionService(Mock())
        self.plan = DistributionPlan()
        
        self.tasks = [
            self._create_mock_task("task1"),
            self._create_mock_task("task2"),
            self._create_mock_task("task3")
        ]
        
        self.agents = [
            self._create_mock_agent("agent1"),
            self._create_mock_agent("agent2")
        ]
    
    def _create_mock_task(self, task_id: str) -> Mock:
        """Create a mock task"""
        task = Mock()
        task.id = Mock()
        task.id.value = task_id
        task.priority = Mock()
        task.priority.value = PriorityLevel.MEDIUM.label
        task.metadata = {}
        task.due_date = None
        return task
    
    def _create_mock_agent(self, agent_id: str) -> Mock:
        """Create a mock agent"""
        agent = Mock()
        agent.id = agent_id
        agent.is_available.return_value = True
        agent.current_workload = 0
        agent.max_concurrent_tasks = 3
        agent.get_workload_percentage.return_value = 25.0
        agent.success_rate = 85.0
        agent.average_task_duration = 6.0
        agent.capabilities = {AgentCapability.BACKEND_DEVELOPMENT}
        return agent
    
    @pytest.mark.asyncio
    async def test_distribute_round_robin(self):
        """Test round-robin distribution strategy"""
        await self.service._distribute_round_robin(self.tasks, self.agents, self.plan)
        
        assert len(self.plan.assignments) == 3
        # Should alternate between agents
        assert self.plan.assignments[0][1] == "agent1"
        assert self.plan.assignments[1][1] == "agent2"
        assert self.plan.assignments[2][1] == "agent1"  # Wraps around
    
    @pytest.mark.asyncio
    async def test_distribute_round_robin_no_agents(self):
        """Test round-robin distribution with no agents"""
        await self.service._distribute_round_robin(self.tasks, [], self.plan)
        
        assert len(self.plan.assignments) == 0
        assert len(self.plan.unassignable_tasks) == 3
    
    @pytest.mark.asyncio
    async def test_distribute_load_balanced(self):
        """Test load-balanced distribution strategy"""
        # Set different workloads
        self.agents[0].get_workload_percentage.return_value = 10.0
        self.agents[1].get_workload_percentage.return_value = 50.0
        
        await self.service._distribute_load_balanced(self.tasks, self.agents, self.plan)
        
        # All tasks should go to agent with lower workload initially
        assert len(self.plan.assignments) == 3
        # First task goes to agent1 (lower workload)
        assert self.plan.assignments[0][1] == "agent1"
    
    @pytest.mark.asyncio
    async def test_distribute_load_balanced_capacity_reached(self):
        """Test load-balanced distribution when agent reaches capacity"""
        # Set agent1 to have high workload
        self.agents[0].is_available.return_value = False
        self.agents[1].is_available.return_value = True
        
        await self.service._distribute_load_balanced(self.tasks, self.agents, self.plan)
        
        # All available assignments should go to agent2
        assigned_agents = [a[1] for a in self.plan.assignments]
        assert all(agent == "agent2" for agent in assigned_agents)
    
    @pytest.mark.asyncio
    async def test_distribute_skill_matched(self):
        """Test skill-matched distribution strategy"""
        # Mock coordination service
        self.service.coordination_service = AsyncMock()
        self.service.coordination_service.find_best_agent_for_task.side_effect = [
            self.agents[0], self.agents[1], None  # Third task has no matching agent
        ]
        
        await self.service._distribute_skill_matched(self.tasks, self.agents, self.plan)
        
        assert len(self.plan.assignments) == 2  # Only 2 tasks have matching agents
        assert len(self.plan.unassignable_tasks) == 1  # One task unassignable
        assert self.service.coordination_service.find_best_agent_for_task.call_count == 3
    
    @pytest.mark.asyncio
    async def test_distribute_priority_based(self):
        """Test priority-based distribution strategy"""
        # Set different priorities
        self.tasks[0].priority.value = PriorityLevel.CRITICAL.label
        self.tasks[1].priority.value = PriorityLevel.LOW.label
        self.tasks[2].priority.value = PriorityLevel.HIGH.label
        
        # Set different performance scores
        self.agents[0].success_rate = 95.0
        self.agents[1].success_rate = 75.0
        
        await self.service._distribute_priority_based(self.tasks, self.agents, self.plan)
        
        assert len(self.plan.assignments) == 3
        
        # Critical task should be assigned first to best agent
        critical_assignment = next(a for a in self.plan.assignments if a[0] == "task1")
        assert critical_assignment[1] == "agent1"  # Best agent
        assert critical_assignment[2] == "priority_assignee"
    
    @pytest.mark.asyncio
    async def test_distribute_hybrid(self):
        """Test hybrid distribution strategy"""
        # Set up different task types
        self.tasks[0].priority.value = PriorityLevel.CRITICAL.label  # Priority task
        self.tasks[1].metadata = {'required_role': 'developer'}  # Skilled task
        self.tasks[2].priority.value = PriorityLevel.LOW.label  # Regular task
        
        # Mock agent matching
        with patch.object(self.service, '_agent_matches_requirements', return_value=True):
            await self.service._distribute_hybrid(self.tasks, self.agents, self.plan)
        
        assert len(self.plan.assignments) == 3
        
        # Check role assignments
        roles = [a[2] for a in self.plan.assignments]
        assert "priority_specialist" in roles
        assert "skill_matched" in roles
        assert "load_balanced" in roles


class TestAgentPerformanceAndMatching:
    """Test suite for agent performance calculation and requirement matching"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkDistributionService(Mock())
    
    def test_get_agent_performance_score_basic(self):
        """Test basic agent performance score calculation"""
        agent = Mock()
        agent.id = "agent1"
        agent.success_rate = 85.0
        agent.average_task_duration = None
        
        score = self.service._get_agent_performance_score(agent)
        
        assert score == 0.85  # 85% success rate
        assert agent.id in self.service.agent_performance_cache
    
    def test_get_agent_performance_score_with_duration(self):
        """Test agent performance score with average task duration"""
        agent = Mock()
        agent.id = "agent2"
        agent.success_rate = 80.0
        agent.average_task_duration = 4.0  # Faster than 8 hour average
        
        score = self.service._get_agent_performance_score(agent)
        
        # Should be (0.8 * 0.7) + (2.0 * 0.3) = 0.56 + 0.6 = 1.16, capped at 1.0
        expected_duration_factor = min(1.0, 8.0 / 4.0)  # 2.0, but capped at 1.0
        expected_score = (0.8 * 0.7) + (1.0 * 0.3)  # 0.56 + 0.3 = 0.86
        assert abs(score - expected_score) < 0.01
    
    def test_get_agent_performance_score_cached(self):
        """Test that agent performance score is cached"""
        agent = Mock()
        agent.id = "agent3"
        agent.success_rate = 90.0
        agent.average_task_duration = None  # No duration data
        
        # First call
        score1 = self.service._get_agent_performance_score(agent)
        
        # Change success rate
        agent.success_rate = 50.0
        
        # Second call should return cached value
        score2 = self.service._get_agent_performance_score(agent)
        
        assert score1 == score2 == 0.9  # Original value
    
    def test_agent_matches_requirements_excluded(self):
        """Test agent matching when agent is excluded"""
        agent = Mock()
        agent.id = "agent1"
        
        requirements = TaskRequirements(
            task_id="task1",
            excluded_agents=["agent1"]
        )
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is False
    
    def test_agent_matches_requirements_preferred(self):
        """Test agent matching when agent is preferred"""
        agent = Mock()
        agent.id = "agent1"
        
        requirements = TaskRequirements(
            task_id="task1",
            preferred_agents=["agent1"]
        )
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is True
    
    def test_agent_matches_requirements_developer_role(self):
        """Test agent matching for developer role requirement"""
        agent = Mock()
        agent.id = "agent1"
        agent.capabilities = {AgentCapability.BACKEND_DEVELOPMENT}
        
        requirements = TaskRequirements(
            task_id="task1",
            required_role=AgentRole.DEVELOPER
        )
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is True
    
    def test_agent_matches_requirements_tester_role(self):
        """Test agent matching for tester role requirement"""
        agent = Mock()
        agent.id = "agent1"
        agent.capabilities = {AgentCapability.TESTING}
        
        requirements = TaskRequirements(
            task_id="task1",
            required_role=AgentRole.TESTER
        )
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is True
    
    def test_agent_matches_requirements_no_required_capability(self):
        """Test agent matching when agent lacks required capability"""
        agent = Mock()
        agent.id = "agent1"
        agent.capabilities = {AgentCapability.FRONTEND_DEVELOPMENT}
        
        requirements = TaskRequirements(
            task_id="task1",
            required_role=AgentRole.TESTER
        )
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is False  # Agent lacks TESTING capability
    
    def test_agent_matches_requirements_default_capable(self):
        """Test agent matching defaults to capable when no specific requirements"""
        agent = Mock()
        agent.id = "agent1"
        
        requirements = TaskRequirements(task_id="task1")
        
        result = self.service._agent_matches_requirements(agent, requirements)
        
        assert result is True


class TestPlanExecution:
    """Test suite for distribution plan execution"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.coordination_service = AsyncMock()
        self.service = WorkDistributionService(
            task_repository=Mock(),
            coordination_service=self.coordination_service
        )
    
    @pytest.mark.asyncio
    async def test_execute_distribution_plan_success(self):
        """Test successful execution of distribution plan"""
        plan = DistributionPlan()
        plan.add_assignment("task1", "agent1", "assignee")
        plan.add_assignment("task2", "agent2", "specialist")
        
        await self.service._execute_distribution_plan(plan)
        
        assert self.coordination_service.assign_agent_to_task.call_count == 2
        self.coordination_service.assign_agent_to_task.assert_any_call(
            task_id="task1",
            agent_id="agent1",
            role="assignee",
            assigned_by="work_distribution_service"
        )
        self.coordination_service.assign_agent_to_task.assert_any_call(
            task_id="task2",
            agent_id="agent2",
            role="specialist",
            assigned_by="work_distribution_service"
        )
    
    @pytest.mark.asyncio
    async def test_execute_distribution_plan_assignment_failure(self):
        """Test plan execution handles assignment failures"""
        plan = DistributionPlan()
        plan.add_assignment("task1", "agent1", "assignee")
        plan.add_assignment("task2", "agent2", "specialist")
        
        # Mock one assignment to fail
        self.coordination_service.assign_agent_to_task.side_effect = [
            None,  # First assignment succeeds
            Exception("Assignment failed")  # Second assignment fails
        ]
        
        await self.service._execute_distribution_plan(plan)
        
        # Plan should mark failed task as unassignable
        assert "task2" in plan.unassignable_tasks
        assert "Assignment failed" in plan.recommendations["task2"]
    
    @pytest.mark.asyncio
    async def test_execute_distribution_plan_no_coordination_service(self):
        """Test plan execution without coordination service"""
        service = WorkDistributionService(task_repository=Mock())
        plan = DistributionPlan()
        plan.add_assignment("task1", "agent1", "assignee")
        
        # Should handle missing coordination service gracefully
        try:
            await service._execute_distribution_plan(plan)
        except AttributeError:
            # Expected when coordination service is None
            pass


class TestDistributionHistory:
    """Test suite for distribution history and analytics"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = WorkDistributionService(Mock())
    
    def test_record_distribution(self):
        """Test recording distribution for history"""
        plan = DistributionPlan()
        plan.add_assignment("task1", "agent1", "assignee")
        plan.add_assignment("task2", "agent2", "specialist")
        plan.mark_unassignable("task3", "No suitable agent")
        
        strategy = DistributionStrategy.HYBRID
        
        self.service._record_distribution(plan, strategy)
        
        assert len(self.service.distribution_history) == 1
        record = self.service.distribution_history[0]
        
        assert record["plan_id"] == plan.plan_id
        assert record["strategy"] == strategy.value
        assert record["total_tasks"] == 3
        assert record["assigned_tasks"] == 2
        assert record["unassignable_tasks"] == 1
        assert len(record["assignments"]) == 2
        assert "No suitable agent" in record["recommendations"].values()
    
    def test_record_distribution_history_limit(self):
        """Test that distribution history is limited to 100 entries"""
        # Add 150 distributions
        for i in range(150):
            plan = DistributionPlan()
            plan.add_assignment(f"task{i}", f"agent{i % 2}", "assignee")
            self.service._record_distribution(plan, DistributionStrategy.ROUND_ROBIN)
        
        # Should keep only the last 100
        assert len(self.service.distribution_history) == 100
        
        # First record should be from distribution 50 (0-indexed)
        first_record = self.service.distribution_history[0]
        assert "task50" in [a[0] for a in first_record["assignments"]]
    
    @pytest.mark.asyncio
    async def test_get_distribution_analytics_no_history(self):
        """Test analytics when no distribution history exists"""
        analytics = await self.service.get_distribution_analytics()
        
        assert analytics == {"message": "No distribution history available"}
    
    @pytest.mark.asyncio
    async def test_get_distribution_analytics_with_history(self):
        """Test analytics calculation with distribution history"""
        # Record some distributions
        distributions = [
            (DistributionStrategy.ROUND_ROBIN, 3, 2),  # 3 total, 2 assigned
            (DistributionStrategy.SKILL_MATCHED, 2, 2),  # 2 total, 2 assigned
            (DistributionStrategy.ROUND_ROBIN, 4, 3),  # 4 total, 3 assigned
        ]
        
        for strategy, total, assigned in distributions:
            plan = DistributionPlan()
            for i in range(assigned):
                plan.add_assignment(f"task{i}", f"agent{i}", "assignee")
            for i in range(total - assigned):
                plan.mark_unassignable(f"unassignable{i}", "No agent available")
            
            self.service._record_distribution(plan, strategy)
        
        analytics = await self.service.get_distribution_analytics()
        
        assert analytics["total_distributions"] == 3
        assert analytics["total_tasks_distributed"] == 9  # 3+2+4
        assert analytics["total_tasks_assigned"] == 7  # 2+2+3
        assert analytics["overall_assignment_rate"] == (7/9 * 100)  # ~77.78%
        
        # Strategy usage
        assert analytics["strategy_usage"]["round_robin"] == 2
        assert analytics["strategy_usage"]["skill_matched"] == 1
        
        # Strategy success rates
        assert analytics["strategy_success_rates"]["round_robin"] == (5/7 * 100)  # 71.43%
        assert analytics["strategy_success_rates"]["skill_matched"] == (2/2 * 100)  # 100%
        
        # Should have recent unassignable reasons
        assert "recent_unassignable_reasons" in analytics
        assert isinstance(analytics["recent_unassignable_reasons"], list)


class TestIntegration:
    """Integration tests for WorkDistributionService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.agent_repository = AsyncMock()
        self.coordination_service = AsyncMock()
        
        self.service = WorkDistributionService(
            task_repository=self.task_repository,
            agent_repository=self.agent_repository,
            coordination_service=self.coordination_service
        )
    
    @pytest.mark.asyncio
    async def test_full_distribution_workflow(self):
        """Test complete distribution workflow"""
        # Set up test data
        task1 = Mock()
        task1.id = Mock()
        task1.id.value = "task1"
        task1.status = Mock()
        task1.status.value = TaskStatusEnum.TODO.value
        task1.metadata = {}
        task1.priority = Mock()
        task1.priority.value = PriorityLevel.HIGH.label
        task1.due_date = None
        
        agent1 = Mock()
        agent1.id = "agent1"
        agent1.is_available.return_value = True
        agent1.current_workload = 0
        agent1.max_concurrent_tasks = 3
        agent1.get_workload_percentage.return_value = 10.0
        agent1.success_rate = 90.0
        agent1.average_task_duration = 5.0
        agent1.capabilities = {AgentCapability.BACKEND_DEVELOPMENT}
        
        # Configure mocks
        self.task_repository.get.return_value = task1
        self.agent_repository.get_all.return_value = [agent1]
        
        # Execute distribution
        plan = await self.service.distribute_tasks(
            ["task1"],
            strategy=DistributionStrategy.LOAD_BALANCED
        )
        
        # Verify results
        assert len(plan.assignments) == 1
        assert plan.assignments[0] == ("task1", "agent1", "assignee")
        
        # Verify coordination service was called
        self.coordination_service.assign_agent_to_task.assert_called_once_with(
            task_id="task1",
            agent_id="agent1",
            role="assignee",
            assigned_by="work_distribution_service"
        )
        
        # Verify history was recorded
        assert len(self.service.distribution_history) == 1
        record = self.service.distribution_history[0]
        assert record["strategy"] == DistributionStrategy.LOAD_BALANCED.value
        assert record["assigned_tasks"] == 1
    
    @pytest.mark.asyncio
    async def test_complex_hybrid_distribution(self):
        """Test complex hybrid distribution with mixed task types"""
        # Create diverse set of tasks
        critical_task = self._create_task("critical", PriorityLevel.CRITICAL.label, {})
        skilled_task = self._create_task("skilled", PriorityLevel.MEDIUM.label, 
                                       {"required_role": "developer"})
        regular_task = self._create_task("regular", PriorityLevel.LOW.label, {})
        
        # Create agents with different capabilities
        expert_agent = self._create_agent("expert", 95.0, 4.0, [AgentCapability.BACKEND_DEVELOPMENT])
        regular_agent = self._create_agent("regular", 80.0, 6.0, [AgentCapability.FRONTEND_DEVELOPMENT])
        
        # Configure repository responses
        self.task_repository.get.side_effect = [critical_task, skilled_task, regular_task]
        self.agent_repository.get_all.return_value = [expert_agent, regular_agent]
        
        # Execute hybrid distribution
        plan = await self.service.distribute_tasks(
            ["critical", "skilled", "regular"],
            strategy=DistributionStrategy.HYBRID
        )
        
        # Verify all tasks were assigned
        assert len(plan.assignments) == 3
        assert len(plan.unassignable_tasks) == 0
        
        # Critical task should go to expert agent
        critical_assignment = next(a for a in plan.assignments if a[0] == "critical")
        assert critical_assignment[1] == "expert"
        assert critical_assignment[2] == "priority_specialist"
    
    def _create_task(self, task_id: str, priority: str, metadata: Dict[str, Any]) -> Mock:
        """Helper to create mock task"""
        task = Mock()
        task.id = Mock()
        task.id.value = task_id
        task.status = Mock()
        task.status.value = TaskStatusEnum.TODO.value
        task.metadata = metadata
        task.priority = Mock()
        task.priority.value = priority
        task.due_date = None
        return task
    
    def _create_agent(self, agent_id: str, success_rate: float, 
                      avg_duration: float, capabilities: List[AgentCapability]) -> Mock:
        """Helper to create mock agent"""
        agent = Mock()
        agent.id = agent_id
        agent.is_available.return_value = True
        agent.current_workload = 0
        agent.max_concurrent_tasks = 5
        agent.get_workload_percentage.return_value = 20.0
        agent.success_rate = success_rate
        agent.average_task_duration = avg_duration
        agent.capabilities = set(capabilities)
        return agent