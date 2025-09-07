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
from ..application.factories.task_facade_factory import TaskFacadeFactory
from ..application.factories.subtask_facade_factory import SubtaskFacadeFactory
# Legacy context factories removed - now using unified context system
from ..application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from ..application.factories.project_facade_factory import ProjectFacadeFactory
from ..application.factories.git_branch_facade_factory import GitBranchFacadeFactory

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
from .controllers.task_mcp_controller import TaskMCPController
from .controllers.subtask_mcp_controller import SubtaskMCPController
from .controllers.unified_context_controller import UnifiedContextMCPController
from .controllers.project_mcp_controller import ProjectMCPController
from .controllers.git_branch_mcp_controller import GitBranchMCPController
from .controllers.agent_mcp_controller import AgentMCPController
from .controllers.claude_agent_controller import ClaudeAgentMCPController
from .controllers.call_agent_mcp_controller import CallAgentMCPController
from .controllers.compliance_mcp_controller import ComplianceMCPController
from .controllers.file_resource_mcp_controller import FileResourceMCPController
from .controllers.rule_orchestration_controller import RuleOrchestrationController

# Vision System Enhanced Controllers
# Enhanced task controller removed - functionality merged into TaskMCPController
from .controllers.workflow_hint_enhancer import WorkflowHintEnhancer


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
        
        # Initialize facade factories
        # Use hierarchical context facade factory for new context system
        # Note: This will be properly initialized later with session_factory if database is available
        self._unified_context_facade_factory = None
        self._context_facade_factory = None
        
        # Initialize project and git branch factories with error handling
        try:
            self._project_facade_factory = ProjectFacadeFactory()
        except Exception as e:
            logger.warning(f"Could not initialize ProjectFacadeFactory: {e}")
            self._project_facade_factory = None
            
        try:
            self._git_branch_facade_factory = GitBranchFacadeFactory()
        except Exception as e:
            logger.warning(f"Could not initialize GitBranchFacadeFactory: {e}")
            self._git_branch_facade_factory = None
        
        # Initialize application factories
        self._task_facade_factory = TaskFacadeFactory(
            self._task_repository_factory,
            self._subtask_repository_factory
        )
        
        self._subtask_facade_factory = SubtaskFacadeFactory(
            self._subtask_repository_factory,
            self._task_repository_factory
        )
        self._subtask_facade = self._subtask_facade_factory.create_subtask_facade()
        
        # Initialize controllers with facades
        self._task_controller = TaskMCPController(
            self._task_facade_factory, 
            self._context_facade_factory,  # Pass context facade factory for auto-context creation
            None,  # project_manager
            self._task_repository_factory
        )
        
        self._subtask_controller = SubtaskMCPController(
            self._subtask_facade_factory,
            task_facade=None,  # Will be set if Vision System is enabled
            context_facade=None,  # Will be set if Vision System is enabled
            task_repository_factory=self._task_repository_factory
        )
        
        # Initialize unified context facade factory if not already done
        # Handle case where database is not available
        if self._session_factory and not self._unified_context_facade_factory:
            self._unified_context_facade_factory = UnifiedContextFacadeFactory(
                session_factory=self._session_factory
            )
            self._context_facade_factory = self._unified_context_facade_factory
            
            # Auto-create global context on system startup
            try:
                global_context_created = self._unified_context_facade_factory.auto_create_global_context()
                if global_context_created:
                    logger.info("Global context initialization completed")
                else:
                    logger.warning("Global context auto-creation failed - hierarchical context operations may not work properly")
            except Exception as e:
                logger.warning(f"Exception during global context initialization: {e}")
                # Continue with startup - this is not a critical failure
            
            # Context controller with unified context system
            self._context_controller = UnifiedContextMCPController(
                unified_context_facade_factory=self._unified_context_facade_factory
            )
        else:
            if not self._session_factory:
                logger.warning("Database not available - context operations will be limited")
            self._context_controller = None
        
        # Initialize controllers only if factories are available
        if self._project_facade_factory:
            self._project_controller = ProjectMCPController(self._project_facade_factory)
        else:
            logger.warning("Project controller not available - skipping initialization")
            self._project_controller = None
        
        if self._git_branch_facade_factory:
            self._git_branch_controller = GitBranchMCPController(self._git_branch_facade_factory)
        else:
            logger.warning("Git branch controller not available - skipping initialization")
            self._git_branch_controller = None
        
        # Agent controller with proper agent facade factory
        from ..application.factories.agent_facade_factory import AgentFacadeFactory
        self._agent_facade_factory = AgentFacadeFactory()
        self._agent_controller = AgentMCPController(self._agent_facade_factory)
        
        # Initialize call agent use case and controller
        cursor_agent_dir = self._path_resolver.get_cursor_agent_dir()
        self._call_agent_use_case = CallAgentUseCase(cursor_agent_dir)
        self._call_agent_controller = CallAgentMCPController(self._call_agent_use_case)
        
        # Initialize Claude agent generation controller
        self._claude_agent_controller = ClaudeAgentMCPController()
        
        # Initialize compliance controller
        self._compliance_controller = ComplianceMCPController(project_root=self._path_resolver.project_root)
        
        # Initialize file resource controller
        self._file_resource_controller = FileResourceMCPController(project_root=self._path_resolver.project_root)
        
        # Initialize cursor rules tools (DDD-compliant)
        from .cursor_rules_tools_ddd import CursorRulesToolsDDD
        self._cursor_rules_tools = CursorRulesToolsDDD()
        
        # Initialize rule orchestration controller
        from ..application.facades.rule_application_facade import RuleApplicationFacade
        rule_app_facade = RuleApplicationFacade(path_resolver=self._path_resolver)
        self._rule_orchestration_facade = rule_app_facade.orchestration_facade
        self._rule_orchestration_controller = RuleOrchestrationController(self._rule_orchestration_facade)
        
        
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
        
        # Register agent tools
        self._register_agent_tools(mcp)
        
        # Register cursor rules tools
        self._register_cursor_rules_tools(mcp)
        
        # Register rule orchestration tools
        self._register_rule_orchestration_tools(mcp)
        
        # Register call agent tool
        self._register_call_agent_tool(mcp)
        
        # Register compliance tools
        self._register_compliance_tools(mcp)
        
        # Register file resource tools
        self._register_file_resource_tools(mcp)
        
        
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
        """Register agent management MCP tools via controller"""
        self._agent_controller.register_tools(mcp)
    
    def _register_cursor_rules_tools(self, mcp: "FastMCP"):
        """Register cursor rules management tools"""
        self._cursor_rules_tools.register_tools(mcp)
    
    def _register_rule_orchestration_tools(self, mcp: "FastMCP"):
        """Register rule orchestration MCP tools via controller"""
        self._rule_orchestration_controller.register_tools(mcp)
    
    def _register_call_agent_tool(self, mcp: "FastMCP"):
        """Register call agent MCP tools via controller"""
        self._call_agent_controller.register_tools(mcp)
    
    def _register_compliance_tools(self, mcp: "FastMCP"):
        """Register compliance management MCP tools via controller"""
        self._compliance_controller.register_tools(mcp)
    
    def _register_file_resource_tools(self, mcp: "FastMCP"):
        """Register file resource MCP tools via controller"""
        self._file_resource_controller.register_resources(mcp)
    
    
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
    
    @property
    def compliance_controller(self) -> ComplianceMCPController:
        """Get the compliance controller for direct access"""
        return self._compliance_controller
    
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
    
    def manage_task(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for task management - delegates to task controller"""
        return self._task_controller.manage_task(**kwargs)
    
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
    
    def manage_compliance(self, **kwargs) -> Dict[str, Any]:
        """Wrapper method for compliance management - delegates to compliance controller"""
        return self._compliance_controller.manage_compliance(**kwargs)
 