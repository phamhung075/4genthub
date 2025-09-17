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

    pass  # All functionality inherited from HintManager