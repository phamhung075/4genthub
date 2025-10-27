"""
Test suite for ListProjects use case

Tests the business logic for listing all projects for a user.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastmcp.task_management.application.use_cases.list_projects import ListProjectsUseCase
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.value_objects import ProjectID, UserID
from fastmcp.task_management.domain.exceptions import ValidationError


class TestListProjectsUseCase:
    """Test suite for ListProjects use case"""

    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        return Mock()

    @pytest.fixture
    def mock_statistics_service(self):
        """Create mock statistics service"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_project_repo, mock_statistics_service):
        """Create use case instance with mocks"""
        return ListProjectsUseCase(
            project_repository=mock_project_repo,
            statistics_service=mock_statistics_service
        )

    @pytest.fixture
    def sample_projects(self):
        """Create sample projects for testing"""
        user_id = UserID("user123")
        projects = []
        
        # Project 1 - Active with tasks
        p1 = Project(
            id=ProjectID(str(uuid4())),
            name="E-commerce Platform",
            description="Full-stack e-commerce solution",
            user_id=user_id
        )
        p1.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        p1.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        p1.total_tasks = 45
        p1.completed_tasks = 20
        p1.active_branches = 3
        projects.append(p1)
        
        # Project 2 - Completed
        p2 = Project(
            id=ProjectID(str(uuid4())),
            name="Blog System",
            description="Personal blog platform",
            user_id=user_id
        )
        p2.created_at = datetime.now(timezone.utc) - timedelta(days=60)
        p2.updated_at = datetime.now(timezone.utc) - timedelta(days=7)
        p2.total_tasks = 30
        p2.completed_tasks = 30
        p2.active_branches = 0
        projects.append(p2)
        
        # Project 3 - New project
        p3 = Project(
            id=ProjectID(str(uuid4())),
            name="Mobile App",
            description="React Native mobile application",
            user_id=user_id
        )
        p3.created_at = datetime.now(timezone.utc) - timedelta(days=3)
        p3.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
        p3.total_tasks = 5
        p3.completed_tasks = 0
        p3.active_branches = 1
        projects.append(p3)
        
        return projects

    def test_list_all_projects_success(self, use_case, mock_project_repo, sample_projects):
        """Test successfully listing all projects for a user"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id)
        
        # Assert
        assert len(result) == 3
        assert result[0].name == "E-commerce Platform"
        assert result[1].name == "Blog System"
        assert result[2].name == "Mobile App"
        
        # Verify repository call
        mock_project_repo.get_all_by_user.assert_called_once_with(UserID(user_id))

    def test_list_projects_empty_result(self, use_case, mock_project_repo):
        """Test listing projects when user has none"""
        # Arrange
        user_id = "new_user"
        
        mock_project_repo.get_all_by_user.return_value = []
        
        # Act
        result = use_case.execute(user_id=user_id)
        
        # Assert
        assert result == []
        assert len(result) == 0

    def test_list_projects_with_statistics(self, use_case, mock_project_repo, mock_statistics_service, sample_projects):
        """Test listing projects with computed statistics"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Add statistics to each project
        for project in sample_projects:
            mock_statistics_service.compute_project_stats.return_value = {
                'completion_rate': (project.completed_tasks / project.total_tasks * 100) if project.total_tasks > 0 else 0,
                'active_users': 5,
                'last_activity': project.updated_at
            }
        
        # Act
        result = use_case.execute(user_id=user_id, include_statistics=True)
        
        # Assert
        assert len(result) == 3
        # Verify statistics were computed
        assert mock_statistics_service.compute_project_stats.call_count == 3

    def test_list_projects_sorted_by_updated(self, use_case, mock_project_repo, sample_projects):
        """Test listing projects sorted by last update"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, sort_by='updated_at')
        
        # Assert - Should be sorted by most recent first
        assert result[0].name == "Mobile App"  # 1 hour ago
        assert result[1].name == "E-commerce Platform"  # 2 hours ago
        assert result[2].name == "Blog System"  # 7 days ago

    def test_list_projects_sorted_by_created(self, use_case, mock_project_repo, sample_projects):
        """Test listing projects sorted by creation date"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, sort_by='created_at')
        
        # Assert - Should be sorted by newest first
        assert result[0].name == "Mobile App"  # 3 days ago
        assert result[1].name == "E-commerce Platform"  # 30 days ago
        assert result[2].name == "Blog System"  # 60 days ago

    def test_list_projects_sorted_by_name(self, use_case, mock_project_repo, sample_projects):
        """Test listing projects sorted alphabetically"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, sort_by='name')
        
        # Assert - Should be sorted alphabetically
        assert result[0].name == "Blog System"
        assert result[1].name == "E-commerce Platform"
        assert result[2].name == "Mobile App"

    def test_list_projects_filtered_by_status(self, use_case, mock_project_repo, sample_projects):
        """Test filtering projects by status"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act - Get only active projects (has uncompleted tasks)
        result = use_case.execute(user_id=user_id, filter_status='active')
        
        # Assert
        assert len(result) == 2  # E-commerce and Mobile App
        assert all(p.completed_tasks < p.total_tasks for p in result)

    def test_list_projects_filtered_completed(self, use_case, mock_project_repo, sample_projects):
        """Test filtering for completed projects"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, filter_status='completed')
        
        # Assert
        assert len(result) == 1  # Only Blog System
        assert result[0].name == "Blog System"
        assert result[0].completed_tasks == result[0].total_tasks

    def test_list_projects_with_limit(self, use_case, mock_project_repo, sample_projects):
        """Test limiting number of returned projects"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, limit=2)
        
        # Assert
        assert len(result) == 2

    def test_list_projects_with_offset(self, use_case, mock_project_repo, sample_projects):
        """Test pagination with offset"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, offset=1, limit=2)
        
        # Assert
        assert len(result) == 2
        assert result[0] == sample_projects[1]
        assert result[1] == sample_projects[2]

    def test_list_projects_none_user_id(self, use_case):
        """Test with None user_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="User ID is required"):
            use_case.execute(user_id=None)

    def test_list_projects_empty_user_id(self, use_case):
        """Test with empty user_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            use_case.execute(user_id="")

    def test_list_projects_invalid_sort_field(self, use_case, mock_project_repo, sample_projects):
        """Test with invalid sort field"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid sort field"):
            use_case.execute(user_id=user_id, sort_by='invalid_field')

    def test_list_projects_large_dataset(self, use_case, mock_project_repo):
        """Test handling large number of projects"""
        # Arrange
        user_id = "user123"
        
        # Create 100 projects
        large_project_list = []
        for i in range(100):
            p = Project(
                id=ProjectID(str(uuid4())),
                name=f"Project {i:03d}",
                description=f"Description for project {i}",
                user_id=UserID(user_id)
            )
            p.total_tasks = i
            p.completed_tasks = i // 2
            large_project_list.append(p)
        
        mock_project_repo.get_all_by_user.return_value = large_project_list
        
        # Act
        result = use_case.execute(user_id=user_id)
        
        # Assert
        assert len(result) == 100

    def test_list_projects_with_active_filter(self, use_case, mock_project_repo, sample_projects):
        """Test filtering for projects with active branches"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, has_active_branches=True)
        
        # Assert
        assert len(result) == 2  # E-commerce and Mobile App
        assert all(p.active_branches > 0 for p in result)

    def test_list_projects_with_search(self, use_case, mock_project_repo, sample_projects):
        """Test searching projects by name"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, search_query="mobile")
        
        # Assert
        assert len(result) == 1
        assert result[0].name == "Mobile App"

    def test_list_projects_search_case_insensitive(self, use_case, mock_project_repo, sample_projects):
        """Test case-insensitive search"""
        # Arrange
        user_id = "user123"
        
        mock_project_repo.get_all_by_user.return_value = sample_projects
        
        # Act
        result = use_case.execute(user_id=user_id, search_query="COMMERCE")
        
        # Assert
        assert len(result) == 1
        assert result[0].name == "E-commerce Platform"