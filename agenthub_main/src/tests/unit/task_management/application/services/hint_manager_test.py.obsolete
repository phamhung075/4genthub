"""
Unit tests for HintManager (Phase 3.1 Consolidated Implementation).

This module tests the consolidated HintManager with factory pattern, multiple strategies,
backward compatibility, and performance metrics.

Test Coverage:
- HintManager initialization and configuration
- Strategy factory pattern
- Domain hint strategy
- Simplified hint strategy
- Optimized hint strategy
- Auto hint strategy
- Hint generation workflows
- Workflow guidance simplification
- Backward compatibility methods
- Performance metrics
- Strategy switching
"""

import pytest
import uuid
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import List, Dict, Any

from fastmcp.task_management.application.services.hint_manager import (
    HintManager,
    HintStrategy,
    HintConfig,
    HintStrategyFactory,
    BaseHintStrategy,
    DomainHintStrategy,
    SimplifiedHintStrategy,
    OptimizedHintStrategy,
    AutoHintStrategy,
    create_hint_manager
)
from fastmcp.task_management.domain.value_objects.hints import (
    WorkflowHint, HintCollection, HintType, HintPriority, HintMetadata
)
from fastmcp.task_management.domain.services.hint_rules import (
    HintRule, RuleContext,
    StalledProgressRule,
    ImplementationReadyForTestingRule,
    MissingContextRule,
    ComplexDependencyRule,
    NearCompletionRule,
    CollaborationNeededRule
)
from fastmcp.task_management.domain.events.hint_events import (
    HintGenerated, HintAccepted, HintDismissed,
    HintFeedbackProvided, HintEffectivenessCalculated
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.context import TaskContext


class TestHintConfig:
    """Test suite for HintConfig dataclass"""

    def test_hint_config_default_values(self):
        """Test HintConfig with default values"""
        config = HintConfig(strategy=HintStrategy.AUTO)

        assert config.strategy == HintStrategy.AUTO
        assert config.max_hints == 5
        assert config.max_required == 3
        assert config.max_tips == 2
        assert config.enable_ultra_hints is True
        assert config.enable_metrics is True
        assert config.cache_effectiveness is True

    def test_hint_config_custom_values(self):
        """Test HintConfig with custom values"""
        config = HintConfig(
            strategy=HintStrategy.DOMAIN,
            max_hints=10,
            max_required=5,
            max_tips=3,
            enable_ultra_hints=False,
            enable_metrics=False,
            cache_effectiveness=False
        )

        assert config.strategy == HintStrategy.DOMAIN
        assert config.max_hints == 10
        assert config.max_required == 5
        assert config.max_tips == 3
        assert config.enable_ultra_hints is False
        assert config.enable_metrics is False
        assert config.cache_effectiveness is False


class TestHintStrategyFactory:
    """Test suite for HintStrategyFactory"""

    def test_create_domain_strategy(self):
        """Test creating domain strategy"""
        config = HintConfig(strategy=HintStrategy.DOMAIN)
        strategy = HintStrategyFactory.create_strategy(HintStrategy.DOMAIN, config)

        assert isinstance(strategy, DomainHintStrategy)
        assert strategy.config == config

    def test_create_simplified_strategy(self):
        """Test creating simplified strategy"""
        config = HintConfig(strategy=HintStrategy.SIMPLIFIED)
        strategy = HintStrategyFactory.create_strategy(HintStrategy.SIMPLIFIED, config)

        assert isinstance(strategy, SimplifiedHintStrategy)
        assert strategy.config == config

    def test_create_optimized_strategy(self):
        """Test creating optimized strategy"""
        config = HintConfig(strategy=HintStrategy.OPTIMIZED)

        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer'):
            strategy = HintStrategyFactory.create_strategy(HintStrategy.OPTIMIZED, config)
            assert isinstance(strategy, OptimizedHintStrategy)

    def test_create_auto_strategy(self):
        """Test creating auto strategy"""
        config = HintConfig(strategy=HintStrategy.AUTO)
        strategy = HintStrategyFactory.create_strategy(HintStrategy.AUTO, config)

        assert isinstance(strategy, AutoHintStrategy)
        assert strategy.config == config

    def test_create_unknown_strategy_raises_error(self):
        """Test that unknown strategy raises ValueError"""
        config = HintConfig(strategy=HintStrategy.AUTO)

        with pytest.raises(ValueError, match="Unknown hint strategy"):
            HintStrategyFactory.create_strategy("invalid", config)


class TestBaseHintStrategy:
    """Test suite for BaseHintStrategy"""

    def test_base_strategy_initialization(self):
        """Test base strategy initialization"""
        config = HintConfig(strategy=HintStrategy.DOMAIN)
        strategy = DomainHintStrategy(config)

        assert strategy.config == config
        assert 'hints_processed' in strategy.metrics
        assert 'processing_time_ms' in strategy.metrics
        assert 'complexity_reduced' in strategy.metrics
        assert 'words_saved' in strategy.metrics

    def test_get_metrics(self):
        """Test getting metrics from strategy"""
        config = HintConfig(strategy=HintStrategy.DOMAIN)
        strategy = DomainHintStrategy(config)

        metrics = strategy.get_metrics()
        assert isinstance(metrics, dict)
        assert metrics['hints_processed'] == 0
        assert metrics['processing_time_ms'] == 0

    def test_reset_metrics(self):
        """Test resetting strategy metrics"""
        config = HintConfig(strategy=HintStrategy.DOMAIN)
        strategy = DomainHintStrategy(config)

        # Set some metrics
        strategy.metrics['hints_processed'] = 10
        strategy.metrics['processing_time_ms'] = 100

        # Reset
        strategy.reset_metrics()

        assert strategy.metrics['hints_processed'] == 0
        assert strategy.metrics['processing_time_ms'] == 0


class TestDomainHintStrategy:
    """Test suite for DomainHintStrategy"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = HintConfig(strategy=HintStrategy.DOMAIN)
        self.task_repository = Mock()
        self.context_repository = Mock()
        self.event_store = Mock()

    def test_initialize_default_rules(self):
        """Test that default rules are initialized"""
        strategy = DomainHintStrategy(self.config)

        assert len(strategy.rules) == 6
        rule_types = {type(rule) for rule in strategy.rules}
        expected_types = {
            StalledProgressRule,
            ImplementationReadyForTestingRule,
            MissingContextRule,
            ComplexDependencyRule,
            NearCompletionRule,
            CollaborationNeededRule
        }
        assert rule_types == expected_types

    @pytest.mark.asyncio
    async def test_generate_hints_task_not_found(self):
        """Test hint generation when task is not found"""
        strategy = DomainHintStrategy(self.config)
        self.task_repository.get = AsyncMock(return_value=None)

        task_id = uuid.uuid4()
        result = await strategy.generate_hints_for_task(
            task_id, self.task_repository, self.context_repository
        )

        assert isinstance(result, HintCollection)
        assert result.task_id == task_id
        assert len(result.hints) == 0

    @pytest.mark.asyncio
    async def test_generate_hints_with_valid_task(self):
        """Test hint generation with valid task"""
        strategy = DomainHintStrategy(self.config)

        # Create mock task
        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.status = "in_progress"
        mock_task.labels = []
        mock_task.subtasks = []
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.updated_at = datetime.now(timezone.utc)

        self.task_repository.get = AsyncMock(return_value=mock_task)
        self.task_repository.list = AsyncMock(return_value=[])
        self.context_repository.get_by_task_id = AsyncMock(return_value=None)

        # Mock rules to return hints
        mock_hint = WorkflowHint(
            id=uuid.uuid4(),
            type=HintType.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message="Test hint",
            suggested_action="Test action",
            metadata=HintMetadata(source="test", confidence=0.8, reasoning="Test reasoning"),
            task_id=task_id,
            created_at=datetime.now(timezone.utc)
        )

        with patch.object(strategy.rules[0], 'evaluate', return_value=mock_hint):
            result = await strategy.generate_hints_for_task(
                task_id, self.task_repository, self.context_repository
            )

        assert isinstance(result, HintCollection)
        assert len(result.hints) > 0
        assert strategy.metrics['hints_processed'] > 0

    def test_simplify_workflow_guidance_passthrough(self):
        """Test that domain strategy passes guidance through unchanged"""
        strategy = DomainHintStrategy(self.config)

        guidance = {
            "next_steps": {"recommendations": ["Do something"]},
            "confidence": 0.9
        }

        result = strategy.simplify_workflow_guidance(guidance)
        assert result == guidance


class TestSimplifiedHintStrategy:
    """Test suite for SimplifiedHintStrategy"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = HintConfig(strategy=HintStrategy.SIMPLIFIED)
        self.task_repository = Mock()
        self.context_repository = Mock()

    def test_simplified_strategy_initialization(self):
        """Test simplified strategy initialization"""
        with patch.dict(os.environ, {'ENABLE_ULTRA_HINTS': 'true'}):
            strategy = SimplifiedHintStrategy(self.config)
            assert strategy.ultra_hints_enabled is True

    def test_simplified_strategy_disabled_ultra_hints(self):
        """Test simplified strategy with ultra hints disabled"""
        with patch.dict(os.environ, {'ENABLE_ULTRA_HINTS': 'false'}):
            config = HintConfig(strategy=HintStrategy.SIMPLIFIED, enable_ultra_hints=False)
            strategy = SimplifiedHintStrategy(config)
            assert strategy.ultra_hints_enabled is False

    def test_simplify_text_removes_verbose_phrases(self):
        """Test that simplify_text removes verbose phrases"""
        strategy = SimplifiedHintStrategy(self.config)

        text = "you should please consider creating a new file"
        result = strategy._simplify_text(text)

        assert "you should" not in result.lower()
        assert "please" not in result.lower()
        assert "consider" not in result.lower()

    def test_simplify_text_capitalizes_first_letter(self):
        """Test that simplify_text capitalizes first letter"""
        strategy = SimplifiedHintStrategy(self.config)

        text = "create a file"
        result = strategy._simplify_text(text)

        assert result[0].isupper()

    def test_simplify_workflow_guidance_legacy(self):
        """Test legacy workflow guidance simplification"""
        strategy = SimplifiedHintStrategy(self.config)
        strategy.ultra_hints_enabled = False
        strategy.hint_optimizer = None

        guidance = {
            "next_steps": {
                "recommendations": ["Do task 1", "Do task 2", "Do task 3"]
            },
            "validation": {
                "required_fields": ["field1", "field2"]
            }
        }

        result = strategy.simplify_workflow_guidance(guidance)

        assert "next" in result or "recommendations" in result
        assert strategy.metrics['hints_processed'] > 0

    def test_simplify_next_steps_with_list(self):
        """Test simplifying next steps that are a list"""
        strategy = SimplifiedHintStrategy(self.config)

        next_steps = ["Step 1", "Step 2", "Step 3", "Step 4"]
        result = strategy._simplify_next_steps(next_steps)

        assert isinstance(result, list)
        assert len(result) <= 3  # Should limit to 3

    def test_simplify_next_steps_with_dict(self):
        """Test simplifying next steps that are a dict"""
        strategy = SimplifiedHintStrategy(self.config)

        next_steps = {
            "recommendations": ["Action 1", "Action 2"],
            "required_actions": ["Required 1"]
        }
        result = strategy._simplify_next_steps(next_steps)

        assert isinstance(result, dict)

    def test_extract_key_points(self):
        """Test extracting key points from data"""
        strategy = SimplifiedHintStrategy(self.config)

        data = ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]
        result = strategy._extract_key_points(data, max_points=3)

        assert len(result) == 3

    def test_extract_ids_or_names_from_list(self):
        """Test extracting IDs or names from list"""
        strategy = SimplifiedHintStrategy(self.config)

        data = [
            {"id": "123", "name": "Item 1"},
            {"id": "456", "name": "Item 2"}
        ]
        result = strategy._extract_ids_or_names(data)

        assert "123" in result
        assert "456" in result


class TestOptimizedHintStrategy:
    """Test suite for OptimizedHintStrategy"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = HintConfig(strategy=HintStrategy.OPTIMIZED)

    def test_optimized_strategy_requires_hint_optimizer(self):
        """Test that optimized strategy requires HintOptimizer"""
        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer', side_effect=ImportError):
            with pytest.raises(ImportError):
                OptimizedHintStrategy(self.config)

    def test_optimized_strategy_initialization(self):
        """Test optimized strategy initialization with HintOptimizer"""
        mock_optimizer = Mock()

        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer', return_value=mock_optimizer):
            strategy = OptimizedHintStrategy(self.config)
            assert strategy.optimizer == mock_optimizer

    def test_simplify_workflow_guidance_uses_optimizer(self):
        """Test that simplify_workflow_guidance uses optimizer"""
        mock_optimizer = Mock()
        mock_optimizer.optimize_workflow_hints = Mock(return_value={"optimized": True})

        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer', return_value=mock_optimizer):
            strategy = OptimizedHintStrategy(self.config)

            guidance = {"next_steps": {"recommendations": ["Action"]}}
            result = strategy.simplify_workflow_guidance(guidance)

            assert result == {"optimized": True}
            mock_optimizer.optimize_workflow_hints.assert_called_once()


class TestAutoHintStrategy:
    """Test suite for AutoHintStrategy"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = HintConfig(strategy=HintStrategy.AUTO)

    def test_select_strategy_domain_from_env(self):
        """Test selecting domain strategy from environment"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'domain'}):
            strategy = AutoHintStrategy(self.config)
            selected = strategy._select_strategy()

            assert isinstance(selected, DomainHintStrategy)

    def test_select_strategy_simplified_from_env(self):
        """Test selecting simplified strategy from environment"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'simplified', 'ENABLE_ULTRA_HINTS': 'false'}):
            with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer'):
                strategy = AutoHintStrategy(self.config)
                selected = strategy._select_strategy()

                assert isinstance(selected, SimplifiedHintStrategy)

    def test_select_strategy_optimized_from_env(self):
        """Test selecting optimized strategy from environment"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'optimized', 'ENABLE_ULTRA_HINTS': 'true'}):
            with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer'):
                strategy = AutoHintStrategy(self.config)
                selected = strategy._select_strategy()

                assert isinstance(selected, OptimizedHintStrategy)

    def test_select_strategy_caching(self):
        """Test that strategy selection is cached"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'domain'}):
            strategy = AutoHintStrategy(self.config)

            selected1 = strategy._select_strategy()
            selected2 = strategy._select_strategy()

            assert selected1 is selected2

    @pytest.mark.asyncio
    async def test_generate_hints_delegates_to_selected_strategy(self):
        """Test that hint generation delegates to selected strategy"""
        task_repository = Mock()
        context_repository = Mock()

        with patch.dict(os.environ, {'HINT_STRATEGY': 'domain'}):
            strategy = AutoHintStrategy(self.config)

            task_id = uuid.uuid4()
            mock_task = Mock(spec=Task)
            mock_task.id = task_id
            mock_task.labels = []
            mock_task.subtasks = []

            task_repository.get = AsyncMock(return_value=mock_task)
            task_repository.list = AsyncMock(return_value=[])
            context_repository.get_by_task_id = AsyncMock(return_value=None)

            result = await strategy.generate_hints_for_task(
                task_id, task_repository, context_repository
            )

            assert isinstance(result, HintCollection)

    def test_simplify_workflow_guidance_delegates(self):
        """Test that workflow guidance simplification delegates"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'domain'}):
            strategy = AutoHintStrategy(self.config)

            guidance = {"next_steps": {"recommendations": ["Action"]}}
            result = strategy.simplify_workflow_guidance(guidance)

            assert result == guidance  # Domain strategy passes through


class TestHintManager:
    """Test suite for HintManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.context_repository = Mock()
        self.event_store = Mock()
        self.hint_repository = Mock()

    def test_hint_manager_initialization_default(self):
        """Test HintManager initialization with defaults"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )

        assert manager.task_repository == self.task_repository
        assert manager.context_repository == self.context_repository
        assert manager.event_store is None
        assert manager.config.strategy == HintStrategy.AUTO
        assert manager.config.max_hints == 5

    def test_hint_manager_initialization_custom(self):
        """Test HintManager initialization with custom parameters"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN,
            max_hints=10,
            max_required=5,
            max_tips=3,
            enable_ultra_hints=False,
            enable_metrics=False,
            event_store=self.event_store
        )

        assert manager.config.strategy == HintStrategy.DOMAIN
        assert manager.config.max_hints == 10
        assert manager.config.max_required == 5
        assert manager.config.max_tips == 3
        assert manager.config.enable_ultra_hints is False
        assert manager.event_store == self.event_store

    @pytest.mark.asyncio
    async def test_generate_hints_for_task(self):
        """Test generating hints for a task"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.labels = []
        mock_task.subtasks = []

        self.task_repository.get = AsyncMock(return_value=mock_task)
        self.task_repository.list = AsyncMock(return_value=[])
        self.context_repository.get_by_task_id = AsyncMock(return_value=None)

        result = await manager.generate_hints_for_task(task_id)

        assert isinstance(result, HintCollection)
        assert result.task_id == task_id

    @pytest.mark.asyncio
    async def test_generate_hints_with_max_hints_override(self):
        """Test generating hints with max_hints override"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN,
            max_hints=5
        )

        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.labels = []
        mock_task.subtasks = []

        self.task_repository.get = AsyncMock(return_value=mock_task)
        self.task_repository.list = AsyncMock(return_value=[])
        self.context_repository.get_by_task_id = AsyncMock(return_value=None)

        result = await manager.generate_hints_for_task(task_id, max_hints=10)

        # Config should be restored after call
        assert manager.config.max_hints == 5

    def test_simplify_workflow_guidance(self):
        """Test simplifying workflow guidance"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        guidance = {"next_steps": {"recommendations": ["Action 1"]}}
        result = manager.simplify_workflow_guidance(guidance)

        assert isinstance(result, dict)

    def test_optimize_workflow_hints_with_optimized_strategy(self):
        """Test optimizing workflow hints when using optimized strategy"""
        mock_optimizer = Mock()
        mock_optimizer.optimize_workflow_hints = Mock(return_value={"optimized": True})

        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer', return_value=mock_optimizer):
            manager = HintManager(
                task_repository=self.task_repository,
                context_repository=self.context_repository,
                strategy=HintStrategy.OPTIMIZED
            )

            guidance = {"next_steps": {"recommendations": ["Action"]}}
            result = manager.optimize_workflow_hints(guidance)

            assert result == {"optimized": True}

    def test_optimize_workflow_hints_switches_to_optimized(self):
        """Test that optimize_workflow_hints switches to optimized strategy"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        with patch('fastmcp.task_management.application.services.hint_optimizer.HintOptimizer') as mock_optimizer_class:
            mock_optimizer = Mock()
            mock_optimizer.optimize_workflow_hints = Mock(return_value={"optimized": True})
            mock_optimizer_class.return_value = mock_optimizer

            guidance = {"next_steps": {"recommendations": ["Action"]}}
            result = manager.optimize_workflow_hints(guidance, max_required=5, max_tips=3)

            assert result == {"optimized": True}

    @pytest.mark.asyncio
    async def test_accept_hint_publishes_event(self):
        """Test accepting a hint publishes event"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store
        )

        self.event_store.append = AsyncMock()

        hint_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = "user123"

        await manager.accept_hint(hint_id, task_id, user_id, "Followed suggestion")

        self.event_store.append.assert_called_once()
        event = self.event_store.append.call_args[0][0]
        assert isinstance(event, HintAccepted)
        assert event.hint_id == hint_id
        assert event.task_id == task_id

    @pytest.mark.asyncio
    async def test_dismiss_hint_publishes_event(self):
        """Test dismissing a hint publishes event"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store
        )

        self.event_store.append = AsyncMock()

        hint_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = "user123"

        await manager.dismiss_hint(hint_id, task_id, user_id, "Not relevant")

        self.event_store.append.assert_called_once()
        event = self.event_store.append.call_args[0][0]
        assert isinstance(event, HintDismissed)

    @pytest.mark.asyncio
    async def test_provide_feedback_publishes_event(self):
        """Test providing feedback publishes event"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store
        )

        self.event_store.append = AsyncMock()

        hint_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = "user123"

        await manager.provide_feedback(
            hint_id, task_id, user_id, was_helpful=True,
            feedback_text="Very helpful", effectiveness_score=0.9
        )

        self.event_store.append.assert_called_once()
        event = self.event_store.append.call_args[0][0]
        assert isinstance(event, HintFeedbackProvided)
        assert event.was_helpful is True

    def test_add_rule_to_domain_strategy(self):
        """Test adding a rule to domain strategy"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        mock_rule = Mock(spec=HintRule)
        mock_rule.rule_name = "CustomRule"

        original_count = len(manager.strategy.rules)
        manager.add_rule(mock_rule)

        assert len(manager.strategy.rules) == original_count + 1
        assert mock_rule in manager.strategy.rules

    def test_add_rule_to_non_domain_strategy_warning(self):
        """Test adding rule to non-domain strategy logs warning"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.SIMPLIFIED
        )

        mock_rule = Mock(spec=HintRule)
        mock_rule.rule_name = "CustomRule"

        with patch('fastmcp.task_management.application.services.hint_manager.logger') as mock_logger:
            manager.add_rule(mock_rule)
            mock_logger.warning.assert_called_once()

    def test_remove_rule_from_domain_strategy(self):
        """Test removing a rule from domain strategy"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        # Get name of first rule
        rule_name = manager.strategy.rules[0].rule_name
        original_count = len(manager.strategy.rules)

        result = manager.remove_rule(rule_name)

        assert result is True
        assert len(manager.strategy.rules) == original_count - 1

    def test_remove_nonexistent_rule(self):
        """Test removing a nonexistent rule"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        result = manager.remove_rule("NonexistentRule")

        assert result is False

    def test_get_rules(self):
        """Test getting list of active rules"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        rules = manager.get_rules()

        assert isinstance(rules, list)
        assert len(rules) == 6  # Default rules
        assert all(isinstance(r, str) for r in rules)

    def test_get_rules_non_domain_returns_empty(self):
        """Test getting rules from non-domain strategy returns empty list"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.SIMPLIFIED
        )

        rules = manager.get_rules()

        assert rules == []

    def test_create_structured_hints(self):
        """Test creating structured hints from guidance"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )

        guidance = {
            "next_steps": {
                "recommendations": ["Action 1", "Action 2"],
                "required_actions": ["Required action"]
            }
        }

        hints = manager.create_structured_hints(guidance)

        assert isinstance(hints, list)
        assert len(hints) > 0
        assert all(isinstance(h, dict) for h in hints)

    def test_get_metrics(self):
        """Test getting performance metrics"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        metrics = manager.get_metrics()

        assert isinstance(metrics, dict)
        assert 'strategy_type' in metrics
        assert metrics['strategy_type'] == 'domain'
        assert 'config' in metrics

    def test_get_performance_metrics(self):
        """Test backward compatibility method for getting metrics"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )

        metrics = manager.get_performance_metrics()

        assert isinstance(metrics, dict)

    def test_reset_metrics(self):
        """Test resetting performance metrics"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )

        # Simulate some processing
        manager.strategy.metrics['hints_processed'] = 10

        manager.reset_metrics()

        assert manager.strategy.metrics['hints_processed'] == 0

    def test_switch_strategy(self):
        """Test switching hint generation strategy"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        assert isinstance(manager.strategy, DomainHintStrategy)

        manager.switch_strategy(HintStrategy.SIMPLIFIED)

        assert isinstance(manager.strategy, SimplifiedHintStrategy)
        assert manager.config.strategy == HintStrategy.SIMPLIFIED

    def test_switch_strategy_same_does_nothing(self):
        """Test switching to same strategy does nothing"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        original_strategy = manager.strategy
        manager.switch_strategy(HintStrategy.DOMAIN)

        # Should be same instance since strategy didn't change
        assert manager.strategy is original_strategy

    def test_get_current_strategy(self):
        """Test getting current strategy"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        current = manager.get_current_strategy()

        assert current == HintStrategy.DOMAIN

    def test_is_ultra_hints_enabled(self):
        """Test checking if ultra hints is enabled"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            enable_ultra_hints=True
        )

        assert manager.is_ultra_hints_enabled() is True

    def test_str_representation(self):
        """Test string representation of HintManager"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN
        )

        str_repr = str(manager)

        assert "HintManager" in str_repr
        assert "domain" in str_repr

    def test_repr_representation(self):
        """Test detailed representation of HintManager"""
        manager = HintManager(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            strategy=HintStrategy.DOMAIN,
            max_hints=10
        )

        repr_str = repr(manager)

        assert "HintManager" in repr_str
        assert "domain" in repr_str
        assert "10" in repr_str


class TestCreateHintManager:
    """Test suite for create_hint_manager factory function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.context_repository = Mock()

    def test_create_hint_manager_with_defaults(self):
        """Test creating HintManager with default values"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'auto'}):
            manager = create_hint_manager(
                self.task_repository,
                self.context_repository
            )

            assert isinstance(manager, HintManager)
            assert manager.config.strategy == HintStrategy.AUTO

    def test_create_hint_manager_with_strategy_parameter(self):
        """Test creating HintManager with strategy parameter"""
        manager = create_hint_manager(
            self.task_repository,
            self.context_repository,
            strategy='domain'
        )

        assert manager.config.strategy == HintStrategy.DOMAIN

    def test_create_hint_manager_with_env_strategy(self):
        """Test creating HintManager with environment strategy"""
        with patch.dict(os.environ, {'HINT_STRATEGY': 'simplified'}):
            manager = create_hint_manager(
                self.task_repository,
                self.context_repository
            )

            assert manager.config.strategy == HintStrategy.SIMPLIFIED

    def test_create_hint_manager_with_custom_config(self):
        """Test creating HintManager with custom configuration"""
        with patch.dict(os.environ, {
            'HINT_MAX_HINTS': '10',
            'HINT_MAX_REQUIRED': '5',
            'HINT_MAX_TIPS': '3'
        }):
            manager = create_hint_manager(
                self.task_repository,
                self.context_repository
            )

            assert manager.config.max_hints == 10
            assert manager.config.max_required == 5
            assert manager.config.max_tips == 3

    def test_create_hint_manager_with_kwargs_override(self):
        """Test that kwargs override environment defaults"""
        with patch.dict(os.environ, {'HINT_MAX_HINTS': '5'}):
            manager = create_hint_manager(
                self.task_repository,
                self.context_repository,
                max_hints=15
            )

            assert manager.config.max_hints == 15

    def test_create_hint_manager_invalid_strategy_defaults_to_auto(self):
        """Test that invalid strategy defaults to auto"""
        manager = create_hint_manager(
            self.task_repository,
            self.context_repository,
            strategy='invalid'
        )

        assert manager.config.strategy == HintStrategy.AUTO


class TestBackwardCompatibilityAliases:
    """Test suite for backward compatibility aliases"""

    def test_hint_generation_service_alias(self):
        """Test that HintGenerationService is an alias for HintManager"""
        from fastmcp.task_management.application.services.hint_manager import HintGenerationService

        assert HintGenerationService is HintManager

    def test_workflow_hints_simplifier_alias(self):
        """Test that WorkflowHintsSimplifier is an alias for HintManager"""
        from fastmcp.task_management.application.services.hint_manager import WorkflowHintsSimplifier

        assert WorkflowHintsSimplifier is HintManager
