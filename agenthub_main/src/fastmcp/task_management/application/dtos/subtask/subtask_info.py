"""Information about a subtask from tasks.json"""

from dataclasses import asdict, dataclass

from ....domain.value_objects.priority import Priority
from ....domain.value_objects.task_status import TaskStatus


@dataclass
class SubtaskInfo:
    """Information about a subtask from tasks.json"""
    id: int
    title: str
    description: str
    status: TaskStatus
    assignees: list[str]
    progress_notes: str
    dependencies: list[str]
    priority: Priority
    details: str
    test_strategy: str
    estimated_effort: str
    subtasks: list['SubtaskInfo']
    
    def to_dict(self) -> dict:
        subtask_dict = asdict(self)
        subtask_dict['status'] = self.status.value
        subtask_dict['priority'] = self.priority.value
        return subtask_dict 