"""Tests for HintOptimizer - AI-optimized workflow guidance transformer

Tests the ultra-fast hint optimizer that converts verbose workflow guidance
into AI-friendly flat hints structure with 70% payload reduction.
"""

import pytest
import time
from unittest.mock import Mock, patch

from fastmcp.task_management.application.services.hint_optimizer import (
    HintOptimizer,
    ActionType
)


class TestHintOptimizer:
    """Test suite for HintOptimizer functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = HintOptimizer()

    def test_init_creates_clean_metrics(self):
        """Test that initialization creates clean metrics"""
        assert self.optimizer.metrics['hints_processed'] == 0
        assert self.optimizer.metrics['original_chars'] == 0
        assert self.optimizer.metrics['optimized_chars'] == 0
        assert self.optimizer.metrics['processing_time_ms'] == 0
        assert self.optimizer.metrics['average_reduction_percent'] == 0.0
        assert self.optimizer.metrics['action_extractions'] == 0
        assert self.optimizer.metrics['entity_extractions'] == 0

    def test_optimize_empty_guidance(self):
        """Test optimization with empty or invalid guidance"""
        result = self.optimizer.optimize_workflow_hints({})
        assert result == {"hints": {}}

        result = self.optimizer.optimize_workflow_hints(None)
        assert result == {"hints": {}}

        result = self.optimizer.optimize_workflow_hints("invalid")
        assert result == {"hints": {}}

    def test_optimize_basic_workflow_guidance(self):
        """Test optimization with basic workflow guidance structure"""
        guidance = {
            "next_steps": {
                "required_actions": ["You should update the task status", "Please add a description"],
                "recommendations": ["Consider increasing priority", "You might want to verify completion"]
            },
            "autonomous_guidance": {
                "confidence": 0.85
            }
        }

        result = self.optimizer.optimize_workflow_hints(guidance)
        
        assert "hints" in result
        hints = result["hints"]
        
        # Check next action extraction
        assert "next" in hints
        assert hints["next"] == "update"
        
        # Check required actions
        assert "required" in hints
        assert len(hints["required"]) <= 3
        assert "update" in hints["required"][0]
        
        # Check tips
        assert "tips" in hints
        assert len(hints["tips"]) <= 2
        
        # Check confidence
        assert "confidence" in hints
        assert hints["confidence"] == 0.85

    def test_extract_next_action_from_autonomous_guidance(self):
        """Test next action extraction from autonomous guidance"""
        guidance = {
            "autonomous_guidance": {
                "recommendations": ["Create a new task immediately", "Update existing records"],
                "next_action": "review the current status"
            }
        }

        next_action = self.optimizer._extract_next_action(guidance)
        assert next_action == "create"

    def test_extract_next_action_from_next_steps(self):
        """Test next action extraction from next steps"""
        guidance = {
            "next_steps": {
                "required_actions": ["Fix the validation errors", "Complete the implementation"]
            }
        }

        next_action = self.optimizer._extract_next_action(guidance)
        assert next_action == "fix"

    def test_extract_required_actions_with_validation_errors(self):
        """Test required actions extraction including validation errors"""
        guidance = {
            "next_steps": {
                "required_actions": ["Update task title", "Add description"]
            },
            "validation": {
                "errors": [
                    {"field": "assignees", "message": "Missing assignees"},
                    {"field": "priority", "message": "Invalid priority"}
                ]
            }
        }

        required = self.optimizer._extract_required_actions(guidance, 5)
        
        assert len(required) <= 5
        assert any("update" in action for action in required)
        assert any("add" in action for action in required)
        assert any("fix" in action for action in required)

    def test_extract_required_actions_with_dependencies(self):
        """Test required actions extraction with dependencies"""
        guidance = {
            "dependencies": {
                "blocked_by": ["task-1", "task-2", "task-3"]
            }
        }

        required = self.optimizer._extract_required_actions(guidance, 3)
        
        assert len(required) >= 1
        assert any("resolve" in action and "dependencies" in action for action in required)

    def test_extract_tips_from_recommendations(self):
        """Test tips extraction from recommendations"""
        guidance = {
            "next_steps": {
                "recommendations": ["First action", "Consider adding priority", "You might want to set deadline"],
                "optional_actions": ["Review documentation", "Update related tasks"]
            }
        }

        tips = self.optimizer._extract_tips(guidance, 2)

        assert len(tips) <= 2
        # Current implementation prioritizes optional_actions over recommendations
        assert any("review" in tip or "update" in tip for tip in tips)

    def test_extract_tips_from_autonomous_suggestions(self):
        """Test tips extraction from autonomous suggestions"""
        guidance = {
            "autonomous_guidance": {
                "suggestions": ["Optimize performance", "Add logging for debugging"]
            }
        }

        tips = self.optimizer._extract_tips(guidance, 2)
        
        assert len(tips) <= 2
        assert any("optimize" in tip for tip in tips)

    def test_extract_critical_warnings_only(self):
        """Test that only critical warnings are extracted"""
        guidance = {
            "validation": {
                "warnings": [
                    "This is a minor issue",  # Not critical
                    "Critical error in validation",  # Critical
                    "Missing required field",  # Critical
                    "Consider improving performance"  # Not critical
                ]
            }
        }

        warnings = self.optimizer._extract_warnings(guidance)
        
        assert len(warnings) <= 2
        assert any("critical" in warning or "error" in warning for warning in warnings)
        assert any("missing" in warning or "required" in warning for warning in warnings)

    def test_is_critical_warning_detection(self):
        """Test critical warning detection logic"""
        assert self.optimizer._is_critical_warning("Critical error occurred") == True
        assert self.optimizer._is_critical_warning("Unable to process request") == True
        assert self.optimizer._is_critical_warning("Missing required field") == True
        assert self.optimizer._is_critical_warning("Task failed to complete") == True
        assert self.optimizer._is_critical_warning("Invalid configuration") == True
        
        assert self.optimizer._is_critical_warning("Consider improving this") == False
        assert self.optimizer._is_critical_warning("You might want to update") == False
        assert self.optimizer._is_critical_warning("Performance could be better") == False

    def test_simplify_action_removes_redundant_phrases(self):
        """Test action simplification removes redundant phrases"""
        test_cases = [
            ("You should create a new task", "create"),
            ("Please update the existing record", "update"),
            ("Consider adding more details", "add"),  # Normalized to canonical form
            ("It is recommended to verify the results", "verify"),
            ("Go ahead and delete the old files", "delete"),
            ("Make sure to complete the implementation", "complete")
        ]

        for original, expected in test_cases:
            result = self.optimizer._simplify_action(original)
            assert expected in result or result == expected

    def test_simplify_action_extracts_core_verbs(self):
        """Test action simplification extracts core action verbs"""
        test_cases = [
            ("creating new user account", "create"),
            ("updating existing configuration", "update"),
            ("deleting obsolete records", "delete"),
            ("verifying data integrity", "verify"),
            ("fixing validation errors", "fix"),
            ("completing the workflow", "complete")
        ]

        for original, expected in test_cases:
            result = self.optimizer._simplify_action(original)
            assert result == expected

    def test_simplify_action_handles_entity_extraction(self):
        """Test action simplification with entity extraction"""
        with patch.object(self.optimizer, '_extract_entities', return_value=['user123']):
            result = self.optimizer._simplify_action("create new user account")
            assert "create" in result

        with patch.object(self.optimizer, '_extract_entities', return_value=[]):
            result = self.optimizer._simplify_action("create new user account")
            assert result == "create"

    def test_extract_entities_finds_uuids_and_agents(self):
        """Test entity extraction finds UUIDs and agent names"""
        test_text = "Update task: 550e8400-e29b-41d4-a716-446655440000 assigned to @coding-agent"
        
        entities = self.optimizer._extract_entities(test_text)
        
        assert len(entities) > 0
        # Should find UUID and agent name
        uuid_found = any(len(entity) == 36 and '-' in entity for entity in entities)
        agent_found = any('coding' in entity or 'agent' in entity for entity in entities)
        assert uuid_found or agent_found

    def test_extract_entities_prioritizes_agent_names(self):
        """Test entity extraction prioritizes agent names"""
        test_text = "Assign to @test-agent and task_id: 12345"
        
        entities = self.optimizer._extract_entities(test_text)
        
        # Agent names should come first
        if entities:
            first_entity = entities[0]
            assert any(char.isalpha() for char in first_entity)

    def test_simplify_warning_preserves_critical_keywords(self):
        """Test warning simplification preserves critical keywords"""
        test_cases = [
            ("Critical error in the validation process", "critical_error"),
            ("Missing required field for user data", "missing_required"),
            ("Unable to connect to the database", "unable_connect"),
            ("Invalid configuration in the settings", "invalid_configuration")
        ]

        for original, expected_pattern in test_cases:
            result = self.optimizer._simplify_warning(original)
            # Check that the result contains key parts of expected pattern
            assert any(word in result for word in expected_pattern.split('_'))

    def test_metrics_tracking_during_optimization(self):
        """Test that metrics are properly tracked during optimization"""
        guidance = {
            "next_steps": {
                "required_actions": ["Create new task", "Update status"],
                "recommendations": ["Add priority", "Set deadline"]
            }
        }

        initial_processed = self.optimizer.metrics['hints_processed']
        initial_actions = self.optimizer.metrics['action_extractions']

        result = self.optimizer.optimize_workflow_hints(guidance)

        assert self.optimizer.metrics['hints_processed'] == initial_processed + 1
        assert self.optimizer.metrics['action_extractions'] > initial_actions
        assert self.optimizer.metrics['original_chars'] > 0
        assert self.optimizer.metrics['optimized_chars'] > 0

    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        # Process some hints to generate metrics
        guidance = {
            "next_steps": {
                "required_actions": ["This is a very long action that should be simplified significantly"],
                "recommendations": ["Another long recommendation that needs optimization"]
            }
        }

        self.optimizer.optimize_workflow_hints(guidance)
        metrics = self.optimizer.get_performance_metrics()

        assert metrics['hints_processed'] == 1
        assert metrics['average_reduction_percent'] >= 0
        assert metrics['average_processing_time_ms'] >= 0
        assert metrics['total_bytes_saved'] >= 0
        assert metrics['compression_ratio'] >= 0
        assert metrics['estimated_ai_speedup_percent'] >= 0

    def test_reset_metrics_clears_all_counters(self):
        """Test that reset_metrics clears all metric counters"""
        # Generate some metrics first
        guidance = {"next_steps": {"required_actions": ["test action"]}}
        self.optimizer.optimize_workflow_hints(guidance)

        # Verify metrics exist
        assert self.optimizer.metrics['hints_processed'] > 0

        # Reset and verify
        self.optimizer.reset_metrics()
        
        assert self.optimizer.metrics['hints_processed'] == 0
        assert self.optimizer.metrics['original_chars'] == 0
        assert self.optimizer.metrics['optimized_chars'] == 0
        assert self.optimizer.metrics['processing_time_ms'] == 0
        assert self.optimizer.metrics['average_reduction_percent'] == 0.0

    def test_create_legacy_compatible_response(self):
        """Test creation of legacy-compatible response structure"""
        hints = {
            "hints": {
                "next": "create_task",
                "required": ["add_description", "set_priority"],
                "tips": ["consider_deadline"],
                "warnings": ["missing_assignee"],
                "confidence": 0.9
            }
        }

        original_guidance = {"some": "original structure"}
        
        result = self.optimizer.create_legacy_compatible_response(hints, original_guidance)

        assert "hints" in result
        assert "workflow_guidance" in result
        
        # Check new structure
        assert result["hints"]["next"] == "create_task"
        assert result["hints"]["required"] == ["add_description", "set_priority"]
        
        # Check legacy structure
        legacy = result["workflow_guidance"]
        assert "next_steps" in legacy
        assert legacy["next_steps"]["recommendations"] == ["consider_deadline"]
        assert legacy["next_steps"]["required_actions"] == ["add_description", "set_priority"]
        assert legacy["confidence"] == 0.9
        
        # Check warnings are properly mapped
        assert "validation" in legacy
        assert legacy["validation"]["warnings"] == ["missing_assignee"]

    def test_wrapped_guidance_structure_handling(self):
        """Test handling of wrapped guidance structures"""
        wrapped_guidance = {
            "workflow_guidance": {
                "next_steps": {
                    "required_actions": ["Update the task"],
                    "recommendations": ["Add more details"]
                }
            }
        }

        result = self.optimizer.optimize_workflow_hints(wrapped_guidance)
        
        assert "hints" in result
        hints = result["hints"]
        assert "next" in hints
        assert hints["next"] == "update"

    def test_max_limits_are_respected(self):
        """Test that max limits for required actions and tips are respected"""
        guidance = {
            "next_steps": {
                "required_actions": [
                    "Action 1", "Action 2", "Action 3", "Action 4", "Action 5"
                ],
                "recommendations": [
                    "Tip 1", "Tip 2", "Tip 3", "Tip 4", "Tip 5"
                ]
            }
        }

        result = self.optimizer.optimize_workflow_hints(guidance, max_required=2, max_tips=1)
        hints = result["hints"]
        
        if "required" in hints:
            assert len(hints["required"]) <= 2
        if "tips" in hints:
            assert len(hints["tips"]) <= 1

    def test_action_type_enum_values(self):
        """Test ActionType enum contains expected values"""
        expected_actions = [
            "create", "update", "delete", "add", "remove",
            "verify", "complete", "review", "fix", "optimize"
        ]
        
        for action in expected_actions:
            assert hasattr(ActionType, action.upper())
            assert getattr(ActionType, action.upper()).value == action

    def test_confidence_extraction_priority(self):
        """Test confidence extraction prioritizes autonomous guidance"""
        guidance = {
            "confidence": 0.5,  # Lower priority
            "autonomous_guidance": {
                "confidence": 0.8  # Higher priority
            }
        }

        confidence = self.optimizer._extract_confidence(guidance)
        assert confidence == 0.8

    def test_processing_time_measurement(self):
        """Test that processing time is measured"""
        guidance = {
            "next_steps": {
                "required_actions": ["Test action"]
            }
        }

        start_time = time.perf_counter()
        self.optimizer.optimize_workflow_hints(guidance)
        end_time = time.perf_counter()

        assert self.optimizer.metrics['processing_time_ms'] > 0
        # Should be reasonable (less than actual elapsed time in ms)
        elapsed_ms = (end_time - start_time) * 1000
        assert self.optimizer.metrics['processing_time_ms'] <= elapsed_ms * 2  # Allow some overhead

    def test_empty_metrics_when_no_processing(self):
        """Test metrics return empty when no processing has occurred"""
        metrics = self.optimizer.get_performance_metrics()
        
        assert metrics['hints_processed'] == 0
        assert metrics['average_reduction_percent'] == 0.0
        assert metrics['average_processing_time_ms'] == 0.0
        assert metrics['total_bytes_saved'] == 0
        assert metrics['estimated_ai_speedup_percent'] == 0.0

    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation"""
        # Force specific metrics for testing
        self.optimizer.metrics['original_chars'] = 1000
        self.optimizer.metrics['optimized_chars'] = 300
        self.optimizer.metrics['hints_processed'] = 1

        metrics = self.optimizer.get_performance_metrics()
        
        # 300/1000 * 100 = 30%
        assert metrics['compression_ratio'] == 30.0
        # 1000 - 300 = 700 bytes saved
        assert metrics['total_bytes_saved'] == 700

    def test_ai_speedup_calculation_caps_at_40_percent(self):
        """Test AI speedup calculation caps at 40%"""
        # Force high reduction percentage
        self.optimizer.metrics['average_reduction_percent'] = 80.0
        self.optimizer.metrics['hints_processed'] = 1

        metrics = self.optimizer.get_performance_metrics()
        
        # Should cap at 40% even though 80% * 0.6 = 48%
        assert metrics['estimated_ai_speedup_percent'] == 40.0

    def test_action_length_limit_enforcement(self):
        """Test that action length is limited to 50 characters"""
        very_long_action = "This is an extremely long action description that exceeds the fifty character limit significantly"
        
        result = self.optimizer._simplify_action(very_long_action)
        
        assert len(result) <= 50
        if len(result) == 50:
            assert result.endswith("...")

    def test_warning_length_limit_enforcement(self):
        """Test that warning length is limited to 50 characters"""
        very_long_warning = "This is a critical error that has an extremely long description exceeding limits"
        
        result = self.optimizer._simplify_warning(very_long_warning)
        
        assert len(result) <= 50
        if len(result) == 50:
            assert result.endswith("...")