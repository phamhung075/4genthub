"""
Workflow hint value objects for the Vision System.

This module defines the domain models for intelligent workflow hints,
including hint types, priorities, metadata, and collections.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4


class HintType(Enum):
    """Types of workflow hints available in the system."""
    
    NEXT_ACTION = "next_action"
    BLOCKER_RESOLUTION = "blocker_resolution"
    OPTIMIZATION = "optimization"
    COMPLETION = "completion"
    COLLABORATION = "collaboration"


class HintPriority(Enum):
    """Priority levels for workflow hints."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class HintMetadata:
    """
    Metadata associated with a workflow hint.
    
    Attributes:
        source: The system or rule that generated the hint
        confidence: Confidence score (0.0 to 1.0)
        reasoning: Explanation of why this hint was generated
        related_tasks: IDs of tasks that influenced this hint
        patterns_detected: Named patterns that were identified
        effectiveness_score: Historical effectiveness of similar hints
    """
    
    source: str
    confidence: float
    reasoning: str
    related_tasks: List[UUID] = field(default_factory=list)
    patterns_detected: List[str] = field(default_factory=list)
    effectiveness_score: Optional[float] = None
    
    def __post_init__(self):
        """Validate metadata fields."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        
        if self.effectiveness_score is not None:
            if not 0.0 <= self.effectiveness_score <= 1.0:
                raise ValueError("Effectiveness score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class WorkflowHint:
    """
    A single workflow hint providing intelligent guidance.
    
    Attributes:
        id: Unique identifier for the hint
        type: The type of hint (next action, blocker resolution, etc.)
        priority: The priority level of the hint
        message: Human-readable hint message
        suggested_action: Specific action the user should take
        metadata: Additional metadata about the hint
        created_at: When the hint was generated
        task_id: The task this hint is for
        context_data: Relevant context data for the hint
        expires_at: When this hint is no longer relevant
    """
    
    id: UUID
    type: HintType
    priority: HintPriority
    message: str
    suggested_action: str
    metadata: HintMetadata
    created_at: datetime
    task_id: UUID
    context_data: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        task_id: UUID,
        hint_type: HintType,
        priority: HintPriority,
        message: str,
        suggested_action: str,
        metadata: HintMetadata,
        context_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> "WorkflowHint":
        """
        Factory method to create a new workflow hint.
        
        Args:
            task_id: The task this hint is for
            hint_type: The type of hint
            priority: The priority level
            message: Human-readable hint message
            suggested_action: Specific action to take
            metadata: Hint metadata
            context_data: Additional context data
            expires_at: Expiration time for the hint
            
        Returns:
            A new WorkflowHint instance
        """
        return cls(
            id=uuid4(),
            type=hint_type,
            priority=priority,
            message=message,
            suggested_action=suggested_action,
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
            task_id=task_id,
            context_data=context_data or {},
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if the hint has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert hint to dictionary representation."""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "priority": self.priority.value,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "reasoning": self.metadata.reasoning,
            "confidence": self.metadata.confidence,
            "created_at": self.created_at.isoformat(),
            "task_id": str(self.task_id),
            "context_data": self.context_data,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class HintCollection:
    """
    A collection of workflow hints for a task.
    
    Manages multiple hints, filtering, and prioritization.
    """
    
    task_id: UUID
    hints: List[WorkflowHint] = field(default_factory=list)
    
    def add_hint(self, hint: WorkflowHint) -> None:
        """Add a hint to the collection."""
        if hint.task_id != self.task_id:
            raise ValueError("Hint task_id must match collection task_id")
        self.hints.append(hint)
    
    def get_active_hints(self) -> List[WorkflowHint]:
        """Get all non-expired hints."""
        return [hint for hint in self.hints if not hint.is_expired()]
    
    def get_hints_by_type(self, hint_type: HintType) -> List[WorkflowHint]:
        """Get hints of a specific type."""
        return [
            hint for hint in self.get_active_hints()
            if hint.type == hint_type
        ]
    
    def get_hints_by_priority(self, priority: HintPriority) -> List[WorkflowHint]:
        """Get hints of a specific priority."""
        return [
            hint for hint in self.get_active_hints()
            if hint.priority == priority
        ]
    
    def get_top_hints(self, limit: int = 3) -> List[WorkflowHint]:
        """
        Get the top hints by priority and confidence.
        
        Args:
            limit: Maximum number of hints to return
            
        Returns:
            List of top hints, sorted by priority and confidence
        """
        priority_order = {
            HintPriority.CRITICAL: 0,
            HintPriority.HIGH: 1,
            HintPriority.MEDIUM: 2,
            HintPriority.LOW: 3
        }
        
        active_hints = self.get_active_hints()
        sorted_hints = sorted(
            active_hints,
            key=lambda h: (
                priority_order[h.priority],
                -h.metadata.confidence
            )
        )
        
        return sorted_hints[:limit]
    
    def remove_expired_hints(self) -> int:
        """Remove all expired hints and return the count removed."""
        original_count = len(self.hints)
        self.hints = self.get_active_hints()
        return original_count - len(self.hints)
    
    def clear_hints_by_type(self, hint_type: HintType) -> int:
        """Remove all hints of a specific type and return the count removed."""
        original_count = len(self.hints)
        self.hints = [
            hint for hint in self.hints
            if hint.type != hint_type
        ]
        return original_count - len(self.hints)