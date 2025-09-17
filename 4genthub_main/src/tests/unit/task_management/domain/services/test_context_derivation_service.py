"""Unit tests for ContextDerivationService domain service"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Optional, Dict, Any

from fastmcp.task_management.domain.services.context_derivation_service import ContextDerivationService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository


class MockGitBranch:
    """Mock GitBranch entity for testing"""
    
    def __init__(self, branch_id: str, name: str, project_id: str, project_user_id: str = None):
        self.id = branch_id
        self.name = name
        self.project_id = project_id
        self.project = None
        
        if project_user_id:
            # Mock project with user_id
            self.project = Mock()
            self.project.user_id = project_user_id


class TestContextDerivationService:
    """Test suite for ContextDerivationService domain service"""

    def setup_method(self):
        """Setup test data before each test"""
        self.mock_task_repository = Mock(spec=TaskRepository)
        self.mock_git_branch_repository = Mock(spec=GitBranchRepository)

        # Make repository methods async
        self.mock_task_repository.find_by_id = AsyncMock()
        self.mock_git_branch_repository.find_by_id = AsyncMock()
        
        self.service = ContextDerivationService(
            task_repository=self.mock_task_repository,
            git_branch_repository=self.mock_git_branch_repository
        )
        
        # Create test task
        self.test_task = Task(
            title="Test Task",
            description="Test description",
            id=TaskId.from_string("88888888-8888-8888-8888-888888888888"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id="test-branch-id",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create test git branch
        self.test_git_branch = MockGitBranch(
            branch_id="test-branch-id",
            name="feature/test-branch", 
            project_id="test-project-id",
            project_user_id="test-user"
        )

    @pytest.mark.asyncio
    async def test_derive_context_from_task_with_valid_git_branch(self):
        """Test context derivation from task with valid git branch"""
        # Arrange
        self.mock_task_repository.find_by_id.return_value = self.test_task
        self.mock_git_branch_repository.find_by_id.return_value = self.test_git_branch

        # Act
        context = await self.service.derive_context_from_task("test-task-id", "default-user")

        # Assert
        assert context["project_id"] == "test-project-id"
        assert context["git_branch_name"] == "feature/test-branch"
        assert context["user_id"] == "test-user"

        # Verify repository calls
        self.mock_task_repository.find_by_id.assert_called_once()
        self.mock_git_branch_repository.find_by_id.assert_called_once_with("test-branch-id")

    @pytest.mark.asyncio
    async def test_derive_context_from_task_without_git_branch_id(self):
        """Test context derivation from task without git_branch_id"""
        # Arrange
        task_without_branch = Task(
            title="Task Without Branch",
            description="Test description",
            id=TaskId.from_string("99999999-9999-9999-9999-999999999999"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id=None,  # No branch ID
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        self.mock_task_repository.find_by_id = AsyncMock(return_value=task_without_branch)

        # Act
        context = await self.service.derive_context_from_task("no-branch-task", "default-user")

        # Assert - Should return default context
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "default-user"

    @pytest.mark.asyncio
    async def test_derive_context_from_task_not_found(self):
        """Test context derivation when task is not found"""
        # Arrange
        self.mock_task_repository.find_by_id.return_value = None

        # Act
        context = await self.service.derive_context_from_task("missing-task", "default-user")
        
        # Assert - Should return default context
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "default-user"

    @pytest.mark.asyncio
    async def test_derive_context_from_task_repository_exception(self):
        """Test context derivation when repository throws exception"""
        # Arrange
        self.mock_task_repository.find_by_id.side_effect = Exception("Database error")

        # Act
        context = await self.service.derive_context_from_task("error-task", "default-user")
        
        # Assert - Should return default context gracefully
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "default-user"

    @pytest.mark.asyncio
    async def test_derive_context_from_git_branch_success(self):
        """Test successful context derivation from git branch"""
        # Arrange
        self.mock_git_branch_repository.find_by_id.return_value = self.test_git_branch
        
        # Act
        context = await self.service.derive_context_from_git_branch("test-branch-id", "fallback-user")
        
        # Assert
        assert context["project_id"] == "test-project-id"
        assert context["git_branch_name"] == "feature/test-branch"
        assert context["user_id"] == "test-user"  # From project
        
        self.mock_git_branch_repository.find_by_id.assert_called_once_with("test-branch-id")

    @pytest.mark.asyncio
    async def test_derive_context_from_git_branch_no_project_user(self):
        """Test context derivation from git branch without project user"""
        # Arrange
        branch_without_project_user = MockGitBranch(
            branch_id="no-user-branch",
            name="feature/no-user",
            project_id="project-id"
            # No project_user_id
        )
        
        self.mock_git_branch_repository.find_by_id.return_value = branch_without_project_user
        
        # Act
        context = await self.service.derive_context_from_git_branch("no-user-branch", "fallback-user")
        
        # Assert
        assert context["project_id"] == "project-id"
        assert context["git_branch_name"] == "feature/no-user"
        assert context["user_id"] == "fallback-user"  # Should use fallback

    @pytest.mark.asyncio
    async def test_derive_context_from_git_branch_not_found(self):
        """Test context derivation when git branch is not found"""
        # Arrange
        self.mock_git_branch_repository.find_by_id.return_value = None
        
        # Act
        context = await self.service.derive_context_from_git_branch("missing-branch", "fallback-user")
        
        # Assert - Should return default context
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "fallback-user"

    @pytest.mark.asyncio
    async def test_derive_context_from_git_branch_repository_exception(self):
        """Test context derivation when git branch repository throws exception"""
        # Arrange
        self.mock_git_branch_repository.find_by_id.side_effect = Exception("Database error")
        
        # Act
        context = await self.service.derive_context_from_git_branch("error-branch", "fallback-user")
        
        # Assert - Should return default context gracefully
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "fallback-user"

    @pytest.mark.asyncio
    async def test_derive_context_hierarchy_complete(self):
        """Test deriving complete context hierarchy with all parameters"""
        # Arrange
        self.mock_task_repository.find_by_id.return_value = self.test_task
        self.mock_git_branch_repository.find_by_id.return_value = self.test_git_branch
        
        # Act
        hierarchy = await self.service.derive_context_hierarchy(
            task_id="test-task-id",
            git_branch_id="test-branch-id",
            project_id="explicit-project-id",
            user_id="hierarchy-user"
        )
        
        # Assert
        assert "global" in hierarchy
        assert "project" in hierarchy
        assert "branch" in hierarchy
        assert "task" in hierarchy
        
        # Check global level
        assert hierarchy["global"]["user_id"] == "hierarchy-user"
        
        # Check project level
        assert hierarchy["project"]["project_id"] == "explicit-project-id"
        
        # Check branch level
        assert hierarchy["branch"]["project_id"] == "test-project-id"
        assert hierarchy["branch"]["git_branch_name"] == "feature/test-branch"
        
        # Check task level
        assert hierarchy["task"]["project_id"] == "test-project-id"
        assert hierarchy["task"]["git_branch_name"] == "feature/test-branch"

    @pytest.mark.asyncio
    async def test_derive_context_hierarchy_with_propagation(self):
        """Test context hierarchy with propagation from lower to higher levels"""
        # Arrange
        self.mock_task_repository.find_by_id.return_value = self.test_task
        self.mock_git_branch_repository.find_by_id.return_value = self.test_git_branch
        
        # Act - Only provide task_id, let others propagate
        hierarchy = await self.service.derive_context_hierarchy(
            task_id="test-task-id",
            user_id="hierarchy-user"
        )
        
        # Assert
        # Branch context should be populated from task derivation
        assert hierarchy["branch"]["project_id"] == "test-project-id"
        assert hierarchy["branch"]["git_branch_name"] == "feature/test-branch"
        
        # Project should inherit from branch
        assert hierarchy["project"]["project_id"] == "test-project-id"
        
        # Task context should be populated
        assert hierarchy["task"]["project_id"] == "test-project-id"
        assert hierarchy["task"]["git_branch_name"] == "feature/test-branch"

    @pytest.mark.asyncio
    async def test_derive_context_hierarchy_minimal(self):
        """Test context hierarchy with minimal input"""
        # Act
        hierarchy = await self.service.derive_context_hierarchy(user_id="minimal-user")
        
        # Assert
        assert hierarchy["global"]["user_id"] == "minimal-user"
        assert hierarchy["project"] == {}
        assert hierarchy["branch"] == {}
        assert hierarchy["task"] == {}

    def test_get_default_context(self):
        """Test default context generation"""
        # Act
        context = self.service._get_default_context("test-user")
        
        # Assert
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "test-user"

    def test_get_default_context_no_user(self):
        """Test default context generation without user"""
        # Act
        context = self.service._get_default_context(None)
        
        # Assert
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "system"  # Should fallback to system

    def test_resolve_user_id_with_default(self):
        """Test user ID resolution with provided default"""
        # Act
        user_id = self.service._resolve_user_id("provided-user")
        
        # Assert
        assert user_id == "provided-user"

    def test_resolve_user_id_without_default(self):
        """Test user ID resolution without provided default"""
        # Act
        user_id = self.service._resolve_user_id(None)
        
        # Assert
        assert user_id == "system"  # Should fallback to system user

    def test_determine_context_level_task(self):
        """Test context level determination for task level"""
        # Act
        level = self.service.determine_context_level(task_id="task-123")
        
        # Assert
        assert level == "task"

    def test_determine_context_level_branch(self):
        """Test context level determination for branch level"""
        # Act
        level = self.service.determine_context_level(git_branch_id="branch-123")
        
        # Assert
        assert level == "branch"

    def test_determine_context_level_project(self):
        """Test context level determination for project level"""
        # Act
        level = self.service.determine_context_level(project_id="project-123")
        
        # Assert
        assert level == "project"

    def test_determine_context_level_global(self):
        """Test context level determination for global level"""
        # Act
        level = self.service.determine_context_level()
        
        # Assert
        assert level == "global"

    def test_determine_context_level_priority_task_over_branch(self):
        """Test context level priority - task takes precedence over branch"""
        # Act
        level = self.service.determine_context_level(
            task_id="task-123", 
            git_branch_id="branch-123"
        )
        
        # Assert
        assert level == "task"

    def test_determine_context_level_priority_branch_over_project(self):
        """Test context level priority - branch takes precedence over project"""
        # Act
        level = self.service.determine_context_level(
            git_branch_id="branch-123",
            project_id="project-123"
        )
        
        # Assert
        assert level == "branch"

    @pytest.mark.asyncio
    async def test_service_without_repositories(self):
        """Test service functionality without repositories (basic operations)"""
        # Arrange
        service_no_repos = ContextDerivationService()

        # Act & Assert - Should work with default fallbacks
        context = await service_no_repos.derive_context_from_task("any-task", "test-user")
        assert context["project_id"] == "default_project"

        context = await service_no_repos.derive_context_from_git_branch("any-branch", "test-user")
        assert context["project_id"] == "default_project"

        hierarchy = await service_no_repos.derive_context_hierarchy(user_id="test-user")
        assert hierarchy["global"]["user_id"] == "test-user"
        
        level = service_no_repos.determine_context_level(task_id="task-123")
        assert level == "task"


class TestContextDerivationServiceIntegration:
    """Integration tests for ContextDerivationService with complex scenarios"""

    def setup_method(self):
        """Setup integration test environment"""
        self.mock_task_repository = AsyncMock(spec=TaskRepository)
        self.mock_git_branch_repository = AsyncMock(spec=GitBranchRepository)
        
        self.service = ContextDerivationService(
            task_repository=self.mock_task_repository,
            git_branch_repository=self.mock_git_branch_repository
        )

    @pytest.mark.asyncio
    async def test_complete_context_derivation_chain(self):
        """Test complete context derivation chain from task to project"""
        # Arrange: Create a realistic scenario
        project_user = "project-owner"
        
        # Create task with git branch
        task = Task(
            title="Feature Implementation",
            description="Implement authentication feature",
            id=TaskId.from_string("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            status=TaskStatus.in_progress(),
            priority=Priority.from_string("high"),
            git_branch_id="auth-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create git branch with project
        git_branch = MockGitBranch(
            branch_id="auth-branch",
            name="feature/authentication",
            project_id="auth-project",
            project_user_id=project_user
        )
        
        # Mock repository responses with proper async return
        self.mock_task_repository.find_by_id = AsyncMock(return_value=task)
        self.mock_git_branch_repository.find_by_id = AsyncMock(return_value=git_branch)
        
        # Act: Derive context from task
        context = await self.service.derive_context_from_task("auth-task", "fallback-user")
        
        # Assert: Should derive complete context chain
        assert context["project_id"] == "auth-project"
        assert context["git_branch_name"] == "feature/authentication"
        assert context["user_id"] == project_user
        
        # Verify both repositories were used
        self.mock_task_repository.find_by_id.assert_called_once()
        self.mock_git_branch_repository.find_by_id.assert_called_once_with("auth-branch")

    @pytest.mark.asyncio
    async def test_context_hierarchy_complex_inheritance(self):
        """Test complex context hierarchy with inheritance and overrides"""
        # Arrange
        task_with_branch = Task(
            title="Complex Task",
            description="Task with complex context",
            id=TaskId.from_string("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id="complex-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        complex_branch = MockGitBranch(
            branch_id="complex-branch",
            name="feature/complex",
            project_id="derived-project",
            project_user_id="branch-user"
        )
        
        self.mock_task_repository.find_by_id = AsyncMock(return_value=task_with_branch)
        self.mock_git_branch_repository.find_by_id = AsyncMock(return_value=complex_branch)
        
        # Act: Derive hierarchy with explicit overrides
        hierarchy = await self.service.derive_context_hierarchy(
            task_id="complex-task",
            git_branch_id="explicit-branch",  # Different from task's branch
            project_id="explicit-project",   # Different from derived project
            user_id="hierarchy-user"
        )
        
        # Assert: Check inheritance and overrides
        # Global level
        assert hierarchy["global"]["user_id"] == "hierarchy-user"
        
        # Project level - should have explicit value
        assert hierarchy["project"]["project_id"] == "explicit-project"
        
        # Branch level - should use explicit branch but derived context still applies to task
        # Task level - should use task's actual branch context
        assert hierarchy["task"]["project_id"] == "derived-project"
        assert hierarchy["task"]["git_branch_name"] == "feature/complex"

    @pytest.mark.asyncio
    async def test_context_derivation_with_partial_failures(self):
        """Test context derivation with partial repository failures"""
        # Arrange: Task exists but git branch lookup fails
        partial_task = Task(
            title="Partial Task",
            description="Task with failing branch lookup",
            id=TaskId.from_string("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id="failing-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.mock_task_repository.find_by_id.return_value = partial_task
        self.mock_git_branch_repository.find_by_id.side_effect = Exception("Branch lookup failed")
        
        # Act
        context = await self.service.derive_context_from_task("partial-task", "fallback-user")
        
        # Assert: Should gracefully fallback to defaults
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "fallback-user"

    def test_context_level_determination_with_complex_parameters(self):
        """Test context level determination with various parameter combinations"""
        test_cases = [
            # (task_id, git_branch_id, project_id, expected_level)
            ("task-1", "branch-1", "project-1", "task"),
            (None, "branch-1", "project-1", "branch"),
            (None, None, "project-1", "project"),
            (None, None, None, "global"),
            ("task-1", None, None, "task"),
            ("task-1", "branch-1", None, "task"),
        ]
        
        for task_id, branch_id, project_id, expected_level in test_cases:
            # Act
            level = self.service.determine_context_level(
                task_id=task_id,
                git_branch_id=branch_id,
                project_id=project_id
            )
            
            # Assert
            assert level == expected_level, f"Failed for task:{task_id}, branch:{branch_id}, project:{project_id}"

    @pytest.mark.asyncio
    async def test_business_rules_enforcement(self):
        """Test enforcement of context derivation business rules"""
        # Business Rule: Tasks inherit context from their git branch
        # Business Rule: If task has no git branch, use default context
        # Business Rule: User authentication is required for context derivation
        
        # Test Rule 1: Task inherits from git branch
        task_with_branch = Task(
            title="Task with Branch",
            description="Should inherit from branch",
            id=TaskId.from_string("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id="inherit-branch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        inherit_branch = MockGitBranch(
            branch_id="inherit-branch",
            name="feature/inherit",
            project_id="inherit-project",
            project_user_id="inherit-user"
        )
        
        self.mock_task_repository.find_by_id = AsyncMock(return_value=task_with_branch)
        self.mock_git_branch_repository.find_by_id = AsyncMock(return_value=inherit_branch)
        
        context = await self.service.derive_context_from_task("inherit-task")
        
        # Should inherit from branch
        assert context["project_id"] == "inherit-project"
        assert context["git_branch_name"] == "feature/inherit"
        
        # Test Rule 2: Task without branch uses defaults
        task_without_branch = Task(
            title="Task without Branch",
            description="Should use defaults",
            id=TaskId.from_string("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            status=TaskStatus.todo(),
            priority=Priority.from_string("medium"),
            git_branch_id=None,  # No branch
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.mock_task_repository.find_by_id = AsyncMock(return_value=task_without_branch)
        
        context = await self.service.derive_context_from_task("default-task", "test-user")
        
        # Should use defaults
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "test-user"
        
        # Test Rule 3: User authentication required
        context_no_user = self.service._get_default_context(None)
        assert context_no_user["user_id"] == "system"  # Falls back to system user