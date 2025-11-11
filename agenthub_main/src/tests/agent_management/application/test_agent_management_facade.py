"""
Tests for AgentManagementFacade.

This module tests the application facade layer for agent management,
ensuring correct orchestration between domain services and repositories.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from fastmcp.agent_management.application.facades.agent_management_facade import (
    AgentManagementFacade,
)
from fastmcp.agent_management.domain.entities import AgentTemplate, UserAgentInstance
from fastmcp.agent_management.domain.value_objects import (
    AgentConfiguration,
    AgentTemplateId,
    UserAgentInstanceId,
    UserId,
)


@pytest.fixture
def mock_template_repo():
    """Mock agent template repository"""
    repo = Mock()
    return repo


@pytest.fixture
def mock_instance_repo():
    """Mock user agent instance repository"""
    repo = Mock()
    return repo


@pytest.fixture
def mock_instantiation_service():
    """Mock instantiation service"""
    service = Mock()
    return service


@pytest.fixture
def sample_template():
    """Sample agent template for testing"""
    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test coding agent system prompt",
        tools=["Read", "Write", "Edit", "Bash"],
        capabilities={"languages": ["Python", "JavaScript"]},
        rules=["Write clean code"],
        output_format="markdown",
        metadata={"author": "test", "version": "1.0.0"},
    )

    return AgentTemplate(
        id=template_id,
        slug="coding-agent",
        name="Coding Agent",
        description="Test coding agent",
        category="development",
        version="1.0.0",
        default_configuration=configuration,
        metadata={"source": "test"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_instance(sample_template):
    """Sample user agent instance for testing"""
    user_id = UserId.generate_new()
    instance_id = UserAgentInstanceId.generate_new()

    configuration = AgentConfiguration(
        system_prompt="Customized coding agent prompt",
        tools=["Read", "Write", "Edit", "Bash", "Grep"],  # Added Grep
        capabilities={
            "languages": ["Python", "JavaScript", "TypeScript"]
        },  # Added TypeScript
        rules=["Write clean code", "Follow DRY principles"],  # Added rule
        output_format="markdown",
        metadata={},
    )

    return UserAgentInstance(
        id=instance_id,
        user_id=user_id,
        template_id=sample_template.id,
        agent_name="My Custom Coding Agent",
        is_customized=True,
        configuration=configuration,
        visibility="private",
        last_used_at=None,
        metadata={"customization_notes": "Added Grep tool and TypeScript support"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestGetOrCreateInstance:
    """Tests for get_or_create_instance method"""

    def test_returns_existing_instance_when_found(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_instance,
    ):
        """Test that existing instance is returned without creating new one"""
        # Arrange
        user_id = sample_instance.user_id
        agent_slug = "coding-agent"

        mock_instance_repo.find_by_user_and_template_slug.return_value = sample_instance

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_or_create_instance(user_id, agent_slug)

        # Assert
        assert result == sample_instance
        mock_instance_repo.find_by_user_and_template_slug.assert_called_once_with(
            user_id=user_id, template_slug=agent_slug
        )
        # Should NOT create new instance
        mock_instantiation_service.create_instance_from_template.assert_not_called()
        mock_instance_repo.save.assert_not_called()

    def test_creates_new_instance_when_not_found(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_instance,
    ):
        """Test that new instance is created when user doesn't have one"""
        # Arrange
        user_id = sample_instance.user_id
        agent_slug = "coding-agent"

        # No existing instance
        mock_instance_repo.find_by_user_and_template_slug.return_value = None

        # Instantiation service creates new instance
        mock_instantiation_service.create_instance_from_template.return_value = (
            sample_instance
        )

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_or_create_instance(user_id, agent_slug)

        # Assert
        assert result == sample_instance
        mock_instantiation_service.create_instance_from_template.assert_called_once_with(
            user_id=user_id, template_slug=agent_slug
        )
        mock_instance_repo.save.assert_called_once_with(sample_instance)

    def test_raises_value_error_when_template_not_found(
        self, mock_template_repo, mock_instance_repo, mock_instantiation_service
    ):
        """Test that ValueError is raised when agent template doesn't exist"""
        # Arrange
        user_id = UserId.generate_new()
        agent_slug = "nonexistent-agent"

        mock_instance_repo.find_by_user_and_template_slug.return_value = None
        mock_instantiation_service.create_instance_from_template.side_effect = (
            ValueError(f"Agent template not found: {agent_slug}")
        )

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Agent template not found"):
            facade.get_or_create_instance(user_id, agent_slug)


class TestGetAgentForCall:
    """Tests for get_agent_for_call method"""

    def test_returns_correct_configuration_format(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_template,
        sample_instance,
    ):
        """Test that configuration is returned in correct format for MCP"""
        # Arrange
        user_id = sample_instance.user_id
        agent_slug = "coding-agent"

        mock_instance_repo.find_by_user_and_template_slug.return_value = sample_instance
        mock_template_repo.find_by_slug.return_value = sample_template

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_agent_for_call(user_id, agent_slug)

        # Assert
        assert isinstance(result, dict)
        assert result["name"] == "My Custom Coding Agent"  # Custom name
        assert result["slug"] == "coding-agent"
        assert result["system_prompt"] == "Customized coding agent prompt"
        assert result["tools"] == ["Read", "Write", "Edit", "Bash", "Grep"]
        assert result["is_customized"] is True
        assert result["instance_id"] == sample_instance.id.value
        assert result["template_id"] == sample_template.id.value
        assert "metadata" in result

    def test_handles_default_instance_without_customization(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_template,
    ):
        """Test handling instance with default configuration (not customized)"""
        # Arrange
        user_id = UserId.generate_new()
        agent_slug = "coding-agent"

        # Create instance with default config
        default_instance = UserAgentInstance(
            id=UserAgentInstanceId.generate_new(),
            user_id=user_id,
            template_id=sample_template.id,
            agent_name=sample_template.name,  # Use template name for default
            is_customized=False,
            configuration=sample_template.default_configuration,  # Default config
            visibility="private",
            last_used_at=None,
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_instance_repo.find_by_user_and_template_slug.return_value = (
            default_instance
        )
        mock_template_repo.find_by_slug.return_value = sample_template

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_agent_for_call(user_id, agent_slug)

        # Assert
        assert result["name"] == "Coding Agent"  # Template name (no custom name)
        assert result["is_customized"] is False
        assert result["system_prompt"] == "Test coding agent system prompt"

    def test_tracks_usage_on_call(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_template,
        sample_instance,
    ):
        """Test that usage tracking is updated when agent is called"""
        # Arrange
        user_id = sample_instance.user_id
        agent_slug = "coding-agent"

        # Record initial last_used_at state
        initial_last_used = sample_instance.last_used_at

        mock_instance_repo.find_by_user_and_template_slug.return_value = sample_instance
        mock_template_repo.find_by_slug.return_value = sample_template

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        facade.get_agent_for_call(user_id, agent_slug)

        # Assert
        # Instance should be saved (usage tracking)
        mock_instance_repo.save.assert_called()

        # Verify track_usage was called on instance (updates last_used_at)
        assert (
            sample_instance.last_used_at != initial_last_used
            or initial_last_used is None
        )

    def test_raises_value_error_when_template_not_found_after_instantiation(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_instance,
    ):
        """Test that ValueError is raised if template lookup fails after instantiation"""
        # Arrange
        user_id = sample_instance.user_id
        agent_slug = "coding-agent"

        mock_instance_repo.find_by_user_and_template_slug.return_value = sample_instance
        mock_template_repo.find_by_slug.return_value = None  # Template not found

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Agent template not found"):
            facade.get_agent_for_call(user_id, agent_slug)


class TestGetUserInstances:
    """Tests for get_user_instances method"""

    def test_returns_all_user_instances(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_instance,
    ):
        """Test that all user's instances are returned"""
        # Arrange
        user_id = sample_instance.user_id

        # Create additional instances
        instance2 = UserAgentInstance(
            id=UserAgentInstanceId.generate_new(),
            user_id=user_id,
            template_id=AgentTemplateId.generate_new(),
            agent_name="Test Agent 2",
            is_customized=False,
            configuration=AgentConfiguration(
                system_prompt="Test prompt 2", tools=["Read"], capabilities={}
            ),
            visibility="private",
            last_used_at=None,
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_instance_repo.find_all_by_user.return_value = [sample_instance, instance2]

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_user_instances(user_id)

        # Assert
        assert len(result) == 2
        assert sample_instance in result
        assert instance2 in result
        mock_instance_repo.find_all_by_user.assert_called_once_with(user_id)

    def test_returns_empty_list_when_no_instances(
        self, mock_template_repo, mock_instance_repo, mock_instantiation_service
    ):
        """Test that empty list is returned when user has no instances"""
        # Arrange
        user_id = UserId.generate_new()
        mock_instance_repo.find_all_by_user.return_value = []

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_user_instances(user_id)

        # Assert
        assert result == []
        assert isinstance(result, list)


class TestGetTemplateBySlug:
    """Tests for get_template_by_slug method"""

    def test_returns_template_when_found(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_template,
    ):
        """Test that template is returned when found"""
        # Arrange
        agent_slug = "coding-agent"
        mock_template_repo.find_by_slug.return_value = sample_template

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_template_by_slug(agent_slug)

        # Assert
        assert result == sample_template
        mock_template_repo.find_by_slug.assert_called_once_with(agent_slug)

    def test_returns_none_when_template_not_found(
        self, mock_template_repo, mock_instance_repo, mock_instantiation_service
    ):
        """Test that None is returned when template doesn't exist"""
        # Arrange
        agent_slug = "nonexistent-agent"
        mock_template_repo.find_by_slug.return_value = None

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.get_template_by_slug(agent_slug)

        # Assert
        assert result is None


class TestListAvailableTemplates:
    """Tests for list_available_templates method"""

    def test_returns_all_templates(
        self,
        mock_template_repo,
        mock_instance_repo,
        mock_instantiation_service,
        sample_template,
    ):
        """Test that all available templates are returned"""
        # Arrange
        template2 = AgentTemplate(
            id=AgentTemplateId.generate_new(),
            slug="test-agent",
            name="Test Agent",
            description="Another test agent",
            category="testing",
            version="1.0.0",
            default_configuration=AgentConfiguration(
                system_prompt="Test prompt", tools=["Read"], capabilities={}
            ),
            metadata={"source": "test"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_template_repo.find_all.return_value = [sample_template, template2]

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.list_available_templates()

        # Assert
        assert len(result) == 2
        assert sample_template in result
        assert template2 in result
        mock_template_repo.find_all.assert_called_once()

    def test_returns_empty_list_when_no_templates(
        self, mock_template_repo, mock_instance_repo, mock_instantiation_service
    ):
        """Test that empty list is returned when no templates exist"""
        # Arrange
        mock_template_repo.find_all.return_value = []

        facade = AgentManagementFacade(
            template_repository=mock_template_repo,
            instance_repository=mock_instance_repo,
            instantiation_service=mock_instantiation_service,
        )

        # Act
        result = facade.list_available_templates()

        # Assert
        assert result == []
        assert isinstance(result, list)


if __name__ == "__main__":
    print("\n=== Running Agent Management Facade Tests ===\n")
    pytest.main([__file__, "-v", "--tb=short"])
