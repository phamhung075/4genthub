"""
Test suite for GetProject use case

Tests the business logic for retrieving project details.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.use_cases.get_project import GetProjectUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.value_objects import ProjectID, UserID
from fastmcp.task_management.domain.exceptions import ProjectNotFoundError, UnauthorizedAccessError


class TestGetProjectUseCase:
    """Test suite for GetProject use case"""

    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        return Mock()

    @pytest.fixture
    def mock_context_repo(self):
        """Create mock context repository"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_project_repo, mock_context_repo):
        """Create use case instance with mocks"""
        return GetProjectUseCase(
            project_repository=mock_project_repo,
            context_repository=mock_context_repo
        )

    @pytest.fixture
    def sample_project(self):
        """Create a sample project"""
        project = Project(
            id=ProjectID(str(uuid4())),
            name="Test Project",
            description="A comprehensive test project",
            user_id=UserID("user123")
        )
        project.created_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        return project

    def test_get_project_by_id_success(self, use_case, mock_project_repo, sample_project):
        """Test successfully getting project by ID"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act
        result = use_case.execute(project_id=project_id, user_id=user_id)
        
        # Assert
        assert result == sample_project
        assert result.id.value == project_id
        assert result.name == "Test Project"
        mock_project_repo.get_by_id.assert_called_once_with(ProjectID(project_id))

    def test_get_project_by_name_success(self, use_case, mock_project_repo, sample_project):
        """Test successfully getting project by name"""
        # Arrange
        project_name = "Test Project"
        user_id = "user123"
        
        mock_project_repo.get_by_name.return_value = sample_project
        
        # Act
        result = use_case.execute(name=project_name, user_id=user_id)
        
        # Assert
        assert result == sample_project
        assert result.name == project_name
        mock_project_repo.get_by_name.assert_called_once_with(project_name, UserID(user_id))

    def test_get_project_not_found(self, use_case, mock_project_repo):
        """Test getting non-existent project"""
        # Arrange
        project_id = str(uuid4())
        
        mock_project_repo.get_by_id.side_effect = ProjectNotFoundError(f"Project {project_id} not found")
        
        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            use_case.execute(project_id=project_id, user_id="user123")

    def test_get_project_unauthorized_access(self, use_case, mock_project_repo, sample_project):
        """Test accessing project by different user"""
        # Arrange
        project_id = sample_project.id.value
        different_user = "user456"  # Not the owner
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act & Assert
        with pytest.raises(UnauthorizedAccessError, match="not authorized to access"):
            use_case.execute(project_id=project_id, user_id=different_user)

    def test_get_project_no_id_or_name(self, use_case):
        """Test calling without project_id or name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Either project_id or name must be provided"):
            use_case.execute(user_id="user123")

    def test_get_project_both_id_and_name(self, use_case):
        """Test calling with both project_id and name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Only one of project_id or name should be provided"):
            use_case.execute(
                project_id=str(uuid4()),
                name="Test Project",
                user_id="user123"
            )

    def test_get_project_with_context(self, use_case, mock_project_repo, mock_context_repo, sample_project):
        """Test getting project with context data"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        context_data = {
            "theme": "dark",
            "preferences": {"notifications": True}
        }
        
        mock_project_repo.get_by_id.return_value = sample_project
        mock_context_repo.get_project_context.return_value = context_data
        
        # Act
        result = use_case.execute(
            project_id=project_id,
            user_id=user_id,
            include_context=True
        )
        
        # Assert
        assert result == sample_project
        assert hasattr(result, 'context_data')
        assert result.context_data == context_data
        mock_context_repo.get_project_context.assert_called_once_with(sample_project.id)

    def test_get_project_without_context(self, use_case, mock_project_repo, mock_context_repo, sample_project):
        """Test getting project without context data"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act
        result = use_case.execute(
            project_id=project_id,
            user_id=user_id,
            include_context=False
        )
        
        # Assert
        assert result == sample_project
        mock_context_repo.get_project_context.assert_not_called()

    def test_get_project_with_statistics(self, use_case, mock_project_repo, sample_project):
        """Test getting project with statistics"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        
        # Add statistics to project
        sample_project.total_tasks = 25
        sample_project.completed_tasks = 10
        sample_project.active_branches = 3
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act
        result = use_case.execute(project_id=project_id, user_id=user_id)
        
        # Assert
        assert result.total_tasks == 25
        assert result.completed_tasks == 10
        assert result.active_branches == 3

    def test_get_project_by_name_case_sensitivity(self, use_case, mock_project_repo, sample_project):
        """Test project name lookup case sensitivity"""
        # Arrange
        user_id = "user123"
        
        # Test different cases
        test_cases = ["Test Project", "test project", "TEST PROJECT"]
        
        for name_variant in test_cases:
            mock_project_repo.get_by_name.return_value = sample_project
            
            # Act
            result = use_case.execute(name=name_variant, user_id=user_id)
            
            # Assert
            assert result == sample_project
            mock_project_repo.get_by_name.assert_called_with(name_variant, UserID(user_id))

    def test_get_project_empty_name(self, use_case):
        """Test with empty project name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Name cannot be empty"):
            use_case.execute(name="", user_id="user123")

    def test_get_project_whitespace_name(self, use_case):
        """Test with whitespace-only project name"""
        # Act & Assert
        with pytest.raises(ValueError, match="Name cannot be empty"):
            use_case.execute(name="   ", user_id="user123")

    def test_get_project_by_name_not_found(self, use_case, mock_project_repo):
        """Test getting non-existent project by name"""
        # Arrange
        project_name = "Non-existent Project"
        user_id = "user123"
        
        mock_project_repo.get_by_name.return_value = None
        
        # Act & Assert
        with pytest.raises(ProjectNotFoundError, match=f"Project '{project_name}' not found"):
            use_case.execute(name=project_name, user_id=user_id)

    def test_get_project_with_last_activity(self, use_case, mock_project_repo, sample_project):
        """Test project with last activity timestamp"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        last_activity = datetime.now(timezone.utc)
        
        sample_project.last_activity = last_activity
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act
        result = use_case.execute(project_id=project_id, user_id=user_id)
        
        # Assert
        assert result.last_activity == last_activity

    def test_get_project_invalid_uuid(self, use_case):
        """Test with invalid UUID format"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid project ID format"):
            use_case.execute(project_id="not-a-uuid", user_id="user123")

    def test_get_project_none_user_id(self, use_case):
        """Test with None user_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="User ID is required"):
            use_case.execute(project_id=str(uuid4()), user_id=None)

    def test_get_project_caching_behavior(self, use_case, mock_project_repo, sample_project):
        """Test that project is fetched from repository each time"""
        # Arrange
        project_id = sample_project.id.value
        user_id = "user123"
        
        mock_project_repo.get_by_id.return_value = sample_project
        
        # Act - Get same project twice
        result1 = use_case.execute(project_id=project_id, user_id=user_id)
        result2 = use_case.execute(project_id=project_id, user_id=user_id)
        
        # Assert - Repository called twice (no caching)
        assert mock_project_repo.get_by_id.call_count == 2
        assert result1 == result2