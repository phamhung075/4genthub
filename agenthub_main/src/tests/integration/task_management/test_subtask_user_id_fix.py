"""
Test to verify that subtask creation with user_id works correctly after the fix.
This test specifically addresses the issue where subtasks failed to be created
due to missing user_id in the database.
"""

import os
import pytest
import uuid
from datetime import datetime, timezone
from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch, Task, Subtask as SubtaskModel
from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority

# Ensure MVP mode is disabled for this test
os.environ['PRODUCTION'] = 'false'


class TestSubtaskUserIdFix:
    """Test subtask creation with proper user_id handling"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        """Set up test data before each test"""
        # Ensure MVP mode is disabled for these tests
        monkeypatch.setenv('PRODUCTION', 'false')
        
        self.session = get_session()
        self.user_id = str(uuid.uuid4())
        self.project_id = str(uuid.uuid4())
        self.branch_id = str(uuid.uuid4())
        self.task_id = str(uuid.uuid4())
        
        # Create test project
        project = Project(
            id=self.project_id,
            name="Test Project for Subtask",
            description="Project for testing subtask user_id fix",
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.session.add(project)
        
        # Create test branch
        branch = ProjectGitBranch(
            id=self.branch_id,
            project_id=self.project_id,
            name="test/subtask-fix",
            description="Branch for testing subtask creation",
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.session.add(branch)
        
        # Create test task
        task = Task(
            id=self.task_id,
            title="Parent Task for Subtask Test",
            description="This task will have subtasks",
            git_branch_id=self.branch_id,
            status="todo",
            priority="medium",
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.session.add(task)
        self.session.commit()
        
        yield
        
        # Cleanup
        self.session.query(SubtaskModel).filter(SubtaskModel.task_id == self.task_id).delete()
        self.session.query(Task).filter(Task.id == self.task_id).delete()
        self.session.query(ProjectGitBranch).filter(ProjectGitBranch.id == self.branch_id).delete()
        self.session.query(Project).filter(Project.id == self.project_id).delete()
        self.session.commit()
        self.session.close()
    
    def test_create_subtask_with_user_id(self):
        """Test that subtasks can be created with proper user_id"""
        # Create subtask repository with user_id
        subtask_repo = ORMSubtaskRepository(session=self.session, user_id=self.user_id)
        
        # Create subtask entity
        subtask_id = SubtaskId(str(uuid.uuid4()))
        subtask = Subtask.create(
            id=subtask_id,
            title="Test Subtask",
            description="Testing subtask creation with user_id",
            parent_task_id=TaskId(self.task_id),
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        
        # Save subtask - this should now work with user_id properly set
        result = subtask_repo.save(subtask)
        
        # Verify save was successful
        assert result is True, "Subtask save should return True"
        
        # Verify subtask was created in database
        db_subtask = self.session.query(SubtaskModel).filter(
            SubtaskModel.id == subtask_id.value
        ).first()
        
        assert db_subtask is not None, "Subtask should exist in database"
        assert db_subtask.user_id == self.user_id, f"Subtask user_id should be {self.user_id}"
        assert db_subtask.title == "Test Subtask", "Subtask title should match"
        assert db_subtask.task_id == self.task_id, "Subtask should be linked to parent task"
    
    def test_create_subtask_without_user_id_uses_mvp_fallback(self):
        """Test that creating subtask without user_id requires authentication"""
        # Create subtask repository WITHOUT user_id (system mode)
        subtask_repo = ORMSubtaskRepository(session=self.session, user_id=None)
        
        # Create subtask entity
        subtask_id = SubtaskId(str(uuid.uuid4()))
        subtask = Subtask.create(
            id=subtask_id,
            title="Test Subtask System Mode",
            description="Testing subtask creation requires authentication",
            parent_task_id=TaskId(self.task_id),
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        
        # Save subtask - this should fail without authentication
        result = subtask_repo.save(subtask)
        
        # Should fail (return False) when no authentication
        assert result is False, \
            "Should fail to save subtask when no user_id is provided"
        
        # Verify it was NOT saved in database
        from fastmcp.task_management.infrastructure.database.models import Subtask as SubtaskModel
        db_subtask = self.session.query(SubtaskModel).filter_by(id=str(subtask_id)).first()
        
        assert db_subtask is None, "Subtask should NOT be saved without authentication"
    
    def test_subtask_repository_from_factory(self):
        """Test that subtask repository created from factory has proper user_id"""
        from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
        
        # Get subtask repository from factory with user_id
        subtask_repo = RepositoryFactory.get_subtask_repository(user_id=self.user_id)
        
        # Create subtask entity
        subtask_id = SubtaskId(str(uuid.uuid4()))
        subtask = Subtask.create(
            id=subtask_id,
            title="Test Subtask from Factory",
            description="Testing subtask creation from factory",
            parent_task_id=TaskId(self.task_id),
            status=TaskStatus.todo(),
            priority=Priority.high()
        )
        
        # Save subtask
        result = subtask_repo.save(subtask)
        
        # Verify save was successful
        assert result is True, "Subtask save should return True"
        
        # Verify subtask was created in database
        db_subtask = self.session.query(SubtaskModel).filter(
            SubtaskModel.id == subtask_id.value
        ).first()
        
        assert db_subtask is not None, "Subtask should exist in database"
        assert db_subtask.user_id == self.user_id, f"Subtask user_id should be {self.user_id}"
        assert db_subtask.title == "Test Subtask from Factory", "Subtask title should match"
        assert db_subtask.priority == "high", "Subtask priority should be high"