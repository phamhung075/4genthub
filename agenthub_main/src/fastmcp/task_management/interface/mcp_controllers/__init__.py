"""Interface Controllers Package

This package contains MCP controllers that handle interface-specific concerns
while delegating business logic to the application layer.
"""

# Import using 'from ... import' syntax
from .task_mcp_controller.task_mcp_controller import TaskMCPController
from .subtask_mcp_controller.subtask_mcp_controller import SubtaskMCPController
from .dependency_mcp_controller.dependency_mcp_controller import DependencyMCPController
from .unified_context_controller.unified_context_controller import UnifiedContextMCPController
from .project_mcp_controller.project_mcp_controller import ProjectMCPController
from .git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from .call_agent_mcp_controller.call_agent_mcp_controller import CallAgentMCPController
from .agent_mcp_controller import AgentMCPController, UnifiedAgentMCPController

# Note: Internal subpackages (task_mcp_controller, auth_helper, etc.) are exposed
# as module attributes, but __all__ below controls what gets imported with "import *"

__all__ = [
    "TaskMCPController",
    "SubtaskMCPController",
    "DependencyMCPController",
    "UnifiedContextMCPController",
    "ProjectMCPController",
    "GitBranchMCPController",
    "UnifiedAgentMCPController",
    "AgentMCPController",  # Backward compatibility alias
    "CallAgentMCPController",
]
