"""
End-to-End Tests for Orphaned Agent Import Workflow

Tests the complete orphaned agent handling workflow from user perspective:
1. User A creates and shares public agent
2. User B imports agent
3. User A deletes their agent (creates orphan)
4. Verify marketplace doesn't show orphaned import
5. Verify User B can still use their imported copy
6. Verify User B sees warning when using agent

Test Strategy:
- E2E tests for complete user workflows
- Multi-user scenarios (User A shares, User B imports, User A deletes)
- Marketplace visibility verification
- User experience verification (warnings displayed)
- Data preservation (imports still work after original deleted)

Requirements Coverage:
- Complete orphaned agent lifecycle
- Marketplace filtering in action
- User data preservation
- Warning system for orphaned imports
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fastmcp.agent_management.application.facades.agent_management_facade import (
    AgentManagementFacade,
)
from fastmcp.agent_management.domain.entities import AgentTemplate
from fastmcp.agent_management.domain.services.agent_sharing_service import (
    AgentSharingService,
)
from fastmcp.agent_management.domain.value_objects import (
    AgentConfiguration,
    AgentTemplateId,
    UserId,
)
from fastmcp.agent_management.infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_template(slug: str = "e2e-test-agent") -> AgentTemplate:
    """Create a test agent template for E2E tests"""
    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="E2E test agent for orphaned workflow",
        tools=["Read", "Write", "Edit"],
        capabilities={"test": True, "e2e": True},
        rules=["Test rule for E2E"],
        output_format=None
    )

    return AgentTemplate(
        id=template_id,
        slug=slug,
        name=f"E2E Test Agent {slug}",
        description="Agent for end-to-end orphaned workflow testing",
        category="test",
        version="1.0.0",
        default_configuration=configuration,
        metadata={"source": "e2e-test"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


# ============================================================================
# E2E TEST SUITE: ORPHANED AGENT COMPLETE WORKFLOW
# ============================================================================

@pytest.mark.asyncio
class TestOrphanedAgentE2EWorkflow:
    """Complete E2E test suite for orphaned agent workflow"""

    async def test_orphaned_agent_complete_workflow(self):
        """
        Complete workflow test:
        1. User A creates and shares public agent
        2. User B imports agent (verify in marketplace)
        3. User A deletes their agent
        4. Verify marketplace doesn't show orphaned import
        5. User B can still use imported agent
        6. User B sees warning when calling agent
        """
        # Arrange - Setup repositories and facades
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        sharing_service = AgentSharingService(instance_repo, template_repo)
        facade = AgentManagementFacade(
            template_repo,
            instance_repo,
            sharing_service=sharing_service
        )

        # Create test template
        template = create_test_template("e2e-orphan-workflow")
        template_repo.save(template)

        # STEP 1: User A creates and customizes agent
        user_a = UserId.from_string(str(uuid4()))
        print(f"\n🔹 Step 1: User A ({user_a.value[:8]}) creates agent")

        # Get or create instance for User A
        instance_a = facade.get_or_create_instance(user_a, template.slug)
        print(f"  ✓ User A has instance: {instance_a.id.value[:8]}")

        # Share agent (make public)
        share_token = facade.share_agent(user_a, str(instance_a.id.value))
        print(f"  ✓ Agent shared with token: {share_token[:16]}...")

        # Verify in marketplace
        marketplace_before = instance_repo.find_public_instances(limit=100, offset=0)
        marketplace_ids_before = [inst.id.value for inst in marketplace_before]
        assert instance_a.id.value in marketplace_ids_before, "Original agent should be in marketplace"
        print("  ✓ Agent visible in marketplace")

        # STEP 2: User B imports agent
        user_b = UserId.from_string(str(uuid4()))
        print(f"\n🔹 Step 2: User B ({user_b.value[:8]}) imports agent")

        # Preview agent
        preview = facade.get_shared_agent_preview(share_token)
        assert preview is not None, "Should be able to preview shared agent"
        print(f"  ✓ User B previewed agent: {preview.agent_name}")

        # Import agent
        imported_instance = facade.import_agent(share_token, user_b, creator_email="user_a@test.com")
        assert imported_instance is not None, "Import should succeed"
        assert imported_instance.original_creator_id == user_a, \
            "Import should reference original creator's user ID"
        print(f"  ✓ User B imported agent: {imported_instance.id.value[:8]}")

        # Verify both in marketplace
        marketplace_after_import = instance_repo.find_public_instances(limit=100, offset=0)
        marketplace_ids_after_import = [inst.id.value for inst in marketplace_after_import]
        assert instance_a.id.value in marketplace_ids_after_import, \
            "Original should still be in marketplace"
        assert imported_instance.id.value in marketplace_ids_after_import, \
            "Active import should be in marketplace"
        print(f"  ✓ Both agents visible in marketplace (count: {len(marketplace_ids_after_import)})")

        # STEP 3: User A deletes their agent
        print("\n🔹 Step 3: User A deletes their agent")
        facade.delete_instance(user_a, str(instance_a.id.value))
        print("  ✓ User A deleted original agent")

        # STEP 4: Verify marketplace doesn't show orphaned import
        print("\n🔹 Step 4: Verify marketplace filtering")
        marketplace_after_delete = instance_repo.find_public_instances(limit=100, offset=0)
        marketplace_ids_after_delete = [inst.id.value for inst in marketplace_after_delete]

        assert instance_a.id.value not in marketplace_ids_after_delete, \
            "Deleted original should not be in marketplace"
        assert imported_instance.id.value not in marketplace_ids_after_delete, \
            "Orphaned import should NOT be in marketplace"
        print("  ✓ Orphaned import hidden from marketplace")

        # STEP 5: User B can still use imported agent
        print("\n🔹 Step 5: User B can still use their import")

        # Verify instance still exists
        user_b_instance = instance_repo.find_by_id(imported_instance.id)
        assert user_b_instance is not None, "User B's import should still exist"
        print("  ✓ User B's import still exists and usable")

        # STEP 6: User B sees warning when calling agent
        print("\n🔹 Step 6: User B sees orphaned warning")

        agent_response = facade.get_agent_for_call(user_b, template.slug)
        assert agent_response["is_orphaned"] is True, \
            "Should flag as orphaned"
        assert agent_response["metadata"]["orphaned_warning"] is not None, \
            "Should include warning message"
        assert "not supported by owner anymore" in agent_response["metadata"]["orphaned_warning"], \
            "Warning should mention lack of support"
        print(f"  ✓ Warning displayed: '{agent_response['metadata']['orphaned_warning']}'")

        # Cleanup
        instance_repo.delete(imported_instance.id)
        template_repo.delete(template.id)

        print("\n✅ Complete orphaned agent workflow test passed")

    async def test_marketplace_filtering_with_multiple_scenarios(self):
        """
        Test marketplace with mixed scenarios:
        - Original public agents (should show)
        - Active imports (should show)
        - Orphaned imports (should NOT show)
        """
        # Arrange
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        sharing_service = AgentSharingService(instance_repo, template_repo)
        facade = AgentManagementFacade(
            template_repo,
            instance_repo,
            sharing_service=sharing_service
        )

        print("\n🔹 Setting up mixed marketplace scenario")

        # Create template
        template = create_test_template("e2e-mixed-marketplace")
        template_repo.save(template)

        # Scenario 1: Original public agent (should show)
        user_1 = UserId.from_string(str(uuid4()))
        instance_1 = facade.get_or_create_instance(user_1, template.slug)
        facade.share_agent(user_1, str(instance_1.id.value))
        print(f"  ✓ Created original public agent: {instance_1.id.value[:8]}")

        # Scenario 2: Active import (should show)
        user_2 = UserId.from_string(str(uuid4()))
        instance_2 = facade.get_or_create_instance(user_2, template.slug)
        share_token_2 = facade.share_agent(user_2, str(instance_2.id.value))

        user_3 = UserId.from_string(str(uuid4()))
        imported_active = facade.import_agent(share_token_2, user_3)
        print(f"  ✓ Created active import: {imported_active.id.value[:8]}")

        # Scenario 3: Orphaned import (should NOT show)
        user_4 = UserId.from_string(str(uuid4()))
        instance_4 = facade.get_or_create_instance(user_4, template.slug)
        share_token_4 = facade.share_agent(user_4, str(instance_4.id.value))

        user_5 = UserId.from_string(str(uuid4()))
        imported_orphan = facade.import_agent(share_token_4, user_5)

        # Delete original to create orphan
        facade.delete_instance(user_4, str(instance_4.id.value))
        print(f"  ✓ Created orphaned import: {imported_orphan.id.value[:8]}")

        # Act - Query marketplace
        print("\n🔹 Querying marketplace")
        marketplace = instance_repo.find_public_instances(limit=100, offset=0)
        marketplace_ids = [inst.id.value for inst in marketplace]

        # Assert - Verify filtering
        print("\n🔹 Verifying marketplace contents")

        # Original public agent should be present
        assert instance_1.id.value in marketplace_ids, \
            "Original public agent should be in marketplace"
        print("  ✓ Original agent visible")

        # Active import's original should be present
        assert instance_2.id.value in marketplace_ids, \
            "Original of active import should be in marketplace"
        print("  ✓ Active import's original visible")

        # Active import should be present
        assert imported_active.id.value in marketplace_ids, \
            "Active import should be in marketplace"
        print("  ✓ Active import visible")

        # Orphaned import should NOT be present
        assert imported_orphan.id.value not in marketplace_ids, \
            "Orphaned import should NOT be in marketplace"
        print("  ✓ Orphaned import hidden")

        # Cleanup
        instance_repo.delete(imported_orphan.id)
        instance_repo.delete(imported_active.id)
        instance_repo.delete(instance_2.id)
        instance_repo.delete(instance_1.id)
        template_repo.delete(template.id)

        print("\n✅ Mixed marketplace scenario test passed")
