"""
Comprehensive test suite for CreateTaskUseCase.

Tests the create task use case including:
- Successful task creation
- Request validation and transformation
- Error handling and edge cases
- Repository interaction
- Domain entity creation
- Dependency management
- Business logic validation
"""

import pytest
from unittest.mock import Mock, patch
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.create_task_response import CreateTaskResponse
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskCreationError


class TestCreateTaskUseCaseInitialization:
    """Test cases for CreateTaskUseCase initialization."""
    
    def test_init_with_repository(self):
        """Test use case initialization with repository."""
        mock_repository = Mock(spec=TaskRepository)
        
        use_case = CreateTaskUseCase(mock_repository)
        
        assert use_case._task_repository == mock_repository
        assert hasattr(use_case, '_logger')
    
    def test_init_without_repository_fails(self):
        """Test initialization without repository fails."""
        with pytest.raises(TypeError):
            CreateTaskUseCase()


class TestCreateTaskUseCaseExecution:
    """Test cases for task creation execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=TaskRepository)
        self.use_case = CreateTaskUseCase(self.mock_repository)
    
    def test_execute_minimal_request_success(self):
        """Test successful execution with minimal request."""
        # Setup
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
        )
        
        # Mock Task.create
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
            
            result = self.use_case.execute(request)
            
            # Verify task creation
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['id'] == task_id
            assert call_args[1]['title'] == "Test Task"
            assert call_args[1]['description'] == "Test Description"
            assert call_args[1]['git_branch_id'] == "branch-456"
            
            # Verify repository save
            self.mock_repository.save.assert_called_once_with(mock_task)
            
            # Verify response
            assert isinstance(result, CreateTaskResponse)
            assert result.success
    
    def test_execute_full_request_success(self):
        """Test successful execution with full request data."""
        # Setup
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Full Test Task",
            description="Full Test Description",
            git_branch_id="branch-456",
            status="in_progress",
            priority="high",
            details="Implementation details",
            estimated_effort="4 hours",
            assignees=["@user1", "@user2"],
            labels=["feature", "urgent"],
            due_date="2024-12-31",
            dependencies=["dep-1", "dep-2"]
        )
        
        # Mock Task.create and dependencies
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.add_dependency = Mock()
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Full Test Task",
            "description": "Full Test Description",
            "status": "in_progress",
            "priority": "high",
            "git_branch_id": "branch-456",
            "details": "Implementation details",
            "estimatedEffort": "4 hours",
            "assignees": ["@user1", "@user2"],
            "labels": ["feature", "urgent"],
            "dueDate": "2024-12-31",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "dependencies": ["dep-1", "dep-2"],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
            with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId') as mock_task_id:
                mock_dep_id = Mock()
                mock_task_id.return_value = mock_dep_id
                
                result = self.use_case.execute(request)
                
                # Verify task creation with all fields
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                assert call_args['title'] == "Full Test Task"
                assert call_args['description'] == "Full Test Description"
                assert call_args['git_branch_id'] == "branch-456"
                assert call_args['details'] == "Implementation details"
                assert call_args['estimated_effort'] == "4 hours"
                assert call_args['assignees'] == ["@user1", "@user2"]
                assert call_args['labels'] == ["feature", "urgent"]
                assert call_args['due_date'] == "2024-12-31"
                
                # Verify dependencies were added
                assert mock_task.add_dependency.call_count == 2
                
                # Verify success
                assert result.success
    
    def test_execute_with_default_values(self):
        """Test execution applies default status and priority."""
        # Setup
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
            # No status or priority specified
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.application.use_cases.create_task.TaskStatus') as mock_status:
            with patch('fastmcp.task_management.application.use_cases.create_task.Priority') as mock_priority:
                # Mock the value objects
                mock_status_instance = Mock()
                mock_priority_instance = Mock()
                mock_status.return_value = mock_status_instance
                mock_priority.return_value = mock_priority_instance
                
                with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
                    
                    self.use_case.execute(request)
                    
                    # Verify default values were used
                    mock_status.assert_called_once_with(TaskStatusEnum.TODO.value)
                    mock_priority.assert_called_once_with(PriorityLevel.MEDIUM.label)
                    
                    # Verify Task.create was called with the created value objects
                    call_args = mock_create.call_args[1]
                    assert call_args['status'] == mock_status_instance
                    assert call_args['priority'] == mock_priority_instance
    
    def test_execute_truncates_long_content(self):
        """Test execution truncates overly long title and description."""
        # Setup
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="a" * 250,  # Exceeds 200 char limit
            description="b" * 1100,  # Exceeds 1000 char limit
            git_branch_id="branch-456"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "a" * 200,  # Truncated
            "description": "b" * 1000,  # Truncated
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
            
            self.use_case.execute(request)
            
            # Verify content was truncated
            call_args = mock_create.call_args[1]
            assert len(call_args['title']) == 200
            assert len(call_args['description']) == 1000
            assert call_args['title'] == "a" * 200
            assert call_args['description'] == "b" * 1000


class TestCreateTaskUseCaseValidation:
    """Test cases for request validation and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=TaskRepository)
        self.use_case = CreateTaskUseCase(self.mock_repository)
    
    def test_execute_git_branch_validation_success(self):
        """Test git branch validation passes when branch exists."""
        # Setup repository with git branch validation
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.git_branch_exists = Mock(return_value=True)
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="existing-branch"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "existing-branch"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "existing-branch",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            
            result = self.use_case.execute(request)
            
            # Verify branch validation was called
            self.mock_repository.git_branch_exists.assert_called_once_with("existing-branch")
            
            # Verify success
            assert result.success
    
    def test_execute_git_branch_validation_failure(self):
        """Test git branch validation fails when branch doesn't exist."""
        # Setup repository with git branch validation
        self.mock_repository.git_branch_exists = Mock(return_value=False)
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="nonexistent-branch"
        )
        
        result = self.use_case.execute(request)
        
        # Verify validation was called
        self.mock_repository.git_branch_exists.assert_called_once_with("nonexistent-branch")
        
        # Verify error response
        assert not result.success
        assert "does not exist" in result.message
        assert "nonexistent-branch" in result.message
    
    def test_execute_invalid_status_handling(self):
        """Test handling of invalid status values."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            status="invalid_status"
        )
        
        # Mock TaskStatus to raise ValueError for invalid status
        with patch('fastmcp.task_management.application.use_cases.create_task.TaskStatus', 
                   side_effect=ValueError("Invalid status")):
            
            with pytest.raises(ValueError, match="Invalid status"):
                self.use_case.execute(request)
    
    def test_execute_invalid_priority_handling(self):
        """Test handling of invalid priority values."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            priority="invalid_priority"
        )
        
        # Mock Priority to raise ValueError for invalid priority
        with patch('fastmcp.task_management.application.use_cases.create_task.Priority',
                   side_effect=ValueError("Invalid priority")):
            
            with pytest.raises(ValueError, match="Invalid priority"):
                self.use_case.execute(request)


class TestCreateTaskUseCaseDependencies:
    """Test cases for dependency handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=TaskRepository)
        self.use_case = CreateTaskUseCase(self.mock_repository)
    
    def test_execute_with_valid_dependencies(self):
        """Test adding valid dependencies to task."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            dependencies=["dep-1", "dep-2", "dep-3"]
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.add_dependency = Mock()
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": ["dep-1", "dep-2", "dep-3"],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            with patch('fastmcp.task_management.application.use_cases.create_task.TaskId') as mock_task_id:
                # Mock TaskId creation for dependencies
                mock_dep_ids = [Mock(spec=TaskId), Mock(spec=TaskId), Mock(spec=TaskId)]
                mock_task_id.side_effect = mock_dep_ids
                
                result = self.use_case.execute(request)
                
                # Verify all dependencies were added
                assert mock_task.add_dependency.call_count == 3
                for i, mock_dep_id in enumerate(mock_dep_ids):
                    mock_task.add_dependency.assert_any_call(mock_dep_id)
                
                # Verify TaskId was created for each dependency
                assert mock_task_id.call_count == 3
                mock_task_id.assert_any_call("dep-1")
                mock_task_id.assert_any_call("dep-2")
                mock_task_id.assert_any_call("dep-3")
                
                assert result.success
    
    def test_execute_with_invalid_dependencies(self):
        """Test handling of invalid dependency IDs."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            dependencies=["valid-dep", "", "  ", "invalid-dep"]
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.add_dependency = Mock()
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": ["dep-1", "dep-2", "dep-3"],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            with patch('fastmcp.task_management.application.use_cases.create_task.TaskId') as mock_task_id:
                # Mock TaskId to raise ValueError for invalid dependency
                def side_effect(dep_id):
                    if dep_id == "invalid-dep":
                        raise ValueError("Invalid task ID")
                    return Mock(spec=TaskId)
                
                mock_task_id.side_effect = side_effect
                
                with patch('logging.warning') as mock_warning:
                    
                    result = self.use_case.execute(request)
                    
                    # Verify valid dependency was added (only "valid-dep")
                    mock_task.add_dependency.assert_called_once()
                    
                    # Verify warning was logged for invalid dependency
                    mock_warning.assert_called()
                    
                    # Task creation should still succeed
                    assert result.success
    
    def test_execute_with_empty_dependencies(self):
        """Test handling of empty or whitespace-only dependencies."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            dependencies=["", "  ", "\t", None]
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.add_dependency = Mock()
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": ["dep-1", "dep-2", "dep-3"],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            
            result = self.use_case.execute(request)
            
            # No dependencies should be added
            mock_task.add_dependency.assert_not_called()
            
            assert result.success


class TestCreateTaskUseCaseRepositoryInteraction:
    """Test cases for repository interaction and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=TaskRepository)
        self.use_case = CreateTaskUseCase(self.mock_repository)
    
    def test_execute_repository_save_failure(self):
        """Test handling of repository save failure."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = False  # Save fails
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            
            result = self.use_case.execute(request)
            
            # Verify save was attempted
            self.mock_repository.save.assert_called_once_with(mock_task)
            
            # Verify error response
            assert not result.success
            assert "Failed to save task" in result.message
    
    def test_execute_repository_exception(self):
        """Test handling of repository exceptions."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.side_effect = TaskCreationError("Database error")
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456"
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task",
            "description": "Test Description",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            
            # Execute should return error response instead of raising exception
            result = self.use_case.execute(request)
            
            # Verify error response
            assert not result.success
            assert "Database error" in result.message
    
    def test_execute_id_generation_failure(self):
        """Test handling of ID generation failure."""
        self.mock_repository.get_next_id.side_effect = Exception("ID generation failed")
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
        )
        
        # Execute should return error response instead of raising exception
        result = self.use_case.execute(request)
        
        # Verify error response
        assert not result.success
        assert "ID generation failed" in result.message
    
    def test_execute_task_creation_failure(self):
        """Test handling of task entity creation failure."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456"
        )
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create',
                   side_effect=ValueError("Invalid task data")):
            
            with pytest.raises(ValueError, match="Invalid task data"):
                self.use_case.execute(request)


class TestCreateTaskUseCaseEdgeCases:
    """Test cases for edge cases and special scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock(spec=TaskRepository)
        self.use_case = CreateTaskUseCase(self.mock_repository)
    
    def test_execute_with_unicode_content(self):
        """Test creation with unicode characters."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task with 🚀 emoji",
            description="Description with unicode: αβγ 中文 русский",
            git_branch_id="branch-456"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456" 
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task with 🚀 emoji",
            "description": "Description with unicode: αβγ 中文 русский",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
            
            result = self.use_case.execute(request)
            
            # Verify unicode content is preserved
            call_args = mock_create.call_args[1]
            assert "🚀" in call_args['title']
            assert "αβγ" in call_args['description']
            assert "中文" in call_args['description']
            assert "русский" in call_args['description']
            
            assert result.success
    
    def test_execute_with_none_optional_fields(self):
        """Test creation with None values for optional fields."""
        task_id = TaskId("task-123")
        self.mock_repository.get_next_id.return_value = task_id
        self.mock_repository.save.return_value = True
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-456",
            details=None,
            estimated_effort=None,
            assignees=None,
            labels=None,
            due_date=None
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = task_id
        mock_task.git_branch_id = "branch-456" 
        mock_task.get_events = Mock(return_value=[])  # Add get_events method
        mock_task.to_dict = Mock(return_value={
            "id": str(task_id),
            "title": "Test Task with 🚀 emoji",
            "description": "Description with unicode: αβγ 中文 русский",
            "status": "todo",
            "priority": "medium",
            "git_branch_id": "branch-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assignees": [],
            "labels": [],
            "details": None,
            "estimatedEffort": None,
            "dueDate": None,
            "dependencies": [],
            "subtasks": []
        })
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create:
            
            result = self.use_case.execute(request)
            
            # Verify None values are passed through (or converted to defaults)
            call_args = mock_create.call_args[1]
            assert call_args['details'] is None
            assert call_args['estimated_effort'] is None
            # assignees and labels may be None or [] depending on CreateTaskRequest behavior
            assert call_args['assignees'] in [None, []]
            assert call_args['labels'] in [None, []]
            assert call_args['due_date'] is None
            
            assert result.success


if __name__ == "__main__":
    pytest.main([__file__])