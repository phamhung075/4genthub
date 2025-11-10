"""Request DTO for updating a project"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateProjectRequest:
    """Request DTO for updating a project"""
    # Required fields
    project_id: str
    
    # Optional fields with defaults
    name: str | None = None
    description: str | None = None 