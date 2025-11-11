"""Domain Exceptions"""

from .base import DomainException
from .base_exceptions import ValidationError
from .task_exceptions import (
    TaskNotFoundError,
    InvalidTaskStateError,
    InvalidTaskTransitionError,
    AutoRuleGenerationError,
    AgentNotFoundError,
    ProjectNotFoundError,
)

# Import application exceptions that are commonly used by use cases
from ...application.exceptions import (
    SubtaskNotFoundError,
    AuthorizationError as UnauthorizedAccessError,
    BusinessRuleViolationError,
)

# Create aliases for commonly used exceptions
GitBranchNotFoundError = ProjectNotFoundError  # Branch errors use project error
NoTasksAvailableError = (
    BusinessRuleViolationError  # No tasks is a business rule violation
)

__all__ = [
    "DomainException",
    "ValidationError",
    "TaskNotFoundError",
    "InvalidTaskStateError",
    "InvalidTaskTransitionError",
    "AutoRuleGenerationError",
    "AgentNotFoundError",
    "ProjectNotFoundError",
    # Application exceptions
    "SubtaskNotFoundError",
    "UnauthorizedAccessError",
    "GitBranchNotFoundError",
    "NoTasksAvailableError",
    "BusinessRuleViolationError",
]
