"""
Event handlers for workflow hint events in the Vision System.

This module processes hint-related events, updates statistics,
and triggers follow-up actions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from datetime import datetime, timedelta
from collections import defaultdict
from uuid import UUID

from ...domain.events.hint_events import (
    HintGenerated, HintAccepted, HintDismissed,
    HintFeedbackProvided, HintEffectivenessCalculated,
    HintPatternDetected
)
from ...domain.events.base import DomainEvent
from ...domain.interfaces.event_store import EventStore


logger = logging.getLogger(__name__)


class HintEventHandlers:
    """
    Handles hint-related domain events.
    
    Processes events to maintain statistics, update effectiveness scores,
    and trigger pattern detection.
    """
    
    def __init__(
        self,
        event_store: EventStore,
        hint_repository: Optional[Any] = None
    ):
        self.event_store = event_store
        self.hint_repository = hint_repository
        
        # Statistics tracking
        self.hint_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"generated": 0, "accepted": 0, "dismissed": 0, "feedback": 0}
        )
        
        # Pattern detection thresholds
        self.pattern_thresholds = {
            "min_hints_for_pattern": 10,
            "acceptance_threshold": 0.7,
            "dismissal_threshold": 0.5
        }
    
    async def handle_hint_generated(self, event: HintGenerated) -> None:
        """
        Handle hint generated event.
        
        Updates statistics and checks for emerging patterns.
        """
        logger.info(
            f"Hint generated: {event.hint_id} for task {event.task_id} "
            f"(type: {event.hint_type}, rule: {event.source_rule})"
        )
        
        # Update statistics
        stat_key = f"{event.source_rule}:{event.hint_type}"
        self.hint_stats[stat_key]["generated"] += 1
        
        # Store hint if repository available
        if self.hint_repository:
            await self.hint_repository.store_generated_hint(event)
        
        # Check if we should calculate effectiveness
        if self.hint_stats[stat_key]["generated"] % 50 == 0:
            await self._calculate_and_publish_effectiveness(
                event.source_rule,
                event.hint_type
            )
    
    async def handle_hint_accepted(self, event: HintAccepted) -> None:
        """
        Handle hint accepted event.
        
        Updates acceptance statistics and learns from positive feedback.
        """
        logger.info(
            f"Hint accepted: {event.hint_id} by user {event.user_id}"
        )
        
        # Get original hint details
        hint_details = await self._get_hint_details(event.hint_id)
        if hint_details:
            stat_key = f"{hint_details['source_rule']}:{hint_details['hint_type']}"
            self.hint_stats[stat_key]["accepted"] += 1
            
            # Check for positive patterns
            await self._check_acceptance_patterns(hint_details)
        
        # Store acceptance if repository available
        if self.hint_repository:
            await self.hint_repository.store_hint_acceptance(event)
    
    async def handle_hint_dismissed(self, event: HintDismissed) -> None:
        """
        Handle hint dismissed event.
        
        Updates dismissal statistics and learns from negative feedback.
        """
        logger.info(
            f"Hint dismissed: {event.hint_id} by user {event.user_id} "
            f"(reason: {event.reason})"
        )
        
        # Get original hint details
        hint_details = await self._get_hint_details(event.hint_id)
        if hint_details:
            stat_key = f"{hint_details['source_rule']}:{hint_details['hint_type']}"
            self.hint_stats[stat_key]["dismissed"] += 1
            
            # Check for negative patterns
            await self._check_dismissal_patterns(hint_details, event.reason)
        
        # Store dismissal if repository available
        if self.hint_repository:
            await self.hint_repository.store_hint_dismissal(event)
    
    async def handle_hint_feedback(self, event: HintFeedbackProvided) -> None:
        """
        Handle hint feedback event.
        
        Processes detailed feedback to improve hint generation.
        """
        logger.info(
            f"Feedback provided for hint {event.hint_id}: "
            f"helpful={event.was_helpful}, score={event.effectiveness_score}"
        )
        
        # Get original hint details
        hint_details = await self._get_hint_details(event.hint_id)
        if hint_details:
            stat_key = f"{hint_details['source_rule']}:{hint_details['hint_type']}"
            self.hint_stats[stat_key]["feedback"] += 1
        
        # Store feedback if repository available
        if self.hint_repository:
            await self.hint_repository.store_hint_feedback(event)
        
        # Process improvement suggestions
        if event.improvement_suggestions:
            await self._process_improvement_suggestions(
                event.hint_id,
                event.improvement_suggestions
            )
    
    async def handle_pattern_detected(self, event: HintPatternDetected) -> None:
        """
        Handle pattern detected event.
        
        Stores new patterns for future hint generation.
        """
        logger.info(
            f"Pattern detected: {event.pattern_name} "
            f"(confidence: {event.confidence})"
        )
        
        # Store pattern if repository available
        if self.hint_repository:
            await self.hint_repository.store_detected_pattern(event)
        
        # Update hint generation rules if confidence is high
        if event.confidence > 0.8 and event.suggested_rule:
            logger.info(
                f"High confidence pattern suggests new rule: "
                f"{event.suggested_rule}"
            )
    
    async def handle_effectiveness_calculated(
        self,
        event: HintEffectivenessCalculated
    ) -> None:
        """
        Handle effectiveness calculated event.
        
        Updates effectiveness scores for hint types and rules.
        """
        logger.info(
            f"Effectiveness calculated for {event.source_rule}:{event.hint_type}: "
            f"{event.effectiveness_score:.2f} "
            f"(accepted: {event.accepted_count}/{event.total_hints})"
        )
        
        # Store effectiveness if repository available
        if self.hint_repository:
            await self.hint_repository.store_effectiveness_score(event)
    
    async def _get_hint_details(self, hint_id: UUID) -> Optional[Dict[str, Any]]:
        """Get details of a hint from events or repository."""
        # Try repository first
        if self.hint_repository:
            hint = await self.hint_repository.get(hint_id)
            if hint:
                return {
                    "hint_id": hint.id,
                    "source_rule": hint.metadata.source,
                    "hint_type": hint.type.value,
                    "priority": hint.priority.value,
                    "task_id": hint.task_id
                }
        
        # Fallback to searching events
        events = await self.event_store.get_events_by_aggregate(
            aggregate_id=hint_id,
            event_types=["hint_generated"]
        )
        
        if events:
            event = events[0]
            return {
                "hint_id": hint_id,
                "source_rule": event.source_rule,
                "hint_type": event.hint_type,
                "priority": event.priority,
                "task_id": event.task_id
            }
        
        return None
    
    async def _calculate_and_publish_effectiveness(
        self,
        source_rule: str,
        hint_type: str
    ) -> None:
        """Calculate and publish effectiveness for a rule/type combination."""
        stat_key = f"{source_rule}:{hint_type}"
        stats = self.hint_stats[stat_key]
        
        total = stats["generated"]
        if total == 0:
            return
        
        accepted = stats["accepted"]
        dismissed = stats["dismissed"]
        
        # Simple effectiveness calculation
        # Could be enhanced with weighted scoring
        effectiveness = accepted / total if total > 0 else 0
        
        # Create and publish event
        event = HintEffectivenessCalculated(
            aggregate_id=UUID(int=0),  # System event
            occurred_at=datetime.now(timezone.utc),
            user_id="hint_event_handler",
            hint_type=hint_type,
            source_rule=source_rule,
            total_hints=total,
            accepted_count=accepted,
            dismissed_count=dismissed,
            effectiveness_score=effectiveness,
            period_start=datetime.now(timezone.utc) - timedelta(days=30),
            period_end=datetime.now(timezone.utc)
        )
        
        await self.event_store.append(event)
        await self.handle_effectiveness_calculated(event)
    
    async def _check_acceptance_patterns(
        self,
        hint_details: Dict[str, Any]
    ) -> None:
        """Check for patterns in accepted hints."""
        stat_key = f"{hint_details['source_rule']}:{hint_details['hint_type']}"
        stats = self.hint_stats[stat_key]
        
        # Check if we have enough data
        if stats["generated"] < self.pattern_thresholds["min_hints_for_pattern"]:
            return
        
        acceptance_rate = stats["accepted"] / stats["generated"]
        
        # High acceptance rate indicates good pattern
        if acceptance_rate > self.pattern_thresholds["acceptance_threshold"]:
            pattern_event = HintPatternDetected(
                aggregate_id=UUID(int=0),
                occurred_at=datetime.now(timezone.utc),
                user_id="hint_event_handler",
                pattern_id=UUID(int=hash(stat_key) & 0xFFFFFFFF),
                pattern_name=f"high_acceptance_{hint_details['source_rule']}",
                pattern_description=f"High acceptance rate for {hint_details['hint_type']} hints from {hint_details['source_rule']}",
                confidence=min(acceptance_rate, 0.95),
                affected_tasks=[],
                suggested_rule={
                    "action": "increase_priority",
                    "rule": hint_details['source_rule'],
                    "type": hint_details['hint_type']
                }
            )
            
            await self.event_store.append(pattern_event)
            await self.handle_pattern_detected(pattern_event)
    
    async def _check_dismissal_patterns(
        self,
        hint_details: Dict[str, Any],
        reason: Optional[str]
    ) -> None:
        """Check for patterns in dismissed hints."""
        stat_key = f"{hint_details['source_rule']}:{hint_details['hint_type']}"
        stats = self.hint_stats[stat_key]
        
        # Check if we have enough data
        if stats["generated"] < self.pattern_thresholds["min_hints_for_pattern"]:
            return
        
        dismissal_rate = stats["dismissed"] / stats["generated"]
        
        # High dismissal rate indicates poor pattern
        if dismissal_rate > self.pattern_thresholds["dismissal_threshold"]:
            pattern_event = HintPatternDetected(
                aggregate_id=UUID(int=0),
                occurred_at=datetime.now(timezone.utc),
                user_id="hint_event_handler",
                pattern_id=UUID(int=hash(stat_key + "_dismissed") & 0xFFFFFFFF),
                pattern_name=f"high_dismissal_{hint_details['source_rule']}",
                pattern_description=f"High dismissal rate for {hint_details['hint_type']} hints from {hint_details['source_rule']}",
                confidence=min(dismissal_rate, 0.95),
                affected_tasks=[],
                suggested_rule={
                    "action": "decrease_priority",
                    "rule": hint_details['source_rule'],
                    "type": hint_details['hint_type'],
                    "common_reason": reason
                }
            )
            
            await self.event_store.append(pattern_event)
            await self.handle_pattern_detected(pattern_event)
    
    async def _process_improvement_suggestions(
        self,
        hint_id: UUID,
        suggestions: str
    ) -> None:
        """Process improvement suggestions from feedback."""
        logger.info(
            f"Processing improvement suggestions for hint {hint_id}: "
            f"{suggestions[:100]}..."
        )
        
        # In a real implementation, this could:
        # 1. Parse suggestions using NLP
        # 2. Identify actionable improvements
        # 3. Update hint generation rules
        # 4. Create tickets for manual review
        
        # For now, just log for manual review
        if self.hint_repository:
            await self.hint_repository.store_improvement_suggestion(
                hint_id,
                suggestions
            )
    
    async def get_hint_statistics(self) -> Dict[str, Any]:
        """Get current hint statistics."""
        return {
            "statistics": dict(self.hint_stats),
            "summary": {
                "total_generated": sum(s["generated"] for s in self.hint_stats.values()),
                "total_accepted": sum(s["accepted"] for s in self.hint_stats.values()),
                "total_dismissed": sum(s["dismissed"] for s in self.hint_stats.values()),
                "total_feedback": sum(s["feedback"] for s in self.hint_stats.values()),
                "overall_acceptance_rate": (
                    sum(s["accepted"] for s in self.hint_stats.values()) /
                    max(sum(s["generated"] for s in self.hint_stats.values()), 1)
                )
            }
        }
    
    async def process_event(self, event: DomainEvent) -> None:
        """
        Process a domain event.
        
        Routes events to appropriate handlers.
        """
        handlers = {
            "hint_generated": self.handle_hint_generated,
            "hint_accepted": self.handle_hint_accepted,
            "hint_dismissed": self.handle_hint_dismissed,
            "hint_feedback_provided": self.handle_hint_feedback,
            "hint_pattern_detected": self.handle_pattern_detected,
            "hint_effectiveness_calculated": self.handle_effectiveness_calculated
        }
        
        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"No handler for event type: {event.event_type}")