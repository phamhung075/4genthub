"""Information about a subtask from tasks.json"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from ....domain.value_objects.task_status import TaskStatus
from ....domain.value_objects.priority import Priority

@dataclass
class SubtaskInfo:
    """Information about a subtask from tasks.json"""
    id: int
    title: str
    description: str
    status: TaskStatus
    assignees: List[str]
    progress_notes: str
    dependencies: List[str]
    priority: Priority
    details: str
    test_strategy: str
    estimated_effort: str
    subtasks: List['SubtaskInfo']
    
    def to_dict(self) -> Dict:
        subtask_dict = asdict(self)
        subtask_dict['status'] = self.status.value
        subtask_dict['priority'] = self.priority.value
        return subtask_dict 