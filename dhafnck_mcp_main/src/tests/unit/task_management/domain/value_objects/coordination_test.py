"""Test suite for Coordination value objects.

Tests the coordination value objects including:
- CoordinationType and HandoffStatus enums
- ConflictType and ResolutionStrategy enums
- CoordinationStrategy enum
- CoordinationRequest value object
- WorkAssignment value object
- WorkHandoff entity
- ConflictResolution entity
- AgentCommunication value object
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

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
    AgentCommunication
)


class TestEnums:
    """Test cases for coordination enums."""
    
    def test_coordination_type_values(self):
        """Test CoordinationType enum values."""
        assert CoordinationType.HANDOFF.value == "handoff"
        assert CoordinationType.PARALLEL.value == "parallel"
        assert CoordinationType.REVIEW.value == "review"
        assert CoordinationType.ESCALATION.value == "escalation"
        assert CoordinationType.COLLABORATION.value == "collaboration"
        assert CoordinationType.DELEGATION.value == "delegation"
        assert CoordinationType.CONSULTATION.value == "consultation"
    
    def test_handoff_status_values(self):
        """Test HandoffStatus enum values."""
        assert HandoffStatus.PENDING.value == "pending"
        assert HandoffStatus.ACCEPTED.value == "accepted"
        assert HandoffStatus.REJECTED.value == "rejected"
        assert HandoffStatus.IN_PROGRESS.value == "in_progress"
        assert HandoffStatus.COMPLETED.value == "completed"
        assert HandoffStatus.CANCELLED.value == "cancelled"
    
    def test_conflict_type_values(self):
        """Test ConflictType enum values."""
        assert ConflictType.CONCURRENT_EDIT.value == "concurrent_edit"
        assert ConflictType.RESOURCE_CONTENTION.value == "resource_contention"
        assert ConflictType.PRIORITY_DISAGREEMENT.value == "priority_disagreement"
        assert ConflictType.APPROACH_DIFFERENCE.value == "approach_difference"
        assert ConflictType.DEPENDENCY_CONFLICT.value == "dependency_conflict"
        assert ConflictType.SCHEDULE_CONFLICT.value == "schedule_conflict"
    
    def test_resolution_strategy_values(self):
        """Test ResolutionStrategy enum values."""
        assert ResolutionStrategy.MERGE.value == "merge"
        assert ResolutionStrategy.OVERRIDE.value == "override"
        assert ResolutionStrategy.VOTE.value == "vote"
        assert ResolutionStrategy.ESCALATE.value == "escalate"
        assert ResolutionStrategy.COLLABORATE.value == "collaborate"
        assert ResolutionStrategy.DEFER.value == "defer"
    
    def test_coordination_strategy_values(self):
        """Test CoordinationStrategy enum values."""
        assert CoordinationStrategy.ROUND_ROBIN.value == "round_robin"
        assert CoordinationStrategy.EXPERTISE_BASED.value == "expertise_based"
        assert CoordinationStrategy.LOAD_BALANCING.value == "load_balancing"
        assert CoordinationStrategy.PRIORITY_FIRST.value == "priority_first"
        assert CoordinationStrategy.COLLABORATIVE.value == "collaborative"
        assert CoordinationStrategy.SEQUENTIAL.value == "sequential"
        assert CoordinationStrategy.PARALLEL.value == "parallel"


class TestCoordinationRequest:
    """Test cases for CoordinationRequest value object."""
    
    def test_create_coordination_request_minimal(self):
        """Test creating coordination request with minimal data."""
        now = datetime.now(timezone.utc)
        request = CoordinationRequest(
            request_id="req-123",
            coordination_type=CoordinationType.HANDOFF,
            requesting_agent_id="agent-1",
            target_agent_id="agent-2",
            task_id="task-123",
            created_at=now,
            reason="Need help with implementation"
        )
        
        assert request.request_id == "req-123"
        assert request.coordination_type == CoordinationType.HANDOFF
        assert request.requesting_agent_id == "agent-1"
        assert request.target_agent_id == "agent-2"
        assert request.task_id == "task-123"
        assert request.created_at == now
        assert request.reason == "Need help with implementation"
        assert request.priority == "medium"
        assert request.deadline is None
        assert request.context == {}
        assert request.handoff_notes is None
        assert request.completion_criteria == []
        assert request.review_items == []
        assert request.review_checklist == {}
    
    def test_create_coordination_request_full(self):
        """Test creating coordination request with all fields."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=24)
        
        request = CoordinationRequest(
            request_id="req-456",
            coordination_type=CoordinationType.REVIEW,
            requesting_agent_id="agent-3",
            target_agent_id="agent-4",
            task_id="task-456",
            created_at=now,
            reason="Code review needed",
            context={"pr_number": 123, "branch": "feature/auth"},
            priority="high",
            deadline=deadline,
            handoff_notes="Please check authentication logic",
            completion_criteria=["All tests pass", "Security review complete"],
            review_items=["auth.py", "login.py"],
            review_checklist={"security": True, "performance": False}
        )
        
        assert request.context == {"pr_number": 123, "branch": "feature/auth"}
        assert request.priority == "high"
        assert request.deadline == deadline
        assert request.handoff_notes == "Please check authentication logic"
        assert request.completion_criteria == ["All tests pass", "Security review complete"]
        assert request.review_items == ["auth.py", "login.py"]
        assert request.review_checklist == {"security": True, "performance": False}
    
    def test_coordination_request_immutable(self):
        """Test that coordination request is immutable."""
        request = CoordinationRequest(
            request_id="req-789",
            coordination_type=CoordinationType.ESCALATION,
            requesting_agent_id="agent-5",
            target_agent_id="agent-6",
            task_id="task-789",
            created_at=datetime.now(timezone.utc),
            reason="Escalation needed"
        )
        
        with pytest.raises(AttributeError):
            request.priority = "critical"
    
    def test_is_expired_no_deadline(self):
        """Test is_expired when no deadline is set."""
        request = CoordinationRequest(
            request_id="req-001",
            coordination_type=CoordinationType.CONSULTATION,
            requesting_agent_id="agent-7",
            target_agent_id="agent-8",
            task_id="task-001",
            created_at=datetime.now(timezone.utc),
            reason="Need expertise"
        )
        
        assert not request.is_expired()
    
    def test_is_expired_future_deadline(self):
        """Test is_expired with future deadline."""
        request = CoordinationRequest(
            request_id="req-002",
            coordination_type=CoordinationType.DELEGATION,
            requesting_agent_id="agent-9",
            target_agent_id="agent-10",
            task_id="task-002",
            created_at=datetime.now(timezone.utc),
            reason="Delegate subtask",
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        assert not request.is_expired()
    
    def test_is_expired_past_deadline(self):
        """Test is_expired with past deadline."""
        request = CoordinationRequest(
            request_id="req-003",
            coordination_type=CoordinationType.PARALLEL,
            requesting_agent_id="agent-11",
            target_agent_id="agent-12",
            task_id="task-003",
            created_at=datetime.now(timezone.utc),
            reason="Parallel work",
            deadline=datetime.now() - timedelta(hours=1)
        )
        
        assert request.is_expired()
    
    def test_to_notification(self):
        """Test converting request to notification format."""
        created_at = datetime.now(timezone.utc)
        deadline = created_at + timedelta(days=1)
        
        request = CoordinationRequest(
            request_id="req-004",
            coordination_type=CoordinationType.COLLABORATION,
            requesting_agent_id="agent-13",
            target_agent_id="agent-14",
            task_id="task-004",
            created_at=created_at,
            reason="Let's collaborate",
            context={"work_item": "feature"},
            priority="high",
            deadline=deadline
        )
        
        notification = request.to_notification()
        
        assert notification["type"] == "coordination_collaboration"
        assert notification["from_agent"] == "agent-13"
        assert notification["task_id"] == "task-004"
        assert notification["priority"] == "high"
        assert notification["reason"] == "Let's collaborate"
        assert notification["created_at"] == created_at.isoformat()
        assert notification["deadline"] == deadline.isoformat()
        assert notification["context"] == {"work_item": "feature"}


class TestWorkAssignment:
    """Test cases for WorkAssignment value object."""
    
    def test_create_work_assignment_minimal(self):
        """Test creating work assignment with minimal data."""
        now = datetime.now(timezone.utc)
        assignment = WorkAssignment(
            assignment_id="assign-123",
            task_id="task-123",
            assigned_agent_id="agent-1",
            assigned_by_agent_id="agent-2",
            assigned_at=now
        )
        
        assert assignment.assignment_id == "assign-123"
        assert assignment.task_id == "task-123"
        assert assignment.assigned_agent_id == "agent-1"
        assert assignment.assigned_by_agent_id == "agent-2"
        assert assignment.assigned_at == now
        assert assignment.role is None
        assert assignment.responsibilities == []
        assert assignment.deliverables == []
        assert assignment.constraints == {}
        assert assignment.estimated_hours is None
        assert assignment.due_date is None
        assert assignment.collaborating_agents == []
        assert assignment.reporting_to is None
    
    def test_create_work_assignment_full(self):
        """Test creating work assignment with all fields."""
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=3)
        
        assignment = WorkAssignment(
            assignment_id="assign-456",
            task_id="task-456",
            assigned_agent_id="agent-3",
            assigned_by_agent_id="agent-4",
            assigned_at=now,
            role="Lead Developer",
            responsibilities=["Design architecture", "Code review"],
            deliverables=["API implementation", "Documentation"],
            constraints={"language": "Python", "framework": "FastAPI"},
            estimated_hours=40.0,
            due_date=due_date,
            collaborating_agents=["agent-5", "agent-6"],
            reporting_to="agent-7"
        )
        
        assert assignment.role == "Lead Developer"
        assert assignment.responsibilities == ["Design architecture", "Code review"]
        assert assignment.deliverables == ["API implementation", "Documentation"]
        assert assignment.constraints == {"language": "Python", "framework": "FastAPI"}
        assert assignment.estimated_hours == 40.0
        assert assignment.due_date == due_date
        assert assignment.collaborating_agents == ["agent-5", "agent-6"]
        assert assignment.reporting_to == "agent-7"
    
    def test_work_assignment_immutable(self):
        """Test that work assignment is immutable."""
        assignment = WorkAssignment(
            assignment_id="assign-789",
            task_id="task-789",
            assigned_agent_id="agent-8",
            assigned_by_agent_id="agent-9",
            assigned_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(AttributeError):
            assignment.role = "New Role"
    
    def test_is_overdue_no_due_date(self):
        """Test is_overdue when no due date is set."""
        assignment = WorkAssignment(
            assignment_id="assign-001",
            task_id="task-001",
            assigned_agent_id="agent-10",
            assigned_by_agent_id="agent-11",
            assigned_at=datetime.now(timezone.utc)
        )
        
        assert not assignment.is_overdue()
    
    def test_is_overdue_future_due_date(self):
        """Test is_overdue with future due date."""
        assignment = WorkAssignment(
            assignment_id="assign-002",
            task_id="task-002",
            assigned_agent_id="agent-12",
            assigned_by_agent_id="agent-13",
            assigned_at=datetime.now(timezone.utc),
            due_date=datetime.now() + timedelta(hours=1)
        )
        
        assert not assignment.is_overdue()
    
    def test_is_overdue_past_due_date(self):
        """Test is_overdue with past due date."""
        assignment = WorkAssignment(
            assignment_id="assign-003",
            task_id="task-003",
            assigned_agent_id="agent-14",
            assigned_by_agent_id="agent-15",
            assigned_at=datetime.now(timezone.utc),
            due_date=datetime.now() - timedelta(hours=1)
        )
        
        assert assignment.is_overdue()
    
    def test_to_task_context(self):
        """Test converting assignment to task context format."""
        assigned_at = datetime.now(timezone.utc)
        due_date = assigned_at + timedelta(days=2)
        
        assignment = WorkAssignment(
            assignment_id="assign-004",
            task_id="task-004",
            assigned_agent_id="agent-16",
            assigned_by_agent_id="agent-17",
            assigned_at=assigned_at,
            role="Backend Developer",
            responsibilities=["Implement API", "Write tests"],
            deliverables=["REST endpoints", "Unit tests"],
            collaborating_agents=["agent-18", "agent-19"],
            due_date=due_date
        )
        
        context = assignment.to_task_context()
        
        assert context["assignment"]["agent_id"] == "agent-16"
        assert context["assignment"]["role"] == "Backend Developer"
        assert context["assignment"]["assigned_by"] == "agent-17"
        assert context["assignment"]["assigned_at"] == assigned_at.isoformat()
        assert context["assignment"]["responsibilities"] == ["Implement API", "Write tests"]
        assert context["assignment"]["deliverables"] == ["REST endpoints", "Unit tests"]
        assert context["assignment"]["collaborators"] == ["agent-18", "agent-19"]
        assert context["assignment"]["due_date"] == due_date


class TestWorkHandoff:
    """Test cases for WorkHandoff entity."""
    
    def test_create_work_handoff_minimal(self):
        """Test creating work handoff with minimal data."""
        now = datetime.now(timezone.utc)
        handoff = WorkHandoff(
            handoff_id="handoff-123",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            task_id="task-123",
            initiated_at=now
        )
        
        assert handoff.handoff_id == "handoff-123"
        assert handoff.from_agent_id == "agent-1"
        assert handoff.to_agent_id == "agent-2"
        assert handoff.task_id == "task-123"
        assert handoff.initiated_at == now
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.work_summary == ""
        assert handoff.completed_items == []
        assert handoff.remaining_items == []
        assert handoff.known_issues == []
        assert handoff.handoff_notes == ""
        assert handoff.artifacts == {}
        assert handoff.documentation_links == []
        assert handoff.accepted_at is None
        assert handoff.completed_at is None
        assert handoff.rejection_reason is None
    
    def test_create_work_handoff_full(self):
        """Test creating work handoff with all fields."""
        now = datetime.now(timezone.utc)
        
        handoff = WorkHandoff(
            handoff_id="handoff-456",
            from_agent_id="agent-3",
            to_agent_id="agent-4",
            task_id="task-456",
            initiated_at=now,
            status=HandoffStatus.ACCEPTED,
            work_summary="Completed authentication module",
            completed_items=["Login API", "JWT implementation"],
            remaining_items=["Password reset", "OAuth integration"],
            known_issues=["Token expiry handling"],
            handoff_notes="Check security requirements",
            artifacts={"api_docs": "/ai_docs/api.md", "tests": "/tests/auth"},
            documentation_links=["http://ai_docs.example.com/auth"],
            accepted_at=now + timedelta(minutes=30)
        )
        
        assert handoff.status == HandoffStatus.ACCEPTED
        assert handoff.work_summary == "Completed authentication module"
        assert handoff.completed_items == ["Login API", "JWT implementation"]
        assert handoff.remaining_items == ["Password reset", "OAuth integration"]
        assert handoff.known_issues == ["Token expiry handling"]
        assert handoff.handoff_notes == "Check security requirements"
        assert handoff.artifacts == {"api_docs": "/ai_docs/api.md", "tests": "/tests/auth"}
        assert handoff.documentation_links == ["http://ai_docs.example.com/auth"]
        assert handoff.accepted_at == now + timedelta(minutes=30)
    
    def test_accept_handoff(self):
        """Test accepting a handoff."""
        handoff = WorkHandoff(
            handoff_id="handoff-001",
            from_agent_id="agent-5",
            to_agent_id="agent-6",
            task_id="task-001",
            initiated_at=datetime.now(timezone.utc)
        )
        
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.accepted_at is None
        
        handoff.accept()
        
        assert handoff.status == HandoffStatus.ACCEPTED
        assert handoff.accepted_at is not None
    
    def test_accept_handoff_invalid_status(self):
        """Test accepting handoff with invalid status."""
        handoff = WorkHandoff(
            handoff_id="handoff-002",
            from_agent_id="agent-7",
            to_agent_id="agent-8",
            task_id="task-002",
            initiated_at=datetime.now(timezone.utc),
            status=HandoffStatus.COMPLETED
        )
        
        with pytest.raises(ValueError) as exc_info:
            handoff.accept()
        
        assert "Cannot accept handoff in status" in str(exc_info.value)
    
    def test_reject_handoff(self):
        """Test rejecting a handoff."""
        handoff = WorkHandoff(
            handoff_id="handoff-003",
            from_agent_id="agent-9",
            to_agent_id="agent-10",
            task_id="task-003",
            initiated_at=datetime.now(timezone.utc)
        )
        
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.rejection_reason is None
        
        handoff.reject("Insufficient information provided")
        
        assert handoff.status == HandoffStatus.REJECTED
        assert handoff.rejection_reason == "Insufficient information provided"
    
    def test_reject_handoff_invalid_status(self):
        """Test rejecting handoff with invalid status."""
        handoff = WorkHandoff(
            handoff_id="handoff-004",
            from_agent_id="agent-11",
            to_agent_id="agent-12",
            task_id="task-004",
            initiated_at=datetime.now(timezone.utc),
            status=HandoffStatus.ACCEPTED
        )
        
        with pytest.raises(ValueError) as exc_info:
            handoff.reject("Too late")
        
        assert "Cannot reject handoff in status" in str(exc_info.value)
    
    def test_complete_handoff(self):
        """Test completing a handoff."""
        handoff = WorkHandoff(
            handoff_id="handoff-005",
            from_agent_id="agent-13",
            to_agent_id="agent-14",
            task_id="task-005",
            initiated_at=datetime.now(timezone.utc),
            status=HandoffStatus.IN_PROGRESS
        )
        
        assert handoff.completed_at is None
        
        handoff.complete()
        
        assert handoff.status == HandoffStatus.COMPLETED
        assert handoff.completed_at is not None
    
    def test_complete_handoff_invalid_status(self):
        """Test completing handoff with invalid status."""
        handoff = WorkHandoff(
            handoff_id="handoff-006",
            from_agent_id="agent-15",
            to_agent_id="agent-16",
            task_id="task-006",
            initiated_at=datetime.now(timezone.utc),
            status=HandoffStatus.PENDING
        )
        
        with pytest.raises(ValueError) as exc_info:
            handoff.complete()
        
        assert "Cannot complete handoff in status" in str(exc_info.value)
    
    def test_to_handoff_package(self):
        """Test creating handoff package."""
        initiated_at = datetime.now(timezone.utc)
        accepted_at = initiated_at + timedelta(minutes=15)
        completed_at = accepted_at + timedelta(hours=2)
        
        handoff = WorkHandoff(
            handoff_id="handoff-007",
            from_agent_id="agent-17",
            to_agent_id="agent-18",
            task_id="task-007",
            initiated_at=initiated_at,
            status=HandoffStatus.COMPLETED,
            work_summary="Frontend implementation complete",
            completed_items=["React components", "Styling"],
            remaining_items=["Integration tests"],
            known_issues=["Performance optimization needed"],
            handoff_notes="Review component architecture",
            artifacts={"components": "/src/components"},
            documentation_links=["http://example.com/frontend-guide"],
            accepted_at=accepted_at,
            completed_at=completed_at
        )
        
        package = handoff.to_handoff_package()
        
        assert package["handoff_id"] == "handoff-007"
        assert package["from_agent"] == "agent-17"
        assert package["to_agent"] == "agent-18"
        assert package["task_id"] == "task-007"
        assert package["status"] == "completed"
        assert package["summary"] == "Frontend implementation complete"
        assert package["completed"] == ["React components", "Styling"]
        assert package["remaining"] == ["Integration tests"]
        assert package["issues"] == ["Performance optimization needed"]
        assert package["notes"] == "Review component architecture"
        assert package["artifacts"] == {"components": "/src/components"}
        assert package["documentation"] == ["http://example.com/frontend-guide"]
        assert package["timeline"]["initiated"] == initiated_at.isoformat()
        assert package["timeline"]["accepted"] == accepted_at.isoformat()
        assert package["timeline"]["completed"] == completed_at.isoformat()


class TestConflictResolution:
    """Test cases for ConflictResolution entity."""
    
    def test_create_conflict_resolution_minimal(self):
        """Test creating conflict resolution with minimal data."""
        now = datetime.now(timezone.utc)
        resolution = ConflictResolution(
            conflict_id="conflict-123",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            involved_agents=["agent-1", "agent-2"],
            task_id="task-123",
            detected_at=now,
            description="Both agents edited the same file"
        )
        
        assert resolution.conflict_id == "conflict-123"
        assert resolution.conflict_type == ConflictType.CONCURRENT_EDIT
        assert resolution.involved_agents == ["agent-1", "agent-2"]
        assert resolution.task_id == "task-123"
        assert resolution.detected_at == now
        assert resolution.description == "Both agents edited the same file"
        assert resolution.conflicting_elements == {}
        assert resolution.impact_assessment == "low"
        assert resolution.resolution_strategy is None
        assert resolution.resolved_by is None
        assert resolution.resolution_details is None
        assert resolution.resolved_at is None
        assert resolution.votes == {}
    
    def test_create_conflict_resolution_full(self):
        """Test creating conflict resolution with all fields."""
        now = datetime.now(timezone.utc)
        
        resolution = ConflictResolution(
            conflict_id="conflict-456",
            conflict_type=ConflictType.PRIORITY_DISAGREEMENT,
            involved_agents=["agent-3", "agent-4", "agent-5"],
            task_id="task-456",
            detected_at=now,
            description="Disagreement on task priority",
            conflicting_elements={"agent-3": "high", "agent-4": "low", "agent-5": "medium"},
            impact_assessment="medium",
            resolution_strategy=ResolutionStrategy.VOTE,
            resolved_by="agent-6",
            resolution_details="Voted for medium priority",
            resolved_at=now + timedelta(hours=1),
            votes={"agent-3": "high", "agent-4": "medium", "agent-5": "medium"}
        )
        
        assert resolution.conflicting_elements == {"agent-3": "high", "agent-4": "low", "agent-5": "medium"}
        assert resolution.impact_assessment == "medium"
        assert resolution.resolution_strategy == ResolutionStrategy.VOTE
        assert resolution.resolved_by == "agent-6"
        assert resolution.resolution_details == "Voted for medium priority"
        assert resolution.resolved_at == now + timedelta(hours=1)
        assert resolution.votes == {"agent-3": "high", "agent-4": "medium", "agent-5": "medium"}
    
    def test_is_resolved(self):
        """Test checking if conflict is resolved."""
        resolution = ConflictResolution(
            conflict_id="conflict-001",
            conflict_type=ConflictType.RESOURCE_CONTENTION,
            involved_agents=["agent-7", "agent-8"],
            task_id="task-001",
            detected_at=datetime.now(timezone.utc),
            description="Both need same resource"
        )
        
        assert not resolution.is_resolved()
        
        resolution.resolved_at = datetime.now(timezone.utc)
        assert resolution.is_resolved()
    
    def test_resolve_conflict(self):
        """Test resolving a conflict."""
        resolution = ConflictResolution(
            conflict_id="conflict-002",
            conflict_type=ConflictType.APPROACH_DIFFERENCE,
            involved_agents=["agent-9", "agent-10"],
            task_id="task-002",
            detected_at=datetime.now(timezone.utc),
            description="Different implementation approaches"
        )
        
        assert not resolution.is_resolved()
        assert resolution.resolution_strategy is None
        assert resolution.resolved_by is None
        assert resolution.resolution_details is None
        assert resolution.resolved_at is None
        
        resolution.resolve(
            strategy=ResolutionStrategy.COLLABORATE,
            resolved_by="agent-11",
            details="Combined best aspects of both approaches"
        )
        
        assert resolution.is_resolved()
        assert resolution.resolution_strategy == ResolutionStrategy.COLLABORATE
        assert resolution.resolved_by == "agent-11"
        assert resolution.resolution_details == "Combined best aspects of both approaches"
        assert resolution.resolved_at is not None
    
    def test_resolve_conflict_already_resolved(self):
        """Test resolving an already resolved conflict."""
        resolution = ConflictResolution(
            conflict_id="conflict-003",
            conflict_type=ConflictType.DEPENDENCY_CONFLICT,
            involved_agents=["agent-12", "agent-13"],
            task_id="task-003",
            detected_at=datetime.now(timezone.utc),
            description="Circular dependency",
            resolved_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError) as exc_info:
            resolution.resolve(
                strategy=ResolutionStrategy.OVERRIDE,
                resolved_by="agent-14",
                details="Override attempt"
            )
        
        assert "Conflict already resolved" in str(exc_info.value)
    
    def test_add_vote(self):
        """Test adding votes to conflict resolution."""
        resolution = ConflictResolution(
            conflict_id="conflict-004",
            conflict_type=ConflictType.SCHEDULE_CONFLICT,
            involved_agents=["agent-15", "agent-16", "agent-17"],
            task_id="task-004",
            detected_at=datetime.now(timezone.utc),
            description="Schedule overlap"
        )
        
        assert resolution.votes == {}
        
        resolution.add_vote("agent-15", "option_a")
        resolution.add_vote("agent-16", "option_b")
        resolution.add_vote("agent-17", "option_a")
        
        assert resolution.votes == {
            "agent-15": "option_a",
            "agent-16": "option_b",
            "agent-17": "option_a"
        }
    
    def test_get_vote_summary(self):
        """Test getting vote summary."""
        resolution = ConflictResolution(
            conflict_id="conflict-005",
            conflict_type=ConflictType.PRIORITY_DISAGREEMENT,
            involved_agents=["agent-18", "agent-19", "agent-20", "agent-21"],
            task_id="task-005",
            detected_at=datetime.now(timezone.utc),
            description="Priority voting"
        )
        
        resolution.add_vote("agent-18", "high")
        resolution.add_vote("agent-19", "medium")
        resolution.add_vote("agent-20", "high")
        resolution.add_vote("agent-21", "high")
        
        summary = resolution.get_vote_summary()
        
        assert summary == {"high": 3, "medium": 1}


class TestAgentCommunication:
    """Test cases for AgentCommunication value object."""
    
    def test_create_agent_communication_minimal(self):
        """Test creating agent communication with minimal data."""
        now = datetime.now(timezone.utc)
        communication = AgentCommunication(
            message_id="msg-123",
            from_agent_id="agent-1",
            to_agent_ids=["agent-2"],
            task_id="task-123",
            sent_at=now,
            message_type="status_update",
            subject="Progress update",
            content="Completed initial implementation"
        )
        
        assert communication.message_id == "msg-123"
        assert communication.from_agent_id == "agent-1"
        assert communication.to_agent_ids == ["agent-2"]
        assert communication.task_id == "task-123"
        assert communication.sent_at == now
        assert communication.message_type == "status_update"
        assert communication.subject == "Progress update"
        assert communication.content == "Completed initial implementation"
        assert communication.priority == "normal"
        assert communication.in_reply_to is None
        assert communication.thread_id is None
        assert communication.requires_response is False
        assert communication.response_deadline is None
        assert communication.attachments == []
    
    def test_create_agent_communication_full(self):
        """Test creating agent communication with all fields."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=2)
        
        communication = AgentCommunication(
            message_id="msg-456",
            from_agent_id="agent-3",
            to_agent_ids=["agent-4", "agent-5", "agent-6"],
            task_id=None,  # Can be None
            sent_at=now,
            message_type="question",
            subject="Architecture question",
            content="Should we use microservices?",
            priority="high",
            in_reply_to="msg-123",
            thread_id="thread-001",
            requires_response=True,
            response_deadline=deadline,
            attachments=["diagram.png", "proposal.pdf"]
        )
        
        assert communication.task_id is None
        assert communication.priority == "high"
        assert communication.in_reply_to == "msg-123"
        assert communication.thread_id == "thread-001"
        assert communication.requires_response is True
        assert communication.response_deadline == deadline
        assert communication.attachments == ["diagram.png", "proposal.pdf"]
    
    def test_agent_communication_immutable(self):
        """Test that agent communication is immutable."""
        communication = AgentCommunication(
            message_id="msg-789",
            from_agent_id="agent-7",
            to_agent_ids=["agent-8"],
            task_id="task-789",
            sent_at=datetime.now(timezone.utc),
            message_type="notification",
            subject="Alert",
            content="System issue detected"
        )
        
        with pytest.raises(AttributeError):
            communication.priority = "urgent"
    
    def test_is_broadcast_single_recipient(self):
        """Test is_broadcast with single recipient."""
        communication = AgentCommunication(
            message_id="msg-001",
            from_agent_id="agent-9",
            to_agent_ids=["agent-10"],
            task_id="task-001",
            sent_at=datetime.now(timezone.utc),
            message_type="response",
            subject="Re: Question",
            content="Here's the answer"
        )
        
        assert not communication.is_broadcast()
    
    def test_is_broadcast_multiple_recipients(self):
        """Test is_broadcast with multiple recipients."""
        communication = AgentCommunication(
            message_id="msg-002",
            from_agent_id="agent-11",
            to_agent_ids=["agent-12", "agent-13", "agent-14"],
            task_id="task-002",
            sent_at=datetime.now(timezone.utc),
            message_type="notification",
            subject="Team update",
            content="New requirements"
        )
        
        assert communication.is_broadcast()
    
    def test_needs_urgent_response_not_required(self):
        """Test needs_urgent_response when response not required."""
        communication = AgentCommunication(
            message_id="msg-003",
            from_agent_id="agent-15",
            to_agent_ids=["agent-16"],
            task_id="task-003",
            sent_at=datetime.now(timezone.utc),
            message_type="status_update",
            subject="FYI",
            content="Just an update",
            requires_response=False
        )
        
        assert not communication.needs_urgent_response()
    
    def test_needs_urgent_response_high_priority(self):
        """Test needs_urgent_response with high priority."""
        communication = AgentCommunication(
            message_id="msg-004",
            from_agent_id="agent-17",
            to_agent_ids=["agent-18"],
            task_id="task-004",
            sent_at=datetime.now(timezone.utc),
            message_type="question",
            subject="Urgent question",
            content="Need immediate answer",
            priority="high",
            requires_response=True
        )
        
        assert communication.needs_urgent_response()
    
    def test_needs_urgent_response_urgent_priority(self):
        """Test needs_urgent_response with urgent priority."""
        communication = AgentCommunication(
            message_id="msg-005",
            from_agent_id="agent-19",
            to_agent_ids=["agent-20"],
            task_id="task-005",
            sent_at=datetime.now(timezone.utc),
            message_type="question",
            subject="Critical issue",
            content="System down",
            priority="urgent",
            requires_response=True
        )
        
        assert communication.needs_urgent_response()
    
    def test_needs_urgent_response_approaching_deadline(self):
        """Test needs_urgent_response with approaching deadline."""
        communication = AgentCommunication(
            message_id="msg-006",
            from_agent_id="agent-21",
            to_agent_ids=["agent-22"],
            task_id="task-006",
            sent_at=datetime.now(timezone.utc),
            message_type="question",
            subject="Question",
            content="Please respond",
            priority="normal",
            requires_response=True,
            response_deadline=datetime.now() + timedelta(hours=1.5)  # Less than 2 hours
        )
        
        assert communication.needs_urgent_response()
    
    def test_needs_urgent_response_distant_deadline(self):
        """Test needs_urgent_response with distant deadline."""
        communication = AgentCommunication(
            message_id="msg-007",
            from_agent_id="agent-23",
            to_agent_ids=["agent-24"],
            task_id="task-007",
            sent_at=datetime.now(timezone.utc),
            message_type="question",
            subject="Question",
            content="When you have time",
            priority="low",
            requires_response=True,
            response_deadline=datetime.now() + timedelta(days=1)  # More than 2 hours
        )
        
        assert not communication.needs_urgent_response()