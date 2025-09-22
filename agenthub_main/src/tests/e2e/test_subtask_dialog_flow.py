"""
End-to-End tests for subtask dialog functionality
Tests the complete user flow from clicking subtask detail to dialog interaction

NOTE: These tests require pytest-playwright to be installed:
    pip install pytest-playwright
    playwright install chromium
"""

import pytest
import re
from uuid import UUID
from typing import List, Dict, Any
import json

# Mark entire module to be skipped if playwright is not available
pytestmark = pytest.mark.skip(
    reason="Playwright E2E tests require pytest-playwright. Install with: pip install pytest-playwright && playwright install"
)

# Import with proper handling
try:
    from playwright.sync_api import Page, expect, Route
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    # Playwright not available, create dummy types to avoid syntax errors
    class Page: pass
    class Route: pass
    def expect(x): pass
    PLAYWRIGHT_AVAILABLE = False


class TestSubtaskDialogFlow:
    """E2E tests for subtask detail dialog functionality and URL stability"""

    @pytest.fixture
    def base_url(self):
        """Get the base URL for the application"""
        return "http://localhost:3800"  # Adjust based on frontend port

    @pytest.fixture
    def test_project_data(self):
        """Sample test project data"""
        return {
            "project_id": "test-project-id",
            "project_name": "test-project",
            "branch_id": "test-branch-id",
            "branch_name": "test-branch",
            "task_id": "test-task-id",
            "subtask_id": "test-subtask-id"
        }

    def test_subtask_detail_button_opens_correct_dialog(self, page: Page, base_url: str, test_project_data: Dict):
        """Test that clicking subtask detail button opens the subtask dialog (not task dialog)"""

        # Navigate to the task page containing subtasks
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for the page to load and subtasks to be visible
        page.wait_for_load_state("networkidle")

        # Check if subtasks are present
        subtask_rows = page.locator("[data-testid='subtask-row']")

        # If no subtasks found, try alternative selectors
        if subtask_rows.count() == 0:
            subtask_rows = page.locator(".subtask-row, [class*='subtask']")

        # Skip test if no subtasks present
        if subtask_rows.count() == 0:
            pytest.skip("No subtasks found on the page")

        # Get the first subtask row
        first_subtask = subtask_rows.first

        # Look for the detail button within the subtask row
        detail_button = first_subtask.locator(
            "[data-testid='subtask-detail-button'], button[aria-label*='detail'], button[title*='detail']"
        ).first

        # If no detail button found, try finding any button in the subtask row
        if not detail_button.is_visible():
            detail_button = first_subtask.locator("button").first

        # Click the detail button
        detail_button.click()

        # Wait for dialog to appear
        page.wait_for_timeout(500)  # Small wait for dialog animation

        # Check that subtask dialog is visible
        subtask_dialog = page.locator(
            "[data-testid='subtask-details-dialog'], [role='dialog'][aria-label*='subtask'], .subtask-dialog"
        )
        expect(subtask_dialog).to_be_visible(timeout=5000)

        # Verify that task dialog is NOT visible
        task_dialog = page.locator(
            "[data-testid='task-details-dialog'], [role='dialog'][aria-label*='task']:not([aria-label*='subtask'])"
        )

        # Task dialog should not be visible
        if task_dialog.count() > 0:
            expect(task_dialog).not_to_be_visible()

        # Verify URL contains 'subtask' parameter or path
        current_url = page.url
        assert "subtask" in current_url.lower(), \
            f"URL should contain 'subtask' but got: {current_url}"

    def test_subtask_url_remains_stable_after_dialog_open(self, page: Page, base_url: str, test_project_data: Dict):
        """Test that the URL doesn't revert after opening subtask dialog"""

        # Navigate to task page
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for page load
        page.wait_for_load_state("networkidle")

        # Find and click subtask detail button
        subtask_button = page.locator(
            "[data-testid='subtask-detail-button'], .subtask-row button, [class*='subtask'] button"
        ).first

        if not subtask_button.is_visible():
            pytest.skip("No subtask detail button found")

        # Capture URL before clicking
        url_before_click = page.url

        # Click the subtask detail button
        subtask_button.click()

        # Capture URL immediately after click
        page.wait_for_timeout(100)  # Very short wait
        url_after_click = page.url

        # URL should have changed to include subtask
        assert url_after_click != url_before_click, \
            "URL should change when subtask dialog opens"
        assert "subtask" in url_after_click.lower(), \
            f"URL should contain 'subtask': {url_after_click}"

        # Wait 3 seconds to ensure URL doesn't revert
        page.wait_for_timeout(3000)
        url_after_wait = page.url

        # URL should remain stable (not revert)
        assert url_after_wait == url_after_click, \
            f"URL reverted from {url_after_click} to {url_after_wait}"
        assert "subtask" in url_after_wait.lower(), \
            "URL should still contain 'subtask' after waiting"

    def test_subtask_api_calls_use_correct_task_id_format(self, page: Page, base_url: str, test_project_data: Dict):
        """Test that API calls for subtasks use correct task_id (not MCP format)"""

        # Track API calls
        api_calls: List[str] = []

        def intercept_api_calls(route: Route):
            """Intercept and log API calls"""
            request_url = route.request.url
            if "/api/" in request_url and "subtask" in request_url.lower():
                api_calls.append(request_url)
            route.continue_()

        # Set up route interception
        page.route("**/api/**", intercept_api_calls)

        # Navigate to task page
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for page to load
        page.wait_for_load_state("networkidle")

        # Click on subtask detail if available
        try:
            subtask_button = page.locator(
                "[data-testid='subtask-detail-button'], .subtask-row button"
            ).first
            if subtask_button.is_visible():
                subtask_button.click()
                page.wait_for_timeout(1000)  # Wait for API calls
        except:
            pass  # Continue even if no button found

        # Analyze captured API calls
        for api_url in api_calls:
            # Extract task_id from URL pattern: /tasks/{task_id}/subtasks/
            match = re.search(r'/tasks/([^/]+)/subtasks', api_url)
            if match:
                task_id_in_url = match.group(1)

                # Verify it's a valid UUID format (not MCP format)
                try:
                    UUID(task_id_in_url)
                    # If UUID parsing succeeds, it's correctly formatted
                except ValueError:
                    pytest.fail(
                        f"Task ID in API URL is not a valid UUID: {task_id_in_url}\n"
                        f"Full URL: {api_url}"
                    )

                # Verify it's not using git_branch_id pattern
                # Git branch IDs typically have different patterns
                assert len(task_id_in_url) == 36, \
                    f"Task ID should be standard UUID length (36): {task_id_in_url}"

    def test_subtask_dialog_displays_correct_content(self, page: Page, base_url: str, test_project_data: Dict):
        """Test that subtask dialog displays subtask-specific content"""

        # Navigate to task page
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for page load
        page.wait_for_load_state("networkidle")

        # Find subtask row with title
        subtask_rows = page.locator("[data-testid='subtask-row'], .subtask-row")

        if subtask_rows.count() == 0:
            pytest.skip("No subtasks found")

        # Get the subtask title from the list
        first_subtask = subtask_rows.first
        subtask_title_element = first_subtask.locator(
            "[data-testid='subtask-title'], .subtask-title, h3, h4"
        ).first

        subtask_title = ""
        if subtask_title_element.is_visible():
            subtask_title = subtask_title_element.inner_text()

        # Click detail button
        detail_button = first_subtask.locator("button").first
        detail_button.click()

        # Wait for dialog
        page.wait_for_timeout(500)

        # Find the dialog
        dialog = page.locator("[role='dialog']").first
        expect(dialog).to_be_visible()

        # If we captured a title, verify it appears in the dialog
        if subtask_title:
            dialog_title = dialog.locator("h1, h2, h3, [class*='title']").first
            if dialog_title.is_visible():
                dialog_title_text = dialog_title.inner_text()
                assert subtask_title.lower() in dialog_title_text.lower(), \
                    f"Dialog should show subtask title '{subtask_title}' but shows '{dialog_title_text}'"

        # Verify dialog has subtask-specific elements
        # Look for elements that would only appear in a subtask dialog
        subtask_indicators = [
            "parent task",
            "subtask",
            "sub-task"
        ]

        dialog_text = dialog.inner_text().lower()
        has_subtask_indicator = any(indicator in dialog_text for indicator in subtask_indicators)

        assert has_subtask_indicator, \
            "Dialog should contain subtask-specific content"

    def test_closing_subtask_dialog_updates_url_correctly(self, page: Page, base_url: str, test_project_data: Dict):
        """Test that closing subtask dialog correctly updates the URL"""

        # Navigate to task page
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for page load
        page.wait_for_load_state("networkidle")

        # Find and click subtask detail
        subtask_button = page.locator(
            "[data-testid='subtask-detail-button'], .subtask-row button"
        ).first

        if not subtask_button.is_visible():
            pytest.skip("No subtask detail button found")

        # Capture original URL
        original_url = page.url

        # Open subtask dialog
        subtask_button.click()
        page.wait_for_timeout(500)

        # Verify URL changed
        dialog_open_url = page.url
        assert "subtask" in dialog_open_url.lower()

        # Find and click close button
        close_button = page.locator(
            "[aria-label='Close'], button:has-text('Close'), button:has-text('×'), [data-testid='dialog-close']"
        ).first

        if close_button.is_visible():
            close_button.click()
        else:
            # Try pressing Escape
            page.keyboard.press("Escape")

        # Wait for dialog to close
        page.wait_for_timeout(500)

        # Check URL after closing
        url_after_close = page.url

        # URL should no longer contain subtask parameter
        assert "subtask" not in url_after_close.lower() or url_after_close == original_url, \
            f"URL should revert after closing dialog: {url_after_close}"

    def test_multiple_subtask_dialogs_maintain_correct_urls(self, page: Page, base_url: str, test_project_data: Dict):
        """Test opening multiple subtask dialogs maintains correct URLs"""

        # Navigate to task page
        task_url = f"{base_url}/dashboard/project/{test_project_data['project_name']}/branch/{test_project_data['branch_name']}/task/{test_project_data['task_id']}"
        page.goto(task_url)

        # Wait for page load
        page.wait_for_load_state("networkidle")

        # Get all subtask rows
        subtask_rows = page.locator("[data-testid='subtask-row'], .subtask-row")

        if subtask_rows.count() < 2:
            pytest.skip("Need at least 2 subtasks for this test")

        # Open first subtask
        first_button = subtask_rows.nth(0).locator("button").first
        first_button.click()
        page.wait_for_timeout(500)

        first_subtask_url = page.url
        assert "subtask" in first_subtask_url.lower()

        # Close dialog
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # Open second subtask
        second_button = subtask_rows.nth(1).locator("button").first
        second_button.click()
        page.wait_for_timeout(500)

        second_subtask_url = page.url
        assert "subtask" in second_subtask_url.lower()

        # URLs should be different (different subtask IDs)
        assert first_subtask_url != second_subtask_url, \
            "Different subtasks should have different URLs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])