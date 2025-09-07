"""Task Domain Exceptions"""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskDomainError(Exception):
    """Base exception for task domain errors"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """Initialize base task domain error."""
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.context = context or {}
        self.recoverable = recoverable


class TaskNotFoundError(TaskDomainError):
    """Raised when a task is not found"""
    
    def __init__(self, message_or_task_id):
        if isinstance(message_or_task_id, str) and "not found" in message_or_task_id:
            # Already a formatted message
            message = message_or_task_id
            # Extract task_id from message if possible
            try:
                import re
                match = re.search(r'Task (\w+) not found', message_or_task_id)
                self.task_id = match.group(1) if match else message_or_task_id
            except:
                self.task_id = message_or_task_id
        else:
            # Raw task_id passed
            self.task_id = message_or_task_id
            message = f"Task with ID {message_or_task_id} not found"
            
        super().__init__(
            message=message,
            error_code="TASK_NOT_FOUND",
            severity=ErrorSeverity.MEDIUM,
            context={"task_id": self.task_id},
            recoverable=False
        )


class InvalidTaskStateError(TaskDomainError):
    """Raised when a task operation is invalid for the current state"""
    
    def __init__(self, message: str):
        super().__init__(message)


class InvalidTaskTransitionError(TaskDomainError):
    """Raised when a task status transition is invalid"""
    
    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Cannot transition from '{current_status}' to '{target_status}'")


class AutoRuleGenerationError(TaskDomainError):
    """Raised when auto rule generation fails"""

    def __init__(self, message: str, original_exception: Exception = None):
        self.original_exception = original_exception
        super().__init__(message)


class AgentNotFoundError(TaskDomainError):
    """Raised when an agent is not found"""
    
    def __init__(self, message: str):
        super().__init__(message)


class ProjectNotFoundError(TaskDomainError):
    """Raised when a project is not found"""
    
    def __init__(self, message: str):
        super().__init__(message)


class TaskCompletionError(TaskDomainError):
    """Raised when a task cannot be completed due to business rule violations"""
    
    def __init__(self, message: str):
        super().__init__(message)


class TaskCreationError(TaskDomainError):
    """Raised when a task cannot be created"""
    
    def __init__(self, message: str):
        super().__init__(message)


class TaskUpdateError(TaskDomainError):
    """Raised when a task cannot be updated"""
    
    def __init__(self, message: str):
        super().__init__(message)


class DuplicateTaskError(TaskDomainError):
    """Raised when attempting to create a duplicate task"""
    
    def __init__(self, message: str):
        super().__init__(message) 