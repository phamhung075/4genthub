"""Comprehensive test suite for Agent Application Facade"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from dataclasses import asdict

from fastmcp.task_management.application.facades.agent_application_facade import AgentApplicationFacade
from fastmcp.task_management.domain.repositories.agent_repository import AgentRepository
from fastmcp.task_management.domain.exceptions.task_exceptions import AgentNotFoundError, ProjectNotFoundError
from fastmcp.task_management.application.use_cases.register_agent import RegisterAgentResponse
from fastmcp.task_management.application.use_cases.unregister_agent import UnregisterAgentResponse
from fastmcp.task_management.application.use_cases.assign_agent import AssignAgentResponse
from fastmcp.task_management.application.use_cases.unassign_agent import UnassignAgentResponse
from fastmcp.task_management.application.use_cases.get_agent import GetAgentResponse
from fastmcp.task_management.application.use_cases.list_agents import ListAgentsResponse
from fastmcp.task_management.domain.entities.agent import Agent


class TestAgentApplicationFacade:
    """Test suite for AgentApplicationFacade"""
    
    # Use a constant UUID for all tests
    AGENT_ID = "550e8400-e29b-41d4-a716-446655440000"
    AGENT_ID_2 = "550e8400-e29b-41d4-a716-446655440002"
    PROJECT_ID = "550e8400-e29b-41d4-a716-446655440001"
    
    @pytest.fixture
    def mock_agent_repository(self):
        """Create a mock agent repository"""
        return Mock(spec=AgentRepository)
    
    @pytest.fixture
    def facade(self, mock_agent_repository):
        """Create an AgentApplicationFacade instance"""
        return AgentApplicationFacade(mock_agent_repository)
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent for testing"""
        agent = Agent(
            id=self.AGENT_ID,
            name="test_agent",
            description="Test agent for testing purposes"
        )
        # Assign to project using the proper method
        agent.assigned_projects.add(self.PROJECT_ID)
        return agent
    
    def test_init(self, mock_agent_repository):
        """Test facade initialization"""
        facade = AgentApplicationFacade(mock_agent_repository)
        assert facade._agent_repository == mock_agent_repository
        assert hasattr(facade, '_register_agent_use_case')
        assert hasattr(facade, '_unregister_agent_use_case')
        assert hasattr(facade, '_assign_agent_use_case')
        assert hasattr(facade, '_unassign_agent_use_case')
        assert hasattr(facade, '_get_agent_use_case')
        assert hasattr(facade, '_list_agents_use_case')
    
    def test_register_agent_success(self, facade, sample_agent):
        """Test successful agent registration"""
        # Mock the use case response
        mock_response = RegisterAgentResponse(
            success=True,
            agent=sample_agent,
            message="Agent registered successfully"
        )
        facade._register_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call register_agent
        result = facade.register_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="test_agent"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "register"
        assert result["agent"]["id"] == self.AGENT_ID
        assert result["agent"]["name"] == "test_agent"
        assert "hint" in result
        assert "successfully registered" in result["hint"]
    
    def test_register_agent_duplicate_error(self, facade):
        """Test agent registration with duplicate error"""
        # Mock the use case response
        mock_response = RegisterAgentResponse(
            success=False,
            agent=None,
            error="Agent already exists with this ID"
        )
        facade._register_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call register_agent
        result = facade.register_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="test_agent"
        )
        
        # Verify error response
        assert result["success"] is False
        assert result["error_code"] == "DUPLICATE_AGENT"
        assert "hint" in result
        assert "suggested_actions" in result
        assert len(result["suggested_actions"]) > 0
    
    def test_register_agent_project_not_found(self, facade):
        """Test agent registration when project doesn't exist"""
        # Mock the use case response
        mock_response = RegisterAgentResponse(
            success=False,
            agent=None,
            error="Project does not exist"
        )
        facade._register_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call register_agent with a valid UUID format that doesn't exist
        nonexistent_project_id = "550e8400-e29b-41d4-a716-446655440999"
        result = facade.register_agent(
            project_id=nonexistent_project_id,
            agent_id=self.AGENT_ID,
            name="test_agent"
        )
        
        # Verify error response
        assert result["success"] is False
        assert result["error_code"] == "PROJECT_NOT_FOUND"
        assert "hint" in result
        assert "create the project first" in result["hint"]
    
    def test_register_agent_validation_error(self, facade):
        """Test agent registration with validation error"""
        # Mock the use case to raise ValueError
        facade._register_agent_use_case.execute = Mock(
            side_effect=ValueError("Agent name already exists")
        )
        
        # Call register_agent
        result = facade.register_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="existing_agent"
        )
        
        # Verify error response
        assert result["success"] is False
        assert result["error_code"] == "DUPLICATE_AGENT"
        assert "hint" in result
        assert "suggested_actions" in result
    
    def test_register_agent_missing_field_error(self, facade):
        """Test agent registration with missing required field"""
        # Mock the use case to raise ValueError
        facade._register_agent_use_case.execute = Mock(
            side_effect=ValueError("Missing required field: name")
        )
        
        # Call register_agent
        result = facade.register_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify error response
        assert result["success"] is False
        assert result["error_code"] == "MISSING_FIELD"
        assert "hint" in result
        assert "required fields" in result["hint"]
    
    def test_register_agent_unexpected_error(self, facade):
        """Test agent registration with unexpected error"""
        # Mock the use case to raise unexpected exception
        facade._register_agent_use_case.execute = Mock(
            side_effect=Exception("Unexpected database error")
        )
        
        # Call register_agent
        result = facade.register_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="test_agent"
        )
        
        # Verify error response
        assert result["success"] is False
        assert result["error_code"] == "INTERNAL_ERROR"
        assert "Unexpected error" in result["error"]
        assert "hint" in result
    
    def test_unregister_agent_success(self, facade):
        """Test successful agent unregistration"""
        # Mock the use case response
        mock_response = UnregisterAgentResponse(
            success=True,
            agent_id=self.AGENT_ID,
            agent_data={"name": "test_agent"},
            removed_assignments=["branch-1", "branch-2"],
            message="Agent unregistered successfully"
        )
        facade._unregister_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call unregister_agent
        result = facade.unregister_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "unregister"
        assert result["agent_id"] == self.AGENT_ID
        assert result["removed_assignments"] == ["branch-1", "branch-2"]
    
    def test_unregister_agent_failure(self, facade):
        """Test failed agent unregistration"""
        # Mock the use case response
        mock_response = UnregisterAgentResponse(
            success=False,
            agent_id=self.AGENT_ID,
            error="Agent not found"
        )
        facade._unregister_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call unregister_agent
        result = facade.unregister_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "unregister"
        assert result["error"] == "Agent not found"
    
    def test_unregister_agent_exception(self, facade):
        """Test agent unregistration with exception"""
        # Mock the use case to raise exception
        facade._unregister_agent_use_case.execute = Mock(
            side_effect=Exception("Database connection lost")
        )
        
        # Call unregister_agent
        result = facade.unregister_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "unregister"
        assert "Unexpected error" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.agent_application_facade.datetime')
    def test_assign_agent_success(self, mock_datetime, facade):
        """Test successful agent assignment"""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock the use case response
        mock_response = AssignAgentResponse(
            success=True,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456",
            message="Agent assigned successfully"
        )
        facade._assign_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call assign_agent
        result = facade.assign_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "assign"
        assert result["agent_id"] == self.AGENT_ID
        assert result["git_branch_id"] == "branch-456"
        assert result["metadata"]["project_id"] == self.PROJECT_ID
        assert result["metadata"]["timestamp"] == mock_now.isoformat()
    
    def test_assign_agent_failure(self, facade):
        """Test failed agent assignment"""
        # Mock the use case response
        mock_response = AssignAgentResponse(
            success=False,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456",
            error="Branch not found"
        )
        facade._assign_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call assign_agent
        result = facade.assign_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "assign"
        assert result["error"] == "Branch not found"
        assert result["metadata"]["agent_id"] == self.AGENT_ID
        assert result["metadata"]["git_branch_id"] == "branch-456"
    
    def test_assign_agent_exception(self, facade):
        """Test agent assignment with exception"""
        # Mock the use case to raise exception
        facade._assign_agent_use_case.execute = Mock(
            side_effect=Exception("Network timeout")
        )
        
        # Call assign_agent
        result = facade.assign_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "assign"
        assert "Unexpected error" in result["error"]
        assert result["metadata"]["project_id"] == self.PROJECT_ID
    
    def test_unassign_agent_success(self, facade):
        """Test successful agent unassignment"""
        # Mock the use case response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "success": True,
            "message": "Agent unassigned successfully"
        }
        facade._unassign_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call unassign_agent
        result = facade.unassign_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["message"] == "Agent unassigned successfully"
    
    def test_unassign_agent_exception(self, facade):
        """Test agent unassignment with exception"""
        # Mock the use case to raise exception
        facade._unassign_agent_use_case.execute = Mock(
            side_effect=Exception("Permission denied")
        )
        
        # Call unassign_agent
        result = facade.unassign_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            git_branch_id="branch-456"
        )
        
        # Verify result
        assert result["success"] is False
        assert "Permission denied" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.agent_application_facade.datetime')
    def test_get_agent_success(self, mock_datetime, facade, sample_agent):
        """Test successful agent retrieval"""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock the use case response
        mock_response = GetAgentResponse(
            success=True,
            agent=sample_agent,
            workload_status={"tasks": 5, "completed": 3}
        )
        facade._get_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call get_agent
        result = facade.get_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "get"
        assert result["agent"]["id"] == self.AGENT_ID
        assert result["workload_status"]["tasks"] == 5
        assert result["metadata"]["timestamp"] == mock_now.isoformat()
    
    def test_get_agent_not_found(self, facade):
        """Test agent retrieval when agent not found"""
        # Mock the use case response
        mock_response = GetAgentResponse(
            success=False,
            agent=None,
            error="Agent not found"
        )
        facade._get_agent_use_case.execute = Mock(return_value=mock_response)
        
        # Call get_agent
        result = facade.get_agent(
            project_id=self.PROJECT_ID,
            agent_id="nonexistent-agent"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "get"
        assert result["error"] == "Agent not found"
        assert result["metadata"]["agent_id"] == "nonexistent-agent"
    
    def test_get_agent_exception(self, facade):
        """Test agent retrieval with exception"""
        # Mock the use case to raise exception
        facade._get_agent_use_case.execute = Mock(
            side_effect=Exception("Cache error")
        )
        
        # Call get_agent
        result = facade.get_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "get"
        assert "Unexpected error" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.agent_application_facade.datetime')
    def test_list_agents_success(self, mock_datetime, facade, sample_agent):
        """Test successful agent listing"""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Create multiple agents
        agent2 = Agent(
            id=self.AGENT_ID_2,
            name="test_agent_2",
            description="Second test agent for testing purposes"
        )
        # Assign to project using the proper method
        agent2.assigned_projects.add(self.PROJECT_ID)
        
        # Mock the use case response
        mock_response = ListAgentsResponse(
            success=True,
            agents=[sample_agent, agent2]
        )
        facade._list_agents_use_case.execute = Mock(return_value=mock_response)
        
        # Call list_agents
        result = facade.list_agents(project_id=self.PROJECT_ID)
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "list"
        assert len(result["agents"]) == 2
        assert result["agents"][0]["id"] == self.AGENT_ID
        assert result["agents"][1]["id"] == self.AGENT_ID_2
        assert result["metadata"]["count"] == 2
        assert result["metadata"]["timestamp"] == mock_now.isoformat()
    
    def test_list_agents_empty(self, facade):
        """Test agent listing with no agents"""
        # Mock the use case response
        mock_response = ListAgentsResponse(
            success=True,
            agents=[]
        )
        facade._list_agents_use_case.execute = Mock(return_value=mock_response)
        
        # Call list_agents
        result = facade.list_agents(project_id=self.PROJECT_ID)
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "list"
        assert len(result["agents"]) == 0
        assert result["metadata"]["count"] == 0
    
    def test_list_agents_failure(self, facade):
        """Test failed agent listing"""
        # Mock the use case response
        mock_response = ListAgentsResponse(
            success=False,
            agents=[],
            error="Project not found"
        )
        facade._list_agents_use_case.execute = Mock(return_value=mock_response)
        
        # Call list_agents
        result = facade.list_agents(project_id="nonexistent-project")
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "list"
        assert result["error"] == "Project not found"
    
    def test_list_agents_exception(self, facade):
        """Test agent listing with exception"""
        # Mock the use case to raise exception
        facade._list_agents_use_case.execute = Mock(
            side_effect=Exception("Query timeout")
        )
        
        # Call list_agents
        result = facade.list_agents(project_id=self.PROJECT_ID)
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "list"
        assert "Unexpected error" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.agent_application_facade.datetime')
    def test_update_agent_success(self, mock_datetime, facade):
        """Test successful agent update"""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock repository response
        updated_agent = {
            "id": self.AGENT_ID,
            "name": "updated_agent",
            "call_agent": "updated_call_agent"
        }
        facade._agent_repository.update_agent = Mock(return_value=updated_agent)
        
        # Call update_agent
        result = facade.update_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="updated_agent",
            call_agent="updated_call_agent"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "update"
        assert result["agent"]["name"] == "updated_agent"
        assert result["message"] == f"Agent {self.AGENT_ID} updated successfully"
        assert result["metadata"]["timestamp"] == mock_now.isoformat()
    
    def test_update_agent_not_found(self, facade):
        """Test agent update when agent not found"""
        # Mock repository to raise AgentNotFoundError
        facade._agent_repository.update_agent = Mock(
            side_effect=AgentNotFoundError("Agent not found")
        )
        
        # Call update_agent
        result = facade.update_agent(
            project_id=self.PROJECT_ID,
            agent_id="nonexistent-agent",
            name="updated_agent"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "update"
        assert "Agent not found" in result["error"]
    
    def test_update_agent_project_not_found(self, facade):
        """Test agent update when project not found"""
        # Mock repository to raise ProjectNotFoundError
        facade._agent_repository.update_agent = Mock(
            side_effect=ProjectNotFoundError("Project not found")
        )
        
        # Call update_agent
        result = facade.update_agent(
            project_id="nonexistent-project",
            agent_id=self.AGENT_ID,
            name="updated_agent"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "update"
        assert "Project not found" in result["error"]
    
    def test_update_agent_exception(self, facade):
        """Test agent update with exception"""
        # Mock repository to raise exception
        facade._agent_repository.update_agent = Mock(
            side_effect=Exception("Concurrency conflict")
        )
        
        # Call update_agent
        result = facade.update_agent(
            project_id=self.PROJECT_ID,
            agent_id=self.AGENT_ID,
            name="updated_agent"
        )
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "update"
        assert "Unexpected error" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.agent_application_facade.datetime')
    def test_rebalance_agents_success(self, mock_datetime, facade):
        """Test successful agent rebalancing"""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock repository response
        rebalance_result = {
            "rebalance_result": {
                "agents_reassigned": 3,
                "branches_affected": 5
            }
        }
        facade._agent_repository.rebalance_agents = Mock(return_value=rebalance_result)
        
        # Call rebalance_agents
        result = facade.rebalance_agents(project_id=self.PROJECT_ID)
        
        # Verify result
        assert result["success"] is True
        assert result["action"] == "rebalance"
        assert result["rebalance_result"]["agents_reassigned"] == 3
        assert result["message"] == f"Agent rebalancing completed for project {self.PROJECT_ID}"
        assert result["metadata"]["timestamp"] == mock_now.isoformat()
    
    def test_rebalance_agents_project_not_found(self, facade):
        """Test agent rebalancing when project not found"""
        # Mock repository to raise ProjectNotFoundError
        facade._agent_repository.rebalance_agents = Mock(
            side_effect=ProjectNotFoundError("Project not found")
        )
        
        # Call rebalance_agents
        result = facade.rebalance_agents(project_id="nonexistent-project")
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "rebalance"
        assert "Project not found" in result["error"]
    
    def test_rebalance_agents_exception(self, facade):
        """Test agent rebalancing with exception"""
        # Mock repository to raise exception
        facade._agent_repository.rebalance_agents = Mock(
            side_effect=Exception("Lock acquisition failed")
        )
        
        # Call rebalance_agents
        result = facade.rebalance_agents(project_id=self.PROJECT_ID)
        
        # Verify result
        assert result["success"] is False
        assert result["action"] == "rebalance"
        assert "Unexpected error" in result["error"]