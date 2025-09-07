#!/usr/bin/env python3
"""
Test for progress field mapping between domain entity and database model
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from fastmcp.task_management.infrastructure.database.models import ProjectGitBranch
from datetime import datetime, timezone
import uuid
from sqlalchemy import text


@pytest.mark.database
def test_progress_field_mapping():
    """Test that overall_progress in entity maps correctly to progress_percentage in database"""
    
    # Use the existing test infrastructure that's already set up by conftest.py
    db_config = get_db_config()
    
    # Enable foreign key constraints for SQLite
    with db_config.get_session() as session:
        if db_config.database_type == "sqlite":
            session.execute(text("PRAGMA foreign_keys = ON"))
    
    # Find an existing git branch from the test setup (conftest.py creates one automatically)
    with db_config.get_session() as session:
        result = session.execute(text(
            "SELECT id FROM project_git_branchs WHERE project_id = 'default_project' AND user_id = 'system' LIMIT 1"
        ))
        row = result.fetchone()
        
        if not row:
            raise RuntimeError("No test git branch found - test database may not be properly initialized")
        
        test_branch_id = str(row[0])  # Ensure it's a string
        print(f"DEBUG: Using git_branch_id: {test_branch_id} (type: {type(test_branch_id)})")
    
    # Verify the git branch exists before creating tasks
    with db_config.get_session() as session:
        verify_result = session.execute(text(
            "SELECT COUNT(*) FROM project_git_branchs WHERE id = :branch_id"
        ), {"branch_id": test_branch_id})
        count = verify_result.fetchone()[0]
        print(f"DEBUG: Found {count} git branch(es) with id {test_branch_id}")
        
        if count == 0:
            # List all available branches for debugging
            all_branches = session.execute(text("SELECT id, name, project_id, user_id FROM project_git_branchs"))
            print("DEBUG: Available git branches:")
            for branch in all_branches.fetchall():
                print(f"  - ID: {branch[0]}, Name: {branch[1]}, Project: {branch[2]}, User: {branch[3]}")
            raise RuntimeError(f"Git branch {test_branch_id} does not exist in database")

    # Create repository with the valid git_branch_id and system user_id (matches conftest setup)
    repo = ORMTaskRepository(git_branch_id=test_branch_id, user_id="system")
    
    # Create a task
    task = repo.create_task(
        title="Test Progress Task",
        description="Testing progress field mapping",
        priority="medium"
    )
    
    assert task is not None
    assert hasattr(task, 'overall_progress'), "Entity should have overall_progress field"
    assert task.overall_progress == 0, "Initial progress should be 0"
    
    # Update progress using overall_progress
    updated_task = repo.update_task(
        str(task.id),
        overall_progress=75
    )
    
    assert updated_task.overall_progress == 75, "Progress should be updated to 75%"
    
    # Retrieve task to verify persistence
    retrieved_task = repo.get_task(str(task.id))
    assert retrieved_task is not None
    assert retrieved_task.overall_progress == 75, "Retrieved task should have correct progress"
    
    # Save task entity with progress
    task.overall_progress = 90
    success = repo.save(task)
    assert success, "Save should succeed"
    
    # Retrieve again to verify save worked
    final_task = repo.get_task(str(task.id))
    assert final_task.overall_progress == 90, "Saved progress should be persisted"
    
    print("✅ Progress field mapping test passed!")


if __name__ == "__main__":
    test_progress_field_mapping()