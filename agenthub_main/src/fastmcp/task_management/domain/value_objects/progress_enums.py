"""
Progress State Domain Enums
Date: 2025-09-21

This file contains all enums related to progress state management following DDD principles.
"""

from enum import Enum
from typing import List


class ProgressState(Enum):
    """Progress state enum for stepper visualization"""
    INITIAL = "initial"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"

    @classmethod
    def get_all_states(cls) -> List[str]:
        """Get list of all progress states"""
        return [state.value for state in cls]

    @classmethod
    def is_valid_state(cls, state_str: str) -> bool:
        """Check if a state string is valid"""
        return state_str.lower() in cls.get_all_states()

    @classmethod
    def from_progress_percentage(cls, percentage: int) -> "ProgressState":
        """Convert progress percentage to progress state"""
        if percentage == 0:
            return cls.INITIAL
        elif percentage == 100:
            return cls.COMPLETE
        else:
            return cls.IN_PROGRESS

    @classmethod
    def from_task_status(cls, status: str) -> "ProgressState":
        """Convert task status to progress state"""
        status_lower = status.lower()
        if status_lower in ["todo", "pending"]:
            return cls.INITIAL
        elif status_lower in ["done", "completed", "finished"]:
            return cls.COMPLETE
        else:
            return cls.IN_PROGRESS

    def get_visual_indicator(self) -> str:
        """Get visual indicator for the progress state"""
        if self == ProgressState.INITIAL:
            return "○"  # Empty circle
        elif self == ProgressState.IN_PROGRESS:
            return "◐"  # Half-filled circle
        else:  # COMPLETE
            return "●"  # Filled circle

    def get_step_number(self) -> int:
        """Get the step number for stepper visualization"""
        state_to_step = {
            ProgressState.INITIAL: 1,
            ProgressState.IN_PROGRESS: 2,
            ProgressState.COMPLETE: 3
        }
        return state_to_step[self]

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further progression)"""
        return self == ProgressState.COMPLETE

    @property
    def is_active(self) -> bool:
        """Check if this state indicates active work"""
        return self == ProgressState.IN_PROGRESS