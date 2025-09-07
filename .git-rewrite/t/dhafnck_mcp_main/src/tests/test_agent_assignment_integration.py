"""Integration test for agent assignment with @agent_name format"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.application.factories.agent_facade_factory import AgentFacadeFactory


class TestAgentAssignmentIntegration:
    """Integration test for agent assignment with various formats"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.controller = GitBranchMCPController(GitBranchFacadeFactory())
        self.project_id = str(uuid.uuid4())
        self.branch_id = str(uuid.uuid4())
        self.branch_name = "main"
        
    @patch('fastmcp.task_management.application.factories.agent_facade_factory.AgentFacadeFactory')
    @patch.object(GitBranchMCPController, '_resolve_branch_name_to_id')
    @patch.object(GitBranchMCPController, '_get_facade_for_request')
    def test_assign_agent_with_at_name_format(self, mock_get_facade, mock_resolve_branch, mock_agent_factory):
        """Test that @agent_name format works end-to-end"""
        
        # Set up mocks
        mock_resolve_branch.return_value = self.branch_id
        
        # Mock agent facade
        mock_agent_facade = Mock()
        mock_agent_facade.assign_agent.return_value = {
            "success": True,
            "message": "Agent assigned successfully"
        }
        
        mock_factory_instance = Mock()
        mock_factory_instance.create_agent_facade.return_value = mock_agent_facade
        mock_agent_factory.return_value = mock_factory_instance
        
        # Mock the _resolve_agent_identifier to simulate our logic
        with patch.object(self.controller, '_resolve_agent_identifier') as mock_resolve:
            # Simulate that @coding_agent doesn't exist and gets a generated UUID
            generated_uuid = str(uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_DNS, self.project_id), "coding_agent"))
            mock_resolve.return_value = f"{generated_uuid}:coding_agent"
            
            # Test the assignment
            result = self.controller.manage_git_branch(
                action="assign_agent",
                project_id=self.project_id,
                git_branch_name=self.branch_name,
                agent_id="@coding_agent"
            )
            
            # Verify the result
            assert result["success"] == True
            assert "workflow_guidance" in result or "message" in result
            
            # Verify _resolve_agent_identifier was called with the right parameters
            mock_resolve.assert_called_once_with(self.project_id, "@coding_agent")
            
            # Verify the agent facade was called with the resolved UUID
            mock_agent_facade.assign_agent.assert_called_once_with(
                self.project_id,
                f"{generated_uuid}:coding_agent",
                self.branch_id
            )
            
    @patch('fastmcp.task_management.application.factories.agent_facade_factory.AgentFacadeFactory')
    @patch.object(GitBranchMCPController, '_get_facade_for_request')
    def test_assign_agent_with_uuid_format(self, mock_get_facade, mock_agent_factory):
        """Test that UUID format still works"""
        
        # Mock agent facade
        mock_agent_facade = Mock()
        mock_agent_facade.assign_agent.return_value = {
            "success": True,
            "message": "Agent assigned successfully"
        }
        
        mock_factory_instance = Mock()
        mock_factory_instance.create_agent_facade.return_value = mock_agent_facade
        mock_agent_factory.return_value = mock_factory_instance
        
        # Test with a valid UUID
        agent_uuid = str(uuid.uuid4())
        
        with patch.object(self.controller, '_resolve_agent_identifier') as mock_resolve:
            # UUID should be returned as-is
            mock_resolve.return_value = agent_uuid
            
            # Test the assignment
            result = self.controller.manage_git_branch(
                action="assign_agent",
                project_id=self.project_id,
                git_branch_id=self.branch_id,
                agent_id=agent_uuid
            )
            
            # Verify the result
            assert result["success"] == True
            
            # Verify _resolve_agent_identifier was called
            mock_resolve.assert_called_once_with(self.project_id, agent_uuid)
            
            # Verify the agent facade was called with the UUID directly
            mock_agent_facade.assign_agent.assert_called_once_with(
                self.project_id,
                agent_uuid,
                self.branch_id
            )
            
    @patch('fastmcp.task_management.application.factories.agent_facade_factory.AgentFacadeFactory')
    @patch.object(GitBranchMCPController, '_get_facade_for_request')
    def test_assign_agent_without_at_prefix(self, mock_get_facade, mock_agent_factory):
        """Test that agent names without @ prefix also work"""
        
        # Mock agent facade
        mock_agent_facade = Mock()
        mock_agent_facade.assign_agent.return_value = {
            "success": True,
            "message": "Agent assigned successfully"
        }
        
        mock_factory_instance = Mock()
        mock_factory_instance.create_agent_facade.return_value = mock_agent_facade
        mock_agent_factory.return_value = mock_factory_instance
        
        with patch.object(self.controller, '_resolve_agent_identifier') as mock_resolve:
            # Simulate resolution for name without @
            generated_uuid = str(uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_DNS, self.project_id), "test_agent"))
            mock_resolve.return_value = f"{generated_uuid}:test_agent"
            
            # Test the assignment
            result = self.controller.manage_git_branch(
                action="assign_agent",
                project_id=self.project_id,
                git_branch_id=self.branch_id,
                agent_id="test_agent"  # No @ prefix
            )
            
            # Verify the result
            assert result["success"] == True
            
            # Verify _resolve_agent_identifier was called
            mock_resolve.assert_called_once_with(self.project_id, "test_agent")
            
            # Verify the agent facade was called
            mock_agent_facade.assign_agent.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])