"""Domain events for progress tracking in the Vision System.

This module defines events that are emitted when progress-related actions occur,
enabling event-driven architectures and maintaining audit trails.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4

from ..value_objects.progress import ProgressType, ProgressStatus, ProgressSnapshot
from ..value_objects.task_id import TaskId


@dataclass(frozen=True)
class ProgressEvent:
    """Base class for all progress-related events."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: Union[str, TaskId] = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        # Handle TaskId objects by converting to string
        task_id_str = str(self.task_id) if isinstance(self.task_id, TaskId) else self.task_id
        
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "task_id": task_id_str,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id
        }


@dataclass(frozen=True)
class ProgressUpdated(ProgressEvent):
    """Event emitted when task progress is updated."""
    progress_type: ProgressType = ProgressType.GENERAL
    old_percentage: float = 0.0
    new_percentage: float = 0.0
    status: ProgressStatus = ProgressStatus.IN_PROGRESS
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress_type": self.progress_type.value,
            "old_percentage": self.old_percentage,
            "new_percentage": self.new_percentage,
            "status": self.status.value,
            "description": self.description,
            "metadata": self.metadata
        })
        return base_dict
    
    @property
    def progress_delta(self) -> float:
        """Calculate the change in progress."""
        return self.new_percentage - self.old_percentage


@dataclass(frozen=True)
class ProgressMilestoneReached(ProgressEvent):
    """Event emitted when a progress milestone is reached."""
    milestone_name: str = ""
    milestone_percentage: float = 0.0
    current_progress: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "milestone_name": self.milestone_name,
            "milestone_percentage": self.milestone_percentage,
            "current_progress": self.current_progress
        })
        return base_dict


@dataclass(frozen=True)
class ProgressStalled(ProgressEvent):
    """Event emitted when progress has not changed for a significant period."""
    last_update_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stall_duration_hours: float = 0.0
    current_percentage: float = 0.0
    blockers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "last_update_timestamp": self.last_update_timestamp.isoformat(),
            "stall_duration_hours": self.stall_duration_hours,
            "current_percentage": self.current_percentage,
            "blockers": self.blockers
        })
        return base_dict


@dataclass(frozen=True)
class SubtaskProgressAggregated(ProgressEvent):
    """Event emitted when subtask progress is aggregated into parent task."""
    parent_task_id: str = ""
    subtask_count: int = 0
    old_parent_progress: float = 0.0
    new_parent_progress: float = 0.0
    aggregation_method: str = "weighted_average"
    subtask_progress_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "parent_task_id": self.parent_task_id,
            "subtask_count": self.subtask_count,
            "old_parent_progress": self.old_parent_progress,
            "new_parent_progress": self.new_parent_progress,
            "aggregation_method": self.aggregation_method,
            "subtask_progress_details": self.subtask_progress_details
        })
        return base_dict


@dataclass(frozen=True)
class ProgressSnapshotCreated(ProgressEvent):
    """Event emitted when a progress snapshot is created."""
    snapshot: ProgressSnapshot = field(default_factory=ProgressSnapshot)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "snapshot": self.snapshot.to_dict()
        })
        return base_dict


@dataclass(frozen=True)
class ProgressTypeCompleted(ProgressEvent):
    """Event emitted when a specific progress type reaches 100%."""
    progress_type: ProgressType = ProgressType.GENERAL
    completion_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress_type": self.progress_type.value,
            "completion_timestamp": self.completion_timestamp.isoformat()
        })
        return base_dict


@dataclass(frozen=True)
class ProgressBlocked(ProgressEvent):
    """Event emitted when progress is blocked."""
    progress_type: ProgressType = ProgressType.GENERAL
    current_percentage: float = 0.0
    blockers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_unblock_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress_type": self.progress_type.value,
            "current_percentage": self.current_percentage,
            "blockers": self.blockers,
            "dependencies": self.dependencies,
            "estimated_unblock_time": self.estimated_unblock_time.isoformat() 
                                     if self.estimated_unblock_time else None
        })
        return base_dict


@dataclass(frozen=True)
class ProgressUnblocked(ProgressEvent):
    """Event emitted when progress is unblocked."""
    progress_type: ProgressType = ProgressType.GENERAL
    blocked_duration_hours: float = 0.0
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress_type": self.progress_type.value,
            "blocked_duration_hours": self.blocked_duration_hours,
            "resolution": self.resolution
        })
        return base_dict


@dataclass(frozen=True) 
class ProgressRolledBack(ProgressEvent):
    """Event emitted when progress is rolled back due to issues."""
    progress_type: ProgressType = ProgressType.GENERAL
    from_percentage: float = 0.0
    to_percentage: float = 0.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress_type": self.progress_type.value,
            "from_percentage": self.from_percentage,
            "to_percentage": self.to_percentage,
            "reason": self.reason
        })
        return base_dict