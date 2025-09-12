"""Comprehensive Tests for HintOptimizer

Tests the advanced hint optimization functionality that transforms
verbose nested workflow guidance into flat, AI-optimized hints.
"""

import pytest
from unittest.mock import Mock, patch
import json
import time

from fastmcp.task_management.application.services.hint_optimizer import (
    HintOptimizer, ActionType
)


class TestHintOptimizer:
    """Test suite for HintOptimizer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = HintOptimizer()
        
        # Sample verbose workflow guidance (typical input)
        self.verbose_guidance = {
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": [
                        "You should create a new task for implementing the authentication feature",
                        "Please consider updating the status to in_progress once you start working",
                        "It would be good to add a description with more details about the implementation"
                    ],
                    "required_actions": [
                        "You must add assignees to this task before proceeding",
                        "Please make sure to validate all required fields are present"
                    ],
                    "optional_actions": [
                        "Consider adding labels for better organization",
                        "You might want to set a priority level"
                    ]
                },
                "validation": {
                    "errors": [
                        {"field": "assignees", "message": "This field is required"},
                        {"field": "description", "message": "Description cannot be empty"}
                    ],
                    "warnings": [
                        "Task has no estimated effort specified",
                        "No dependencies defined - this might cause blocking issues"
                    ]
                },
                "autonomous_guidance": {
                    "recommendations": [
                        "Based on the task type, I recommend assigning this to coding-agent",
                        "The complexity suggests this should be high priority"
                    ],
                    "confidence": 0.85,
                    "decision_points": [
                        "Should this be broken into subtasks?",
                        "Are there dependencies we haven't identified?"
                    ]
                },
                "dependencies": {
                    "blocked_by": [
                        {"id": "task-123", "title": "Setup authentication database"}
                    ]
                }
            }
        }
        
        # Expected optimized output structure
        self.expected_hints = {
            "hints": {
                "next": "create_task",
                "required": ["add_assignees", "validate_fields"],
                "tips": ["add_labels", "set_priority"],
                "warnings": ["resolve_1_dependencies"],
                "confidence": 0.85
            }
        }
    
    def test_optimize_workflow_hints_basic(self):
        """Test basic workflow hints optimization"""
        result = self.optimizer.optimize_workflow_hints(self.verbose_guidance)
        
        assert "hints" in result
        hints = result["hints"]
        
        # Should have all main sections
        assert "next" in hints
        assert "required" in hints
        assert "tips" in hints
        assert "confidence" in hints
        
        # Next action should be simplified
        assert isinstance(hints["next"], str)
        assert len(hints["next"]) <= 50  # Per requirement
        
        # Required actions should be limited and simplified
        assert isinstance(hints["required"], list)
        assert len(hints["required"]) <= 3  # Max 3 required
        
        # Tips should be limited and simplified
        assert isinstance(hints["tips"], list)
        assert len(hints["tips"]) <= 2  # Max 2 tips
        
        # Confidence should be preserved
        assert hints["confidence"] == 0.85
    
    def test_payload_size_reduction(self):
        """Test that payload size is reduced by at least 70%"""
        original_size = len(json.dumps(self.verbose_guidance))
        result = self.optimizer.optimize_workflow_hints(self.verbose_guidance)
        optimized_size = len(json.dumps(result))
        
        reduction_percent = ((original_size - optimized_size) / original_size) * 100
        
        # Should achieve at least 70% reduction
        assert reduction_percent >= 70.0, f"Only achieved {reduction_percent:.1f}% reduction"
        
        # Check metrics reflect the reduction
        metrics = self.optimizer.get_performance_metrics()
        assert metrics["average_reduction_percent"] >= 70.0
    
    def test_action_simplification(self):
        """Test action text simplification"""
        verbose_actions = [
            "You should create a new task for implementing the feature",
            "Please make sure to update the status field",
            "It would be good to add some validation",
            "Consider removing the old configuration",
            "Go ahead and verify the implementation works"
        ]
        
        for action in verbose_actions:
            simplified = self.optimizer._simplify_action(action)
            
            # Should be concise
            assert len(simplified) <= 50
            
            # Should remove redundant phrases
            assert not any(phrase in simplified.lower() for phrase in 
                         ["you should", "please", "it would be good", "consider", "go ahead"])
            
            # Should contain action verb
            action_verbs = ["create", "update", "add", "remove", "verify"]
            assert any(verb in simplified.lower() for verb in action_verbs)
    
    def test_next_action_extraction(self):
        """Test extraction of the most important next action"""
        # Test autonomous guidance priority
        guidance_with_autonomous = {
            "autonomous_guidance": {
                "recommendations": ["Create the authentication module"]
            },
            "next_steps": {
                "recommendations": ["Update the documentation"]
            }
        }
        
        next_action = self.optimizer._extract_next_action(guidance_with_autonomous)
        assert "create" in next_action.lower()
        
        # Test required actions priority over recommendations
        guidance_with_required = {
            "next_steps": {
                "required_actions": ["Fix the validation error"],
                "recommendations": ["Add some comments"]
            }
        }
        
        next_action = self.optimizer._extract_next_action(guidance_with_required)
        assert "fix" in next_action.lower()
    
    def test_required_actions_extraction(self):
        """Test extraction of required actions"""
        guidance = {
            "next_steps": {
                "required_actions": [
                    "Add assignees to the task",
                    "Validate all required fields",
                    "Set the task priority",
                    "Additional action that should be truncated"
                ]
            },
            "validation": {
                "errors": [
                    {"field": "description", "message": "Required field"}
                ]
            }
        }
        
        required = self.optimizer._extract_required_actions(guidance, max_actions=3)
        
        # Should limit to max_actions
        assert len(required) <= 3
        
        # Should include validation fixes
        assert any("fix" in action.lower() for action in required)
        
        # All actions should be simplified
        for action in required:
            assert len(action) <= 50
            assert isinstance(action, str)
    
    def test_tips_extraction(self):
        """Test extraction of optional tips"""
        guidance = {
            "next_steps": {
                "optional_actions": [
                    "Consider adding labels for organization",
                    "You might want to set an estimated effort"
                ],
                "recommendations": [
                    "Main recommendation",  # This goes to next_action
                    "Secondary recommendation",
                    "Third recommendation"
                ]
            }
        }
        
        tips = self.optimizer._extract_tips(guidance, max_tips=2)
        
        # Should limit to max_tips
        assert len(tips) <= 2
        
        # Should be simplified
        for tip in tips:
            assert len(tip) <= 50
            assert isinstance(tip, str)
    
    def test_warnings_extraction(self):
        """Test extraction of critical warnings only"""
        guidance = {
            "validation": {
                "warnings": [
                    "Critical error in validation process",  # Critical
                    "Missing optional field suggestion",     # Not critical
                    "Unable to process required field",      # Critical
                    "Consider adding more details"           # Not critical
                ]
            }
        }
        
        warnings = self.optimizer._extract_warnings(guidance)
        
        # Should only include critical warnings
        assert len(warnings) <= 2  # Max 2 critical warnings
        
        # Should contain critical keywords
        for warning in warnings:
            assert any(keyword in warning.lower() 
                      for keyword in ["error", "unable", "critical", "fail", "block"])
    
    def test_confidence_extraction(self):
        """Test confidence score extraction"""
        # Test autonomous guidance confidence
        guidance_with_autonomous = {
            "autonomous_guidance": {"confidence": 0.92}
        }
        confidence = self.optimizer._extract_confidence(guidance_with_autonomous)
        assert confidence == 0.92
        
        # Test top-level confidence
        guidance_with_top_level = {
            "confidence": 0.78
        }
        confidence = self.optimizer._extract_confidence(guidance_with_top_level)
        assert confidence == 0.78
        
        # Test no confidence
        guidance_without = {}
        confidence = self.optimizer._extract_confidence(guidance_without)
        assert confidence is None
    
    def test_entity_extraction(self):
        """Test extraction of entities (IDs, names) from text"""
        text_with_entities = (
            "You should update task_id: 550e8400-e29b-41d4-a716-446655440000 "
            "and assign it to @coding-agent with label #urgent"
        )
        
        entities = self.optimizer._extract_entities(text_with_entities)
        
        # Should extract UUID, agent name, and label
        assert len(entities) >= 2
        assert any("550e8400" in entity for entity in entities)  # UUID part
        assert any("coding-agent" in entity for entity in entities)  # Agent name
    
    def test_critical_warning_detection(self):
        """Test detection of critical warnings"""
        critical_warnings = [
            "Critical error in validation",
            "Task is blocked by missing dependency",
            "Required field is missing",
            "Cannot proceed without validation",
            "Urgent issue needs immediate attention"
        ]
        
        non_critical_warnings = [
            "Consider adding more details",
            "Optional field could be improved",
            "Nice to have feature suggestion",
            "Future enhancement possibility"
        ]
        
        for warning in critical_warnings:
            assert self.optimizer._is_critical_warning(warning), f"Should be critical: {warning}"
        
        for warning in non_critical_warnings:
            assert not self.optimizer._is_critical_warning(warning), f"Should not be critical: {warning}"
    
    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        # Process multiple hints to test metrics
        for i in range(5):
            test_guidance = {
                "next_steps": {
                    "recommendations": [f"Test recommendation {i}"]
                },
                "confidence": 0.8
            }
            self.optimizer.optimize_workflow_hints(test_guidance)
        
        metrics = self.optimizer.get_performance_metrics()
        
        # Should track all processed hints
        assert metrics["hints_processed"] == 5
        
        # Should have positive reduction
        assert metrics["average_reduction_percent"] > 0
        
        # Should have processing time
        assert metrics["average_processing_time_ms"] > 0
        
        # Should have bytes saved
        assert metrics["total_bytes_saved"] > 0
        
        # Should estimate AI speedup
        assert 0 <= metrics["estimated_ai_speedup_percent"] <= 40
    
    def test_empty_guidance_handling(self):
        """Test handling of empty or invalid guidance"""
        # Empty dict
        result = self.optimizer.optimize_workflow_hints({})
        assert result == {"hints": {}}
        
        # None input
        result = self.optimizer.optimize_workflow_hints(None)
        assert result == {"hints": {}}
        
        # Invalid input type
        result = self.optimizer.optimize_workflow_hints("invalid")
        assert result == {"hints": {}}
    
    def test_max_limits_respected(self):
        """Test that max limits for required actions and tips are respected"""
        # Create guidance with many actions
        guidance = {
            "next_steps": {
                "required_actions": [f"Required action {i}" for i in range(10)],
                "optional_actions": [f"Optional action {i}" for i in range(10)]
            }
        }
        
        result = self.optimizer.optimize_workflow_hints(guidance, max_required=2, max_tips=1)
        hints = result["hints"]
        
        # Should respect max limits
        assert len(hints.get("required", [])) <= 2
        assert len(hints.get("tips", [])) <= 1
    
    def test_legacy_compatibility_response(self):
        """Test legacy compatibility response structure"""
        hints_result = self.optimizer.optimize_workflow_hints(self.verbose_guidance)
        
        legacy_response = self.optimizer.create_legacy_compatible_response(
            hints_result, self.verbose_guidance
        )
        
        # Should have new hints structure
        assert "hints" in legacy_response
        
        # Should have legacy workflow_guidance structure
        assert "workflow_guidance" in legacy_response
        legacy_wg = legacy_response["workflow_guidance"]
        
        assert "next_steps" in legacy_wg
        assert "confidence" in legacy_wg
        assert "recommendations" in legacy_wg["next_steps"]
        assert "required_actions" in legacy_wg["next_steps"]
    
    def test_processing_speed_performance(self):
        """Test that optimization is fast enough for 40% AI speedup"""
        # Test with large guidance structure
        large_guidance = {
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": [f"Very long recommendation text that goes on and on with lots of verbose language and redundant phrases that should be optimized recommendation {i}" for i in range(20)],
                    "required_actions": [f"Another verbose required action with lots of unnecessary text that needs simplification action {i}" for i in range(10)]
                },
                "validation": {
                    "errors": [{"field": f"field_{i}", "message": f"Long error message with verbose details {i}"} for i in range(15)]
                },
                "autonomous_guidance": {
                    "recommendations": [f"Autonomous recommendation with detailed explanation and verbose phrasing {i}" for i in range(10)],
                    "confidence": 0.75
                }
            }
        }
        
        start_time = time.perf_counter()
        result = self.optimizer.optimize_workflow_hints(large_guidance)
        processing_time = (time.perf_counter() - start_time) * 1000  # ms
        
        # Should process quickly (under 50ms for large input)
        assert processing_time < 50, f"Processing took {processing_time:.2f}ms, too slow"
        
        # Should still achieve good reduction
        original_size = len(json.dumps(large_guidance))
        optimized_size = len(json.dumps(result))
        reduction = ((original_size - optimized_size) / original_size) * 100
        
        assert reduction >= 60, f"Large guidance only achieved {reduction:.1f}% reduction"
    
    def test_metrics_reset(self):
        """Test metrics reset functionality"""
        # Process some hints
        self.optimizer.optimize_workflow_hints(self.verbose_guidance)
        
        metrics_before = self.optimizer.get_performance_metrics()
        assert metrics_before["hints_processed"] > 0
        
        # Reset metrics
        self.optimizer.reset_metrics()
        
        metrics_after = self.optimizer.get_performance_metrics()
        assert metrics_after["hints_processed"] == 0
        assert metrics_after["total_bytes_saved"] == 0
        assert metrics_after["average_reduction_percent"] == 0.0


class TestHintOptimizerIntegration:
    """Integration tests for HintOptimizer with real-world scenarios"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.optimizer = HintOptimizer()
    
    def test_task_management_scenario(self):
        """Test optimization with typical task management guidance"""
        task_guidance = {
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": [
                        "You should create subtasks to break down this complex feature implementation",
                        "Please consider assigning this to the coding-agent based on the technical requirements",
                        "It would be helpful to add estimated effort to better plan the work"
                    ],
                    "required_actions": [
                        "You must add a detailed description before this task can be started",
                        "Please make sure to set the priority level based on business impact"
                    ]
                },
                "autonomous_guidance": {
                    "confidence": 0.88,
                    "recommendations": [
                        "Based on similar tasks, this should be marked as high priority",
                        "Consider creating dependencies with the database setup task"
                    ]
                }
            }
        }
        
        result = self.optimizer.optimize_workflow_hints(task_guidance)
        hints = result["hints"]
        
        # Should extract meaningful actions
        assert "next" in hints
        assert any(word in hints["next"].lower() for word in ["create", "assign", "add"])
        
        # Should have required actions
        assert "required" in hints
        assert len(hints["required"]) <= 3
        
        # Should preserve confidence
        assert hints["confidence"] == 0.88
    
    def test_error_handling_scenario(self):
        """Test optimization with error-focused guidance"""
        error_guidance = {
            "validation": {
                "errors": [
                    {"field": "assignees", "message": "This field is required and cannot be empty"},
                    {"field": "git_branch_id", "message": "Invalid UUID format provided"}
                ],
                "warnings": [
                    "Task has no description - this will make it difficult to understand",
                    "Critical dependency missing - task may be blocked",
                    "No estimated effort specified"
                ]
            },
            "workflow_guidance": {
                "next_steps": {
                    "required_actions": [
                        "Fix the validation errors before proceeding with task creation",
                        "Add the missing assignees field with at least one agent",
                        "Correct the git_branch_id format to valid UUID"
                    ]
                }
            }
        }
        
        result = self.optimizer.optimize_workflow_hints(error_guidance)
        hints = result["hints"]
        
        # Should prioritize fixing errors
        assert "required" in hints
        assert any("fix" in action.lower() for action in hints["required"])
        
        # Should include critical warnings only
        if "warnings" in hints:
            assert len(hints["warnings"]) <= 2
            # Should focus on critical issues
            critical_found = any(
                any(word in warning.lower() for word in ["critical", "missing", "error", "blocked"])
                for warning in hints["warnings"]
            )
            assert critical_found
    
    def test_dependency_scenario(self):
        """Test optimization with dependency-focused guidance"""
        dependency_guidance = {
            "dependencies": {
                "blocked_by": [
                    {"id": "task-001", "title": "Setup authentication database"},
                    {"id": "task-002", "title": "Configure API endpoints"}
                ],
                "required": ["database-setup", "api-config"]
            },
            "workflow_guidance": {
                "next_steps": {
                    "recommendations": [
                        "Wait for blocking dependencies to be completed before starting this task",
                        "Consider coordinating with the database team for task-001",
                        "Review the API configuration requirements for task-002"
                    ]
                }
            }
        }
        
        result = self.optimizer.optimize_workflow_hints(dependency_guidance)
        hints = result["hints"]
        
        # Should identify dependency resolution as required
        if "required" in hints:
            dependency_action_found = any(
                "resolve" in action.lower() or "depend" in action.lower()
                for action in hints["required"]
            )
            assert dependency_action_found
    
    @pytest.mark.performance
    def test_large_scale_optimization(self):
        """Test optimization with very large guidance structures"""
        # Create a large, complex guidance structure
        large_guidance = {}
        
        # Add many nested levels
        large_guidance["workflow_guidance"] = {
            "next_steps": {
                "recommendations": [
                    f"Very detailed recommendation number {i} with lots of verbose text and redundant phrasing that should be optimized for AI processing speed and efficiency"
                    for i in range(50)
                ],
                "required_actions": [
                    f"Required action {i} with extensive description and verbose language that needs to be simplified and optimized"
                    for i in range(25)
                ],
                "optional_actions": [
                    f"Optional action {i} with detailed explanation and wordy descriptions"
                    for i in range(30)
                ]
            },
            "validation": {
                "errors": [
                    {
                        "field": f"field_{i}",
                        "message": f"Detailed error message {i} with comprehensive explanation and verbose details"
                    }
                    for i in range(20)
                ],
                "warnings": [
                    f"Warning message {i} with extensive details and verbose explanations"
                    for i in range(15)
                ]
            },
            "autonomous_guidance": {
                "recommendations": [
                    f"AI recommendation {i} with detailed analysis and comprehensive suggestions"
                    for i in range(30)
                ],
                "confidence": 0.82,
                "decision_points": [
                    f"Decision point {i} with detailed considerations and multiple options"
                    for i in range(20)
                ]
            }
        }
        
        # Test optimization
        start_time = time.perf_counter()
        result = self.optimizer.optimize_workflow_hints(large_guidance)
        processing_time = (time.perf_counter() - start_time) * 1000
        
        # Should process in reasonable time (under 100ms)
        assert processing_time < 100, f"Large guidance processing took {processing_time:.2f}ms"
        
        # Should achieve significant reduction
        original_size = len(json.dumps(large_guidance))
        optimized_size = len(json.dumps(result))
        reduction = ((original_size - optimized_size) / original_size) * 100
        
        assert reduction >= 70, f"Large guidance achieved {reduction:.1f}% reduction"
        
        # Should maintain structure limits
        hints = result["hints"]
        if "required" in hints:
            assert len(hints["required"]) <= 3
        if "tips" in hints:
            assert len(hints["tips"]) <= 2
        if "warnings" in hints:
            assert len(hints["warnings"]) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])