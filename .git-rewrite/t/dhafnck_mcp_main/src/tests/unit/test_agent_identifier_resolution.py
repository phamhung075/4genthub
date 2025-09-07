"""
Unit tests for agent identifier resolution functionality.

This test file validates the _resolve_agent_identifier method works correctly
with different input formats.
"""

import pytest
import uuid
from unittest.mock import Mock

from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory


class TestAgentIdentifierResolution:
    """Test the agent identifier resolution method in isolation"""
    
    @pytest.fixture
    def controller(self) -> GitBranchMCPController:
        """Create a GitBranchMCPController instance"""
        factory = GitBranchFacadeFactory()
        return GitBranchMCPController(factory)
    
    def test_resolve_agent_identifier_valid_uuid(self, controller: GitBranchMCPController):
        """Test that valid UUID format is preserved as-is"""
        test_uuid = str(uuid.uuid4())
        project_id = "test-project"
        
        resolved_id = controller._resolve_agent_identifier(project_id, test_uuid)
        
        assert resolved_id == test_uuid, f"UUID should be preserved as-is, got: {resolved_id}"
    
    def test_resolve_agent_identifier_uuid_different_cases(self, controller: GitBranchMCPController):
        """Test that UUIDs with different cases are handled correctly"""
        test_uuid_lower = "2d3727cf-6915-4b54-be8d-4a5a0311ca03"
        test_uuid_upper = "2D3727CF-6915-4B54-BE8D-4A5A0311CA03"
        test_uuid_mixed = "2d3727CF-6915-4b54-BE8d-4a5a0311CA03"
        project_id = "test-project"
        
        # All should be preserved as-is
        assert controller._resolve_agent_identifier(project_id, test_uuid_lower) == test_uuid_lower
        assert controller._resolve_agent_identifier(project_id, test_uuid_upper) == test_uuid_upper
        assert controller._resolve_agent_identifier(project_id, test_uuid_mixed) == test_uuid_mixed
    
    def test_resolve_agent_identifier_prefixed_name(self, controller: GitBranchMCPController):
        """Test that @prefixed agent names are preserved as-is"""
        test_cases = [
            "@coding_agent",
            "@ui_designer_agent", 
            "@debugger_agent",
            "@test-agent-with-dashes",
            "@agent_with_underscores",
            "@agent123",
            "@agent.with.dots"
        ]
        project_id = "test-project"
        
        for agent_name in test_cases:
            resolved_id = controller._resolve_agent_identifier(project_id, agent_name)
            assert resolved_id == agent_name, f"@prefixed name '{agent_name}' should be preserved, got: {resolved_id}"
    
    def test_resolve_agent_identifier_unprefixed_name(self, controller: GitBranchMCPController):
        """Test that unprefixed agent names get @ prefix added"""
        test_cases = [
            ("coding_agent", "@coding_agent"),
            ("ui_designer_agent", "@ui_designer_agent"),
            ("debugger_agent", "@debugger_agent"),
            ("test-agent-with-dashes", "@test-agent-with-dashes"),
            ("agent_with_underscores", "@agent_with_underscores"),
            ("agent123", "@agent123"),
            ("agent.with.dots", "@agent.with.dots")
        ]
        project_id = "test-project"
        
        for input_name, expected_output in test_cases:
            resolved_id = controller._resolve_agent_identifier(project_id, input_name)
            assert resolved_id == expected_output, f"Unprefixed name '{input_name}' should become '{expected_output}', got: {resolved_id}"
    
    def test_resolve_agent_identifier_edge_cases(self, controller: GitBranchMCPController):
        """Test edge cases for agent identifier resolution"""
        project_id = "test-project"
        
        # Single character names
        assert controller._resolve_agent_identifier(project_id, "a") == "@a"
        assert controller._resolve_agent_identifier(project_id, "@a") == "@a"
        
        # Very long names (should work)
        long_name = "very_long_agent_name_with_many_characters_to_test_length_handling"
        expected_long = f"@{long_name}"
        assert controller._resolve_agent_identifier(project_id, long_name) == expected_long
        assert controller._resolve_agent_identifier(project_id, expected_long) == expected_long
        
        # Names with numbers
        assert controller._resolve_agent_identifier(project_id, "agent1") == "@agent1"
        assert controller._resolve_agent_identifier(project_id, "123agent") == "@123agent"
    
    def test_resolve_agent_identifier_error_handling(self, controller: GitBranchMCPController):
        """Test that errors in resolution are handled gracefully"""
        project_id = "test-project"
        
        # Test with potentially problematic inputs - these should not crash
        edge_cases = [
            "",  # Empty string
            "@",  # Just the @ symbol
            "@@agent",  # Double @ prefix
        ]
        
        for edge_case in edge_cases:
            try:
                # Should not crash, even with edge cases
                result = controller._resolve_agent_identifier(project_id, edge_case)
                # Result should be a string (even if it's the same as input)
                assert isinstance(result, str), f"Result should be string, got: {type(result)}"
            except Exception as e:
                pytest.fail(f"Agent identifier resolution should not crash on input '{edge_case}', but got: {e}")
    
    def test_resolve_agent_identifier_malformed_uuid(self, controller: GitBranchMCPController):
        """Test that malformed UUIDs are treated as agent names"""
        project_id = "test-project"
        
        malformed_uuids = [
            "2d3727cf-6915-4b54-be8d",  # Too short
            "2d3727cf-6915-4b54-be8d-4a5a0311ca03-extra",  # Too long
            "2d3727cf_6915_4b54_be8d_4a5a0311ca03",  # Wrong separator
            "2d3727cf-6915-4b54-be8d-4a5a0311ca0g",  # Invalid hex character
        ]
        
        for malformed_uuid in malformed_uuids:
            resolved_id = controller._resolve_agent_identifier(project_id, malformed_uuid)
            expected = f"@{malformed_uuid}"
            assert resolved_id == expected, f"Malformed UUID '{malformed_uuid}' should be treated as agent name: expected '{expected}', got '{resolved_id}'"
    
    def test_resolve_agent_identifier_multiple_calls_consistent(self, controller: GitBranchMCPController):
        """Test that multiple calls with same input return consistent results"""
        project_id = "test-project"
        test_inputs = [
            str(uuid.uuid4()),
            "@coding_agent",
            "debugger_agent"
        ]
        
        for test_input in test_inputs:
            # Call multiple times and verify consistency
            result1 = controller._resolve_agent_identifier(project_id, test_input)
            result2 = controller._resolve_agent_identifier(project_id, test_input)
            result3 = controller._resolve_agent_identifier(project_id, test_input)
            
            assert result1 == result2 == result3, f"Multiple calls should return consistent results for '{test_input}'"
    
    def test_resolve_agent_identifier_case_sensitivity(self, controller: GitBranchMCPController):
        """Test that agent name resolution is case-sensitive"""
        project_id = "test-project"
        
        # These should all be treated as different agents
        test_cases = [
            ("Agent", "@Agent"),
            ("agent", "@agent"), 
            ("AGENT", "@AGENT"),
            ("@Agent", "@Agent"),
            ("@agent", "@agent"),
            ("@AGENT", "@AGENT")
        ]
        
        for input_name, expected_output in test_cases:
            resolved_id = controller._resolve_agent_identifier(project_id, input_name)
            assert resolved_id == expected_output, f"Case sensitivity test failed for '{input_name}': expected '{expected_output}', got '{resolved_id}'"
    
    def test_resolve_agent_identifier_preserves_special_characters(self, controller: GitBranchMCPController):
        """Test that special characters in agent names are preserved"""
        project_id = "test-project"
        
        special_char_cases = [
            ("agent-1", "@agent-1"),
            ("agent_2", "@agent_2"),
            ("agent.3", "@agent.3"),
            ("agent+4", "@agent+4"),
            ("@agent-5", "@agent-5"),
            ("@agent_6", "@agent_6"),
            ("@agent.7", "@agent.7")
        ]
        
        for input_name, expected_output in special_char_cases:
            resolved_id = controller._resolve_agent_identifier(project_id, input_name)
            assert resolved_id == expected_output, f"Special character preservation failed for '{input_name}': expected '{expected_output}', got '{resolved_id}'"