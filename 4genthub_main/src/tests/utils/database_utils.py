"""
Standardized Database Testing Utilities

Consolidates database fixture patterns and provides consistent test data creation utilities.
Replaces scattered database setup patterns with a unified approach.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from sqlalchemy import text
import pytest


@dataclass
class TestProjectData:
    """Standardized test project data structure"""
    project_id: str
    git_branch_id: str
    project_name: str = ""
    branch_name: str = "test-branch"
    user_id: str = "test_user"
    
    def __post_init__(self):
        if not self.project_name:
            self.project_name = f'Test Project {self.project_id[:8]}'


class TestDataBuilder:
    """Builder pattern for creating consistent test data"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state"""
        self._project_id = None
        self._git_branch_id = None
        self._project_name = None
        self._branch_name = "test-branch"
        self._user_id = "test_user"
        return self
    
    def with_project_id(self, project_id: str):
        """Set specific project ID"""
        self._project_id = project_id
        return self
    
    def with_git_branch_id(self, git_branch_id: str):
        """Set specific git branch ID"""
        self._git_branch_id = git_branch_id
        return self
    
    def with_project_name(self, name: str):
        """Set specific project name"""
        self._project_name = name
        return self
    
    def with_branch_name(self, name: str):
        """Set specific branch name"""
        self._branch_name = name
        return self
    
    def with_user_id(self, user_id: str):
        """Set specific user ID"""
        self._user_id = user_id
        return self
    
    def build(self) -> TestProjectData:
        """Build the test project data"""
        project_id = self._project_id or f"test-project-{uuid.uuid4()}"
        git_branch_id = self._git_branch_id or f"test-branch-{uuid.uuid4()}"
        
        return TestProjectData(
            project_id=project_id,
            git_branch_id=git_branch_id,
            project_name=self._project_name or f'Test Project {project_id[:8]}',
            branch_name=self._branch_name,
            user_id=self._user_id
        )


def create_test_project_data(
    project_id: Optional[str] = None,
    git_branch_id: Optional[str] = None,
    project_name: Optional[str] = None,
    branch_name: str = "test-branch",
    user_id: str = "test_user"
) -> TestProjectData:
    """
    Create standardized test project data with consistent structure.
    
    This function consolidates the various database fixture patterns
    used throughout the test suite into a single, consistent approach.
    """
    return (TestDataBuilder()
            .with_project_id(project_id)
            .with_git_branch_id(git_branch_id)
            .with_project_name(project_name)
            .with_branch_name(branch_name)
            .with_user_id(user_id)
            .build())


def create_database_records(test_data: TestProjectData) -> None:
    """
    Create database records for test project data.
    
    Args:
        test_data: TestProjectData instance with the records to create
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    db_config = get_db_config()
    
    with db_config.get_session() as session:
        try:
            # Create project
            session.execute(text("""
                INSERT INTO projects (id, name, description, user_id, status, created_at, updated_at, metadata)
                VALUES (:id, :name, :description, :user_id, :status, :created_at, :updated_at, :metadata)
            """), {
                'id': test_data.project_id,
                'name': test_data.project_name,
                'description': 'Project for testing',
                'user_id': test_data.user_id,
                'status': 'active',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'metadata': '{}'
            })
            
            # Create git branch
            session.execute(text("""
                INSERT INTO project_git_branchs (
                    id, project_id, name, description, 
                    created_at, updated_at, priority, status, 
                    metadata, task_count, completed_task_count
                )
                VALUES (
                    :id, :project_id, :name, :description,
                    :created_at, :updated_at, :priority, :status,
                    :metadata, :task_count, :completed_task_count
                )
            """), {
                'id': test_data.git_branch_id,
                'project_id': test_data.project_id,
                'name': test_data.branch_name,
                'description': 'Branch for testing',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'priority': 'medium',
                'status': 'todo',
                'metadata': '{}',
                'task_count': 0,
                'completed_task_count': 0
            })
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to create test database records: {e}")


def cleanup_test_data(test_data: TestProjectData) -> None:
    """
    Clean up test database records.
    
    Args:
        test_data: TestProjectData instance with the records to clean up
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    db_config = get_db_config()
    
    with db_config.get_session() as session:
        try:
            # Delete tasks first (foreign key constraint)
            session.execute(text("DELETE FROM tasks WHERE git_branch_id = :branch_id"), 
                          {'branch_id': test_data.git_branch_id})
            
            # Delete branch
            session.execute(text("DELETE FROM project_git_branchs WHERE id = :id"), 
                          {'id': test_data.git_branch_id})
            
            # Delete project
            session.execute(text("DELETE FROM projects WHERE id = :id"), 
                          {'id': test_data.project_id})
            
            session.commit()
            
        except Exception:
            session.rollback()


def create_valid_git_branch(project_id: Optional[str] = None) -> str:
    """
    Create a valid git branch ID that exists in the database.
    
    Args:
        project_id: Optional project ID to use. If None, creates a new project.
    
    Returns:
        git_branch_id: The ID of the created branch
    """
    test_data = create_test_project_data(project_id=project_id)
    create_database_records(test_data)
    return test_data.git_branch_id


def create_invalid_git_branch_id() -> str:
    """
    Create an invalid git_branch_id that does NOT exist in the database.
    Used for testing foreign key constraint violations.
    """
    return f"non-existent-branch-{uuid.uuid4()}"


# =============================================
# PYTEST FIXTURES
# =============================================

@pytest.fixture
def test_project_data(request):
    """
    Standardized pytest fixture for test project data.
    
    This fixture consolidates the various database fixture patterns
    and provides consistent test data creation and cleanup.
    """
    # Create test data
    test_data = create_test_project_data()
    
    # Create database records
    create_database_records(test_data)
    
    yield test_data
    
    # Cleanup after test
    cleanup_test_data(test_data)


@pytest.fixture
def valid_git_branch_id():
    """
    Standardized pytest fixture for valid git branch ID.
    
    This provides a valid git_branch_id that exists in the database
    and cleans up automatically after the test.
    """
    test_data = create_test_project_data()
    create_database_records(test_data)
    
    yield test_data.git_branch_id
    
    cleanup_test_data(test_data)


@pytest.fixture
def invalid_git_branch_id():
    """
    Standardized pytest fixture for invalid git branch ID.
    
    This provides an invalid git_branch_id for testing error conditions.
    """
    return create_invalid_git_branch_id()


@pytest.fixture
def test_data_builder():
    """
    Pytest fixture providing the TestDataBuilder for custom test data.
    
    Usage:
        def test_something(test_data_builder):
            test_data = test_data_builder.with_project_name("Custom Project").build()
            create_database_records(test_data)
            # ... test code ...
            cleanup_test_data(test_data)
    """
    return TestDataBuilder()