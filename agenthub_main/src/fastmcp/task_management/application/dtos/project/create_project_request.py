"""Request DTO for creating a project"""

from dataclasses import dataclass


@dataclass
class CreateProjectRequest:
    """Request DTO for creating a project"""
    # Required fields
    name: str
    
    # Optional fields with defaults
    description: str | None = None 