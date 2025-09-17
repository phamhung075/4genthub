"""Request DTO for creating a project"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateProjectRequest:
    """Request DTO for creating a project"""
    # Required fields
    name: str
    
    # Optional fields with defaults
    description: Optional[str] = None 