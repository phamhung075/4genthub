"""
Unit tests for frontend API context resolution patterns.
Ensures that frontend API calls use the correct context levels for different entity types.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from fastmcp.task_management.interface.controllers.unified_context_controller import (
    UnifiedContextMCPController
)
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel


class TestFrontendContextAPIPatterns:
    
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

    """Test frontend API patterns for context resolution."""
    
    @pytest.fixture
    def mock_facade(self):
        """Create a mock facade for testing."""
        facade = Mock()
        return facade
    
    @pytest.fixture
    def controller(self):
        """Create controller with mock facade factory."""
        mock_facade_factory = Mock()
        return UnifiedContextMCPController(mock_facade_factory)
    
    def test_get_branch_context_api_pattern(self, controller, mock_facade):
        """Test the getBranchContext API pattern from frontend."""
        # Arrange
        branch_id = "d4f91ee3-1f97-4768-b4ff-1e734180f874"
        user_id = "test-user-123"
        expected_context = {
            "id": branch_id,
            "branch_standards": {"branch_name": "feature/auth-system"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                mock_facade.resolve_context.return_value = {
                    "success": True,
                    "context": expected_context,
                    "resolved": True
                }
                
                # Register tools to get the manage_context function
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
                
                # Act - Simulate frontend getBranchContext call
                result = manage_context(
                    action="resolve",
                    level="branch",
                    context_id=branch_id,
                    force_refresh=False,
                    include_inherited=True
                )
            
                # Assert
                assert result["success"] is True
                # After standardization by StandardResponseFormatter, data is under 'data' field
                data = result.get("data", {})
                context = data.get("resolved_context") or data.get("context_data") or data.get("context")
                assert context is not None, f"No context found in result: {result}"
                assert context["id"] == branch_id
                
                # Verify facade was called with correct parameters
                mock_facade.resolve_context.assert_called_once_with(
                    level="branch",
                    context_id=branch_id,
                    force_refresh=False
                )
    
    def test_get_task_context_api_pattern(self, controller, mock_facade):
        """Test the getTaskContext API pattern from frontend."""
        # Arrange
        task_id = "a5f91ee3-2b97-4768-c5ff-2e834290f985"
        user_id = "test-user-123"
        expected_context = {
            "id": task_id,
            "level": "task",
            "data": {"task_title": "Implement login"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                mock_facade.resolve_context.return_value = {
                    "success": True,
                    "context": expected_context,
                    "resolved": True
                }
                
                # Register tools to get the manage_context function
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
                
                # Act - Simulate frontend getTaskContext call
                result = manage_context(
                    action="resolve",
                    level="task",
                    context_id=task_id,
                    force_refresh=False,
                    include_inherited=True
                )
            
                # Assert
                assert result["success"] is True
                # After standardization by StandardResponseFormatter, data is under 'data' field
                data = result.get("data", {})
                context = data.get("resolved_context") or data.get("context_data") or data.get("context")
                assert context is not None, f"No context found in result: {result}"
                assert context["id"] == task_id
                
                # Verify facade was called with correct parameters
                mock_facade.resolve_context.assert_called_once_with(
                    level="task",
                    context_id=task_id,
                    force_refresh=False
                )
    
    def test_wrong_level_returns_error(self, controller, mock_facade):
        """Test that using wrong level returns appropriate error."""
        # Arrange
        branch_id = "d4f91ee3-1f97-4768-b4ff-1e734180f874"
        user_id = "test-user-123"
        
        # Setup mock facade to return error response
        mock_facade.resolve_context.return_value = {
            "success": False,
            "error": f"Context not found: {branch_id}",
            "error_code": "CONTEXT_NOT_FOUND"
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                
                # Register tools to get the manage_context function
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
                
                # Act - Try to resolve branch as task
                result = manage_context(
                    action="resolve",
                    level="task",
                    context_id=branch_id,
                    include_inherited=True
                )
            
                # Assert
                assert result["success"] is False
                # Check if error is in 'error' field or under 'error.message' 
                error_msg = result.get("error", {})
                if isinstance(error_msg, dict):
                    error_text = error_msg.get("message", str(error_msg))
                else:
                    error_text = str(error_msg)
                assert "Context not found" in error_text
    
    def test_manage_context_action_mapping(self, controller, mock_facade):
        """Test that manage_context action parameter maps correctly."""
        user_id = "test-user-123"
        
        # Setup mock facade responses first
        mock_facade.resolve_context.return_value = {
            "success": True,
            "context": {"id": "test-id"},
            "resolved": True
        }
        mock_facade.get_context.return_value = {
            "success": True,
            "context": {"id": "test-id"}
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                
                # Register tools to get the manage_context function
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
                
                # Test resolve action (most common)
                result = manage_context(
                    action="resolve",
                    level="task",
                    context_id="test-id"
                )
                
                assert result["success"] is True
                mock_facade.resolve_context.assert_called_once_with(
                    level="task",
                    context_id="test-id",
                    force_refresh=False
                )
                
                # Test get action
                mock_facade.reset_mock()
                result = manage_context(
                    action="get",
                    level="task",
                    context_id="test-id"
                )
                
                assert result["success"] is True
                mock_facade.get_context.assert_called_once_with(
                    level="task",
                    context_id="test-id",
                    include_inherited=False,
                    force_refresh=False
                )
    
    def test_frontend_error_handling_pattern(self, controller, mock_facade):
        """Test error handling pattern that frontend expects."""
        # Arrange
        branch_id = "d4f91ee3-1f97-4768-b4ff-1e734180f874"
        user_id = "test-user-123"
        
        # Setup mock facade to return error response
        mock_facade.resolve_context.return_value = {
            "success": False,
            "error": "Database connection error",
            "error_code": "DATABASE_ERROR"
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                
                # Register tools to get the manage_context function
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
                
                # Act
                result = manage_context(
                    action="resolve",
                    level="branch",
                    context_id=branch_id
                )
            
                # Assert - Frontend expects specific error format
                assert result["success"] is False
                assert "error" in result
                # Error might be string or dict with message
                error = result["error"]
                if isinstance(error, dict):
                    assert "message" in error
                    assert len(error["message"]) > 0
                else:
                    assert isinstance(error, str)
                    assert len(error) > 0
    
    def test_auto_level_detection_disabled_for_resolve(self, controller, mock_facade):
        """Test that resolve action requires explicit level specification."""
        # Arrange
        context_id = "some-context-id"
        user_id = "test-user-123"
        
        # Setup mock facade response
        mock_facade.resolve_context.return_value = {
            "success": True,
            "context": {"id": context_id},
            "resolved": True
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                
                # Register tools to get the manage_context function
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
                
                # Act - Try resolve without level
                result = manage_context(
                    action="resolve",
                    context_id=context_id
                )
            
                # Assert - Should use default level (task)
                assert mock_facade.resolve_context.called
                call_args = mock_facade.resolve_context.call_args
                # Check if level was passed as keyword argument or defaults to task
                called_level = call_args[1].get("level", "task")
                assert called_level == "task"
    
    def test_inheritance_data_structure(self, controller, mock_facade):
        """Test that inheritance data matches frontend expectations."""
        # Arrange
        task_id = "task-123"
        user_id = "test-user-123"
        task_context = {
            "id": task_id,
            "level": "task",
            "data": {"title": "Test Task"},
            "_inheritance": {
                "chain": ["global", "project", "branch", "task"],
                "inheritance_depth": 4
            },
            "global_settings": {"org": "DhafnckMCP"},
            "project_settings": {"name": "Test Project"},
            "branch_settings": {"name": "feature"}
        }
        
        # Setup mock facade response
        mock_facade.resolve_context.return_value = {
            "success": True,
            "context": task_context,
            "resolved": True,
            "inheritance_applied": True
        }
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock the facade factory to return our mock facade
            with patch.object(controller, '_facade_factory') as mock_factory:
                mock_factory.create_facade.return_value = mock_facade
                
                # Register tools to get the manage_context function
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
                
                # Act
                result = manage_context(
                    action="resolve",
                    level="task",
                    context_id=task_id,
                    include_inherited=True
                )
            
                # Assert - Check structure matches frontend expectations
                assert result["success"] is True
                # After standardization by StandardResponseFormatter, data is under 'data' field
                data = result.get("data", {})
                context = data.get("resolved_context") or data.get("context_data") or data.get("context")
                assert context is not None, f"No context found in result: {result}"
                
                # Verify inheritance data is present
                assert "_inheritance" in context
                assert context["_inheritance"]["chain"] == ["global", "project", "branch", "task"]
                assert "global_settings" in context
                assert "project_settings" in context
                assert "branch_settings" in context