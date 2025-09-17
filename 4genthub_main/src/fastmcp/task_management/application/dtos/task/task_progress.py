"""Tracks current task and subtask progress"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

@dataclass
class TaskProgress:
    """Tracks current task and subtask progress"""
    current_task_id: Optional[int]
    current_subtask_id: Optional[str]
    task_start_time: Optional[str]
    subtask_start_time: Optional[str]
    completed_tasks: List[int]
    completed_subtasks: List[str]
    last_updated: str
    
    def to_dict(self) -> Dict:
        return asdict(self) 