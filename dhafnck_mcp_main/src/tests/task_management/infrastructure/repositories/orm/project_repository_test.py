"""
Tests for Project Repository ORM implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from fastmcp.task_management.infrastructure.repositories.orm.project_repository import (
    ProjectRepository
)
from fastmcp.task_management.infrastructure.orm.models import (
    Project as ProjectORM,
    Task as TaskORM,
    Agent as AgentORM,
    ProjectGitBranch as GitBranchORM,
    ProjectContext as ContextORM
)
from fastmcp.task_management.domain.entities import Project


class TestProjectRepository:
    """Test Project Repository functionality"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock(spec=Session)
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.flush = Mock()
        session.refresh = Mock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session"""
        return ProjectRepository(session=mock_session)

    @pytest.fixture
    def sample_project_orm(self):
        """Create sample project ORM object"""
        project = ProjectORM(
            id="proj-123",
            name="Test Project",
            description="A test project",
            user_id="user-123",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        # Add related objects
        project.git_branches = [
            GitBranchORM(
                id="branch-1",
                git_branch_name="main",
                git_branch_description="Main branch"
            )
        ]
        project.agents = [
            AgentORM(
                id="agent-1",
                name="coding-agent",
                project_id="proj-123"
            )
        ]
        return project

    def test_create_project(self, repository, mock_session):
        """Test creating a new project"""
        project = Project(
            id="proj-456",
            name="New Project",
            description="Brand new project",
            user_id="user-456"
        )
        
        # Configure mock
        mock_session.query().filter().first.return_value = None  # No duplicate
        
        # Execute
        created = repository.create(project)
        
        # Verify
        assert mock_session.add.called
        assert mock_session.commit.called
        assert created.id == project.id
        assert created.name == project.name

    def test_create_project_duplicate_name(self, repository, mock_session):
        """Test creating project with duplicate name"""
        project = Project(
            id="proj-789",
            name="Existing Project",
            description="Another project with same name",
            user_id="user-123"
        )
        
        # Configure mock to return existing project
        existing = ProjectORM(id="proj-existing", name="Existing Project")
        mock_session.query().filter().first.return_value = existing
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            repository.create(project)
        
        assert mock_session.rollback.called

    def test_get_project_by_id(self, repository, mock_session, sample_project_orm):
        """Test retrieving project by ID"""
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        project = repository.get_by_id("proj-123")
        
        # Verify
        assert project is not None
        assert project.id == "proj-123"
        assert project.name == "Test Project"
        assert len(project.git_branch_ids) == 1
        assert len(project.agent_ids) == 1

    def test_get_project_not_found(self, repository, mock_session):
        """Test retrieving non-existent project"""
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Execute
        project = repository.get_by_id("non-existent")
        
        # Verify
        assert project is None

    def test_get_project_by_name(self, repository, mock_session, sample_project_orm):
        """Test retrieving project by name"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        project = repository.get_by_name("Test Project", user_id="user-123")
        
        # Verify
        assert project is not None
        assert project.name == "Test Project"
        assert project.user_id == "user-123"

    def test_update_project(self, repository, mock_session, sample_project_orm):
        """Test updating project"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Create updated project
        updated_project = Project(
            id="proj-123",
            name="Updated Project Name",
            description="Updated description",
            user_id="user-123"
        )
        
        # Execute
        result = repository.update(updated_project)
        
        # Verify
        assert mock_session.commit.called
        assert result.name == "Updated Project Name"
        assert result.description == "Updated description"

    def test_delete_project(self, repository, mock_session, sample_project_orm):
        """Test deleting project"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        repository.delete("proj-123")
        
        # Verify
        assert mock_session.delete.called_with(sample_project_orm)
        assert mock_session.commit.called

    def test_list_projects(self, repository, mock_session):
        """Test listing all projects"""
        # Create sample projects
        projects = [
            ProjectORM(id=f"proj-{i}", name=f"Project {i}", user_id="user-123")
            for i in range(3)
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().all.return_value = projects
        mock_session.query.return_value = mock_query
        
        # Execute
        result = repository.list(user_id="user-123")
        
        # Verify
        assert len(result) == 3
        assert all(isinstance(p, Project) for p in result)
        assert result[0].name == "Project 0"

    def test_list_projects_with_filters(self, repository, mock_session):
        """Test listing projects with filters"""
        # Create filtered projects
        active_projects = [
            ProjectORM(
                id="proj-1",
                name="Active Project",
                user_id="user-123",
                status="active"
            )
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().filter().all.return_value = active_projects
        mock_session.query.return_value = mock_query
        
        # Execute
        result = repository.list(user_id="user-123", filters={"status": "active"})
        
        # Verify
        assert len(result) == 1
        assert result[0].name == "Active Project"

    def test_get_project_statistics(self, repository, mock_session, sample_project_orm):
        """Test getting project statistics"""
        # Configure project with tasks
        sample_project_orm.tasks = [
            TaskORM(id=f"task-{i}", status=status, project_id="proj-123")
            for i, status in enumerate(["done", "done", "in_progress", "todo"])
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        stats = repository.get_statistics("proj-123")
        
        # Verify
        assert stats["total_tasks"] == 4
        assert stats["completed_tasks"] == 2
        assert stats["in_progress_tasks"] == 1
        assert stats["pending_tasks"] == 1
        assert stats["total_agents"] == 1
        assert stats["total_branches"] == 1

    def test_bulk_create_projects(self, repository, mock_session):
        """Test creating multiple projects at once"""
        projects = [
            Project(
                id=f"proj-bulk-{i}",
                name=f"Bulk Project {i}",
                user_id="user-123"
            )
            for i in range(5)
        ]
        
        # Configure mock
        mock_session.query().filter().first.return_value = None  # No duplicates
        mock_session.bulk_insert_mappings = Mock()
        
        # Execute
        created = repository.bulk_create(projects)
        
        # Verify
        assert len(created) == 5
        assert mock_session.commit.called

    def test_transaction_rollback(self, repository, mock_session):
        """Test transaction rollback on error"""
        project = Project(
            id="proj-error",
            name="Error Project",
            user_id="user-123"
        )
        
        # Configure mock to raise error on commit
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        mock_session.query().filter().first.return_value = None
        
        # Execute and expect error
        with pytest.raises(SQLAlchemyError):
            repository.create(project)
        
        # Verify rollback was called
        assert mock_session.rollback.called

    def test_eager_loading_relationships(self, repository, mock_session):
        """Test eager loading of related entities"""
        # Configure mock with complex relationships
        project_orm = ProjectORM(id="proj-123", name="Complex Project")
        project_orm.tasks = [TaskORM(id=f"task-{i}") for i in range(10)]
        project_orm.agents = [AgentORM(id=f"agent-{i}") for i in range(5)]
        project_orm.git_branches = [GitBranchORM(id=f"branch-{i}") for i in range(3)]
        
        mock_query = Mock()
        mock_query.options().filter().first.return_value = project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        project = repository.get_by_id("proj-123", include_relationships=True)
        
        # Verify eager loading was used
        assert mock_query.options.called
        assert len(project.task_ids) == 10
        assert len(project.agent_ids) == 5
        assert len(project.git_branch_ids) == 3

    def test_partial_update(self, repository, mock_session, sample_project_orm):
        """Test partial update of project fields"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute partial update
        updates = {"description": "New description only"}
        result = repository.partial_update("proj-123", updates)
        
        # Verify
        assert result.description == "New description only"
        assert result.name == "Test Project"  # Unchanged
        assert mock_session.commit.called

    def test_cascade_delete(self, repository, mock_session, sample_project_orm):
        """Test cascade deletion of related entities"""
        # Add more related entities
        sample_project_orm.contexts = [
            ContextORM(id="ctx-1", level="project", context_id="proj-123")
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_project_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        repository.delete("proj-123", cascade=True)
        
        # Verify cascading delete
        assert mock_session.delete.called
        # In real implementation, related entities would be deleted via cascade

    def test_search_projects(self, repository, mock_session):
        """Test searching projects by keyword"""
        matching_projects = [
            ProjectORM(
                id="proj-1",
                name="Authentication System",
                description="User authentication project"
            ),
            ProjectORM(
                id="proj-2",
                name="Auth Module",
                description="Authentication and authorization"
            )
        ]
        
        # Configure mock for search
        mock_query = Mock()
        mock_query.filter().filter().all.return_value = matching_projects
        mock_session.query.return_value = mock_query
        
        # Execute search
        results = repository.search("auth", user_id="user-123")
        
        # Verify
        assert len(results) == 2
        assert all("auth" in p.name.lower() or "auth" in p.description.lower() 
                  for p in results)

    def test_performance_optimization(self, repository, mock_session):
        """Test query performance optimizations"""
        # Configure mock for count query
        mock_query = Mock()
        mock_query.filter().count.return_value = 1000
        mock_session.query.return_value = mock_query
        
        # Test optimized count
        count = repository.count(user_id="user-123")
        
        # Verify count query was used instead of loading all records
        assert count == 1000
        assert mock_query.filter().count.called
        assert not mock_query.all.called  # Should not load all records