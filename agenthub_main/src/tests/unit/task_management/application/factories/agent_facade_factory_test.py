"""
Tests for Agent Facade Factory

This module tests the AgentFacadeFactory which creates agent application facades
with proper dependency injection following DDD patterns.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.application.factories.agent_facade_factory import (
    AgentFacadeFactory,
    MockAgentApplicationFacade
)
from fastmcp.task_management.application.facades.agent_application_facade import AgentApplicationFacade
from fastmcp.task_management.infrastructure.repositories.agent_repository_factory import AgentRepositoryFactory


class TestAgentFacadeFactory:
    """Test suite for AgentFacadeFactory"""
    
    @pytest.fixture
    def mock_agent_repository_factory(self):
        """Create a mock agent repository factory"""
        factory = Mock(spec=AgentRepositoryFactory)
        return factory
    
    @pytest.fixture
    def factory(self, mock_agent_repository_factory):
        """Create an AgentFacadeFactory instance with mocked dependencies"""
        return AgentFacadeFactory(agent_repository_factory=mock_agent_repository_factory)
    
    def test_initialization(self, mock_agent_repository_factory):
        """Test factory initialization"""
        factory = AgentFacadeFactory(agent_repository_factory=mock_agent_repository_factory)
        
        assert factory._agent_repository_factory == mock_agent_repository_factory
        assert factory._facades_cache == {}
    
    def test_initialization_without_repository_factory(self):
        """Test factory initialization without repository factory"""
        factory = AgentFacadeFactory()
        
        assert factory._agent_repository_factory is None
        assert factory._facades_cache == {}
    
    def test_create_agent_facade_with_default_user(self, factory):
        """Test creating agent facade without user ID raises error"""
        # Should raise error when user_id is not provided
        with pytest.raises(ValueError) as exc_info:
            factory.create_agent_facade(project_id="test-project")
        
        assert "user_id is required" in str(exc_info.value)
    
    @patch('fastmcp.task_management.infrastructure.repositories.agent_repository_factory.AgentRepositoryFactory.create')
    def test_create_agent_facade_with_specific_user(self, mock_create_repo, factory):
        """Test creating agent facade with specific user ID"""
        # Setup mocks
        mock_repo = Mock()
        mock_create_repo.return_value = mock_repo
        
        # Create facade
        with patch('fastmcp.task_management.application.factories.agent_facade_factory.AgentApplicationFacade') as mock_facade_class:
            mock_facade = Mock(spec=AgentApplicationFacade)
            mock_facade_class.return_value = mock_facade
            
            result = factory.create_agent_facade(project_id="test-project", user_id="user-123")
            
            # Verify - should use the provided user_id directly
            mock_create_repo.assert_called_once_with(user_id="user-123")
            assert result == mock_facade
    
    def test_create_agent_facade_cached(self, factory):
        """Test returning cached facade when available"""
        # Pre-populate cache
        mock_cached_facade = Mock(spec=AgentApplicationFacade)
        factory._facades_cache["test-project"] = mock_cached_facade
        
        # Create facade
        result = factory.create_agent_facade(project_id="test-project")
        
        # Verify cached facade is returned
        assert result == mock_cached_facade
    
    @patch('fastmcp.task_management.infrastructure.repositories.agent_repository_factory.AgentRepositoryFactory.create')
    def test_create_agent_facade_without_repository_factory(self, mock_create_repo):
        """Test creating facade without repository factory (uses default)"""
        # Setup mocks
        mock_repo = Mock()
        mock_create_repo.return_value = mock_repo
        
        # Create factory without repository factory
        factory = AgentFacadeFactory()
        
        # Create facade
        with patch('fastmcp.task_management.application.factories.agent_facade_factory.AgentApplicationFacade') as mock_facade_class:
            mock_facade = Mock(spec=AgentApplicationFacade)
            mock_facade_class.return_value = mock_facade
            
            result = factory.create_agent_facade(project_id="test-project", user_id="user-123")
            
            # Verify default repository factory is used with provided user_id
            mock_create_repo.assert_called_once_with(user_id='user-123')
            mock_facade_class.assert_called_once_with(mock_repo)
            assert result == mock_facade
    
    @patch('fastmcp.task_management.infrastructure.repositories.agent_repository_factory.AgentRepositoryFactory.create')
    def test_create_agent_facade_with_exception(self, mock_create_repo, factory):
        """Test creating facade when exception occurs (falls back to mock)"""
        # Setup mocks - make repository creation fail
        mock_create_repo.side_effect = Exception("Test error")
        
        # Create facade
        with patch('fastmcp.task_management.application.factories.agent_facade_factory.logger') as mock_logger:
            result = factory.create_agent_facade(project_id="test-project", user_id="user-123")
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "Failed to create proper AgentApplicationFacade" in str(mock_logger.warning.call_args)
            
            # Verify mock facade is returned
            assert isinstance(result, MockAgentApplicationFacade)
            assert factory._facades_cache["test-project"] == result
    
    def test_clear_cache(self, factory):
        """Test clearing the facades cache"""
        # Add items to cache
        factory._facades_cache["project1"] = Mock()
        factory._facades_cache["project2"] = Mock()
        
        # Clear cache
        factory.clear_cache()
        
        # Verify cache is empty
        assert factory._facades_cache == {}
    
    def test_get_cached_facade(self, factory):
        """Test getting a cached facade"""
        # Add facade to cache
        mock_facade = Mock(spec=AgentApplicationFacade)
        factory._facades_cache["test-project"] = mock_facade
        
        # Get cached facade
        result = factory.get_cached_facade("test-project")
        
        # Verify
        assert result == mock_facade
    
    def test_get_cached_facade_not_found(self, factory):
        """Test getting cached facade when not found"""
        result = factory.get_cached_facade("non-existent-project")
        assert result is None
    
    def test_create_facade_alias(self, factory):
        """Test create_facade alias method"""
        # Pre-populate cache to avoid complex mocking
        mock_facade = Mock(spec=AgentApplicationFacade)
        factory._facades_cache["test-project"] = mock_facade
        
        # Use alias method
        result = factory.create_facade(project_id="test-project")
        
        # Verify it calls create_agent_facade
        assert result == mock_facade
    
    def test_static_create_method(self):
        """Test static create method requires user_id"""
        # Static create method should also require user_id
        with pytest.raises(ValueError) as exc_info:
            # Call static method without user_id will raise error
            factory = AgentFacadeFactory()
            factory.create_agent_facade("default_project")
        
        assert "user_id is required" in str(exc_info.value)


class TestMockAgentApplicationFacade:
    """Test the MockAgentApplicationFacade"""
    
    @pytest.fixture
    def mock_facade(self):
        """Create a MockAgentApplicationFacade instance"""
        return MockAgentApplicationFacade()
    
    def test_register_agent(self, mock_facade):
        """Test mock register_agent method"""
        result = mock_facade.register_agent(
            project_id="test-project",
            agent_id="agent-123",
            name="Test Agent",
            call_agent="@test_agent"
        )
        
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert result["agent"]["name"] == "Test Agent"
        assert result["agent"]["project_id"] == "test-project"
        assert result["agent"]["call_agent"] == "@test_agent"
        assert "registered successfully" in result["message"]
    
    def test_assign_agent(self, mock_facade):
        """Test mock assign_agent method"""
        result = mock_facade.assign_agent(
            project_id="test-project",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
        
        assert result["success"] is True
        assert result["agent_id"] == "agent-123"
        assert result["git_branch_id"] == "branch-456"
        assert "assigned to" in result["message"]
    
    def test_unassign_agent(self, mock_facade):
        """Test mock unassign_agent method"""
        result = mock_facade.unassign_agent(
            project_id="test-project",
            agent_id="agent-123",
            git_branch_id="branch-456"
        )
        
        assert result["success"] is True
        assert result["agent_id"] == "agent-123"
        assert result["git_branch_id"] == "branch-456"
        assert "unassigned from" in result["message"]
    
    def test_get_agent(self, mock_facade):
        """Test mock get_agent method"""
        result = mock_facade.get_agent(
            project_id="test-project",
            agent_id="agent-123"
        )
        
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert "Mock Agent" in result["agent"]["name"]
        assert result["agent"]["project_id"] == "test-project"
        assert "retrieved successfully" in result["message"]
    
    def test_list_agents(self, mock_facade):
        """Test mock list_agents method"""
        result = mock_facade.list_agents(project_id="test-project")
        
        assert result["success"] is True
        assert len(result["agents"]) == 2
        assert result["agents"][0]["id"] == "mock-agent-1"
        assert result["agents"][1]["id"] == "mock-agent-2"
        assert all(agent["project_id"] == "test-project" for agent in result["agents"])
        assert "Listed agents" in result["message"]
    
    def test_update_agent(self, mock_facade):
        """Test mock update_agent method"""
        result = mock_facade.update_agent(
            project_id="test-project",
            agent_id="agent-123",
            name="Updated Agent",
            call_agent="@updated_agent"
        )
        
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert result["agent"]["name"] == "Updated Agent"
        assert result["agent"]["call_agent"] == "@updated_agent"
        assert "updated successfully" in result["message"]
    
    def test_update_agent_partial(self, mock_facade):
        """Test mock update_agent with partial updates"""
        result = mock_facade.update_agent(
            project_id="test-project",
            agent_id="agent-123"
        )
        
        assert result["success"] is True
        assert result["agent"]["id"] == "agent-123"
        assert "Mock Agent" in result["agent"]["name"]
        assert result["agent"]["call_agent"] is None
    
    def test_unregister_agent(self, mock_facade):
        """Test mock unregister_agent method"""
        result = mock_facade.unregister_agent(
            project_id="test-project",
            agent_id="agent-123"
        )
        
        assert result["success"] is True
        assert result["agent_id"] == "agent-123"
        assert "unregistered successfully" in result["message"]
    
    def test_rebalance_agents(self, mock_facade):
        """Test mock rebalance_agents method"""
        result = mock_facade.rebalance_agents(project_id="test-project")
        
        assert result["success"] is True
        assert result["project_id"] == "test-project"
        assert "Agents rebalanced" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])