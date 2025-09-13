"""
Tests for Search Tasks Use Case
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from fastmcp.task_management.application.use_cases.search_tasks import SearchTasksUseCase
from fastmcp.task_management.application.dtos.task import (
    SearchTasksRequest,
    TaskListResponse
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestSearchTasksUseCase:
    """Test the SearchTasksUseCase class"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def use_case(self, mock_task_repository):
        """Create a use case instance"""
        return SearchTasksUseCase(task_repository=mock_task_repository)
    
    @pytest.fixture
    def sample_tasks(self):
        """Create a list of sample task entities"""
        tasks = []
        
        # Task 1
        task1 = Mock(spec=Task)
        task1.id = TaskId("12345678-1234-5678-1234-567812345678")
        task1.title = "Implement authentication system"
        task1.description = "Build JWT-based authentication with login/logout"
        task1.git_branch_id = "branch-auth"
        task1.status = TaskStatus.TODO
        task1.priority = Priority.high()
        task1.assignees = ["user-1"]
        task1.labels = ["security", "backend"]
        task1.created_at = datetime(2023, 1, 1, 10, 0, 0)
        task1.updated_at = datetime(2023, 1, 1, 12, 0, 0)
        tasks.append(task1)
        
        # Task 2
        task2 = Mock(spec=Task)
        task2.id = TaskId("87654321-4321-8765-4321-876543218765")
        task2.title = "Fix login bug"
        task2.description = "Users cannot login after password reset"
        task2.git_branch_id = "branch-bugfix"
        task2.status = TaskStatus.IN_PROGRESS
        task2.priority = Priority.critical()
        task2.assignees = ["user-2"]
        task2.labels = ["bug", "urgent", "authentication"]
        task2.created_at = datetime(2023, 1, 2, 9, 0, 0)
        task2.updated_at = datetime(2023, 1, 2, 14, 30, 0)
        tasks.append(task2)
        
        # Task 3
        task3 = Mock(spec=Task)
        task3.id = TaskId("11111111-2222-3333-4444-555555555555")
        task3.title = "Update user interface"
        task3.description = "Modernize the login form design"
        task3.git_branch_id = "branch-ui"
        task3.status = TaskStatus.DONE
        task3.priority = Priority.medium()
        task3.assignees = ["user-3", "user-4"]
        task3.labels = ["ui", "frontend"]
        task3.created_at = datetime(2023, 1, 3, 8, 0, 0)
        task3.updated_at = datetime(2023, 1, 3, 16, 0, 0)
        tasks.append(task3)
        
        return tasks
    
    @pytest.fixture
    def empty_task_list(self):
        """Create an empty task list"""
        return []
    
    def test_execute_successful_search_with_results(self, use_case, mock_task_repository, sample_tasks):
        """Test successful search with results returned"""
        # Arrange
        query = "authentication"
        limit = 10
        request = SearchTasksRequest(query=query, limit=limit)
        mock_task_repository.search.return_value = sample_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            
            # Verify repository search was called with correct parameters
            mock_task_repository.search.assert_called_once_with(query, limit=limit)
            
            # Verify response creation
            mock_response.from_domain_list.assert_called_once_with(sample_tasks, query=query)
    
    def test_execute_successful_search_with_no_results(self, use_case, mock_task_repository, empty_task_list):
        """Test successful search with no results returned"""
        # Arrange
        query = "nonexistent"
        limit = 5
        request = SearchTasksRequest(query=query, limit=limit)
        mock_task_repository.search.return_value = empty_task_list
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            
            # Verify repository search was called
            mock_task_repository.search.assert_called_once_with(query, limit=limit)
            
            # Verify response creation with empty list
            mock_response.from_domain_list.assert_called_once_with(empty_task_list, query=query)
    
    def test_execute_search_with_different_limits(self, use_case, mock_task_repository, sample_tasks):
        """Test search with different limit values"""
        # Test cases: different limit values
        test_cases = [1, 5, 10, 50, 100]
        
        for limit in test_cases:
            # Arrange
            query = "test"
            request = SearchTasksRequest(query=query, limit=limit)
            mock_task_repository.search.return_value = sample_tasks[:limit] if limit < len(sample_tasks) else sample_tasks
            
            with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
                mock_task_list_response = Mock()
                mock_response.from_domain_list.return_value = mock_task_list_response
                
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result == mock_task_list_response
                mock_task_repository.search.assert_called_with(query, limit=limit)
                
            # Reset mock for next iteration
            mock_task_repository.reset_mock()
    
    @pytest.mark.parametrize("query,expected_calls", [
        ("authentication", 1),
        ("login", 1),
        ("", 1),  # Empty query should still be processed
        ("special@chars#test", 1),
        ("very long query with multiple words and symbols !@#$%^&*()", 1),
        ("SQL injection'; DROP TABLE tasks; --", 1),  # Security test
    ])
    def test_execute_various_query_formats(self, use_case, mock_task_repository, sample_tasks,
                                          query, expected_calls):
        """Test search with various query formats and edge cases"""
        # Arrange
        request = SearchTasksRequest(query=query, limit=10)
        mock_task_repository.search.return_value = sample_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            assert mock_task_repository.search.call_count == expected_calls
            mock_task_repository.search.assert_called_with(query, limit=10)
    
    def test_execute_with_default_limit(self, use_case, mock_task_repository, sample_tasks):
        """Test search when limit is not specified (should use default)"""
        # Arrange
        query = "test query"
        request = SearchTasksRequest(query=query)  # No limit specified
        mock_task_repository.search.return_value = sample_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            
            # Verify repository was called - limit should be None or default value from request
            mock_task_repository.search.assert_called_once()
            call_args = mock_task_repository.search.call_args
            assert call_args[0][0] == query  # First positional arg is query
            assert 'limit' in call_args[1]   # limit is passed as keyword argument
    
    def test_request_dto_creation(self):
        """Test SearchTasksRequest DTO creation"""
        # Test with all parameters
        request = SearchTasksRequest(query="test query", limit=15)
        assert request.query == "test query"
        assert request.limit == 15
        
        # Test with only query
        request_minimal = SearchTasksRequest(query="minimal")
        assert request_minimal.query == "minimal"
        # limit should have a default value or be None
        assert hasattr(request_minimal, 'limit')
    
    def test_repository_interaction_error_handling(self, use_case, mock_task_repository):
        """Test handling of repository errors"""
        # Arrange
        query = "test"
        request = SearchTasksRequest(query=query, limit=10)
        mock_task_repository.search.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(request)
        
        assert "Database connection error" in str(exc_info.value)
        mock_task_repository.search.assert_called_once_with(query, limit=10)
    
    def test_execute_with_git_branch_filtering(self, use_case, mock_task_repository, sample_tasks):
        """Test search functionality (assuming repository handles branch filtering)"""
        # Arrange
        query = "authentication branch:auth"  # Example of query with branch filter
        request = SearchTasksRequest(query=query, limit=10)
        
        # Return only tasks from auth branch
        auth_tasks = [task for task in sample_tasks if "auth" in task.git_branch_id]
        mock_task_repository.search.return_value = auth_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            mock_task_repository.search.assert_called_once_with(query, limit=10)
            mock_response.from_domain_list.assert_called_once_with(auth_tasks, query=query)
    
    def test_execute_preserves_query_in_response(self, use_case, mock_task_repository, sample_tasks):
        """Test that the original query is preserved in the response"""
        # Arrange
        query = "specific search query"
        request = SearchTasksRequest(query=query, limit=5)
        mock_task_repository.search.return_value = sample_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            
            # Verify the query was passed to the response
            mock_response.from_domain_list.assert_called_once()
            call_args = mock_response.from_domain_list.call_args
            assert call_args[1]['query'] == query  # query passed as keyword argument
    
    def test_execute_with_large_result_set(self, use_case, mock_task_repository):
        """Test search with large number of results"""
        # Arrange
        query = "common"
        request = SearchTasksRequest(query=query, limit=100)
        
        # Create a large list of tasks
        large_task_list = []
        for i in range(50):
            task = Mock(spec=Task)
            task.id = TaskId(f"12345678-1234-5678-1234-{i:012d}")  # Valid UUID format
            task.title = f"Task {i} with common keyword"
            task.description = f"Description {i}"
            task.status = TaskStatus.TODO
            task.priority = Priority.medium()
            large_task_list.append(task)
        
        mock_task_repository.search.return_value = large_task_list
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            mock_task_repository.search.assert_called_once_with(query, limit=100)
            mock_response.from_domain_list.assert_called_once_with(large_task_list, query=query)
    
    @pytest.mark.parametrize("limit_value", [0, -1, -10, 1000000])
    def test_execute_edge_case_limits(self, use_case, mock_task_repository, sample_tasks, limit_value):
        """Test search with edge case limit values"""
        # Arrange
        query = "test"
        request = SearchTasksRequest(query=query, limit=limit_value)
        mock_task_repository.search.return_value = sample_tasks
        
        with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
            mock_task_list_response = Mock()
            mock_response.from_domain_list.return_value = mock_task_list_response
            
            # Act
            result = use_case.execute(request)
            
            # Assert
            assert result == mock_task_list_response
            mock_task_repository.search.assert_called_once_with(query, limit=limit_value)
    
    def test_use_case_initialization(self, mock_task_repository):
        """Test proper initialization of the use case"""
        # Act
        use_case = SearchTasksUseCase(task_repository=mock_task_repository)
        
        # Assert
        assert use_case._task_repository == mock_task_repository
    
    def test_multiple_consecutive_searches(self, use_case, mock_task_repository, sample_tasks):
        """Test multiple consecutive searches maintain proper state"""
        # Arrange
        queries = ["query1", "query2", "query3"]
        
        for i, query in enumerate(queries):
            request = SearchTasksRequest(query=query, limit=5)
            mock_task_repository.search.return_value = sample_tasks[i:i+1] if i < len(sample_tasks) else []
            
            with patch('fastmcp.task_management.application.use_cases.search_tasks.TaskListResponse') as mock_response:
                mock_task_list_response = Mock()
                mock_response.from_domain_list.return_value = mock_task_list_response
                
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result == mock_task_list_response
            
            # Reset repository mock for next iteration
            mock_task_repository.reset_mock()
        
        # Verify total calls
        assert mock_task_repository.search.call_count == 0  # Reset after each iteration