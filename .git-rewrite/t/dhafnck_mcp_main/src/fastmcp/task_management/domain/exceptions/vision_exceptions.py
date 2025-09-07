"""Vision System Domain Exceptions.

This module defines exceptions specific to the Vision System integration,
particularly for context enforcement and validation rules.
"""

from typing import Optional


class VisionSystemError(Exception):
    """Base exception for all vision system errors."""
    pass


class ContextEnforcementError(VisionSystemError):
    """Raised when context enforcement rules are violated."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        self.task_id = task_id
        super().__init__(message)


class MissingCompletionSummaryError(ContextEnforcementError):
    """Raised when attempting to complete a task without a completion summary."""
    
    def __init__(self, task_id: str):
        message = (
            f"Task '{task_id}' cannot be completed without a completion_summary. "
            "The Vision System requires a summary of what was accomplished."
        )
        super().__init__(message, task_id)


class InvalidContextUpdateError(ContextEnforcementError):
    """Raised when context update validation fails."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, field: Optional[str] = None):
        self.field = field
        super().__init__(message, task_id)


class WorkflowStateError(VisionSystemError):
    """Raised when workflow state transitions are invalid."""
    
    def __init__(self, message: str, current_state: str, attempted_state: str):
        self.current_state = current_state
        self.attempted_state = attempted_state
        super().__init__(message)


class VisionDataIntegrityError(VisionSystemError):
    """Raised when vision data integrity checks fail."""
    pass


class ProgressTrackingError(VisionSystemError):
    """Raised when progress tracking operations fail."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        self.task_id = task_id
        super().__init__(message)