"""
Application layer exceptions for task management domain.

These exceptions represent application-level errors that can occur during
business operations and use case execution.
"""

from typing import Any, Dict, Optional, Union


class TaskManagementException(Exception):
    """Base exception for all task management application errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class TaskNotFoundError(TaskManagementException):
    """Raised when a requested task cannot be found."""
    
    def __init__(self, task_id: Union[str, int], details: Optional[Dict[str, Any]] = None):
        message = f"Task with ID '{task_id}' not found"
        super().__init__(message, "TASK_NOT_FOUND", details)
        self.task_id = task_id


class SubtaskNotFoundError(TaskManagementException):
    """Raised when a requested subtask cannot be found."""
    
    def __init__(self, subtask_id: Union[str, int], task_id: Optional[Union[str, int]] = None, details: Optional[Dict[str, Any]] = None):
        if task_id:
            message = f"Subtask with ID '{subtask_id}' not found in task '{task_id}'"
        else:
            message = f"Subtask with ID '{subtask_id}' not found"
        super().__init__(message, "SUBTASK_NOT_FOUND", details)
        self.subtask_id = subtask_id
        self.task_id = task_id


class ValidationError(TaskManagementException):
    """Raised when input data fails validation."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class DuplicateError(TaskManagementException):
    """Raised when attempting to create a duplicate resource."""
    
    def __init__(self, resource: str, identifier: Union[str, int], details: Optional[Dict[str, Any]] = None):
        message = f"Duplicate {resource} with identifier '{identifier}'"
        super().__init__(message, "DUPLICATE_ERROR", details)
        self.resource = resource
        self.identifier = identifier


class AuthorizationError(TaskManagementException):
    """Raised when user lacks permission for the requested operation."""
    
    def __init__(self, operation: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if resource:
            message = f"Not authorized to {operation} {resource}"
        else:
            message = f"Not authorized to {operation}"
        super().__init__(message, "AUTHORIZATION_ERROR", details)
        self.operation = operation
        self.resource = resource


class BusinessRuleViolationError(TaskManagementException):
    """Raised when an operation violates business rules."""
    
    def __init__(self, rule: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "BUSINESS_RULE_VIOLATION", details)
        self.rule = rule


class ExternalServiceError(TaskManagementException):
    """Raised when an external service call fails."""
    
    def __init__(self, service: str, operation: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"External service '{service}' failed during '{operation}': {message}"
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR", details)
        self.service = service
        self.operation = operation