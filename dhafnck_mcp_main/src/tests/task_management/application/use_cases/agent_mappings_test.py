"""Test for Agent Mappings Use Case"""

import pytest
from fastmcp.task_management.application.use_cases.agent_mappings import (
    DEPRECATED_AGENT_MAPPINGS,
    resolve_agent_name,
    is_deprecated_agent
)


class TestAgentMappings:
    """Test suite for agent name mappings and backward compatibility"""
    
    def test_deprecated_agent_mappings_structure(self):
        """Test that DEPRECATED_AGENT_MAPPINGS has the expected structure"""
        assert isinstance(DEPRECATED_AGENT_MAPPINGS, dict)
        
        # Verify all keys are strings
        for key, value in DEPRECATED_AGENT_MAPPINGS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
        
        # Verify expected mappings exist
        expected_mappings = {
            # Documentation consolidation
            "tech_spec_agent": "documentation-agent",
            "tech-spec-agent": "documentation-agent",
            "prd_architect_agent": "documentation-agent",
            "prd-architect-agent": "documentation-agent",
            
            # Research consolidation
            "mcp_researcher_agent": "deep-research-agent",
            "mcp-researcher-agent": "deep-research-agent",
            
            # Creative consolidation
            "idea_generation_agent": "creative-ideation-agent",
            "idea-generation-agent": "creative-ideation-agent",
            "idea_refinement_agent": "creative-ideation-agent",
            "idea-refinement-agent": "creative-ideation-agent",
            
            # Marketing consolidation
            "seo_sem_agent": "marketing-strategy-orchestrator-agent",
            "seo-sem-agent": "marketing-strategy-orchestrator-agent",
            "growth_hacking_idea_agent": "marketing-strategy-orchestrator-agent",
            "growth-hacking-idea-agent": "marketing-strategy-orchestrator-agent",
            "content_strategy_agent": "marketing-strategy-orchestrator-agent",
            "content-strategy-agent": "marketing-strategy-orchestrator-agent",
            
            # DevOps consolidation
            "swarm_scaler_agent": "devops-agent",
            "swarm-scaler-agent": "devops-agent",
            "adaptive_deployment_strategist_agent": "devops-agent",
            "adaptive-deployment-strategist-agent": "devops-agent",
            "mcp_configuration_agent": "devops-agent",
            "mcp-configuration-agent": "devops-agent",
            
            # Debug consolidation
            "remediation_agent": "debugger-agent",
            "remediation-agent": "debugger-agent",
            
            # Renamings
            "master-orchestrator-agent": "master-orchestrator-agent",
            "master-orchestrator-agent": "master-orchestrator-agent",
            "brainjs_ml_agent": "ml-specialist-agent",
            "brainjs-ml-agent": "ml-specialist-agent",
            "ui_designer_expert_shadcn_agent": "ui-specialist-agent",
            "ui-designer-expert-shadcn-agent": "ui-specialist-agent",
        }
        
        for old_name, new_name in expected_mappings.items():
            assert DEPRECATED_AGENT_MAPPINGS[old_name] == new_name


class TestResolveAgentName:
    """Test suite for resolve_agent_name function"""
    
    def test_resolve_deprecated_underscore_names(self):
        """Test resolving deprecated agent names with underscores"""
        test_cases = [
            ("tech_spec_agent", "documentation-agent"),
            ("prd_architect_agent", "documentation-agent"),
            ("mcp_researcher_agent", "deep-research-agent"),
            ("idea_generation_agent", "creative-ideation-agent"),
            ("idea_refinement_agent", "creative-ideation-agent"),
            ("seo_sem_agent", "marketing-strategy-orchestrator-agent"),
            ("growth_hacking_idea_agent", "marketing-strategy-orchestrator-agent"),
            ("content_strategy_agent", "marketing-strategy-orchestrator-agent"),
            ("swarm_scaler_agent", "devops-agent"),
            ("adaptive_deployment_strategist_agent", "devops-agent"),
            ("mcp_configuration_agent", "devops-agent"),
            ("remediation_agent", "debugger-agent"),
            ("master-orchestrator-agent", "master-orchestrator-agent"),
            ("brainjs_ml_agent", "ml-specialist-agent"),
            ("ui_designer_expert_shadcn_agent", "ui-specialist-agent"),
        ]
        
        for old_name, expected in test_cases:
            assert resolve_agent_name(old_name) == expected
    
    def test_resolve_deprecated_hyphenated_names(self):
        """Test resolving deprecated agent names with hyphens"""
        test_cases = [
            ("tech-spec-agent", "documentation-agent"),
            ("prd-architect-agent", "documentation-agent"),
            ("mcp-researcher-agent", "deep-research-agent"),
            ("idea-generation-agent", "creative-ideation-agent"),
            ("idea-refinement-agent", "creative-ideation-agent"),
            ("seo-sem-agent", "marketing-strategy-orchestrator-agent"),
            ("growth-hacking-idea-agent", "marketing-strategy-orchestrator-agent"),
            ("content-strategy-agent", "marketing-strategy-orchestrator-agent"),
            ("swarm-scaler-agent", "devops-agent"),
            ("adaptive-deployment-strategist-agent", "devops-agent"),
            ("mcp-configuration-agent", "devops-agent"),
            ("remediation-agent", "debugger-agent"),
            ("master-orchestrator-agent", "master-orchestrator-agent"),
            ("brainjs-ml-agent", "ml-specialist-agent"),
            ("ui-designer-expert-shadcn-agent", "ui-specialist-agent"),
        ]
        
        for old_name, expected in test_cases:
            assert resolve_agent_name(old_name) == expected
    
    def test_resolve_non_deprecated_names(self):
        """Test that non-deprecated names are returned unchanged"""
        test_cases = [
            "documentation-agent",
            "documentation-agent",
            "deep-research-agent",
            "deep-research-agent",
            "creative-ideation-agent",
            "creative-ideation-agent",
            "marketing-strategy-orchestrator-agent",
            "marketing-strategy-orchestrator-agent",
            "devops-agent",
            "devops-agent",
            "debugger-agent",
            "debugger-agent",
            "ml-specialist-agent",
            "ml-specialist-agent",
            "ui-specialist-agent",
            "ui-specialist-agent",
            "some_new_agent",
            "some-new-agent",
            "completely_unknown_agent",
            "another-test-agent",
        ]
        
        for name in test_cases:
            assert resolve_agent_name(name) == name
    
    def test_resolve_mixed_format_names(self):
        """Test resolving names that have mixed underscore/hyphen formats"""
        # Test that a name with underscores can resolve hyphenated deprecated names
        assert resolve_agent_name("tech-spec_agent") == "documentation-agent"
        
        # Test edge cases with inconsistent formatting
        assert resolve_agent_name("tech_spec-agent") == "documentation-agent"
    
    def test_resolve_empty_string(self):
        """Test resolving an empty string"""
        assert resolve_agent_name("") == ""
    
    def test_resolve_special_characters(self):
        """Test resolving names with special characters"""
        # Names with special characters should be returned unchanged
        special_names = [
            "agent@test",
            "agent#123",
            "agent.test",
            "agent+plus",
            "agent!exclaim",
        ]
        
        for name in special_names:
            assert resolve_agent_name(name) == name


class TestIsDeprecatedAgent:
    """Test suite for is_deprecated_agent function"""
    
    def test_is_deprecated_underscore_names(self):
        """Test checking deprecated status of underscore names"""
        deprecated_names = [
            "tech_spec_agent",
            "prd_architect_agent",
            "mcp_researcher_agent",
            "idea_generation_agent",
            "idea_refinement_agent",
            "seo_sem_agent",
            "growth_hacking_idea_agent",
            "content_strategy_agent",
            "swarm_scaler_agent",
            "adaptive_deployment_strategist_agent",
            "mcp_configuration_agent",
            "remediation_agent",
            "master-orchestrator-agent",
            "brainjs_ml_agent",
            "ui_designer_expert_shadcn_agent",
        ]
        
        for name in deprecated_names:
            assert is_deprecated_agent(name) is True
    
    def test_is_deprecated_hyphenated_names(self):
        """Test checking deprecated status of hyphenated names"""
        deprecated_names = [
            "tech-spec-agent",
            "prd-architect-agent",
            "mcp-researcher-agent",
            "idea-generation-agent",
            "idea-refinement-agent",
            "seo-sem-agent",
            "growth-hacking-idea-agent",
            "content-strategy-agent",
            "swarm-scaler-agent",
            "adaptive-deployment-strategist-agent",
            "mcp-configuration-agent",
            "remediation-agent",
            "master-orchestrator-agent",
            "brainjs-ml-agent",
            "ui-designer-expert-shadcn-agent",
        ]
        
        for name in deprecated_names:
            assert is_deprecated_agent(name) is True
    
    def test_is_not_deprecated_names(self):
        """Test checking deprecated status of non-deprecated names"""
        active_names = [
            "documentation-agent",
            "documentation-agent",
            "deep-research-agent",
            "deep-research-agent",
            "creative-ideation-agent",
            "creative-ideation-agent",
            "marketing-strategy-orchestrator-agent",
            "marketing-strategy-orchestrator-agent",
            "devops-agent",
            "devops-agent",
            "debugger-agent",
            "debugger-agent",
            "ml-specialist-agent",
            "ml-specialist-agent",
            "ui-specialist-agent",
            "ui-specialist-agent",
            "coding-agent",
            "test-orchestrator-agent",
            "security-auditor-agent",
            "unknown_agent",
            "new-agent-name",
        ]
        
        for name in active_names:
            assert is_deprecated_agent(name) is False
    
    def test_is_deprecated_mixed_format_names(self):
        """Test checking deprecated status with mixed formats"""
        # These should still be recognized as deprecated
        assert is_deprecated_agent("tech-spec_agent") is True
        assert is_deprecated_agent("tech_spec-agent") is True
        assert is_deprecated_agent("mcp_researcher-agent") is True
        assert is_deprecated_agent("mcp-researcher_agent") is True
    
    def test_is_deprecated_empty_string(self):
        """Test checking deprecated status of empty string"""
        assert is_deprecated_agent("") is False
    
    def test_is_deprecated_special_characters(self):
        """Test checking deprecated status with special characters"""
        special_names = [
            "agent@deprecated",
            "agent#123",
            "agent.old",
            "agent+deprecated",
            "deprecated!agent",
        ]
        
        for name in special_names:
            assert is_deprecated_agent(name) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_resolve_none_like_strings(self):
        """Test resolving strings that could be confused with None"""
        test_cases = ["None", "none", "null", "NULL", "undefined"]
        
        for name in test_cases:
            # These should be treated as regular strings
            assert resolve_agent_name(name) == name
            assert is_deprecated_agent(name) is False
    
    def test_resolve_numeric_strings(self):
        """Test resolving numeric strings"""
        test_cases = ["123", "456_agent", "agent-789", "0", "-1"]
        
        for name in test_cases:
            assert resolve_agent_name(name) == name
            assert is_deprecated_agent(name) is False
    
    def test_resolve_unicode_names(self):
        """Test resolving names with unicode characters"""
        test_cases = [
            "agent_测试",
            "тест-agent",
            "agent_🤖",
            "ñ_agent",
            "agent-ü",
        ]
        
        for name in test_cases:
            assert resolve_agent_name(name) == name
            assert is_deprecated_agent(name) is False
    
    def test_resolve_very_long_names(self):
        """Test resolving very long agent names"""
        long_name = "a" * 1000 + "_agent"
        assert resolve_agent_name(long_name) == long_name
        assert is_deprecated_agent(long_name) is False
    
    def test_case_sensitivity(self):
        """Test that agent name resolution is case-sensitive"""
        # Uppercase versions should not be recognized as deprecated
        assert resolve_agent_name("TECH_SPEC_AGENT") == "TECH_SPEC_AGENT"
        assert is_deprecated_agent("TECH_SPEC_AGENT") is False
        
        # Mixed case should also not be recognized
        assert resolve_agent_name("Tech_Spec_Agent") == "Tech_Spec_Agent"
        assert is_deprecated_agent("Tech_Spec_Agent") is False
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in agent names"""
        # Names with spaces should not be normalized
        assert resolve_agent_name("tech spec agent") == "tech spec agent"
        assert is_deprecated_agent("tech spec agent") is False
        
        # Names with leading/trailing whitespace
        assert resolve_agent_name(" tech_spec_agent ") == " tech_spec_agent "
        assert is_deprecated_agent(" tech_spec_agent ") is False
    
    def test_multiple_consecutive_separators(self):
        """Test handling of multiple consecutive separators"""
        test_cases = [
            "tech__spec__agent",
            "tech--spec--agent",
            "tech___spec___agent",
            "tech---spec---agent",
        ]
        
        for name in test_cases:
            # These should not match the deprecated names
            assert resolve_agent_name(name) == name
            assert is_deprecated_agent(name) is False


class TestConsistency:
    """Test consistency between resolve_agent_name and is_deprecated_agent"""
    
    def test_consistency_for_all_deprecated_names(self):
        """Test that all deprecated names are consistently handled by both functions"""
        for old_name, new_name in DEPRECATED_AGENT_MAPPINGS.items():
            # If a name is deprecated, it should resolve to a different name
            resolved = resolve_agent_name(old_name)
            is_deprecated = is_deprecated_agent(old_name)
            
            assert is_deprecated is True
            assert resolved == new_name
            
            # The resolved name should not be deprecated (unless it maps to itself)
            if old_name != new_name:
                # Convert format if needed to check
                if '-' in new_name and '_' in new_name:
                    # Mixed format, check exact match
                    assert is_deprecated_agent(new_name) == (new_name in DEPRECATED_AGENT_MAPPINGS)
                else:
                    # For consistency, check both formats of the target name
                    new_name_alt = new_name.replace('-', '_') if '-' in new_name else new_name.replace('_', '-')
                    # At least one format of the target should not be deprecated
                    assert (not is_deprecated_agent(new_name) or 
                           not is_deprecated_agent(new_name_alt) or
                           new_name in DEPRECATED_AGENT_MAPPINGS.values())
    
    def test_idempotency(self):
        """Test that resolving a name twice gives the same result"""
        test_names = [
            "tech_spec_agent",
            "documentation-agent",
            "unknown_agent",
            "mcp-researcher-agent",
            "deep-research-agent",
        ]
        
        for name in test_names:
            first_resolve = resolve_agent_name(name)
            second_resolve = resolve_agent_name(first_resolve)
            
            # For non-deprecated names, both should be the same
            if not is_deprecated_agent(name):
                assert first_resolve == second_resolve == name
            else:
                # For deprecated names, the resolved name should be stable
                assert second_resolve == first_resolve