"""DDD-Compliant MCP Tools

This module demonstrates the proper DDD architecture for MCP tools by:
- Using controllers that delegate to application facades
- Removing business logic from the interface layer
- Following proper dependency direction (Interface → Application → Domain ← Infrastructure)
- Providing clean separation of concerns

This serves as a replacement for the existing consolidated_mcp_tools.py that
violates DDD principles.
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ...server.server import FastMCP

# Application layer imports (proper DDD dependency injection)
from ..application.services.facade_service import FacadeService

# Import facades for type hints only
if TYPE_CHECKING:
    from ..application.facades.task_application_facade import TaskApplicationFacade


# Infrastructure layer imports (proper DDD dependency direction)
from ..infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from ..infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
from ..application.use_cases.call_agent import CallAgentUseCase

# Infrastructure layer imports (proper DDD dependency direction)
from ..infrastructure.configuration.tool_config import ToolConfig
from ..infrastructure.utilities.path_resolver import PathResolver

# Interface layer imports (same layer, acceptable)
from .mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
from .mcp_controllers.subtask_mcp_controller.subtask_mcp_controller import SubtaskMCPController
from .mcp_controllers.unified_context_controller.unified_context_controller import UnifiedContextMCPController
from .mcp_controllers.project_mcp_controller.project_mcp_controller import ProjectMCPController
from .mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from .mcp_controllers.agent_mcp_controller.agent_mcp_controller import AgentMCPController
# Claude agent controller removed
from .mcp_controllers.call_agent_mcp_controller.call_agent_mcp_controller import CallAgentMCPController

# Vision System Enhanced Controllers
# Enhanced task controller removed - functionality merged into TaskMCPController
from .mcp_controllers.workflow_hint_enhancer.workflow_hint_enhancer import WorkflowHintEnhancer


# Application layer imports (proper DDD dependency direction) 
# Use case imports for tool registration (call_agent)

logger = logging.getLogger(__name__)


class DDDCompliantMCPTools:
    """
    DDD-compliant MCP tools that follow proper architectural patterns.
    
    This class demonstrates the correct way to structure MCP tools by:
    - Using dependency injection for proper inversion of control
    - Delegating business logic to application facades
    - Keeping interface concerns separate from business logic
    - Following proper DDD layering principles
    """
    
    def __init__(self, 
                 projects_file_path: Optional[str] = None,  # Kept for backward compatibility, ignored
                 config_overrides: Optional[Dict[str, Any]] = None,
                 enable_vision_system: bool = True):
        """
        Initialize DDD-compliant MCP tools.
        
        Args:
            projects_file_path: Deprecated parameter kept for backward compatibility (ignored)
            config_overrides: Optional configuration overrides
            enable_vision_system: Enable Vision System features (default: True)
        """
        logger.info("Initializing DDD-compliant MCP tools...")
        
        # Initialize configuration and infrastructure
        self._config = ToolConfig(config_overrides)
        self._path_resolver = PathResolver()
        self._task_repository_factory = TaskRepositoryFactory()
        self._subtask_repository_factory = SubtaskRepositoryFactory()
        
        # Initialize session factory for unified context controller
        # Make database optional - tools will register but may have limited functionality
        self._session_factory = None
        try:
            from ..infrastructure.database.database_config import get_db_config
            db_config = get_db_config()
            self._session_factory = db_config.SessionLocal
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            logger.warning("Tools will be registered with limited functionality")
            logger.warning("Some operations may fail without a configured database")
        
        # Initialize facade service for all facades
        self._facade_service = FacadeService.get_instance()
        
        # Initialize controllers with facade service
        self._task_controller = TaskMCPController(
            facade_service=self._facade_service,
            workflow_hint_enhancer=None
        )
        
        self._subtask_controller = SubtaskMCPController(
            facade_service=self._facade_service,
            task_facade=None,  # Will be set if Vision System is enabled
            context_facade=None,  # Will be set if Vision System is enabled
            task_repository_factory=self._task_repository_factory
        )
        
        # Auto-create global context on system startup with a system user ID
        if self._session_factory:
            try:
                # Get system user ID from environment for startup context creation
                # This ensures the context system is properly initialized
                import os
                system_user_id = os.getenv("SYSTEM_USER_ID")
                if not system_user_id:
                    raise ValueError("SYSTEM_USER_ID environment variable is required for system initialization")
                
                # Get context facade from service
                context_facade = self._facade_service.get_context_facade(user_id=system_user_id)
                # Global context auto-creation is handled by the facade
                logger.info(f"Global context initialization completed for system user: {system_user_id}")
            except Exception as e:
                logger.debug(f"Global context initialization skipped: {e}")
                # Continue with startup - this is not a critical failure
            
            # Context controller with facade service
            self._context_controller = UnifiedContextMCPController(
                facade_service=self._facade_service
            )
        else:
            if not self._session_factory:
                logger.warning("Database not available - context operations will be limited")
            self._context_controller = None
        
        # Initialize controllers with facade service
        self._project_controller = ProjectMCPController(
            facade_service=self._facade_service
        )
        
        self._git_branch_controller = GitBranchMCPController(
            facade_service=self._facade_service
        )
        
        # Agent controller with facade service
        self._agent_controller = AgentMCPController(
            facade_service=self._facade_service
        )
        
        # Initialize call agent use case and controller
        cursor_agent_dir = self._path_resolver.get_cursor_agent_dir()
        self._call_agent_use_case = CallAgentUseCase(cursor_agent_dir)
        self._call_agent_controller = CallAgentMCPController(self._call_agent_use_case)
        
        # Claude agent controller removed
        
        
        
        
        # Initialize cursor rules tools (DDD-compliant)
        # FIXED: Commented out non-existent module import
        # from .cursor_rules_tools_ddd import CursorRulesToolsDDD
        # self._cursor_rules_tools = CursorRulesToolsDDD()
        self._cursor_rules_tools = None  # Temporarily disabled until module is available
        
        
        
        # Vision System Disabled (components removed as requested)
        self._enable_vision_system = False
        logger.info("Vision System disabled - using standard workflow without enhanced features")
        
        # Initialize service placeholders (Vision System removed)
        self._vision_enrichment_service = None
        self._vision_analytics_service = None
        self._hint_generation_service = None
        self._workflow_analysis_service = None
        self._progress_tracking_service = None
        self._agent_coordination_service = None
        self._work_distribution_service = None
        
        # Initialize workflow hint enhancer (independent of Vision System)
        self._workflow_hint_enhancer = WorkflowHintEnhancer()
        
        logger.info("Standard workflow controllers initialized successfully.")
        
        logger.info("DDD-compliant MCP tools initialized successfully.")
    
    def register_tools(self, mcp: "FastMCP"):
        """
        Register MCP tools with the FastMCP server.

        This method demonstrates proper tool registration using controllers
        that delegate to application facades.

        Note: This method delegates to application facades for all business logic,
        ensuring DDD-compliant separation of concerns.
        """
        logger.info("Registering DDD-compliant MCP tools...")
        
        # Schema monkey patches removed - they cause "unknown" type display in MCP tools
        # MCP cannot handle anyOf constructs properly - use clean parameter patterns instead
        logger.info("Using clean parameter patterns instead of schema monkey patches for MCP compatibility")
        
        # Register task management tools
        self._register_task_tools(mcp)
        
        # Register subtask management tools
        self._register_subtask_tools(mcp)
        
        # Register context management tools
        self._register_context_tools(mcp)
        
        # Register project management tools
        self._register_project_tools(mcp)
        
        # Register git branch management tools
        self._register_git_branch_tools(mcp)
        
        # Register unified agent management and invocation tools
        self._register_agent_tools(mcp)
        
        # Register cursor rules tools
        self._register_cursor_rules_tools(mcp)
        
        # Call agent functionality now integrated into unified agent controller
        # self._register_call_agent_tool(mcp)  # Deprecated - functionality merged
        
        
        
        
        # Register Vision System enhanced tools if enabled
        if self._enable_vision_system:
            logger.info("Registering Vision System enhanced tools...")
            self._register_vision_enhanced_tools(mcp)
        
        logger.info("DDD-compliant MCP tools registered successfully.")
    
    
    def _register_task_tools(self, mcp: "FastMCP"):
        """Register task management MCP tools via controller"""
        self._task_controller.register_tools(mcp)
    
    def _register_subtask_tools(self, mcp: "FastMCP"):
        """Register subtask management MCP tools via controller"""
        self._subtask_controller.register_tools(mcp)
    
    def _register_context_tools(self, mcp: "FastMCP"):
        """Register context management MCP tools via controller"""
        if self._context_controller:
            self._context_controller.register_tools(mcp)
        else:
            logger.warning("Context controller not available - skipping context tool registration")
    
    def _register_project_tools(self, mcp: "FastMCP"):
        """Register project management MCP tools via controller"""
        if self._project_controller:
            self._project_controller.register_tools(mcp)
        else:
            logger.warning("Project controller not available - skipping project tool registration")
    
    def _register_git_branch_tools(self, mcp: "FastMCP"):
        """Register git branch management MCP tools via controller"""
        if self._git_branch_controller:
            self._git_branch_controller.register_tools(mcp)
        else:
            logger.warning("Git branch controller not available - skipping git branch tool registration")
    
    def _register_agent_tools(self, mcp: "FastMCP"):
        """Register unified agent management and invocation MCP tools via controller"""
        # FIXED: Use correct attribute name
        if hasattr(self, '_agent_controller'):
            self._agent_controller.register_tools(mcp)
        else:
            logger.warning("Agent controller not initialized")
    
    def _register_cursor_rules_tools(self, mcp: "FastMCP"):
        """Register cursor rules management tools"""
        # FIXED: Skip registration when cursor_rules_tools is not available
        if self._cursor_rules_tools:
            self._cursor_rules_tools.register_tools(mcp)
        else:
            logger.info("Cursor rules tools disabled - module not available")
    
    def _register_call_agent_tool(self, mcp: "FastMCP"):
        """Register call agent MCP tools via controller - DEPRECATED: now handled by unified agent controller"""
        # No longer needed - call functionality integrated into unified agent controller
        logger.info("Call agent functionality is now integrated into the unified agent controller")
        pass
    
    
    
    
    def _register_vision_enhanced_tools(self, mcp: "FastMCP"):
        """Register Vision System enhanced tools"""
        # DISABLED: Enhanced task tools should be merged into manage_task action
        # per user requirement - these duplicate functionality
        # self._enhanced_task_controller.register_enhanced_tools(mcp)
        
        # Context enforcing tools are now integrated into task controller
        # and registered automatically when Vision System is enabled
        
        # Note: Subtask progress tools are now integrated into the main subtask controller
        # and are automatically registered when Vision System is enabled
        
        # Register workflow hint enhancement
        # Note: WorkflowHintEnhancer is designed to enhance individual responses,
        # not register tools with MCP. It should be used within other controllers
        # to enhance their responses.
        # self._workflow_hint_enhancer.enhance_all_responses(mcp)
        
        logger.info("Vision System enhanced tools registered successfully.")
    
    # Properties for backward compatibility and testing
    @property
    def task_controller(self) -> TaskMCPController:
        """Get the task controller for direct access"""
        return self._task_controller
    
    @property
    def subtask_controller(self) -> SubtaskMCPController:
        """Get the subtask controller for direct access"""
        return self._subtask_controller
    
    @property
    def context_controller(self) -> UnifiedContextMCPController:
        """Get the context controller for direct access"""
        return self._context_controller
    
    @property
    def project_controller(self) -> ProjectMCPController:
        """Get the project controller for direct access"""
        return self._project_controller
    
    @property
    def git_branch_controller(self) -> GitBranchMCPController:
        """Get the git branch controller for direct access"""
        return self._git_branch_controller
    
    @property
    def agent_controller(self) -> AgentMCPController:
        """Get the agent controller for direct access"""
        return self._agent_controller
    
    @property
    def call_agent_controller(self) -> CallAgentMCPController:
        """Get the call agent controller for direct access"""
        return self._call_agent_controller
    
    
    # Vision System Properties
    @property
    def enhanced_task_controller(self) -> Optional[TaskMCPController]:
        """Get the task controller (includes enhanced functionality if Vision System is enabled)"""
        return self._task_controller if self._enable_vision_system else None
    
    @property
    def context_enforcing_controller(self) -> Optional[TaskMCPController]:
        """Get the task controller (includes context enforcing if Vision System is enabled)"""
        # Context enforcing is now integrated into TaskMCPController
        return self._task_controller if self._enable_vision_system else None
    
    @property
    def subtask_progress_controller(self) -> Optional[SubtaskMCPController]:
        """Get the subtask controller (includes progress tracking if Vision System is enabled)"""
        return self._subtask_controller
    
    @property
    def workflow_hint_enhancer(self) -> Optional[WorkflowHintEnhancer]:
        """Get the workflow hint enhancer if Vision System is enabled"""
        return getattr(self, '_workflow_hint_enhancer', None)
    
    @property
    def vision_enrichment_service(self):
        """Get the vision enrichment service if Vision System is enabled"""
        return getattr(self, '_vision_enrichment_service', None)
    
    @property
    def vision_analytics_service(self):
        """Get the vision analytics service if Vision System is enabled"""
        return getattr(self, '_vision_analytics_service', None)
    
    # Wrapper methods for backward compatibility with tests and legacy code
    def manage_project(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for project management - delegates to project controller"""
        return self._project_controller.manage_project(**kwargs)
    
    def manage_git_branch(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for git branch management - delegates to git branch controller"""
        return self._git_branch_controller.manage_git_branch(**kwargs)
    
    async def manage_task(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for task management - delegates to task controller"""
        return await self._task_controller.manage_task(**kwargs)
    
    def manage_subtask(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for subtask management - delegates to subtask controller"""
        return self._subtask_controller.manage_subtask(**kwargs)
    
    def manage_context(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for context management - delegates to context controller"""
        return self._context_controller.manage_context(**kwargs)
    
    def manage_agent(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for agent management - delegates to agent controller"""
        return self._agent_controller.manage_agent(**kwargs)
    
    def call_agent(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for agent calls - delegates to call agent controller"""
        return self._call_agent_controller.call_agent(**kwargs)
    
 