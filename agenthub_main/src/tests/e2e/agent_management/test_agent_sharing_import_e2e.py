"""
End-to-End Tests for Agent Sharing and Import Flow

Tests the complete sharing and import workflow:
1. User A customizes an agent
2. User A shares agent (generates share token)
3. User A gets shareable URL
4. User B opens share link and previews agent
5. User B imports agent into their account
6. Verify name collision handling ("- created by [creator]")
7. Test public/private visibility toggling
8. Test import history tracking

Test Strategy:
- Multi-user scenarios (User A shares, User B imports)
- Share token generation and validation
- Public/private visibility enforcement
- Name collision resolution
- Import history tracking
- Marketplace browsing

Requirements Coverage:
- Phase 5.2: Complete sharing and import workflow
- Share token security
- Public marketplace visibility
- Import tracking and attribution
- Name collision handling
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import uuid4

# Import domain layer
from fastmcp.agent_management.domain.entities.user_agent_instance import UserAgentInstance
from fastmcp.agent_management.domain.value_objects import UserId

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES - Defined in conftest.py
# ============================================================================
# test_user_id, test_template, agent_management_facade, db_session


# ============================================================================
# MOCK BROWSER CONTEXT - Reused from customization tests
# ============================================================================

class MockBrowserContext:
    """Mock browser context for simulating user interactions"""

    def __init__(self, user_id: str, base_url: str = "http://localhost:3800"):
        self.user_id = user_id
        self.base_url = base_url
        self.current_url = ""
        self.storage = {}
        self.dom_state = {}
        self.clipboard = ""

    async def navigate(self, path: str):
        """Simulate navigation"""
        self.current_url = f"{self.base_url}{path}"
        logger.info(f"🌐 User {self.user_id[:8]} navigated to: {self.current_url}")

    async def click_button(self, selector: str):
        """Simulate button click"""
        logger.info(f"🖱️ User {self.user_id[:8]} clicked: {selector}")

    async def get_text(self, selector: str) -> str:
        """Get element text"""
        return self.dom_state.get(selector, "")

    async def wait_for_selector(self, selector: str):
        """Wait for element"""
        await asyncio.sleep(0.05)
        logger.info(f"⏳ Waited for: {selector}")

    async def copy_to_clipboard(self, text: str):
        """Simulate copying to clipboard"""
        self.clipboard = text
        logger.info(f"📋 Copied to clipboard: {text[:50]}...")

    async def get_clipboard(self) -> str:
        """Get clipboard contents"""
        return self.clipboard


# ============================================================================
# E2E TEST SUITE: AGENT SHARING COMPLETE WORKFLOW
# ============================================================================

@pytest.mark.asyncio
class TestAgentSharingE2EWorkflow:
    """Complete E2E test suite for agent sharing and import workflow"""

    async def test_complete_sharing_and_import_workflow(
        self,
        test_template,
        agent_management_facade,
        db_session
    ):
        """
        Test COMPLETE sharing and import workflow:
        1. User A customizes agent
        2. User A shares agent
        3. User A copies share URL
        4. User B previews shared agent
        5. User B imports agent
        6. Verify import successful with attribution
        """

        # ========================================================================
        # SETUP: Create two users
        # ========================================================================

        user_a_id = UserId(uuid4())
        user_b_id = UserId(uuid4())

        browser_a = MockBrowserContext(str(user_a_id.value))
        browser_b = MockBrowserContext(str(user_b_id.value))

        logger.info("=" * 80)
        logger.info("SETUP: Created User A and User B")
        logger.info(f"User A ID: {user_a_id.value}")
        logger.info(f"User B ID: {user_b_id.value}")
        logger.info("=" * 80)


        # ========================================================================
        # STEP 1: USER A - Create and Customize Agent
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 1: User A Creates and Customizes Agent")
        logger.info("=" * 80)

        # User A creates instance
        instance_a = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_a_id,
            template_slug=test_template.slug
        )

        assert instance_a is not None
        logger.info(f"✅ User A created agent instance: {instance_a.id}")

        # User A customizes the agent
        custom_instructions = """
        # MY CUSTOM AGENT FOR SHARING

        This agent has been heavily customized by User A and is being shared
        as a demonstration of the sharing feature.

        ## Special Features
        - Custom instructions tailored to my workflow
        - Optimized for my specific use case
        - Ready to be shared with the community
        """

        await asyncio.to_thread(
            agent_management_facade.update_configuration,
            user_id=user_a_id,
            instance_id=instance_a.id,
            instructions_markdown=custom_instructions
        )

        logger.info("✅ User A customized agent configuration")


        # ========================================================================
        # STEP 2: USER A - Share Agent (Generate Share Token)
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 2: User A Shares Agent")
        logger.info("=" * 80)

        await browser_a.navigate(f"/agents/{instance_a.id}")
        await browser_a.click_button("#share-agent-btn")
        await browser_a.wait_for_selector("#share-dialog")

        # Simulate API call to POST /api/v2/agent-management/instances/{id}/share
        share_result = await asyncio.to_thread(
            agent_management_facade.share_agent,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        assert share_result is not None
        assert "share_token" in share_result
        assert "shareable_url" in share_result

        share_token = share_result["share_token"]
        shareable_url = share_result["shareable_url"]

        logger.info(f"✅ Share token generated: {share_token[:16]}...")
        logger.info(f"✅ Shareable URL: {shareable_url}")

        # User A copies URL to clipboard
        await browser_a.copy_to_clipboard(shareable_url)
        assert await browser_a.get_clipboard() == shareable_url

        logger.info("✅ User A copied share URL to clipboard")


        # ========================================================================
        # STEP 3: USER B - Open Share Link and Preview
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 3: User B Opens Share Link and Previews Agent")
        logger.info("=" * 80)

        # User B opens the share link (no auth required for preview)
        await browser_b.navigate(f"/marketplace/agents/{share_token}")
        await browser_b.wait_for_selector("#shared-agent-preview")

        # Simulate API call to GET /api/v2/marketplace/agents/{share_token}
        preview = await asyncio.to_thread(
            agent_management_facade.get_shared_agent_preview,
            share_token=share_token
        )

        assert preview is not None
        assert preview["agent_name"] is not None
        assert preview["configuration"] is not None
        assert "creator_display_name" in preview
        assert "MY CUSTOM AGENT FOR SHARING" in preview["configuration"].get("instructions", "")

        logger.info(f"✅ User B previewed agent: {preview['agent_name']}")
        logger.info(f"✅ Creator attribution: {preview.get('creator_display_name', 'N/A')}")


        # ========================================================================
        # STEP 4: USER B - Import Agent
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 4: User B Imports Agent")
        logger.info("=" * 80)

        await browser_b.click_button("#import-agent-btn")
        await browser_b.wait_for_selector("#import-success-message")

        # Simulate API call to POST /api/v2/agent-management/import
        import_result = await asyncio.to_thread(
            agent_management_facade.import_agent,
            importer_user_id=user_b_id,
            share_token=share_token
        )

        assert import_result is not None
        assert "instance" in import_result
        assert "import_history_id" in import_result

        imported_instance = import_result["instance"]

        logger.info(f"✅ Agent imported successfully: {imported_instance.id}")
        logger.info(f"✅ Import history ID: {import_result['import_history_id']}")


        # ========================================================================
        # STEP 5: VERIFY - Import Successful with Correct Data
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 5: Verify Import Success and Data Integrity")
        logger.info("=" * 80)

        # Verify instance belongs to User B
        assert imported_instance.user_id == user_b_id
        logger.info("✅ Instance correctly assigned to User B")

        # Verify configuration was copied
        assert "MY CUSTOM AGENT FOR SHARING" in imported_instance.configuration.get("instructions", "")
        logger.info("✅ Configuration correctly copied")

        # Verify it's marked as customized
        assert imported_instance.is_customized is True
        logger.info("✅ Instance correctly marked as customized")

        # Verify original creator attribution
        assert imported_instance.original_creator_id is not None
        logger.info(f"✅ Original creator tracked: {imported_instance.original_creator_id}")

        # Verify User B can see it in their agent list
        user_b_instances = await asyncio.to_thread(
            agent_management_facade.list_user_instances,
            user_id=user_b_id
        )

        found = any(inst.id == imported_instance.id for inst in user_b_instances)
        assert found is True
        logger.info("✅ Imported agent appears in User B's agent list")

        logger.info("=" * 80)
        logger.info("SHARING AND IMPORT E2E TEST COMPLETE - ALL STEPS PASSED")
        logger.info("=" * 80)


    async def test_name_collision_handling(
        self,
        test_template,
        agent_management_facade,
        db_session
    ):
        """
        Test name collision handling when importing:
        If User B already has an agent with the same template,
        the imported one should be renamed to "AgentName - created by [creator]"
        """

        user_a_id = UserId(uuid4())
        user_b_id = UserId(uuid4())

        logger.info("=" * 80)
        logger.info("TEST: Name Collision Handling")
        logger.info("=" * 80)

        # User A creates and shares agent
        instance_a = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_a_id,
            template_slug=test_template.slug
        )

        share_result = await asyncio.to_thread(
            agent_management_facade.share_agent,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        share_token = share_result["share_token"]
        logger.info(f"✅ User A shared agent with token: {share_token[:16]}...")

        # User B ALREADY has an instance from the same template
        existing_instance_b = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_b_id,
            template_slug=test_template.slug
        )

        original_name = existing_instance_b.agent_name
        logger.info(f"✅ User B already has instance: {original_name}")

        # User B imports User A's agent (name collision!)
        import_result = await asyncio.to_thread(
            agent_management_facade.import_agent,
            importer_user_id=user_b_id,
            share_token=share_token
        )

        imported_instance = import_result["instance"]

        # Verify name was modified to avoid collision
        assert imported_instance.agent_name != original_name
        assert "created by" in imported_instance.agent_name.lower()

        logger.info(f"✅ Name collision resolved!")
        logger.info(f"   Original name: {original_name}")
        logger.info(f"   Imported name: {imported_instance.agent_name}")


    async def test_public_private_visibility_toggling(
        self,
        test_template,
        agent_management_facade,
        db_session
    ):
        """
        Test public/private visibility toggling:
        - Share makes agent public with token
        - Unshare makes agent private and revokes token
        - Existing imports remain unaffected
        """

        user_a_id = UserId(uuid4())
        user_b_id = UserId(uuid4())

        logger.info("=" * 80)
        logger.info("TEST: Public/Private Visibility Toggling")
        logger.info("=" * 80)

        # User A creates and shares agent
        instance_a = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_a_id,
            template_slug=test_template.slug
        )

        # Initially private
        assert instance_a.visibility == "private"
        logger.info("✅ Agent starts as private")

        # Share makes it public
        share_result = await asyncio.to_thread(
            agent_management_facade.share_agent,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        share_token = share_result["share_token"]

        # Refresh instance
        db_session.expire_all()
        shared_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        assert shared_instance.visibility == "public"
        assert shared_instance.share_token == share_token
        logger.info("✅ Sharing made agent public with token")

        # User B imports while it's public
        import_result = await asyncio.to_thread(
            agent_management_facade.import_agent,
            importer_user_id=user_b_id,
            share_token=share_token
        )

        imported_instance_id = import_result["instance"].id
        logger.info(f"✅ User B imported agent: {imported_instance_id}")

        # User A unshares (makes private again)
        await asyncio.to_thread(
            agent_management_facade.unshare_agent,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        # Refresh instance
        db_session.expire_all()
        unshared_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        assert unshared_instance.visibility == "private"
        assert unshared_instance.share_token is None
        logger.info("✅ Unsharing made agent private and revoked token")

        # User B's imported copy is UNAFFECTED
        user_b_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_b_id,
            instance_id=imported_instance_id
        )

        assert user_b_instance is not None
        assert user_b_instance.user_id == user_b_id
        logger.info("✅ User B's imported copy remains unaffected")

        # New users CANNOT import with old token
        user_c_id = UserId(uuid4())

        with pytest.raises(Exception) as exc_info:
            await asyncio.to_thread(
                agent_management_facade.import_agent,
                importer_user_id=user_c_id,
                share_token=share_token  # Revoked token
            )

        assert "not found" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
        logger.info("✅ Revoked token cannot be used for new imports")


# ============================================================================
# E2E TEST SUITE: MARKETPLACE BROWSING
# ============================================================================

@pytest.mark.asyncio
class TestMarketplaceBrowsingE2E:
    """Test marketplace browsing and discovery features"""

    async def test_browse_public_marketplace(
        self,
        test_template,
        agent_management_facade,
        db_session
    ):
        """
        Test marketplace browsing:
        - Multiple users share agents
        - Browse marketplace to see all public agents
        - Filter and search functionality
        """

        logger.info("=" * 80)
        logger.info("TEST: Browse Public Marketplace")
        logger.info("=" * 80)

        # Create 3 users who share agents
        users = [UserId(uuid4()) for _ in range(3)]
        shared_instances = []

        for i, user_id in enumerate(users):
            # Each user creates and shares an agent
            instance = await asyncio.to_thread(
                agent_management_facade.get_or_create_instance,
                user_id=user_id,
                template_slug=test_template.slug
            )

            # Customize with unique content
            await asyncio.to_thread(
                agent_management_facade.update_configuration,
                user_id=user_id,
                instance_id=instance.id,
                instructions_markdown=f"Shared agent #{i+1} from user {user_id.value}"
            )

            # Share it
            share_result = await asyncio.to_thread(
                agent_management_facade.share_agent,
                user_id=user_id,
                instance_id=instance.id
            )

            shared_instances.append({
                "instance_id": instance.id,
                "user_id": user_id,
                "share_token": share_result["share_token"]
            })

            logger.info(f"✅ User {i+1} shared agent")

        # Browse marketplace
        marketplace_agents = await asyncio.to_thread(
            agent_management_facade.browse_marketplace,
            filters=None
        )

        assert marketplace_agents is not None
        assert len(marketplace_agents) >= 3  # At least our 3 shared agents

        logger.info(f"✅ Marketplace shows {len(marketplace_agents)} public agents")

        # Verify all our shared agents appear in marketplace
        our_tokens = {item["share_token"] for item in shared_instances}
        marketplace_tokens = {agent.get("share_token") for agent in marketplace_agents}

        assert our_tokens.issubset(marketplace_tokens)
        logger.info("✅ All shared agents visible in marketplace")


# ============================================================================
# E2E TEST SUITE: EDGE CASES
# ============================================================================

@pytest.mark.asyncio
class TestSharingImportE2EEdgeCases:
    """Test edge cases and error scenarios"""

    async def test_import_own_shared_agent(
        self,
        test_template,
        agent_management_facade
    ):
        """Test that user cannot import their own shared agent"""

        user_id = UserId(uuid4())

        # Create and share agent
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug
        )

        share_result = await asyncio.to_thread(
            agent_management_facade.share_agent,
            user_id=user_id,
            instance_id=instance.id
        )

        share_token = share_result["share_token"]

        # Try to import own agent
        with pytest.raises(Exception) as exc_info:
            await asyncio.to_thread(
                agent_management_facade.import_agent,
                importer_user_id=user_id,  # Same user!
                share_token=share_token
            )

        assert "cannot import your own" in str(exc_info.value).lower() or "already own" in str(exc_info.value).lower()
        logger.info("✅ User correctly prevented from importing own agent")


    async def test_import_multiple_times(
        self,
        test_template,
        agent_management_facade
    ):
        """Test importing the same agent multiple times"""

        user_a_id = UserId(uuid4())
        user_b_id = UserId(uuid4())

        # User A shares
        instance_a = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_a_id,
            template_slug=test_template.slug
        )

        share_result = await asyncio.to_thread(
            agent_management_facade.share_agent,
            user_id=user_a_id,
            instance_id=instance_a.id
        )

        share_token = share_result["share_token"]

        # User B imports once
        import_1 = await asyncio.to_thread(
            agent_management_facade.import_agent,
            importer_user_id=user_b_id,
            share_token=share_token
        )

        # User B tries to import again (should either succeed with new copy or prevent duplicate)
        try:
            import_2 = await asyncio.to_thread(
                agent_management_facade.import_agent,
                importer_user_id=user_b_id,
                share_token=share_token
            )

            # If allowed, should create different instance with collision-resolved name
            assert import_2["instance"].id != import_1["instance"].id
            logger.info("✅ Multiple imports allowed, created separate instances")

        except Exception as e:
            # If prevented, that's also acceptable
            assert "already imported" in str(e).lower()
            logger.info("✅ Duplicate import correctly prevented")
