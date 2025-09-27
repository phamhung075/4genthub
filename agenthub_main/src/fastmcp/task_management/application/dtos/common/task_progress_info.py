"""Enhanced progress tracking for tasks"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict

@dataclass
class TaskProgressInfo:
    """Enhanced progress tracking for tasks"""
    current_phase_index: int
    total_phases: int
    completion_percentage: float
    estimated_completion: Optional[str]
    
    def to_dict(self) -> Dict:
        return asdict(self) 