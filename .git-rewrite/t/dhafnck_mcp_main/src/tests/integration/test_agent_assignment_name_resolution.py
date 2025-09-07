"""
Integration tests for agent assignment with name resolution support.

This test file validates that agent assignment works with:
1. UUID format (existing functionality)
2. @prefixed agent names (new functionality)  
3. Agent names without @ prefix (new functionality)
"""

import pytest
import uuid
from typing import Dict, Any
from unittest.mock import patch

from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.application.factories.agent_facade_factory import AgentFacadeFactory


class TestAgentAssignmentNameResolution:
    """Test agent assignment with user-friendly name resolution"""
    
    @pytest.fixture
    def project_id(self) -> str:
        """Create a test project and return its ID"""
        import asyncio
        import threading
        
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        project_facade = ProjectFacadeFactory().create_project_facade(user_id=test_user_id)
        
        # Handle async project creation in a sync test
        result = None
        exception = None
        
        def run_in_new_loop():
            nonlocal result, exception
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(
                    project_facade.manage_project(
                        action="create",
                        name="test-agent-assignment",
                        description="Test project for agent assignment",
                        user_id=test_user_id
                    )
                )
                new_loop.close()
            except Exception as e:
                exception = e
                if new_loop:
                    new_loop.close()
        
        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()
        
        if exception:
            raise exception
            
        assert result["success"], f"Failed to create project: {result.get('error')}"
        return result["project"]["id"]
    
    @pytest.fixture  
    def git_branch_id(self, project_id: str) -> str:
        """Create a test git branch and return its ID"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        git_branch_facade = GitBranchFacadeFactory().create_git_branch_facade(project_id=project_id, user_id=test_user_id)
        result = git_branch_facade.create_git_branch(project_id, "feature/test-branch", "Test branch for agent assignment")
        assert result["success"], f"Failed to create branch: {result.get('error')}"
        return result["git_branch"]["id"]
    
    @pytest.fixture
    def controller(self) -> GitBranchMCPController:
        """Create a GitBranchMCPController instance"""
        factory = GitBranchFacadeFactory()
        return GitBranchMCPController(factory)
    
    def test_resolve_agent_identifier_uuid_format(self, controller: GitBranchMCPController, project_id: str):
        """Test that UUID format is preserved as-is"""
        test_uuid = str(uuid.uuid4())
        resolved_id = controller._resolve_agent_identifier(project_id, test_uuid)
        
        assert resolved_id == test_uuid, f"UUID should be preserved as-is, got: {resolved_id}"
    
    def test_resolve_agent_identifier_prefixed_name(self, controller: GitBranchMCPController, project_id: str):
        """Test that @prefixed agent names are preserved as-is"""
        agent_name = "@coding_agent"
        resolved_id = controller._resolve_agent_identifier(project_id, agent_name)
        
        assert resolved_id == agent_name, f"@prefixed name should be preserved, got: {resolved_id}"
    
    def test_resolve_agent_identifier_unprefixed_name(self, controller: GitBranchMCPController, project_id: str):
        """Test that unprefixed agent names get @ prefix added"""
        agent_name = "coding_agent"
        expected_resolved = "@coding_agent"
        resolved_id = controller._resolve_agent_identifier(project_id, agent_name)
        
        assert resolved_id == expected_resolved, f"Unprefixed name should get @ prefix, got: {resolved_id}"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_assign_agent_with_uuid(self, mock_auth, controller: GitBranchMCPController, project_id: str, git_branch_id: str):
        """Test agent assignment using UUID format (existing functionality)"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        # Register agent first to get UUID
        agent_facade = AgentFacadeFactory().create_agent_facade(project_id=project_id, user_id=test_user_id)
        agent_uuid = str(uuid.uuid4())
        register_result = agent_facade.register_agent(project_id, agent_uuid, "Test UUID Agent")
        assert register_result["success"], f"Failed to register agent: {register_result.get('error')}"
        
        # Assign agent using UUID
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=agent_uuid,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent assignment with UUID failed: {result.get('error')}"
        assert result["agent_id"] == agent_uuid, f"Expected agent_id to be {agent_uuid}, got: {result.get('agent_id')}"
        assert result["original_agent_id"] == agent_uuid, "original_agent_id should match input"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_assign_agent_with_prefixed_name(self, mock_auth, controller: GitBranchMCPController, project_id: str, git_branch_id: str):
        """Test agent assignment using @prefixed agent name (new functionality)"""
        agent_name = "@test_coding_agent"
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=agent_name,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent assignment with @prefixed name failed: {result.get('error')}"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        # The UUID:name format should contain the clean agent name (no @ prefix)
        clean_expected = agent_name.lstrip('@')
        assert clean_expected in result["agent_id"], f"Expected '{clean_expected}' in UUID format: {result['agent_id']}"
        assert result["original_agent_id"] == agent_name, "original_agent_id should match input"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_assign_agent_with_unprefixed_name(self, mock_auth, controller: GitBranchMCPController, project_id: str, git_branch_id: str):
        """Test agent assignment using unprefixed agent name (new functionality)"""
        agent_name = "test_ui_agent"
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=agent_name,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent assignment with unprefixed name failed: {result.get('error')}"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        # The UUID:name format should contain the clean agent name
        assert "test_ui_agent" in result["agent_id"], f"Expected 'test_ui_agent' in UUID format: {result['agent_id']}"
        assert result["original_agent_id"] == agent_name, "original_agent_id should match input"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_unassign_agent_with_prefixed_name(self, mock_auth, controller: GitBranchMCPController, project_id: str, git_branch_id: str):
        """Test agent unassignment using @prefixed agent name"""
        agent_name = "@test_debugger_agent"
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        # First assign the agent
        assign_result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=agent_name,
            user_id=test_user_id
        )
        assert assign_result["success"], f"Failed to assign agent: {assign_result.get('error')}"
        
        # Then unassign using the same name format
        result = controller.manage_git_branch(
            action="unassign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=agent_name,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent unassignment with @prefixed name failed: {result.get('error')}"
        # For unassign, we should get the same UUID format that was assigned
        assigned_agent_id = assign_result["agent_id"]
        assert result["agent_id"] == assigned_agent_id, f"Expected agent_id to match assigned ID, got: {result.get('agent_id')}"
        assert result["original_agent_id"] == agent_name, "original_agent_id should match input"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_assign_agent_with_branch_name(self, mock_auth, controller: GitBranchMCPController, project_id: str):
        """Test agent assignment using branch name instead of branch ID"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        # Create a test branch with a specific name
        git_branch_facade = GitBranchFacadeFactory().create_git_branch_facade(project_id=project_id, user_id=test_user_id)
        branch_result = git_branch_facade.create_git_branch(project_id, "feature/agent-test", "Branch for agent assignment test")
        assert branch_result["success"], f"Failed to create branch: {branch_result.get('error')}"
        
        agent_name = "@branch_test_agent"
        branch_name = "feature/agent-test"
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_name=branch_name,
            agent_id=agent_name,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent assignment with branch name failed: {result.get('error')}"
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        assert result["git_branch_name"] == branch_name, f"Expected branch_name to be {branch_name}, got: {result.get('git_branch_name')}"
        assert result["original_agent_id"] == agent_name, "original_agent_id should match input"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_error_handling_invalid_branch(self, mock_auth, controller: GitBranchMCPController, project_id: str):
        """Test error handling when branch doesn't exist"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_name="non-existent-branch",
            agent_id="@test_agent",
            user_id=test_user_id
        )
        
        assert not result["success"], "Assignment to non-existent branch should fail"
        assert result["error_code"] == "BRANCH_NOT_FOUND", f"Expected BRANCH_NOT_FOUND error code, got: {result.get('error_code')}"
        assert "non-existent-branch" in result["error"], "Error message should mention the branch name"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_response_includes_tracking_fields(self, mock_auth, controller: GitBranchMCPController, project_id: str, git_branch_id: str):
        """Test that response includes both resolved and original agent identifiers"""
        original_agent_id = "tracking_test_agent"
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        result = controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=git_branch_id,
            agent_id=original_agent_id,
            user_id=test_user_id
        )
        
        assert result["success"], f"Agent assignment failed: {result.get('error')}"
        
        # Verify tracking fields are present
        assert "agent_id" in result, "Response should include resolved agent_id"
        assert "original_agent_id" in result, "Response should include original_agent_id"
        assert "action" in result, "Response should include action"
        
        # Verify values are correct
        # agent_id should be the resolved UUID format from auto-registration
        assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
        assert "tracking_test_agent" in result["agent_id"], f"Expected 'tracking_test_agent' in UUID format: {result['agent_id']}"
        assert result["original_agent_id"] == original_agent_id, f"Expected original_agent_id to be {original_agent_id}"
        assert result["action"] == "assign_agent", "Action should be assign_agent"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_authenticated_user_id')
    def test_edge_cases_empty_and_special_characters(self, mock_auth, controller: GitBranchMCPController, project_id: str):
        """Test edge cases with empty strings and special characters"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_auth.return_value = test_user_id
        
        # Test with edge case agent names (these should work since they'll be auto-registered)
        edge_cases = [
            "@agent-with-dashes",
            "@agent_with_underscores", 
            "agent123",
            "@agent.with.dots"
        ]
        
        git_branch_facade = GitBranchFacadeFactory().create_git_branch_facade(project_id=project_id, user_id=test_user_id)
        
        for i, agent_name in enumerate(edge_cases):
            # Create a unique branch for each test
            branch_name = f"test-edge-case-{i}"
            branch_result = git_branch_facade.create_git_branch(project_id, branch_name, f"Branch for edge case test {i}")
            assert branch_result["success"], f"Failed to create branch {branch_name}"
            
            branch_id = branch_result["git_branch"]["id"]
            
            result = controller.manage_git_branch(
                action="assign_agent",
                project_id=project_id,
                git_branch_id=branch_id,
                agent_id=agent_name,
                user_id=test_user_id
            )
            
            # These should succeed due to auto-registration in the agent repository
            assert result["success"], f"Assignment with edge case agent name '{agent_name}' failed: {result.get('error')}"
            
            # agent_id should be the resolved UUID format from auto-registration
            assert ":" in result["agent_id"], f"Expected UUID:name format, got: {result['agent_id']}"
            
            # Verify the resolution logic worked correctly in the UUID:name format
            if agent_name.startswith('@'):
                clean_name = agent_name.lstrip('@')
                assert clean_name in result["agent_id"], f"Expected '{clean_name}' in UUID format: {result['agent_id']}"
            else:
                assert agent_name in result["agent_id"], f"Expected '{agent_name}' in UUID format: {result['agent_id']}"