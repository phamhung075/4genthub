"""
Tests for Assign Agent Use Case
"""

import pytest
from unittest.mock import Mock, patch
import logging

from fastmcp.task_management.application.use_cases.assign_agent import (
    AssignAgentUseCase,
    AssignAgentRequest,
    AssignAgentResponse
)
from fastmcp.task_management.domain.repositories.agent_repository import AgentRepository
from fastmcp.task_management.domain.exceptions import (
    AgentNotFoundError,
    ProjectNotFoundError
)


class TestAssignAgentUseCase:
    """Test the AssignAgentUseCase class"""
    
    @pytest.fixture
    def mock_agent_repository(self):
        """Create a mock agent repository"""
        return Mock(spec=AgentRepository)
    
    @pytest.fixture  
    def mock_git_branch_repository(self):
        """Create a mock git branch repository"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_agent_repository):
        """Create a use case instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.use_cases.assign_agent.RepositoryFactory') as mock_factory:
            mock_factory.get_git_branch_repository.return_value = Mock()
            return AssignAgentUseCase(agent_repository=mock_agent_repository)
    
    @pytest.fixture
    def valid_request(self):
        """Create a valid assign agent request"""
        return AssignAgentRequest(
            project_id="12345678-1234-5678-1234-567812345678",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
    
    def test_execute_successful_assignment(self, use_case, valid_request, mock_agent_repository):
        """Test successful agent assignment"""
        # Arrange
        mock_agent_repository.assign_agent_to_tree.return_value = None  # Success
        
        # Act
        result = use_case.execute(valid_request)
        
        # Assert
        assert isinstance(result, AssignAgentResponse)
        assert result.success is True
        assert result.agent_id == valid_request.agent_id
        assert result.git_branch_id == valid_request.git_branch_id
        assert "assigned to tree" in result.message
        assert result.error is None
        
        # Verify repository was called with correct parameters
        mock_agent_repository.assign_agent_to_tree.assert_called_once_with(
            valid_request.project_id,
            valid_request.agent_id,
            valid_request.git_branch_id
        )
    
    def test_execute_agent_not_found_error(self, use_case, valid_request, mock_agent_repository):
        """Test handling of AgentNotFoundError"""
        # Arrange
        error_message = "Agent agent-123 not found"
        mock_agent_repository.assign_agent_to_tree.side_effect = AgentNotFoundError(error_message)
        
        # Act
        result = use_case.execute(valid_request)
        
        # Assert
        assert isinstance(result, AssignAgentResponse)
        assert result.success is False
        assert result.agent_id == valid_request.agent_id
        assert result.git_branch_id is None
        assert result.message is None
        assert result.error == error_message
        
        # Verify repository was called
        mock_agent_repository.assign_agent_to_tree.assert_called_once()
    
    def test_execute_project_not_found_error(self, use_case, valid_request, mock_agent_repository):
        """Test handling of ProjectNotFoundError"""
        # Arrange
        error_message = "Project 12345678-1234-5678-1234-567812345678 not found"
        mock_agent_repository.assign_agent_to_tree.side_effect = ProjectNotFoundError(error_message)
        
        # Act
        result = use_case.execute(valid_request)
        
        # Assert
        assert isinstance(result, AssignAgentResponse)
        assert result.success is False
        assert result.agent_id == valid_request.agent_id
        assert result.git_branch_id is None
        assert result.message is None
        assert result.error == error_message
    
    def test_execute_unexpected_error(self, use_case, valid_request, mock_agent_repository):
        """Test handling of unexpected errors"""
        # Arrange
        unexpected_error = Exception("Database connection failed")
        mock_agent_repository.assign_agent_to_tree.side_effect = unexpected_error
        
        # Act
        result = use_case.execute(valid_request)
        
        # Assert
        assert isinstance(result, AssignAgentResponse)
        assert result.success is False
        assert result.agent_id == valid_request.agent_id
        assert result.git_branch_id is None
        assert result.message is None
        assert "Unexpected error: Database connection failed" in result.error
    
    def test_execute_with_different_request_data(self, use_case, mock_agent_repository):
        """Test execute with different valid request data"""
        # Arrange
        request = AssignAgentRequest(
            project_id="different-project-id",
            agent_id="different-agent",
            git_branch_id="different-branch"
        )
        mock_agent_repository.assign_agent_to_tree.return_value = None
        
        # Act
        result = use_case.execute(request)
        
        # Assert
        assert result.success is True
        assert result.agent_id == "different-agent"
        assert result.git_branch_id == "different-branch"
        
        # Verify correct parameters were passed
        mock_agent_repository.assign_agent_to_tree.assert_called_once_with(
            "different-project-id",
            "different-agent",
            "different-branch"
        )
    
    def test_logging_on_agent_not_found(self, use_case, valid_request, mock_agent_repository, caplog):
        """Test logging when agent is not found"""
        # Arrange
        error_message = "Agent not found"
        mock_agent_repository.assign_agent_to_tree.side_effect = AgentNotFoundError(error_message)
        
        # Act
        with caplog.at_level(logging.WARNING):
            result = use_case.execute(valid_request)
        
        # Assert
        assert result.success is False
        assert "Agent or project not found during assignment" in caplog.text
    
    def test_logging_on_unexpected_error(self, use_case, valid_request, mock_agent_repository, caplog):
        """Test logging when unexpected error occurs"""
        # Arrange
        error_message = "Database error"
        mock_agent_repository.assign_agent_to_tree.side_effect = Exception(error_message)
        
        # Act
        with caplog.at_level(logging.ERROR):
            result = use_case.execute(valid_request)
        
        # Assert
        assert result.success is False
        assert "Unexpected error in assign agent" in caplog.text
    
    def test_request_dto_creation(self):
        """Test AssignAgentRequest DTO creation"""
        # Arrange & Act
        request = AssignAgentRequest(
            project_id="proj-123",
            agent_id="agent-456",
            git_branch_id="branch-789"
        )
        
        # Assert
        assert request.project_id == "proj-123"
        assert request.agent_id == "agent-456"
        assert request.git_branch_id == "branch-789"
    
    def test_response_dto_success_creation(self):
        """Test AssignAgentResponse DTO creation for success"""
        # Arrange & Act
        response = AssignAgentResponse(
            success=True,
            agent_id="agent-123",
            git_branch_id="branch-456",
            message="Assignment successful"
        )
        
        # Assert
        assert response.success is True
        assert response.agent_id == "agent-123"
        assert response.git_branch_id == "branch-456"
        assert response.message == "Assignment successful"
        assert response.error is None
    
    def test_response_dto_error_creation(self):
        """Test AssignAgentResponse DTO creation for error"""
        # Arrange & Act
        response = AssignAgentResponse(
            success=False,
            agent_id="agent-123",
            error="Agent not found"
        )
        
        # Assert
        assert response.success is False
        assert response.agent_id == "agent-123"
        assert response.git_branch_id is None
        assert response.message is None
        assert response.error == "Agent not found"
    
    @pytest.mark.parametrize("project_id,agent_id,git_branch_id", [
        ("proj-1", "agent-1", "branch-1"),
        ("12345678-1234-5678-1234-567812345678", "agent-uuid", "branch-uuid"),
        ("", "agent", "branch"),  # Edge case: empty project_id
        ("proj", "", "branch"),   # Edge case: empty agent_id
        ("proj", "agent", ""),    # Edge case: empty branch_id
    ])
    def test_execute_with_various_input_formats(self, use_case, mock_agent_repository, 
                                               project_id, agent_id, git_branch_id):
        """Test execute with various input formats"""
        # Arrange
        request = AssignAgentRequest(
            project_id=project_id,
            agent_id=agent_id,
            git_branch_id=git_branch_id
        )
        mock_agent_repository.assign_agent_to_tree.return_value = None
        
        # Act
        result = use_case.execute(request)
        
        # Assert
        assert result.success is True
        assert result.agent_id == agent_id
        assert result.git_branch_id == git_branch_id
        
        # Verify repository was called with exact parameters
        mock_agent_repository.assign_agent_to_tree.assert_called_once_with(
            project_id, agent_id, git_branch_id
        )
    
    def test_repository_initialization_with_factory(self, mock_agent_repository):
        """Test that the use case properly initializes repositories using the factory"""
        # Arrange & Act
        with patch('fastmcp.task_management.application.use_cases.assign_agent.RepositoryFactory') as mock_factory:
            mock_git_branch_repo = Mock()
            mock_factory.get_git_branch_repository.return_value = mock_git_branch_repo
            
            use_case = AssignAgentUseCase(agent_repository=mock_agent_repository)
            
            # Assert
            mock_factory.get_git_branch_repository.assert_called_once()
            assert use_case._git_branch_repository == mock_git_branch_repo