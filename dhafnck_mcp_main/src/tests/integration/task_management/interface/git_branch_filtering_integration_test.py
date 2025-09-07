"""
Integration Test for Git Branch Task Filtering

This integration test verifies that the git branch filtering bug is fixed
by testing against the actual database and repositories.

The bug: When clicking on a git branch in the frontend sidebar, all tasks
from all branches were being displayed instead of just the tasks from the 
selected branch.

Root cause: The performance mode path in TaskApplicationFacade was not
passing the git_branch_id parameter to the optimized repository's 
list_tasks_minimal method.
"""

import pytest
import logging
import uuid
from typing import Dict, Any

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.orm.optimized_task_repository import OptimizedTaskRepository

logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestGitBranchFilteringIntegration:
    """Integration tests for git branch-specific task filtering."""
    
    def setup_method(self):
        """Set up test fixtures with real database."""
        # Create unique git branch IDs for isolation
        self.branch_a_id = str(uuid.uuid4())
        self.branch_b_id = str(uuid.uuid4()) 
        self.project_id = str(uuid.uuid4())
        self.user_id = "test-user-integration"
        
        # Get real facade via factory singleton with required dependencies
        task_repo_factory = TaskRepositoryFactory()
        subtask_repo_factory = SubtaskRepositoryFactory()
        self.facade_factory = TaskFacadeFactory.get_instance(
            repository_factory=task_repo_factory,
            subtask_repository_factory=subtask_repo_factory
        )
        self.facade = self.facade_factory.create_task_facade(user_id=self.user_id)
        
        # Create project and git branches first
        self._create_project_and_branches()
        
        # Create test data in the database
        self._create_test_data()
    
    def _create_project_and_branches(self):
        """Create project and git branches in the database."""
        from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        
        # Create a database session
        session = get_db_config().get_session()
        try:
            # Create the project
            project = Project(
                id=self.project_id,
                name=f"Test Project {self.project_id[:8]}",
                description="Integration test project",
                user_id=self.user_id
            )
            session.add(project)
            
            # Create git branch A
            branch_a = ProjectGitBranch(
                id=self.branch_a_id,
                project_id=self.project_id,
                name=f"branch-a-{self.branch_a_id[:8]}",
                description="Test branch A",
                user_id=self.user_id
            )
            session.add(branch_a)
            
            # Create git branch B
            branch_b = ProjectGitBranch(
                id=self.branch_b_id,
                project_id=self.project_id,
                name=f"branch-b-{self.branch_b_id[:8]}",
                description="Test branch B",
                user_id=self.user_id
            )
            session.add(branch_b)
            
            # Commit the changes
            session.commit()
            
            logger.info(f"Created project: {self.project_id}")
            logger.info(f"Created git branch A: {self.branch_a_id}")
            logger.info(f"Created git branch B: {self.branch_b_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create project and branches: {e}")
            raise
        finally:
            session.close()
    
    def _create_test_data(self):
        """Create test tasks in different branches."""
        # Tasks for branch A
        self.task_a1_request = CreateTaskRequest(
            git_branch_id=self.branch_a_id,
            title="Task A1 - Integration Test",
            description="Test task for branch A",
            priority="high",
            status="todo",
            user_id=self.user_id
        )
        
        self.task_a2_request = CreateTaskRequest(
            git_branch_id=self.branch_a_id,
            title="Task A2 - Integration Test",
            description="Another test task for branch A",
            priority="medium",
            status="in_progress",
            user_id=self.user_id
        )
        
        # Tasks for branch B
        self.task_b1_request = CreateTaskRequest(
            git_branch_id=self.branch_b_id,
            title="Task B1 - Integration Test",
            description="Test task for branch B",
            priority="low",
            status="todo",
            user_id=self.user_id
        )
        
        self.task_b2_request = CreateTaskRequest(
            git_branch_id=self.branch_b_id,
            title="Task B2 - Integration Test", 
            description="Another test task for branch B",
            priority="high",
            status="done",
            user_id=self.user_id
        )
        
        # Create tasks in database
        self.task_a1 = self.facade.create_task(self.task_a1_request)
        self.task_a2 = self.facade.create_task(self.task_a2_request)
        self.task_b1 = self.facade.create_task(self.task_b1_request)
        self.task_b2 = self.facade.create_task(self.task_b2_request)
        
        # Debug: Check what was actually returned
        logger.info(f"Debug - Task A1 response type: {type(self.task_a1)}")
        logger.info(f"Debug - Task A1 response: {self.task_a1}")
        
        # Check if creation was successful
        if not self.task_a1.get('success', False):
            raise RuntimeError(f"Failed to create task A1: {self.task_a1.get('error', 'Unknown error')}")
        if not self.task_a2.get('success', False):
            raise RuntimeError(f"Failed to create task A2: {self.task_a2.get('error', 'Unknown error')}")
        if not self.task_b1.get('success', False):
            raise RuntimeError(f"Failed to create task B1: {self.task_b1.get('error', 'Unknown error')}")
        if not self.task_b2.get('success', False):
            raise RuntimeError(f"Failed to create task B2: {self.task_b2.get('error', 'Unknown error')}")
        
        logger.info(f"Created test data:")
        logger.info(f"  Branch A ({self.branch_a_id}): 2 tasks")
        if 'task' in self.task_a1:
            logger.info(f"    Task A1 ID: {self.task_a1['task']['id']}")
            logger.info(f"    Task A2 ID: {self.task_a2['task']['id']}")
        else:
            logger.info(f"    Task A1 keys: {self.task_a1.keys()}")
            logger.info(f"    Task A2 keys: {self.task_a2.keys()}")
        logger.info(f"  Branch B ({self.branch_b_id}): 2 tasks")
        if 'task' in self.task_b1:
            logger.info(f"    Task B1 ID: {self.task_b1['task']['id']}")
            logger.info(f"    Task B2 ID: {self.task_b2['task']['id']}")
        else:
            logger.info(f"    Task B1 keys: {self.task_b1.keys()}")
            logger.info(f"    Task B2 keys: {self.task_b2.keys()}")
        
        # Debug: Verify tasks were created with correct git_branch_id
        logger.info(f"Task creation verification:")
        if 'task' in self.task_a1:
            logger.info(f"  Task A1 git_branch_id: {self.task_a1['task'].get('git_branch_id', 'MISSING')}")
            logger.info(f"  Task A2 git_branch_id: {self.task_a2['task'].get('git_branch_id', 'MISSING')}")
            logger.info(f"  Task B1 git_branch_id: {self.task_b1['task'].get('git_branch_id', 'MISSING')}")
            logger.info(f"  Task B2 git_branch_id: {self.task_b2['task'].get('git_branch_id', 'MISSING')}")
    
    def test_list_tasks_filters_by_branch_a(self):
        """Test that listing tasks for branch A returns only branch A tasks."""
        # Create list request for branch A
        request = ListTasksRequest(
            git_branch_id=self.branch_a_id,
            limit=50
        )
        
        # Execute list operation
        result = self.facade.list_tasks(request)
        
        # Assertions
        assert result["success"] is True, "List operation should succeed"
        assert "tasks" in result, "Result should contain tasks array"
        
        returned_tasks = result["tasks"]
        logger.info(f"Branch A returned {len(returned_tasks)} tasks")
        
        # Debug: Show what tasks were actually returned
        logger.info(f"List result debug:")
        logger.info(f"  Result keys: {list(result.keys())}")
        logger.info(f"  Success: {result.get('success')}")
        logger.info(f"  Tasks count: {len(returned_tasks)}")
        for i, task in enumerate(returned_tasks):
            logger.info(f"  Task {i+1}: {task.get('title', 'NO TITLE')} | git_branch_id: {task.get('git_branch_id', 'MISSING')}")
            
        # Also test without any filters to see if tasks exist at all
        no_filter_request = ListTasksRequest(limit=50)
        no_filter_result = self.facade.list_tasks(no_filter_request)
        no_filter_tasks = no_filter_result.get("tasks", [])
        logger.info(f"No-filter query returned {len(no_filter_tasks)} tasks:")
        for i, task in enumerate(no_filter_tasks):
            logger.info(f"  All Task {i+1}: {task.get('title', 'NO TITLE')} | git_branch_id: {task.get('git_branch_id', 'MISSING')}")
        
        # Should return exactly 2 tasks for branch A
        assert len(returned_tasks) == 2, f"Expected 2 tasks for branch A, got {len(returned_tasks)}"
        
        # All returned tasks should belong to branch A
        for task in returned_tasks:
            task_git_branch_id = task.get("git_branch_id")
            assert task_git_branch_id == self.branch_a_id, \
                f"Task {task.get('id')} has wrong branch_id: {task_git_branch_id} (expected {self.branch_a_id})"
        
        # Verify specific task titles are present
        task_titles = [task.get("title", "") for task in returned_tasks]
        assert "Task A1 - Integration Test" in task_titles, "Task A1 should be in results"
        assert "Task A2 - Integration Test" in task_titles, "Task A2 should be in results"
        
        # Verify no branch B tasks are present
        assert "Task B1 - Integration Test" not in task_titles, "Task B1 should NOT be in branch A results"
        assert "Task B2 - Integration Test" not in task_titles, "Task B2 should NOT be in branch A results"
        
        logger.info("✅ Branch A filtering test passed")
    
    def test_list_tasks_filters_by_branch_b(self):
        """Test that listing tasks for branch B returns only branch B tasks."""
        # Create list request for branch B
        request = ListTasksRequest(
            git_branch_id=self.branch_b_id,
            limit=50
        )
        
        # Execute list operation
        result = self.facade.list_tasks(request)
        
        # Assertions
        assert result["success"] is True, "List operation should succeed"
        assert "tasks" in result, "Result should contain tasks array"
        
        returned_tasks = result["tasks"]
        logger.info(f"Branch B returned {len(returned_tasks)} tasks")
        
        # Should return exactly 2 tasks for branch B
        assert len(returned_tasks) == 2, f"Expected 2 tasks for branch B, got {len(returned_tasks)}"
        
        # All returned tasks should belong to branch B
        for task in returned_tasks:
            task_git_branch_id = task.get("git_branch_id")
            assert task_git_branch_id == self.branch_b_id, \
                f"Task {task.get('id')} has wrong branch_id: {task_git_branch_id} (expected {self.branch_b_id})"
        
        # Verify specific task titles are present
        task_titles = [task.get("title", "") for task in returned_tasks]
        assert "Task B1 - Integration Test" in task_titles, "Task B1 should be in results"
        assert "Task B2 - Integration Test" in task_titles, "Task B2 should be in results"
        
        # Verify no branch A tasks are present
        assert "Task A1 - Integration Test" not in task_titles, "Task A1 should NOT be in branch B results"
        assert "Task A2 - Integration Test" not in task_titles, "Task A2 should NOT be in branch B results"
        
        logger.info("✅ Branch B filtering test passed")
    
    def test_list_tasks_without_filter_returns_all_tasks(self):
        """Test that listing without branch filter returns tasks from all branches (acceptable behavior)."""
        # Create list request without git_branch_id filter
        request = ListTasksRequest(
            limit=50
        )
        
        # Execute list operation
        result = self.facade.list_tasks(request)
        
        # Assertions
        assert result["success"] is True, "List operation should succeed"
        assert "tasks" in result, "Result should contain tasks array"
        
        returned_tasks = result["tasks"]
        logger.info(f"No filter returned {len(returned_tasks)} tasks")
        
        # Should return at least our 4 test tasks (there might be more from other tests)
        assert len(returned_tasks) >= 4, f"Expected at least 4 tasks (our test data), got {len(returned_tasks)}"
        
        # Verify our test tasks are present
        task_titles = [task.get("title", "") for task in returned_tasks]
        assert "Task A1 - Integration Test" in task_titles, "Task A1 should be in unfiltered results"
        assert "Task A2 - Integration Test" in task_titles, "Task A2 should be in unfiltered results"
        assert "Task B1 - Integration Test" in task_titles, "Task B1 should be in unfiltered results"
        assert "Task B2 - Integration Test" in task_titles, "Task B2 should be in unfiltered results"
        
        logger.info("✅ Unfiltered listing test passed")
    
    def test_optimized_repository_direct_filtering(self):
        """Test the optimized repository directly to ensure it filters correctly."""
        # Create optimized repository instances for each branch
        repo_a = OptimizedTaskRepository(git_branch_id=self.branch_a_id)
        repo_b = OptimizedTaskRepository(git_branch_id=self.branch_b_id)
        
        # Test branch A repository
        tasks_a = repo_a.list_tasks_minimal(limit=50)
        logger.info(f"Optimized repo A returned {len(tasks_a)} tasks")
        
        # Verify branch A results
        assert len(tasks_a) >= 2, f"Branch A repo should return at least 2 tasks, got {len(tasks_a)}"
        for task in tasks_a:
            assert task.get("git_branch_id") == self.branch_a_id or task.get("git_branch_id") is None, \
                f"Optimized repo A returned task with wrong branch_id: {task.get('git_branch_id')}"
        
        # Test branch B repository
        tasks_b = repo_b.list_tasks_minimal(limit=50)
        logger.info(f"Optimized repo B returned {len(tasks_b)} tasks")
        
        # Verify branch B results
        assert len(tasks_b) >= 2, f"Branch B repo should return at least 2 tasks, got {len(tasks_b)}"
        for task in tasks_b:
            assert task.get("git_branch_id") == self.branch_b_id or task.get("git_branch_id") is None, \
                f"Optimized repo B returned task with wrong branch_id: {task.get('git_branch_id')}"
        
        logger.info("✅ Optimized repository direct test passed")
    
    def test_optimized_repository_parameter_override(self):
        """Test that the git_branch_id parameter overrides repository's git_branch_id."""
        # Create repository for branch A
        repo = OptimizedTaskRepository(git_branch_id=self.branch_a_id)
        
        # Use parameter to filter by branch B (should override repository's branch A setting)
        tasks = repo.list_tasks_minimal(git_branch_id=self.branch_b_id, limit=50)
        logger.info(f"Repo with parameter override returned {len(tasks)} tasks")
        
        # Verify we get branch B tasks despite repository being initialized for branch A
        task_branch_ids = [task.get("git_branch_id") for task in tasks if task.get("git_branch_id") is not None]
        for branch_id in task_branch_ids:
            assert branch_id == self.branch_b_id, \
                f"Expected branch B tasks, got task with branch_id: {branch_id}"
        
        logger.info("✅ Repository parameter override test passed")
        
    def teardown_method(self):
        """Clean up test data."""
        try:
            # Clean up test tasks (if delete functionality exists)
            # This is optional since test database should be isolated
            logger.info("Integration test completed - test data cleanup handled by test framework")
        except Exception as e:
            logger.warning(f"Test cleanup warning: {e}")


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([
        __file__,
        "-v", "--tb=short",
        "-k", "test_list_tasks_filters_by_branch_a"  # Run specific test first
    ])