"""Information about a task from tasks.json"""

from dataclasses import asdict, dataclass

from ....domain.value_objects.priority import Priority
from ....domain.value_objects.task_status import TaskStatus
from ..subtask.subtask_info import SubtaskInfo


@dataclass
class TaskInfo:
    """Information about a task from tasks.json"""
    id: int
    title: str
    description: str
    status: TaskStatus
    dependencies: list[int]
    priority: Priority
    details: str
    test_strategy: str
    estimated_effort: str
    actual_effort: str | None
    assignees: list[str]
    labels: list[str]
    due_date: str
    code_context_paths: list[str]
    complexity_score: int
    recommended_subtasks: int
    subtasks: list[SubtaskInfo]
    
    def to_dict(self) -> dict:
        task_dict = asdict(self)
        task_dict['status'] = self.status.value
        task_dict['priority'] = self.priority.value
        return task_dict 