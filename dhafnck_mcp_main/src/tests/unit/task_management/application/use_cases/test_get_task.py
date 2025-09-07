"""
Tests for Get Task Use Case
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import logging
from datetime import datetime

from fastmcp.task_management.application.use_cases.get_task import GetTaskUseCase
from fastmcp.task_management.application.dtos.task import TaskResponse
from fastmcp.task_management.application.dtos.context import GetContextRequest
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.domain.events import TaskRetrieved


class TestGetTaskUseCase:
    """Test the GetTaskUseCase class"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service (sync version - UnifiedContextFacade)"""
        mock_service = Mock()
        mock_service.get_context = Mock()  # Sync method
        return mock_service
    
    @pytest.fixture
    def mock_async_context_service(self):
        """Create a mock async context service (old-style)"""
        mock_service = Mock()
        mock_service.get_context = AsyncMock()  # Async method
        return mock_service
    
    @pytest.fixture
    def use_case_with_sync_context(self, mock_task_repository, mock_context_service):
        """Create a use case instance with sync context service"""
        return GetTaskUseCase(
            task_repository=mock_task_repository,
            context_service=mock_context_service
        )
    
    @pytest.fixture
    def use_case_with_async_context(self, mock_task_repository, mock_async_context_service):
        """Create a use case instance with async context service"""
        return GetTaskUseCase(
            task_repository=mock_task_repository,
            context_service=mock_async_context_service
        )
    
    @pytest.fixture
    def use_case_without_context(self, mock_task_repository):
        """Create a use case instance without context service"""
        return GetTaskUseCase(
            task_repository=mock_task_repository,
            context_service=None
        )
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task entity"""
        task = Mock(spec=Task)
        task.id = TaskId("12345678-1234-5678-1234-567812345678")
        task.title = "Test Task"
        task.description = "Test description"
        task.git_branch_id = "branch-456"
        task.status = TaskStatus.TODO
        task.priority = Priority.high()
        task.assignees = ["user-1", "user-2"]
        task.labels = ["bug", "urgent"]
        task.context_id = "context-123"
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        task.to_dict.return_value = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": str(task.status),
            "priority": str(task.priority)
        }
        return task
    
    @pytest.fixture
    def sample_context_data(self):
        """Create sample context data"""
        return {
            "task_context": {
                "current_work": "Working on authentication",
                "blockers": ["Missing API credentials"],
                "progress_notes": "50% complete"
            },
            "project_context": {
                "technology_stack": ["Python", "React"],
                "team_preferences": {"review_required": True}
            }
        }
    
    @pytest.mark.asyncio
    async def test_execute_successful_without_context(self, use_case_without_context, 
                                                     mock_task_repository, sample_task):
        """Test successful task retrieval without context"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_without_context.execute(task_id)
            
            # Assert
            assert result == mock_task_response
            
            # Verify repository interaction
            mock_task_repository.find_by_id.assert_called_once()
            called_task_id = mock_task_repository.find_by_id.call_args[0][0]
            assert isinstance(called_task_id, TaskId)
            assert str(called_task_id) == task_id
            
            # Verify response creation
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=None)
    
    @pytest.mark.asyncio
    async def test_execute_successful_with_sync_context(self, use_case_with_sync_context, 
                                                       mock_task_repository, sample_task, 
                                                       mock_context_service, sample_context_data):
        """Test successful task retrieval with sync context service"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_context_service.get_context.return_value = {
            "success": True,
            "context": sample_context_data
        }
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_with_sync_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            
            # Verify context service interaction
            mock_context_service.get_context.assert_called_once_with(
                level="task",
                context_id=task_id,
                include_inherited=True
            )
            
            # Verify response creation with context data
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=sample_context_data)
    
    @pytest.mark.asyncio
    async def test_execute_successful_with_async_context(self, use_case_with_async_context, 
                                                        mock_task_repository, sample_task, 
                                                        mock_async_context_service, sample_context_data):
        """Test successful task retrieval with async context service"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        # Mock async context response
        mock_context_response = Mock()
        mock_context_response.success = True
        mock_context_response.context = sample_context_data
        mock_async_context_service.get_context.return_value = mock_context_response
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_with_async_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            
            # Verify async context service interaction
            mock_async_context_service.get_context.assert_called_once()
            call_args = mock_async_context_service.get_context.call_args[0][0]
            assert isinstance(call_args, GetContextRequest)
            assert call_args.task_id == task_id
            
            # Verify response creation with context data
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=sample_context_data)
    
    @pytest.mark.asyncio
    async def test_execute_task_not_found_raises_exception(self, use_case_without_context, mock_task_repository):
        """Test TaskNotFoundError is raised when task is not found"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345999"  # Valid UUID format
        mock_task_repository.find_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError) as exc_info:
            await use_case_without_context.execute(task_id)
        
        assert f"Task with ID {task_id} not found" in str(exc_info.value)
        mock_task_repository.find_by_id.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_generate_rules_flag(self, use_case_without_context, 
                                                   mock_task_repository, sample_task):
        """Test execution with generate_rules flag"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        with patch('fastmcp.task_management.application.use_cases.get_task.generate_docs_for_assignees') as mock_generate:
            with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
                mock_task_response = Mock()
                mock_response.from_domain.return_value = mock_task_response
                
                # Act
                result = await use_case_without_context.execute(
                    task_id, 
                    generate_rules=True, 
                    force_full_generation=True
                )
                
                # Assert
                assert result == mock_task_response
                mock_generate.assert_called_once_with(sample_task.assignees, clear_all=True)
    
    @pytest.mark.asyncio
    async def test_execute_without_generate_rules_flag(self, use_case_without_context, 
                                                      mock_task_repository, sample_task):
        """Test execution without generate_rules flag"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        with patch('fastmcp.task_management.application.use_cases.get_task.generate_docs_for_assignees') as mock_generate:
            with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
                mock_task_response = Mock()
                mock_response.from_domain.return_value = mock_task_response
                
                # Act
                result = await use_case_without_context.execute(task_id, generate_rules=False)
                
                # Assert
                assert result == mock_task_response
                mock_generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_context_service_exception(self, use_case_with_sync_context, 
                                                    mock_task_repository, sample_task, 
                                                    mock_context_service, caplog):
        """Test handling of context service exceptions"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_context_service.get_context.side_effect = Exception("Context service error")
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            with caplog.at_level(logging.WARNING):
                result = await use_case_with_sync_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            assert "Failed to fetch context data" in caplog.text
            
            # Verify response creation without context data
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=None)
    
    @pytest.mark.asyncio
    async def test_execute_sync_context_with_data_field(self, use_case_with_sync_context, 
                                                       mock_task_repository, sample_task, 
                                                       mock_context_service, sample_context_data):
        """Test sync context service with data field instead of context field"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_context_service.get_context.return_value = {
            "success": True,
            "data": {"context_data": sample_context_data}
        }
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_with_sync_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=sample_context_data)
    
    @pytest.mark.asyncio
    async def test_execute_sync_context_no_success(self, use_case_with_sync_context, 
                                                  mock_task_repository, sample_task, 
                                                  mock_context_service, caplog):
        """Test sync context service when success is False"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_context_service.get_context.return_value = {
            "success": False,
            "error": "Context not found"
        }
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            with caplog.at_level(logging.WARNING):
                result = await use_case_with_sync_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            assert "No context data found" in caplog.text
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=None)
    
    @pytest.mark.asyncio
    async def test_execute_async_context_with_data_field(self, use_case_with_async_context, 
                                                        mock_task_repository, sample_task, 
                                                        mock_async_context_service, sample_context_data):
        """Test async context service with data field fallback"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        mock_context_response = Mock()
        mock_context_response.success = True
        mock_context_response.context = None  # No context field
        mock_context_response.data = sample_context_data  # Has data field
        mock_async_context_service.get_context.return_value = mock_context_response
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_with_async_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=sample_context_data)
    
    @pytest.mark.asyncio
    async def test_execute_async_context_with_to_dict_method(self, use_case_with_async_context, 
                                                            mock_task_repository, sample_task, 
                                                            mock_async_context_service, sample_context_data):
        """Test async context service with to_dict method on context"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        mock_context_obj = Mock()
        mock_context_obj.to_dict.return_value = sample_context_data
        
        mock_context_response = Mock()
        mock_context_response.success = True
        mock_context_response.context = mock_context_obj
        mock_async_context_service.get_context.return_value = mock_context_response
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            result = await use_case_with_async_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            mock_context_obj.to_dict.assert_called_once()
            mock_response.from_domain.assert_called_once_with(sample_task, context_data=sample_context_data)
    
    @pytest.mark.asyncio
    async def test_execute_domain_event_creation(self, use_case_without_context, 
                                                mock_task_repository, sample_task):
        """Test domain event creation during task retrieval"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            with patch('fastmcp.task_management.application.use_cases.get_task.TaskRetrieved') as mock_event:
                mock_task_response = Mock()
                mock_response.from_domain.return_value = mock_task_response
                
                # Act
                result = await use_case_without_context.execute(task_id)
                
                # Assert
                assert result == mock_task_response
                
                # Verify domain event was created
                mock_event.assert_called_once()
                event_call_args = mock_event.call_args[1]
                assert event_call_args['task_id'] == sample_task.id
                assert 'task_data' in event_call_args
                assert 'retrieved_at' in event_call_args
    
    @pytest.mark.asyncio
    async def test_execute_unexpected_exception_handling(self, use_case_without_context, 
                                                        mock_task_repository, caplog):
        """Test handling of unexpected exceptions"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception) as exc_info:
                await use_case_without_context.execute(task_id)
            
            assert "Database connection error" in str(exc_info.value)
            assert "Unexpected error retrieving task" in caplog.text
    
    @pytest.mark.asyncio
    async def test_execute_no_context_service_warning(self, use_case_without_context, 
                                                     mock_task_repository, sample_task, caplog):
        """Test warning when context service is not available"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        
        with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
            mock_task_response = Mock()
            mock_response.from_domain.return_value = mock_task_response
            
            # Act
            with caplog.at_level(logging.WARNING):
                result = await use_case_without_context.execute(task_id, include_context=True)
            
            # Assert
            assert result == mock_task_response
            assert "No context service available" in caplog.text
    
    @pytest.mark.parametrize("task_id_input", [
        "12345678-1234-5678-1234-567812345678",  # Valid UUID
        "simple-task-id",  # Invalid
        "",  # Empty
        "task-with-special-chars-@#$%",  # Invalid chars
    ])
    @pytest.mark.asyncio
    async def test_execute_various_task_id_formats(self, use_case_without_context, 
                                                  mock_task_repository, sample_task, task_id_input):
        """Test execution with various task ID formats"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        
        # Only valid UUID format should succeed
        if task_id_input == "12345678-1234-5678-1234-567812345678":
            with patch('fastmcp.task_management.application.use_cases.get_task.TaskResponse') as mock_response:
                mock_task_response = Mock()
                mock_response.from_domain.return_value = mock_task_response
                
                # Act
                result = await use_case_without_context.execute(task_id_input)
                
                # Assert
                assert result == mock_task_response
                
                # Verify TaskId conversion
                mock_task_repository.find_by_id.assert_called_once()
                called_task_id = mock_task_repository.find_by_id.call_args[0][0]
                assert isinstance(called_task_id, TaskId)
        else:
            # Invalid formats should raise ValueError
            with pytest.raises((ValueError, TaskNotFoundError)):
                await use_case_without_context.execute(task_id_input)