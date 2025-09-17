"""Consolidated Hint Manager - Phase 3.1 Factory Pattern Implementation

This module consolidates the three hint-related services into a unified HintManager
using the factory pattern established in Phase 2.1. It provides a single interface
for all hint operations while maintaining backward compatibility.

Consolidated Services:
- HintGenerationService: Domain-level hint generation with rules
- WorkflowHintsSimplifier: AI optimization with legacy support
- HintOptimizer: Ultra-fast flat hints with 70% size reduction

Factory Pattern Features:
- Strategy-based hint generation (domain, simplified, optimized)
- Environment-driven configuration
- Backward compatibility preservation
- Performance metrics aggregation
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union, Type
from uuid import UUID
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass

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
from ...infrastructure.event_store import EventStore


logger = logging.getLogger(__name__)


class HintStrategy(Enum):
    """Hint generation strategies available"""
    DOMAIN = "domain"           # Full domain-level hint generation
    SIMPLIFIED = "simplified"   # AI-optimized with legacy support
    OPTIMIZED = "optimized"     # Ultra-fast flat hints structure
    AUTO = "auto"              # Automatic strategy selection


@dataclass
class HintConfig:
    """Configuration for hint generation"""
    strategy: HintStrategy
    max_hints: int = 5
    max_required: int = 3
    max_tips: int = 2
    enable_ultra_hints: bool = True
    enable_metrics: bool = True
    cache_effectiveness: bool = True


class HintStrategyFactory:
    """Factory for creating hint generation strategies"""

    @staticmethod
    def create_strategy(strategy: HintStrategy, config: HintConfig) -> 'BaseHintStrategy':
        """Create a hint strategy instance"""
        if strategy == HintStrategy.DOMAIN:
            return DomainHintStrategy(config)
        elif strategy == HintStrategy.SIMPLIFIED:
            return SimplifiedHintStrategy(config)
        elif strategy == HintStrategy.OPTIMIZED:
            return OptimizedHintStrategy(config)
        elif strategy == HintStrategy.AUTO:
            return AutoHintStrategy(config)
        else:
            raise ValueError(f"Unknown hint strategy: {strategy}")


class BaseHintStrategy:
    """Base class for hint generation strategies"""

    def __init__(self, config: HintConfig):
        self.config = config
        self.metrics = {
            'hints_processed': 0,
            'processing_time_ms': 0,
            'complexity_reduced': 0,
            'words_saved': 0
        }

    async def generate_hints_for_task(
        self,
        task_id: UUID,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[EventStore] = None,
        hint_types: Optional[List[HintType]] = None
    ) -> HintCollection:
        """Generate hints for a task - implemented by subclasses"""
        raise NotImplementedError

    def simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify workflow guidance - implemented by subclasses"""
        raise NotImplementedError

    def get_metrics(self) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset strategy metrics"""
        self.metrics = {
            'hints_processed': 0,
            'processing_time_ms': 0,
            'complexity_reduced': 0,
            'words_saved': 0
        }


class DomainHintStrategy(BaseHintStrategy):
    """Domain-level hint generation strategy (from HintGenerationService)"""

    def __init__(self, config: HintConfig):
        super().__init__(config)
        self.rules: List[HintRule] = self._initialize_default_rules()
        self._effectiveness_cache: Dict[str, float] = {}

    def _initialize_default_rules(self) -> List[HintRule]:
        """Initialize the default set of hint generation rules"""
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
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[EventStore] = None,
        hint_types: Optional[List[HintType]] = None
    ) -> HintCollection:
        """Generate workflow hints using domain rules"""
        import time
        start_time = time.perf_counter()

        # Fetch task and context
        task = await task_repository.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return HintCollection(task_id=task_id)

        context = None
        try:
            context = await context_repository.get_by_task_id(task_id)
        except Exception as e:
            logger.debug(f"No context found for task {task_id}: {e}")

        # Get related tasks for pattern analysis
        related_tasks = await self._get_related_tasks(task, task_repository)

        # Create rule context
        rule_context = RuleContext(
            task=task,
            context=context,
            related_tasks=related_tasks,
            historical_patterns=await self._get_historical_patterns(task, task_repository)
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
                    if event_store:
                        await self._publish_hint_generated(hint, rule, event_store)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_name}: {e}")

        # Create and return hint collection
        collection = HintCollection(task_id=task_id, hints=hints)

        # Sort and limit hints
        top_hints = collection.get_top_hints(limit=self.config.max_hints)
        collection.hints = top_hints

        # Update metrics
        processing_time = (time.perf_counter() - start_time) * 1000
        self.metrics['hints_processed'] += 1
        self.metrics['processing_time_ms'] += processing_time

        return collection

    def simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Simple pass-through for domain strategy - no simplification"""
        return guidance

    async def _get_related_tasks(self, task: Task, task_repository: TaskRepository) -> List[Task]:
        """Get tasks related to the given task"""
        related = []

        # Get tasks with same labels
        if hasattr(task, 'labels') and task.labels:
            for label in task.labels[:2]:  # Limit to avoid too many queries
                tasks = await task_repository.list(labels=[label], limit=5)
                related.extend(tasks)

        # Get subtasks if any
        if hasattr(task, 'subtasks') and task.subtasks:
            for subtask_id in task.subtasks[:5]:
                subtask = await task_repository.get(subtask_id)
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

    async def _get_historical_patterns(self, task: Task, task_repository: TaskRepository) -> Dict[str, Any]:
        """Get historical patterns relevant to the task"""
        patterns = {}

        # Get patterns from similar completed tasks
        if hasattr(task, 'labels') and task.labels:
            completed_similar = await task_repository.list(
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

        return patterns

    def _should_include_hint(
        self,
        hint: WorkflowHint,
        hint_types: Optional[List[HintType]]
    ) -> bool:
        """Check if a hint should be included based on filters"""
        if hint_types is None:
            return True
        return hint.type in hint_types

    def _enhance_hint_with_effectiveness(
        self,
        hint: WorkflowHint,
        rule: HintRule
    ) -> WorkflowHint:
        """Enhance hint with historical effectiveness data"""
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
        rule: HintRule,
        event_store: EventStore
    ) -> None:
        """Publish a hint generated event"""
        event = HintGenerated(
            aggregate_id=hint.task_id,
            occurred_at=datetime.now(timezone.utc),
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
        await event_store.append(event)


class SimplifiedHintStrategy(BaseHintStrategy):
    """Simplified hint generation strategy (from WorkflowHintsSimplifier)"""

    def __init__(self, config: HintConfig):
        super().__init__(config)

        # Try to import and use HintOptimizer if available
        self.ultra_hints_enabled = (
            config.enable_ultra_hints and
            os.getenv('ENABLE_ULTRA_HINTS', 'true').lower() in ['true', '1', 'yes', 'on']
        )

        self.hint_optimizer = None
        if self.ultra_hints_enabled:
            try:
                from .hint_optimizer import HintOptimizer
                self.hint_optimizer = HintOptimizer()
                logger.info("Phase 3 Ultra-Hints optimization is ENABLED in SimplifiedHintStrategy")
            except ImportError:
                logger.warning("HintOptimizer not available, using legacy simplification")
                self.hint_optimizer = None

        # Action verb mapping for conciseness
        self.ACTION_VERBS = {
            "you should": "",
            "please": "",
            "it is recommended to": "",
            "consider": "",
            "you might want to": "",
            "it would be good to": "",
            "you may": "",
            "create a new": "create",
            "update the existing": "update",
            "delete the": "delete",
            "add a": "add",
            "remove the": "remove",
            "check if": "verify",
            "make sure": "ensure",
            "take a look at": "review",
            "go ahead and": "",
        }

    async def generate_hints_for_task(
        self,
        task_id: UUID,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[EventStore] = None,
        hint_types: Optional[List[HintType]] = None
    ) -> HintCollection:
        """Generate simplified hints - delegates to domain strategy first"""
        # Use domain strategy to generate base hints
        domain_strategy = DomainHintStrategy(self.config)
        collection = await domain_strategy.generate_hints_for_task(
            task_id, task_repository, context_repository, event_store, hint_types
        )

        # Apply simplification to each hint
        simplified_hints = []
        for hint in collection.hints:
            simplified_message = self._simplify_text(hint.message)
            simplified_action = self._simplify_text(hint.suggested_action)

            # Create new simplified hint
            simplified_hint = WorkflowHint(
                id=hint.id,
                type=hint.type,
                priority=hint.priority,
                message=simplified_message,
                suggested_action=simplified_action,
                metadata=hint.metadata,
                created_at=hint.created_at,
                task_id=hint.task_id,
                context_data=hint.context_data,
                expires_at=hint.expires_at
            )
            simplified_hints.append(simplified_hint)

        collection.hints = simplified_hints
        self.metrics['hints_processed'] += len(simplified_hints)

        return collection

    def simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify complete workflow guidance structure"""
        if not guidance:
            return {}

        # Use HintOptimizer for ultra-flat structure if enabled
        if self.ultra_hints_enabled and self.hint_optimizer:
            try:
                ultra_result = self.hint_optimizer.optimize_workflow_hints(guidance)

                # Merge performance metrics
                hint_metrics = self.hint_optimizer.get_performance_metrics()
                if hint_metrics["hints_processed"] > 0:
                    self.metrics["hints_processed"] += hint_metrics["hints_processed"]
                    self.metrics["complexity_reduced"] += hint_metrics["total_bytes_saved"]

                logger.debug(
                    f"Ultra-hints optimization: {hint_metrics['average_reduction_percent']:.1f}% "
                    f"reduction, {hint_metrics['estimated_ai_speedup_percent']:.1f}% faster AI processing"
                )

                return ultra_result

            except Exception as e:
                logger.warning(f"HintOptimizer failed, falling back to legacy: {e}")
                # Fall through to legacy processing

        # Legacy simplification process
        simplified = {}

        # Process next steps
        if "next_steps" in guidance:
            simplified["next"] = self._simplify_next_steps(guidance["next_steps"])

        # Process autonomous guidance
        if "autonomous_guidance" in guidance:
            autonomous = guidance["autonomous_guidance"]
            if isinstance(autonomous, dict):
                if "confidence" in autonomous:
                    simplified["confidence"] = autonomous["confidence"]

                if "recommendations" in autonomous:
                    simplified["recommendations"] = self._extract_key_points(
                        autonomous["recommendations"]
                    )

        # Process validation requirements
        if "validation" in guidance:
            simplified["validation"] = self._simplify_validation(guidance["validation"])

        # Process dependencies
        if "dependencies" in guidance:
            simplified["dependencies"] = self._simplify_dependencies(guidance["dependencies"])

        # Extract performance hints
        if "performance_hints" in guidance:
            simplified["performance"] = self._simplify_performance_hints(
                guidance["performance_hints"]
            )

        # Update metrics
        original_size = len(str(guidance))
        simplified_size = len(str(simplified))
        self.metrics["complexity_reduced"] += max(0, original_size - simplified_size)
        self.metrics["hints_processed"] += 1

        return simplified

    def _simplify_text(self, text: str) -> str:
        """Simplify text by removing verbose phrases and words"""
        if not text or not isinstance(text, str):
            return text

        original_length = len(text.split())

        # Convert to lowercase for processing
        simplified = text.lower().strip()

        # Remove verbose phrases
        for verbose, replacement in self.ACTION_VERBS.items():
            import re
            simplified = re.sub(r'\b' + re.escape(verbose) + r'\b', replacement, simplified)

        # Remove extra whitespace
        simplified = re.sub(r'\s+', ' ', simplified).strip()

        # Capitalize first letter
        if simplified:
            simplified = simplified[0].upper() + simplified[1:]

        # Track word savings
        final_length = len(simplified.split())
        self.metrics["words_saved"] += max(0, original_length - final_length)

        return simplified

    def _simplify_next_steps(self, next_steps: Any) -> Any:
        """Simplify next steps structure"""
        if isinstance(next_steps, dict):
            result = {}

            if "recommendations" in next_steps:
                recommendations = next_steps["recommendations"]
                if isinstance(recommendations, list):
                    simplified_recs = []
                    for rec in recommendations[:3]:
                        simplified_recs.append(self._simplify_text(str(rec)))
                    result["actions"] = simplified_recs
                elif isinstance(recommendations, str):
                    result["action"] = self._simplify_text(recommendations)

            if "required_actions" in next_steps:
                required = next_steps["required_actions"]
                if isinstance(required, list):
                    result["required"] = [self._simplify_text(str(action)) for action in required[:3]]
                elif isinstance(required, str):
                    result["required"] = self._simplify_text(required)

            if "context" in next_steps:
                result["context"] = self._extract_key_context(next_steps["context"])

            return result

        elif isinstance(next_steps, list):
            return [self._simplify_text(str(step)) for step in next_steps[:3]]

        elif isinstance(next_steps, str):
            return self._simplify_text(next_steps)

        return next_steps

    def _simplify_validation(self, validation: Any) -> Dict[str, Any]:
        """Simplify validation requirements"""
        if not validation:
            return {}

        result = {}

        if isinstance(validation, dict):
            if "required_fields" in validation:
                result["required"] = validation["required_fields"]

            if "rules" in validation:
                rules = validation["rules"]
                if isinstance(rules, list):
                    result["rules"] = [self._simplify_text(str(rule)) for rule in rules[:3]]
                elif isinstance(rules, str):
                    result["rule"] = self._simplify_text(rules)

            if "constraints" in validation:
                result["constraints"] = self._extract_key_points(validation["constraints"])

        elif isinstance(validation, list):
            result["rules"] = [self._simplify_text(str(rule)) for rule in validation[:3]]

        return result

    def _simplify_dependencies(self, dependencies: Any) -> Any:
        """Simplify dependency information"""
        if isinstance(dependencies, dict):
            result = {}

            if "required" in dependencies:
                result["required"] = self._extract_ids_or_names(dependencies["required"])

            if "optional" in dependencies:
                result["optional"] = self._extract_ids_or_names(dependencies["optional"])

            if "blocked_by" in dependencies:
                result["blocked_by"] = self._extract_ids_or_names(dependencies["blocked_by"])

            return result

        elif isinstance(dependencies, list):
            return self._extract_ids_or_names(dependencies)

        return dependencies

    def _simplify_performance_hints(self, hints: Any) -> Dict[str, Any]:
        """Simplify performance optimization hints"""
        if not hints:
            return {}

        result = {}

        if isinstance(hints, dict):
            if "caching" in hints:
                result["cache"] = self._simplify_text(str(hints["caching"]))

            if "query_optimization" in hints:
                result["query"] = self._simplify_text(str(hints["query_optimization"]))

            if "field_selection" in hints:
                result["fields"] = hints["field_selection"]

            if "batching" in hints:
                result["batch"] = self._simplify_text(str(hints["batching"]))

        return result

    def _extract_key_points(self, data: Any, max_points: int = 3) -> List[str]:
        """Extract key points from complex data"""
        if isinstance(data, list):
            return [self._simplify_text(str(item)) for item in data[:max_points]]
        elif isinstance(data, dict):
            points = []
            for key, value in list(data.items())[:max_points]:
                if isinstance(value, str):
                    points.append(f"{key}: {self._simplify_text(value)}")
                else:
                    points.append(f"{key}: {str(value)}")
            return points
        elif isinstance(data, str):
            return [self._simplify_text(data)]
        else:
            return [str(data)]

    def _extract_key_context(self, context: Any) -> str:
        """Extract key context information"""
        if isinstance(context, dict):
            priority_keys = ["when", "if", "after", "before", "requires"]
            for key in priority_keys:
                if key in context:
                    return f"{key} {self._simplify_text(str(context[key]))}"

            if context:
                first_key = next(iter(context))
                return f"{first_key}: {self._simplify_text(str(context[first_key]))}"

        elif isinstance(context, str):
            return self._simplify_text(context)

        return str(context)

    def _extract_ids_or_names(self, data: Any) -> List[str]:
        """Extract IDs or names from complex dependency data"""
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, dict):
                    if "id" in item:
                        result.append(item["id"])
                    elif "name" in item:
                        result.append(item["name"])
                    elif "title" in item:
                        result.append(item["title"])
                    else:
                        result.append(str(item))
                else:
                    result.append(str(item))
            return result
        elif isinstance(data, dict):
            if "id" in data:
                return [data["id"]]
            elif "name" in data:
                return [data["name"]]
            elif "items" in data:
                return self._extract_ids_or_names(data["items"])

        return [str(data)]


class OptimizedHintStrategy(BaseHintStrategy):
    """Optimized hint generation strategy (from HintOptimizer)"""

    def __init__(self, config: HintConfig):
        super().__init__(config)

        # Import HintOptimizer
        try:
            from .hint_optimizer import HintOptimizer
            self.optimizer = HintOptimizer()
        except ImportError:
            logger.error("HintOptimizer not available for OptimizedHintStrategy")
            raise

    async def generate_hints_for_task(
        self,
        task_id: UUID,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[EventStore] = None,
        hint_types: Optional[List[HintType]] = None
    ) -> HintCollection:
        """Generate optimized flat hints - converts domain hints to flat structure"""
        # Use domain strategy to generate base hints
        domain_strategy = DomainHintStrategy(self.config)
        collection = await domain_strategy.generate_hints_for_task(
            task_id, task_repository, context_repository, event_store, hint_types
        )

        # Convert hints to flat structure using optimizer
        if collection.hints:
            # Create guidance structure from hints
            guidance = {
                "next_steps": {
                    "recommendations": [hint.message for hint in collection.hints[:3]],
                    "required_actions": [hint.suggested_action for hint in collection.hints if hint.priority == HintPriority.CRITICAL]
                },
                "confidence": 0.8  # Default confidence
            }

            # Optimize using HintOptimizer
            optimized = self.optimizer.optimize_workflow_hints(guidance)

            # Update metrics from optimizer
            optimizer_metrics = self.optimizer.get_performance_metrics()
            self.metrics.update({
                'hints_processed': optimizer_metrics['hints_processed'],
                'processing_time_ms': optimizer_metrics.get('average_processing_time_ms', 0),
                'complexity_reduced': optimizer_metrics['total_bytes_saved']
            })

        return collection

    def simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize workflow guidance to ultra-flat structure"""
        return self.optimizer.optimize_workflow_hints(
            guidance,
            max_required=self.config.max_required,
            max_tips=self.config.max_tips
        )


class AutoHintStrategy(BaseHintStrategy):
    """Automatic strategy selection based on context and environment"""

    def __init__(self, config: HintConfig):
        super().__init__(config)
        self._current_strategy: Optional[BaseHintStrategy] = None

    def _select_strategy(self, context: Optional[Dict[str, Any]] = None) -> BaseHintStrategy:
        """Select the best strategy based on context and environment"""

        # Check environment variables
        strategy_env = os.getenv('HINT_STRATEGY', 'simplified').lower()
        ultra_hints = os.getenv('ENABLE_ULTRA_HINTS', 'true').lower() in ['true', '1', 'yes', 'on']

        # Strategy selection logic
        if strategy_env == 'domain':
            strategy = HintStrategy.DOMAIN
        elif strategy_env == 'optimized' or (ultra_hints and strategy_env != 'domain'):
            strategy = HintStrategy.OPTIMIZED
        else:
            strategy = HintStrategy.SIMPLIFIED

        # Create and cache strategy
        if self._current_strategy is None or type(self._current_strategy).__name__ != f"{strategy.value.title()}HintStrategy":
            self._current_strategy = HintStrategyFactory.create_strategy(strategy, self.config)

        return self._current_strategy

    async def generate_hints_for_task(
        self,
        task_id: UUID,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        event_store: Optional[EventStore] = None,
        hint_types: Optional[List[HintType]] = None
    ) -> HintCollection:
        """Generate hints using automatically selected strategy"""
        strategy = self._select_strategy()
        result = await strategy.generate_hints_for_task(
            task_id, task_repository, context_repository, event_store, hint_types
        )

        # Aggregate metrics
        strategy_metrics = strategy.get_metrics()
        for key, value in strategy_metrics.items():
            self.metrics[key] = self.metrics.get(key, 0) + value

        return result

    def simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify using automatically selected strategy"""
        strategy = self._select_strategy(guidance)
        result = strategy.simplify_workflow_guidance(guidance)

        # Aggregate metrics
        strategy_metrics = strategy.get_metrics()
        for key, value in strategy_metrics.items():
            self.metrics[key] = self.metrics.get(key, 0) + value

        return result


class HintManager:
    """
    Consolidated Hint Manager - Phase 3.1 Implementation

    This class unifies all hint-related functionality using the factory pattern.
    It provides backward compatibility while offering improved performance and
    simplified usage.

    Features:
    - Multiple hint generation strategies (domain, simplified, optimized, auto)
    - Environment-based configuration
    - Performance metrics aggregation
    - Event publishing and feedback tracking
    - Backward compatibility with all original APIs
    """

    def __init__(
        self,
        task_repository: TaskRepository,
        context_repository: ContextRepository,
        strategy: HintStrategy = HintStrategy.AUTO,
        max_hints: int = 5,
        max_required: int = 3,
        max_tips: int = 2,
        enable_ultra_hints: bool = True,
        enable_metrics: bool = True,
        event_store: Optional[EventStore] = None,
        hint_repository: Optional[Any] = None
    ):
        """
        Initialize the HintManager with specified configuration

        Args:
            task_repository: Repository for task data access
            context_repository: Repository for context data access
            strategy: Hint generation strategy to use
            max_hints: Maximum number of hints to return (default: 5)
            max_required: Maximum required actions for optimized strategy (default: 3)
            max_tips: Maximum tips for optimized strategy (default: 2)
            enable_ultra_hints: Enable ultra-fast optimization (default: True)
            enable_metrics: Enable performance metrics collection (default: True)
            event_store: Optional event store for publishing events
            hint_repository: Optional hint repository for persistence
        """
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_store = event_store
        self.hint_repository = hint_repository

        # Create configuration
        self.config = HintConfig(
            strategy=strategy,
            max_hints=max_hints,
            max_required=max_required,
            max_tips=max_tips,
            enable_ultra_hints=enable_ultra_hints,
            enable_metrics=enable_metrics
        )

        # Create strategy using factory
        self.strategy = HintStrategyFactory.create_strategy(strategy, self.config)

        logger.info(f"HintManager initialized with {strategy.value} strategy")

    # === PRIMARY INTERFACE METHODS ===

    async def generate_hints_for_task(
        self,
        task_id: UUID,
        hint_types: Optional[List[HintType]] = None,
        max_hints: Optional[int] = None
    ) -> HintCollection:
        """
        Generate workflow hints for a specific task.

        This is the main entry point for hint generation, providing a clean
        interface that delegates to the configured strategy.

        Args:
            task_id: ID of the task to generate hints for
            hint_types: Optional filter for specific hint types
            max_hints: Override default maximum hints

        Returns:
            HintCollection containing generated hints
        """
        # Override config if specified
        if max_hints is not None:
            original_max = self.config.max_hints
            self.config.max_hints = max_hints
            try:
                result = await self.strategy.generate_hints_for_task(
                    task_id, self.task_repository, self.context_repository,
                    self.event_store, hint_types
                )
            finally:
                self.config.max_hints = original_max
            return result

        return await self.strategy.generate_hints_for_task(
            task_id, self.task_repository, self.context_repository,
            self.event_store, hint_types
        )

    def simplify_workflow_guidance(
        self,
        guidance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simplify complete workflow guidance structure.

        This method provides optimization of complex workflow guidance
        into AI-friendly formats based on the configured strategy.

        Args:
            guidance: Original workflow guidance structure

        Returns:
            Simplified/optimized guidance structure
        """
        return self.strategy.simplify_workflow_guidance(guidance)

    def optimize_workflow_hints(
        self,
        workflow_guidance: Dict[str, Any],
        max_required: Optional[int] = None,
        max_tips: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Optimize workflow hints to ultra-flat structure (HintOptimizer compatibility).

        This method provides direct access to the optimized hint generation
        for maximum performance when ultra-flat structure is needed.

        Args:
            workflow_guidance: Original nested workflow guidance
            max_required: Override maximum required actions
            max_tips: Override maximum tips

        Returns:
            Optimized flat hints structure
        """
        # Temporarily switch to optimized strategy if needed
        if not isinstance(self.strategy, OptimizedHintStrategy):
            temp_config = HintConfig(
                strategy=HintStrategy.OPTIMIZED,
                max_hints=self.config.max_hints,
                max_required=max_required or self.config.max_required,
                max_tips=max_tips or self.config.max_tips,
                enable_ultra_hints=self.config.enable_ultra_hints,
                enable_metrics=self.config.enable_metrics
            )
            temp_strategy = HintStrategyFactory.create_strategy(HintStrategy.OPTIMIZED, temp_config)
            return temp_strategy.simplify_workflow_guidance(workflow_guidance)

        # Use current optimized strategy
        if max_required is not None or max_tips is not None:
            original_required = self.config.max_required
            original_tips = self.config.max_tips

            if max_required is not None:
                self.config.max_required = max_required
            if max_tips is not None:
                self.config.max_tips = max_tips

            try:
                result = self.strategy.simplify_workflow_guidance(workflow_guidance)
            finally:
                self.config.max_required = original_required
                self.config.max_tips = original_tips

            return result

        return self.strategy.simplify_workflow_guidance(workflow_guidance)

    # === BACKWARD COMPATIBILITY METHODS ===

    # HintGenerationService compatibility methods
    async def accept_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        action_taken: Optional[str] = None
    ) -> None:
        """Record that a hint was accepted (HintGenerationService compatibility)"""
        if not self.event_store:
            logger.warning("Event store not available for hint acceptance tracking")
            return

        event = HintAccepted(
            aggregate_id=task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id=user_id,
            hint_id=hint_id,
            task_id=task_id,
            action_taken=action_taken
        )
        await self.event_store.append(event)

    async def dismiss_hint(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        reason: Optional[str] = None
    ) -> None:
        """Record that a hint was dismissed (HintGenerationService compatibility)"""
        if not self.event_store:
            logger.warning("Event store not available for hint dismissal tracking")
            return

        event = HintDismissed(
            aggregate_id=task_id,
            occurred_at=datetime.now(timezone.utc),
            user_id=user_id,
            hint_id=hint_id,
            task_id=task_id,
            reason=reason
        )
        await self.event_store.append(event)

    async def provide_feedback(
        self,
        hint_id: UUID,
        task_id: UUID,
        user_id: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None,
        effectiveness_score: Optional[float] = None
    ) -> None:
        """Record feedback on a hint (HintGenerationService compatibility)"""
        if not self.event_store:
            logger.warning("Event store not available for hint feedback tracking")
            return

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

    def add_rule(self, rule: HintRule) -> None:
        """Add a custom hint generation rule (HintGenerationService compatibility)"""
        if isinstance(self.strategy, DomainHintStrategy):
            self.strategy.rules.append(rule)
            logger.info(f"Added hint rule: {rule.rule_name}")
        else:
            logger.warning(f"Cannot add rule to {type(self.strategy).__name__}, use DomainHintStrategy")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a hint generation rule (HintGenerationService compatibility)"""
        if isinstance(self.strategy, DomainHintStrategy):
            original_count = len(self.strategy.rules)
            self.strategy.rules = [r for r in self.strategy.rules if r.rule_name != rule_name]
            removed = len(self.strategy.rules) < original_count

            if removed:
                logger.info(f"Removed hint rule: {rule_name}")

            return removed
        else:
            logger.warning(f"Cannot remove rule from {type(self.strategy).__name__}, use DomainHintStrategy")
            return False

    def get_rules(self) -> List[str]:
        """Get list of active rule names (HintGenerationService compatibility)"""
        if isinstance(self.strategy, DomainHintStrategy):
            return [rule.rule_name for rule in self.strategy.rules]
        else:
            return []

    # WorkflowHintsSimplifier compatibility methods
    def create_structured_hints(
        self,
        guidance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create structured hints from guidance (WorkflowHintsSimplifier compatibility)"""
        # Convert guidance to structured format
        hints = []

        if "next_steps" in guidance:
            next_steps = guidance["next_steps"]

            if isinstance(next_steps, dict):
                if "recommendations" in next_steps:
                    recs = next_steps["recommendations"]
                    if isinstance(recs, list):
                        for rec in recs[:3]:
                            hints.append({
                                "type": "action",
                                "action": str(rec),
                                "priority": "medium"
                            })
                    elif isinstance(recs, str):
                        hints.append({
                            "type": "action",
                            "action": recs,
                            "priority": "medium"
                        })

                if "required_actions" in next_steps:
                    required = next_steps["required_actions"]
                    if isinstance(required, list):
                        for action in required[:2]:
                            hints.append({
                                "type": "action",
                                "action": str(action),
                                "priority": "high"
                            })

        return hints

    # === PERFORMANCE AND METRICS ===

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        base_metrics = self.strategy.get_metrics()

        # Add manager-level metrics
        manager_metrics = {
            "strategy_type": self.config.strategy.value,
            "config": {
                "max_hints": self.config.max_hints,
                "max_required": self.config.max_required,
                "max_tips": self.config.max_tips,
                "enable_ultra_hints": self.config.enable_ultra_hints,
                "enable_metrics": self.config.enable_metrics
            }
        }

        # Merge metrics
        return {**base_metrics, **manager_metrics}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics (HintOptimizer compatibility)"""
        return self.get_metrics()

    def reset_metrics(self) -> None:
        """Reset all performance metrics"""
        self.strategy.reset_metrics()

    # === UTILITY METHODS ===

    def switch_strategy(self, new_strategy: HintStrategy) -> None:
        """Switch to a different hint generation strategy"""
        if new_strategy != self.config.strategy:
            self.config.strategy = new_strategy
            self.strategy = HintStrategyFactory.create_strategy(new_strategy, self.config)
            logger.info(f"Switched to {new_strategy.value} strategy")

    def get_current_strategy(self) -> HintStrategy:
        """Get the currently active strategy"""
        return self.config.strategy

    def is_ultra_hints_enabled(self) -> bool:
        """Check if ultra-hints optimization is enabled"""
        return self.config.enable_ultra_hints

    def __str__(self) -> str:
        """String representation of the HintManager"""
        return f"HintManager(strategy={self.config.strategy.value}, ultra_hints={self.config.enable_ultra_hints})"

    def __repr__(self) -> str:
        """Detailed representation of the HintManager"""
        return (f"HintManager(strategy={self.config.strategy.value}, "
                f"max_hints={self.config.max_hints}, "
                f"ultra_hints={self.config.enable_ultra_hints}, "
                f"metrics={self.config.enable_metrics})")


# === FACTORY FUNCTION FOR EASY INSTANTIATION ===

def create_hint_manager(
    task_repository: TaskRepository,
    context_repository: ContextRepository,
    strategy: Optional[str] = None,
    **kwargs
) -> HintManager:
    """
    Factory function to create HintManager with environment-based defaults.

    Args:
        task_repository: Repository for task data access
        context_repository: Repository for context data access
        strategy: Strategy name ('domain', 'simplified', 'optimized', 'auto')
        **kwargs: Additional configuration options

    Returns:
        Configured HintManager instance
    """
    # Determine strategy from parameter or environment
    if strategy is None:
        strategy = os.getenv('HINT_STRATEGY', 'auto').lower()

    strategy_enum = {
        'domain': HintStrategy.DOMAIN,
        'simplified': HintStrategy.SIMPLIFIED,
        'optimized': HintStrategy.OPTIMIZED,
        'auto': HintStrategy.AUTO
    }.get(strategy, HintStrategy.AUTO)

    # Set default values from environment
    defaults = {
        'max_hints': int(os.getenv('HINT_MAX_HINTS', '5')),
        'max_required': int(os.getenv('HINT_MAX_REQUIRED', '3')),
        'max_tips': int(os.getenv('HINT_MAX_TIPS', '2')),
        'enable_ultra_hints': os.getenv('ENABLE_ULTRA_HINTS', 'true').lower() in ['true', '1', 'yes', 'on'],
        'enable_metrics': os.getenv('HINT_ENABLE_METRICS', 'true').lower() in ['true', '1', 'yes', 'on']
    }

    # Override defaults with provided kwargs
    config = {**defaults, **kwargs}

    return HintManager(
        task_repository=task_repository,
        context_repository=context_repository,
        strategy=strategy_enum,
        **config
    )


# === BACKWARD COMPATIBILITY ALIASES ===

# For code that imports the old classes directly
HintGenerationService = HintManager
WorkflowHintsSimplifier = HintManager

# Legacy function for WorkflowHintsSimplifier users
def create_workflow_hints_simplifier() -> HintManager:
    """Create HintManager configured for simplified workflow hints"""
    # This requires repositories, so we'll need to use the domain service factory
    try:
        from .domain_service_factory import DomainServiceFactory

        repository_factory = DomainServiceFactory.get_repository_factory()
        task_repository = repository_factory.create_task_repository()
        context_repository = repository_factory.create_context_repository()

        return HintManager(
            task_repository=task_repository,
            context_repository=context_repository,
            strategy=HintStrategy.SIMPLIFIED
        )
    except Exception as e:
        logger.error(f"Failed to create workflow hints simplifier: {e}")
        raise