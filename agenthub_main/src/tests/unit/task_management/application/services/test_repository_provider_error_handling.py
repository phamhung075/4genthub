"""
Test suite for fail-fast error handling in repository provider.

Tests verify that the system fails fast with clear error messages when
the repository provider is unavailable, rather than silently returning None.

This is critical because:
1. Frontend TypeScript contract requires project_id: string (not optional)
2. Returning None would violate type contract and cause UI errors
3. Better to fail explicitly than corrupt data silently
"""

from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.application.exceptions import RepositoryProviderError
from fastmcp.task_management.application.services.task_application_service import (
    TaskApplicationService,
)
from fastmcp.task_management.application.services.task_context_sync_service import (
    TaskContextSyncService,
)


class TestRepositoryProviderFailFast:
    """Test fail-fast behavior when repository provider fails."""

    def test_task_application_service_should_raise_when_provider_unavailable(self):
        """Verify TaskApplicationService fails fast when repository provider unavailable.

        CRITICAL: System should NOT return None or log WARNING.
        Should raise RepositoryProviderError with ERROR logging.
        """
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_provider.side_effect = Exception("Provider service unavailable")

            # Act & Assert: Should raise RepositoryProviderError, not return None
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskApplicationService(mock_task_repo)

            # Verify error message is clear
            assert "Cannot fetch project_id without git_branch_repository" in str(
                exc_info.value
            )
            assert "Provider service unavailable" in str(exc_info.value)

    def test_task_application_service_should_raise_when_provider_returns_none(self):
        """Verify TaskApplicationService fails fast when provider returns None.

        CRITICAL: None is not acceptable - system requires git_branch_repository.
        """
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_instance = Mock()
            mock_instance.get_git_branch_repository.return_value = None
            mock_provider.return_value = mock_instance

            # Act & Assert: Should raise RepositoryProviderError
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskApplicationService(mock_task_repo)

            # Verify error message indicates None was returned
            assert "git_branch_repository is None" in str(exc_info.value)

    def test_task_context_sync_service_should_raise_when_provider_unavailable(self):
        """Verify TaskContextSyncService fails fast when repository provider unavailable.

        Both services should have consistent error handling.
        """
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_provider.side_effect = Exception("Provider service unavailable")

            # Act & Assert: Should raise RepositoryProviderError
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskContextSyncService(mock_task_repo)

            # Verify error message is clear
            assert "Cannot fetch project_id without git_branch_repository" in str(
                exc_info.value
            )

    def test_task_context_sync_service_should_raise_when_provider_returns_none(self):
        """Verify TaskContextSyncService fails fast when provider returns None."""
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_instance = Mock()
            mock_instance.get_git_branch_repository.return_value = None
            mock_provider.return_value = mock_instance

            # Act & Assert: Should raise RepositoryProviderError
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskContextSyncService(mock_task_repo)

            # Verify error message indicates None was returned
            assert "git_branch_repository is None" in str(exc_info.value)

    def test_should_log_errors_not_warnings_for_critical_failures(self):
        """Verify critical failures logged as ERROR not WARNING.

        CRITICAL: WARNING is inappropriate for infrastructure failures.
        Should log at ERROR level with full stack trace (exc_info=True).
        """
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                mock_provider.side_effect = Exception("Critical infrastructure failure")

                # Act: Attempt to create service (will fail)
                try:
                    TaskApplicationService(mock_task_repo)
                except RepositoryProviderError:
                    pass  # Expected

                # Assert: ERROR logged with stack trace, NOT WARNING
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args

                # Verify ERROR message contains critical info
                assert "CRITICAL" in error_call[0][0]
                assert "Failed to get git_branch_repository" in error_call[0][0]

                # Verify exc_info=True for stack trace
                assert error_call[1].get("exc_info") is True

                # Verify WARNING was NOT called
                mock_logger.warning.assert_not_called()

    def test_should_include_stack_trace_for_debugging(self):
        """Verify exc_info=True is passed to logger for stack trace.

        Stack traces are essential for debugging infrastructure failures.
        """
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                mock_provider.side_effect = RuntimeError("Infrastructure down")

                # Act: Attempt to create service
                try:
                    TaskApplicationService(mock_task_repo)
                except RepositoryProviderError:
                    pass  # Expected

                # Assert: exc_info=True was passed
                error_call = mock_logger.error.call_args
                assert error_call is not None, "logger.error should have been called"
                assert error_call[1].get("exc_info") is True, (
                    "exc_info should be True for stack traces"
                )

    def test_error_should_preserve_original_exception_chain(self):
        """Verify 'raise ... from e' preserves exception chain for debugging.

        Exception chaining helps developers trace root cause.
        """
        # Arrange
        mock_task_repo = Mock()
        original_error = RuntimeError("Original infrastructure error")

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_provider.side_effect = original_error

            # Act & Assert
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskApplicationService(mock_task_repo)

            # Verify exception chain preserved
            assert exc_info.value.__cause__ is original_error
            assert "Original infrastructure error" in str(exc_info.value.__cause__)


class TestRepositoryProviderSuccessPath:
    """Test normal operation when repository provider works correctly."""

    def test_should_return_repository_when_provider_succeeds(self):
        """Verify normal operation when repository provider works."""
        # Arrange
        mock_task_repo = Mock()
        mock_task_repo.with_user = Mock(return_value=mock_task_repo)
        mock_task_repo.user_id = None

        mock_git_branch_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_instance = Mock()
            mock_instance.get_git_branch_repository.return_value = mock_git_branch_repo
            mock_provider.return_value = mock_instance

            # Act: Create service (should succeed)
            service = TaskApplicationService(mock_task_repo)

            # Assert: Service created successfully
            assert service is not None

            # Verify repository provider was called
            mock_provider.assert_called_once()
            mock_instance.get_git_branch_repository.assert_called_once()

    def test_should_not_log_errors_on_success(self):
        """Verify no error logging when provider works correctly."""
        # Arrange
        mock_task_repo = Mock()
        mock_task_repo.with_user = Mock(return_value=mock_task_repo)
        mock_task_repo.user_id = None

        mock_git_branch_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                mock_instance = Mock()
                mock_instance.get_git_branch_repository.return_value = (
                    mock_git_branch_repo
                )
                mock_provider.return_value = mock_instance

                # Act: Create service
                TaskApplicationService(mock_task_repo)

                # Assert: No error or warning logging
                mock_logger.error.assert_not_called()
                mock_logger.warning.assert_not_called()


class TestErrorHandlingDocumentation:
    """Test that error messages provide clear guidance."""

    def test_error_message_should_explain_impact(self):
        """Verify error messages explain why failure is critical."""
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_provider.side_effect = Exception("Provider unavailable")

            # Act & Assert
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskApplicationService(mock_task_repo)

            # Verify message explains impact (cannot fetch project_id)
            error_message = str(exc_info.value)
            assert "Cannot fetch project_id" in error_message
            assert "git_branch_repository" in error_message

    def test_error_code_should_be_standardized(self):
        """Verify RepositoryProviderError has consistent error code."""
        # Arrange
        mock_task_repo = Mock()

        with patch(
            "fastmcp.task_management.application.services.repository_provider_service.RepositoryProviderService.get_instance"
        ) as mock_provider:
            mock_provider.side_effect = Exception("Provider unavailable")

            # Act & Assert
            with pytest.raises(RepositoryProviderError) as exc_info:
                TaskApplicationService(mock_task_repo)

            # Verify error code is standardized
            assert exc_info.value.code == "REPOSITORY_PROVIDER_ERROR"
