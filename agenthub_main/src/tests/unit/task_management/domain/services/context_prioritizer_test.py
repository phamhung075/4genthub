"""Unit tests for ContextPrioritizer domain service"""

import math
from datetime import UTC, datetime, timedelta

import pytest

from fastmcp.task_management.domain.services.intelligence.context_prioritizer import (
    ContextPrioritizer,
    ContextScore,
    ScoreFactor,
    ScoringWeights,
    UserPreferences,
)


class TestScoringWeights:
    """Test suite for ScoringWeights dataclass"""

    def test_default_weights_initialization(self):
        """Test default weights are initialized correctly"""
        weights = ScoringWeights()

        assert weights.semantic_relevance == 0.3
        assert weights.recency == 0.15
        assert weights.frequency == 0.15
        assert weights.completeness == 0.10
        assert weights.size_penalty == 0.05
        assert weights.user_preference == 0.10
        assert weights.project_priority == 0.10
        assert weights.dependency_boost == 0.05

    def test_normalize_weights(self):
        """Test weight normalization to sum to 1.0"""
        # Custom weights that don't sum to 1.0
        weights = ScoringWeights(
            semantic_relevance=0.4,
            recency=0.2,
            frequency=0.2,
            completeness=0.2,
            user_preference=0.2,
            project_priority=0.2,
            dependency_boost=0.2,
        )

        normalized = weights.normalize()

        # Check sum is approximately 1.0 (excluding size_penalty)
        total = (
            normalized.semantic_relevance
            + normalized.recency
            + normalized.frequency
            + normalized.completeness
            + normalized.user_preference
            + normalized.project_priority
            + normalized.dependency_boost
        )

        assert abs(total - 1.0) < 0.001
        assert normalized.size_penalty == weights.size_penalty  # Size penalty unchanged

    def test_normalize_zero_weights(self):
        """Test normalization with zero weights"""
        weights = ScoringWeights(
            semantic_relevance=0,
            recency=0,
            frequency=0,
            completeness=0,
            user_preference=0,
            project_priority=0,
            dependency_boost=0,
        )

        normalized = weights.normalize()

        # Should return original weights when sum is 0
        assert normalized.semantic_relevance == 0
        assert normalized.recency == 0


class TestContextPrioritizer:
    """Test suite for ContextPrioritizer"""

    @pytest.fixture
    def prioritizer(self):
        """Create a ContextPrioritizer instance"""
        return ContextPrioritizer(
            recency_decay_hours=24.0,
            frequency_window_days=30,
            size_penalty_threshold=1500,
        )

    @pytest.fixture
    def sample_context(self):
        """Create sample context data"""
        return {
            "id": "ctx-123",
            "context_type": "task",
            "title": "Implement user authentication",
            "description": "Add JWT authentication to the API",
            "status": "in_progress",
            "assignees": ["agent-1", "agent-2"],
            "details": "Using JWT tokens with refresh mechanism",
            "git_branch_id": "branch-123",
            "project_id": "proj-123",
        }

    @pytest.fixture
    def user_preferences(self):
        """Create sample user preferences"""
        return UserPreferences(
            preferred_context_types=["task", "branch"],
            max_context_size=2000,
            priority_boost_keywords=["authentication", "security"],
            penalty_keywords=["deprecated", "obsolete"],
            agent_preferences={"agent-1": 0.8, "agent-3": -0.2},
        )

    def test_initialization(self):
        """Test ContextPrioritizer initialization"""
        prioritizer = ContextPrioritizer()

        assert prioritizer.recency_decay_hours == 24.0
        assert prioritizer.frequency_window_days == 30
        assert prioritizer.size_penalty_threshold == 1500
        assert isinstance(prioritizer.default_weights, ScoringWeights)
        assert prioritizer.context_access_history == {}

    def test_score_context_basic(self, prioritizer, sample_context):
        """Test basic context scoring"""
        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="authentication JWT",
            semantic_similarity=0.7,
        )

        assert isinstance(score, ContextScore)
        assert score.context_id == "ctx-123"
        assert 0 <= score.total_score <= 1.0
        assert ScoreFactor.SEMANTIC_RELEVANCE in score.factor_scores
        assert len(score.explanations) > 0

    def test_semantic_score_calculation(self, prioritizer, sample_context):
        """Test semantic relevance scoring with keyword matching"""
        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="authentication JWT tokens",  # Matches keywords in context
            semantic_similarity=0.6,
        )

        # Should have boost from keyword matches
        semantic_score = score.factor_scores[ScoreFactor.SEMANTIC_RELEVANCE]
        assert semantic_score > 0.6  # Base similarity + keyword boost
        assert semantic_score <= 1.0

    def test_recency_score_without_access(self, prioritizer, sample_context):
        """Test recency score for never-accessed context"""
        score = prioritizer.score_context(
            context_id="ctx-new",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        recency_score = score.factor_scores[ScoreFactor.RECENCY]
        assert recency_score == 0.1  # Low score for never accessed

    def test_recency_score_with_recent_access(self, prioritizer, sample_context):
        """Test recency score with recent access"""
        # Record recent access
        prioritizer.record_context_access("ctx-123", datetime.now(UTC))

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        recency_score = score.factor_scores[ScoreFactor.RECENCY]
        assert recency_score > 0.9  # High score for very recent access

    def test_recency_score_decay(self, prioritizer, sample_context):
        """Test recency score decay over time"""
        # Record access 12 hours ago
        access_time = datetime.now(UTC) - timedelta(hours=12)
        prioritizer.record_context_access("ctx-123", access_time)

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        recency_score = score.factor_scores[ScoreFactor.RECENCY]
        expected = math.exp(-12 / 24)  # Exponential decay
        assert abs(recency_score - expected) < 0.01

    def test_frequency_score_calculation(self, prioritizer, sample_context):
        """Test frequency score based on access history"""
        # Record multiple accesses
        now = datetime.now(UTC)
        for days_ago in [1, 3, 5, 10, 20]:
            access_time = now - timedelta(days=days_ago)
            prioritizer.record_context_access("ctx-123", access_time)

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        frequency_score = score.factor_scores[ScoreFactor.FREQUENCY]
        assert frequency_score > 0.1  # Higher than never accessed
        assert frequency_score <= 1.0

    def test_completeness_score_full_context(self, prioritizer):
        """Test completeness score for fully populated context"""
        full_context = {
            "context_type": "task",
            "title": "Complete task",
            "description": "Full description",
            "status": "in_progress",
            "assignees": ["agent-1"],
            "details": "Detailed information",
        }

        score = prioritizer.score_context(
            context_id="ctx-full",
            context_data=full_context,
            query="test",
            semantic_similarity=0.5,
        )

        completeness = score.factor_scores[ScoreFactor.COMPLETENESS]
        assert completeness == 1.0  # All expected fields are filled

    def test_completeness_score_partial_context(self, prioritizer):
        """Test completeness score for partially populated context"""
        partial_context = {
            "context_type": "task",
            "title": "Partial task",
            "description": "",  # Empty
            "status": "todo",
            # Missing assignees and details
        }

        score = prioritizer.score_context(
            context_id="ctx-partial",
            context_data=partial_context,
            query="test",
            semantic_similarity=0.5,
        )

        completeness = score.factor_scores[ScoreFactor.COMPLETENESS]
        assert 0.4 <= completeness <= 0.6  # Partial completeness

    def test_size_penalty_below_threshold(self, prioritizer, sample_context):
        """Test size penalty when context is below threshold"""
        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        size_penalty = score.factor_scores[ScoreFactor.SIZE_PENALTY]
        assert size_penalty == 0.0  # No penalty below threshold

    def test_size_penalty_above_threshold(self, prioritizer):
        """Test size penalty when context exceeds threshold"""
        large_context = {
            "title": "Large context",
            "description": "x" * 10000,  # Very large content
        }

        score = prioritizer.score_context(
            context_id="ctx-large",
            context_data=large_context,
            query="test",
            semantic_similarity=0.5,
        )

        size_penalty = score.factor_scores[ScoreFactor.SIZE_PENALTY]
        assert size_penalty > 0.0  # Penalty applied
        assert size_penalty <= 0.5  # Capped at 50%

    def test_user_preference_score(self, prioritizer, sample_context, user_preferences):
        """Test user preference scoring"""
        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="authentication",  # Matches priority keyword
            semantic_similarity=0.5,
            user_preferences=user_preferences,
        )

        pref_score = score.factor_scores[ScoreFactor.USER_PREFERENCE]
        assert pref_score > 0.5  # Base + boost for preferred type and keyword

    def test_user_preference_with_penalties(self, prioritizer, user_preferences):
        """Test user preference with penalty keywords"""
        context_with_penalty = {
            "context_type": "task",
            "title": "Deprecated authentication method",
            "description": "This is obsolete",
        }

        score = prioritizer.score_context(
            context_id="ctx-penalty",
            context_data=context_with_penalty,
            query="authentication",
            semantic_similarity=0.5,
            user_preferences=user_preferences,
        )

        pref_score = score.factor_scores[ScoreFactor.USER_PREFERENCE]
        # Base score 0.5 + 0.3 for preferred type + 0.1 for auth keyword - 0.2 for two penalty keywords = 0.7
        assert 0.6 < pref_score < 0.8  # Score with penalties applied

    def test_project_priority_score(self, prioritizer, sample_context):
        """Test project priority scoring"""
        project_context = {"priorities": {"task": 0.8, "branch": 0.6, "global": 0.4}}

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
            project_context=project_context,
        )

        project_score = score.factor_scores[ScoreFactor.PROJECT_PRIORITY]
        assert project_score > 0.5  # Higher for in_progress task

    def test_dependency_boost_direct(self, prioritizer, sample_context):
        """Test dependency boost for direct dependencies"""
        current_task = {
            "id": "current-task",
            "dependencies": ["ctx-123"],  # Direct dependency
            "git_branch_id": "branch-456",
            "project_id": "proj-123",
        }

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
            current_task=current_task,
        )

        dep_boost = score.factor_scores[ScoreFactor.DEPENDENCY_BOOST]
        assert dep_boost == 0.8  # Strong boost for direct dependency

    def test_dependency_boost_same_branch(self, prioritizer, sample_context):
        """Test dependency boost for same branch"""
        current_task = {
            "id": "current-task",
            "dependencies": [],
            "git_branch_id": "branch-123",  # Same as context
            "project_id": "proj-456",
        }

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
            current_task=current_task,
        )

        dep_boost = score.factor_scores[ScoreFactor.DEPENDENCY_BOOST]
        assert dep_boost == 0.3  # Moderate boost for same branch

    def test_score_contexts_batch(self, prioritizer):
        """Test batch scoring of multiple contexts"""
        contexts = [
            {
                "id": "ctx-1",
                "context_type": "task",
                "title": "High relevance task",
                "description": "authentication security",
            },
            {
                "id": "ctx-2",
                "context_type": "branch",
                "title": "Low relevance branch",
                "description": "unrelated feature",
            },
            {
                "id": "ctx-3",
                "context_type": "task",
                "title": "Medium relevance",
                "description": "user management",
            },
        ]

        similarities = {"ctx-1": 0.9, "ctx-2": 0.2, "ctx-3": 0.6}

        scores = prioritizer.score_contexts_batch(
            contexts=contexts,
            query="authentication",
            semantic_similarities=similarities,
        )

        assert len(scores) == 3
        assert scores[0].context_id == "ctx-1"  # Highest score first
        assert scores[0].total_score > scores[1].total_score
        assert scores[1].total_score > scores[2].total_score

    def test_record_context_access(self, prioritizer):
        """Test recording context access"""
        assert "ctx-123" not in prioritizer.context_access_history

        prioritizer.record_context_access("ctx-123")

        assert "ctx-123" in prioritizer.context_access_history
        assert len(prioritizer.context_access_history["ctx-123"]) == 1

        # Record another access
        prioritizer.record_context_access("ctx-123")
        assert len(prioritizer.context_access_history["ctx-123"]) == 2

    def test_record_context_access_cleanup(self, prioritizer):
        """Test old access records are cleaned up"""
        # Record old access beyond cleanup window
        old_time = datetime.now(UTC) - timedelta(days=65)
        prioritizer.record_context_access("ctx-123", old_time)

        # Record recent access
        prioritizer.record_context_access("ctx-123")

        # Old access should be removed
        assert len(prioritizer.context_access_history["ctx-123"]) == 1

    def test_adjust_weights_dynamically_long_query(self, prioritizer):
        """Test dynamic weight adjustment for long queries"""
        long_query = " ".join(["word"] * 15)  # 15 words

        adjusted = prioritizer.adjust_weights_dynamically(
            query=long_query, context_type="task"
        )

        # Should increase semantic relevance for long queries
        assert adjusted.semantic_relevance > 0.3
        assert adjusted.completeness > 0.1

    def test_adjust_weights_dynamically_short_query(self, prioritizer):
        """Test dynamic weight adjustment for short queries"""
        short_query = "auth user"  # 2 words

        adjusted = prioritizer.adjust_weights_dynamically(
            query=short_query, context_type="task"
        )

        # Should increase frequency/recency for short queries
        assert adjusted.frequency > 0.15
        assert adjusted.recency > 0.15

    def test_adjust_weights_with_feedback(self, prioritizer):
        """Test weight adjustment with user feedback"""
        feedback = {
            "semantic_relevance": 0.1,  # Increase by 0.1
            "frequency": -0.05,  # Decrease by 0.05
        }

        adjusted = prioritizer.adjust_weights_dynamically(
            query="test", context_type="task", user_feedback=feedback
        )

        # Check feedback is applied
        base_weights = ScoringWeights().normalize()
        assert adjusted.semantic_relevance > base_weights.semantic_relevance

    def test_get_scoring_stats(self, prioritizer):
        """Test getting scoring statistics"""
        # Record some accesses
        for i in range(5):
            prioritizer.record_context_access("ctx-1")

        for i in range(3):
            prioritizer.record_context_access("ctx-2")

        prioritizer.record_context_access("ctx-3")

        stats = prioritizer.get_scoring_stats()

        assert stats["total_contexts_tracked"] == 3
        assert stats["total_accesses_recorded"] == 9
        assert stats["avg_accesses_per_context"] == 3.0
        assert len(stats["most_frequent_contexts"]) <= 5
        assert stats["most_frequent_contexts"][0]["context_id"] == "ctx-1"
        assert stats["most_frequent_contexts"][0]["access_count"] == 5

    def test_estimate_tokens(self, prioritizer):
        """Test token estimation"""
        context = {"title": "Test", "description": "A" * 1000}

        # Use internal method
        tokens = prioritizer._estimate_tokens(context)

        assert tokens > 250  # Rough estimate
        assert tokens < 500

    def test_extract_searchable_text(self, prioritizer):
        """Test searchable text extraction"""
        context = {
            "title": "Test Title",
            "description": "Test Description",
            "details": "Test Details",
            "name": "Test Name",
            "git_branch_name": "feature/test",
            "other_field": "Not searched",
        }

        text = prioritizer._extract_searchable_text(context)

        assert "Test Title" in text
        assert "Test Description" in text
        assert "Test Details" in text
        assert "Test Name" in text
        assert "feature/test" in text
        assert "Not searched" not in text

    def test_total_score_normalization(self, prioritizer, sample_context):
        """Test total score is normalized between 0 and 1"""
        # Test with very high individual scores
        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="authentication JWT tokens security",  # Many matches
            semantic_similarity=0.99,
            weights=ScoringWeights(
                semantic_relevance=1.0, recency=1.0, frequency=1.0
            ).normalize(),
        )

        assert 0 <= score.total_score <= 1.0

    def test_context_score_metadata(self, prioritizer, sample_context):
        """Test context score includes proper metadata"""
        prioritizer.record_context_access("ctx-123")

        score = prioritizer.score_context(
            context_id="ctx-123",
            context_data=sample_context,
            query="test",
            semantic_similarity=0.5,
        )

        assert "estimated_tokens" in score.metadata
        assert score.metadata["context_type"] == "task"
        assert "last_accessed" in score.metadata
        assert score.metadata["last_accessed"] is not None


class TestContextScoreEdgeCases:
    """Test edge cases for context scoring"""

    @pytest.fixture
    def prioritizer(self):
        return ContextPrioritizer()

    def test_empty_context(self, prioritizer):
        """Test scoring empty context"""
        empty_context = {}

        score = prioritizer.score_context(
            context_id="empty",
            context_data=empty_context,
            query="test",
            semantic_similarity=0.5,
        )

        assert score.total_score >= 0
        assert score.context_id == "empty"

    def test_missing_id_in_context(self, prioritizer):
        """Test scoring context without ID field"""
        context = {"context_id": "fallback-id", "title": "Test"}

        scores = prioritizer.score_contexts_batch(
            contexts=[context], query="test", semantic_similarities={"fallback-id": 0.5}
        )

        assert len(scores) == 1
        assert scores[0].context_id == "fallback-id"

    def test_none_values_in_context(self, prioritizer):
        """Test handling None values in context"""
        context = {"title": None, "description": None, "assignees": None}

        score = prioritizer.score_context(
            context_id="none-test",
            context_data=context,
            query="test",
            semantic_similarity=0.5,
        )

        assert score.total_score >= 0

    def test_invalid_semantic_similarity(self, prioritizer):
        """Test handling invalid semantic similarity values"""
        context = {"title": "Test"}

        # Test with out-of-range similarity
        score = prioritizer.score_context(
            context_id="test",
            context_data=context,
            query="test",
            semantic_similarity=2.0,  # Invalid, > 1.0
        )

        # Should still produce valid score
        assert 0 <= score.total_score <= 1.0
