"""
Database fixtures for test data setup.

This module provides fixtures that ensure proper database setup for tests,
including creating necessary parent records before creating child records.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import text


@pytest.fixture
def test_project_data(request):
    """
    Create a test project with proper database setup.
    Returns project_id and git_branch_id for use in tests.
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    # Generate unique IDs for this test
    project_id = f"test-project-{uuid.uuid4()}"
    branch_id = f"test-branch-{uuid.uuid4()}"
    
    db_config = get_db_config()
    
    # Create project and branch
    with db_config.get_session() as session:
        try:
            # Create project
            session.execute(text("""
                INSERT INTO projects (id, name, description, user_id, status, created_at, updated_at, metadata)
                VALUES (:id, :name, :description, :user_id, :status, :created_at, :updated_at, :metadata)
            """), {
                'id': project_id,
                'name': f'Test Project {project_id[:8]}',
                'description': 'Project for testing',
                'user_id': 'test_user',
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
                'id': branch_id,
                'project_id': project_id,
                'name': 'test-branch',
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
            raise Exception(f"Failed to create test data: {e}")
    
    # Return the IDs for use in tests
    test_data = {
        'project_id': project_id,
        'git_branch_id': branch_id
    }
    
    yield test_data
    
    # Cleanup after test
    with db_config.get_session() as session:
        try:
            # Delete tasks first (foreign key constraint)
            session.execute(text("DELETE FROM tasks WHERE git_branch_id = :branch_id"), 
                          {'branch_id': branch_id})
            # Delete branch
            session.execute(text("DELETE FROM project_git_branchs WHERE id = :id"), 
                          {'id': branch_id})
            # Delete project
            session.execute(text("DELETE FROM projects WHERE id = :id"), 
                          {'id': project_id})
            session.commit()
        except Exception:
            session.rollback()


@pytest.fixture
def valid_git_branch_id():
    """
    Provides a valid git_branch_id that exists in the database.
    Creates the necessary project and branch records.
    """
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    
    branch_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    db_config = get_db_config()
    
    with db_config.get_session() as session:
        try:
            # Create project first
            session.execute(text("""
                INSERT INTO projects (id, name, description, user_id, status, created_at, updated_at, metadata)
                VALUES (:id, :name, :description, :user_id, :status, :created_at, :updated_at, :metadata)
            """), {
                'id': project_id,
                'name': 'Test Project for Valid Branch',
                'description': 'Test project',
                'user_id': 'test_user',
                'status': 'active',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'metadata': '{}'
            })
            
            # Create branch
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
                'id': branch_id,
                'project_id': project_id,
                'name': 'valid-test-branch',
                'description': 'Valid branch for testing',
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
            raise Exception(f"Failed to create valid git branch: {e}")
    
    yield branch_id
    
    # Cleanup
    with db_config.get_session() as session:
        try:
            session.execute(text("DELETE FROM tasks WHERE git_branch_id = :branch_id"),
                          {'branch_id': branch_id})
            session.execute(text("DELETE FROM project_git_branchs WHERE id = :id"),
                          {'id': branch_id})
            session.execute(text("DELETE FROM projects WHERE id = :id"),
                          {'id': project_id})
            session.commit()
        except Exception:
            session.rollback()


@pytest.fixture
def invalid_git_branch_id():
    """
    Provides an invalid git_branch_id that does NOT exist in the database.
    Used for testing foreign key constraint violations.
    """
    return f"non-existent-branch-{uuid.uuid4()}"