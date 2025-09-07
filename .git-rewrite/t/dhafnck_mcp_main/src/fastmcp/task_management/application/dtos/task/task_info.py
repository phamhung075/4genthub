"""Information about a task from tasks.json"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

from ..subtask.subtask_info import SubtaskInfo
from ....domain.value_objects.task_status import TaskStatus
from ....domain.value_objects.priority import Priority

@dataclass
class TaskInfo:
    """Information about a task from tasks.json"""
    id: int
    title: str
    description: str
    status: TaskStatus
    dependencies: List[int]
    priority: Priority
    details: str
    test_strategy: str
    estimated_effort: str
    actual_effort: Optional[str]
    assignees: List[str]
    labels: List[str]
    due_date: str
    code_context_paths: List[str]
    complexity_score: int
    recommended_subtasks: int
    subtasks: List[SubtaskInfo]
    
    def to_dict(self) -> Dict:
        task_dict = asdict(self)
        task_dict['status'] = self.status.value
        task_dict['priority'] = self.priority.value
        return task_dict 