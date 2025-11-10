"""
Tests for agent_management repository implementations.

This module tests the ORM repositories to ensure they correctly
persist and retrieve agent templates and user agent instances.
"""

from datetime import UTC, datetime

from fastmcp.agent_management.domain.entities import AgentTemplate, UserAgentInstance
from fastmcp.agent_management.domain.value_objects import (
    AgentConfiguration,
    AgentTemplateId,
    UserAgentInstanceId,
    UserId,
)
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository,
)


def test_agent_template_repository_save_and_find():
    """Test saving and finding agent templates"""
    # Arrange
    repository = ORMAgentTemplateRepository()

    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test system prompt for coding agent",
        tools=["Read", "Write", "Edit", "Bash"],
        capabilities={"languages": ["Python", "JavaScript"], "frameworks": ["FastAPI", "React"]},
        rules=["Write clean code", "Follow DRY principles"],
        output_format={"format": "markdown"},
        metadata={"author": "test", "version": "1.0.0"}
    )

    template = AgentTemplate(
        id=template_id,
        slug="test-coding-agent",
        name="Test Coding Agent",
        description="A test coding agent for unit tests",
        category="development",
        version="1.0.0",
        default_configuration=configuration,
        metadata={"source": "test"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Act - Save
    saved_template = repository.save(template)

    # Assert - Save succeeded
    assert saved_template is not None
    assert saved_template.id == template_id
    assert saved_template.slug == "test-coding-agent"

    # Act - Find by ID
    found_by_id = repository.find_by_id(template_id)

    # Assert - Found by ID
    assert found_by_id is not None
    assert found_by_id.id == template_id
    assert found_by_id.slug == "test-coding-agent"
    assert found_by_id.name == "Test Coding Agent"
    assert found_by_id.default_configuration.system_prompt == "Test system prompt for coding agent"
    assert len(found_by_id.default_configuration.tools) == 4

    # Act - Find by slug
    found_by_slug = repository.find_by_slug("test-coding-agent")

    # Assert - Found by slug
    assert found_by_slug is not None
    assert found_by_slug.id == template_id

    # Cleanup
    repository.delete(template_id)
    print("✅ AgentTemplateRepository save and find test passed")


def test_user_agent_instance_repository_save_and_find():
    """Test saving and finding user agent instances"""
    # Arrange
    template_repo = ORMAgentTemplateRepository()
    instance_repo = ORMUserAgentInstanceRepository()

    # Create a template first
    template_id = AgentTemplateId.generate_new()
    template_config = AgentConfiguration(
        system_prompt="Template system prompt",
        tools=["Read", "Write"],
        capabilities={"test": "capability"}
    )

    template = AgentTemplate(
        id=template_id,
        slug="test-template-for-instance",
        name="Test Template",
        description="Template for testing instances",
        category="testing",
        version="1.0.0",
        default_configuration=template_config,
        metadata={"source": "test"}
    )
    template_repo.save(template)

    # Create a user instance
    user_id = UserId.generate_new()
    instance_id = UserAgentInstanceId.generate_new()
    instance_config = AgentConfiguration(
        system_prompt="Customized system prompt",
        tools=["Read", "Write", "Edit"],  # Added Edit tool
        capabilities={"test": "capability", "custom": "feature"}
    )

    instance = UserAgentInstance(
        id=instance_id,
        user_id=user_id,
        template_id=template_id,
        agent_name="My Custom Agent",
        is_customized=True,
        customization_notes="Added Edit tool and custom capability",
        configuration=instance_config,
        visibility="private",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Act - Save instance
    saved_instance = instance_repo.save(instance)

    # Assert - Save succeeded
    assert saved_instance is not None
    assert saved_instance.id == instance_id
    assert saved_instance.agent_name == "My Custom Agent"
    assert saved_instance.is_customized is True

    # Act - Find by ID
    found_by_id = instance_repo.find_by_id(instance_id)

    # Assert - Found by ID
    assert found_by_id is not None
    assert found_by_id.id == instance_id
    assert found_by_id.user_id == user_id
    assert found_by_id.template_id == template_id
    assert found_by_id.configuration.system_prompt == "Customized system prompt"
    assert len(found_by_id.configuration.tools) == 3

    # Act - Find by user and template
    found_by_user_template = instance_repo.find_by_user_and_template(user_id, template_id)

    # Assert - Found by user and template
    assert found_by_user_template is not None
    assert found_by_user_template.id == instance_id

    # Act - Find by user
    user_instances = instance_repo.find_by_user(user_id)

    # Assert - Found by user
    assert len(user_instances) >= 1
    assert any(inst.id == instance_id for inst in user_instances)

    # Cleanup
    instance_repo.delete(instance_id)
    template_repo.delete(template_id)
    print("✅ UserAgentInstanceRepository save and find test passed")


def test_user_agent_instance_sharing():
    """Test sharing functionality for user agent instances"""
    # Arrange
    template_repo = ORMAgentTemplateRepository()
    instance_repo = ORMUserAgentInstanceRepository()

    # Create template
    template_id = AgentTemplateId.generate_new()
    template = AgentTemplate(
        id=template_id,
        slug="shareable-template",
        name="Shareable Template",
        description="Template for sharing tests",
        category="testing",
        version="1.0.0",
        default_configuration=AgentConfiguration(
            system_prompt="Shareable prompt",
            tools=["Read"],
            capabilities={}
        ),
        metadata={"source": "test"}
    )
    template_repo.save(template)

    # Create instance with sharing
    user_id = UserId.generate_new()
    instance_id = UserAgentInstanceId.generate_new()
    share_token = "test_share_token_123456789012345678901234567890123456789012345"

    instance = UserAgentInstance(
        id=instance_id,
        user_id=user_id,
        template_id=template_id,
        agent_name="Shared Agent",
        is_customized=False,
        configuration=template.default_configuration,
        visibility="public",
        share_token=share_token,
        share_created_at=datetime.now(UTC)
    )

    # Act - Save and find by share token
    instance_repo.save(instance)
    found_by_token = instance_repo.find_by_share_token(share_token)

    # Assert
    assert found_by_token is not None
    assert found_by_token.id == instance_id
    assert found_by_token.share_token == share_token
    assert found_by_token.visibility == "public"

    # Act - Find public instances
    public_instances = instance_repo.find_public_instances(limit=10)

    # Assert
    assert len(public_instances) >= 1
    assert any(inst.id == instance_id for inst in public_instances)

    # Cleanup
    instance_repo.delete(instance_id)
    template_repo.delete(template_id)
    print("✅ UserAgentInstanceRepository sharing test passed")


def test_count_by_agent_name():
    """Test counting instances by agent name"""
    # Arrange
    template_repo = ORMAgentTemplateRepository()
    instance_repo = ORMUserAgentInstanceRepository()

    template_id = AgentTemplateId.generate_new()
    template = AgentTemplate(
        id=template_id,
        slug="count-test-template",
        name="Count Test Template",
        description="Template for count tests",
        category="testing",
        version="1.0.0",
        default_configuration=AgentConfiguration(
            system_prompt="Count test prompt",
            tools=["Read"],
            capabilities={}
        ),
        metadata={"source": "test"}
    )
    template_repo.save(template)

    user_id = UserId.generate_new()

    # Create two instances with same name (imported agents)
    instance1_id = UserAgentInstanceId.generate_new()
    instance1 = UserAgentInstance(
        id=instance1_id,
        user_id=user_id,
        template_id=template_id,
        agent_name="Imported Agent",
        is_customized=False,
        configuration=template.default_configuration,
        visibility="private"
    )
    instance_repo.save(instance1)

    # Act - Count before adding second
    count_before = instance_repo.count_by_agent_name_for_user(user_id, "Imported Agent")

    # Assert
    assert count_before == 1

    # Cleanup
    instance_repo.delete(instance1_id)
    template_repo.delete(template_id)
    print("✅ count_by_agent_name test passed")


if __name__ == "__main__":
    print("\n=== Running Agent Management Repository Tests ===\n")

    try:
        test_agent_template_repository_save_and_find()
        test_user_agent_instance_repository_save_and_find()
        test_user_agent_instance_sharing()
        test_count_by_agent_name()

        print("\n✅ All repository tests passed!\n")
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
