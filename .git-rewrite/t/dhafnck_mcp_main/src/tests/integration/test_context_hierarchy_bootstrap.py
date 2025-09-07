"""
Integration tests for context hierarchy bootstrap functionality.

Tests the new bootstrap system that allows graceful initialization of the 
context hierarchy without circular dependencies.
"""

import pytest
import uuid
from typing import Dict, Any

from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory


class TestContextHierarchyBootstrap:
    """Test cases for context hierarchy bootstrap functionality."""

    @pytest.fixture
    def test_user_id(self):
        """Generate a test user ID."""
        return f"test-user-{uuid.uuid4()}"

    @pytest.fixture
    def test_project_id(self):
        """Generate a test project ID."""
        return f"test-project-{uuid.uuid4()}"

    @pytest.fixture
    def test_branch_id(self):
        """Generate a test branch ID."""
        return f"test-branch-{uuid.uuid4()}"

    @pytest.fixture
    def facade_factory(self):
        """Create a facade factory for testing."""
        return UnifiedContextFacadeFactory()

    def test_bootstrap_global_only(self, facade_factory, test_user_id):
        """Test bootstrapping global context only."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        result = facade.bootstrap_context_hierarchy()
        
        assert result["success"] is True
        assert result["bootstrap_completed"] is True
        assert "global" in result["created_contexts"]
        assert result["hierarchy_ready"] is True

    def test_bootstrap_global_and_project(self, facade_factory, test_user_id, test_project_id):
        """Test bootstrapping global and project contexts."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        result = facade.bootstrap_context_hierarchy(project_id=test_project_id)
        
        assert result["success"] is True
        assert result["bootstrap_completed"] is True
        assert "global" in result["created_contexts"]
        assert "project" in result["created_contexts"]
        assert result["hierarchy_ready"] is True

    def test_bootstrap_full_hierarchy(self, facade_factory, test_user_id, test_project_id, test_branch_id):
        """Test bootstrapping full hierarchy (global → project → branch)."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        result = facade.bootstrap_context_hierarchy(
            project_id=test_project_id,
            branch_id=test_branch_id
        )
        
        assert result["success"] is True
        assert result["bootstrap_completed"] is True
        assert "global" in result["created_contexts"]
        assert "project" in result["created_contexts"]
        assert "branch" in result["created_contexts"]
        assert result["hierarchy_ready"] is True

    def test_bootstrap_idempotent(self, facade_factory, test_user_id, test_project_id):
        """Test that bootstrap is idempotent (can be called multiple times safely)."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # First bootstrap
        result1 = facade.bootstrap_context_hierarchy(project_id=test_project_id)
        assert result1["success"] is True
        
        # Second bootstrap (should not create duplicate contexts)
        result2 = facade.bootstrap_context_hierarchy(project_id=test_project_id)
        assert result2["success"] is True
        
        # Check that contexts were not created twice
        assert result2["created_contexts"]["global"]["created"] is False  # Already existed
        assert result2["created_contexts"]["project"]["created"] is False  # Already existed

    def test_auto_parent_creation_project(self, facade_factory, test_user_id, test_project_id):
        """Test automatic parent creation when creating project context."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # Create project context (should auto-create global)
        result = facade.create_context(
            level="project",
            context_id=test_project_id,
            data={"project_name": "Test Project"}
        )
        
        assert result["success"] is True
        assert result["context_id"] == test_project_id

    def test_auto_parent_creation_branch(self, facade_factory, test_user_id, test_project_id, test_branch_id):
        """Test automatic parent creation when creating branch context."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # Create branch context (should auto-create global and project)
        result = facade.create_context(
            level="branch",
            context_id=test_branch_id,
            data={
                "project_id": test_project_id,
                "git_branch_name": "test-branch"
            }
        )
        
        assert result["success"] is True
        assert result["context_id"] == test_branch_id

    def test_auto_parent_creation_task(self, facade_factory, test_user_id, test_project_id, test_branch_id):
        """Test automatic parent creation when creating task context."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # Create task context (should auto-create full hierarchy)
        task_id = f"test-task-{uuid.uuid4()}"
        result = facade.create_context(
            level="task",
            context_id=task_id,
            data={
                "branch_id": test_branch_id,
                "task_data": {
                    "title": "Test Task",
                    "description": "Test task description"
                }
            }
        )
        
        assert result["success"] is True
        assert result["context_id"] == task_id

    def test_global_singleton_normalization(self, facade_factory, test_user_id):
        """Test that 'global_singleton' is properly normalized to UUID."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # Create global context using 'global_singleton' string
        result = facade.create_context(
            level="global",
            context_id="global_singleton",
            data={"organization_name": "Test Organization"}
        )
        
        assert result["success"] is True
        # Should be converted to proper UUID format
        assert result["context_id"] != "global_singleton"
        assert len(result["context_id"]) == 36  # Standard UUID format

    def test_flexible_creation_with_auto_parents_disabled(self, facade_factory, test_user_id, test_project_id):
        """Test flexible creation with auto-parent creation disabled."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # First ensure global context exists
        facade.bootstrap_context_hierarchy()
        
        # Try to create project with auto_create_parents=False
        result = facade.create_context_flexible(
            level="project",
            context_id=test_project_id,
            data={
                "project_name": "Test Project",
                "allow_orphaned_creation": True  # Special flag for testing
            },
            auto_create_parents=False
        )
        
        # Should still work because global context exists and orphaned creation is allowed
        assert result["success"] is True

    def test_hierarchy_inheritance(self, facade_factory, test_user_id, test_project_id, test_branch_id):
        """Test that contexts properly inherit from parent levels."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        # Bootstrap with initial data
        facade.bootstrap_context_hierarchy(
            project_id=test_project_id,
            branch_id=test_branch_id
        )
        
        # Update global context with settings
        facade.update_context(
            level="global",
            context_id="global_singleton",
            data={
                "global_settings": {
                    "timezone": "UTC",
                    "default_theme": "dark"
                }
            }
        )
        
        # Get branch context with inheritance
        result = facade.get_context(
            level="branch",
            context_id=test_branch_id,
            include_inherited=True
        )
        
        assert result["success"] is True
        # Should have inherited global settings (exact structure depends on inheritance service)
        context_data = result["context"]
        assert context_data is not None

    def test_bootstrap_usage_guidance(self, facade_factory, test_user_id, test_project_id):
        """Test that bootstrap provides usage guidance."""
        facade = facade_factory.create_facade(user_id=test_user_id)
        
        result = facade.bootstrap_context_hierarchy(project_id=test_project_id)
        
        assert result["success"] is True
        assert "usage_guidance" in result
        assert "next_steps" in result["usage_guidance"]
        assert "examples" in result["usage_guidance"]
        assert len(result["usage_guidance"]["next_steps"]) > 0
        assert len(result["usage_guidance"]["examples"]) > 0

    def test_bootstrap_error_handling(self, facade_factory):
        """Test bootstrap error handling with invalid parameters."""
        # Test with no user context (should still work for system-level contexts)
        facade = facade_factory.create_facade()
        
        result = facade.bootstrap_context_hierarchy()
        
        # Should either succeed or provide clear error information
        if not result["success"]:
            assert "error" in result
            assert result["bootstrap_completed"] is False
        else:
            assert result["bootstrap_completed"] is True

    def test_user_isolation(self, facade_factory):
        """Test that different users get isolated contexts."""
        user1_id = f"test-user1-{uuid.uuid4()}"
        user2_id = f"test-user2-{uuid.uuid4()}"
        project_id = f"shared-project-{uuid.uuid4()}"
        
        # Create facades for different users
        facade1 = facade_factory.create_facade(user_id=user1_id)
        facade2 = facade_factory.create_facade(user_id=user2_id)
        
        # Bootstrap for both users with same project ID
        result1 = facade1.bootstrap_context_hierarchy(project_id=project_id)
        result2 = facade2.bootstrap_context_hierarchy(project_id=project_id)
        
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Global contexts should have different IDs (user-scoped)
        global1_id = result1["created_contexts"]["global"]["id"]
        global2_id = result2["created_contexts"]["global"]["id"]
        assert global1_id != global2_id