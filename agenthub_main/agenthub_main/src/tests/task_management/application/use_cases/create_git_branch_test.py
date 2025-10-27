"""
Test suite for CreateGitBranch use case

Tests the business logic for creating git branches (task trees).
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.value_objects import (
    GitBranchID,
    ProjectID,
    GitBranchName,
    UserID
)
from fastmcp.task_management.domain.exceptions import (
    ProjectNotFoundError,
    GitBranchAlreadyExistsError,
    ValidationError
)


class TestCreateGitBranchUseCase:
    """Test suite for CreateGitBranch use case"""

    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        return Mock()

    @pytest.fixture
    def mock_git_branch_repo(self):
        """Create mock git branch repository"""
        return Mock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_project_repo, mock_git_branch_repo, mock_event_bus):
        """Create use case instance with mocks"""
        return CreateGitBranchUseCase(
            project_repository=mock_project_repo,
            git_branch_repository=mock_git_branch_repo,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_project(self):
        """Create a sample project"""
        project = Project(
            id=ProjectID(str(uuid4())),
            name="Test Project",
            description="A test project",
            user_id=UserID("user123")
        )
        project.created_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        return project

    def test_create_git_branch_success(self, use_case, mock_project_repo, mock_git_branch_repo, mock_event_bus, sample_project):
        """Test successfully creating a git branch"""
        # Arrange
        project_id = sample_project.id.value
        branch_name = "feature/user-authentication"
        branch_description = "Implement user authentication system"
        user_id = "user123"
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None  # Branch doesn't exist
        mock_git_branch_repo.create.return_value = None
        
        # Act
        result = use_case.execute(
            project_id=project_id,
            git_branch_name=branch_name,
            git_branch_description=branch_description,
            user_id=user_id
        )
        
        # Assert
        assert isinstance(result, GitBranch)
        assert result.git_branch_name == GitBranchName(branch_name)
        assert result.project_id == sample_project.id
        assert result.git_branch_description == branch_description
        assert result.user_id == UserID(user_id)
        
        # Verify repository calls
        mock_project_repo.get_by_id.assert_called_once_with(ProjectID(project_id))
        mock_git_branch_repo.get_by_name.assert_called_once()
        mock_git_branch_repo.create.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()

    def test_create_git_branch_project_not_found(self, use_case, mock_project_repo):
        """Test creating branch when project doesn't exist"""
        # Arrange
        project_id = str(uuid4())
        
        mock_project_repo.get_by_id.side_effect = ProjectNotFoundError(f"Project {project_id} not found")
        
        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            use_case.execute(
                project_id=project_id,
                git_branch_name="feature/test",
                user_id="user123"
            )

    def test_create_git_branch_already_exists(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test creating branch that already exists"""
        # Arrange
        project_id = sample_project.id.value
        branch_name = "feature/existing"
        
        existing_branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=sample_project.id,
            git_branch_name=GitBranchName(branch_name),
            user_id=UserID("user123")
        )
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = existing_branch
        
        # Act & Assert
        with pytest.raises(GitBranchAlreadyExistsError, match=f"Branch {branch_name} already exists"):
            use_case.execute(
                project_id=project_id,
                git_branch_name=branch_name,
                user_id="user123"
            )

    def test_create_git_branch_invalid_name(self, use_case, mock_project_repo, sample_project):
        """Test creating branch with invalid name"""
        # Arrange
        project_id = sample_project.id.value
        invalid_names = [
            "",  # Empty
            " ",  # Whitespace only
            "feature branch",  # Contains space
            "feature@branch",  # Invalid character
            "a" * 256  # Too long
        ]
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act & Assert
        for invalid_name in invalid_names:
            with pytest.raises(ValidationError):
                use_case.execute(
                    project_id=project_id,
                    git_branch_name=invalid_name,
                    user_id="user123"
                )

    def test_create_git_branch_without_description(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test creating branch without description"""
        # Arrange
        project_id = sample_project.id.value
        branch_name = "feature/minimal"
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        result = use_case.execute(
            project_id=project_id,
            git_branch_name=branch_name,
            user_id="user123"
            # No description provided
        )
        
        # Assert
        assert result.git_branch_description is None

    def test_create_git_branch_valid_name_formats(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test various valid branch name formats"""
        # Arrange
        valid_names = [
            "main",
            "develop",
            "feature/user-auth",
            "bugfix/issue-123",
            "hotfix/security-patch",
            "release/v1.2.3",
            "feat/ABC-123-new-feature",
            "test_branch_123"
        ]
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act & Assert
        for branch_name in valid_names:
            result = use_case.execute(
                project_id=sample_project.id.value,
                git_branch_name=branch_name,
                user_id="user123"
            )
            assert result.git_branch_name == GitBranchName(branch_name)

    def test_create_git_branch_updates_project(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test project is updated when branch is created"""
        # Arrange
        original_updated_at = sample_project.updated_at
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        use_case.execute(
            project_id=sample_project.id.value,
            git_branch_name="feature/test",
            user_id="user123"
        )
        
        # Assert
        mock_project_repo.update.assert_called_once_with(sample_project)
        assert sample_project.updated_at > original_updated_at

    def test_create_git_branch_with_long_description(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test creating branch with long description"""
        # Arrange
        long_description = "This is a very detailed description " * 50  # 1750 chars
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        result = use_case.execute(
            project_id=sample_project.id.value,
            git_branch_name="feature/long-desc",
            git_branch_description=long_description,
            user_id="user123"
        )
        
        # Assert
        assert result.git_branch_description == long_description

    def test_create_git_branch_id_generation(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test branch gets valid UUID"""
        # Arrange
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        result = use_case.execute(
            project_id=sample_project.id.value,
            git_branch_name="feature/test-id",
            user_id="user123"
        )
        
        # Assert
        assert isinstance(result.id, GitBranchID)
        # Verify it's a valid UUID
        uuid4(result.id.value)  # Will raise if not valid

    def test_create_git_branch_transaction_rollback(self, use_case, mock_project_repo, mock_git_branch_repo, mock_event_bus, sample_project):
        """Test transaction rollback on error"""
        # Arrange
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        mock_git_branch_repo.create.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            use_case.execute(
                project_id=sample_project.id.value,
                git_branch_name="feature/failing",
                user_id="user123"
            )
        
        # Verify event was not published due to error
        mock_event_bus.publish.assert_not_called()

    def test_create_multiple_branches_same_project(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test creating multiple branches for same project"""
        # Arrange
        branch_names = ["feature/auth", "feature/api", "bugfix/issue-1"]
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        branches = []
        for branch_name in branch_names:
            result = use_case.execute(
                project_id=sample_project.id.value,
                git_branch_name=branch_name,
                user_id="user123"
            )
            branches.append(result)
        
        # Assert
        assert len(branches) == 3
        assert all(b.project_id == sample_project.id for b in branches)
        assert len(set(b.id.value for b in branches)) == 3  # All unique IDs

    def test_create_git_branch_preserves_user_id(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test user_id is properly stored"""
        # Arrange
        user_id = "specific-user-456"
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_git_branch_repo.get_by_name.return_value = None
        
        # Act
        result = use_case.execute(
            project_id=sample_project.id.value,
            git_branch_name="feature/user-test",
            user_id=user_id
        )
        
        # Assert
        assert result.user_id == UserID(user_id)

    def test_create_git_branch_case_sensitivity(self, use_case, mock_project_repo, mock_git_branch_repo, sample_project):
        """Test branch name case sensitivity"""
        # Arrange
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Create first branch
        mock_git_branch_repo.get_by_name.return_value = None
        branch1 = use_case.execute(
            project_id=sample_project.id.value,
            git_branch_name="Feature/TestCase",
            user_id="user123"
        )
        
        # Try to create with different case
        existing_branch = GitBranch(
            id=GitBranchID(str(uuid4())),
            project_id=sample_project.id,
            git_branch_name=GitBranchName("feature/testcase"),
            user_id=UserID("user123")
        )
        mock_git_branch_repo.get_by_name.return_value = existing_branch
        
        # Act & Assert - Should fail if case insensitive
        with pytest.raises(GitBranchAlreadyExistsError):
            use_case.execute(
                project_id=sample_project.id.value,
                git_branch_name="feature/testcase",
                user_id="user123"
            )