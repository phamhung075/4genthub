"""
Tests for ORM Agent Repository

This module contains comprehensive tests for the ORM-based agent repository
implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository
from fastmcp.task_management.infrastructure.database.models import Agent
from fastmcp.task_management.domain.entities.agent import Agent as AgentEntity, AgentStatus, AgentCapability
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)


class TestORMAgentRepository:
    
    def setup_method(self, method):
        """Set up test fixtures"""
        # Unit tests should not access the database
        # All database interactions will be mocked
        pass

    """Test suite for ORM Agent Repository"""
    
    @pytest.fixture
    def mock_agent_model(self):
        """Create a mock agent model"""
        agent = Mock(spec=Agent)
        agent.id = "test_agent_1"
        agent.name = "Test Agent"
        agent.description = "Test agent description"
        agent.capabilities = ["frontend_development", "testing"]
        agent.status = "available"
        agent.availability_score = 1.0
        agent.last_active_at = datetime.now()
        agent.created_at = datetime.now()
        agent.updated_at = datetime.now()
        agent.model_metadata = {
            "assigned_trees": ["main", "feature-branch"],
            "call_agent": "@test_agent"
        }
        return agent
    
    @pytest.fixture
    def agent_repository(self):
        """Create an ORM agent repository instance"""
        # Mock the database configuration to prevent actual database access
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config'):
            with patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.get_session'):
                return ORMAgentRepository(project_id="test_project", user_id="test_user")
    
    def test_init(self, agent_repository):
        """Test repository initialization"""
        import uuid
        assert agent_repository.project_id == "test_project"
        # The user_id gets converted to UUID format for database consistency
        expected_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test_user"))
        assert agent_repository.user_id == expected_user_id
        assert agent_repository.model_class == Agent
    
    def test_model_to_entity(self, agent_repository, mock_agent_model):
        """Test converting model to entity"""
        entity = agent_repository._model_to_entity(mock_agent_model)
        
        assert isinstance(entity, AgentEntity)
        assert entity.id == "test_agent_1"
        assert entity.name == "Test Agent"
        assert entity.description == "Test agent description"
        assert entity.status == AgentStatus.AVAILABLE
        assert AgentCapability.FRONTEND_DEVELOPMENT in entity.capabilities
        assert AgentCapability.TESTING in entity.capabilities
    
    def test_entity_to_model_dict(self, agent_repository):
        """Test converting entity to model dictionary"""
        entity = AgentEntity(
            id="test_agent_1",
            name="Test Agent",
            description="Test description",
            capabilities={AgentCapability.FRONTEND_DEVELOPMENT, AgentCapability.TESTING},
            status=AgentStatus.AVAILABLE
        )
        
        model_dict = agent_repository._entity_to_model_dict(entity)
        
        assert model_dict["id"] == "test_agent_1"
        assert model_dict["name"] == "Test Agent"
        assert model_dict["description"] == "Test description"
        assert model_dict["status"] == "available"
        assert "frontend_development" in model_dict["capabilities"]
        assert "testing" in model_dict["capabilities"]
        assert model_dict["availability_score"] == 1.0
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.find_by_name')
    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.BaseORMRepository.exists')
    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.BaseORMRepository.create')
    def test_register_agent_success(self, mock_create, mock_exists, mock_find_by_name, agent_repository, mock_agent_model):
        """Test successful agent registration"""
        mock_exists.return_value = False
        mock_find_by_name.return_value = None  # No existing agent with same name
        mock_create.return_value = mock_agent_model
        
        result = agent_repository.register_agent(
            project_id="test_project",
            agent_id="test_agent_1",
            name="Test Agent",
            call_agent="@test_agent"
        )
        
        assert result["id"] == "test_agent_1"
        assert result["name"] == "Test Agent"
        assert result["status"] == "available"
        mock_exists.assert_called_once_with(id="test_agent_1")
        mock_create.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.base_orm_repository.BaseORMRepository.exists')
    def test_register_agent_already_exists(self, mock_exists, agent_repository):
        """Test agent registration when agent already exists"""
        mock_exists.return_value = True
        
        with pytest.raises(ValidationException) as exc_info:
            agent_repository.register_agent(
                project_id="test_project",
                agent_id="test_agent_1",
                name="Test Agent"
            )
        
        assert "already exists" in str(exc_info.value)
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    def test_get_agent_success(self, mock_get_by_id, agent_repository, mock_agent_model):
        """Test successful agent retrieval"""
        mock_get_by_id.return_value = mock_agent_model
        
        result = agent_repository.get_agent(
            project_id="test_project",
            agent_id="test_agent_1"
        )
        
        assert result["id"] == "test_agent_1"
        assert result["name"] == "Test Agent"
        assert result["assignments"] == ["main", "feature-branch"]
        mock_get_by_id.assert_called_once_with("test_agent_1")
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    def test_get_agent_not_found(self, mock_get_by_id, agent_repository):
        """Test agent retrieval when agent not found"""
        mock_get_by_id.return_value = None
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            agent_repository.get_agent(
                project_id="test_project",
                agent_id="nonexistent_agent"
            )
        
        assert "not found" in str(exc_info.value)
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.delete')
    def test_unregister_agent_success(self, mock_delete, mock_get_by_id, agent_repository, mock_agent_model):
        """Test successful agent unregistration"""
        mock_get_by_id.return_value = mock_agent_model
        mock_delete.return_value = True
        
        result = agent_repository.unregister_agent(
            project_id="test_project",
            agent_id="test_agent_1"
        )
        
        assert result["agent_data"]["id"] == "test_agent_1"
        assert result["agent_data"]["name"] == "Test Agent"
        assert "removed_assignments" in result
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_delete.assert_called_once_with("test_agent_1")
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.update')
    def test_assign_agent_to_tree_success(self, mock_update, mock_get_by_id, agent_repository, mock_agent_model):
        """Test successful agent assignment to tree"""
        mock_agent_model.model_metadata = {"assigned_trees": ["main"]}
        mock_get_by_id.return_value = mock_agent_model
        mock_update.return_value = mock_agent_model
        
        result = agent_repository.assign_agent_to_tree(
            project_id="test_project",
            agent_id="test_agent_1",
            git_branch_id="feature-branch"
        )
        
        assert result["success"] is True
        assert "assigned to tree" in result["message"]
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_update.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.update')
    def test_assign_agent_to_tree_already_assigned(self, mock_update, mock_get_by_id, agent_repository, mock_agent_model):
        """Test agent assignment when already assigned to tree"""
        mock_agent_model.model_metadata = {"assigned_trees": ["main", "feature-branch"]}
        mock_get_by_id.return_value = mock_agent_model
        
        result = agent_repository.assign_agent_to_tree(
            project_id="test_project",
            agent_id="test_agent_1",
            git_branch_id="feature-branch"
        )
        
        assert result["success"] is True
        assert "already assigned" in result["message"]
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_update.assert_not_called()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.update')
    def test_unassign_agent_from_tree_success(self, mock_update, mock_get_by_id, agent_repository, mock_agent_model):
        """Test successful agent unassignment from tree"""
        mock_agent_model.model_metadata = {"assigned_trees": ["main", "feature-branch"]}
        mock_get_by_id.return_value = mock_agent_model
        mock_update.return_value = mock_agent_model
        
        result = agent_repository.unassign_agent_from_tree(
            project_id="test_project",
            agent_id="test_agent_1",
            git_branch_id="feature-branch"
        )
        
        assert result["removed_assignments"] == ["feature-branch"]
        assert result["remaining_assignments"] == ["main"]
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_update.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.update')
    def test_unassign_agent_from_all_trees(self, mock_update, mock_get_by_id, agent_repository, mock_agent_model):
        """Test agent unassignment from all trees"""
        mock_agent_model.model_metadata = {"assigned_trees": ["main", "feature-branch"]}
        mock_get_by_id.return_value = mock_agent_model
        mock_update.return_value = mock_agent_model
        
        result = agent_repository.unassign_agent_from_tree(
            project_id="test_project",
            agent_id="test_agent_1",
            git_branch_id=None
        )
        
        assert set(result["removed_assignments"]) == {"main", "feature-branch"}
        assert result["remaining_assignments"] == []
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_update.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_all')
    def test_list_agents_success(self, mock_get_all, agent_repository, mock_agent_model):
        """Test successful agent listing"""
        mock_get_all.return_value = [mock_agent_model]
        
        result = agent_repository.list_agents(project_id="test_project")
        
        assert result["total_agents"] == 1
        assert len(result["agents"]) == 1
        assert result["agents"][0]["id"] == "test_agent_1"
        assert result["agents"][0]["name"] == "Test Agent"
        mock_get_all.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.update')
    def test_update_agent_success(self, mock_update, mock_get_by_id, agent_repository, mock_agent_model):
        """Test successful agent update"""
        mock_get_by_id.return_value = mock_agent_model
        mock_agent_model.name = "Updated Agent"
        mock_update.return_value = mock_agent_model
        
        result = agent_repository.update_agent(
            project_id="test_project",
            agent_id="test_agent_1",
            name="Updated Agent",
            call_agent="@updated_agent"
        )
        
        assert result["id"] == "test_agent_1"
        assert result["name"] == "Updated Agent"
        mock_get_by_id.assert_called_once_with("test_agent_1")
        mock_update.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_all')
    def test_rebalance_agents_success(self, mock_get_all, agent_repository, mock_agent_model):
        """Test successful agent rebalancing"""
        mock_get_all.return_value = [mock_agent_model]
        
        result = agent_repository.rebalance_agents(project_id="test_project")
        
        assert "rebalance_result" in result
        assert result["rebalance_result"]["changes_made"] is True
        assert len(result["rebalance_result"]["changes"]) > 0
        mock_get_all.assert_called_once()
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.find_by')
    def test_get_available_agents_success(self, mock_find_by, agent_repository, mock_agent_model):
        """Test getting available agents"""
        mock_find_by.return_value = [mock_agent_model]
        
        result = agent_repository.get_available_agents(project_id="test_project")
        
        assert len(result) == 1
        assert result[0]["id"] == "test_agent_1"
        assert result[0]["status"] == "available"
        mock_find_by.assert_called_once_with(status="available")
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_db_session')
    def test_search_agents_success(self, mock_get_db_session, agent_repository, mock_agent_model):
        """Test searching agents"""
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = [mock_agent_model]
        
        result = agent_repository.search_agents(
            project_id="test_project",
            query="test"
        )
        
        assert len(result) == 1
        assert result[0]["id"] == "test_agent_1"
        assert result[0]["name"] == "Test Agent"
        mock_get_db_session.assert_called_once()
    
    def test_model_to_entity_with_invalid_capability(self, agent_repository):
        """Test model to entity conversion with invalid capability"""
        mock_agent = Mock(spec=Agent)
        mock_agent.id = "test_agent_1"
        mock_agent.name = "Test Agent"
        mock_agent.description = "Test description"
        mock_agent.capabilities = ["invalid_capability", "testing"]
        mock_agent.status = "available"
        mock_agent.created_at = datetime.now()
        mock_agent.updated_at = datetime.now()
        mock_agent.model_metadata = {}
        
        entity = agent_repository._model_to_entity(mock_agent)
        
        # Should only have valid capabilities
        assert AgentCapability.TESTING in entity.capabilities
        assert len(entity.capabilities) == 1
    
    def test_model_to_entity_with_invalid_status(self, agent_repository):
        """Test model to entity conversion with invalid status"""
        mock_agent = Mock(spec=Agent)
        mock_agent.id = "test_agent_1"
        mock_agent.name = "Test Agent"
        mock_agent.description = "Test description"
        mock_agent.capabilities = []
        mock_agent.status = "invalid_status"
        mock_agent.created_at = datetime.now()
        mock_agent.updated_at = datetime.now()
        mock_agent.model_metadata = {}
        
        entity = agent_repository._model_to_entity(mock_agent)
        
        # Should default to AVAILABLE for invalid status
        assert entity.status == AgentStatus.AVAILABLE
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.exists')
    def test_register_agent_database_error(self, mock_exists, agent_repository):
        """Test agent registration with database error"""
        mock_exists.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            agent_repository.register_agent(
                project_id="test_project",
                agent_id="test_agent_1",
                name="Test Agent"
            )
        
        assert "Failed to register agent" in str(exc_info.value)
    
    @patch('fastmcp.task_management.infrastructure.repositories.orm.agent_repository.ORMAgentRepository.get_by_id')
    @pytest.mark.skip(reason="Incompatible with PostgreSQL")

    def test_assign_agent_to_tree_agent_not_found(self, mock_get_by_id, agent_repository):
        """Test agent assignment when agent not found"""
        mock_get_by_id.return_value = None
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            agent_repository.assign_agent_to_tree(
                project_id="test_project",
                agent_id="nonexistent_agent",
                git_branch_id="main"
            )
        
        assert "not found" in str(exc_info.value)
        assert "nonexistent_agent" in str(exc_info.value)