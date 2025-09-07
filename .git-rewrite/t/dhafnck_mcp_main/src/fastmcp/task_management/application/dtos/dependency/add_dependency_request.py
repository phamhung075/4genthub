"""Request DTO for adding a dependency between tasks."""

from dataclasses import dataclass
from typing import Union

@dataclass
class AddDependencyRequest:
    task_id: Union[str, int]
    depends_on_task_id: Union[str, int]
    dependency_type: str = "blocks"  # e.g., 'blocks', 'relates_to', etc. 