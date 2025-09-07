"""
Test suite for DDDCompliantMCPTools.

Tests the DDD-compliant MCP tools initialization, registration, and
proper architectural patterns with mock dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from contextlib import ExitStack


class TestDDDCompliantMCPTools:
    """Test suite for DDDCompliantMCPTools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_overrides = {"test_config": "value"}

    def test_initialization_success(self):
        """Test successful initialization of DDD-compliant MCP tools."""
        # Mock database configuration
        mock_session_factory = Mock()
        mock_db_config = Mock()
        mock_db_config.SessionLocal = mock_session_factory
        
        with ExitStack() as stack:
            # Patch all dependencies using ExitStack to avoid nesting limits
            stack.enter_context(patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.PathResolver'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.AgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentUseCase'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ClaudeAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ComplianceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FileResourceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.RuleOrchestrationController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.WorkflowHintEnhancer'))
            
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            
            tools = DDDCompliantMCPTools(
                config_overrides=self.config_overrides,
                enable_vision_system=False
            )
            
            # Verify initialization
            assert tools is not None

    def test_initialization_without_database(self):
        """Test initialization without database connection."""
        with ExitStack() as stack:
            # Patch all dependencies, database config raises exception
            stack.enter_context(patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', side_effect=Exception("No database")))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.PathResolver'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.AgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentUseCase'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ClaudeAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ComplianceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FileResourceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.RuleOrchestrationController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.WorkflowHintEnhancer'))
            
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            
            tools = DDDCompliantMCPTools(enable_vision_system=False)
            
            # Verify initialization without database
            assert tools is not None
            assert tools._session_factory is None

    def test_register_tools_basic(self):
        """Test basic tool registration."""
        with ExitStack() as stack:
            # Setup minimal patching for basic functionality test
            stack.enter_context(patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', side_effect=Exception("No database")))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.PathResolver'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.AgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentUseCase'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ClaudeAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ComplianceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FileResourceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.RuleOrchestrationController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.WorkflowHintEnhancer'))
            
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            
            mock_mcp = Mock()
            tools = DDDCompliantMCPTools(enable_vision_system=False)
            
            # Mock controllers to avoid AttributeError  
            tools._task_controller = Mock()
            tools._subtask_controller = Mock()
            tools._context_controller = Mock()
            tools._project_controller = Mock()
            tools._git_branch_controller = Mock()
            tools._agent_controller = Mock()
            tools._call_agent_controller = Mock()
            tools._compliance_controller = Mock()
            tools._file_resource_controller = Mock()
            tools._rule_orchestration_controller = Mock()
            
            # Test registration
            tools.register_tools(mock_mcp)
            
            # Verify some controllers were called
            tools._task_controller.register_tools.assert_called_once_with(mock_mcp)
            tools._subtask_controller.register_tools.assert_called_once_with(mock_mcp)

    def test_basic_wrapper_methods(self):
        """Test basic wrapper methods."""
        with ExitStack() as stack:
            # Setup minimal patching for basic functionality test
            stack.enter_context(patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', side_effect=Exception("No database")))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ToolConfig'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.PathResolver'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskRepositoryFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchFacadeFactory'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.TaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.SubtaskMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.UnifiedContextMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ProjectMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.GitBranchMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.AgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentUseCase'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.CallAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ClaudeAgentMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.ComplianceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.FileResourceMCPController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.RuleOrchestrationController'))
            stack.enter_context(patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.WorkflowHintEnhancer'))
            
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            
            tools = DDDCompliantMCPTools(enable_vision_system=False)
            
            # Mock controllers
            mock_task_controller = Mock()
            mock_task_controller.manage_task.return_value = {"success": True}
            tools._task_controller = mock_task_controller
            
            # Test wrapper method
            result = tools.manage_task(action="test")
            assert result == {"success": True}
            mock_task_controller.manage_task.assert_called_once_with(action="test")