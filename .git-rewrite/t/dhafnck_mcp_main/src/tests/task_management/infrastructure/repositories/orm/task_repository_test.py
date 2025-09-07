"""
Comprehensive tests for ORMTaskRepository

This module tests the ORMTaskRepository functionality including:
- CRUD operations (Create, Read, Update, Delete)
- Search functionality with multi-word support
- User isolation and data security
- Relationship handling (assignees, labels, dependencies)
- Error handling and graceful fallbacks
- Performance optimizations
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.database.models import (
    Base, Project, ProjectGitBranch, Task, TaskAssignee, TaskLabel, TaskDependency, Label
)
from fastmcp.task_management.domain.entities.task import Task as TaskEntity
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.exceptions.task_exceptions import (
    TaskCreationError, TaskNotFoundError, TaskUpdateError
)


class TestORMTaskRepository:
    """Test suite for ORMTaskRepository"""
    
    @pytest.fixture(scope="function")
    def engine(self):
        """Create in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="function")
    def session(self, engine):
        """Create database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def test_data(self, session):
        """Create test data in database"""
        # Create project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Test Project",
            user_id="user-123"
        )
        session.add(project)
        
        # Create git branch
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        session.commit()
        
        return {
            "project_id": project_id,
            "branch_id": branch_id,
            "user_id": "user-123"
        }
    
    @pytest.fixture
    def repository(self, session, test_data):
        """Create repository instance with test data"""
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session', return_value=session):
            return ORMTaskRepository(
                session=session,
                git_branch_id=test_data["branch_id"],
                user_id=test_data["user_id"]
            )
    
    def test_repository_initialization(self, session, test_data):
        """Test repository initialization with parameters"""
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session', return_value=session):
            repo = ORMTaskRepository(
                session=session,
                git_branch_id=test_data["branch_id"],
                project_id=test_data["project_id"],
                git_branch_name="test-branch",
                user_id=test_data["user_id"]
            )
            
            assert repo.git_branch_id == test_data["branch_id"]
            assert repo.project_id == test_data["project_id"]
            assert repo.git_branch_name == "test-branch"
            assert repo.user_id == test_data["user_id"]
    
    def test_create_task_basic(self, repository, test_data):
        """Test basic task creation"""
        task = repository.create_task(
            title="Test Task",
            description="Test description",
            priority="high",
            status="todo"
        )
        
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "Test description"
        assert str(task.priority) == "high"
        assert str(task.status) == "todo"
        assert task.git_branch_id == test_data["branch_id"]
    
    def test_create_task_with_assignees_and_labels(self, repository, session):
        """Test task creation with assignees and labels"""
        task = repository.create_task(
            title="Task with Relations",
            description="Test task with assignees and labels",
            assignee_ids=["user-456", "user-789"],
            label_names=["bug", "urgent"]
        )
        
        assert task is not None
        assert len(task.assignees) == 2
        assert "user-456" in task.assignees
        assert "user-789" in task.assignees
        assert len(task.labels) == 2
        assert "bug" in task.labels
        assert "urgent" in task.labels
        
        # Verify in database
        db_task = session.query(Task).filter_by(id=str(task.id)).first()
        assert len(db_task.assignees) == 2
        assert len(db_task.labels) == 2
    
    def test_get_task_success(self, repository, session, test_data):
        """Test successful task retrieval"""
        # Create task in database
        task_id = str(uuid.uuid4())
        db_task = Task(
            id=task_id,
            title="Retrieve Test Task",
            description="Task for retrieval testing",
            git_branch_id=test_data["branch_id"],
            status="in_progress",
            priority="medium",
            user_id=test_data["user_id"]
        )
        session.add(db_task)
        session.commit()
        
        # Retrieve task
        task = repository.get_task(task_id)
        
        assert task is not None
        assert task.title == "Retrieve Test Task"
        assert str(task.status) == "in_progress"
        assert str(task.priority) == "medium"
    
    def test_get_task_not_found(self, repository):
        """Test task retrieval when task doesn't exist"""
        non_existent_id = str(uuid.uuid4())
        task = repository.get_task(non_existent_id)
        assert task is None
    
    def test_get_task_user_isolation(self, session, test_data):
        """Test that users can only retrieve their own tasks"""
        # Create task for different user
        task_id = str(uuid.uuid4())
        other_user_task = Task(
            id=task_id,
            title="Other User Task",
            description="Task belonging to another user",
            git_branch_id=test_data["branch_id"],
            user_id="other-user-456"
        )
        session.add(other_user_task)
        session.commit()
        
        # Try to retrieve with original user's repository
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session', return_value=session):
            repository = ORMTaskRepository(
                session=session,
                git_branch_id=test_data["branch_id"],
                user_id=test_data["user_id"]  # Different user
            )
            
            task = repository.get_task(task_id)
            assert task is None  # Should not retrieve other user's task
    
    def test_update_task_basic_fields(self, repository, session, test_data):
        """Test updating basic task fields"""
        # Create initial task
        task = repository.create_task(
            title="Original Title",
            description="Original description",
            priority="low"
        )
        task_id = str(task.id)
        
        # Update task
        updated_task = repository.update_task(
            task_id,
            title="Updated Title",
            description="Updated description",
            priority="high",
            status="completed"
        )
        
        assert updated_task is not None
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "Updated description"
        assert str(updated_task.priority) == "high"
        assert str(updated_task.status) == "completed"
    
    def test_update_task_assignees_and_labels(self, repository, session):
        """Test updating task assignees and labels"""
        # Create initial task
        task = repository.create_task(
            title="Update Relations Task",
            description="Task for testing relation updates",
            assignee_ids=["user-1"],
            label_names=["initial"]
        )
        task_id = str(task.id)
        
        # Update with new assignees and labels
        updated_task = repository.update_task(
            task_id,
            assignee_ids=["user-2", "user-3"],
            label_names=["updated", "testing"]
        )
        
        assert len(updated_task.assignees) == 2
        assert "user-2" in updated_task.assignees
        assert "user-3" in updated_task.assignees
        assert len(updated_task.labels) == 2
        assert "updated" in updated_task.labels
        assert "testing" in updated_task.labels
    
    def test_update_task_not_found(self, repository):
        """Test updating non-existent task"""
        non_existent_id = str(uuid.uuid4())
        
        with pytest.raises(TaskNotFoundError):
            repository.update_task(non_existent_id, title="New Title")
    
    def test_delete_task_success(self, repository, session):
        """Test successful task deletion"""
        # Create task
        task = repository.create_task(
            title="Delete Test Task",
            description="Task to be deleted"
        )
        task_id = str(task.id)
        
        # Verify task exists
        assert repository.get_task(task_id) is not None
        
        # Delete task
        success = repository.delete_task(task_id)
        
        assert success is True
        assert repository.get_task(task_id) is None
    
    def test_list_tasks_basic(self, repository, session):
        """Test basic task listing"""
        # Create multiple tasks
        tasks_data = [
            ("Task 1", "todo", "high"),
            ("Task 2", "in_progress", "medium"),
            ("Task 3", "completed", "low")
        ]
        
        for title, status, priority in tasks_data:
            repository.create_task(title=title, description=f"Description for {title}", 
                                status=status, priority=priority)
        
        # List all tasks
        tasks = repository.list_tasks()
        
        assert len(tasks) == 3
        assert all(isinstance(task, TaskEntity) for task in tasks)
    
    def test_list_tasks_with_filters(self, repository):
        """Test task listing with status and priority filters"""
        # Create tasks with different statuses
        repository.create_task(title="Todo Task", description="Todo task", status="todo")
        repository.create_task(title="Progress Task", description="In progress task", status="in_progress")
        repository.create_task(title="High Priority Task", description="High priority", priority="high")
        
        # Filter by status
        todo_tasks = repository.list_tasks(status="todo")
        assert len(todo_tasks) == 1
        assert str(todo_tasks[0].status) == "todo"
        
        # Filter by priority
        high_priority_tasks = repository.list_tasks(priority="high")
        assert len(high_priority_tasks) == 1
        assert str(high_priority_tasks[0].priority) == "high"
    
    def test_list_tasks_with_assignee_filter(self, repository):
        """Test task listing filtered by assignee"""
        # Create tasks with different assignees
        repository.create_task(
            title="User A Task", 
            description="Task for user A", 
            assignee_ids=["user-a"]
        )
        repository.create_task(
            title="User B Task", 
            description="Task for user B", 
            assignee_ids=["user-b"]
        )
        repository.create_task(
            title="Shared Task", 
            description="Task for both users", 
            assignee_ids=["user-a", "user-b"]
        )
        
        # Filter by assignee
        user_a_tasks = repository.list_tasks(assignee_id="user-a")
        assert len(user_a_tasks) == 2  # User A Task and Shared Task
    
    def test_search_tasks_single_word(self, repository):
        """Test searching tasks with single word"""
        # Create tasks with searchable content
        repository.create_task(title="Authentication Bug", description="Login authentication issue")
        repository.create_task(title="Database Connection", description="Database connectivity problem")
        repository.create_task(title="User Authentication", description="User login system")
        
        # Search for authentication-related tasks
        results = repository.search_tasks("authentication")
        
        assert len(results) == 2
        task_titles = [task.title for task in results]
        assert "Authentication Bug" in task_titles
        assert "User Authentication" in task_titles
    
    def test_search_tasks_multi_word(self, repository):
        """Test searching tasks with multiple words"""
        # Create tasks
        repository.create_task(title="JWT Token Authentication", description="Implement JWT tokens")
        repository.create_task(title="Database Authentication", description="Database auth system")
        repository.create_task(title="Email Service", description="Send email notifications")
        repository.create_task(title="JWT Email Notifications", description="Email with JWT")
        
        # Search with multiple words - should find tasks containing ANY of the words
        results = repository.search_tasks("JWT email")
        
        assert len(results) == 3  # JWT Token, Email Service, JWT Email (contains both)
    
    def test_search_tasks_by_labels(self, repository, session):
        """Test searching tasks by label names"""
        # Create labels and tasks
        repository.create_task(
            title="Bug Fix Task", 
            description="Fix critical bug", 
            label_names=["bug", "critical"]
        )
        repository.create_task(
            title="Feature Task", 
            description="New feature implementation", 
            label_names=["feature", "enhancement"]
        )
        
        # Search by label
        bug_tasks = repository.search_tasks("bug")
        
        assert len(bug_tasks) == 1
        assert bug_tasks[0].title == "Bug Fix Task"
    
    def test_get_task_count(self, repository):
        """Test getting task count with and without filters"""
        # Create tasks with different statuses
        repository.create_task(title="Todo 1", description="First todo", status="todo")
        repository.create_task(title="Todo 2", description="Second todo", status="todo")
        repository.create_task(title="Progress 1", description="In progress", status="in_progress")
        
        # Get total count
        total_count = repository.get_task_count()
        assert total_count == 3
        
        # Get count by status
        todo_count = repository.get_task_count(status="todo")
        assert todo_count == 2
        
        progress_count = repository.get_task_count(status="in_progress")
        assert progress_count == 1
    
    def test_save_new_task_entity(self, repository, test_data):
        """Test saving a new task entity using domain objects"""
        # Create task entity
        task_entity = TaskEntity(
            id=TaskId(str(uuid.uuid4())),
            title="Domain Task",
            description="Task created from domain entity",
            git_branch_id=test_data["branch_id"],
            status=TaskStatus(TaskStatusEnum.TODO.value),
            priority=Priority(PriorityLevel.HIGH.label),
            assignees=["user-1"],
            labels=["domain", "test"]
        )
        
        # Save task
        saved_task = repository.save(task_entity)
        
        assert saved_task is not None
        assert saved_task.title == "Domain Task"
        assert str(saved_task.id) == str(task_entity.id)
    
    def test_save_existing_task_entity(self, repository, session, test_data):
        """Test updating an existing task entity"""
        # Create initial task in database
        task_id = str(uuid.uuid4())
        db_task = Task(
            id=task_id,
            title="Original Task",
            description="Original description",
            git_branch_id=test_data["branch_id"],
            status="todo",
            priority="medium",
            user_id=test_data["user_id"]
        )
        session.add(db_task)
        session.commit()
        
        # Create updated task entity
        updated_entity = TaskEntity(
            id=TaskId(task_id),
            title="Updated Task",
            description="Updated description",
            git_branch_id=test_data["branch_id"],
            status=TaskStatus(TaskStatusEnum.COMPLETED.value),
            priority=Priority(PriorityLevel.LOW.label),
            assignees=["user-2"],
            labels=["updated"]
        )
        
        # Save updated task
        saved_task = repository.save(updated_entity)
        
        assert saved_task is not None
        assert saved_task.title == "Updated Task"
        assert str(saved_task.status) == "completed"
    
    def test_find_by_criteria_comprehensive(self, repository):
        """Test finding tasks by multiple criteria"""
        # Create diverse tasks
        repository.create_task(
            title="High Priority Bug",
            description="Critical bug fix",
            status="todo",
            priority="high",
            assignee_ids=["developer-1"],
            label_names=["bug", "critical"]
        )
        repository.create_task(
            title="Medium Feature",
            description="New feature",
            status="in_progress",
            priority="medium",
            assignee_ids=["developer-2"],
            label_names=["feature"]
        )
        repository.create_task(
            title="Low Priority Task",
            description="Low priority work",
            status="todo",
            priority="low",
            assignee_ids=["developer-1"],
            label_names=["maintenance"]
        )
        
        # Search by multiple criteria
        criteria = {
            "status": "todo",
            "assignees": ["developer-1"],
            "labels": ["bug"]
        }
        results = repository.find_by_criteria(criteria)
        
        assert len(results) == 1
        assert results[0].title == "High Priority Bug"
    
    def test_batch_update_status(self, repository, session):
        """Test batch status update for multiple tasks"""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = repository.create_task(
                title=f"Batch Task {i+1}",
                description=f"Task {i+1} for batch update",
                status="todo"
            )
            tasks.append(str(task.id))
        
        # Batch update status
        updated_count = repository.batch_update_status(tasks, "completed")
        
        assert updated_count == 3
        
        # Verify updates
        for task_id in tasks:
            task = repository.get_task(task_id)
            assert str(task.status) == "completed"
    
    def test_get_overdue_tasks(self, repository, session, test_data):
        """Test retrieval of overdue tasks"""
        # Create tasks with different due dates
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        
        # Create overdue task directly in database
        overdue_task_id = str(uuid.uuid4())
        overdue_task = Task(
            id=overdue_task_id,
            title="Overdue Task",
            description="This task is overdue",
            git_branch_id=test_data["branch_id"],
            status="todo",
            due_date=yesterday,
            user_id=test_data["user_id"]
        )
        session.add(overdue_task)
        
        # Create future task
        future_task_id = str(uuid.uuid4())
        future_task = Task(
            id=future_task_id,
            title="Future Task",
            description="This task is not due yet",
            git_branch_id=test_data["branch_id"],
            status="todo",
            due_date=tomorrow,
            user_id=test_data["user_id"]
        )
        session.add(future_task)
        session.commit()
        
        # Get overdue tasks
        overdue_tasks = repository.get_overdue_tasks()
        
        assert len(overdue_tasks) == 1
        assert overdue_tasks[0].title == "Overdue Task"
    
    def test_load_task_with_relationships_graceful_fallback(self, repository, session, test_data):
        """Test graceful fallback when relationship loading fails"""
        # Create task in database
        task_id = str(uuid.uuid4())
        db_task = Task(
            id=task_id,
            title="Test Task",
            description="Task for relationship testing",
            git_branch_id=test_data["branch_id"],
            user_id=test_data["user_id"]
        )
        session.add(db_task)
        session.commit()
        
        # Mock relationship loading to fail
        with patch.object(session, 'query') as mock_query:
            # First call (with relationships) fails
            mock_query.return_value.options.side_effect = Exception("Relationship loading failed")
            # Second call (basic loading) succeeds
            mock_query.return_value.filter.return_value.first.return_value = db_task
            
            task = repository._load_task_with_relationships(session, task_id)
            
            assert task is not None
            assert task.title == "Test Task"
            # Fallback should initialize empty relationships
            assert hasattr(task, 'assignees')
            assert hasattr(task, 'labels')
    
    def test_model_to_entity_conversion_error_handling(self, repository, session, test_data):
        """Test error handling during model to entity conversion"""
        # Create task with potentially problematic relationships
        task_id = str(uuid.uuid4())
        db_task = Task(
            id=task_id,
            title="Conversion Test Task",
            description="Task for testing conversion error handling",
            git_branch_id=test_data["branch_id"],
            status="todo",
            priority="medium",
            user_id=test_data["user_id"]
        )
        session.add(db_task)
        session.commit()
        
        # Mock assignees relationship to raise exception
        mock_assignees = Mock()
        mock_assignees.__iter__ = Mock(side_effect=Exception("Assignee loading error"))
        db_task.assignees = mock_assignees
        
        # Conversion should handle the error gracefully
        entity = repository._model_to_entity(db_task)
        
        assert entity is not None
        assert entity.title == "Conversion Test Task"
        assert entity.assignees == []  # Should be empty due to error
    
    def test_git_branch_exists_validation(self, repository, session, test_data):
        """Test git_branch_exists validation method"""
        # Test with existing branch
        exists = repository.git_branch_exists(test_data["branch_id"])
        assert exists is True
        
        # Test with non-existent branch
        non_existent_id = str(uuid.uuid4())
        exists = repository.git_branch_exists(non_existent_id)
        assert exists is False
    
    def test_get_statistics(self, repository):
        """Test getting repository statistics"""
        # Create tasks with different statuses
        repository.create_task(title="Todo 1", description="Todo task 1", status="todo")
        repository.create_task(title="Todo 2", description="Todo task 2", status="todo")
        repository.create_task(title="Progress 1", description="In progress task", status="in_progress")
        repository.create_task(title="Done 1", description="Completed task", status="completed")
        
        stats = repository.get_statistics()
        
        assert stats["total_tasks"] == 4
        assert stats["todo_tasks"] == 2
        assert stats["in_progress_tasks"] == 1
        assert stats["completed_tasks"] == 1
    
    def test_list_tasks_optimized_performance(self, repository):
        """Test optimized task listing performance improvement"""
        # Create multiple tasks for performance testing
        for i in range(10):
            repository.create_task(
                title=f"Performance Task {i+1}",
                description=f"Task {i+1} for performance testing",
                assignee_ids=[f"user-{i}"],
                label_names=[f"label-{i}"]
            )
        
        # Use optimized listing
        tasks = repository.list_tasks_optimized(limit=5)
        
        assert len(tasks) == 5
        assert all(isinstance(task, TaskEntity) for task in tasks)
    
    def test_error_handling_task_creation_failure(self, repository):
        """Test error handling when task creation fails"""
        with patch('fastmcp.task_management.domain.entities.task.Task.create', 
                   side_effect=Exception("Task creation failed")):
            with pytest.raises(TaskCreationError):
                repository.create_task(
                    title="Failing Task",
                    description="This task creation should fail"
                )
    
    def test_user_authentication_required_for_save(self, session, test_data):
        """Test that user authentication is required for save operations"""
        # Create repository without user_id
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session', return_value=session):
            repo = ORMTaskRepository(
                session=session,
                git_branch_id=test_data["branch_id"],
                user_id=None  # No user authentication
            )
        
        task_entity = TaskEntity(
            id=TaskId(str(uuid.uuid4())),
            title="No Auth Task",
            description="Task without authentication",
            git_branch_id=test_data["branch_id"],
            status=TaskStatus(TaskStatusEnum.TODO.value),
            priority=Priority(PriorityLevel.MEDIUM.label)
        )
        
        # Save should fail due to missing authentication
        with pytest.raises(Exception):  # Should raise UserAuthenticationRequiredError
            repo.save(task_entity)