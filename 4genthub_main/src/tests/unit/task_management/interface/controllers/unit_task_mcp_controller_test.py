"""Test suite for TaskMCPController.

Tests the task MCP controller including:
- Tool registration and MCP integration
- CRUD operations for tasks
- Task search and filtering
- Progress tracking and completion
- Authentication and user context
- Error handling and validation
- Workflow guidance integration
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.services.response_enrichment_service import ResponseEnrichmentService
from fastmcp.task_management.application.services.parameter_enforcement_service import ParameterEnforcementService
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestTaskMCPController:
    """Test cases for TaskMCPController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock(spec=TaskFacadeFactory)
        self.mock_facade = Mock(spec=TaskApplicationFacade)
        self.mock_facade_factory.create_task_facade.return_value = self.mock_facade
        self.mock_facade_factory.create_task_facade_with_git_branch_id.return_value = self.mock_facade
        
        self.controller = TaskMCPController(facade_service_or_factory=self.mock_facade_factory)
    
    def test_init(self):
        """Test controller initialization."""
        controller = TaskMCPController(facade_service_or_factory=self.mock_facade_factory)
        
        assert controller._task_facade_factory == self.mock_facade_factory
    
    def test_register_tools(self):
        """Test MCP tool registration."""
        mock_mcp = Mock()
        mock_mcp.tool = Mock()
        
        # Mock the get_manage_task_description function that's actually used
        with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_manage_task_description') as mock_get_desc, \
             patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_manage_task_parameters') as mock_get_params:
            
            mock_get_desc.return_value = "Test task management description"
            mock_get_params.return_value = {
                "properties": {
                    "action": {"description": "Action parameter"},
                    "task_id": {"description": "Task ID parameter"},
                    "git_branch_id": {"description": "Branch ID parameter"},
                    "title": {"description": "Title parameter"},
                    "description": {"description": "Description parameter"},
                    "status": {"description": "Status parameter"},
                    "priority": {"description": "Priority parameter"},
                    "details": {"description": "Details parameter"},
                    "estimated_effort": {"description": "Effort parameter"},
                    "assignees": {"description": "Assignees parameter"},
                    "labels": {"description": "Labels parameter"},
                    "due_date": {"description": "Due date parameter"},
                    "dependencies": {"description": "Dependencies parameter"},
                    "dependency_id": {"description": "Dependency ID parameter"},
                    "context_id": {"description": "Context ID parameter"},
                    "completion_summary": {"description": "Completion summary parameter"},
                    "testing_notes": {"description": "Testing notes parameter"},
                    "query": {"description": "Query parameter"},
                    "limit": {"description": "Limit parameter"},
                    "offset": {"description": "Offset parameter"},
                    "sort_by": {"description": "Sort by parameter"},
                    "sort_order": {"description": "Sort order parameter"},
                    "include_context": {"description": "Include context parameter"},
                    "force_full_generation": {"description": "Force full generation parameter"},
                    "assignee": {"description": "Assignee parameter"},
                    "tag": {"description": "Tag parameter"},
                    "user_id": {"description": "User ID parameter"},
                    "requirements": {"description": "Requirements parameter"},
                    "context": {"description": "Context parameter"},
                    "auto_create_tasks": {"description": "Auto create tasks parameter"},
                    "enable_ai_breakdown": {"description": "Enable AI breakdown parameter"},
                    "enable_smart_assignment": {"description": "Enable smart assignment parameter"},
                    "enable_auto_subtasks": {"description": "Enable auto subtasks parameter"},
                    "ai_requirements": {"description": "AI requirements parameter"},
                    "planning_context": {"description": "Planning context parameter"},
                    "analyze_complexity": {"description": "Analyze complexity parameter"},
                    "suggest_optimizations": {"description": "Suggest optimizations parameter"},
                    "identify_risks": {"description": "Identify risks parameter"},
                    "available_agents": {"description": "Available agents parameter"}
                }
            }
            
            self.controller.register_tools(mock_mcp)
            
            # Verify tool decorator was called
            mock_mcp.tool.assert_called_once()
            # Get the arguments passed to tool decorator
            call_args = mock_mcp.tool.call_args
            if call_args and call_args.kwargs:
                assert 'description' in call_args.kwargs
                assert call_args.kwargs['description'] == "Test task management description"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    def test_get_facade_for_request_with_user_context(self, mock_get_auth_user_id):
        """Test getting facade with user context from JWT."""
        mock_get_auth_user_id.return_value = "jwt-user-123"
        git_branch_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the facade service that the controller now uses
        mock_facade_service = Mock()
        mock_facade_service.get_task_facade.return_value = self.mock_facade
        self.controller._facade_service = mock_facade_service
        
        result = self.controller._get_facade_for_request(git_branch_id=git_branch_id, user_id="jwt-user-123")
        
        assert result == self.mock_facade
        # Verify the facade service was called with correct parameters  
        mock_facade_service.get_task_facade.assert_called_once_with(
            project_id=None,
            git_branch_id=git_branch_id,
            user_id="jwt-user-123"
        )
    
    def test_get_facade_for_request_no_auth_raises_error(self):
        """Test getting facade without facade service raises error."""
        git_branch_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Set facade service to None to trigger the error
        self.controller._facade_service = None
        
        with pytest.raises(ValueError) as exc_info:
            self.controller._get_facade_for_request(git_branch_id=git_branch_id)
        
        assert "FacadeService is required but not provided" in str(exc_info.value)
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_task_create_action(self, mock_get_user_id):
        """Test manage_task with create action."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Setup mock facade to return success response
        self.mock_facade.create_task.return_value = {"success": True, "task": {"id": "task-123", "title": "Test task"}}
        
        # Mock the facade factory to return our mock facade
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test task",
                description="Test description",
                assignees="coding-agent"
            )
        
        # Should return standardized success response
        assert result["success"] is True
        # Verify the facade method was called
        self.mock_facade.create_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_task_search_action(self, mock_get_user_id):
        """Test manage_task with search action."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Setup mock facade to return success response
        self.mock_facade.search_tasks.return_value = {"success": True, "tasks": []}
        
        # Mock the facade factory to return our mock facade
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="search",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                query="test query"
            )
            
            assert result["success"] is True
            # Verify the facade method was called
            self.mock_facade.search_tasks.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_task_next_action(self, mock_get_user_id):
        """Test manage_task with next action."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Setup mock facade to return success response for list_tasks (which is what next action actually calls)
        self.mock_facade.list_tasks.return_value = {
            "success": True, 
            "tasks": [{"id": "next-task-123", "title": "Next task"}]
        }
        # Setup for the subsequent get_task call
        self.mock_facade.get_task.return_value = {
            "success": True, 
            "task": {"id": "next-task-123", "title": "Next task"}
        }
        
        # Mock the facade factory to return our mock facade
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="next",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                include_context=True
            )
            
            assert result["success"] is True
            # Verify the facade methods were called
            self.mock_facade.list_tasks.assert_called_once()
            self.mock_facade.get_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_manage_task_unknown_action(self, mock_get_user_id):
        """Test manage_task with unknown action."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.return_value = self.mock_facade
            
            result = await self.controller.manage_task(
                action="invalid_action",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_create_success(self, mock_get_user_id):
        """Test handling create operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.create_task.return_value = {
            "success": True,
            "task": {"id": "550e8400-e29b-41d4-a716-446655440001", "title": "Test task"}
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test task",
                description="Test description",
                priority="medium",
                assignees="coding-agent"
            )
            
            assert result["success"] is True
            self.mock_facade.create_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_create_missing_title(self, mock_get_user_id):
        """Test create operation with missing title."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title=None,
                description="Test description"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_get_success(self, mock_get_user_id):
        """Test handling get operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.get_task.return_value = {
            "success": True,
            "task": {"id": "550e8400-e29b-41d4-a716-446655440001", "title": "Test task"}
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="get",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440002"
            )
            
            assert result["success"] is True
            self.mock_facade.get_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_get_missing_task_id(self, mock_get_user_id):
        """Test get operation with missing task_id."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="get",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id=None
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_list_success(self, mock_get_user_id):
        """Test handling list operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": [{"id": "550e8400-e29b-41d4-a716-446655440004"}, {"id": "550e8400-e29b-41d4-a716-446655440005"}]
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="list",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                status="todo",
                priority="high",
                limit=10
            )
            
            assert result["success"] is True
            self.mock_facade.list_tasks.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_update_success(self, mock_get_user_id):
        """Test handling update operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.update_task.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="update",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440002",
                title="New title",
                description="New description",
                status="in_progress",
                priority="high",
                details="Details",
                estimated_effort="2 hours",
                assignees="coding-agent",
                labels="backend,api",
                due_date="2024-12-31",
                context_id="context-123"
            )
            
            assert result["success"] is True
            self.mock_facade.update_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_complete_success(self, mock_get_user_id):
        """Test handling complete operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Set up proper mock response structure - complete_task calls facade.update_task
        self.mock_facade.update_task.return_value = {
            "success": True,
            "task": {"id": "550e8400-e29b-41d4-a716-446655440002", "status": "done"},
            "message": "Task completed successfully"
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="complete",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440002",
                completion_summary="Task completed successfully",
                testing_notes="All tests passed"
            )
            
            assert result["success"] is True
            self.mock_facade.update_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_delete_success(self, mock_get_user_id):
        """Test handling delete operation successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.delete_task.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="delete",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440002"
            )
            
            assert result["success"] is True
            self.mock_facade.delete_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_crud_operations_exception(self, mock_get_user_id):
        """Test handling exception in CRUD operations."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = await self.controller.manage_task(
                action="create",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                title="Test task",
                description="description",
                assignees="coding-agent"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_search_operations_success(self, mock_get_user_id):
        """Test handling search operations successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        self.mock_facade.search_tasks.return_value = {
            "success": True,
            "tasks": [{"id": "550e8400-e29b-41d4-a716-446655440004", "title": "Found task"}]
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="search", 
                query="test query", 
                limit=10,
                git_branch_id="550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert result["success"] is True
            self.mock_facade.search_tasks.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_search_operations_missing_query(self, mock_get_user_id):
        """Test search operation with missing query."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="search", 
                query=None, 
                limit=10,
                git_branch_id="550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_search_operations_exception(self, mock_get_user_id):
        """Test handling exception in search operations."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = await self.controller.manage_task(
                action="search",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000", 
                query="test query", 
                limit=10
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_recommendation_operations_success(self, mock_get_user_id):
        """Test handling recommendation operations successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Mock facade.list_tasks to return task list for SearchHandler
        self.mock_facade.list_tasks.return_value = {
            "success": True,
            "tasks": [{"id": "550e8400-e29b-41d4-a716-446655440001", "title": "Next task"}]
        }
        
        # Mock facade.get_task for CRUDHandler call
        self.mock_facade.get_task.return_value = {
            "success": True,
            "task": {"id": "550e8400-e29b-41d4-a716-446655440001", "title": "Next task"}
        }
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="next",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                include_context=True
            )
            
            assert result["success"] is True
            self.mock_facade.list_tasks.assert_called_once()
            self.mock_facade.get_task.assert_called_once()
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_recommendation_operations_exception(self, mock_get_user_id):
        """Test handling exception in recommendation operations."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request') as mock_get_facade:
            mock_get_facade.side_effect = Exception("Test exception")
            
            result = await self.controller.manage_task(
                action="next",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                include_context=True
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_dependency_operations_success(self, mock_get_user_id):
        """Test handling dependency operations successfully."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Mock facade.add_dependency method
        self.mock_facade.add_dependency.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="add_dependency",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440001",
                dependency_id="550e8400-e29b-41d4-a716-446655440003"
            )
            
            assert result["success"] is True
            self.mock_facade.add_dependency.assert_called_once_with("550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440003")
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_dependency_operations_missing_task_id(self, mock_get_user_id):
        """Test dependency operation with missing task_id."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="add_dependency",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id=None,
                dependency_id="550e8400-e29b-41d4-a716-446655440003"
            )
        
        assert result["success"] is False
        assert "task_id" in result["error"]["message"]
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_dependency_operations_missing_dependency_id(self, mock_get_user_id):
        """Test dependency operation with missing dependency_id."""
        mock_get_user_id.return_value = "test-user-123"
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="add_dependency",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440001",
                dependency_id=None
            )
            
        assert result["success"] is False
        assert "dependency_id" in result["error"]["message"]
    
    @patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.get_authenticated_user_id')
    @pytest.mark.asyncio
    async def test_handle_dependency_operations_remove_dependency(self, mock_get_user_id):
        """Test handling remove dependency operation."""
        mock_get_user_id.return_value = "test-user-123"
        
        # Mock facade.remove_dependency method
        self.mock_facade.remove_dependency.return_value = {"success": True}
        
        with patch.object(self.controller, '_get_facade_for_request', return_value=self.mock_facade):
            result = await self.controller.manage_task(
                action="remove_dependency",
                git_branch_id="550e8400-e29b-41d4-a716-446655440000",
                task_id="550e8400-e29b-41d4-a716-446655440001",
                dependency_id="550e8400-e29b-41d4-a716-446655440003"
            )
            
            assert result["success"] is True
            self.mock_facade.remove_dependency.assert_called_once_with("550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440003")
    
    def test_get_task_management_descriptions(self):
        """Test getting task management descriptions."""
        with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.description_loader') as mock_loader:
            mock_loader.get_all_descriptions.return_value = {
                "tasks": {
                    "manage_task": {
                        "description": "Test description",
                        "parameters": {"action": "Action param"}
                    }
                }
            }
            
            result = self.controller._get_task_management_descriptions()
            
            expected = {
                "manage_task": {
                    "description": "Test description",
                    "parameters": {"action": "Action param"}
                }
            }
            assert result == expected
    
    def test_create_missing_field_error(self):
        """Test creating missing field error response."""
        result = self.controller._create_missing_field_error("test_field", "test_action")
        
        assert result["status"] == "failure"
        assert result["error"]["message"] == "Validation failed for field: test_field"
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["operation"] == "test_action"
        assert "validation_details" in result["metadata"]
        assert result["metadata"]["validation_details"]["field"] == "test_field"
    
    def test_create_invalid_action_error(self):
        """Test creating invalid action error response."""
        result = self.controller._create_invalid_action_error("invalid_action")
        
        assert result["status"] == "failure"
        assert result["error"]["message"] == "Validation failed for field: action"
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["operation"] == "unknown_action"
        assert "validation_details" in result["metadata"]
        assert result["metadata"]["validation_details"]["field"] == "action"
        assert "One of:" in result["metadata"]["validation_details"]["expected"]
        assert "Invalid action: invalid_action" in result["metadata"]["validation_details"]["hint"]
    
    def test_missing_field_error_response(self):
        """Test missing field error response structure."""
        result = self.controller._create_missing_field_error("task_id", "get")
        
        assert result["status"] == "failure"
        assert result["error"]["message"] == "Validation failed for field: task_id"
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["operation"] == "get"
        assert "validation_details" in result["metadata"]
        assert result["metadata"]["validation_details"]["field"] == "task_id"
    
    def test_get_task_management_descriptions_flattening(self):
        """Test getting flattened task management descriptions."""
        with patch('fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller.description_loader') as mock_loader:
            mock_loader.get_all_descriptions.return_value = {
                "tasks": {
                    "manage_task": {
                        "description": "Task management description",
                        "parameters": {"action": "Action parameter"}
                    }
                },
                "other_section": {
                    "different_tool": {
                        "description": "Other tool"
                    }
                }
            }
            
            result = self.controller._get_task_management_descriptions()
            
            # Should only include manage_task from nested structure
            expected = {
                "manage_task": {
                    "description": "Task management description",
                    "parameters": {"action": "Action parameter"}
                }
            }
            assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])