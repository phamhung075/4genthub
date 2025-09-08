"""Response DTO containing subtask information"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class SubtaskResponse:
    task_id: str
    subtask: Dict[str, Any]
    progress: Dict[str, Any]
    agent_inheritance_applied: bool = field(default=False)
    inherited_assignees: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        result = {
            "task_id": self.task_id,
            "subtask": self.subtask,
            "progress": self.progress
        }
        
        # Include inheritance information if applied
        if self.agent_inheritance_applied:
            result["agent_inheritance_applied"] = self.agent_inheritance_applied
            result["inherited_assignees"] = self.inherited_assignees
        
        return result 