"""Context for current development task"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Literal
from datetime import datetime
from .task_progress_info import TaskProgressInfo

@dataclass
class TaskContext:
    """Context for current development task"""
    id: str
    title: str
    description: str
    requirements: List[str]
    current_phase: Literal["planning", "coding", "testing", "review", "completed"]
    assigned_roles: List[str]
    primary_role: str
    context_data: Dict
    created_at: datetime
    updated_at: datetime
    progress: TaskProgressInfo
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        return result 