"""Test Mock Repository Completeness

This test ensures that all mock repository implementations have
all the required abstract methods from their interfaces.
"""

import inspect
import pytest
from typing import List, Set
import asyncio

# Import interfaces
from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository

# Import mock implementations from fixtures
from tests.fixtures.mocks.repositories import (
    MockProjectRepository,
    MockGitBranchRepository,
    MockTaskRepository,
    MockSubtaskRepository
)


def get_abstract_methods(interface_class) -> Set[str]:
    """Get all abstract methods from an interface class"""
    abstract_methods = set()
    
    # Get all methods from the class and its bases
    for name, method in inspect.getmembers(interface_class, predicate=inspect.isfunction):
        # Skip private methods
        if name.startswith('_'):
            continue
        # Add all public methods as they should be implemented
        abstract_methods.add(name)
    
    # Also check for abstract methods explicitly
    if hasattr(interface_class, '__abstractmethods__'):
        abstract_methods.update(interface_class.__abstractmethods__)
    
    return abstract_methods


def get_implemented_methods(implementation_class) -> Set[str]:
    """Get all implemented methods from a class"""
    implemented = set()
    
    for name, method in inspect.getmembers(implementation_class, predicate=inspect.ismethod):
        # Skip private methods
        if name.startswith('_'):
            continue
        implemented.add(name)
    
    # Also check instance methods
    for name in dir(implementation_class):
        if not name.startswith('_'):
            attr = getattr(implementation_class, name)
            if callable(attr):
                implemented.add(name)
    
    return implemented


class TestMockRepositoryCompleteness:
    """Test that mock repositories implement all required methods"""
    
    def test_mock_project_repository_completeness(self):
        """Test MockProjectRepository has all required methods"""
        # Get required methods from interface
        required_methods = get_abstract_methods(ProjectRepository)
        
        # Get implemented methods from mock
        mock_instance = MockProjectRepository()
        implemented_methods = set()
        for name in dir(mock_instance):
            if not name.startswith('_') and callable(getattr(mock_instance, name)):
                implemented_methods.add(name)
        
        # Find missing methods
        missing_methods = required_methods - implemented_methods
        
        # Assert no methods are missing
        assert len(missing_methods) == 0, f"MockProjectRepository missing methods: {missing_methods}"
        
        # Additional check: Try to instantiate and use basic methods
        repo = MockProjectRepository()
        assert repo is not None
        
        # Test basic async methods work
        loop = asyncio.new_event_loop()
        try:
            # Test find_all
            result = loop.run_until_complete(repo.find_all())
            assert isinstance(result, list)
            
            # Test count
            count = loop.run_until_complete(repo.count())
            assert isinstance(count, int)
            
            # Test exists
            exists = loop.run_until_complete(repo.exists("test-id"))
            assert isinstance(exists, bool)
        finally:
            loop.close()
    
    def test_mock_git_branch_repository_completeness(self):
        """Test MockGitBranchRepository has all required methods"""
        required_methods = get_abstract_methods(GitBranchRepository)
        
        mock_instance = MockGitBranchRepository()
        implemented_methods = set()
        for name in dir(mock_instance):
            if not name.startswith('_') and callable(getattr(mock_instance, name)):
                implemented_methods.add(name)
        
        missing_methods = required_methods - implemented_methods
        
        assert len(missing_methods) == 0, f"MockGitBranchRepository missing methods: {missing_methods}"
        
        # Test instantiation
        repo = MockGitBranchRepository()
        assert repo is not None
        
        # Test basic async methods
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(repo.find_all())
            assert isinstance(result, list)
            
            count = loop.run_until_complete(repo.count())
            assert isinstance(count, int)
        finally:
            loop.close()
    
    def test_mock_task_repository_completeness(self):
        """Test MockTaskRepository has all required methods"""
        required_methods = get_abstract_methods(TaskRepository)
        
        mock_instance = MockTaskRepository("test-project", "test-branch", "test-user")
        implemented_methods = set()
        for name in dir(mock_instance):
            if not name.startswith('_') and callable(getattr(mock_instance, name)):
                implemented_methods.add(name)
        
        missing_methods = required_methods - implemented_methods
        
        assert len(missing_methods) == 0, f"MockTaskRepository missing methods: {missing_methods}"
        
        # Test instantiation with required parameters
        repo = MockTaskRepository("test-project", "test-branch", "test-user")
        assert repo is not None
    
    def test_mock_subtask_repository_completeness(self):
        """Test MockSubtaskRepository has all required methods"""
        required_methods = get_abstract_methods(SubtaskRepository)
        
        mock_instance = MockSubtaskRepository("test-project", "test-branch", "test-user")
        implemented_methods = set()
        for name in dir(mock_instance):
            if not name.startswith('_') and callable(getattr(mock_instance, name)):
                implemented_methods.add(name)
        
        missing_methods = required_methods - implemented_methods
        
        assert len(missing_methods) == 0, f"MockSubtaskRepository missing methods: {missing_methods}"
        
        # Test instantiation
        repo = MockSubtaskRepository("test-project", "test-branch", "test-user")
        assert repo is not None
    
    def test_all_mocks_can_be_created(self):
        """Test that all mock repositories can be instantiated without errors"""
        # Project repository
        project_repo = MockProjectRepository()
        assert project_repo is not None
        
        # Git branch repository
        branch_repo = MockGitBranchRepository()
        assert branch_repo is not None
        
        # Task repository (requires parameters)
        task_repo = MockTaskRepository("proj-1", "branch-1", "user-1")
        assert task_repo is not None
        
        # Subtask repository (requires parameters)
        subtask_repo = MockSubtaskRepository("proj-1", "branch-1", "user-1")
        assert subtask_repo is not None
    
    def test_mock_methods_return_appropriate_types(self):
        """Test that mock methods return appropriate types"""
        project_repo = MockProjectRepository()
        
        loop = asyncio.new_event_loop()
        try:
            # Test find_all returns list
            all_projects = loop.run_until_complete(project_repo.find_all())
            assert isinstance(all_projects, list)
            
            # Test find_by_id returns None or Project
            project = loop.run_until_complete(project_repo.find_by_id("nonexistent"))
            assert project is None
            
            # Test count returns int
            count = loop.run_until_complete(project_repo.count())
            assert isinstance(count, int)
            assert count >= 0
            
            # Test exists returns bool
            exists = loop.run_until_complete(project_repo.exists("test"))
            assert isinstance(exists, bool)
            
            # Test delete returns bool
            deleted = loop.run_until_complete(project_repo.delete("test"))
            assert isinstance(deleted, bool)
            
        finally:
            loop.close()


class TestMockRepositoryFunctionality:
    """Test that mock repositories provide basic functionality"""
    
    def test_mock_project_repository_crud(self):
        """Test basic CRUD operations on MockProjectRepository"""
        from fastmcp.task_management.domain.entities.project import Project
        from datetime import datetime
        
        repo = MockProjectRepository()
        loop = asyncio.new_event_loop()
        
        try:
            # Create a project
            project = Project(
                id="proj-1",
                name="Test Project",
                description="Test Description",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save project
            saved = loop.run_until_complete(repo.save(project))
            assert saved.id == project.id
            
            # Find by ID
            found = loop.run_until_complete(repo.find_by_id("proj-1"))
            assert found is not None
            assert found.name == "Test Project"
            
            # Find by name
            found_by_name = loop.run_until_complete(repo.find_by_name("Test Project"))
            assert found_by_name is not None
            assert found_by_name.id == "proj-1"
            
            # Check exists
            exists = loop.run_until_complete(repo.exists("proj-1"))
            assert exists is True
            
            # Count
            count = loop.run_until_complete(repo.count())
            assert count == 1
            
            # Find all
            all_projects = loop.run_until_complete(repo.find_all())
            assert len(all_projects) == 1
            
            # Delete
            deleted = loop.run_until_complete(repo.delete("proj-1"))
            assert deleted is True
            
            # Verify deleted
            found_after_delete = loop.run_until_complete(repo.find_by_id("proj-1"))
            assert found_after_delete is None
            
            count_after_delete = loop.run_until_complete(repo.count())
            assert count_after_delete == 0
            
        finally:
            loop.close()
    
    def test_mock_task_repository_basic_operations(self):
        """Test basic operations on MockTaskRepository"""
        from fastmcp.task_management.domain.entities.task import Task
        from fastmcp.task_management.domain.value_objects import TaskId
        from datetime import datetime
        
        repo = MockTaskRepository("proj-1", "branch-1", "user-1")
        
        # Create a task
        task = Task(
            id="task-1",
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-1",
            status="pending",
            priority="medium",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save task
        saved = repo.save(task)
        assert saved.id == task.id
        
        # Find by ID
        task_id = TaskId("task-1")
        found = repo.find_by_id(task_id)
        assert found is not None
        assert found.title == "Test Task"
        
        # Find all
        all_tasks = repo.find_all()
        assert len(all_tasks) == 1
        
        # Delete
        deleted = repo.delete(task_id)
        assert deleted is True
        
        # Verify deleted
        found_after_delete = repo.find_by_id(task_id)
        assert found_after_delete is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])