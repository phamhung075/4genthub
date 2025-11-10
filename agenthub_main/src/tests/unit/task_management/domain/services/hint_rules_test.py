"""Unit tests for Hint Rules Domain Service"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from fastmcp.task_management.domain.entities.context import TaskContext
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.services.hint_rules import (
    CollaborationNeededRule,
    ComplexDependencyRule,
    ImplementationReadyForTestingRule,
    MissingContextRule,
    NearCompletionRule,
    ProgressBasedHintRule,
    RuleContext,
    StalledProgressRule,
)
from fastmcp.task_management.domain.value_objects.hints import (
    HintPriority,
    HintType,
)
from fastmcp.task_management.domain.value_objects.progress import (
    ProgressType,
)


class TestRuleContext:
    
    def test_rule_context_initialization(self):
        """Test RuleContext initialization with defaults"""
        task = Mock(spec=Task)
        context = RuleContext(task=task)
        
        assert context.task == task
        assert context.context is None
        assert context.related_tasks == []
        assert context.historical_patterns == {}
    
    def test_rule_context_with_all_fields(self):
        """Test RuleContext with all fields provided"""
        task = Mock(spec=Task)
        task_context = Mock(spec=TaskContext)
        related = [Mock(spec=Task)]
        patterns = {"pattern": "value"}
        
        context = RuleContext(
            task=task,
            context=task_context,
            related_tasks=related,
            historical_patterns=patterns
        )
        
        assert context.task == task
        assert context.context == task_context
        assert context.related_tasks == related
        assert context.historical_patterns == patterns


class TestProgressBasedHintRule:
    
    @pytest.fixture
    def rule(self):
        # Create concrete implementation for testing
        class TestRule(ProgressBasedHintRule):
            @property
            def rule_name(self):
                return "test_rule"
            
            def evaluate(self, rule_context):
                return None
        
        return TestRule()
    
    def test_get_latest_progress_no_timeline(self, rule):
        """Test getting latest progress when no timeline exists"""
        task = Mock(spec=Task)
        task.progress_timeline = None
        
        result = rule.get_latest_progress(task)
        assert result is None
    
    def test_get_latest_progress_empty_timeline(self, rule):
        """Test getting latest progress from empty timeline"""
        task = Mock(spec=Task)
        task.progress_timeline = []
        
        result = rule.get_latest_progress(task)
        assert result is None
    
    def test_get_latest_progress_success(self, rule):
        """Test getting latest progress entry"""
        task = Mock(spec=Task)
        task.progress_timeline = [
            {"type": "implementation", "timestamp": "2024-01-01"},
            {"type": "testing", "timestamp": "2024-01-02"}
        ]
        
        result = rule.get_latest_progress(task)
        assert result == {"type": "testing", "timestamp": "2024-01-02"}
    
    def test_get_latest_progress_by_type(self, rule):
        """Test getting latest progress filtered by type"""
        task = Mock(spec=Task)
        task.progress_timeline = [
            {"type": ProgressType.IMPLEMENTATION.value, "timestamp": "2024-01-01"},
            {"type": ProgressType.TESTING.value, "timestamp": "2024-01-02"},
            {"type": ProgressType.IMPLEMENTATION.value, "timestamp": "2024-01-03"}
        ]
        
        result = rule.get_latest_progress(task, ProgressType.IMPLEMENTATION)
        assert result == {"type": ProgressType.IMPLEMENTATION.value, "timestamp": "2024-01-03"}
    
    def test_get_latest_progress_type_not_found(self, rule):
        """Test getting latest progress when type not found"""
        task = Mock(spec=Task)
        task.progress_timeline = [
            {"type": ProgressType.IMPLEMENTATION.value, "timestamp": "2024-01-01"}
        ]
        
        result = rule.get_latest_progress(task, ProgressType.DOCUMENTATION)
        assert result is None


class TestStalledProgressRule:
    
    @pytest.fixture
    def rule(self):
        return StalledProgressRule(stall_hours=24)
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.status = Mock()
        task.status.value = "in_progress"
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "stalled_progress"
    
    def test_evaluate_no_progress(self, rule, mock_task):
        """Test evaluation with no progress data"""
        mock_task.progress_timeline = []
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_recent_progress(self, rule, mock_task):
        """Test evaluation with recent progress"""
        recent_time = datetime.now(UTC) - timedelta(hours=10)
        mock_task.progress_timeline = [
            {"timestamp": recent_time.isoformat()}
        ]
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None  # Not stalled yet
    
    def test_evaluate_stalled_blocked(self, rule, mock_task):
        """Test evaluation for stalled blocked task"""
        stalled_time = datetime.now(UTC) - timedelta(hours=49)  # More than 48 hours for CRITICAL priority
        mock_task.progress_timeline = [
            {"timestamp": stalled_time.isoformat()}
        ]
        mock_task.status.value = "blocked"
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.BLOCKER_RESOLUTION
        assert result.priority == HintPriority.CRITICAL
        assert "49 hours" in result.message
        assert result.metadata.patterns_detected == ["extended_blocker"]
    
    def test_evaluate_stalled_not_blocked(self, rule, mock_task):
        """Test evaluation for stalled non-blocked task"""
        stalled_time = datetime.now(UTC) - timedelta(hours=30)
        mock_task.progress_timeline = [
            {"timestamp": stalled_time.isoformat()}
        ]
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.NEXT_ACTION
        assert result.priority == HintPriority.HIGH
        assert "30 hours" in result.message
        assert result.metadata.patterns_detected == ["progress_stall"]
    
    def test_custom_stall_hours(self):
        """Test rule with custom stall hours"""
        rule = StalledProgressRule(stall_hours=12)
        assert rule.stall_hours == 12


class TestImplementationReadyForTestingRule:
    
    @pytest.fixture
    def rule(self):
        return ImplementationReadyForTestingRule()
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.progress_breakdown = {
            ProgressType.IMPLEMENTATION.value: 0.8,
            ProgressType.TESTING.value: 0.0
        }
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "implementation_ready_for_testing"
    
    def test_evaluate_implementation_not_ready(self, rule, mock_task):
        """Test when implementation is not sufficiently complete"""
        mock_task.progress_breakdown[ProgressType.IMPLEMENTATION.value] = 0.5
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_no_progress_data(self, rule):
        """Test with no progress breakdown"""
        task = Mock(spec=Task)
        task.id = "task-123"
        # No progress_breakdown attribute
        
        context = RuleContext(task=task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_testing_already_started(self, rule, mock_task):
        """Test when testing has already started"""
        mock_task.progress_breakdown[ProgressType.TESTING.value] = 0.2
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_ready_for_testing(self, rule, mock_task):
        """Test when implementation is ready for testing"""
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.NEXT_ACTION
        assert result.priority == HintPriority.HIGH
        assert "80% complete" in result.message
        assert "ready for testing" in result.message
        assert result.metadata.patterns_detected == ["parallel_testing_opportunity"]
        assert result.context_data["implementation_progress"] == 0.8
        assert result.context_data["testing_progress"] == 0.0
    
    def test_custom_threshold(self):
        """Test rule with custom implementation threshold"""
        rule = ImplementationReadyForTestingRule(implementation_threshold=0.9)
        assert rule.implementation_threshold == 0.9


class TestMissingContextRule:
    
    @pytest.fixture
    def rule(self):
        return MissingContextRule()
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.status = Mock()
        task.status.value = "in_progress"
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "missing_context"
    
    def test_evaluate_no_context(self, rule, mock_task):
        """Test evaluation with completely missing context"""
        context = RuleContext(task=mock_task, context=None)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.NEXT_ACTION
        assert result.priority == HintPriority.HIGH
        assert "missing context information" in result.message
        assert result.metadata.patterns_detected == ["missing_context"]
    
    def test_evaluate_complete_context(self, rule, mock_task):
        """Test evaluation with complete context"""
        task_context = Mock(spec=TaskContext)
        task_context.notes = {
            'test_notes': "Some test notes",
            'design_decisions': "Some design decisions"
        }
        task_context.data = {
            'completion_summary': "Task completed successfully"
        }
        
        context = RuleContext(task=mock_task, context=task_context)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_missing_test_notes(self, rule, mock_task):
        """Test evaluation with missing test notes"""
        task_context = Mock(spec=TaskContext)
        task_context.notes = {
            'design_decisions': "Some design decisions"
        }
        task_context.data = {}
        
        context = RuleContext(task=mock_task, context=task_context)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.COMPLETION
        assert "test notes" in result.message
        assert "test notes" in result.context_data["missing_fields"]
    
    def test_evaluate_missing_completion_summary(self, rule, mock_task):
        """Test evaluation with missing completion summary for done task"""
        mock_task.status.value = "done"
        
        task_context = Mock(spec=TaskContext)
        task_context.notes = {
            'test_notes': "Test notes",
            'design_decisions': "Design decisions"
        }
        task_context.data = {}
        
        context = RuleContext(task=mock_task, context=task_context)
        result = rule.evaluate(context)
        
        assert result is not None
        assert "completion summary" in result.message
        assert "completion summary" in result.context_data["missing_fields"]


class TestComplexDependencyRule:
    
    @pytest.fixture
    def rule(self):
        return ComplexDependencyRule()
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.dependencies = ["dep1", "dep2", "dep3", "dep4"]
        task.subtasks = []
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "complex_dependencies"
    
    def test_evaluate_simple_dependencies(self, rule, mock_task):
        """Test evaluation with simple dependencies"""
        mock_task.dependencies = ["dep1", "dep2"]
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_no_dependencies(self, rule):
        """Test evaluation with no dependencies"""
        task = Mock(spec=Task)
        task.id = "task-123"
        # No dependencies attribute
        
        context = RuleContext(task=task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_has_subtasks(self, rule, mock_task):
        """Test evaluation when task already has subtasks"""
        mock_task.subtasks = ["subtask1", "subtask2"]
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_complex_dependencies(self, rule, mock_task):
        """Test evaluation with complex dependencies"""
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.OPTIMIZATION
        assert result.priority == HintPriority.MEDIUM
        assert "4 dependencies" in result.message
        assert result.metadata.patterns_detected == ["high_complexity"]
        assert result.context_data["dependency_count"] == 4
    
    def test_custom_threshold(self):
        """Test rule with custom complexity threshold"""
        rule = ComplexDependencyRule(complexity_threshold=5)
        assert rule.complexity_threshold == 5


class TestNearCompletionRule:
    
    @pytest.fixture
    def rule(self):
        return NearCompletionRule()
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.progress = 0.92
        task.progress_breakdown = {
            ProgressType.IMPLEMENTATION.value: 1.0,
            ProgressType.TESTING.value: 0.8,
            ProgressType.DOCUMENTATION.value: 0.5,
            ProgressType.REVIEW.value: 0.8
        }
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "near_completion"
    
    def test_evaluate_not_near_completion(self, rule, mock_task):
        """Test evaluation when not near completion"""
        mock_task.progress = 0.5
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_no_progress(self, rule):
        """Test evaluation with no progress attribute"""
        task = Mock(spec=Task)
        task.id = "task-123"
        # No progress attribute
        
        context = RuleContext(task=task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_all_complete(self, rule, mock_task):
        """Test evaluation when all steps are complete"""
        mock_task.progress_breakdown = {
            ProgressType.IMPLEMENTATION.value: 1.0,
            ProgressType.TESTING.value: 1.0,
            ProgressType.DOCUMENTATION.value: 1.0,
            ProgressType.REVIEW.value: 1.0
        }
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_near_completion_missing_steps(self, rule, mock_task):
        """Test evaluation near completion with missing steps"""
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.COMPLETION
        assert result.priority == HintPriority.HIGH
        assert "92% complete" in result.message
        assert "complete testing" in result.suggested_action
        assert "update documentation" in result.suggested_action
        assert "complete review" in result.suggested_action
        assert result.context_data["overall_progress"] == 0.92
        assert len(result.context_data["missing_steps"]) == 3
    
    def test_custom_threshold(self):
        """Test rule with custom completion threshold"""
        rule = NearCompletionRule(completion_threshold=0.95)
        assert rule.completion_threshold == 0.95


class TestCollaborationNeededRule:
    
    @pytest.fixture
    def rule(self):
        return CollaborationNeededRule()
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = "task-123"
        task.status = Mock()
        task.status.value = "in_progress"
        task.priority = Mock()
        task.priority.label = "medium"
        task.created_at = datetime.now(UTC) - timedelta(days=3)
        task.progress = 0.2
        return task
    
    def test_rule_name(self, rule):
        """Test rule name property"""
        assert rule.rule_name == "collaboration_needed"
    
    def test_evaluate_no_indicators(self, rule, mock_task):
        """Test evaluation with no collaboration indicators"""
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_evaluate_long_running_task(self, rule, mock_task):
        """Test evaluation for long-running task"""
        mock_task.created_at = datetime.now(UTC) - timedelta(days=10)
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.type == HintType.COLLABORATION
        assert result.priority == HintPriority.MEDIUM
        assert "long_running" in result.metadata.patterns_detected
    
    def test_evaluate_multiple_failures(self, rule, mock_task):
        """Test evaluation for multiple failed attempts"""
        task_context = Mock(spec=TaskContext)
        task_context.notes = {"failed_attempts": 3}
        
        context = RuleContext(task=mock_task, context=task_context)
        result = rule.evaluate(context)
        
        assert result is not None
        assert "multiple_failures" in result.metadata.patterns_detected
    
    def test_evaluate_high_priority_slow_progress(self, rule, mock_task):
        """Test evaluation for high priority with slow progress"""
        mock_task.priority.label = "urgent"
        mock_task.progress = 0.1
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is not None
        assert "high_priority_slow_progress" in result.metadata.patterns_detected
    
    def test_evaluate_completed_task(self, rule, mock_task):
        """Test evaluation skips completed tasks"""
        mock_task.created_at = datetime.now(UTC) - timedelta(days=10)
        mock_task.status.value = "done"
        
        context = RuleContext(task=mock_task)
        result = rule.evaluate(context)
        
        assert result is None