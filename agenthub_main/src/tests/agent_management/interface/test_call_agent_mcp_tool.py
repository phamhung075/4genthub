"""
Tests for call_agent MCP tool.

This module tests the MCP interface layer for calling agents,
ensuring correct integration with authentication and facade layer.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from fastmcp.agent_management.domain.value_objects import UserId
from fastmcp.agent_management.interface.mcp_controllers.call_agent import (
    call_agent_mcp_tool,
)


@pytest.fixture
def mock_auth_service():
    """Mock authentication service"""
    with patch('fastmcp.agent_management.interface.mcp_controllers.call_agent.AuthenticationService') as mock:
        yield mock


@pytest.fixture
def mock_facade():
    """Mock AgentManagementFacade"""
    with patch('fastmcp.agent_management.interface.mcp_controllers.call_agent.AgentManagementFacade') as mock:
        yield mock


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration returned by facade"""
    return {
        "name": "Coding Agent",
        "slug": "coding-agent",
        "description": "Test coding agent for development tasks",
        "system_prompt": "You are a coding agent that helps with development",
        "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
        "capabilities": {
            "languages": ["Python", "JavaScript", "TypeScript"],
            "frameworks": ["FastAPI", "React", "Next.js"]
        },
        "rules": ["Write clean code", "Follow DRY principles"],
        "output_format": "markdown",
        "category": "development",
        "version": "1.0.0",
        "is_customized": False,
        "instance_id": "550e8400-e29b-41d4-a716-446655440001",
        "template_id": "550e8400-e29b-41d4-a716-446655440002",
        "metadata": {
            "author": "test",
            "created_at": "2025-11-01T12:00:00+00:00",
            "last_used": None,
            "customizations": {}
        }
    }


class TestCallAgentMCPToolSuccess:
    """Tests for successful call_agent MCP tool invocations"""

    def test_success_with_existing_instance(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test successful call when user has existing agent instance"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440003"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is True
        assert result["agent"] == sample_agent_config
        assert result["source"] == "agent-management-system"

        # Verify authentication was called
        auth_instance.get_authenticated_user_id.assert_called_once_with(
            provided_user_id=None,
            operation_name="call_agent"
        )

        # Verify facade was called correctly
        facade_instance.get_agent_for_call.assert_called_once()
        call_args = facade_instance.get_agent_for_call.call_args
        assert call_args[1]["agent_slug"] == agent_name
        assert isinstance(call_args[1]["user_id"], UserId)

    def test_success_with_auto_created_instance(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test successful call when agent instance is auto-created"""
        # Arrange
        agent_name = "test-orchestrator-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440004"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - agent config for newly created instance
        new_instance_config = {
            **sample_agent_config,
            "name": "Test Orchestrator Agent",
            "slug": "test-orchestrator-agent",
            "is_customized": False,  # Newly created, not customized
            "metadata": {
                **sample_agent_config["metadata"],
                "created_at": datetime.now(UTC).isoformat()
            }
        }

        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = new_instance_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is True
        assert result["agent"]["slug"] == "test-orchestrator-agent"
        assert result["agent"]["is_customized"] is False
        assert "created_at" in result["agent"]["metadata"]

    def test_success_with_provided_user_id(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test successful call when user_id is explicitly provided"""
        # Arrange
        agent_name = "coding-agent"
        provided_user_id = "550e8400-e29b-41d4-a716-446655440005"

        # Mock authentication - should use provided user_id
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = provided_user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=provided_user_id)

        # Assert
        assert result["success"] is True

        # Verify authentication was called with provided user_id
        auth_instance.get_authenticated_user_id.assert_called_once_with(
            provided_user_id=provided_user_id,
            operation_name="call_agent"
        )

    def test_success_with_customized_instance(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test successful call with user-customized agent instance"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440006"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - customized agent config
        customized_config = {
            **sample_agent_config,
            "name": "My Custom Coding Agent",
            "system_prompt": "Customized prompt for my workflow",
            "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],  # Added Glob
            "is_customized": True,
            "metadata": {
                **sample_agent_config["metadata"],
                "customizations": {
                    "added_tools": ["Glob"],
                    "modified_prompt": True
                }
            }
        }

        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = customized_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is True
        assert result["agent"]["is_customized"] is True
        assert result["agent"]["name"] == "My Custom Coding Agent"
        assert "Glob" in result["agent"]["tools"]


class TestCallAgentMCPToolFailure:
    """Tests for failed call_agent MCP tool invocations"""

    def test_failure_agent_not_found(self, mock_auth_service, mock_facade):
        """Test failure when agent template doesn't exist"""
        # Arrange
        agent_name = "nonexistent-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440007"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - raises ValueError
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.side_effect = ValueError(
            f"Agent not found: {agent_name}"
        )

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert f"Agent not found: {agent_name}" in result["error"]
        assert "message" in result

    def test_failure_authentication_error(self, mock_auth_service, mock_facade):
        """Test failure when authentication fails"""
        # Arrange
        agent_name = "coding-agent"

        # Mock authentication - raises exception
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.side_effect = Exception(
            "Authentication failed: No JWT token provided"
        )

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Failed to load agent"
        assert "Authentication failed" in result["message"]

    def test_failure_invalid_agent_slug(self, mock_auth_service, mock_facade):
        """Test failure with invalid agent slug format"""
        # Arrange
        agent_name = "invalid agent name"  # Spaces not allowed
        user_id = "550e8400-e29b-41d4-a716-446655440008"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - raises ValueError for invalid slug
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.side_effect = ValueError(
            "Invalid agent slug format"
        )

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is False
        assert "Invalid agent slug format" in result["message"]

    def test_failure_database_error(self, mock_auth_service, mock_facade):
        """Test failure when database operation fails"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440009"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - database error
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.side_effect = Exception(
            "Database connection error"
        )

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to load agent"
        assert "Database connection error" in result["message"]


class TestCallAgentMCPToolEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_concurrent_calls_same_agent(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test multiple concurrent calls for same agent (race condition)"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440010"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act - Simulate concurrent calls
        result1 = call_agent_mcp_tool(name_agent=agent_name, user_id=None)
        result2 = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert - Both should succeed
        assert result1["success"] is True
        assert result2["success"] is True

        # Facade should be called twice
        assert facade_instance.get_agent_for_call.call_count == 2

    def test_empty_agent_name(self, mock_auth_service, mock_facade):
        """Test with empty agent name"""
        # Arrange
        agent_name = ""
        user_id = "550e8400-e29b-41d4-a716-446655440011"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - raises ValueError
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.side_effect = ValueError(
            "Agent name cannot be empty"
        )

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert result["success"] is False
        assert "Agent name cannot be empty" in result["message"]

    def test_none_agent_name(self, mock_auth_service, mock_facade):
        """Test with None as agent name"""
        # Arrange
        agent_name = None
        user_id = "550e8400-e29b-41d4-a716-446655440012"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade - raises TypeError or ValueError
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.side_effect = TypeError(
            "Agent name cannot be None"
        )

        # Act & Assert - Should raise error or return failure
        try:
            result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)
            assert result["success"] is False
        except TypeError:
            # This is also acceptable behavior
            pass


class TestCallAgentMCPToolResponseFormat:
    """Tests for response format validation"""

    def test_response_has_required_fields(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test that response contains all required fields"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440013"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert - Check required top-level fields
        assert "success" in result
        assert "agent" in result
        assert "source" in result

        # Check agent configuration fields
        agent = result["agent"]
        required_fields = [
            "name", "slug", "description", "system_prompt", "tools",
            "capabilities", "category", "version", "is_customized",
            "instance_id", "template_id", "metadata"
        ]

        for field in required_fields:
            assert field in agent, f"Missing required field: {field}"

    def test_response_agent_tools_is_list(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test that tools field is a list"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440014"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert isinstance(result["agent"]["tools"], list)
        assert len(result["agent"]["tools"]) > 0

    def test_response_capabilities_is_dict(self, mock_auth_service, mock_facade, sample_agent_config):
        """Test that capabilities field is a dictionary"""
        # Arrange
        agent_name = "coding-agent"
        user_id = "550e8400-e29b-41d4-a716-446655440015"

        # Mock authentication
        auth_instance = mock_auth_service.return_value
        auth_instance.get_authenticated_user_id.return_value = user_id

        # Mock facade
        facade_instance = mock_facade.return_value
        facade_instance.get_agent_for_call.return_value = sample_agent_config

        # Act
        result = call_agent_mcp_tool(name_agent=agent_name, user_id=None)

        # Assert
        assert isinstance(result["agent"]["capabilities"], dict)


if __name__ == "__main__":
    print("\n=== Running call_agent MCP Tool Tests ===\n")
    pytest.main([__file__, "-v", "--tb=short"])
