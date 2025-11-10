"""Tracks current task and subtask progress"""

from dataclasses import asdict, dataclass


@dataclass
class TaskProgress:
    """Tracks current task and subtask progress"""
    current_task_id: int | None
    current_subtask_id: str | None
    task_start_time: str | None
    subtask_start_time: str | None
    completed_tasks: list[int]
    completed_subtasks: list[str]
    last_updated: str
    
    def to_dict(self) -> dict:
        return asdict(self) 