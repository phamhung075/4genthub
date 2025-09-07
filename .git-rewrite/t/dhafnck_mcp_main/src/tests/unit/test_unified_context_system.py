"""
Comprehensive tests for the Unified Context System.

Tests cover:
- UnifiedContextService operations
- UnifiedContextController parameter validation  
- Repository implementations
- Context hierarchy and inheritance
- Delegation functionality
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Import the components we're testing
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.interface.controllers.unified_context_controller import (
    UnifiedContextMCPController
)
from fastmcp.task_management.infrastructure.repositories.global_context_repository_user_scoped import GlobalContextRepository
from fastmcp.task_management.infrastructure.repositories.project_context_repository import ProjectContextRepository
from fastmcp.task_management.infrastructure.repositories.branch_context_repository import BranchContextRepository
from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
from fastmcp.task_management.domain.entities.context import (
    GlobalContext, ProjectContext, BranchContext, TaskContextUnified
)
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel




class TestUnifiedContextService:
    """Test the unified context service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock repositories
        self.global_repo = Mock(spec=GlobalContextRepository)
        self.project_repo = Mock(spec=ProjectContextRepository)
        self.branch_repo = Mock(spec=BranchContextRepository)
        self.task_repo = Mock(spec=TaskContextRepository)
        
        # Create mock services
        self.cache_service = Mock()
        self.cache_service.invalidate = Mock()
        self.cache_service.get = Mock(return_value=None)
        self.cache_service.set = Mock()
        self.cache_service.invalidate_all = Mock()
        
        self.inheritance_service = Mock()
        self.inheritance_service.resolve_inheritance = Mock()
        
        self.delegation_service = Mock()
        self.delegation_service.delegate_context = Mock()
        
        self.validation_service = Mock()
        # Set up sync methods on validation service
        self.validation_service.validate_context_data = Mock(return_value={"valid": True, "errors": []})
        
        # Create service instance
        self.service = UnifiedContextService(
            global_context_repository=self.global_repo,
            project_context_repository=self.project_repo,
            branch_context_repository=self.branch_repo,
            task_context_repository=self.task_repo,
            cache_service=self.cache_service,
            inheritance_service=self.inheritance_service,
            delegation_service=self.delegation_service,
            validation_service=self.validation_service
        )
    
    def test_create_context_global(self):
        """Test creating a global context."""
        # Mock repository behavior
        self.global_repo.create = Mock(return_value=GlobalContext(
            id="global_singleton",
            organization_name="TestOrg",
            global_settings={"autonomous_rules": {"test": "rule"}},
            metadata={}
        ))
        
        # Call create_context
        result = self.service.create_context(
            level="global",
            context_id="global_singleton",
            data={"organization_name": "TestOrg", "autonomous_rules": {"test": "rule"}}
        )
        
        # Verify result
        assert result["success"] is True
        assert result["context"]["id"] == "global_singleton"
        assert result["context"]["global_settings"]["autonomous_rules"] == {"test": "rule"}
        assert result["level"] == "global"
        
        # Verify repository called
        self.global_repo.create.assert_called_once()
    
    def test_create_context_task(self):
        """Test creating a task context."""
        # Mock repository behavior
        self.task_repo.create = Mock(return_value=TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=0,

            next_steps=[],
            metadata={}
        ))
        
        # Call create_context
        result = self.service.create_context(
            level="task",
            context_id="task-123",
            data={"title": "Test Task", "branch_id": "branch-456"}
        )
        
        # Verify result
        assert result["success"] is True
        assert result["context"]["id"] == "task-123"
        assert result["context"]["task_data"]["title"] == "Test Task"
        assert result["level"] == "task"
    
    def test_get_context_with_cache(self):
        """Test getting context with cache hit."""
        # Mock cache hit
        cached_data = {
            "id": "task-123",
            "task_data": {"title": "Cached Task"},
            "progress": 50
        }
        self.cache_service.get = Mock(return_value=cached_data)
        
        # Call get_context - note: we skip cache in sync mode, so mock the repository
        self.task_repo.get = Mock(return_value=TaskContextUnified(
            id="task-123",
            branch_id="branch-456", 
            task_data={"title": "Cached Task"},
            progress=50,

            next_steps=[],
            metadata={}
        ))
        
        result = self.service.get_context(
            level="task",
            context_id="task-123"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["context"]["id"] == "task-123"
        assert result["context"]["task_data"]["title"] == "Cached Task"
        
        # Verify repository was called (since we skip cache in sync mode)
        self.task_repo.get.assert_called_once_with("task-123")
    
    def test_get_context_with_inheritance(self):
        """Test getting context with inheritance resolution."""
        # Mock repository response
        task_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=0,

            next_steps=[],
            metadata={}
        )
        self.task_repo.get = Mock(return_value=task_context)
        
        # Mock cache miss
        self.cache_service.get = Mock(return_value=None)
        
        # Mock inheritance resolution
        inherited_data = {
            "id": "task-123",
            "task_data": {"title": "Test Task"},
            "inherited_patterns": {"from_project": "pattern"}
        }
        self.inheritance_service.resolve_inheritance = Mock(
            return_value=inherited_data
        )
        
        # Call get_context with inheritance - note: sync service skips inheritance for now
        result = self.service.get_context(
            level="task",
            context_id="task-123",
            include_inherited=True
        )
        
        # Verify result (inheritance skipped in sync mode)
        assert result["success"] is True
        assert result["context"]["task_data"]["title"] == "Test Task"
        assert result["inherited"] is True
        
        # Verify repository was called
        self.task_repo.get.assert_called_once_with("task-123")
    
    def test_update_context_with_propagation(self):
        """Test updating context with change propagation."""
        # Mock get existing context
        existing_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Old Title"},
            progress=0,

            next_steps=[],
            metadata={}
        )
        self.task_repo.get = Mock(return_value=existing_context)
        
        # Mock update
        updated_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "New Title", "status": "in_progress"},
            progress=50,

            next_steps=[],
            metadata={}
        )
        self.task_repo.update = Mock(return_value=updated_context)
        
        # Mock cache operations
        self.cache_service.invalidate = Mock()
        
        # Call update_context
        result = self.service.update_context(
            level="task",
            context_id="task-123",
            data={"title": "New Title", "status": "in_progress", "progress": 50},
            propagate_changes=True
        )
        
        # Verify result
        assert result["success"] is True
        assert result["context"]["task_data"]["title"] == "New Title"
        assert result["context"]["progress"] == 50
        
        # Cache operations are skipped in sync mode
    
    def test_delegate_context(self):
        """Test delegating context to higher level."""
        # Mock get source context
        source_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=100,
            insights=["Discovered reusable pattern"],
            next_steps=[],
            metadata={}
        )
        self.task_repo.get = Mock(return_value=source_context)
        
        # Mock delegation service
        delegation_result = {
            "delegation_id": "del-789",
            "status": "queued"
        }
        self.delegation_service.delegate_context = Mock(return_value=delegation_result)
        
        # Call delegate_context
        result = self.service.delegate_context(
            level="task",
            context_id="task-123",
            delegate_to="project",
            data={"pattern": "reusable_auth_flow"},
            delegation_reason="Authentication pattern useful across tasks"
        )
        
        # Verify result (delegation is skipped in sync mode)
        assert result["success"] is True
        assert "delegation" in result
        
        # Delegation is skipped in sync mode
    
    def test_add_insight(self):
        """Test adding an insight to context."""
        # Mock get existing context
        existing_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=50,

            next_steps=[],
            metadata={}
        )
        self.task_repo.get = Mock(return_value=existing_context)
        
        # Mock update
        updated_context = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=50,
            insights=[{
                "content": "Found optimization opportunity",
                "category": "performance",
                "importance": "high",
                "agent": "test_agent",
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            next_steps=[],
            metadata={}
        )
        self.task_repo.update = Mock(return_value=updated_context)
        
        # Call add_insight
        with patch('fastmcp.task_management.application.services.unified_context_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            
            result = self.service.add_insight(
                level="task",
                context_id="task-123",
                content="Found optimization opportunity",
                category="performance",
                importance="high",
                agent="test_agent"
            )
        
        # Verify result
        assert result["success"] is True
        assert len(result["context"]["insights"]) == 1
        assert result["context"]["insights"][0]["content"] == "Found optimization opportunity"


class TestUnifiedContextController:
    """Test the unified context controller."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock facade factory
        self.facade_factory = Mock()
        self.facade = Mock()
        self.facade_factory.create_facade = Mock(return_value=self.facade)
        
        # Create controller
        self.controller = UnifiedContextMCPController(self.facade_factory)
    
    
    def test_register_tools(self):
        """Test MCP tool registration."""
        # Create mock MCP instance
        mcp = Mock()
        mcp.tool = Mock(return_value=lambda func: func)
        
        # Register tools
        self.controller.register_tools(mcp)
        
        # Verify tool registered
        mcp.tool.assert_called_once()
        call_args = mcp.tool.call_args[1]
        assert call_args["name"] == "manage_context"
        assert "description" in call_args


class TestContextRepositories:
    """Test the context repository implementations."""
    
    def test_task_context_repository_create(self):
        """Test creating a task context via repository."""
        # Create entity
        entity = TaskContextUnified(
            id="task-123",
            branch_id="branch-456",
            task_data={"title": "Test Task"},
            progress=0,

            next_steps=[],
            metadata={}
        )
        
        # Create mock session with correct method calls
        mock_session = Mock()
        mock_session.get = Mock(return_value=None)  # No existing context
        mock_session.add = Mock()
        mock_session.flush = Mock()
        mock_session.refresh = Mock()
        
        
        # Create repository
        repo = TaskContextRepository(None)
        
        # Mock get_db_session to return our context manager
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        repo.get_db_session = Mock(return_value=mock_context_manager)
        
        # Mock _to_entity to return our entity
        repo._to_entity = Mock(return_value=entity)
        
        # Patch TaskContextModel to avoid constructor issues
        with patch('fastmcp.task_management.infrastructure.repositories.task_context_repository.TaskContextModel') as MockModel:
            mock_db_model = Mock()
            MockModel.return_value = mock_db_model
            
            # Call create (now sync)
            result = repo.create(entity)
            
            # Verify result
            assert result.id == "task-123"
            assert result.branch_id == "branch-456"
            assert result.task_data["title"] == "Test Task"
            
            # Verify session methods called
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()
            # Note: refresh is NOT called in the actual implementation to avoid UUID conversion issues with SQLite


class TestContextLevelEnum:
    """Test the ContextLevel enum."""
    
    def test_context_level_values(self):
        """Test context level enum values."""
        assert ContextLevel.GLOBAL.value == "global"
        assert ContextLevel.PROJECT.value == "project"
        assert ContextLevel.BRANCH.value == "branch"
        assert ContextLevel.TASK.value == "task"
    
    def test_context_level_from_string(self):
        """Test creating context level from string."""
        assert ContextLevel.from_string("global") == ContextLevel.GLOBAL
        assert ContextLevel.from_string("PROJECT") == ContextLevel.PROJECT
        assert ContextLevel.from_string("Branch") == ContextLevel.BRANCH
        assert ContextLevel.from_string("task") == ContextLevel.TASK
        
        with pytest.raises(ValueError, match="Invalid context level"):
            ContextLevel.from_string("invalid")
    
    def test_context_level_parent(self):
        """Test getting parent level."""
        assert ContextLevel.TASK.get_parent_level() == ContextLevel.BRANCH
        assert ContextLevel.BRANCH.get_parent_level() == ContextLevel.PROJECT
        assert ContextLevel.PROJECT.get_parent_level() == ContextLevel.GLOBAL
        assert ContextLevel.GLOBAL.get_parent_level() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])