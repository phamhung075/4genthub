"""Response DTO for update task operations"""

from __future__ import annotations

from dataclasses import dataclass

from .task_response import TaskResponse


@dataclass
class UpdateTaskResponse:
    """Response DTO for update task operations"""
    success: bool
    task: TaskResponse
    message: str = ""

    @classmethod
    def success_response(cls, task: TaskResponse, message: str = "Task updated successfully") -> UpdateTaskResponse:
        """Create a successful response"""
        return cls(success=True, task=task, message=message)

    @classmethod
    def error_response(cls, message: str, task: TaskResponse | None = None) -> UpdateTaskResponse:
        """Create an error response"""
        return cls(success=False, task=task, message=message) 