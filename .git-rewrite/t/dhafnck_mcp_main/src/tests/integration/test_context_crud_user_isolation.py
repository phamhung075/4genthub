"""
Comprehensive test suite for Context CRUD operations with user isolation.
Tests all context layers (Global, Project, Branch, Task) with proper user UUID separation.
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.infrastructure.database.models import (
    GLOBAL_SINGLETON_UUID, 
    GlobalContext as GlobalContextModel,
    ProjectContext as ProjectContextModel,
    BranchContext as BranchContextModel,
    TaskContext as TaskContextModel,
    Project,
    ProjectGitBranch,
    Task
)
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy.orm import Session


class TestContextCRUDUserIsolation:
    """Test suite for context CRUD operations with user isolation."""
    
    @pytest.fixture
    def user_id_1(self):
        """First test user UUID."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def user_id_2(self):
        """Second test user UUID for isolation testing."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def db_session(self):
        """Get database session for test setup."""
        db_config = get_db_config()
        with db_config.get_session() as session:
            yield session
    
    @pytest.fixture
    def setup_project_hierarchy(self, db_session: Session, user_id_1: str):
        """Setup project hierarchy for testing."""
        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="Test project for context CRUD",
            user_id=user_id_1
        )
        db_session.add(project)
        
        # Create git branch
        git_branch = ProjectGitBranch(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name="feature/test-context",
            description="Test branch for context CRUD",
            user_id=user_id_1
        )
        db_session.add(git_branch)
        
        # Create task
        task = Task(
            id=str(uuid.uuid4()),
            title="Test Task",
            description="Test task for context CRUD",
            status="todo",
            git_branch_id=git_branch.id,
            user_id=user_id_1
        )
        db_session.add(task)
        
        db_session.commit()
        
        return {
            "project_id": project.id,
            "git_branch_id": git_branch.id,
            "task_id": task.id
        }
    
    @pytest.fixture
    def facade_factory(self):
        """Create facade factory."""
        return UnifiedContextFacadeFactory()
    
    def test_global_context_user_isolation(self, facade_factory, user_id_1, user_id_2):
        """Test that global contexts are properly isolated by user."""
        # Create facade for user 1
        facade_user1 = facade_factory.create_facade(user_id=user_id_1)
        
        # Create global context for user 1
        result1 = facade_user1.create_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_1}",  # User-specific global ID
            data={
                "global_settings": {
                    "autonomous_rules": {"user1_rule": "value1"},
                    "security_policies": {"user1_policy": "policy1"}
                }
            }
        )
        assert result1["success"] is True
        print(f"DEBUG: result1 = {result1}")
        print(f"DEBUG: context keys = {result1.get('context', {}).keys() if result1.get('context') else 'No context'}")
        # Check what structure we actually get
        if result1.get("context"):
            if "global_settings" in result1["context"]:
                assert result1["context"]["global_settings"]["autonomous_rules"]["user1_rule"] == "value1"
            elif "autonomous_rules" in result1["context"]:
                # Maybe the structure is flattened
                assert result1["context"]["autonomous_rules"]["user1_rule"] == "value1"
            else:
                print(f"ERROR: Unexpected context structure: {result1['context']}")
                assert False, f"Unexpected context structure"
        
        # Create facade for user 2
        facade_user2 = facade_factory.create_facade(user_id=user_id_2)
        
        # Create global context for user 2
        result2 = facade_user2.create_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_2}",  # Different user-specific global ID
            data={
                "global_settings": {
                    "autonomous_rules": {"user2_rule": "value2"},
                    "security_policies": {"user2_policy": "policy2"}
                }
            }
        )
        assert result2["success"] is True
        assert result2["context"]["global_settings"]["autonomous_rules"]["user2_rule"] == "value2"
        
        # Verify user 1 cannot see user 2's global context
        get_result1 = facade_user1.get_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_2}"
        )
        assert get_result1["success"] is False or get_result1["context"] is None
        
        # Verify user 2 cannot see user 1's global context
        get_result2 = facade_user2.get_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_1}"
        )
        assert get_result2["success"] is False or get_result2["context"] is None
        
        # Verify each user can see their own global context
        own_result1 = facade_user1.get_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_1}"
        )
        assert own_result1["success"] is True
        assert own_result1["context"]["global_settings"]["autonomous_rules"]["user1_rule"] == "value1"
        
        own_result2 = facade_user2.get_context(
            level="global",
            context_id=f"{GLOBAL_SINGLETON_UUID}_{user_id_2}"
        )
        assert own_result2["success"] is True
        assert own_result2["context"]["global_settings"]["autonomous_rules"]["user2_rule"] == "value2"
    
    def test_project_context_user_isolation(self, facade_factory, setup_project_hierarchy, user_id_1, user_id_2):
        """Test that project contexts are properly isolated by user."""
        hierarchy = setup_project_hierarchy
        
        # Create facade for user 1 (owner of the project)
        facade_user1 = facade_factory.create_facade(
            user_id=user_id_1,
            project_id=hierarchy["project_id"]
        )
        
        # Create project context for user 1
        project_context_id = str(uuid.uuid4())
        result1 = facade_user1.create_context(
            level="project",
            context_id=project_context_id,
            data={
                "project_name": "User1 Project",
                "project_settings": {"theme": "dark"},
                "technology_stack": {"framework": "FastAPI"}
            }
        )
        if not result1["success"]:
            print(f"Failed to create project context: {result1.get('error')}")
            print(f"Full result: {result1}")
        assert result1["success"] is True
        
        # Create facade for user 2 (different user)
        facade_user2 = facade_factory.create_facade(
            user_id=user_id_2,
            project_id=hierarchy["project_id"]  # Same project ID
        )
        
        # User 2 should not be able to access user 1's project context
        get_result2 = facade_user2.get_context(
            level="project",
            context_id=project_context_id
        )
        # Should fail or return None due to user isolation
        assert get_result2["success"] is False or get_result2["context"] is None
    
    def test_branch_context_user_isolation(self, facade_factory, setup_project_hierarchy, user_id_1, user_id_2):
        """Test that branch contexts are properly isolated by user."""
        hierarchy = setup_project_hierarchy
        
        # Create facade for user 1
        facade_user1 = facade_factory.create_facade(
            user_id=user_id_1,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # Create branch context for user 1
        branch_context_id = str(uuid.uuid4())
        result1 = facade_user1.create_context(
            level="branch",
            context_id=branch_context_id,
            data={
                "git_branch_name": "feature/user1-feature",
                "branch_settings": {"workflow": "agile"},
                "feature_flags": {"new_ui": True}
            }
        )
        assert result1["success"] is True
        
        # Create facade for user 2
        facade_user2 = facade_factory.create_facade(
            user_id=user_id_2,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # User 2 should not be able to access user 1's branch context
        get_result2 = facade_user2.get_context(
            level="branch",
            context_id=branch_context_id
        )
        assert get_result2["success"] is False or get_result2["context"] is None
    
    def test_task_context_user_isolation(self, facade_factory, setup_project_hierarchy, user_id_1, user_id_2):
        """Test that task contexts are properly isolated by user."""
        hierarchy = setup_project_hierarchy
        
        # Create facade for user 1
        facade_user1 = facade_factory.create_facade(
            user_id=user_id_1,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # Create task context for user 1
        task_context_id = hierarchy["task_id"]  # Use the actual task ID
        result1 = facade_user1.create_context(
            level="task",
            context_id=task_context_id,
            data={
                "task_data": {
                    "title": "User1 Task",
                    "status": "in_progress",
                    "priority": "high"
                },
                "progress": 50,
                "insights": ["User1 insight"],
                "next_steps": ["User1 next step"]
            }
        )
        assert result1["success"] is True
        
        # Create facade for user 2
        facade_user2 = facade_factory.create_facade(
            user_id=user_id_2,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # User 2 should not be able to access user 1's task context
        get_result2 = facade_user2.get_context(
            level="task",
            context_id=task_context_id
        )
        assert get_result2["success"] is False or get_result2["context"] is None
    
    def test_context_crud_operations_with_user_uuid(self, facade_factory, setup_project_hierarchy, user_id_1):
        """Test complete CRUD operations for all context levels with user UUID."""
        hierarchy = setup_project_hierarchy
        
        # Create facade with user UUID
        facade = facade_factory.create_facade(
            user_id=user_id_1,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # CREATE - Global Context
        global_id = f"{GLOBAL_SINGLETON_UUID}_{user_id_1}"
        global_create = facade.create_context(
            level="global",
            context_id=global_id,
            data={
                "global_settings": {
                    "autonomous_rules": {"test_rule": "value"},
                    "security_policies": {"test_policy": "enabled"}
                }
            }
        )
        assert global_create["success"] is True
        
        # READ - Global Context
        global_read = facade.get_context(
            level="global",
            context_id=global_id
        )
        assert global_read["success"] is True
        assert global_read["context"]["global_settings"]["autonomous_rules"]["test_rule"] == "value"
        
        # UPDATE - Global Context
        global_update = facade.update_context(
            level="global",
            context_id=global_id,
            data={
                "global_settings": {
                    "autonomous_rules": {"test_rule": "updated_value"},
                    "security_policies": {"test_policy": "disabled"}
                }
            }
        )
        assert global_update["success"] is True
        
        # Verify update
        global_verify = facade.get_context(
            level="global",
            context_id=global_id
        )
        assert global_verify["context"]["global_settings"]["autonomous_rules"]["test_rule"] == "updated_value"
        
        # CREATE - Project Context
        project_id = str(uuid.uuid4())
        project_create = facade.create_context(
            level="project",
            context_id=project_id,
            data={
                "project_name": "Test Project",
                "project_settings": {"language": "Python"}
            }
        )
        assert project_create["success"] is True
        
        # CREATE - Branch Context
        branch_id = str(uuid.uuid4())
        branch_create = facade.create_context(
            level="branch",
            context_id=branch_id,
            data={
                "git_branch_name": "feature/test",
                "branch_settings": {"auto_merge": False}
            }
        )
        assert branch_create["success"] is True
        
        # CREATE - Task Context
        task_id = hierarchy["task_id"]
        task_create = facade.create_context(
            level="task",
            context_id=task_id,
            data={
                "task_data": {"title": "Test Task", "status": "todo"},
                "progress": 0
            }
        )
        assert task_create["success"] is True
        
        # Test inheritance resolution
        resolved = facade.resolve_context(
            level="task",
            context_id=task_id
        )
        assert resolved["success"] is True
        # Should include inherited data from all levels
        assert "autonomous_rules" in str(resolved["resolved_context"])  # From global
        
        # DELETE - Task Context
        task_delete = facade.delete_context(
            level="task",
            context_id=task_id
        )
        assert task_delete["success"] is True
        
        # Verify deletion
        task_verify = facade.get_context(
            level="task",
            context_id=task_id
        )
        assert task_verify["success"] is False or task_verify["context"] is None
    
    def test_context_list_operations_with_user_filter(self, facade_factory, setup_project_hierarchy, user_id_1, user_id_2):
        """Test that list operations only return contexts for the authenticated user."""
        hierarchy = setup_project_hierarchy
        
        # Create contexts for user 1
        facade_user1 = facade_factory.create_facade(
            user_id=user_id_1,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # Create multiple contexts for user 1
        created_contexts = []
        for i in range(3):
            result = facade_user1.create_context(
                level="project",
                context_id=str(uuid.uuid4()),
                data={"project_name": f"User1 Project {i}"}
            )
            created_contexts.append(result)
        
        # List contexts for user 1
        list_result1 = facade_user1.list_contexts(level="project")
        assert list_result1["success"] is True
        assert len(list_result1["contexts"]) >= 3
        
        # Create facade for user 2
        facade_user2 = facade_factory.create_facade(
            user_id=user_id_2,
            project_id=hierarchy["project_id"],
            git_branch_id=hierarchy["git_branch_id"]
        )
        
        # List contexts for user 2 (should be empty or only user 2's contexts)
        list_result2 = facade_user2.list_contexts(level="project")
        assert list_result2["success"] is True
        # User 2 should not see user 1's contexts
        for context in list_result2.get("contexts", []):
            assert "User1 Project" not in str(context)