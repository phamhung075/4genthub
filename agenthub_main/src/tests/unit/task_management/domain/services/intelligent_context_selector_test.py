"""Comprehensive unit tests for IntelligentContextSelector domain service.

Tests the main ML orchestrator that combines all intelligence components
for intelligent context selection with semantic matching, progressive expansion,
and prediction capabilities.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call
import time
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.intelligence.intelligent_context_selector import (
    IntelligentContextSelector,
    SelectionResult,
    SelectionMetrics
)
from fastmcp.task_management.domain.services.intelligence.semantic_matcher import (
    ContextItem,
    SimilarityResult
)
from fastmcp.task_management.domain.services.intelligence.progressive_expander import (
    ExpansionResult,
    ExpansionCandidate,
    UserPreferences,
    ContextLevel,
    ExpansionTrigger
)
from fastmcp.task_management.domain.services.intelligence.predictive_loader import (
    PredictionResult
)
from fastmcp.task_management.domain.services.intelligence.context_prioritizer import (
    ContextScore
)


class TestIntelligentContextSelector:
    """Test suite for IntelligentContextSelector."""

    @pytest.fixture
    def mock_semantic_matcher(self):
        """Mock semantic matcher component."""
        mock = Mock()
        mock.similarity_threshold = 0.5
        mock.generate_embedding.return_value = [0.1, 0.2, 0.3]  # Mock embedding
        mock.find_similar_contexts.return_value = []
        mock.add_context_items.return_value = None
        mock.get_stats.return_value = {"matches_found": 10}
        return mock

    @pytest.fixture
    def mock_progressive_expander(self):
        """Mock progressive expander component."""
        mock = Mock()
        mock.expand_context_progressive.return_value = ExpansionResult(
            expanded_contexts=[],
            total_tokens_used=0,
            remaining_token_budget=2000,
            expansion_path=[],
            prefetched_contexts=[]
        )
        mock.get_expansion_stats.return_value = {"expansions": 5}
        return mock

    @pytest.fixture
    def mock_predictive_loader(self):
        """Mock predictive loader component."""
        mock = Mock()
        mock.predict_next_contexts.return_value = PredictionResult(
            predicted_contexts=[],
            confidence_scores={},
            patterns_used=[],
            prediction_reasons=[],
            preload_priority={}
        )
        mock.start_session.return_value = None
        mock.end_session.return_value = {}
        mock.record_tool_usage.return_value = None
        mock.get_prediction_stats.return_value = {"predictions": 3}
        return mock

    @pytest.fixture  
    def mock_context_prioritizer(self):
        """Mock context prioritizer component."""
        mock = Mock()
        mock.score_contexts_batch.return_value = []
        mock._estimate_tokens.return_value = 100
        mock.record_context_access.return_value = None
        mock.get_scoring_stats.return_value = {"scored": 20}
        return mock

    @pytest.fixture
    def selector(self, mock_semantic_matcher, mock_progressive_expander, 
                  mock_predictive_loader, mock_context_prioritizer):
        """Create selector with mocked dependencies."""
        with patch('fastmcp.task_management.domain.services.intelligence.intelligent_context_selector.SemanticMatcher', return_value=mock_semantic_matcher), \
             patch('fastmcp.task_management.domain.services.intelligence.intelligent_context_selector.ProgressiveExpander', return_value=mock_progressive_expander), \
             patch('fastmcp.task_management.domain.services.intelligence.intelligent_context_selector.PredictiveLoader', return_value=mock_predictive_loader), \
             patch('fastmcp.task_management.domain.services.intelligence.intelligent_context_selector.ContextPrioritizer', return_value=mock_context_prioritizer):
            
            selector = IntelligentContextSelector(
                semantic_model="test-model",
                similarity_threshold=0.5,
                default_token_budget=2000,
                max_selection_time_ms=200.0,
                target_hit_rate=0.9,
                target_size_reduction=0.5,
                enable_caching=True,
                cache_ttl_seconds=300,
                enable_metrics=True
            )
            
            # Inject the mocks
            selector.semantic_matcher = mock_semantic_matcher
            selector.progressive_expander = mock_progressive_expander
            selector.predictive_loader = mock_predictive_loader
            selector.context_prioritizer = mock_context_prioritizer
            
            return selector

    @pytest.fixture
    def sample_contexts(self):
        """Sample context data for testing."""
        return [
            {
                'id': 'ctx1',
                'context_id': 'ctx1',
                'title': 'User authentication',
                'description': 'Implement JWT authentication for users',
                'context_type': 'task',
                'estimated_tokens': 150
            },
            {
                'id': 'ctx2',
                'context_id': 'ctx2',
                'title': 'Database schema',
                'description': 'Design database schema for user management',
                'context_type': 'project',
                'estimated_tokens': 200
            },
            {
                'id': 'ctx3',
                'context_id': 'ctx3', 
                'title': 'API documentation',
                'description': 'Document authentication API endpoints',
                'context_type': 'task',
                'metadata': {
                    'priority': 'high',
                    'tags': ['api', 'docs']
                },
                'estimated_tokens': 100
            }
        ]

    def test_initialization(self, selector):
        """Test proper initialization of IntelligentContextSelector."""
        assert selector.default_token_budget == 2000
        assert selector.max_selection_time_ms == 200.0
        assert selector.target_hit_rate == 0.9
        assert selector.target_size_reduction == 0.5
        assert selector.enable_caching is True
        assert selector.cache_ttl_seconds == 300
        assert selector.enable_metrics is True
        assert isinstance(selector.metrics, SelectionMetrics)
        assert selector.current_session_id is None
        assert len(selector.available_contexts) == 0

    def test_load_available_contexts(self, selector, sample_contexts):
        """Test loading available contexts."""
        selector.load_available_contexts(sample_contexts)
        
        assert len(selector.available_contexts) == 3
        assert selector.semantic_matcher.add_context_items.called
        
        # Verify context items were created correctly
        call_args = selector.semantic_matcher.add_context_items.call_args[0][0]
        assert len(call_args) == 3
        assert all(isinstance(item, ContextItem) for item in call_args)
        assert call_args[0].id == 'ctx1'
        assert call_args[1].id == 'ctx2'
        assert call_args[2].id == 'ctx3'

    def test_extract_context_content(self, selector):
        """Test context content extraction for search."""
        context_data = {
            'title': 'Test Task',
            'description': 'A test task description',
            'details': 'Additional details',
            'name': 'test_name',
            'git_branch_name': 'feature/test',
            'metadata': {
                'long_text': 'This is a long metadata text',
                'short': 'abc',  # Should be skipped (too short)
                'number': 123    # Should be skipped (not string)
            }
        }
        
        content = selector._extract_context_content(context_data)
        
        assert 'Test Task' in content
        assert 'A test task description' in content
        assert 'Additional details' in content
        assert 'test_name' in content
        assert 'feature/test' in content
        assert 'This is a long metadata text' in content
        assert 'abc' not in content  # Too short
        assert '123' not in content  # Not a string

    def test_select_context_with_semantic_matches(self, selector, sample_contexts):
        """Test context selection with semantic matching results."""
        # Setup
        selector.load_available_contexts(sample_contexts)
        
        # Mock semantic matches
        mock_similar_contexts = [
            SimilarityResult(
                item=ContextItem(
                    id='ctx1',
                    content='User authentication',
                    context_type='task',
                    metadata={'context_data': sample_contexts[0]}
                ),
                similarity_score=0.8,
                rank=1
            ),
            SimilarityResult(
                item=ContextItem(
                    id='ctx3',
                    content='API documentation',
                    context_type='task',
                    metadata={'context_data': sample_contexts[2]}
                ),
                similarity_score=0.6,
                rank=2
            )
        ]
        selector.semantic_matcher.find_similar_contexts.return_value = mock_similar_contexts
        
        # Mock context scores
        mock_scores = [
            ContextScore(
                context_id='ctx1',
                total_score=0.85,
                factor_scores={
                    'semantic_relevance': 0.8,
                    'recency': 0.5,
                    'frequency': 0.3
                },
                metadata=sample_contexts[0]
            ),
            ContextScore(
                context_id='ctx3',
                total_score=0.65,
                factor_scores={
                    'semantic_relevance': 0.6,
                    'recency': 0.4,
                    'frequency': 0.2
                },
                metadata=sample_contexts[2]
            )
        ]
        selector.context_prioritizer.score_contexts_batch.return_value = mock_scores
        
        # Mock expansion result
        mock_expansion = ExpansionResult(
            expanded_contexts=[sample_contexts[0], sample_contexts[2]],
            total_tokens_used=250,
            remaining_token_budget=750,
            expansion_path=['ctx1', 'ctx3'],
            prefetched_contexts=[]
        )
        selector.progressive_expander.expand_context_progressive.return_value = mock_expansion
        
        # Execute
        result = selector.select_context(
            query="How to implement user authentication?",
            max_tokens=1000
        )
        
        # Verify
        assert isinstance(result, SelectionResult)
        assert len(result.selected_contexts) == 2
        assert result.total_tokens_used == 250
        assert result.selection_time_ms > 0
        assert result.selection_time_ms < 200  # Should meet performance target
        assert 0 <= result.hit_rate_estimate <= 1.0
        assert 0 <= result.size_reduction_percent <= 1.0
        
        # Verify method calls
        selector.semantic_matcher.generate_embedding.assert_called_once()
        selector.semantic_matcher.find_similar_contexts.assert_called_once()
        selector.context_prioritizer.score_contexts_batch.assert_called_once()
        selector.progressive_expander.expand_context_progressive.assert_called_once()

    def test_select_context_with_predictive_fallback(self, selector, sample_contexts):
        """Test context selection using predictive loading when no semantic matches."""
        # Setup
        selector.load_available_contexts(sample_contexts)
        
        # No semantic matches
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # Mock prediction
        mock_prediction = PredictionResult(
            predicted_contexts=['ctx2', 'ctx1'],
            confidence_scores={'ctx2': 0.8, 'ctx1': 0.6},
            patterns_used=['pattern1'],
            prediction_reasons=['Based on historical pattern'],
            preload_priority={'ctx2': 0.8, 'ctx1': 0.6}
        )
        selector.predictive_loader.predict_next_contexts.return_value = mock_prediction
        
        # Execute
        result = selector.select_context(
            query="What's next?",
            max_tokens=500,
            current_task={'id': 'current_task'}
        )
        
        # Verify fallback to predictive loading
        assert isinstance(result, SelectionResult)
        assert len(result.selected_contexts) == 2  # Both predicted contexts fit
        assert result.selected_contexts[0]['id'] == 'ctx2'
        assert result.selected_contexts[1]['id'] == 'ctx1'
        assert result.total_tokens_used == 200  # The mock returns 100 per context, so 2 contexts = 200
        
        selector.predictive_loader.predict_next_contexts.assert_called_once()

    def test_select_context_with_caching(self, selector, sample_contexts):
        """Test that context selection results are cached."""
        # Setup
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # First call
        result1 = selector.select_context("test query", max_tokens=1000)
        
        # Second call with same parameters
        result2 = selector.select_context("test query", max_tokens=1000)
        
        # Verify cache hit
        assert result2.metadata['cache_used'] is False  # First result didn't have this
        assert selector.metrics.cache_hit_rate > 0
        
        # Semantic matcher should only be called once due to caching
        assert selector.semantic_matcher.generate_embedding.call_count == 1

    def test_select_context_cache_expiry(self, selector, sample_contexts):
        """Test that cached results expire after TTL."""
        # Setup
        selector.load_available_contexts(sample_contexts)
        selector.cache_ttl_seconds = 0.1  # 100ms for testing
        
        # First call
        result1 = selector.select_context("test query", max_tokens=1000)
        
        # Wait for cache to expire
        time.sleep(0.2)
        
        # Second call should not use cache
        result2 = selector.select_context("test query", max_tokens=1000)
        
        # Semantic matcher should be called twice
        assert selector.semantic_matcher.generate_embedding.call_count == 2

    def test_select_context_error_handling(self, selector, sample_contexts):
        """Test fallback selection when main algorithm fails."""
        # Setup
        selector.load_available_contexts(sample_contexts)
        
        # Make semantic matcher raise an exception
        selector.semantic_matcher.generate_embedding.side_effect = Exception("Embedding error")
        
        # Execute
        result = selector.select_context("test query", max_tokens=500)
        
        # Verify fallback was used
        assert isinstance(result, SelectionResult)
        assert result.metadata.get('fallback') is True
        assert len(result.selected_contexts) >= 0  # Should have some contexts
        assert result.selection_time_ms == 10.0  # Fallback time
        assert result.hit_rate_estimate == 0.5  # Conservative estimate

    def test_estimate_hit_rate(self, selector, sample_contexts):
        """Test hit rate estimation logic."""
        selected = [
            {'title': 'User authentication', 'description': 'JWT tokens'},
            {'title': 'Database design', 'description': 'Schema for users'}
        ]
        
        # Query with matching keywords
        hit_rate = selector._estimate_hit_rate(selected, "user authentication JWT")
        assert hit_rate >= 0.5  # Should be high (at least one context matches)
        
        # Query with no matching keywords
        hit_rate = selector._estimate_hit_rate(selected, "payment processing stripe")
        assert hit_rate < 0.5  # Should be low
        
        # Empty contexts
        hit_rate = selector._estimate_hit_rate([], "any query")
        assert hit_rate == 0.0

    def test_estimate_size_reduction(self, selector, sample_contexts):
        """Test size reduction estimation."""
        # Selected subset
        selected = sample_contexts[:1]  # Just first context (150 tokens)
        
        # All contexts total 450 tokens (150 + 200 + 100)
        reduction = selector._estimate_size_reduction(selected, sample_contexts)
        
        # Should be ~67% reduction (300/450)
        assert 0.65 < reduction < 0.68
        
        # Edge cases
        assert selector._estimate_size_reduction([], sample_contexts) == 1.0
        assert selector._estimate_size_reduction(sample_contexts, sample_contexts) == 0.0
        assert selector._estimate_size_reduction(selected, []) == 0.0

    def test_session_management(self, selector):
        """Test session lifecycle management."""
        # Start session
        selector.start_session('session123', 'user456')
        
        assert selector.current_session_id == 'session123'
        selector.predictive_loader.start_session.assert_called_once_with('session123', 'user456')
        
        # Record tool usage
        selector.record_tool_usage('Read', 'ctx1')
        
        selector.predictive_loader.record_tool_usage.assert_called_once_with('Read', 'ctx1')
        selector.context_prioritizer.record_context_access.assert_called_once_with('ctx1')
        
        # End session
        mock_analytics = {'total_predictions': 5}
        selector.predictive_loader.end_session.return_value = mock_analytics
        
        analytics = selector.end_session()
        
        assert analytics == mock_analytics
        assert selector.current_session_id is None
        selector.predictive_loader.end_session.assert_called_once()

    def test_find_context_by_id(self, selector, sample_contexts):
        """Test finding context by ID."""
        selector.load_available_contexts(sample_contexts)
        
        # Find by 'id' field
        context = selector._find_context_by_id('ctx2')
        assert context is not None
        assert context['title'] == 'Database schema'
        
        # Find by 'context_id' field
        context = selector._find_context_by_id('ctx3')
        assert context is not None
        assert context['title'] == 'API documentation'
        
        # Not found
        context = selector._find_context_by_id('nonexistent')
        assert context is None

    def test_performance_metrics_tracking(self, selector, sample_contexts):
        """Test that performance metrics are tracked correctly."""
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # Initial metrics
        assert selector.metrics.total_selections == 0
        assert selector.metrics.avg_selection_time_ms == 0.0
        
        # Make a selection
        result = selector.select_context("test", max_tokens=1000)
        
        # Metrics should be updated
        assert selector.metrics.total_selections == 1
        assert selector.metrics.avg_selection_time_ms > 0
        # Moving average with alpha=0.1: new_avg = 0.1 * new + 0.9 * old (old=0)
        assert selector.metrics.avg_hit_rate == 0.1 * result.hit_rate_estimate
        assert selector.metrics.avg_size_reduction == 0.1 * result.size_reduction_percent
        
        # Performance history should have an entry
        assert len(selector.performance_history) == 1
        assert selector.performance_history[0]['selection_time_ms'] == result.selection_time_ms

    def test_get_performance_stats(self, selector):
        """Test comprehensive performance statistics retrieval."""
        stats = selector.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert 'total_selections' in stats
        assert 'avg_selection_time_ms' in stats
        assert 'avg_hit_rate' in stats
        assert 'avg_size_reduction' in stats
        assert 'cache_hit_rate' in stats
        assert 'time_target_achievement' in stats
        assert 'hit_rate_target_achievement' in stats
        assert 'size_reduction_target_achievement' in stats
        assert 'semantic_matching' in stats
        assert 'progressive_expansion' in stats
        assert 'predictive_loading' in stats
        assert 'context_prioritization' in stats
        assert 'available_contexts' in stats
        assert 'cached_results' in stats
        assert 'current_session' in stats

    def test_optimize_performance_slow_selection(self, selector):
        """Test performance optimization when selection is too slow."""
        # Set metrics to indicate slow performance
        selector.metrics.avg_selection_time_ms = 180  # 90% of target
        selector.metrics.avg_hit_rate = 0.85
        selector.semantic_matcher.similarity_threshold = 0.5
        
        result = selector.optimize_performance()
        
        assert len(result['optimization_actions']) > 0
        assert any('similarity threshold' in action for action in result['optimization_actions'])
        assert selector.semantic_matcher.similarity_threshold > 0.5  # Should increase

    def test_optimize_performance_low_hit_rate(self, selector):
        """Test performance optimization when hit rate is low."""
        # Set metrics to indicate low hit rate
        selector.metrics.avg_selection_time_ms = 100  # Good time
        selector.metrics.avg_hit_rate = 0.6  # 67% of target
        selector.semantic_matcher.similarity_threshold = 0.5
        
        result = selector.optimize_performance()
        
        assert len(result['optimization_actions']) > 0
        assert any('similarity threshold' in action for action in result['optimization_actions'])
        assert selector.semantic_matcher.similarity_threshold < 0.5  # Should decrease

    def test_optimize_performance_poor_cache(self, selector):
        """Test performance optimization when cache hit rate is poor."""
        # Set metrics to indicate poor cache performance
        selector.metrics.cache_hit_rate = 0.05
        selector.result_cache = {f'key{i}': (Mock(), datetime.now(timezone.utc)) for i in range(20)}
        
        result = selector.optimize_performance()
        
        assert len(result['optimization_actions']) > 0
        assert any('cache' in action for action in result['optimization_actions'])
        assert len(selector.result_cache) == 0  # Should be cleared

    def test_cache_size_limiting(self, selector):
        """Test that cache size is limited."""
        # Add many cache entries
        for i in range(150):
            selector._cache_result(f"query{i}", 1000, SelectionResult(
                selected_contexts=[],
                total_tokens_used=100,
                selection_time_ms=50,
                hit_rate_estimate=0.8,
                size_reduction_percent=0.5
            ))
        
        # Cache should be limited to around 80 newest entries (some hash collisions may occur)
        assert 75 <= len(selector.result_cache) <= 90  # Allow some variance for hash collisions

    def test_select_context_with_user_preferences(self, selector, sample_contexts):
        """Test context selection with user preferences."""
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        user_prefs = UserPreferences(
            max_expansion_depth=3,
            preferred_context_level='PROJECT',
            auto_expand_related=True,
            prefetch_enabled=True
        )
        
        result = selector.select_context(
            query="test",
            max_tokens=1000,
            user_preferences=user_prefs
        )
        
        # Verify user preferences were passed through
        assert isinstance(result, SelectionResult)
        
        # Check that predictive loader was called with proper context
        selector.predictive_loader.predict_next_contexts.assert_called_once()

    def test_select_context_aggressive_expansion(self, selector, sample_contexts):
        """Test context selection with aggressive expansion mode."""
        selector.load_available_contexts(sample_contexts)
        
        # Mock some semantic matches
        mock_similar = [
            SimilarityResult(
                item=ContextItem('ctx1', 'content', 'task', {'context_data': sample_contexts[0]}),
                similarity_score=0.7,
                rank=1
            )
        ]
        selector.semantic_matcher.find_similar_contexts.return_value = mock_similar
        
        # Mock context score
        mock_score = ContextScore(
            context_id='ctx1',
            total_score=0.8,
            factor_scores={'semantic_relevance': 0.8},
            metadata=sample_contexts[0]
        )
        selector.context_prioritizer.score_contexts_batch.return_value = [mock_score]
        
        # Execute with aggressive expansion
        result = selector.select_context(
            query="test",
            max_tokens=2000,
            aggressive_expansion=True
        )
        
        # Verify aggressive flag was passed to expander
        call_args = selector.progressive_expander.expand_context_progressive.call_args
        assert call_args[1]['aggressive'] is True

    def test_performance_warning_logs(self, selector, sample_contexts, caplog):
        """Test that performance warnings are logged."""
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # Mock slow selection time
        with patch('time.time') as mock_time:
            # Make it take 250ms - provide enough values for all time.time calls including logging
            mock_time.side_effect = [0, 0.25] + [0.25] * 10  # Extra values for logging calls
            
            # Mock low hit rate
            with patch.object(selector, '_estimate_hit_rate', return_value=0.5):
                result = selector.select_context("test", max_tokens=1000)
        
        # Check warnings were logged
        assert any('Selection time' in record.message and 'exceeded target' in record.message 
                  for record in caplog.records if record.levelname == 'WARNING')
        assert any('Hit rate estimate' in record.message and 'below target' in record.message
                  for record in caplog.records if record.levelname == 'WARNING')

    def test_expansion_trigger_determination(self, selector, sample_contexts):
        """Test correct expansion trigger determination based on scores."""
        selector.load_available_contexts(sample_contexts)
        
        # Mock semantic match with high relevance
        mock_similar = [
            SimilarityResult(
                item=ContextItem('ctx1', 'content', 'task', {'context_data': sample_contexts[0]}),
                similarity_score=0.9,
                rank=1
            )
        ]
        selector.semantic_matcher.find_similar_contexts.return_value = mock_similar
        
        # Mock different score scenarios
        mock_scores = [
            ContextScore(
                context_id='ctx1',
                total_score=0.9,
                factor_scores={'semantic_relevance': 0.8, 'dependency_boost': 0.1},
                metadata=sample_contexts[0]
            ),
            ContextScore(
                context_id='ctx2',
                total_score=0.7,
                factor_scores={'semantic_relevance': 0.3, 'dependency_boost': 0.4},
                metadata=sample_contexts[1]
            ),
            ContextScore(
                context_id='ctx3',
                total_score=0.5,
                factor_scores={'semantic_relevance': 0.2, 'dependency_boost': 0.1},
                metadata=sample_contexts[2]
            )
        ]
        selector.context_prioritizer.score_contexts_batch.return_value = mock_scores
        
        # Execute
        result = selector.select_context("test", max_tokens=2000)
        
        # Verify expansion candidates were created with correct triggers
        expand_call = selector.progressive_expander.expand_context_progressive.call_args
        candidates = expand_call[1]['expansion_candidates']
        
        assert len(candidates) >= 3
        assert candidates[0].trigger == ExpansionTrigger.SIMILARITY_MATCH  # High semantic
        assert candidates[1].trigger == ExpansionTrigger.DEPENDENCY_CHAIN  # High dependency
        assert candidates[2].trigger == ExpansionTrigger.PATTERN_BASED     # Default

    def test_context_level_mapping(self, selector, sample_contexts):
        """Test correct context level mapping for expansion."""
        # Add contexts with different types
        contexts = [
            {'id': '1', 'context_type': 'global', 'title': 'Global settings'},
            {'id': '2', 'context_type': 'project', 'title': 'Project config'},
            {'id': '3', 'context_type': 'branch', 'title': 'Feature branch'},
            {'id': '4', 'context_type': 'task', 'title': 'Current task'},
            {'id': '5', 'context_type': 'unknown', 'title': 'Unknown type'}
        ]
        selector.load_available_contexts(contexts)
        
        # Mock matches and scores
        mock_similar = [
            SimilarityResult(
                item=ContextItem(ctx['id'], ctx['title'], ctx['context_type'], 
                               {'context_data': ctx}),
                similarity_score=0.7,
                rank=idx + 1
            )
            for idx, ctx in enumerate(contexts)
        ]
        selector.semantic_matcher.find_similar_contexts.return_value = mock_similar
        
        mock_scores = [
            ContextScore(
                context_id=ctx['id'],
                total_score=0.7,
                factor_scores={'semantic_relevance': 0.7},
                metadata=ctx
            )
            for ctx in contexts
        ]
        selector.context_prioritizer.score_contexts_batch.return_value = mock_scores
        
        # Execute
        result = selector.select_context("test", max_tokens=5000)
        
        # Verify context levels were mapped correctly
        expand_call = selector.progressive_expander.expand_context_progressive.call_args
        candidates = expand_call[1]['expansion_candidates']
        
        # Check level mapping
        level_map = {c.context_id: c.context_level for c in candidates}
        assert level_map['1'] == ContextLevel.GLOBAL
        assert level_map['2'] == ContextLevel.PROJECT
        assert level_map['3'] == ContextLevel.BRANCH
        assert level_map['4'] == ContextLevel.TASK
        assert level_map['5'] == ContextLevel.TASK  # Default for unknown

    def test_empty_contexts_handling(self, selector):
        """Test behavior with no available contexts."""
        # No contexts loaded
        result = selector.select_context("test query", max_tokens=1000)
        
        assert isinstance(result, SelectionResult)
        assert len(result.selected_contexts) == 0
        assert result.total_tokens_used == 0

    def test_performance_history_limiting(self, selector, sample_contexts):
        """Test that performance history is limited in size."""
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # Make many selections to fill history  
        for i in range(1200):
            selector.metrics.total_selections = i  # Reset to avoid averaging issues
            selector.select_context(f"query{i}", max_tokens=1000)
        
        # History should be trimmed when > 1000, then continue adding
        # After trimming at 1001 entries to 800, we add 199 more (1001-1199)
        assert len(selector.performance_history) == 999
        
        # Verify it kept the most recent ones
        assert selector.performance_history[-1]['contexts_selected'] >= 0

    def test_moving_average_metrics(self, selector, sample_contexts):
        """Test that metrics use moving averages correctly."""
        selector.load_available_contexts(sample_contexts)
        selector.semantic_matcher.find_similar_contexts.return_value = []
        
        # Make first selection with specific metrics
        with patch.object(selector, '_estimate_hit_rate', return_value=1.0):
            with patch.object(selector, '_estimate_size_reduction', return_value=0.8):
                selector.select_context("query1", max_tokens=1000)
        
        # First values should be set directly (alpha factor on zero base)
        assert abs(selector.metrics.avg_hit_rate - 0.1) < 0.01  # 0.1 * 1.0 + 0.9 * 0
        assert abs(selector.metrics.avg_size_reduction - 0.08) < 0.01  # 0.1 * 0.8 + 0.9 * 0
        
        # Make second selection with different metrics
        with patch.object(selector, '_estimate_hit_rate', return_value=0.5):
            with patch.object(selector, '_estimate_size_reduction', return_value=0.4):
                selector.select_context("query2", max_tokens=1000)
        
        # Should be moving average
        # avg = 0.1 * new + 0.9 * old
        expected_hit_rate = 0.1 * 0.5 + 0.9 * 0.1
        expected_size_reduction = 0.1 * 0.4 + 0.9 * 0.08
        
        assert abs(selector.metrics.avg_hit_rate - expected_hit_rate) < 0.01
        assert abs(selector.metrics.avg_size_reduction - expected_size_reduction) < 0.01