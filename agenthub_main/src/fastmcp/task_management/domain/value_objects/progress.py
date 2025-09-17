"""Progress tracking value objects for the Vision System.

This module provides value objects for tracking task progress with support for:
- Different progress types (analysis, design, implementation, testing, etc.)
- Progress snapshots and timeline tracking
- Progress calculation and aggregation
- Milestone tracking
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4


class ProgressType(Enum):
    """Types of progress that can be tracked."""
    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    GENERAL = "general"  # Default/catch-all type


class ProgressStatus(Enum):
    """Status of progress."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    PAUSED = "paused"


@dataclass(frozen=True)
class ProgressMetadata:
    """Additional metadata for progress tracking."""
    blockers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    confidence_level: float = 1.0  # 0.0 to 1.0
    notes: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "blockers": self.blockers,
            "dependencies": self.dependencies,
            "confidence_level": self.confidence_level,
            "notes": self.notes,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProgressMetadata:
        """Create from dictionary representation."""
        return cls(
            blockers=data.get("blockers", []),
            dependencies=data.get("dependencies", []),
            confidence_level=data.get("confidence_level", 1.0),
            notes=data.get("notes"),
            estimated_completion=datetime.fromisoformat(data["estimated_completion"]) 
                                if data.get("estimated_completion") else None
        )


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable snapshot of progress at a point in time."""
    id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    progress_type: ProgressType = ProgressType.GENERAL
    percentage: float = 0.0  # 0-100
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    description: Optional[str] = None
    metadata: ProgressMetadata = field(default_factory=ProgressMetadata)
    agent_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate progress percentage."""
        if not 0 <= self.percentage <= 100:
            raise ValueError(f"Progress percentage must be between 0 and 100, got {self.percentage}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "progress_type": self.progress_type.value,
            "percentage": self.percentage,
            "status": self.status.value,
            "description": self.description,
            "metadata": self.metadata.to_dict(),
            "agent_id": self.agent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProgressSnapshot:
        """Create from dictionary representation."""
        return cls(
            id=data.get("id", str(uuid4())),
            task_id=data.get("task_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            progress_type=ProgressType(data.get("progress_type", "general")),
            percentage=data.get("percentage", 0.0),
            status=ProgressStatus(data.get("status", "not_started")),
            description=data.get("description"),
            metadata=ProgressMetadata.from_dict(data.get("metadata", {})),
            agent_id=data.get("agent_id")
        )


@dataclass
class ProgressTimeline:
    """Aggregate tracking the timeline of progress updates."""
    task_id: str
    snapshots: List[ProgressSnapshot] = field(default_factory=list)
    milestones: Dict[str, float] = field(default_factory=dict)  # name -> percentage
    
    def add_snapshot(self, snapshot: ProgressSnapshot) -> None:
        """Add a new progress snapshot to the timeline."""
        if snapshot.task_id != self.task_id:
            raise ValueError(f"Snapshot task_id {snapshot.task_id} doesn't match timeline task_id {self.task_id}")
        self.snapshots.append(snapshot)
        self.snapshots.sort(key=lambda s: s.timestamp)
    
    def get_latest_snapshot(self) -> Optional[ProgressSnapshot]:
        """Get the most recent progress snapshot."""
        return self.snapshots[-1] if self.snapshots else None
    
    def get_snapshots_by_type(self, progress_type: ProgressType) -> List[ProgressSnapshot]:
        """Get all snapshots of a specific progress type."""
        return [s for s in self.snapshots if s.progress_type == progress_type]
    
    def get_overall_progress(self) -> float:
        """Calculate overall progress based on latest snapshot of each type."""
        if not self.snapshots:
            return 0.0
        
        # Get latest snapshot for each progress type
        latest_by_type: Dict[ProgressType, ProgressSnapshot] = {}
        for snapshot in self.snapshots:
            if (snapshot.progress_type not in latest_by_type or 
                snapshot.timestamp > latest_by_type[snapshot.progress_type].timestamp):
                latest_by_type[snapshot.progress_type] = snapshot
        
        # Calculate average progress across all types
        if not latest_by_type:
            return 0.0
        
        total_progress = sum(s.percentage for s in latest_by_type.values())
        return total_progress / len(latest_by_type)
    
    def add_milestone(self, name: str, percentage: float) -> None:
        """Add or update a milestone."""
        if not 0 <= percentage <= 100:
            raise ValueError(f"Milestone percentage must be between 0 and 100, got {percentage}")
        self.milestones[name] = percentage
    
    def is_milestone_reached(self, name: str) -> bool:
        """Check if a milestone has been reached."""
        if name not in self.milestones:
            return False
        
        current_progress = self.get_overall_progress()
        return current_progress >= self.milestones[name]
    
    def get_progress_trend(self, hours: int = 24) -> List[ProgressSnapshot]:
        """Get progress snapshots from the last N hours."""
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        return [s for s in self.snapshots if s.timestamp.timestamp() > cutoff]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "milestones": self.milestones,
            "overall_progress": self.get_overall_progress()
        }


@dataclass
class ProgressCalculationStrategy:
    """Strategy for calculating progress from multiple sources."""
    
    @staticmethod
    def calculate_weighted_average(
        progress_values: Dict[str, float], 
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate weighted average of progress values."""
        if not progress_values:
            return 0.0
        
        if weights is None:
            # Equal weights if not specified
            weights = {k: 1.0 for k in progress_values.keys()}
        
        # Ensure all progress values have weights
        for key in progress_values:
            if key not in weights:
                weights[key] = 1.0
        
        total_weight = sum(weights.get(k, 0) for k in progress_values.keys())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(
            progress_values[k] * weights.get(k, 0) 
            for k in progress_values.keys()
        )
        
        return weighted_sum / total_weight
    
    @staticmethod
    def calculate_from_subtasks(
        subtask_progress: List[Dict[str, Any]], 
        include_blocked: bool = False
    ) -> float:
        """Calculate progress from subtasks."""
        if not subtask_progress:
            return 0.0
        
        valid_subtasks = []
        for subtask in subtask_progress:
            status = subtask.get("status", "")
            if not include_blocked and status == "blocked":
                continue
            valid_subtasks.append(subtask)
        
        if not valid_subtasks:
            return 0.0
        
        total_progress = sum(
            subtask.get("progress", 0.0) for subtask in valid_subtasks
        )
        
        return total_progress / len(valid_subtasks)
    
    @staticmethod
    def calculate_by_milestones(
        completed_milestones: List[str],
        all_milestones: Dict[str, float]
    ) -> float:
        """Calculate progress based on completed milestones."""
        if not all_milestones:
            return 0.0
        
        completed_values = [
            all_milestones[m] for m in completed_milestones 
            if m in all_milestones
        ]
        
        if not completed_values:
            return 0.0
        
        return max(completed_values)