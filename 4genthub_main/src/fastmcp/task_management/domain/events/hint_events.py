"""
Domain events for workflow hints in the Vision System.

This module defines events related to hint generation, acceptance,
dismissal, and feedback collection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from .base import DomainEvent, create_event_metadata
from ..value_objects.hints import HintType, HintPriority


@dataclass(frozen=True)
class HintGenerated(DomainEvent):
    """
    Event raised when a workflow hint is generated.
    
    Attributes:
        hint_id: Unique identifier for the hint
        task_id: Task the hint was generated for
        hint_type: Type of hint generated
        priority: Priority level of the hint
        message: The hint message
        suggested_action: The suggested action
        source_rule: Name of the rule that generated the hint
        confidence: Confidence score of the hint
        metadata: Additional hint metadata
        event_id: Event identifier
        occurred_at: When the event occurred
        aggregate_id: Aggregate identifier
        aggregate_type: Type of aggregate
    """
    
    hint_id: UUID
    task_id: UUID
    hint_type: HintType
    priority: HintPriority
    message: str
    suggested_action: str
    source_rule: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "hint_id": str(self.hint_id),
            "task_id": str(self.task_id),
            "hint_type": self.hint_type.value,
            "priority": self.priority.value,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "source_rule": self.source_rule,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class HintAccepted(DomainEvent):
    """
    Event raised when a user accepts/follows a hint.
    
    Attributes:
        hint_id: The hint that was accepted
        task_id: The task the hint was for
        user_id: User who accepted the hint
        action_taken: Description of action taken based on hint
        acceptance_context: Context around why hint was accepted
    """
    
    hint_id: UUID
    task_id: UUID
    user_id: str
    action_taken: Optional[str] = None
    acceptance_context: Dict[str, Any] = field(default_factory=dict)
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_accepted"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "hint_id": str(self.hint_id),
            "task_id": str(self.task_id),
            "user_id": self.user_id,
            "action_taken": self.action_taken,
            "acceptance_context": self.acceptance_context
        }


@dataclass(frozen=True)
class HintDismissed(DomainEvent):
    """
    Event raised when a user dismisses a hint.
    
    Attributes:
        hint_id: The hint that was dismissed
        task_id: The task the hint was for
        user_id: User who dismissed the hint
        reason: Reason for dismissal
        dismissal_context: Additional context about dismissal
    """
    
    hint_id: UUID
    task_id: UUID
    user_id: str
    reason: Optional[str] = None
    dismissal_context: Dict[str, Any] = field(default_factory=dict)
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_dismissed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "hint_id": str(self.hint_id),
            "task_id": str(self.task_id),
            "user_id": self.user_id,
            "reason": self.reason,
            "dismissal_context": self.dismissal_context
        }


@dataclass(frozen=True)
class HintFeedbackProvided(DomainEvent):
    """
    Event raised when user provides feedback on a hint.
    
    Attributes:
        hint_id: The hint feedback is for
        task_id: The task the hint was for
        user_id: User providing feedback
        was_helpful: Whether the hint was helpful
        feedback_text: Detailed feedback text
        effectiveness_score: Numerical effectiveness rating
        improvement_suggestions: Suggestions for better hints
    """
    
    hint_id: UUID
    task_id: UUID
    user_id: str
    was_helpful: bool
    feedback_text: Optional[str] = None
    effectiveness_score: Optional[float] = None
    improvement_suggestions: Optional[str] = None
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_feedback_provided"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "hint_id": str(self.hint_id),
            "task_id": str(self.task_id),
            "user_id": self.user_id,
            "was_helpful": self.was_helpful,
            "feedback_text": self.feedback_text,
            "effectiveness_score": self.effectiveness_score,
            "improvement_suggestions": self.improvement_suggestions
        }


@dataclass(frozen=True)
class HintPatternDetected(DomainEvent):
    """
    Event raised when a new pattern is detected for hint generation.
    
    Attributes:
        pattern_id: Unique identifier for the pattern
        pattern_name: Name of the detected pattern
        pattern_description: Description of what was detected
        confidence: Confidence in the pattern
        affected_tasks: Tasks that match this pattern
        suggested_rule: Suggested rule based on pattern
    """
    
    pattern_id: UUID
    pattern_name: str
    pattern_description: str
    confidence: float
    affected_tasks: list[UUID] = field(default_factory=list)
    suggested_rule: Optional[Dict[str, Any]] = None
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_pattern_detected"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "pattern_id": str(self.pattern_id),
            "pattern_name": self.pattern_name,
            "pattern_description": self.pattern_description,
            "confidence": self.confidence,
            "affected_tasks": [str(task_id) for task_id in self.affected_tasks],
            "suggested_rule": self.suggested_rule
        }


@dataclass(frozen=True)
class HintEffectivenessCalculated(DomainEvent):
    """
    Event raised when hint effectiveness is calculated.
    
    Attributes:
        hint_type: Type of hints being evaluated
        source_rule: Rule that generated the hints
        total_hints: Total number of hints generated
        accepted_count: Number of hints accepted
        dismissed_count: Number of hints dismissed
        effectiveness_score: Calculated effectiveness (0.0 to 1.0)
        period_start: Start of evaluation period
        period_end: End of evaluation period
    """
    
    hint_type: HintType
    source_rule: str
    total_hints: int
    accepted_count: int
    dismissed_count: int
    effectiveness_score: float
    period_start: datetime
    period_end: datetime
    # Event metadata
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "hint_effectiveness_calculated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "hint_type": self.hint_type.value,
            "source_rule": self.source_rule,
            "total_hints": self.total_hints,
            "accepted_count": self.accepted_count,
            "dismissed_count": self.dismissed_count,
            "effectiveness_score": self.effectiveness_score,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat()
        }