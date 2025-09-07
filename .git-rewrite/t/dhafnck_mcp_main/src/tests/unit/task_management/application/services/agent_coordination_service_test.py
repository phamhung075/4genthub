"""
Tests for Agent Coordination Service

This module tests the AgentCoordinationService functionality including:
- Agent assignment to tasks
- Work handoff between agents
- Conflict detection and resolution
- Agent status broadcasting
- Workload rebalancing
- Finding best agents for tasks
- User context handling
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from fastmcp.task_management.application.services.agent_coordination_service import (
    AgentCoordinationService,
    AgentCoordinationException,
    CoordinationContext,
)
from fastmcp.task_management.domain.value_objects.coordination import (
    CoordinationType,
    CoordinationRequest,
    WorkAssignment,
    WorkHandoff,
    HandoffStatus,
    ConflictResolution,
    ConflictType,
    ResolutionStrategy,
    AgentCommunication,
)
from fastmcp.task_management.domain.value_objects.agents import (
    AgentRole,
    AgentExpertise,
    AgentStatus,
)


class TestAgentCoordinationService:
    """Test suite for AgentCoordinationService"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock()
        repo.get = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_agent_repository(self):
        """Create a mock agent repository"""
        repo = Mock()
        repo.get = AsyncMock()
        repo.save = AsyncMock()
        repo.get_by_project = AsyncMock()
        repo.get_all = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        return event_bus
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_agent_repository, mock_event_bus):
        """Create service instance"""
        return AgentCoordinationService(
            task_repository=mock_task_repository,
            agent_repository=mock_agent_repository,
            event_bus=mock_event_bus,
            user_id="test-user-123"
        )
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task"""
        task = Mock()
        task.id = "task-123"
        task.title = "Test Task"
        return task
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent"""
        agent = Mock()
        agent.id = "agent-123"
        agent.name = "Test Agent"
        agent.is_available.return_value = True
        agent.start_task = Mock()
        agent.active_tasks = []
        agent.get_workload_percentage.return_value = 50.0
        agent.max_concurrent_tasks = 5
        agent.status = Mock(value="active")
        agent.success_rate = 95.0
        return agent
    
    @pytest.mark.asyncio
    async def test_assign_agent_to_task_task_not_found(self, service, mock_task_repository):
        """Test agent assignment when task not found"""
        # Set up repositories to support user scoping and async operations
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        mock_task_repository.get = AsyncMock(return_value=None)
        
        with pytest.raises(AgentCoordinationException) as exc_info:
            await service.assign_agent_to_task("task-123", "agent-123", "developer", "manager-123")
        
        assert "Task task-123 not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_assign_agent_to_task_agent_not_available(self, service, mock_task_repository, mock_agent_repository, mock_task, mock_agent):
        """Test agent assignment when agent not available"""
        # Set up repositories to support user scoping and async operations
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        mock_agent_repository.with_user = Mock(return_value=mock_agent_repository)
        mock_task_repository.get = AsyncMock(return_value=mock_task)
        mock_agent_repository.get = AsyncMock(return_value=mock_agent)
        mock_agent.is_available.return_value = False
        
        with pytest.raises(AgentCoordinationException) as exc_info:
            await service.assign_agent_to_task("task-123", "agent-123", "developer", "manager-123")
        
        assert "not available for new assignments" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_request_work_handoff_success(self, service, mock_agent_repository, mock_event_bus):
        """Test successful work handoff request"""
        # Setup
        from_agent = Mock(id="agent-123")
        to_agent = Mock(id="agent-456")
        mock_agent_repository.get.side_effect = [from_agent, to_agent]
        
        # Execute
        handoff = await service.request_work_handoff(
            from_agent_id="agent-123",
            to_agent_id="agent-456",
            task_id="task-123",
            work_summary="Completed authentication module",
            completed_items=["Login API", "JWT implementation"],
            remaining_items=["Password reset", "2FA"],
            handoff_notes="JWT tokens expire in 24h"
        )
        
        # Verify
        assert handoff.from_agent_id == "agent-123"
        assert handoff.to_agent_id == "agent-456"
        assert handoff.task_id == "task-123"
        assert handoff.work_summary == "Completed authentication module"
        assert len(handoff.completed_items) == 2
        assert len(handoff.remaining_items) == 2
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_accept_handoff_success(self, service, mock_event_bus):
        """Test accepting a work handoff"""
        # Setup handoff
        handoff_id = str(uuid4())
        handoff = WorkHandoff(
            handoff_id=handoff_id,
            from_agent_id="agent-123",
            to_agent_id="agent-456",
            task_id="task-123",
            initiated_at=datetime.now(),
            work_summary="Test handoff",
            completed_items=[],
            remaining_items=[]
        )
        service.handoffs[handoff_id] = handoff
        
        # Mock assign_agent_to_task
        service.assign_agent_to_task = AsyncMock()
        
        # Execute
        await service.accept_handoff(handoff_id, "agent-456", "Ready to continue")
        
        # Verify
        assert handoff.status == HandoffStatus.ACCEPTED
        service.assign_agent_to_task.assert_called_once()
        mock_event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reject_handoff_success(self, service, mock_event_bus):
        """Test rejecting a work handoff"""
        # Setup handoff
        handoff_id = str(uuid4())
        handoff = WorkHandoff(
            handoff_id=handoff_id,
            from_agent_id="agent-123",
            to_agent_id="agent-456",
            task_id="task-123",
            initiated_at=datetime.now(),
            work_summary="Test handoff",
            completed_items=[],
            remaining_items=[]
        )
        service.handoffs[handoff_id] = handoff
        
        # Execute
        await service.reject_handoff(handoff_id, "agent-456", "Currently overloaded")
        
        # Verify
        assert handoff.status == HandoffStatus.REJECTED
        assert handoff.rejection_reason == "Currently overloaded"
        mock_event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_and_resolve_conflict(self, service, mock_event_bus):
        """Test conflict detection and resolution"""
        # Execute detection
        conflict = await service.detect_and_resolve_conflict(
            task_id="task-123",
            conflict_type=ConflictType.RESOURCE_CONTENTION,
            involved_agents=["agent-123", "agent-456"],
            description="Both agents trying to modify same file",
            resolution_strategy=ResolutionStrategy.MERGE
        )
        
        # Verify
        assert conflict.conflict_type == ConflictType.RESOURCE_CONTENTION
        assert len(conflict.involved_agents) == 2
        assert conflict.task_id == "task-123"
        
        # Should have 2 events - detection and resolution
        assert mock_event_bus.publish.call_count == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_agent_status(self, service, mock_agent_repository, mock_event_bus, mock_agent):
        """Test broadcasting agent status"""
        mock_agent_repository.get.return_value = mock_agent
        
        await service.broadcast_agent_status(
            agent_id="agent-123",
            status="busy",
            current_task_id="task-123",
            current_activity="Implementing feature",
            blocker_description="Waiting for API docs"
        )
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.agent_id == "agent-123"
        assert event.status == "busy"
        assert event.current_task_id == "task-123"
        assert event.blocker_description == "Waiting for API docs"
    
    @pytest.mark.asyncio
    async def test_rebalance_workload(self, service, mock_agent_repository, mock_event_bus):
        """Test workload rebalancing"""
        # Setup agents
        overloaded_agent = Mock(
            id="agent-overloaded",
            active_tasks=["task-1", "task-2", "task-3"],
            get_workload_percentage=Mock(return_value=90)
        )
        underutilized_agent = Mock(
            id="agent-underutilized",
            active_tasks=["task-4"],
            get_workload_percentage=Mock(return_value=20),
            is_available=Mock(return_value=True)
        )
        
        mock_agent_repository.get_by_project.return_value = [overloaded_agent, underutilized_agent]
        
        # Mock handoff request
        service.request_work_handoff = AsyncMock()
        
        # Execute
        result = await service.rebalance_workload(
            project_id="project-123",
            initiated_by="manager-123",
            reason="Weekly rebalancing"
        )
        
        # Verify
        assert "tasks_reassigned" in result
        assert "workload_before" in result
        assert "workload_after" in result
        
        # Should request handoff for at least one task
        service.request_work_handoff.assert_called()
        mock_event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_agent_workload(self, service, mock_agent_repository, mock_agent):
        """Test getting detailed agent workload"""
        mock_agent_repository.get.return_value = mock_agent
        
        # Add some assignments
        assignment = WorkAssignment(
            assignment_id=str(uuid4()),
            task_id="task-123",
            assigned_agent_id="agent-123",
            assigned_by_agent_id="manager-123",
            assigned_at=datetime.now(),
            role="developer"
        )
        service.work_assignments[assignment.assignment_id] = assignment
        mock_agent.active_tasks = ["task-123"]
        
        # Execute
        workload = await service.get_agent_workload("agent-123")
        
        # Verify
        assert workload["agent_id"] == "agent-123"
        assert workload["status"] == "active"
        assert workload["workload_percentage"] == 50.0
        assert workload["current_tasks"] == 1
        assert workload["max_tasks"] == 5
        assert len(workload["active_assignments"]) == 1
        assert workload["can_accept_work"] is True
    
    @pytest.mark.asyncio
    async def test_find_best_agent_for_task(self, service, mock_task_repository, mock_agent_repository, mock_task):
        """Test finding best agent for a task"""
        # Setup
        mock_task_repository.get.return_value = mock_task
        
        agent1 = Mock(
            id="agent-1",
            name="Agent 1",
            is_available=Mock(return_value=True),
            get_workload_percentage=Mock(return_value=30),
            success_rate=90.0
        )
        agent2 = Mock(
            id="agent-2",
            name="Agent 2",
            is_available=Mock(return_value=True),
            get_workload_percentage=Mock(return_value=10),
            success_rate=95.0
        )
        
        mock_agent_repository.get_all.return_value = [agent1, agent2]
        
        # Execute
        best_agent = await service.find_best_agent_for_task(
            task_id="task-123",
            required_role=AgentRole.DEVELOPER,
            required_skills={"python": 0.8, "testing": 0.7}
        )
        
        # Verify
        assert best_agent is not None
        # Agent 2 should be selected (lower workload, higher success rate)
        assert best_agent.id == "agent-2"
    
    def test_with_user_creates_scoped_service(self, service):
        """Test creating user-scoped service"""
        new_user_id = "different-user-456"
        scoped_service = service.with_user(new_user_id)
        
        assert isinstance(scoped_service, AgentCoordinationService)
        assert scoped_service._user_id == new_user_id
        assert scoped_service._user_id != service._user_id
    
    def test_get_user_scoped_repository_with_user(self, service):
        """Test getting user-scoped repository"""
        # Test repository with 'with_user' method
        mock_repo = Mock()
        mock_repo.with_user = Mock(return_value="scoped_repo")
        
        result = service._get_user_scoped_repository(mock_repo)
        
        mock_repo.with_user.assert_called_once_with("test-user-123")
        assert result == "scoped_repo"
    
    def test_get_user_scoped_repository_with_user_id_attribute(self, service):
        """Test getting user-scoped repository with user_id attribute"""
        # Test repository with user_id attribute and session
        mock_repo = Mock()
        mock_repo.user_id = "different-user"
        mock_repo.session = Mock()
        
        # Configure mock to not have with_user method but have user_id and session
        mock_repo.configure_mock(**{
            'with_user': None,  # Ensure hasattr returns False
            'user_id': 'different-user',
            'session': Mock()
        })
        del mock_repo.with_user  # Remove with_user to ensure hasattr returns False
        
        # Create a proper mock class that can be instantiated
        mock_repo_class = Mock()
        mock_new_repo = Mock()
        mock_repo_class.return_value = mock_new_repo
        
        with patch('builtins.type', return_value=mock_repo_class):
            result = service._get_user_scoped_repository(mock_repo)
            
            # Should create new instance with correct user_id
            mock_repo_class.assert_called_once_with(mock_repo.session, user_id="test-user-123")
            assert result == mock_new_repo
    
    def test_get_user_scoped_repository_no_user_context(self, mock_task_repository):
        """Test repository scoping without user context"""
        service = AgentCoordinationService(
            task_repository=mock_task_repository,
            user_id=None  # No user context
        )
        
        mock_repo = Mock()
        result = service._get_user_scoped_repository(mock_repo)
        
        # Should return original repository unchanged
        assert result == mock_repo
    
    def test_coordination_context_workload_tracking(self):
        """Test CoordinationContext workload tracking"""
        context = CoordinationContext(
            task=Mock(),
            available_agents=[],
            current_assignments={"agent-1": ["task-1", "task-2"]},
            workload_metrics={"agent-1": 0.75, "agent-2": 0.3}
        )
        
        assert context.get_agent_workload("agent-1") == 0.75
        assert context.get_agent_workload("agent-3") == 0.0  # Unknown agent
        assert context.is_agent_overloaded("agent-1") is False
        assert context.is_agent_overloaded("agent-1", threshold=0.7) is True
    
    @pytest.mark.asyncio
    async def test_assign_agent_user_scoped_repositories(self, service, mock_task_repository, mock_agent_repository, mock_event_bus, mock_task, mock_agent):
        """Test agent assignment uses user-scoped repositories"""
        # Setup repositories that support user scoping
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        mock_agent_repository.with_user = Mock(return_value=mock_agent_repository)
        
        # Set up async mocks
        mock_task_repository.get = AsyncMock(return_value=mock_task)
        mock_agent_repository.get = AsyncMock(return_value=mock_agent)
        mock_agent_repository.save = AsyncMock()
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await service.assign_agent_to_task(
            task_id="task-123",
            agent_id="agent-123",
            role="developer",
            assigned_by="manager-123"
        )
        
        # Verify repositories were scoped to user
        mock_task_repository.with_user.assert_called_with("test-user-123")
        mock_agent_repository.with_user.assert_called_with("test-user-123")
    
    @pytest.mark.asyncio
    async def test_handoff_with_invalid_agents(self, service, mock_agent_repository, mock_event_bus):
        """Test work handoff with invalid agent IDs"""
        # Setup - one agent not found
        mock_agent_repository.get.side_effect = [Mock(id="agent-123"), None]
        
        with pytest.raises(AgentCoordinationException) as exc_info:
            await service.request_work_handoff(
                from_agent_id="agent-123",
                to_agent_id="invalid-agent",
                task_id="task-123",
                work_summary="Test",
                completed_items=[],
                remaining_items=[]
            )
        
        assert "Invalid agent IDs" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handoff_wrong_target_agent(self, service, mock_event_bus):
        """Test accepting/rejecting handoff with wrong target agent"""
        # Setup handoff
        handoff_id = str(uuid4())
        handoff = WorkHandoff(
            handoff_id=handoff_id,
            from_agent_id="agent-123",
            to_agent_id="agent-456",  # Target is agent-456
            task_id="task-123",
            initiated_at=datetime.now(),
            work_summary="Test handoff",
            completed_items=[],
            remaining_items=[]
        )
        service.handoffs[handoff_id] = handoff
        
        # Try to accept as wrong agent
        with pytest.raises(AgentCoordinationException) as exc_info:
            await service.accept_handoff(handoff_id, "agent-789", "Ready")
        
        assert "not the target of this handoff" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_conflict(self, service, mock_event_bus):
        """Test resolving a non-existent conflict"""
        with pytest.raises(AgentCoordinationException) as exc_info:
            await service.resolve_conflict(
                conflict_id="nonexistent-conflict",
                strategy=ResolutionStrategy.MERGE,
                resolved_by="manager-123",
                details="Test resolution"
            )
        
        assert "Conflict nonexistent-conflict not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_find_best_agent_no_available_agents(self, service, mock_task_repository, mock_agent_repository, mock_task):
        """Test finding best agent when no agents are available"""
        mock_task_repository.get.return_value = mock_task
        
        # All agents are unavailable
        agent = Mock(
            id="agent-1",
            is_available=Mock(return_value=False)
        )
        mock_agent_repository.get_all.return_value = [agent]
        
        result = await service.find_best_agent_for_task("task-123")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_best_agent_low_scores(self, service, mock_task_repository, mock_agent_repository, mock_task):
        """Test finding best agent when all scores are below threshold"""
        mock_task_repository.get.return_value = mock_task
        
        # Agent with very low availability
        agent = Mock(
            id="agent-1",
            name="Agent 1",
            is_available=Mock(return_value=True),
            get_workload_percentage=Mock(return_value=95),  # Very high workload
            success_rate=20.0  # Very low success rate
        )
        mock_agent_repository.get_all.return_value = [agent]
        
        result = await service.find_best_agent_for_task(
            task_id="task-123",
            required_role=AgentRole.DEVELOPER
        )
        
        # Should return None if score is too low
        assert result is None