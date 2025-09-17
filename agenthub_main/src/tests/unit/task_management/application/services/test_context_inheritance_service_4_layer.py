"""
Test Context Inheritance Service for 4-Layer Hierarchy

Tests the new 4-layer hierarchy system: Global -> Project -> Branch -> Task
with proper inheritance and validation.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastmcp.task_management.application.services.context_inheritance_service import ContextInheritanceService


class TestContextInheritanceService4Layer:
    """Test the 4-layer hierarchical context inheritance system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.inheritance_service = ContextInheritanceService()
        
        # Sample global context
        self.global_context = {
            "autonomous_rules": {
                "agent_switching": True,
                "context_resolution": True
            },
            "security_policies": {
                "mfa_required": True,
                "audit_logging": True
            },
            "coding_standards": {
                "python_style": "PEP8",
                "test_coverage": 80
            },
            "delegation_rules": {
                "auto_delegate": {
                    "patterns": True,
                    "best_practices": True
                },
                "thresholds": {
                    "complexity": 5,
                    "impact": 3
                }
            },
            "metadata": {"version": 1}
        }
        
        # Sample project context
        self.project_context = {
            "team_preferences": {
                "code_review": "required",
                "testing_framework": "pytest"
            },
            "technology_stack": {
                "language": "python",
                "framework": "fastapi",
                "database": "sqlite"
            },
            "project_workflow": {
                "git_flow": True,
                "automated_testing": True
            },
            "local_standards": {
                "max_line_length": 120
            },
            "global_overrides": {
                "coding_standards.test_coverage": 90
            },
            "delegation_rules": {
                "auto_delegate": {
                    "code_patterns": True
                }
            },
            "metadata": {"version": 2}
        }
        
        # Sample branch context
        self.branch_context = {
            "branch_workflow": {
                "feature_flags": True,
                "continuous_integration": True
            },
            "branch_standards": {
                "commit_message_format": "conventional",
                "branch_protection": True
            },
            "agent_assignments": {
                "primary_agent": "coding-agent",
                "reviewer_agent": "code-reviewer-agent"
            },
            "local_overrides": {
                "security_policies.mfa_required": False  # Development branch
            },
            "delegation_rules": {
                "thresholds": {
                    "complexity": 3  # Lower threshold for feature branch
                }
            },
            "metadata": {"version": 1}
        }
        
        # Sample task context
        self.task_context = {
            "task_data": {
                "implementation_approach": "TDD",
                "estimated_complexity": 4
            },
            "local_overrides": {
                "coding_standards.max_line_length": 100  # Specific to this task
            },
            "implementation_notes": {
                "special_requirements": "Performance critical",
                "dependencies": ["authentication_service"]
            },
            "delegation_triggers": {
                "auto_delegate_patterns": True
            },
            "force_local_only": False,
            "metadata": {"version": 1}
        }

    def test_inherit_project_from_global(self):
        """Test project inheritance from global context"""
        result = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        
        # Check that global context is inherited
        assert result["autonomous_rules"]["agent_switching"] is True
        assert result["security_policies"]["mfa_required"] is True
        assert result["coding_standards"]["python_style"] == "PEP8"
        
        # Check that project-specific configs are added
        assert result["team_preferences"]["code_review"] == "required"
        assert result["technology_stack"]["language"] == "python"
        assert result["project_workflow"]["git_flow"] is True
        
        # Check that global overrides are applied
        assert result["coding_standards"]["test_coverage"] == 90  # Overridden from 80
        
        # Check inheritance metadata
        assert result["inheritance_metadata"]["inherited_from"] == "global"
        assert result["inheritance_metadata"]["global_context_version"] == 1
        assert result["inheritance_metadata"]["project_overrides_applied"] == 1

    def test_inherit_branch_from_project(self):
        """Test branch inheritance from project context (which includes global)"""
        # First inherit project from global
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        
        # Then inherit branch from project
        result = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        
        # Check that both global and project contexts are inherited
        assert result["autonomous_rules"]["agent_switching"] is True  # From global
        assert result["team_preferences"]["code_review"] == "required"  # From project
        assert result["coding_standards"]["test_coverage"] == 90  # From project override
        
        # Check that branch-specific configs are added
        assert result["branch_workflow"]["feature_flags"] is True
        assert result["branch_standards"]["commit_message_format"] == "conventional"
        assert result["agent_assignments"]["primary_agent"] == "coding-agent"
        
        # Check that branch overrides are applied
        assert result["security_policies"]["mfa_required"] is False  # Branch override
        
        # Check inheritance metadata
        assert result["inheritance_metadata"]["inherited_from"] == "project"
        assert result["inheritance_metadata"]["inheritance_chain"] == ["global", "project", "branch"]
        assert result["inheritance_metadata"]["branch_overrides_applied"] == 1

    def test_inherit_task_from_branch(self):
        """Test task inheritance from branch context (which includes global + project)"""
        # First build the full inheritance chain
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        
        # Then inherit task from branch
        result = self.inheritance_service.inherit_task_from_branch(
            branch_inherited, self.task_context
        )
        
        # Check that global, project, and branch contexts are inherited
        assert result["autonomous_rules"]["agent_switching"] is True  # From global
        assert result["team_preferences"]["code_review"] == "required"  # From project
        assert result["branch_workflow"]["feature_flags"] is True  # From branch
        assert result["security_policies"]["mfa_required"] is False  # From branch override
        
        # Check that task-specific data is added
        assert result["task_data"]["implementation_approach"] == "TDD"
        assert result["task_data"]["estimated_complexity"] == 4
        assert result["implementation_notes"]["special_requirements"] == "Performance critical"
        assert result["delegation_triggers"]["auto_delegate_patterns"] is True
        
        # Check that task overrides are applied
        assert result["coding_standards"]["max_line_length"] == 100  # Task override
        
        # Check inheritance metadata
        assert result["inheritance_metadata"]["inherited_from"] == "branch"
        assert result["inheritance_metadata"]["inheritance_chain"] == ["global", "project", "branch", "task"]
        assert result["inheritance_metadata"]["local_overrides_applied"] == 1

    def test_full_inheritance_chain(self):
        """Test the complete 4-layer inheritance chain"""
        # Build the complete inheritance chain
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        task_inherited = self.inheritance_service.inherit_task_from_branch(
            branch_inherited, self.task_context
        )
        
        # Verify the final result contains data from all levels
        final_result = task_inherited
        
        # Global data
        assert final_result["autonomous_rules"]["agent_switching"] is True
        assert final_result["security_policies"]["audit_logging"] is True
        assert final_result["coding_standards"]["python_style"] == "PEP8"
        
        # Project data
        assert final_result["team_preferences"]["code_review"] == "required"
        assert final_result["technology_stack"]["language"] == "python"
        assert final_result["project_workflow"]["git_flow"] is True
        
        # Branch data
        assert final_result["branch_workflow"]["feature_flags"] is True
        assert final_result["agent_assignments"]["primary_agent"] == "coding-agent"
        
        # Task data
        assert final_result["task_data"]["implementation_approach"] == "TDD"
        assert final_result["implementation_notes"]["special_requirements"] == "Performance critical"
        
        # Verify override precedence (most specific wins)
        assert final_result["coding_standards"]["test_coverage"] == 90  # Project override
        assert final_result["security_policies"]["mfa_required"] is False  # Branch override
        assert final_result["coding_standards"]["max_line_length"] == 100  # Task override
        
        # Verify delegation rules are properly merged
        assert final_result["delegation_rules"]["auto_delegate"]["patterns"] is True  # Global
        assert final_result["delegation_rules"]["auto_delegate"]["code_patterns"] is True  # Project
        assert final_result["delegation_rules"]["thresholds"]["complexity"] == 3  # Branch override

    def test_validate_inheritance_chain_task(self):
        """Test validation of task inheritance chain"""
        # Build a complete task context
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        task_inherited = self.inheritance_service.inherit_task_from_branch(
            branch_inherited, self.task_context
        )
        
        # Validate the inheritance chain
        validation_result = self.inheritance_service.validate_inheritance_chain(
            "task", "task-123", task_inherited
        )
        
        assert validation_result["valid"] is True
        assert validation_result["metadata"]["context_level"] == "task"
        assert validation_result["metadata"]["context_id"] == "task-123"
        assert len(validation_result["issues"]) == 0

    def test_validate_inheritance_chain_branch(self):
        """Test validation of branch inheritance chain"""
        # Build a complete branch context
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        
        # Validate the inheritance chain
        validation_result = self.inheritance_service.validate_inheritance_chain(
            "branch", "branch-456", branch_inherited
        )
        
        assert validation_result["valid"] is True
        assert validation_result["metadata"]["context_level"] == "branch"
        assert validation_result["metadata"]["context_id"] == "branch-456"
        assert len(validation_result["issues"]) == 0

    def test_inheritance_with_missing_metadata(self):
        """Test validation when inheritance metadata is missing"""
        incomplete_context = {
            "some_data": "value"
            # Missing inheritance_metadata
        }
        
        validation_result = self.inheritance_service.validate_inheritance_chain(
            "task", "task-123", incomplete_context
        )
        
        assert validation_result["valid"] is False
        assert "Missing inheritance metadata" in validation_result["issues"]

    def test_inheritance_with_incorrect_chain(self):
        """Test validation when inheritance chain is incorrect"""
        incorrect_context = {
            "inheritance_metadata": {
                "inherited_from": "project",
                "inheritance_chain": ["global", "project", "task"]  # Missing branch
            }
        }
        
        validation_result = self.inheritance_service.validate_inheritance_chain(
            "task", "task-123", incorrect_context
        )
        
        assert validation_result["valid"] is True  # This is a warning, not an error
        assert len(validation_result["warnings"]) > 0
        assert "Unexpected inheritance chain" in validation_result["warnings"][0]

    def test_complex_override_scenarios(self):
        """Test complex override scenarios across all levels"""
        # Create contexts with overlapping override paths
        global_ctx = {
            "settings": {
                "timeout": 30,
                "retries": 3,
                "debug": False
            }
        }
        
        project_ctx = {
            "global_overrides": {
                "settings.timeout": 60,
                "settings.debug": True
            }
        }
        
        branch_ctx = {
            "local_overrides": {
                "settings.retries": 5
            }
        }
        
        task_ctx = {
            "local_overrides": {
                "settings.timeout": 90,
                "settings.debug": False
            }
        }
        
        # Build inheritance chain
        project_inherited = self.inheritance_service.inherit_project_from_global(
            global_ctx, project_ctx
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, branch_ctx
        )
        task_inherited = self.inheritance_service.inherit_task_from_branch(
            branch_inherited, task_ctx
        )
        
        # Verify final values (most specific level wins)
        final_settings = task_inherited["settings"]
        assert final_settings["timeout"] == 90  # Task override
        assert final_settings["retries"] == 5   # Branch override
        assert final_settings["debug"] is False  # Task override

    def test_delegation_rules_merging(self):
        """Test that delegation rules are properly merged across hierarchy"""
        # Build inheritance chain
        project_inherited = self.inheritance_service.inherit_project_from_global(
            self.global_context, self.project_context
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, self.branch_context
        )
        
        # Check that delegation rules from all levels are merged
        delegation_rules = branch_inherited["delegation_rules"]
        
        # Global rules
        assert delegation_rules["auto_delegate"]["patterns"] is True
        assert delegation_rules["auto_delegate"]["best_practices"] is True
        
        # Project rules
        assert delegation_rules["auto_delegate"]["code_patterns"] is True
        
        # Branch rules (threshold override)
        assert delegation_rules["thresholds"]["complexity"] == 3
        assert delegation_rules["thresholds"]["impact"] == 3  # Still from global

    def test_error_handling_in_inheritance(self):
        """Test error handling in inheritance methods"""
        # Test with malformed context
        malformed_context = None
        
        with pytest.raises(Exception):
            self.inheritance_service.inherit_project_from_global(
                malformed_context, self.project_context
            )

    def test_empty_contexts(self):
        """Test inheritance with empty contexts"""
        empty_global = {}
        empty_project = {}
        empty_branch = {}
        empty_task = {}
        
        # Should work without errors
        project_inherited = self.inheritance_service.inherit_project_from_global(
            empty_global, empty_project
        )
        branch_inherited = self.inheritance_service.inherit_branch_from_project(
            project_inherited, empty_branch
        )
        task_inherited = self.inheritance_service.inherit_task_from_branch(
            branch_inherited, empty_task
        )
        
        # Should have inheritance metadata
        assert "inheritance_metadata" in task_inherited
        assert task_inherited["inheritance_metadata"]["inheritance_chain"] == ["global", "project", "branch", "task"]

    def test_list_merging_strategies(self):
        """Test various list merging strategies"""
        base_context = {
            "assignees": ["user1", "user2"],
            "labels": ["frontend", "bug"],
            "requirements": ["req1", "req2"]
        }
        
        override_context = {
            "assignees": ["user3", "user1"],  # Should deduplicate
            "labels": ["backend"],  # Should combine
            "requirements": ["req3"]  # Should append
        }
        
        result = self.inheritance_service._deep_merge(base_context, override_context)
        
        # Check assignees deduplication
        assert set(result["assignees"]) == {"user1", "user2", "user3"}
        
        # Check labels combination
        assert set(result["labels"]) == {"frontend", "bug", "backend"}
        
        # Check requirements append
        assert result["requirements"] == ["req1", "req2", "req3"]