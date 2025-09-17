"""
Context-related enums for the unified context system.
"""

from enum import Enum
from typing import Optional


class ContextLevel(str, Enum):
    """
    Enumeration of context hierarchy levels.
    Global → Project → Branch → Task
    """
    GLOBAL = "global"
    PROJECT = "project" 
    BRANCH = "branch"
    TASK = "task"
    
    @classmethod
    def from_string(cls, value: str) -> 'ContextLevel':
        """Create ContextLevel from string value."""
        value_lower = value.lower()
        for level in cls:
            if level.value == value_lower:
                return level
        raise ValueError(f"Invalid context level: {value}. Valid levels are: {', '.join([l.value for l in cls])}")
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    def get_parent_level(self) -> Optional['ContextLevel']:
        """Get the parent level in the hierarchy."""
        hierarchy = {
            ContextLevel.TASK: ContextLevel.BRANCH,
            ContextLevel.BRANCH: ContextLevel.PROJECT,
            ContextLevel.PROJECT: ContextLevel.GLOBAL,
            ContextLevel.GLOBAL: None
        }
        return hierarchy.get(self)