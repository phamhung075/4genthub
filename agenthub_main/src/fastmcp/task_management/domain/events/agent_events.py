"""Domain Events for Multi-Agent Coordination"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


class DomainEvent:
    """Base class for domain events"""
    pass

@dataclass(frozen=True)
class AgentAssigned:
    """Event raised when an agent is assigned to a task"""
    agent_id: str
    task_id: str
    role: str
    assigned_by: str
    assignment_id: str = field(default_factory=lambda: str(uuid4()))
    responsibilities: List[str] = field(default_factory=list)
    estimated_hours: Optional[float] = None
    occurred_at: datetime = field(default_factory=datetime.now)
    event_type: str = field(default="agent_assigned")
    due_date: Optional[datetime] = None
    

@dataclass(frozen=True)
class AgentUnassigned:
    """Event raised when an agent is unassigned from a task"""
    agent_id: str
    task_id: str
    unassigned_by: str
    reason: str
    
    # Handoff details if applicable
    handoff_to_agent: Optional[str] = None
    handoff_notes: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_unassigned')

@dataclass(frozen=True)
class WorkHandoffRequested:
    """Event raised when work handoff is requested"""
    handoff_id: str
    from_agent_id: str
    to_agent_id: str
    task_id: str
    
    # Handoff content
    work_summary: str = ""
    completed_items: List[str] = field(default_factory=list)
    remaining_items: List[str] = field(default_factory=list)
    handoff_notes: str = ""
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'work_handoff_requested')

@dataclass(frozen=True)
class WorkHandoffAccepted:
    """Event raised when work handoff is accepted"""
    handoff_id: str
    accepted_by: str
    task_id: str
    acceptance_notes: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'work_handoff_accepted')

@dataclass(frozen=True)
class WorkHandoffRejected:
    """Event raised when work handoff is rejected"""
    handoff_id: str
    rejected_by: str
    task_id: str
    rejection_reason: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'work_handoff_rejected')

@dataclass(frozen=True)
class WorkHandoffCompleted:
    """Event raised when work handoff is completed"""
    handoff_id: str
    from_agent_id: str
    to_agent_id: str
    task_id: str
    
    # Completion metrics
    handoff_duration_hours: float = 0.0
    knowledge_transfer_complete: bool = True
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'work_handoff_completed')

@dataclass(frozen=True)
class ConflictDetected:
    """Event raised when a conflict is detected"""
    conflict_id: str
    conflict_type: str  # concurrent_edit, resource_contention, etc.
    involved_agents: List[str]
    task_id: str
    
    # Conflict details
    description: str = ""
    conflicting_elements: Dict[str, Any] = field(default_factory=dict)
    impact_assessment: str = "low"  # low, medium, high, critical
    suggested_resolution: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'conflict_detected')

@dataclass(frozen=True)
class ConflictResolved:
    """Event raised when a conflict is resolved"""
    conflict_id: str
    resolution_strategy: str  # merge, override, vote, escalate, etc.
    resolved_by: str
    task_id: str
    
    # Resolution details
    resolution_details: str = ""
    winning_agent: Optional[str] = None
    compromise_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'conflict_resolved')

@dataclass(frozen=True)
class AgentCollaborationStarted:
    """Event raised when agents start collaborating"""
    collaboration_id: str
    initiating_agent: str
    collaborating_agents: List[str]
    task_id: str
    
    # Collaboration details
    collaboration_type: str = "general"  # general, pair_programming, review, brainstorming
    objectives: List[str] = field(default_factory=list)
    expected_duration_hours: Optional[float] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_collaboration_started')

@dataclass(frozen=True)
class AgentCollaborationEnded:
    """Event raised when collaboration ends"""
    collaboration_id: str
    task_id: str
    
    # Results
    outcomes: List[str] = field(default_factory=list)
    decisions_made: Dict[str, str] = field(default_factory=dict)
    follow_up_actions: List[Dict[str, Any]] = field(default_factory=list)
    duration_hours: float = 0.0
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_collaboration_ended')

@dataclass(frozen=True)
class AgentStatusBroadcast:
    """Event raised when agent broadcasts status"""
    agent_id: str
    status: str  # available, busy, blocked, offline
    
    # Status details
    current_task_id: Optional[str] = None
    current_activity: Optional[str] = None
    blocker_description: Optional[str] = None
    estimated_availability: Optional[datetime] = None
    workload_percentage: float = 0.0
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_status_broadcast')

@dataclass(frozen=True)
class AgentWorkloadRebalanced:
    """Event raised when workload is rebalanced"""
    rebalance_id: str
    initiated_by: str
    
    # Rebalancing details
    agents_affected: List[str] = field(default_factory=list)
    tasks_reassigned: Dict[str, str] = field(default_factory=dict)  # task_id -> new_agent_id
    reason: str = ""
    
    # Metrics
    workload_before: Dict[str, int] = field(default_factory=dict)  # agent_id -> task_count
    workload_after: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_workload_rebalanced')

@dataclass(frozen=True)
class AgentEscalationRaised:
    """Event raised when escalation is needed"""
    escalation_id: str
    escalating_agent: str
    escalated_to: str  # manager or senior agent
    task_id: str
    
    # Escalation details
    reason: str = ""
    severity: str = "medium"  # low, medium, high, critical
    context: Dict[str, Any] = field(default_factory=dict)
    requested_action: str = ""
    deadline: Optional[datetime] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_escalation_raised')

@dataclass(frozen=True)
class AgentEscalationResolved:
    """Event raised when escalation is resolved"""
    escalation_id: str
    resolved_by: str
    task_id: str
    
    # Resolution
    resolution: str = ""
    actions_taken: List[str] = field(default_factory=list)
    guidance_provided: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_escalation_resolved')

@dataclass(frozen=True)
class AgentCommunicationSent:
    """Event raised when agent sends communication"""
    message_id: str
    from_agent_id: str
    to_agent_ids: List[str]
    
    # Message details
    message_type: str = "status_update"  # status_update, question, response, notification
    subject: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    task_id: Optional[str] = None
    requires_response: bool = False
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_communication_sent')

@dataclass(frozen=True)
class AgentPerformanceEvaluated:
    """Event raised when agent performance is evaluated"""
    agent_id: str
    evaluation_id: str
    evaluated_by: Optional[str] = None  # None if system-generated
    
    # Performance metrics
    task_id: Optional[str] = None
    quality_score: float = 0.0  # 0-1
    timeliness_score: float = 0.0  # 0-1
    collaboration_score: float = 0.0  # 0-1
    overall_score: float = 0.0  # 0-1
    
    # Feedback
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'agent_performance_evaluated')