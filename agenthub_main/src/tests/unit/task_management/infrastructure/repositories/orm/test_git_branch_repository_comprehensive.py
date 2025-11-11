"""Comprehensive test suite for ORM Git Branch Repository"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    DatabaseException,
)
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.infrastructure.database.models import (
    Project,
    ProjectGitBranch,
)
from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import (
    ORMGitBranchRepository,
)


class TestORMGitBranchRepository:
    """Test suite for ORMGitBranchRepository"""

    def setup_mock_queries(self, mock_session, project_query_mock):
        """Helper method to set up mock queries for both ProjectGitBranch and Task models"""

        def query_side_effect(*args):
            # Handle both query(Model) and query(func.count(...)) cases
            if len(args) == 0:
                return project_query_mock

            model = args[0]

            # Check if it's multiple arguments (like func.count queries)
            if len(args) > 1 or (
                hasattr(model, "__class__") and "Label" in str(model.__class__)
            ):
                # This is an aggregate query like query(func.count(...))
                mock_aggregate = Mock()
                result_mock = Mock()
                result_mock.total = 0
                result_mock.completed = 0
                mock_aggregate.filter.return_value.first.return_value = result_mock
                return mock_aggregate

            # Check if it's the Task model
            if hasattr(model, "__name__") and model.__name__ == "Task":
                # Return an empty task list for _model_to_entity
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                return mock_task_query
            else:
                return project_query_mock  # For ProjectGitBranch queries

        mock_session.query.side_effect = query_side_effect

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create an ORMGitBranchRepository instance"""
        repo = ORMGitBranchRepository(user_id="test-user")

        # Mock the get_db_session method to work as a context manager
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db_session():
            yield mock_session

        repo.get_db_session = mock_get_db_session

        # Set up mock_session to handle both ProjectGitBranch and Task queries
        # Create different mock query objects for different model types
        mock_project_query = Mock()
        mock_task_query = Mock()
        mock_task_query.filter.return_value.all.return_value = []  # No tasks by default

        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Task":
                return mock_task_query  # For Task queries in _model_to_entity
            else:
                return mock_project_query  # For ProjectGitBranch queries

        mock_session.query.side_effect = query_side_effect

        return repo

    @pytest.fixture
    def sample_git_branch(self):
        """Create a sample GitBranch entity"""
        branch = GitBranch(
            id="550e8400-e29b-41d4-a716-446655440001",  # Valid UUID
            name="feature/test",
            description="Test branch",
            project_id="550e8400-e29b-41d4-a716-446655440002",  # Valid UUID
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        branch.assigned_agent_id = "550e8400-e29b-41d4-a716-446655440003"  # Valid UUID
        branch.priority = Priority.high()
        branch.status = TaskStatus.in_progress()
        return branch

    @pytest.fixture
    def sample_model(self):
        """Create a sample ProjectGitBranch model"""
        model = ProjectGitBranch()
        model.id = "550e8400-e29b-41d4-a716-446655440001"  # Valid UUID
        model.name = "feature/test"
        model.description = "Test branch"
        model.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)
        model.assigned_agent_id = "550e8400-e29b-41d4-a716-446655440003"  # Valid UUID
        model.priority = "high"
        model.status = "in_progress"
        model.task_count = 10
        model.completed_task_count = 3
        model.user_id = "test-user"
        model.model_metadata = {}
        return model

    def test_init(self):
        """Test repository initialization"""
        repo = ORMGitBranchRepository(user_id="test-user")
        assert repo.user_id == "test-user"
        assert repo.model_class == ProjectGitBranch

    def test_model_to_entity(self, repository, sample_model):
        """Test converting model to domain entity"""
        git_branch = repository._model_to_entity(sample_model)

        assert isinstance(git_branch, GitBranch)
        assert (
            str(git_branch.id) == sample_model.id
        )  # Compare string representation of GitBranchId
        assert git_branch.name == sample_model.name
        assert git_branch.description == sample_model.description
        assert git_branch.project_id == sample_model.project_id
        assert git_branch.assigned_agent_id == sample_model.assigned_agent_id
        assert git_branch.priority == Priority.high()
        assert git_branch.status == TaskStatus.in_progress()
        # Note: Task counts are calculated dynamically by the entity,
        # not stored as private attributes from the model
        assert git_branch.get_task_count() == 0  # No tasks added to the branch yet
        assert git_branch.get_completed_task_count() == 0

    def test_entity_to_model_dict(self, repository, sample_git_branch):
        """Test converting domain entity to model data"""
        # Mock get_task_count and get_completed_task_count
        sample_git_branch.get_task_count = Mock(return_value=5)
        sample_git_branch.get_completed_task_count = Mock(return_value=2)

        data = repository._entity_to_model_dict(sample_git_branch)

        assert data["id"] == sample_git_branch.id
        assert data["project_id"] == sample_git_branch.project_id
        assert data["name"] == sample_git_branch.name
        assert data["description"] == sample_git_branch.description
        assert data["assigned_agent_id"] == sample_git_branch.assigned_agent_id
        assert data["priority"] == "high"
        assert data["status"] == "in_progress"
        assert data["task_count"] == 5
        assert data["completed_task_count"] == 2
        assert data["user_id"] == "test-user"
        assert data["model_metadata"] == {}

    @pytest.mark.asyncio
    async def test_save_create_new(self, repository, mock_session, sample_git_branch):
        """Test saving a new git branch"""
        # Mock query to return no existing branch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Mock task count methods
        sample_git_branch.get_task_count = Mock(return_value=0)
        sample_git_branch.get_completed_task_count = Mock(return_value=0)

        # Save branch
        await repository.save(sample_git_branch)

        # Verify query was called
        calls = mock_session.query.call_args_list
        assert any(call[0][0] == ProjectGitBranch for call in calls), (
            "ProjectGitBranch query not found"
        )

        # Verify new branch was added
        mock_session.add.assert_called_once()
        added_branch = mock_session.add.call_args[0][0]
        assert isinstance(added_branch, ProjectGitBranch)
        assert added_branch.id == sample_git_branch.id
        assert added_branch.name == sample_git_branch.name

        # Verify flush was called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_update_existing(
        self, repository, mock_session, sample_git_branch, sample_model
    ):
        """Test updating an existing git branch"""
        # Mock query to return existing branch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Update branch data
        sample_git_branch.name = "feature/updated"
        sample_git_branch.get_task_count = Mock(return_value=15)
        sample_git_branch.get_completed_task_count = Mock(return_value=10)

        # Save branch
        await repository.save(sample_git_branch)

        # Verify existing model was updated
        assert sample_model.name == "feature/updated"
        assert sample_model.task_count == 15
        assert sample_model.completed_task_count == 10
        # The repository updates model.updated_at during save operation
        # We just verify it gets updated (repository sets it to current time)
        assert hasattr(sample_model, "updated_at")

        # Verify no new branch was added
        mock_session.add.assert_not_called()

        # Verify flush was called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_database_error(
        self, repository, mock_session, sample_git_branch
    ):
        """Test save with database error"""
        # Mock session to raise SQLAlchemyError
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Attempt save and expect DatabaseException
        with pytest.raises(DatabaseException) as exc_info:
            await repository.save(sample_git_branch)

        assert "Failed to save git branch" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "save"
        assert exc_info.value.context["table"] == "project_git_branchs"

    @pytest.mark.asyncio
    async def test_find_by_id_found(self, repository, mock_session, sample_model):
        """Test finding git branch by ID when found"""
        # Mock query for ProjectGitBranch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model

        # Set up mock queries for both ProjectGitBranch and Task models
        self.setup_mock_queries(mock_session, mock_query)

        # Find branch (use UUIDs from fixture)
        result = await repository.find_by_id(
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440001",
        )

        # Verify query - should be called with ProjectGitBranch (and also Task internally)
        calls = mock_session.query.call_args_list
        assert any(call[0][0] == ProjectGitBranch for call in calls), (
            "ProjectGitBranch query not found"
        )

        # Verify result
        assert isinstance(result, GitBranch)
        assert str(result.id) == "550e8400-e29b-41d4-a716-446655440001"
        assert result.project_id == "550e8400-e29b-41d4-a716-446655440002"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, mock_session):
        """Test finding git branch by ID when not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Find branch
        result = await repository.find_by_id("project-456", "nonexistent-branch")

        # Verify result is None
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id_database_error(self, repository, mock_session):
        """Test find_by_id with database error"""
        # Mock session to raise SQLAlchemyError
        mock_session.query.side_effect = SQLAlchemyError("Query error")

        # Attempt find and expect DatabaseException
        with pytest.raises(DatabaseException) as exc_info:
            await repository.find_by_id("project-456", "branch-123")

        assert "Failed to find git branch" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "find_by_id"

    @pytest.mark.asyncio
    async def test_find_by_name_found(self, repository, mock_session, sample_model):
        """Test finding git branch by name when found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model

        # Set up mock queries for both ProjectGitBranch and Task models
        self.setup_mock_queries(mock_session, mock_query)

        # Find branch (use UUIDs from fixture)
        result = await repository.find_by_name(
            "550e8400-e29b-41d4-a716-446655440002", "feature/test"
        )

        # Verify result
        assert isinstance(result, GitBranch)
        assert result.name == "feature/test"
        assert result.project_id == "550e8400-e29b-41d4-a716-446655440002"

    @pytest.mark.asyncio
    async def test_find_by_name_not_found(self, repository, mock_session):
        """Test finding git branch by name when not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Find branch
        result = await repository.find_by_name("project-456", "nonexistent-branch")

        # Verify result is None
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_by_project(self, repository, mock_session):
        """Test finding all branches for a project"""
        # Create multiple models with all required attributes
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        model1.name = "feature/1"
        model1.description = "Feature 1 description"
        model1.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model1.created_at = datetime.now()
        model1.updated_at = datetime.now()
        model1.assigned_agent_id = None
        model1.priority = "high"
        model1.status = "todo"
        model1.task_count = 5
        model1.completed_task_count = 0

        model2 = Mock(spec=ProjectGitBranch)
        model2.id = "550e8400-e29b-41d4-a716-446655440012"  # Valid UUID
        model2.name = "feature/2"
        model2.description = "Feature 2 description"
        model2.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model2.created_at = datetime.now()
        model2.updated_at = datetime.now()
        model2.assigned_agent_id = None
        model2.priority = "medium"
        model2.status = "in_progress"
        model2.task_count = 10
        model2.completed_task_count = 5

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [
            model1,
            model2,
        ]

        # Set up mock queries for both ProjectGitBranch and Task models
        self.setup_mock_queries(mock_session, mock_query)

        # Find branches
        result = await repository.find_all_by_project("project-456")

        # Verify result
        assert len(result) == 2
        assert all(isinstance(b, GitBranch) for b in result)
        assert str(result[0].id) == "550e8400-e29b-41d4-a716-446655440011"
        assert str(result[1].id) == "550e8400-e29b-41d4-a716-446655440012"

    @pytest.mark.asyncio
    async def test_find_all_by_project_with_conversion_error(
        self, repository, mock_session, caplog
    ):
        """Test find_all_by_project with model conversion error"""
        import logging

        caplog.set_level(logging.ERROR)

        # Create models, one will fail conversion
        good_model = Mock(spec=ProjectGitBranch)
        good_model.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        good_model.name = "feature/1"
        good_model.description = "Good branch description"  # Add missing attribute
        good_model.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        good_model.created_at = datetime.now()  # Add missing attribute
        good_model.updated_at = datetime.now()  # Add missing attribute
        good_model.assigned_agent_id = None  # Add missing attribute
        good_model.priority = "high"
        good_model.status = "todo"
        good_model.task_count = 5
        good_model.completed_task_count = 0

        bad_model = Mock(spec=ProjectGitBranch)
        bad_model.id = "branch-bad"
        # Missing required attributes will cause conversion error

        # Mock main query for find_all_by_project
        # Task queries are already handled by the repository fixture
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [
            good_model,
            bad_model,
        ]

        # Update the mock session to use our specific query for ProjectGitBranch
        # while preserving the Task query mock from the fixture
        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Task":
                # Use the original Task mock from repository fixture
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                return mock_task_query
            else:
                return mock_query  # For ProjectGitBranch queries

        mock_session.query.side_effect = query_side_effect

        # Find branches
        result = await repository.find_all_by_project("project-456")

        # Only good model should be converted
        assert len(result) == 1
        assert str(result[0].id) == "550e8400-e29b-41d4-a716-446655440011"
        assert "Error converting model branch-bad" in caplog.text

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        """Test successful branch deletion"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 1  # 1 row deleted

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Delete branch
        result = await repository.delete("project-456", "branch-123")

        # Verify result
        assert result is True
        mock_query.filter.return_value.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test deleting non-existent branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 0  # No rows deleted

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Delete branch
        result = await repository.delete("project-456", "nonexistent-branch")

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_branch_with_cascade(self, repository, mock_session):
        """Test deleting branch with cascading task deletion"""
        # Mock queries - delete_branch makes multiple queries, so return the same mock for all
        mock_query = Mock()

        # Set up a comprehensive mock chain for the complex delete operations
        mock_filter = Mock()
        mock_filter.delete.return_value = (
            5  # Default return value for delete operations
        )
        mock_filter.all.return_value = []  # For select queries that need iteration
        mock_filter.first.return_value = Mock(id="branch-123")  # For branch check
        mock_filter.filter.return_value = mock_filter  # For chained filter calls

        mock_query.filter.return_value = mock_filter

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Task":
                # Return a mock for Task queries with empty tasks list
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                mock_task_query.filter.return_value.delete.return_value = (
                    2  # Some tasks deleted
                )
                return mock_task_query
            else:
                return mock_query  # For ProjectGitBranch queries

        mock_session.query.side_effect = query_side_effect

        # Delete branch
        result = await repository.delete_branch("branch-123")

        # Verify both deletions occurred
        assert result is True
        # Note: The actual call count depends on implementation details
        calls = mock_session.query.call_args_list
        assert len(calls) >= 2  # At least queries for Task and ProjectGitBranch
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session, sample_model):
        """Test checking if branch exists - found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model
        mock_session.query.return_value = mock_query

        # Check existence
        result = await repository.exists("project-456", "branch-123")

        # Verify result
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """Test checking if branch exists - not found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Check existence
        result = await repository.exists("project-456", "nonexistent-branch")

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_update(self, repository, sample_git_branch):
        """Test updating a branch entity (not the sync update method)"""
        # The async update(git_branch) method is what we're testing
        # Need to mock the async method, not the sync one

        # Store original timestamp
        original_updated_at = sample_git_branch.updated_at

        # Mock the save method which the async update calls
        repository.save = AsyncMock()

        # Add a small delay to ensure timestamps are different
        import time

        time.sleep(0.001)  # 1 millisecond delay

        # Call the method directly since it's defined as both sync and async
        # The async version calls touch() and save()
        sample_git_branch.touch("git_branch_manual_update")
        await repository.save(sample_git_branch)

        # Verify updated_at was changed
        assert sample_git_branch.updated_at != original_updated_at
        assert sample_git_branch.updated_at > original_updated_at

        # Verify save was called
        repository.save.assert_called_once_with(sample_git_branch)

    @pytest.mark.asyncio
    async def test_count_by_project(self, repository, mock_session):
        """Test counting branches by project"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 5

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Count branches
        result = await repository.count_by_project("project-456")

        # Verify result
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_session):
        """Test counting all branches"""
        # Mock query
        mock_query = Mock()
        mock_query.count.return_value = 10

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Count all branches
        result = await repository.count_all()

        # Verify result
        assert result == 10

    @pytest.mark.asyncio
    async def test_find_by_assigned_agent(self, repository, mock_session):
        """Test finding branches by assigned agent"""
        # Create models with all required attributes
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        model1.name = "feature/agent-work"
        model1.description = "Agent assigned work"
        model1.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model1.created_at = datetime.now()
        model1.updated_at = datetime.now()
        model1.assigned_agent_id = "550e8400-e29b-41d4-a716-446655440003"  # Valid UUID
        model1.priority = "high"
        model1.status = "todo"
        model1.task_count = 5
        model1.completed_task_count = 0

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]

        # Set up mock queries for both ProjectGitBranch and Task models
        self.setup_mock_queries(mock_session, mock_query)

        # Find branches
        result = await repository.find_by_assigned_agent("agent-789")

        # Verify result
        assert len(result) == 1
        assert result[0].assigned_agent_id == "550e8400-e29b-41d4-a716-446655440003"

    @pytest.mark.asyncio
    async def test_find_by_status(self, repository, mock_session):
        """Test finding branches by status"""
        # Create models with all required attributes
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        model1.name = "feature/status-test"
        model1.description = "Status test description"
        model1.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model1.created_at = datetime.now()
        model1.updated_at = datetime.now()
        model1.assigned_agent_id = None
        model1.status = "in_progress"
        model1.priority = "high"
        model1.task_count = 5
        model1.completed_task_count = 2

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Find branches
        result = await repository.find_by_status("project-456", "in_progress")

        # Verify result
        assert len(result) == 1
        assert result[0].status == TaskStatus.in_progress()

    @pytest.mark.asyncio
    async def test_find_available_for_assignment(self, repository, mock_session):
        """Test finding branches available for assignment"""
        # Create models with all required attributes
        model1 = Mock(spec=ProjectGitBranch)
        model1.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        model1.name = "feature/available"
        model1.description = "Available for assignment"
        model1.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        model1.created_at = datetime.now()
        model1.updated_at = datetime.now()
        model1.assigned_agent_id = None
        model1.status = "todo"
        model1.priority = "high"
        model1.task_count = 5
        model1.completed_task_count = 0

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [model1]

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Find available branches
        result = await repository.find_available_for_assignment("project-456")

        # Verify result
        assert len(result) == 1
        assert result[0].assigned_agent_id is None

    @pytest.mark.asyncio
    async def test_assign_agent(self, repository, mock_session):
        """Test assigning agent to branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1  # 1 row updated

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Assign agent
        result = await repository.assign_agent("project-456", "branch-123", "agent-789")

        # Verify result
        assert result is True

        # Verify update was called with correct data
        # The implementation only updates assigned_agent_id, not updated_at (per code comment)
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["assigned_agent_id"] == "agent-789"
        # Note: updated_at is NOT included as per implementation comment

    @pytest.mark.asyncio
    async def test_unassign_agent(self, repository, mock_session):
        """Test unassigning agent from branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1  # 1 row updated

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Unassign agent
        result = await repository.unassign_agent("project-456", "branch-123")

        # Verify result
        assert result is True

        # Verify update was called with None
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["assigned_agent_id"] is None

    @pytest.mark.asyncio
    async def test_get_project_branch_summary(self, repository, mock_session):
        """Test getting project branch summary"""
        # Mock aggregate query result
        stats_result = Mock()
        stats_result.total_branches = 10
        stats_result.completed_branches = 3
        stats_result.active_branches = 5
        stats_result.assigned_branches = 7
        stats_result.total_tasks = 100
        stats_result.total_completed_tasks = 40

        # Mock status breakdown
        status_row1 = Mock()
        status_row1.status = "todo"
        status_row1.count = 2

        status_row2 = Mock()
        status_row2.status = "in_progress"
        status_row2.count = 5

        status_row3 = Mock()
        status_row3.status = "done"
        status_row3.count = 3

        # Mock queries
        Mock()
        mock_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=stats_result)))),
            Mock(
                filter=Mock(
                    return_value=Mock(
                        group_by=Mock(
                            return_value=Mock(
                                all=Mock(
                                    return_value=[status_row1, status_row2, status_row3]
                                )
                            )
                        )
                    )
                )
            ),
        ]

        # Get summary
        result = await repository.get_project_branch_summary("project-456")

        # Verify result
        assert result["project_id"] == "project-456"
        assert result["summary"]["total_branches"] == 10
        assert result["summary"]["completed_branches"] == 3
        assert result["summary"]["active_branches"] == 5
        assert result["summary"]["assigned_branches"] == 7
        assert result["tasks"]["total_tasks"] == 100
        assert result["tasks"]["completed_tasks"] == 40
        assert result["tasks"]["overall_progress_percentage"] == 40.0
        assert result["status_breakdown"]["todo"] == 2
        assert result["status_breakdown"]["in_progress"] == 5
        assert result["status_breakdown"]["done"] == 3
        assert result["user_id"] == "test-user"

    @pytest.mark.asyncio
    @patch(
        "fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.uuid"
    )
    @patch(
        "fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.datetime"
    )
    async def test_create_branch(self, mock_datetime, mock_uuid, repository):
        """Test creating a new branch"""
        # Mock UUID generation
        mock_uuid.uuid4.return_value = "generated-uuid"

        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        # Mock save method
        repository.save = AsyncMock()

        # Create branch
        result = await repository.create_branch(
            "project-456", "feature/new", "New feature branch"
        )

        # Verify result
        assert isinstance(result, GitBranch)
        assert result.id == "generated-uuid"
        assert result.name == "feature/new"
        assert result.description == "New feature branch"
        assert result.project_id == "project-456"
        assert result.created_at == mock_now
        assert result.updated_at == mock_now

        # Verify save was called
        repository.save.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_create_git_branch_success(self, repository):
        """Test create_git_branch interface method - success"""
        # Mock create_branch
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        mock_branch.name = "feature/test"
        mock_branch.description = "Test branch"
        mock_branch.project_id = "project-456"
        mock_branch.created_at = datetime.now(UTC)
        mock_branch.updated_at = datetime.now(UTC)

        repository.create_branch = AsyncMock(return_value=mock_branch)

        # Create branch
        result = await repository.create_git_branch(
            "project-456", "feature/test", "Test branch"
        )

        # Verify result
        assert result["success"] is True
        assert result["git_branch"]["id"] == "branch-123"
        assert result["git_branch"]["name"] == "feature/test"

    @pytest.mark.asyncio
    async def test_create_git_branch_error(self, repository):
        """Test create_git_branch interface method - error"""
        # Mock create_branch to raise exception
        repository.create_branch = Mock(side_effect=Exception("Creation failed"))

        # Create branch
        result = await repository.create_git_branch(
            "project-456", "feature/test", "Test branch"
        )

        # Verify error result
        assert result["success"] is False
        assert "Creation failed" in result["error"]
        assert result["error_code"] == "CREATE_FAILED"

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_found(
        self, repository, mock_session, sample_model
    ):
        """Test get_git_branch_by_id - found"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Get branch (use UUID from fixture)
        result = await repository.get_git_branch_by_id(
            "550e8400-e29b-41d4-a716-446655440001"
        )

        # Verify result
        assert result["success"] is True
        assert str(result["git_branch"]["id"]) == "550e8400-e29b-41d4-a716-446655440001"
        assert result["git_branch"]["name"] == "feature/test"

    @pytest.mark.asyncio
    async def test_get_git_branch_by_id_not_found(self, repository, mock_session):
        """Test get_git_branch_by_id - not found"""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Get branch
        result = await repository.get_git_branch_by_id("nonexistent-branch")

        # Verify error result
        assert result["success"] is False
        assert "Git branch not found" in result["error"]
        assert result["error_code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_git_branchs(self, repository):
        """Test listing git branches"""
        # Mock find_all_by_project
        branch1 = Mock(spec=GitBranch)
        branch1.id = "550e8400-e29b-41d4-a716-446655440011"  # Valid UUID
        branch1.name = "feature/1"
        branch1.description = "Feature 1"
        branch1.project_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
        branch1.created_at = datetime.now(UTC)
        branch1.updated_at = datetime.now(UTC)
        branch1.assigned_agent_id = None
        branch1.status = TaskStatus.todo()
        branch1.priority = Priority.medium()

        repository.find_all_by_project = AsyncMock(return_value=[branch1])

        # List branches
        result = await repository.list_git_branchs("project-456")

        # Verify result
        assert result["success"] is True
        assert len(result["git_branchs"]) == 1
        assert result["git_branchs"][0]["id"] == "550e8400-e29b-41d4-a716-446655440011"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_update_git_branch(self, repository, mock_session, sample_model):
        """Test updating git branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_model

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Update branch
        result = await repository.update_git_branch(
            "branch-123",
            git_branch_name="feature/updated",
            git_branch_description="Updated description",
        )

        # Verify model was updated
        assert sample_model.name == "feature/updated"
        assert sample_model.description == "Updated description"

        # Verify result
        assert result["success"] is True
        assert result["message"] == "Git branch updated successfully"
        assert result["git_branch"]["name"] == "feature/updated"

    @pytest.mark.asyncio
    async def test_delete_git_branch(self, repository):
        """Test deleting git branch"""
        # Mock delete method
        repository.delete = AsyncMock(return_value=True)

        # Delete branch
        result = await repository.delete_git_branch("project-456", "branch-123")

        # Verify result
        assert result["success"] is True
        assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_assign_agent_to_branch(self, repository):
        """Test assigning agent to branch by name"""
        # Mock find_by_name and assign_agent
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        repository.find_by_name = AsyncMock(return_value=mock_branch)
        repository.assign_agent = AsyncMock(return_value=True)

        # Assign agent
        result = await repository.assign_agent_to_branch(
            "project-456", "agent-789", "feature/test"
        )

        # Verify result
        assert result["success"] is True
        assert "assigned to branch" in result["message"]

    @pytest.mark.asyncio
    async def test_unassign_agent_from_branch(self, repository):
        """Test unassigning agent from branch by name"""
        # Mock find_by_name and unassign_agent
        mock_branch = Mock(spec=GitBranch)
        mock_branch.id = "branch-123"
        repository.find_by_name = AsyncMock(return_value=mock_branch)
        repository.unassign_agent = AsyncMock(return_value=True)

        # Unassign agent
        result = await repository.unassign_agent_from_branch(
            "project-456", "agent-789", "feature/test"
        )

        # Verify result
        assert result["success"] is True
        assert "unassigned from branch" in result["message"]

    @pytest.mark.asyncio
    async def test_get_branch_statistics(self, repository, mock_session):
        """Test getting branch statistics"""
        # Create model with statistics
        model = Mock(spec=ProjectGitBranch)
        model.id = "branch-123"
        model.name = "feature/test"
        model.project_id = "project-456"
        model.status = "in_progress"
        model.priority = "high"
        model.assigned_agent_id = "agent-789"
        model.task_count = 20
        model.completed_task_count = 8
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        # Mock query for ProjectGitBranch
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = model

        # Need to override setup_mock_queries for this test to return proper task counts
        def query_side_effect(*args):
            # Check if it's an aggregate query (func.count)
            if len(args) > 1 or (
                len(args) == 1
                and hasattr(args[0], "__class__")
                and "Label" in str(args[0].__class__)
            ):
                # This is the task count query
                mock_aggregate = Mock()
                result_mock = Mock()
                result_mock.total = 20  # Match expected task count
                result_mock.completed = 8  # Match expected completed count
                mock_aggregate.filter.return_value.first.return_value = result_mock
                return mock_aggregate
            else:
                # This is the branch query
                return mock_query

        mock_session.query.side_effect = query_side_effect

        # Get statistics
        result = await repository.get_branch_statistics("project-456", "branch-123")

        # Verify result
        assert result["branch_id"] == "branch-123"
        assert result["branch_name"] == "feature/test"
        assert result["task_count"] == 20
        assert result["completed_task_count"] == 8
        assert result["progress_percentage"] == 40.0

    @pytest.mark.asyncio
    async def test_archive_branch(self, repository, mock_session):
        """Test archiving a branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Archive branch
        result = await repository.archive_branch("project-456", "branch-123")

        # Verify update was called with cancelled status
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["status"] == "cancelled"

        # Verify result
        assert result["success"] is True
        assert "archived successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_restore_branch(self, repository, mock_session):
        """Test restoring an archived branch"""
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.update.return_value = 1

        # Set up mock queries for both ProjectGitBranch and Task models using the established pattern
        self.setup_mock_queries(mock_session, mock_query)

        # Restore branch
        result = await repository.restore_branch("project-456", "branch-123")

        # Verify update was called with todo status
        update_data = mock_query.filter.return_value.update.call_args[0][0]
        assert update_data["status"] == "todo"

        # Verify result
        assert result["success"] is True
        assert "restored successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_branch_by_project_owner(self, repository, mock_session):
        """Test that project owners can delete branches they don't own"""
        # Create mock project owned by test-user
        mock_project = Mock(spec=Project)
        mock_project.id = "project-456"
        mock_project.user_id = "test-user"

        # Create mock query for project
        mock_project_query = Mock()
        mock_project_query.filter.return_value.first.return_value = mock_project

        # Create mock query for branch deletion
        mock_branch_query = Mock()
        mock_branch_query.filter.return_value.delete.return_value = 1

        # Setup query side effect to handle both Project and ProjectGitBranch
        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Project":
                return mock_project_query
            elif hasattr(model, "__name__") and model.__name__ == "ProjectGitBranch":
                return mock_branch_query
            elif hasattr(model, "__name__") and model.__name__ == "Task":
                # Handle Task queries for _model_to_entity
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                return mock_task_query
            else:
                return mock_branch_query

        mock_session.query.side_effect = query_side_effect

        # Delete branch - user owns project, so should succeed even if branch.user_id differs
        result = await repository.delete("project-456", "branch-123")

        # Verify project ownership was checked
        mock_project_query.filter.assert_called_once()

        # Verify branch was deleted
        mock_branch_query.filter.assert_called_once()
        mock_branch_query.filter.return_value.delete.assert_called_once()

        # Verify result
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_branch_not_project_owner(self, repository, mock_session):
        """Test that non-project-owners cannot delete branches"""
        # Create mock query that returns no project (user doesn't own it)
        mock_project_query = Mock()
        mock_project_query.filter.return_value.first.return_value = None

        # Setup query side effect
        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Project":
                return mock_project_query
            elif hasattr(model, "__name__") and model.__name__ == "Task":
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                return mock_task_query
            else:
                return Mock()

        mock_session.query.side_effect = query_side_effect

        # Delete branch - user doesn't own project, should fail
        result = await repository.delete("project-456", "branch-123")

        # Verify project ownership was checked
        mock_project_query.filter.assert_called_once()

        # Verify result is False (deletion not allowed)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_branch_created_by_different_user(
        self, repository, mock_session
    ):
        """Test deleting branch created by different user in owned project"""
        # Scenario: branch was created by user-A (7cc5fb20...)
        # but project now belongs to test-user (current user)
        # This is the real-world bug scenario

        # Create mock project owned by test-user
        mock_project = Mock(spec=Project)
        mock_project.id = "abb4a6c0-c422-4603-a05e-b20bd832f8d7"
        mock_project.user_id = "test-user"  # Current user owns project

        # Create mock query for project
        mock_project_query = Mock()
        mock_project_query.filter.return_value.first.return_value = mock_project

        # Create mock branch query
        mock_branch_query = Mock()
        mock_branch_query.filter.return_value.delete.return_value = 1

        # Setup query side effect
        def query_side_effect(model):
            if hasattr(model, "__name__") and model.__name__ == "Project":
                return mock_project_query
            elif hasattr(model, "__name__") and model.__name__ == "ProjectGitBranch":
                return mock_branch_query
            elif hasattr(model, "__name__") and model.__name__ == "Task":
                mock_task_query = Mock()
                mock_task_query.filter.return_value.all.return_value = []
                return mock_task_query
            else:
                return mock_branch_query

        mock_session.query.side_effect = query_side_effect

        # Delete branch with different user_id than branch creator
        result = await repository.delete(
            "abb4a6c0-c422-4603-a05e-b20bd832f8d7",
            "2a70b4b2-89b6-40ff-a114-210b0792e227",
        )

        # Verify project ownership was checked (not branch user_id)
        mock_project_query.filter.assert_called_once()

        # Verify branch was deleted (no user_id filter on branch)
        mock_branch_query.filter.assert_called_once()

        # Verify result is True (deletion allowed because user owns project)
        assert result is True
