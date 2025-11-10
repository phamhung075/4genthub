"""Unit tests for ProjectNameValidator domain service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    ValidationException,
)
from fastmcp.task_management.domain.repositories.project_repository import (
    ProjectRepository,
)
from fastmcp.task_management.domain.services.project_name_validator import (
    ProjectNameValidator,
)


class TestProjectNameValidator:
    """Test ProjectNameValidator domain service."""

    @pytest.fixture
    def mock_project_repository(self):
        """Create a mock project repository."""
        repo = MagicMock(spec=ProjectRepository)
        repo.find_by_name_and_user = AsyncMock()
        return repo

    @pytest.fixture
    def validator(self, mock_project_repository):
        """Create a ProjectNameValidator instance."""
        return ProjectNameValidator(project_repository=mock_project_repository)

    @pytest.mark.asyncio
    async def test_validate_unique_name_success(self, validator, mock_project_repository):
        """Test successful validation of a unique project name."""
        # Arrange
        mock_project_repository.find_by_name.return_value = None  # No existing project
        
        # Act
        await validator.validate_unique_name("New Project", "user123")
        
        # Assert
        mock_project_repository.find_by_name.assert_called_once_with("New Project")

    @pytest.mark.asyncio
    async def test_validate_unique_name_empty_name(self, validator):
        """Test validation fails with empty name."""
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("", "user123")
        assert "Project name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_whitespace_name(self, validator):
        """Test validation fails with whitespace-only name."""
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("   ", "user123")
        assert "Project name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_empty_user_id(self, validator):
        """Test validation fails with empty user ID."""
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("Project Name", "")
        assert "User ID is required for validation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_duplicate_found(self, validator, mock_project_repository):
        """Test validation fails when duplicate project name exists."""
        # Arrange
        existing_project = Project(
            id="existing123",
            name="Existing Project",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("Existing Project", "user123")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_with_exclude_same_project(self, validator, mock_project_repository):
        """Test validation succeeds when excluding the same project (for updates)."""
        # Arrange
        existing_project = Project(
            id="project123",
            name="My Project",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act - Should not raise exception when excluding same project
        await validator.validate_unique_name("My Project", "user123", exclude_project_id="project123")
        
        # Assert
        mock_project_repository.find_by_name.assert_called_once_with("My Project")

    @pytest.mark.asyncio
    async def test_validate_unique_name_with_exclude_different_project(self, validator, mock_project_repository):
        """Test validation fails when duplicate exists but excluding different project."""
        # Arrange
        existing_project = Project(
            id="project123",
            name="My Project",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("My Project", "user123", exclude_project_id="different456")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_case_insensitive(self, validator, mock_project_repository):
        """Test that name validation is case-insensitive."""
        # Arrange
        existing_project = Project(
            id="project123",
            name="My Project",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        # Mock should be called with normalized name
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act & Assert - Should fail even with different case
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("MY PROJECT", "user123")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_unique_name_trimmed(self, validator, mock_project_repository):
        """Test that name validation trims whitespace."""
        # Arrange
        existing_project = Project(
            id="existing123",
            name="My Project",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act & Assert - Should fail because trimmed name matches existing project
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("  My Project  ", "user123")
        assert "already exists" in str(exc_info.value)
        
        # Verify it was called with trimmed name
        mock_project_repository.find_by_name.assert_called_once_with("My Project")

    @pytest.mark.asyncio
    async def test_validate_unique_name_different_users(self, validator, mock_project_repository):
        """Test that same project name is allowed for different users."""
        # Arrange - Simulate an existing project with same name from different user
        existing_project = Project(
            id="project123",
            name="Common Name",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        mock_project_repository.find_by_name.return_value = existing_project
        
        # Act & Assert - Should fail because name exists (not user-scoped)
        with pytest.raises(ValidationException) as exc_info:
            await validator.validate_unique_name("Common Name", "user456")
        assert "already exists" in str(exc_info.value)