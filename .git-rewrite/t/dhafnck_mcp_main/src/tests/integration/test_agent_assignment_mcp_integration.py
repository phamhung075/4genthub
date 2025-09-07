"""
Integration test for agent assignment via MCP tools.

This test verifies that the MCP tool correctly handles agent name resolution
when called through the MCP interface.
"""

import pytest

# Import MCP tool directly
try:
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="MCP tools not available")
class TestAgentAssignmentMCPIntegration:
    """Test agent assignment through MCP tools interface"""
    
    @pytest.fixture
    def mcp_tools(self):
        """Create MCP tools instance"""
        return DDDCompliantMCPTools()
    
    @pytest.fixture
    def project_and_branch(self, mcp_tools):
        """Create test project and branch, return their details"""
        # Create project with test user ID (valid UUID format)
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        project_result = mcp_tools.manage_project(
            action="create",
            name="test-agent-mcp",
            description="Test project for agent MCP integration",
            user_id=test_user_id
        )
        assert project_result["success"], f"Failed to create project: {project_result.get('error')}"
        project_id = project_result["project"]["id"]
        
        # Create branch
        branch_result = mcp_tools.manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name="test-agent-branch",
            git_branch_description="Test branch for agent assignment",
            user_id=test_user_id
        )
        assert branch_result["success"], f"Failed to create branch: {branch_result.get('error')}"
        branch_id = branch_result["git_branch"]["id"]
        
        return {
            "project_id": project_id,
            "branch_id": branch_id,
            "branch_name": "test-agent-branch",
            "user_id": test_user_id
        }
    
    def test_assign_agent_with_prefixed_name_via_mcp(self, mcp_tools, project_and_branch):
        """Test assigning agent with @prefixed name through MCP interface"""
        agent_name = "@mcp_test_agent"
        
        result = mcp_tools.manage_git_branch(
            action="assign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_id=project_and_branch["branch_id"],
            agent_id=agent_name,
            user_id=project_and_branch["user_id"]
        )
        
        assert result["success"], f"Agent assignment failed: {result.get('error')}"
        assert result["action"] == "assign_agent"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        # original_agent_id should preserve user input
        assert result["original_agent_id"] == agent_name
        assert "workflow_guidance" in result, "Response should include workflow guidance"
    
    def test_assign_agent_with_unprefixed_name_via_mcp(self, mcp_tools, project_and_branch):
        """Test assigning agent with unprefixed name through MCP interface"""
        agent_name = "mcp_unprefixed_agent"
        expected_resolved = "@mcp_unprefixed_agent"
        
        result = mcp_tools.manage_git_branch(
            action="assign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_id=project_and_branch["branch_id"],
            agent_id=agent_name,
            user_id=project_and_branch["user_id"]
        )
        
        assert result["success"], f"Agent assignment failed: {result.get('error')}"
        assert result["action"] == "assign_agent"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        # The UUID:name format should contain the prefixed name
        assert "mcp_unprefixed_agent" in result["agent_id"], f"Expected agent name in UUID format: {result['agent_id']}"
        # original_agent_id should preserve user input
        assert result["original_agent_id"] == agent_name
        assert "workflow_guidance" in result, "Response should include workflow guidance"
    
    def test_assign_agent_with_branch_name_via_mcp(self, mcp_tools, project_and_branch):
        """Test assigning agent using branch name instead of branch ID through MCP interface"""
        agent_name = "@branch_name_test_agent"
        
        result = mcp_tools.manage_git_branch(
            action="assign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_name=project_and_branch["branch_name"],
            agent_id=agent_name,
            user_id=project_and_branch["user_id"]
        )
        
        assert result["success"], f"Agent assignment failed: {result.get('error')}"
        assert result["action"] == "assign_agent"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        # original_agent_id should preserve user input
        assert result["original_agent_id"] == agent_name
        assert result["git_branch_name"] == project_and_branch["branch_name"]
        assert "workflow_guidance" in result, "Response should include workflow guidance"
    
    def test_unassign_agent_via_mcp(self, mcp_tools, project_and_branch):
        """Test unassigning agent through MCP interface"""
        agent_name = "@mcp_unassign_test_agent"
        
        # First assign the agent
        assign_result = mcp_tools.manage_git_branch(
            action="assign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_id=project_and_branch["branch_id"],
            agent_id=agent_name,
            user_id=project_and_branch["user_id"]
        )
        assert assign_result["success"], f"Failed to assign agent: {assign_result.get('error')}"
        
        # Then unassign
        unassign_result = mcp_tools.manage_git_branch(
            action="unassign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_id=project_and_branch["branch_id"],
            agent_id=agent_name,
            user_id=project_and_branch["user_id"]
        )
        
        assert unassign_result["success"], f"Agent unassignment failed: {unassign_result.get('error')}"
        assert unassign_result["action"] == "unassign_agent"
        # For unassign, we should get the same UUID format that was assigned
        # The agent_id should match what was returned from assignment
        assigned_agent_id = assign_result["agent_id"]
        assert unassign_result["agent_id"] == assigned_agent_id
        assert unassign_result["original_agent_id"] == agent_name
        assert "workflow_guidance" in unassign_result, "Response should include workflow guidance"
    
    def test_error_handling_invalid_branch_via_mcp(self, mcp_tools, project_and_branch):
        """Test error handling for invalid branch through MCP interface"""
        result = mcp_tools.manage_git_branch(
            action="assign_agent",
            project_id=project_and_branch["project_id"],
            git_branch_name="non-existent-branch",
            agent_id="@error_test_agent",
            user_id=project_and_branch["user_id"]
        )
        
        assert not result["success"], "Assignment to non-existent branch should fail"
        assert result["error_code"] == "BRANCH_NOT_FOUND"
        assert "non-existent-branch" in result["error"]
    
    def test_all_agent_formats_work_via_mcp(self, mcp_tools, project_and_branch):
        """Test that all supported agent formats work through MCP interface"""
        # Create separate branches for each test to avoid conflicts
        project_id = project_and_branch["project_id"]
        
        test_cases = [
            ("@prefixed_agent", "@prefixed_agent", "prefixed-test"),
            ("unprefixed_agent", "@unprefixed_agent", "unprefixed-test"),
            ("agent-with-dashes", "@agent-with-dashes", "dashes-test"),
            ("agent_with_underscores", "@agent_with_underscores", "underscores-test")
        ]
        
        for input_agent, expected_agent, branch_suffix in test_cases:
            # Create unique branch for this test
            branch_result = mcp_tools.manage_git_branch(
                action="create",
                project_id=project_id,
                git_branch_name=f"test-{branch_suffix}",
                git_branch_description=f"Branch for testing {input_agent}",
                user_id=project_and_branch["user_id"]
            )
            assert branch_result["success"], f"Failed to create branch for {input_agent}"
            branch_id = branch_result["git_branch"]["id"]
            
            # Test assignment
            assign_result = mcp_tools.manage_git_branch(
                action="assign_agent",
                project_id=project_id,
                git_branch_id=branch_id,
                agent_id=input_agent,
                user_id=project_and_branch["user_id"]
            )
            
            assert assign_result["success"], f"Assignment failed for agent '{input_agent}': {assign_result.get('error')}"
            # agent_id should be the resolved UUID format from auto-registration
            assert ":" in assign_result["agent_id"], f"Expected UUID:name format, got: {assign_result['agent_id']}"
            # The UUID:name format should contain the clean agent name (no @ prefix)
            clean_expected = expected_agent.lstrip('@')
            assert clean_expected in assign_result["agent_id"], f"Expected '{clean_expected}' in UUID format: {assign_result['agent_id']}"
            assert assign_result["original_agent_id"] == input_agent, f"Original agent ID should be preserved"