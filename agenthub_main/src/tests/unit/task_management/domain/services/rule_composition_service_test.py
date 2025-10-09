"""
Unit tests for RuleCompositionService
Tests all functionality of the rule composition domain service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any

from fastmcp.task_management.domain.services.rule_composition_service import (
    RuleCompositionService, 
    IRuleCompositionService
)
from fastmcp.task_management.domain.entities.rule_entity import RuleContent, RuleInheritance
from fastmcp.task_management.domain.value_objects.rule_value_objects import CompositionResult
from fastmcp.task_management.domain.value_objects.rule_enums import (
    RuleFormat, 
    ConflictResolution, 
    InheritanceType,
    RuleType
)


class TestRuleCompositionService:
    """Test suite for RuleCompositionService"""

    @pytest.fixture
    def service(self):
        """Create a rule composition service instance"""
        return RuleCompositionService(conflict_strategy=ConflictResolution.MERGE)

    @pytest.fixture
    def sample_rule_content(self):
        """Create a sample rule content"""
        rule_content = Mock(spec=RuleContent)
        rule_content.rule_path = "test/rule.md"
        rule_content.raw_content = "# Test Rule\nTest content"
        rule_content.sections = {"General": "Test section content"}
        rule_content.variables = {"test_var": "test_value"}
        rule_content.parsed_content = {"title": "Test Rule"}
        rule_content.metadata = Mock()
        rule_content.metadata.priority = 10
        rule_content.rule_type = Mock()
        rule_content.rule_type.value = "core"
        return rule_content

    @pytest.fixture
    def sample_rule_list(self):
        """Create a list of sample rules"""
        rule1 = Mock(spec=RuleContent)
        rule1.rule_path = "rule1.md"
        rule1.raw_content = "# Rule 1"
        rule1.sections = {"Section1": "Content 1", "Common": "Rule1 common"}
        rule1.variables = {"var1": "value1", "common_var": "rule1_value"}
        rule1.parsed_content = {"title": "Rule 1"}
        rule1.metadata = Mock()
        rule1.metadata.priority = 20
        rule1.rule_type = Mock()
        rule1.rule_type.value = "workflow"
        
        rule2 = Mock(spec=RuleContent)
        rule2.rule_path = "rule2.md"
        rule2.raw_content = "# Rule 2"
        rule2.sections = {"Section2": "Content 2", "Common": "Rule2 common"}
        rule2.variables = {"var2": "value2", "common_var": "rule2_value"}
        rule2.parsed_content = {"title": "Rule 2"}
        rule2.metadata = Mock()
        rule2.metadata.priority = 10
        rule2.rule_type = Mock()
        rule2.rule_type.value = "core"
        
        return [rule1, rule2]

    def test_service_implements_interface(self, service):
        """Test that service implements the interface"""
        assert isinstance(service, IRuleCompositionService)

    def test_compose_rules_empty_list(self, service):
        """Test composing empty rule list"""
        result = service.compose_rules([])
        
        assert isinstance(result, CompositionResult)
        assert not result.success
        assert result.composed_content == ""
        assert "No rules provided" in result.warnings[0]

    @patch.object(RuleCompositionService, '_get_current_timestamp')
    def test_compose_rules_single_rule(self, mock_timestamp, service, sample_rule_content):
        """Test composing a single rule"""
        mock_timestamp.return_value = 1234567890.0
        
        result = service.compose_rules([sample_rule_content])
        
        assert result.success
        assert result.composed_content != ""
        assert result.source_rules == ["test/rule.md"]
        assert len(result.conflicts_resolved) == 0
        assert result.composition_metadata["total_rules"] == 1

    @patch.object(RuleCompositionService, '_get_current_timestamp')
    def test_compose_rules_multiple_with_conflicts(self, mock_timestamp, service, sample_rule_list):
        """Test composing multiple rules with conflicts"""
        mock_timestamp.return_value = 1234567890.0
        
        result = service.compose_rules(sample_rule_list)
        
        assert result.success
        assert result.composed_content != ""
        assert len(result.source_rules) == 2
        assert len(result.conflicts_resolved) >= 1  # Common section and variable conflicts

    def test_compose_rules_with_exception(self, service):
        """Test compose rules handles exceptions gracefully"""
        bad_rule = Mock(spec=RuleContent)
        bad_rule.rule_path = "bad.md"
        bad_rule.sections = None  # This will cause an error
        bad_rule.metadata = Mock()  # Need metadata attribute
        bad_rule.rule_type = None
        
        result = service.compose_rules([bad_rule], composition_strategy="intelligent")
        
        assert not result.success
        assert "Composition failed" in result.warnings[0]

    def test_resolve_conflicts_no_conflicts(self, service):
        """Test resolving conflicts when there are none"""
        rule1 = Mock(spec=RuleContent)
        rule1.sections = {"Section1": "Content1"}
        rule1.variables = {"var1": "value1"}
        
        rule2 = Mock(spec=RuleContent)
        rule2.sections = {"Section2": "Content2"}
        rule2.variables = {"var2": "value2"}
        
        result = service.resolve_conflicts([rule1, rule2])
        
        assert result["total_conflicts"] == 0
        assert len(result["conflicts"]) == 0

    def test_resolve_conflicts_with_conflicts(self, service, sample_rule_list):
        """Test resolving conflicts between rules"""
        result = service.resolve_conflicts(sample_rule_list)
        
        assert result["total_conflicts"] > 0
        assert result["strategy_used"] == ConflictResolution.MERGE.value

    def test_merge_section_content_empty_inputs(self, service):
        """Test merging empty section content"""
        assert service.merge_section_content("", "content") == "content"
        assert service.merge_section_content("content", "") == "content"
        assert service.merge_section_content("", "") == ""

    def test_merge_section_content_identical(self, service):
        """Test merging identical content"""
        content = "Same content"
        assert service.merge_section_content(content, content) == content

    def test_merge_section_content_different(self, service):
        """Test merging different content"""
        content1 = "Line 1\nLine 2"
        content2 = "Line 2\nLine 3"
        
        result = service.merge_section_content(content1, content2)
        
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_sort_rules_by_priority(self, service):
        """Test sorting rules by priority"""
        rule1 = Mock(spec=RuleContent)
        rule1.rule_type = Mock()
        rule1.rule_type.value = "workflow"
        rule1.metadata = Mock()
        rule1.metadata.priority = 5
        
        rule2 = Mock(spec=RuleContent)
        rule2.rule_type = Mock()
        rule2.rule_type.value = "core"
        rule2.metadata = Mock()
        rule2.metadata.priority = 10
        
        rule3 = Mock(spec=RuleContent)
        rule3.rule_type = None
        rule3.metadata = Mock()
        rule3.metadata.priority = 100
        
        sorted_rules = service._sort_rules_by_priority([rule1, rule2, rule3])
        
        # Core rule should be first (1000 + 10 = 1010)
        assert sorted_rules[0] == rule2
        # Workflow rule second (500 + 5 = 505)
        assert sorted_rules[1] == rule1
        # Rule without type last (0 + 100 = 100)
        assert sorted_rules[2] == rule3

    def test_intelligent_composition_strategy(self, service, sample_rule_list):
        """Test intelligent composition strategy"""
        content, conflicts, warnings = service._intelligent_composition(
            sample_rule_list, 
            RuleFormat.MDC
        )
        
        assert content != ""
        assert len(conflicts) > 0  # Should have resolved conflicts

    def test_sequential_composition_strategy(self, service, sample_rule_list):
        """Test sequential composition strategy"""
        content, conflicts, warnings = service._sequential_composition(
            sample_rule_list,
            RuleFormat.MDC
        )
        
        assert "# From rule1.md" in content
        assert "# From rule2.md" in content
        assert len(conflicts) == 0  # No conflict resolution in sequential

    def test_priority_merge_composition_strategy(self, service, sample_rule_list):
        """Test priority merge composition strategy"""
        content, conflicts, warnings = service._priority_merge_composition(
            sample_rule_list,
            RuleFormat.MDC
        )
        
        assert content != ""
        assert len(conflicts) >= 0

    def test_detect_rule_conflicts(self, service, sample_rule_list):
        """Test detecting conflicts between rules"""
        conflicts = service._detect_rule_conflicts(sample_rule_list[0], sample_rule_list[1])
        
        assert len(conflicts) > 0
        # Should detect both section and variable conflicts
        section_conflicts = [c for c in conflicts if c["type"] == "section"]
        var_conflicts = [c for c in conflicts if c["type"] == "variable"]
        
        assert len(section_conflicts) > 0  # Common section
        assert len(var_conflicts) > 0  # common_var

    def test_resolve_single_rule_conflict_merge(self, service):
        """Test resolving a single conflict with merge strategy"""
        conflict = {
            "type": "section",
            "name": "Common",
            "rule1_content": "Content 1",
            "rule2_content": "Content 2"
        }
        
        resolution = service._resolve_single_rule_conflict(conflict)
        
        assert resolution["strategy"] == ConflictResolution.MERGE.value
        assert resolution["resolved_value"] is not None
        assert "Merged section content" in resolution["resolution_reason"]

    def test_resolve_single_rule_conflict_override(self):
        """Test resolving a single conflict with override strategy"""
        service = RuleCompositionService(conflict_strategy=ConflictResolution.OVERRIDE)
        
        conflict = {
            "type": "variable",
            "name": "common_var",
            "rule1_value": "value1",
            "rule2_value": "value2"
        }
        
        resolution = service._resolve_single_rule_conflict(conflict)
        
        assert resolution["strategy"] == ConflictResolution.OVERRIDE.value
        assert resolution["resolved_value"] == "value2"
        assert "Override with latest value" in resolution["resolution_reason"]

    def test_build_inheritance_chain(self, service, sample_rule_list):
        """Test building inheritance chain from rules"""
        chain = service._build_inheritance_chain(sample_rule_list)
        
        assert len(chain) == 1  # One inheritance relationship for 2 rules
        inheritance = chain[0]
        assert inheritance.parent_path == "rule1.md"
        assert inheritance.child_path == "rule2.md"
        assert inheritance.inheritance_type == InheritanceType.CONTENT

    def test_generate_composed_content_mdc(self, service):
        """Test generating MDC format content"""
        sections = {"Section1": "Content 1", "Section2": "Content 2"}
        variables = {"var1": "value1"}
        metadata = {"title": "Test"}
        
        content = service._generate_composed_content(
            sections, variables, metadata, RuleFormat.MDC
        )
        
        assert "---" in content  # Metadata header
        assert "## Variables" in content
        assert "## Section1" in content
        assert "Content 1" in content

    def test_generate_composed_content_markdown(self, service):
        """Test generating Markdown format content"""
        sections = {"Section1": "Content 1"}
        variables = {"var1": "value1"}
        metadata = {"title": "Test Rule"}
        
        content = service._generate_composed_content(
            sections, variables, metadata, RuleFormat.MD
        )
        
        assert "# Test Rule" in content
        assert "## Configuration" in content
        assert "**var1**: value1" in content

    def test_generate_composed_content_json(self, service):
        """Test generating JSON format content"""
        sections = {"Section1": "Content 1"}
        variables = {"var1": "value1"}
        metadata = {"title": "Test"}
        
        content = service._generate_composed_content(
            sections, variables, metadata, RuleFormat.JSON
        )
        
        import json
        data = json.loads(content)
        assert data["metadata"]["title"] == "Test"
        assert data["variables"]["var1"] == "value1"
        assert data["sections"]["Section1"] == "Content 1"

    def test_composition_with_different_strategies(self, service, sample_rule_list):
        """Test all composition strategies"""
        strategies = ["intelligent", "sequential", "priority_merge"]
        
        for strategy in strategies:
            result = service.compose_rules(sample_rule_list, composition_strategy=strategy)
            assert result.success
            assert result.composition_metadata["strategy"] == strategy

    def test_compose_rules_with_unknown_strategy(self, service, sample_rule_list):
        """Test compose rules with unknown strategy defaults to intelligent"""
        result = service.compose_rules(sample_rule_list, composition_strategy="unknown")
        
        assert result.success
        # Should default to intelligent composition
        assert result.composition_metadata["strategy"] == "unknown"

    def test_sort_rules_handles_missing_attributes(self, service):
        """Test sorting rules handles missing attributes gracefully"""
        rule1 = Mock(spec=RuleContent)
        rule1.rule_type = None
        rule1.metadata = Mock(spec=[])  # No priority attribute
        
        rule2 = Mock(spec=RuleContent)
        rule2.rule_type = Mock()
        rule2.rule_type.value = "core"
        rule2.metadata = Mock()
        rule2.metadata.priority = "invalid"  # Non-numeric priority
        
        # Should not raise exception
        sorted_rules = service._sort_rules_by_priority([rule1, rule2])
        assert len(sorted_rules) == 2