"""
Facade/Application Layer Tests for Orphaned Agent Import Functionality

Tests the AgentManagementFacade methods that return orphaned status
in API responses:
1. get_agent_for_call() - includes is_orphaned flag and warning message

Test Strategy:
- Integration tests for application/facade layer
- Test business logic coordination between domain and infrastructure
- Verify API responses include proper orphaned flags and warnings
- Test user experience: warnings displayed for orphaned imports

Requirements Coverage:
- API returns is_orphaned=True for orphaned imports
- API returns is_orphaned=False for original agents
- API returns is_orphaned=False for active imports
- API includes warning message in metadata for orphaned imports
"""

from datetime import UTC, datetime
from uuid import uuid4

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
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_test_template(slug: str = "test-agent") -> AgentTemplate:
    """Create a test agent template"""
    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test agent for facade tests",
        tools=["Read", "Write"],
        capabilities={"test": True},
        rules=["Test rule"],
        output_format=None,
    )

    return AgentTemplate(
        id=template_id,
        slug=slug,
        name=f"Test Agent {slug}",
        description="Test agent for facade tests",
        category="test",
        version="1.0.0",
        default_configuration=configuration,
        metadata={"source": "test"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def create_test_instance(
    user_id: UserId,
    template_id: AgentTemplateId,
    visibility: str = "public",
    share_token: str = None,
    original_creator_id: UserAgentInstanceId = None,
) -> UserAgentInstance:
    """Create a test user agent instance"""
    instance_id = UserAgentInstanceId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="Test instance",
        tools=["Read"],
        capabilities={},
        rules=[],
        output_format=None,
    )

    return UserAgentInstance(
        id=instance_id,
        user_id=user_id,
        template_id=template_id,
        agent_name="Test Instance",
        configuration=configuration,
        is_enabled=True,
        is_customized=False,
        visibility=visibility,
        share_token=share_token
        or (str(uuid4())[:64] if visibility == "public" else None),
        original_creator_id=original_creator_id,
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_used_at=None,
    )


# ============================================================================
# TEST SUITE: get_agent_for_call() - ORPHANED FLAG IN API RESPONSE
# ============================================================================


class TestGetAgentForCallOrphanedFlag:
    """Test API responses include orphaned status and warnings"""

    def test_get_agent_for_call_flags_orphaned_import(self):
        """
        GIVEN: User has an orphaned import
        WHEN: Getting agent configuration via facade
        THEN: Response includes is_orphaned=True and warning message
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        facade = AgentManagementFacade(template_repo, instance_repo)

        template = create_test_template("facade-orphan-test")
        template_repo.save(template)

        # User A creates agent
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        # User B imports
        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            original_creator_id=user_a,  # User ID of original creator
        )
        instance_repo.save(imported_instance)

        # User A deletes (creates orphan)
        instance_repo.delete(original_instance.id)

        # Act - User B calls get_agent_for_call
        response = facade.get_agent_for_call(user_b, template.slug)

        # Assert - Orphaned flag and warning present
        assert response["is_orphaned"] is True, "Response should flag orphaned import"
        assert response["metadata"]["orphaned_warning"] is not None, (
            "Response should include orphaned warning message"
        )
        assert (
            "not supported by owner anymore" in response["metadata"]["orphaned_warning"]
        ), "Warning should mention owner no longer supports"

        # Cleanup
        instance_repo.delete(imported_instance.id)
        template_repo.delete(template.id)

        print("✅ test_get_agent_for_call_flags_orphaned_import passed")

    def test_get_agent_for_call_no_flag_for_original_agent(self):
        """
        GIVEN: User uses their own original agent
        WHEN: Getting agent configuration via facade
        THEN: Response includes is_orphaned=False, no warning
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        facade = AgentManagementFacade(template_repo, instance_repo)

        template = create_test_template("facade-original-test")
        template_repo.save(template)

        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        # Act - User A calls get_agent_for_call (their own agent)
        response = facade.get_agent_for_call(user_a, template.slug)

        # Assert - No orphaned flag
        assert response["is_orphaned"] is False, (
            "Original agent should not be flagged as orphaned"
        )
        assert response["metadata"]["orphaned_warning"] is None, (
            "Original agent should not have warning"
        )

        # Cleanup
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_get_agent_for_call_no_flag_for_original_agent passed")

    def test_get_agent_for_call_no_flag_for_active_import(self):
        """
        GIVEN: User has an active import (original still exists)
        WHEN: Getting agent configuration via facade
        THEN: Response includes is_orphaned=False, no warning
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        facade = AgentManagementFacade(template_repo, instance_repo)

        template = create_test_template("facade-active-test")
        template_repo.save(template)

        # User A creates agent
        user_a = UserId.from_string(str(uuid4()))
        original_instance = create_test_instance(user_a, template.id)
        instance_repo.save(original_instance)

        # User B imports (original still exists)
        user_b = UserId.from_string(str(uuid4()))
        imported_instance = create_test_instance(
            user_b,
            template.id,
            original_creator_id=user_a,  # User ID of original creator
        )
        instance_repo.save(imported_instance)

        # Act - User B calls get_agent_for_call (active import)
        response = facade.get_agent_for_call(user_b, template.slug)

        # Assert - No orphaned flag (original still exists)
        assert response["is_orphaned"] is False, (
            "Active import should not be flagged as orphaned"
        )
        assert response["metadata"]["orphaned_warning"] is None, (
            "Active import should not have warning"
        )

        # Cleanup
        instance_repo.delete(imported_instance.id)
        instance_repo.delete(original_instance.id)
        template_repo.delete(template.id)

        print("✅ test_get_agent_for_call_no_flag_for_active_import passed")
