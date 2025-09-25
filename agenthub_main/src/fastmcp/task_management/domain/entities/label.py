"""Label Domain Entity"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from .base.base_timestamp_entity import BaseTimestampEntity


@dataclass
class Label(BaseTimestampEntity):
    """Label entity for categorizing and organizing tasks"""

    id: int = 0
    name: str = ""
    color: str = "#0066cc"  # Default color
    description: str = ""

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id) if self.id else "unknown"
    
    def __post_init__(self):
        """Post initialization timestamp handling."""
        super().__post_init__()

    def _validate_entity(self) -> None:
        """Ensure label invariants hold."""
        if not self.name or not self.name.strip():
            raise ValueError("Label name cannot be empty")
        if self.color and not self._is_valid_hex_color(self.color):
            raise ValueError(
                f"Invalid color format: {self.color}. Expected hex color (e.g., #ff0000)"
            )
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Validate hex color format"""
        if not color or not color.startswith("#"):
            return False
        
        # Remove # and check if remaining is valid hex
        hex_part = color[1:]
        if len(hex_part) not in (3, 6):
            return False
        
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False
    
    def __str__(self) -> str:
        """String representation"""
        return f"Label({self.name})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"Label(id={self.id}, name='{self.name}', color='{self.color}')"
