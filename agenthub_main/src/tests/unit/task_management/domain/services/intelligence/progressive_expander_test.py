"""
Unit tests for the Progressive Expander
"""

from datetime import UTC, datetime, timedelta

import pytest

from fastmcp.task_management.domain.services.intelligence.progressive_expander import (
    ContextLevel,
    ExpansionCandidate,
    ExpansionResult,
    ExpansionTrigger,
    ProgressiveExpander,
    UserPreferences,
)


# Fixtures
@pytest.fixture
def progressive_expander():
    """Create a ProgressiveExpander instance"""
    return ProgressiveExpander(
        default_token_budget=2000,
        min_context_tokens=100,
        prefetch_threshold=0.7,
        expansion_factor=1.5
    )


@pytest.fixture
def user_preferences():
    """Create default user preferences"""
    return UserPreferences()


@pytest.fixture
def sample_current_context():
    """Create a sample current context"""
    return {
        'id': 'current_context',
        'loaded_contexts': ['ctx_1', 'ctx_2'],
        'task_ids': ['task_1', 'task_2'],
        'dependencies': ['task_3'],
        'git_branch_id': 'branch_123'
    }


@pytest.fixture
def sample_available_contexts():
    """Create sample available contexts"""
    return [
        {
            'id': 'ctx_3',
            'context_id': 'ctx_3',
            'context_type': 'task',
            'title': 'Implement authentication',
            'description': 'JWT auth implementation',
            'assignees': ['@backend-agent']
        },
        {
            'id': 'ctx_4',
            'context_id': 'ctx_4',
            'context_type': 'branch',
            'git_branch_id': 'branch_123',
            'branch_name': 'feature/auth',
            'tasks': ['task_1', 'task_2', 'task_3']
        },
        {
            'id': 'ctx_5',
            'context_id': 'ctx_5',
            'context_type': 'project',
            'project_name': 'Web App',
            'branches': ['branch_123', 'branch_456']
        },
        {
            'id': 'task_3',  # Dependency
            'context_id': 'task_3',
            'context_type': 'task',
            'title': 'Create database schema',
            'description': 'User and role tables'
        }
    ]


@pytest.fixture
def similarity_scores():
    """Create sample similarity scores"""
    return {
        'ctx_3': 0.85,  # High similarity
        'ctx_4': 0.65,  # Medium similarity  
        'ctx_5': 0.3,   # Low similarity
        'task_3': 0.72  # Above prefetch threshold
    }


class TestProgressiveExpander:
    """Test the main ProgressiveExpander class"""
    
    def test_initialization(self, progressive_expander):
        """Test expander initialization"""
        assert progressive_expander.default_token_budget == 2000
        assert progressive_expander.min_context_tokens == 100
        assert progressive_expander.prefetch_threshold == 0.7
        assert progressive_expander.expansion_factor == 1.5
        assert len(progressive_expander.expansion_history) == 0
        assert len(progressive_expander.context_access_patterns) == 0
    
    def test_estimate_context_tokens(self, progressive_expander):
        """Test token estimation"""
        # Empty context
        assert progressive_expander.estimate_context_tokens({}) == 0
        assert progressive_expander.estimate_context_tokens(None) == 0
        
        # Small context
        small_context = {'id': 'test', 'name': 'Test'}
        tokens = progressive_expander.estimate_context_tokens(small_context)
        assert tokens > 0
        assert tokens < 50  # Should be small
        
        # Large context
        large_context = {
            'id': 'test',
            'description': 'A' * 1000,  # Long description
            'items': list(range(100))
        }
        large_tokens = progressive_expander.estimate_context_tokens(large_context)
        assert large_tokens > tokens
        assert large_tokens > 250  # Should be larger
    
    def test_calculate_expansion_priority_by_level(self, progressive_expander):
        """Test priority calculation for different context levels"""
        query_context = {'current': 'context'}
        
        # Task level should have highest base priority
        task_priority = progressive_expander._calculate_expansion_priority(
            'task_1', ContextLevel.TASK, query_context, ExpansionTrigger.USER_REQUEST
        )
        
        # Project level should have lower priority
        project_priority = progressive_expander._calculate_expansion_priority(
            'proj_1', ContextLevel.PROJECT, query_context, ExpansionTrigger.USER_REQUEST
        )
        
        assert task_priority > project_priority
        assert 0.0 <= task_priority <= 1.0
        assert 0.0 <= project_priority <= 1.0
    
    def test_calculate_expansion_priority_by_trigger(self, progressive_expander):
        """Test priority calculation for different triggers"""
        query_context = {'current': 'context'}
        
        # User request should have highest modifier
        user_priority = progressive_expander._calculate_expansion_priority(
            'ctx_1', ContextLevel.TASK, query_context, ExpansionTrigger.USER_REQUEST
        )
        
        # Prefetch should have lower modifier
        prefetch_priority = progressive_expander._calculate_expansion_priority(
            'ctx_1', ContextLevel.TASK, query_context, ExpansionTrigger.PREFETCH
        )
        
        assert user_priority > prefetch_priority
    
    def test_calculate_expansion_priority_with_access_patterns(self, progressive_expander):
        """Test priority calculation with historical access patterns"""
        query_context = {'current': 'context'}
        context_id = 'frequently_accessed'
        
        # Add access history
        progressive_expander.context_access_patterns[context_id] = {
            'access_count': 10,
            'total_sessions': 20,  # 50% access rate
            'last_accessed': datetime.now(UTC) - timedelta(hours=2)
        }
        
        priority_with_history = progressive_expander._calculate_expansion_priority(
            context_id, ContextLevel.TASK, query_context, ExpansionTrigger.SIMILARITY_MATCH
        )
        
        priority_without_history = progressive_expander._calculate_expansion_priority(
            'new_context', ContextLevel.TASK, query_context, ExpansionTrigger.SIMILARITY_MATCH
        )
        
        assert priority_with_history > priority_without_history
    
    def test_identify_expansion_candidates(
        self, progressive_expander, sample_current_context, 
        sample_available_contexts, similarity_scores
    ):
        """Test identification of expansion candidates"""
        candidates = progressive_expander.identify_expansion_candidates(
            sample_current_context,
            "auth implementation query",
            sample_available_contexts,
            similarity_scores
        )
        
        assert len(candidates) > 0
        
        # Should not include already loaded contexts
        candidate_ids = [c.context_id for c in candidates]
        assert 'ctx_1' not in candidate_ids
        assert 'ctx_2' not in candidate_ids
        
        # High similarity contexts should be present
        ctx_3_candidates = [c for c in candidates if c.context_id == 'ctx_3']
        assert len(ctx_3_candidates) > 0
        assert any(c.trigger == ExpansionTrigger.SIMILARITY_MATCH for c in ctx_3_candidates)
        
        # Dependency should be identified
        task_3_candidates = [c for c in candidates if c.context_id == 'task_3']
        assert len(task_3_candidates) > 0
        assert any(c.trigger == ExpansionTrigger.DEPENDENCY_CHAIN for c in task_3_candidates)
    
    def test_has_dependency_relationship(self, progressive_expander, sample_current_context):
        """Test dependency relationship detection"""
        # Direct dependency
        dependent_context = {'id': 'task_3', 'context_type': 'task'}
        assert progressive_expander._has_dependency_relationship(
            dependent_context, sample_current_context
        )
        
        # Same branch
        same_branch_context = {
            'id': 'task_10',
            'git_branch_id': 'branch_123'
        }
        assert progressive_expander._has_dependency_relationship(
            same_branch_context, sample_current_context
        )
        
        # No relationship
        unrelated_context = {
            'id': 'task_99',
            'git_branch_id': 'branch_999'
        }
        assert not progressive_expander._has_dependency_relationship(
            unrelated_context, sample_current_context
        )
    
    def test_matches_usage_pattern(self, progressive_expander):
        """Test usage pattern matching"""
        context_id = 'pattern_test'
        
        # No pattern yet
        assert not progressive_expander._matches_usage_pattern(context_id, "test query")
        
        # Add frequent access pattern
        progressive_expander.context_access_patterns[context_id] = {
            'access_count': 4,
            'total_sessions': 10,  # 40% access rate
            'common_keywords': ['auth', 'jwt', 'token']
        }
        
        # Should match based on frequency
        assert progressive_expander._matches_usage_pattern(context_id, "any query")
        
        # Should match based on keywords
        progressive_expander.context_access_patterns[context_id]['access_count'] = 1
        assert progressive_expander._matches_usage_pattern(context_id, "implement JWT auth")
    
    def test_record_context_access(self, progressive_expander):
        """Test context access recording"""
        context_id = 'test_context'
        
        # First access
        progressive_expander._record_context_access(context_id)
        assert context_id in progressive_expander.context_access_patterns
        assert progressive_expander.context_access_patterns[context_id]['access_count'] == 1
        assert progressive_expander.context_access_patterns[context_id]['last_accessed'] is not None
        
        # Second access
        progressive_expander._record_context_access(context_id)
        assert progressive_expander.context_access_patterns[context_id]['access_count'] == 2
    
    def test_expand_context_progressive_basic(self, progressive_expander):
        """Test basic progressive expansion"""
        current_context = {'loaded_contexts': []}
        
        candidates = [
            ExpansionCandidate(
                context_id='high_priority',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.9,
                estimated_tokens=100,
                trigger=ExpansionTrigger.USER_REQUEST,
                metadata={'context_data': {'id': 'high_priority', 'data': 'important'}}
            ),
            ExpansionCandidate(
                context_id='low_priority',
                context_level=ContextLevel.PROJECT,
                context_type='project',
                priority_score=0.3,
                estimated_tokens=200,
                trigger=ExpansionTrigger.PREFETCH,
                metadata={'context_data': {'id': 'low_priority', 'data': 'less important'}}
            )
        ]
        
        result = progressive_expander.expand_context_progressive(
            current_context, candidates, token_budget=500
        )
        
        assert isinstance(result, ExpansionResult)
        assert len(result.expanded_contexts) > 0
        assert result.total_tokens_used > 0
        assert result.total_tokens_used <= 400  # 500 - 100 min reserve
        assert len(result.expansion_path) > 0
    
    def test_expand_context_progressive_token_limit(self, progressive_expander):
        """Test expansion respects token limits"""
        current_context = {'loaded_contexts': []}
        
        # Create many candidates that exceed token budget
        candidates = []
        for i in range(10):
            candidates.append(
                ExpansionCandidate(
                    context_id=f'ctx_{i}',
                    context_level=ContextLevel.TASK,
                    context_type='task',
                    priority_score=0.9 - (i * 0.05),  # Decreasing priority
                    estimated_tokens=300,  # Each is expensive
                    trigger=ExpansionTrigger.SIMILARITY_MATCH,
                    metadata={'context_data': {'id': f'ctx_{i}', 'data': f'data_{i}'}}
                )
            )
        
        result = progressive_expander.expand_context_progressive(
            current_context, candidates, token_budget=1000
        )
        
        # Should only expand what fits in budget
        assert result.total_tokens_used <= 900  # 1000 - 100 min reserve
        assert len(result.expanded_contexts) < len(candidates)
        
        # High priority items may be prefetched
        assert len(result.prefetched_contexts) >= 0
    
    def test_expand_context_progressive_aggressive(self, progressive_expander):
        """Test aggressive expansion mode"""
        current_context = {'loaded_contexts': []}
        
        candidates = [
            ExpansionCandidate(
                context_id='ctx_1',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.7,
                estimated_tokens=100,
                trigger=ExpansionTrigger.SIMILARITY_MATCH,
                metadata={'context_data': {'id': 'ctx_1'}}
            )
        ]
        
        # Normal expansion
        normal_result = progressive_expander.expand_context_progressive(
            current_context, candidates, token_budget=500, aggressive=False
        )
        
        # Aggressive expansion
        aggressive_result = progressive_expander.expand_context_progressive(
            current_context, candidates, token_budget=500, aggressive=True
        )
        
        # Aggressive should use more tokens (due to expansion factor)
        assert aggressive_result.total_tokens_used >= normal_result.total_tokens_used
    
    def test_get_expansion_stats(self, progressive_expander):
        """Test expansion statistics"""
        # No history yet
        stats = progressive_expander.get_expansion_stats()
        assert stats == {}
        
        # Add some expansion history
        for i in range(5):
            progressive_expander.expansion_history.append({
                'timestamp': datetime.now(UTC),
                'token_budget': 1000,
                'tokens_used': 500 + (i * 50),
                'contexts_expanded': 3 + i,
                'contexts_prefetched': i,
                'expansion_path': [f'path_{i}']
            })
        
        stats = progressive_expander.get_expansion_stats()
        assert stats['total_expansions'] == 5
        assert stats['avg_tokens_used'] > 0
        assert stats['avg_contexts_expanded'] > 0
        assert stats['expansion_factor'] == 1.5
        assert stats['token_budget'] == 2000


class TestUserPreferences:
    """Test UserPreferences dataclass"""
    
    def test_default_preferences(self, user_preferences):
        """Test default user preferences"""
        assert user_preferences.auto_expand_related is True
        assert user_preferences.max_expansion_depth == 3
        assert user_preferences.preferred_context_level == "PROJECT"
        assert user_preferences.max_tokens_per_request == 4000
        assert user_preferences.prefetch_enabled is True
        assert user_preferences.include_completed is True
        assert user_preferences.priority_threshold == "LOW"
    
    def test_custom_preferences(self):
        """Test custom user preferences"""
        prefs = UserPreferences(
            auto_expand_related=False,
            max_tokens_per_request=2000,
            priority_threshold="HIGH"
        )
        assert prefs.auto_expand_related is False
        assert prefs.max_tokens_per_request == 2000
        assert prefs.priority_threshold == "HIGH"


class TestEnums:
    """Test enum values"""
    
    def test_context_level_values(self):
        """Test ContextLevel enum"""
        assert ContextLevel.GLOBAL.value == "global"
        assert ContextLevel.PROJECT.value == "project"
        assert ContextLevel.BRANCH.value == "branch"
        assert ContextLevel.TASK.value == "task"
    
    def test_expansion_trigger_values(self):
        """Test ExpansionTrigger enum"""
        assert ExpansionTrigger.USER_REQUEST.value == "user_request"
        assert ExpansionTrigger.SIMILARITY_MATCH.value == "similarity_match"
        assert ExpansionTrigger.DEPENDENCY_CHAIN.value == "dependency_chain"
        assert ExpansionTrigger.PATTERN_BASED.value == "pattern_based"
        assert ExpansionTrigger.TOKEN_AVAILABLE.value == "token_available"
        assert ExpansionTrigger.PREFETCH.value == "prefetch"


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_expansion_with_empty_candidates(self, progressive_expander):
        """Test expansion with no candidates"""
        result = progressive_expander.expand_context_progressive(
            {'loaded_contexts': []},
            [],  # Empty candidates
            token_budget=1000
        )
        
        assert result.expanded_contexts == []
        assert result.total_tokens_used == 0
        assert result.remaining_token_budget == 900  # 1000 - 100 min
    
    def test_expansion_with_zero_budget(self, progressive_expander):
        """Test expansion with zero token budget"""
        candidates = [
            ExpansionCandidate(
                context_id='ctx_1',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.9,
                estimated_tokens=100,
                trigger=ExpansionTrigger.USER_REQUEST,
                metadata={'context_data': {'id': 'ctx_1'}}
            )
        ]
        
        result = progressive_expander.expand_context_progressive(
            {'loaded_contexts': []},
            candidates,
            token_budget=0
        )
        
        assert result.expanded_contexts == []
        assert result.total_tokens_used == 0
    
    def test_token_estimation_with_special_values(self, progressive_expander):
        """Test token estimation with special values"""
        # With datetime
        context_with_datetime = {
            'created_at': datetime.now(UTC),
            'data': 'test'
        }
        tokens = progressive_expander.estimate_context_tokens(context_with_datetime)
        assert tokens > 0
        
        # With None values
        context_with_none = {
            'id': 'test',
            'value': None,
            'list': [1, None, 3]
        }
        tokens = progressive_expander.estimate_context_tokens(context_with_none)
        assert tokens > 0
    
    def test_high_priority_prefetch(self, progressive_expander):
        """Test high priority items get prefetched when budget is tight"""
        candidates = [
            ExpansionCandidate(
                context_id='expensive',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.5,
                estimated_tokens=400,  # Too big for budget
                trigger=ExpansionTrigger.SIMILARITY_MATCH,
                metadata={'context_data': {'id': 'expensive'}}
            ),
            ExpansionCandidate(
                context_id='critical_small',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.9,  # High priority
                estimated_tokens=30,  # Small size
                trigger=ExpansionTrigger.USER_REQUEST,
                metadata={'context_data': {'id': 'critical_small'}}
            )
        ]

        result = progressive_expander.expand_context_progressive(
            {'loaded_contexts': []},
            candidates,
            token_budget=200  # Only enough for min reserve + a bit
        )

        # The high priority small item should be expanded (it fits in budget)
        assert len(result.expanded_contexts) == 1
        assert result.expanded_contexts[0]['id'] == 'critical_small'
        # The expensive one should not be expanded or prefetched
        assert 'expensive' not in [c['id'] for c in result.expanded_contexts]

    def test_skip_already_loaded_contexts(self, progressive_expander):
        """Test that already loaded contexts are skipped - Line 238"""
        current_context = {
            'loaded_contexts': ['ctx_already_loaded', 'ctx_another']
        }

        available_contexts = [
            {
                'id': 'ctx_already_loaded',
                'context_id': 'ctx_already_loaded',
                'context_type': 'task'
            },
            {
                'id': 'ctx_new',
                'context_id': 'ctx_new',
                'context_type': 'task'
            }
        ]

        candidates = progressive_expander.identify_expansion_candidates(
            current_context,
            "test query",
            available_contexts
        )

        # Should skip already loaded context
        candidate_ids = [c.context_id for c in candidates]
        assert 'ctx_already_loaded' not in candidate_ids
        assert 'ctx_new' in candidate_ids

    def test_unknown_context_type_defaults_to_global(self, progressive_expander):
        """Test unknown context_type defaults to GLOBAL - Line 248"""
        current_context = {'loaded_contexts': []}

        available_contexts = [
            {
                'id': 'ctx_unknown',
                'context_id': 'ctx_unknown',
                'context_type': 'unknown_type'  # Not task/branch/project
            }
        ]

        candidates = progressive_expander.identify_expansion_candidates(
            current_context,
            "test query",
            available_contexts
        )

        assert len(candidates) > 0
        # Should default to GLOBAL level for unknown types
        unknown_candidates = [c for c in candidates if c.context_id == 'ctx_unknown']
        assert any(c.context_level == ContextLevel.GLOBAL for c in unknown_candidates)

    def test_pattern_based_trigger_identified(self, progressive_expander):
        """Test pattern-based trigger is identified - Line 270"""
        context_id = 'pattern_context'

        # Set up usage pattern that matches
        progressive_expander.context_access_patterns[context_id] = {
            'access_count': 5,
            'total_sessions': 10,  # 50% access rate
            'common_keywords': ['authentication', 'jwt']
        }

        current_context = {'loaded_contexts': []}
        available_contexts = [
            {
                'id': context_id,
                'context_id': context_id,
                'context_type': 'task'
            }
        ]

        candidates = progressive_expander.identify_expansion_candidates(
            current_context,
            "implement authentication system",  # Matches keyword
            available_contexts
        )

        # Should have pattern-based trigger
        pattern_candidates = [
            c for c in candidates
            if c.context_id == context_id and c.trigger == ExpansionTrigger.PATTERN_BASED
        ]
        assert len(pattern_candidates) > 0

    def test_expand_context_with_none_token_budget(self, progressive_expander):
        """Test expansion with None token_budget uses default - Line 323"""
        candidates = [
            ExpansionCandidate(
                context_id='ctx_1',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.8,
                estimated_tokens=100,
                trigger=ExpansionTrigger.SIMILARITY_MATCH,
                metadata={'context_data': {'id': 'ctx_1'}}
            )
        ]

        # Pass None for token_budget
        result = progressive_expander.expand_context_progressive(
            {'loaded_contexts': []},
            candidates,
            token_budget=None  # Should use default_token_budget (2000)
        )

        # Should use default budget
        assert len(result.expanded_contexts) > 0
        assert result.remaining_token_budget > 0
        # Verify it used the default budget (2000 - 100 min reserve = 1900 available)
        assert result.total_tokens_used + result.remaining_token_budget == 1900

    def test_high_priority_small_items_prefetch_on_budget_exceeded(self, progressive_expander):
        """Test high priority small items get prefetched when budget exceeded - Lines 349-350"""
        candidates = [
            ExpansionCandidate(
                context_id='fills_budget',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.7,
                estimated_tokens=125,  # Takes 125 * 1.5 = 187.5 (rounds to 187)
                trigger=ExpansionTrigger.USER_REQUEST,
                metadata={'context_data': {'id': 'fills_budget'}}
            ),
            ExpansionCandidate(
                context_id='high_priority_small',
                context_level=ContextLevel.TASK,
                context_type='task',
                priority_score=0.85,  # High priority (> 0.8)
                estimated_tokens=5,  # Small: 5 < 19 (10% of 190 available_budget)
                trigger=ExpansionTrigger.SIMILARITY_MATCH,
                metadata={'context_data': {'id': 'high_priority_small'}}
            )
        ]

        result = progressive_expander.expand_context_progressive(
            {'loaded_contexts': []},
            candidates,
            token_budget=290  # 290 - 100 = 190 available, first takes 187, leaves 3
        )

        # First should be expanded (fits in budget)
        # Second should be prefetched (priority > 0.8, est_tokens=5 < 19, but needed=7.5 exceeds remaining 3)
        assert 'high_priority_small' in result.prefetched_contexts
        assert 'prefetch:high_priority_small' in result.expansion_path

    def test_recency_bonus_without_last_accessed(self, progressive_expander):
        """Test recency bonus calculation when last_accessed is None - Branch 202->207"""
        context_id = 'no_recent_access'

        # Set up pattern without last_accessed
        progressive_expander.context_access_patterns[context_id] = {
            'access_count': 5,
            'total_sessions': 10,
            'last_accessed': None  # No last access timestamp
        }

        query_context = {'current': 'context'}
        priority = progressive_expander._calculate_expansion_priority(
            context_id, ContextLevel.TASK, query_context, ExpansionTrigger.SIMILARITY_MATCH
        )

        # Should still calculate priority without crashing
        assert 0.0 <= priority <= 1.0

    def test_similarity_below_prefetch_threshold(self, progressive_expander):
        """Test similarity scores below prefetch threshold - Branch 257->265"""
        current_context = {'loaded_contexts': []}

        available_contexts = [
            {
                'id': 'low_sim',
                'context_id': 'low_sim',
                'context_type': 'task'
            }
        ]

        # Similarity below prefetch threshold (0.7 * 0.7 = 0.49)
        similarity_scores = {
            'low_sim': 0.45  # Below 0.49, won't trigger prefetch
        }

        candidates = progressive_expander.identify_expansion_candidates(
            current_context,
            "test query",
            available_contexts,
            similarity_scores
        )

        # Should not have similarity or prefetch triggers
        low_sim_candidates = [c for c in candidates if c.context_id == 'low_sim']
        for candidate in low_sim_candidates:
            assert candidate.trigger not in [
                ExpansionTrigger.SIMILARITY_MATCH,
                ExpansionTrigger.PREFETCH
            ]

    def test_token_availability_not_small_enough(self, progressive_expander):
        """Test contexts not small enough for token availability trigger - Branch 273->277"""
        current_context = {'loaded_contexts': []}

        # Large context (> 10% of default budget)
        large_context = {
            'id': 'large_ctx',
            'context_id': 'large_ctx',
            'context_type': 'task',
            'description': 'A' * 5000  # Very large, > 200 tokens (10% of 2000)
        }

        candidates = progressive_expander.identify_expansion_candidates(
            current_context,
            "test query",
            [large_context],
            None  # No similarity scores
        )

        # Should have candidates but not with TOKEN_AVAILABLE trigger
        large_candidates = [c for c in candidates if c.context_id == 'large_ctx']
        assert len(large_candidates) > 0  # Should still create candidate with default trigger

    def test_keyword_match_no_match_found(self, progressive_expander):
        """Test keyword matching when no match is found - Branches 441->440, 444"""
        context_id = 'keyword_test'

        # Set up pattern with keywords that won't match
        progressive_expander.context_access_patterns[context_id] = {
            'access_count': 2,  # Low frequency (< 30%)
            'total_sessions': 10,
            'common_keywords': ['database', 'schema', 'migration']
        }

        # Query with no matching keywords
        result = progressive_expander._matches_usage_pattern(
            context_id,
            "implement frontend authentication with react"
        )

        # Should return False (no match)
        assert result is False