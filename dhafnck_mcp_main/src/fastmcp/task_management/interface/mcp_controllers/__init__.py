"""Interface Controllers Package

This package contains MCP controllers that handle interface-specific concerns
while delegating business logic to the application layer.
"""

from .task_mcp_controller.task_mcp_controller import TaskMCPController
from .subtask_mcp_controller.subtask_mcp_controller import SubtaskMCPController
from .dependency_mcp_controller.dependency_mcp_controller import DependencyMCPController
from .unified_context_controller.unified_context_controller import UnifiedContextMCPController
from .project_mcp_controller.project_mcp_controller import ProjectMCPController
from .git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController
from .agent_mcp_controller.agent_mcp_controller import UnifiedAgentMCPController

# Maintain backward compatibility
AgentMCPController = UnifiedAgentMCPController

__all__ = [
    "TaskMCPController",
    "SubtaskMCPController",
    "DependencyMCPController",
    "UnifiedContextMCPController",
    "ProjectMCPController",
    "GitBranchMCPController",
    "UnifiedAgentMCPController",
    "AgentMCPController",  # Backward compatibility alias
] 