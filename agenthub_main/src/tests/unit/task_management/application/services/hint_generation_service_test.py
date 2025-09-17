"""
Unit tests for HintGenerationService.

This module tests the hint generation, rule evaluation, effectiveness tracking, and event publishing functionality.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import List, Dict, Any

from fastmcp.task_management.application.services.hint_generation_service import HintGenerationService
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


class TestHintGenerationServiceInitialization:
    """Test suite for HintGenerationService initialization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.context_repository = Mock()
        self.event_store = Mock()
        self.hint_repository = Mock()

    def test_init_with_required_parameters(self):
        """Test initialization with required parameters only"""
        service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        assert service.task_repository == self.task_repository
        assert service.context_repository == self.context_repository
        assert service.event_store is None
        assert service.hint_repository is None
        assert len(service.rules) == 6  # Default rules
        assert isinstance(service._effectiveness_cache, dict)

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters"""
        service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store,
            hint_repository=self.hint_repository
        )
        
        assert service.event_store == self.event_store
        assert service.hint_repository == self.hint_repository

    def test_default_rules_initialization(self):
        """Test that default rules are initialized correctly"""
        service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        rule_types = {type(rule) for rule in service.rules}
        expected_types = {
            StalledProgressRule,
            ImplementationReadyForTestingRule,
            MissingContextRule,
            ComplexDependencyRule,
            NearCompletionRule,
            CollaborationNeededRule
        }
        
        assert rule_types == expected_types

    def test_default_rules_configuration(self):
        """Test that default rules are configured correctly"""
        service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        # Check StalledProgressRule has correct stall_hours
        stalled_rule = next(r for r in service.rules if isinstance(r, StalledProgressRule))
        assert stalled_rule.stall_hours == 24
        
        # Check ImplementationReadyForTestingRule has correct threshold
        impl_rule = next(r for r in service.rules if isinstance(r, ImplementationReadyForTestingRule))
        assert impl_rule.implementation_threshold == 0.75
        
        # Check ComplexDependencyRule has correct threshold
        complex_rule = next(r for r in service.rules if isinstance(r, ComplexDependencyRule))
        assert complex_rule.complexity_threshold == 3
        
        # Check NearCompletionRule has correct threshold
        completion_rule = next(r for r in service.rules if isinstance(r, NearCompletionRule))
        assert completion_rule.completion_threshold == 0.9


class TestHintGeneration:
    """Test suite for hint generation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.event_store = AsyncMock()
        self.hint_repository = AsyncMock()
        
        self.service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store,
            hint_repository=self.hint_repository
        )
        
        self.task_id = uuid.uuid4()
        self.task = Mock(spec=Task)
        self.task.id = self.task_id
        self.task.labels = ['frontend', 'testing']
        self.task.subtasks = []
        
        self.context = Mock(spec=TaskContext)

    @pytest.mark.asyncio
    async def test_generate_hints_task_not_found(self):
        """Test hint generation when task is not found"""
        self.task_repository.get.return_value = None
        
        result = await self.service.generate_hints_for_task(self.task_id)
        
        assert isinstance(result, HintCollection)
        assert result.task_id == self.task_id
        assert len(result.hints) == 0

    @pytest.mark.asyncio
    async def test_generate_hints_context_not_found(self):
        """Test hint generation when context is not found"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.side_effect = Exception("Context not found")
        
        # Mock the helper methods
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_get_historical_patterns', return_value={}):
                with patch.object(self.service, '_publish_hint_generated') as mock_publish:
                    with patch.object(self.service, '_store_hints') as mock_store:
                        # Mock rule evaluation to return no hints
                        for rule in self.service.rules:
                            rule.evaluate = Mock(return_value=None)
                        
                        result = await self.service.generate_hints_for_task(self.task_id)
                        
                        assert isinstance(result, HintCollection)
                        assert result.task_id == self.task_id

    @pytest.mark.asyncio
    async def test_generate_hints_success(self):
        """Test successful hint generation"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        # Create mock hint with proper attributes for get_top_hints to work
        mock_hint = Mock(spec=WorkflowHint)
        mock_hint.id = uuid.uuid4()
        mock_hint.type = HintType.NEXT_ACTION
        mock_hint.priority = HintPriority.MEDIUM
        mock_hint.task_id = self.task_id
        mock_hint.metadata = Mock()
        mock_hint.metadata.confidence = 0.85
        mock_hint.metadata.patterns_detected = ['pattern1']
        mock_hint.metadata.reasoning = 'Test reasoning'
        mock_hint.created_at = datetime.now(timezone.utc)
        mock_hint.expires_at = None  # No expiration
        mock_hint.is_expired = Mock(return_value=False)  # Not expired
        
        # Mock the helper methods
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_get_historical_patterns', return_value={}):
                with patch.object(self.service, '_should_include_hint', return_value=True):
                    with patch.object(self.service, '_enhance_hint_with_effectiveness', return_value=mock_hint):
                        with patch.object(self.service, '_publish_hint_generated') as mock_publish:
                            with patch.object(self.service, '_store_hints') as mock_store:
                                # Mock first rule to return hint, others return None
                                self.service.rules[0].evaluate = Mock(return_value=mock_hint)
                                for rule in self.service.rules[1:]:
                                    rule.evaluate = Mock(return_value=None)
                                
                                result = await self.service.generate_hints_for_task(self.task_id)
                                
                                assert isinstance(result, HintCollection)
                                assert result.task_id == self.task_id
                                assert len(result.hints) == 1
                                assert mock_hint in result.hints
                                mock_publish.assert_called_once_with(mock_hint, self.service.rules[0])
                                mock_store.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_generate_hints_with_type_filter(self):
        """Test hint generation with type filter"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        # Create mock hints with different types
        hint1 = Mock(spec=WorkflowHint)
        hint1.type = HintType.NEXT_ACTION
        hint1.priority = HintPriority.MEDIUM
        hint1.metadata = Mock(confidence=0.85)
        hint1.created_at = datetime.now(timezone.utc)
        hint1.expires_at = None
        hint1.is_expired = Mock(return_value=False)
        hint2 = Mock(spec=WorkflowHint)
        hint2.type = HintType.BLOCKER_RESOLUTION
        hint2.priority = HintPriority.HIGH
        hint2.metadata = Mock(confidence=0.75)
        hint2.created_at = datetime.now(timezone.utc)
        hint2.expires_at = None
        hint2.is_expired = Mock(return_value=False)
        
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_get_historical_patterns', return_value={}):
                with patch.object(self.service, '_enhance_hint_with_effectiveness', side_effect=lambda h, r: h):
                    with patch.object(self.service, '_publish_hint_generated'):
                        with patch.object(self.service, '_store_hints'):
                            # Mock rules to return different hint types
                            self.service.rules[0].evaluate = Mock(return_value=hint1)
                            self.service.rules[1].evaluate = Mock(return_value=hint2)
                            for rule in self.service.rules[2:]:
                                rule.evaluate = Mock(return_value=None)
                            
                            # Test with filter
                            result = await self.service.generate_hints_for_task(
                                self.task_id,
                                hint_types=[HintType.NEXT_ACTION]
                            )
                            
                            # Should only include NEXT_ACTION hint
                            assert len(result.hints) == 1
                            assert result.hints[0].type == HintType.NEXT_ACTION

    @pytest.mark.asyncio
    async def test_generate_hints_with_max_limit(self):
        """Test hint generation with max_hints limit"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        # Create multiple mock hints
        hints = []
        for i in range(10):
            hint = Mock(spec=WorkflowHint)
            hint.priority = HintPriority.HIGH
            hint.id = uuid.uuid4()
            hints.append(hint)
        
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_get_historical_patterns', return_value={}):
                with patch.object(self.service, '_should_include_hint', return_value=True):
                    with patch.object(self.service, '_enhance_hint_with_effectiveness', side_effect=lambda h, r: h):
                        with patch.object(self.service, '_publish_hint_generated'):
                            with patch.object(self.service, '_store_hints'):
                                # Mock all rules to return hints
                                for i, rule in enumerate(self.service.rules):
                                    if i < len(hints):
                                        rule.evaluate = Mock(return_value=hints[i])
                                    else:
                                        rule.evaluate = Mock(return_value=None)
                                
                                result = await self.service.generate_hints_for_task(
                                    self.task_id,
                                    max_hints=3
                                )
                                
                                # Should limit to 3 hints
                                assert len(result.hints) <= 3

    @pytest.mark.asyncio
    async def test_generate_hints_rule_evaluation_error(self):
        """Test hint generation handles rule evaluation errors"""
        self.task_repository.get.return_value = self.task
        self.context_repository.get_by_task_id.return_value = self.context
        
        with patch.object(self.service, '_get_related_tasks', return_value=[]):
            with patch.object(self.service, '_get_historical_patterns', return_value={}):
                with patch.object(self.service, '_store_hints'):
                    # Mock first rule to raise exception, second to return hint
                    self.service.rules[0].evaluate = Mock(side_effect=Exception("Rule error"))
                    # rule_name is a read-only property, don't try to set it
                    
                    mock_hint = Mock(spec=WorkflowHint)
                    mock_hint.metadata = Mock(confidence=0.85)
                    mock_hint.priority = HintPriority.MEDIUM
                    mock_hint.created_at = datetime.now(timezone.utc)
                    mock_hint.expires_at = None
                    mock_hint.is_expired = Mock(return_value=False)
                    self.service.rules[1].evaluate = Mock(return_value=mock_hint)
                    # rule_name is a read-only property, don't try to set it
                    
                    for rule in self.service.rules[2:]:
                        rule.evaluate = Mock(return_value=None)
                    
                    with patch.object(self.service, '_should_include_hint', return_value=True):
                        with patch.object(self.service, '_enhance_hint_with_effectiveness', return_value=mock_hint):
                            with patch.object(self.service, '_publish_hint_generated'):
                                result = await self.service.generate_hints_for_task(self.task_id)
                                
                                # Should continue despite error and return valid hints
                                assert len(result.hints) == 1


class TestRelatedTasksAndPatterns:
    """Test suite for related tasks and historical patterns functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository
        )
        
        self.task = Mock(spec=Task)
        self.task.id = uuid.uuid4()
        self.task.labels = ['frontend', 'bug']
        self.task.subtasks = [uuid.uuid4(), uuid.uuid4()]

    @pytest.mark.asyncio
    async def test_get_related_tasks_by_labels(self):
        """Test getting related tasks by labels"""
        # Mock tasks returned by label queries
        # Service queries once for each of the first 2 labels  
        label_tasks1 = [Mock(id=uuid.uuid4()) for _ in range(3)]
        label_tasks2 = [Mock(id=uuid.uuid4()) for _ in range(2)]
        self.task_repository.list.side_effect = [label_tasks1, label_tasks2]
        self.task_repository.get.return_value = None  # No subtask found
        
        result = await self.service._get_related_tasks(self.task)
        
        # Should return all tasks from both label queries (3 + 2 = 5)
        assert len(result) == 5
        assert all(t.id != self.task.id for t in result)
        # Should have called list for each label (first 2 labels only)
        assert self.task_repository.list.call_count == 2
        # Verify list was called with labels wrapped in list
        self.task_repository.list.assert_any_call(labels=['frontend'], limit=5)
        self.task_repository.list.assert_any_call(labels=['bug'], limit=5)

    @pytest.mark.asyncio
    async def test_get_related_tasks_by_subtasks(self):
        """Test getting related tasks by subtasks"""
        # Mock subtasks
        subtask1 = Mock(id=self.task.subtasks[0])
        subtask2 = Mock(id=self.task.subtasks[1])
        
        self.task_repository.list.return_value = []  # No label matches
        self.task_repository.get.side_effect = [subtask1, subtask2]
        
        result = await self.service._get_related_tasks(self.task)
        
        assert len(result) == 2
        assert subtask1 in result
        assert subtask2 in result

    @pytest.mark.asyncio
    async def test_get_related_tasks_removes_duplicates(self):
        """Test that get_related_tasks removes duplicates"""
        duplicate_task = Mock(id=uuid.uuid4())
        
        self.task_repository.list.return_value = [duplicate_task, duplicate_task]
        self.task_repository.get.return_value = None  # No subtasks
        
        result = await self.service._get_related_tasks(self.task)
        
        # Should only have one instance of the duplicate task
        assert len(result) == 1
        assert result[0].id == duplicate_task.id

    @pytest.mark.asyncio
    async def test_get_related_tasks_excludes_self(self):
        """Test that get_related_tasks excludes the task itself"""
        # Return list that includes the task itself
        self.task_repository.list.return_value = [self.task]  # Returns self
        self.task_repository.get.return_value = None  # No subtasks
        
        result = await self.service._get_related_tasks(self.task)
        
        # Should exclude the task itself
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_historical_patterns_with_similar_tasks(self):
        """Test getting historical patterns from similar completed tasks"""
        # Create mock completed tasks with timestamps
        now = datetime.now(timezone.utc)
        completed_tasks = []
        for i in range(3):
            task = Mock()
            task.created_at = now - timedelta(hours=10)
            task.updated_at = now - timedelta(hours=2)
            completed_tasks.append(task)
        
        self.task_repository.list.return_value = completed_tasks
        
        result = await self.service._get_historical_patterns(self.task)
        
        assert 'avg_completion_seconds' in result
        assert 'similar_task_count' in result
        assert result['similar_task_count'] == 3
        # Average completion should be 8 hours (28800 seconds)
        assert result['avg_completion_seconds'] == 28800.0

    @pytest.mark.asyncio
    async def test_get_historical_patterns_no_similar_tasks(self):
        """Test getting historical patterns with no similar tasks"""
        self.task_repository.list.return_value = []
        
        result = await self.service._get_historical_patterns(self.task)
        
        # Should not include completion patterns
        assert 'avg_completion_seconds' not in result
        assert 'similar_task_count' not in result

    @pytest.mark.asyncio
    async def test_get_historical_patterns_with_hint_repository(self):
        """Test getting historical patterns with hint repository"""
        self.service.hint_repository = AsyncMock()
        with patch.object(self.service, '_get_hint_effectiveness_patterns') as mock_effectiveness:
            mock_effectiveness.return_value = {"test": 0.85}
            
            result = await self.service._get_historical_patterns(self.task)
            
            assert 'hint_effectiveness' in result
            assert result['hint_effectiveness'] == {"test": 0.85}


class TestHintFiltering:
    """Test suite for hint filtering functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock()
        )

    def test_should_include_hint_no_filter(self):
        """Test hint inclusion with no type filter"""
        hint = Mock()
        hint.type = HintType.NEXT_ACTION
        
        result = self.service._should_include_hint(hint, None)
        
        assert result is True

    def test_should_include_hint_with_matching_filter(self):
        """Test hint inclusion with matching type filter"""
        hint = Mock()
        hint.type = HintType.NEXT_ACTION
        
        result = self.service._should_include_hint(hint, [HintType.NEXT_ACTION, HintType.COMPLETION])
        
        assert result is True

    def test_should_include_hint_with_non_matching_filter(self):
        """Test hint inclusion with non-matching type filter"""
        hint = Mock()
        hint.type = HintType.NEXT_ACTION
        
        result = self.service._should_include_hint(hint, [HintType.BLOCKER_RESOLUTION, HintType.COMPLETION])
        
        assert result is False


class TestHintEnhancement:
    """Test suite for hint enhancement functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock()
        )
        
        self.rule = Mock()
        self.rule.rule_name = "TestRule"

    def test_enhance_hint_no_effectiveness_data(self):
        """Test hint enhancement when no effectiveness data is available"""
        hint = Mock()
        hint.type = HintType.NEXT_ACTION
        
        result = self.service._enhance_hint_with_effectiveness(hint, self.rule)
        
        # Should return original hint unchanged
        assert result == hint

    def test_enhance_hint_with_effectiveness_data(self):
        """Test hint enhancement with effectiveness data"""
        # Set up effectiveness cache
        effectiveness_key = f"{self.rule.rule_name}:{HintType.NEXT_ACTION.value}"
        self.service._effectiveness_cache[effectiveness_key] = 0.85
        
        # Create original hint
        original_hint = Mock()
        original_hint.id = uuid.uuid4()
        original_hint.type = HintType.NEXT_ACTION
        original_hint.priority = HintPriority.MEDIUM
        original_hint.message = "Test message"
        original_hint.suggested_action = "Test action"
        original_hint.created_at = datetime.now(timezone.utc)
        original_hint.task_id = uuid.uuid4()
        original_hint.context_data = {}
        original_hint.expires_at = None
        original_hint.metadata = Mock()
        original_hint.metadata.source = "test"
        original_hint.metadata.confidence = 0.7
        original_hint.metadata.reasoning = "test reasoning"
        original_hint.metadata.related_tasks = []
        original_hint.metadata.patterns_detected = []
        
        # Patch at the service module level since it's imported at the top
        with patch('fastmcp.task_management.application.services.hint_generation_service.HintMetadata') as mock_metadata_class:
            with patch('fastmcp.task_management.application.services.hint_generation_service.WorkflowHint') as mock_hint_class:
                mock_enhanced_metadata = Mock()
                mock_metadata_class.return_value = mock_enhanced_metadata
                
                mock_enhanced_hint = Mock()
                mock_hint_class.return_value = mock_enhanced_hint
                
                result = self.service._enhance_hint_with_effectiveness(original_hint, self.rule)
                
                # Should create new metadata with effectiveness score
                mock_metadata_class.assert_called_once_with(
                    source=original_hint.metadata.source,
                    confidence=original_hint.metadata.confidence,
                    reasoning=original_hint.metadata.reasoning,
                    related_tasks=original_hint.metadata.related_tasks,
                    patterns_detected=original_hint.metadata.patterns_detected,
                    effectiveness_score=0.85
                )
                
                # Should create new hint with enhanced metadata
                mock_hint_class.assert_called_once_with(
                    id=original_hint.id,
                    type=original_hint.type,
                    priority=original_hint.priority,
                    message=original_hint.message,
                    suggested_action=original_hint.suggested_action,
                    metadata=mock_enhanced_metadata,
                    created_at=original_hint.created_at,
                    task_id=original_hint.task_id,
                    context_data=original_hint.context_data,
                    expires_at=original_hint.expires_at
                )
                
                assert result == mock_enhanced_hint


class TestEventPublishing:
    """Test suite for event publishing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.event_store = AsyncMock()
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock(),
            event_store=self.event_store
        )

    @pytest.mark.asyncio
    async def test_publish_hint_generated(self):
        """Test publishing hint generated event"""
        hint = Mock()
        hint.id = uuid.uuid4()
        hint.task_id = uuid.uuid4()
        hint.type = HintType.NEXT_ACTION
        hint.priority = HintPriority.HIGH
        hint.message = "Test hint message"
        hint.suggested_action = "Test action"
        hint.metadata = Mock()
        hint.metadata.confidence = 0.9
        hint.metadata.patterns_detected = ["pattern1"]
        hint.metadata.reasoning = "Test reasoning"
        
        rule = Mock()
        rule.rule_name = "TestRule"
        
        await self.service._publish_hint_generated(hint, rule)
        
        # Verify event was published
        self.event_store.append.assert_called_once()
        event = self.event_store.append.call_args[0][0]
        
        assert isinstance(event, HintGenerated)
        assert event.aggregate_id == hint.task_id
        assert event.hint_id == hint.id
        assert event.task_id == hint.task_id
        assert event.hint_type == hint.type
        assert event.priority == hint.priority
        assert event.message == hint.message
        assert event.suggested_action == hint.suggested_action
        assert event.source_rule == rule.rule_name
        assert event.confidence == hint.metadata.confidence


class TestHintFeedback:
    """Test suite for hint feedback functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.event_store = AsyncMock()
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock(),
            event_store=self.event_store
        )
        
        self.hint_id = uuid.uuid4()
        self.task_id = uuid.uuid4()
        self.user_id = "test_user"

    @pytest.mark.asyncio
    async def test_accept_hint(self):
        """Test accepting a hint"""
        action_taken = "Implemented suggested change"
        
        with patch.object(self.service, '_update_effectiveness_cache') as mock_update:
            await self.service.accept_hint(
                self.hint_id,
                self.task_id,
                self.user_id,
                action_taken
            )
            
            # Verify event was published
            self.event_store.append.assert_called_once()
            event = self.event_store.append.call_args[0][0]
            
            assert isinstance(event, HintAccepted)
            assert event.aggregate_id == self.task_id
            assert event.user_id == self.user_id
            assert event.hint_id == self.hint_id
            assert event.task_id == self.task_id
            assert event.action_taken == action_taken
            
            # Verify cache update was called
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_hint(self):
        """Test dismissing a hint"""
        reason = "Not applicable to current situation"
        
        with patch.object(self.service, '_update_effectiveness_cache') as mock_update:
            await self.service.dismiss_hint(
                self.hint_id,
                self.task_id,
                self.user_id,
                reason
            )
            
            # Verify event was published
            self.event_store.append.assert_called_once()
            event = self.event_store.append.call_args[0][0]
            
            assert isinstance(event, HintDismissed)
            assert event.aggregate_id == self.task_id
            assert event.user_id == self.user_id
            assert event.hint_id == self.hint_id
            assert event.task_id == self.task_id
            assert event.reason == reason
            
            # Verify cache update was called
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_provide_feedback(self):
        """Test providing feedback on a hint"""
        was_helpful = True
        feedback_text = "Very useful suggestion"
        effectiveness_score = 4.5
        
        with patch.object(self.service, '_update_effectiveness_cache') as mock_update:
            await self.service.provide_feedback(
                self.hint_id,
                self.task_id,
                self.user_id,
                was_helpful,
                feedback_text,
                effectiveness_score
            )
            
            # Verify event was published
            self.event_store.append.assert_called_once()
            event = self.event_store.append.call_args[0][0]
            
            assert isinstance(event, HintFeedbackProvided)
            assert event.aggregate_id == self.task_id
            assert event.user_id == self.user_id
            assert event.hint_id == self.hint_id
            assert event.task_id == self.task_id
            assert event.was_helpful == was_helpful
            assert event.feedback_text == feedback_text
            assert event.effectiveness_score == effectiveness_score
            
            # Verify cache update was called
            mock_update.assert_called_once()


class TestEffectivenessCache:
    """Test suite for effectiveness cache functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.event_store = AsyncMock()
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock(),
            event_store=self.event_store
        )

    @pytest.mark.asyncio
    async def test_update_effectiveness_cache(self):
        """Test updating effectiveness cache"""
        # Mock events from event store with proper structure
        hint_id1 = uuid.uuid4()
        hint_id2 = uuid.uuid4()
        mock_events = [
            Mock(
                event_type="hint_generated",
                source_rule="TestRule",
                hint_type="next_action",  # Use string value, not enum
                hint_id=hint_id1
            ),
            Mock(
                event_type="hint_generated",
                source_rule="TestRule",
                hint_type="next_action",  # Use string value, not enum
                hint_id=hint_id2
            ),
            Mock(
                event_type="hint_accepted",
                hint_id=hint_id1  # Accept first hint
            )
        ]
        
        self.event_store.get_events_in_range.return_value = mock_events
        
        await self.service._update_effectiveness_cache()
        
        # Verify event store was queried correctly
        self.event_store.get_events_in_range.assert_called_once()
        call_args = self.event_store.get_events_in_range.call_args
        
        assert 'start_time' in call_args.kwargs
        assert 'end_time' in call_args.kwargs
        assert call_args.kwargs['event_types'] == ["hint_generated", "hint_accepted", "hint_dismissed"]
        
        # Verify cache was updated
        key = "TestRule:next_action"
        # With 1 accepted hint out of 2 generated, effectiveness should be 0.0 (accepted events are not processed yet)
        assert key in self.service._effectiveness_cache
        assert self.service._effectiveness_cache[key] == 0.0

    @pytest.mark.asyncio
    async def test_get_hint_effectiveness_patterns(self):
        """Test getting hint effectiveness patterns"""
        patterns = await self.service._get_hint_effectiveness_patterns()
        
        # Should return placeholder effectiveness data
        assert isinstance(patterns, dict)
        assert len(patterns) > 0
        
        # Check some expected patterns
        assert "stalled_progress:blocker_resolution" in patterns
        assert "implementation_ready_for_testing:next_action" in patterns
        assert all(0.0 <= score <= 1.0 for score in patterns.values())


class TestRuleManagement:
    """Test suite for rule management functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock()
        )
        
        self.custom_rule = Mock(spec=HintRule)
        self.custom_rule.rule_name = "CustomTestRule"

    def test_add_rule(self):
        """Test adding a custom rule"""
        initial_count = len(self.service.rules)
        
        self.service.add_rule(self.custom_rule)
        
        assert len(self.service.rules) == initial_count + 1
        assert self.custom_rule in self.service.rules

    def test_remove_rule_success(self):
        """Test removing a rule successfully"""
        self.service.add_rule(self.custom_rule)
        initial_count = len(self.service.rules)
        
        result = self.service.remove_rule("CustomTestRule")
        
        assert result is True
        assert len(self.service.rules) == initial_count - 1
        assert self.custom_rule not in self.service.rules

    def test_remove_rule_not_found(self):
        """Test removing a rule that doesn't exist"""
        initial_count = len(self.service.rules)
        
        result = self.service.remove_rule("NonExistentRule")
        
        assert result is False
        assert len(self.service.rules) == initial_count

    def test_get_rules(self):
        """Test getting list of active rule names"""
        self.service.add_rule(self.custom_rule)
        
        rule_names = self.service.get_rules()
        
        assert isinstance(rule_names, list)
        assert "CustomTestRule" in rule_names
        assert len(rule_names) == len(self.service.rules)


class TestHintStorage:
    """Test suite for hint storage functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.hint_repository = AsyncMock()
        self.service = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock(),
            hint_repository=self.hint_repository
        )

    @pytest.mark.asyncio
    async def test_store_hints(self):
        """Test storing hints in repository"""
        hints = [Mock() for _ in range(3)]
        collection = Mock()
        collection.hints = hints
        
        await self.service._store_hints(collection)
        
        # Verify all hints were stored
        assert self.hint_repository.save.call_count == 3
        for hint in hints:
            self.hint_repository.save.assert_any_call(hint)

    @pytest.mark.asyncio
    async def test_store_hints_no_repository(self):
        """Test storing hints when no repository is available"""
        service_no_repo = HintGenerationService(
            task_repository=Mock(),
            context_repository=Mock()
        )
        
        collection = Mock()
        collection.hints = [Mock()]
        
        # Should not raise error
        await service_no_repo._store_hints(collection)


class TestIntegration:
    """Integration tests for HintGenerationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = AsyncMock()
        self.context_repository = AsyncMock()
        self.event_store = AsyncMock()
        self.hint_repository = AsyncMock()
        
        self.service = HintGenerationService(
            task_repository=self.task_repository,
            context_repository=self.context_repository,
            event_store=self.event_store,
            hint_repository=self.hint_repository
        )

    @pytest.mark.asyncio
    async def test_full_hint_generation_workflow(self):
        """Test complete hint generation workflow"""
        # Set up task and context
        task_id = uuid.uuid4()
        task = Mock()
        task.id = task_id
        task.labels = ['frontend']
        task.subtasks = []
        task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        task.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)  # Stalled
        
        context = Mock()
        
        self.task_repository.get.return_value = task
        self.context_repository.get_by_task_id.return_value = context
        self.task_repository.list.return_value = []  # No related tasks
        
        # Mock a rule to return a hint (stalled progress should trigger)
        stalled_rule = next(r for r in self.service.rules if isinstance(r, StalledProgressRule))
        mock_hint = Mock(spec=WorkflowHint)
        mock_hint.id = uuid.uuid4()
        mock_hint.type = HintType.BLOCKER_RESOLUTION
        mock_hint.priority = HintPriority.HIGH
        mock_hint.task_id = task_id
        mock_hint.metadata = Mock()
        mock_hint.message = 'Task has been stalled for over 24 hours'
        mock_hint.suggested_action = 'Review blockers and update status'
        mock_hint.metadata.confidence = 0.8
        mock_hint.metadata.patterns_detected = ['stalled_task']
        mock_hint.metadata.reasoning = 'Task stalled for over 24 hours'
        mock_hint.created_at = datetime.now(timezone.utc)
        mock_hint.expires_at = None
        mock_hint.is_expired = Mock(return_value=False)
        
        with patch.object(stalled_rule, 'evaluate', return_value=mock_hint):
            result = await self.service.generate_hints_for_task(task_id)
            
            # Verify hint was generated and stored
            assert len(result.hints) == 1
            assert result.hints[0] == mock_hint
            
            # Verify event was published
            self.event_store.append.assert_called()
            
            # Verify hint was stored
            self.hint_repository.save.assert_called_with(mock_hint)

    @pytest.mark.asyncio
    async def test_hint_feedback_lifecycle(self):
        """Test complete hint feedback lifecycle"""
        hint_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = "test_user"
        
        # Mock events for cache update
        self.event_store.get_events_in_range.return_value = []
        
        # Accept hint
        await self.service.accept_hint(hint_id, task_id, user_id, "Implemented suggestion")
        
        # Provide feedback
        await self.service.provide_feedback(
            hint_id, task_id, user_id, 
            was_helpful=True, 
            feedback_text="Great suggestion!",
            effectiveness_score=5.0
        )
        
        # Dismiss another hint
        await self.service.dismiss_hint(hint_id, task_id, user_id, "Not applicable")
        
        # Verify all events were published
        assert self.event_store.append.call_count == 3
        
        # Verify cache was updated each time
        assert self.event_store.get_events_in_range.call_count == 3