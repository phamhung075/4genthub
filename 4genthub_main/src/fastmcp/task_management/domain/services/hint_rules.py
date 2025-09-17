"""
Hint generation rules for the Vision System.

This module defines the rule interface and various rule implementations
for generating intelligent workflow hints based on task state, progress,
and context.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..value_objects.hints import (
    WorkflowHint, HintType, HintPriority, HintMetadata
)
from ..value_objects.progress import ProgressType, ProgressStatus
from ..entities.task import Task
from ..entities.context import TaskContext


@dataclass
class RuleContext:
    """Context information for rule evaluation."""
    
    task: Task
    context: Optional[TaskContext] = None
    related_tasks: List[Task] = None
    historical_patterns: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.related_tasks is None:
            self.related_tasks = []
        if self.historical_patterns is None:
            self.historical_patterns = {}


class HintRule(ABC):
    """Abstract base class for hint generation rules."""
    
    @abstractmethod
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        """
        Evaluate the rule and generate a hint if applicable.
        
        Args:
            rule_context: Context information for evaluation
            
        Returns:
            A WorkflowHint if the rule applies, None otherwise
        """
        pass
    
    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Return the name of this rule."""
        pass


class ProgressBasedHintRule(HintRule):
    """Base class for rules based on task progress."""
    
    def get_latest_progress(
        self,
        task: Task,
        progress_type: Optional[ProgressType] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest progress entry for a task."""
        if not hasattr(task, 'progress_timeline') or not task.progress_timeline:
            return None
        
        if progress_type:
            filtered = [
                p for p in task.progress_timeline
                if p.get('type') == progress_type.value
            ]
            return filtered[-1] if filtered else None
        
        return task.progress_timeline[-1] if task.progress_timeline else None


class StalledProgressRule(ProgressBasedHintRule):
    """Generate hints for stalled tasks."""
    
    def __init__(self, stall_hours: int = 24):
        self.stall_hours = stall_hours
    
    @property
    def rule_name(self) -> str:
        return "stalled_progress"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        latest_progress = self.get_latest_progress(task)
        
        if not latest_progress:
            return None
        
        last_update = datetime.fromisoformat(latest_progress['timestamp'])
        stall_duration = datetime.now(timezone.utc) - last_update
        
        if stall_duration < timedelta(hours=self.stall_hours):
            return None
        
        # Check if task is blocked
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        if status_value == "blocked":
            return self._create_blocker_hint(task, stall_duration)
        
        # Task is stalled but not marked as blocked
        return self._create_stalled_hint(task, stall_duration)
    
    def _create_blocker_hint(
        self,
        task: Task,
        stall_duration: timedelta
    ) -> WorkflowHint:
        """Create a blocker resolution hint."""
        hours_stalled = int(stall_duration.total_seconds() / 3600)
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.9,
            reasoning=f"Task has been blocked for {hours_stalled} hours",
            related_tasks=[],
            patterns_detected=["extended_blocker"]
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.BLOCKER_RESOLUTION,
            priority=HintPriority.CRITICAL if hours_stalled > 48 else HintPriority.HIGH,
            message=f"Task has been blocked for {hours_stalled} hours",
            suggested_action="Review blockers and consider: 1) Escalating to team lead, 2) Finding alternative approaches, 3) Breaking down the blocker into smaller issues",
            metadata=metadata,
            context_data={"hours_stalled": hours_stalled}
        )
    
    def _create_stalled_hint(
        self,
        task: Task,
        stall_duration: timedelta
    ) -> WorkflowHint:
        """Create a hint for stalled but not blocked tasks."""
        hours_stalled = int(stall_duration.total_seconds() / 3600)
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.8,
            reasoning=f"No progress recorded for {hours_stalled} hours",
            related_tasks=[],
            patterns_detected=["progress_stall"]
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message=f"No progress recorded for {hours_stalled} hours",
            suggested_action="Consider: 1) Updating task progress, 2) Marking as blocked if stuck, 3) Breaking down into smaller subtasks",
            metadata=metadata,
            context_data={"hours_stalled": hours_stalled}
        )


class ImplementationReadyForTestingRule(ProgressBasedHintRule):
    """Suggest testing when implementation is sufficiently complete."""
    
    def __init__(self, implementation_threshold: float = 0.75):
        self.implementation_threshold = implementation_threshold
    
    @property
    def rule_name(self) -> str:
        return "implementation_ready_for_testing"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        
        # Get implementation progress
        impl_progress = None
        test_progress = None
        
        if hasattr(task, 'progress_breakdown'):
            impl_progress = task.progress_breakdown.get(ProgressType.IMPLEMENTATION.value)
            test_progress = task.progress_breakdown.get(ProgressType.TESTING.value)
        
        if not impl_progress or impl_progress < self.implementation_threshold:
            return None
        
        # Check if testing has started
        if test_progress and test_progress > 0.1:
            return None
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.85,
            reasoning=f"Implementation is {int(impl_progress * 100)}% complete",
            patterns_detected=["parallel_testing_opportunity"]
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message=f"Implementation is {int(impl_progress * 100)}% complete - ready for testing",
            suggested_action="Start creating test cases for completed functionality to enable parallel development",
            metadata=metadata,
            context_data={
                "implementation_progress": impl_progress,
                "testing_progress": test_progress or 0
            }
        )


class MissingContextRule(HintRule):
    """Generate hints for tasks with missing or incomplete context."""
    
    @property
    def rule_name(self) -> str:
        return "missing_context"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        context = rule_context.context
        
        if not context:
            return self._create_missing_context_hint(task)
        
        # Check for specific missing fields
        missing_fields = []
        
        if not context.notes.get('test_notes'):
            missing_fields.append("test notes")
        
        if not context.notes.get('design_decisions'):
            missing_fields.append("design decisions")
        
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        if status_value in ["done", "review"] and not context.data.get('completion_summary'):
            missing_fields.append("completion summary")
        
        if missing_fields:
            return self._create_incomplete_context_hint(task, missing_fields)
        
        return None
    
    def _create_missing_context_hint(self, task: Task) -> WorkflowHint:
        """Create hint for completely missing context."""
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.95,
            reasoning="Task has no context information",
            patterns_detected=["missing_context"]
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Task is missing context information",
            suggested_action="Add context with task objectives, requirements, and initial notes",
            metadata=metadata
        )
    
    def _create_incomplete_context_hint(
        self,
        task: Task,
        missing_fields: List[str]
    ) -> WorkflowHint:
        """Create hint for incomplete context."""
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.9,
            reasoning=f"Context missing: {', '.join(missing_fields)}",
            patterns_detected=["incomplete_context"]
        )
        
        fields_str = ", ".join(missing_fields)
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.COMPLETION,
            priority=HintPriority.MEDIUM,
            message=f"Context is missing: {fields_str}",
            suggested_action=f"Update context with {fields_str} for better tracking and knowledge sharing",
            metadata=metadata,
            context_data={"missing_fields": missing_fields}
        )


class ComplexDependencyRule(HintRule):
    """Suggest breakdown for tasks with complex dependencies."""
    
    def __init__(self, complexity_threshold: int = 3):
        self.complexity_threshold = complexity_threshold
    
    @property
    def rule_name(self) -> str:
        return "complex_dependencies"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        
        # Count dependencies
        dependency_count = len(getattr(task, 'dependencies', []))
        
        if dependency_count < self.complexity_threshold:
            return None
        
        # Check if task already has subtasks
        if hasattr(task, 'subtasks') and task.subtasks:
            return None
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.8,
            reasoning=f"Task has {dependency_count} dependencies",
            patterns_detected=["high_complexity"]
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.OPTIMIZATION,
            priority=HintPriority.MEDIUM,
            message=f"Task has {dependency_count} dependencies - consider decomposition",
            suggested_action="Break down the task into smaller subtasks to manage dependencies more effectively",
            metadata=metadata,
            context_data={"dependency_count": dependency_count}
        )


class NearCompletionRule(ProgressBasedHintRule):
    """Generate hints for tasks nearing completion."""
    
    def __init__(self, completion_threshold: float = 0.9):
        self.completion_threshold = completion_threshold
    
    @property
    def rule_name(self) -> str:
        return "near_completion"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        
        # Check overall progress
        if not hasattr(task, 'progress') or task.progress < self.completion_threshold:
            return None
        
        # Check what's missing
        missing_steps = []
        
        if hasattr(task, 'progress_breakdown'):
            breakdown = task.progress_breakdown
            
            if breakdown.get(ProgressType.TESTING.value, 0) < 1.0:
                missing_steps.append("complete testing")
            
            if breakdown.get(ProgressType.DOCUMENTATION.value, 0) < 0.8:
                missing_steps.append("update documentation")
            
            if breakdown.get(ProgressType.REVIEW.value, 0) < 1.0:
                missing_steps.append("complete review")
        
        if not missing_steps:
            return None
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.9,
            reasoning=f"Task is {int(task.progress * 100)}% complete",
            patterns_detected=["near_completion"]
        )
        
        steps_str = ", ".join(missing_steps)
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.COMPLETION,
            priority=HintPriority.HIGH,
            message=f"Task is {int(task.progress * 100)}% complete",
            suggested_action=f"To complete the task: {steps_str}",
            metadata=metadata,
            context_data={
                "overall_progress": task.progress,
                "missing_steps": missing_steps
            }
        )


class CollaborationNeededRule(HintRule):
    """Suggest collaboration for tasks that would benefit from it."""
    
    @property
    def rule_name(self) -> str:
        return "collaboration_needed"
    
    def evaluate(self, rule_context: RuleContext) -> Optional[WorkflowHint]:
        task = rule_context.task
        context = rule_context.context
        
        # Check for collaboration indicators
        indicators = []
        
        # Long-running task
        if hasattr(task, 'created_at'):
            age = datetime.now(timezone.utc) - task.created_at
            status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
            if age > timedelta(days=7) and status_value not in ["done", "cancelled"]:
                indicators.append("long_running")
        
        # Multiple failed attempts
        if context and context.notes.get('failed_attempts', 0) > 2:
            indicators.append("multiple_failures")
        
        # High priority but slow progress
        priority_value = task.priority.label if hasattr(task.priority, 'label') else str(task.priority)
        if priority_value in ["urgent", "critical"] and getattr(task, 'progress', 0) < 0.3:
            indicators.append("high_priority_slow_progress")
        
        if not indicators:
            return None
        
        metadata = HintMetadata(
            source=self.rule_name,
            confidence=0.75,
            reasoning=f"Collaboration indicators: {', '.join(indicators)}",
            patterns_detected=indicators
        )
        
        return WorkflowHint.create(
            task_id=task.id,
            hint_type=HintType.COLLABORATION,
            priority=HintPriority.MEDIUM,
            message="This task might benefit from collaboration",
            suggested_action="Consider: 1) Pair programming session, 2) Design review with team, 3) Asking for help on specific blockers",
            metadata=metadata,
            context_data={"indicators": indicators}
        )