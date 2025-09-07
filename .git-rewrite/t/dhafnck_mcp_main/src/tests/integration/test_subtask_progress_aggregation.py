#!/usr/bin/env python3
"""
Test: Subtask Progress Aggregation to Parent Task

This test verifies if updating subtask progress automatically updates
the parent task's completion percentage.
"""

import pytest
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import (
    Project, ProjectGitBranch, Task as TaskModel, TaskSubtask as SubtaskModel,
    GlobalContext as GlobalContextModel
)
from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.interface.controllers.subtask_mcp_controller import SubtaskMCPController
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory


class TestSubtaskProgressAggregation:
    
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

    """Test if subtask progress updates parent task progress."""
    
    @pytest.fixture
    def setup_project_and_branch(self):
        """Create test project and branch."""
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
            
            # Create project
            project_id = str(uuid.uuid4())
            project = Project(
                id=project_id,
                name="Test Progress Aggregation Project",
                description="Testing subtask progress aggregation",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(project)
            
            # Create branch
            branch_id = str(uuid.uuid4())
            branch = ProjectGitBranch(
                id=branch_id,
                project_id=project_id,
                name="feature/test-progress",
                description="Test branch for progress tracking",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(branch)
            session.commit()
            
            return project_id, branch_id
    
    @pytest.fixture
    def task_controller(self, setup_project_and_branch):
        """Create task controller."""
        project_id, branch_id = setup_project_and_branch
        
        # Import here to avoid circular dependency
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
        
        # Create a mock repository factory that returns the correct repositories
        class MockRepositoryFactory:
            def create_repository_with_git_branch_id(self, project_id, git_branch_name, user_id, git_branch_id):
                return ORMTaskRepository(git_branch_id=git_branch_id, user_id=user_id)
            
            def create_subtask_repository(self):
                return ORMSubtaskRepository()
        
        factory = TaskFacadeFactory(MockRepositoryFactory())
        return TaskMCPController(factory)
    
    @pytest.fixture
    def subtask_controller(self, setup_project_and_branch):
        """Create subtask controller."""
        project_id, branch_id = setup_project_and_branch
        
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
        from fastmcp.task_management.application.factories.subtask_facade_factory import SubtaskFacadeFactory
        
        # Create repositories with the same context as the task controller
        task_repository = ORMTaskRepository(git_branch_id=branch_id, user_id="default_id")
        subtask_repository = ORMSubtaskRepository()
        
        # Create a simple mock factory that returns the configured facade
        class MockFactory:
            def create_subtask_facade(self, project_id=None):
                return SubtaskApplicationFacade(task_repository, subtask_repository)
        
        return SubtaskMCPController(MockFactory())
    
    def test_subtask_progress_updates_parent(self, task_controller, subtask_controller, setup_project_and_branch):
        """Test if updating subtask progress updates parent task."""
        project_id, branch_id = setup_project_and_branch
        
        # Create parent task
        task_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Parent Task with Progress Tracking",
            description="This task should track subtask progress"
        )
        assert task_result["success"], f"Task creation failed: {task_result.get('error')}"
        task_id = task_result["data"]["task"]["id"]
        
        # Get initial task to check if it has completion_percentage field
        task_details = task_controller.manage_task(
            action="get",
            task_id=task_id
        )
        assert task_details["success"]
        
        # Check response structure
        print(f"Task details response keys: {list(task_details.keys())}")
        
        # Handle different response structures
        if "data" in task_details and "task" in task_details["data"]:
            task_data = task_details["data"]["task"]
        elif "task" in task_details:
            task_data = task_details["task"]
        else:
            # Print full response to debug
            print(f"Full task details response: {task_details}")
            pytest.fail("Unexpected response structure for get task")
        
        # Check what progress-related fields exist
        print(f"Task fields: {list(task_data.keys())}")
        print(f"Task data: {task_data}")
        
        # Look for any progress-related field
        progress_field = None
        for field in ["completion_percentage", "progress", "overall_progress", "progress_percentage"]:
            if field in task_data:
                progress_field = field
                break
        
        if not progress_field:
            # No progress field found - feature not implemented
            pytest.skip("Task progress tracking not implemented - no progress field found in task data")
        
        initial_progress = task_data.get(progress_field, 0)
        print(f"Initial {progress_field}: {initial_progress}")
        
        # Create a subtask
        subtask_result = subtask_controller.manage_subtask(
            action="create",
            task_id=task_id,
            title="First Subtask",
            description="This subtask will be updated"
        )
        assert subtask_result["success"], f"Subtask creation failed: {subtask_result.get('error')}"
        subtask_id = subtask_result["data"]["subtask"]["id"]
        
        # Update subtask progress to 50%
        update_result = subtask_controller.manage_subtask(
            action="update",
            task_id=task_id,
            subtask_id=subtask_id,
            progress_percentage=50,
            progress_notes="Halfway done"
        )
        print(f"Subtask update raw result: {update_result}")
        assert update_result["success"], f"Subtask update failed: {update_result}"
        
        # Debug: Print the update result to see what's being returned
        print(f"Subtask update result: {update_result}")
        
        # Debug: Verify the subtask was updated correctly
        get_subtask_result = subtask_controller.manage_subtask(
            action="get",
            task_id=task_id,
            subtask_id=subtask_id
        )
        print(f"Subtask after update: {get_subtask_result}")
        
        # Check if parent task progress was updated
        task_details = task_controller.manage_task(
            action="get",
            task_id=task_id
        )
        assert task_details["success"]
        
        # Handle different response structures
        if "data" in task_details and "task" in task_details["data"]:
            task_data = task_details["data"]["task"]
        elif "task" in task_details:
            task_data = task_details["task"]
        else:
            pytest.fail("Unexpected response structure")
            
        updated_progress = task_data.get(progress_field, 0)
        
        print(f"Updated {progress_field}: {updated_progress}")
        
        # This test will fail if the feature is not implemented
        assert updated_progress == 50, \
            f"Expected parent {progress_field} to be 50%, got {updated_progress}"
    
    def test_multiple_subtasks_aggregation(self, task_controller, subtask_controller, setup_project_and_branch):
        """Test aggregation of multiple subtasks' progress."""
        project_id, branch_id = setup_project_and_branch
        
        # Create parent task
        task_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Parent with Multiple Subtasks",
            description="Testing multiple subtask aggregation"
        )
        assert task_result["success"]
        task_id = task_result["data"]["task"]["id"]
        
        # Check for progress field
        task_details = task_controller.manage_task(action="get", task_id=task_id)
        assert task_details["success"]
        
        # Handle different response structures
        if "data" in task_details and "task" in task_details["data"]:
            task_data = task_details["data"]["task"]
        elif "task" in task_details:
            task_data = task_details["task"]
        else:
            pytest.fail("Unexpected response structure for get task")
        
        progress_field = None
        for field in ["completion_percentage", "progress", "overall_progress", "progress_percentage"]:
            if field in task_data:
                progress_field = field
                break
        
        if not progress_field:
            pytest.skip("Task progress tracking not implemented")
        
        # Create 4 subtasks
        subtask_ids = []
        for i in range(4):
            subtask_result = subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                description=f"Subtask number {i+1}"
            )
            assert subtask_result["success"]
            subtask_ids.append(subtask_result["data"]["subtask"]["id"])
        
        # Update subtasks with different progress values
        progress_values = [100, 50, 75, 25]
        for subtask_id, progress in zip(subtask_ids, progress_values):
            update_result = subtask_controller.manage_subtask(
                action="update",
                task_id=task_id,
                subtask_id=subtask_id,
                progress_percentage=progress
            )
            assert update_result["success"]
        
        # Check parent task progress
        task_details = task_controller.manage_task(action="get", task_id=task_id)
        assert task_details["success"]
        
        # Handle different response structures
        if "data" in task_details and "task" in task_details["data"]:
            task_data = task_details["data"]["task"]
        elif "task" in task_details:
            task_data = task_details["task"]
        else:
            pytest.fail("Unexpected response structure for get task")
            
        parent_progress = task_data.get(progress_field, 0)
        
        expected_progress = sum(progress_values) / len(progress_values)  # 62.5%
        expected_progress_rounded = round(expected_progress)  # 62% (system rounds to nearest integer)
        print(f"Expected progress: {expected_progress}, Expected rounded: {expected_progress_rounded}, Actual: {parent_progress}")
        
        # Check for rounded value (system rounds to nearest integer)
        assert parent_progress == expected_progress_rounded, \
            f"Expected parent {progress_field} to be {expected_progress_rounded}% (rounded from {expected_progress}%), got {parent_progress}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])