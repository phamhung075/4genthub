"""
Common DTOs for Task Management
"""
from .agent_role import AgentRole
from .task_context import TaskContext
from .task_progress_info import TaskProgressInfo
from .validation_result import ValidationResult

__all__ = [
    "AgentRole",
    "TaskContext",
    "TaskProgressInfo",
    "ValidationResult",
]
