"""Test agent coordination service"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4

from fastmcp.task_management.application.services.agent_coordination_service import (
    AgentCoordinationService,
    AgentCoordinationException,
    CoordinationContext
)
from fastmcp.task_management.domain.entities.agent import Agent, AgentStatus as EntityAgentStatus
from fastmcp.task_management.domain.entities.task import Task, TaskStatus
from fastmcp.task_management.domain.value_objects.agents import (
    AgentProfile, AgentCapabilities, AgentRole, AgentExpertise, AgentStatus
)
from fastmcp.task_management.domain.value_objects.coordination import (
    CoordinationType, CoordinationRequest, WorkAssignment, WorkHandoff,
    HandoffStatus, ConflictResolution, ConflictType, ResolutionStrategy
)
from fastmcp.task_management.domain.events.agent_events import (
    AgentAssigned, WorkHandoffRequested, WorkHandoffAccepted,
    WorkHandoffRejected, ConflictDetected, ConflictResolved,
    AgentStatusBroadcast, AgentWorkloadRebalanced
)


class TestCoordinationContext:
    """Test coordination context"""

    def test_get_agent_workload(self):
        """Test getting agent workload"""
        context = CoordinationContext(
            task=Mock(),
            available_agents=[],
            current_assignments={},
            workload_metrics={"agent1": 75.0, "agent2": 50.0}
        )
        
        assert context.get_agent_workload("agent1") == 75.0
        assert context.get_agent_workload("agent2") == 50.0
        assert context.get_agent_workload("agent3") == 0.0  # Default for unknown

    def test_is_agent_overloaded(self):
        """Test checking if agent is overloaded"""
        context = CoordinationContext(
            task=Mock(),
            available_agents=[],
            current_assignments={},
            workload_metrics={"agent1": 85.0, "agent2": 70.0}
        )
        
        # Default threshold (80%)
        assert context.is_agent_overloaded("agent1")
        assert not context.is_agent_overloaded("agent2")
        
        # Custom threshold
        assert context.is_agent_overloaded("agent2", threshold=0.6)
        assert not context.is_agent_overloaded("agent2", threshold=0.9)


class TestAgentCoordinationService:
    """Test agent coordination service"""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        task_repo = AsyncMock()
        agent_repo = AsyncMock()
        event_bus = AsyncMock()
        coordination_repo = AsyncMock()
        
        return task_repo, agent_repo, event_bus, coordination_repo

    @pytest.fixture
    def service(self, mock_repositories):
        """Create service instance"""
        task_repo, agent_repo, event_bus, coordination_repo = mock_repositories
        return AgentCoordinationService(
            task_repository=task_repo,
            agent_repository=agent_repo,
            event_bus=event_bus,
            coordination_repository=coordination_repo,
            user_id="test_user"
        )

    @pytest.fixture
    def mock_task(self):
        """Create mock task"""
        task = Mock(spec=Task)
        task.id = str(uuid4())
        task.title = "Test Task"
        task.status = TaskStatus.IN_PROGRESS
        return task

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent"""
        agent = Mock(spec=Agent)
        agent.id = str(uuid4())
        agent.name = "Test Agent"
        agent.status = EntityAgentStatus.AVAILABLE
        agent.active_tasks = set()
        agent.max_concurrent_tasks = 5
        agent.success_rate = 90.0
        agent.is_available = Mock(return_value=True)
        agent.start_task = Mock()
        agent.get_workload_percentage = Mock(return_value=60.0)
        return agent

    def test_with_user(self, service):
        """Test creating user-scoped service"""
        new_service = service.with_user("new_user")
        assert new_service._user_id == "new_user"
        assert new_service.task_repository == service.task_repository
        assert new_service.agent_repository == service.agent_repository

    def test_get_user_scoped_repository(self, service):
        """Test getting user-scoped repository"""
        # Repository without user support
        simple_repo = Mock()
        assert service._get_user_scoped_repository(simple_repo) == simple_repo
        
        # Repository with with_user method
        repo_with_user = Mock()
        repo_with_user.with_user = Mock(return_value="scoped_repo")
        result = service._get_user_scoped_repository(repo_with_user)
        assert result == "scoped_repo"
        repo_with_user.with_user.assert_called_once_with("test_user")
        
        # Repository with user_id attribute
        repo_with_user_id = Mock()
        repo_with_user_id.user_id = "different_user"
        repo_with_user_id.session = Mock()
        type(repo_with_user_id).__name__ = "TestRepo"
        
        with patch.object(type(repo_with_user_id), '__call__', return_value="new_repo"):
            result = service._get_user_scoped_repository(repo_with_user_id)

    @pytest.mark.asyncio
    async def test_assign_agent_to_task_success(self, service, mock_task, mock_agent):
        """Test successful agent assignment"""
        # Setup mocks
        service.task_repository.get.return_value = mock_task
        service.agent_repository.get.return_value = mock_agent
        service.agent_repository.save = AsyncMock()
        
        # Assign agent
        assignment = await service.assign_agent_to_task(
            task_id=mock_task.id,
            agent_id=mock_agent.id,
            role="developer",
            assigned_by="manager",
            responsibilities=["Implement feature"],
            estimated_hours=8.0,
            due_date=datetime.now()
        )
        
        # Verify assignment
        assert assignment.task_id == mock_task.id
        assert assignment.assigned_agent_id == mock_agent.id
        assert assignment.role == "developer"
        assert assignment.assigned_by_agent_id == "manager"
        assert assignment.responsibilities == ["Implement feature"]
        assert assignment.estimated_hours == 8.0
        
        # Verify agent update
        mock_agent.start_task.assert_called_once_with(mock_task.id)
        service.agent_repository.save.assert_called_once_with(mock_agent)
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, AgentAssigned)
        assert event.agent_id == mock_agent.id
        assert event.task_id == mock_task.id

    @pytest.mark.asyncio
    async def test_assign_agent_to_task_task_not_found(self, service):
        """Test assignment when task not found"""
        service.task_repository.get.return_value = None
        
        with pytest.raises(AgentCoordinationException) as exc:
            await service.assign_agent_to_task(
                task_id="invalid",
                agent_id="agent1",
                role="developer",
                assigned_by="manager"
            )
        assert "Task invalid not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_assign_agent_to_task_agent_not_available(self, service, mock_task, mock_agent):
        """Test assignment when agent not available"""
        service.task_repository.get.return_value = mock_task
        mock_agent.is_available.return_value = False
        service.agent_repository.get.return_value = mock_agent
        
        with pytest.raises(AgentCoordinationException) as exc:
            await service.assign_agent_to_task(
                task_id=mock_task.id,
                agent_id=mock_agent.id,
                role="developer",
                assigned_by="manager"
            )
        assert "not available for new assignments" in str(exc.value)

    @pytest.mark.asyncio
    async def test_request_work_handoff(self, service, mock_task):
        """Test requesting work handoff"""
        # Setup mocks
        from_agent = Mock(id="agent1")
        to_agent = Mock(id="agent2")
        service.agent_repository.get.side_effect = [from_agent, to_agent]
        
        # Request handoff
        handoff = await service.request_work_handoff(
            from_agent_id="agent1",
            to_agent_id="agent2",
            task_id=mock_task.id,
            work_summary="Completed backend",
            completed_items=["API endpoints"],
            remaining_items=["Frontend integration"],
            handoff_notes="Ready for UI work"
        )
        
        # Verify handoff
        assert handoff.from_agent_id == "agent1"
        assert handoff.to_agent_id == "agent2"
        assert handoff.task_id == mock_task.id
        assert handoff.work_summary == "Completed backend"
        assert handoff.status == HandoffStatus.PENDING
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, WorkHandoffRequested)

    @pytest.mark.asyncio
    async def test_accept_handoff(self, service):
        """Test accepting handoff"""
        # Create handoff
        handoff_id = str(uuid4())
        handoff = WorkHandoff(
            handoff_id=handoff_id,
            from_agent_id="agent1",
            to_agent_id="agent2",
            task_id="task123",
            initiated_at=datetime.now(),
            work_summary="Test",
            completed_items=[],
            remaining_items=[]
        )
        service.handoffs[handoff_id] = handoff
        
        # Mock task assignment
        service.assign_agent_to_task = AsyncMock()
        
        # Accept handoff
        await service.accept_handoff(handoff_id, "agent2", "Accepting work")
        
        # Verify handoff accepted
        assert handoff.status == HandoffStatus.ACCEPTED
        
        # Verify task reassigned
        service.assign_agent_to_task.assert_called_once_with(
            task_id="task123",
            agent_id="agent2",
            role="continued_work",
            assigned_by="agent1"
        )
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, WorkHandoffAccepted)

    @pytest.mark.asyncio
    async def test_reject_handoff(self, service):
        """Test rejecting handoff"""
        # Create handoff
        handoff_id = str(uuid4())
        handoff = WorkHandoff(
            handoff_id=handoff_id,
            from_agent_id="agent1",
            to_agent_id="agent2",
            task_id="task123",
            initiated_at=datetime.now(),
            work_summary="Test",
            completed_items=[],
            remaining_items=[]
        )
        service.handoffs[handoff_id] = handoff
        
        # Reject handoff
        await service.reject_handoff(handoff_id, "agent2", "Too busy")
        
        # Verify handoff rejected
        assert handoff.status == HandoffStatus.REJECTED
        assert handoff.rejection_reason == "Too busy"
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, WorkHandoffRejected)

    @pytest.mark.asyncio
    async def test_detect_and_resolve_conflict(self, service):
        """Test conflict detection and resolution"""
        # Detect conflict
        conflict = await service.detect_and_resolve_conflict(
            task_id="task123",
            conflict_type=ConflictType.RESOURCE_CONTENTION,
            involved_agents=["agent1", "agent2"],
            description="Both agents working on same file",
            resolution_strategy=ResolutionStrategy.PRIORITY_BASED
        )
        
        # Verify conflict created
        assert conflict.conflict_type == ConflictType.RESOURCE_CONTENTION
        assert conflict.involved_agents == ["agent1", "agent2"]
        assert conflict.is_resolved
        
        # Verify events published (detection + resolution)
        assert service.event_bus.publish.call_count == 2
        detect_event = service.event_bus.publish.call_args_list[0][0][0]
        resolve_event = service.event_bus.publish.call_args_list[1][0][0]
        assert isinstance(detect_event, ConflictDetected)
        assert isinstance(resolve_event, ConflictResolved)

    @pytest.mark.asyncio
    async def test_broadcast_agent_status(self, service, mock_agent):
        """Test broadcasting agent status"""
        service.agent_repository.get.return_value = mock_agent
        
        await service.broadcast_agent_status(
            agent_id=mock_agent.id,
            status="working",
            current_task_id="task123",
            current_activity="Implementing feature",
            blocker_description=None
        )
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, AgentStatusBroadcast)
        assert event.agent_id == mock_agent.id
        assert event.status == "working"
        assert event.workload_percentage == 60.0

    @pytest.mark.asyncio
    async def test_rebalance_workload(self, service):
        """Test workload rebalancing"""
        # Create agents with different workloads
        overloaded_agent = Mock(
            id="agent1",
            active_tasks={"task1", "task2", "task3"},
            get_workload_percentage=Mock(return_value=90.0),
            is_available=Mock(return_value=True)
        )
        
        underutilized_agent = Mock(
            id="agent2",
            active_tasks={"task4"},
            get_workload_percentage=Mock(return_value=20.0),
            is_available=Mock(return_value=True)
        )
        
        service.agent_repository.get_by_project = AsyncMock(
            side_effect=[[overloaded_agent, underutilized_agent]] * 2
        )
        
        # Mock handoff request
        service.request_work_handoff = AsyncMock()
        
        # Rebalance
        result = await service.rebalance_workload(
            project_id="proj123",
            initiated_by="system",
            reason="Scheduled rebalancing"
        )
        
        # Verify handoff requested
        service.request_work_handoff.assert_called_once()
        
        # Verify event published
        service.event_bus.publish.assert_called_once()
        event = service.event_bus.publish.call_args[0][0]
        assert isinstance(event, AgentWorkloadRebalanced)

    @pytest.mark.asyncio
    async def test_get_agent_workload(self, service, mock_agent):
        """Test getting agent workload details"""
        service.agent_repository.get.return_value = mock_agent
        mock_agent.active_tasks = {"task1", "task2"}
        
        # Add some assignments
        assignment = WorkAssignment(
            assignment_id="assign1",
            task_id="task1",
            assigned_agent_id=mock_agent.id,
            assigned_by_agent_id="manager",
            assigned_at=datetime.now(),
            role="developer"
        )
        service.work_assignments["assign1"] = assignment
        
        # Get workload
        workload = await service.get_agent_workload(mock_agent.id)
        
        assert workload["agent_id"] == mock_agent.id
        assert workload["workload_percentage"] == 60.0
        assert workload["current_tasks"] == 2
        assert workload["max_tasks"] == 5
        assert len(workload["active_assignments"]) == 1
        assert workload["can_accept_work"] is True

    @pytest.mark.asyncio
    async def test_find_best_agent_for_task(self, service, mock_task):
        """Test finding best agent for task"""
        # Setup mocks
        service.task_repository.get.return_value = mock_task
        
        # Create agents with different capabilities
        agent1 = Mock(
            id="agent1",
            name="Agent 1",
            is_available=Mock(return_value=True),
            get_workload_percentage=Mock(return_value=30.0),
            success_rate=95.0
        )
        
        agent2 = Mock(
            id="agent2", 
            name="Agent 2",
            is_available=Mock(return_value=True),
            get_workload_percentage=Mock(return_value=60.0),
            success_rate=85.0
        )
        
        service.agent_repository.get_all = AsyncMock(return_value=[agent1, agent2])
        
        # Find best agent
        best_agent = await service.find_best_agent_for_task(
            task_id=mock_task.id,
            required_role=AgentRole.DEVELOPER,
            required_expertise={AgentExpertise.BACKEND},
            required_skills={"python": 0.8}
        )
        
        # Should return agent with better availability
        assert best_agent == agent1

    @pytest.mark.asyncio
    async def test_find_best_agent_no_available(self, service, mock_task):
        """Test finding agent when none available"""
        service.task_repository.get.return_value = mock_task
        
        # All agents unavailable
        agent = Mock(is_available=Mock(return_value=False))
        service.agent_repository.get_all = AsyncMock(return_value=[agent])
        
        result = await service.find_best_agent_for_task(mock_task.id)
        assert result is None