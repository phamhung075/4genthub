"""Task Status Value Object"""

from dataclasses import dataclass
from enum import Enum
from typing import Set


class TaskStatusEnum(Enum):
    """Enumeration of valid task statuses"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class TaskStatus:
    """Value object for Task Status with validation"""
    
    value: str
    
    # Class attributes for backward compatibility 
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review" 
    TESTING = "testing"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Task status cannot be empty")
        
        valid_statuses = {status.value for status in TaskStatusEnum}
        if self.value not in valid_statuses:
            raise ValueError(f"Invalid task status: {self.value}. Valid statuses: {', '.join(valid_statuses)}")
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def todo(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.TODO.value)
    
    @classmethod
    def in_progress(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.IN_PROGRESS.value)
    
    @classmethod
    def blocked(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.BLOCKED.value)
    
    @classmethod
    def review(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.REVIEW.value)
    
    @classmethod
    def testing(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.TESTING.value)
    
    @classmethod
    def done(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.DONE.value)
    
    @classmethod
    def cancelled(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.CANCELLED.value)
    
    @classmethod
    def archived(cls) -> 'TaskStatus':
        return cls(TaskStatusEnum.ARCHIVED.value)
    
    @classmethod
    def from_string(cls, value: str) -> 'TaskStatus':
        """Create TaskStatus from string value"""
        return cls(value.strip() if value else "todo")
    
    def is_todo(self) -> bool:
        return self.value == TaskStatusEnum.TODO.value
    
    def is_in_progress(self) -> bool:
        return self.value == TaskStatusEnum.IN_PROGRESS.value
    
    def is_done(self) -> bool:
        return self.value == TaskStatusEnum.DONE.value
    
    def is_completed(self) -> bool:
        """Alias for is_done() for backward compatibility"""
        return self.is_done()
    
    def can_transition_to(self, new_status: str) -> bool:
        """
        Check if transition to new status is valid based on business rules.
        
        Business Rule: Tasks follow a flexible workflow progression. Direct transitions from TODO to DONE
        are now allowed for quick task completion scenarios, while still supporting traditional workflows.
        
        Transition Rules:
        - TODO → IN_PROGRESS, CANCELLED, DONE (direct completion allowed)
        - IN_PROGRESS → BLOCKED, REVIEW, TESTING, CANCELLED, DONE
        - BLOCKED → IN_PROGRESS, CANCELLED
        - REVIEW → IN_PROGRESS, TESTING, DONE, CANCELLED
        - TESTING → IN_PROGRESS, REVIEW, DONE, CANCELLED
        - DONE → (no transitions - final state)
        - CANCELLED → TODO (can reopen)
        - ARCHIVED → (no transitions - final state)
        
        Note: The CompleteTaskUseCase handles both direct TODO → DONE and 
        traditional TODO → IN_PROGRESS → DONE transitions automatically.
        """
        transitions = {
            TaskStatusEnum.TODO.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.CANCELLED.value, TaskStatusEnum.DONE.value},
            TaskStatusEnum.IN_PROGRESS.value: {TaskStatusEnum.BLOCKED.value, TaskStatusEnum.REVIEW.value, TaskStatusEnum.TESTING.value, TaskStatusEnum.CANCELLED.value, TaskStatusEnum.DONE.value},
            TaskStatusEnum.BLOCKED.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.REVIEW.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.TESTING.value, TaskStatusEnum.DONE.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.TESTING.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.REVIEW.value, TaskStatusEnum.DONE.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.DONE.value: set(),  # No transitions from completed
            TaskStatusEnum.CANCELLED.value: {TaskStatusEnum.TODO.value},  # Can reopen cancelled tasks
            TaskStatusEnum.ARCHIVED.value: set()  # No transitions from archived
        }
        
        return new_status in transitions.get(self.value, set())
    
    def get_valid_transitions(self) -> Set[str]:
        """
        Get all valid status transitions from the current status.
        
        Returns:
            Set of valid status values this status can transition to
        """
        transitions = {
            TaskStatusEnum.TODO.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.CANCELLED.value, TaskStatusEnum.DONE.value},
            TaskStatusEnum.IN_PROGRESS.value: {TaskStatusEnum.BLOCKED.value, TaskStatusEnum.REVIEW.value, TaskStatusEnum.TESTING.value, TaskStatusEnum.CANCELLED.value, TaskStatusEnum.DONE.value},
            TaskStatusEnum.BLOCKED.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.REVIEW.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.TESTING.value, TaskStatusEnum.DONE.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.TESTING.value: {TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.REVIEW.value, TaskStatusEnum.DONE.value, TaskStatusEnum.CANCELLED.value},
            TaskStatusEnum.DONE.value: set(),
            TaskStatusEnum.CANCELLED.value: {TaskStatusEnum.TODO.value},
            TaskStatusEnum.ARCHIVED.value: set()
        }
        
        return transitions.get(self.value, set())
    
    def get_transition_error_message(self, target_status: str) -> str:
        """
        Get a helpful error message explaining why a transition is not valid.
        
        Args:
            target_status: The status attempting to transition to
            
        Returns:
            Error message explaining the business rule and suggesting alternatives
        """
        if self.can_transition_to(target_status):
            return f"Transition from {self.value} to {target_status} is valid."
        
        valid_transitions = self.get_valid_transitions()
        
        if not valid_transitions:
            return f"Status {self.value} is a final state with no valid transitions."
        
        return (
            f"Cannot transition from {self.value} to {target_status}. "
            f"Valid transitions from {self.value}: {', '.join(sorted(valid_transitions))}"
        ) 