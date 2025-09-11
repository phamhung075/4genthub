"""
Comprehensive test suite for AgentAPIController.

Tests the agent API controller including:
- Agent metadata retrieval
- Single agent lookup
- Category-based filtering
- Category listing
- Error handling and fallback mechanisms
- Static metadata fallback
- Authentication context handling
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from fastmcp.task_management.interface.api_controllers.agent_api_controller import AgentAPIController
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.agent_application_facade import AgentApplicationFacade


class TestAgentAPIController:
    """Test cases for AgentAPIController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock facade service
        self.mock_facade_service = Mock(spec=FacadeService)
        self.mock_facade = Mock()  # Don't specify spec since methods may not exist yet
        self.mock_facade_service.get_agent_facade.return_value = self.mock_facade
        
        # Mock session
        self.mock_session = Mock()
        
        # Test user ID
        self.test_user_id = "test-user-123"
        
        # Create controller with mocked facade service
        with patch.object(FacadeService, 'get_instance', return_value=self.mock_facade_service):
            self.controller = AgentAPIController()
    
    def test_init(self):
        """Test controller initialization."""
        with patch.object(FacadeService, 'get_instance') as mock_get_instance:
            mock_get_instance.return_value = self.mock_facade_service
            
            controller = AgentAPIController()
            
            assert controller.facade_service == self.mock_facade_service
            mock_get_instance.assert_called_once()
    
    # ===== get_agent_metadata tests =====
    
    def test_get_agent_metadata_success(self):
        """Test successful retrieval of agent metadata."""
        # Mock successful facade response
        mock_agents = [
            {
                "id": "@coding_agent",
                "name": "Coding Agent",
                "category": "development",
                "description": "Handles code implementation"
            },
            {
                "id": "@test_agent",
                "name": "Test Agent",
                "category": "quality",
                "description": "Handles testing"
            }
        ]
        
        self.mock_facade.list_all_agents.return_value = {
            "success": True,
            "agents": mock_agents
        }
        
        # Call the method
        result = self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
        
        # Verify the result
        assert result["success"] is True
        assert result["agents"] == mock_agents
        assert result["total"] == 2
        assert result["source"] == "facade"
        
        # Verify facade was called correctly
        self.mock_facade_service.get_agent_facade.assert_called_once_with(
            project_id=None,
            user_id=self.test_user_id
        )
        self.mock_facade.list_all_agents.assert_called_once()
    
    def test_get_agent_metadata_facade_failure_returns_static(self):
        """Test fallback to static metadata when facade fails."""
        # Mock facade failure
        self.mock_facade.list_all_agents.return_value = {
            "success": False,
            "error": "Database connection failed"
        }
        
        # Call the method
        result = self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
        
        # Verify static fallback
        assert result["success"] is True
        assert result["source"] == "static"
        assert len(result["agents"]) > 0  # Should have static agents
        assert result["total"] == len(result["agents"])
        
        # Verify static agents have expected structure
        for agent in result["agents"]:
            assert "id" in agent
            assert "name" in agent
            assert "category" in agent
            assert "description" in agent
    
    def test_get_agent_metadata_exception_returns_fallback(self):
        """Test fallback to static metadata when exception occurs."""
        # Mock exception
        self.mock_facade.list_all_agents.side_effect = Exception("Unexpected error")
        
        # Call the method
        result = self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
        
        # Verify fallback with error info
        assert result["success"] is True
        assert result["source"] == "fallback"
        assert result["error"] == "Unexpected error"
        assert len(result["agents"]) > 0  # Should have static agents
        assert result["total"] == len(result["agents"])
    
    # ===== get_agent_by_id tests =====
    
    def test_get_agent_by_id_success(self):
        """Test successful retrieval of a specific agent."""
        agent_id = "@coding_agent"
        mock_agent = {
            "id": agent_id,
            "name": "Coding Agent",
            "category": "development",
            "description": "Handles code implementation"
        }
        
        self.mock_facade.get_agent.return_value = {
            "success": True,
            "agent": mock_agent
        }
        
        # Call the method
        result = self.controller.get_agent_by_id(agent_id, self.test_user_id, self.mock_session)
        
        # Verify the result
        assert result["success"] is True
        assert result["agent"] == mock_agent
        assert result["source"] == "facade"
        
        # Verify facade was called correctly
        self.mock_facade_service.get_agent_facade.assert_called_once_with(
            project_id=None,
            user_id=self.test_user_id
        )
        self.mock_facade.get_agent.assert_called_once_with(agent_id)
    
    def test_get_agent_by_id_not_found_tries_static(self):
        """Test fallback to static metadata when agent not found in facade."""
        agent_id = "@master_orchestrator_agent"
        
        # Mock facade not found response
        self.mock_facade.get_agent.return_value = {
            "success": False,
            "error": f"Agent '{agent_id}' not found"
        }
        
        # Call the method
        result = self.controller.get_agent_by_id(agent_id, self.test_user_id, self.mock_session)
        
        # Should find it in static metadata
        assert result["success"] is True
        assert result["agent"]["id"] == agent_id
        assert result["source"] == "static"
    
    def test_get_agent_by_id_not_found_anywhere(self):
        """Test when agent not found in facade or static metadata."""
        agent_id = "@non_existent_agent"
        
        # Mock facade not found response
        self.mock_facade.get_agent.return_value = {
            "success": False,
            "error": f"Agent '{agent_id}' not found"
        }
        
        # Call the method
        result = self.controller.get_agent_by_id(agent_id, self.test_user_id, self.mock_session)
        
        # Should return not found
        assert result["success"] is False
        assert result["error"] == f"Agent '{agent_id}' not found"
        assert result["agent"] is None
    
    def test_get_agent_by_id_exception_tries_static_fallback(self):
        """Test fallback to static metadata when exception occurs."""
        agent_id = "@debugger_agent"
        
        # Mock exception
        self.mock_facade.get_agent.side_effect = Exception("Database error")
        
        # Call the method
        result = self.controller.get_agent_by_id(agent_id, self.test_user_id, self.mock_session)
        
        # Should find it in static metadata
        assert result["success"] is True
        assert result["agent"]["id"] == agent_id
        assert result["source"] == "fallback"
    
    # ===== get_agents_by_category tests =====
    
    def test_get_agents_by_category_success(self):
        """Test successful retrieval of agents by category."""
        category = "development"
        mock_agents = [
            {
                "id": "@coding_agent",
                "name": "Coding Agent",
                "category": category,
                "description": "Handles code implementation"
            },
            {
                "id": "@debugger_agent",
                "name": "Debugger Agent",
                "category": category,
                "description": "Handles debugging"
            }
        ]
        
        self.mock_facade.list_agents_by_category.return_value = {
            "success": True,
            "agents": mock_agents
        }
        
        # Call the method
        result = self.controller.get_agents_by_category(category, self.test_user_id, self.mock_session)
        
        # Verify the result
        assert result["success"] is True
        assert result["category"] == category
        assert result["agents"] == mock_agents
        assert result["total"] == 2
        assert result["source"] == "facade"
        
        # Verify facade was called correctly
        self.mock_facade_service.get_agent_facade.assert_called_once_with(
            project_id=None,
            user_id=self.test_user_id
        )
        self.mock_facade.list_agents_by_category.assert_called_once_with(category)
    
    def test_get_agents_by_category_facade_failure_uses_static(self):
        """Test fallback to static metadata filtering when facade fails."""
        category = "orchestration"
        
        # Mock facade failure
        self.mock_facade.list_agents_by_category.return_value = {
            "success": False,
            "error": "Service unavailable"
        }
        
        # Call the method
        result = self.controller.get_agents_by_category(category, self.test_user_id, self.mock_session)
        
        # Verify static fallback
        assert result["success"] is True
        assert result["category"] == category
        assert result["source"] == "static"
        assert all(agent["category"] == category for agent in result["agents"])
        assert result["total"] == len(result["agents"])
    
    def test_get_agents_by_category_exception_uses_fallback(self):
        """Test fallback to static metadata filtering when exception occurs."""
        category = "quality"
        
        # Mock exception
        self.mock_facade.list_agents_by_category.side_effect = Exception("Unexpected error")
        
        # Call the method
        result = self.controller.get_agents_by_category(category, self.test_user_id, self.mock_session)
        
        # Verify fallback
        assert result["success"] is True
        assert result["category"] == category
        assert result["source"] == "fallback"
        assert all(agent["category"] == category for agent in result["agents"])
        assert result["total"] == len(result["agents"])
    
    def test_get_agents_by_category_empty_result(self):
        """Test when no agents found in category."""
        category = "non_existent_category"
        
        # Mock empty facade response
        self.mock_facade.list_agents_by_category.return_value = {
            "success": True,
            "agents": []
        }
        
        # Call the method
        result = self.controller.get_agents_by_category(category, self.test_user_id, self.mock_session)
        
        # Verify empty result
        assert result["success"] is True
        assert result["category"] == category
        assert result["agents"] == []
        assert result["total"] == 0
        assert result["source"] == "facade"
    
    # ===== list_agent_categories tests =====
    
    def test_list_agent_categories_success(self):
        """Test successful retrieval of agent categories."""
        mock_categories = ["development", "orchestration", "quality", "security"]
        
        self.mock_facade.list_agent_categories.return_value = {
            "success": True,
            "categories": mock_categories
        }
        
        # Call the method
        result = self.controller.list_agent_categories(self.test_user_id, self.mock_session)
        
        # Verify the result
        assert result["success"] is True
        assert result["categories"] == mock_categories
        assert result["total"] == 4
        assert result["source"] == "facade"
        
        # Verify facade was called correctly
        self.mock_facade_service.get_agent_facade.assert_called_once_with(
            project_id=None,
            user_id=self.test_user_id
        )
        self.mock_facade.list_agent_categories.assert_called_once()
    
    def test_list_agent_categories_facade_failure_uses_static(self):
        """Test fallback to static categories when facade fails."""
        # Mock facade failure
        self.mock_facade.list_agent_categories.return_value = {
            "success": False,
            "error": "Service unavailable"
        }
        
        # Call the method
        result = self.controller.list_agent_categories(self.test_user_id, self.mock_session)
        
        # Verify static fallback
        assert result["success"] is True
        assert result["source"] == "static"
        assert len(result["categories"]) > 0  # Should have static categories
        assert result["total"] == len(result["categories"])
        assert all(isinstance(cat, str) for cat in result["categories"])
    
    def test_list_agent_categories_exception_uses_fallback(self):
        """Test fallback to static categories when exception occurs."""
        # Mock exception
        self.mock_facade.list_agent_categories.side_effect = Exception("Database error")
        
        # Call the method
        result = self.controller.list_agent_categories(self.test_user_id, self.mock_session)
        
        # Verify fallback
        assert result["success"] is True
        assert result["source"] == "fallback"
        assert len(result["categories"]) > 0  # Should have static categories
        assert result["total"] == len(result["categories"])
        assert all(isinstance(cat, str) for cat in result["categories"])
    
    # ===== Static metadata tests =====
    
    def test_get_static_metadata_structure(self):
        """Test the structure of static metadata."""
        static_metadata = self.controller._get_static_metadata()
        
        assert isinstance(static_metadata, list)
        assert len(static_metadata) > 0
        
        # Verify each agent has required fields
        for agent in static_metadata:
            assert "id" in agent
            assert "name" in agent
            assert "call_name" in agent
            assert "role" in agent
            assert "description" in agent
            assert "category" in agent
            assert "type" in agent
            assert "priority" in agent
            assert "capabilities" in agent
            assert isinstance(agent["capabilities"], list)
            assert "tools" in agent
            assert isinstance(agent["tools"], list)
            assert "guidelines" in agent
    
    def test_find_static_agent_found(self):
        """Test finding an agent in static metadata."""
        agent_id = "@master_orchestrator_agent"
        agent = self.controller._find_static_agent(agent_id)
        
        assert agent is not None
        assert agent["id"] == agent_id
        assert agent["name"] == "Uber Orchestrator Agent"
    
    def test_find_static_agent_not_found(self):
        """Test when agent not found in static metadata."""
        agent_id = "@non_existent_agent"
        agent = self.controller._find_static_agent(agent_id)
        
        assert agent is None
    
    def test_get_static_categories(self):
        """Test getting unique categories from static metadata."""
        categories = self.controller._get_static_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert all(isinstance(cat, str) for cat in categories)
        assert categories == sorted(categories)  # Should be sorted
        
        # Verify categories match static metadata
        static_agents = self.controller._get_static_metadata()
        expected_categories = sorted(set(agent.get("category", "uncategorized") for agent in static_agents))
        assert categories == expected_categories
    
    # ===== Edge cases and error handling =====
    
    def test_get_agent_metadata_with_logging(self, caplog):
        """Test logging behavior during agent metadata retrieval."""
        with caplog.at_level(logging.INFO):
            mock_agents = [{"id": "@agent1"}, {"id": "@agent2"}]
            self.mock_facade.list_all_agents.return_value = {
                "success": True,
                "agents": mock_agents
            }
            
            self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
            
            assert "Retrieved 2 agent metadata entries" in caplog.text
    
    def test_get_agent_by_id_with_error_logging(self, caplog):
        """Test error logging when exception occurs."""
        with caplog.at_level(logging.ERROR):
            agent_id = "@test_agent"
            self.mock_facade.get_agent.side_effect = RuntimeError("Test error")
            
            result = self.controller.get_agent_by_id(agent_id, self.test_user_id, self.mock_session)
            
            assert f"Error getting agent {agent_id}: Test error" in caplog.text
            assert result["success"] is False or result["source"] in ["fallback", "static"]
    
    def test_facade_service_singleton_behavior(self):
        """Test that facade service follows singleton pattern."""
        # Create multiple controllers
        with patch.object(FacadeService, 'get_instance', return_value=self.mock_facade_service) as mock_get_instance:
            controller1 = AgentAPIController()
            controller2 = AgentAPIController()
            
            # Both should use the same facade service instance
            assert controller1.facade_service is controller2.facade_service
            assert mock_get_instance.call_count == 2
    
    def test_project_independent_agent_metadata(self):
        """Test that agent metadata operations don't require project context."""
        # Test all methods to ensure they pass None for project_id
        
        # get_agent_metadata
        self.mock_facade.list_all_agents.return_value = {"success": True, "agents": []}
        self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
        self.mock_facade_service.get_agent_facade.assert_called_with(project_id=None, user_id=self.test_user_id)
        
        # get_agent_by_id
        self.mock_facade_service.get_agent_facade.reset_mock()
        self.mock_facade.get_agent.return_value = {"success": True, "agent": {}}
        self.controller.get_agent_by_id("@test", self.test_user_id, self.mock_session)
        self.mock_facade_service.get_agent_facade.assert_called_with(project_id=None, user_id=self.test_user_id)
        
        # get_agents_by_category
        self.mock_facade_service.get_agent_facade.reset_mock()
        self.mock_facade.list_agents_by_category.return_value = {"success": True, "agents": []}
        self.controller.get_agents_by_category("test", self.test_user_id, self.mock_session)
        self.mock_facade_service.get_agent_facade.assert_called_with(project_id=None, user_id=self.test_user_id)
        
        # list_agent_categories
        self.mock_facade_service.get_agent_facade.reset_mock()
        self.mock_facade.list_agent_categories.return_value = {"success": True, "categories": []}
        self.controller.list_agent_categories(self.test_user_id, self.mock_session)
        self.mock_facade_service.get_agent_facade.assert_called_with(project_id=None, user_id=self.test_user_id)


# Integration tests
class TestAgentAPIControllerIntegration:
    """Integration tests for AgentAPIController with real static data."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create controller with real facade service that will fail
        # This tests the fallback behavior in a more realistic scenario
        self.controller = AgentAPIController()
        self.test_user_id = "test-user-123"
        self.mock_session = Mock()
    
    def test_static_fallback_provides_complete_agent_list(self):
        """Test that static fallback provides a complete list of agents."""
        # Force an error in facade service
        with patch.object(self.controller.facade_service, 'get_agent_facade', side_effect=Exception("Service error")):
            result = self.controller.get_agent_metadata(self.test_user_id, self.mock_session)
        
        assert result["success"] is True
        assert result["source"] == "fallback"
        assert len(result["agents"]) >= 4  # At least the 4 agents defined in static data
        
        # Verify key agents are present
        agent_ids = [agent["id"] for agent in result["agents"]]
        assert "@master_orchestrator_agent" in agent_ids
        assert "@coding_agent" in agent_ids
        assert "@debugger_agent" in agent_ids
        assert "@test_orchestrator_agent" in agent_ids
    
    def test_static_categories_match_agents(self):
        """Test that static categories match the agents defined."""
        # Get static data directly
        agents = self.controller._get_static_metadata()
        categories = self.controller._get_static_categories()
        
        # Extract categories from agents
        agent_categories = set(agent.get("category", "uncategorized") for agent in agents)
        
        # Categories should match
        assert set(categories) == agent_categories