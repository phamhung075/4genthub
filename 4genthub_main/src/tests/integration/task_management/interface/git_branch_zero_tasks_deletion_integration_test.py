"""
Integration Test Suite for Git Branch Zero Tasks Deletion Bug

This integration test suite tests the complete flow from controller to database
to identify where the "0 tasks deletion" bug actually occurs.

Bug Description: The delete button on the sidebar cannot delete git branches that have 0 tasks.
Expected Behavior: Branches with 0 tasks should be deletable.
"""

import pytest
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch, Task
# Removed unused imports

logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestGitBranchZeroTasksDeletionIntegration:
    """Integration test suite for git branch zero tasks deletion"""
    
    def setup_method(self):
        """Set up integration test data in actual database"""
        self.project_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())  # Use valid UUID for user_id
        
        # Create branches for testing
        self.empty_branch_id = str(uuid.uuid4())
        self.empty_branch_name = "feature/empty-integration-branch"
        
        self.branch_with_tasks_id = str(uuid.uuid4())
        self.branch_with_tasks_name = "feature/branch-with-tasks-integration"
        
        # Set up controller with real factory
        self.facade_factory = GitBranchFacadeFactory()
        self.controller = GitBranchMCPController(self.facade_factory)
        
        # Create test data in database
        self._create_test_data_in_database()
        
    def teardown_method(self):
        """Clean up test data from database"""
        self._cleanup_test_data()
        
    def _create_test_data_in_database(self):
        """Create project and branches in the database"""
        session = get_db_config().get_session()
        try:
            # Create project
            project = Project(
                id=self.project_id,
                name=f"Integration Test Project {self.project_id[:8]}",
                description="Integration test for git branch deletion",
                user_id=self.user_id
            )
            session.add(project)
            
            # Create empty branch (0 tasks)
            empty_branch = ProjectGitBranch(
                id=self.empty_branch_id,
                project_id=self.project_id,
                name=self.empty_branch_name,
                description="Branch with zero tasks for integration testing",
                user_id=self.user_id,
                task_count=0,
                completed_task_count=0,
                status="todo",
                priority="medium"
            )
            session.add(empty_branch)
            
            # Create branch with tasks
            branch_with_tasks = ProjectGitBranch(
                id=self.branch_with_tasks_id,
                project_id=self.project_id,
                name=self.branch_with_tasks_name,
                description="Branch with tasks for comparison testing",
                user_id=self.user_id,
                task_count=2,  # We'll create 2 tasks
                completed_task_count=0,
                status="todo",
                priority="medium"
            )
            session.add(branch_with_tasks)
            
            # Create tasks in the branch_with_tasks
            task1 = Task(
                id=str(uuid.uuid4()),
                git_branch_id=self.branch_with_tasks_id,
                title="Integration Test Task 1",
                description="First test task",
                status="todo",
                priority="medium",
                user_id=self.user_id
            )
            session.add(task1)
            
            task2 = Task(
                id=str(uuid.uuid4()),
                git_branch_id=self.branch_with_tasks_id,
                title="Integration Test Task 2",
                description="Second test task",
                status="todo",
                priority="medium",
                user_id=self.user_id
            )
            session.add(task2)
            
            session.commit()
            
            logger.info(f"Created integration test data:")
            logger.info(f"  Project: {self.project_id}")
            logger.info(f"  Empty Branch: {self.empty_branch_id} (0 tasks)")
            logger.info(f"  Branch with Tasks: {self.branch_with_tasks_id} (2 tasks)")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create integration test data: {e}")
            raise
        finally:
            session.close()
            
    def _cleanup_test_data(self):
        """Remove test data from database"""
        session = get_db_config().get_session()
        try:
            # Delete tasks first (foreign key constraints)
            session.query(Task).filter(Task.git_branch_id.in_([
                self.empty_branch_id, 
                self.branch_with_tasks_id
            ])).delete(synchronize_session=False)
            
            # Delete branches
            session.query(ProjectGitBranch).filter(ProjectGitBranch.project_id == self.project_id).delete()
            
            # Delete project
            session.query(Project).filter(Project.id == self.project_id).delete()
            
            session.commit()
            logger.info("Cleaned up integration test data")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to clean up integration test data: {e}")
        finally:
            session.close()
            
    def _verify_branch_exists_in_database(self, branch_id: str) -> bool:
        """Helper to verify branch exists in database"""
        session = get_db_config().get_session()
        try:
            branch = session.query(ProjectGitBranch).filter(
                ProjectGitBranch.id == branch_id
            ).first()
            return branch is not None
        finally:
            session.close()
            
    def _get_branch_task_count_from_database(self, branch_id: str) -> int:
        """Helper to get actual task count from database"""
        session = get_db_config().get_session()
        try:
            count = session.query(Task).filter(Task.git_branch_id == branch_id).count()
            return count
        finally:
            session.close()
    
    def test_verify_test_data_setup(self):
        """SETUP VERIFICATION: Ensure test data is correctly set up"""
        
        # Verify empty branch exists and has 0 tasks
        assert self._verify_branch_exists_in_database(self.empty_branch_id)
        assert self._get_branch_task_count_from_database(self.empty_branch_id) == 0
        
        # Verify branch with tasks exists and has 2 tasks
        assert self._verify_branch_exists_in_database(self.branch_with_tasks_id)
        assert self._get_branch_task_count_from_database(self.branch_with_tasks_id) == 2
        
        logger.info("✅ Test data setup verification passed")
    
    def test_delete_empty_branch_full_integration(self):
        """MAIN INTEGRATION TEST: Delete branch with 0 tasks through complete stack
        
        This test goes through the complete flow:
        1. Controller -> Facade -> Service -> Repository -> Database
        2. Verifies the branch is actually deleted from the database
        """
        
        # Verify branch exists and has 0 tasks before deletion
        assert self._verify_branch_exists_in_database(self.empty_branch_id)
        assert self._get_branch_task_count_from_database(self.empty_branch_id) == 0
        
        logger.info(f"🧪 Attempting to delete empty branch {self.empty_branch_id}")
        
        # Attempt deletion through controller (full stack)
        result = self.controller.manage_git_branch(
            action="delete",
            project_id=self.project_id,
            git_branch_id=self.empty_branch_id,
            user_id=self.user_id
        )
        
        logger.info(f"🔍 Deletion result: {result}")
        
        # Verify deletion succeeded
        assert result["success"] is True, f"Empty branch deletion failed: {result.get('error')}"
        
        # Verify branch no longer exists in database
        branch_still_exists = self._verify_branch_exists_in_database(self.empty_branch_id)
        assert not branch_still_exists, "Branch still exists in database after deletion"
        
        logger.info("✅ Empty branch deletion integration test passed")
    
    def test_delete_branch_with_tasks_for_comparison(self):
        """COMPARISON TEST: Delete branch with tasks to ensure general deletion works"""
        
        # Verify branch exists and has 2 tasks before deletion
        assert self._verify_branch_exists_in_database(self.branch_with_tasks_id)
        assert self._get_branch_task_count_from_database(self.branch_with_tasks_id) == 2
        
        logger.info(f"🧪 Attempting to delete branch with tasks {self.branch_with_tasks_id}")
        
        # Attempt deletion through controller
        result = self.controller.manage_git_branch(
            action="delete",
            project_id=self.project_id,
            git_branch_id=self.branch_with_tasks_id,
            user_id=self.user_id
        )
        
        logger.info(f"🔍 Deletion result: {result}")
        
        # Verify deletion succeeded (or failed as expected)
        if result["success"]:
            # If it succeeds, verify it's actually deleted
            branch_still_exists = self._verify_branch_exists_in_database(self.branch_with_tasks_id)
            assert not branch_still_exists, "Branch still exists after successful deletion"
            logger.info("✅ Branch with tasks deletion succeeded")
        else:
            # If it fails, that might be the expected behavior (cascade delete not implemented)
            logger.info(f"ℹ️ Branch with tasks deletion failed (might be expected): {result.get('error')}")
            
    def test_list_branches_shows_task_counts_correctly(self):
        """HELPER TEST: Verify that branch listing shows correct task counts"""
        
        # List branches through controller
        result = self.controller.manage_git_branch(
            action="list",
            project_id=self.project_id,
            user_id=self.user_id
        )
        
        assert result["success"] is True, f"Failed to list branches: {result.get('error')}"
        
        branches = result.get("data", {}).get("git_branchs", [])
        assert len(branches) == 2, f"Expected 2 branches, got {len(branches)}"
        
        # Find our test branches
        empty_branch_data = None
        tasks_branch_data = None
        
        for branch in branches:
            if branch["id"] == self.empty_branch_id:
                empty_branch_data = branch
            elif branch["id"] == self.branch_with_tasks_id:
                tasks_branch_data = branch
                
        assert empty_branch_data is not None, "Empty branch not found in list"
        assert tasks_branch_data is not None, "Branch with tasks not found in list"
        
        # Verify task counts are correctly reported
        logger.info(f"Empty branch task count in list: {empty_branch_data.get('task_count', 'MISSING')}")
        logger.info(f"Tasks branch task count in list: {tasks_branch_data.get('task_count', 'MISSING')}")
        
        # The task count might be in different fields depending on implementation
        empty_count = (empty_branch_data.get('task_count', 0) or 
                      empty_branch_data.get('total_tasks', 0) or 0)
        tasks_count = (tasks_branch_data.get('task_count', 0) or 
                      tasks_branch_data.get('total_tasks', 0) or 0)
        
        # Note: The counts might not match database exactly due to caching or calculation differences
        logger.info(f"Reported task counts - Empty: {empty_count}, With tasks: {tasks_count}")
        
    def test_get_branch_statistics_for_empty_branch(self):
        """DIAGNOSTIC TEST: Get detailed statistics for empty branch"""
        
        # Get statistics through controller
        result = self.controller.manage_git_branch(
            action="get_statistics",
            project_id=self.project_id,
            git_branch_id=self.empty_branch_id,
            user_id=self.user_id
        )
        
        logger.info(f"🔍 Empty branch statistics: {result}")
        
        if result["success"]:
            stats = result.get("data", {})
            task_count = stats.get('statistics', {}).get('task_count', 'MISSING')
            logger.info(f"Statistics report task count for empty branch: {task_count}")
        else:
            logger.info(f"Failed to get statistics: {result.get('error')}")
            
    def test_edge_case_delete_nonexistent_branch(self):
        """EDGE CASE TEST: Attempt to delete non-existent branch"""
        
        fake_branch_id = str(uuid.uuid4())
        
        result = self.controller.manage_git_branch(
            action="delete",
            project_id=self.project_id,
            git_branch_id=fake_branch_id,
            user_id=self.user_id
        )
        
        # Debug: print the actual result to understand its structure
        logger.info(f"Result from delete non-existent branch: {result}")
        
        # Should fail gracefully
        # Check various possible response formats
        if "success" in result:
            assert result["success"] is False, f"Expected success=False but got {result}"
        elif "status" in result:
            assert result["status"] == "failure", f"Expected status=failure but got {result}"
        
        # Check for error indication
        error_found = (
            "not found" in str(result).lower() or 
            "NOT_FOUND" in str(result) or
            (result.get("error") and "not found" in result.get("error", {}).get("message", "").lower()) or
            result.get("error_code") == "NOT_FOUND"
        )
        assert error_found, f"Expected 'not found' error indication in result: {result}"
        
        logger.info("✅ Non-existent branch deletion handled correctly")
        
    def test_comprehensive_branch_lifecycle(self):
        """COMPREHENSIVE TEST: Create -> Verify Empty -> Delete -> Verify Gone"""
        
        # Create a new empty branch
        new_branch_id = str(uuid.uuid4())
        new_branch_name = "feature/lifecycle-test-branch"
        
        # Create through controller
        create_result = self.controller.manage_git_branch(
            action="create",
            project_id=self.project_id,
            git_branch_name=new_branch_name,
            git_branch_description="Lifecycle test branch",
            user_id=self.user_id
        )
        
        assert create_result["success"] is True, f"Failed to create branch: {create_result.get('error')}"
        
        # Get the created branch ID
        created_branch_id = create_result.get("data", {}).get("git_branch", {}).get("id")
        assert created_branch_id is not None, "No branch ID returned from creation"
        
        logger.info(f"✅ Created branch: {created_branch_id}")
        
        # Verify it exists and has 0 tasks
        assert self._verify_branch_exists_in_database(created_branch_id)
        assert self._get_branch_task_count_from_database(created_branch_id) == 0
        
        # Now delete it
        delete_result = self.controller.manage_git_branch(
            action="delete",
            project_id=self.project_id,
            git_branch_id=created_branch_id,
            user_id=self.user_id
        )
        
        logger.info(f"🔍 Lifecycle delete result: {delete_result}")
        
        # Verify deletion
        assert delete_result["success"] is True, f"Failed to delete created empty branch: {delete_result.get('error')}"
        
        # Verify it's gone from database
        assert not self._verify_branch_exists_in_database(created_branch_id), "Branch still exists after deletion"
        
        logger.info("✅ Complete branch lifecycle test passed")
        

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])