"""Response DTO containing subtask information"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SubtaskResponse:
    task_id: str
    subtask: Dict[str, Any]
    progress: Dict[str, Any] 
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "task_id": self.task_id,
            "subtask": self.subtask,
            "progress": self.progress
        } 