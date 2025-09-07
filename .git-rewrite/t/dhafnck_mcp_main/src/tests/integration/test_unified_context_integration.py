"""
Integration tests for the Unified Context System.

Tests the complete flow of the unified context system including:
- Creating contexts at all levels
- Inheritance resolution
- Delegation workflow
- MCP controller integration
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from fastmcp.task_management.interface.controllers.unified_context_controller import UnifiedContextMCPController
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.infrastructure.database.database_config import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestUnifiedContextIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                # Clean up in reverse order of foreign key dependencies
                session.execute(text("DELETE FROM task_contexts"))
                session.execute(text("DELETE FROM tasks"))
                session.execute(text("DELETE FROM branch_contexts"))
                session.execute(text("DELETE FROM project_git_branchs WHERE project_id != 'default_project'"))
                session.execute(text("DELETE FROM project_contexts WHERE project_id != 'default_project'"))
                session.execute(text("DELETE FROM projects WHERE id != 'default_project'"))
                # Don't delete global_singleton - it might be needed by the test framework
                session.commit()
            except Exception as e:
                print(f"Cleanup error: {e}")
                session.rollback()

    """Integration tests for the unified context system."""
    
    @pytest.fixture
    def setup_test_db(self):
        """Set up test database using existing test infrastructure."""
        # Use the existing test database infrastructure
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        return get_session
    
    def _ensure_global_context(self, facade):
        """Ensure global context exists for tests that need it."""
        # Check if global context already exists
        result = facade.get_context("global", "global_singleton")
        if not result["success"]:
            # Create global context
            global_result = facade.create_context(
                level="global",
                context_id="global_singleton",
                data={
                    "autonomous_rules": {"default": "rules"},
                    "security_policies": {"default": "policies"}
                }
            )
            return global_result
        return result
    
    @pytest.fixture
    def facade_factory(self, setup_test_db):
        """Create a facade factory with test database."""
        return UnifiedContextFacadeFactory()
        
    @pytest.fixture
    def facade(self, facade_factory):
        """Create a facade for testing."""
        return facade_factory.create_facade()
    
    @pytest.fixture
    def controller(self, facade_factory):
        """Create a controller for testing."""
        return UnifiedContextMCPController(facade_factory)
    
    @pytest.mark.skip(reason="Incompatible with PostgreSQL")

    
    def test_complete_context_hierarchy_flow(self, facade, setup_test_db):
        """Test creating and managing contexts across the full hierarchy."""
        # First create the actual project and git branch that contexts will reference
        with setup_test_db() as session:
            # Create project
            from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch
            project_id = f'test-project-{uuid.uuid4().hex[:8]}'

            project = Project(
                id=str(uuid.uuid4()),
                name="Test Project",
                description="Test project for context hierarchy",
                user_id="test_user"
            )
            session.add(project)
            
            # Create git branch
            git_branch = ProjectGitBranch(
                id=str(uuid.uuid4()),
                project_id=project.id,
                name="feature/test",
                description="Test branch for context hierarchy"
            )
            session.add(git_branch)
            session.commit()
        
        # Create global context
        global_result = facade.create_context(
            level="global",
            context_id="global_singleton",
            data={
                "autonomous_rules": {"coding": "PEP8"},
                "security_policies": {"auth": "JWT required"}
            }
        )
        assert global_result["success"] is True
        assert global_result["level"] == "global"
        
        # Create project context (must be created before branch context due to foreign key constraints)
        project_result = facade.create_context(
            level="project", 
            context_id=str(uuid.uuid4()),
            data={
                "project_name": "Test Project",
                "project_settings": {
                    "team_preferences": {"language": "Python"},
                    "technology_stack": {"framework": "FastAPI"}
                }
            }
        )
        # Debug: Print result if project context creation fails
        if not project_result.get("success"):
            print(f"Project context creation failed: {project_result}")
        assert project_result["success"] is True
        
        # Create branch context
        branch_result = facade.create_context(
            level="branch",
            context_id=str(uuid.uuid4()),
            data={
                "project_id": project.id,  # Reference to parent project (use project_id not parent_project_id)
                "git_branch_name": "feature/test",
                "branch_workflow": {"type": "feature"},
                "branch_standards": {"review": "required"}
            }
        )
        # Debug: Print result if branch context creation fails
        if not branch_result.get("success"):
            print(f"Branch context creation failed: {branch_result}")
        assert branch_result["success"] is True
        
        # Verify branch context was created in database
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import BranchContext as BranchContextModel
            branch_ctx = session.get(BranchContextModel, git_branch.id)
            if not branch_ctx:
                print("ERROR: Branch context not found in database after creation!")
            else:
                print(f"Branch context found: {branch_ctx.branch_id}")
        
        # Create the actual task in the database first
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Task
            task = Task(
                id=str(uuid.uuid4()),
                git_branch_id=git_branch.id,
                title="Implement authentication",
                description="Implement JWT-based authentication",
                status="in_progress",
                priority="medium"
            )
            session.add(task)
            session.commit()
        
        # Create task context
        task_result = facade.create_context(
            level="task",
            context_id=str(uuid.uuid4()),
            data={
                "parent_branch_id": git_branch.id,  # Reference to parent branch
                "task_data": {
                    "title": "Implement authentication",
                    "status": "in_progress"
                }
            }
        )
        assert task_result["success"] is True
        
        # Get task context with inheritance
        inherited_result = facade.get_context(
            level="task",
            context_id=str(uuid.uuid4()),
            include_inherited=True
        )
        assert inherited_result["success"] is True
    
    def test_context_update_and_propagation(self, facade, setup_test_db):
        """Test updating context and propagating changes."""
        # Ensure global context exists
        self._ensure_global_context(facade)
        
        # First ensure we have a valid branch
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch
            project_id = f'test-project-{uuid.uuid4().hex[:8]}'

            project = Project(
                id=str(uuid.uuid4()),
                name="Update Test Project",
                description="Test project for update",
                user_id="test_user"
            )
            session.add(project)
            
            git_branch = ProjectGitBranch(
                id=str(uuid.uuid4()),
                project_id=project.id,
                name="feature/update-test",
                description="Test branch for update"
            )
            session.add(git_branch)
            session.commit()
        
        # Create project context first
        project_result = facade.create_context(
            level="project",
            context_id=project.id,
            data={
                "project_name": "Update Test Project",
                "project_settings": {
                    "team_preferences": {"language": "Python"},
                    "technology_stack": {"framework": "FastAPI"}
                }
            }
        )
        assert project_result["success"] is True
        
        # Create branch context next
        branch_result = facade.create_context(
            level="branch",
            context_id=git_branch.id,
            data={
                "project_id": project.id,
                "git_branch_name": "feature/update-test",
                "branch_settings": {
                    "branch_workflow": {"type": "feature"},
                    "branch_standards": {"review": "required"}
                }
            }
        )
        assert branch_result["success"] is True
        
        # Create the actual task in the database first
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Task
            task = Task(
                id=str(uuid.uuid4()),
                git_branch_id=git_branch.id,
                title="Initial Task",
                description="Test task for update",
                status="todo",
                priority="medium"
            )
            session.add(task)
            session.commit()
        
        # Create initial task context
        create_result = facade.create_context(
            level="task",
            context_id=task.id,
            data={
                "branch_id": git_branch.id,
                "task_data": {
                    "title": "Initial Task",
                    "status": "todo"
                }
            }
        )
        assert create_result["success"] is True
        
        # Update task context
        update_result = facade.update_context(
            level="task",
            context_id=task.id,
            data={
                "task_data": {
                    "title": "Initial Task",
                    "status": "in_progress",
                    "progress": 50
                }
            },
            propagate_changes=True
        )
        assert update_result["success"] is True
    
    def test_context_delegation_workflow(self, facade, setup_test_db):
        """Test delegating patterns from task to project level."""
        # Ensure global context exists
        self._ensure_global_context(facade)
        
        # First ensure we have a valid branch
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch
            project_id = f'test-project-{uuid.uuid4().hex[:8]}'

            project = Project(
                id=str(uuid.uuid4()),
                name="Delegate Test Project",
                description="Test project for delegation",
                user_id="test_user"
            )
            session.add(project)
            
            git_branch = ProjectGitBranch(
                id=str(uuid.uuid4()),
                project_id=project.id,
                name="feature/delegate-test",
                description="Test branch for delegation"
            )
            session.add(git_branch)
            session.commit()
        
        # Create project context first
        project_result = facade.create_context(
            level="project",
            context_id=project.id,
            data={
                "project_name": "Delegate Test Project",
                "project_settings": {
                    "team_preferences": {"language": "Python"},
                    "technology_stack": {"framework": "FastAPI"}
                }
            }
        )
        assert project_result["success"] is True
        
        # Create branch context next
        branch_result = facade.create_context(
            level="branch",
            context_id=git_branch.id,
            data={
                "project_id": project.id,
                "branch_workflow": {"type": "feature"},
                "branch_standards": {"review": "required"}
            }
        )
        assert branch_result["success"] is True
        
        # Create the actual task in the database first
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Task
            task = Task(
                id=str(uuid.uuid4()),
                git_branch_id=git_branch.id,
                title="Auth Implementation",
                description="Implement authentication with JWT",
                status="todo",
                priority="high"
            )
            session.add(task)
            session.commit()
        
        # Create task context with reusable pattern
        create_result = facade.create_context(
            level="task",
            context_id=task.id,
            data={
                "parent_branch_id": git_branch.id,
                "task_data": {
                    "title": "Auth Implementation"
                },
                "implementation_notes": {
                    "auth_pattern": "JWT with refresh tokens"
                },
                "local_overrides": {},
                "delegation_triggers": {},
                "inheritance_disabled": False,
                "force_local_only": False
            }
        )
        assert create_result["success"] is True
        
        # Delegate pattern to project level
        delegate_result = facade.delegate_context(
            level="task",
            context_id=task.id,
            delegate_to="project",
            data={
                "auth_pattern": "JWT with refresh tokens",
                "usage": "Standard auth implementation"
            },
            delegation_reason="Reusable authentication pattern"
        )
        assert delegate_result["success"] is True
    
    def test_add_insights_and_progress(self, facade, setup_test_db):
        """Test adding insights and progress to contexts."""
        # Ensure global context exists
        self._ensure_global_context(facade)
        
        # First ensure we have a valid branch
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Project, ProjectGitBranch
            project_id = f'test-project-{uuid.uuid4().hex[:8]}'

            project = Project(
                id=str(uuid.uuid4()),
                name="Insights Test Project",
                description="Test project for insights",
                user_id="test_user"
            )
            session.add(project)
            
            git_branch = ProjectGitBranch(
                id=str(uuid.uuid4()),
                project_id=project.id,
                name="feature/insights-test",
                description="Test branch for insights"
            )
            session.add(git_branch)
            session.commit()
        
        # Create project context first
        project_result = facade.create_context(
            level="project",
            context_id=project.id,
            data={
                "project_name": "Insights Test Project",
                "project_settings": {
                    "team_preferences": {"language": "Python"},
                    "technology_stack": {"framework": "FastAPI"}
                }
            }
        )
        assert project_result["success"] is True
        
        # Create branch context next
        branch_result = facade.create_context(
            level="branch",
            context_id=git_branch.id,
            data={
                "project_id": project.id,
                "branch_workflow": {"type": "feature"},
                "branch_standards": {"review": "required"}
            }
        )
        assert branch_result["success"] is True
        
        # Create the actual task in the database first
        with setup_test_db() as session:
            from fastmcp.task_management.infrastructure.database.models import Task
            task = Task(
                id=str(uuid.uuid4()),
                git_branch_id=git_branch.id,
                title="Performance Optimization",
                description="Optimize application performance",
                status="in_progress",
                priority="high"
            )
            session.add(task)
            session.commit()
        
        # Create task context
        create_result = facade.create_context(
            level="task",
            context_id=task.id,
            data={
                "parent_branch_id": git_branch.id,
                "task_data": {
                    "title": "Performance Optimization"
                },
                "local_overrides": {},
                "implementation_notes": {},
                "delegation_triggers": {},
                "inheritance_disabled": False,
                "force_local_only": False
            }
        )
        assert create_result["success"] is True
        
        # Add insight
        insight_result = facade.add_insight(
            level="task",
            context_id=task.id,
            content="Found N+1 query issue in user loader",
            category="performance",
            importance="high",
            agent="performance_analyzer"
        )
        assert insight_result["success"] is True
        
        # Add progress
        progress_result = facade.add_progress(
            level="task",
            context_id=task.id,
            content="Optimized database queries, 50% improvement",
            agent="optimization_agent"
        )
        assert progress_result["success"] is True
    
    def test_legacy_format_compatibility(self, controller, facade):
        """Test backward compatibility with legacy manage_context format."""
        # First ensure global context exists
        self._ensure_global_context(facade)
        
        # Create the project in database first
        from fastmcp.task_management.infrastructure.database.database_config import get_session
        from fastmcp.task_management.infrastructure.database.models import Project
        
        with get_session() as session:
            project_id = f'test-project-{uuid.uuid4().hex[:8]}'

            project = Project(
                id=str(uuid.uuid4()),
                name="Legacy Project",
                description="Test legacy format compatibility",
                user_id="test_user"
            )
            session.add(project)
            session.commit()
        
        # Create a mock MCP instance and register tools to get access to manage_context
        mcp = Mock()
        tools = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools[name] = func
                return func
            return decorator
        
        mcp.tool = mock_tool
        controller.register_tools(mcp)
        
        # Use legacy format to create context  
        # Test project level which doesn't require branch_id
        manage_context = tools["manage_context"]
        result = manage_context(
            action="create",
            level="project",
            context_id=project.id,
            data_title="Legacy Project",
            data_description="Created with legacy format",
            data_status="active",
            data_priority="high"
        )
        assert result["success"] is True
    
    def test_error_handling(self, controller):
        """Test error handling in the unified context system."""
        # Create a mock MCP instance and register tools to get access to manage_context
        mcp = Mock()
        tools = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools[name] = func
                return func
            return decorator
        
        mcp.tool = mock_tool
        controller.register_tools(mcp)
        manage_context = tools["manage_context"]
        
        # Test invalid action
        result = manage_context(
            action="invalid_action",
            level="task",
            context_id=str(uuid.uuid4())
        )
        assert result["success"] is False
        assert "error" in result
        assert "message" in result["error"]
        assert "Unknown action" in result["error"]["message"]
        
        # Test invalid level - this will be caught by the facade/service
        result = manage_context(
            action="create",
            level="invalid_level",
            context_id="test-123",
            data={"title": "Test"}
        )
        assert result["success"] is False
    
    def test_list_contexts(self, controller):
        """Test listing contexts at different levels."""
        # Create a mock MCP instance and register tools to get access to manage_context
        mcp = Mock()
        tools = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools[name] = func
                return func
            return decorator
        
        mcp.tool = mock_tool
        controller.register_tools(mcp)
        manage_context = tools["manage_context"]
        
        # Mock the list_contexts method to return test data
        with patch.object(controller._facade_factory, 'create_facade') as mock_factory:
            mock_facade = Mock()
            mock_facade.list_contexts.return_value = {
                "success": True,
                "contexts": [
                    {"id": "task-0", "title": "Task 0"},
                    {"id": "task-1", "title": "Task 1"},
                    {"id": "task-2", "title": "Task 2"}
                ],
                "count": 3
            }
            mock_factory.return_value = mock_facade
            
            list_result = manage_context(
                action="list",
                level="task"
            )
            assert list_result["success"] is True
            # Count should be in metadata.context_operation.count after formatting
            assert list_result.get("count") == 3 or \
                   list_result.get("metadata", {}).get("context_operation", {}).get("count") == 3 or \
                   len(list_result.get("contexts", [])) == 3
    
    @pytest.mark.skip(reason="Incompatible with PostgreSQL")

    
    def test_mcp_tool_integration(self, controller):
        """Test MCP tool registration and usage."""
        # Create mock MCP instance
        mcp = Mock()
        tools = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools[name] = {
                    "func": func,
                    "description": description
                }
                return func
            return decorator
        
        mcp.tool = mock_tool
        
        # Register tools
        controller.register_tools(mcp)
        
        # Verify manage_context tool was registered
        assert "manage_context" in tools
        assert tools["manage_context"]["description"] is not None
        
        # Test calling the registered tool
        manage_context = tools["manage_context"]["func"]
        
        # No need to mock, just call the tool directly
        
        # Call the tool (now sync)
        # First create a global context to test a simpler case
        result = manage_context(
            action="create",
            level="global",
            context_id="global_singleton",
            data={"autonomous_rules": {"test": "rule"}}
        )
        
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])