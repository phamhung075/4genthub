"""Test coordination value objects"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
import uuid

from fastmcp.task_management.domain.value_objects.coordination import (
    CoordinationType,
    HandoffStatus,
    ConflictType,
    ResolutionStrategy,
    CoordinationStrategy,
    CoordinationRequest,
    WorkAssignment,
    WorkHandoff,
    ConflictResolution,
    AgentCommunication,
    CoordinationMessage
)


class TestCoordinationRequest:
    """Test coordination request value object"""

    @pytest.fixture
    def request(self):
        """Create test coordination request"""
        return CoordinationRequest(
            request_id="req-123",
            coordination_type=CoordinationType.HANDOFF,
            requesting_agent_id="agent-1",
            target_agent_id="agent-2",
            task_id="task-456",
            created_at=datetime.utcnow(),
            reason="Need expertise in frontend",
            priority="high",
            deadline=datetime.utcnow() + timedelta(hours=2)
        )

    def test_request_creation(self, request):
        """Test creating coordination request"""
        assert request.request_id == "req-123"
        assert request.coordination_type == CoordinationType.HANDOFF
        assert request.requesting_agent_id == "agent-1"
        assert request.target_agent_id == "agent-2"
        assert request.task_id == "task-456"
        assert request.reason == "Need expertise in frontend"
        assert request.priority == "high"

    def test_is_expired(self, request):
        """Test checking if request is expired"""
        # Not expired
        assert not request.is_expired()
        
        # Create expired request
        expired_request = CoordinationRequest(
            request_id="req-2",
            coordination_type=CoordinationType.REVIEW,
            requesting_agent_id="agent-1",
            target_agent_id="agent-2",
            task_id="task-1",
            created_at=datetime.utcnow(),
            reason="Review needed",
            deadline=datetime.utcnow() - timedelta(hours=1)
        )
        assert expired_request.is_expired()
        
        # No deadline
        no_deadline = CoordinationRequest(
            request_id="req-3",
            coordination_type=CoordinationType.CONSULTATION,
            requesting_agent_id="agent-1",
            target_agent_id="agent-2",
            task_id="task-1",
            created_at=datetime.utcnow(),
            reason="Need advice"
        )
        assert not no_deadline.is_expired()

    def test_to_notification(self, request):
        """Test converting to notification"""
        notification = request.to_notification()
        
        assert notification["type"] == "coordination_handoff"
        assert notification["from_agent"] == "agent-1"
        assert notification["task_id"] == "task-456"
        assert notification["priority"] == "high"
        assert notification["reason"] == "Need expertise in frontend"
        assert notification["deadline"] is not None
        assert isinstance(notification["context"], dict)

    def test_frozen_dataclass(self, request):
        """Test that request is immutable"""
        with pytest.raises(AttributeError):
            request.priority = "low"


class TestWorkAssignment:
    """Test work assignment value object"""

    @pytest.fixture
    def assignment(self):
        """Create test work assignment"""
        return WorkAssignment(
            assignment_id="assign-123",
            task_id="task-456",
            assigned_agent_id="agent-789",
            assigned_by_agent_id="manager-1",
            assigned_at=datetime.utcnow(),
            role="frontend_developer",
            responsibilities=["Implement UI", "Write tests"],
            estimated_hours=8.0,
            due_date=datetime.utcnow() + timedelta(days=2)
        )

    def test_assignment_creation(self, assignment):
        """Test creating work assignment"""
        assert assignment.assignment_id == "assign-123"
        assert assignment.task_id == "task-456"
        assert assignment.assigned_agent_id == "agent-789"
        assert assignment.role == "frontend_developer"
        assert len(assignment.responsibilities) == 2
        assert assignment.estimated_hours == 8.0

    def test_is_overdue(self, assignment):
        """Test checking if assignment is overdue"""
        # Not overdue
        assert not assignment.is_overdue()
        
        # Create overdue assignment
        overdue = WorkAssignment(
            assignment_id="assign-2",
            task_id="task-1",
            assigned_agent_id="agent-1",
            assigned_by_agent_id="manager-1",
            assigned_at=datetime.utcnow(),
            due_date=datetime.utcnow() - timedelta(hours=1)
        )
        assert overdue.is_overdue()

    def test_to_task_context(self, assignment):
        """Test converting to task context"""
        context = assignment.to_task_context()
        
        assert "assignment" in context
        assert context["assignment"]["agent_id"] == "agent-789"
        assert context["assignment"]["role"] == "frontend_developer"
        assert context["assignment"]["assigned_by"] == "manager-1"
        assert len(context["assignment"]["responsibilities"]) == 2


class TestWorkHandoff:
    """Test work handoff value object"""

    @pytest.fixture
    def handoff(self):
        """Create test work handoff"""
        return WorkHandoff(
            handoff_id="handoff-123",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            task_id="task-456",
            initiated_at=datetime.utcnow(),
            work_summary="Completed backend API",
            completed_items=["API endpoints", "Database schema"],
            remaining_items=["Frontend integration", "Documentation"]
        )

    def test_handoff_creation(self, handoff):
        """Test creating work handoff"""
        assert handoff.handoff_id == "handoff-123"
        assert handoff.from_agent_id == "agent-1"
        assert handoff.to_agent_id == "agent-2"
        assert handoff.status == HandoffStatus.PENDING
        assert len(handoff.completed_items) == 2
        assert len(handoff.remaining_items) == 2

    def test_accept_handoff(self, handoff):
        """Test accepting handoff"""
        handoff.accept()
        
        assert handoff.status == HandoffStatus.ACCEPTED
        assert handoff.accepted_at is not None
        
        # Cannot accept again
        with pytest.raises(ValueError):
            handoff.accept()

    def test_reject_handoff(self, handoff):
        """Test rejecting handoff"""
        handoff.reject("Too busy with other tasks")
        
        assert handoff.status == HandoffStatus.REJECTED
        assert handoff.rejection_reason == "Too busy with other tasks"
        
        # Cannot reject again
        with pytest.raises(ValueError):
            handoff.reject("Another reason")

    def test_complete_handoff(self, handoff):
        """Test completing handoff"""
        # Must be in progress first
        handoff.status = HandoffStatus.IN_PROGRESS
        
        handoff.complete()
        
        assert handoff.status == HandoffStatus.COMPLETED
        assert handoff.completed_at is not None

    def test_complete_invalid_status(self, handoff):
        """Test completing from invalid status"""
        with pytest.raises(ValueError):
            handoff.complete()

    def test_to_handoff_package(self, handoff):
        """Test creating handoff package"""
        package = handoff.to_handoff_package()
        
        assert package["handoff_id"] == "handoff-123"
        assert package["from_agent"] == "agent-1"
        assert package["to_agent"] == "agent-2"
        assert package["status"] == "pending"
        assert len(package["completed"]) == 2
        assert len(package["remaining"]) == 2
        assert "timeline" in package


class TestConflictResolution:
    """Test conflict resolution value object"""

    @pytest.fixture
    def conflict(self):
        """Create test conflict"""
        return ConflictResolution(
            conflict_id="conflict-123",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            involved_agents=["agent-1", "agent-2"],
            task_id="task-456",
            detected_at=datetime.utcnow(),
            description="Both agents editing same file",
            impact_assessment="medium"
        )

    def test_conflict_creation(self, conflict):
        """Test creating conflict resolution"""
        assert conflict.conflict_id == "conflict-123"
        assert conflict.conflict_type == ConflictType.CONCURRENT_EDIT
        assert len(conflict.involved_agents) == 2
        assert conflict.impact_assessment == "medium"
        assert not conflict.is_resolved()

    def test_resolve_conflict(self, conflict):
        """Test resolving conflict"""
        conflict.resolve(
            strategy=ResolutionStrategy.MERGE,
            resolved_by="agent-1",
            details="Merged changes successfully"
        )
        
        assert conflict.is_resolved()
        assert conflict.resolution_strategy == ResolutionStrategy.MERGE
        assert conflict.resolved_by == "agent-1"
        assert conflict.resolution_details == "Merged changes successfully"
        assert conflict.resolved_at is not None

    def test_resolve_already_resolved(self, conflict):
        """Test resolving already resolved conflict"""
        conflict.resolve(ResolutionStrategy.MERGE, "agent-1", "Merged")
        
        with pytest.raises(ValueError):
            conflict.resolve(ResolutionStrategy.OVERRIDE, "agent-2", "Override")

    def test_add_vote(self, conflict):
        """Test adding votes"""
        conflict.add_vote("agent-1", "merge")
        conflict.add_vote("agent-2", "override")
        conflict.add_vote("agent-3", "merge")
        
        assert len(conflict.votes) == 3
        assert conflict.votes["agent-1"] == "merge"

    def test_get_vote_summary(self, conflict):
        """Test getting vote summary"""
        conflict.add_vote("agent-1", "merge")
        conflict.add_vote("agent-2", "override")
        conflict.add_vote("agent-3", "merge")
        conflict.add_vote("agent-4", "merge")
        
        summary = conflict.get_vote_summary()
        
        assert summary["merge"] == 3
        assert summary["override"] == 1


class TestAgentCommunication:
    """Test agent communication value object"""

    @pytest.fixture
    def communication(self):
        """Create test communication"""
        return AgentCommunication(
            message_id="msg-123",
            from_agent_id="agent-1",
            to_agent_ids=["agent-2", "agent-3"],
            task_id="task-456",
            sent_at=datetime.utcnow(),
            message_type="status_update",
            subject="Progress Update",
            content="Completed 50% of implementation",
            priority="normal",
            requires_response=True,
            response_deadline=datetime.utcnow() + timedelta(hours=1)
        )

    def test_communication_creation(self, communication):
        """Test creating agent communication"""
        assert communication.message_id == "msg-123"
        assert communication.from_agent_id == "agent-1"
        assert len(communication.to_agent_ids) == 2
        assert communication.message_type == "status_update"
        assert communication.requires_response

    def test_is_broadcast(self, communication):
        """Test checking if broadcast"""
        assert communication.is_broadcast()
        
        # Single recipient
        single = AgentCommunication(
            message_id="msg-2",
            from_agent_id="agent-1",
            to_agent_ids=["agent-2"],
            task_id=None,
            sent_at=datetime.utcnow(),
            message_type="question",
            subject="Question",
            content="Need clarification"
        )
        assert not single.is_broadcast()

    def test_needs_urgent_response(self, communication):
        """Test checking if needs urgent response"""
        # Has response deadline within 2 hours
        assert communication.needs_urgent_response()
        
        # High priority
        high_priority = AgentCommunication(
            message_id="msg-2",
            from_agent_id="agent-1",
            to_agent_ids=["agent-2"],
            task_id=None,
            sent_at=datetime.utcnow(),
            message_type="question",
            subject="Urgent",
            content="Need immediate help",
            priority="high",
            requires_response=True
        )
        assert high_priority.needs_urgent_response()
        
        # No response required
        no_response = AgentCommunication(
            message_id="msg-3",
            from_agent_id="agent-1",
            to_agent_ids=["agent-2"],
            task_id=None,
            sent_at=datetime.utcnow(),
            message_type="notification",
            subject="FYI",
            content="Just letting you know",
            requires_response=False
        )
        assert not no_response.needs_urgent_response()

    def test_frozen_dataclass(self, communication):
        """Test that communication is immutable"""
        with pytest.raises(AttributeError):
            communication.priority = "high"


class TestCoordinationMessage:
    """Test coordination message value object"""

    @pytest.fixture
    def message(self):
        """Create test coordination message"""
        return CoordinationMessage(
            message_id="msg-123",
            message_type="handoff_request",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            timestamp=datetime.utcnow(),
            payload={"task_id": "task-456", "reason": "Need help"},
            priority="high",
            requires_response=True,
            correlation_id="corr-789"
        )

    def test_message_creation(self, message):
        """Test creating coordination message"""
        assert message.message_id == "msg-123"
        assert message.message_type == "handoff_request"
        assert message.from_agent_id == "agent-1"
        assert message.to_agent_id == "agent-2"
        assert message.payload["task_id"] == "task-456"
        assert message.priority == "high"
        assert message.requires_response
        assert message.correlation_id == "corr-789"

    def test_is_broadcast(self, message):
        """Test checking if broadcast"""
        assert not message.is_broadcast()
        
        # Broadcast message
        broadcast = CoordinationMessage(
            message_id="msg-2",
            message_type="status_update",
            from_agent_id="agent-1",
            to_agent_id=None,
            timestamp=datetime.utcnow(),
            payload={"status": "available"}
        )
        assert broadcast.is_broadcast()

    def test_to_json(self, message):
        """Test converting to JSON"""
        json_data = message.to_json()
        
        assert json_data["message_id"] == "msg-123"
        assert json_data["message_type"] == "handoff_request"
        assert json_data["from_agent_id"] == "agent-1"
        assert json_data["to_agent_id"] == "agent-2"
        assert isinstance(json_data["timestamp"], str)  # ISO format
        assert json_data["payload"]["task_id"] == "task-456"
        assert json_data["priority"] == "high"
        assert json_data["requires_response"] is True
        assert json_data["correlation_id"] == "corr-789"

    def test_frozen_dataclass(self, message):
        """Test that message is immutable"""
        with pytest.raises(AttributeError):
            message.priority = "low"


class TestEnums:
    """Test coordination enums"""

    def test_coordination_type(self):
        """Test coordination type enum"""
        assert CoordinationType.HANDOFF.value == "handoff"
        assert CoordinationType.PARALLEL.value == "parallel"
        assert CoordinationType.REVIEW.value == "review"
        assert CoordinationType.ESCALATION.value == "escalation"
        assert CoordinationType.COLLABORATION.value == "collaboration"
        assert CoordinationType.DELEGATION.value == "delegation"
        assert CoordinationType.CONSULTATION.value == "consultation"

    def test_handoff_status(self):
        """Test handoff status enum"""
        assert HandoffStatus.PENDING.value == "pending"
        assert HandoffStatus.ACCEPTED.value == "accepted"
        assert HandoffStatus.REJECTED.value == "rejected"
        assert HandoffStatus.IN_PROGRESS.value == "in_progress"
        assert HandoffStatus.COMPLETED.value == "completed"
        assert HandoffStatus.CANCELLED.value == "cancelled"

    def test_conflict_type(self):
        """Test conflict type enum"""
        assert ConflictType.CONCURRENT_EDIT.value == "concurrent_edit"
        assert ConflictType.RESOURCE_CONTENTION.value == "resource_contention"
        assert ConflictType.PRIORITY_DISAGREEMENT.value == "priority_disagreement"
        assert ConflictType.APPROACH_DIFFERENCE.value == "approach_difference"
        assert ConflictType.DEPENDENCY_CONFLICT.value == "dependency_conflict"
        assert ConflictType.SCHEDULE_CONFLICT.value == "schedule_conflict"

    def test_resolution_strategy(self):
        """Test resolution strategy enum"""
        assert ResolutionStrategy.MERGE.value == "merge"
        assert ResolutionStrategy.OVERRIDE.value == "override"
        assert ResolutionStrategy.VOTE.value == "vote"
        assert ResolutionStrategy.ESCALATE.value == "escalate"
        assert ResolutionStrategy.COLLABORATE.value == "collaborate"
        assert ResolutionStrategy.DEFER.value == "defer"

    def test_coordination_strategy(self):
        """Test coordination strategy enum"""
        assert CoordinationStrategy.ROUND_ROBIN.value == "round_robin"
        assert CoordinationStrategy.EXPERTISE_BASED.value == "expertise_based"
        assert CoordinationStrategy.LOAD_BALANCING.value == "load_balancing"
        assert CoordinationStrategy.PRIORITY_FIRST.value == "priority_first"
        assert CoordinationStrategy.COLLABORATIVE.value == "collaborative"
        assert CoordinationStrategy.SEQUENTIAL.value == "sequential"
        assert CoordinationStrategy.PARALLEL.value == "parallel"