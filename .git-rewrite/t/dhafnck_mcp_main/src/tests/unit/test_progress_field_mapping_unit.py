#!/usr/bin/env python3
"""
Unit test for progress field mapping functions
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
def test_model_to_entity_progress_mapping():
    """Test that _model_to_entity correctly maps progress_percentage to overall_progress"""
    
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    
    # Create a repository instance
    repo = ORMTaskRepository(git_branch_id="test-branch")
    
    # Create a mock Task model with progress_percentage
    mock_task = Mock()
    mock_task.id = str(uuid.uuid4())  # Use valid UUID
    mock_task.title = "Test Task"
    mock_task.description = "Test Description"
    mock_task.git_branch_id = "test-branch"
    mock_task.status = "in_progress"
    mock_task.priority = "medium"
    mock_task.details = "Some details"
    mock_task.estimated_effort = "2 hours"
    mock_task.due_date = None
    mock_task.created_at = datetime.now()
    mock_task.updated_at = datetime.now()
    mock_task.context_id = None
    mock_task.progress_percentage = 75  # This is the field we're testing
    
    # Mock relationships
    mock_task.assignees = []
    mock_task.labels = []
    mock_task.subtasks = []
    mock_task.dependencies = []
    
    # Call the mapping function
    entity = repo._model_to_entity(mock_task)
    
    # Verify the mapping
    assert hasattr(entity, 'overall_progress'), "Entity should have overall_progress field"
    assert entity.overall_progress == 75, f"Expected overall_progress to be 75, got {entity.overall_progress}"
    print("✅ Model to entity progress mapping works correctly")


@pytest.mark.unit
def test_update_task_progress_mapping():
    """Test that update_task correctly maps overall_progress to progress_percentage"""
    
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
    from unittest.mock import patch, MagicMock
    
    # Create a repository instance
    repo = ORMTaskRepository(git_branch_id="test-branch")
    
    # Mock the base update method
    with patch.object(repo, 'update') as mock_update:
        # Mock a return task
        mock_task = Mock()
        mock_task.id = str(uuid.uuid4())  # Use valid UUID
        mock_update.return_value = mock_task
        
        # Mock the transaction and session
        with patch.object(repo, 'transaction'):
            with patch.object(repo, 'get_db_session'):
                # Mock the _model_to_entity to return a simple entity
                with patch.object(repo, '_model_to_entity') as mock_to_entity:
                    mock_entity = Mock()
                    mock_entity.overall_progress = 90
                    mock_to_entity.return_value = mock_entity
                    
                    # Call update_task with overall_progress
                    task_id = str(uuid.uuid4())
                    result = repo.update_task(task_id, overall_progress=90)
                    
                    # Verify that update was called with progress_percentage
                    mock_update.assert_called_once()
                    call_args = mock_update.call_args[1]
                    assert 'progress_percentage' in call_args, "progress_percentage should be in update arguments"
                    assert call_args['progress_percentage'] == 90, f"Expected progress_percentage to be 90, got {call_args['progress_percentage']}"
                    assert 'overall_progress' not in call_args, "overall_progress should have been removed from arguments"
                    
    print("✅ Update task progress mapping works correctly")


if __name__ == "__main__":
    test_model_to_entity_progress_mapping()
    test_update_task_progress_mapping()
    print("\n✅ All unit tests passed!")