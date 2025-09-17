"""Response DTO for dependency operations."""

from dataclasses import dataclass
from typing import Union, Optional, List

@dataclass
class DependencyResponse:
    success: bool
    message: Optional[str] = None
    task_id: Optional[Union[str, int]] = None
    depends_on_task_id: Optional[Union[str, int]] = None
    dependency_type: Optional[str] = None
    errors: Optional[List[str]] = None 