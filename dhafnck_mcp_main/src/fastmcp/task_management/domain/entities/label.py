"""Label Domain Entity"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Label:
    """Label entity for categorizing and organizing tasks"""
    
    id: int
    name: str
    color: str = "#0066cc"  # Default color
    description: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post initialization validation"""
        if not self.name:
            raise ValueError("Label name cannot be empty")
        
        # Validate color format (simple hex color validation)
        if self.color and not self._is_valid_hex_color(self.color):
            raise ValueError(f"Invalid color format: {self.color}. Expected hex color (e.g., #ff0000)")
    
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