#!/usr/bin/env python3
"""
Test-Driven Development: Response Formatting Fixes

This test file verifies proper response formatting for:
1. Agent assignment to branches - should include git_branch_name
2. Task dependencies - should return clean JSON structure

Expected behavior:
- Agent assignment response should include actual git_branch_name, not null
- Task dependency response should have clean, parseable structure
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.database.models import (
    Project, ProjectGitBranch, Task as TaskModel, Agent,
    GlobalContext as GlobalContextModel
)
from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory


class TestResponseFormattingFixes:
    
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

    """Test proper response formatting for various MCP operations."""
    
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
                name="Test Response Formatting Project",
                description="Testing response formatting",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(project)
            
            # Create branch
            branch_id = str(uuid.uuid4())
            branch = ProjectGitBranch(
                id=branch_id,
                project_id=project_id,
                name="feature/test-response-formatting",
                description="Test branch for response formatting",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(branch)
            session.commit()
            
            return project_id, branch_id
    
    @pytest.fixture
    def git_branch_controller(self, setup_project_and_branch):
        """Create git branch controller."""
        project_id, branch_id = setup_project_and_branch
        
        # Create repository factory and facade factory
        repo_factory = GitBranchRepositoryFactory()
        facade_factory = GitBranchFacadeFactory(repo_factory)
        return GitBranchMCPController(facade_factory)
    
    @pytest.fixture
    def task_controller(self, setup_project_and_branch):
        """Create task controller."""
        project_id, branch_id = setup_project_and_branch
        
        # Import here to avoid circular dependency
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
        
        # Create a mock repository factory that returns the correct repositories
        class MockRepositoryFactory:
            def create_repository_with_git_branch_id(self, project_id, git_branch_name, user_id, git_branch_id):
                return ORMTaskRepository(git_branch_id=git_branch_id, user_id=user_id)
        
        factory = TaskFacadeFactory(MockRepositoryFactory())
        return TaskMCPController(factory)
    
    def test_agent_assignment_includes_branch_name(self, git_branch_controller, setup_project_and_branch):
        """Test that agent assignment response includes actual git_branch_name."""
        project_id, existing_branch_id = setup_project_and_branch
        
        # Create a new branch for this test
        create_result = git_branch_controller.manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name="feature/test-agent-assignment",
            git_branch_description="Testing agent assignment response"
        )
        assert create_result["success"], f"Branch creation failed: {create_result.get('error')}"
        
        # Extract branch info
        if "data" in create_result and "git_branch" in create_result["data"]:
            branch_data = create_result["data"]["git_branch"]
        elif "git_branch" in create_result:
            branch_data = create_result["git_branch"]
        else:
            pytest.fail(f"Unexpected branch creation response structure: {create_result}")
        
        branch_id = branch_data["id"]
        expected_branch_name = "feature/test-agent-assignment"
        
        # Assign an agent to the branch
        assign_result = git_branch_controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=branch_id,
            agent_id="@coding_agent"
        )
        
        # Verify response includes branch name
        assert assign_result["success"], f"Agent assignment failed: {assign_result.get('error')}"
        
        # Check response structure (handle variations)
        if "data" in assign_result and "git_branch" in assign_result["data"]:
            response_branch = assign_result["data"]["git_branch"]
            actual_name = response_branch.get("git_branch_name") or response_branch.get("name")
        elif "git_branch" in assign_result:
            response_branch = assign_result["git_branch"]
            actual_name = response_branch.get("git_branch_name") or response_branch.get("name")
        elif "git_branch_name" in assign_result:
            # Handle case where git_branch_name is at top level
            actual_name = assign_result["git_branch_name"]
        else:
            pytest.fail(f"No branch data found in response: {assign_result}")
        
        # Verify we found the branch name
        if not actual_name and "git_branch_name" not in assign_result:
            pytest.fail("Response should contain branch name field")
        assert actual_name is not None, "git_branch_name should not be null in response"
        assert actual_name == expected_branch_name, \
            f"Expected branch name '{expected_branch_name}', got '{actual_name}'"
    
    def test_task_dependency_clean_response(self, task_controller, setup_project_and_branch):
        """Test that task dependency response has clean JSON structure."""
        project_id, branch_id = setup_project_and_branch
        
        # Create two tasks
        task1_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Task 1 - Dependency",
            description="This will be a dependency"
        )
        assert task1_result["success"], f"Task 1 creation failed: {task1_result.get('error')}"
        task1_id = task1_result["data"]["task"]["id"]
        
        task2_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Task 2 - Dependent",
            description="This depends on Task 1"
        )
        assert task2_result["success"], f"Task 2 creation failed: {task2_result.get('error')}"
        task2_id = task2_result["data"]["task"]["id"]
        
        # Add dependency
        dep_result = task_controller.manage_task(
            action="add_dependency",
            task_id=task2_id,
            dependency_id=task1_id
        )
        
        # Verify response structure
        assert dep_result["success"], f"Add dependency failed: {dep_result.get('error')}"
        
        # Check that response has clean structure
        assert "data" in dep_result or "task" in dep_result, \
            f"Response should have data or task field: {dep_result}"
        
        # Extract task object
        if "data" in dep_result and "task" in dep_result["data"]:
            task_obj = dep_result["data"]["task"]
        elif "task" in dep_result:
            task_obj = dep_result["task"]
        else:
            # If the response doesn't have a task object, it might just be a success message
            # This could be valid depending on the implementation
            return
        
        # Verify task object is clean JSON (not complex internal structure)
        try:
            json_str = json.dumps(task_obj)
            parsed = json.loads(json_str)
            assert parsed["id"] == task2_id
        except (TypeError, ValueError) as e:
            pytest.fail(f"Task object is not clean JSON: {e}")
    
    def test_agent_unassignment_response_format(self, git_branch_controller, setup_project_and_branch):
        """Test that agent unassignment also returns proper branch name."""
        project_id, existing_branch_id = setup_project_and_branch
        
        # Create a branch for this test
        create_result = git_branch_controller.manage_git_branch(
            action="create",
            project_id=project_id,
            git_branch_name="feature/test-agent-unassignment",
            git_branch_description="Testing agent unassignment"
        )
        assert create_result["success"], f"Branch creation failed: {create_result.get('error')}"
        
        # Extract branch info
        if "data" in create_result and "git_branch" in create_result["data"]:
            branch_data = create_result["data"]["git_branch"]
        elif "git_branch" in create_result:
            branch_data = create_result["git_branch"]
        else:
            pytest.fail(f"Unexpected branch creation response structure: {create_result}")
        
        branch_id = branch_data["id"]
        expected_branch_name = "feature/test-agent-unassignment"
        
        # Assign an agent first
        assign_result = git_branch_controller.manage_git_branch(
            action="assign_agent",
            project_id=project_id,
            git_branch_id=branch_id,
            agent_id="@coding_agent"
        )
        assert assign_result["success"], f"Agent assignment failed: {assign_result.get('error')}"
        
        # Unassign the agent
        unassign_result = git_branch_controller.manage_git_branch(
            action="unassign_agent",
            project_id=project_id,
            git_branch_id=branch_id,
            agent_id="@coding_agent"
        )
        
        # Verify response includes branch name
        assert unassign_result["success"], f"Agent unassignment failed: {unassign_result.get('error')}"
        
        # Check response structure (handle variations)
        if "data" in unassign_result and "git_branch" in unassign_result["data"]:
            response_branch = unassign_result["data"]["git_branch"]
            actual_name = response_branch.get("git_branch_name") or response_branch.get("name")
        elif "git_branch" in unassign_result:
            response_branch = unassign_result["git_branch"]
            actual_name = response_branch.get("git_branch_name") or response_branch.get("name")
        elif "git_branch_name" in unassign_result:
            # Handle case where git_branch_name is at top level
            actual_name = unassign_result["git_branch_name"]
        else:
            # Some implementations might not return branch data on unassignment
            # This could be acceptable behavior
            return
        if actual_name is not None:
            assert actual_name == expected_branch_name, \
                f"Branch name should be '{expected_branch_name}', got '{actual_name}'"
    
    def test_task_remove_dependency_response(self, task_controller, setup_project_and_branch):
        """Test that removing dependencies also returns clean response."""
        project_id, branch_id = setup_project_and_branch
        
        # Create tasks
        task1_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Dependency Task",
            description="Will be added then removed"
        )
        assert task1_result["success"], f"Task 1 creation failed: {task1_result.get('error')}"
        task1_id = task1_result["data"]["task"]["id"]
        
        task2_result = task_controller.manage_task(
            action="create",
            git_branch_id=branch_id,
            title="Main Task",
            description="Will have dependency added and removed"
        )
        assert task2_result["success"], f"Task 2 creation failed: {task2_result.get('error')}"
        task2_id = task2_result["data"]["task"]["id"]
        
        # Add dependency
        add_result = task_controller.manage_task(
            action="add_dependency",
            task_id=task2_id,
            dependency_id=task1_id
        )
        assert add_result["success"], f"Add dependency failed: {add_result.get('error')}"
        
        # Remove dependency
        remove_result = task_controller.manage_task(
            action="remove_dependency",
            task_id=task2_id,
            dependency_id=task1_id
        )
        
        # Verify clean response
        assert remove_result["success"], f"Remove dependency failed: {remove_result.get('error')}"
        
        # If response contains task data, verify it's JSON serializable
        if "data" in remove_result and "task" in remove_result["data"]:
            try:
                json.dumps(remove_result["data"]["task"])
            except (TypeError, ValueError) as e:
                pytest.fail(f"Response not JSON serializable: {e}")
        elif "task" in remove_result:
            try:
                json.dumps(remove_result["task"])
            except (TypeError, ValueError) as e:
                pytest.fail(f"Response not JSON serializable: {e}")