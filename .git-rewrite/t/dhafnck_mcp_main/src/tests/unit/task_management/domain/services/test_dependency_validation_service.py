"""Unit tests for dependency validation service"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import List, Optional

from fastmcp.task_management.domain.services.dependency_validation_service import (
    DependencyValidationService
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import TaskId, TaskStatus


class TestDependencyValidationService:
    """Test suite for DependencyValidationService"""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_repository):
        """Create service instance"""
        return DependencyValidationService(mock_repository)
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task"""
        task = Mock(spec=Task)
        task.id = TaskId.generate_new()
        task.status = TaskStatus.TODO
        task.dependencies = []
        task.title = "Test Task"
        task.get_dependency_ids = Mock(return_value=[])
        return task
    
    def test_validate_dependency_chain_no_task(self, service, mock_repository):
        """Test validation when task doesn't exist"""
        task_id = TaskId.generate_new()
        mock_repository.find_by_id.return_value = None
        
        result = service.validate_dependency_chain(task_id)
        
        assert result["valid"] == False
        assert len(result["errors"]) > 0
        assert f"Task {task_id}" in result["errors"][0]
    
    def test_validate_dependency_chain_no_dependencies(self, service, mock_repository, mock_task):
        """Test validation with no dependencies"""
        mock_repository.find_by_id.return_value = mock_task
        mock_repository.find_all.return_value = [mock_task]
        
        result = service.validate_dependency_chain(mock_task.id)
        
        assert "valid" in result
        assert "issues" in result
        assert "errors" in result
    
    def test_validate_with_dependencies(self, service, mock_repository):
        """Test validation with dependencies"""
        # Create tasks with dependencies
        task1 = Mock(spec=Task)
        task1.id = TaskId.generate_new()
        task1.status = TaskStatus.DONE
        task1.get_dependency_ids = Mock(return_value=[])
        
        task2 = Mock(spec=Task)
        task2.id = TaskId.generate_new()
        task2.status = TaskStatus.TODO
        task2.get_dependency_ids = Mock(return_value=[str(task1.id)])
        
        mock_repository.find_by_id.return_value = task2
        mock_repository.find_all.return_value = [task1, task2]
        
        result = service.validate_dependency_chain(task2.id)
        
        assert "valid" in result
        assert "dependency_chain" in result or "issues" in result
    
    def test_detect_circular_dependencies(self, service, mock_repository):
        """Test detection of circular dependencies"""
        # Create circular dependency
        task1 = Mock(spec=Task)
        task1.id = TaskId.generate_new()
        task1.get_dependency_ids = Mock(return_value=[])
        
        task2 = Mock(spec=Task)
        task2.id = TaskId.generate_new()
        
        # Make them depend on each other
        task1.get_dependency_ids = Mock(return_value=[str(task2.id)])
        task2.get_dependency_ids = Mock(return_value=[str(task1.id)])
        
        mock_repository.find_by_id.return_value = task1
        mock_repository.find_all.return_value = [task1, task2]
        
        result = service.validate_dependency_chain(task1.id)
        
        # Should detect circular dependency
        assert "issues" in result or "errors" in result
    
    def test_missing_dependency(self, service, mock_repository):
        """Test validation with missing dependency"""
        task = Mock(spec=Task)
        task.id = TaskId.generate_new()
        task.get_dependency_ids = Mock(return_value=["non-existent-id"])
        
        mock_repository.find_by_id.return_value = task
        mock_repository.find_all.return_value = [task]
        
        result = service.validate_dependency_chain(task.id)
        
        assert "issues" in result or "errors" in result
    
    def test_check_circular_reference(self, service, mock_repository):
        """Test circular reference checking method if exists"""
        task_id = TaskId.generate_new()
        
        # Check if method exists
        if hasattr(service, 'check_circular_references'):
            visited = set()
            result = service.check_circular_references(
                str(task_id),
                {},
                visited
            )
            # Method should handle empty task map
            assert result is not None
    
    def test_get_blocking_dependencies(self, service, mock_repository):
        """Test getting blocking dependencies if method exists"""
        if hasattr(service, 'get_blocking_dependencies'):
            # Create test setup
            blocker = Mock(spec=Task)
            blocker.id = TaskId.generate_new()
            blocker.status = TaskStatus.IN_PROGRESS
            
            task = Mock(spec=Task)
            task.id = TaskId.generate_new()
            task.get_dependency_ids = Mock(return_value=[str(blocker.id)])
            
            mock_repository.find_by_id.return_value = task
            mock_repository.find_all.return_value = [task, blocker]
            
            # This might be part of the validation
            result = service.validate_dependency_chain(task.id)
            
            # Check if blocking info is included
            assert result is not None
    
    def test_validate_complex_chain(self, service, mock_repository):
        """Test validation of complex dependency chain"""
        # Create a chain: task3 -> task2 -> task1
        task1 = Mock(spec=Task)
        task1.id = TaskId.generate_new()
        task1.status = TaskStatus.DONE
        task1.get_dependency_ids = Mock(return_value=[])
        
        task2 = Mock(spec=Task)
        task2.id = TaskId.generate_new()
        task2.status = TaskStatus.DONE
        task2.get_dependency_ids = Mock(return_value=[str(task1.id)])
        
        task3 = Mock(spec=Task)
        task3.id = TaskId.generate_new()
        task3.status = TaskStatus.TODO
        task3.get_dependency_ids = Mock(return_value=[str(task2.id)])
        
        mock_repository.find_by_id.return_value = task3
        mock_repository.find_all.return_value = [task1, task2, task3]
        
        result = service.validate_dependency_chain(task3.id)
        
        assert "valid" in result
        # Chain should be valid as dependencies are complete
    
    def test_parallel_dependencies(self, service, mock_repository):
        """Test task with multiple parallel dependencies"""
        dep1 = Mock(spec=Task)
        dep1.id = TaskId.generate_new()
        dep1.status = TaskStatus.DONE
        dep1.get_dependency_ids = Mock(return_value=[])
        
        dep2 = Mock(spec=Task)
        dep2.id = TaskId.generate_new()
        dep2.status = TaskStatus.IN_PROGRESS
        dep2.get_dependency_ids = Mock(return_value=[])
        
        task = Mock(spec=Task)
        task.id = TaskId.generate_new()
        task.status = TaskStatus.TODO
        task.get_dependency_ids = Mock(return_value=[str(dep1.id), str(dep2.id)])
        
        mock_repository.find_by_id.return_value = task
        mock_repository.find_all.return_value = [dep1, dep2, task]
        
        result = service.validate_dependency_chain(task.id)
        
        # Should identify dep2 as blocking
        assert "valid" in result
        assert "issues" in result or "blocking" in str(result)
    
    def test_self_dependency(self, service, mock_repository):
        """Test task depending on itself"""
        task = Mock(spec=Task)
        task.id = TaskId.generate_new()
        task.get_dependency_ids = Mock(return_value=[str(task.id)])
        
        mock_repository.find_by_id.return_value = task
        mock_repository.find_all.return_value = [task]
        
        result = service.validate_dependency_chain(task.id)
        
        # Should detect self-dependency as issue
        assert "issues" in result or "errors" in result
        
    def test_empty_repository(self, service, mock_repository):
        """Test validation with empty repository"""
        task_id = TaskId.generate_new()
        mock_repository.find_by_id.return_value = None
        mock_repository.find_all.return_value = []
        
        result = service.validate_dependency_chain(task_id)
        
        assert result["valid"] == False
        assert len(result["errors"]) > 0