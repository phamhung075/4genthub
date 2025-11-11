"""Request DTO for creating a project"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreateProjectRequest:
    """Request DTO for creating a project"""

    # Required fields
    name: str

    # Optional fields with defaults
    description: str | None = None
