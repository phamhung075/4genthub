"""
Domain Events for Multi-Agent Coordination.

These events track agent assignments, workload, collaboration, and coordination.
All events follow the standardized BaseDomainEvent pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import BaseDomainEvent


@dataclass(frozen=True)
class AgentAssigned(BaseDomainEvent):
    """Event raised when an agent is assigned to a task"""

    agent_id: str = ""
    task_id: str = ""
    role: str = ""
    assigned_by: str = ""
    responsibilities: list[str] = field(default_factory=list)
    estimated_hours: float | None = None
    due_date: datetime | None = None


@dataclass(frozen=True)
class AgentUnassigned(BaseDomainEvent):
    """Event raised when an agent is unassigned from a task"""

    agent_id: str = ""
    task_id: str = ""
    unassigned_by: str = ""
    reason: str = ""
    handoff_to_agent: str | None = None
    handoff_notes: str | None = None


@dataclass(frozen=True)
class WorkHandoffRequested(BaseDomainEvent):
    """Event raised when work handoff is requested"""

    handoff_id: str = ""
    from_agent_id: str = ""
    to_agent_id: str = ""
    task_id: str = ""
    work_summary: str = ""
    completed_items: list[str] = field(default_factory=list)
    remaining_items: list[str] = field(default_factory=list)
    handoff_notes: str = ""


@dataclass(frozen=True)
class WorkHandoffAccepted(BaseDomainEvent):
    """Event raised when work handoff is accepted"""

    handoff_id: str = ""
    accepted_by: str = ""
    task_id: str = ""
    acceptance_notes: str | None = None


@dataclass(frozen=True)
class WorkHandoffRejected(BaseDomainEvent):
    """Event raised when work handoff is rejected"""

    handoff_id: str = ""
    rejected_by: str = ""
    task_id: str = ""
    rejection_reason: str = ""


@dataclass(frozen=True)
class WorkHandoffCompleted(BaseDomainEvent):
    """Event raised when work handoff is completed"""

    handoff_id: str = ""
    from_agent_id: str = ""
    to_agent_id: str = ""
    task_id: str = ""
    handoff_duration_hours: float = 0.0
    knowledge_transfer_complete: bool = True


@dataclass(frozen=True)
class ConflictDetected(BaseDomainEvent):
    """Event raised when a conflict is detected"""

    conflict_id: str = ""
    conflict_type: str = ""  # concurrent_edit, resource_contention, etc.
    involved_agents: list[str] = field(default_factory=list)
    task_id: str = ""
    description: str = ""
    conflicting_elements: dict[str, Any] = field(default_factory=dict)
    impact_assessment: str = "low"  # low, medium, high, critical
    suggested_resolution: str | None = None


@dataclass(frozen=True)
class ConflictResolved(BaseDomainEvent):
    """Event raised when a conflict is resolved"""

    conflict_id: str = ""
    resolution_strategy: str = ""  # merge, override, vote, escalate, etc.
    resolved_by: str = ""
    task_id: str = ""
    resolution_details: str = ""
    winning_agent: str | None = None
    compromise_details: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentCollaborationStarted(BaseDomainEvent):
    """Event raised when agents start collaborating"""

    collaboration_id: str = ""
    initiating_agent: str = ""
    collaborating_agents: list[str] = field(default_factory=list)
    task_id: str = ""
    collaboration_type: str = (
        "general"  # general, pair_programming, review, brainstorming
    )
    objectives: list[str] = field(default_factory=list)
    expected_duration_hours: float | None = None


@dataclass(frozen=True)
class AgentCollaborationEnded(BaseDomainEvent):
    """Event raised when collaboration ends"""

    collaboration_id: str = ""
    task_id: str = ""
    outcomes: list[str] = field(default_factory=list)
    decisions_made: dict[str, str] = field(default_factory=dict)
    follow_up_actions: list[dict[str, Any]] = field(default_factory=list)
    duration_hours: float = 0.0


@dataclass(frozen=True)
class AgentStatusBroadcast(BaseDomainEvent):
    """Event raised when agent broadcasts status"""

    agent_id: str = ""
    status: str = ""  # available, busy, blocked, offline
    current_task_id: str | None = None
    current_activity: str | None = None
    blocker_description: str | None = None
    estimated_availability: datetime | None = None
    workload_percentage: float = 0.0


@dataclass(frozen=True)
class AgentWorkloadRebalanced(BaseDomainEvent):
    """Event raised when workload is rebalanced"""

    rebalance_id: str = ""
    initiated_by: str = ""
    agents_affected: list[str] = field(default_factory=list)
    tasks_reassigned: dict[str, str] = field(
        default_factory=dict
    )  # task_id -> new_agent_id
    reason: str = ""
    workload_before: dict[str, int] = field(
        default_factory=dict
    )  # agent_id -> task_count
    workload_after: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentWorkloadChanged(BaseDomainEvent):
    """
    Event raised when an agent's workload changes.

    This is a new event added in Phase 5 to track workload metrics changes.
    """

    agent_id: str = ""
    old_task_count: int = 0
    new_task_count: int = 0
    old_workload_percentage: float = 0.0
    new_workload_percentage: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class AgentEscalationRaised(BaseDomainEvent):
    """Event raised when escalation is needed"""

    escalation_id: str = ""
    escalating_agent: str = ""
    escalated_to: str = ""  # manager or senior agent
    task_id: str = ""
    reason: str = ""
    severity: str = "medium"  # low, medium, high, critical
    context: dict[str, Any] = field(default_factory=dict)
    requested_action: str = ""
    deadline: datetime | None = None


@dataclass(frozen=True)
class AgentEscalationResolved(BaseDomainEvent):
    """Event raised when escalation is resolved"""

    escalation_id: str = ""
    resolved_by: str = ""
    task_id: str = ""
    resolution: str = ""
    actions_taken: list[str] = field(default_factory=list)
    guidance_provided: str | None = None


@dataclass(frozen=True)
class AgentCommunicationSent(BaseDomainEvent):
    """Event raised when agent sends communication"""

    message_id: str = ""
    from_agent_id: str = ""
    to_agent_ids: list[str] = field(default_factory=list)
    message_type: str = (
        "status_update"  # status_update, question, response, notification
    )
    subject: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    task_id: str | None = None
    requires_response: bool = False


@dataclass(frozen=True)
class AgentPerformanceEvaluated(BaseDomainEvent):
    """Event raised when agent performance is evaluated"""

    agent_id: str = ""
    evaluation_id: str = ""
    evaluated_by: str | None = None  # None if system-generated
    task_id: str | None = None
    quality_score: float = 0.0  # 0-1
    timeliness_score: float = 0.0  # 0-1
    collaboration_score: float = 0.0  # 0-1
    overall_score: float = 0.0  # 0-1
    strengths: list[str] = field(default_factory=list)
    areas_for_improvement: list[str] = field(default_factory=list)


__all__ = [
    "AgentAssigned",
    "AgentUnassigned",
    "WorkHandoffRequested",
    "WorkHandoffAccepted",
    "WorkHandoffRejected",
    "WorkHandoffCompleted",
    "ConflictDetected",
    "ConflictResolved",
    "AgentCollaborationStarted",
    "AgentCollaborationEnded",
    "AgentStatusBroadcast",
    "AgentWorkloadRebalanced",
    "AgentWorkloadChanged",
    "AgentEscalationRaised",
    "AgentEscalationResolved",
    "AgentCommunicationSent",
    "AgentPerformanceEvaluated",
]
