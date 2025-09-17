"""Unit tests for RuleCompositionService domain service"""

import pytest
import json
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.rule_composition_service import (
    RuleCompositionService,
    IRuleCompositionService
)
from fastmcp.task_management.domain.entities.rule_entity import RuleContent, RuleInheritance
from fastmcp.task_management.domain.value_objects.rule_value_objects import CompositionResult
from fastmcp.task_management.domain.enums.rule_enums import RuleFormat, ConflictResolution, InheritanceType


class MockRuleContent:
    """Mock RuleContent entity for testing"""
    
    def __init__(self, rule_path: str, rule_type: str = "workflow", sections: Dict[str, str] = None, 
                 variables: Dict[str, Any] = None, parsed_content: Dict[str, Any] = None, raw_content: str = ""):
        self.rule_path = rule_path
        self.rule_type = Mock()
        self.rule_type.value = rule_type
        self.sections = sections or {}
        self.variables = variables or {}
        self.parsed_content = parsed_content or {}
        self.raw_content = raw_content or f"Raw content for {rule_path}"
        
        # Mock metadata with priority
        self.metadata = Mock()
        self.metadata.priority = 100 if rule_type == "core" else 50


class TestRuleCompositionService:
    """Test suite for RuleCompositionService domain service"""

    def setup_method(self):
        """Setup test data before each test"""
        self.service = RuleCompositionService(ConflictResolution.MERGE)
        
        # Create mock rule contents
        self.core_rule = MockRuleContent(
            rule_path="core/base.mdc",
            rule_type="core",
            sections={
                "introduction": "Core introduction content",
                "rules": "Core business rules"
            },
            variables={
                "project_name": "TestProject",
                "version": "1.0"
            },
            parsed_content={
                "title": "Core Rules",
                "priority": "high"
            }
        )
        
        self.workflow_rule = MockRuleContent(
            rule_path="workflow/development.mdc",
            rule_type="workflow", 
            sections={
                "rules": "Workflow specific rules",
                "procedures": "Development procedures"
            },
            variables={
                "team_size": "5",
                "version": "1.1"  # Conflicts with core rule
            },
            parsed_content={
                "workflow_type": "agile"
            }
        )
        
        self.custom_rule = MockRuleContent(
            rule_path="custom/project.mdc",
            rule_type="custom",
            sections={
                "procedures": "Custom procedures override",
                "exceptions": "Special project exceptions"
            },
            variables={
                "custom_var": "custom_value"
            }
        )

    def test_compose_rules_empty_list(self):
        """Test composing empty rule list"""
        # Act
        result = self.service.compose_rules([])
        
        # Assert
        assert isinstance(result, CompositionResult)
        assert result.success is False
        assert result.composed_content == ""
        assert "No rules provided" in result.warnings

    def test_compose_rules_intelligent_strategy_success(self):
        """Test intelligent composition strategy with multiple rules"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule, self.custom_rule]
        
        # Act
        result = self.service.compose_rules(
            rules, 
            RuleFormat.MDC, 
            "intelligent"
        )
        
        # Assert
        assert result.success is True
        assert result.composed_content != ""
        assert len(result.source_rules) == 3
        assert len(result.conflicts_resolved) > 0  # Should have version conflict
        assert result.composition_metadata["strategy"] == "intelligent"
        assert result.composition_metadata["total_rules"] == 3

    def test_compose_rules_sequential_strategy(self):
        """Test sequential composition strategy"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule]
        
        # Act
        result = self.service.compose_rules(
            rules,
            RuleFormat.MD,
            "sequential"
        )
        
        # Assert
        assert result.success is True
        assert "# From core/base.mdc" in result.composed_content
        assert "# From workflow/development.mdc" in result.composed_content
        assert self.core_rule.raw_content in result.composed_content
        assert self.workflow_rule.raw_content in result.composed_content

    def test_compose_rules_priority_merge_strategy(self):
        """Test priority merge composition strategy"""
        # Arrange
        rules = [self.workflow_rule, self.core_rule]  # Core should be prioritized
        
        # Act
        result = self.service.compose_rules(
            rules,
            RuleFormat.MDC,
            "priority_merge"
        )
        
        # Assert
        assert result.success is True
        # Core rule should be used as base (higher priority)
        # Lower priority rules should only add missing sections
        assert len(result.conflicts_resolved) > 0

    def test_compose_rules_unknown_strategy_fallback(self):
        """Test fallback to intelligent strategy for unknown strategy"""
        # Arrange
        rules = [self.core_rule]
        
        # Act
        result = self.service.compose_rules(
            rules,
            RuleFormat.MDC,
            "unknown_strategy"
        )
        
        # Assert
        assert result.success is True
        assert result.composition_metadata["strategy"] == "unknown_strategy"
        # Should still work (fallback to intelligent)

    def test_compose_rules_exception_handling(self):
        """Test exception handling during composition"""
        # Arrange
        invalid_rule = Mock()
        invalid_rule.rule_path = "invalid/rule.mdc"
        invalid_rule.rule_type = None  # This should cause an error
        
        # Act
        result = self.service.compose_rules([invalid_rule])
        
        # Assert
        assert result.success is False
        assert "Composition failed" in result.warnings
        assert "error" in result.composition_metadata

    def test_resolve_conflicts(self):
        """Test conflict resolution between rules"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule]  # These have version conflict
        
        # Act
        resolution = self.service.resolve_conflicts(rules)
        
        # Assert
        assert "total_conflicts" in resolution
        assert "conflicts" in resolution
        assert "resolutions" in resolution
        assert resolution["strategy_used"] == ConflictResolution.MERGE.value
        
        # Should detect version variable conflict
        assert resolution["total_conflicts"] > 0

    def test_resolve_conflicts_no_conflicts(self):
        """Test conflict resolution when no conflicts exist"""
        # Arrange - Rules with no overlapping sections or variables
        rule1 = MockRuleContent(
            "rule1.mdc",
            sections={"section1": "content1"},
            variables={"var1": "value1"}
        )
        rule2 = MockRuleContent(
            "rule2.mdc", 
            sections={"section2": "content2"},
            variables={"var2": "value2"}
        )
        
        # Act
        resolution = self.service.resolve_conflicts([rule1, rule2])
        
        # Assert
        assert resolution["total_conflicts"] == 0
        assert len(resolution["conflicts"]) == 0

    def test_merge_section_content_simple_merge(self):
        """Test simple section content merging"""
        # Test case 1: Empty content
        result = self.service.merge_section_content("", "content2")
        assert result == "content2"
        
        result = self.service.merge_section_content("content1", "")
        assert result == "content1"
        
        # Test case 2: Identical content
        result = self.service.merge_section_content("same", "same")
        assert result == "same"
        
        # Test case 3: Different content merge
        result = self.service.merge_section_content("line1\nline2", "line3\nline2")
        assert "line1" in result
        assert "line2" in result  # Should appear once
        assert "line3" in result

    def test_merge_section_content_intelligent_merge(self):
        """Test intelligent section content merging"""
        # Arrange
        content1 = "Rule 1: First rule\nRule 2: Second rule"
        content2 = "Rule 2: Second rule\nRule 3: Third rule"
        
        # Act
        merged = self.service.merge_section_content(content1, content2)
        
        # Assert
        lines = merged.split('\n')
        assert "Rule 1: First rule" in lines
        assert "Rule 2: Second rule" in lines
        assert "Rule 3: Third rule" in lines
        # Rule 2 should only appear once (intelligent deduplication)

    def test_sort_rules_by_priority(self):
        """Test sorting rules by priority"""
        # Arrange
        rules = [self.workflow_rule, self.core_rule, self.custom_rule]
        
        # Act
        sorted_rules = self.service._sort_rules_by_priority(rules)
        
        # Assert
        # Core rules should come first (highest priority)
        assert sorted_rules[0].rule_type.value == "core"
        # Workflow rules should come second
        assert sorted_rules[1].rule_type.value == "workflow"
        # Custom rules should come last
        assert sorted_rules[2].rule_type.value == "custom"

    def test_intelligent_composition_with_conflicts(self):
        """Test intelligent composition handling conflicts"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule]
        
        # Act
        composed, conflicts, warnings = self.service._intelligent_composition(
            rules, 
            RuleFormat.MDC
        )
        
        # Assert
        assert composed != ""
        assert len(conflicts) > 0  # Should detect version variable conflict
        # Merged sections should contain content from both rules
        assert "Core introduction content" in composed or "introduction" in composed
        assert "procedures" in composed or "procedures" in composed.lower()

    def test_sequential_composition(self):
        """Test sequential composition implementation"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule]
        
        # Act
        composed, conflicts, warnings = self.service._sequential_composition(
            rules,
            RuleFormat.MD
        )
        
        # Assert
        assert composed != ""
        assert "# From core/base.mdc" in composed
        assert "# From workflow/development.mdc" in composed
        assert self.core_rule.raw_content in composed
        assert self.workflow_rule.raw_content in composed
        assert len(conflicts) == 0  # Sequential doesn't resolve conflicts

    def test_priority_merge_composition(self):
        """Test priority merge composition implementation"""
        # Arrange
        rules = [self.workflow_rule, self.core_rule]  # Core will be prioritized
        sorted_rules = self.service._sort_rules_by_priority(rules)
        
        # Act
        composed, conflicts, warnings = self.service._priority_merge_composition(
            sorted_rules,
            RuleFormat.MDC
        )
        
        # Assert
        assert composed != ""
        assert len(conflicts) > 0  # Should track added sections from lower priority
        # Should be based on highest priority rule (core)

    def test_detect_rule_conflicts(self):
        """Test detection of conflicts between rules"""
        # Act
        conflicts = self.service._detect_rule_conflicts(self.core_rule, self.workflow_rule)
        
        # Assert
        assert len(conflicts) > 0
        
        # Should detect version variable conflict
        version_conflict = next(
            (c for c in conflicts if c["name"] == "version"), 
            None
        )
        assert version_conflict is not None
        assert version_conflict["type"] == "variable"
        assert version_conflict["rule1_value"] == "1.0"
        assert version_conflict["rule2_value"] == "1.1"

    def test_detect_rule_conflicts_sections(self):
        """Test detection of section conflicts between rules"""
        # Arrange
        rule1 = MockRuleContent(
            "rule1.mdc",
            sections={"shared_section": "content from rule1"}
        )
        rule2 = MockRuleContent(
            "rule2.mdc",
            sections={"shared_section": "different content from rule2"}
        )
        
        # Act
        conflicts = self.service._detect_rule_conflicts(rule1, rule2)
        
        # Assert
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "section"
        assert conflicts[0]["name"] == "shared_section"

    def test_resolve_single_rule_conflict_merge_strategy(self):
        """Test resolving single rule conflict with merge strategy"""
        # Arrange
        section_conflict = {
            "type": "section",
            "name": "test_section",
            "rule1_path": "rule1.mdc",
            "rule2_path": "rule2.mdc",
            "rule1_content": "content1\nshared",
            "rule2_content": "content2\nshared"
        }
        
        # Act
        resolution = self.service._resolve_single_rule_conflict(section_conflict)
        
        # Assert
        assert resolution["strategy"] == ConflictResolution.MERGE.value
        assert "content1" in resolution["resolved_value"]
        assert "content2" in resolution["resolved_value"]
        assert "shared" in resolution["resolved_value"]

    def test_resolve_single_rule_conflict_variable_merge(self):
        """Test resolving variable conflict with merge strategy"""
        # Arrange
        variable_conflict = {
            "type": "variable",
            "name": "test_var",
            "rule1_value": "value1", 
            "rule2_value": "value2"
        }
        
        # Act
        resolution = self.service._resolve_single_rule_conflict(variable_conflict)
        
        # Assert
        assert resolution["strategy"] == ConflictResolution.MERGE.value
        assert resolution["resolved_value"] == "value2"  # Uses latest value
        assert "latest variable value" in resolution["resolution_reason"]

    def test_resolve_single_rule_conflict_override_strategy(self):
        """Test resolving conflict with override strategy"""
        # Arrange
        service_override = RuleCompositionService(ConflictResolution.OVERRIDE)
        conflict = {
            "type": "section",
            "rule2_content": "override content"
        }
        
        # Act
        resolution = service_override._resolve_single_rule_conflict(conflict)
        
        # Assert
        assert resolution["strategy"] == ConflictResolution.OVERRIDE.value
        assert resolution["resolved_value"] == "override content"

    def test_build_inheritance_chain(self):
        """Test building inheritance chain from rules"""
        # Arrange
        rules = [self.core_rule, self.workflow_rule, self.custom_rule]
        
        # Act
        chain = self.service._build_inheritance_chain(rules)
        
        # Assert
        assert len(chain) == 2  # N-1 inheritance relationships
        assert all(isinstance(inheritance, RuleInheritance) for inheritance in chain)
        
        # Check first inheritance relationship
        assert chain[0].parent_path == self.core_rule.rule_path
        assert chain[0].child_path == self.workflow_rule.rule_path
        assert chain[0].inheritance_type == InheritanceType.CONTENT

    def test_generate_composed_content_mdc_format(self):
        """Test generating composed content in MDC format"""
        # Arrange
        sections = {
            "introduction": "This is the introduction",
            "rules": "These are the rules"
        }
        variables = {
            "project": "TestProject",
            "version": "2.0"
        }
        metadata = {
            "title": "Test Rules",
            "author": "Test Author"
        }
        
        # Act
        content = self.service._generate_mdc_content(sections, variables, metadata)
        
        # Assert
        assert "---" in content  # Metadata header
        assert "title: Test Rules" in content
        assert "author: Test Author" in content
        assert "## Variables" in content
        assert "project: TestProject" in content
        assert "## introduction" in content
        assert "This is the introduction" in content
        assert "## rules" in content
        assert "These are the rules" in content

    def test_generate_composed_content_markdown_format(self):
        """Test generating composed content in Markdown format"""
        # Arrange
        sections = {"section1": "Content 1"}
        variables = {"var1": "value1"}
        metadata = {"title": "Test Title"}
        
        # Act
        content = self.service._generate_markdown_content(sections, variables, metadata)
        
        # Assert
        assert "# Test Title" in content
        assert "## Configuration" in content
        assert "**var1**: value1" in content
        assert "## section1" in content
        assert "Content 1" in content

    def test_generate_composed_content_json_format(self):
        """Test generating composed content in JSON format"""
        # Arrange
        sections = {"section1": "Content 1"}
        variables = {"var1": "value1"}
        metadata = {"title": "Test Title"}
        
        # Act
        content = self.service._generate_json_content(sections, variables, metadata)
        
        # Assert
        parsed = json.loads(content)
        assert parsed["metadata"]["title"] == "Test Title"
        assert parsed["variables"]["var1"] == "value1"
        assert parsed["sections"]["section1"] == "Content 1"

    @patch('time.time')
    def test_get_current_timestamp(self, mock_time):
        """Test getting current timestamp"""
        # Arrange
        mock_time.return_value = 1234567890.0
        
        # Act
        timestamp = self.service._get_current_timestamp()
        
        # Assert
        assert timestamp == 1234567890.0
        mock_time.assert_called_once()

    def test_service_implements_interface(self):
        """Test that service properly implements the interface"""
        # Assert
        assert isinstance(self.service, IRuleCompositionService)
        
        # Test interface methods are callable
        assert callable(self.service.compose_rules)
        assert callable(self.service.resolve_conflicts)
        assert callable(self.service.merge_section_content)


class TestRuleCompositionServiceIntegration:
    """Integration tests for RuleCompositionService with complex scenarios"""

    def setup_method(self):
        """Setup integration test environment"""
        self.service = RuleCompositionService(ConflictResolution.MERGE)

    def test_complete_composition_workflow(self):
        """Test complete composition workflow with realistic rules"""
        # Arrange: Create realistic rule hierarchy
        base_rule = MockRuleContent(
            rule_path="base/foundation.mdc",
            rule_type="core",
            sections={
                "project_overview": "This project implements task management",
                "core_principles": "DDD, Clean Architecture, SOLID principles",
                "architecture": "Layered architecture with domain focus"
            },
            variables={
                "project_name": "TaskManager",
                "version": "1.0.0",
                "language": "Python"
            },
            parsed_content={
                "title": "Foundation Rules",
                "priority": "critical"
            }
        )
        
        development_rule = MockRuleContent(
            rule_path="development/coding.mdc",
            rule_type="workflow",
            sections={
                "coding_standards": "Follow PEP 8, use type hints",
                "testing": "Minimum 80% coverage, unit + integration tests",
                "architecture": "Extended: Use repository pattern for data access"  # Conflicts with base
            },
            variables={
                "test_framework": "pytest",
                "version": "1.1.0"  # Version conflict
            }
        )
        
        project_rule = MockRuleContent(
            rule_path="project/specific.mdc",
            rule_type="custom",
            sections={
                "deployment": "Deploy to containerized environment",
                "monitoring": "Use structured logging and metrics"
            },
            variables={
                "environment": "docker",
                "log_level": "INFO"
            }
        )
        
        rules = [base_rule, development_rule, project_rule]
        
        # Act: Compose with intelligent strategy
        result = self.service.compose_rules(
            rules,
            RuleFormat.MDC,
            "intelligent"
        )
        
        # Assert: Verify complete workflow
        assert result.success is True
        assert len(result.source_rules) == 3
        assert len(result.conflicts_resolved) > 0  # Should resolve version and architecture conflicts
        
        # Verify content structure
        content = result.composed_content
        assert "project_overview" in content
        assert "coding_standards" in content
        assert "deployment" in content
        
        # Verify metadata
        metadata = result.composition_metadata
        assert metadata["strategy"] == "intelligent"
        assert metadata["total_rules"] == 3
        assert metadata["conflicts_resolved"] > 0

    def test_multi_level_inheritance_resolution(self):
        """Test multi-level rule inheritance resolution"""
        # Arrange: Create inheritance chain Global -> Team -> Project
        global_rule = MockRuleContent(
            "global/standards.mdc",
            rule_type="core",
            sections={"global_standards": "Global coding standards"},
            variables={"company": "TechCorp", "compliance": "SOX"}
        )
        
        team_rule = MockRuleContent(
            "team/backend.mdc",
            rule_type="workflow",
            sections={
                "team_standards": "Backend team specific standards",
                "global_standards": "Extended global standards with backend focus"  # Override
            },
            variables={"team": "Backend", "tech_stack": "Python"}
        )
        
        project_rule = MockRuleContent(
            "project/api.mdc",
            rule_type="custom",
            sections={
                "api_standards": "REST API specific standards",
                "team_standards": "API project team standards"  # Override
            },
            variables={"project": "UserAPI", "version": "2.0.0"}
        )
        
        rules = [global_rule, team_rule, project_rule]
        
        # Act
        result = self.service.compose_rules(rules, RuleFormat.MDC, "intelligent")
        
        # Assert
        assert result.success is True
        
        # Verify inheritance chain
        assert len(result.inheritance_chain) == 2
        assert result.inheritance_chain[0].parent_path == "global/standards.mdc"
        assert result.inheritance_chain[0].child_path == "team/backend.mdc"
        assert result.inheritance_chain[1].parent_path == "team/backend.mdc"
        assert result.inheritance_chain[1].child_path == "project/api.mdc"
        
        # Verify conflicts were resolved for overridden sections
        section_conflicts = [
            c for c in result.conflicts_resolved 
            if "Section" in c and ("global_standards" in c or "team_standards" in c)
        ]
        assert len(section_conflicts) >= 2

    def test_conflict_resolution_strategies_comparison(self):
        """Test different conflict resolution strategies produce different results"""
        # Arrange: Rules with conflicts
        rule1 = MockRuleContent(
            "rule1.mdc",
            sections={"shared": "Original content"},
            variables={"config": "default"}
        )
        rule2 = MockRuleContent(
            "rule2.mdc", 
            sections={"shared": "Modified content"},
            variables={"config": "updated"}
        )
        
        rules = [rule1, rule2]
        
        # Act: Test different strategies
        merge_service = RuleCompositionService(ConflictResolution.MERGE)
        override_service = RuleCompositionService(ConflictResolution.OVERRIDE)
        
        merge_result = merge_service.compose_rules(rules, RuleFormat.MDC, "intelligent")
        override_result = override_service.compose_rules(rules, RuleFormat.MDC, "intelligent")
        
        # Assert: Different strategies should produce different results
        assert merge_result.success is True
        assert override_result.success is True
        assert merge_result.composed_content != override_result.composed_content
        
        # Merge should contain both contents
        merge_content = merge_result.composed_content
        assert "Original content" in merge_content
        assert "Modified content" in merge_content
        
        # Override should prefer latest content
        override_content = override_result.composed_content
        assert "Modified content" in override_content

    def test_error_resilience_with_malformed_rules(self):
        """Test system resilience with malformed or incomplete rules"""
        # Arrange: Mix of valid and problematic rules
        valid_rule = MockRuleContent(
            "valid.mdc",
            sections={"valid_section": "Valid content"},
            variables={"valid_var": "valid_value"}
        )
        
        # Problematic rule with None values
        problematic_rule = Mock()
        problematic_rule.rule_path = "problematic.mdc"
        problematic_rule.rule_type = Mock()
        problematic_rule.rule_type.value = "custom"
        problematic_rule.sections = None  # This should cause issues
        problematic_rule.variables = {}
        problematic_rule.parsed_content = {}
        
        rules = [valid_rule, problematic_rule]
        
        # Act
        result = self.service.compose_rules(rules, RuleFormat.MDC, "intelligent")
        
        # Assert: Should handle errors gracefully
        assert result.success is False  # Should fail due to problematic rule
        assert "error" in result.composition_metadata
        assert len(result.warnings) > 0

    def test_performance_with_large_rule_sets(self):
        """Test performance characteristics with large rule sets"""
        # Arrange: Create many rules to test scalability
        rules = []
        for i in range(50):  # Create 50 rules
            rule = MockRuleContent(
                f"rule_{i:03d}.mdc",
                rule_type="custom" if i % 3 == 0 else "workflow",
                sections={f"section_{i}": f"Content for rule {i}"},
                variables={f"var_{i}": f"value_{i}"}
            )
            rules.append(rule)
        
        # Act
        result = self.service.compose_rules(rules, RuleFormat.MDC, "intelligent")
        
        # Assert: Should handle large sets successfully
        assert result.success is True
        assert len(result.source_rules) == 50
        assert result.composition_metadata["total_rules"] == 50
        assert result.composed_content != ""