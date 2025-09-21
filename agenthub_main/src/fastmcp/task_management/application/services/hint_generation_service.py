"""
DEPRECATED: Hint generation service for the Vision System.

This module has been consolidated into hint_manager.py as part of Phase 3.1.
This file now provides backward compatibility by importing from the new HintManager.

For new code, use:
    from .hint_manager import HintManager, create_hint_manager

This service coordinates hint generation using various rules,
manages hint lifecycle, and integrates with the event system.
"""

import logging
from typing import List, Optional, Dict, Any, Type
from uuid import UUID
from datetime import datetime, timezone
from datetime import datetime, timedelta

from ...domain.value_objects.hints import (
    WorkflowHint, HintCollection, HintType, HintPriority, HintMetadata
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


# Backward compatibility import
from .hint_manager import HintManager as _HintManager, HintStrategy

class HintGenerationService(_HintManager):
    """
    DEPRECATED: Service for generating intelligent workflow hints.

    This class now inherits from the consolidated HintManager for backward compatibility.
    For new code, use HintManager directly.

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
        # Call parent HintManager with domain strategy for backward compatibility
        super().__init__(
            task_repository=task_repository,
            context_repository=context_repository,
            strategy=HintStrategy.DOMAIN,
            event_store=event_store,
            hint_repository=hint_repository
        )

        # Expose legacy attributes for backward compatibility
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_store = event_store
        self.hint_repository = hint_repository
        self.rules = self.strategy.rules if hasattr(self.strategy, 'rules') else []
        self._effectiveness_cache = self.strategy._effectiveness_cache if hasattr(self.strategy, '_effectiveness_cache') else {}
    # All methods are now inherited from HintManager
    # The following methods are available and work as before:
    # - generate_hints_for_task()
    # - accept_hint()
    # - dismiss_hint()
    # - provide_feedback()
    # - add_rule()
    # - remove_rule()
    # - get_rules()

    # === BACKWARD COMPATIBILITY METHODS FOR TESTS ===
    # These methods delegate to the strategy for backward compatibility with existing tests

    async def _get_related_tasks(self, task: Task, task_repository: TaskRepository = None) -> List[Task]:
        """Get tasks related to the given task - delegates to strategy"""
        if hasattr(self.strategy, '_get_related_tasks'):
            return await self.strategy._get_related_tasks(task, task_repository or self.task_repository)
        return []

    async def _get_historical_patterns(self, task: Task, task_repository: TaskRepository = None) -> Dict[str, Any]:
        """Get historical patterns relevant to the task - delegates to strategy"""
        if hasattr(self.strategy, '_get_historical_patterns'):
            return await self.strategy._get_historical_patterns(task, task_repository or self.task_repository)
        return {}

    def _should_include_hint(self, hint: WorkflowHint, hint_types: Optional[List[HintType]]) -> bool:
        """Check if a hint should be included based on filters - delegates to strategy"""
        if hasattr(self.strategy, '_should_include_hint'):
            return self.strategy._should_include_hint(hint, hint_types)
        return True

    def _enhance_hint_with_effectiveness(self, hint: WorkflowHint, rule: HintRule) -> WorkflowHint:
        """Enhance hint with historical effectiveness data - delegates to strategy"""
        if hasattr(self.strategy, '_enhance_hint_with_effectiveness'):
            return self.strategy._enhance_hint_with_effectiveness(hint, rule)
        return hint

    async def _publish_hint_generated(self, hint: WorkflowHint, rule: HintRule, event_store: Any = None) -> None:
        """Publish a hint generated event - delegates to strategy"""
        if hasattr(self.strategy, '_publish_hint_generated'):
            await self.strategy._publish_hint_generated(hint, rule, event_store or self.event_store)

    async def _store_hints(self, collection: HintCollection) -> None:
        """Store hints in repository - backward compatibility method"""
        if self.hint_repository is not None:
            for hint in collection.hints:
                # Store each hint individually - prioritize save method for test compatibility
                if hasattr(self.hint_repository, 'save'):
                    await self.hint_repository.save(hint)
                elif hasattr(self.hint_repository, 'store'):
                    await self.hint_repository.store(hint)

    async def _update_effectiveness_cache(self) -> None:
        """Update effectiveness cache - backward compatibility method"""
        # This is a placeholder for backward compatibility with tests
        # In the new architecture, effectiveness is managed by the strategy
        pass

    async def _get_hint_effectiveness_patterns(self) -> Dict[str, float]:
        """Get hint effectiveness patterns - backward compatibility method"""
        if hasattr(self.strategy, '_effectiveness_cache'):
            return dict(self.strategy._effectiveness_cache)
        return {}

    # === OVERRIDE METHODS FOR BACKWARD COMPATIBILITY ===
    # Override parent methods to include effectiveness cache updates for test compatibility

    async def accept_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        action_taken: Optional[str] = None
    ) -> None:
        """Record that a hint was accepted with effectiveness cache update"""
        # Call parent implementation
        await super().accept_hint(hint_id, task_id, user_id, action_taken)
        # Update effectiveness cache for test compatibility
        await self._update_effectiveness_cache()

    async def dismiss_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        reason: Optional[str] = None
    ) -> None:
        """Record that a hint was dismissed with effectiveness cache update"""
        # Call parent implementation
        await super().dismiss_hint(hint_id, task_id, user_id, reason)
        # Update effectiveness cache for test compatibility
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
        """Record feedback for a hint with effectiveness cache update"""
        # Call parent implementation
        await super().provide_feedback(hint_id, task_id, user_id, was_helpful, feedback_text, effectiveness_score)
        # Update effectiveness cache for test compatibility
        await self._update_effectiveness_cache()