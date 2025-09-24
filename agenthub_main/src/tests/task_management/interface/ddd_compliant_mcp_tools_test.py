"""Test suite for DDDCompliantMCPTools.

Tests the DDD-compliant MCP tools including:
- Tool initialization and configuration
- Controller registration and delegation
- Facade service integration
- Vision System feature toggling
- Backward compatibility methods
- Error handling and resilience
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, Optional
import os

from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.subtask_mcp_controller import SubtaskMCPController
from fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller import UnifiedContextMCPController
from fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller import ProjectMCPController
from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller.agent_mcp_controller import AgentMCPController
from fastmcp.task_management.interface.mcp_controllers.call_agent_mcp_controller.call_agent_mcp_controller import CallAgentMCPController
from fastmcp.task_management.interface.mcp_controllers.workflow_hint_enhancer.workflow_hint_enhancer import WorkflowHintEnhancer


class TestDDDCompliantMCPTools:
    """Test cases for DDDCompliantMCPTools."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset FacadeService singleton
        if hasattr(FacadeService, '_instance'):
            FacadeService._instance = None
        
        # Set required environment variable for tests
        os.environ['SYSTEM_USER_ID'] = 'test-system-user'
    
    def teardown_method(self):
        """Clean up after tests."""
        # Reset singleton
        if hasattr(FacadeService, '_instance'):
            FacadeService._instance = None
        
        # Clean up environment
        if 'SYSTEM_USER_ID' in os.environ:
            del os.environ['SYSTEM_USER_ID']
    
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService')
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig')
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.PathResolver')
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskRepositoryFactory')
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskRepositoryFactory')
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentUseCase')
    def test_init_default_configuration(self, mock_call_agent_use_case, mock_subtask_repo_factory, 
                                       mock_task_repo_factory, mock_path_resolver, 
                                       mock_tool_config, mock_facade_service):
        """Test initialization with default configuration."""
        # Mock database configuration
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_db_config:
            mock_session_factory = Mock()
            mock_db_config.return_value.SessionLocal = mock_session_factory
            
            # Mock facade service
            mock_facade_instance = Mock()
            mock_context_facade = Mock()
            mock_facade_instance.get_context_facade.return_value = mock_context_facade
            mock_facade_service.get_instance.return_value = mock_facade_instance
            
            # Initialize tools
            tools = DDDCompliantMCPTools()
            
            # Verify initialization
            assert tools._enable_vision_system is False  # Vision System disabled by default
            mock_tool_config.assert_called_once_with(None)
            mock_path_resolver.assert_called_once()
            mock_task_repo_factory.assert_called_once()
            mock_subtask_repo_factory.assert_called_once()
            mock_facade_service.get_instance.assert_called_once()
            
            # Verify controllers are initialized
            assert isinstance(tools._task_controller, TaskMCPController)
            assert isinstance(tools._subtask_controller, SubtaskMCPController)
            assert isinstance(tools._context_controller, UnifiedContextMCPController)
            assert isinstance(tools._project_controller, ProjectMCPController)
            assert isinstance(tools._git_branch_controller, GitBranchMCPController)
            assert isinstance(tools._agent_controller, AgentMCPController)
            assert isinstance(tools._call_agent_controller, CallAgentMCPController)
            assert isinstance(tools._workflow_hint_enhancer, WorkflowHintEnhancer)
    
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService')
    def test_init_without_database(self, mock_facade_service):
        """Test initialization when database is not available."""
        # Mock database configuration to fail
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_db_config:
            mock_db_config.side_effect = Exception("Database not configured")
            
            # Mock facade service
            mock_facade_instance = Mock()
            mock_facade_service.get_instance.return_value = mock_facade_instance
            
            # Initialize tools - should not fail
            tools = DDDCompliantMCPTools()
            
            # Verify session factory is None
            assert tools._session_factory is None
            assert tools._context_controller is None
    
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService')
    def test_init_with_config_overrides(self, mock_facade_service):
        """Test initialization with configuration overrides."""
        config_overrides = {
            "test_mode": True,
            "custom_setting": "value"
        }
        
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig') as mock_tool_config:
            mock_facade_instance = Mock()
            mock_facade_service.get_instance.return_value = mock_facade_instance
            
            tools = DDDCompliantMCPTools(config_overrides=config_overrides)
            
            mock_tool_config.assert_called_once_with(config_overrides)
    
    @patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService')
    def test_init_without_system_user_id(self, mock_facade_service):
        """Test initialization when SYSTEM_USER_ID is not set."""
        # Remove SYSTEM_USER_ID
        if 'SYSTEM_USER_ID' in os.environ:
            del os.environ['SYSTEM_USER_ID']
        
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_db_config:
            mock_session_factory = Mock()
            mock_db_config.return_value.SessionLocal = mock_session_factory
            
            # Mock facade service
            mock_facade_instance = Mock()
            mock_facade_service.get_instance.return_value = mock_facade_instance
            
            # Initialize tools - should handle missing SYSTEM_USER_ID gracefully
            tools = DDDCompliantMCPTools()
            
            # Should continue without global context initialization
            assert tools._session_factory is not None
    
    def test_register_tools(self):
        """Test MCP tool registration."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock MCP server
            mock_mcp = Mock()
            
            # Mock controller register_tools methods
            tools._task_controller.register_tools = Mock()
            tools._subtask_controller.register_tools = Mock()
            tools._context_controller = Mock()
            tools._context_controller.register_tools = Mock()
            tools._project_controller.register_tools = Mock()
            tools._git_branch_controller.register_tools = Mock()
            tools._agent_controller.register_tools = Mock()
            
            # Register tools
            tools.register_tools(mock_mcp)
            
            # Verify all controllers registered their tools
            tools._task_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._subtask_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._context_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._project_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._git_branch_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._agent_controller.register_tools.assert_called_once_with(mock_mcp)
    
    def test_register_tools_without_context_controller(self):
        """Test tool registration when context controller is not available."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            tools._context_controller = None
            
            # Mock MCP server
            mock_mcp = Mock()
            
            # Mock other controllers
            tools._task_controller.register_tools = Mock()
            tools._subtask_controller.register_tools = Mock()
            tools._project_controller.register_tools = Mock()
            tools._git_branch_controller.register_tools = Mock()
            tools._agent_controller.register_tools = Mock()
            
            # Register tools - should handle missing context controller
            tools.register_tools(mock_mcp)
            
            # Verify other controllers still registered
            tools._task_controller.register_tools.assert_called_once()
    
    def test_property_accessors(self):
        """Test property accessor methods."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Test controller properties
            assert tools.task_controller == tools._task_controller
            assert tools.subtask_controller == tools._subtask_controller
            assert tools.context_controller == tools._context_controller
            assert tools.project_controller == tools._project_controller
            assert tools.git_branch_controller == tools._git_branch_controller
            assert tools.agent_controller == tools._agent_controller
            assert tools.call_agent_controller == tools._call_agent_controller
            
            # Test Vision System properties (should be None when disabled)
            assert tools.enhanced_task_controller is None
            assert tools.context_enforcing_controller is None
            assert tools.subtask_progress_controller == tools._subtask_controller
            assert tools.workflow_hint_enhancer == tools._workflow_hint_enhancer
            assert tools.vision_enrichment_service is None
            assert tools.vision_analytics_service is None
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_manage_task(self):
        """Test backward compatibility method for manage_task."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method with async function
            mock_result = {"status": "success", "task_id": "123"}
            async def async_mock(**kwargs):
                return mock_result
            tools._task_controller.manage_task = Mock(side_effect=async_mock)
            
            # Call wrapper method
            kwargs = {"action": "create", "title": "Test task"}
            result = await tools.manage_task(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._task_controller.manage_task.assert_called_once_with(**kwargs)
    
    def test_backward_compatibility_manage_subtask(self):
        """Test backward compatibility method for manage_subtask."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method
            mock_result = {"status": "success", "subtask_id": "456"}
            tools._subtask_controller.manage_subtask = Mock(return_value=mock_result)
            
            # Call wrapper method
            kwargs = {"action": "create", "task_id": "123", "title": "Test subtask"}
            result = tools.manage_subtask(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._subtask_controller.manage_subtask.assert_called_once_with(**kwargs)
    
    def test_backward_compatibility_manage_context(self):
        """Test backward compatibility method for manage_context."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()

            # Mock the permission check to always allow
            with patch.object(tools._context_controller, '_check_context_permissions') as mock_check_perms:
                mock_check_perms.return_value = (True, None)

                # Call wrapper method with user_id to bypass authentication error
                kwargs = {"action": "create", "level": "task", "context_id": "123", "user_id": "test-user"}
                result = tools.manage_context(**kwargs)

                # Verify that the call succeeds and returns expected structure
                assert isinstance(result, dict)
                assert result.get("success") is True
                assert "data" in result
                assert "meta" in result

                # Verify permission check was called with the correct arguments
                # The user ID will be converted to UUID format by the authentication service
                assert mock_check_perms.called
                call_args = mock_check_perms.call_args[0]
                assert call_args[0] == "create"  # action
                assert len(call_args[1]) == 36  # user_id should be UUID format
                assert call_args[2] == "123"  # context_id
    
    def test_backward_compatibility_manage_project(self):
        """Test backward compatibility method for manage_project."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method
            mock_result = {"status": "success", "project_id": "proj-123"}
            tools._project_controller.manage_project = Mock(return_value=mock_result)
            
            # Call wrapper method
            kwargs = {"action": "create", "name": "Test Project"}
            result = tools.manage_project(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._project_controller.manage_project.assert_called_once_with(**kwargs)
    
    def test_backward_compatibility_manage_git_branch(self):
        """Test backward compatibility method for manage_git_branch."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method
            mock_result = {"status": "success", "git_branch_id": "branch-123"}
            tools._git_branch_controller.manage_git_branch = Mock(return_value=mock_result)
            
            # Call wrapper method
            kwargs = {"action": "create", "project_id": "proj-123", "git_branch_name": "feature/test"}
            result = tools.manage_git_branch(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._git_branch_controller.manage_git_branch.assert_called_once_with(**kwargs)
    
    def test_backward_compatibility_manage_agent(self):
        """Test backward compatibility method for manage_agent."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method
            mock_result = {"status": "success", "agent_id": "agent-123"}
            tools._agent_controller.manage_agent = Mock(return_value=mock_result)
            
            # Call wrapper method
            kwargs = {"action": "register", "project_id": "proj-123", "name": "Test Agent"}
            result = tools.manage_agent(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._agent_controller.manage_agent.assert_called_once_with(**kwargs)
    
    def test_backward_compatibility_call_agent(self):
        """Test backward compatibility method for call_agent."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Mock controller method
            mock_result = {"status": "success", "response": "Agent called"}
            tools._call_agent_controller.call_agent = Mock(return_value=mock_result)
            
            # Call wrapper method
            kwargs = {"agent_id": "agent-123", "action": "execute"}
            result = tools.call_agent(**kwargs)
            
            # Verify delegation
            assert result == mock_result
            tools._call_agent_controller.call_agent.assert_called_once_with(**kwargs)
    
    def test_cursor_rules_tools_disabled(self):
        """Test that cursor rules tools are properly disabled when module is not available."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Verify cursor rules tools is None
            assert tools._cursor_rules_tools is None
            
            # Mock MCP server
            mock_mcp = Mock()
            
            # Register cursor rules tools - should handle None gracefully
            tools._register_cursor_rules_tools(mock_mcp)
            
            # No exception should be raised
    
    def test_vision_system_disabled_by_default(self):
        """Test that Vision System is disabled by default."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools()
            
            # Verify Vision System is disabled
            assert tools._enable_vision_system is False
            
            # Verify Vision System services are None
            assert tools._vision_enrichment_service is None
            assert tools._vision_analytics_service is None
            assert tools._hint_generation_service is None
            assert tools._workflow_analysis_service is None
            assert tools._progress_tracking_service is None
            assert tools._agent_coordination_service is None
            assert tools._work_distribution_service is None
    
    def test_deprecated_parameters_backward_compatibility(self):
        """Test that deprecated parameters are properly ignored."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            # Initialize with deprecated projects_file_path parameter
            tools = DDDCompliantMCPTools(projects_file_path="/path/to/projects.json")
            
            # Should initialize successfully, ignoring the deprecated parameter
            assert tools is not None
    
    def test_register_vision_enhanced_tools_when_disabled(self):
        """Test registering Vision System tools when disabled."""
        with patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FacadeService'):
            tools = DDDCompliantMCPTools(enable_vision_system=False)
            
            # Mock MCP server
            mock_mcp = Mock()
            
            # Register Vision System tools - should do nothing when disabled
            tools._register_vision_enhanced_tools(mock_mcp)
            
            # Verify Vision System is still disabled
            assert tools._enable_vision_system is False