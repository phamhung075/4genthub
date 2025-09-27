"""Response DTO for create task operations"""

from dataclasses import dataclass
from typing import Optional
from .task_response import TaskResponse

@dataclass
class CreateTaskResponse:
    """Response DTO for create task operations"""
    success: bool
    task: TaskResponse
    message: str = ""
    
    @classmethod
    def success_response(cls, task: TaskResponse, message: str = "Task created successfully") -> 'CreateTaskResponse':
        """Create a successful response"""
        return cls(success=True, task=task, message=message)
    
    @classmethod
    def error_response(cls, message: str, task: Optional[TaskResponse] = None) -> 'CreateTaskResponse':
        """Create an error response"""
        return cls(success=False, task=task, message=message) 