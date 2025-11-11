"""Unit tests for ContextDerivationService - Domain Service for Context Derivation Logic"""

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.repositories.git_branch_repository import (
    GitBranchRepository,
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.services.context_derivation_service import (
    ContextDerivationService,
)
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestContextDerivationService:
    """Test suite for ContextDerivationService following DDD patterns."""

    @pytest.fixture
    def mock_task_repository(self) -> Mock:
        """Mock task repository for testing."""
        mock = Mock(spec=TaskRepository)
        mock.find_by_id = AsyncMock()
        return mock

    @pytest.fixture
    def mock_git_branch_repository(self) -> Mock:
        """Mock git branch repository for testing."""
        mock = Mock(spec=GitBranchRepository)
        mock.find_by_id = AsyncMock()
        return mock

    @pytest.fixture
    def service_without_repos(self) -> ContextDerivationService:
        """Create ContextDerivationService instance without repositories."""
        return ContextDerivationService()

    @pytest.fixture
    def service_with_repos(
        self, mock_task_repository: Mock, mock_git_branch_repository: Mock
    ) -> ContextDerivationService:
        """Create ContextDerivationService instance with repositories."""
        return ContextDerivationService(
            task_repository=mock_task_repository,
            git_branch_repository=mock_git_branch_repository,
        )

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task for testing."""
        task = Task(
            id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440000"),
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
        )
        task.git_branch_id = "550e8400-e29b-41d4-a716-446655440001"
        return task

    @pytest.fixture
    def sample_git_branch(self) -> GitBranch:
        """Create a sample git branch for testing."""
        branch = GitBranch(
            id="550e8400-e29b-41d4-a716-446655440001",
            name="feature/test-branch",
            project_id="550e8400-e29b-41d4-a716-446655440002",
        )
        return branch

    @pytest.fixture
    def sample_git_branch_with_project(self) -> GitBranch:
        """Create a sample git branch with project for testing."""
        project = Project(
            id="550e8400-e29b-41d4-a716-446655440002", name="Test Project"
        )
        project.user_id = "test-user-123"

        branch = GitBranch(
            id="550e8400-e29b-41d4-a716-446655440001",
            name="feature/test-branch",
            project_id="550e8400-e29b-41d4-a716-446655440002",
        )
        branch.project = project
        return branch

    class TestDeriveContextFromTask:
        """Test cases for derive_context_from_task method."""

        @pytest.mark.asyncio
        async def test_derive_context_from_task_success(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            mock_git_branch_repository: Mock,
            sample_task: Task,
            sample_git_branch: GitBranch,
        ):
            """Test successful context derivation from task."""
            # Arrange
            mock_task_repository.find_by_id.return_value = sample_task
            mock_git_branch_repository.find_by_id.return_value = sample_git_branch

            # Act
            result = await service_with_repos.derive_context_from_task(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                default_user_id="test-user",
            )

            # Assert
            assert result == {
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "git_branch_name": "feature/test-branch",
                "user_id": "test-user",
            }
            mock_task_repository.find_by_id.assert_called_once()
            mock_git_branch_repository.find_by_id.assert_called_once_with(
                "550e8400-e29b-41d4-a716-446655440001"
            )

        @pytest.mark.asyncio
        async def test_derive_context_from_task_no_branch(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
        ):
            """Test context derivation when task has no git branch."""
            # Arrange
            task = Task(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440000"),
                title="Task without branch",
                description="Test",
                status="todo",
                priority="medium",
            )
            # No git_branch_id set
            mock_task_repository.find_by_id.return_value = task

            # Act
            result = await service_with_repos.derive_context_from_task(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                default_user_id="test-user",
            )

            # Assert - Should return default context
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

        @pytest.mark.asyncio
        async def test_derive_context_from_task_not_found(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
        ):
            """Test context derivation when task is not found."""
            # Arrange
            mock_task_repository.find_by_id.return_value = None

            # Act
            result = await service_with_repos.derive_context_from_task(
                task_id="non-existent-task", default_user_id="test-user"
            )

            # Assert - Should return default context
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

        @pytest.mark.asyncio
        async def test_derive_context_from_task_repository_error(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            caplog,
        ):
            """Test context derivation when repository raises exception."""
            # Arrange
            mock_task_repository.find_by_id.side_effect = Exception("Repository error")

            # Act
            with caplog.at_level(logging.WARNING):
                result = await service_with_repos.derive_context_from_task(
                    task_id="550e8400-e29b-41d4-a716-446655440000",
                    default_user_id="test-user",
                )

            # Assert
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }
            assert "Failed to derive context from task" in caplog.text

        @pytest.mark.asyncio
        async def test_derive_context_from_task_no_repository(
            self, service_without_repos: ContextDerivationService
        ):
            """Test context derivation when no repository is configured."""
            # Act
            result = await service_without_repos.derive_context_from_task(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                default_user_id="test-user",
            )

            # Assert - Should return default context
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

    class TestDeriveContextFromGitBranch:
        """Test cases for derive_context_from_git_branch method."""

        @pytest.mark.asyncio
        async def test_derive_context_from_git_branch_success(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
            sample_git_branch: GitBranch,
        ):
            """Test successful context derivation from git branch."""
            # Arrange
            mock_git_branch_repository.find_by_id.return_value = sample_git_branch

            # Act
            result = await service_with_repos.derive_context_from_git_branch(
                git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                default_user_id="test-user",
            )

            # Assert
            assert result == {
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "git_branch_name": "feature/test-branch",
                "user_id": "test-user",
            }

        @pytest.mark.asyncio
        async def test_derive_context_from_git_branch_with_project_user(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
            sample_git_branch_with_project: GitBranch,
        ):
            """Test context derivation when git branch has project with user."""
            # Arrange
            mock_git_branch_repository.find_by_id.return_value = (
                sample_git_branch_with_project
            )

            # Act
            result = await service_with_repos.derive_context_from_git_branch(
                git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                default_user_id="default-user",
            )

            # Assert - Should use project's user_id instead of default
            assert result == {
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "git_branch_name": "feature/test-branch",
                "user_id": "test-user-123",  # From project
            }

        @pytest.mark.asyncio
        async def test_derive_context_from_git_branch_not_found(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
        ):
            """Test context derivation when git branch is not found."""
            # Arrange
            mock_git_branch_repository.find_by_id.return_value = None

            # Act
            result = await service_with_repos.derive_context_from_git_branch(
                git_branch_id="non-existent-branch", default_user_id="test-user"
            )

            # Assert - Should return default context
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

        @pytest.mark.asyncio
        async def test_derive_context_from_git_branch_repository_error(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
            caplog,
        ):
            """Test context derivation when repository raises exception."""
            # Arrange
            mock_git_branch_repository.find_by_id.side_effect = Exception(
                "Repository error"
            )

            # Act
            with caplog.at_level(logging.WARNING):
                result = await service_with_repos.derive_context_from_git_branch(
                    git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                    default_user_id="test-user",
                )

            # Assert
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }
            assert "Failed to derive context from git_branch" in caplog.text

        @pytest.mark.asyncio
        async def test_derive_context_from_git_branch_no_repository(
            self, service_without_repos: ContextDerivationService
        ):
            """Test context derivation when no repository is configured."""
            # Act
            result = await service_without_repos.derive_context_from_git_branch(
                git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                default_user_id="test-user",
            )

            # Assert - Should return default context
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

    class TestDeriveContextHierarchy:
        """Test cases for derive_context_hierarchy method."""

        @pytest.mark.asyncio
        async def test_derive_context_hierarchy_full(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            mock_git_branch_repository: Mock,
            sample_task: Task,
            sample_git_branch: GitBranch,
        ):
            """Test full context hierarchy derivation with all identifiers."""
            # Arrange
            mock_task_repository.find_by_id.return_value = sample_task
            mock_git_branch_repository.find_by_id.return_value = sample_git_branch

            # Act
            result = await service_with_repos.derive_context_hierarchy(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                project_id="550e8400-e29b-41d4-a716-446655440002",
                user_id="test-user",
            )

            # Assert
            assert result == {
                "global": {"user_id": "test-user"},
                "project": {"project_id": "550e8400-e29b-41d4-a716-446655440002"},
                "branch": {
                    "project_id": "550e8400-e29b-41d4-a716-446655440002",
                    "git_branch_name": "feature/test-branch",
                    "user_id": "test-user",
                },
                "task": {
                    "project_id": "550e8400-e29b-41d4-a716-446655440002",
                    "git_branch_name": "feature/test-branch",
                    "user_id": "test-user",
                },
            }

        @pytest.mark.asyncio
        async def test_derive_context_hierarchy_task_only(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            mock_git_branch_repository: Mock,
            sample_task: Task,
            sample_git_branch: GitBranch,
        ):
            """Test context hierarchy derivation with only task ID."""
            # Arrange
            mock_task_repository.find_by_id.return_value = sample_task
            mock_git_branch_repository.find_by_id.return_value = sample_git_branch

            # Act
            result = await service_with_repos.derive_context_hierarchy(
                task_id="550e8400-e29b-41d4-a716-446655440000", user_id="test-user"
            )

            # Assert - Should propagate context upwards
            assert result["global"]["user_id"] == "test-user"
            assert (
                result["project"]["project_id"]
                == "550e8400-e29b-41d4-a716-446655440002"
            )
            assert result["branch"]["git_branch_name"] == "feature/test-branch"
            assert (
                result["task"]["project_id"] == "550e8400-e29b-41d4-a716-446655440002"
            )

        @pytest.mark.asyncio
        async def test_derive_context_hierarchy_branch_only(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
            sample_git_branch: GitBranch,
        ):
            """Test context hierarchy derivation with only branch ID."""
            # Arrange
            mock_git_branch_repository.find_by_id.return_value = sample_git_branch

            # Act
            result = await service_with_repos.derive_context_hierarchy(
                git_branch_id="550e8400-e29b-41d4-a716-446655440001",
                user_id="test-user",
            )

            # Assert
            assert result["global"]["user_id"] == "test-user"
            assert (
                result["project"]["project_id"]
                == "550e8400-e29b-41d4-a716-446655440002"
            )
            assert (
                result["branch"]["project_id"] == "550e8400-e29b-41d4-a716-446655440002"
            )
            assert result["task"] == {}  # No task context

        @pytest.mark.asyncio
        async def test_derive_context_hierarchy_empty(
            self, service_without_repos: ContextDerivationService
        ):
            """Test context hierarchy derivation with no identifiers."""
            # Act
            result = await service_without_repos.derive_context_hierarchy()

            # Assert - Should have empty contexts
            assert result == {"global": {}, "project": {}, "branch": {}, "task": {}}

    class TestGetDefaultContext:
        """Test cases for _get_default_context method."""

        def test_get_default_context_with_user(
            self, service_without_repos: ContextDerivationService
        ):
            """Test getting default context with user ID."""
            # Act
            result = service_without_repos._get_default_context("test-user")

            # Assert
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }

        def test_get_default_context_without_user(
            self, service_without_repos: ContextDerivationService
        ):
            """Test getting default context without user ID."""
            # Act
            result = service_without_repos._get_default_context()

            # Assert
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "system",  # Should use system user
            }

    class TestResolveUserId:
        """Test cases for _resolve_user_id method."""

        def test_resolve_user_id_with_default(
            self, service_without_repos: ContextDerivationService
        ):
            """Test resolving user ID with default provided."""
            # Act
            result = service_without_repos._resolve_user_id("test-user")

            # Assert
            assert result == "test-user"

        def test_resolve_user_id_without_default(
            self, service_without_repos: ContextDerivationService, caplog
        ):
            """Test resolving user ID without default."""
            # Act
            with caplog.at_level(logging.WARNING):
                result = service_without_repos._resolve_user_id()

            # Assert
            assert result == "system"
            assert "No user ID provided, using system user" in caplog.text

    class TestDetermineContextLevel:
        """Test cases for determine_context_level method."""

        def test_determine_context_level_task(
            self, service_without_repos: ContextDerivationService
        ):
            """Test determining context level with task ID."""
            # Act
            result = service_without_repos.determine_context_level(
                task_id="task-123", git_branch_id="branch-123", project_id="project-123"
            )

            # Assert
            assert result == "task"

        def test_determine_context_level_branch(
            self, service_without_repos: ContextDerivationService
        ):
            """Test determining context level with branch ID only."""
            # Act
            result = service_without_repos.determine_context_level(
                git_branch_id="branch-123", project_id="project-123"
            )

            # Assert
            assert result == "branch"

        def test_determine_context_level_project(
            self, service_without_repos: ContextDerivationService
        ):
            """Test determining context level with project ID only."""
            # Act
            result = service_without_repos.determine_context_level(
                project_id="project-123"
            )

            # Assert
            assert result == "project"

        def test_determine_context_level_global(
            self, service_without_repos: ContextDerivationService
        ):
            """Test determining context level with no identifiers."""
            # Act
            result = service_without_repos.determine_context_level()

            # Assert
            assert result == "global"

        def test_determine_context_level_priority_order(
            self, service_without_repos: ContextDerivationService
        ):
            """Test that task level has priority over others."""
            # Act - Task should take priority even if others are present
            result = service_without_repos.determine_context_level(
                task_id="task-123", git_branch_id="branch-123", project_id="project-123"
            )

            # Assert
            assert result == "task"

    class TestEdgeCases:
        """Test edge cases and error scenarios."""

        @pytest.mark.asyncio
        async def test_derive_context_from_task_invalid_uuid(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            caplog,
        ):
            """Test context derivation with invalid task UUID."""
            # Arrange
            mock_task_repository.find_by_id.side_effect = ValueError("Invalid UUID")

            # Act
            with caplog.at_level(logging.WARNING):
                result = await service_with_repos.derive_context_from_task(
                    task_id="invalid-uuid", default_user_id="test-user"
                )

            # Assert
            assert result == {
                "project_id": "default_project",
                "git_branch_name": "main",
                "user_id": "test-user",
            }
            assert "Failed to derive context from task" in caplog.text

        @pytest.mark.asyncio
        async def test_context_hierarchy_partial_failure(
            self,
            service_with_repos: ContextDerivationService,
            mock_task_repository: Mock,
            mock_git_branch_repository: Mock,
        ):
            """Test context hierarchy when some derivations fail."""
            # Arrange
            mock_task_repository.find_by_id.return_value = None  # Task not found
            mock_git_branch_repository.find_by_id.return_value = (
                None  # Branch not found
            )

            # Act
            result = await service_with_repos.derive_context_hierarchy(
                task_id="non-existent",
                git_branch_id="non-existent",
                user_id="test-user",
            )

            # Assert - Should still have structure with defaults
            assert result["global"]["user_id"] == "test-user"
            assert result["branch"]["project_id"] == "default_project"
            assert result["task"]["git_branch_name"] == "main"

        def test_resolve_user_id_empty_string(
            self, service_without_repos: ContextDerivationService
        ):
            """Test resolving user ID with empty string."""
            # Act
            result = service_without_repos._resolve_user_id("")

            # Assert - Empty string is falsy, should use system
            assert result == "system"

        @pytest.mark.asyncio
        async def test_derive_context_with_minimal_values(
            self,
            service_with_repos: ContextDerivationService,
            mock_git_branch_repository: Mock,
        ):
            """Test context derivation when entity has minimal values."""
            # Arrange
            branch = GitBranch(
                id="branch-123",
                name="minimal-branch",  # Valid name
                project_id="minimal-project",  # Valid project_id
            )
            # Simulate a branch without a loaded project relation
            branch.project = None
            mock_git_branch_repository.find_by_id.return_value = branch

            # Act
            result = await service_with_repos.derive_context_from_git_branch(
                git_branch_id="branch-123", default_user_id="test-user"
            )

            # Assert
            assert result["project_id"] == "minimal-project"
            assert result["git_branch_name"] == "minimal-branch"
            assert (
                result["user_id"] == "test-user"
            )  # Should use default since no project user
