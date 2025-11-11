"""Unit tests for PredictiveLoader domain service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from fastmcp.task_management.domain.services.intelligence.predictive_loader import (
    PredictionResult,
    PredictionTrigger,
    PredictiveLoader,
    UsagePattern,
)


@pytest.fixture
def predictive_loader():
    """Create a PredictiveLoader instance for testing."""
    return PredictiveLoader(
        pattern_min_frequency=2,
        pattern_confidence_threshold=0.5,
        session_history_days=30,
        max_preload_contexts=3,
    )


@pytest.fixture
def sample_current_context():
    """Sample current context for predictions."""
    return {
        "id": "ctx-123",
        "context_id": "ctx-123",
        "type": "task",
        "name": "Test Task",
    }


@pytest.fixture
def sample_session_context():
    """Sample session context for predictions."""
    return {
        "tool_sequence": ["manage_task", "Read", "Edit"],
        "context_sequence": ["ctx-100", "ctx-101", "ctx-102"],
    }


class TestPredictiveLoaderInitialization:
    """Test PredictiveLoader initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        loader = PredictiveLoader()

        assert loader.pattern_min_frequency == 3
        assert loader.pattern_confidence_threshold == 0.6
        assert loader.session_history_days == 30
        assert loader.max_preload_contexts == 5
        assert loader.usage_patterns == {}
        assert loader.session_history == []
        assert loader.current_session is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        loader = PredictiveLoader(
            pattern_min_frequency=5,
            pattern_confidence_threshold=0.8,
            session_history_days=14,
            max_preload_contexts=10,
        )

        assert loader.pattern_min_frequency == 5
        assert loader.pattern_confidence_threshold == 0.8
        assert loader.session_history_days == 14
        assert loader.max_preload_contexts == 10


class TestSessionManagement:
    """Test session management functionality."""

    def test_start_session(self, predictive_loader):
        """Test starting a new session."""
        predictive_loader.start_session("sess-123", "user-456")

        assert predictive_loader.current_session is not None
        assert predictive_loader.current_session.session_id == "sess-123"
        assert predictive_loader.current_session.user_id == "user-456"
        assert isinstance(predictive_loader.current_session.start_time, datetime)
        assert predictive_loader.current_session.tool_sequence == []
        assert predictive_loader.current_session.context_sequence == []

    def test_record_tool_usage_no_session(self, predictive_loader):
        """Test recording tool usage without active session."""
        with patch("logging.Logger.warning") as mock_warning:
            predictive_loader.record_tool_usage("Read")
            mock_warning.assert_called_with(
                "No active session for tool usage recording"
            )

    def test_record_tool_usage_with_session(self, predictive_loader):
        """Test recording tool usage with active session."""
        predictive_loader.start_session("sess-123")
        predictive_loader.record_tool_usage("Read", "ctx-100")

        assert "Read" in predictive_loader.current_session.tool_sequence
        assert "ctx-100" in predictive_loader.current_session.context_sequence

    def test_record_tool_sequence_patterns(self, predictive_loader):
        """Test recording tool sequence patterns."""
        predictive_loader.start_session("sess-123")

        # Record sequence of tools
        tools = ["manage_task", "Read", "Edit", "Write"]
        for tool in tools:
            predictive_loader.record_tool_usage(tool)

        # Check 2-tool sequences
        assert ("Read", "Edit") in predictive_loader.tool_sequences
        assert ("Edit", "Write") in predictive_loader.tool_sequences

        # Check 3-tool sequences
        assert ("manage_task", "Read", "Edit") in predictive_loader.tool_sequences
        assert ("Read", "Edit", "Write") in predictive_loader.tool_sequences

    def test_record_context_access_no_session(self, predictive_loader):
        """Test recording context access without session."""
        with patch("logging.Logger.warning") as mock_warning:
            predictive_loader.record_context_access("ctx-123", "task")
            mock_warning.assert_called_with(
                "No active session for context access recording"
            )

    def test_record_context_transitions(self, predictive_loader):
        """Test recording context transition patterns."""
        predictive_loader.start_session("sess-123")

        # Record sequence of context accesses
        contexts = [("ctx-100", "task"), ("ctx-101", "task"), ("ctx-102", "branch")]
        for ctx_id, ctx_type in contexts:
            predictive_loader.record_context_access(ctx_id, ctx_type)

        # Check transitions
        assert ("ctx-100", "ctx-101") in predictive_loader.context_transitions
        assert ("ctx-101", "ctx-102") in predictive_loader.context_transitions

    def test_time_based_patterns(self, predictive_loader):
        """Test recording time-based patterns."""
        predictive_loader.start_session("sess-123")

        with patch(
            "fastmcp.task_management.domain.services.intelligence.predictive_loader.datetime"
        ) as mock_dt:
            mock_now = datetime(2025, 9, 26, 14, 30, 0, tzinfo=UTC)
            mock_dt.now.return_value = mock_now

            predictive_loader.record_context_access("ctx-100", "task")

            # Check time-based pattern key
            assert "task_14" in predictive_loader.time_based_patterns
            assert len(predictive_loader.time_based_patterns["task_14"]) == 1

    def test_end_session(self, predictive_loader):
        """Test ending a session."""
        predictive_loader.start_session("sess-123", "user-456")
        predictive_loader.record_tool_usage("Read")
        predictive_loader.record_context_access("ctx-100", "task")

        result = predictive_loader.end_session()

        assert result["session_id"] == "sess-123"
        assert result["user_id"] == "user-456"
        assert result["tool_sequence"] == ["Read"]
        assert result["context_sequence"] == ["ctx-100"]
        assert "duration_minutes" in result
        assert predictive_loader.current_session is None
        assert len(predictive_loader.session_history) == 1

    def test_session_history_cleanup(self, predictive_loader):
        """Test old session history cleanup."""
        # Add old session
        old_session = {
            "session_id": "old-sess",
            "end_time": datetime.now(UTC) - timedelta(days=40),
            "tool_sequence": [],
            "context_sequence": [],
        }
        predictive_loader.session_history.append(old_session)

        # Start and end new session
        predictive_loader.start_session("new-sess")
        predictive_loader.end_session()

        # Old session should be removed
        assert len(predictive_loader.session_history) == 1
        assert predictive_loader.session_history[0]["session_id"] == "new-sess"


class TestPredictions:
    """Test prediction functionality."""

    def test_predict_next_contexts_no_patterns(
        self, predictive_loader, sample_current_context
    ):
        """Test predictions with no established patterns."""
        result = predictive_loader.predict_next_contexts(
            sample_current_context, recent_tools=["Read"], session_context=None
        )

        assert isinstance(result, PredictionResult)
        assert result.predicted_contexts == []
        assert result.confidence_scores == {}
        assert result.patterns_used == []

    def test_predict_from_tool_sequence(
        self, predictive_loader, sample_current_context
    ):
        """Test predictions based on tool sequences."""
        # Establish tool sequence patterns that extend the current sequence
        predictive_loader.tool_sequences[("Read", "Edit", "manage_task")] = 5
        predictive_loader.tool_sequences[("Edit", "manage_task")] = 3

        result = predictive_loader.predict_next_contexts(
            sample_current_context, recent_tools=["Read", "Edit"], session_context=None
        )

        # Should predict based on tool mapping - manage_task maps to 'task' context
        assert len(result.predicted_contexts) > 0
        assert (
            "predicted_task" in result.predicted_contexts
        )  # Tool maps to task context
        assert "tool_sequence:2" in result.patterns_used

    def test_predict_from_context_transitions(self, predictive_loader):
        """Test predictions based on context transitions."""
        # Establish transition patterns with higher frequency for confidence
        predictive_loader.context_transitions[("ctx-123", "ctx-124")] = (
            10  # Higher frequency
        )
        predictive_loader.context_transitions[("ctx-123", "ctx-125")] = (
            8  # Also above threshold
        )

        current_context = {"id": "ctx-123"}
        result = predictive_loader.predict_next_contexts(
            current_context, recent_tools=[], session_context=None
        )

        assert "ctx-124" in result.predicted_contexts
        assert "ctx-125" in result.predicted_contexts  # Both should be included now
        assert (
            result.confidence_scores["ctx-124"] >= result.confidence_scores["ctx-125"]
        )
        assert "context_transition:ctx-123" in result.patterns_used

    def test_predict_from_time_patterns(
        self, predictive_loader, sample_current_context
    ):
        """Test predictions based on time patterns."""
        # Lower the confidence threshold for this test
        predictive_loader.pattern_confidence_threshold = 0.4

        with patch(
            "fastmcp.task_management.domain.services.intelligence.predictive_loader.datetime"
        ) as mock_dt:
            mock_now = datetime(2025, 9, 26, 14, 30, 0, tzinfo=UTC)
            mock_dt.now.return_value = mock_now

            # Establish time patterns with higher frequency
            for _ in range(10):  # Add enough patterns
                predictive_loader.time_based_patterns["task_14"].append(mock_now)

            result = predictive_loader.predict_next_contexts(
                sample_current_context, recent_tools=[], session_context=None
            )

            # Time patterns have lower weight (0.7) and confidence
            assert "time_based" in result.patterns_used
            # Check that time pattern was considered even if not in final predictions
            assert "time_based_task" in result.confidence_scores

    def test_predict_from_session_history(
        self, predictive_loader, sample_current_context
    ):
        """Test predictions based on session history."""
        # Add at least 2 historical sessions (implementation requires >= 2)
        historical_session1 = {
            "tool_sequence": ["manage_task", "Read", "Edit", "Write"],
            "context_sequence": ["ctx-100", "ctx-101", "ctx-102", "ctx-103"],
            "end_time": datetime.now(UTC),  # Required for session filtering
        }
        historical_session2 = {
            "tool_sequence": ["manage_task", "Read", "Grep"],
            "context_sequence": ["ctx-200", "ctx-201", "ctx-202"],
            "end_time": datetime.now(UTC),  # Required for session filtering
        }
        predictive_loader.session_history.append(historical_session1)
        predictive_loader.session_history.append(historical_session2)

        # Lower confidence threshold to ensure predictions are included
        predictive_loader.pattern_confidence_threshold = 0.4

        # Current session similar to historical - high similarity
        session_context = {
            "tool_sequence": ["manage_task", "Read"],  # Exact match prefix
            "context_sequence": ["ctx-100", "ctx-101"],  # Exact match prefix
        }

        result = predictive_loader.predict_next_contexts(
            sample_current_context,
            recent_tools=["manage_task", "Read"],
            session_context=session_context,
        )

        # Should predict either ctx-102 or ctx-202 as next based on similarity
        # Both sessions have similar tool sequences, so either is valid
        assert len(result.predicted_contexts) > 0
        assert any(ctx in ["ctx-102", "ctx-202"] for ctx in result.predicted_contexts)
        assert "session_history" in result.patterns_used

    def test_max_preload_contexts_limit(self, predictive_loader):
        """Test that predictions respect max_preload_contexts limit."""
        # Establish many transition patterns
        for i in range(10):
            predictive_loader.context_transitions[("ctx-123", f"ctx-{200 + i}")] = 5

        current_context = {"id": "ctx-123"}
        result = predictive_loader.predict_next_contexts(
            current_context, recent_tools=[], session_context=None
        )

        assert len(result.predicted_contexts) <= predictive_loader.max_preload_contexts

    def test_confidence_threshold_filtering(self, predictive_loader):
        """Test that predictions filter by confidence threshold."""
        # Set high threshold
        predictive_loader.pattern_confidence_threshold = 0.8

        # Add low-frequency pattern (low confidence)
        predictive_loader.context_transitions[("ctx-123", "ctx-124")] = 1

        current_context = {"id": "ctx-123"}
        result = predictive_loader.predict_next_contexts(
            current_context, recent_tools=[], session_context=None
        )

        # Should not include low-confidence prediction
        assert "ctx-124" not in result.predicted_contexts


class TestPatternManagement:
    """Test pattern management functionality."""

    def test_update_usage_patterns(self, predictive_loader):
        """Test updating usage patterns from session history."""
        # Add sessions to history
        for i in range(3):
            session = {
                "tool_sequence": ["manage_task", "Read", "Edit"],
                "context_sequence": [f"ctx-{i}00", f"ctx-{i}01"],
            }
            predictive_loader.session_history.append(session)

        # Update patterns
        predictive_loader._update_usage_patterns()

        # Should have created patterns
        assert len(predictive_loader.usage_patterns) > 0

        # Check pattern properties
        for pattern in predictive_loader.usage_patterns.values():
            assert pattern.pattern_type == "tool_sequence"
            assert pattern.trigger == PredictionTrigger.TOOL_SEQUENCE
            assert pattern.frequency >= 1
            assert 0.0 <= pattern.confidence <= 1.0

    def test_sequence_similarity_calculation(self, predictive_loader):
        """Test sequence similarity calculation."""
        seq1 = ["A", "B", "C", "D"]
        seq2 = ["B", "C", "D", "E"]

        similarity = predictive_loader._calculate_sequence_similarity(seq1, seq2)

        # Jaccard similarity: |{B,C,D}| / |{A,B,C,D,E}| = 3/5 = 0.6
        assert similarity == 0.6

    def test_sequence_similarity_empty(self, predictive_loader):
        """Test sequence similarity with empty sequences."""
        assert predictive_loader._calculate_sequence_similarity([], ["A"]) == 0.0
        assert predictive_loader._calculate_sequence_similarity(["A"], []) == 0.0
        assert predictive_loader._calculate_sequence_similarity([], []) == 0.0

    def test_tool_context_mapping(self, predictive_loader):
        """Test tool to context type mapping."""
        mapping = predictive_loader._get_tool_context_mapping()

        assert mapping["manage_task"] == "task"
        assert mapping["manage_git_branch"] == "branch"
        assert mapping["Bash"] == "execution"
        assert mapping["Read"] == "file"


class TestValidation:
    """Test prediction validation functionality."""

    def test_validate_predictions_all_correct(self, predictive_loader):
        """Test validation when all predictions are correct."""
        # Add pattern for tracking
        pattern = UsagePattern(
            pattern_id="test_pattern",
            pattern_type="test",
            trigger=PredictionTrigger.TOOL_SEQUENCE,
            sequence=["Read", "Edit"],
            confidence=0.8,
            frequency=5,
            last_seen=datetime.now(UTC),
            success_rate=0.0,
        )
        predictive_loader.usage_patterns["test_pattern"] = pattern

        predictions = ["ctx-100", "ctx-101", "ctx-102"]
        actual = ["ctx-100", "ctx-101", "ctx-102", "ctx-103"]

        accuracy = predictive_loader.validate_predictions(
            predictions, actual, ["test_pattern"]
        )

        assert accuracy["test_pattern"] == 1.0
        assert pattern.success_rate == 1.0

    def test_validate_predictions_partial_correct(self, predictive_loader):
        """Test validation with partial correct predictions."""
        # Add pattern for tracking
        pattern = UsagePattern(
            pattern_id="test_pattern",
            pattern_type="test",
            trigger=PredictionTrigger.CONTEXT_CHAIN,
            sequence=[],
            confidence=0.7,
            frequency=3,
            last_seen=datetime.now(UTC),
            success_rate=0.5,
        )
        predictive_loader.usage_patterns["test_pattern"] = pattern

        predictions = ["ctx-100", "ctx-101", "ctx-999"]
        actual = ["ctx-100", "ctx-102"]

        accuracy = predictive_loader.validate_predictions(
            predictions, actual, ["test_pattern"]
        )

        # 1/3 predictions correct = 0.333
        # Exponential moving average: 0.2 * 0.333 + 0.8 * 0.5 = 0.467
        assert 0.46 < accuracy["test_pattern"] < 0.47

    def test_validate_predictions_no_predictions(self, predictive_loader):
        """Test validation with no predictions."""
        accuracy = predictive_loader.validate_predictions([], ["ctx-100"], [])

        assert accuracy == {}


class TestStatistics:
    """Test statistics functionality."""

    def test_get_prediction_stats_empty(self, predictive_loader):
        """Test getting stats with no patterns."""
        stats = predictive_loader.get_prediction_stats()
        assert stats == {}

    def test_get_prediction_stats_with_patterns(self, predictive_loader):
        """Test getting stats with patterns."""
        # Add multiple patterns
        for i in range(5):
            pattern = UsagePattern(
                pattern_id=f"pattern_{i}",
                pattern_type="test",
                trigger=PredictionTrigger.TOOL_SEQUENCE,
                sequence=[],
                confidence=0.5 + i * 0.1,
                frequency=i + 1,
                last_seen=datetime.now(UTC),
                success_rate=0.6 + i * 0.05,
            )
            predictive_loader.usage_patterns[f"pattern_{i}"] = pattern

        # Add session history
        predictive_loader.session_history = [{"id": "sess1"}, {"id": "sess2"}]

        stats = predictive_loader.get_prediction_stats()

        assert stats["total_patterns"] == 5
        assert "avg_success_rate" in stats
        assert stats["high_confidence_patterns"] == 2  # patterns with confidence > 0.7
        assert stats["session_history_count"] == 2
        assert stats["pattern_confidence_threshold"] == 0.5
        assert "patterns" in stats
        assert len(stats["patterns"]) <= 10


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_predict_with_none_context(self, predictive_loader):
        """Test predictions with None values in context."""
        context = {"id": None, "context_id": None}

        result = predictive_loader.predict_next_contexts(
            context, recent_tools=[], session_context=None
        )

        assert isinstance(result, PredictionResult)
        assert result.predicted_contexts == []

    def test_predict_with_empty_recent_tools(
        self, predictive_loader, sample_current_context
    ):
        """Test predictions with empty recent tools."""
        result = predictive_loader.predict_next_contexts(
            sample_current_context, recent_tools=[], session_context=None
        )

        assert isinstance(result, PredictionResult)
        # Should still work, just no tool-based predictions

    def test_multiple_session_tracking(self, predictive_loader):
        """Test that only one session can be active at a time."""
        predictive_loader.start_session("sess-1")
        assert predictive_loader.current_session.session_id == "sess-1"

        # Starting new session replaces the old one
        predictive_loader.start_session("sess-2")
        assert predictive_loader.current_session.session_id == "sess-2"

    def test_pattern_frequency_updates(self, predictive_loader):
        """Test that pattern frequency increases correctly."""
        # Create initial pattern
        predictive_loader._update_usage_patterns()
        initial_count = len(predictive_loader.usage_patterns)

        # Add session with repeated pattern
        session = {
            "tool_sequence": ["Read", "Edit", "Write"],
            "context_sequence": ["ctx-1", "ctx-2"],
        }
        predictive_loader.session_history.append(session)
        predictive_loader._update_usage_patterns()

        # Pattern count should increase
        assert len(predictive_loader.usage_patterns) >= initial_count

        # Check frequency increases for existing patterns
        for pattern in predictive_loader.usage_patterns.values():
            assert pattern.frequency >= 1
            assert pattern.last_seen is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
