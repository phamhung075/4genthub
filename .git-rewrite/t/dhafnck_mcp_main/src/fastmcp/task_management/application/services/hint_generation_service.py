"""
Hint generation service for the Vision System.

This service coordinates hint generation using various rules,
manages hint lifecycle, and integrates with the event system.
"""

import logging
from typing import List, Optional, Dict, Any, Type
from uuid import UUID
from datetime import datetime, timezone
from datetime import datetime, timedelta

from ...domain.value_objects.hints import (
    WorkflowHint, HintCollection, HintType, HintPriority
)
from ...domain.services.hint_rules import (
    HintRule, RuleContext,
    StalledProgressRule,
    ImplementationReadyForTestingRule,
    MissingContextRule,
    ComplexDependencyRule,
    NearCompletionRule,
    CollaborationNeededRule
)
from ...domain.events.hint_events import (
    HintGenerated, HintAccepted, HintDismissed,
    HintFeedbackProvided, HintEffectivenessCalculated
)
from ...domain.entities.task import Task
from ...domain.entities.context import TaskContext
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.context_repository import ContextRepository
from ...infrastructure.event_store import EventStore, get_event_store


logger = logging.getLogger(__name__)


class HintGenerationService:
    """
    Service for generating intelligent workflow hints.
    
    This service applies various rules to generate context-aware hints,
    manages hint ranking and filtering, and publishes hint-related events.
    """
    
    def __init__(
        self,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[Any] = None,  # EventStore not implemented yet
        hint_repository: Optional[Any] = None  # Will be created later
    ):
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_store = event_store
        self.hint_repository = hint_repository
        
        # Initialize default rules
        self.rules: List[HintRule] = self._initialize_default_rules()
        
        # Cache for hint effectiveness scores
        self._effectiveness_cache: Dict[str, float] = {}
    
    def _initialize_default_rules(self) -> List[HintRule]:
        """Initialize the default set of hint generation rules."""
        return [
            StalledProgressRule(stall_hours=24),
            ImplementationReadyForTestingRule(implementation_threshold=0.75),
            MissingContextRule(),
            ComplexDependencyRule(complexity_threshold=3),
            NearCompletionRule(completion_threshold=0.9),
            CollaborationNeededRule()
        ]
    
    async def generate_hints_for_task(
        self,
        task_id: UUID,
        hint_types: Optional[List[HintType]] = None,
        max_hints: int = 5
    ) -> HintCollection:
        """
        Generate workflow hints for a specific task.
        
        Args:
            task_id: ID of the task to generate hints for
            hint_types: Optional filter for specific hint types
            max_hints: Maximum number of hints to return
            
        Returns:
            HintCollection containing generated hints
        """
        # Fetch task and context
        task = await self.task_repository.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return HintCollection(task_id=task_id)
        
        context = None
        try:
            context = await self.context_repository.get_by_task_id(task_id)
        except Exception as e:
            logger.debug(f"No context found for task {task_id}: {e}")
        
        # Get related tasks for pattern analysis
        related_tasks = await self._get_related_tasks(task)
        
        # Create rule context
        rule_context = RuleContext(
            task=task,
            context=context,
            related_tasks=related_tasks,
            historical_patterns=await self._get_historical_patterns(task)
        )
        
        # Generate hints using all applicable rules
        hints = []
        for rule in self.rules:
            try:
                hint = rule.evaluate(rule_context)
                if hint and self._should_include_hint(hint, hint_types):
                    # Enhance hint with effectiveness score
                    hint = self._enhance_hint_with_effectiveness(hint, rule)
                    hints.append(hint)
                    
                    # Publish hint generated event
                    await self._publish_hint_generated(hint, rule)
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_name}: {e}")
        
        # Create and return hint collection
        collection = HintCollection(task_id=task_id, hints=hints)
        
        # Sort and limit hints
        top_hints = collection.get_top_hints(limit=max_hints)
        collection.hints = top_hints
        
        # Store hints if repository available
        if self.hint_repository:
            await self._store_hints(collection)
        
        return collection
    
    async def _get_related_tasks(self, task: Task) -> List[Task]:
        """Get tasks related to the given task."""
        related = []
        
        # Get tasks with same labels
        if hasattr(task, 'labels') and task.labels:
            for label in task.labels[:2]:  # Limit to avoid too many queries
                tasks = await self.task_repository.list(labels=[label], limit=5)
                related.extend(tasks)
        
        # Get subtasks if any
        if hasattr(task, 'subtasks') and task.subtasks:
            for subtask_id in task.subtasks[:5]:
                subtask = await self.task_repository.get(subtask_id)
                if subtask:
                    related.append(subtask)
        
        # Remove duplicates
        seen = set()
        unique_related = []
        for t in related:
            if t.id not in seen and t.id != task.id:
                seen.add(t.id)
                unique_related.append(t)
        
        return unique_related
    
    async def _get_historical_patterns(self, task: Task) -> Dict[str, Any]:
        """Get historical patterns relevant to the task."""
        patterns = {}
        
        # Get patterns from similar completed tasks
        if hasattr(task, 'labels') and task.labels:
            completed_similar = await self.task_repository.list(
                status="done",
                labels=task.labels[:1],
                limit=10
            )
            
            if completed_similar:
                # Analyze completion times
                completion_times = []
                for t in completed_similar:
                    if hasattr(t, 'created_at') and hasattr(t, 'updated_at'):
                        duration = t.updated_at - t.created_at
                        completion_times.append(duration.total_seconds())
                
                if completion_times:
                    avg_completion = sum(completion_times) / len(completion_times)
                    patterns['avg_completion_seconds'] = avg_completion
                    patterns['similar_task_count'] = len(completed_similar)
        
        # Get hint effectiveness patterns
        if self.hint_repository:
            effectiveness = await self._get_hint_effectiveness_patterns()
            patterns['hint_effectiveness'] = effectiveness
        
        return patterns
    
    def _should_include_hint(
        self,
        hint: WorkflowHint,
        hint_types: Optional[List[HintType]]
    ) -> bool:
        """Check if a hint should be included based on filters."""
        if hint_types is None:
            return True
        return hint.type in hint_types
    
    def _enhance_hint_with_effectiveness(
        self,
        hint: WorkflowHint,
        rule: HintRule
    ) -> WorkflowHint:
        """Enhance hint with historical effectiveness data."""
        effectiveness_key = f"{rule.rule_name}:{hint.type.value}"
        effectiveness_score = self._effectiveness_cache.get(effectiveness_key)
        
        if effectiveness_score is not None:
            # Create new metadata with effectiveness score
            enhanced_metadata = HintMetadata(
                source=hint.metadata.source,
                confidence=hint.metadata.confidence,
                reasoning=hint.metadata.reasoning,
                related_tasks=hint.metadata.related_tasks,
                patterns_detected=hint.metadata.patterns_detected,
                effectiveness_score=effectiveness_score
            )
            
            # Import HintMetadata
            from ...domain.value_objects.hints import HintMetadata
            
            # Create new hint with enhanced metadata
            return WorkflowHint(
                id=hint.id,
                type=hint.type,
                priority=hint.priority,
                message=hint.message,
                suggested_action=hint.suggested_action,
                metadata=enhanced_metadata,
                created_at=hint.created_at,
                task_id=hint.task_id,
                context_data=hint.context_data,
                expires_at=hint.expires_at
            )
        
        return hint
    
    async def _publish_hint_generated(
        self,
        hint: WorkflowHint,
        rule: HintRule
    ) -> None:
        """Publish a hint generated event."""
        event = HintGenerated(
            aggregate_id=hint.task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id="system",
            hint_id=hint.id,
            task_id=hint.task_id,
            hint_type=hint.type,
            priority=hint.priority,
            message=hint.message,
            suggested_action=hint.suggested_action,
            source_rule=rule.rule_name,
            confidence=hint.metadata.confidence,
            metadata={
                "patterns_detected": hint.metadata.patterns_detected,
                "reasoning": hint.metadata.reasoning
            }
        )
        await self.event_store.append(event)
    
    async def _store_hints(self, collection: HintCollection) -> None:
        """Store hints in the repository."""
        if self.hint_repository:
            for hint in collection.hints:
                await self.hint_repository.save(hint)
    
    async def _get_hint_effectiveness_patterns(self) -> Dict[str, float]:
        """Get hint effectiveness patterns from historical data."""
        # This would query the hint repository for effectiveness data
        # For now, return placeholder data
        return {
            "stalled_progress:blocker_resolution": 0.85,
            "implementation_ready_for_testing:next_action": 0.92,
            "missing_context:next_action": 0.78,
            "complex_dependencies:optimization": 0.65,
            "near_completion:completion": 0.88,
            "collaboration_needed:collaboration": 0.70
        }
    
    async def accept_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        action_taken: Optional[str] = None
    ) -> None:
        """
        Record that a hint was accepted.
        
        Args:
            hint_id: ID of the accepted hint
            task_id: ID of the task
            user_id: User who accepted the hint
            action_taken: Description of action taken
        """
        event = HintAccepted(
            aggregate_id=task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id=user_id,
            hint_id=hint_id,
            task_id=task_id,
            action_taken=action_taken
        )
        await self.event_store.append(event)
        
        # Update effectiveness cache
        await self._update_effectiveness_cache()
    
    async def dismiss_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Record that a hint was dismissed.
        
        Args:
            hint_id: ID of the dismissed hint
            task_id: ID of the task
            user_id: User who dismissed the hint
            reason: Reason for dismissal
        """
        event = HintDismissed(
            aggregate_id=task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id=user_id,
            hint_id=hint_id,
            task_id=task_id,
            reason=reason
        )
        await self.event_store.append(event)
        
        # Update effectiveness cache
        await self._update_effectiveness_cache()
    
    async def provide_feedback(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None,
        effectiveness_score: Optional[float] = None
    ) -> None:
        """
        Record feedback on a hint.
        
        Args:
            hint_id: ID of the hint
            task_id: ID of the task
            user_id: User providing feedback
            was_helpful: Whether the hint was helpful
            feedback_text: Detailed feedback
            effectiveness_score: Numerical rating
        """
        event = HintFeedbackProvided(
            aggregate_id=task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id=user_id,
            hint_id=hint_id,
            task_id=task_id,
            was_helpful=was_helpful,
            feedback_text=feedback_text,
            effectiveness_score=effectiveness_score
        )
        await self.event_store.append(event)
        
        # Update effectiveness cache
        await self._update_effectiveness_cache()
    
    async def _update_effectiveness_cache(self) -> None:
        """Update the effectiveness cache based on recent events."""
        # Calculate effectiveness for each rule/type combination
        # This is a simplified implementation
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        # Get hint events from the last 30 days
        events = await self.event_store.get_events_in_range(
            start_time=start_time,
            end_time=end_time,
            event_types=["hint_generated", "hint_accepted", "hint_dismissed"]
        )
        
        # Group by rule and type
        stats: Dict[str, Dict[str, int]] = {}
        
        for event in events:
            if event.event_type == "hint_generated":
                key = f"{event.source_rule}:{event.hint_type}"
                if key not in stats:
                    stats[key] = {"generated": 0, "accepted": 0, "dismissed": 0}
                stats[key]["generated"] += 1
            
            elif event.event_type == "hint_accepted":
                # Would need to look up the original hint to get rule/type
                # For now, skip
                pass
            
            elif event.event_type == "hint_dismissed":
                # Would need to look up the original hint to get rule/type
                # For now, skip
                pass
        
        # Calculate effectiveness scores
        for key, counts in stats.items():
            total = counts["generated"]
            if total > 0:
                effectiveness = counts["accepted"] / total
                self._effectiveness_cache[key] = effectiveness
    
    def add_rule(self, rule: HintRule) -> None:
        """Add a custom hint generation rule."""
        self.rules.append(rule)
        logger.info(f"Added hint rule: {rule.rule_name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a hint generation rule by name."""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_name != rule_name]
        removed = len(self.rules) < original_count
        
        if removed:
            logger.info(f"Removed hint rule: {rule_name}")
        
        return removed
    
    def get_rules(self) -> List[str]:
        """Get list of active rule names."""
        return [rule.rule_name for rule in self.rules]