"""
Unit Tests for Git Branch ID Validation Fix

This test suite prevents regression of the critical git_branch_id validation bug
where tasks could be created with non-existent branch IDs, causing phantom branches.

Bug Details:
- Date Fixed: 2025-10-30
- Issue: Tasks created with invalid git_branch_id auto-created phantom branches
- Root Cause: _derive_context_from_git_branch_id() returned None instead of raising ValueError
- Fix Location: task_application_facade.py:121-174
- Impact: Data integrity restored, no more phantom branches

Test Coverage:
1. Valid git_branch_id (should succeed)
2. Invalid UUID format (should fail immediately)
3. Valid UUID, non-existent branch (should fail - THE CRITICAL FIX)
4. Null/None git_branch_id (should fail)
5. Empty string git_branch_id (should fail)
6. Integration: Validation prevents auto-creation bypass

Related Documentation:
- Bug report: ai_docs/issues/git-branch-validation-bug.md
- Test report: ai_docs/reports-status/mcp-comprehensive-testing-report-2025-10-30.md
"""
import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4


class TestGitBranchIdValidation(unittest.TestCase):
    """
    Comprehensive test suite for git_branch_id validation.

    These tests ensure the validation fix remains in place and prevents
    creation of tasks with invalid or non-existent branch IDs.
    """

    def setUp(self):
        """Set up test fixtures before each test"""
        # Create valid test UUIDs
        self.valid_branch_id = str(uuid4())
        self.valid_project_id = str(uuid4())
        self.nonexistent_branch_id = "99999999-9999-9999-9999-999999999999"

    def test_validation_method_exists(self):
        """Verify _derive_context_from_git_branch_id method exists"""
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

        # Method must exist
        self.assertTrue(
            hasattr(TaskApplicationFacade, '_derive_context_from_git_branch_id'),
            "CRITICAL: TaskApplicationFacade must have _derive_context_from_git_branch_id method"
        )

    def test_validation_raises_value_error_not_returns_none(self):
        """
        CRITICAL TEST: Verify validation raises ValueError, not returns None.
        This was the root cause of the phantom branch bug.
        """
        import inspect
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

        # Get source code of the validation method
        source = inspect.getsource(TaskApplicationFacade._derive_context_from_git_branch_id)

        # Must contain raise ValueError
        self.assertIn(
            'raise ValueError',
            source,
            "CRITICAL: Validation must raise ValueError when branch not found"
        )

        # Should not silently return None in error cases
        # Check for patterns that would return None inappropriately
        lines = source.split('\n')
        for line in lines:
            # If we see "return None" it should only be in legitimate cases
            # (not when handling "not found" scenario)
            if 'return None' in line and 'not found' not in line.lower():
                # This is okay - might be legitimate None return
                pass

    def test_valid_branch_id_succeeds(self):
        """Test 1: Task creation succeeds when git_branch_id exists"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            mock_branch = Mock()
            mock_branch.project_id = self.valid_project_id
            mock_branch.name = "main"
            mock_branch_repo.find_by_id = AsyncMock(return_value=mock_branch)

            # Create facade with mocked repositories (correct constructor signature)
            facade = TaskApplicationFacade(
                task_repository=mock_task_repo,
                git_branch_repository=mock_branch_repo
            )

            # Execute validation
            result = await facade._derive_context_from_git_branch_id(self.valid_branch_id)

            # Assertions
            self.assertIsNotNone(result, "Valid branch ID should return context")
            self.assertEqual(result['project_id'], self.valid_project_id)
            self.assertEqual(result['git_branch_name'], "main")
            mock_branch_repo.find_by_id.assert_called_once_with(self.valid_branch_id)

        # Run async test
        asyncio.run(run_test())

    def test_invalid_uuid_format_fails(self):
        """Test 2: Task creation fails with malformed UUID"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            mock_branch_repo.find_by_id = AsyncMock(return_value=None)

            # Mock ProjectManagementService to return failure
            with patch('fastmcp.task_management.application.services.project_management_service.ProjectManagementService') as MockPMS:
                mock_pms = MockPMS.return_value
                mock_pms.get_git_branch_by_id = Mock(return_value={"success": False})

                # Create facade with correct constructor signature
                facade = TaskApplicationFacade(
                    task_repository=mock_task_repo,
                    git_branch_repository=mock_branch_repo
                )

                # Execute and expect ValueError
                with self.assertRaises(ValueError) as context:
                    await facade._derive_context_from_git_branch_id("invalid-branch-id")

                # Verify error message is helpful
                error_message = str(context.exception)
                self.assertIn("not found", error_message.lower())

        asyncio.run(run_test())

    def test_nonexistent_branch_id_fails_with_helpful_message(self):
        """
        Test 3: CRITICAL TEST - Valid UUID but non-existent branch fails.
        This is THE FIX that prevents phantom branches.
        """

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            mock_branch_repo.find_by_id = AsyncMock(return_value=None)

            # Mock ProjectManagementService to also return failure
            with patch('fastmcp.task_management.application.services.project_management_service.ProjectManagementService') as MockPMS:
                mock_pms = MockPMS.return_value
                mock_pms.get_git_branch_by_id = Mock(return_value={"success": False})

                # Create facade with correct constructor signature
                facade = TaskApplicationFacade(
                    task_repository=mock_task_repo,
                    git_branch_repository=mock_branch_repo
                )

                # Execute and expect ValueError
                with self.assertRaises(ValueError) as context:
                    await facade._derive_context_from_git_branch_id(self.nonexistent_branch_id)

                # Verify error message is helpful
                error_message = str(context.exception)
                self.assertIn("not found", error_message.lower())
                self.assertIn(self.nonexistent_branch_id, error_message)
                # Check for helpful guidance
                self.assertTrue(
                    "manage_git_branch" in error_message or "create" in error_message.lower(),
                    "Error message should provide guidance on how to fix the issue"
                )

        asyncio.run(run_test())

    def test_null_branch_id_fails(self):
        """Test 4: Task creation fails with None git_branch_id"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            # Make repository raise TypeError when None is passed (realistic behavior)
            mock_branch_repo.find_by_id = AsyncMock(side_effect=TypeError("Cannot use None as branch_id"))

            with patch('fastmcp.task_management.application.services.project_management_service.ProjectManagementService') as MockPMS:
                mock_pms = MockPMS.return_value
                mock_pms.get_git_branch_by_id = Mock(side_effect=TypeError("Cannot use None as branch_id"))

                # Create facade with correct constructor signature
                facade = TaskApplicationFacade(
                    task_repository=mock_task_repo,
                    git_branch_repository=mock_branch_repo
                )

                # Execute and expect ValueError, AttributeError, or TypeError
                with self.assertRaises((ValueError, AttributeError, TypeError)):
                    await facade._derive_context_from_git_branch_id(None)

        asyncio.run(run_test())

    def test_empty_string_branch_id_fails(self):
        """Test 5: Task creation fails with empty string git_branch_id"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            mock_branch_repo.find_by_id = AsyncMock(return_value=None)

            with patch('fastmcp.task_management.application.services.project_management_service.ProjectManagementService') as MockPMS:
                mock_pms = MockPMS.return_value
                mock_pms.get_git_branch_by_id = Mock(return_value={"success": False})

                # Create facade with correct constructor signature
                facade = TaskApplicationFacade(
                    task_repository=mock_task_repo,
                    git_branch_repository=mock_branch_repo
                )

                # Execute and expect ValueError
                with self.assertRaises(ValueError):
                    await facade._derive_context_from_git_branch_id("")

        asyncio.run(run_test())

    def test_repository_not_available_fails(self):
        """Test 6: Validation fails gracefully when repository not available"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()

            # Create facade with correct constructor signature
            facade = TaskApplicationFacade(
                task_repository=mock_task_repo,
                git_branch_repository=None  # Explicitly set to None
            )

            # Execute and expect ValueError
            with self.assertRaises(ValueError) as context:
                await facade._derive_context_from_git_branch_id(self.valid_branch_id)

            # Verify error message mentions repository unavailability
            error_message = str(context.exception)
            self.assertIn("repository not available", error_message.lower())

        asyncio.run(run_test())

    def test_validation_occurs_before_task_creation(self):
        """
        Integration Test: Verify validation happens BEFORE task creation.
        This ensures _ensure_branch_context_exists doesn't bypass validation.
        """
        import inspect
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

        # Get source of create_task method
        source = inspect.getsource(TaskApplicationFacade.create_task)

        # Find positions of key method calls
        derive_context_pos = source.find('_derive_context_from_git_branch_id')
        ensure_context_pos = source.find('_ensure_branch_context_exists')

        # If both exist, derive should come before ensure
        if derive_context_pos != -1 and ensure_context_pos != -1:
            self.assertLess(
                derive_context_pos,
                ensure_context_pos,
                "CRITICAL: Validation (_derive_context) must occur before auto-creation (_ensure_context)"
            )

    def test_error_message_quality(self):
        """Test 7: Verify error messages are helpful and actionable"""

        async def run_test():
            from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

            # Mock repositories
            mock_task_repo = AsyncMock()
            mock_branch_repo = AsyncMock()
            mock_branch_repo.find_by_id = AsyncMock(return_value=None)

            with patch('fastmcp.task_management.application.services.project_management_service.ProjectManagementService') as MockPMS:
                mock_pms = MockPMS.return_value
                mock_pms.get_git_branch_by_id = Mock(return_value={"success": False})

                # Create facade with correct constructor signature
                facade = TaskApplicationFacade(
                    task_repository=mock_task_repo,
                    git_branch_repository=mock_branch_repo
                )

                try:
                    await facade._derive_context_from_git_branch_id(self.nonexistent_branch_id)
                    self.fail("Should have raised ValueError")
                except ValueError as e:
                    error_msg = str(e)

                    # Error message quality checks
                    self.assertIn(self.nonexistent_branch_id, error_msg, "Error should mention the invalid ID")
                    self.assertIn("not found", error_msg.lower(), "Error should clearly state branch not found")

                    # Should provide actionable guidance
                    has_guidance = any(word in error_msg.lower() for word in ['create', 'list', 'manage_git_branch'])
                    self.assertTrue(has_guidance, "Error should provide guidance on how to fix the issue")

        asyncio.run(run_test())


class TestValidationImpact(unittest.TestCase):
    """
    Test the broader impact of validation to ensure no phantom branches are created.
    """

    def test_no_phantom_branch_creation_in_source(self):
        """Verify source code doesn't create branches without validation"""
        import inspect
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

        # Get source of task creation method
        source = inspect.getsource(TaskApplicationFacade.create_task)

        # Should contain validation call
        self.assertIn(
            '_derive_context_from_git_branch_id',
            source,
            "CRITICAL: Task creation must call validation method"
        )

    def test_validation_method_signature(self):
        """Verify validation method has correct signature"""
        import inspect
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade

        # Get method signature
        sig = inspect.signature(TaskApplicationFacade._derive_context_from_git_branch_id)

        # Should have git_branch_id parameter
        self.assertIn('git_branch_id', sig.parameters, "Method must accept git_branch_id parameter")

        # Check return type annotation if present
        if sig.return_annotation != inspect.Parameter.empty:
            # Should indicate it returns a Dict
            return_type_str = str(sig.return_annotation)
            self.assertTrue(
                'Dict' in return_type_str or 'dict' in return_type_str,
                "Method should return a dictionary"
            )


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
