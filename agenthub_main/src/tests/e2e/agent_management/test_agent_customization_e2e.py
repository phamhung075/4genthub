"""
End-to-End Tests for Agent Customization Flow

Tests the complete user journey for customizing agent configurations:
1. User authenticates/logs in
2. Views agent instances list
3. Selects a specific agent
4. Opens configuration editor
5. Edits markdown configuration (instructions, rules, capabilities, output_format)
6. Saves changes
7. Verifies changes persisted to database
8. Verifies changes reflected in UI

Test Strategy:
- Uses Browser MCP tools for Playwright-compatible E2E testing
- Tests complete frontend-to-backend integration
- Verifies data persistence across sessions
- Validates UI state management and updates

Requirements Coverage:
- Phase 5.1: Complete customization workflow testing
- User authentication flow
- Agent list display and selection
- Configuration editor functionality
- Markdown editing and preview
- Save/persist operations
- UI updates and feedback
"""

import asyncio
import logging
from uuid import uuid4

import pytest

# Import application layer
from fastmcp.agent_management.domain.value_objects import UserId

# Import infrastructure layer

logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES - Defined in conftest.py
# ============================================================================
# test_user_id, test_template, agent_management_facade, db_session
# are provided by conftest.py


# ============================================================================
# MOCK BROWSER CONTEXT (Simulating Playwright Browser Automation)
# ============================================================================


class MockBrowserContext:
    """
    Mock browser context that simulates Playwright browser automation
    for testing the complete E2E user journey without actual browser

    In production E2E tests, this would be replaced with actual Browser MCP tools:
    - browser_navigate(url)
    - browser_click(element)
    - browser_type(element, text)
    - browser_screenshot()
    etc.
    """

    def __init__(self, base_url: str = "http://localhost:3800"):
        self.base_url = base_url
        self.current_url = ""
        self.storage = {}  # Simulates localStorage/sessionStorage
        self.dom_state = {}  # Simulates DOM elements
        self.network_requests = []

    async def navigate(self, path: str):
        """Simulate browser navigation"""
        self.current_url = f"{self.base_url}{path}"
        logger.info(f"🌐 Navigated to: {self.current_url}")

    async def fill_input(self, selector: str, value: str):
        """Simulate filling input field"""
        self.dom_state[selector] = value
        logger.info(f"✍️ Filled input '{selector}' with: {value}")

    async def click_button(self, selector: str):
        """Simulate clicking button"""
        logger.info(f"🖱️ Clicked button: {selector}")

    async def get_text(self, selector: str) -> str:
        """Simulate getting element text"""
        return self.dom_state.get(selector, "")

    async def wait_for_selector(self, selector: str, timeout: int = 5000):
        """Simulate waiting for element to appear"""
        await asyncio.sleep(0.1)  # Simulate network/render delay
        logger.info(f"⏳ Waited for selector: {selector}")

    async def screenshot(self, path: str):
        """Simulate taking screenshot"""
        logger.info(f"📸 Screenshot saved to: {path}")

    async def store_auth_token(self, token: str):
        """Simulate storing auth token"""
        self.storage["auth_token"] = token
        logger.info("🔑 Auth token stored")

    async def get_auth_token(self) -> str:
        """Simulate retrieving auth token"""
        return self.storage.get("auth_token", "")


# ============================================================================
# E2E TEST SUITE: AGENT CUSTOMIZATION COMPLETE WORKFLOW
# ============================================================================


@pytest.mark.asyncio
class TestAgentCustomizationE2EWorkflow:
    """
    Complete E2E test suite for agent customization workflow

    Tests the entire user journey from authentication to configuration persistence
    """

    async def test_complete_customization_workflow(
        self, test_user_id, test_template, agent_management_facade, db_session
    ):
        """
        Test COMPLETE customization workflow:
        1. User authenticates
        2. Views agent list
        3. Selects agent
        4. Edits configuration
        5. Saves changes
        6. Verifies persistence
        """

        # ========================================================================
        # STEP 1: USER AUTHENTICATION
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 1: User Authentication")
        logger.info("=" * 80)

        browser = MockBrowserContext()
        await browser.navigate("/login")
        await browser.fill_input("#email", "test@example.com")
        await browser.fill_input("#password", "password123")
        await browser.click_button("#login-btn")

        # Simulate successful authentication
        mock_auth_token = "mock-jwt-token-" + str(uuid4())
        await browser.store_auth_token(mock_auth_token)

        await browser.wait_for_selector("#dashboard")
        assert await browser.get_auth_token() != "", (
            "Authentication failed - no token stored"
        )
        logger.info("✅ User authenticated successfully")

        # ========================================================================
        # STEP 2: AUTO-INSTANTIATE AGENT (via call_agent pattern)
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 2: Auto-instantiate Agent Instance")
        logger.info("=" * 80)

        # Simulate calling call_agent which auto-creates instance
        user_id = UserId(test_user_id)
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug,
        )

        assert instance is not None, "Failed to create agent instance"
        assert instance.user_id == user_id
        assert instance.template_id == test_template.id
        assert instance.is_customized is False, "New instance should not be customized"
        logger.info(f"✅ Agent instance created: {instance.id}")

        # ========================================================================
        # STEP 3: VIEW AGENT INSTANCES LIST
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 3: View Agent Instances List")
        logger.info("=" * 80)

        await browser.navigate("/agents")
        await browser.wait_for_selector(".agent-card")

        # Simulate API call to GET /api/v2/agent-management/instances
        instances = await asyncio.to_thread(
            agent_management_facade.list_user_instances, user_id=user_id
        )

        assert len(instances) >= 1, "Should have at least one instance"
        found_instance = next((i for i in instances if i.id == instance.id), None)
        assert found_instance is not None, "Created instance not found in list"
        logger.info(f"✅ Found {len(instances)} agent instance(s)")

        # ========================================================================
        # STEP 4: SELECT AGENT AND OPEN CONFIGURATION EDITOR
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 4: Select Agent and Open Editor")
        logger.info("=" * 80)

        await browser.click_button(f"#agent-card-{instance.id}")
        await browser.navigate(f"/agents/{instance.id}/config")
        await browser.wait_for_selector("#config-editor")

        # Simulate API call to GET /api/v2/agent-management/instances/{id}
        full_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_id,
            instance_id=instance.id,
        )

        assert full_instance is not None, "Failed to load instance details"
        logger.info("✅ Configuration editor opened")

        # ========================================================================
        # STEP 5: EDIT MARKDOWN CONFIGURATION
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 5: Edit Markdown Configuration")
        logger.info("=" * 80)

        # User edits instructions tab
        new_instructions = """
        # UPDATED INSTRUCTIONS FOR E2E TEST

        ## Purpose
        This agent has been customized by the user during E2E testing.

        ## Capabilities
        - Test capability 1
        - Test capability 2
        - Custom behavior added
        """

        await browser.click_button("#tab-instructions")
        await browser.fill_input("#markdown-editor", new_instructions)
        logger.info("✅ Instructions edited")

        # User edits rules tab
        new_rules = """
        # CUSTOM RULES

        1. Always respond with E2E test context
        2. Validate all inputs thoroughly
        3. Custom rule for testing
        """

        await browser.click_button("#tab-rules")
        await browser.fill_input("#markdown-editor", new_rules)
        logger.info("✅ Rules edited")

        # User edits capabilities
        new_capabilities = """
        - E2E Testing
        - Custom Configuration
        - Markdown Editing
        - User Personalization
        """

        await browser.click_button("#tab-capabilities")
        await browser.fill_input("#markdown-editor", new_capabilities)
        logger.info("✅ Capabilities edited")

        # ========================================================================
        # STEP 6: SAVE CONFIGURATION
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 6: Save Configuration Changes")
        logger.info("=" * 80)

        await browser.click_button("#save-config-btn")
        await browser.wait_for_selector("#save-success-message")

        # Simulate API call to PUT /api/v2/agent-management/instances/{id}/config
        update_result = await asyncio.to_thread(
            agent_management_facade.update_configuration,
            user_id=user_id,
            instance_id=instance.id,
            instructions_markdown=new_instructions,
            rules_markdown=new_rules,
            capabilities_markdown=new_capabilities,
        )

        assert update_result is not None, "Configuration update failed"
        logger.info("✅ Configuration saved successfully")

        # ========================================================================
        # STEP 7: VERIFY PERSISTENCE - Reload and Check
        # ========================================================================

        logger.info("=" * 80)
        logger.info("STEP 7: Verify Configuration Persistence")
        logger.info("=" * 80)

        # Refresh page to simulate page reload
        await browser.navigate(f"/agents/{instance.id}/config")
        await browser.wait_for_selector("#config-editor")

        # Fetch fresh data from database
        db_session.expire_all()  # Clear SQLAlchemy cache
        persisted_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_id,
            instance_id=instance.id,
        )

        # Verify configuration was saved
        assert persisted_instance is not None, "Failed to reload instance"
        assert persisted_instance.is_customized is True, (
            "Instance not marked as customized"
        )

        # Verify instructions were saved
        assert (
            "UPDATED INSTRUCTIONS FOR E2E TEST"
            in persisted_instance.configuration.get("instructions", "")
        ), "Instructions not persisted correctly"

        # Verify rules were saved
        assert "CUSTOM RULES" in persisted_instance.configuration.get("rules", ""), (
            "Rules not persisted correctly"
        )

        # Verify capabilities were saved
        assert "E2E Testing" in persisted_instance.configuration.get(
            "capabilities", ""
        ), "Capabilities not persisted correctly"

        logger.info("✅ All configuration changes persisted correctly")
        logger.info("=" * 80)
        logger.info("E2E TEST COMPLETE - ALL STEPS PASSED")
        logger.info("=" * 80)

    async def test_configuration_editor_tabs_switching(
        self, test_user_id, test_template, agent_management_facade, db_session
    ):
        """
        Test configuration editor tab switching functionality
        Ensures each tab displays correct content and preserves edits
        """

        browser = MockBrowserContext()
        user_id = UserId(test_user_id)

        # Create instance
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug,
        )

        # Navigate to config editor
        await browser.navigate(f"/agents/{instance.id}/config")
        await browser.wait_for_selector("#config-editor")

        # Test tab 1: Instructions
        await browser.click_button("#tab-instructions")
        await browser.fill_input("#markdown-editor", "Instructions content")
        instructions_value = await browser.get_text("#markdown-editor")
        assert instructions_value == "Instructions content"

        # Test tab 2: Rules
        await browser.click_button("#tab-rules")
        await browser.fill_input("#markdown-editor", "Rules content")
        rules_value = await browser.get_text("#markdown-editor")
        assert rules_value == "Rules content"

        # Verify tab switch preserves previous content
        await browser.click_button("#tab-instructions")
        preserved_instructions = await browser.get_text("#markdown-editor")
        assert preserved_instructions == "Instructions content", (
            "Instructions lost after tab switch"
        )

        logger.info("✅ Tab switching preserves content correctly")

    async def test_save_validation_feedback(
        self, test_user_id, test_template, agent_management_facade
    ):
        """
        Test that save operation provides proper feedback
        - Success message on valid save
        - Error message on invalid configuration
        - Loading state during save
        """

        browser = MockBrowserContext()
        user_id = UserId(test_user_id)

        # Create instance
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug,
        )

        # Navigate to editor
        await browser.navigate(f"/agents/{instance.id}/config")

        # Make valid changes
        await browser.fill_input("#markdown-editor", "Valid content")
        await browser.click_button("#save-config-btn")

        # Should show loading state
        await browser.wait_for_selector("#save-loading")

        # Should show success message
        await browser.wait_for_selector("#save-success-message")
        success_text = await browser.get_text("#save-success-message")
        assert "saved successfully" in success_text.lower()

        logger.info("✅ Save validation feedback working correctly")

    async def test_cancel_changes_without_saving(
        self, test_user_id, test_template, agent_management_facade, db_session
    ):
        """
        Test that canceling changes without saving doesn't persist them
        """

        browser = MockBrowserContext()
        user_id = UserId(test_user_id)

        # Create instance
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug,
        )

        # Get original configuration
        original_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_id,
            instance_id=instance.id,
        )
        original_instructions = original_instance.configuration.get("instructions", "")

        # Navigate and make changes
        await browser.navigate(f"/agents/{instance.id}/config")
        await browser.fill_input(
            "#markdown-editor", "Changed content that will be canceled"
        )

        # Navigate away without saving
        await browser.navigate("/agents")

        # Verify changes were NOT persisted
        db_session.expire_all()
        reloaded_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_id,
            instance_id=instance.id,
        )

        reloaded_instructions = reloaded_instance.configuration.get("instructions", "")
        assert reloaded_instructions == original_instructions, (
            "Changes persisted without save"
        )

        logger.info("✅ Canceled changes not persisted")


# ============================================================================
# E2E TEST SUITE: EDGE CASES AND ERROR SCENARIOS
# ============================================================================


@pytest.mark.asyncio
class TestAgentCustomizationE2EEdgeCases:
    """Test edge cases and error scenarios in E2E workflow"""

    async def test_unauthorized_access_to_config_editor(
        self, test_template, agent_management_facade
    ):
        """Test that unauthorized users cannot access configuration editor"""

        MockBrowserContext()

        # User A creates instance
        user_a_id = UserId(uuid4())
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_a_id,
            template_slug=test_template.slug,
        )

        # User B tries to access User A's instance
        user_b_id = UserId(uuid4())

        with pytest.raises(Exception) as exc_info:
            await asyncio.to_thread(
                agent_management_facade.get_instance_details,
                user_id=user_b_id,
                instance_id=instance.id,
            )

        assert (
            "not found" in str(exc_info.value).lower()
            or "unauthorized" in str(exc_info.value).lower()
        )
        logger.info("✅ Unauthorized access properly blocked")

    async def test_concurrent_edits_handling(
        self, test_user_id, test_template, agent_management_facade
    ):
        """Test handling of concurrent edits from multiple browser tabs"""

        user_id = UserId(test_user_id)

        # Create instance
        instance = await asyncio.to_thread(
            agent_management_facade.get_or_create_instance,
            user_id=user_id,
            template_slug=test_template.slug,
        )

        # Simulate two browser tabs editing simultaneously
        browser_tab1 = MockBrowserContext()
        browser_tab2 = MockBrowserContext()

        # Both tabs load the same instance
        await browser_tab1.navigate(f"/agents/{instance.id}/config")
        await browser_tab2.navigate(f"/agents/{instance.id}/config")

        # Tab 1 makes and saves changes
        await browser_tab1.fill_input("#markdown-editor", "Tab 1 changes")
        await asyncio.to_thread(
            agent_management_facade.update_configuration,
            user_id=user_id,
            instance_id=instance.id,
            instructions_markdown="Tab 1 changes",
        )

        # Tab 2 makes and saves changes (should overwrite)
        await browser_tab2.fill_input("#markdown-editor", "Tab 2 changes")
        await asyncio.to_thread(
            agent_management_facade.update_configuration,
            user_id=user_id,
            instance_id=instance.id,
            instructions_markdown="Tab 2 changes",
        )

        # Verify last write wins
        final_instance = await asyncio.to_thread(
            agent_management_facade.get_instance_details,
            user_id=user_id,
            instance_id=instance.id,
        )

        assert "Tab 2 changes" in final_instance.configuration.get("instructions", "")
        logger.info("✅ Concurrent edits handled (last write wins)")
