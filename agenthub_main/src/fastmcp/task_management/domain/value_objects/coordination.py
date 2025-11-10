"""Coordination Value Objects for Multi-Agent Workflows"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CoordinationType(Enum):
    """Types of agent coordination patterns"""
    HANDOFF = "handoff"  # Sequential task transfer
    PARALLEL = "parallel"  # Concurrent work on related tasks
    REVIEW = "review"  # Review and feedback cycle
    ESCALATION = "escalation"  # Escalate to higher authority
    COLLABORATION = "collaboration"  # Joint work on same task
    DELEGATION = "delegation"  # Assign subtasks to other agents
    CONSULTATION = "consultation"  # Request expertise/advice

class HandoffStatus(Enum):
    """Status of work handoff between agents"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ConflictType(Enum):
    """Types of conflicts that can occur"""
    CONCURRENT_EDIT = "concurrent_edit"
    RESOURCE_CONTENTION = "resource_contention"
    PRIORITY_DISAGREEMENT = "priority_disagreement"
    APPROACH_DIFFERENCE = "approach_difference"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    SCHEDULE_CONFLICT = "schedule_conflict"

class ResolutionStrategy(Enum):
    """Strategies for conflict resolution"""
    MERGE = "merge"  # Merge changes
    OVERRIDE = "override"  # One takes precedence
    VOTE = "vote"  # Team voting
    ESCALATE = "escalate"  # Escalate to manager
    COLLABORATE = "collaborate"  # Work together to resolve
    DEFER = "defer"  # Postpone resolution

class CoordinationStrategy(Enum):
    """Strategies for coordinating work between agents"""
    ROUND_ROBIN = "round_robin"  # Distribute tasks evenly
    EXPERTISE_BASED = "expertise_based"  # Assign based on skills
    LOAD_BALANCING = "load_balancing"  # Balance workload
    PRIORITY_FIRST = "priority_first"  # High priority tasks first
    COLLABORATIVE = "collaborative"  # Multiple agents on same task
    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"  # Multiple agents simultaneously

@dataclass(frozen=True)
class CoordinationRequest:
    """Request for coordination between agents"""
    request_id: str
    coordination_type: CoordinationType
    requesting_agent_id: str
    target_agent_id: str
    task_id: str
    created_at: datetime
    
    # Request details
    reason: str
    context: dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"  # low, medium, high, critical
    deadline: datetime | None = None
    
    # Handoff-specific fields
    handoff_notes: str | None = None
    completion_criteria: list[str] = field(default_factory=list)
    
    # Review-specific fields
    review_items: list[str] = field(default_factory=list)
    review_checklist: dict[str, bool] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if request has expired"""
        if not self.deadline:
            return False
        return datetime.now(UTC) > self.deadline
    
    def to_notification(self) -> dict[str, Any]:
        """Convert to notification format for target agent"""
        return {
            "type": f"coordination_{self.coordination_type.value}",
            "from_agent": self.requesting_agent_id,
            "task_id": self.task_id,
            "priority": self.priority,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "context": self.context
        }

@dataclass(frozen=True)
class WorkAssignment:
    """Assignment of work to an agent"""
    assignment_id: str
    task_id: str
    assigned_agent_id: str
    assigned_by_agent_id: str
    assigned_at: datetime
    
    # Assignment details
    role: str | None = None
    responsibilities: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    
    # Timeline
    estimated_hours: float | None = None
    due_date: datetime | None = None
    
    # Collaboration
    collaborating_agents: list[str] = field(default_factory=list)
    reporting_to: str | None = None
    
    def is_overdue(self) -> bool:
        """Check if assignment is overdue"""
        if not self.due_date:
            return False
        return datetime.now(UTC) > self.due_date
    
    def to_task_context(self) -> dict[str, Any]:
        """Convert to task context format"""
        return {
            "assignment": {
                "agent_id": self.assigned_agent_id,
                "role": self.role,
                "assigned_by": self.assigned_by_agent_id,
                "assigned_at": self.assigned_at.isoformat(),
                "responsibilities": self.responsibilities,
                "deliverables": self.deliverables,
                "collaborators": self.collaborating_agents,
                "due_date": self.due_date if self.due_date else None
            }
        }

@dataclass
class WorkHandoff:
    """Handoff of work between agents"""
    handoff_id: str
    from_agent_id: str
    to_agent_id: str
    task_id: str
    initiated_at: datetime
    status: HandoffStatus = HandoffStatus.PENDING
    
    # Handoff content
    work_summary: str = ""
    completed_items: list[str] = field(default_factory=list)
    remaining_items: list[str] = field(default_factory=list)
    known_issues: list[str] = field(default_factory=list)
    handoff_notes: str = ""
    
    # Supporting materials
    artifacts: dict[str, str] = field(default_factory=dict)  # name -> location
    documentation_links: list[str] = field(default_factory=list)
    
    # Status tracking
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    rejection_reason: str | None = None
    
    def accept(self) -> None:
        """Accept the handoff"""
        if self.status != HandoffStatus.PENDING:
            raise ValueError(f"Cannot accept handoff in status {self.status}")
        
        self.status = HandoffStatus.ACCEPTED
        self.accepted_at = datetime.now(UTC)
    
    def reject(self, reason: str) -> None:
        """Reject the handoff"""
        if self.status != HandoffStatus.PENDING:
            raise ValueError(f"Cannot reject handoff in status {self.status}")
        
        self.status = HandoffStatus.REJECTED
        self.rejection_reason = reason
    
    def complete(self) -> None:
        """Mark handoff as completed"""
        if self.status != HandoffStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete handoff in status {self.status}")
        
        self.status = HandoffStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
    
    def to_handoff_package(self) -> dict[str, Any]:
        """Create complete handoff package"""
        return {
            "handoff_id": self.handoff_id,
            "from_agent": self.from_agent_id,
            "to_agent": self.to_agent_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "summary": self.work_summary,
            "completed": self.completed_items,
            "remaining": self.remaining_items,
            "issues": self.known_issues,
            "notes": self.handoff_notes,
            "artifacts": self.artifacts,
            "documentation": self.documentation_links,
            "timeline": {
                "initiated": self.initiated_at.isoformat(),
                "accepted": self.accepted_at.isoformat() if self.accepted_at else None,
                "completed": self.completed_at.isoformat() if self.completed_at else None
            }
        }

@dataclass
class ConflictResolution:
    """Resolution of conflicts between agents"""
    conflict_id: str
    conflict_type: ConflictType
    involved_agents: list[str]
    task_id: str
    detected_at: datetime
    
    # Conflict details
    description: str
    conflicting_elements: dict[str, Any] = field(default_factory=dict)
    impact_assessment: str = "low"  # low, medium, high, critical
    
    # Resolution
    resolution_strategy: ResolutionStrategy | None = None
    resolved_by: str | None = None
    resolution_details: str | None = None
    resolved_at: datetime | None = None
    
    # Voting (if applicable)
    votes: dict[str, str] = field(default_factory=dict)  # agent_id -> choice
    
    def is_resolved(self) -> bool:
        """Check if conflict is resolved"""
        return self.resolved_at is not None
    
    def resolve(self, strategy: ResolutionStrategy, resolved_by: str, details: str) -> None:
        """Resolve the conflict"""
        if self.is_resolved():
            raise ValueError("Conflict already resolved")
        
        self.resolution_strategy = strategy
        self.resolved_by = resolved_by
        self.resolution_details = details
        self.resolved_at = datetime.now(UTC)
    
    def add_vote(self, agent_id: str, choice: str) -> None:
        """Add agent vote for resolution"""
        self.votes[agent_id] = choice
    
    def get_vote_summary(self) -> dict[str, int]:
        """Get summary of votes"""
        summary = {}
        for choice in self.votes.values():
            summary[choice] = summary.get(choice, 0) + 1
        return summary

@dataclass(frozen=True)
class AgentCommunication:
    """Communication between agents"""
    message_id: str
    from_agent_id: str
    to_agent_ids: list[str]  # Can be broadcast
    task_id: str | None
    sent_at: datetime
    
    # Message content
    message_type: str  # status_update, question, response, notification
    subject: str
    content: str
    priority: str = "normal"  # low, normal, high, urgent
    
    # Threading
    in_reply_to: str | None = None
    thread_id: str | None = None
    
    # Metadata
    requires_response: bool = False
    response_deadline: datetime | None = None
    attachments: list[str] = field(default_factory=list)
    
    def is_broadcast(self) -> bool:
        """Check if message is broadcast"""
        return len(self.to_agent_ids) > 1
    
    def needs_urgent_response(self) -> bool:
        """Check if urgent response needed"""
        if not self.requires_response:
            return False
        
        if self.priority in ["high", "urgent"]:
            return True
        
        if self.response_deadline:
            hours_until_deadline = (self.response_deadline - datetime.now(UTC)).total_seconds() / 3600
            return hours_until_deadline <= 2
        
        return False


@dataclass(frozen=True)
class CoordinationMessage:
    """Message for agent coordination and communication"""
    message_id: str
    message_type: str  # handoff_request, status_update, resource_request, etc.
    from_agent_id: str
    to_agent_id: str | None  # None for broadcast
    timestamp: datetime
    payload: dict[str, Any]
    priority: str = "normal"  # low, normal, high, urgent
    requires_response: bool = False
    correlation_id: str | None = None
    
    def is_broadcast(self) -> bool:
        """Check if message is a broadcast"""
        return self.to_agent_id is None
    
    def to_json(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "priority": self.priority,
            "requires_response": self.requires_response,
            "correlation_id": self.correlation_id
        }