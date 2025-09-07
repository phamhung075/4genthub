"""Test auto-context creation during task completion.

This test verifies that Issue #1 is fixed: tasks can now be completed
without manually creating context first.
"""

import pytest
import uuid
from unittest.mock import Mock
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.complete_task import CompleteTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import TaskStatus, Priority, TaskId
from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import (
    Project, ProjectGitBranch, Task as TaskModel, 
    GlobalContext as GlobalContextModel
)


class TestTaskCompletionAutoContext:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test that task completion auto-creates context if needed."""
    
    @pytest.fixture
    def setup_test_data(self):
        """Set up test database with project, branch, and task."""
        with get_session() as session:
            # Ensure global context exists
            global_context = session.get(GlobalContextModel, "global_singleton")
            if not global_context:
                global_context = GlobalContextModel(
                    id="global_singleton",
                    organization_id="default_org",
                    autonomous_rules={},
                    security_policies={},
                    coding_standards={},
                    workflow_templates={},
                    delegation_rules={},
                    version=1
                )
                session.add(global_context)
                session.commit()
            
            # Generate UUIDs for test entities
            project_id = str(uuid.uuid4())
            branch_id = str(uuid.uuid4())
            task_id = str(uuid.uuid4())
            
            # Create test project
            project = Project(
                id=project_id,
                name="Test Project Auto Context",
                description="Test project for auto context creation",
                user_id="test_user",
                status="active"
            )
            session.add(project)
            
            # Create test branch
            branch = ProjectGitBranch(
                id=branch_id,
                project_id=project_id,
                name="main",
                description="Main branch for testing"
            )
            session.add(branch)
            
            # Create test task WITHOUT context
            task = TaskModel(
                id=task_id,
                git_branch_id=branch_id,
                title="Test Task for Auto Context",
                description="This task will test auto context creation",
                status="todo",
                priority="medium"
            )
            session.add(task)
            
            session.commit()
            
            return {
                "project_id": project_id,
                "branch_id": branch_id,
                "task_id": task_id
            }
    
    def test_complete_task_auto_creates_context(self, setup_test_data):
        """Test that completing a task without context auto-creates it."""
        task_id = setup_test_data["task_id"]
        
        # Create repositories
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
        from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
        
        task_repo = ORMTaskRepository(git_branch_id=setup_test_data["branch_id"], user_id="test_user")
        subtask_repo = ORMSubtaskRepository()
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        context_repo = TaskContextRepository(get_session)
        
        # Create use case
        use_case = CompleteTaskUseCase(
            task_repository=task_repo,
            subtask_repository=subtask_repo,
            task_context_repository=context_repo
        )
        
        # Verify context doesn't exist yet
        initial_context = context_repo.get(task_id)
        assert initial_context is None, "Context should not exist before completion"
        
        # Complete the task
        result = use_case.execute(
            task_id=task_id,
            completion_summary="Task completed successfully with auto-created context",
            testing_notes="Verified auto context creation works"
        )
        
        # Verify completion succeeded
        print(f"Task completion result: {result}")
        assert result["success"] is True, f"Task completion failed: {result}"
        assert result["status"] == "done"
        assert f"task {task_id} done, can next_task" in result["message"]
        
        # Verify context was auto-created
        created_context = context_repo.get(task_id)
        assert created_context is not None, "Context should have been auto-created"
        
        # TaskContextUnified is an object, not a dict, so access attributes directly
        if hasattr(created_context, 'id'):
            assert created_context.id == task_id
        elif hasattr(created_context, 'get'):
            assert created_context.get("id") == task_id
        else:
            # If it's a dict-like object returned by the repository
            assert str(created_context).find(task_id) != -1, f"Context should contain task_id {task_id}, got: {created_context}"
    
    def test_complete_task_with_existing_context(self, setup_test_data):
        """Test that completing a task with existing context works normally."""
        task_id = setup_test_data["task_id"]
        branch_id = setup_test_data["branch_id"]
        
        # Create repositories
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
        from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
        
        task_repo = ORMTaskRepository(git_branch_id=setup_test_data["branch_id"], user_id="test_user")
        subtask_repo = ORMSubtaskRepository()
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        context_repo = TaskContextRepository(get_session)
        
        # Pre-create context
        from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        facade = UnifiedContextFacadeFactory().create_facade(git_branch_id=branch_id)
        
        # Create project context first (required by hierarchy)
        project_result = facade.create_context(
            level="project",
            context_id=setup_test_data["project_id"],
            data={
                "project_name": "Test Project Auto Context",
                "project_settings": {}
            }
        )
        assert project_result["success"], f"Project context creation failed: {project_result.get('error')}"
        
        # Create branch context
        branch_result = facade.create_context(
            level="branch",
            context_id=branch_id,
            data={
                "project_id": setup_test_data["project_id"],
                "git_branch_name": "main",
                "branch_settings": {}
            }
        )
        assert branch_result["success"], f"Branch context creation failed: {branch_result.get('error')}"
        
        # Create task context
        context_result = facade.create_context(
            level="task",
            context_id=task_id,
            data={
                "branch_id": branch_id,
                "task_data": {
                    "title": "Pre-existing context",
                    "status": "todo"
                }
            }
        )
        assert context_result["success"], "Pre-creating context failed"
        
        # Create use case
        use_case = CompleteTaskUseCase(
            task_repository=task_repo,
            subtask_repository=subtask_repo,
            task_context_repository=context_repo
        )
        
        # Complete the task
        result = use_case.execute(
            task_id=task_id,
            completion_summary="Task completed with pre-existing context",
            testing_notes="Verified existing context flow still works"
        )
        
        # Verify completion succeeded
        print(f"Task completion result (with existing context): {result}")
        assert result["success"] is True, f"Task completion failed: {result.get('message')}"
        assert result["status"] == "done"
    
    def test_complete_task_auto_context_handles_errors_gracefully(self, setup_test_data):
        """Test that task completion continues even if auto-context creation fails."""
        task_id = setup_test_data["task_id"]
        
        # Create repositories
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
        
        task_repo = ORMTaskRepository(git_branch_id=setup_test_data["branch_id"], user_id="test_user")
        subtask_repo = ORMSubtaskRepository()
        
        # Create a mock context repository that will fail on get but not crash
        mock_context_repo = Mock()
        mock_context_repo.get.return_value = None  # No existing context
        
        # Create use case with mock repository
        use_case = CompleteTaskUseCase(
            task_repository=task_repo,
            subtask_repository=subtask_repo,
            task_context_repository=mock_context_repo
        )
        
        # Complete the task (even though context creation might fail internally)
        result = use_case.execute(
            task_id=task_id,
            completion_summary="Task completed even with context issues",
            testing_notes="Testing graceful handling"
        )
        
        # Verify completion succeeded despite potential context issues
        assert result["success"] is True, f"Task completion failed: {result.get('message')}"
        assert result["status"] == "done"
        
        # Verify context check was attempted
        mock_context_repo.get.assert_called_once_with(task_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])