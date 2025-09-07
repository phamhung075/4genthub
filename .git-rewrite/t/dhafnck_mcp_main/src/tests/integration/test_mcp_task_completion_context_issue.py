"""Test to reproduce the MCP task completion context issue.

This test reproduces the exact scenario described by the user:
1. Create task via MCP: manage_task(action="create", git_branch_id="branch-id", title="Test Task")
2. Complete task via MCP: manage_task(action="complete", task_id="task-id", completion_summary="Done")
3. Should NOT fail with "Task completion requires hierarchical context to be created first"
"""

import pytest
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.interface.controllers.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.factories.project_facade_factory import ProjectFacadeFactory
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.project_repository_factory import ProjectRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory
from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import GlobalContext as GlobalContextModel


class TestMCPTaskCompletionContextIssue:
    
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

    """Test task completion context requirement via MCP controller interface."""
    
    @pytest.fixture
    def controllers(self):
        """Set up MCP controllers for testing."""
        # Ensure global context exists
        with get_session() as session:
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
        
        # Create repository factories and controllers
        task_repo_factory = TaskRepositoryFactory()
        subtask_repo_factory = SubtaskRepositoryFactory()
        project_repo_factory = ProjectRepositoryFactory()
        branch_repo_factory = GitBranchRepositoryFactory()
        
        task_controller = TaskMCPController(TaskFacadeFactory(task_repo_factory, subtask_repo_factory))
        project_controller = ProjectMCPController(ProjectFacadeFactory(project_repo_factory))
        branch_controller = GitBranchMCPController(GitBranchFacadeFactory(branch_repo_factory))
        
        return {
            "task": task_controller,
            "project": project_controller,
            "branch": branch_controller
        }
    
    def test_reproduce_mcp_context_requirement_issue(self, controllers):
        """Reproduce the exact issue described by the user via MCP interface.
        
        Steps:
        1. Create task: manage_task(action="create", git_branch_id="branch-id", title="Test Task")
        2. Complete task: manage_task(action="complete", task_id="task-id", completion_summary="Done")
        3. Should succeed, NOT fail with context error
        """
        # Step 1: Create project and branch to get a valid git_branch_id
        project_name = f"test_project_{uuid.uuid4().hex[:8]}"
        project_result = controllers["project"].manage_project(
            action="create",
            name=project_name,
            description="Test project for MCP context issue"
        )
        assert project_result["success"], f"Project creation failed: {project_result.get('error')}"
        project_id = project_result["project"]["id"]
        
        branch_name = f"test_branch_{uuid.uuid4().hex[:8]}"
        branch_result = controllers["branch"].manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name=branch_name,
            git_branch_description="Test branch for MCP context issue"
        )
        assert branch_result["success"], f"Branch creation failed: {branch_result.get('error')}"
        branch_id = branch_result["git_branch"]["id"]
        
        # Step 2: Create task via MCP interface (as user described)
        print(f"Creating task with git_branch_id: {branch_id}")
        task_result = controllers["task"].manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Test Task",
            description="Test task for context requirement issue"
        )
        print(f"Task creation result: {task_result['success']}")
        assert task_result["success"], f"Task creation failed: {task_result.get('error')}"
        
        # Extract task ID from standardized response
        task_id = task_result["data"]["task"]["id"]
        print(f"Created task with ID: {task_id}")
        
        # Verify task has no context_id initially (this is what causes the issue)
        task_data = task_result["data"]["task"]
        print(f"Task context_id after creation: {task_data.get('context_id')}")
        print(f"Task context_available: {task_data.get('context_available', False)}")
        
        # Step 3: Complete task via MCP interface (as user described) 
        # THIS should NOT fail with "Task completion requires hierarchical context to be created first"
        print(f"Attempting to complete task {task_id}")
        complete_result = controllers["task"].manage_task(
            action="complete",
            task_id=task_id,
            completion_summary="Task completed successfully",
            testing_notes="Testing MCP context requirement issue"
        )
        
        # Print detailed error information if it fails
        if not complete_result.get("success"):
            print(f"FAILURE DETAILS:")
            print(f"  Error: {complete_result.get('error')}")
            print(f"  Message: {complete_result.get('message')}")
            print(f"  Error Code: {complete_result.get('error_code')}")
            print(f"  Full result: {complete_result}")
        
        # This is the critical assertion - should NOT fail with context error
        assert complete_result["success"], f"Task completion failed with context error: {complete_result.get('error', complete_result.get('message'))}"
        assert complete_result["status"] == "done"
        
        print("✅ Task completion succeeded - context issue resolved!")
    
    def test_mcp_task_completion_no_contexts_exist(self, controllers):
        """Test MCP task completion when no contexts exist at all.
        
        This is a more aggressive test where we ensure NO contexts exist
        and verify that auto-creation works through the MCP interface.
        """
        # Create minimal project and branch without any contexts
        project_name = f"minimal_project_{uuid.uuid4().hex[:8]}"
        project_result = controllers["project"].manage_project(
            action="create",
            name=project_name,
            description="Minimal project with no contexts"
        )
        assert project_result["success"], f"Project creation failed: {project_result}"
        project_id = project_result["project"]["id"]
        
        branch_name = f"minimal_branch_{uuid.uuid4().hex[:8]}"
        branch_result = controllers["branch"].manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name=branch_name,
            git_branch_description="Minimal branch with no contexts"
        )
        assert branch_result["success"], f"Branch creation failed: {branch_result}"
        branch_id = branch_result["git_branch"]["id"]
        
        # Create task with NO pre-existing contexts
        task_result = controllers["task"].manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Minimal Test Task",
            description="Task with no pre-existing contexts"
        )
        assert task_result["success"], f"Task creation failed: {task_result}"
        task_id = task_result["data"]["task"]["id"]
        
        # Verify no context exists initially
        task_data = task_result["data"]["task"]
        initial_context_available = task_data.get("context_available", False)
        print(f"Initial context available: {initial_context_available}")
        
        # Complete task - should auto-create entire hierarchy and succeed
        complete_result = controllers["task"].manage_task(
            action="complete",
            task_id=task_id,
            completion_summary="Minimal task completed with auto-context creation"
        )
        
        # Should succeed without context errors
        if not complete_result.get("success"):
            print(f"Completion failed: {complete_result}")
        
        assert complete_result["success"], f"Minimal task completion failed: {complete_result}"
        assert complete_result["status"] == "done"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])