"""Request DTO for updating a project"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateProjectRequest:
    """Request DTO for updating a project"""
    # Required fields
    project_id: str
    
    # Optional fields with defaults
    name: Optional[str] = None
    description: Optional[str] = None 