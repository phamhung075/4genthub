"""
Tests for Workflow Hints Simplifier Service
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any
from datetime import datetime

from fastmcp.task_management.application.services.workflow_hints_simplifier import (
    WorkflowHintsSimplifier,
    HintPriority,
    HintCategory,
    SimplificationLevel,
    WorkflowHint
)


class TestWorkflowHintsSimplifier:
    """Test Workflow Hints Simplifier functionality"""

    @pytest.fixture
    def simplifier(self):
        """Create workflow hints simplifier instance"""
        return WorkflowHintsSimplifier()

    @pytest.fixture
    def complex_hints(self):
        """Create complex workflow hints for testing"""
        return [
            WorkflowHint(
                id="hint1",
                category=HintCategory.NEXT_ACTION,
                priority=HintPriority.HIGH,
                message="Complete task A before starting task B due to dependency constraints",
                details="Task B requires outputs from task A. Ensure all tests pass.",
                context={"task_a_id": "123", "task_b_id": "456"}
            ),
            WorkflowHint(
                id="hint2",
                category=HintCategory.WARNING,
                priority=HintPriority.MEDIUM,
                message="Resource conflict detected between parallel tasks",
                details="Tasks C and D both require exclusive access to the database",
                context={"tasks": ["C", "D"], "resource": "database"}
            ),
            WorkflowHint(
                id="hint3",
                category=HintCategory.SUGGESTION,
                priority=HintPriority.LOW,
                message="Consider grouping similar tasks for efficiency",
                details="Tasks E, F, and G perform similar operations and could be batched",
                context={"similar_tasks": ["E", "F", "G"]}
            ),
            WorkflowHint(
                id="hint4",
                category=HintCategory.OPTIMIZATION,
                priority=HintPriority.LOW,
                message="Cache frequently accessed data to improve performance",
                details="Data X is accessed 50 times across different tasks",
                context={"data_id": "X", "access_count": 50}
            )
        ]

    def test_simplifier_initialization(self):
        """Test simplifier initialization"""
        simplifier = WorkflowHintsSimplifier(
            max_hints=10,
            default_level=SimplificationLevel.STANDARD
        )
        assert simplifier.max_hints == 10
        assert simplifier.default_level == SimplificationLevel.STANDARD

    def test_simplify_minimal_level(self, simplifier, complex_hints):
        """Test simplification at minimal level"""
        result = simplifier.simplify(
            hints=complex_hints,
            level=SimplificationLevel.MINIMAL
        )
        
        # Should only include high priority hints
        assert len(result) <= 2
        assert all(h.priority == HintPriority.HIGH or h.priority == HintPriority.MEDIUM for h in result)
        
        # Messages should be simplified
        for hint in result:
            assert len(hint.message) < 100
            assert hasattr(hint, 'details') is False or hint.details is None

    def test_simplify_standard_level(self, simplifier, complex_hints):
        """Test simplification at standard level"""
        result = simplifier.simplify(
            hints=complex_hints,
            level=SimplificationLevel.STANDARD
        )
        
        # Should include high and medium priority hints
        assert len(result) <= 3
        
        # Should have simplified messages but keep some details
        high_priority_hint = next(h for h in result if h.priority == HintPriority.HIGH)
        assert high_priority_hint.message is not None
        assert len(high_priority_hint.details or "") > 0

    def test_simplify_detailed_level(self, simplifier, complex_hints):
        """Test simplification at detailed level"""
        result = simplifier.simplify(
            hints=complex_hints,
            level=SimplificationLevel.DETAILED
        )
        
        # Should include most hints
        assert len(result) == len(complex_hints)
        
        # All details should be preserved
        for original, simplified in zip(complex_hints, result):
            assert simplified.message == original.message
            assert simplified.details == original.details
            assert simplified.context == original.context

    def test_group_similar_hints(self, simplifier):
        """Test grouping of similar hints"""
        similar_hints = [
            WorkflowHint(
                id=f"test_{i}",
                category=HintCategory.WARNING,
                priority=HintPriority.MEDIUM,
                message=f"Test {i} is failing",
                details=f"Test {i} failed with error XYZ"
            ) for i in range(5)
        ]
        
        result = simplifier.simplify(
            hints=similar_hints,
            group_similar=True
        )
        
        # Should group similar warnings
        assert len(result) < len(similar_hints)
        grouped_hint = result[0]
        assert "5 tests" in grouped_hint.message or "multiple" in grouped_hint.message

    def test_priority_based_filtering(self, simplifier, complex_hints):
        """Test filtering hints by priority"""
        result = simplifier.simplify(
            hints=complex_hints,
            min_priority=HintPriority.MEDIUM
        )
        
        # Should only include medium and high priority
        assert all(h.priority in [HintPriority.MEDIUM, HintPriority.HIGH] for h in result)
        assert len(result) == 2

    def test_category_based_filtering(self, simplifier, complex_hints):
        """Test filtering hints by category"""
        result = simplifier.simplify(
            hints=complex_hints,
            include_categories=[HintCategory.NEXT_ACTION, HintCategory.WARNING]
        )
        
        # Should only include specified categories
        assert all(h.category in [HintCategory.NEXT_ACTION, HintCategory.WARNING] for h in result)
        assert len(result) == 2

    def test_deduplication(self, simplifier):
        """Test deduplication of similar hints"""
        duplicate_hints = [
            WorkflowHint(
                id="1",
                category=HintCategory.SUGGESTION,
                priority=HintPriority.LOW,
                message="Optimize database queries"
            ),
            WorkflowHint(
                id="2",
                category=HintCategory.SUGGESTION,
                priority=HintPriority.LOW,
                message="Optimize database queries"  # Same message
            ),
            WorkflowHint(
                id="3",
                category=HintCategory.SUGGESTION,
                priority=HintPriority.LOW,
                message="Optimize DB queries"  # Similar message
            )
        ]
        
        result = simplifier.simplify(
            hints=duplicate_hints,
            deduplicate=True
        )
        
        # Should remove duplicates
        assert len(result) <= 2

    def test_context_aware_simplification(self, simplifier):
        """Test context-aware hint simplification"""
        hints_with_context = [
            WorkflowHint(
                id="1",
                category=HintCategory.NEXT_ACTION,
                priority=HintPriority.HIGH,
                message="Complete authentication implementation",
                context={"user_role": "developer", "experience": "senior"}
            ),
            WorkflowHint(
                id="2",
                category=HintCategory.NEXT_ACTION,
                priority=HintPriority.HIGH,
                message="Review authentication documentation",
                context={"user_role": "developer", "experience": "junior"}
            )
        ]
        
        # Simplify for senior developer
        result = simplifier.simplify(
            hints=hints_with_context,
            user_context={"experience": "senior"}
        )
        
        # Should prioritize hints relevant to senior developers
        assert any("implementation" in h.message for h in result)

    def test_time_based_relevance(self, simplifier):
        """Test time-based hint relevance"""
        old_hint = WorkflowHint(
            id="old",
            category=HintCategory.SUGGESTION,
            priority=HintPriority.LOW,
            message="Old suggestion",
            created_at=datetime.now().timestamp() - 86400 * 7  # 7 days old
        )
        
        recent_hint = WorkflowHint(
            id="recent",
            category=HintCategory.SUGGESTION,
            priority=HintPriority.LOW,
            message="Recent suggestion",
            created_at=datetime.now().timestamp()
        )
        
        result = simplifier.simplify(
            hints=[old_hint, recent_hint],
            max_age_days=3
        )
        
        # Should only include recent hints
        assert len(result) == 1
        assert result[0].id == "recent"

    def test_format_hints_for_display(self, simplifier, complex_hints):
        """Test formatting hints for different display contexts"""
        # Format for CLI display
        cli_formatted = simplifier.format_for_display(
            hints=complex_hints[:2],
            display_type="cli",
            max_width=80
        )
        
        assert isinstance(cli_formatted, str)
        assert "HIGH" in cli_formatted
        assert len(cli_formatted.split('\n')[0]) <= 80
        
        # Format for web display
        web_formatted = simplifier.format_for_display(
            hints=complex_hints[:2],
            display_type="web"
        )
        
        assert isinstance(web_formatted, dict) or "<" in web_formatted  # HTML or dict

    def test_actionable_hints_extraction(self, simplifier, complex_hints):
        """Test extraction of actionable hints"""
        actionable = simplifier.get_actionable_hints(complex_hints)
        
        # Should prioritize NEXT_ACTION category
        assert len(actionable) > 0
        assert actionable[0].category == HintCategory.NEXT_ACTION
        
        # Should include specific action details
        for hint in actionable:
            assert hint.context is not None
            assert "id" in str(hint.context) or "task" in str(hint.context)

    def test_hint_aggregation(self, simplifier):
        """Test aggregation of multiple hint sources"""
        source1_hints = [
            WorkflowHint(
                id="s1_1",
                category=HintCategory.WARNING,
                priority=HintPriority.HIGH,
                message="Database connection issue"
            )
        ]
        
        source2_hints = [
            WorkflowHint(
                id="s2_1",
                category=HintCategory.SUGGESTION,
                priority=HintPriority.MEDIUM,
                message="Optimize query performance"
            )
        ]
        
        aggregated = simplifier.aggregate_hints(
            sources={
                "monitoring": source1_hints,
                "optimizer": source2_hints
            }
        )
        
        assert len(aggregated) == 2
        # Should be sorted by priority
        assert aggregated[0].priority == HintPriority.HIGH

    def test_hint_templates(self, simplifier):
        """Test using hint templates for common scenarios"""
        # Register template
        simplifier.register_template(
            name="dependency_warning",
            template="Task {{task_name}} depends on {{dependency_name}} which is not complete"
        )
        
        # Generate hint from template
        hint = simplifier.create_from_template(
            template_name="dependency_warning",
            category=HintCategory.WARNING,
            priority=HintPriority.HIGH,
            context={
                "task_name": "Deploy to Production",
                "dependency_name": "Run Tests"
            }
        )
        
        assert "Deploy to Production" in hint.message
        assert "Run Tests" in hint.message

    def test_ml_based_prioritization(self, simplifier):
        """Test ML-based hint prioritization"""
        hints = [
            WorkflowHint(
                id=str(i),
                category=HintCategory.SUGGESTION,
                priority=HintPriority.MEDIUM,
                message=f"Suggestion {i}",
                context={"impact_score": i * 10, "user_actions": i * 2}
            ) for i in range(10)
        ]
        
        # Simulate ML scoring
        with patch.object(simplifier, 'ml_score_hint') as mock_ml:
            mock_ml.side_effect = lambda h: float(h.context.get("impact_score", 0))
            
            result = simplifier.simplify(
                hints=hints,
                use_ml_ranking=True,
                max_hints=3
            )
        
        # Should return highest scored hints
        assert len(result) == 3
        assert all(int(h.id) >= 7 for h in result)

    def test_internationalization(self, simplifier):
        """Test hint message internationalization"""
        hint = WorkflowHint(
            id="i18n_test",
            category=HintCategory.NEXT_ACTION,
            priority=HintPriority.HIGH,
            message_key="workflow.task.complete_first",
            message_params={"task": "Authentication"}
        )
        
        # Simulate translation
        translated = simplifier.translate_hints(
            hints=[hint],
            locale="es"
        )
        
        # Would check for Spanish translation
        assert len(translated) == 1

    def test_performance_optimization(self, simplifier):
        """Test performance with large number of hints"""
        import time
        
        # Generate many hints
        large_hints = [
            WorkflowHint(
                id=str(i),
                category=HintCategory.SUGGESTION,
                priority=HintPriority.LOW,
                message=f"Hint {i}",
                details=f"Details for hint {i}" * 10
            ) for i in range(1000)
        ]
        
        start_time = time.time()
        result = simplifier.simplify(
            hints=large_hints,
            level=SimplificationLevel.MINIMAL,
            max_hints=10
        )
        elapsed = time.time() - start_time
        
        # Should handle large sets efficiently
        assert elapsed < 0.1  # Less than 100ms
        assert len(result) == 10

    def test_hint_persistence(self, simplifier, complex_hints):
        """Test saving and loading hint configurations"""
        # Save current hints
        config = simplifier.save_configuration(
            hints=complex_hints,
            name="test_workflow"
        )
        
        assert "hints" in config
        assert "settings" in config
        assert config["name"] == "test_workflow"
        
        # Load configuration
        loaded_hints = simplifier.load_configuration(config)
        assert len(loaded_hints) == len(complex_hints)