"""Vision System Domain Value Objects.

This module defines value objects for the Vision Enrichment System,
which tracks alignment between tasks and organizational objectives.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class VisionHierarchyLevel(str, Enum):
    """Hierarchical levels for vision objectives."""
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    TEAM = "team"
    PROJECT = "project"
    MILESTONE = "milestone"


class ContributionType(str, Enum):
    """Types of contributions a task can make to a vision objective."""
    DIRECT = "direct"  # Task directly implements the objective
    SUPPORTING = "supporting"  # Task supports but doesn't directly implement
    ENABLING = "enabling"  # Task enables future work on the objective
    EXPLORATORY = "exploratory"  # Task explores possibilities for the objective
    MAINTENANCE = "maintenance"  # Task maintains existing objective achievements


class MetricType(str, Enum):
    """Types of metrics that can be tracked."""
    PERCENTAGE = "percentage"
    COUNT = "count"
    CURRENCY = "currency"
    TIME = "time"
    RATING = "rating"
    CUSTOM = "custom"


@dataclass(frozen=True)
class VisionMetric:
    """Represents a measurable metric for a vision objective."""
    name: str
    current_value: float
    target_value: float
    unit: str
    metric_type: MetricType = MetricType.CUSTOM
    baseline_value: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as a percentage of target."""
        if self.target_value == self.baseline_value:
            return 100.0 if self.current_value >= self.target_value else 0.0
        
        progress = (self.current_value - self.baseline_value) / (self.target_value - self.baseline_value)
        return min(max(progress * 100, 0.0), 100.0)
    
    @property
    def is_achieved(self) -> bool:
        """Check if the metric has reached its target."""
        return self.current_value >= self.target_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "unit": self.unit,
            "metric_type": self.metric_type.value,
            "baseline_value": self.baseline_value,
            "progress_percentage": self.progress_percentage,
            "is_achieved": self.is_achieved,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass(frozen=True)
class VisionObjective:
    """Represents a vision objective in the organizational hierarchy."""
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    level: VisionHierarchyLevel = VisionHierarchyLevel.PROJECT
    parent_id: Optional[UUID] = None
    owner: str = ""
    priority: int = 1  # 1-5, where 5 is highest priority
    status: str = "active"  # active, completed, paused, cancelled
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    metrics: List[VisionMetric] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def overall_progress(self) -> float:
        """Calculate overall progress across all metrics."""
        if not self.metrics:
            return 0.0
        
        total_progress = sum(metric.progress_percentage for metric in self.metrics)
        return total_progress / len(self.metrics)
    
    @property
    def is_completed(self) -> bool:
        """Check if all metrics are achieved."""
        if not self.metrics:
            return False
        return all(metric.is_achieved for metric in self.metrics)
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until due date."""
        if not self.due_date:
            return None
        
        remaining = (self.due_date - datetime.now(timezone.utc)).days
        return max(remaining, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "level": self.level.value,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "owner": self.owner,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "due_date": self.due_date if self.due_date else None,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "tags": self.tags,
            "overall_progress": self.overall_progress,
            "is_completed": self.is_completed,
            "days_remaining": self.days_remaining,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class VisionAlignment:
    """Represents alignment between a task and a vision objective."""
    task_id: UUID
    objective_id: UUID
    alignment_score: float  # 0.0 to 1.0
    contribution_type: ContributionType
    confidence: float = 0.8  # Confidence in the alignment assessment
    rationale: str = ""
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    factors: Dict[str, float] = field(default_factory=dict)  # Contributing factors to score
    
    @property
    def is_strong_alignment(self) -> bool:
        """Check if alignment is strong (>= 0.7)."""
        return self.alignment_score >= 0.7
    
    @property
    def is_weak_alignment(self) -> bool:
        """Check if alignment is weak (< 0.3)."""
        return self.alignment_score < 0.3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": str(self.task_id),
            "objective_id": str(self.objective_id),
            "alignment_score": self.alignment_score,
            "contribution_type": self.contribution_type.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "calculated_at": self.calculated_at.isoformat(),
            "is_strong_alignment": self.is_strong_alignment,
            "is_weak_alignment": self.is_weak_alignment,
            "factors": self.factors
        }


@dataclass(frozen=True)
class VisionInsight:
    """Represents an insight or recommendation based on vision analysis."""
    id: UUID = field(default_factory=uuid4)
    type: str = "recommendation"  # recommendation, warning, opportunity
    title: str = ""
    description: str = ""
    impact: str = "medium"  # low, medium, high, critical
    affected_objectives: List[UUID] = field(default_factory=list)
    affected_tasks: List[UUID] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if the insight has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def urgency_score(self) -> float:
        """Calculate urgency based on impact and expiration."""
        impact_scores = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
        base_score = impact_scores.get(self.impact, 0.5)
        
        if self.expires_at:
            days_until_expiry = (self.expires_at - datetime.now(timezone.utc)).days
            if days_until_expiry <= 1:
                return min(base_score * 1.5, 1.0)
            elif days_until_expiry <= 7:
                return min(base_score * 1.2, 1.0)
        
        return base_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "affected_objectives": [str(obj_id) for obj_id in self.affected_objectives],
            "affected_tasks": [str(task_id) for task_id in self.affected_tasks],
            "suggested_actions": self.suggested_actions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "urgency_score": self.urgency_score,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class VisionDashboard:
    """Aggregated vision metrics and insights for executive view."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_objectives: int = 0
    active_objectives: int = 0
    completed_objectives: int = 0
    overall_progress: float = 0.0
    objectives_by_level: Dict[str, int] = field(default_factory=dict)
    objectives_by_status: Dict[str, int] = field(default_factory=dict)
    top_performing_objectives: List[Dict[str, Any]] = field(default_factory=list)
    at_risk_objectives: List[Dict[str, Any]] = field(default_factory=list)
    recent_completions: List[Dict[str, Any]] = field(default_factory=list)
    active_insights: List[VisionInsight] = field(default_factory=list)
    alignment_summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_objectives": self.total_objectives,
                "active_objectives": self.active_objectives,
                "completed_objectives": self.completed_objectives,
                "overall_progress": self.overall_progress
            },
            "breakdowns": {
                "by_level": self.objectives_by_level,
                "by_status": self.objectives_by_status
            },
            "highlights": {
                "top_performing": self.top_performing_objectives,
                "at_risk": self.at_risk_objectives,
                "recent_completions": self.recent_completions
            },
            "insights": [insight.to_dict() for insight in self.active_insights],
            "alignment": self.alignment_summary
        }