"""Enhanced progress tracking for tasks"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TaskProgressInfo:
    """Enhanced progress tracking for tasks"""

    current_phase_index: int
    total_phases: int
    completion_percentage: float
    estimated_completion: str | None

    def to_dict(self) -> dict:
        return asdict(self)
